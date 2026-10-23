// DOM helpers the screen modules share (AD-13).

export function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// A loading skeleton: `label` for assistive tech, three bars drawn for the eye
export function skeleton(label) {
  const node = element("div", "skeleton");
  node.setAttribute("role", "status");
  const bars = element("div", "skeleton-bars");
  bars.setAttribute("aria-hidden", "true");
  for (let i = 0; i < 3; i += 1) bars.append(element("span", "skeleton-bar"));
  node.append(element("div", "skeleton-label", label), bars);
  return node;
}

// An inline error alert, `inline-alert-error` plus `className`, announced as it appears
export function alertBox(className, ...children) {
  const node = element("div", `inline-alert-error ${className}`);
  node.setAttribute("role", "alert");
  node.append(...children);
  return node;
}

// A "Try again" button in the `variant` button style ("destructive" or "secondary")
export function tryAgain(onClick, variant = "destructive") {
  const button = element("button", `button button-${variant}`, "Try again");
  button.type = "button";
  button.addEventListener("click", onClick);
  return button;
}
