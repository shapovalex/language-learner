// The Make an Item pane and the Draft editor, built for the Captures screen (S-NewItem,
// S-CapturesDesk, C-Draft, S-DraftPhone; FR-11, FR-12, FR-18). Neither holds state of its own:
// the Captures screen keeps the pane's choices and the Draft in its memory (AD-13) and passes
// them in; these build the DOM and report the user's edits back.
//
// The pane picks the text (Use as is or Custom value), the Language and the Category, and
// "Write it myself" asks for a blank Draft; like Generate Draft (entry 2) it is disabled with a
// visible reason until those are chosen. The editor shows every field of the Category, editable,
// with the alternatives one per line, and Discard and Save to Anki (pinned to the bottom on the
// phone).

import { element } from "../dom.js";

const MAKE_AN_ITEM = "Make an Item";
const USE_AS_IS = "Use as is";
const CUSTOM_VALUE = "Custom value";
const CUSTOM_HINT = "Write it in the language you're learning, not in Russian.";
const WRITE_IT_MYSELF = "Write it myself";
const CHOOSE_REASON = "Choose a Language and Category.";
const CUSTOM_REASON = "Enter the custom value.";
const REQUIRED_REASON = "Enter the Target text and Russian meaning.";
const COMMA_REASON = "An alternative can't contain a comma. Put each one on its own line.";
const DRAFT_CHIP = "Draft — not saved yet";
const BACK = "‹ Capture";

export const LANGUAGES = [
  ["en", "English"],
  ["fr", "French"],
];
export const CATEGORIES = [
  ["vocabulary", "Vocabulary"],
  ["sentence", "Sentence"],
];

// Each Category's fields in order: [key, label, multiline, placeholder]. `alternatives` is the
// textarea of `russianAlternatives`, one per line (decided 2026-10-22)
const FIELDS = {
  vocabulary: [
    ["target", "Target", false],
    ["russian", "Russian meaning", false],
    ["alternatives", "Alternatives · optional · one per line", true],
    ["partOfSpeech", "Part of speech · optional", false],
    ["grammar", "Grammar · optional", false],
    ["hint", "Hint · optional", false, "Shown on Produce and Write"],
    ["example", "Example · optional", true],
    ["exampleRussian", "Example in Russian · optional", true],
    ["mnemonic", "Mnemonic · optional · only you write this", true],
  ],
  sentence: [
    ["target", "Target", false],
    ["russian", "Russian meaning", false],
    ["alternatives", "Alternatives · optional · one per line", true],
    ["hint", "Hint · optional", false, "Shown on Produce and Write"],
    ["note", "Note · optional", true],
  ],
};

let ids = 0;

function uniqueId(name) {
  ids += 1;
  return `${name}-${ids}`;
}

function nameOf(choices, key) {
  return choices.find(([value]) => value === key)?.[1] ?? "";
}

// A blank Draft's field values: Target prefilled with the chosen text, every other one empty
export function blankValues(category, target) {
  const values = Object.fromEntries(FIELDS[category].map(([key]) => [key, ""]));
  values.target = target;
  return values;
}

