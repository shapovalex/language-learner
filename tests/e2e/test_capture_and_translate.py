"""Capture and translate on the Captures screen (plan capture-and-translate).

- **Happy path.** "Capture and translate" saves the compose text like Save Capture, then asks
  POST /api/helpers/translate in the picker's Language; the card shows "original → Russian" and
  the Capture is in the list.
- **Picker.** English by default; a choice survives a reload; blocked storage falls back to
  English and the choice still works for the session.
- **Failures.** A failed save is Save Capture's alert and asks no translation; its Try again
  saves then translates. A failed translation keeps the Capture; its Try again asks only the
  translation, with no second Capture.

Desktop Captures on the live server; the translate route is the per-test `TranslateApi`.
"""

import uuid

import pytest
from playwright.sync_api import Page, expect

from tests.support import viewports
from tests.support.captures_screen import API, CAPTURES_PATH, compose_box, main, rows
from tests.support.navigation import path_pattern
from tests.support.network import HeldRoute, record_json_bodies, stub_api_error
from tests.support.translate_screen import (
    CAPTURE_LANGUAGE_KEY,
    NOT_TRANSLATED,
    PHRASE,
    RUSSIAN,
    TranslateApi,
    language_choice,
    translate_button,
    translation,
    translation_alert,
)

NOT_SAVED = "Not saved — Anki isn't reachable"
TRY_AGAIN = "Try again"


def open_captures(page: Page) -> None:
    page.set_viewport_size(viewports.DESKTOP)
    page.goto(CAPTURES_PATH)


def unique(text: str = PHRASE) -> str:
    """`text` tagged for this test: the live server's Captures outlive a test."""
    return f"{text} #{uuid.uuid4().hex[:8]}"


def capture_and_translate(page: Page, text: str = PHRASE) -> None:
    compose_box(page).fill(text)
    translate_button(page).click()


@pytest.mark.p0
def test_capture_and_translate_saves_then_shows_the_russian(page: Page) -> None:
    """[P0] HAPPY_PATH: the Capture is saved and listed, the box cleared, and the card shows
    "jump to conclusions → делать поспешные выводы"; the request is in English.
    """
    text = unique()
    saves = record_json_bodies(page, API)
    api = TranslateApi(page)
    open_captures(page)

    capture_and_translate(page, text)

    expect(translation(page)).to_have_text(f"{text} → {RUSSIAN}")
    expect(compose_box(page)).to_have_value("")
    expect(rows(page).filter(has_text=text)).to_have_count(1)
    assert [body["text"] for body in saves] == [text]
    assert api.requests == [{"language": "en", "target": text}]
    expect(page).to_have_url(path_pattern(CAPTURES_PATH))


@pytest.mark.p0
def test_the_picker_defaults_to_english_and_remembers_french(page: Page) -> None:
    """[P0] AC fresh browser shows English; PICKER_CHANGED French survives a reload and the
    next request sends `language: "fr"`.
    """
    api = TranslateApi(page)
    open_captures(page)
    expect(language_choice(page, "English")).to_have_attribute("aria-pressed", "true")
    expect(language_choice(page, "French")).to_have_attribute("aria-pressed", "false")

    language_choice(page, "French").click()
    expect(language_choice(page, "French")).to_have_attribute("aria-pressed", "true")
    page.reload()

    expect(language_choice(page, "French")).to_have_attribute("aria-pressed", "true")
    assert page.evaluate(f"localStorage.getItem('{CAPTURE_LANGUAGE_KEY}')") == "fr"
    capture_and_translate(page, "tirer des conclusions hâtives")
    expect(translation(page)).to_be_visible()
    assert api.requests == [{"language": "fr", "target": "tirer des conclusions hâtives"}]


@pytest.mark.p1
@pytest.mark.parametrize("stored", ["de", ""])
def test_an_unknown_stored_language_falls_back_to_english(page: Page, stored: str) -> None:
    """[P1] an unknown stored value shows English."""
    page.add_init_script(f"localStorage.setItem('{CAPTURE_LANGUAGE_KEY}', '{stored}')")
    open_captures(page)
    expect(language_choice(page, "English")).to_have_attribute("aria-pressed", "true")


