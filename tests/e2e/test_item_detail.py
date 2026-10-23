"""Story 4.3: the view-only Item detail screen (S-ItemDetail, EXPERIENCE.md; FR-22; AD-13).

Item detail is at /<lang>/items/<itemId>, which Open existing opens. On every mount it reads GET
/api/items/<lang>/<itemId> (AD-13: no cross-screen cache, so a value edited in Anki shows the
next time). It shows the Target as its heading, the Category, and each filled field under the
Draft editor's labels, view-only: no textbox, and no Save changes, Delete or Regenerate (those
are epic-maintain-items'). Its back link is "‹ English Items" or "‹ French Items".

An ItemId Anki doesn't hold shows "This Item isn't in Anki."; any other failed read shows an
inline error alert with Try again, which reads again.

The Item read is stubbed at the network.
"""

from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.support.captures_screen import main
from tests.support.drafts import drafted
from tests.support.items_screen import (
    ITEM_NOT_IN_ANKI,
    TRY_AGAIN,
    item_api,
    item_detail_path,
    items_back_link,
)
from tests.support.navigation import screen_heading
from tests.support.network import stub_api_error, stub_api_json

pytestmark = pytest.mark.skip(reason="red phase (story 4.3): un-skip with the Item detail screen")

ITEM_ID = "3f6b9c2d-1a4e-4b7c-9d8e-2c5a7f1b0e3d"

VOCABULARY_ITEM = {
    **drafted("vocabulary", "jump to conclusions"),
    "russian": "делать поспешные выводы",
    "russianAlternatives": ["торопиться с выводами", "спешить с выводами"],
    "hint": "about evidence",
    "partOfSpeech": "phrase",
    "grammar": "jump to conclusions about sth",
    "example": "Let's not jump to conclusions.",
    "exampleRussian": "Давай не будем делать поспешных выводов.",
    "mnemonic": "a leap over the facts",
}
SENTENCE_ITEM = {
    **drafted("sentence", "Ne tirons pas de conclusions hâtives."),
    "russian": "Не будем делать поспешных выводов.",
    "russianAlternatives": ["Не надо спешить с выводами."],
    "hint": "tirer des conclusions",
    "note": "hâtif, hâtive: agrees with the noun",
}

# Language code, its name, the Item, the Category's name, the values Item detail shows
ITEMS = {
    "en-vocabulary": (
        "en",
        "English",
        VOCABULARY_ITEM,
        "Vocabulary",
        [
            VOCABULARY_ITEM["russian"],
            *VOCABULARY_ITEM["russianAlternatives"],
            VOCABULARY_ITEM["hint"],
            VOCABULARY_ITEM["partOfSpeech"],
            VOCABULARY_ITEM["grammar"],
            VOCABULARY_ITEM["example"],
            VOCABULARY_ITEM["exampleRussian"],
            VOCABULARY_ITEM["mnemonic"],
        ],
    ),
    "fr-sentence": (
        "fr",
        "French",
        SENTENCE_ITEM,
        "Sentence",
        [
            SENTENCE_ITEM["russian"],
            *SENTENCE_ITEM["russianAlternatives"],
            SENTENCE_ITEM["hint"],
            SENTENCE_ITEM["note"],
        ],
    ),
}


@pytest.mark.p0
@pytest.mark.parametrize(
    ("lang", "language", "wire", "category", "values"), ITEMS.values(), ids=ITEMS.keys()
)
def test_item_detail_shows_the_items_values_view_only(
    page: Page, lang: str, language: str, wire: dict[str, Any], category: str, values: list[str]
) -> None:
    """AC-17: /<lang>/items/<itemId> reads the Item and shows the Target as its heading, the
    Category and each field's value, with no editable field and the "‹ <Language> Items" link.
    """
    stub_api_json(page, item_api(lang, ITEM_ID), {"itemId": ITEM_ID, **wire}, method="GET")
    page.goto(item_detail_path(lang, ITEM_ID))

    expect(screen_heading(page)).to_have_text(wire["target"])

    expect(main(page)).to_contain_text(category)
    for value in values:
        expect(main(page)).to_contain_text(value)
    expect(main(page).get_by_role("textbox")).to_have_count(0)
    expect(
        main(page).get_by_role("link", name=items_back_link(language), exact=True)
    ).to_be_visible()


@pytest.mark.p1
def test_item_detail_of_an_item_id_anki_doesnt_hold_says_so(page: Page) -> None:
    """AC-18: a `not_found` read shows "This Item isn't in Anki."."""
    stub_api_error(page, item_api("en", ITEM_ID), status=404, code="not_found", method="GET")
    page.goto(item_detail_path("en", ITEM_ID))

    expect(main(page)).to_contain_text(ITEM_NOT_IN_ANKI)


@pytest.mark.p1
def test_a_failed_item_read_shows_an_alert_and_try_again_reads_again(page: Page) -> None:
    """AC-18: a failed read (Anki down) shows an inline error alert with Try again, which reads
    the Item again and shows it.
    """
    envelope = stub_api_error(
        page, item_api("en", ITEM_ID), status=503, code="anki_unavailable", method="GET"
    )
    page.goto(item_detail_path("en", ITEM_ID))
    alert = main(page).get_by_role("alert")
    expect(alert).to_contain_text(envelope["error"]["message"])

    stub_api_json(
        page, item_api("en", ITEM_ID), {"itemId": ITEM_ID, **VOCABULARY_ITEM}, method="GET"
    )
    with page.expect_request(lambda r: r.url.endswith(item_api("en", ITEM_ID))):
        alert.get_by_role("button", name=TRY_AGAIN, exact=True).click()

    expect(screen_heading(page)).to_have_text(VOCABULARY_ITEM["target"])
