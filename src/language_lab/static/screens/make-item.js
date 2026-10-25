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
// Try again. Before a Save, a duplicate opens the duplicate sheet (S-Duplicate, story 4.3).

import { CATEGORIES, LANGUAGES, categoryName, languageName } from "../catalog.js";
import { errorMessage, isApiError } from "../api.js";
import { alertBox, element, skeleton, tryAgain } from "../dom.js";
import {
  loadVoices as loadVoiceList,
  releasePlayer,
  requestPreview,
  voicePicker,
} from "../reference-audio.js";

const MAKE_AN_ITEM = "Make an Item";
const USE_AS_IS = "Use as is";
const CUSTOM_VALUE = "Custom value";
const CUSTOM_HINT = "Write it in the language you're learning, not in Russian.";
const WRITE_IT_MYSELF = "Write it myself";
const GENERATE_DRAFT = "Generate Draft";
const GENERATION_CONTEXT = "Generation context · optional · used once, never saved";
const WRITING = "Writing your Draft…";
const CLEAR = "Clear";
const CHOOSE_REASON = "Choose a Language and Category.";
const CUSTOM_REASON = "Enter the custom value.";
const REQUIRED_REASON = "Enter the Target text and Russian meaning.";
const COMMA_REASON = "An alternative can't contain a comma. Put each one on its own line.";
const DRAFT_CHIP = "Draft — not saved yet";
const DUPLICATE_TITLE = "You already have an Item with this text";
const DUPLICATE_BODY = "Nothing has been saved yet. You can still create a second Item.";
const OPEN_EXISTING = "Open existing";
const CANCEL = "Cancel";
const CREATE_ANYWAY = "Create anyway";
const BACK = "‹ Capture";
const UNREACHABLE_TITLE = "Not saved — Anki isn't reachable";
const MAKING_AUDIO = "Making audio…";
const AUTO_ERROR = "Couldn't make the audio. The Draft will save without audio.";
const UNREACHABLE_BODY =
  "Make sure Anki Desktop is open on the Mac mini, then try again. Your text is still here.";

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

// [title, body] of a failed Save, of a Capture, a Draft or an Item (EXPERIENCE.md State Patterns)
export function saveFailure(error) {
  if (isApiError(error, "anki_unavailable")) return [UNREACHABLE_TITLE, UNREACHABLE_BODY];
  return ["Not saved", errorMessage(error)];
}

// The Save's `item` part (Consistency Conventions): ItemContent, the ItemId and the Draft's
// audio intent; Item detail overrides `audio` with its own card's intent
export function itemPart(draft) {
  const item = { category: draft.category, itemId: draft.itemId, audio: draft.audio?.accepted ? "replace" : "keep" };
  for (const [key] of FIELDS[draft.category]) {
    if (key === "alternatives") {
      item.russianAlternatives = alternativeLines(draft.values.alternatives);
    } else {
      item[key] = draft.values[key];
    }
  }
  return item;
}

// Why the Draft or Item can't be saved yet, or null
export function saveBlocker(values) {
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
    section.append(alertBox("make-item-alert", choice.error));
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
    element("span", null, `${languageName(draft.language)} ${categoryName(draft.category)}`),
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
    again = tryAgain(onRetry, "secondary");
    body.append(
      alertBox(
        "draft-alert",
        element("p", "compose-alert-title", alertTitle),
        element("p", "draft-alert-body", alertBody),
        again,
      ),
    );
  }
  screen.append(backLink(draft, "draft-generating-back"), header, body);
  return { screen, title, retry: again };
}

