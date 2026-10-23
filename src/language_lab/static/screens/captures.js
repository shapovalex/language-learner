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
//
// "Delete Capture" in detail asks through the router's confirmation, then DELETE
// /api/captures/<captureId> (FR-13). After it the list shows without it at /captures; a failed
// delete keeps the Capture with an inline alert in detail.
//
// Capture detail also has the Make an Item pane (stories 4.1, 4.2). "Generate Draft" opens
// /captures/<captureId>/new at once with "Writing your Draft…", asks POST /api/drafts/generate
// with the chosen text, Language, Category and Generation context, then fills the Draft editor
// from the reply; a failure shows its alert there with Try again, which sends the same request.
// "Write it myself" asks POST /api/drafts/blank for the ItemId and opens the blank Draft editor.
// The editor replaces the list and detail. The Draft and the Generation context live only in this
// module's memory (AD-13), so that route with no Draft in memory (a reload, a direct visit) shows
// the Capture instead, and the screen is dirty only once a Draft has values. Save to Anki is POST
// /api/items/<lang>; it returns to the Capture with the success banner, and a failed Save keeps
// the Draft and its ItemId, so Save again updates rather than duplicates (AD-20). Save to Anki
// first asks GET /api/items/<lang>/duplicates (story 4.3): a match opens the duplicate sheet,
// whose Create anyway saves, Cancel returns to the editor, and Open existing goes, once the
// router's unsaved alert allows, to the match's Item detail.

import {
  blankDraft,
  createCapture,
  deleteCapture,
  errorMessage,
  findDuplicates,
  generateDraft,
  getCapture,
  isApiError,
  listCaptures,
  saveItem,
} from "../api.js";
import { element, skeleton } from "../dom.js";
import { confirmDestructive, confirmLeave, navigate, redirect, setDirty } from "../router.js";
import {
  blankValues,
  chosenText,
  draftEditor,
  duplicateSheet,
  generatedValues,
  generatingScreen,
  itemPart,
  makeItemPane,
} from "./make-item.js";

const LABEL = "New Capture";
const PLACEHOLDER = "Paste or type a word, phrase or sentence";
const UNREACHABLE_TITLE = "Not saved — Anki isn't reachable";
const UNREACHABLE_BODY =
  "Make sure Anki Desktop is open on the Mac mini, then try again. Your text is still here.";
const LOADING = "Loading Captures…";
const EMPTY = "No Captures yet.";
const NEWEST_FIRST = "Newest first";
const NO_SELECTION = "Choose a Capture to see it here.";
const NOT_IN_ANKI = "This Capture isn't in Anki.";
const BACK = "‹ Captures";
const TWO_PANES = "(min-width: 1024px)";
const DELETE_CAPTURE = "Delete Capture";
const DELETE_TITLE = "Delete this Capture?";
const DELETE_BODY = "This removes the Capture from Anki. Items you made from it stay.";
const DELETE_CONFIRM = "Delete permanently";
const NOT_DELETED_TITLE = "Not deleted — Anki isn't reachable";
const NOT_DELETED_BODY = "Make sure Anki Desktop is open on the Mac mini, then try again.";
const MODEL_UNREACHABLE = ["Couldn't reach the model", "Your Capture is unchanged."];
const NOT_GENERATED = "Couldn't generate a Draft";
const INVALID_TWICE = "The model's answer failed the checks twice. Your Capture is unchanged.";

function capturePath(captureId) {
  return `/captures/${encodeURIComponent(captureId)}`;
}

function savedFlash(target) {
  return `Saved “${target}” to Anki. Make another Item from this Capture, or delete it.`;
}

// The pane's choices, as a Capture opens: Use as is, nothing picked
function freshChoice() {
  return {
    source: "capture",
    custom: "",
    language: null,
    category: null,
    context: "",
    busy: false,
    error: null,
  };
}

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

function loadError(error, onRetry) {
  const alert = element("div", "inline-alert-error captures-load-alert");
  alert.setAttribute("role", "alert");
  const again = element("button", "button button-destructive", "Try again");
  again.type = "button";
  again.addEventListener("click", onRetry);
  alert.append(element("p", "captures-load-alert-body", errorMessage(error)), again);
  return alert;
}

