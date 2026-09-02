from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.chain.vault import vault

# Domain separation. The vault key also signs evidence chains, and a signature
# is only a statement about bytes — without a prefix saying WHICH kind of
# document those bytes are, a signature produced over one could in principle be
# presented as a signature over the other. The prefix is inside the signed
# payload, so it cannot be stripped or swapped after the fact.
DOMAIN = b"isnad-number-registry-v1\n"

SIGNATURE_SUFFIX = ".sig"


class RegistryTampered(Exception):
    """A signature is present and does not match the file.

    Deliberately fatal. A MISSING signature is an unsigned development file — a
    posture question. A signature that is present and WRONG is somebody having
    edited a list that decides which phone numbers belong to which bank, and
    those are different facts that must not share a code path.
    """


@dataclass(frozen=True)
class SignatureFile:
    algorithm: str
    public_key: str
    signature: str
    sha256: str
    signed_at: str


def payload_for(registry_bytes: bytes) -> bytes:
    return DOMAIN + registry_bytes


def sign_bytes(registry_bytes: bytes) -> SignatureFile:
    payload = payload_for(registry_bytes)
    return SignatureFile(
        algorithm="Ed25519",
        public_key=vault.public_key_hex(),
        signature=vault.sign(payload),
        sha256=hashlib.sha256(registry_bytes).hexdigest(),
        signed_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def signature_path(registry_path: Path) -> Path:
    return registry_path.with_name(registry_path.name + SIGNATURE_SUFFIX)


def write(registry_path: Path) -> SignatureFile:
    record = sign_bytes(registry_path.read_bytes())
    signature_path(registry_path).write_text(
        json.dumps(record.__dict__, indent=2) + "\n", encoding="utf-8"
    )
    return record


def verify(registry_path: Path, required: bool = False) -> str | None:
    """Check the registry against its signature.

    Returns None when a signature is present and valid, or a human-readable
    reason when there is nothing to check. Raises RegistryTampered when a
    signature is present and does not verify.
    """
    path = signature_path(registry_path)
    if not path.exists():
        if required:
            raise RegistryTampered(f"{path} is missing and a signature is required")
        return "unsigned (no .sig file)"

    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        signature = record["signature"]
        public_key = record["public_key"]
    except (json.JSONDecodeError, KeyError, OSError) as err:
        # An unreadable signature file is treated as tampering, not as an
        # absent one. "I could not parse the proof" must never be the cheaper
        # path than "the proof failed".
        raise RegistryTampered(f"{path} is unreadable: {err}") from None

    # The key must be one this deployment vouches for. Verifying with whatever
    # key the signature file names would let an attacker who can write both
    # files re-sign the registry with a key they generated and have it pass.
    if not vault.trusts(public_key):
        raise RegistryTampered(f"{path} is signed by a key this deployment does not trust")
    if not vault.verify_with(public_key, payload_for(registry_path.read_bytes()), signature):
        raise RegistryTampered(f"{registry_path} does not match {path}")
    return None
