// Setup screen (AD-13). Readiness tiles from /api/setup/readiness (FR-5), then what Setup would
// change in Anki from /api/setup/plan (FR-6) and the study footer, then the server version from
// /api/health. Apply setup POSTs the plan's hash to /api/setup/apply; the progress card shows
// until the run ends, then a verification banner. The run is the server's: leaving doesn't
// cancel it, and coming back reads /api/setup/apply/status (polled while it runs). When the
// plan's `state` is `newer_schema` (AD-19), a blocking alert takes the change list's place and
// Apply setup is hidden.

import { applySetup, getApplyStatus, getHealth, getPlan, getReadiness } from "../api.js";

const SVG_NS = "http://www.w3.org/2000/svg";

// The server sends `{id, ok}` only; the copy lives here, keyed by check id
const CHECKS = {
  ankiConnect: {
    pass: "AnkiConnect reachable",
    fail: "AnkiConnect not reachable",
    fix: "Open Anki on the Mac mini and check that the AnkiConnect add-on is installed, then reload this page.",
  },
  azure: {
    pass: "Azure configured",
    fail: "Azure not configured",
    fix: "Add your Azure Speech key and region to the LanguageLab configuration on the Mac mini, restart LanguageLab, then reload this page.",
  },
  openrouter: {
    pass: "OpenRouter configured",
    fail: "OpenRouter not configured",
    fix: "Add your OpenRouter key to the LanguageLab configuration on the Mac mini, restart LanguageLab, then reload this page.",
  },
};

// Change rows go in this kind order, then action order within a kind (mockup S-Setup)
const KINDS = [
  ["deck", "Decks"],
  ["noteType", "Note types"],
  ["templates", "Card templates and CSS"],
  ["preset", "Deck options"],
];
const ACTIONS = [
  ["create", "Create"],
  ["repair", "Repair"],
  ["migrate", "Migrate"],
];
const UNMANAGED_KINDS = { deck: "Deck", noteType: "Note type" };

const APPLY_LABEL = "Apply setup";
const FIX_REASON = "Fix the failing check to continue.";
const PROGRESS = "Applying setup and verifying… Keep Anki open.";
const NEWER_SCHEMA = "newer_schema";
const NEWER_SCHEMA_ALERT = "Anki was set up by a newer LanguageLab. Install the latest release.";
const STATUS_POLL_MS = 1000;
// A discrepancy row: its kind, then what verify expected and found, by action and kind
const DISCREPANCY_KINDS = {
  deck: "Deck",
  noteType: "Note type",
  templates: "Card templates and CSS",
  preset: "Deck options",
};
const EXPECTED_FOUND = {
  "create:deck": "Expected this deck; found none.",
  "create:noteType": "Expected this note type; found none.",
  "create:templates": "Expected LanguageLab's card templates and CSS; found none.",
  "create:preset": "Expected this deck options preset; found none.",
  "repair:templates": "Expected LanguageLab's card templates and CSS; found different ones.",
  "repair:preset":
    "Expected sibling burying off on every Study and Pronunciation deck; found it on, or a deck on another preset.",
  "migrate:noteType": "Expected LanguageLab's fields; found different ones.",
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// Check or cross, drawn so it adds nothing to the tile's accessible text
function icon(ok) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "readiness-icon");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const paths = ok ? ["M5 12l5 5L20 7"] : ["M6 6l12 12", "M18 6L6 18"];
  for (const d of paths) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

function skeleton() {
  const node = element("div", "skeleton");
  node.setAttribute("role", "status");
  // Not a <p>: until readiness settles, the version line is the screen's only paragraph
  const label = element("div", "skeleton-label", "Checking Anki and your keys…");
  const bars = element("div", "skeleton-bars");
  bars.setAttribute("aria-hidden", "true");
  for (let i = 0; i < 3; i += 1) bars.append(element("span", "skeleton-bar"));
  node.append(label, bars);
  return node;
}

function subtitle(prefix) {
  const node = element("p", "setup-subtitle");
  node.append("Creates or repairs everything LanguageLab manages under the prefix ");
  node.append(element("b", "", prefix));
  node.append(". Safe to run again.");
  return node;
}

