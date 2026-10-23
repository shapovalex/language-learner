// The Make an Item pane and the Draft editor, built for the Captures screen (S-NewItem,
// S-CapturesDesk, C-Draft, S-DraftPhone; FR-11, FR-12, FR-18). Neither holds state of its own:
// the Captures screen keeps the pane's choices and the Draft in its memory (AD-13) and passes
// them in; these build the DOM and report the user's edits back.
//
// The pane picks the text (Use as is or Custom value), the Language and the Category, and takes
// an optional Generation context. "Generate Draft" asks the model for a Draft and "Write it
// myself" for a blank one; both are disabled with a visible reason until those are chosen. The
// editor shows every field of the Category, editable, with the alternatives one per line, Clear
// on a Vocabulary example, and Discard and Save to Anki (pinned to the bottom on the phone).
// While the model writes, the generating screen shows the loading state, or the failure with
// Try again.

import { element, skeleton } from "../dom.js";

const MAKE_AN_ITEM = "Make an Item";
const USE_AS_IS = "Use as is";
const CUSTOM_VALUE = "Custom value";
const CUSTOM_HINT = "Write it in the language you're learning, not in Russian.";
const WRITE_IT_MYSELF = "Write it myself";
const GENERATE_DRAFT = "Generate Draft";
const GENERATION_CONTEXT = "Generation context · optional · used once, never saved";
const WRITING = "Writing your Draft…";
const TRY_AGAIN = "Try again";
const CLEAR = "Clear";
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

// A generated Draft's field values, from the ItemContent the model's Draft carries
export function generatedValues(content) {
  const values = blankValues(content.category, content.target);
  for (const [key] of FIELDS[content.category]) {
    if (key === "alternatives") {
      values.alternatives = (content.russianAlternatives ?? []).join("\n");
    } else if (key !== "target") {
      values[key] = content[key] ?? "";
    }
  }
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

// The Make an Item pane. `choice` is {source, custom, language, category, context, busy, error},
// which the pane changes in place as the user picks; `onGenerate()` runs on "Generate Draft" and
// `onWrite()` on "Write it myself"
export function makeItemPane(choice, { onGenerate, onWrite }) {
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

  // The Generation context is kept in `choice` only, and sent once with Generate Draft (AD-13)
  const contextGroup = element("div", "make-item-group");
  const contextId = uniqueId("make-item-context");
  const contextLabel = element("label", "make-item-label", GENERATION_CONTEXT);
  contextLabel.htmlFor = contextId;
  const context = element("textarea", "compose-field make-item-context");
  context.id = contextId;
  context.rows = 2;
  context.value = choice.context;
  context.addEventListener("input", () => {
    choice.context = context.value;
  });
  contextGroup.append(contextLabel, context);

  const actions = element("div", "make-item-actions");
  const generate = element("button", "button button-primary", GENERATE_DRAFT);
  generate.type = "button";
  generate.addEventListener("click", onGenerate);
  const write = element("button", "button-link", WRITE_IT_MYSELF);
  write.type = "button";
  const reason = element("p", "make-item-reason");
  write.addEventListener("click", onWrite);
  actions.append(generate, write, reason);
  section.append(heading, text, languages, categories, contextGroup, actions);
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
    generate.disabled = why !== null || choice.busy;
    write.disabled = why !== null || choice.busy;
  }

  refresh();
  return section;
}

function backLink(draft, className) {
  const back = element("a", `back-link ${className}`, BACK);
  back.href = `/captures/${encodeURIComponent(draft.captureId)}`;
  return back;
}

// The Draft's header: its Capture, `target` as the title, and the Language and Category, with
// the "not saved yet" chip once there is a Draft to save
function draftHeader(draft, target, { chip }) {
  const header = element("header", "draft-header");
  const title = element("h1", "draft-title", target);
  title.tabIndex = -1;
  const meta = element("p", "draft-meta");
  meta.append(
    element(
      "span",
      null,
      `${nameOf(LANGUAGES, draft.language)} ${nameOf(CATEGORIES, draft.category)}`,
    ),
  );
  if (chip) meta.append(element("span", "chip chip-accent", DRAFT_CHIP));
  header.append(
    element("p", "draft-source", `From Capture “${draft.captureText}”`),
    title,
    meta,
  );
  return { header, title };
}

// The generated Draft before it has values. `draft.generation` is {request, busy, error}: the
// skeleton while `busy`, else the failure's alert (`alertFor(error)` gives [title, body]) with
// Try again, which runs `onRetry()`. The back link shows at every width: there is no Discard yet
export function generatingScreen(draft, { onRetry, alertFor }) {
  const screen = element("div", "draft-screen");
  const { header, title } = draftHeader(draft, draft.generation.request.target, { chip: false });
  const body = element("div", "draft-generating");
  let again = null;
  if (draft.generation.busy) {
    body.append(skeleton(WRITING));
  } else {
    const [alertTitle, alertBody] = alertFor(draft.generation.error);
    const alert = element("div", "inline-alert-error draft-alert");
    alert.setAttribute("role", "alert");
    again = element("button", "button button-secondary", TRY_AGAIN);
    again.type = "button";
    again.addEventListener("click", onRetry);
    alert.append(
      element("p", "compose-alert-title", alertTitle),
      element("p", "draft-alert-body", alertBody),
      again,
    );
    body.append(alert);
  }
  screen.append(backLink(draft, "draft-generating-back"), header, body);
  return { screen, title, retry: again };
}

// The Draft editor. `draft` is {captureId, captureText, language, category, itemId, values,
// busy, error}; edits go into `draft.values` and `onEdit()` runs after each. `onSave()` and
// `onDiscard()` run on Save to Anki and Discard; `alertFor(error)` gives a failed Save's
// [title, body]
export function draftEditor(draft, { onEdit, onSave, onDiscard, alertFor }) {
  const screen = element("div", "draft-screen");
  const back = backLink(draft, "draft-back");

  const form = element("form", "draft-editor");
  form.setAttribute("aria-label", "Draft");
  form.noValidate = true;

  const { header, title } = draftHeader(draft, draft.values.target, { chip: true });

  const fields = element("div", "draft-fields");
  const inputs = {};
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
    inputs[key] = input;
    if (key === "example") {
      // Clear removes the example and its translation together (FR-14)
      const row = element("div", "draft-field-row");
      const clear = element("button", "button-link", CLEAR);
      clear.type = "button";
      clear.disabled = draft.busy;
      clear.addEventListener("click", () => {
        for (const cleared of ["example", "exampleRussian"]) {
          draft.values[cleared] = "";
          inputs[cleared].value = "";
        }
        refresh();
        onEdit();
        inputs.example.focus();
      });
      row.append(caption, clear);
      wrap.append(row, input);
    } else {
      wrap.append(caption, input);
    }
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