@pytest.mark.p1
def test_blocked_storage_shows_english_and_the_choice_works(page: Page) -> None:
    """[P1] STORAGE_BLOCKED: English shows; picking French works for the session."""
    page.add_init_script("""Object.defineProperty(window, 'localStorage', {get() {
      throw new DOMException('denied', 'SecurityError');
    }});""")
    api = TranslateApi(page)
    open_captures(page)
    expect(language_choice(page, "English")).to_have_attribute("aria-pressed", "true")

    language_choice(page, "French").click()
    capture_and_translate(page)

    expect(translation(page)).to_be_visible()
    assert api.requests == [{"language": "fr", "target": PHRASE}]


@pytest.mark.p1
def test_the_button_follows_save_captures_enabled_rule(page: Page) -> None:
    """[P1] disabled while the box is blank."""
    open_captures(page)
    expect(translate_button(page)).to_be_disabled()
    compose_box(page).fill("   ")
    expect(translate_button(page)).to_be_disabled()
    compose_box(page).fill(PHRASE)
    expect(translate_button(page)).to_be_enabled()


@pytest.mark.p0
def test_a_failed_save_asks_no_translation_and_try_again_saves_then_translates(
    page: Page,
) -> None:
    """[P0] SAVE_FAILS: Save Capture's alert, the text kept, no translate request; Try again
    (with Anki back) saves then translates.
    """
    stub_api_error(page, API, status=503, code="anki_unavailable", method="POST")
    api = TranslateApi(page)
    open_captures(page)

    capture_and_translate(page)

    alert = main(page).get_by_role("alert").filter(has_text=NOT_SAVED)
    expect(alert).to_be_visible()
    expect(compose_box(page)).to_have_value(PHRASE)
    assert api.requests == []

    page.unroute(f"**{API}")
    alert.get_by_role("button", name=TRY_AGAIN, exact=True).click()

    expect(translation(page)).to_have_text(f"{PHRASE} → {RUSSIAN}")
    expect(compose_box(page)).to_have_value("")
    assert api.requests == [{"language": "en", "target": PHRASE}]


@pytest.mark.p0
def test_a_failed_translation_keeps_the_capture_and_try_again_asks_only_it(page: Page) -> None:
    """[P0] TRANSLATE_FAILS: the Capture is saved and listed, the card shows "Couldn't
    translate"; Try again re-asks only the translation and makes no second Capture.
    """
    text = unique()
    saves = record_json_bodies(page, API)
    api = TranslateApi(page, error="llm_failed")
    open_captures(page)

    capture_and_translate(page, text)

    alert = translation_alert(page)
    expect(alert).to_contain_text(NOT_TRANSLATED)
    expect(rows(page).filter(has_text=text)).to_have_count(1)
    expect(compose_box(page)).to_have_value("")

    api.error = None
    alert.get_by_role("button", name=TRY_AGAIN, exact=True).click()

    expect(translation(page)).to_have_text(f"{text} → {RUSSIAN}")
    expect(translation_alert(page)).to_have_count(0)
    assert api.requests == [{"language": "en", "target": text}] * 2
    assert len(saves) == 1
    expect(rows(page).filter(has_text=text)).to_have_count(1)


@pytest.mark.p1
def test_editing_the_text_clears_the_translation(page: Page) -> None:
    """[P1] the translation is shown only until the text is edited (AD-13)."""
    TranslateApi(page)
    open_captures(page)
    capture_and_translate(page)
    expect(translation(page)).to_be_visible()

    compose_box(page).fill("un rendez-vous")

    expect(translation(page)).to_have_count(0)


@pytest.mark.p1
def test_text_typed_while_the_save_is_in_flight_is_not_translated(page: Page) -> None:
    """[P1] text edited during the save is a new composition: it stays in the box, and no
    translation is asked or shown for the saved text.
    """
    held = HeldRoute(page, API, method="POST")
    saves = record_json_bodies(page, API)
    api = TranslateApi(page)
    open_captures(page)
    capture_and_translate(page)

    compose_box(page).fill("un rendez-vous")
    held.fulfill_json(
        {"captureId": saves[0]["captureId"], "text": PHRASE, "createdAt": "2026-11-14T21:14:05Z"},
        status=201,
    )

    expect(rows(page).filter(has_text=PHRASE).first).to_be_visible()
    expect(compose_box(page)).to_have_value("un rendez-vous")
    expect(main(page).locator(".compose-translation-slot")).to_be_empty()
    assert api.requests == []
