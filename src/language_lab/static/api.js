// The only module that calls fetch (AD-13).

// A failed API call, parsed from the AD-15 envelope `{error: {code, message, requestId, details?}}`.
export class ApiError extends Error {
  constructor({ status, code, message, requestId = null, details = null }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

// What the screens show when a request never reached the server (no envelope)
export const NETWORK_FALLBACK = "LanguageLab could not reach the server.";

export function isApiError(error, code) {
  return error?.name === "ApiError" && error.code === code;
}

// An ApiError carries the envelope's fixed message (AD-15)
export function errorMessage(error) {
  return error?.name === "ApiError" ? error.message : NETWORK_FALLBACK;
}

async function toApiError(response) {
  let body = null;
  try {
    body = await response.json();
  } catch {
    // Not JSON, e.g. an HTML error page from a proxy
  }
  const error = body && typeof body === "object" ? body.error : null;
  if (error && typeof error.code === "string" && typeof error.message === "string") {
    return new ApiError({
      status: response.status,
      code: error.code,
      message: error.message,
      requestId: typeof error.requestId === "string" ? error.requestId : null,
      details: error.details ?? null,
    });
  }
  return new ApiError({
    status: response.status,
    code: "internal_error",
    message: `Request failed: ${response.status}`,
  });
}

export async function request(path, options = {}, binary = false) {
  const headers = new Headers(options.headers);
  headers.set("Accept", binary ? "audio/mpeg" : "application/json");
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) return null; // No Content: nothing to parse
  return binary ? response.blob() : response.json();
}

export function getHealth() {
  return request("/api/health");
}

// `{prefix, checks: [{id, ok}]}`, the checks in tile order (FR-5); `fullSync` last (AD-17)
export function getReadiness() {
  return request("/api/setup/readiness");
}

// `{prefix, planHash, state, items: [{action, kind, name, requiresFullSync}],
// repairs: [{key, action, kind, name, checked, ...detail}], unmanaged: [{kind, name}]}`
// (FR-6, AD-3). `repairs` are the checked opt-in repair keys: the server re-plans with them,
// and `planHash` covers the items plus those rows.
export function getPlan(repairs = []) {
  const query = new URLSearchParams(repairs.map((key) => ["repair", key])).toString();
  return request(query ? `/api/setup/plan?${query}` : "/api/setup/plan");
}

// Apply the plan the user confirmed by its hash, run to its end and verified (FR-6, AD-3):
// `{verified, planHash, discrepancies: [{action, kind, name, requiresFullSync}], fullSyncRequired}`.
// A stale hash is 409 `plan_changed`; a field change whose Sync failed is 409 `sync_required`.
// `repairs` are the checked opt-in repair keys `planHash` was read with.
export function applySetup(planHash, repairs = []) {
  return request("/api/setup/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ planHash, repairs }),
  });
}

// `{state: "idle" | "running" | "finished", result}`: the last apply run, for a screen coming back
export function getApplyStatus() {
  return request("/api/setup/apply/status");
}

// The user uploaded in Anki Desktop after a field change: clears Full sync required (204)
export function fullSyncUploaded() {
  return request("/api/setup/full-sync/uploaded", { method: "POST" });
}

// Save a Capture under the composition's CaptureId (FR-9, AD-8): 201 `{captureId, text,
// createdAt}`. A retry with the same CaptureId returns the Capture already saved (AD-20).
export function createCapture(captureId, text) {
  return request("/api/captures", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ captureId, text }),
  });
}

// Every Capture, newest first by CreatedAt (FR-10): `{captures: [{captureId, text, createdAt}]}`
export function listCaptures() {
  return request("/api/captures");
}

// One Capture, `{captureId, text, createdAt}`; 404 `not_found` when it isn't in Anki
export function getCapture(captureId) {
  return request(`/api/captures/${encodeURIComponent(captureId)}`);
}

// Delete a Capture (FR-13): 204, also for one already gone, so a retry succeeds
export function deleteCapture(captureId) {
  return request(`/api/captures/${encodeURIComponent(captureId)}`, { method: "DELETE" });
}

// A blank Draft (AD-8): 201 `{itemId}`, the ItemId the Draft carries until Save
export function blankDraft() {
  return request("/api/drafts/blank", { method: "POST" });
}

// A generated Draft (FR-14 to FR-16): `{language, category, target, generationContext}` in,
// 201 `{itemId, ...ItemContent}` out; `llm_failed` or `llm_invalid_output` when the model fails
export function generateDraft(body) {
  return request("/api/drafts/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// An Item's regenerated content, for its Preview (FR-24, AD-11): `{language, category, target,
// generationContext}` in, 200 ItemContent out, the Category's full generated model with no
// `itemId`; `llm_failed` or `llm_invalid_output` when the model fails
export function regenerateContent(body) {
  return request("/api/drafts/regenerate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// Save an Item (FR-20): `multipart/form-data` with the `item` JSON part, ItemContent plus
// `itemId` and `audio` (Consistency Conventions): `replace` with `audioBlob` as `audioFile`,
// `keep` or `remove` (AD-6, story 6.2) with none. 200 `{itemId}`; a retry with the same ItemId
// updates the Item (AD-20). The part is a string field: a Blob would arrive as a file
export function saveItem(lang, item, audioBlob = null) {
  const body = new FormData();
  body.append("item", JSON.stringify(item));
  if (audioBlob) body.append("audioFile", audioBlob, "preview.mp3");
  return request(`/api/items/${encodeURIComponent(lang)}`, { method: "POST", body });
}

// The duplicate check before a Save (FR-19, AD-12): `{matches: [{itemId, ...ItemContent}]}`,
// the Items of `lang` and `category` whose normalized Target equals `target`'s, without the
// Draft's own `itemId`
export function findDuplicates(lang, { category, target, itemId }) {
  const params = new URLSearchParams({ category, target });
  if (itemId) params.set("itemId", itemId);
  const query = params.toString();
  return request(`/api/items/${encodeURIComponent(lang)}/duplicates?${query}`);
}

// One Item as Anki holds it now (FR-22): `{itemId, ...ItemContent, audio}`, `audio` the managed
// clip's name for /api/media or null; 404 `not_found` when
// that Language has no Item with the ItemId
export function getItem(lang, itemId) {
  return request(`/api/items/${encodeURIComponent(lang)}/${encodeURIComponent(itemId)}`);
}

// Delete the Item and finish its media cleanup, including on retries (204).
export function deleteItem(lang, itemId) {
  return request(`/api/items/${encodeURIComponent(lang)}/${encodeURIComponent(itemId)}`, {
    method: "DELETE",
  });
}

// The Items of `lang`, both Categories (FR-22): `{items: [{itemId, ...ItemContent, hasAudio}]}`,
// those whose normalized Target, Russian meaning or an alternative contains `query` (AD-12).
// A blank `query` is not sent, and lists every Item
export function listItems(lang, query = "") {
  const path = `/api/items/${encodeURIComponent(lang)}`;
  if (!query.trim()) return request(path);
  return request(`${path}?${new URLSearchParams({ q: query })}`);
}

export function getVoices(language) {
  return request(`/api/audio/voices?${new URLSearchParams({ language })}`);
}

export function previewAudio(body) {
  return request("/api/audio/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }, true);
}
