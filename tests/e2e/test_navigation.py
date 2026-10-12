"""Story 1.6: shell navigation between the four areas and six destinations (AD-13).

Decided 2026-10-11: router.js replaces `/` and unknown paths with /captures; the server
version renders on the Setup screen; English and French lead to their Items section.
"""

import pytest
from playwright.sync_api import Page, ViewportSize, expect

from language_lab import __version__
from tests.support import viewports
from tests.support.navigation import (
    AREAS,
    CAPTURES,
    DESTINATIONS,
    MARK_DOCUMENT,
    READ_MARK,
    SECTIONS,
    SETUP,
    Destination,
    go_by_nav,
    language_nav,
    main_nav,
    menu_button,
    path_pattern,
    screen_heading,
)

VERSION_TEXT = f"LanguageLab v{__version__}"
LANGUAGES = {"English": "en", "French": "fr"}

# Imports a screen module, mounts it on a detached element, unmounts it, and reports as data
MOUNT_SCREEN = """async ({ url, params }) => {
  let screen;
  try {
    screen = await import(url);
  } catch {
    return { imported: false };
  }
  const root = document.createElement("div");
  const unmount = screen.mount(root, params);
  const heading = root.querySelector("h1")?.textContent.trim() ?? null;
  const unmountIsFunction = typeof unmount === "function";
  if (unmountIsFunction) unmount();
  return { imported: true, heading, unmountIsFunction, emptyAfterUnmount: !root.hasChildNodes() };
}"""

# (module, params, heading): one module per kind of screen, Language passed as a param
SCREEN_MODULES = [
    ("captures", {}, "Captures"),
    ("items", {"lang": "en"}, "English Items"),
    ("items", {"lang": "fr"}, "French Items"),
    ("pronunciation", {"lang": "en"}, "English Pronunciation"),
    ("pronunciation", {"lang": "fr"}, "French Pronunciation"),
    ("setup", {}, "Setup"),
]

WIDTHS = pytest.mark.parametrize("viewport", viewports.ALL.values(), ids=viewports.ALL.keys())
BY_DESTINATION = pytest.mark.parametrize("destination", DESTINATIONS, ids=lambda d: d.path)


def expect_at(page: Page, destination: Destination) -> None:
    expect(page).to_have_url(path_pattern(destination.path))
    expect(screen_heading(page)).to_have_text(destination.heading)


@pytest.mark.p1
def test_nav_links_route_without_reloading(page: Page) -> None:
    """AC-1: router.js routes with the History API, so following a link keeps the document."""
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES.path)
    mark = page.evaluate(MARK_DOCUMENT)

    main_nav(page).get_by_role("link", name=SETUP.area, exact=True).click()

    expect(page).to_have_url(path_pattern(SETUP.path))
    assert page.evaluate(READ_MARK) == mark
    expect(screen_heading(page)).to_have_text(SETUP.heading)


@pytest.mark.p1
@pytest.mark.parametrize(
    "viewport", [viewports.TABLET, viewports.DESKTOP], ids=["tablet", "desktop"]
)
def test_header_shows_pills_on_tablet_and_desktop(page: Page, viewport: ViewportSize) -> None:
    """AC-2: the header shows nav pills on tablet and desktop."""
    page.set_viewport_size(viewport)
    page.goto(CAPTURES.path)

    expect(main_nav(page).get_by_role("link")).to_have_text(list(AREAS))
    expect(main_nav(page)).to_be_visible()
    expect(menu_button(page)).to_be_hidden()


@pytest.mark.p1
@pytest.mark.parametrize("area", LANGUAGES, ids=LANGUAGES.values())
def test_language_nav_switches_section(page: Page, area: str) -> None:
    """AC-4: each Language's Items / Pronunciation control changes the route."""
    lang = LANGUAGES[area]
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(f"/{lang}/items")
    sections = language_nav(page, area)

    expect(sections.get_by_role("link")).to_have_text(list(SECTIONS))

    sections.get_by_role("link", name="Pronunciation", exact=True).click()
    expect(page).to_have_url(path_pattern(f"/{lang}/pronunciation"))
    expect(screen_heading(page)).to_have_text(f"{area} Pronunciation")
    sections.get_by_role("link", name="Items", exact=True).click()
    expect(page).to_have_url(path_pattern(f"/{lang}/items"))
    expect(screen_heading(page)).to_have_text(f"{area} Items")


@pytest.mark.p1
@BY_DESTINATION
def test_aria_current_marks_area_and_section(page: Page, destination: Destination) -> None:
    """AC-5: aria-current marks the active area and, inside a Language, the active section."""
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(destination.path)

    expect(main_nav(page).locator("[aria-current='page']")).to_have_text([destination.area])
    if destination.section:
        sections = language_nav(page, destination.area)
        expect(sections.locator("[aria-current='page']")).to_have_text([destination.section])


