"""`AnkiConnectStore`: the AnkiStore port over AnkiConnect. Each method is one use case, run
entirely under the Anki lock (AD-5).
"""

import asyncio
from typing import Any

from language_lab.adapters.anki.client import AnkiConnectClient
from language_lab.adapters.anki.lock import AnkiLock
from language_lab.adapters.anki.manifest import Manifest
from language_lab.adapters.anki.setup_apply import run_plan
from language_lab.adapters.anki.setup_diff import AnkiState, ModelState, diff
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.setup import SetupPreview
from language_lab.domain.setup import plan_hash as _plan_hash
from language_lab.domain.sync import SyncOutcome

POLL_INTERVAL_S = 1.0
SYNC_BUDGET_S = 120.0  # a Sync with AnkiWeb can take far longer than any other action

# API v1 operation states (spike 2.2, Q7)
_SUCCEEDED = "succeeded"
_FAILED = "failed"
# Decided 2026-10-21: a dialog in Anki or a cancelled Sync ends the Sync at once
_GAVE_UP = frozenset({"waitingForUser", "cancelled"})
_AUTH_REQUIRED_TYPE = "authenticationRequired"
_INNER_VERSION = 6  # `multi` answers each inner action as `{result, error}` from version 6

type Read = tuple[str, dict[str, Any]]


def _failure_outcome(poll: dict[str, Any]) -> SyncOutcome:
    """A failed operation's outcome, from its `error.data.type` (spike 2.2, Q3/Q4)."""
    error = poll.get("error")
    data = error.get("data") if isinstance(error, dict) else None
    kind = data.get("type") if isinstance(data, dict) else None
    if kind == _AUTH_REQUIRED_TYPE:
        return SyncOutcome.AUTH_REQUIRED
    return SyncOutcome.ANKIWEB_UNREACHABLE


_MODEL_READS = ("modelFieldNames", "modelTemplates", "modelStyling")


def _names(value: Any) -> frozenset[str]:
    if not isinstance(value, list) or not all(isinstance(n, str) for n in value):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    return frozenset(value)


def _model_state(fields: Any, templates: Any, styling: Any) -> ModelState:
    """A note type from `modelFieldNames`, `modelTemplates` and `modelStyling` (spike 2.2)."""
    if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    if not isinstance(templates, dict) or not isinstance(styling, dict):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    sides: dict[str, tuple[str, str]] = {}
    for card, template in templates.items():
        if not isinstance(template, dict):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        front, back = template.get("Front"), template.get("Back")
        if not isinstance(front, str) or not isinstance(back, str):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        sides[card] = (front, back)
    css = styling.get("css")
    if not isinstance(css, str):
        raise AppError(ErrorCode.ANKI_UNAVAILABLE)
    return ModelState(tuple(fields), sides, css)


class AnkiConnectStore:
    def __init__(
        self,
        client: AnkiConnectClient,
        lock: AnkiLock,
        *,
        manifest: Manifest | None = None,
        poll_interval_s: float = POLL_INTERVAL_S,
        sync_budget_s: float = SYNC_BUDGET_S,
    ) -> None:
        self._client = client
        self._lock = lock
        self._manifest = manifest
        self._poll_interval_s = poll_interval_s
        self._sync_budget_s = sync_budget_s

    async def reachable(self) -> bool:
        async with self._lock.hold():
            try:
                await self._client.invoke("version")
            except AppError as exc:
                if exc.code is ErrorCode.ANKI_UNAVAILABLE:
                    return False
                raise
            return True

    async def setup_preview(self) -> SetupPreview:
        """Read the managed state and diff it against the manifest, with reads only, under one
        lock hold (AD-3, AD-5). Raises `AppError(ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            state = await self._read_state(manifest)
        return diff(manifest, state)

    async def setup_apply(self, plan_hash: str) -> SetupPreview:
        """Re-diff, refuse a stale `plan_hash` before any write, run the plan's Create and Repair
        items through the guarded client, and verify by a fresh diff, all under one lock hold
        (AD-3, AD-4, AD-5). Raises `AppError(PLAN_CHANGED | ANKI_UNAVAILABLE | ANKI_BUSY)`.
        """
        manifest = self._require_manifest()
        async with self._lock.hold():
            state = await self._read_state(manifest)
            before = diff(manifest, state)
            if _plan_hash(before.items) != plan_hash:
                raise AppError(ErrorCode.PLAN_CHANGED)
            await run_plan(self._client.invoke, manifest, state, before.items)
            verified = await self._read_state(manifest)
        return diff(manifest, verified)

    def _require_manifest(self) -> Manifest:
        if self._manifest is None:
            raise RuntimeError("AnkiConnectStore was built without a manifest")
        return self._manifest

    async def _read_state(self, manifest: Manifest) -> AnkiState:
        deck_names, model_names = await self._multi([("deckNames", {}), ("modelNames", {})])
        decks, models = _names(deck_names), _names(model_names)
        managed = [nt.name for nt in manifest.note_types if nt.name in models]
        preset_decks = [deck for deck in manifest.preset.decks if deck in decks]
        reads: list[Read] = []
        for name in managed:
            reads += [(action, {"modelName": name}) for action in _MODEL_READS]
        reads += [("getDeckConfig", {"deck": deck}) for deck in preset_decks]
        results = await self._multi(reads) if reads else []
        per_model = len(_MODEL_READS)
        managed_models = {
            name: _model_state(*results[i * per_model : (i + 1) * per_model])
            for i, name in enumerate(managed)
        }
        configs = results[len(managed) * per_model :]
        preset_configs = {deck: config for deck, config in zip(preset_decks, configs, strict=True)}
        if not all(isinstance(c, dict) for c in preset_configs.values()):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        return AnkiState(decks, models, managed_models, preset_configs)

    async def _multi(self, reads: list[Read]) -> list[Any]:
        """Send `reads` as one `multi` and return each inner `result`."""
        actions = [
            {"action": action, "version": _INNER_VERSION, "params": params}
            for action, params in reads
        ]
        replies = await self._client.invoke("multi", actions=actions)
        if not isinstance(replies, list) or len(replies) != len(reads):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        results = []
        for reply in replies:
            if not isinstance(reply, dict) or reply.get("error") is not None:
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            results.append(reply.get("result"))
        return results

    async def sync(self) -> SyncOutcome:
        async with self._lock.hold():
            try:
                async with asyncio.timeout(self._sync_budget_s):
                    return await self._sync_to_end()
            except TimeoutError:
                return SyncOutcome.ANKIWEB_UNREACHABLE

    async def _sync_to_end(self) -> SyncOutcome:
        started = await self._client.invoke_v1("collection.sync")
        operation_id = started.get("operationId") if isinstance(started, dict) else None
        if not isinstance(operation_id, str):
            raise AppError(ErrorCode.ANKI_UNAVAILABLE)
        while True:
            poll = await self._client.invoke_v1("operations.get", operationId=operation_id)
            if not isinstance(poll, dict):
                raise AppError(ErrorCode.ANKI_UNAVAILABLE)
            state = poll.get("state")
            if state == _SUCCEEDED:
                return SyncOutcome.OK
            if state == _FAILED:
                return _failure_outcome(poll)
            if state in _GAVE_UP:
                return SyncOutcome.ANKIWEB_UNREACHABLE
            await asyncio.sleep(self._poll_interval_s)
