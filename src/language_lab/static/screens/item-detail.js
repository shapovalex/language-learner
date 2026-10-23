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
// inline alert; Save changes again retries the same ItemId. Regeneration, Voice, audio and
// Delete are later stories'.

import { errorMessage, findDuplicates, getItem, isApiError, saveItem } from "../api.js";
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

function unsavedCount(values, loaded) {
  return Object.keys(loaded).filter((key) => values[key] !== loaded[key]).length;
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

  const screen = element("div", "item-detail");
  const back = element("a", "back-link", `‹ ${languageName(lang)} Items`);
  back.href = `/${lang}/items`;
  const body = element("div", "item-detail-body");
  screen.append(back, body);
  root.replaceChildren(screen);

  function syncDirty() {
    const count = unsavedCount(values, loadedValues);
    setDirty(count ? { kind: "item", count, target: item.target } : null);
    return count;
  }

  function renderEditor({ focus = null } = {}) {
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

    const { fields } = editorFields(item.category, values, {
      busy,
      onChange: (key) => {
        if (key === "target") title.textContent = values.target;
        refresh();
      },
    });

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
    }

    refresh();
    if (focus === "title") title.focus();
    if (focus === "save") save.focus();
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
