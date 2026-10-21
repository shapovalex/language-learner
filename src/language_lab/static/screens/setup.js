// Setup screen (AD-13). Readiness tiles from /api/setup/readiness (FR-5), then what Setup would
// change in Anki from /api/setup/plan (FR-6) and the study footer, then the server version from
// /api/health. Apply setup POSTs the plan's hash to /api/setup/apply; the progress card shows
// until the run ends, then a verification banner. The run is the server's: leaving doesn't
// cancel it, and coming back reads /api/setup/apply/status (polled while it runs). When the
// plan's `state` is `newer_schema` (AD-19), a blocking alert takes the change list's place and
// Apply setup is hidden. After a field change, readiness's `fullSync` check fails: a warning
// tile asks for an upload in Anki Desktop until "I've uploaded" clears it (AD-17); it never
// disables Apply. Leftovers (story 2.11) show as "Optional repairs", one checkbox each,
// unchecked: a toggle re-reads the plan with the checked keys (the server hashes them), and
// Apply setup posts that plan's hash with the keys.

import {
  applySetup,
  fullSyncUploaded,
  getApplyStatus,
  getHealth,
  getPlan,
  getReadiness,
} from "../api.js";

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
  ["notes", "Notes"],
  ["templates", "Card templates and CSS"],
  ["preset", "Deck options"],
];
const ACTIONS = [
  ["create", "Create"],
  ["repair", "Repair"],
  ["migrate", "Migrate"],
];
const UNMANAGED_KINDS = { deck: "Deck", noteType: "Note type" };
const NEEDS_FULL_SYNC = "Needs a full sync afterwards.";

// Shown only while the `fullSync` check fails, as a warning: not a failing check (AD-17)
const FULL_SYNC = "fullSync";
const FULL_SYNC_TITLE = "Full sync required";
const FULL_SYNC_FIX = "Open Anki Desktop, sync, and choose Upload to AnkiWeb.";
const FULL_SYNC_UPLOADED = "I've uploaded";

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
  notes: "Notes",
  templates: "Card templates and CSS",
  preset: "Deck options",
  orphanMedia: "Media file",
  misplacedCard: "Card",
  unsuspendedCard: "Capture card",
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
  "migrate:notes": "Expected every note at LanguageLab's schema version; found older ones.",
  "repair:orphanMedia": "Expected this file deleted; found it still there.",
  "repair:misplacedCard": "Expected this card in its LanguageLab deck; found it elsewhere.",
  "repair:unsuspendedCard": "Expected this Capture card suspended; found it unsuspended.",
};

const REPAIR_KINDS = new Set(["orphanMedia", "misplacedCard", "unsuspendedCard"]);

// The keys of the checked repairs a run left as discrepancies: Run Setup again retries them
function repairKeys(discrepancies) {
  return discrepancies.filter((d) => REPAIR_KINDS.has(d.kind)).map((d) => `${d.kind}:${d.name}`);
}

// Optional repairs (story 2.11): default copy, not from the UX docs
const REPAIRS_HEADING = "Optional repairs";
const REPAIRS_HINT = "Nothing here changes unless you check it.";

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

// The Full sync required warning: title, fix, and "I've uploaded"
function fullSyncTile(onUploaded) {
  const item = element("li", "readiness-item");
  const tile = element("div", "readiness-tile readiness-tile-warning");
  tile.append(icon(false), FULL_SYNC_TITLE);
  const hint = element("p", "readiness-fix-hint readiness-fix-hint-warning", FULL_SYNC_FIX);
  hint.setAttribute("role", "alert");
  const uploaded = element("button", "button button-secondary", FULL_SYNC_UPLOADED);
  uploaded.type = "button";
  uploaded.addEventListener("click", () => {
    uploaded.disabled = true;
    onUploaded();
  });
  item.append(tile, hint, uploaded);
  return item;
}

