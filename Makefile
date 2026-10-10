.PHONY: test test-fast test-e2e test-webkit test-integration test-cov test-ci browsers

# Everything, Chromium only.
test:
	uv run pytest

# No browser: unit, api, integration.
test-fast:
	uv run pytest -m "not e2e"

test-e2e:
	uv run pytest -m e2e

# Tag runs: E2E under WebKit as well (R-09).
test-webkit:
	uv run pytest -m e2e --browser chromium --browser webkit

test-integration:
	uv run pytest -m integration

test-cov:
	uv run pytest -m "not e2e" --cov --cov-report=term-missing

# What CI runs: JUnit XML for the job summary, video kept for failed E2E tests.
test-ci:
	uv run pytest --junitxml=test-results/junit.xml --video=retain-on-failure

browsers:
	uv run playwright install chromium webkit
