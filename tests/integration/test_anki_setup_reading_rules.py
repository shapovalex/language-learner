"""French reading rules: Setup creates and fills `<Prefix>::Study::French::Reading Rules`.

Setup's plan has one Create `readingRule` row, named by the combination, per seeded rule
(`manifest.reading_rules`) no `<Prefix> French Reading Rule` note holds by its decoded `RuleId`,
last in the items. Apply stores each example's bundled MP3 under its AD-7 name
(`media_name(prefix, rule id, bytes)`), then adds the note with its one Read card in the Reading
Rules deck. A store that fails skips that rule's note; the run goes on and verify lists it.

A missing rule note never makes the SetupState `needs_setup`: deleting one in Anki must not
block feature writes. Rule notes' example audio is referenced, so it's never orphan media, and
a rule card moved by hand is a `misplacedCard` repair like any managed card.

Anki is the in-memory collection in tests/support/anki_state.py.
"""

import base64
import uuid
from typing import Any

import pytest

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.codec import decode_field
from language_lab.adapters.anki.guard import PrefixGuard, media_pattern
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.setup_gate import SetupGate
from language_lab.adapters.anki.store import AnkiConnectStore
from language_lab.domain.audio import media_name
from language_lab.domain.catalog import Language
from language_lab.domain.setup import PlanAction, ResourceKind, SetupState, plan_hash
from tests.support.aio import settle
from tests.support.anki_connect import ANKI_URL, AnkiConnectReplay
from tests.support.anki_state import (
    Collection,
    collection_replies,
    item_note,
    managed_collection,
    reading_rule_fields,
    reading_rule_media,
    sent_writes,
    stock_collection,
)
from tests.support.items import VOCABULARY, content
from tests.support.setup_collections import (
    DELETED_RULE,
    MANIFEST,
    READING_RULE,
    READING_RULES_DECK,
    as_tuples,
    rule_deleted,
)

RULES = MANIFEST.reading_rules
STORE_FAILS_FOR = RULES[5]  # "eau": its second example's store fails


def wired(
    collection: Collection, *, replies: dict[str, Any] | None = None
) -> tuple[AnkiConnectStore, SetupGate, AnkiConnectReplay]:
    """The real guarded, gated client and store over `collection`, writes answered."""
    gate = SetupGate(MANIFEST)
    replay = AnkiConnectReplay(collection_replies(collection, writes=True) | (replies or {}))
    client = AnkiConnectClient(
        ANKI_URL, transport=replay.transport, guard=PrefixGuard(MANIFEST), gate=gate
    )
    return AnkiConnectStore(client, AnkiLock(), manifest=MANIFEST, gate=gate), gate, replay


async def _preview_then_apply(store: AnkiConnectStore) -> Any:
    preview = await store.setup_preview()
    return await store.setup_apply(plan_hash(preview.items))


def rule_notes(collection: Collection) -> dict[str, tuple[int, dict[str, str]]]:
    """Decoded RuleId -> (note id, stored fields) of every reading rule note."""
    return {
        decode_field(note.fields["RuleId"]): (note_id, note.fields)
        for note_id, note in collection.notes.items()
        if note.model == READING_RULE
    }


def rule_rows(items: Any) -> list[str]:
    return [i.name for i in items if i.kind is ResourceKind.READING_RULE]