// The editable fields of a Category, shared by the Draft editor and Item detail: one labelled
// input per field in `FIELDS` order, the alternatives one per line, and Clear on a Vocabulary
// example. Edits go into `values`, then `onChange(key)` runs; while `busy` nothing is editable,
// since an edit typed while the Save is in flight would never be sent
export function editorFields(category, values, { busy, onChange }) {
  const fields = element("div", "draft-fields");
  const inputs = {};
  for (const [key, label, multiline, placeholder] of FIELDS[category]) {
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
    input.value = values[key];
    input.readOnly = busy;
    if (placeholder) input.placeholder = placeholder;
    input.addEventListener("input", () => {
      values[key] = input.value;
      onChange(key);
    });
    inputs[key] = input;
    if (key === "example") {
      // Clear removes the example and its translation together (FR-14)
      const row = element("div", "draft-field-row");
      const clear = element("button", "button-link", CLEAR);
      clear.type = "button";
      clear.disabled = busy;
      clear.addEventListener("click", () => {
        for (const cleared of ["example", "exampleRussian"]) {
          values[cleared] = "";
          inputs[cleared].value = "";
        }
        onChange("example");
        inputs.example.focus();
      });
      row.append(caption, clear);
      wrap.append(row, input);
    } else {
      wrap.append(caption, input);
    }
    fields.append(wrap);
  }
  return { fields, inputs };
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

  const { fields } = editorFields(draft.category, draft.values, {
    busy: draft.busy,
    onChange: (key) => {
      if (key === "target") title.textContent = draft.values.target;
      refresh();
      audio.refresh();
      onEdit();
    },
  });

  const audio = referenceAudio(draft);
  const alertSlot = element("div", "draft-alert-slot");
  if (draft.error) {
    const [alertTitle, body] = alertFor(draft.error);
    alertSlot.append(
      alertBox(
        "draft-alert",
        element("p", "compose-alert-title", alertTitle),
        element("p", "draft-alert-body", body),
      ),
    );
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
  form.append(header, fields, audio.card, alertSlot, actions);
  screen.append(back, form);

  function refresh() {
    const why = saveBlocker(draft.values);
    reason.textContent = why ?? "";
    reason.hidden = why === null;
    save.disabled = why !== null || draft.busy;
    // A Save pressed while the automatic audio is made waits for it (captures.js saveDraft)
    save.textContent = draft.busy && draft.audio?.autoPending ? MAKING_AUDIO : "Save to Anki";
    discard.disabled = draft.busy;
  }

  refresh();
  return { screen, title };
}

// The duplicate sheet (S-Duplicate; FR-19): a native modal <dialog>, a bottom sheet on the phone
// and centered from tablet width up, naming the Draft's Language and Category and listing each
// match. Open existing (the Primary, focused first) runs `onOpen(match)` with the first match;
// Cancel, Esc and a tap on the backdrop run `onCancel()`; Create anyway runs `onCreate()`.
// The caller shows it with `showModal()` and removes it.
export function duplicateSheet(draft, matches, { onOpen, onCancel, onCreate }) {
  const dialog = element("dialog", "duplicate-sheet");
  const titleId = uniqueId("duplicate-title");
  dialog.setAttribute("aria-labelledby", titleId);
  const sheet = element("div", "duplicate-sheet-body");

  const language = languageName(draft.language);
  const category = categoryName(draft.category);
  const overline = element("p", "duplicate-overline", `Possible duplicate · ${language} · ${category}`);
  const title = element("h2", "duplicate-title", DUPLICATE_TITLE);
  title.id = titleId;

  const list = element("ul", "duplicate-matches");
  for (const match of matches) {
    const card = element("li", "duplicate-match");
    card.append(
      element("p", "duplicate-match-target", match.target),
      element("p", "duplicate-match-russian", match.russian),
    );
    list.append(card);
  }

  const actions = element("div", "duplicate-actions");
  const open = element("button", "button button-primary", OPEN_EXISTING);
  open.type = "button";
  open.addEventListener("click", () => onOpen(matches[0]));
  const cancel = element("button", "button button-secondary", CANCEL);
  cancel.type = "button";
  cancel.addEventListener("click", onCancel);
  const create = element("button", "button-link duplicate-create", CREATE_ANYWAY);
  create.type = "button";
  create.addEventListener("click", onCreate);
  actions.append(open, cancel, create);

  sheet.append(
    overline,
    title,
    list,
    element("p", "duplicate-body", DUPLICATE_BODY),
    actions,
  );
  dialog.append(sheet);
  // Tab and Shift+Tab stay on the sheet's buttons: a modal <dialog> alone lets Tab reach the
  // browser's own controls (EXPERIENCE.md Bottom sheet: focus trapped)
  const buttons = [open, cancel, create];
  dialog.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    event.preventDefault();
    const step = event.shiftKey ? -1 : 1;
    const index = buttons.indexOf(document.activeElement);
    const next = index === -1 ? 0 : (index + step + buttons.length) % buttons.length;
    buttons[next].focus();
  });
  // Esc is Cancel
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    onCancel();
  });
  // The body fills the dialog, so a click on the dialog itself is on the backdrop
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) onCancel();
  });
  return { dialog, primary: open };
}


// URLs belong to the Draft, independent of DOM rerenders after a failed Save.
export function disposeDraftAudio(draft) {
  const state = draft?.audio;
  if (!state) return;
  state.disposed = true;
  state.render = null;
  for (const player of state.players) releasePlayer(player);
  state.players.clear();
  for (const clip of [state.accepted, state.offered]) {
    if (clip) URL.revokeObjectURL(clip.url);
  }
  state.accepted = state.offered = null;
}

