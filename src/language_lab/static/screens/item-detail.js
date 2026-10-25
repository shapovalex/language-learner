// Item detail, editable (S-ItemDetail; FR-22, FR-23; story 5.1). params are { lang, itemId }.
// Every mount reads the Item from Anki (AD-13), so a value edited in Anki shows the next time;
// nothing from the Items list or an earlier editor is reused. The editor shows the Category's
// fields, the Draft editor's own (make-item.js), and edits stay local until "Save changes"
// (FR-18, NFR-4). The unsaved chip and the router's unsaved alert count the fields that differ
// from the loaded values; back to the loaded values is clean again.
//
// Save changes is the existing Save, POST /api/items/<lang>, under the loaded ItemId with
// `audio: "keep"`, so it updates that note in place (AD-20). A changed Target is first checked
// for duplicates, this Item left out: a match opens the duplicate sheet, whose Cancel keeps the
// edits, Create anyway saves under this ItemId, and Open existing goes, once the router's
// unsaved alert allows, to the match. A failed Save keeps the edits and the dirty state, with an
// inline alert; Save changes again retries the same ItemId.
//
// Regenerate (FR-24, story 5.2) asks POST /api/drafts/regenerate with the edit buffer's Target
// and the Item's Language and Category, never the ItemId, and takes only its group: the Russian
// meaning and alternatives, the Vocabulary example and its translation, or the Sentence Note. The
// group's compare pair shows Current over (or beside) the Preview; Use preview copies the group
// into the edit buffer and Keep current drops the Preview. Neither writes: only Save changes does
// (NFR-4), and it never sends an open Preview. An open Preview counts as one unsaved change for
// the chip and the router's unsaved alert. One regeneration runs at a time; a failed one shows
// its alert with Try again in its group and leaves the buffer as it was, and a reply arriving
// after the screen is gone opens nothing. Previews stay open across a Save and compare against
// the new Current. Delete permanently removes the persisted Item, with a reusable confirmation;
// cancellation and failures keep this buffer and every Preview.
//
// Reference audio (FR-23, story 6.2) is a card after the fields. The current clip plays from
// /api/media/<audio> of this mount's read, never autoplaying; a clip that fails to load leaves
// the card without a player and the edits unaffected. Voice changes only write voice-pref.js;
// only "Regenerate audio" (or "Preview" when there is no audio) synthesizes, via 6.1's Preview,
// and writes nothing. Its compare pair offers Keep current / Use preview; "Remove audio" marks a
// pending removal that "Keep audio" undoes. The offered clip, the accepted one and the removal
// each count as one unsaved change and live only in screen memory. Save changes sends the
// intent (`replace` with the accepted Blob, `remove`, else `keep`) with the edits in one Save;
// a failed Save keeps them, so a retry resends the same bytes under the same ItemId. A buffer
// Target that differs from the remaining clip's Target warns "Audio no longer matches the
// text." without blocking Save. Blob URLs are revoked when replaced, discarded or left behind.

import {
  deleteItem,
  errorMessage,
  findDuplicates,
  getItem,
  isApiError,
  regenerateContent,
  saveItem,
} from "../api.js";
import { categoryName, languageName } from "../catalog.js";
import { alertBox, element, skeleton, tryAgain } from "../dom.js";
import {
  loadVoices as loadVoiceList,
  releasePlayer,
  requestPreview,
  voicePicker,
} from "../reference-audio.js";
import { confirmDestructive, confirmLeave, navigate, setDirty } from "../router.js";
import {
  duplicateSheet,
  editorFields,
  generatedValues,
  itemPart,
  saveBlocker,
  saveFailure,
} from "./make-item.js";

const LOADING = "Loading Item…";
const NOT_IN_ANKI = "This Item isn't in Anki.";
const SAVE_CHANGES = "Save changes";
const WRITING_PREVIEW = "Writing a Preview…";
const CURRENT = "Current";
const PREVIEW_NOT_SAVED = "Preview · not saved";
const KEEP_CURRENT = "Keep current";
const USE_PREVIEW = "Use preview";
const NOT_REGENERATED = "Couldn't regenerate";
const MODEL_UNREACHABLE = ["Couldn't reach the model", "Your Item is unchanged."];
const INVALID_TWICE = "The model's answer failed the checks twice. Your Item is unchanged.";
const EMPTY = "—";

