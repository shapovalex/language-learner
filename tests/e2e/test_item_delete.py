"""Story 5.3 Item deletion journeys (FR-25, AC21, S-Delete).

Network doubles isolate client behavior from Anki; real history deletion remains manual.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.support import viewports
from tests.support.captures_screen import main
from tests.support.delete_item_screen import (
    CARDS,
    CONFIRM,
    NO_UNDO,
    NOT_DELETED,
    NOT_DELETED_BODY,
    PERMANENT,
    DeletableItemApi,
    cancel_button,
    confirm_button,
    delete_button,
    delete_dialog,
)
from tests.support.items_screen import item_detail_path
from tests.support.keys import shift_tab, tab
from tests.support.maintain_items_screen import edit_field, item_row, stored_item
from tests.support.navigation import path_pattern
from tests.support.network import HeldRoute
from tests.support.unsaved import navigate, unsaved_alert


@pytest.mark.p0
def test_delete_names_the_stored_item_and_all_four_cards(page: Page) -> None:
    """[P0] AC-1 Delete opens the reusable confirmation naming Target, Cards and history."""
    row = stored_item()
    api = DeletableItemApi(page, row, stored_item(target="by and large"))
    api.open(page)
    # The deletion is for the persisted Item, even when Target has a local unsaved edit.
    edit_field(page, "Target").fill("an unsaved replacement")

    delete_button(page).click()

    expect(delete_dialog(page, row["target"])).to_be_visible()
    dialog = delete_dialog(page, row["target"])
    expect(dialog).to_contain_text(PERMANENT)
    expect(dialog).to_contain_text(NO_UNDO)
    for card in CARDS:
        expect(dialog.get_by_text(card, exact=True)).to_be_visible()
    expect(confirm_button(page, row["target"])).to_be_visible()
    expect(cancel_button(page, row["target"])).to_be_visible()
    assert api.mutations == []


@pytest.mark.p0
def test_cancel_preserves_edits_and_the_confirmation_traps_keyboard_focus(
    page: Page, browser_name: str
) -> None:
    """[P0] AC-5 Cancel/Escape keep local edits and send no delete, returning focus to Delete."""
    row = stored_item()
    api = DeletableItemApi(page, row, stored_item(target="by and large"))
    api.open(page)
    changed_meaning = "локальное изменение"
    edit_field(page, "Russian meaning").fill(changed_meaning)
    delete_button(page).click()

    cancel_button(page, row["target"]).click()

    expect(delete_dialog(page, row["target"])).to_be_hidden()
    expect(delete_button(page)).to_be_focused()
    expect(edit_field(page, "Russian meaning")).to_have_value(changed_meaning)
    expect(page).to_have_url(path_pattern(item_detail_path("en", row["itemId"])))
    assert api.mutations == []
    delete_button(page).click()
    expect(cancel_button(page, row["target"])).to_be_focused()
    page.keyboard.press(tab(browser_name))
    expect(confirm_button(page, row["target"])).to_be_focused()
    page.keyboard.press(tab(browser_name))
    expect(cancel_button(page, row["target"])).to_be_focused()
    page.keyboard.press(shift_tab(browser_name))
    expect(confirm_button(page, row["target"])).to_be_focused()
    page.keyboard.press("Escape")
    expect(delete_dialog(page, row["target"])).to_be_hidden()
    expect(delete_button(page)).to_be_focused()
    expect(edit_field(page, "Russian meaning")).to_have_value(changed_meaning)
    assert api.mutations == []


@pytest.mark.p0
def test_pending_delete_keeps_the_dialog_disabled_and_ignores_duplicate_submit(page: Page) -> None:
    """[P0] AC-8 Pending DELETE stays in its busy confirmation and cannot submit twice."""
    row = stored_item()
    api = DeletableItemApi(page, row, stored_item(target="by and large"))
    held = HeldRoute(page, api.path, method="DELETE")
    api.open(page)
    delete_button(page).click()

    confirm_button(page, row["target"]).click()

    expect(confirm_button(page, row["target"])).to_be_disabled()
    expect(cancel_button(page, row["target"])).to_be_disabled()
    expect(confirm_button(page, row["target"])).to_have_text(CONFIRM)
    page.keyboard.press("Enter")
    page.keyboard.press("Escape")
    expect(delete_dialog(page, row["target"])).to_be_visible()
    assert len(api.deletes) == 1
    held.fulfill_json(
        {
            "error": {
                "code": "anki_unavailable",
                "message": "Anki isn't reachable.",
                "requestId": "",
            }
        },
        status=503,
    )
    expect(delete_dialog(page, row["target"])).to_be_hidden()
    assert len(api.deletes) == 1


@pytest.mark.p0
def test_failed_delete_retains_the_buffer_and_a_new_confirmation_can_retry(page: Page) -> None:
    """[P0] AC-9 Failed DELETE keeps edits and an inline alert; confirming again retries."""
    row = stored_item()
    other = stored_item(target="by and large")
    api = DeletableItemApi(page, row, other)
    api.delete_status = 503
    api.open(page)
    changed_meaning = "локальное изменение после ошибки"
    edit_field(page, "Russian meaning").fill(changed_meaning)
    delete_button(page).click()

    confirm_button(page, row["target"]).click()

    expect(main(page).get_by_role("alert").filter(has_text=NOT_DELETED)).to_be_visible()
    expect(main(page).get_by_role("alert").filter(has_text=NOT_DELETED)).to_contain_text(
        NOT_DELETED_BODY
    )
    expect(delete_dialog(page, row["target"])).to_be_hidden()
    expect(edit_field(page, "Russian meaning")).to_have_value(changed_meaning)
    expect(page).to_have_url(path_pattern(item_detail_path("en", row["itemId"])))
    assert len(api.deletes) == 1
    api.delete_status = 204
    delete_button(page).click()
    confirm_button(page, row["target"]).click()
    expect(page).to_have_url(path_pattern("/en/items"))
    expect(item_row(page, other["target"])).to_be_visible()
    expect(item_row(page, row["target"])).to_have_count(0)
    assert len(api.deletes) == 2
    assert all(request.url.endswith(api.path) for request in api.deletes)
    assert len(api.mutations) == 2


@pytest.mark.p0
def test_phone_delete_returns_to_a_refreshed_list_without_an_unsaved_prompt(page: Page) -> None:
    """[P0] AC-10 Phone deletion refreshes Items and discards the removed Item's buffer."""
    page.set_viewport_size(viewports.PHONE)
    row = stored_item()
    other = stored_item(target="by and large")
    api = DeletableItemApi(page, row, other)
    api.open(page)
    edit_field(page, "Russian meaning").fill("не сохранять перед удалением")
    delete_button(page).click()

    confirm_button(page, row["target"]).click()

    expect(page).to_have_url(path_pattern("/en/items"))
    expect(item_row(page, other["target"])).to_be_visible()
    expect(item_row(page, row["target"])).to_have_count(0)
    expect(unsaved_alert(page)).to_have_count(0)
    assert api.list_reads == 1
    assert len(api.mutations) == 1
    assert api.mutations[0].method == "DELETE"
    assert api.mutations[0].url.endswith(api.path)


