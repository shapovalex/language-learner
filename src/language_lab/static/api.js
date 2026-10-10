// The only module that calls fetch (AD-13).

export async function request(path, options = {}) {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export function getHealth() {
  return request("/api/health");
}