function readinessCard(checks, actions) {
  const card = element("section", "setup-card");
  const heading = element("h2", "setup-card-title", "Ready to go?");
  heading.id = "readiness-heading";
  const list = element("ul", "readiness-tiles");
  list.setAttribute("aria-labelledby", heading.id);
  for (const { id, ok } of checks) {
    const copy = CHECKS[id];
    if (!copy) continue; // a check this client doesn't know yet
    const item = element("li", "readiness-item");
    const tile = element("div", `readiness-tile readiness-tile-${ok ? "pass" : "fail"}`);
    tile.append(icon(ok), ok ? copy.pass : copy.fail);
    item.append(tile);
    if (!ok) {
      const hint = element("p", "readiness-fix-hint", copy.fix);
      hint.setAttribute("role", "alert");
      item.append(hint);
    }
    list.append(item);
  }
  card.append(heading, list, actions);
  return card;
}

// One row per kind and action: the kind, its resource names as muted detail, and a count chip
function changeRows(items) {
  const rows = [];
  for (const [kind, label] of KINDS) {
    for (const [action, word] of ACTIONS) {
      const names = items.filter((i) => i.kind === kind && i.action === action).map((i) => i.name);
      if (names.length === 0) continue;
      const row = element("li", "change-row");
      const text = element("span", "change-row-text", label);
      text.append(element("span", "change-row-detail", ` · ${names.join(", ")}`));
      row.append(text, element("span", "chip chip-accent", `${word} ${names.length}`));
      rows.push(row);
    }
  }
  return rows;
}

function changesCard(items) {
  const card = element("section", "setup-card");
  const header = element("div", "setup-card-header");
  const heading = element("h2", "setup-card-title", "What will change in Anki");
  heading.id = "changes-heading";
  header.append(heading, element("p", "setup-card-note", "Nothing changes until you apply."));
  const list = element("ul", "change-rows");
  list.setAttribute("aria-labelledby", heading.id);
  list.append(...changeRows(items));
  card.append(header, list);
  return card;
}

function nothingToChange() {
  const callout = element("section", "info-callout");
  callout.append(
    element("p", "info-callout-title", "Nothing to change."),
    element("p", "info-callout-detail", "Everything LanguageLab manages is already set up."),
  );
  return callout;
}

function unmanagedCard(unmanaged) {
  const card = element("section", "setup-card");
  const heading = element("h2", "setup-card-title", "Not managed by LanguageLab");
  heading.id = "unmanaged-heading";
  const list = element("ul", "change-rows");
  list.setAttribute("aria-labelledby", heading.id);
  for (const { kind, name } of unmanaged) {
    const row = element("li", "change-row");
    const text = element("span", "change-row-text", name);
    const kindLabel = UNMANAGED_KINDS[kind];
    if (kindLabel) text.append(element("span", "change-row-detail", ` · ${kindLabel}`));
    row.append(text);
    list.append(row);
  }
  card.append(heading, list);
  return card;
}

function studyFooter(prefix) {
  const footer = element("section", "info-callout");
  footer.append(
    element("p", "info-callout-title", `In Anki, study “${prefix}::Study”, not the root deck`),
    element(
      "p",
      "info-callout-detail",
      `Pronounce Cards live under ${prefix}::Pronunciation and are reviewed here, in LanguageLab.`,
    ),
  );
  return footer;
}

// In the failing readiness tile's pattern: an older release never writes a newer schema
function newerSchemaAlert() {
  const node = element("div", "readiness-tile newer-schema-alert");
  node.setAttribute("role", "alert");
  node.append(icon(false), NEWER_SCHEMA_ALERT);
  return node;
}

function isNewerSchema(body) {
  return body?.state === NEWER_SCHEMA;
}

function planSection(body) {
  const { prefix, items, unmanaged } = body;
  const main = isNewerSchema(body)
    ? newerSchemaAlert()
    : items.length > 0
      ? changesCard(items)
      : nothingToChange();
  const nodes = [main];
  if (unmanaged.length > 0) nodes.push(unmanagedCard(unmanaged));
  nodes.push(studyFooter(prefix));
  return nodes;
}

