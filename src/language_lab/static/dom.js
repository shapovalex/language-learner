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
