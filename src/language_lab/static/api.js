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

export async function request(path, options = {}) {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    throw await toApiError(response);
  }
  return response.json();
}

export function getHealth() {
  return request("/api/health");
}
