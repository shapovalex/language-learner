"""Story 1.3: the AD-15 error-code enum."""

import pytest

# AD-15 lists these codes exactly; the API and api.js both depend on the spelling
AD15_CODES = {
    "anki_unavailable",
    "anki_busy",
    "llm_failed",
    "llm_invalid_output",
    "tts_failed",
    "assessment_failed",
    "validation_failed",
    "not_found",
    "forbidden_origin",
    "setup_required",
    "payload_too_large",
    "internal_error",
    "plan_changed",  # story 2.7, decided with the user on 2026-10-21
    "sync_required",  # story 2.9, decided with the user on 2026-10-21
}


@pytest.mark.p1
def test_error_code_enum_holds_the_ad15_codes() -> None:
    """AC-1: domain/errors.py defines the AD-15 code enum (story 2.7 adds `plan_changed`, story
    2.9 `sync_required`).
    """
    from language_lab.domain.errors import ErrorCode

    assert {code.value for code in ErrorCode} == AD15_CODES
    assert len(ErrorCode) == len(AD15_CODES)
