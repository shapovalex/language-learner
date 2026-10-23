// The Languages and Categories the screens name (domain/catalog.py), as [value, name] pairs.

export const LANGUAGES = [
  ["en", "English"],
  ["fr", "French"],
];
export const CATEGORIES = [
  ["vocabulary", "Vocabulary"],
  ["sentence", "Sentence"],
];

function nameOf(choices, key) {
  return choices.find(([value]) => value === key)?.[1] ?? "";
}

export function languageName(code) {
  return nameOf(LANGUAGES, code);
}

export function categoryName(key) {
  return nameOf(CATEGORIES, key);
}