// The regenerable groups: the buffer keys each takes from the reply, the field its slot follows,
// and the Categories that have it
const GROUPS = [
  {
    key: "russian",
    name: "Russian meaning",
    button: "Regenerate Russian meaning",
    fields: ["russian", "alternatives"],
    after: "alternatives",
    categories: ["vocabulary", "sentence"],
  },
  {
    key: "example",
    name: "Example",
    button: "Regenerate example",
    fields: ["example", "exampleRussian"],
    after: "exampleRussian",
    categories: ["vocabulary"],
  },
  {
    key: "note",
    name: "Note",
    button: "Regenerate Note",
    fields: ["note"],
    after: "note",
    categories: ["sentence"],
  },
];

// Changed fields, plus one per open Preview (EXPERIENCE.md "Unsaved … Preview") and one per
// pending audio state (offered, accepted, removal)
function unsavedCount(values, loaded, previews, audioPending = 0) {
  const changed = Object.keys(loaded).filter((key) => values[key] !== loaded[key]).length;
  return changed + Object.keys(previews).length + audioPending;
}

const REGENERATE_AUDIO = "Regenerate audio";
const PREVIEW_AUDIO = "Preview";
const MAKING_AUDIO = "Making audio…";
const REMOVE_AUDIO = "Remove audio";
const KEEP_AUDIO = "Keep audio";
const REMOVAL_NOTE = "Audio will be removed when you save.";
const STALE_AUDIO = "Audio no longer matches the text.";
const TTS_FAILED = "Couldn't make the audio. Current audio is unchanged.";
const MEDIA_FAILED = "Couldn't load the saved audio.";
let compareIds = 0; // unique ids for the audio compare headings
const AUDIO_COMPARE_HINT = "The old audio is removed only after Save succeeds.";

