"""Setup readiness (FR-5), preview, and confirmed apply with verify (FR-6).

Readiness: AnkiConnect reachable, Azure and OpenRouter configured, the Prefix. The keys are
checked as configured only, with no live call. The plan: what Setup would change in Anki, with
its hash (AD-3), read without touching Anki. Apply: the plan the user confirmed by its hash,
run to its end and verified (AD-3). The run is a task the service keeps; a request only awaits
it, shielded, so a client that disconnects doesn't cancel it, and a second request while it
runs awaits the same run. `apply_status()` reports it for a screen coming back. Responses
carry ids and names; the Setup screen owns the copy.
"""

import asyncio
import contextlib
from typing import Literal, TypedDict

from language_lab.domain.setup import PlanItem, SetupPreview, plan_hash
from language_lab.ports.anki_store import AnkiStore

type CheckId = Literal["ankiConnect", "azure", "openrouter"]


class Check(TypedDict):
    id: CheckId
    ok: bool


class Readiness(TypedDict):
    prefix: str
    checks: list[Check]


class PlanRow(TypedDict):
    action: str
    kind: str
    name: str


class UnmanagedRow(TypedDict):
    kind: str
    name: str


class Plan(TypedDict):
    prefix: str
    planHash: str  # camelCase on the wire (Consistency Conventions)
    items: list[PlanRow]
    unmanaged: list[UnmanagedRow]


class ApplyResult(TypedDict):
    verified: bool
    planHash: str  # what a fresh preview hashes to while Anki stays as verify found it
    discrepancies: list[PlanRow]


class ApplyStatus(TypedDict):
    state: Literal["idle", "running", "finished"]
    result: ApplyResult | None


def _rows(items: tuple[PlanItem, ...]) -> list[PlanRow]:
    return [{"action": str(i.action), "kind": str(i.kind), "name": i.name} for i in items]


def _result(verification: SetupPreview) -> ApplyResult:
    return {
        "verified": not verification.items,
        "planHash": plan_hash(verification.items),
        "discrepancies": _rows(verification.items),
    }


def _retrieve(task: asyncio.Task[ApplyResult]) -> None:
    """Mark a run's exception as seen: its requests may all have gone away."""
    if not task.cancelled():
        task.exception()


class SetupService:
    def __init__(
        self,
        anki: AnkiStore,
        *,
        prefix: str,
        azure_configured: bool,
        openrouter_configured: bool,
    ) -> None:
        self._anki = anki
        self._prefix = prefix
        self._azure = azure_configured
        self._openrouter = openrouter_configured
        self._run: asyncio.Task[ApplyResult] | None = None
        self._last: ApplyResult | None = None  # the last run that finished

    async def readiness(self) -> Readiness:
        """Each check on its own, in tile order. `anki_busy` propagates as an `AppError`."""
        return {
            "prefix": self._prefix,
            "checks": [
                {"id": "ankiConnect", "ok": await self._anki.reachable()},
                {"id": "azure", "ok": self._azure},
                {"id": "openrouter", "ok": self._openrouter},
            ],
        }

    async def plan(self) -> Plan:
        """The preview, items in the store's order. `anki_busy`/`anki_unavailable` propagate."""
        preview = await self._anki.setup_preview()
        return {
            "prefix": self._prefix,
            "planHash": plan_hash(preview.items),
            "items": _rows(preview.items),
            "unmanaged": [{"kind": str(u.kind), "name": u.name} for u in preview.unmanaged],
        }

    async def apply(self, plan_hash: str) -> ApplyResult:
        """Run the confirmed plan to its end and return the verification. `plan_changed`,
        `anki_busy` and `anki_unavailable` propagate. A cancelled caller leaves the run going.
        """
        if self._run is None or self._run.done():
            self._run = asyncio.create_task(self._apply(plan_hash))
            self._run.add_done_callback(_retrieve)
        return await asyncio.shield(self._run)

    def apply_status(self) -> ApplyStatus:
        if self._run is not None and not self._run.done():
            return {"state": "running", "result": None}
        if self._last is not None:
            return {"state": "finished", "result": self._last}
        return {"state": "idle", "result": None}

    async def aclose(self) -> None:
        """Cancel a run still going (shutdown)."""
        run, self._run = self._run, None
        if run is not None and not run.done():
            run.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await run

    async def _apply(self, plan_hash: str) -> ApplyResult:
        result = _result(await self._anki.setup_apply(plan_hash))
        self._last = result  # a run that raised isn't recorded
        return result
