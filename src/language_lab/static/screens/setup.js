// Setup screen (AD-13). Readiness tiles from /api/setup/readiness (FR-5), then the server
// version from /api/health.

import { getHealth, getReadiness } from "../api.js";

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

function readinessError(message) {
  const node = element("p", "inline-alert-error", message);
  node.setAttribute("role", "alert");
  return node;
}

export function mount(root) {
  let mounted = true;
  const heading = element("h1", "", "Setup");
  const readiness = element("div", "setup-readiness");
  readiness.append(skeleton());
  const status = element("p", "setup-version");
  root.replaceChildren(heading, readiness, status);

  getReadiness().then(
    ({ prefix, checks }) => {
      if (mounted) readiness.replaceChildren(subtitle(prefix), readinessCard(checks));
    },
    (error) => {
      // An ApiError carries the envelope's fixed message (AD-15)
      const message =
        error?.name === "ApiError" ? error.message : "LanguageLab could not reach the server.";
      if (mounted) readiness.replaceChildren(readinessError(message));
    },
  );

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
