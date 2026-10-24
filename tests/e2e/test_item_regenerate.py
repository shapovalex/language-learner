"""Story 5.2: regenerate with Current vs Preview on the editable Item detail (FR-24, NFR-4).

The Item read and Save are `EditableItemApi`, the regeneration route `RegenerateApi`; both are
per-test doubles that check client behavior. Keep current and Use preview change only the local
edit buffer; Save changes alone writes, under the loaded ItemId with audio=keep.
"""

import pytest
from playwright.sync_api import Page, Route, expect

from tests.support.captures_screen import main
from tests.support.items_screen import is_item_save, item_detail_path, item_part, items_back_link
from tests.support.maintain_items_screen import (
    EditableItemApi,
    edit_field,
    save_changes,
    stored_item,
    stub_items,
)
from tests.support.navigation import path_pattern
from tests.support.regenerate_screen import (
    CURRENT,
    KEEP_CURRENT,
    PREVIEW_NOT_SAVED,
    PREVIEW_SENTENCE,
    PREVIEW_VOCABULARY,
    REGENERATE_API,
    USE_PREVIEW,
    RegenerateApi,
    compare_pair,
    pair_button,
    regenerate_button,
    stored_sentence,
    unsaved_chip,
)
from tests.support.unsaved import discard_button, keep_editing_button, unsaved_alert

UNRELATED_EDIT = "my own memory aid, not saved yet"


def back_to_items(page: Page) -> None:
    main(page).get_by_role("link", name=items_back_link("English"), exact=True).click()


@pytest.mark.p0
def test_regenerate_russian_meaning_shows_current_beside_the_preview(page: Page) -> None:
    """[P0] AC-3 compare pair for the Russian meaning; buffer and Anki untouched."""
    row = stored_item()
    api = EditableItemApi(page, row)
    regenerate = RegenerateApi(page, PREVIEW_VOCABULARY)
    api.open(page)
    edit_field(page, "Russian meaning").wait_for()

    regenerate_button(page, "Regenerate Russian meaning").click()
    pair = compare_pair(page, "Russian meaning")

    expect(pair.get_by_text(PREVIEW_VOCABULARY["russian"])).to_be_visible()

    expect(pair).to_contain_text(CURRENT)
    expect(pair).to_contain_text(PREVIEW_NOT_SAVED)
    expect(pair).to_contain_text(row["russian"])
    expect(pair).to_contain_text(PREVIEW_VOCABULARY["russianAlternatives"][0])
    expect(edit_field(page, "Russian meaning")).to_have_value(row["russian"])
    [sent] = regenerate.requests
    assert sent["language"] == "en"
    assert sent["category"] == row["category"]
    assert sent["target"] == row["target"]
    assert "itemId" not in sent
    assert api.saved_payloads == []


