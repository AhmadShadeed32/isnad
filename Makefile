# Isnad — common tasks. Run `make setup` first.
# Uses the project virtualenv if present, else the active/global python.
# .venv311 first: this project needs 3.11, and a stale .venv on 3.9 silently
# ran `make test` on the wrong interpreter.
PY := $(shell [ -x .venv311/bin/python ] && echo .venv311/bin/python \
	|| ([ -x .venv/bin/python ] && echo .venv/bin/python || echo python3))

# The demo runs on its own database and its own signing key, so a judge's run
# can never touch a developer's. ISNAD_VAULT_TRUSTED_PUBLIC_KEYS is the *public*
# half of the key that signed the bundled caller registry (app/registry/
# registry.yaml.sig) — pinning it lets a fresh checkout trust that file. It is
# not a credential and there is nothing to keep secret about it.
PORT ?= 8010
JUDGE_ENV := ISNAD_DEMO_MODE=true \
	ISNAD_PROVIDER=mock \
	ISNAD_DATABASE_URL=sqlite:///./isnad-demo.db \
	ISNAD_VAULT_KEY_PATH=.isnad/demo-vault-key.pem \
	ISNAD_MERCHANT_API_KEYS=demo-merchant-key \
	ISNAD_VAULT_TRUSTED_PUBLIC_KEYS=4034e169495122a893d8fe6738c2b0f54655fdfb6ec3c6d0eeb938d1330e7f9f
JUDGE_SERVE := -m uvicorn app.main:app --host 127.0.0.1 --port $(PORT) \
	--workers 1 --no-access-log

.DEFAULT_GOAL := help
.PHONY: help setup judge judge-ai demo test test-fast run serve lint audit lock clean verify-lock

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup:  ## Create .venv311 and install dependencies
	./setup.sh

judge:  ## Serve the reviewer demo, fully offline, at http://127.0.0.1:8010/judge
	@echo "Judge Mode  http://127.0.0.1:$(PORT)/judge"
	@echo "Lab         http://127.0.0.1:$(PORT)/lab"
	@echo "Console     http://127.0.0.1:$(PORT)/console"
	@echo "API docs    http://127.0.0.1:$(PORT)/docs"
	@echo "Planner: greedy (deterministic). Use 'make judge-ai' for the Gemini agent."
	@$(JUDGE_ENV) ISNAD_PLANNER=greedy $(PY) $(JUDGE_SERVE)

judge-ai:  ## Same demo with the Gemini agent choosing the checks (needs ISNAD_GEMINI_API_KEY)
	@test -n "$$ISNAD_GEMINI_API_KEY" || { \
		echo "Set ISNAD_GEMINI_API_KEY first — see submission/JUDGE_GUIDE.md step 6."; exit 1; }
	@echo "Judge Mode  http://127.0.0.1:$(PORT)/judge   (planner: gemini)"
	@$(JUDGE_ENV) ISNAD_PLANNER=llm $(PY) $(JUDGE_SERVE)

demo:  ## Run the three demo acts through the real engine
	$(PY) -m demo.run_acts

test:  ## Run the whole suite, browser tests included
	$(PY) -m pytest -q

test-fast:  ## Run the suite without the browser tests (no Chromium needed)
	$(PY) -m pytest -q --ignore=tests/browser

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
	$(PY) -m ruff check app tests scripts demo
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
