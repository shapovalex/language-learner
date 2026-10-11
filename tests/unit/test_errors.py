"""Story 1.3: the AD-15 error-code enum.

Skipped until `domain/errors.py` lands. Un-skip, watch it fail, then implement.
"""

import pytest

RED_PHASE = pytest.mark.skip(reason="ATDD red phase, story 1.3: un-skip with domain/errors.py")

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
}


@RED_PHASE
@pytest.mark.p1
def test_error_code_enum_holds_the_twelve_ad15_codes() -> None:
    """AC-1: domain/errors.py defines the twelve-code enum from AD-15."""
    from language_lab.domain.errors import ErrorCode

    assert {code.value for code in ErrorCode} == AD15_CODES
    assert len(ErrorCode) == len(AD15_CODES)
