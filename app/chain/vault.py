from __future__ import annotations

import hashlib
import hmac
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# Signing the stored verdict JSON makes each chain tamper-evident: any change to
# the decision, a link's result/detail, or their order invalidates the signature.


class MissingVaultKey(RuntimeError):
    """The signing key was expected on disk and was not there."""


class InsecureVaultKey(RuntimeError):
    """The signing key is readable by someone other than its owner."""


# The whole tamper-evidence pitch rests on this one file. It was written with no
# mode argument, so it inherited umask 022 and landed as 0644 — any local user or
# co-tenant process could read the signing key and forge chains that verify (S7b).
_KEY_FILE_MODE = 0o600
_KEY_DIR_MODE = 0o700


class VaultSigner:
    """Signs issued chains with Ed25519. The key is loaded from disk if present,
    otherwise generated and persisted so signatures stay verifiable across restarts.
    """

    def __init__(self, key_path: Path | None = None, allow_create: bool = True):
        self.key_path = resolve_key_path(key_path)
        self._key = self._load_or_create(self.key_path, allow_create)
        self._pub: Ed25519PublicKey = self._key.public_key()

    def configure(self, key_path: Path | None, allow_create: bool = True) -> None:
        """Load the configured signer into this stable module-level instance.

        Modules import ``vault`` by object reference.  Mutating that one object
        after startup posture validation lets those imports keep working without
        creating a persistent key during module import.
        """
        resolved = resolve_key_path(key_path)
        key = self._load_or_create(resolved, allow_create)
        self.key_path = resolved
        self._key = key
        self._pub = key.public_key()

    @staticmethod
    def _load_or_create(key_path: Path | None, allow_create: bool) -> Ed25519PrivateKey:
        if key_path and key_path.exists():
            _require_owner_only(key_path)
            return serialization.load_pem_private_key(
                key_path.read_bytes(), password=_key_passphrase()
            )  # type: ignore[return-value]
        if not allow_create:
            # Silently generating here is what turns a missing volume into every
            # stored chain reporting invalid on stage (S6). Refuse instead.
            raise MissingVaultKey(
                f"No signing key at {key_path}. Generating one would invalidate "
                f"every chain already issued. Mount the volume holding it, or "
                f"start once with ISNAD_PROVIDER=mock to create one deliberately."
            )
        key = Ed25519PrivateKey.generate()
        if key_path:
            key_path.parent.mkdir(parents=True, mode=_KEY_DIR_MODE, exist_ok=True)
            os.chmod(key_path.parent, _KEY_DIR_MODE)  # mkdir's mode is umask-masked
            passphrase = _key_passphrase()
            encryption = (
                serialization.BestAvailableEncryption(passphrase)
                if passphrase
                else serialization.NoEncryption()
            )
            pem = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption,
            )
            # O_EXCL so a concurrent start cannot race two keys into one path,
            # and the mode is passed to open() rather than applied afterwards so
            # the key is never briefly world-readable on disk.
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _KEY_FILE_MODE)
            try:
                os.write(fd, pem)
            finally:
                os.close(fd)
        return key

    def sign(self, payload: bytes) -> str:
        return self._key.sign(payload).hex()

    def verify(self, payload: bytes, signature_hex: str) -> bool:
        """Verify against the key this process is holding."""
        return _verify_with_key(self._pub, payload, signature_hex)

    def verify_with(self, public_key_hex: str, payload: bytes, signature_hex: str) -> bool:
        """Verify against the key that actually signed the record (S6).

        The route used to verify with whatever key this process happened to load
        while returning the record's own public_key beside the answer. Those are
        not the same key after a rotation or a restart from the wrong directory,
        and the mismatch reads on stage as the vault act failing.

        The record's key still has to be one we trust, or a forged row could
        carry its own key and its own signature and verify perfectly.
        """
        if not self.trusts(public_key_hex):
            return False
        try:
            pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        except ValueError:
            return False
        return _verify_with_key(pub, payload, signature_hex)

    def trusts(self, public_key_hex: str) -> bool:
        """Whether a public key is one this deployment vouches for.

        The live key, plus any listed in ISNAD_VAULT_TRUSTED_PUBLIC_KEYS — which
        is how a rotation keeps old chains verifiable instead of orphaning them.
        """
        candidates = {self.public_key_hex(), *_trusted_from_settings()}
        return any(hmac.compare_digest(public_key_hex, k) for k in candidates)

    def subject_pepper(self) -> bytes:
        """The secret a subject binding is computed under (S5).

        Configured explicitly in any real deployment. Derived from the signing
        key otherwise, so a local demo has one secret to persist rather than two
        that must be rotated together — the failure mode if they drift apart is
        identical to S6's, and one file is easier to get right than two.
        """
        if settings.subject_pepper:
            return settings.subject_pepper.encode("utf-8")
        raw = self._key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return hmac.new(raw, b"isnad/subject-pepper/v1", hashlib.sha256).digest()

    def public_key_hex(self) -> str:
        return self._pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()


def _key_passphrase() -> bytes | None:
    """Encrypt the key at rest when a passphrase is configured."""
    raw = settings.vault_key_passphrase
    return raw.encode("utf-8") if raw else None


def _require_owner_only(key_path: Path) -> None:
    """Refuse to load a signing key that anyone else can read (S7b).

    File mode is not enforced on Windows; the check is skipped there rather than
    failing on a platform where it means nothing.
    """
    if os.name != "posix":  # pragma: no cover - posix-only deployment
        return
    mode = key_path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise InsecureVaultKey(
            f"{key_path} is mode {oct(stat.S_IMODE(mode))}: readable beyond its "
            f"owner. Any local user could read the signing key and forge chains "
            f"that verify. Fix with: chmod 600 {key_path}"
        )


def _verify_with_key(pub: Ed25519PublicKey, payload: bytes, signature_hex: str) -> bool:
    try:
        pub.verify(bytes.fromhex(signature_hex), payload)
        return True
    except (InvalidSignature, ValueError):
        return False


def resolve_key_path(key_path: Path | None) -> Path | None:
    """Make the key path absolute (S6).

    The default is CWD-relative, so the same service started from a different
    directory looks healthy, quietly writes a second key, and then reports every
    previously signed chain as invalid. Anchoring a relative path to the package
    root instead of the process's working directory removes that.
    """
    if key_path is None:
        return None
    path = Path(key_path)
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parent.parent.parent / path).resolve()


def _trusted_from_settings() -> set[str]:
    raw = settings.vault_trusted_public_keys or ""
    return {k.strip() for k in raw.split(",") if k.strip()}


# Module-level signer.  It starts ephemeral on purpose: importing a route must
# never create a persistent signing key before the lifespan validates a billable
# deployment.  ``main.lifespan`` loads the configured key into this same object
# after ``check_startup_posture`` has confirmed it already exists.
from app.config import settings

vault = VaultSigner(None)
