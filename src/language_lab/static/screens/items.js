// A Language's Items screen (AD-13). params.lang is "en" or "fr".

const LANGUAGE_NAMES = { en: "English", fr: "French" };

export function mount(root, params) {
  const heading = document.createElement("h1");
  heading.textContent = `${LANGUAGE_NAMES[params.lang]} Items`;
  root.replaceChildren(heading);
  return () => root.replaceChildren();
}
