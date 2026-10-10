import { getHealth } from "./api.js";

const root = document.getElementById("app");

try {
  const { version } = await getHealth();
  root.textContent = `LanguageLab v${version}`;
} catch {
  root.textContent = "LanguageLab could not reach the server.";
}