@pytest.mark.p0
def test_use_preview_moves_only_the_example_into_the_edit_buffer(page: Page) -> None:
    """[P0] AC-4 the example pair only; the unrelated unsaved edit and ItemId are retained."""
    row = stored_item()
    api = EditableItemApi(page, row)
    RegenerateApi(page, PREVIEW_VOCABULARY)
    api.open(page)
    edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)

    regenerate_button(page, "Regenerate example").click()
    pair_button(compare_pair(page, "Example"), USE_PREVIEW).click()

    expect(edit_field(page, "Example")).to_have_value(PREVIEW_VOCABULARY["example"])

    expect(edit_field(page, "Example in Russian")).to_have_value(
        PREVIEW_VOCABULARY["exampleRussian"]
    )
    expect(edit_field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
    expect(edit_field(page, "Russian meaning")).to_have_value(row["russian"])
    expect(edit_field(page, "Hint")).to_have_value(row["hint"])
    expect(edit_field(page, "Grammar")).to_have_value(row["grammar"])
    expect(edit_field(page, "Part of speech")).to_have_value(row["partOfSpeech"])
    expect(compare_pair(page, "Example")).to_have_count(0)
    expect(unsaved_chip(page, 3)).to_be_visible()
    expect(page).to_have_url(path_pattern(item_detail_path("en", row["itemId"])))
    assert api.saved_payloads == []


@pytest.mark.p1
def test_a_sentence_regenerates_its_note_with_the_same_compare_pair(page: Page) -> None:
    """[P1] AC-5 Regenerate Note; Use preview changes only the Note."""
    row = stored_sentence()
    api = EditableItemApi(page, row, lang="fr")
    regenerate = RegenerateApi(page, PREVIEW_SENTENCE)
    api.open(page)
    edit_field(page, "Note").wait_for()

    regenerate_button(page, "Regenerate Note").click()
    pair_button(compare_pair(page, "Note"), USE_PREVIEW).click()

    expect(edit_field(page, "Note")).to_have_value(PREVIEW_SENTENCE["note"])

    expect(edit_field(page, "Russian meaning")).to_have_value(row["russian"])
    expect(edit_field(page, "Hint")).to_have_value(row["hint"])
    expect(main(page).get_by_role("button", name="Regenerate example")).to_have_count(0)
    [sent] = regenerate.requests
    assert (sent["language"], sent["category"]) == ("fr", "sentence")
    assert api.saved_payloads == []


@pytest.mark.p0
def test_keep_current_discards_the_preview_and_leaves_the_buffer(page: Page) -> None:
    """[P0] AC-6 Keep current: the Example and the unrelated unsaved edit stay as they were."""
    row = stored_item()
    api = EditableItemApi(page, row)
    RegenerateApi(page, PREVIEW_VOCABULARY)
    api.open(page)
    edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)

    regenerate_button(page, "Regenerate example").click()
    pair_button(compare_pair(page, "Example"), KEEP_CURRENT).click()

    expect(compare_pair(page, "Example")).to_have_count(0)

    expect(edit_field(page, "Example")).to_have_value(row["example"])
    expect(edit_field(page, "Example in Russian")).to_have_value(row["exampleRussian"])
    expect(edit_field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
    expect(unsaved_chip(page, 1)).to_be_visible()
    assert api.saved_payloads == []


@pytest.mark.p1
def test_a_failed_regeneration_keeps_the_buffer_and_try_again_shows_the_preview(
    page: Page,
) -> None:
    """[P1] AC-7 the alert with Try again; nothing in the buffer is lost."""
    row = stored_item()
    api = EditableItemApi(page, row)
    regenerate = RegenerateApi(page, PREVIEW_VOCABULARY, error="llm_failed")
    api.open(page)
    edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)

    regenerate_button(page, "Regenerate example").click()
    alert = (
        main(page)
        .get_by_role("alert")
        .filter(has=page.get_by_role("button", name="Try again", exact=True))
    )

    expect(alert).to_be_visible()

    expect(edit_field(page, "Example")).to_have_value(row["example"])
    expect(edit_field(page, "Mnemonic")).to_have_value(UNRELATED_EDIT)
    regenerate.error = None
    alert.get_by_role("button", name="Try again", exact=True).click()
    expect(compare_pair(page, "Example").get_by_text(PREVIEW_VOCABULARY["example"])).to_be_visible()
    expect(alert).to_have_count(0)
    assert len(regenerate.requests) == 2
    assert api.saved_payloads == []


@pytest.mark.p0
def test_save_changes_alone_commits_the_accepted_preview_under_the_same_item_id(
    page: Page,
) -> None:
    """[P0] AC-8 one Save: the accepted Russian meaning plus the unrelated edit, audio=keep."""
    row = stored_item(has_audio=True)
    api = EditableItemApi(page, row)
    RegenerateApi(page, PREVIEW_VOCABULARY)
    api.open(page)
    edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)
    regenerate_button(page, "Regenerate Russian meaning").click()
    pair_button(compare_pair(page, "Russian meaning"), USE_PREVIEW).click()
    writes_before_save = len(api.saved_payloads)

    with page.expect_response(lambda response: is_item_save(response.request)) as saved:
        save_changes(page).click()
    payload = item_part(saved.value.request)

    assert payload["russian"] == PREVIEW_VOCABULARY["russian"]

    assert payload["russianAlternatives"] == PREVIEW_VOCABULARY["russianAlternatives"]
    assert payload["itemId"] == row["itemId"]
    assert payload["audio"] == "keep"
    assert payload["mnemonic"] == UNRELATED_EDIT
    assert payload["target"] == row["target"]
    assert payload["example"] == row["example"]
    assert payload["hint"] == row["hint"]
    assert payload["grammar"] == row["grammar"]
    assert writes_before_save == 0
    assert len(api.saved_payloads) == 1
    expect(main(page).get_by_text("unsaved change")).to_have_count(0)


@pytest.mark.p1
def test_the_edited_target_is_the_one_sent(page: Page) -> None:
    """[P1] AC-3 the request carries the edit buffer's Target, not the loaded one."""
    row = stored_item()
    api = EditableItemApi(page, row)
    regenerate = RegenerateApi(page, PREVIEW_VOCABULARY)
    api.open(page)
    edit_field(page, "Target").fill("jump the gun")

    regenerate_button(page, "Regenerate Russian meaning").click()

    expect(compare_pair(page, "Russian meaning")).to_be_visible()
    [sent] = regenerate.requests
    assert sent["target"] == "jump the gun"
    assert "itemId" not in sent
    expect(edit_field(page, "Target")).to_have_value("jump the gun")