@pytest.mark.p0
def test_a_stock_anki_previews_all_46_rules_last_and_apply_fills_the_deck() -> None:
    """Fresh install: 46 Create rows after the preset; apply leaves 46 notes, one card each in
    the Reading Rules deck and three stored MP3s, and verify finds nothing to change.
    """
    collection = stock_collection()
    media: dict[str, bytes] = {}
    store_media = collection_replies(collection, writes=True)["storeMediaFile"]

    def storing(body: dict[str, Any]) -> Any:
        params = body["params"]
        media[params["filename"]] = base64.b64decode(params["data"])
        return store_media(body)

    store, _, replay = wired(collection, replies={"storeMediaFile": storing})

    preview = settle(store.setup_preview())
    assert rule_rows(preview.items) == [r.combination for r in RULES]
    assert [i.kind for i in preview.items[-46:]] == [ResourceKind.READING_RULE] * 46
    assert all(i.action is PlanAction.CREATE for i in preview.items[-46:])
    assert READING_RULES_DECK in {i.name for i in preview.items}
    assert preview.state is SetupState.NEEDS_SETUP  # the decks and note types are missing

    verified = settle(store.setup_apply(plan_hash(preview.items)))

    assert not isinstance(verified, Exception), verified
    assert (verified.items, verified.repairs, verified.state) == ((), (), SetupState.READY)
    notes = rule_notes(collection)
    assert list(notes) == [r.id for r in RULES]  # added in data order
    for rule in RULES:
        note_id, fields = notes[rule.id]
        assert fields == reading_rule_fields(MANIFEST, rule)
        cards = [c for c in collection.cards.values() if c.note == note_id]
        assert [(c.ord, c.deck) for c in cards] == [(0, READING_RULES_DECK)]
        for example in rule.examples:
            name = media_name(MANIFEST.prefix, rule.id, example.audio)
            assert media_pattern(MANIFEST.prefix).fullmatch(name)
            assert media[name] == example.audio  # the bundled bytes, unchanged
    assert set(media) == reading_rule_media(MANIFEST) <= collection.media
    writes = sent_writes(replay.sent)
    first_rule = writes.index("storeMediaFile")
    assert (
        writes[first_rule:]
        == ["storeMediaFile"] * 3 + ["addNote"] + (["storeMediaFile"] * 3 + ["addNote"]) * 45
    )


@pytest.mark.p0
def test_a_set_up_anki_has_no_reading_rule_row_and_offers_no_repair_for_their_media() -> None:
    """Already set up: nothing to change, `ready`, and the rule media is never orphan."""
    store, _, _ = wired(managed_collection(MANIFEST))

    preview = settle(store.setup_preview())

    assert (preview.items, preview.repairs, preview.state) == ((), (), SetupState.READY)


@pytest.mark.p0
def test_a_deleted_rule_is_offered_again_and_never_blocks_saving_an_item() -> None:
    """One rule deleted: one Create row, the state stays `ready`, Save Item passes the gate,
    and apply recreates the note with the same media names.
    """
    collection = managed_collection(MANIFEST)
    rule_deleted(collection)
    store, gate, replay = wired(collection)

    preview = settle(store.setup_preview())

    assert as_tuples(preview.items) == {("create", "readingRule", DELETED_RULE.combination)}
    assert preview.state is SetupState.READY
    assert gate.state is SetupState.READY
    saved = settle(store.save_item(str(uuid.uuid4()), Language.EN, content(VOCABULARY)))
    assert not isinstance(saved, Exception), saved
    assert "addNote" in sent_writes(replay.sent)

    verified = settle(_preview_then_apply(store))

    assert (verified.items, verified.state) == ((), SetupState.READY)
    assert DELETED_RULE.id in rule_notes(collection)
    assert verified.repairs == ()  # its media is referenced again


@pytest.mark.p1
def test_a_rule_card_moved_by_hand_is_a_misplaced_card_repair() -> None:
    collection = managed_collection(MANIFEST)
    note_id, _ = rule_notes(collection)[RULES[0].id]
    (card_id,) = (i for i, c in collection.cards.items() if c.note == note_id)
    elsewhere = f"{MANIFEST.prefix}::Study::French::Sentences::Write"
    collection.cards[card_id].deck = elsewhere
    store, _, _ = wired(collection)

    preview = settle(store.setup_preview())

    assert preview.items == ()
    ((repair),) = preview.repairs
    assert (repair.kind, repair.name) == (ResourceKind.MISPLACED_CARD, str(card_id))
    assert repair.detail == {
        "noteType": READING_RULE,
        "card": "Read",
        "deck": elsewhere,
        "expectedDeck": READING_RULES_DECK,
    }