function alternativeLines(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

// The Save's `item` part (Consistency Conventions): ItemContent, the ItemId and `audio: "keep"`
export function itemPart(draft) {
  const item = { category: draft.category, itemId: draft.itemId, audio: "keep" };
  for (const [key] of FIELDS[draft.category]) {
    if (key === "alternatives") {
      item.russianAlternatives = alternativeLines(draft.values.alternatives);
    } else {
      item[key] = draft.values[key];
    }
  }
  return item;
}

// Why the Draft can't be saved yet, or null
function saveBlocker(values) {
  if (!values.target.trim() || !values.russian.trim()) return REQUIRED_REASON;
  if (alternativeLines(values.alternatives).some((line) => line.includes(","))) {
    return COMMA_REASON;
  }
  return null;
}

// The text Write it myself starts from, or null while Custom value is chosen and empty
export function chosenText(choice, captureText) {
  if (choice.source !== "custom") return captureText;
  return choice.custom.trim() || null;
}

function picker(label, choices, chosen, onChoose) {
  const group = element("div", "make-item-group");
  const labelId = uniqueId("make-item-label");
  const caption = element("p", "make-item-label", label);
  caption.id = labelId;
  const segments = element("div", "segmented-control");
  segments.setAttribute("role", "group");
  segments.setAttribute("aria-labelledby", labelId);
  const buttons = choices.map(([value, name]) => {
    const button = element("button", "segment", name);
    button.type = "button";
    button.dataset.value = value;
    button.addEventListener("click", () => onChoose(value));
    segments.append(button);
    return button;
  });
  group.append(caption, segments);
  const mark = (value) => {
    for (const button of buttons) {
      button.setAttribute("aria-pressed", String(button.dataset.value === value));
    }
  };
  mark(chosen);
  return [group, mark];
}

// The Make an Item pane. `choice` is {source, custom, language, category, busy, error}, which the
// pane changes in place as the user picks; `onWrite()` runs on "Write it myself"
export function makeItemPane(choice, { onWrite }) {
  const headingId = uniqueId("make-item-heading");
  const section = element("section", "make-item");
  section.setAttribute("aria-labelledby", headingId);
  const heading = element("h2", "make-item-heading", MAKE_AN_ITEM);
  heading.id = headingId;
  heading.tabIndex = -1; // focus lands here when the Draft editor closes

  const text = element("fieldset", "make-item-text");
  text.append(element("legend", "make-item-label", "Text"));
  const radioName = uniqueId("text-source");
  const radios = element("div", "make-item-radios");
  const custom = element("input", "compose-field make-item-custom");
  custom.type = "text";
  custom.setAttribute("aria-label", CUSTOM_VALUE);
  custom.value = choice.custom;
  const hintId = uniqueId("make-item-hint");
  custom.setAttribute("aria-describedby", hintId);
  for (const [value, name] of [
    ["capture", USE_AS_IS],
    ["custom", CUSTOM_VALUE],
  ]) {
    const option = element("label", "make-item-radio");
    const radio = element("input");
    radio.type = "radio";
    radio.name = radioName;
    radio.value = value;
    radio.checked = choice.source === value;
    radio.addEventListener("change", () => {
      choice.source = value;
      refresh();
      if (value === "custom") custom.focus();
    });
    option.append(radio, element("span", null, name));
    radios.append(option);
  }
  const hint = element("p", "make-item-hint", CUSTOM_HINT);
  hint.id = hintId;
  text.append(radios, custom, hint);
  custom.addEventListener("input", () => {
    choice.custom = custom.value;
    refresh();
  });

  const [languages, markLanguage] = picker("Language", LANGUAGES, choice.language, (value) => {
    choice.language = value;
    refresh();
  });
  const [categories, markCategory] = picker("Category", CATEGORIES, choice.category, (value) => {
    choice.category = value;
    refresh();
  });

  const actions = element("div", "make-item-actions");
  const write = element("button", "button-link", WRITE_IT_MYSELF);
  write.type = "button";
  const reason = element("p", "make-item-reason");
  write.addEventListener("click", onWrite);
  actions.append(write, reason);
  section.append(heading, text, languages, categories, actions);
  if (choice.error) {
    const alert = element("div", "inline-alert-error make-item-alert");
    alert.setAttribute("role", "alert");
    alert.textContent = choice.error;
    section.append(alert);
  }

  function refresh() {
    custom.disabled = choice.source !== "custom";
    markLanguage(choice.language);
    markCategory(choice.category);
    let why = null;
    if (!choice.language || !choice.category) {
      why = CHOOSE_REASON;
    } else if (choice.source === "custom" && !choice.custom.trim()) {
      why = CUSTOM_REASON;
    }
    reason.textContent = why ?? "";
    reason.hidden = why === null;
    write.disabled = why !== null || choice.busy;
  }

  refresh();
  return section;
}

// The Draft editor. `draft` is {captureId, captureText, language, category, itemId, values,
// busy, error}; edits go into `draft.values` and `onEdit()` runs after each. `onSave()` and
// `onDiscard()` run on Save to Anki and Discard; `alertFor(error)` gives a failed Save's
// [title, body]
export function draftEditor(draft, { onEdit, onSave, onDiscard, alertFor }) {
  const screen = element("div", "draft-screen");
  const back = element("a", "back-link draft-back", BACK);
  back.href = `/captures/${encodeURIComponent(draft.captureId)}`;

  const form = element("form", "draft-editor");
  form.setAttribute("aria-label", "Draft");
  form.noValidate = true;

  const header = element("header", "draft-header");
  const title = element("h1", "draft-title", draft.values.target);
  title.tabIndex = -1;
  const meta = element("p", "draft-meta");
  meta.append(
    element(
      "span",
      null,
      `${nameOf(LANGUAGES, draft.language)} ${nameOf(CATEGORIES, draft.category)}`,
    ),
    element("span", "chip chip-accent", DRAFT_CHIP),
  );
  header.append(
    element("p", "draft-source", `From Capture “${draft.captureText}”`),
    title,
    meta,
  );

  const fields = element("div", "draft-fields");
  for (const [key, label, multiline, placeholder] of FIELDS[draft.category]) {
    const id = uniqueId(`draft-${key}`);
    const wrap = element("div", "draft-field");
    const caption = element("label", "compose-label", label);
    caption.htmlFor = id;
    const input = element(multiline ? "textarea" : "input", "compose-field");
    if (multiline) {
      input.rows = key === "alternatives" ? 2 : 3;
    } else {
      input.type = "text";
    }
    input.id = id;
    input.value = draft.values[key];
    // An edit typed while the Save is in flight would never be sent
    input.readOnly = draft.busy;
    if (placeholder) input.placeholder = placeholder;
    input.addEventListener("input", () => {
      draft.values[key] = input.value;
      if (key === "target") title.textContent = input.value;
      refresh();
      onEdit();
    });
    wrap.append(caption, input);
    fields.append(wrap);
  }

  const alertSlot = element("div", "draft-alert-slot");
  if (draft.error) {
    const [alertTitle, body] = alertFor(draft.error);
    const alert = element("div", "inline-alert-error draft-alert");
    alert.setAttribute("role", "alert");
    alert.append(
      element("p", "compose-alert-title", alertTitle),
      element("p", "draft-alert-body", body),
    );
    alertSlot.append(alert);
  }

  const actions = element("div", "draft-actions");
  const reason = element("p", "draft-reason");
  const discard = element("button", "button button-secondary", "Discard");
  discard.type = "button";
  discard.addEventListener("click", onDiscard);
  const save = element("button", "button button-primary", "Save to Anki");
  save.type = "submit";
  actions.append(reason, discard, save);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!save.disabled) onSave();
  });
  form.append(header, fields, alertSlot, actions);
  screen.append(back, form);

  function refresh() {
    const why = saveBlocker(draft.values);
    reason.textContent = why ?? "";
    reason.hidden = why === null;
    save.disabled = why !== null || draft.busy;
    discard.disabled = draft.busy;
  }

  refresh();
  return { screen, title };
}
