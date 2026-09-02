#!/usr/bin/env bash
# Bootstrap a local Python environment for Isnad.
#   ./setup.sh
set -euo pipefail

PYTHON="${PYTHON:-python3}"

echo "==> Using $($PYTHON --version)"

if [ ! -d ".venv" ]; then
  echo "==> Creating virtual environment in .venv"
  "$PYTHON" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing dependencies (runtime + dev)"
python -m pip install -r requirements-dev.txt

echo ""
echo "Done. Activate with:  source .venv/bin/activate"
echo "Then try:             make demo   |   make test   |   make run"