@pytest.mark.p1
def test_a_blank_target_disables_regenerate(page: Page) -> None:
    """[P1] AC-3 no Target, nothing to regenerate from: the buttons are disabled."""
    row = stored_item()
    api = EditableItemApi(page, row)
    regenerate = RegenerateApi(page, PREVIEW_VOCABULARY)
    api.open(page)
    edit_field(page, "Target").fill("  ")

    expect(regenerate_button(page, "Regenerate Russian meaning")).to_be_disabled()
    expect(regenerate_button(page, "Regenerate example")).to_be_disabled()
    assert regenerate.requests == []


@pytest.mark.p1
def test_an_open_preview_is_one_unsaved_change_and_guards_leaving(page: Page) -> None:
    """[P1] AC-6 an unaccepted Preview counts once; Keep editing keeps it, Discard leaves."""
    row = stored_item()
    api = EditableItemApi(page, row)
    stub_items(page, [row])
    RegenerateApi(page, PREVIEW_VOCABULARY)
    api.open(page)

    regenerate_button(page, "Regenerate example").click()
    pair = compare_pair(page, "Example")
    expect(pair).to_be_visible()
    expect(unsaved_chip(page, 1)).to_be_visible()

    back_to_items(page)
    expect(unsaved_alert(page)).to_be_visible()
    keep_editing_button(page).click()
    expect(page).to_have_url(path_pattern(item_detail_path("en", row["itemId"])))
    expect(pair.get_by_text(PREVIEW_VOCABULARY["example"])).to_be_visible()
    expect(unsaved_chip(page, 1)).to_be_visible()

    back_to_items(page)
    discard_button(page).click()
    expect(page).to_have_url(path_pattern("/en/items"))
    assert api.saved_payloads == []


@pytest.mark.p0
def test_save_with_an_unaccepted_preview_sends_the_current_values(page: Page) -> None:
    """[P0] AC-8 an open Preview is never sent by Save; it stays open afterwards."""
    row = stored_item()
    api = EditableItemApi(page, row)
    RegenerateApi(page, PREVIEW_VOCABULARY)
    api.open(page)
    edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)
    regenerate_button(page, "Regenerate Russian meaning").click()
    expect(compare_pair(page, "Russian meaning")).to_be_visible()
    expect(unsaved_chip(page, 2)).to_be_visible()

    with page.expect_response(lambda response: is_item_save(response.request)) as saved:
        save_changes(page).click()
    payload = item_part(saved.value.request)

    assert payload["russian"] == row["russian"]
    assert payload["russianAlternatives"] == row["russianAlternatives"]
    assert payload["mnemonic"] == UNRELATED_EDIT
    assert payload["itemId"] == row["itemId"]
    expect(compare_pair(page, "Russian meaning")).to_be_visible()
    expect(unsaved_chip(page, 1)).to_be_visible()


@pytest.mark.p1
def test_use_preview_on_the_russian_meaning_takes_the_alternatives_one_per_line(
    page: Page,
) -> None:
    """[P1] AC-4 the Russian meaning group: the meaning and its alternatives, one per line."""
    row = stored_item()
    api = EditableItemApi(page, row)
    RegenerateApi(page, PREVIEW_VOCABULARY)
    api.open(page)

    regenerate_button(page, "Regenerate Russian meaning").click()
    pair_button(compare_pair(page, "Russian meaning"), USE_PREVIEW).click()

    expect(edit_field(page, "Russian meaning")).to_have_value(PREVIEW_VOCABULARY["russian"])
    expect(edit_field(page, "Alternatives")).to_have_value(
        "\n".join(PREVIEW_VOCABULARY["russianAlternatives"])
    )
    expect(edit_field(page, "Example")).to_have_value(row["example"])
    expect(regenerate_button(page, "Regenerate Russian meaning")).to_be_focused()
    assert api.saved_payloads == []


@pytest.mark.p1
def test_vocabulary_has_no_regenerate_note_and_sentence_no_regenerate_example(
    page: Page,
) -> None:
    """[P1] AC-5 the button matrix: Vocabulary regenerates its example, a Sentence its Note."""
    row = stored_item()
    EditableItemApi(page, row).open(page)

    expect(regenerate_button(page, "Regenerate Russian meaning")).to_be_visible()
    expect(regenerate_button(page, "Regenerate example")).to_be_visible()
    expect(regenerate_button(page, "Regenerate Note")).to_have_count(0)

    sentence_row = stored_sentence()
    EditableItemApi(page, sentence_row, lang="fr").open(page)
    expect(regenerate_button(page, "Regenerate Russian meaning")).to_be_visible()
    expect(regenerate_button(page, "Regenerate Note")).to_be_visible()
    expect(regenerate_button(page, "Regenerate example")).to_have_count(0)


