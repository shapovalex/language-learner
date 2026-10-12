// Client-side routing for the shell (AD-13): History API, the Main nav and Menu sheet,
// the per-Language Items / Pronunciation nav, and mounting one screen module at a time.

const ROUTES = [
  [/^\/captures$/, "captures", () => ({})],
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
let renderToken = 0;

let menuButton;
let menuSheet;
let scrim;
let menuRows = [];

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

function markCurrentArea(area) {
  for (const link of document.querySelectorAll("a[data-area]")) {
    if (link.dataset.area === area) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }
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
  for (const link of languageNav.querySelectorAll("a")) {
    if (link.dataset.section === route.name) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }
}

async function render() {
  const route = matchRoute(location.pathname);
  if (!route) {
    history.replaceState(null, "", FALLBACK_PATH);
    return render();
  }
  const token = ++renderToken;

  if (unmountScreen) {
    unmountScreen();
    unmountScreen = null;
  }
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
  unmountScreen = screen.mount(screenRoot, route.params);
}

export function navigate(path) {
  if (path === location.pathname) return;
  history.pushState(null, "", path);
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
  if (menuSheet.contains(link)) closeMenu();
  navigate(url.pathname);
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
  // Any modifiers: WebKit reaches links with Alt+Tab
  if (event.key === "Tab") {
    event.preventDefault();
    const index = menuRows.indexOf(document.activeElement);
    const step = event.shiftKey ? -1 : 1;
    const next =
      index === -1
        ? event.shiftKey
          ? menuRows.length - 1
          : 0
        : (index + step + menuRows.length) % menuRows.length;
    menuRows[next].focus();
  }
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
  document.addEventListener("click", onLinkClick);
  window.addEventListener("popstate", () => {
    closeMenu();
    render();
  });
  render();
}