@pytest.mark.p0
def test_desktop_delete_refreshes_the_list_and_preserves_the_other_item(page: Page) -> None:
    """[P0] AC-11 Desktop deletion returns to a newly read Items list with unrelated rows intact."""
    page.set_viewport_size(viewports.DESKTOP)
    row = stored_item()
    other = stored_item(target="by and large")
    api = DeletableItemApi(page, row, other)
    page.goto("/en/items")
    item_row(page, row["target"]).click()
    delete_button(page).click()
    reads_before_delete = api.list_reads

    confirm_button(page, row["target"]).click()

    expect(page).to_have_url(path_pattern("/en/items"))
    expect(item_row(page, other["target"])).to_be_visible()
    expect(item_row(page, row["target"])).to_have_count(0)
    expect(main(page).get_by_role("heading", name="English Items", exact=True)).to_be_visible()
    expect(delete_dialog(page, row["target"])).to_be_hidden()
    assert api.list_reads == reads_before_delete + 1
    assert len(api.mutations) == 1
    assert api.mutations[0].method == "DELETE"
    assert api.mutations[0].url.endswith(api.path)


@pytest.mark.parametrize("failure", ["cancel", "unavailable", "network", "generic"])
def test_cancel_and_failures_preserve_an_open_preview_and_local_edits(page: Page, failure) -> None:
    from tests.support.regenerate_screen import (
        PREVIEW_VOCABULARY,
        RegenerateApi,
        compare_pair,
        regenerate_button,
    )

    row = stored_item()
    api = DeletableItemApi(page, row, stored_item(target="by and large"))
    RegenerateApi(page, PREVIEW_VOCABULARY)
    api.open(page)
    edit_field(page, "Mnemonic").fill("keep this local edit")
    regenerate_button(page, "Regenerate Russian meaning").click()
    pair = compare_pair(page, "Russian meaning")
    expect(pair).to_be_visible()
    if failure == "network":
        page.route(f"**{api.path}", lambda route: route.abort())
    elif failure == "generic":
        page.route(
            f"**{api.path}",
            lambda route: route.fulfill(
                status=409,
                json={
                    "error": {
                        "code": "setup_required",
                        "message": "Run Setup first.",
                        "requestId": "test",
                    }
                },
            ),
        )
    elif failure == "unavailable":
        api.delete_status = 503
    delete_button(page).click()
    if failure == "cancel":
        cancel_button(page, row["target"]).click()
    else:
        confirm_button(page, row["target"]).click()
        alert = main(page).get_by_role("alert").filter(has_text="Not deleted")
        expect(alert).to_be_visible()
        if failure == "network":
            expect(alert).to_contain_text("LanguageLab could not reach the server.")
        elif failure == "generic":
            expect(alert).to_contain_text("Run Setup first.")
    expect(edit_field(page, "Mnemonic")).to_have_value("keep this local edit")
    expect(pair).to_be_visible()
    expect(pair).to_contain_text(PREVIEW_VOCABULARY["russian"])
    expect(delete_button(page)).to_be_focused()
    assert not any(
        request.method == "POST" for request in api.mutations if "/api/items/" in request.url
    )


