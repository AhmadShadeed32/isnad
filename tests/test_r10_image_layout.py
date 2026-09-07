"""R10 — the runtime image must carry what its routes import and read.

The image copied `app/` and `pyproject.toml` and nothing else. `/lab` imports
`demo.lab.runner` unconditionally and reads a recorded bundle from
`demo/lab/artifacts/`, so the container answered `/readyz` happily and then
failed that route. The wheel already packaged `demo`, which is exactly why a
wheel smoke test did not catch it: the two artifacts have different layouts.

These tests read the Dockerfile and `.dockerignore` as the file-layout contract
they are. They do not build or run an image — that needs a Docker daemon, which
is not available in this environment, and it is stated as a limit rather than
implied to have passed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
DOCKERIGNORE = (ROOT / ".dockerignore").read_text(encoding="utf-8")


def _runtime_copy_sources() -> list[str]:
    """Every host path the runtime stage copies in (not the build stage)."""
    runtime = DOCKERFILE.split("AS runtime", 1)[1]
    sources = []
    for line in runtime.splitlines():
        line = line.strip()
        if not line.startswith("COPY") or "--from=" in line:
            continue
        parts = re.sub(r"--\S+", "", line[len("COPY"):]).split()
        sources.extend(parts[:-1])  # the last token is the destination
    return sources


def _ignored(path: str) -> bool:
    """Whether `.dockerignore` excludes `path`, last matching pattern winning."""
    import fnmatch

    excluded = False
    for raw in DOCKERIGNORE.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negate = line.startswith("!")
        pattern = line[1:] if negate else line
        pattern = pattern.rstrip("/")
        if (
            fnmatch.fnmatch(path, pattern)
            or fnmatch.fnmatch(path, pattern + "/*")
            or path.startswith(pattern.replace("/**", "") + "/")
            and "**" in pattern
        ):
            excluded = not negate
    return excluded


@pytest.mark.parametrize(
    "needed",
    ["app", "demo/__init__.py", "demo/lab"],
    ids=["the application", "the demo package marker", "the recorded lab"],
)
def test_the_runtime_stage_copies_what_the_routes_need(needed):
    sources = _runtime_copy_sources()
    assert any(
        needed == src or src.startswith(needed + "/") or needed.startswith(src + "/")
        for src in sources
    ), f"the runtime image never copies {needed}; a route that reads it will fail"


def test_the_lab_bundle_is_inside_a_copied_path():
    """`/lab/bundle.json` reads this file directly from disk."""
    bundle = ROOT / "demo" / "lab" / "artifacts" / "bundle.json"
    assert bundle.exists(), "the recorded bundle is missing from the repository"
    assert not _ignored("demo/lab/artifacts/bundle.json"), (
        ".dockerignore excludes the bundle, so the COPY would not carry it"
    )


def test_the_build_context_still_excludes_the_development_harnesses():
    """Only the lab is re-included. A runtime image must not ship a fake operator."""
    assert _ignored("demo/fake_operator/app.py")
    assert _ignored("demo/merchant_pilot/app.py")
    assert _ignored("tests/conftest.py")


def test_the_lab_runtime_imports_nothing_outside_what_the_image_carries():
    """`demo.lab.runner` must not pull in a development-only harness."""
    source = (ROOT / "demo" / "lab" / "runner.py").read_text(encoding="utf-8")
    imports = re.findall(r"^\s*(?:from|import)\s+(demo\.[\w.]+)", source, re.MULTILINE)
    for module in imports:
        assert module.startswith("demo.lab"), (
            f"demo.lab.runner imports {module}, which the runtime image does not carry"
        )


def test_the_image_documents_the_registry_signing_posture():
    """Signing the registry has two halves and doing one is a startup failure.

    The image keeps the developer's `.sig` out of the build context on purpose,
    so an operator who enables signature enforcement must both sign with this
    deployment's key and pin that key as trusted. Doing only the first starts a
    container that verifies and then refuses. The wheel hits the same wall from
    the other side — it ships the dev `.sig` — which is what the release smoke
    found, so the image says it too.
    """
    assert "ISNAD_VAULT_TRUSTED_PUBLIC_KEYS" in DOCKERFILE, (
        "the Dockerfile must name the trusted-key pin the registry check requires"
    )
    assert "ISNAD_REGISTRY_SIGNATURE_REQUIRED" in DOCKERFILE
