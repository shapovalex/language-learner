// Captures screen (AD-13). Empty until the Captures entries land.

export function mount(root) {
  const heading = document.createElement("h1");
  heading.textContent = "Captures";
  root.replaceChildren(heading);
  return () => root.replaceChildren();
}
