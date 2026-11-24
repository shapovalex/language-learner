// A Language's Items screen (S-Items; FR-22; AD-13). params.lang is "en" or "fr".
//
// Every mount reads GET /api/items/<lang> and lists the Items of both Categories, each row a
// whole-row link to its Item detail with the Target, the Russian meaning, the Category and, only
// when the Item has Reference audio, the audio icon. The search field filters as you type: the
// read is debounced, and a sequence token drops any reply that isn't the latest query's, so a
// slow earlier reply never replaces newer results. Matching is the server's (AD-12). An empty
// collection hides the search; a search with no match says so; a failed read shows an inline
// alert with Try again.
//
// Flagged Items: a "Flagged" toggle button (`aria-pressed`) beside the search field lists only
// the Items with a card flagged in Anki (`flagged=true` on the same read, so search and filter
// settle through the same sequence token), combined with the search. Each flagged row shows a
// flag marker. The toggle is remembered per Language for the page's life, so coming back from
// an Item detail keeps it. With the filter on and nothing flagged the screen says so, and the
// search stays shown so the filter can be turned off.
//
// Example audio (backfill): once a read lists Vocabulary Items, "Add example audio" gives every
// Vocabulary Item with an Example and its Russian but no example audio that audio, in the saved
// Voice (the first listed when none is saved). It posts one batch at a time to
// /api/items/<lang>/example-audio and shows the progress after each; a failed Item is counted
// and skipped (`skip`), and running it again retries it. A failed request stops with an alert
// whose Try again goes on.

import { backfillExampleAudio, errorMessage, getVoices, listItems } from "../api.js";
import { CATEGORIES, categoryName, languageName } from "../catalog.js";
import { alertBox, element, skeleton, tryAgain } from "../dom.js";
import { chooseVoice } from "../reference-audio.js";

const DEBOUNCE_MS = 300;
const PLACEHOLDER = "Search English or Russian";
const EMPTY_BODY = "Items are made from Captures.";
const AUDIO = "Reference audio";
const BACKFILL = "Add example audio";
const BACKFILL_FAILED = "Example audio stopped";
const NO_VOICE = "No voices available for this language.";
const FLAGGED = "Flagged";
const SVG = "http://www.w3.org/2000/svg";

// The Flagged toggle of each Language, kept across mounts (back from an Item detail)
const flaggedOnly = new Map();

function svgIcon(className, label, d) {
  const icon = element("span", className);
  icon.setAttribute("role", "img");
  icon.setAttribute("aria-label", label);
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const path = document.createElementNS(SVG, "path");
  path.setAttribute("d", d);
  svg.append(path);
  icon.append(svg);
  return icon;
}

// A flag icon named "Flagged" (the row's flag marker; not a control)
function flagIcon() {
  return svgIcon("item-row-flag", FLAGGED, "M5 21V4h9l.4 2H20v10h-7l-.4-2H7v7H5z");
}

// A speaker icon named "Reference audio" (the row's audio indicator; not a control)
function audioIcon() {
  return svgIcon(
    "item-row-audio",
    AUDIO,
    "M4 9v6h4l5 4V5L8 9H4zm12.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4zM14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6z",
  );
}

export function mount(root, params) {
  const { lang } = params;
  const language = languageName(lang);
  let mounted = true;
  let timer = null;
  let seq = 0;
  // { query, flagged, items, error }: the latest settled read; null until the first one settles
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
  const toggle = element("button", "button button-secondary items-flag-toggle", FLAGGED);
  toggle.type = "button";
  toggle.setAttribute("aria-pressed", String(Boolean(flaggedOnly.get(lang))));
  search.append(box, toggle);
  search.hidden = true;
  const count = element("p", "items-count");
  count.hidden = true;
  const backfill = element("section", "items-backfill");
  backfill.setAttribute("aria-label", "Example audio");
  backfill.hidden = true;
  const body = element("div", "items-body");
  screen.append(heading, backfill, search, count, body);
  root.replaceChildren(screen);

  // {running, done, failed, remaining, error}: the backfill's progress; null before a run
  let progress = null;

  function renderBackfill() {
    const button = element("button", "button button-secondary", BACKFILL);
    button.type = "button";
    button.disabled = Boolean(progress?.running);
    button.addEventListener("click", () => runBackfill());
    const nodes = [button];
    if (progress) {
      const { running, done, failed, remaining } = progress;
      let text = running
        ? `Adding example audio… ${done} added · ${remaining ?? "?"} left`
        : `Example audio added to ${done} ${done === 1 ? "Item" : "Items"} · ${remaining} left`;
      if (failed) text += ` · ${failed} couldn't be made`;
      const status = element("p", "items-backfill-progress", text);
      status.setAttribute("role", "status");
      nodes.push(status);
      if (progress.error) {
        nodes.push(
          alertBox(
            "items-alert",
            element("p", "items-alert-body", `${BACKFILL_FAILED} — ${progress.error}`),
            tryAgain(() => runBackfill(true)),
          ),
        );
      }
    }
    backfill.replaceChildren(...nodes);
  }

  // The saved Voice of the Language, else the first one listed
  async function backfillVoice() {
    const { voices } = await getVoices(lang);
    return chooseVoice(voices, null, lang);
  }

  // Post batches until none is left; `resume` goes on from the last run's counts
  async function runBackfill(resume = false) {
    if (progress?.running) return;
    const carried = resume && progress ? progress : { done: 0, failed: 0, remaining: null };
    progress = { ...carried, running: true, error: null };
    renderBackfill();
    try {
      const voice = await backfillVoice();
      if (!mounted) return;
      if (!voice) {
        progress.error = NO_VOICE;
        progress.running = false;
        renderBackfill();
        return;
      }
      do {
        const batch = await backfillExampleAudio(lang, { voice, skip: progress.failed });
        if (!mounted) return;
        progress.done += batch.done;
        progress.failed += batch.failed;
        progress.remaining = batch.remaining;
        renderBackfill();
      } while (progress.remaining > 0);
    } catch (error) {
      if (!mounted) return;
      progress.error = errorMessage(error);
    }
    progress.running = false;
    renderBackfill();
    // The list's audio state may have changed: read it again
    load(shown?.query ?? "");
  }

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
    if (item.flagged) meta.append(flagIcon());
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
    const { query, flagged, items } = shown;
    const blank = !query.trim();
    if (!items.length && blank && !flagged) {
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
      const kind = flagged ? `flagged ${language}` : language;
      const text = blank
        ? `No ${kind} Items.`
        : `No ${kind} Items match “${query.trim()}”.`;
      body.replaceChildren(element("p", "items-empty-title", text));
      return;
    }
    count.hidden = !blank;
    const full = blank && !flagged;
    if (full && items.some((item) => item.category === "vocabulary") && backfill.hidden) {
      backfill.hidden = false;
      renderBackfill();
    }
    const noun = `${flagged ? "flagged " : ""}${items.length === 1 ? "Item" : "Items"}`;
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
    const flagged = Boolean(flaggedOnly.get(lang));
    let next;
    try {
      next = { query, flagged, items: (await listItems(lang, query, flagged)).items, error: null };
    } catch (error) {
      next = { query, flagged, items: null, error };
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

  toggle.addEventListener("click", () => {
    const on = !flaggedOnly.get(lang);
    flaggedOnly.set(lang, on);
    toggle.setAttribute("aria-pressed", String(on));
    clearTimeout(timer);
    load(box.value);
  });

  load("");
  return () => {
    mounted = false;
    clearTimeout(timer);
    root.replaceChildren();
  };
}
