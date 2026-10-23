// A Language's Items screen (S-Items; FR-22; AD-13). params.lang is "en" or "fr".
//
// Every mount reads GET /api/items/<lang> and lists the Items of both Categories, each row a
// whole-row link to its Item detail with the Target, the Russian meaning, the Category and, only
// when the Item has Reference audio, the audio icon. The search field filters as you type: the
// read is debounced, and a sequence token drops any reply that isn't the latest query's, so a
// slow earlier reply never replaces newer results. Matching is the server's (AD-12). An empty
// collection hides the search; a search with no match says so; a failed read shows an inline
// alert with Try again.

import { errorMessage, listItems } from "../api.js";
import { CATEGORIES, categoryName, languageName } from "../catalog.js";
import { alertBox, element, skeleton, tryAgain } from "../dom.js";

const DEBOUNCE_MS = 300;
const PLACEHOLDER = "Search English or Russian";
const EMPTY_BODY = "Items are made from Captures.";
const AUDIO = "Reference audio";
const SVG = "http://www.w3.org/2000/svg";

// A speaker icon named "Reference audio" (the row's audio indicator; not a control)
function audioIcon() {
  const icon = element("span", "item-row-audio");
  icon.setAttribute("role", "img");
  icon.setAttribute("aria-label", AUDIO);
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const path = document.createElementNS(SVG, "path");
  path.setAttribute(
    "d",
    "M4 9v6h4l5 4V5L8 9H4zm12.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4zM14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6z",
  );
  svg.append(path);
  icon.append(svg);
  return icon;
}

export function mount(root, params) {
  const { lang } = params;
  const language = languageName(lang);
  let mounted = true;
  let timer = null;
  let seq = 0;
  // { query, items, error }: the latest settled read; null until the first one settles
  let shown = null;

  const screen = element("div", "items-screen");
  const heading = element("h1", "items-title", `${language} Items`);
  const search = element("div", "items-search");
  const box = element("input", "compose-field items-search-field");
  box.type = "text";
  box.setAttribute("aria-label", `Search ${language} Items`);
  box.placeholder = PLACEHOLDER;
  box.autocomplete = "off";
  box.spellcheck = false;
  search.append(box);
  search.hidden = true;
  const count = element("p", "items-count");
  count.hidden = true;
  const body = element("div", "items-body");
  screen.append(heading, search, count, body);
  root.replaceChildren(screen);

  function row(item) {
    const li = element("li");
    const link = element("a", "list-row item-row");
    link.href = `/${lang}/items/${encodeURIComponent(item.itemId)}`;
    const text = element("span", "item-row-body");
    const target = element("span", "item-row-target", item.target);
    const russian = element("span", "item-row-russian", item.russian);
    russian.lang = "ru";
    text.append(target, russian);
    const meta = element("span", "item-row-meta");
    if (item.hasAudio) meta.append(audioIcon());
    meta.append(element("span", "chip item-row-category", categoryName(item.category)));
    link.append(text, meta);
    li.append(link);
    return li;
  }

  function render() {
    if (shown.error) {
      count.hidden = true;
      body.replaceChildren(
        alertBox(
          "items-alert",
          element("p", "items-alert-body", errorMessage(shown.error)),
          tryAgain(() => load(shown.query)),
        ),
      );
      return;
    }
    const { query, items } = shown;
    const blank = !query.trim();
    if (!items.length && blank) {
      // An empty collection: nothing to search (EXPERIENCE.md Items empty)
      search.hidden = true;
      count.hidden = true;
      const empty = element("div", "items-empty");
      empty.append(
        element("p", "items-empty-title", `No ${language} Items yet`),
        element("p", "items-empty-body", EMPTY_BODY),
      );
      body.replaceChildren(empty);
      return;
    }
    search.hidden = false;
    if (!items.length) {
      count.hidden = true;
      body.replaceChildren(
        element("p", "items-empty-title", `No ${language} Items match “${query.trim()}”.`),
      );
      return;
    }
    count.hidden = !blank;
    const noun = items.length === 1 ? "Item" : "Items";
    const present = CATEGORIES.filter(([key]) => items.some((item) => item.category === key));
    const kinds = present.map(([key]) => categoryName(key)).join(" and ");
    count.textContent = `${items.length} ${noun} · ${kinds}`;
    const list = element("ul", "items-list");
    list.setAttribute("aria-label", `${language} Items`);
    list.append(...items.map(row));
    body.replaceChildren(list);
  }

  async function load(query) {
    const token = ++seq;
    // The first read, or a retry, shows the skeleton; a search keeps the rows until it settles
    if (shown === null || shown.error) body.replaceChildren(skeleton(`Loading ${language} Items…`));
    body.setAttribute("aria-busy", "true");
    let next;
    try {
      next = { query, items: (await listItems(lang, query)).items, error: null };
    } catch (error) {
      next = { query, items: null, error };
    }
    // Only the latest query's reply is shown
    if (!mounted || token !== seq) return;
    body.removeAttribute("aria-busy");
    shown = next;
    render();
  }

  box.addEventListener("input", () => {
    clearTimeout(timer);
    const query = box.value;
    timer = setTimeout(() => load(query), DEBOUNCE_MS);
  });

  load("");
  return () => {
    mounted = false;
    clearTimeout(timer);
    root.replaceChildren();
  };
}
