from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# Signing the stored verdict JSON makes each chain tamper-evident: any change to
# the decision, a link's result/detail, or their order invalidates the signature.


class VaultSigner:
    """Signs issued chains with Ed25519. The key is loaded from disk if present,
    otherwise generated and persisted so signatures stay verifiable across restarts.
    """

    def __init__(self, key_path: Optional[Path] = None):
        self._key = self._load_or_create(key_path)
        self._pub: Ed25519PublicKey = self._key.public_key()

    @staticmethod
    def _load_or_create(key_path: Optional[Path]) -> Ed25519PrivateKey:
        if key_path and key_path.exists():
            return serialization.load_pem_private_key(key_path.read_bytes(), password=None)  # type: ignore[return-value]
        key = Ed25519PrivateKey.generate()
        if key_path:
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_bytes(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        return key

    def sign(self, payload: bytes) -> str:
        return self._key.sign(payload).hex()

    def verify(self, payload: bytes, signature_hex: str) -> bool:
        try:
            self._pub.verify(bytes.fromhex(signature_hex), payload)
            return True
        except (InvalidSignature, ValueError):
            return False

    def public_key_hex(self) -> str:
        return self._pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


# Module-level signer, keyed from config.
from app.config import settings  # noqa: E402  (after class to avoid import cycle)

vault = VaultSigner(settings.vault_key_path)
