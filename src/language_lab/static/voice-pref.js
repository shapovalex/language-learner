// The sole localStorage owner. Only explicit Voice selections are persisted (AD-13).
export function readVoice(locale) {
  try {
    return localStorage.getItem(`languagelab.voice.${locale}`);
  } catch {
    return null;
  }
}

export function writeVoice(locale, voice) {
  try {
    localStorage.setItem(`languagelab.voice.${locale}`, voice);
  } catch {
    // A denied or full storage leaves the current screen usable.
  }
}
