"""The Make an Item pane and the Draft editor: copy, locators and the Save request, shared by
the Item E2E tests (tests/e2e/test_make_an_item.py).

The pane is a region named "Make an Item" in Capture detail; the Draft editor is a form named
"Draft" at /captures/<captureId>/new. Its fields are found by the start of their label, so an
"optional" note in the label doesn't matter. `item_part(request)` reads the `item` JSON part of
a Save's multipart body.
"""

import json
import re
from email.parser import BytesParser
from email.policy import HTTP
from typing import Any

from playwright.sync_api import Locator, Page, Request

from tests.support.captures_screen import main

BLANK_DRAFT_API = "/api/drafts/blank"
ITEMS_API = "/api/items/"

MAKE_AN_ITEM = "Make an Item"
USE_AS_IS = "Use as is"
CUSTOM_VALUE = "Custom value"
WRITE_IT_MYSELF = "Write it myself"
CHOOSE_REASON = "Choose a Language and Category."
CUSTOM_REASON = "Enter the custom value."

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