// The Item's Reference audio card (story 6.2). `values()` is the edit buffer, `busy()` whether
// a Save or Delete runs, `changed()` reports a pending-state change to the screen. State stays
// in this closure: `current` ({url, target, blob?}: the saved clip, a /api/media URL or, after a
// replace Save, the accepted Blob's URL), `offered` and `accepted` ({blob, url, target}) and
// `removing`. Players are kept per URL, so a re-render moves them without stopping playback.
function itemAudioCard({ language, audioName, target, values, busy, changed }) {
  const state = {
    voices: [], voice: null, loading: true, voiceError: false,
    previewing: false, previewError: false, sequence: 0, disposed: false,
    current: audioName ? { url: `/api/media/${encodeURIComponent(audioName)}`, target } : null,
    currentFailed: false, offered: null, accepted: null, removing: false,
  };
  const players = new Map(); // url -> <audio>
  const card = element("section", "reference-audio item-reference-audio");
  card.setAttribute("aria-label", "Reference audio");
  const heading = element("h2", "make-item-heading", "Reference audio");
  const body = element("div", "reference-audio-body");
  card.append(heading, body);
  let stale = null; // the stale row, updated on every edit
  let controls = []; // buttons whose disabled state follows busy/previewing
  let nodes = {}; // this render's focus targets: regenerate, remove, keepAudio, compare, retry

  function remaining() {
    if (state.removing) return null;
    return state.accepted ?? state.current;
  }

  function release(clip) {
    if (!clip) return;
    const audio = players.get(clip.url);
    if (audio) {
      releasePlayer(audio);
      players.delete(clip.url);
    }
    if (clip.blob) URL.revokeObjectURL(clip.url);
  }

  function button(label, action, className = "button button-secondary") {
    const node = element("button", className, label);
    node.type = "button";
    node.addEventListener("click", action);
    controls.push(node);
    return node;
  }

  function player(clip, label) {
    const wrap = element("div", "reference-audio-clip");
    let audio = players.get(clip.url);
    if (!audio) {
      audio = element("audio");
      audio.controls = true;
      audio.preload = clip.blob ? "auto" : "metadata";
      audio.src = clip.url;
      if (clip === state.current && !clip.blob) {
        audio.addEventListener("error", () => {
          if (state.disposed || state.current !== clip) return;
          state.currentFailed = true;
          players.delete(clip.url);
          render();
        });
      }
      players.set(clip.url, audio);
    }
    audio.setAttribute("aria-label", label);
    wrap.append(audio);
    return wrap;
  }

  function currentPlayer() {
    const clip = remaining();
    if (!clip) return null;
    if (clip === state.current && state.currentFailed) {
      return element("p", "make-item-hint", MEDIA_FAILED);
    }
    return player(clip, clip === state.accepted ? "Play new audio" : "Play current audio");
  }

  function render() {
    if (state.disposed) return;
    controls = [];
    nodes = {};
    body.replaceChildren();
    body.append(...voicePicker(state, language, loadVoices));

    const hasAudio = Boolean(state.current || state.accepted);
    const regenerateRow = element("div", "reference-audio-actions");
    const regenerate = button(
      state.previewing ? MAKING_AUDIO : hasAudio ? REGENERATE_AUDIO : PREVIEW_AUDIO,
      preview,
    );
    if (state.previewing) regenerate.setAttribute("aria-busy", "true");
    regenerate.dataset.role = "regenerate";
    nodes.regenerate = regenerate;
    regenerateRow.append(regenerate);
    if (remaining()) {
      nodes.remove = button(REMOVE_AUDIO, removeAudio, "button-link");
      regenerateRow.append(nodes.remove);
    }
    stale = element("p", "reference-audio-stale", STALE_AUDIO);
    regenerateRow.append(stale);

    if (state.offered) {
      const pair = element("section", "compare-pair reference-audio-compare");
      pair.setAttribute("role", "group");
      const title = element("h3", "compare-title", "Reference audio · compare");
      title.id = `compare-audio-${++compareIds}`;
      title.tabIndex = -1;
      nodes.compare = title;
      pair.setAttribute("aria-labelledby", title.id);
      const panes = element("div", "compare-panes");
      const now = element("div", "compare-pane compare-current");
      now.append(element("span", "compare-label", CURRENT));
      now.append(currentPlayer() ?? element("p", "compare-secondary", "No audio"));
      const offered = element("div", "compare-pane compare-preview");
      offered.append(
        element("span", "compare-label", PREVIEW_NOT_SAVED),
        player(state.offered, "Play audio preview"),
      );
      panes.append(now, offered);
      const actions = element("div", "compare-actions");
      actions.append(
        button(KEEP_CURRENT, keepCurrent),
        button(USE_PREVIEW, usePreview, "button button-soft"),
      );
      pair.append(
        title,
        panes,
        element("p", "make-item-hint", AUDIO_COMPARE_HINT),
        actions,
      );
      body.append(regenerateRow, pair);
    } else {
      const clip = currentPlayer();
      if (clip) body.append(clip);
      body.append(regenerateRow);
      if (state.accepted) {
        body.append(element("p", "make-item-hint", "New audio · saved when you save."));
      }
    }
    if (state.removing) {
      const row = element("div", "reference-audio-removal");
      row.append(element("p", "reference-audio-removal-note", REMOVAL_NOTE));
      nodes.keepAudio = button(KEEP_AUDIO, keepAudio, "button-link");
      row.append(nodes.keepAudio);
      body.append(row);
    }
    if (state.previewError) {
      nodes.retry = tryAgain(preview);
      body.append(alertBox("reference-audio-error", TTS_FAILED, nodes.retry));
    }
    refresh();
  }

  // Stale warning and disabled states: run on every edit, without rebuilding the players
  function refresh() {
    if (state.disposed) return;
    const clip = remaining();
    if (stale) stale.hidden = !clip || clip.target === values().target;
    const blocked = busy() || state.previewing;
    for (const node of controls) {
      if (node.dataset.role === "regenerate") {
        // The in-flight button stays focusable, marked busy and aria-disabled (preview()
        // refuses re-entry)
        if (state.previewing) {
          node.disabled = false;
          node.setAttribute("aria-disabled", "true");
          continue;
        }
        node.disabled = busy() || state.loading || !state.voice || !values().target.trim();
      } else {
        node.disabled = blocked;
      }
    }
  }

  // Report a pending-state change, then focus `key` of the re-rendered card (the pressed
  // control is gone), as the text groups do
  function settle(key) {
    changed();
    if (!state.disposed) nodes[key]?.focus();
  }

  function loadVoices() {
    return loadVoiceList(state, language, render);
  }

  // The only synthesis: the buffer's Target in the chosen Voice, kept in memory (NFR-4)
  async function preview() {
    const text = values().target;
    if (state.previewing || busy() || !state.voice || !text.trim()) return;
    const voice = state.voice;
    state.previewing = true;
    state.previewError = false;
    render();
    nodes.regenerate?.focus();
    try {
      const blob = await requestPreview(state, { language, voice, target: text });
      if (!blob) return;
      release(state.offered);
      state.offered = { blob, target: text, url: URL.createObjectURL(blob) };
    } catch {
      state.previewError = true;
    }
    state.previewing = false;
    render();
    settle(state.previewError ? "retry" : "compare");
  }

  function keepCurrent() {
    release(state.offered);
    state.offered = null;
    render();
    settle("regenerate");
  }

  function usePreview() {
    if (!state.offered) return;
    release(state.accepted);
    state.accepted = state.offered;
    state.offered = null;
    state.removing = false;
    render();
    settle("regenerate");
  }

  function removeAudio() {
    release(state.accepted);
    state.accepted = null;
    state.removing = Boolean(state.current);
    render();
    settle(state.removing ? "keepAudio" : "regenerate");
  }

  function keepAudio() {
    state.removing = false;
    render();
    settle("remove");
  }

  render();
  loadVoices();
  return {
    card,
    render,
    refresh,
    // Unsaved changes the card holds: one each for the offered clip, accepted clip, removal
    pending: () => Number(Boolean(state.offered)) + Number(Boolean(state.accepted))
      + Number(state.removing),
    intent: () => (state.accepted ? "replace" : state.removing ? "remove" : "keep"),
    blob: () => state.accepted?.blob ?? null,
    // A successful Save of `intent`: the accepted clip becomes Current, or the clip is gone
    saved(intent) {
      if (state.disposed) return;
      if (intent === "replace" && state.accepted) {
        release(state.current);
        state.current = state.accepted;
        state.currentFailed = false;
        state.accepted = null;
      } else if (intent === "remove") {
        release(state.current);
        state.current = null;
        state.currentFailed = false;
        state.removing = false;
      }
      render();
    },
    dispose() {
      state.disposed = true;
      for (const clip of [state.current, state.accepted, state.offered]) release(clip);
      for (const audio of players.values()) {
        audio.pause();
        audio.removeAttribute("src");
      }
      players.clear();
      state.current = state.accepted = state.offered = null;
    },
  };
}

