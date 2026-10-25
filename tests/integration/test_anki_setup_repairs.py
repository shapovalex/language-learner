"""Story 2.11: opt-in repairs for leftovers in the Anki adapter (AD-3, AD-4, AD-7, AD-9).

Setup reports three kinds of leftover under the Prefix and offers each as an opt-in repair row,
one row per resource (decided with the user, 2026-10-21):

- **Orphan media** (`orphanMedia`, named by its file name): an AD-7 media name that no managed
  note's `Audio` field references, read through the codec. Repaired by `deleteMediaFile`.
- **A misplaced managed card** (`misplacedCard`, named by its card id): a card of a manifest
  note type in a deck other than `manifest.card_deck(note type, ord)`. Repaired by
  `changeDeck` to that deck.
- **An unsuspended Capture card** (`unsuspendedCard`, named by its card id). Repaired by
  `suspend`.

Rows are offered in `SetupPreview.repairs`, unchecked. They stay out of `items`, the plan hash
and the SetupState, so leftovers never gate feature writes. `setup_apply(plan_hash, repairs=)`
takes the checked rows by key (`"<kind>:<name>"`): only those enter the plan and its hash,
`plan_hash((*items, *checked))`, and only those are repaired. Non-managed notes and decks stay
read-only.

Anki is the in-memory collection in tests/support/anki_state.py, with its cards and media.
"""

from collections.abc import Iterable
from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.guard import PrefixGuard
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import build_manifest
from language_lab.adapters.anki.setup_gate import SetupGate
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, SetupState, plan_hash
from language_lab.features.setup.service import SetupService
from tests.fakes.sync_requester import FakeSyncRequester
from tests.support.aio import run, settle
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay
from tests.support.anki_state import (
    Collection,
    add_card,
    add_note,
    collection_replies,
    managed_collection,
    managed_note,
    media_name,
    sent_writes,
)
from tests.support.clock import bounded

PREFIX = "LanguageLab"
DEV = "LanguageLabDev"
MANIFEST = build_manifest(PREFIX)

VOCABULARY = f"{PREFIX} English Vocabulary"
CAPTURE = f"{PREFIX} Capture"
UNDERSTAND = 0
PRODUCE = 1
PRONOUNCE = 3

ORPHAN_MEDIA = "orphanMedia"
MISPLACED_CARD = "misplacedCard"
UNSUSPENDED_CARD = "unsuspendedCard"


def key(kind: str, name: object) -> str:
    return f"{kind}:{name}"


def keys(rows: Iterable[PlanItem]) -> set[str]:
    return {f"{r.kind}:{r.name}" for r in rows}


def wired(collection: Collection, *, list_all_media: bool = False) -> tuple[Any, AnkiConnectReplay]:
    """The real client and store over `collection`, writes answered. Returns (store, replay).

    `list_all_media=True` answers `getMediaFilesNames` with every media name, whatever the
    pattern, so the adapter's own AD-7 filter is what decides.
    """
    gate = SetupGate(MANIFEST)
    replies = collection_replies(collection, writes=True)
    if list_all_media:
        multi = replies["multi"]

        def unfiltered(body: Any) -> Any:
            reply = multi(body)
            for index, inner in enumerate(body["params"]["actions"]):
                if inner["action"] == "getMediaFilesNames":
                    reply["result"][index] = {"result": sorted(collection.media), "error": None}
            return reply

        replies["multi"] = unfiltered
    replay = AnkiConnectReplay(replies)
    client = AnkiConnectClient(
        ANKI_URL, transport=replay.transport, guard=PrefixGuard(MANIFEST), gate=gate
    )
    return AnkiConnectStore(client, AnkiLock(), manifest=MANIFEST, gate=gate), replay


def vocabulary_note(collection: Collection, audio: str = "") -> int:
    note_id = managed_note(collection, MANIFEST, VOCABULARY, str(MANIFEST.schema_version))
    collection.notes[note_id].fields["Audio"] = audio
    return note_id


def capture_note(collection: Collection) -> int:
    return managed_note(collection, MANIFEST, CAPTURE, str(MANIFEST.schema_version))


