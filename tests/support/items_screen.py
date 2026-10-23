"""The Make an Item pane, the Draft editor, the duplicate sheet and Item detail: copy, locators
and the requests, shared by the Item E2E tests (tests/e2e/test_make_an_item.py,
tests/e2e/test_generate_draft.py, tests/e2e/test_duplicate_warning.py,
tests/e2e/test_item_detail.py).

The pane is a region named "Make an Item" in Capture detail; the Draft editor is a form named
"Draft" at /captures/<captureId>/new. Its fields are found by the start of their label, so an
"optional" note in the label doesn't matter. `item_part(request)` reads the `item` JSON part of
a Save's multipart body.

The duplicate sheet (S-Duplicate, story 4.3) is a dialog named by its title, over the Draft
editor. `stub_duplicates(page, matches)` answers the duplicate read with `matches`, whatever its
query string; the Item E2E tests stub it before every Save, since the live server's fake keeps
the Items earlier tests saved. `duplicate_query(request)` is a check's query parameters. Item
detail (S-ItemDetail) is at /<lang>/items/<itemId>.
"""

import json
import re
from email.parser import BytesParser
from email.policy import HTTP
from typing import Any
from urllib.parse import parse_qsl, urlparse

from playwright.sync_api import Locator, Page, Request, Route

from tests.support.captures_screen import main

BLANK_DRAFT_API = "/api/drafts/blank"
GENERATE_API = "/api/drafts/generate"
ITEMS_API = "/api/items/"

MAKE_AN_ITEM = "Make an Item"
USE_AS_IS = "Use as is"
CUSTOM_VALUE = "Custom value"
WRITE_IT_MYSELF = "Write it myself"
CHOOSE_REASON = "Choose a Language and Category."
CUSTOM_REASON = "Enter the custom value."
GENERATE_DRAFT = "Generate Draft"
GENERATION_CONTEXT = "Generation context · optional · used once, never saved"
WRITING = "Writing your Draft…"
TRY_AGAIN = "Try again"
CLEAR = "Clear"

# A failed generation's inline alert per code: title, body (EXPERIENCE.md State Patterns)
GENERATION_FAILED = {
    "llm_failed": ("Couldn't reach the model", "Your Capture is unchanged."),
    "llm_invalid_output": (
        "Couldn't generate a Draft",
        "The model's answer failed the checks twice. Your Capture is unchanged.",
    ),
}

DRAFT_CHIP = "Draft — not saved yet"
SAVE_TO_ANKI = "Save to Anki"
DRAFT_LOSS = "This Draft isn't saved."
NOT_SAVED_TITLE = "Not saved — Anki isn't reachable"
NOT_SAVED_BODY = (
    "Make sure Anki Desktop is open on the Mac mini, then try again. Your text is still here."
)

# Each Category's Draft fields, by label (decided 2026-10-22: the alternatives one per line)
VOCABULARY_FIELDS = (
    "Target",
    "Russian meaning",
    "Alternatives",
    "Part of speech",
    "Grammar",
    "Hint",
    "Example",
    "Example in Russian",
    "Mnemonic",
)
SENTENCE_FIELDS = ("Target", "Russian meaning", "Alternatives", "Hint", "Note")


def new_item_path(capture_id: str) -> str:
    return f"/captures/{capture_id}/new"


def from_capture(text: str) -> str:
    return f"From Capture “{text}”"


def saved_banner(target: str) -> str:
    return f"Saved “{target}” to Anki. Make another Item from this Capture, or delete it."


def banner(page: Page, target: str) -> Locator:
    """The success banner for a Save of `target`, shown on the Capture (FR-12)."""
    return page.get_by_role("status").filter(has_text=saved_banner(target))


def pane(page: Page) -> Locator:
    return main(page).get_by_role("region", name=MAKE_AN_ITEM, exact=True)


def choice(page: Page, name: str) -> Locator:
    """A Language or Category button in the pane (a picker with `aria-pressed`)."""
    return pane(page).get_by_role("button", name=name, exact=True)


def write_it_myself(page: Page) -> Locator:
    return pane(page).get_by_role("button", name=WRITE_IT_MYSELF, exact=True)


def generate_draft(page: Page) -> Locator:
    return pane(page).get_by_role("button", name=GENERATE_DRAFT, exact=True)


