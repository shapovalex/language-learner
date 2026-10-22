// Client-side routing for the shell (AD-13): History API, the Main nav and Menu sheet,
// the per-Language Items / Pronunciation nav, mounting one screen module at a time, the
// unsaved-changes guard on every way off a dirty screen, and the one-shot flash (story 1.7).
// A screen's `mount` returns its unmount function (or `{unmount}`). One that also carries
// `update(params)`, on that function or that object, stays mounted while the route moves
// within it (`/captures` ↔ `/captures/<id>`), so its unsaved state survives and no unsaved
// alert is asked (story 3.2).

// A path segment, percent-decoded; kept as it is when it isn't valid percent-encoding
function decoded(segment) {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
}

const ROUTES = [
  [/^\/captures$/, "captures", () => ({})],
  [/^\/captures\/([^/]+)$/, "captures", (m) => ({ captureId: decoded(m[1]) })],
  [/^\/(en|fr)\/items$/, "items", (m) => ({ lang: m[1] })],
  [/^\/(en|fr)\/pronunciation$/, "pronunciation", (m) => ({ lang: m[1] })],
  [/^\/setup$/, "setup", () => ({})],
];

const FALLBACK_PATH = "/captures";
const LANGUAGE_NAMES = { en: "English", fr: "French" };
const WIDE = "(min-width: 600px)";

let main;
let screenRoot;
let languageNav = null;
let unmountScreen = null;
let mountedName = null; // the mounted screen's route name
let updateScreen = null; // its `update(params)`, when it keeps its mount within its routes
let renderToken = 0;

let menuButton;
let menuSheet;
let scrim;
let menuRows = [];

// Unsaved-changes guard: null, or { kind, count, target } from the mounted screen
let dirty = null;
let currentPath = null;
let pendingAnswer = null; // the open alert's answer, shared by every leave asked meanwhile
let resolveAlert = null;
let alertReturnFocus = null;
let leaveSeq = 0;

let alertDialog;
let alertBody;
let alertButtons = [];
let keepButton;

// Flash: handed over by navigate(path, { flash }), shown once on the next screen
let pendingFlash = null;
let flashBanner = null;

function matchRoute(path) {
  for (const [pattern, name, toParams] of ROUTES) {
    const match = pattern.exec(path);
    if (match) return { name, params: toParams(match) };
  }
  return null;
}

// "captures", "en", "fr" or "setup": the Main nav area a route belongs to
function areaOf(route) {
  return route.params.lang ?? route.name;
}

function markCurrent(links, isCurrent) {
  for (const link of links) {
    if (isCurrent(link)) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }
}

function markCurrentArea(area) {
  markCurrent(document.querySelectorAll("a[data-area]"), (link) => link.dataset.area === area);
}

// Tab and Shift+Tab move focus round `items` only, entering at the first or last.
// Any modifiers: WebKit reaches buttons and links with Alt+Tab
function cycleFocus(event, items) {
  event.preventDefault();
  const index = items.indexOf(document.activeElement);
  const step = event.shiftKey ? -1 : 1;
  const next =
    index === -1
      ? event.shiftKey
        ? items.length - 1
        : 0
      : (index + step + items.length) % items.length;
  items[next].focus();
}

function renderLanguageNav(route) {
  const { lang } = route.params;
  if (!lang) {
    languageNav?.remove();
    languageNav = null;
    return;
  }
  if (!languageNav || languageNav.dataset.lang !== lang) {
    languageNav?.remove();
    languageNav = document.createElement("nav");
    languageNav.className = "segmented-control";
    languageNav.dataset.lang = lang;
    languageNav.setAttribute("aria-label", LANGUAGE_NAMES[lang]);
    for (const [section, label] of [
      ["items", "Items"],
      ["pronunciation", "Pronunciation"],
    ]) {
      const link = document.createElement("a");
      link.className = "segment";
      link.href = `/${lang}/${section}`;
      link.dataset.section = section;
      link.textContent = label;
      languageNav.append(link);
    }
    main.prepend(languageNav);
  }
  markCurrent(languageNav.querySelectorAll("a"), (link) => link.dataset.section === route.name);
}

