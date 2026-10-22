"""The Setup screen's stubbed API, shared by the Setup E2E tests (tests/e2e/test_setup_*.py).

The Prefix is `LanguageLabDev`, not the default, so a hard-coded "LanguageLab" can't pass.
`open_setup(page, plan_body)` stubs readiness, the plan and the apply status, opens /setup and
returns its main landmark. The copy strings are the ones more than one Setup test checks.
"""

from typing import Any

from playwright.sync_api import Locator, Page

from tests.support.network import stub_api_json

READINESS = "/api/setup/readiness"
PLAN = "/api/setup/plan"
APPLY = "/api/setup/apply"
STATUS = "/api/setup/apply/status"
PREFIX = "LanguageLabDev"  # not the default, so a hard-coded "LanguageLab" can't pass
PLAN_HASH = "0" * 64

IDLE = {"state": "idle", "result": None}

APPLY_LABEL = "Apply setup"
FIX_REASON = "Fix the failing check to continue."
CHANGES_HEADING = "What will change in Anki"


def readiness(*, anki_connect: bool = True, full_sync_ok: bool | None = None) -> dict[str, Any]:
    """Readiness with Azure and OpenRouter configured; a `fullSync` check only when
    `full_sync_ok` is given.
    """
    checks = [
        {"id": "ankiConnect", "ok": anki_connect},
        {"id": "azure", "ok": True},
        {"id": "openrouter", "ok": True},
    ]
    if full_sync_ok is not None:
        checks.append({"id": "fullSync", "ok": full_sync_ok})
    return {"prefix": PREFIX, "checks": checks}


def item(action: str, kind: str, name: str) -> dict[str, str]:
    return {"action": action, "kind": kind, "name": name}


def plan(
    items: list[dict[str, str]],
    plan_hash: str = PLAN_HASH,
    *,
    unmanaged: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {"prefix": PREFIX, "planHash": plan_hash, "items": items, "unmanaged": unmanaged or []}


def open_setup(
    page: Page,
    plan_body: dict[str, Any],
    *,
    anki_connect: bool = True,
    full_sync_ok: bool | None = None,
    status: Any = IDLE,
) -> Locator:
    stub_api_json(page, READINESS, readiness(anki_connect=anki_connect, full_sync_ok=full_sync_ok))
    stub_api_json(page, PLAN, plan_body)
    stub_api_json(page, STATUS, status)
    page.goto("/setup")
    return page.get_by_role("main")