function progressCard() {
  const card = element("div", "progress-card", PROGRESS);
  card.setAttribute("role", "status");
  return card;
}

function verifiedBanner() {
  const banner = element("section", "verification-banner-verified");
  banner.setAttribute("role", "status");
  const disc = element("span", "verification-banner-disc");
  disc.setAttribute("aria-hidden", "true");
  const text = element("div", "verification-banner-text");
  text.append(
    element("div", "verification-banner-title", "Setup applied and verified"),
    element(
      "div",
      "verification-banner-detail",
      "Decks, note types, templates and deck options match what LanguageLab expects.",
    ),
  );
  banner.append(disc, text);
  return banner;
}

function discrepancyBanner(discrepancies, onRunAgain) {
  const banner = element("section", "verification-banner-discrepancy");
  banner.setAttribute("role", "alert");
  const count = discrepancies.length;
  const what = count === 1 ? "1 thing doesn't" : `${count} things don't`;
  const list = element("ul", "change-rows");
  for (const { action, kind, name } of discrepancies) {
    const row = element("li", "change-row");
    const text = element("span", "change-row-text", `${DISCREPANCY_KINDS[kind] ?? kind} · ${name}`);
    const found = EXPECTED_FOUND[`${action}:${kind}`];
    if (found) text.append(element("span", "verification-banner-found", found));
    row.append(text);
    list.append(row);
  }
  const again = element("button", "button button-primary", "Run Setup again");
  again.type = "button";
  again.addEventListener("click", onRunAgain);
  const actions = element("div", "verification-banner-actions");
  actions.append(again);
  banner.append(
    element("div", "verification-banner-title", `Setup applied, but ${what} match`),
    element(
      "div",
      "verification-banner-detail",
      "Anki was changed. Review the difference below, then run Setup again.",
    ),
    list,
    actions,
  );
  return banner;
}

function errorMessage(error) {
  // An ApiError carries the envelope's fixed message (AD-15)
  return error?.name === "ApiError" ? error.message : "LanguageLab could not reach the server.";
}

function inlineError(message) {
  const node = element("p", "inline-alert-error", message);
  node.setAttribute("role", "alert");
  return node;
}

