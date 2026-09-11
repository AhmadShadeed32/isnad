#!/usr/bin/env bash
# Bootstrap a local Python environment for Isnad.
#   ./setup.sh
set -euo pipefail

PYTHON="${PYTHON:-python3.11}"

echo "==> Using $($PYTHON --version)"

"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), "Isnad requires Python 3.11 or newer"'

if [ ! -d ".venv311" ]; then
  echo "==> Creating virtual environment in .venv311"
  "$PYTHON" -m venv .venv311
fi

# shellcheck disable=SC1091
source .venv311/bin/activate
python -c 'import sys; assert sys.version_info >= (3, 11), "Recreate .venv311 with Python 3.11 or newer"'

echo "==> Upgrading pip"
python -m pip install --upgrade pip >/dev/null

echo "==> Installing dependencies (runtime + dev)"
python -m pip install -r requirements-dev.txt

echo ""
echo "Done. Activate with:  source .venv311/bin/activate"
echo "Then try:             make demo   |   make test   |   make run"