@pytest.mark.p0
def test_a_failed_media_store_skips_that_rules_note_and_the_run_goes_on() -> None:
    """`storeMediaFile` fails for one word: that rule's `addNote` isn't sent, every other rule
    is added, verify lists the rule, and the next plan offers it again.
    """
    collection = stock_collection()
    failing = media_name(MANIFEST.prefix, STORE_FAILS_FOR.id, STORE_FAILS_FOR.examples[1].audio)
    store_media = collection_replies(collection, writes=True)["storeMediaFile"]

    def store_or_fail(body: dict[str, Any]) -> Any:
        if body["params"]["filename"] == failing:
            return {"result": None, "error": "failed to store"}
        return store_media(body)

    store, _, replay = wired(collection, replies={"storeMediaFile": store_or_fail})

    verified = settle(_preview_then_apply(store))

    assert not isinstance(verified, Exception), verified
    assert as_tuples(verified.items) == {("create", "readingRule", STORE_FAILS_FOR.combination)}
    assert verified.state is SetupState.READY  # a missing rule never gates
    assert set(rule_notes(collection)) == {r.id for r in RULES} - {STORE_FAILS_FOR.id}
    assert sent_writes(replay.sent).count("addNote") == 45
    assert rule_rows(settle(store.setup_preview()).items) == [STORE_FAILS_FOR.combination]


@pytest.mark.p1
def test_deleting_an_item_leaves_every_reading_rule_note_and_its_media() -> None:
    """Features never touch the seeded notes: an Item's delete cleans only its own media."""
    collection = managed_collection(MANIFEST)
    item_id = str(uuid.uuid4())
    item_note(collection, MANIFEST, f"{MANIFEST.prefix} English Vocabulary", item_id, {})
    own = f"{MANIFEST.prefix.lower()}_{item_id}_{'a' * 12}.mp3"
    collection.media.add(own)
    before = rule_notes(collection)
    store, _, _ = wired(collection)
    settle(store.setup_preview())  # the gate is `ready`

    outcome = settle(store.delete_item(Language.EN, item_id))

    assert outcome is None
    assert rule_notes(collection) == before
    assert collection.media == reading_rule_media(MANIFEST)


@pytest.mark.p0
def test_a_deleted_rules_media_is_never_offered_as_orphan_and_survives_every_repair() -> None:
    """The deleted rule's Create re-stores its media under the same names, so they aren't
    orphan media: applying with every offered repair checked leaves the note with its 3 files.
    """
    collection = managed_collection(MANIFEST)
    rule_deleted(collection)
    stray = f"{MANIFEST.prefix.lower()}_{uuid.uuid4()}_{'b' * 12}.mp3"  # a real orphan
    collection.media.add(stray)
    store, _, _ = wired(collection)

    async def apply_with_every_repair() -> Any:
        preview = await store.setup_preview()
        keys = [r.key for r in preview.repairs]
        verified = await store.setup_apply(plan_hash((*preview.items, *preview.repairs)), keys)
        return preview, verified

    preview, verified = settle(apply_with_every_repair())

    assert [(r.kind, r.name) for r in preview.repairs] == [(ResourceKind.ORPHAN_MEDIA, stray)]
    assert (verified.items, verified.repairs) == ((), ())
    _, fields = rule_notes(collection)[DELETED_RULE.id]
    assert fields == reading_rule_fields(MANIFEST, DELETED_RULE)
    names = {media_name(MANIFEST.prefix, DELETED_RULE.id, e.audio) for e in DELETED_RULE.examples}
    assert len(names) == 3 and names <= collection.media
    assert stray not in collection.media


@pytest.mark.p0
def test_a_rule_note_type_with_other_fields_gets_no_rule_row_and_apply_adds_no_rule_note() -> None:
    """Its fields differ (`RuleId` removed): a Migrate noteType row, no reading rule Create, so
    apply never adds notes `addNote` would strip of their RuleId.
    """
    collection = managed_collection(MANIFEST)
    rule_deleted(collection)
    collection.models[READING_RULE].fields.remove("RuleId")
    before = len(rule_notes(collection))
    store, _, replay = wired(collection)

    preview = settle(store.setup_preview())

    assert rule_rows(preview.items) == []
    assert ("migrate", "noteType", READING_RULE) in as_tuples(preview.items)
    settle(store.setup_apply(plan_hash(preview.items)))
    assert "addNote" not in sent_writes(replay.sent)
    assert len(rule_notes(collection)) == before
