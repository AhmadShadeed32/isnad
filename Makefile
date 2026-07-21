# Isnad — common tasks. Run `make setup` first.
# Uses the project virtualenv if present, else the active/global python.
PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.DEFAULT_GOAL := help
.PHONY: help setup demo test run lint clean

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

lint:  ## Lint with ruff
	$(PY) -m ruff check app tests

clean:  ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache **/__pycache__ *.egg-info