def test_french_sentence_confirmation_treats_special_target_as_text_and_refreshes_french(
    page: Page,
) -> None:
    from tests.support.regenerate_screen import stored_sentence

    page.set_viewport_size(viewports.PHONE)
    target = '<img src=x onerror="window.targetExecuted=true"> & « Français »'
    row = stored_sentence(target=target)
    api = DeletableItemApi(page, row, stored_sentence(target="une autre phrase"), lang="fr")
    api.open(page)
    delete_button(page).click()
    expect(delete_dialog(page, target)).to_be_visible()
    assert page.evaluate("window.targetExecuted === undefined")
    assert delete_dialog(page, target).locator("img").count() == 0
    box = delete_dialog(page, target).bounding_box()
    assert box is not None and box["width"] <= viewports.PHONE["width"]
    confirm_button(page, target).click()
    expect(page).to_have_url(path_pattern("/fr/items"))
    expect(item_row(page, "une autre phrase")).to_be_visible()
    assert api.list_reads == 1


def test_pending_delete_blocks_back_and_programmatic_navigation_until_its_outcome(
    page: Page,
) -> None:
    row = stored_item()
    api = DeletableItemApi(page, row, stored_item(target="by and large"))
    held = HeldRoute(page, api.path, method="DELETE")
    page.goto("/en/items")
    item_row(page, row["target"]).click()
    delete_button(page).click()
    confirm_button(page, row["target"]).click()
    page.evaluate("history.back()")
    expect(page).to_have_url(path_pattern(item_detail_path("en", row["itemId"])))
    navigate(page, "/fr/items")
    expect(page).to_have_url(path_pattern(item_detail_path("en", row["itemId"])))
    expect(delete_dialog(page, row["target"])).to_be_visible()
    assert len(api.deletes) == 1
    held.fulfill_json(
        {"error": {"code": "anki_unavailable", "message": "Unavailable", "requestId": ""}},
        status=503,
    )
    expect(main(page).get_by_role("alert").filter(has_text=NOT_DELETED)).to_be_visible()
    expect(page).to_have_url(path_pattern(item_detail_path("en", row["itemId"])))
