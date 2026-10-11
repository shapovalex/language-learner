"""Story 1.5: the Studio tokens in static/css and the vendored Figtree files.

Skipped until static/css and static/vendor/figtree land. Un-skip one per task, watch it fail,
then implement.
"""

from pathlib import Path

import pytest

import language_lab
from tests.support.design_tokens import (
    css_custom_properties,
    expected_custom_properties,
    load_front_matter,
)

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 1.5: un-skip with static/css and static/vendor/figtree"
)

STATIC = Path(language_lab.__file__).resolve().parent / "static"
FIGTREE_DIR = STATIC / "vendor" / "figtree"
# Figtree is licensed under the SIL OFL 1.1, which requires shipping the license with the fonts
FIGTREE_LICENSE = FIGTREE_DIR / "OFL.txt"


@RED_PHASE
@pytest.mark.p3
def test_css_declares_every_design_md_token() -> None:
    """AC-1: static/css holds the DESIGN.md Studio tokens (colors, spacing, radius, type scale)."""
    expected = expected_custom_properties(load_front_matter())
    assert expected, "DESIGN.md front matter parsed to no tokens"
    declared = css_custom_properties(STATIC / "css")

    assert sorted(expected.keys() - declared.keys()) == []
    assert {name: declared[name] for name in expected if declared[name] != expected[name]} == {}


@RED_PHASE
@pytest.mark.p2
def test_figtree_is_vendored_with_its_license() -> None:
    """AC-5: Figtree is vendored with its license under static/vendor/."""
    fonts = sorted(path.name for path in FIGTREE_DIR.glob("*.woff2"))

    assert fonts != []
    assert FIGTREE_LICENSE.is_file()
    assert "SIL Open Font License" in FIGTREE_LICENSE.read_text(encoding="utf-8")