def well_placed_cards(collection: Collection, note_id: int) -> list[int]:
    """Every card of an English Vocabulary note, each in its manifest deck."""
    return [
        add_card(collection, note_id, ord, MANIFEST.card_deck(VOCABULARY, ord))
        for ord in (0, 1, 2, 3)
    ]


class Leftovers:
    """A set-up Anki holding one leftover of each kind, beside content that is in order."""

    def __init__(self) -> None:
        self.collection = c = managed_collection(MANIFEST)
        self.used_media = media_name(PREFIX)
        self.orphan_media = media_name(PREFIX)
        c.media |= {self.used_media, self.orphan_media}
        note = vocabulary_note(c, audio=f"[sound:{self.used_media}]")
        self.placed = well_placed_cards(c, note)
        other = vocabulary_note(c)
        self.misplaced = add_card(c, other, PRODUCE, MANIFEST.card_deck(VOCABULARY, UNDERSTAND))
        self.capture = add_card(c, capture_note(c), 0, MANIFEST.card_deck(CAPTURE, 0))

    def all_keys(self) -> list[str]:
        return [
            key(ORPHAN_MEDIA, self.orphan_media),
            key(MISPLACED_CARD, self.misplaced),
            key(UNSUSPENDED_CARD, self.capture),
        ]


@pytest.mark.p0
def test_orphan_media_previews_as_an_opt_in_repair_row() -> None:
    """AC-1: an AD-7 media file no managed note's `Audio` references, read through the codec,
    is offered as an `orphanMedia` row; a referenced one and another Prefix's are not.
    """
    collection = managed_collection(MANIFEST)
    orphan, wrapped, plain, dev = (
        media_name(PREFIX),
        media_name(PREFIX),
        media_name(PREFIX),
        media_name(DEV),
    )
    collection.media |= {orphan, wrapped, plain, dev, "_cards.css", "LanguageLab_notes.mp3"}
    vocabulary_note(collection, audio=f"<div>[sound:{wrapped}]</div>")  # editor markup
    vocabulary_note(collection, audio=f"[sound:{plain}]")
    store, _ = wired(collection, list_all_media=True)

    preview = run(store.setup_preview())

    assert keys(preview.repairs) == {key(ORPHAN_MEDIA, orphan)}
    assert preview.items == ()


@pytest.mark.p0
def test_a_managed_card_in_the_wrong_deck_previews_as_an_opt_in_repair_row() -> None:
    """AC-2: a managed card outside `card_deck(note type, ord)` is offered as a `misplacedCard`
    row named by its card id; cards in their manifest deck are not.
    """
    collection = managed_collection(MANIFEST)
    note = vocabulary_note(collection)
    in_place = add_card(collection, note, UNDERSTAND, MANIFEST.card_deck(VOCABULARY, UNDERSTAND))
    produce = add_card(collection, note, PRODUCE, MANIFEST.card_deck(VOCABULARY, UNDERSTAND))
    pronounce = add_card(collection, note, PRONOUNCE, MANIFEST.card_deck(VOCABULARY, PRODUCE))
    moved_out = add_card(collection, vocabulary_note(collection), UNDERSTAND, "Default")
    store, _ = wired(collection)

    preview = run(store.setup_preview())

    assert keys(preview.repairs) == {
        key(MISPLACED_CARD, produce),
        key(MISPLACED_CARD, pronounce),
        key(MISPLACED_CARD, moved_out),
    }
    assert key(MISPLACED_CARD, in_place) not in keys(preview.repairs)


@pytest.mark.p0
def test_an_unsuspended_capture_card_previews_as_an_opt_in_repair_row() -> None:
    """AC-3: an unsuspended Capture card is offered as an `unsuspendedCard` row; a suspended
    Capture card and an unsuspended Exercise card are not.
    """
    collection = managed_collection(MANIFEST)
    captures = MANIFEST.card_deck(CAPTURE, 0)
    unsuspended = add_card(collection, capture_note(collection), 0, captures)
    add_card(collection, capture_note(collection), 0, captures, suspended=True)
    well_placed_cards(collection, vocabulary_note(collection))
    store, _ = wired(collection)

    preview = run(store.setup_preview())

    assert keys(preview.repairs) == {key(UNSUSPENDED_CARD, unsuspended)}


