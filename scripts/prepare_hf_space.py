"""Stage an explicit runtime-only Space package; never upload the checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(output: Path) -> None:
    output = output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("stage the Space outside the source checkout")
    if output.exists() and any(output.iterdir()):
        raise ValueError("the staging directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    files = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT
    ).decode().split("\0")
    top_level = {"alembic.ini", "pyproject.toml", "requirements.txt", "requirements.lock.txt"}
    for name in sorted(set(files)):
        if not name or not (
            name in top_level or name.startswith(("app/", "migrations/", "demo/lab/"))
            or name in {"demo/__init__.py", "demo/run_acts.py"}
        ):
            continue
        source = ROOT / name
        if not source.is_file() or source.is_symlink():
            continue
        if source.suffix in {".pem", ".key", ".db", ".pyc"} or source.name.startswith(".env"):
            raise ValueError(f"refusing sensitive/runtime artifact: {name}")
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in ("Dockerfile", "README.md", "start.py"):
        shutil.copyfile(ROOT / "deploy" / "huggingface" / name, output / name)
    shutil.copyfile(ROOT / "docs" / "_internal" / "HUGGING_FACE_KEYS.md", output / "SERVER_KEYS.md")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    manifest = {
        "source_revision": revision,
        "files": {
            str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.rglob("*")) if path.is_file()
        },
    }
    (output / "RELEASE.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Staged {len(manifest['files'])} files at {output}; source {revision}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    prepare(parser.parse_args().output)
