"""Validate the committed runtime lock without contacting a package index.

The Docker image installs ``requirements.lock.txt``. A normal development
environment also carries pytest, Ruff and pip-audit, so freezing it makes the
image depend on tooling it never uses. This check keeps the source manifests
and the lock's direct runtime entries aligned; the release job performs the
networked vulnerability and image checks separately.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "requirements.lock.txt"
PROJECT = ROOT / "pyproject.toml"
_PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;]+)$")
_REQ_NAME = re.compile(r"^([A-Za-z0-9_.-]+)")


def _canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _locked() -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in LOCK.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _PIN.fullmatch(line)
        if match is None:
            raise SystemExit(f"{LOCK.name} contains a non-exact requirement: {raw!r}")
        name, version = match.groups()
        canonical = _canonical(name)
        if canonical in pins:
            raise SystemExit(f"{LOCK.name} contains {name!r} more than once")
        pins[canonical] = version
    return pins


def _project_dependencies() -> set[str]:
    data = tomllib.loads(PROJECT.read_text(encoding="utf-8"))
    names: set[str] = set()
    for requirement in data["project"]["dependencies"]:
        match = _REQ_NAME.match(requirement)
        if match is None:
            raise SystemExit(f"Could not read project dependency {requirement!r}")
        names.add(_canonical(match.group(1)))
    return names


def main() -> None:
    locked = _locked()
    missing = sorted(_project_dependencies() - set(locked))
    if missing:
        raise SystemExit("Runtime lock misses direct dependencies: " + ", ".join(missing))
    print(f"{LOCK.name}: {len(locked)} exact pins cover all direct runtime dependencies")


if __name__ == "__main__":
    main()
