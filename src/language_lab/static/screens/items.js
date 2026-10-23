// A Language's Items screen (AD-13). params.lang is "en" or "fr".

import { languageName } from "../catalog.js";

export function mount(root, params) {
  const heading = document.createElement("h1");
  heading.textContent = `${languageName(params.lang)} Items`;
  root.replaceChildren(heading);
  return () => root.replaceChildren();
}
