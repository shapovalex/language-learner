"""The AD-15 error codes and the error envelope every /api failure returns."""

from enum import StrEnum


class ErrorCode(StrEnum):
    ANKI_UNAVAILABLE = "anki_unavailable"
    ANKI_BUSY = "anki_busy"
    LLM_FAILED = "llm_failed"
    LLM_INVALID_OUTPUT = "llm_invalid_output"
    TTS_FAILED = "tts_failed"
    ASSESSMENT_FAILED = "assessment_failed"
    VALIDATION_FAILED = "validation_failed"
    NOT_FOUND = "not_found"
    FORBIDDEN_ORIGIN = "forbidden_origin"
    SETUP_REQUIRED = "setup_required"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    INTERNAL_ERROR = "internal_error"
    PLAN_CHANGED = "plan_changed"


# Fixed per code: a message is never built from input, exception text or headers (AD-15)
MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.ANKI_UNAVAILABLE: "Anki isn't reachable. Check that Anki is running.",
    ErrorCode.ANKI_BUSY: "Anki is busy. Try again in a moment.",
    ErrorCode.LLM_FAILED: "The language model request failed.",
    ErrorCode.LLM_INVALID_OUTPUT: "The language model returned an unusable answer.",
    ErrorCode.TTS_FAILED: "Speech synthesis failed.",
    ErrorCode.ASSESSMENT_FAILED: "Pronunciation assessment failed.",
    ErrorCode.VALIDATION_FAILED: "The request isn't valid.",
    ErrorCode.NOT_FOUND: "Not found.",
    ErrorCode.FORBIDDEN_ORIGIN: "This request's origin isn't allowed.",
    ErrorCode.SETUP_REQUIRED: "Setup isn't complete yet.",
    ErrorCode.PAYLOAD_TOO_LARGE: "The request is too large.",
    ErrorCode.INTERNAL_ERROR: "Something went wrong on the server.",
    ErrorCode.PLAN_CHANGED: "Anki changed since the preview. Review the changes and apply again.",
}


class AppError(Exception):
    """A typed domain failure. Its text is the fixed message for `code`, never upstream text."""

    def __init__(self, code: ErrorCode) -> None:
        super().__init__(MESSAGES[code])
        self.code = code


def error_envelope(code: ErrorCode, request_id: str) -> dict[str, dict[str, str]]:
    """The AD-15 body `{"error": {"code", "message", "requestId"}}` for `code`."""
    return {"error": {"code": code.value, "message": MESSAGES[code], "requestId": request_id}}
