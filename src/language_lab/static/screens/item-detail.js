// Item detail, view-only (S-ItemDetail, story 4.3; FR-22). params are { lang, itemId }.
// Open existing on the duplicate sheet opens it. Every mount reads the Item from Anki (AD-13),
// so a value edited in Anki shows the next time. It shows the Target as its heading, the
// Category and each filled field; editing, regeneration and delete are epic-maintain-items'.

import { errorMessage, getItem, isApiError } from "../api.js";
import { categoryName, languageName } from "../catalog.js";
import { alertBox, element, skeleton, tryAgain } from "../dom.js";

const LOADING = "Loading Item…";
const NOT_IN_ANKI = "This Item isn't in Anki.";

// Each Category's fields after the Target, in the Draft editor's order and labels
const FIELDS = {
  vocabulary: [
    ["russian", "Russian meaning"],
    ["russianAlternatives", "Alternatives"],
    ["partOfSpeech", "Part of speech"],
    ["grammar", "Grammar"],
    ["hint", "Hint"],
    ["example", "Example"],
    ["exampleRussian", "Example in Russian"],
    ["mnemonic", "Mnemonic"],
  ],
  sentence: [
    ["russian", "Russian meaning"],
    ["russianAlternatives", "Alternatives"],
    ["hint", "Hint"],
    ["note", "Note"],
  ],
};

function details(item) {
  const list = element("dl", "item-detail-fields");
  for (const [key, label] of FIELDS[item.category] ?? []) {
    const value = key === "russianAlternatives" ? (item[key] ?? []).join(", ") : item[key];
    if (!value) continue;
    list.append(element("dt", "item-detail-label", label), element("dd", "item-detail-value", value));
  }
  return list;
}

export function mount(root, params) {
  let mounted = true;
  const screen = element("div", "item-detail");
  const back = element("a", "back-link", `‹ ${languageName(params.lang)} Items`);
  back.href = `/${params.lang}/items`;
  const body = element("div", "item-detail-body");
  screen.append(back, body);
  root.replaceChildren(screen);

  async function load() {
    body.replaceChildren(skeleton(LOADING));
    let item;
    try {
      item = await getItem(params.lang, params.itemId);
    } catch (error) {
      if (!mounted) return;
      if (isApiError(error, "not_found")) {
        body.replaceChildren(element("p", "item-detail-empty", NOT_IN_ANKI));
        return;
      }
      body.replaceChildren(
        alertBox(
          "item-detail-alert",
          element("p", "item-detail-alert-body", errorMessage(error)),
          tryAgain(load),
        ),
      );
      return;
    }
    if (!mounted) return;
    const header = element("div", "item-detail-header");
    header.append(
      element("h1", "item-detail-title", item.target),
      element("span", "chip item-detail-category", categoryName(item.category)),
    );
    body.replaceChildren(header, details(item));
  }

  load();
  return () => {
    mounted = false;
    root.replaceChildren();
  };
}
