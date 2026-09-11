"""Restore the Space's stable signing identity, then start one app worker."""

from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

SECRET_NAME = "ISNAD_VAULT_PRIVATE_KEY_B64"


def restore_signer() -> None:
    encoded = os.environ.pop(SECRET_NAME, "")
    if not encoded:
        return  # Existing mounted keys and the app's startup guards still apply.
    try:
        pem = base64.b64decode(encoded, validate=True)
        key = serialization.load_pem_private_key(pem, password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise TypeError("wrong key type")
    except (ValueError, TypeError, UnsupportedAlgorithm):
        raise RuntimeError("The Space signing-key secret is invalid") from None

    configured_path = os.environ.get("ISNAD_VAULT_KEY_PATH", "")
    path = Path(configured_path)
    if not configured_path or not path.is_absolute():
        raise RuntimeError("The Space needs an absolute ISNAD_VAULT_KEY_PATH")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    if path.is_symlink():
        raise RuntimeError("The Space signing-key path must not be a symlink")
    if path.exists():
        if path.read_bytes() != pem:
            raise RuntimeError("The mounted signing key differs from the Space secret")
        os.chmod(path, 0o600)
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(pem)


if __name__ == "__main__":
    restore_signer()
    os.execvp("uvicorn", [
        "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860",
        "--workers", "1", "--no-access-log", "--proxy-headers",
        "--limit-concurrency", "128", "--timeout-graceful-shutdown", "30",
    ])
