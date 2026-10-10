"""Suite-wide pytest wiring: shared fixtures, level markers, priority order, opt-in live runs."""

from pathlib import Path

import pytest

pytest_plugins = [
    "tests.support.fixtures.settings",
    "tests.support.fixtures.logs",
    "tests.support.fixtures.live_server",
]

_TESTS = Path(__file__).resolve().parent
_LEVELS = ("unit", "integration", "api", "e2e")
# Smoke first, then P0..P3, then unmarked (test design: run order within a run).
_ORDER = ("smoke", "p0", "p1", "p2", "p3")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live-anki",
        action="store_true",
        default=False,
        help="Run tests marked live_anki against a real Anki with the dev Prefix.",
    )


def _rank(item: pytest.Item) -> int:
    return next((i for i, name in enumerate(_ORDER) if item.get_closest_marker(name)), len(_ORDER))


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    skip_live = pytest.mark.skip(reason="needs a running Anki; pass --live-anki to run")
    for item in items:
        level = item.path.relative_to(_TESTS).parts[0]
        if level in _LEVELS:
            item.add_marker(level)
        if item.get_closest_marker("live_anki") and not config.getoption("--live-anki"):
            item.add_marker(skip_live)
    items.sort(key=_rank)
