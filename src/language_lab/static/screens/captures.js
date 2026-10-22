// Captures screen (AD-13). The compose box saves a Capture with POST /api/captures (FR-9). The
// CaptureId is made in the browser once per composition and kept across retries, so a retried
// Save never makes a second Capture (AD-8, AD-20). Unsaved text marks the screen dirty through
// the router.
//
// The list (GET /api/captures, newest first) sits under the compose box, and a Capture opens at
// /captures/<captureId> (GET /api/captures/<captureId>, FR-10). Below 1024px the detail is its
// own screen with the "‹ Captures" back link; from 1024px list and detail are two panes, with
// the open row selected. The screen stays mounted across those routes (`update`), so unsaved
// compose text survives opening a Capture. Times read in the browser's time zone, 24-hour.

import { createCapture, getCapture, listCaptures } from "../api.js";
import { setDirty } from "../router.js";

const LABEL = "New Capture";
const PLACEHOLDER = "Paste or type a word, phrase or sentence";
const UNREACHABLE_TITLE = "Not saved — Anki isn't reachable";
const UNREACHABLE_BODY =
  "Make sure Anki Desktop is open on the Mac mini, then try again. Your text is still here.";
const NETWORK_FALLBACK = "LanguageLab could not reach the server.";
const LOADING = "Loading Captures…";
const EMPTY = "No Captures yet.";
const NEWEST_FIRST = "Newest first";
const NO_SELECTION = "Choose a Capture to see it here.";
const NOT_IN_ANKI = "This Capture isn't in Anki.";
const BACK = "‹ Captures";
const TWO_PANES = "(min-width: 1024px)";

const TIME = new Intl.DateTimeFormat("en-US", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});
const DATE = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" });
const DATE_WITH_YEAR = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

function sameDay(a, b) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

// ["today" | "yesterday" | null, the date, the time], in local calendar dates
function timeParts(iso, now) {
  const at = new Date(iso);
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  const day = sameDay(at, now) ? "today" : sameDay(at, yesterday) ? "yesterday" : null;
  const date = (at.getFullYear() === now.getFullYear() ? DATE : DATE_WITH_YEAR).format(at);
  return [day, date, TIME.format(at)];
}

// "Today · 21:14", "Yesterday · 19:40", "Oct 5 · 12:31", "Oct 4, 2025 · 22:05"
export function rowTime(iso, now = new Date()) {
  const [day, date, time] = timeParts(iso, now);
  const when = day ? day[0].toUpperCase() + day.slice(1) : date;
  return `${when} · ${time}`;
}