// [title, body] of a failed Save or delete: `unreachable` when Anki is down, else `title` and
// the envelope's message
function failureCopy(error, unreachable, title) {
  return isApiError(error, "anki_unavailable") ? unreachable : [title, errorMessage(error)];
}

// [title, body] of a failed generation (EXPERIENCE.md State Patterns)
function generationFailure(error) {
  if (isApiError(error, "llm_failed")) return MODEL_UNREACHABLE;
  if (isApiError(error, "llm_invalid_output")) return [NOT_GENERATED, INVALID_TWICE];
  return [NOT_GENERATED, errorMessage(error)];
}

// The failed delete's alert: no Try again, since Delete Capture is right there
function deleteAlert(error) {
  const [title, body] = failureCopy(error, [NOT_DELETED_TITLE, NOT_DELETED_BODY], "Not deleted");
  const alert = element("div", "inline-alert-error capture-delete-alert");
  alert.setAttribute("role", "alert");
  alert.append(
    element("p", "compose-alert-title", title),
    element("p", "capture-delete-alert-body", body),
  );
  return alert;
}

export function mount(root, params = {}) {
  let mounted = true;
  const state = { captureId: crypto.randomUUID(), busy: false, error: null };
  const twoPanes = window.matchMedia(TWO_PANES);

  const heading = element("h1", null, "Captures");
  heading.tabIndex = -1; // focus lands here after a delete removes the focused button
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
  // The Draft editor replaces the layout while it's open; the layout stays, with its compose text
  const draftRoot = element("div");
  draftRoot.hidden = true;
  root.replaceChildren(layout, draftRoot);

  // `captures`: null while loading or failed; `saved` are the ones saved meanwhile, newest first
  const list = { captures: null, error: null, saved: [], token: 0 };
  // `capture`: the open one, once known; `status`: "loading", "shown", "missing" or "failed"
  // `deleteError`: the open Capture's failed delete, shown until another Capture opens
  const open = {
    id: params.captureId ?? null,
    capture: null,
    status: null,
    error: null,
    deleteError: null,
    token: 0,
  };
  // The Make an Item pane's choices for the open Capture
  let choice = freshChoice();
  // The Draft, from "Generate Draft" or "Write it myself" until it's saved or left; `editing`
  // while it's on screen. A generated one has `values` null and `generation` set until its reply
  let draft = null;
  let editing = false;
  // The open duplicate sheet's <dialog>, over the Draft editor
  let sheet = null;

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
      listBody.replaceChildren(skeleton(LOADING));
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
    const content = element("div", "capture-detail-content");
    content.append(
      element("p", "capture-detail-text", open.capture.text),
      element("p", "capture-detail-time", detailTime(open.capture.createdAt)),
    );
    article.append(content);
    // Phone: in the header beside the back link (S-NewItem); desktop: in the card, beside the
    // text (S-CapturesDesk). Only once the read confirmed the Capture is in Anki
    const actions = element("div", "capture-detail-actions narrow-only");
    actions.append(back);
    if (open.status === "shown") {
      actions.append(deleteButton("narrow-only"));
      article.append(deleteButton("wide-only"));
    }
    detailPane.replaceChildren(actions, article);
    if (open.deleteError) detailPane.append(deleteAlert(open.deleteError));
    if (open.status === "shown") detailPane.append(makeItemPane(choice, { onGenerate, onWrite }));
  }

  // "Write it myself": a blank Draft of the chosen text, Language and Category
  async function onWrite() {
    const capture = open.capture;
    const target = chosenText(choice, capture.text);
    if (choice.busy || target === null || !choice.language || !choice.category) return;
    const picked = { ...choice };
    choice.busy = true;
    choice.error = null;
    renderDetail();
    try {
      const { itemId } = await blankDraft();
      if (!mounted || open.capture !== capture) return;
      choice.busy = false;
      draft = {
        captureId: capture.captureId,
        captureText: capture.text,
        language: picked.language,
        category: picked.category,
        itemId,
        values: blankValues(picked.category, target),
        busy: false,
        error: null,
      };
      navigate(`${capturePath(capture.captureId)}/new`);
    } catch (error) {
      if (!mounted || open.capture !== capture) return;
      choice.busy = false;
      choice.error = errorMessage(error);
      renderDetail();
    }
  }

  // "Generate Draft": open the Draft route at once, then ask the model
  async function onGenerate() {
    const capture = open.capture;
    const target = chosenText(choice, capture.text);
    if (choice.busy || target === null || !choice.language || !choice.category) return;
    choice.error = null;
    draft = {
      captureId: capture.captureId,
      captureText: capture.text,
      language: choice.language,
      category: choice.category,
      itemId: null,
      values: null,
      busy: false,
      error: null,
      generation: {
        request: {
          language: choice.language,
          category: choice.category,
          target,
          generationContext: choice.context,
        },
        busy: true,
        error: null,
      },
    };
    const pending = draft;
    await navigate(`${capturePath(capture.captureId)}/new`);
    // The route didn't open the editor (the leave was refused): there is no Draft to fill
    if (!mounted || draft !== pending || !editing) {
      if (draft === pending) draft = null;
      return;
    }
    generate(pending);
  }

  async function generate(pending) {
    const { generation } = pending;
    // The first ask: openEditor() already shows the loading state. Try again: show it now
    if (!generation.busy) {
      generation.busy = true;
      generation.error = null;
      renderEditor({ focus: "title" });
    }
    let reply;
    try {
      reply = await generateDraft(generation.request);
    } catch (error) {
      if (!mounted || draft !== pending) return;
      generation.busy = false;
      generation.error = error;
      if (editing) renderEditor({ focus: "retry" });
      return;
    }
    // Left meanwhile: a late reply opens nothing
    if (!mounted || draft !== pending) return;
    // Used once: the next Draft from this Capture starts without it
    choice.context = "";
    const { itemId, ...content } = reply;
    pending.itemId = itemId;
    pending.values = generatedValues(content);
    pending.generation = null;
    if (!editing) return;
    renderEditor({ focus: "title" });
    syncDirty();
  }

  // The one dirty state the router holds: the open Draft's once it has values, else the
  // compose text's
  function syncDirty() {
    if (editing && draft.values) {
      setDirty({ kind: "draft", count: 1, target: draft.values.target });
    } else {
      setDirty(box.value.trim() ? { kind: "capture", count: 1, target: "" } : null);
    }
  }

  function renderEditor({ focus = null } = {}) {
    if (!draft.values) {
      const { screen, title, retry } = generatingScreen(draft, {
        onRetry: () => generate(draft),
        alertFor: generationFailure,
      });
      draftRoot.replaceChildren(screen);
      if (focus === "title") title.focus();
      if (focus === "retry") retry?.focus();
      return;
    }
    const { screen, title } = draftEditor(draft, {
      onEdit: syncDirty,
      onSave: saveDraft,
      // The router asks about the Draft before it goes
      onDiscard: () => navigate(capturePath(draft.captureId)),
      alertFor: (error) => failureCopy(error, [UNREACHABLE_TITLE, UNREACHABLE_BODY], "Not saved"),
    });
    draftRoot.replaceChildren(screen);
    if (focus === "title") title.focus();
    if (focus === "save") draftRoot.querySelector('button[type="submit"]')?.focus();
  }

  function openEditor() {
    editing = true;
    layout.hidden = true;
    draftRoot.hidden = false;
    renderEditor({ focus: "title" });
    syncDirty();
  }

  function closeEditor() {
    closeSheet();
    draft = null;
    editing = false;
    draftRoot.replaceChildren();
    draftRoot.hidden = true;
    layout.hidden = false;
    syncDirty();
    renderDetail();
    // The editor's focused control is gone: back to the pane the Draft came from
    detailPane.querySelector(".make-item-heading")?.focus();
  }

  // Save to Anki: the duplicate check first (FR-19, decided 2026-10-22), then the Save. After
  // Create anyway the check is skipped while the Target is the one the user accepted
  async function saveDraft() {
    const saving = draft;
    if (!saving || saving.busy) return;
    saving.busy = true;
    saving.error = null;
    renderEditor();
    const item = itemPart(saving);
    if (saving.createdAnyway !== item.target) {
      let matches;
      try {
        ({ matches } = await findDuplicates(saving.language, {
          category: saving.category,
          target: item.target,
          itemId: saving.itemId,
        }));
      } catch (error) {
        if (!mounted || draft !== saving) return;
        saving.busy = false;
        saving.error = error;
        renderEditor({ focus: "save" });
        return;
      }
      if (!mounted || draft !== saving) return;
      if (matches.length > 0) {
        saving.busy = false;
        renderEditor();
        openSheet(saving, matches);
        return;
      }
    }
    try {
      await saveItem(saving.language, item);
    } catch (error) {
      if (!mounted || draft !== saving) return;
      saving.busy = false;
      saving.error = error;
      renderEditor({ focus: "save" });
      return;
    }
    if (!mounted || draft !== saving) return;
    setDirty(null);
    navigate(capturePath(saving.captureId), { flash: savedFlash(item.target) });
  }

  function openSheet(saving, matches) {
    const built = duplicateSheet(saving, matches, {
      onOpen: (match) => openExisting(saving, match),
      onCancel: () => {
        closeSheet();
        draftRoot.querySelector('button[type="submit"]')?.focus();
      },
      onCreate: () => {
        closeSheet();
        saving.createdAnyway = saving.values.target;
        saveDraft();
      },
    });
    sheet = built.dialog;
    root.append(sheet);
    sheet.showModal();
    built.primary.focus();
  }

  function closeSheet() {
    if (!sheet) return;
    if (sheet.open) sheet.close();
    sheet.remove();
    sheet = null;
  }

  // Open existing: the router asks about the Draft (AD-13); Keep editing leaves the sheet open
  async function openExisting(saving, match) {
    if (!(await confirmLeave())) return;
    if (!mounted || draft !== saving) return;
    closeSheet();
    setDirty(null);
    navigate(`/${saving.language}/items/${encodeURIComponent(match.itemId)}`);
  }

  function deleteButton(layout) {
    const button = element("button", `button-destructive-text ${layout}`, DELETE_CAPTURE);
    button.type = "button";
    button.addEventListener("click", () => onDelete(button));
    return button;
  }

  function forget(captureId) {
    list.saved = list.saved.filter((c) => c.captureId !== captureId);
    if (list.captures) list.captures = list.captures.filter((c) => c.captureId !== captureId);
  }

  async function onDelete(trigger) {
    const id = open.id;
    try {
      const deleted = await confirmDestructive({
        title: DELETE_TITLE,
        body: DELETE_BODY,
        confirmLabel: DELETE_CONFIRM,
        trigger,
        action: () => deleteCapture(id),
      });
      if (!deleted) return;
    } catch (error) {
      if (!mounted || open.id !== id) return;
      open.deleteError = error;
      renderDetail();
      // The alert replaced the button that had focus: give it the new one this layout shows
      const buttons = [...detailPane.querySelectorAll(".button-destructive-text")];
      buttons.find((button) => button.checkVisibility?.() !== false)?.focus();
      return;
    }
    if (!mounted) return;
    forget(id);
    renderList();
    if (open.id !== id) return;
    await navigate("/captures");
    if (mounted) heading.focus();
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
      if (isApiError(error, "not_found")) {
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
    open.deleteError = null;
    choice = freshChoice();
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
    const [title, body] = failureCopy(
      state.error,
      [UNREACHABLE_TITLE, UNREACHABLE_BODY],
      "Not saved",
    );
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
    syncDirty();
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
        syncDirty();
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
  // A Draft route with nothing in memory shows its Capture (AD-13)
  if (params.draft) redirect(capturePath(open.id));
  show(open.id);
  loadList();

  // The router's unmount, carrying `update` so the screen stays mounted within its routes
  const unmount = () => {
    mounted = false;
    closeSheet();
    root.replaceChildren();
  };
  // The route moved within Captures: open another Capture, or none
  unmount.update = (next) => {
    const id = next.captureId ?? null;
    if (next.draft) {
      if (draft?.captureId === id) {
        if (!editing) openEditor();
        return;
      }
      redirect(capturePath(id));
    }
    if (editing) closeEditor();
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
