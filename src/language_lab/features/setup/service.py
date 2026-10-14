"""Setup readiness (FR-5): AnkiConnect reachable, Azure and OpenRouter configured, the Prefix.

The keys are checked as configured only, with no live call. The response carries check ids and
results; the Setup screen owns the copy.
"""

from typing import Literal, TypedDict

from language_lab.ports.anki_store import AnkiStore

type CheckId = Literal["ankiConnect", "azure", "openrouter"]


class Check(TypedDict):
    id: CheckId
    ok: bool


class Readiness(TypedDict):
    prefix: str
    checks: list[Check]


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