// "Captured today · 21:14", "Captured yesterday · 19:40", "Captured Oct 5 · 12:31"
export function detailTime(iso, now = new Date()) {
  const [day, date, time] = timeParts(iso, now);
  return `Captured ${day ?? date} · ${time}`;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function errorMessage(error) {
  // An ApiError carries the envelope's fixed message (AD-15)
  return error?.name === "ApiError" ? error.message : NETWORK_FALLBACK;
}

function skeleton() {
  const node = element("div", "skeleton");
  node.setAttribute("role", "status");
  const label = element("div", "skeleton-label", LOADING);
  const bars = element("div", "skeleton-bars");
  bars.setAttribute("aria-hidden", "true");
  for (let i = 0; i < 3; i += 1) bars.append(element("span", "skeleton-bar"));
  node.append(label, bars);
  return node;
}

function loadError(error, onRetry) {
  const alert = element("div", "inline-alert-error captures-load-alert");
  alert.setAttribute("role", "alert");
  const again = element("button", "button button-destructive", "Try again");
  again.type = "button";
  again.addEventListener("click", onRetry);
  alert.append(element("p", "captures-load-alert-body", errorMessage(error)), again);
  return alert;
}

function failureCopy(error) {
  if (error?.name === "ApiError" && error.code === "anki_unavailable") {
    return [UNREACHABLE_TITLE, UNREACHABLE_BODY];
  }
  // An ApiError carries the envelope's fixed message (AD-15)
  return ["Not saved", error?.name === "ApiError" ? error.message : NETWORK_FALLBACK];
}

export function mount(root, params = {}) {
  let mounted = true;
  const state = { captureId: crypto.randomUUID(), busy: false, error: null };
  const twoPanes = window.matchMedia(TWO_PANES);

  const heading = element("h1", null, "Captures");
  const card = element("section", "compose-card");
  const label = element("label", "compose-label", LABEL);
  const box = element("textarea", "compose-field");
  box.rows = 3;
  box.placeholder = PLACEHOLDER;
  label.append(box);
  const alertSlot = element("div", "compose-alert-slot");
  const save = element("button", "button button-primary", "Save Capture");
  save.type = "button";
  card.append(label, alertSlot, save);

  // The list: header, then the skeleton, the empty state, the load error or the rows
  const listSection = element("section", "captures-list-section");
  const listHeader = element("div", "captures-list-header");
  const narrowCount = element("span", "narrow-only", NEWEST_FIRST);
  const wideCount = element("span", "wide-only");
  listHeader.append(narrowCount, wideCount);
  const listBody = element("div", "captures-list-body");
  listSection.append(listHeader, listBody);

  const listPane = element("div", "captures-list-pane");
  listPane.append(heading, card, listSection);
  const detailPane = element("div", "captures-detail-pane");
  const layout = element("div", "captures-layout");
  layout.append(listPane, detailPane);
  root.replaceChildren(layout);

  // `captures`: null while loading or failed; `saved` are the ones saved meanwhile, newest first
  const list = { captures: null, error: null, saved: [], token: 0 };
  // `capture`: the open one, once known; `status`: "loading", "shown", "missing" or "failed"
  const open = { id: params.captureId ?? null, capture: null, status: null, error: null, token: 0 };

  function withSaved(captures) {
    const ids = new Set(list.saved.map((c) => c.captureId));
    return [...list.saved, ...captures.filter((c) => !ids.has(c.captureId))];
  }

  function renderList() {
    listHeader.hidden = !list.captures?.length;
    if (list.error) {
      listBody.replaceChildren(loadError(list.error, loadList));
      return;
    }
    if (!list.captures) {
      listBody.replaceChildren(skeleton());
      return;
    }
    if (!list.captures.length) {
      listBody.replaceChildren(element("p", "captures-empty", EMPTY));
      return;
    }
    const n = list.captures.length;
    wideCount.textContent = `${n} ${n === 1 ? "Capture" : "Captures"} · newest first`;
    const ul = element("ul", "captures-list");
    ul.setAttribute("aria-label", "Captures");
    const now = new Date();
    for (const capture of list.captures) {
      const item = element("li");
      const link = element("a", "list-row capture-row");
      link.href = `/captures/${encodeURIComponent(capture.captureId)}`;
      link.dataset.captureId = capture.captureId;
      const body = element("span", "capture-row-body");
      body.append(
        element("span", "capture-row-text", capture.text),
        element("span", "capture-row-time", rowTime(capture.createdAt, now)),
      );
      link.append(body);
      item.append(link);
      ul.append(item);
    }
    listBody.replaceChildren(ul);
    markOpenRow();
  }

  function markOpenRow() {
    const selected = open.status === "missing" ? null : open.id;
    for (const link of listBody.querySelectorAll("a[data-capture-id]")) {
      if (link.dataset.captureId === selected) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    }
  }

  function backLink() {
    const link = element("a", "back-link narrow-only", BACK);
    link.href = "/captures";
    return link;
  }

  function renderDetail() {
    layout.classList.toggle("captures-detail-open", open.id !== null);
    markOpenRow();
    if (open.id === null) {
      detailPane.replaceChildren(element("p", "captures-hint wide-only", NO_SELECTION));
      return;
    }
    const back = backLink();
    if (open.status === "missing") {
      detailPane.replaceChildren(back, element("p", "captures-not-found", NOT_IN_ANKI));
      return;
    }
    if (open.status === "failed") {
      detailPane.replaceChildren(back, loadError(open.error, loadDetail));
      return;
    }
    if (!open.capture) {
      detailPane.replaceChildren(back);
      return;
    }
    const article = element("article", "capture-detail");
    article.append(
      element("p", "capture-detail-text", open.capture.text),
      element("p", "capture-detail-time", detailTime(open.capture.createdAt)),
    );
    detailPane.replaceChildren(back, article);
  }

  async function loadList() {
    const token = ++list.token;
    list.captures = null;
    list.error = null;
    renderList();
    try {
      const body = await listCaptures();
      if (!mounted || token !== list.token) return;
      list.captures = withSaved(body.captures);
    } catch (error) {
      if (!mounted || token !== list.token) return;
      list.error = error;
    }
    renderList();
  }

  async function loadDetail() {
    const token = ++open.token;
    const id = open.id;
    open.status = "loading";
    open.error = null;
    // Shown from the list at once when it's there; the read below refreshes it
    open.capture = list.captures?.find((c) => c.captureId === id) ?? null;
    renderDetail();
    try {
      const capture = await getCapture(id);
      if (!mounted || token !== open.token) return;
      open.capture = capture;
      open.status = "shown";
    } catch (error) {
      if (!mounted || token !== open.token) return;
      open.capture = null;
      if (error?.name === "ApiError" && error.code === "not_found") {
        open.status = "missing";
      } else {
        open.status = "failed";
        open.error = error;
      }
    }
    renderDetail();
  }

  function show(captureId) {
    open.id = captureId ?? null;
    if (open.id === null) {
      ++open.token;
      open.capture = null;
      open.status = null;
      open.error = null;
      renderDetail();
      return;
    }
    loadDetail();
  }

  function onSaved(capture) {
    list.saved = [capture, ...list.saved.filter((c) => c.captureId !== capture.captureId)];
    if (!list.captures) return; // the list in flight picks it up when it lands
    list.captures = withSaved(list.captures);
    renderList();
  }

  let again = null;

  // Only the disabled states: the alert isn't rebuilt per keystroke, so it isn't re-announced
  function renderButtons() {
    const blocked = state.busy || !box.value.trim();
    save.disabled = blocked;
    if (again) again.disabled = blocked;
  }

  function render() {
    again = null;
    if (!state.error) {
      alertSlot.replaceChildren();
      renderButtons();
      return;
    }
    const [title, body] = failureCopy(state.error);
    const alert = element("div", "inline-alert-error compose-alert");
    alert.setAttribute("role", "alert");
    again = element("button", "button button-destructive", "Try again");
    again.type = "button";
    again.addEventListener("click", submit);
    alert.append(
      element("p", "compose-alert-title", title),
      element("p", "compose-alert-body", body),
      again,
    );
    alertSlot.replaceChildren(alert);
    renderButtons();
  }

  function onInput() {
    setDirty(box.value.trim() ? { kind: "capture", count: 1, target: "" } : null);
    renderButtons();
  }

  async function submit() {
    const text = box.value;
    if (state.busy || !text.trim()) return;
    state.busy = true;
    state.error = null;
    render();
    try {
      const saved = await createCapture(state.captureId, text);
      if (!mounted) return;
      onSaved(saved);
      // Text typed while the Save was in flight is a new composition: keep it
      if (box.value === text) {
        box.value = "";
        setDirty(null);
      }
      state.captureId = crypto.randomUUID();
      state.busy = false;
      render();
      box.focus();
    } catch (error) {
      if (!mounted) return;
      state.busy = false;
      state.error = error;
      // Focus was on the Try again the attempt removed: give it the new one
      const focusLost = !document.activeElement || document.activeElement === document.body;
      render();
      if (focusLost && again) again.focus();
    }
  }

  box.addEventListener("input", onInput);
  save.addEventListener("click", submit);
  render();
  renderList();
  show(open.id);
  loadList();

  // The router's unmount, carrying `update` so the screen stays mounted within its routes
  const unmount = () => {
    mounted = false;
    root.replaceChildren();
  };
  // The route moved within Captures: open another Capture, or none
  unmount.update = (next) => {
    const id = next.captureId ?? null;
    if (id === open.id) return;
    const previous = open.id;
    show(id);
    if (twoPanes.matches) return;
    // Below 1024px the row or the back link that was clicked is hidden now: move focus on
    if (id !== null) {
      detailPane.querySelector(".back-link")?.focus();
    } else if (previous !== null) {
      const row = [...listBody.querySelectorAll("a[data-capture-id]")].find(
        (link) => link.dataset.captureId === previous,
      );
      row?.focus();
    }
  };
  return unmount;
}
