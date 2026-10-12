"""Story 1.8: the release fails when the pushed tag isn't v<pyproject version> (R-04).

Decided 2026-10-12: the guard is scripts/check_release_tag.py <tag>, run by release.yml from
the repo root before anything is built. It exits 0 only for exactly v<version>, else 1, and
names both the tag and the version either way. Bad usage (no tag, an empty tag, or more
than one) is a usage line and exit 2, never a traceback.
"""

import subprocess
import sys

import pytest

from tests.support.release import (
    RELEASE_TAG_SCRIPT,
    REPO_ROOT,
    next_patch,
    pyproject_version,
    run_tag_check,
)

VERSION = pyproject_version()
MISMATCH = 1  # the workflow step fails, so no wheel is built or uploaded
BAD_USAGE = 2


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


@pytest.mark.p3
@pytest.mark.parametrize(
    "args",
    [[], [""], [f"v{VERSION}", f"v{VERSION}"]],
    ids=["no-argument", "empty-argument", "two-arguments"],
)
def test_release_tag_guard_rejects_bad_usage(args: list[str]) -> None:
    """AC-2: anything but exactly one tag is a usage error (exit 2), not a traceback."""
    result = subprocess.run(
        [sys.executable, str(RELEASE_TAG_SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == BAD_USAGE
    assert "usage:" in result.stderr
    assert "Traceback" not in result.stdout + result.stderr
