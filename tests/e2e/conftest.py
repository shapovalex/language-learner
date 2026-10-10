"""Playwright defaults for browser tests: base URL and timeouts."""

import pytest
from playwright.sync_api import BrowserContext, expect

ACTION_TIMEOUT_MS = 15_000
NAVIGATION_TIMEOUT_MS = 30_000
EXPECT_TIMEOUT_MS = 10_000

expect.set_options(timeout=EXPECT_TIMEOUT_MS)


@pytest.fixture
def context(new_context) -> BrowserContext:
    context = new_context()
    context.set_default_timeout(ACTION_TIMEOUT_MS)
    context.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
    return context


# Defined in a conftest, not in support/fixtures: pytest-playwright registers its own
# `base_url` plugin after ours, and only a conftest fixture outranks a plugin's.
@pytest.fixture(scope="session")
def base_url(pytestconfig: pytest.Config, request: pytest.FixtureRequest) -> str:
    """`--base-url` (or PYTEST_BASE_URL) targets a running app; otherwise start `live_server`."""
    explicit = pytestconfig.getoption("--base-url") or pytestconfig.getini("base_url")
    if explicit:
        return explicit.rstrip("/")
    return request.getfixturevalue("live_server").url