@pytest.mark.p0
def test_opt_in_rows_stay_out_of_the_plan_its_hash_and_the_setup_state() -> None:
    """AC-6: with only leftovers, the plan is empty, it hashes as an empty plan, and the
    SetupState is `ready`, so leftovers never gate feature writes.
    """
    leftovers = Leftovers()
    store, _ = wired(leftovers.collection)

    preview = run(store.setup_preview())

    assert preview.items == ()
    assert len(preview.repairs) == 3
    assert preview.state is SetupState.READY


@pytest.mark.p0
def test_non_managed_notes_and_decks_stay_read_only() -> None:
    """AC-8: a note of a non-manifest note type, whose unsuspended card sits in a managed deck,
    and a deck under the Prefix the manifest doesn't declare get no repair row, and an apply
    with every offered row checked never touches them.
    """
    leftovers = Leftovers()
    collection = leftovers.collection
    collection.decks[f"{PREFIX}::Old"] = "Default"
    basic = add_note(collection, "Basic", {"Front": "a", "Back": "b"})
    stray = add_card(collection, basic, 0, MANIFEST.card_deck(CAPTURE, 0))
    parked = add_card(collection, basic, 1, f"{PREFIX}::Old")
    store, _ = wired(collection)

    preview = run(store.setup_preview())

    strays = {key(k, card) for k in (MISPLACED_CARD, UNSUSPENDED_CARD) for card in (stray, parked)}
    assert not strays & keys(preview.repairs)
    checked = leftovers.all_keys()
    run(store.setup_apply(plan_hash((*preview.items, *preview.repairs)), repairs=checked))
    assert (collection.cards[stray].deck, collection.cards[stray].suspended) == (
        MANIFEST.card_deck(CAPTURE, 0),
        False,
    )
    assert collection.cards[parked].deck == f"{PREFIX}::Old"
    assert f"{PREFIX}::Old" in collection.decks


@pytest.mark.p0
def test_applying_without_checking_a_repair_changes_nothing() -> None:
    """AC-9: an apply of the unchecked plan sends no write, and every leftover stays."""
    leftovers = Leftovers()
    store, replay = wired(leftovers.collection)
    preview = run(store.setup_preview())

    verified = run(store.setup_apply(plan_hash(preview.items), repairs=()))

    assert sent_writes(replay.sent) == []
    assert keys(verified.repairs) == set(leftovers.all_keys())


@pytest.mark.p0
@pytest.mark.parametrize(
    ("kind", "write"),
    [
        (ORPHAN_MEDIA, "deleteMediaFile"),
        (MISPLACED_CARD, "changeDeck"),
        (UNSUSPENDED_CARD, "suspend"),
    ],
)
def test_checking_one_repair_changes_exactly_that_resource(kind: str, write: str) -> None:
    """AC-10: with one row checked, the apply sends that one repair's write, the resource is
    repaired, and every other leftover stays offered.
    """
    leftovers = Leftovers()
    collection = leftovers.collection
    store, replay = wired(collection)
    preview = run(store.setup_preview())
    chosen = next(k for k in leftovers.all_keys() if k.startswith(f"{kind}:"))
    checked = [r for r in preview.repairs if f"{r.kind}:{r.name}" == chosen]

    verified = run(store.setup_apply(plan_hash((*preview.items, *checked)), repairs=[chosen]))

    assert sent_writes(replay.sent) == [write]
    assert keys(verified.repairs) == set(leftovers.all_keys()) - {chosen}
    assert leftovers.used_media in collection.media
    assert [collection.cards[c].deck for c in leftovers.placed] == [
        MANIFEST.card_deck(VOCABULARY, ord) for ord in (0, 1, 2, 3)
    ]
    if kind == ORPHAN_MEDIA:
        assert leftovers.orphan_media not in collection.media
    elif kind == MISPLACED_CARD:
        assert collection.cards[leftovers.misplaced].deck == MANIFEST.card_deck(VOCABULARY, PRODUCE)
    else:
        assert collection.cards[leftovers.capture].suspended is True


