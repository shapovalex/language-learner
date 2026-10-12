"""The shell's destinations and the ways to reach them (AD-13, EXPERIENCE navigation model)."""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page

from tests.support import viewports


@dataclass(frozen=True)
class Destination:
    path: str
    area: str  # its link in the Main nav and the Menu sheet
    heading: str  # the screen's one <h1>
    section: str | None = None  # its link in the Language nav (Items / Pronunciation)


CAPTURES = Destination("/captures", "Captures", "Captures")
EN_ITEMS = Destination("/en/items", "English", "English Items", "Items")
EN_PRONUNCIATION = Destination(
    "/en/pronunciation", "English", "English Pronunciation", "Pronunciation"
)
FR_ITEMS = Destination("/fr/items", "French", "French Items", "Items")
FR_PRONUNCIATION = Destination(
    "/fr/pronunciation", "French", "French Pronunciation", "Pronunciation"
)
SETUP = Destination("/setup", "Setup", "Setup")

DESTINATIONS = (CAPTURES, EN_ITEMS, EN_PRONUNCIATION, FR_ITEMS, FR_PRONUNCIATION, SETUP)
AREAS = ("Captures", "English", "French", "Setup")
SECTIONS = ("Items", "Pronunciation")
LANDING_SECTION = "Items"  # where the English and French links lead

# Leaves no trace in the URL or the DOM, and is gone after any document load
MARK_DOCUMENT = "() => { window.__navProbe = crypto.randomUUID(); return window.__navProbe; }"
READ_MARK = "() => window.__navProbe ?? null"


def main_nav(page: Page) -> Locator:
    return page.get_by_role("navigation", name="Main", exact=True)


def language_nav(page: Page, area: str) -> Locator:
    """The per-Language Items / Pronunciation control, named after its Language."""
    return page.get_by_role("navigation", name=area, exact=True)


def menu_button(page: Page) -> Locator:
    return page.get_by_role("button", name="Menu", exact=True)


def menu_sheet(page: Page) -> Locator:
    return page.get_by_role("dialog", name="Menu", exact=True)


def screen_heading(page: Page) -> Locator:
    return page.get_by_role("main").get_by_role("heading", level=1)


def is_phone(page: Page) -> bool:
    size = page.viewport_size
    return size is not None and size["width"] <= viewports.PHONE["width"]


def path_pattern(path: str) -> re.Pattern[str]:
    """Matches a page URL whose path is exactly `path`, on any origin."""
    return re.compile(rf"^[a-z]+://[^/]+{re.escape(path)}$")


def go_by_nav(page: Page, destination: Destination) -> None:
    """Reach `destination` the way a user would at the current width, then wait for its URL.

    Outside the destination's Language: its pill, or its Menu sheet row on phone, which lands on
    the Items section. Then the Language nav, unless that landing is already the destination.
    Inside the Language, only the Language nav, so history gets one entry per destination.
    """
    language_root = destination.path.rsplit("/", 1)[0] + "/"
    in_language = destination.section is not None and urlparse(page.url).path.startswith(
        language_root
    )
    if not in_language:
        if is_phone(page):
            menu_button(page).click()
            menu_sheet(page).get_by_role("link", name=destination.area, exact=True).click()
        else:
            main_nav(page).get_by_role("link", name=destination.area, exact=True).click()
    if destination.section and (in_language or destination.section != LANDING_SECTION):
        language_nav(page, destination.area).get_by_role(
            "link", name=destination.section, exact=True
        ).click()
    page.wait_for_url(path_pattern(destination.path))
