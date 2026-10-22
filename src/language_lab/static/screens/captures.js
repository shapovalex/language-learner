// Captures screen (AD-13). The compose box saves a Capture with POST /api/captures (FR-9). The
// CaptureId is made in the browser once per composition and kept across retries, so a retried
// Save never makes a second Capture (AD-8, AD-20). Unsaved text marks the screen dirty through
// the router. Listing Captures is a later entry's.

import { createCapture } from "../api.js";
import { setDirty } from "../router.js";

const LABEL = "New Capture";
const PLACEHOLDER = "Paste or type a word, phrase or sentence";
const UNREACHABLE_TITLE = "Not saved — Anki isn't reachable";
const UNREACHABLE_BODY =
  "Make sure Anki Desktop is open on the Mac mini, then try again. Your text is still here.";
const NETWORK_FALLBACK = "LanguageLab could not reach the server.";

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function failureCopy(error) {
  if (error?.name === "ApiError" && error.code === "anki_unavailable") {
    return [UNREACHABLE_TITLE, UNREACHABLE_BODY];
  }
  // An ApiError carries the envelope's fixed message (AD-15)
  return ["Not saved", error?.name === "ApiError" ? error.message : NETWORK_FALLBACK];
}

export function mount(root) {
  let mounted = true;
  const state = { captureId: crypto.randomUUID(), busy: false, error: null };

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
  root.replaceChildren(heading, card);

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
      await createCapture(state.captureId, text);
      if (!mounted) return;
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

  return () => {
    mounted = false;
    root.replaceChildren();
  };
}
