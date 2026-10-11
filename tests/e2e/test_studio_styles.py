"""Story 1.5: Studio base styles and vendored Figtree, checked on the served shell.

Skipped until static/css and static/vendor/figtree land. Un-skip one per task, watch it fail,
then implement.
"""

import pytest
from playwright.sync_api import Page, expect

from language_lab import __version__
from tests.support import viewports
from tests.support.dom import append_to_body, computed_style, px, settle_fonts
from tests.support.network import record_resources

RED_PHASE = pytest.mark.skip(
    reason="ATDD red phase, story 1.5: un-skip with static/css and static/vendor/figtree"
)

# EXPERIENCE.md a11y floor: "Visible focus ring on every control ({colors.accent} 2px)"
ACCENT = "rgb(90, 69, 200)"  # colors.accent #5A45C8
FOCUS_RING = {"outlineStyle": "solid", "outlineWidth": "2px", "outlineColor": ACCENT}
# Below 16px, iOS Safari zooms the page when a field takes focus (DESIGN.md Typography)
MIN_FIELD_FONT_PX = 16
FIGTREE_WEIGHTS = (400, 500, 600, 700)

# Reports which Figtree faces rendered text has loaded, then which weights load on request
FIGTREE_FACES = """async (weights) => {
  const isFigtree = (face) => face.family.replace(/["']/g, "") === "Figtree";
  const rendered = [...document.fonts].filter((f) => isFigtree(f) && f.status === "loaded");
  const weightsLoaded = {};
  for (const weight of weights) {
    const faces = await document.fonts.load(`${weight} 16px Figtree`);
    weightsLoaded[weight] = faces.some((f) => isFigtree(f) && f.status === "loaded");
  }
  return { rendered: rendered.length, weightsLoaded };
}"""


def open_shell(page: Page) -> None:
    """Load the shell and wait until it has rendered the version and its fonts have settled."""
    with page.expect_response("**/api/health"):
        page.goto("/")
    expect(page.get_by_role("main")).to_have_text(f"LanguageLab v{__version__}")
    settle_fonts(page)


@RED_PHASE
@pytest.mark.p2
def test_keyboard_focus_shows_accent_ring(page: Page) -> None:
    """AC-2: base styles give a visible focus ring."""
    page.goto("/")
    append_to_body(page, '<button type="button">Focus probe</button>')
    probe = page.get_by_role("button", name="Focus probe")

    page.keyboard.press("Tab")
    expect(probe).to_be_focused()

    assert computed_style(probe, *FOCUS_RING) == FOCUS_RING


@RED_PHASE
@pytest.mark.p2
def test_form_fields_use_at_least_16px_text(page: Page) -> None:
    """AC-3: base styles set inputs at 16px or more."""
    page.set_viewport_size(viewports.PHONE)
    page.goto("/")
    append_to_body(
        page,
        '<input aria-label="Input probe">'
        '<textarea aria-label="Textarea probe"></textarea>'
        '<select aria-label="Select probe"><option>One</option></select>',
    )

    sizes = {
        name: px(computed_style(page.get_by_label(name), "fontSize")["fontSize"])
        for name in ("Input probe", "Textarea probe", "Select probe")
    }

    assert {name: size for name, size in sizes.items() if size < MIN_FIELD_FONT_PX} == {}


@RED_PHASE
@pytest.mark.p2
def test_shell_renders_in_vendored_figtree(page: Page) -> None:
    """AC-6: the shell loads Figtree, and Figtree is applied."""
    open_shell(page)

    fonts = page.evaluate(FIGTREE_FACES, list(FIGTREE_WEIGHTS))

    # Browsers fetch a face only when rendered text uses it, so a loaded face means applied
    assert fonts["rendered"] > 0
    family = computed_style(page.get_by_role("main"), "fontFamily")["fontFamily"]
    assert family.split(",")[0].strip().strip("\"'") == "Figtree"
    assert fonts["weightsLoaded"] == {str(weight): True for weight in FIGTREE_WEIGHTS}


@RED_PHASE
@pytest.mark.p2
def test_styles_and_fonts_come_from_the_app(page: Page, base_url: str) -> None:
    """AC-8: every request the served shell makes goes to the app, none to an external host."""
    resources = record_resources(page)

    open_shell(page)

    assert {"stylesheet", "font"} <= {resource.resource_type for resource in resources}
    assert [r.url for r in resources if not r.url.startswith(f"{base_url}/")] == []