def generation_context(page: Page) -> Locator:
    """The pane's Generation context field, by the start of its label."""
    return pane(page).get_by_role("textbox", name=re.compile(r"^Generation context"))


def choose(page: Page, language: str, category: str, custom: str | None = None) -> None:
    """Pick the text, Language and Category in the pane."""
    if custom is not None:
        pane(page).get_by_role("radio", name=CUSTOM_VALUE, exact=True).check()
        pane(page).get_by_role("textbox", name=CUSTOM_VALUE).fill(custom)
    choice(page, language).click()
    choice(page, category).click()


def editor(page: Page) -> Locator:
    return main(page).get_by_role("form", name="Draft", exact=True)


def field(page: Page, label: str) -> Locator:
    """A Draft field by the start of its label: "Example" never matches "Example in Russian"."""
    name = re.compile(rf"^{re.escape(label)}(?! in Russian)\b")
    return editor(page).get_by_role("textbox", name=name)


def save_button(page: Page) -> Locator:
    return main(page).get_by_role("button", name=SAVE_TO_ANKI, exact=True)


def is_blank_draft(request: Request) -> bool:
    return request.method == "POST" and request.url.endswith(BLANK_DRAFT_API)


def is_generate(request: Request) -> bool:
    return request.method == "POST" and request.url.endswith(GENERATE_API)


def is_item_save(request: Request) -> bool:
    return request.method == "POST" and ITEMS_API in request.url


def item_part(request: Request) -> dict[str, Any]:
    """The `item` JSON part of a Save's `multipart/form-data` body."""
    content_type = request.headers["content-type"]
    raw = f"Content-Type: {content_type}\r\n\r\n".encode() + (request.post_data_buffer or b"")
    message = BytesParser(policy=HTTP).parsebytes(raw)
    for part in message.iter_parts():
        if part.get_param("name", header="content-disposition") == "item":
            return json.loads(part.get_payload(decode=True))
    raise AssertionError("the Save sent no item part")


# The duplicate sheet (EXPERIENCE.md Key strings: Duplicate)
DUPLICATE_TITLE = "You already have an Item with this text"
DUPLICATE_BODY = "Nothing has been saved yet. You can still create a second Item."
OPEN_EXISTING = "Open existing"
CANCEL = "Cancel"
CREATE_ANYWAY = "Create anyway"

# Item detail (EXPERIENCE.md Key strings: Item detail; the Capture detail's not-in-Anki copy)
ITEM_NOT_IN_ANKI = "This Item isn't in Anki."
LOADING_ITEM = "Loading Item…"


def duplicate_overline(language: str, category: str) -> str:
    """The sheet's overline, by the Language's and Category's names (S-Duplicate)."""
    return f"Possible duplicate · {language} · {category}"


def duplicates_api(language: str = "en") -> str:
    return f"/api/items/{language}/duplicates"


def item_api(language: str, item_id: str) -> str:
    return f"/api/items/{language}/{item_id}"


def item_detail_path(language: str, item_id: str) -> str:
    return f"/{language}/items/{item_id}"


def items_back_link(language: str) -> str:
    """Item detail's back link, by the Language's name (S-ItemDetail)."""
    return f"‹ {language} Items"


def duplicate_sheet(page: Page) -> Locator:
    """The sheet, anywhere in the page: an overlay may sit outside `main`."""
    return page.get_by_role("dialog", name=DUPLICATE_TITLE, exact=True)


def sheet_button(page: Page, name: str) -> Locator:
    return duplicate_sheet(page).get_by_role("button", name=name, exact=True)


def is_duplicate_check(request: Request) -> bool:
    return request.method == "GET" and urlparse(request.url).path.endswith("/duplicates")


def duplicate_query(request: Request) -> dict[str, str]:
    """A duplicate check's query parameters, decoded."""
    return dict(parse_qsl(urlparse(request.url).query))


def stub_duplicates(page: Page, matches: list[dict[str, Any]], language: str = "en") -> None:
    """Answer every duplicate read of `language` with `{matches}`, whatever its query string.

    A later stub wins over an earlier one (Playwright runs the newest route first).
    """
    pattern = re.compile(rf"/api/items/{language}/duplicates(\?.*)?$")

    def handle(route: Route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        body = json.dumps({"matches": matches})
        route.fulfill(status=200, content_type="application/json", body=body)

    page.route(pattern, handle)
