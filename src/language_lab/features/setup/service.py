"""Setup readiness (FR-5) and preview (FR-6).

Readiness: AnkiConnect reachable, Azure and OpenRouter configured, the Prefix. The keys are
checked as configured only, with no live call. The plan: what Setup would change in Anki, with
its hash (AD-3), read without touching Anki. Responses carry ids and names; the Setup screen
owns the copy.
"""

from typing import Literal, TypedDict

from language_lab.domain.setup import plan_hash
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
            "items": [
                {"action": str(i.action), "kind": str(i.kind), "name": i.name}
                for i in preview.items
            ],
            "unmanaged": [{"kind": str(u.kind), "name": u.name} for u in preview.unmanaged],
        }