async function render() {
  const route = matchRoute(location.pathname);
  if (!route) {
    history.replaceState(null, "", FALLBACK_PATH);
    return render();
  }
  const token = ++renderToken;
  currentPath = location.pathname;
  const flash = pendingFlash;
  pendingFlash = null;
  flashBanner?.remove();
  flashBanner = null;
  if (route.name === mountedName && updateScreen) {
    // Within the mounted screen: it stays, and so does its dirty state
    updateScreen(route.params);
    if (flash) showFlash(flash);
    return;
  }
  // Every completed navigation leaves the dirty state behind with the screen that set it
  setDirty(null);

  if (unmountScreen) {
    unmountScreen();
    unmountScreen = null;
  }
  mountedName = null;
  updateScreen = null;
  markCurrentArea(areaOf(route));
  renderLanguageNav(route);

  let screen;
  try {
    screen = await import(`./screens/${route.name}.js`);
  } catch {
    // A network blip, or a stale versioned asset after a server upgrade
    if (token !== renderToken) return;
    const alert = document.createElement("p");
    alert.setAttribute("role", "alert");
    alert.textContent = "LanguageLab could not load this screen. Reload the page.";
    screenRoot.replaceChildren(alert);
    return;
  }
  // A later navigation started while the module loaded: only the latest render mounts
  if (token !== renderToken) return;
  const mounted = screen.mount(screenRoot, route.params);
  unmountScreen = typeof mounted === "function" ? mounted : mounted.unmount;
  updateScreen = mounted.update ?? null;
  mountedName = route.name;
  if (flash) showFlash(flash);
}

function showFlash(message) {
  flashBanner = document.createElement("p");
  flashBanner.className = "success-banner";
  flashBanner.setAttribute("role", "status");
  flashBanner.textContent = message;
  main.prepend(flashBanner);
}

// Unsaved-changes guard

function onBeforeUnload(event) {
  event.preventDefault();
  event.returnValue = "";
}

export function setDirty(state) {
  dirty = state ?? null;
  if (dirty) {
    window.addEventListener("beforeunload", onBeforeUnload);
  } else {
    window.removeEventListener("beforeunload", onBeforeUnload);
  }
}

function describeLoss({ kind, count, target }) {
  if (kind === "draft") return "This Draft isn't saved.";
  if (kind === "capture") return "This Capture isn't saved.";
  return `${count} unsaved ${count === 1 ? "change" : "changes"} to “${target}”`;
}

function openAlert(trigger) {
  alertBody.textContent = describeLoss(dirty);
  alertReturnFocus = trigger;
  return new Promise((resolve) => {
    resolveAlert = resolve;
    alertDialog.showModal();
    keepButton.focus();
  });
}

// The one place the alert answers: its buttons, Esc, and a close the browser forces
function answerAlert(discard) {
  const resolve = resolveAlert;
  if (!resolve) return;
  resolveAlert = null;
  if (alertDialog.open) alertDialog.close();
  if (discard) setDirty(null);
  const trigger = alertReturnFocus;
  alertReturnFocus = null;
  if (trigger?.isConnected && trigger.checkVisibility?.() !== false) trigger.focus();
  // Settle now, not on the async close event, so a leave right after this one asks afresh
  pendingAnswer = null;
  resolve(discard);
}

function onAlertKeydown(event) {
  // Keep focus on Discard / Keep editing
  if (event.key === "Tab") cycleFocus(event, alertButtons);
}

function setUpAlert() {
  alertDialog = document.getElementById("unsaved-alert");
  alertBody = document.getElementById("unsaved-alert-body");
  alertButtons = [...alertDialog.querySelectorAll("button")];
  keepButton = alertDialog.querySelector('button[value="keep"]');

  for (const button of alertButtons) {
    button.addEventListener("click", () => answerAlert(button.value === "discard"));
  }
  // Esc is Keep editing
  alertDialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    answerAlert(false);
  });
  // A close the browser forces counts as Keep editing. The close event is queued, so it can
  // arrive after the alert reopened for the next leave: that one is not answered by it.
  alertDialog.addEventListener("close", () => {
    if (!alertDialog.open) answerAlert(false);
  });
  alertDialog.addEventListener("keydown", onAlertKeydown);
}

