// Reference audio pieces shared by the Draft card (make-item.js, story 6.1) and the Item card
// (item-detail.js, story 6.2). Each card keeps its own state and rendering; `state` here is the
// card's object, read and written for: voices, voice, loading, voiceError, sequence, disposed.
// Requests go through api.js and the stored Voice through voice-pref.js.

import { getVoices, previewAudio } from "./api.js";
import { alertBox, element, tryAgain } from "./dom.js";
import { readVoice, writeVoice } from "./voice-pref.js";

// The Voice locale of a Language (domain/catalog.py LOCALES)
export function audioLocale(language) {
  return language === "fr" ? "fr-CA" : "en-US";
}

// The Voice to show: the current choice, else the stored one, if listed; else the first
export function chooseVoice(voices, current, locale) {
  const preferred = current ?? readVoice(locale);
  return voices.some((voice) => voice.name === preferred) ? preferred : voices[0]?.name ?? null;
}

// The Voice <select> and its loading, error (with `retry` as Try again) and empty hints, as the
// nodes to append. A change only stores the choice; it never synthesizes or writes Anki.
export function voicePicker(state, locale, retry, disabled = false) {
  const label = element("label", "draft-label", "Voice");
  const select = element("select", "compose-field reference-audio-voice");
  select.setAttribute("aria-label", "Voice");
  select.disabled = disabled;
  for (const voice of state.voices) {
    const option = element("option", null, voice.displayName);
    option.value = voice.name;
    select.append(option);
  }
  select.value = state.voice ?? "";
  select.addEventListener("change", () => {
    state.voice = select.value;
    writeVoice(locale, state.voice);
  });
  label.append(select);
  const nodes = [label];
  if (state.loading) nodes.push(element("p", "make-item-hint", "Loading voices…"));
  if (state.voiceError) {
    nodes.push(alertBox("reference-audio-error", "Couldn't load voices", tryAgain(retry)));
  } else if (!state.loading && !state.voices.length) {
    nodes.push(element("p", "make-item-hint", "No voices available for this language."));
  }
  return nodes;
}

// Load the locale's Voices into `state`, rendering before and after; nothing after dispose
export async function loadVoices(state, locale, render) {
  state.loading = true;
  state.voiceError = false;
  render();
  try {
    const { voices } = await getVoices(locale);
    if (state.disposed) return;
    state.voices = voices;
    state.voice = chooseVoice(voices, state.voice, locale);
  } catch {
    if (state.disposed) return;
    state.voiceError = true;
  }
  state.loading = false;
  render();
}

// One Preview request: the Blob, or null when a later request or dispose superseded it (a late
// reply, failed or not, is ignored). Throws when the current request fails.
export async function requestPreview(state, body) {
  const sequence = ++state.sequence;
  const current = () => !state.disposed && state.sequence === sequence;
  try {
    const blob = await previewAudio(body);
    return current() ? blob : null;
  } catch (error) {
    if (current()) throw error;
    return null;
  }
}

// Stop a player and let go of its source
export function releasePlayer(audio) {
  audio.pause();
  audio.removeAttribute("src");
  audio.load();
}
