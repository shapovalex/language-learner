// The sole localStorage owner. Only explicit Voice selections are persisted (AD-13): one key
// per Language, `languagelab.voice.en-US` and `languagelab.voice.fr`. An unset French key
// falls back to the `fr-CA` key it replaced, so an earlier Canada choice survives.
const KEYS = { en: "languagelab.voice.en-US", fr: "languagelab.voice.fr" };
const LEGACY = { fr: "languagelab.voice.fr-CA" };

export function readVoice(language) {
  try {
    const stored = localStorage.getItem(KEYS[language]);
    return stored ?? (LEGACY[language] ? localStorage.getItem(LEGACY[language]) : null);
  } catch {
    return null;
  }
}

export function writeVoice(language, voice) {
  try {
    localStorage.setItem(KEYS[language], voice);
  } catch {
    // A denied or full storage leaves the current screen usable.
  }
}