// [title, body] of a failed regeneration: the Draft's copy (captures.js), for an Item
function regenerationFailure(error) {
  if (isApiError(error, "llm_failed")) return MODEL_UNREACHABLE;
  if (isApiError(error, "llm_invalid_output")) return [NOT_REGENERATED, INVALID_TWICE];
  return [NOT_REGENERATED, errorMessage(error)];
}

// One pane's lines: the group's first field, then the rest muted (alternatives one per line)
function paneLines(group, groupValues) {
  const [first, ...rest] = group.fields;
  const lines = [element("p", "compare-main", groupValues[first] || EMPTY)];
  for (const key of rest) {
    const text = groupValues[key].split("\n").filter((line) => line.trim()).join("; ");
    if (text) lines.push(element("p", "compare-secondary", text));
  }
  return lines;
}

function comparePane(className, label, lines) {
  const pane = element("div", `compare-pane ${className}`);
  pane.append(element("span", "compare-label", label), ...lines);
  return pane;
}

function unsavedLabel(count) {
  return `${count} unsaved ${count === 1 ? "change" : "changes"}`;
}

export function mount(root, params) {
  const { lang, itemId } = params;
  let mounted = true;
  // The Item as last read or saved, its field values, and the edit buffer
  let item = null;
  let loadedValues = null;
  let values = null;
  let busy = false;
  let error = null;
  let deleteError = null;
  let createdAnyway = null; // the Target Create anyway accepted, which skips the check
  let sheet = null;
  let previews = {}; // group key -> the Preview's values for that group's fields
  let regenerating = null; // the group key whose regeneration is in flight
  let regenError = null; // {group, error} of the last failed regeneration
  let currentInputs = null; // the rendered inputs, to keep focus across a re-render
  let audioCard = null; // the Reference audio card, built once per read

  const screen = element("div", "item-detail");
  const back = element("a", "back-link", `‹ ${languageName(lang)} Items`);
  back.href = `/${lang}/items`;
  const body = element("div", "item-detail-body");
  screen.append(back, body);
  root.replaceChildren(screen);

  function syncDirty() {
    const count = unsavedCount(values, loadedValues, previews, audioCard?.pending() ?? 0);
    setDirty(count ? { kind: "item", count, target: item.target } : null);
    return count;
  }

  function renderEditor({ focus = null } = {}) {
    // The focused field stays focused across a re-render, e.g. while a Preview arrives; it wins
    // over a regeneration's focus target, so typing is not interrupted
    let keepField = null;
    if (currentInputs) {
      const active = document.activeElement;
      keepField = Object.keys(currentInputs).find((key) => currentInputs[key] === active) ?? null;
      if (keepField) {
        const { selectionStart, selectionEnd } = active;
        keepField = { key: keepField, selectionStart, selectionEnd };
      }
    }

    const form = element("form", "draft-editor item-editor");
    form.setAttribute("aria-label", "Item");
    form.noValidate = true;

    const header = element("header", "item-detail-header");
    const title = element("h1", "item-detail-title", values.target);
    title.tabIndex = -1;
    const chip = element("span", "chip chip-accent item-detail-unsaved");
    header.append(
      title,
      element("span", "chip item-detail-category", categoryName(item.category)),
      chip,
    );

    const { fields, inputs } = editorFields(item.category, values, {
      busy,
      onChange: (key) => {
        if (key === "target") title.textContent = values.target;
        refresh();
      },
    });
    currentInputs = inputs;

    const regenerateButtons = [];
    const retryButtons = [];
    const focusTargets = {};
    for (const group of GROUPS) {
      if (!group.categories.includes(item.category)) continue;
      const built = regenerateSlot(group);
      regenerateButtons.push(built.button);
      if (built.retry) retryButtons.push(built.retry);
      focusTargets[group.key] = built;
      inputs[group.after].parentElement.after(built.slot);
    }

    const alertSlot = element("div", "draft-alert-slot");
    if (error) {
      const [alertTitle, alertBody] = saveFailure(error);
      alertSlot.append(
        alertBox(
          "draft-alert",
          element("p", "compose-alert-title", alertTitle),
          element("p", "draft-alert-body", alertBody),
        ),
      );
    }
    if (deleteError) {
      const unreachable = isApiError(deleteError, "anki_unavailable");
      alertSlot.append(
        alertBox(
          "item-delete-alert",
          element(
            "p", "compose-alert-title",
            unreachable ? "Not deleted — Anki isn't reachable" : "Not deleted",
          ),
          element(
            "p", "draft-alert-body",
            unreachable
              ? "Make sure Anki Desktop is open on the Mac mini, then try again."
              : errorMessage(deleteError),
          ),
        ),
      );
    }

    const actions = element("div", "draft-actions");
    const reason = element("p", "draft-reason");
    const save = element("button", "button button-primary", SAVE_CHANGES);
    save.type = "submit";
    const remove = element("button", "button-destructive-text", "Delete");
    remove.type = "button";
    remove.disabled = busy;
    remove.addEventListener("click", () => onDelete(remove));
    actions.append(remove, reason, save);

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!save.disabled) saveChanges();
    });
    form.append(header, fields, audioCard.card, alertSlot, actions);
    body.replaceChildren(form);
    audioCard.render();

    function refresh() {
      audioCard.refresh();
      const count = syncDirty();
      chip.textContent = count ? unsavedLabel(count) : "";
      chip.hidden = count === 0;
      const why = saveBlocker(values);
      reason.textContent = why ?? "";
      reason.hidden = why === null;
      save.disabled = why !== null || busy;
      const blocked = busy || regenerating !== null || !values.target.trim();
      for (const button of [...regenerateButtons, ...retryButtons]) {
        // The in-flight group's button stays focusable, marked busy and aria-disabled
        if (button.getAttribute("aria-busy") === "true") continue;
        button.disabled = blocked;
      }
    }

    refresh();
    if (focus === "title") title.focus();
    if (focus === "save") save.focus();
    if (focus === "delete") remove.focus();
    if (keepField && focus !== null && !focus.group) keepField = null;
    if (focus?.group && !keepField) {
      const target = focusTargets[focus.group]?.[focus.part];
      target?.focus();
    }
    if (keepField) {
      const input = inputs[keepField.key];
      input.focus();
      try {
        input.setSelectionRange(keepField.selectionStart, keepField.selectionEnd);
      } catch {
        // Not every input type keeps a selection
      }
    }
  }

  async function onDelete(trigger) {
    if (busy || !item) return;
    const content = document.createDocumentFragment();
    content.append(
      document.createTextNode(
        "This permanently removes the Item and its 4 Cards from Anki, with their review history:",
      ),
    );
    const cards = element("ul");
    for (const name of ["Understand", "Produce", "Write", "Pronounce"]) {
      cards.append(element("li", "", name));
    }
    content.append(cards, element("p", "", "There is no undo."));
    try {
      const deleted = await confirmDestructive({
        title: `Delete “${item.target}”?`,
        body: content,
        confirmLabel: "Delete permanently",
        trigger,
        action: async () => {
          busy = true;
          deleteError = null;
          renderEditor();
          await deleteItem(lang, itemId);
        },
      });
      if (!deleted) {
        // A regeneration may have replaced the original trigger while the dialog was open.
        if (mounted) body.querySelector(".button-destructive-text")?.focus();
        return;
      }
    } catch (failure) {
      if (!mounted) return;
      busy = false;
      deleteError = failure;
      renderEditor({ focus: "delete" });
      return;
    }
    if (!mounted) return;
    setDirty(null);
    navigate(`/${lang}/items`);
  }

  // A group's Regenerate button, then its loading state, failure alert or compare pair
  function regenerateSlot(group) {
    const slot = element("div", "regenerate-slot");
    const row = element("div", "regenerate-row");
    const button = element("button", "button-link", group.button);
    button.type = "button";
    if (regenerating === group.key) {
      button.setAttribute("aria-busy", "true");
      button.setAttribute("aria-disabled", "true");
    }
    button.addEventListener("click", () => regenerate(group));
    row.append(button);
    slot.append(row);
    const built = { slot, button, retry: null, heading: null };

    if (regenerating === group.key) {
      slot.append(skeleton(WRITING_PREVIEW));
    } else if (regenError?.group === group.key) {
      const [alertTitle, alertBody] = regenerationFailure(regenError.error);
      built.retry = tryAgain(() => regenerate(group));
      slot.append(
        alertBox(
          "regenerate-alert",
          element("p", "compose-alert-title", alertTitle),
          element("p", "draft-alert-body", alertBody),
          built.retry,
        ),
      );
    } else if (previews[group.key]) {
      const pair = element("section", "compare-pair");
      pair.setAttribute("role", "group");
      const heading = element("h2", "compare-title", `${group.name} · compare`);
      heading.id = `compare-${group.key}-${itemId}`;
      heading.tabIndex = -1;
      pair.setAttribute("aria-labelledby", heading.id);
      built.heading = heading;

      const panes = element("div", "compare-panes");
      panes.append(
        comparePane("compare-current", CURRENT, paneLines(group, values)),
        comparePane("compare-preview", PREVIEW_NOT_SAVED, paneLines(group, previews[group.key])),
      );

      const actions = element("div", "compare-actions");
      const keep = element("button", "button button-secondary", KEEP_CURRENT);
      keep.type = "button";
      keep.disabled = busy; // a choice made during a Save would be lost when it lands
      keep.addEventListener("click", () => keepCurrent(group));
      const use = element("button", "button button-soft", USE_PREVIEW);
      use.type = "button";
      use.disabled = busy;
      use.addEventListener("click", () => usePreview(group));
      actions.append(keep, use);

      pair.append(heading, panes, actions);
      slot.append(pair);
    }
    return built;
  }

  // Ask for the group's Preview with the buffer's Target; only one runs at a time
  async function regenerate(group) {
    if (busy || regenerating !== null || !values?.target.trim()) return;
    regenerating = group.key;
    if (regenError?.group === group.key) regenError = null;
    renderEditor({ focus: { group: group.key, part: "button" } });
    let reply;
    try {
      reply = await regenerateContent({
        language: lang,
        category: item.category,
        target: values.target,
      });
    } catch (failure) {
      if (!mounted) return;
      regenerating = null;
      regenError = { group: group.key, error: failure };
      delete previews[group.key];
      renderEditor({ focus: { group: group.key, part: "retry" } });
      return;
    }
    if (!mounted) return;
    regenerating = null;
    if (regenError?.group === group.key) regenError = null;
    const offered = generatedValues({ ...reply, category: item.category });
    previews[group.key] = Object.fromEntries(group.fields.map((key) => [key, offered[key]]));
    renderEditor({ focus: { group: group.key, part: "heading" } });
  }

  // Use preview: the group into the edit buffer, nothing written (NFR-4)
  function usePreview(group) {
    const preview = previews[group.key];
    if (!preview) return;
    Object.assign(values, preview);
    delete previews[group.key];
    renderEditor({ focus: { group: group.key, part: "button" } });
  }

  // Keep current: the Preview goes, the buffer stays
  function keepCurrent(group) {
    delete previews[group.key];
    renderEditor({ focus: { group: group.key, part: "button" } });
  }

  async function load() {
    body.replaceChildren(skeleton(LOADING));
    let read;
    try {
      read = await getItem(lang, itemId);
    } catch (failure) {
      if (!mounted) return;
      if (isApiError(failure, "not_found")) {
        body.replaceChildren(element("p", "item-detail-empty", NOT_IN_ANKI));
        return;
      }
      body.replaceChildren(
        alertBox(
          "item-detail-alert",
          element("p", "item-detail-alert-body", errorMessage(failure)),
          tryAgain(load),
        ),
      );
      return;
    }
    if (!mounted) return;
    item = read;
    loadedValues = generatedValues(read);
    values = { ...loadedValues };
    audioCard = itemAudioCard({
      language: lang,
      audioName: read.audio ?? null,
      target: read.target,
      values: () => values,
      busy: () => busy,
      changed: () => renderEditor(),
    });
    renderEditor();
  }

  // Save changes: the duplicate check first when the Target changed, then the Save
  async function saveChanges() {
    if (busy || !values) return;
    busy = true;
    error = null;
    renderEditor();
    const part = itemPart({ category: item.category, itemId: item.itemId, values });
    part.audio = audioCard.intent();
    const audioBlob = part.audio === "replace" ? audioCard.blob() : null;
    if (part.target !== item.target && part.target !== createdAnyway) {
      let matches;
      try {
        ({ matches } = await findDuplicates(lang, {
          category: item.category,
          target: part.target,
          itemId: item.itemId,
        }));
      } catch (failure) {
        if (!mounted) return;
        busy = false;
        error = failure;
        renderEditor({ focus: "save" });
        return;
      }
      if (!mounted) return;
      if (matches.length > 0) {
        busy = false;
        renderEditor();
        openSheet(matches);
        return;
      }
    }
    try {
      await saveItem(lang, part, audioBlob);
    } catch (failure) {
      if (!mounted) return;
      busy = false;
      error = failure;
      renderEditor({ focus: "save" });
      return;
    }
    if (!mounted) return;
    // The saved values are now the Item's: clean again
    const { audio: intent, ...saved } = part;
    item = saved;
    loadedValues = generatedValues(saved);
    values = { ...loadedValues };
    busy = false;
    createdAnyway = null;
    audioCard.saved(intent);
    renderEditor({ focus: "save" });
  }

  function openSheet(matches) {
    const built = duplicateSheet({ language: lang, category: item.category }, matches, {
      onOpen: (match) => openExisting(match),
      onCancel: () => {
        closeSheet();
        body.querySelector('button[type="submit"]')?.focus();
      },
      onCreate: () => {
        closeSheet();
        createdAnyway = values.target;
        saveChanges();
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

  // Open existing: the router asks about the edits (AD-13); Keep editing leaves the sheet open
  async function openExisting(match) {
    if (!(await confirmLeave())) return;
    if (!mounted) return;
    closeSheet();
    setDirty(null);
    navigate(`/${lang}/items/${encodeURIComponent(match.itemId)}`);
  }

  load();
  return () => {
    mounted = false;
    closeSheet();
    audioCard?.dispose();
    root.replaceChildren();
  };
}
