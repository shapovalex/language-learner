"""Story 5.1 editable Item detail: explicit Save, freshness, duplicates and dirty state.

Network doubles assert client transitions and requests. Existing adapter integration tests
and released-wheel acceptance retain responsibility for actual Card/history preservation.
"""

import re
import uuid

import pytest
from playwright.sync_api import Page, expect

from tests.support.captures_screen import main
from tests.support.duplicates import on_wire, sentence
from tests.support.items_screen import (
    CANCEL,
    CREATE_ANYWAY,
    OPEN_EXISTING,
    duplicate_query,
    duplicate_sheet,
    is_duplicate_check,
    is_item_save,
    item_api,
    item_detail_path,
    item_part,
    items_back_link,
    sheet_button,
    stub_duplicates,
)
from tests.support.maintain_items_screen import (
    EditableItemApi,
    edit_field,
    item_row,
    save_changes,
    stored_item,
    stub_item_detail,
    stub_items,
)
from tests.support.navigation import path_pattern
from tests.support.unsaved import discard_button, keep_editing_button, unsaved_alert


def back_to_items(page: Page) -> None:
    main(page).get_by_role("link", name=items_back_link("English"), exact=True).click()


@pytest.mark.p0
def test_save_changes_commits_existing_identity_and_clears_dirty_state(page: Page) -> None:
    """[P0] AC-12 explicit Save sends the edited fields under the original ItemId, audio=keep."""
    row = stored_item(has_audio=True)
    api = EditableItemApi(page, row)
    stub_items(page, [row])
    stub_duplicates(page, [])
    api.open(page)
    changed_meaning = "поспешить с выводами"
    edit_field(page, "Russian meaning").fill(changed_meaning)
    edit_field(page, "Alternatives").fill("торопиться\nспешить")
    edit_field(page, "Example").fill("Do not jump to conclusions.")
    edit_field(page, "Example in Russian").fill("Не делай поспешных выводов.")
    edit_field(page, "Mnemonic").fill("Edited memory aid")
    writes_before_save = len(api.saved_payloads)

    with page.expect_response(lambda response: is_item_save(response.request)) as saved:
        save_changes(page).click()
    payload = item_part(saved.value.request)

    assert payload["itemId"] == row["itemId"]

    assert saved.value.status == 200
    assert payload["audio"] == "keep"
    assert payload["russian"] == changed_meaning
    assert payload["russianAlternatives"] == ["торопиться", "спешить"]
    assert payload["example"] == "Do not jump to conclusions."
    assert payload["exampleRussian"] == "Не делай поспешных выводов."
    assert payload["mnemonic"] == "Edited memory aid"
    assert payload["category"] == row["category"]
    assert writes_before_save == 0
    assert len(api.saved_payloads) == 1
    back_to_items(page)
    expect(unsaved_alert(page)).to_have_count(0)
    expect(page).to_have_url(path_pattern("/en/items"))


@pytest.mark.p0
def test_reopening_reads_the_current_item_instead_of_the_prior_buffer(page: Page) -> None:
    """[P0] AC-13 reopen refreshes the editor from Anki even when the list has stale values."""
    row = stored_item()
    api = EditableItemApi(page, row)
    stub_items(page, [row])
    api.open(page)
    edit_field(page, "Russian meaning").wait_for()
    back_to_items(page)
    # Simulate an edit performed directly in Anki, outside LanguageLab's editor.
    api.current = {**api.current, "russian": "прямое изменение в Anki"}
    with page.expect_request(lambda request: request.url.endswith(item_api("en", row["itemId"]))):
        item_row(page, row["target"]).click()

    expect(edit_field(page, "Russian meaning")).to_have_value("прямое изменение в Anki")

    assert api.saved_payloads == []


@pytest.mark.p0
def test_changed_target_rechecks_and_create_anyway_keeps_the_edited_item_id(page: Page) -> None:
    """[P0] AC-14 Cancel retains edits; another Target rechecks; Create anyway updates self."""
    row = stored_item()
    match = stored_item(target="leap to conclusions")
    api = EditableItemApi(page, row)
    stub_duplicates(page, [match])
    api.open(page)
    edit_field(page, "Target").fill(match["target"])
    with page.expect_request(is_duplicate_check) as first:
        save_changes(page).click()

    assert duplicate_query(first.value)["itemId"] == row["itemId"]

    assert duplicate_query(first.value)["target"] == match["target"]
    assert duplicate_query(first.value)["category"] == row["category"]
    expect(duplicate_sheet(page)).to_be_visible()
    assert api.saved_payloads == []
    sheet_button(page, CANCEL).click()
    expect(edit_field(page, "Target")).to_have_value(match["target"])
    changed_again = "Leap to conclusions!"
    edit_field(page, "Target").fill(changed_again)
    with page.expect_request(is_duplicate_check) as second:
        save_changes(page).click()
    assert duplicate_query(second.value)["target"] == changed_again
    assert duplicate_query(second.value)["itemId"] == row["itemId"]
    with page.expect_response(lambda response: is_item_save(response.request)) as saved:
        sheet_button(page, CREATE_ANYWAY).click()
    payload = item_part(saved.value.request)
    assert payload["itemId"] == row["itemId"]
    assert payload["itemId"] != match["itemId"]
    assert payload["target"] == changed_again
    assert len(api.saved_payloads) == 1


