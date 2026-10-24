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
// the new Current. Voice, audio and Delete are later stories'.

import {
  errorMessage,
  findDuplicates,
  getItem,
  isApiError,
  regenerateContent,
  saveItem,
} from "../api.js";
import { categoryName, languageName } from "../catalog.js";
import { alertBox, element, skeleton, tryAgain } from "../dom.js";
import { confirmLeave, navigate, setDirty } from "../router.js";
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

// Changed fields, plus one per open Preview (EXPERIENCE.md "Unsaved … Preview")
function unsavedCount(values, loaded, previews) {
  const changed = Object.keys(loaded).filter((key) => values[key] !== loaded[key]).length;
  return changed + Object.keys(previews).length;
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
  let createdAnyway = null; // the Target Create anyway accepted, which skips the check
  let sheet = null;
  let previews = {}; // group key -> the Preview's values for that group's fields
  let regenerating = null; // the group key whose regeneration is in flight
  let regenError = null; // {group, error} of the last failed regeneration
  let currentInputs = null; // the rendered inputs, to keep focus across a re-render

  const screen = element("div", "item-detail");
  const back = element("a", "back-link", `‹ ${languageName(lang)} Items`);
  back.href = `/${lang}/items`;
  const body = element("div", "item-detail-body");
  screen.append(back, body);
  root.replaceChildren(screen);

  function syncDirty() {
    const count = unsavedCount(values, loadedValues, previews);
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

    const actions = element("div", "draft-actions");
    const reason = element("p", "draft-reason");
    const save = element("button", "button button-primary", SAVE_CHANGES);
    save.type = "submit";
    actions.append(reason, save);

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!save.disabled) saveChanges();
    });
    form.append(header, fields, alertSlot, actions);
    body.replaceChildren(form);

    function refresh() {
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
    renderEditor();
  }

  // Save changes: the duplicate check first when the Target changed, then the Save
  async function saveChanges() {
    if (busy || !values) return;
    busy = true;
    error = null;
    renderEditor();
    const part = itemPart({ category: item.category, itemId: item.itemId, values });
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
      await saveItem(lang, part);
    } catch (failure) {
      if (!mounted) return;
      busy = false;
      error = failure;
      renderEditor({ focus: "save" });
      return;
    }
    if (!mounted) return;
    // The saved values are now the Item's: clean again
    const { audio: _audio, ...saved } = part;
    item = saved;
    loadedValues = generatedValues(saved);
    values = { ...loadedValues };
    busy = false;
    createdAnyway = null;
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
    root.replaceChildren();
  };
}
