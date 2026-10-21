// Setup screen (AD-13). Readiness tiles from /api/setup/readiness (FR-5), then what Setup would
// change in Anki from /api/setup/plan (FR-6) and the study footer, then the server version from
// /api/health. Read-only: Apply setup is entry 7's.

import { getHealth, getPlan, getReadiness } from "../api.js";

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

function readinessCard(checks) {
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
  card.append(heading, list);
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

function planSection({ prefix, items, unmanaged }) {
  const nodes = [items.length > 0 ? changesCard(items) : nothingToChange()];
  if (unmanaged.length > 0) nodes.push(unmanagedCard(unmanaged));
  nodes.push(studyFooter(prefix));
  return nodes;
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
  const heading = element("h1", "", "Setup");
  const readiness = element("div", "setup-readiness");
  readiness.append(skeleton());
  // Empty until the plan arrives: nothing before the version line may be a <p> until then
  const plan = element("div", "setup-plan");
  const status = element("p", "setup-version");
  root.replaceChildren(heading, readiness, plan, status);

  getReadiness().then(
    ({ prefix, checks }) => {
      if (mounted) readiness.replaceChildren(subtitle(prefix), readinessCard(checks));
    },
    (error) => {
      if (mounted) readiness.replaceChildren(inlineError(errorMessage(error)));
    },
  );

  getPlan().then(
    (body) => {
      if (mounted) plan.replaceChildren(...planSection(body));
    },
    (error) => {
      // In place of the change list; readiness renders on its own
      if (mounted) plan.replaceChildren(inlineError(errorMessage(error)));
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
    root.replaceChildren();
  };
}
