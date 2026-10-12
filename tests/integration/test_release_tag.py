"""Story 1.8: the release fails when the pushed tag isn't v<pyproject version> (R-04).

Decided 2026-10-12: the guard is scripts/check_release_tag.py <tag>, run by release.yml from
the repo root before anything is built. It exits 0 only for exactly v<version>, else 1, and
names both the tag and the version either way.

Skipped until the script exists. Un-skip it, watch it fail, then implement.
"""

import pytest

from tests.support.release import next_patch, pyproject_version, run_tag_check

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 1.8: un-skip with scripts/check_release_tag.py"
)

VERSION = pyproject_version()
MISMATCH = 1  # the workflow step fails, so no wheel is built or uploaded


@RED_PHASE
@pytest.mark.p1
@pytest.mark.parametrize(
    ("tag", "expected_exit"),
    [
        (f"v{VERSION}", 0),
        (f"v{next_patch(VERSION)}", MISMATCH),
        (VERSION, MISMATCH),  # vX.Y.Z only: the bare version isn't a release tag
        (f"v{VERSION}-rc1", MISMATCH),
    ],
    ids=["matching", "next-patch", "missing-v", "pre-release-suffix"],
)
def test_release_tag_must_equal_pyproject_version(tag: str, expected_exit: int) -> None:
    """AC-2: the guard passes only a tag equal to v<pyproject version>, naming both values."""
    result = run_tag_check(tag)

    assert result.returncode == expected_exit
    assert tag in result.output
    assert VERSION in result.output
    assert "Traceback" not in result.output