function readinessCard(checks, actions, onUploaded) {
  const card = element("section", "setup-card");
  const heading = element("h2", "setup-card-title", "Ready to go?");
  heading.id = "readiness-heading";
  const list = element("ul", "readiness-tiles");
  list.setAttribute("aria-labelledby", heading.id);
  for (const { id, ok } of checks) {
    if (id === FULL_SYNC) {
      if (!ok) list.append(fullSyncTile(onUploaded));
      continue;
    }
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
      const group = items.filter((i) => i.kind === kind && i.action === action);
      if (group.length === 0) continue;
      const names = group.map((i) => i.name);
      const row = element("li", "change-row");
      const text = element("span", "change-row-text", label);
      text.append(element("span", "change-row-detail", ` · ${names.join(", ")}`));
      if (group.some((i) => i.requiresFullSync)) {
        text.append(element("span", "change-row-full-sync", NEEDS_FULL_SYNC));
      }
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

// A repair row's text and detail, by kind
function repairCopy(row) {
  switch (row.kind) {
    case "orphanMedia":
      return [row.name, "Not used by any note."];
    case "misplacedCard":
      return [`${row.noteType} · ${row.card}`, `In ${row.deck}; belongs in ${row.expectedDeck}.`];
    case "unsuspendedCard":
      return [`${row.noteType} card`, "Not suspended."];
    default:
      return [row.name, ""];
  }
}

function repairsCard(repairs, checked, onToggle) {
  const card = element("section", "setup-card");
  const header = element("div", "setup-card-header");
  const heading = element("h2", "setup-card-title", REPAIRS_HEADING);
  heading.id = "repairs-heading";
  header.append(heading, element("p", "setup-card-note", REPAIRS_HINT));
  const list = element("ul", "change-rows");
  list.setAttribute("aria-labelledby", heading.id);
  for (const row of repairs) {
    const item = element("li", "change-row repair-row");
    const label = element("label", "repair-row-label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = checked.includes(row.key);
    box.dataset.repairKey = row.key;
    box.addEventListener("change", () => onToggle(row.key, box.checked));
    const [title, detail] = repairCopy(row);
    const text = element("span", "change-row-text", title);
    if (detail) text.append(element("span", "repair-row-detail", detail));
    label.append(box, text);
    item.append(label);
    list.append(item);
  }
  card.append(header, list);
  return card;
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

function planSection(body, checked, onToggle) {
  const { prefix, items, unmanaged } = body;
  const repairs = body.repairs ?? [];
  const main = isNewerSchema(body)
    ? newerSchemaAlert()
    : items.length > 0
      ? changesCard(items)
      : nothingToChange();
  const nodes = [main];
  // A newer-schema Anki is never applied to, so nothing is offered
  if (repairs.length > 0 && !isNewerSchema(body)) {
    nodes.push(repairsCard(repairs, checked, onToggle));
  }
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
    checked: [], // the keys of the opt-in repairs the user checked (plan order once re-read)
    replanning: false, // a toggle's plan read is in flight: Apply waits for its hash
  };
  let planSeq = 0; // each plan read's number: an answer that isn't the latest is dropped

  // The plan, read with the checked repairs; `stale` when a later read was sent meanwhile
  function readPlan() {
    const seq = ++planSeq;
    return getPlan(state.checked).then(
      (body) => ({ stale: seq !== planSeq, body }),
      (error) => {
        if (seq !== planSeq) return { stale: true, body: null };
        throw error;
      },
    );
  }

  // A fresh plan: the checks it still offers stay checked, in its order
  function takePlan(body) {
    state.plan = body;
    state.planError = null;
    const offered = (body.repairs ?? []).map((row) => row.key);
    state.checked = offered.filter((key) => state.checked.includes(key));
  }

  function toggle(key, on) {
    const others = state.checked.filter((k) => k !== key);
    state.checked = on ? [...others, key] : others;
    state.replanning = true;
    updateActions();
    readPlan().then(
      ({ stale, body }) => {
        if (!mounted || stale) return;
        state.replanning = false;
        takePlan(body);
        if (state.view === "list") renderPlan();
      },
      (error) => {
        if (!mounted) return;
        state.replanning = false;
        state.planError = error;
        renderPlan();
      },
    );
  }

  function updateActions() {
    const { checks, plan: body, view } = state;
    const shown =
      checks !== null &&
      body !== null &&
      !isNewerSchema(body) &&
      (view === "applying" ||
        (view === "list" && (body.items.length > 0 || state.checked.length > 0)));
    if (!shown) {
      actions.replaceChildren();
      return;
    }
    // Full sync required is a warning, not a failing check: Apply stays enabled
    const failing = checks.some((check) => check.id !== FULL_SYNC && !check.ok);
    const disabled = failing || view === "applying" || state.replanning;
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
      // A re-render after a toggle keeps the focus on the box the user toggled
      const focused = document.activeElement?.dataset?.repairKey;
      plan.replaceChildren(...notice, ...planSection(state.plan, state.checked, toggle));
      if (focused) {
        const boxes = plan.querySelectorAll("input[data-repair-key]");
        [...boxes].find((box) => box.dataset.repairKey === focused)?.focus();
      }
    } else {
      const main =
        state.view === "applying"
          ? progressCard()
          : state.result.verified
            ? verifiedBanner()
            : discrepancyBanner(state.result.discrepancies, () =>
                apply(state.result.planHash, repairKeys(state.result.discrepancies)),
              );
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
    readPlan().then(
      ({ stale, body }) => {
        if (!mounted || stale) return;
        state.replanning = false;
        takePlan(body);
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

  function apply(planHash, repairs) {
    show("applying");
    applySetup(planHash, repairs).then(
      (result) => {
        if (!mounted) return;
        // The checked repairs ran: a plan read from here on starts with none checked
        show("result", { result, checked: [] });
        if (result.fullSyncRequired) loadReadiness(); // brings up the Full sync required tile
      },
      (error) => {
        if (!mounted) return;
        if (error?.name === "ApiError" && error.code === "plan_changed") {
          reread(null, error.message); // keeps the checks the fresh plan still offers
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
    if (!applyButton.disabled && state.plan) apply(state.plan.planHash, state.checked);
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

  function loadReadiness() {
    getReadiness().then(
      ({ prefix, checks }) => {
        if (!mounted) return;
        state.checks = checks;
        readiness.replaceChildren(subtitle(prefix), readinessCard(checks, actions, uploaded));
        updateActions();
      },
      (error) => {
        if (mounted) readiness.replaceChildren(inlineError(errorMessage(error)));
      },
    );
  }

  // "I've uploaded": clear Full sync required, then read readiness again (on a failure too,
  // which brings the tile back with its button)
  function uploaded() {
    const reload = () => {
      if (mounted) loadReadiness();
    };
    fullSyncUploaded().then(reload, reload);
  }

  loadReadiness();

  readPlan().then(
    ({ stale, body }) => {
      if (!mounted || stale) return;
      takePlan(body);
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