function ask(trigger) {
  if (!dirty) return Promise.resolve(true);
  pendingAnswer ??= openAlert(trigger);
  return pendingAnswer;
}

// Resolves true when the screen may be left: clean, or the user chose Discard. Never navigates.
export function confirmLeave() {
  return ask(null);
}

// Whether `path` is a route of the mounted screen that keeps its mount (no leave to ask about)
function staysOnScreen(path) {
  return updateScreen !== null && matchRoute(path)?.name === mountedName;
}

async function go(path, { flash, trigger } = {}) {
  if (path === location.pathname) return;
  if (dirty && !staysOnScreen(path)) {
    const seq = ++leaveSeq;
    // Only the latest leave asked while the alert was open goes ahead on Discard
    if (!(await ask(trigger)) || seq !== leaveSeq) return;
  }
  pendingFlash = flash ?? null;
  history.pushState(null, "", path);
  render();
}

export function navigate(path, { flash } = {}) {
  return go(path, { flash });
}

async function onPopState() {
  closeMenu();
  if (dirty && location.pathname !== currentPath && !staysOnScreen(location.pathname)) {
    // Put the dirty screen's URL back (this drops the entry history just moved off), then ask
    history.pushState(null, "", currentPath);
    // The alert is already asking about another leave: this one is undone, that one stands
    if (pendingAnswer) return;
    const seq = ++leaveSeq;
    // Discard cleared the dirty state, so this back is a clean one; a later leave wins
    if ((await ask(null)) && seq === leaveSeq) history.back();
    return;
  }
  render();
}

function onLinkClick(event) {
  if (
    event.defaultPrevented ||
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  ) {
    return;
  }
  const link = event.target instanceof Element ? event.target.closest('a[href^="/"]') : null;
  if (!link || (link.target && link.target !== "_self") || link.hasAttribute("download")) return;
  const url = new URL(link.href);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/static/")) return;

  event.preventDefault();
  let trigger = link;
  if (menuSheet.contains(link)) {
    closeMenu();
    trigger = menuButton;
  }
  go(url.pathname, { trigger });
}

// Menu sheet (phone)

function isMenuOpen() {
  return !menuSheet.hidden;
}

function openMenu() {
  menuSheet.hidden = false;
  scrim.hidden = false;
  main.inert = true;
  menuButton.setAttribute("aria-expanded", "true");
  const current = menuRows.find((row) => row.getAttribute("aria-current") === "page");
  (current ?? menuRows[0]).focus();
}

function closeMenu() {
  if (!isMenuOpen()) return;
  menuSheet.hidden = true;
  scrim.hidden = true;
  main.inert = false;
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.focus();
}

function onMenuKeydown(event) {
  if (!isMenuOpen()) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeMenu();
    return;
  }
  if (event.key === "Tab") cycleFocus(event, menuRows);
}

function setUpMenu() {
  menuButton = document.querySelector(".menu-button");
  menuSheet = document.getElementById("menu-sheet");
  scrim = document.querySelector(".scrim");
  menuRows = [...menuSheet.querySelectorAll("a")];

  menuButton.addEventListener("click", () => (isMenuOpen() ? closeMenu() : openMenu()));
  scrim.addEventListener("click", closeMenu);
  document.addEventListener("keydown", onMenuKeydown);
  // The sheet only exists below the breakpoint
  window.matchMedia(WIDE).addEventListener("change", (event) => {
    if (event.matches) closeMenu();
  });
}

export function start() {
  main = document.getElementById("app");
  screenRoot = document.createElement("div");
  screenRoot.className = "screen";
  main.replaceChildren(screenRoot);

  setUpMenu();
  setUpAlert();
  document.addEventListener("click", onLinkClick);
  window.addEventListener("popstate", onPopState);
  render();
}
