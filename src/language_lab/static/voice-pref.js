// The sole localStorage owner. Only explicit choices are persisted (AD-13): the Voice, one key
// per Language, `languagelab.voice.en-US` and `languagelab.voice.fr` (an unset French key falls
// back to the `fr-CA` key it replaced, so an earlier Canada choice survives), and the Captures
// screen's Language for Capture and translate, `languagelab.captureLanguage`.
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

const CAPTURE_LANGUAGE_KEY = "languagelab.captureLanguage";
const CAPTURE_LANGUAGES = ["en", "fr"];
const DEFAULT_CAPTURE_LANGUAGE = "en";

// The Language captured text is in: the stored choice, or English when none, unknown or blocked
export function readCaptureLanguage() {
  try {
    const stored = localStorage.getItem(CAPTURE_LANGUAGE_KEY);
    return CAPTURE_LANGUAGES.includes(stored) ? stored : DEFAULT_CAPTURE_LANGUAGE;
  } catch {
    return DEFAULT_CAPTURE_LANGUAGE;
  }
}

export function writeCaptureLanguage(language) {
  try {
    localStorage.setItem(CAPTURE_LANGUAGE_KEY, language);
  } catch {
    // A denied or full storage keeps the choice for this screen only.
  }
}
