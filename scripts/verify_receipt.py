"""I7 — verify a downloaded Isnad receipt entirely offline.

Verifies the exact stored `signed_payload` bytes against the accompanying
signature and public key using the same Ed25519 library the server signs
with. No network call, no server-side trust decision reused: a valid
signature only proves issuance by whichever key is in the bundle -- pass
`--trusted-keys` with an independently obtained list to also check that the
key itself is one you trust.

An offline receipt proves past issuance and integrity. It says nothing about
current session status, current key trust (unless you supply a list), or
whether the underlying network evidence was true.

    .venv311/bin/python scripts/verify_receipt.py receipt.json
    .venv311/bin/python scripts/verify_receipt.py receipt.json --trusted-keys keys.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_BUNDLE_BYTES = 1_000_000
REQUIRED_FIELDS = ("signed_payload", "signature", "public_key")


class BundleError(ValueError):
    pass


def load_bundle(path: Path) -> dict:
    size = path.stat().st_size
    if size > MAX_BUNDLE_BYTES:
        raise BundleError(f"bundle is {size} bytes, over the {MAX_BUNDLE_BYTES}-byte limit")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BundleError(f"bundle is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise BundleError("bundle must be a JSON object")
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise BundleError(f"bundle is missing required field(s): {', '.join(missing)}")
    if not all(isinstance(data[f], str) for f in REQUIRED_FIELDS):
        raise BundleError("signed_payload, signature and public_key must all be strings")
    return data


def load_trusted_keys(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    keys = {line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    return keys


def verify(bundle: dict, trusted_keys: set[str] | None) -> tuple[bool, str]:
    public_key_hex = bundle["public_key"].strip().lower()
    if trusted_keys is not None and public_key_hex not in trusted_keys:
        return False, f"public key {public_key_hex} is not in the trusted-key file"

    try:
        key_bytes = bytes.fromhex(public_key_hex)
        signature_bytes = bytes.fromhex(bundle["signature"].strip())
    except ValueError as exc:
        return False, f"malformed hex in public_key or signature: {exc}"

    try:
        public_key = Ed25519PublicKey.from_public_bytes(key_bytes)
    except Exception as exc:  # noqa: BLE001 - any malformed key is a verification failure, not a crash
        return False, f"malformed public key: {exc}"

    # Verify the STORED bytes exactly as they arrived — never re-serialize
    # signed_payload through json.loads()/json.dumps() first, which is the
    # one mistake that would make an honestly-signed receipt look tampered.
    payload_bytes = bundle["signed_payload"].encode("utf-8")
    try:
        public_key.verify(signature_bytes, payload_bytes)
    except InvalidSignature:
        return False, "signature does not match the payload"

    return True, "signature matches the payload, under the supplied public key"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bundle", type=Path, help="a receipt JSON file downloaded from GET /v1/receipts/{chain_id}")
    parser.add_argument(
        "--trusted-keys",
        type=Path,
        default=None,
        help="a file of one hex Ed25519 public key per line; the bundle's key must be in it",
    )
    args = parser.parse_args()

    try:
        bundle = load_bundle(args.bundle)
        trusted_keys = load_trusted_keys(args.trusted_keys)
    except (BundleError, OSError) as exc:
        print(f"CANNOT VERIFY: {exc}", file=sys.stderr)
        return 2

    ok, reason = verify(bundle, trusted_keys)
    if ok:
        print(f"VALID — {reason}")
        print("This proves issuance and integrity at signing time only, not current status or network truth.")
        return 0
    print(f"INVALID — {reason}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