export function mount(root) {
  let mounted = true;
  let pollTimer = null;
  const heading = element("h1", "", "Setup");
  const readiness = element("div", "setup-readiness");
  readiness.append(skeleton());
  // Empty until the plan arrives: nothing before the version line may be a <p> until then
  const plan = element("div", "setup-plan");
  const status = element("p", "setup-version");
  root.replaceChildren(heading, readiness, plan, status);

  // Apply setup and its reason, in the readiness card once readiness and the plan have arrived
  const actions = element("div", "setup-actions");
  const reason = element("span", "setup-actions-reason", FIX_REASON);
  const applyButton = element("button", "button button-primary", APPLY_LABEL);
  applyButton.type = "button";

  // What the screen knows. `view`: "list" (the change list), "applying" or "result"
  const state = {
    checks: null,
    plan: null,
    planError: null,
    run: undefined, // the apply status read on mount, until it is placed
    view: null,
    result: null,
    notice: null, // a message shown as an inline alert above the change list
  };

  function updateActions() {
    const { checks, plan: body, view } = state;
    const shown =
      checks !== null &&
      body !== null &&
      !isNewerSchema(body) &&
      (view === "applying" || (view === "list" && body.items.length > 0));
    if (!shown) {
      actions.replaceChildren();
      return;
    }
    const failing = checks.some((check) => !check.ok);
    const disabled = failing || view === "applying";
    applyButton.disabled = disabled;
    applyButton.classList.toggle("button-disabled", disabled);
    actions.replaceChildren(...(failing ? [reason] : []), applyButton);
  }

  function renderPlan() {
    if (state.planError) {
      // In place of the change list; readiness renders on its own
      plan.replaceChildren(inlineError(errorMessage(state.planError)));
      actions.replaceChildren(); // no Apply without a plan
      return;
    } else if (state.plan === null || state.view === null) {
      return;
    } else if (state.view === "list") {
      const notice = state.notice ? [inlineError(state.notice)] : [];
      plan.replaceChildren(...notice, ...planSection(state.plan));
    } else {
      const main =
        state.view === "applying"
          ? progressCard()
          : state.result.verified
            ? verifiedBanner()
            : discrepancyBanner(state.result.discrepancies, () => apply(state.result.planHash));
      plan.replaceChildren(main, studyFooter(state.plan.prefix));
    }
    updateActions();
  }

  function show(view, fields = {}) {
    Object.assign(state, { notice: null }, fields, { view });
    renderPlan();
  }

  // The plan read again: a finished result whose hash it still has shows; else the change list
  function reread(result, notice = null) {
    getPlan().then(
      (body) => {
        if (!mounted) return;
        state.plan = body;
        state.planError = null;
        if (result && result.planHash === body.planHash && !isNewerSchema(body)) {
          show("result", { result });
        } else {
          show("list", { notice });
        }
      },
      (error) => {
        if (!mounted) return;
        state.planError = error;
        renderPlan();
      },
    );
  }

  function pollStatus() {
    pollTimer = setTimeout(() => {
      pollTimer = null;
      getApplyStatus().then(
        (run) => {
          if (!mounted) return;
          if (run.state === "running") pollStatus();
          else reread(run.state === "finished" ? run.result : null);
        },
        () => {
          if (mounted) pollStatus();
        },
      );
    }, STATUS_POLL_MS);
  }

  function apply(planHash) {
    show("applying");
    applySetup(planHash).then(
      (result) => {
        if (mounted) show("result", { result });
      },
      (error) => {
        if (!mounted) return;
        if (error?.name === "ApiError" && error.code === "plan_changed") {
          reread(null, error.message);
        } else if (error?.name === "ApiError" && error.code === "setup_required") {
          reread(null); // the fresh plan's state (newer_schema) brings up its own alert
        } else {
          show("list", { notice: errorMessage(error) });
        }
      },
    );
  }

  // Once the status and the plan are both in: where the screen starts
  function place() {
    if (state.run === undefined || state.plan === null || state.view !== null) return;
    const run = state.run;
    if (run.state === "running") {
      show("applying");
      pollStatus();
    } else if (
      run.state === "finished" &&
      run.result?.planHash === state.plan.planHash &&
      !isNewerSchema(state.plan)
    ) {
      show("result", { result: run.result });
    } else {
      show("list");
    }
  }

  applyButton.addEventListener("click", () => {
    if (!applyButton.disabled && state.plan) apply(state.plan.planHash);
  });

  // First: a run in flight decides what the plan area shows
  getApplyStatus().then(
    (run) => {
      if (!mounted) return;
      state.run = run;
      place();
    },
    () => {
      if (!mounted) return;
      state.run = { state: "idle", result: null };
      place();
    },
  );

  getReadiness().then(
    ({ prefix, checks }) => {
      if (!mounted) return;
      state.checks = checks;
      readiness.replaceChildren(subtitle(prefix), readinessCard(checks, actions));
      updateActions();
    },
    (error) => {
      if (mounted) readiness.replaceChildren(inlineError(errorMessage(error)));
    },
  );

  getPlan().then(
    (body) => {
      if (!mounted) return;
      state.plan = body;
      place();
    },
    (error) => {
      if (!mounted) return;
      state.planError = error;
      renderPlan();
    },
  );

  // Last: a late /api/health must not write after unmount (tests/e2e/test_navigation.py)
  getHealth().then(
    ({ version }) => {
      if (mounted) status.textContent = `LanguageLab v${version}`;
    },
    () => {
      if (mounted) status.textContent = "LanguageLab could not reach the server.";
    },
  );

  return () => {
    mounted = false;
    if (pollTimer !== null) clearTimeout(pollTimer);
    root.replaceChildren();
  };
}
