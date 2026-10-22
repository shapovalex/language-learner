"""Story 2.8: SetupState at startup, in the plan, and as `409 setup_required` (AD-19, AD-15).

- **Startup.** The app lifespan asks the AnkiStore for `setup_state()` once at startup, so the
  adapter's gate knows the state before the first feature write. It doesn't wait for it, and a
  failure (Anki down) doesn't fail startup: the gate then computes the state on demand
  (decided with the user, 2026-10-21; see tests/integration/test_anki_setup_state.py).
- **The plan.** GET /api/setup/plan carries the preview's state as `"state"`, so the Setup
  screen can show the `newer_schema` alert.
- **The envelope.** A write the gate refuses raises `AppError(SETUP_REQUIRED)`, which the app
  maps to 409 with the fixed message. No product route writes outside Setup yet, so a probe
  route from tests/support/probes.py raises it.

The app takes the AnkiStore, so these tests pass the fake from tests/fakes/. Its preview's
`state` is what `setup_state()` returns, and it counts the calls (`state_calls`).
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from language_lab.app import create_app
from language_lab.domain.errors import MESSAGES, ErrorCode
from language_lab.domain.setup import PlanAction, PlanItem, ResourceKind, SetupPreview, SetupState
from tests.fakes.anki_store import FakeAnkiStore
from tests.support.aio import settle
from tests.support.clock import FakeClock, bounded, drain
from tests.support.fixtures.settings import SettingsFactory
from tests.support.hosts import client_over
from tests.support.lifespan import LIFESPAN_BOUND_S, start_lifespan
from tests.support.probes import GATED_ROUTE, error_envelope

PLAN = "/api/setup/plan"
PREFIX = "LanguageLab"
ITEMS = (PlanItem(PlanAction.MIGRATE, ResourceKind.NOTE_TYPE, f"{PREFIX} English Vocabulary"),)
STATES = ("ready", "needs_setup", "needs_migration", "newer_schema")


@pytest.mark.p0
@pytest.mark.parametrize("available", [True, False], ids=["anki-up", "anki-down"])
def test_startup_computes_setup_state_once_and_starts_even_when_anki_is_down(
    settings_factory: SettingsFactory, available: bool
) -> None:
    """AC-2: startup asks for the state once; with Anki down the app still starts."""
    store, clock = FakeAnkiStore(available=available), FakeClock()
    app = create_app(settings_factory(), anki_store=store, clock=clock)

    async def scenario() -> int:
        stack = await start_lifespan(app)
        await drain()
        calls = store.state_calls
        await asyncio.wait_for(stack.aclose(), LIFESPAN_BOUND_S)
        return calls

    assert settle(bounded(scenario())) == 1


@pytest.mark.p0
def test_a_gated_write_is_the_409_setup_required_envelope(probe_client: TestClient) -> None:
    """AC-9: `AppError(SETUP_REQUIRED)` from a feature write is 409 with the fixed message."""
    response = probe_client.post(GATED_ROUTE)

    assert response.status_code == 409
    error = error_envelope(response)
    assert error["code"] == ErrorCode.SETUP_REQUIRED.value
    assert error["message"] == MESSAGES[ErrorCode.SETUP_REQUIRED]
    assert error["requestId"]


@pytest.mark.p0
@pytest.mark.parametrize("state", STATES)
def test_the_plan_carries_the_setup_state(settings_factory: SettingsFactory, state: str) -> None:
    """AC-10: GET /api/setup/plan says which SetupState this visit found."""
    store = FakeAnkiStore(preview=SetupPreview(items=ITEMS, state=SetupState(state)))
    client = client_over(settings_factory, store, anki_prefix=PREFIX)

    response = client.get(PLAN)

    assert response.json().get("state") == state
    assert response.status_code == 200


@pytest.mark.p1
def test_startup_returns_while_the_state_is_in_flight_and_shutdown_cancels_it(
    settings_factory: SettingsFactory,
) -> None:
    """AC-2: startup doesn't wait for `setup_state()`, and shutdown cancels it."""
    store = FakeAnkiStore()
    started = asyncio.Event()
    cancelled: list[bool] = []

    async def in_flight() -> SetupState:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.append(True)
            raise
        return SetupState.READY

    store.setup_state = in_flight  # type: ignore[method-assign]
    app = create_app(settings_factory(), anki_store=store, clock=FakeClock())

    async def scenario() -> list[bool]:
        stack = await start_lifespan(app)
        await asyncio.wait_for(started.wait(), LIFESPAN_BOUND_S)
        await asyncio.wait_for(stack.aclose(), LIFESPAN_BOUND_S)
        return cancelled

    assert settle(bounded(scenario())) == [True]
