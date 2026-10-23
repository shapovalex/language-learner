.PHONY: test test-fast test-e2e test-webkit test-integration test-cov test-ci browsers lint burn-in ci-local

# Everything, Chromium only. `-n auto --dist loadgroup`: one pytest-xdist worker per CPU, each with its own live server.
test:
	uv run pytest -n auto --dist loadgroup

# No browser: unit, api, integration.
test-fast:
	uv run pytest -n auto --dist loadgroup -m "not e2e"

test-e2e:
	uv run pytest -n auto --dist loadgroup -m e2e

# E2E under WebKit as well (R-09); release.yml's tag run covers this.
test-webkit:
	uv run pytest -n auto --dist loadgroup -m e2e --browser chromium --browser webkit

test-integration:
	uv run pytest -n auto --dist loadgroup -m integration

test-cov:
	uv run pytest -n auto --dist loadgroup -m "not e2e" --cov --cov-report=term-missing

# What CI runs: JUnit XML for the job summary, video kept for failed E2E tests.
test-ci:
	uv run pytest -n auto --dist loadgroup --junitxml=test-results/junit.xml --video=retain-on-failure

browsers:
	uv run playwright install chromium webkit

lint:
	uv run ruff check .
	uv run ruff format --check .

# Flaky detection: E2E BURN_IN times in a row, stopping at the first failure. CI runs it on PRs.
BURN_IN ?= 10
burn-in:
	@for i in $$(seq 1 $(BURN_IN)); do \
		echo "Burn-in iteration $$i/$(BURN_IN)"; \
		uv run pytest -n auto --dist loadgroup -m e2e -p no:cacheprovider --video=retain-on-failure || exit 1; \
	done; \
	echo "Burn-in complete: $(BURN_IN) clean iterations"

# The push/PR pipeline, locally: lint, the suite, then a short burn-in.
ci-local: lint test-ci
	$(MAKE) burn-in BURN_IN=3