@pytest.mark.p0
def test_a_checked_repair_must_be_confirmed_by_the_hash_that_includes_it() -> None:
    """AC-11: checking a row changes the hash, so an apply that checks a row under the
    unchecked plan's hash is refused with `plan_changed` before any write.
    """
    leftovers = Leftovers()
    store, replay = wired(leftovers.collection)
    preview = run(store.setup_preview())
    chosen = key(ORPHAN_MEDIA, leftovers.orphan_media)

    outcome = settle(bounded(store.setup_apply(plan_hash(preview.items), repairs=[chosen])))

    assert isinstance(outcome, AppError) and outcome.code is ErrorCode.PLAN_CHANGED
    assert sent_writes(replay.sent) == []
    assert leftovers.orphan_media in leftovers.collection.media


# ---- Secondary branches (P1) -------------------------------------------------------------


def wired_over(replies: dict[str, Any]) -> tuple[Any, AnkiConnectReplay]:
    """As `wired()`, over replies a test has changed. Returns (store, replay)."""
    gate = SetupGate(MANIFEST)
    replay = AnkiConnectReplay(replies)
    client = AnkiConnectClient(
        ANKI_URL, transport=replay.transport, guard=PrefixGuard(MANIFEST), gate=gate
    )
    return AnkiConnectStore(client, AnkiLock(), manifest=MANIFEST, gate=gate), replay


@pytest.mark.p1
def test_an_audio_field_with_two_sound_tags_references_both() -> None:
    """AC-1: every `[sound:]` tag of an `Audio` field counts, not only the first."""
    collection = managed_collection(MANIFEST)
    first, second, orphan = media_name(PREFIX), media_name(PREFIX), media_name(PREFIX)
    collection.media |= {first, second, orphan}
    vocabulary_note(collection, audio=f"[sound:{first}]<br>[sound:{second}]")
    store, _ = wired(collection)

    preview = run(store.setup_preview())

    assert keys(preview.repairs) == {key(ORPHAN_MEDIA, orphan)}


@pytest.mark.p1
def test_a_media_name_in_another_case_is_not_offered() -> None:
    """AC-1: AD-7 names are lowercase (spike 2.2: `storeMediaFile` lowercases). A name in
    another case isn't offered, since the guard couldn't delete it. A lowercase leftover of a
    failed v0.8.0 Save is.
    """
    collection = managed_collection(MANIFEST)
    orphan = media_name(PREFIX)
    item_id, digest = orphan.removeprefix(f"{PREFIX.lower()}_").removesuffix(".mp3").split("_")
    upper_digest = f"{PREFIX.lower()}_{item_id}_{digest.upper()}.mp3"
    mixed_prefix = f"{PREFIX}_{item_id}_{digest}.mp3"  # what v0.8.0 requested
    collection.media |= {orphan, upper_digest, mixed_prefix}
    store, _ = wired(collection, list_all_media=True)  # the listing doesn't filter them out

    preview = run(store.setup_preview())

    assert keys(preview.repairs) == {key(ORPHAN_MEDIA, orphan)}


@pytest.mark.p1
def test_a_misplaced_capture_card_belongs_in_captures() -> None:
    """AC-2: a suspended Capture card outside Captures is offered as misplaced, back to
    `<Prefix>::Captures`, with its detail.
    """
    collection = managed_collection(MANIFEST)
    card = add_card(collection, capture_note(collection), 0, "Default", suspended=True)
    store, _ = wired(collection)

    preview = run(store.setup_preview())

    assert keys(preview.repairs) == {key(MISPLACED_CARD, card)}
    assert dict(preview.repairs[0].detail) == {
        "noteType": CAPTURE,
        "card": next(nt for nt in MANIFEST.note_types if nt.name == CAPTURE).templates[0].name,
        "deck": "Default",
        "expectedDeck": f"{PREFIX}::Captures",
    }


