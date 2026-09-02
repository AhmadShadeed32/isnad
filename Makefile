# Isnad — common tasks. Run `make setup` first.
# Uses the project virtualenv if present, else the active/global python.
# .venv311 first: this project needs 3.11, and a stale .venv on 3.9 silently
# ran `make test` on the wrong interpreter.
PY := $(shell [ -x .venv311/bin/python ] && echo .venv311/bin/python \
	|| ([ -x .venv/bin/python ] && echo .venv/bin/python || echo python3))

.DEFAULT_GOAL := help
.PHONY: help setup demo test run lint audit lock clean verify-lock

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup:  ## Create .venv and install dependencies
	./setup.sh

demo:  ## Run the three demo acts through the real engine
	$(PY) -m demo.run_acts

test:  ## Run the test suite
	$(PY) -m pytest -q

run:  ## Serve the API at http://localhost:8000 (docs at /docs)
	$(PY) -m uvicorn app.main:app --reload

serve:  ## Serve as a deployment would: one worker, no reload, no access log
	# --no-access-log because the OAuth `code` and `state` are query parameters,
	# so uvicorn's access log records single-use authorization codes in
	# cleartext (S13). One worker because sessions, consent, the SSE bus, the
	# idempotency cache and the vault are all in-process.
	$(PY) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
		--workers 1 --no-access-log --proxy-headers

lint:  ## Lint with ruff, then audit dependencies
	$(PY) -m ruff check app tests scripts
	$(MAKE) audit

audit:  ## Fail on a known advisory in the dependency closure (S8)
	$(PY) -m pip_audit --skip-editable

lock:  ## Regenerate requirements.lock.txt from this environment
	@echo "Refusing to freeze the active environment: it may contain dev-only packages."
	@echo "Regenerate the runtime lock in a clean Python 3.11 environment, then run make verify-lock."
	@false

verify-lock:  ## Check that the runtime lock is exact and covers direct runtime dependencies
	$(PY) scripts/verify_runtime_lock.py

clean:  ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache **/__pycache__ *.egg-info
