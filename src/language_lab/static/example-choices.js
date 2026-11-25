// The "Regenerate example" choices panel, shared by Item detail and the Vocabulary Draft editor
// (plans regenerate-example-choices, item-example-and-capture-improvements). A DOM builder, not
// a component: the caller owns the state, re-renders, keeps focus and sends the request. The
// panel shows the current Example (the caller's `current` node), an optional context (used once,
// never saved) and Generate, then the loading state, the failure with Try again, or the ten
// sentence/Russian pairs each with "Use this example", and Keep current to close it.

import { alertBox, element, skeleton, tryAgain } from "./dom.js";

const EXAMPLE_CONTEXT = "Context · optional · used once, never saved";
const GENERATE = "Generate";
const WRITING_CHOICES = "Writing 10 examples…";
const USE_THIS_EXAMPLE = "Use this example";
const KEEP_CURRENT = "Keep current";

// The panel for `choices` ({context, busy, error, result}); typing writes `choices.context`.
// `title` names the group ("Example · choose"), `headingId` and `contextId` are its element
// ids, `current` the node showing the current Example, `failure(error)` a failed request's
// [title, body], and `locked` whether a Save runs (a choice made then would be lost when it
// lands). `onGenerate()` runs on Generate and Try again, `onUse(sentence, russian)` on a pair's
// Use this example, `onKeep()` on Keep current. Returns the panel and its focus targets:
// {panel, heading, context, generate, retry}
export function exampleChoicesPanel(choices, {
  title, headingId, contextId, current, failure, locked, onGenerate, onUse, onKeep,
}) {
  const panel = element("section", "compare-pair example-choices");
  panel.setAttribute("role", "group");
  const heading = element("h2", "compare-title", title);
  heading.id = headingId;
  heading.tabIndex = -1;
  panel.setAttribute("aria-labelledby", heading.id);

  const contextGroup = element("div", "make-item-group");
  const contextLabel = element("label", "make-item-label", EXAMPLE_CONTEXT);
  contextLabel.htmlFor = contextId;
  const context = element("textarea", "compose-field make-item-context");
  context.id = contextId;
  context.rows = 2;
  context.value = choices.context;
  context.addEventListener("input", () => {
    choices.context = context.value;
  });
  contextGroup.append(contextLabel, context);

  const actions = element("div", "make-item-actions");
  const generate = element("button", "button button-primary", GENERATE);
  generate.type = "button";
  if (choices.busy) {
    generate.setAttribute("aria-busy", "true");
    generate.setAttribute("aria-disabled", "true");
  }
  generate.addEventListener("click", () => onGenerate());
  actions.append(generate);

  panel.append(heading, current, contextGroup, actions);

  let retry = null;
  if (choices.busy) {
    panel.append(skeleton(WRITING_CHOICES));
  } else if (choices.error) {
    const [alertTitle, alertBody] = failure(choices.error);
    retry = tryAgain(() => onGenerate());
    panel.append(
      alertBox(
        "regenerate-alert",
        element("p", "compose-alert-title", alertTitle),
        element("p", "draft-alert-body", alertBody),
        retry,
      ),
    );
  } else if (choices.result) {
    const list = element("ul", "examples-list");
    list.setAttribute("aria-label", "New examples");
    for (const { sentence, russian } of choices.result.sentences) {
      const li = element("li", "examples-item");
      const words = element("div", "examples-item-body");
      words.append(
        element("p", "examples-sentence", sentence),
        element("p", "examples-russian", russian),
      );
      const use = element("button", "button-link examples-make", USE_THIS_EXAMPLE);
      use.type = "button";
      use.disabled = locked;
      use.addEventListener("click", () => onUse(sentence, russian));
      li.append(words, use);
      list.append(li);
    }
    panel.append(list);
  }

  const closing = element("div", "compare-actions");
  const keep = element("button", "button button-secondary", KEEP_CURRENT);
  keep.type = "button";
  keep.disabled = locked;
  keep.addEventListener("click", () => onKeep());
  closing.append(keep);
  panel.append(closing);
  return { panel, heading, context, generate, retry };
}
