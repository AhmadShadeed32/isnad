"""Sign the number registry so a tampered entry is detectable.

    PYTHONPATH=. .venv311/bin/python scripts/sign_registry.py
    PYTHONPATH=. .venv311/bin/python scripts/sign_registry.py --check

An entry here asserts that a phone number belongs to a named bank. That is the
most attractive thing in this system to tamper with — a single edited digit
turns a scammer's number into a trusted institution — and until now it was an
unsigned YAML file.

Re-run this after EVERY edit to registry.yaml, or the file stops loading.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import settings
from app.registry.signing import RegistryTampered, signature_path, verify, write


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default=str(settings.registry_path))
    parser.add_argument("--check", action="store_true", help="verify only, do not write")
    args = parser.parse_args()
    path = Path(args.registry)

    if not path.exists():
        print(f"no registry at {path}")
        return 1

    if args.check:
        try:
            reason = verify(path)
        except RegistryTampered as err:
            print(f"TAMPERED: {err}")
            return 2
        print(reason or f"OK: {path} matches {signature_path(path)}")
        return 0

    record = write(path)
    print(f"signed {path}")
    print(f"  -> {signature_path(path)}")
    print(f"  sha256     {record.sha256}")
    print(f"  public key {record.public_key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