@pytest.mark.p1
def test_a_card_in_a_deck_that_no_longer_exists_is_misplaced_and_repairable() -> None:
    """AC-2/AC-10: a card whose deck vanished is offered, and `changeDeck` puts it back."""
    collection = managed_collection(MANIFEST)
    collection.decks["Gone"] = "Default"
    card = add_card(collection, vocabulary_note(collection), UNDERSTAND, "Gone")
    del collection.decks["Gone"]
    store, replay = wired(collection)
    preview = run(store.setup_preview())
    row = key(MISPLACED_CARD, card)

    verified = run(store.setup_apply(plan_hash((*preview.items, *preview.repairs)), [row]))

    assert keys(preview.repairs) == {row}
    assert sent_writes(replay.sent) == ["changeDeck"]
    assert collection.cards[card].deck == MANIFEST.card_deck(VOCABULARY, UNDERSTAND)
    assert verified.repairs == ()


@pytest.mark.p1
def test_a_misplaced_unsuspended_capture_card_gives_two_rows() -> None:
    """AC-3: a Capture card both misplaced and unsuspended is offered once of each kind."""
    collection = managed_collection(MANIFEST)
    card = add_card(collection, capture_note(collection), 0, "Default")
    store, _ = wired(collection)

    preview = run(store.setup_preview())

    assert [r.key for r in preview.repairs] == [
        key(MISPLACED_CARD, card),
        key(UNSUSPENDED_CARD, card),
    ]


@pytest.mark.p1
def test_a_failed_repair_write_does_not_end_the_run_and_comes_back_as_a_discrepancy() -> None:
    """AC-10: a `suspend` that fails leaves the run going, and the Setup service reports its
    row as a discrepancy; the other checked rows are repaired.
    """
    leftovers = Leftovers()
    collection = leftovers.collection
    failing = leftovers.capture
    second = add_card(collection, capture_note(collection), 0, MANIFEST.card_deck(CAPTURE, 0))
    replies = collection_replies(collection, writes=True)
    suspend = replies["suspend"]

    def suspend_or_fail(body: Any) -> Any:
        if body.get("params", {}).get("cards") == [failing]:
            return {"result": None, "error": "collection is not available"}
        return suspend(body)

    replies["suspend"] = suspend_or_fail
    store, replay = wired_over(replies)
    setup = SetupService(
        store,
        sync=FakeSyncRequester(),
        prefix=PREFIX,
        azure_configured=True,
        openrouter_configured=True,
    )
    checked = [*leftovers.all_keys(), key(UNSUSPENDED_CARD, second)]

    async def confirm() -> Any:
        plan = await setup.plan(checked)
        return await setup.apply(plan["planHash"], checked)

    result = run(confirm())

    assert result["verified"] is False
    assert result["discrepancies"] == [
        {
            "action": "repair",
            "kind": UNSUSPENDED_CARD,
            "name": str(failing),
            "requiresFullSync": False,
        }
    ]
    assert sent_writes(replay.sent) == ["deleteMediaFile", "changeDeck", "suspend", "suspend"]
    assert collection.cards[second].suspended is True
    assert leftovers.orphan_media not in collection.media
    retry = PlanItem(PlanAction.REPAIR, ResourceKind.UNSUSPENDED_CARD, str(failing))
    assert result["planHash"] == plan_hash((retry,))  # Run Setup again re-checks it


@pytest.mark.p1
def test_a_checked_resource_that_vanished_before_the_apply_is_refused() -> None:
    """AC-11: the orphan deleted in Anki Desktop between the plan and the apply drops out of
    the fresh plan, so its hash differs: `plan_changed` before any write.
    """
    leftovers = Leftovers()
    store, replay = wired(leftovers.collection)
    preview = run(store.setup_preview())
    chosen = key(ORPHAN_MEDIA, leftovers.orphan_media)
    checked = [r for r in preview.repairs if r.key == chosen]
    leftovers.collection.media.discard(leftovers.orphan_media)

    outcome = settle(
        bounded(store.setup_apply(plan_hash((*preview.items, *checked)), repairs=[chosen]))
    )

    assert isinstance(outcome, AppError) and outcome.code is ErrorCode.PLAN_CHANGED
    assert sent_writes(replay.sent) == []
