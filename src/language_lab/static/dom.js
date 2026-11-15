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

// Write `text` to the system clipboard; true once it's there. The async API needs a secure
// context, and the app is also opened over plain http on the LAN, so a hidden textarea and
// execCommand("copy") stand in when it's missing or refuses
export async function copyText(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall through to the textarea
  }
  const field = element("textarea");
  field.value = text;
  field.setAttribute("readonly", "");
  field.setAttribute("aria-hidden", "true");
  field.style.position = "fixed";
  field.style.top = "0";
  field.style.left = "0";
  field.style.opacity = "0";
  field.style.fontSize = "16px"; // iOS zooms into a smaller field
  const focused = document.activeElement;
  document.body.append(field);
  try {
    field.select();
    field.setSelectionRange(0, field.value.length); // iOS Safari ignores select()
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    field.remove();
    if (focused instanceof HTMLElement) focused.focus();
  }
}
