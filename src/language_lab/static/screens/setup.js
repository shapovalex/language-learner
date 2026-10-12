// Setup screen (AD-13). Shows the server version from /api/health.

import { getHealth } from "../api.js";

export function mount(root) {
  let mounted = true;
  const heading = document.createElement("h1");
  heading.textContent = "Setup";
  const status = document.createElement("p");
  root.replaceChildren(heading, status);

  getHealth().then(
    ({ version }) => {
      if (mounted) status.textContent = `LanguageLab v${version}`;
    },
    () => {
      if (mounted) status.textContent = "LanguageLab could not reach the server.";
    },
  );

  return () => {
    mounted = false;
    root.replaceChildren();
  };
}