function referenceAudio(draft) {
  const language = draft.language;
  const first = !draft.audio;
  const state = draft.audio ??= {
    voices: [], voice: null, loading: true, voiceError: false,
    previewing: false, previewError: false, sequence: 0,
    accepted: null, offered: null, disposed: false, render: null, players: new Set(),
    // The one automatic Preview (AD-14): `autoDone` once the Voices first load, `autoError`
    // when it (or its Try again) failed, `autoPending` the promise of the first Voice load and
    // the automatic Preview (or of its Try again) while in flight
    autoDone: false, autoError: false, autoPending: null,
  };
  const card = element("section", "reference-audio");
  card.setAttribute("aria-label", "Reference audio");
  const heading = element("h2", "make-item-heading", "Reference audio · optional");
  const body = element("div", "reference-audio-body");
  card.append(heading, body);

  function button(label, action, className = "button button-secondary") {
    const node = element("button", className, label);
    node.type = "button";
    node.disabled = draft.busy;
    node.addEventListener("click", action);
    return node;
  }

  function player(clip, label) {
    const wrap = element("div", "reference-audio-clip");
    const audio = element("audio");
    state.players.add(audio);
    audio.src = clip.url;
    audio.controls = true;
    audio.preload = "none";
    audio.setAttribute("aria-label", label);
    wrap.append(audio, button(label, () => { audio.play().catch(() => {}); }, "button-link"));
    if (clip.target !== draft.values.target) {
      wrap.append(element("p", "reference-audio-stale", "Audio no longer matches the text."));
    }
    return wrap;
  }

  function render() {
    if (state.disposed) return;
    for (const player of state.players) player.pause();
    state.players.clear();
    body.replaceChildren();
    const locked = state.loading || !state.voices.length || draft.busy || state.previewing;
    body.append(...voicePicker(state, language, loadVoices, locked));
    const previewButton = button(state.previewing ? MAKING_AUDIO : "Preview", preview);
    previewButton.disabled = draft.busy || state.previewing || state.loading || !state.voice || !draft.values.target.trim();
    body.append(previewButton);
    if (state.accepted) body.append(player(state.accepted, state.offered ? "Play current audio" : "Play audio preview"));
    if (state.offered) {
      body.append(player(state.offered, "Play audio preview"));
      const compare = element("div", "reference-audio-actions");
      compare.append(
        button("Keep current", () => {
          URL.revokeObjectURL(state.offered.url);
          state.offered = null;
          state.render();
        }),
        button("Use preview", () => {
          if (state.accepted) URL.revokeObjectURL(state.accepted.url);
          state.accepted = state.offered;
          state.offered = null;
          state.render();
        }, "button button-primary"),
      );
      body.append(compare);
    }
    if (state.previewError) {
      body.append(alertBox("reference-audio-error", "Couldn't make the audio. Current audio is unchanged.", tryAgain(preview)));
    } else if (state.autoError) {
      const again = tryAgain(() => { if (!state.autoPending) track(synthesize()); });
      again.disabled = draft.busy || state.previewing || !state.voice || !draft.values.target.trim();
      body.append(alertBox("reference-audio-error", AUTO_ERROR, again));
    }
  }

  // state.render, not render: a rerendered card replaces it, and the reply updates the new one
  // Once the Voices first load, the Draft's audio is made automatically (AD-14). A Save
  // waits on `autoPending` from the start of that Voice load to the end of the Preview
  function loadVoices() {
    if (state.autoDone) return loadVoiceList(state, language, () => state.render());
    return track((async () => {
      await loadVoiceList(state, language, () => state.render());
      if (state.disposed || state.voiceError) return;
      state.autoDone = true;
      await synthesize();
    })());
  }

  // `work` is what a Save waits for, until it settles
  function track(work) {
    const pending = work.finally(() => {
      if (state.autoPending === pending) state.autoPending = null;
    });
    state.autoPending = pending;
    return pending;
  }

  // The automatic Preview, or its Try again: the clip becomes the accepted audio, so Save
  // stores it. It runs even while a Save waits for it (`draft.busy`); it never autoplays
  async function synthesize() {
    if (!state.voice || !draft.values.target.trim()) return;
    const target = draft.values.target;
    state.previewing = true;
    state.autoError = false;
    state.render();
    try {
      const blob = await requestPreview(state, { language: draft.language, voice: state.voice, target });
      if (blob) {
        if (state.accepted) URL.revokeObjectURL(state.accepted.url);
        state.accepted = { blob, target, url: URL.createObjectURL(blob) };
      }
    } catch {
      state.autoError = true;
    }
    state.previewing = false;
    state.render?.();
  }

  async function preview() {
    if (state.previewing || !state.voice || !draft.values.target.trim() || draft.busy) return;
    const target = draft.values.target;
    const voice = state.voice;
    state.previewing = true;
    state.previewError = false;
    state.autoError = false;
    state.render();
    try {
      const blob = await requestPreview(state, { language: draft.language, voice, target });
      if (!blob) return;
      if (state.offered) URL.revokeObjectURL(state.offered.url);
      state.offered = { blob, target, url: URL.createObjectURL(blob) };
    } catch {
      state.previewError = true;
    }
    state.previewing = false;
    state.render();
  }

  state.render = render;
  render();
  if (first) loadVoices();
  return { card, refresh: render };
}