@pytest.mark.p2
@pytest.mark.parametrize(
    ("module", "params", "heading"),
    SCREEN_MODULES,
    ids=[heading for _, _, heading in SCREEN_MODULES],
)
def test_screen_module_mounts_and_unmounts(
    page: Page, module: str, params: dict[str, str], heading: str
) -> None:
    """AC-6: each screen is one module exporting mount(root, params) -> unmount."""
    page.goto(CAPTURES.path)

    result = page.evaluate(
        MOUNT_SCREEN, {"url": f"/static/{__version__}/screens/{module}.js", "params": params}
    )

    assert result == {
        "imported": True,
        "heading": heading,
        "unmountIsFunction": True,
        "emptyAfterUnmount": True,
    }


@pytest.mark.p1
@WIDTHS
def test_every_destination_reachable_by_nav(page: Page, viewport: ViewportSize) -> None:
    """AC-7: at each width every destination is reachable by nav (pills, or Menu on phone)."""
    page.set_viewport_size(viewport)
    page.goto(SETUP.path)

    for destination in DESTINATIONS:
        go_by_nav(page, destination)
        expect_at(page, destination)


@pytest.mark.p1
@WIDTHS
def test_every_destination_loads_directly(page: Page, viewport: ViewportSize) -> None:
    """AC-8: at each width every destination renders when its URL is loaded directly."""
    page.set_viewport_size(viewport)

    for destination in DESTINATIONS:
        page.goto(destination.path)
        expect_at(page, destination)


@pytest.mark.p1
@WIDTHS
def test_browser_back_returns_through_destinations(page: Page, viewport: ViewportSize) -> None:
    """AC-9: at each width browser back returns to each previously visited destination."""
    page.set_viewport_size(viewport)
    page.goto(SETUP.path)
    visited = [SETUP]
    for destination in DESTINATIONS[:-1]:
        go_by_nav(page, destination)
        visited.append(destination)

    for previous in reversed(visited[:-1]):
        page.go_back()
        expect_at(page, previous)


@pytest.mark.p2
@pytest.mark.parametrize("path", ["/", "/nowhere", "/de/items"])
def test_root_and_unknown_paths_redirect_to_captures(page: Page, path: str) -> None:
    """AC-11: router.js replaces `/` and any path it doesn't know with /captures."""
    page.goto(path)

    expect(page).to_have_url(path_pattern(CAPTURES.path))
    expect(screen_heading(page)).to_have_text(CAPTURES.heading)


@pytest.mark.p1
def test_server_version_shows_on_setup_only(page: Page) -> None:
    """AC-12: the version from /api/health renders on the Setup screen, not in the shell."""
    page.goto(CAPTURES.path)
    # Unasserted setup: without it the absence check below passes before main.js has rendered
    screen_heading(page).filter(has_text=CAPTURES.heading).wait_for()

    expect(page.get_by_role("main").get_by_text(VERSION_TEXT)).to_have_count(0)

    with page.expect_response("**/api/health"):
        page.goto(SETUP.path)
    expect(page.get_by_role("main").get_by_text(VERSION_TEXT)).to_be_visible()


@pytest.mark.p2
def test_redirect_leaves_no_history_entry(page: Page) -> None:
    """AC-11: the redirect replaces the unknown path, so back never returns to it."""
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(SETUP.path)
    screen_heading(page).filter(has_text=SETUP.heading).wait_for()
    page.evaluate(
        "() => { history.pushState(null, '', '/nowhere');"
        " dispatchEvent(new PopStateEvent('popstate')); }"
    )
    expect(page).to_have_url(path_pattern(CAPTURES.path))

    page.go_back()

    expect_at(page, SETUP)


@pytest.mark.p2
def test_same_path_click_pushes_no_history_entry(page: Page) -> None:
    """AC-1: following a link to the current path adds no history entry."""
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(SETUP.path)
    main_nav(page).get_by_role("link", name=CAPTURES.area, exact=True).click()
    expect_at(page, CAPTURES)

    main_nav(page).get_by_role("link", name=CAPTURES.area, exact=True).click()
    page.go_back()

    expect_at(page, SETUP)


# Mounts Setup with /api/health held open, unmounts it, then lets the response arrive
LATE_HEALTH = """async (url) => {
  const { mount } = await import(url);
  let respond;
  const realFetch = window.fetch;
  window.fetch = () => new Promise((resolve) => { respond = resolve; });
  const root = document.createElement("div");
  let status;
  try {
    const unmount = mount(root, {});
    status = root.querySelector("p");
    unmount();
    respond(new Response(JSON.stringify({ version: "9.9.9" }), { status: 200 }));
    await new Promise((resolve) => setTimeout(resolve, 50));
  } finally {
    window.fetch = realFetch;
  }
  const empty = !root.hasChildNodes();
  return { called: respond !== undefined, statusText: status.textContent, empty };
}"""


@pytest.mark.p2
def test_setup_ignores_health_after_unmount(page: Page) -> None:
    """AC-6: a /api/health response that arrives after unmount writes nothing."""
    page.goto(CAPTURES.path)

    result = page.evaluate(LATE_HEALTH, f"/static/{__version__}/screens/setup.js")

    assert result == {"called": True, "statusText": "", "empty": True}
