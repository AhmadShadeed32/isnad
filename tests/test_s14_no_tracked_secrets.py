"""No credential may be tracked in the repository.

This is Operating Rule 0.1 ("Secrets never enter the repo"), and it was violated:
an editor's backup, `.env.bak-194200`, carried a live Anthropic key, the NaC key,
a merchant key and the subject pepper into commit 9e44e00. `.gitignore` listed
`.env` as an exact name, so `.env.bak-*` sailed straight past it, and both prior
security audits missed it.

Nothing in the suite would have caught that, so this is the test that does.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Patterns that identify a real credential rather than a placeholder.
SECRET_PATTERNS = [
    re.compile(r"sk-ant-api\d\d-[A-Za-z0-9_\-]{20,}"),  # Anthropic
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # any private key
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
]


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def test_no_tracked_file_contains_a_credential():
    offenders: list[str] = []
    for rel in _tracked_files():
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                # Report the file, never the match itself.
                offenders.append(f"{rel} matches {pattern.pattern[:28]}")
    assert not offenders, "tracked files carry credentials: " + "; ".join(offenders)


def test_no_dotenv_variant_is_tracked_except_the_example():
    """`.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`."""
    tracked = [f for f in _tracked_files() if Path(f).name.startswith(".env")]
    assert tracked == [".env.example"], f"unexpected tracked dotenv files: {tracked}"


@pytest.mark.parametrize("candidate", [".env.bak-194200", ".env.local", ".env.save"])
def test_the_ignore_rule_actually_covers_editor_backups(candidate):
    """git check-ignore, so the rule is verified rather than eyeballed."""
    result = subprocess.run(
        ["git", "check-ignore", "-q", candidate], cwd=ROOT, capture_output=True, check=False
    )
    assert result.returncode == 0, f"{candidate} would be committable"