@pytest.mark.p0
def test_open_existing_guards_the_unsaved_edit_before_opening_the_match(page: Page) -> None:
    """[P0] AC-15 Keep editing retains self; Discard opens the match without saving self."""
    row = stored_item()
    match = stored_item(target="leap to conclusions")
    api = EditableItemApi(page, row)
    stub_item_detail(page, match)
    stub_duplicates(page, [match])
    api.open(page)
    edit_field(page, "Target").fill(match["target"])
    save_changes(page).click()
    sheet_button(page, OPEN_EXISTING).click()

    expect(unsaved_alert(page)).to_be_visible()

    keep_editing_button(page).click()
    expect(page).to_have_url(path_pattern(item_detail_path("en", row["itemId"])))
    expect(edit_field(page, "Target")).to_have_value(match["target"])
    sheet_button(page, OPEN_EXISTING).click()
    discard_button(page).click()
    expect(page).to_have_url(path_pattern(item_detail_path("en", match["itemId"])))
    expect(edit_field(page, "Target")).to_have_value(match["target"])
    assert api.saved_payloads == []
    assert api.current == api.original


@pytest.mark.p0
def test_failed_save_keeps_edits_and_leave_guard_then_retries_the_same_item(page: Page) -> None:
    """[P0] AC-16 failed Save keeps the buffer dirty and retry commits that same ItemId."""
    row = stored_item(has_audio=True)
    api = EditableItemApi(page, row)
    api.save_status = 503
    stub_items(page, [row])
    stub_duplicates(page, [])
    api.open(page)
    changed = "редактирование после ошибки"
    edit_field(page, "Russian meaning").fill(changed)
    with page.expect_response(lambda response: is_item_save(response.request)):
        save_changes(page).click()

    expect(edit_field(page, "Russian meaning")).to_have_value(changed)

    expect(main(page).get_by_role("alert")).to_be_visible()
    assert api.current == api.original
    back_to_items(page)
    expect(unsaved_alert(page)).to_be_visible()
    keep_editing_button(page).click()
    expect(edit_field(page, "Russian meaning")).to_have_value(changed)
    api.save_status = 200
    with page.expect_response(lambda response: is_item_save(response.request)) as retried:
        save_changes(page).click()
    assert item_part(retried.value.request)["itemId"] == row["itemId"]
    assert item_part(retried.value.request)["audio"] == "keep"
    assert api.current["russian"] == changed
    assert [payload["itemId"] for payload in api.saved_payloads] == [row["itemId"]] * 2
    back_to_items(page)
    expect(unsaved_alert(page)).to_have_count(0)
    expect(page).to_have_url(path_pattern("/en/items"))


@pytest.mark.p1
def test_a_french_sentence_saves_its_note_under_its_item_id(page: Page) -> None:
    """[P1] AC-12 a Sentence edits its own fields, the Note included, and saves in French."""
    row = {**on_wire(str(uuid.uuid4()), sentence()), "hasAudio": False}
    api = EditableItemApi(page, row, lang="fr")
    api.open(page)
    edit_field(page, "Note").fill("hâtif, hâtive: s'accorde avec le nom")
    edit_field(page, "Hint").fill("tirer des conclusions")

    with page.expect_response(lambda response: is_item_save(response.request)) as saved:
        save_changes(page).click()

    payload = item_part(saved.value.request)
    assert saved.value.request.url.endswith("/api/items/fr")
    assert payload["itemId"] == row["itemId"]
    assert payload["category"] == "sentence"
    assert payload["audio"] == "keep"
    assert payload["note"] == "hâtif, hâtive: s'accorde avec le nom"
    assert payload["hint"] == "tirer des conclusions"
    assert "example" not in payload
    expect(main(page).get_by_text(re.compile("unsaved change"))).to_have_count(0)


@pytest.mark.p1
def test_returning_a_field_to_its_loaded_value_clears_the_unsaved_state(page: Page) -> None:
    """[P1] AC-16 the unsaved chip counts changed fields; back to the loaded value is clean."""
    row = stored_item()
    api = EditableItemApi(page, row)
    stub_items(page, [row])
    api.open(page)
    meaning = edit_field(page, "Russian meaning")
    meaning.fill("другое значение")
    edit_field(page, "Hint").fill("another hint")

    expect(main(page).get_by_text("2 unsaved changes", exact=True)).to_be_visible()

    meaning.fill(row["russian"])
    expect(main(page).get_by_text("1 unsaved change", exact=True)).to_be_visible()
    edit_field(page, "Hint").fill(row["hint"])
    expect(main(page).get_by_text("1 unsaved change", exact=True)).to_have_count(0)
    back_to_items(page)
    expect(unsaved_alert(page)).to_have_count(0)
    expect(page).to_have_url(path_pattern("/en/items"))
    assert api.saved_payloads == []