@pytest.mark.p1
def test_invalid_output_twice_shows_its_copy_and_keeps_the_buffer(page: Page) -> None:
    """[P1] AC-7 llm_invalid_output: "Couldn't regenerate" with the Item-unchanged body."""
    row = stored_item()
    api = EditableItemApi(page, row)
    RegenerateApi(page, PREVIEW_VOCABULARY, error="llm_invalid_output")
    api.open(page)

    regenerate_button(page, "Regenerate Russian meaning").click()
    alert = main(page).get_by_role("alert").filter(has_text="Couldn't regenerate")

    expect(alert).to_contain_text(
        "The model's answer failed the checks twice. Your Item is unchanged."
    )
    expect(alert.get_by_role("button", name="Try again", exact=True)).to_be_focused()
    expect(edit_field(page, "Russian meaning")).to_have_value(row["russian"])
    expect(compare_pair(page, "Russian meaning")).to_have_count(0)
    expect(main(page).get_by_text("unsaved change")).to_have_count(0)


@pytest.mark.p1
def test_a_model_failure_shows_the_unreachable_copy(page: Page) -> None:
    """[P1] AC-7 llm_failed: "Couldn't reach the model" / "Your Item is unchanged."."""
    row = stored_item()
    api = EditableItemApi(page, row)
    RegenerateApi(page, PREVIEW_VOCABULARY, error="llm_failed")
    api.open(page)

    regenerate_button(page, "Regenerate example").click()
    alert = main(page).get_by_role("alert").filter(has_text="Couldn't reach the model")

    expect(alert).to_contain_text("Your Item is unchanged.")


@pytest.mark.p1
def test_a_reply_after_leaving_opens_nothing(page: Page) -> None:
    """[P1] AC-7 a regeneration still in flight when the user leaves opens no Preview."""
    row = stored_item()
    api = EditableItemApi(page, row)
    stub_items(page, [row])
    held: list[Route] = []

    def hold(route: Route) -> None:
        if route.request.method != "POST":
            route.fallback()
            return
        held.append(route)

    page.route(f"**{REGENERATE_API}", hold)
    api.open(page)
    regenerate_button(page, "Regenerate example").click()
    expect(main(page).get_by_role("status").filter(has_text="Writing a Preview")).to_be_visible()
    expect(regenerate_button(page, "Regenerate example")).to_be_disabled()
    expect(regenerate_button(page, "Regenerate example")).to_be_focused()
    expect(regenerate_button(page, "Regenerate Russian meaning")).to_be_disabled()
    assert len(held) == 1

    back_to_items(page)
    expect(page).to_have_url(path_pattern("/en/items"))
    held[0].fulfill(json=PREVIEW_VOCABULARY)

    expect(main(page).get_by_role("link").filter(has_text=row["target"])).to_be_visible()
    expect(compare_pair(page, "Example")).to_have_count(0)
    expect(unsaved_alert(page)).to_have_count(0)
    assert api.saved_payloads == []


@pytest.mark.p1
def test_the_pair_buttons_are_disabled_while_a_save_is_in_flight(page: Page) -> None:
    """[P1] AC-8 Keep current / Use preview wait for the Save, so no choice is lost."""
    row = stored_item()
    api = EditableItemApi(page, row)
    RegenerateApi(page, PREVIEW_VOCABULARY)
    held: list[Route] = []

    def hold(route: Route) -> None:
        if route.request.method != "POST":
            route.fallback()
            return
        held.append(route)

    page.route("**/api/items/en", hold)
    api.open(page)
    edit_field(page, "Mnemonic").fill(UNRELATED_EDIT)
    regenerate_button(page, "Regenerate example").click()
    pair = compare_pair(page, "Example")
    expect(pair).to_be_visible()

    save_changes(page).click()
    expect(pair_button(pair, KEEP_CURRENT)).to_be_disabled()
    expect(pair_button(pair, USE_PREVIEW)).to_be_disabled()
    assert len(held) == 1

    held[0].fallback()
    expect(pair_button(pair, USE_PREVIEW)).to_be_enabled()
    expect(unsaved_chip(page, 1)).to_be_visible()
    assert len(api.saved_payloads) == 1
