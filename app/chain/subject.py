from __future__ import annotations

import hashlib
import hmac
from typing import Any

from app.chain.vault import vault

# What a signed verdict is evidence *of* (S5).
#
# The signed payload used to contain no phone number, no merchant, no request and
# no timestamp, so the signature proved only that this server once issued this
# verdict about something. A merchant in a COD dispute could present a clean
# ALLOW / ATTESTED_FULL chain obtained for any other number and it would verify.
#
# The binding is an HMAC under a server-side pepper rather than the number
# itself, which keeps the no-PII property of the chain intact: the payload is
# safe to publish (T6 does exactly that) and still says who it is about to
# anyone who can supply the number and ask.


def subject_hash(e164: str) -> str:
    """Bind a verdict to the number it was issued about."""
    return hmac.new(vault.subject_pepper(), e164.encode("utf-8"), hashlib.sha256).hexdigest()


def owner_binding(api_key_hash: str) -> str:
    """Bind a verdict to the merchant it was issued for.

    Peppered rather than the bare sha256 the database column uses. The payload
    becomes public on the receipt page, and a bare hash of a merchant key is an
    offline guessing target if anyone ever configures a weak one.
    """
    return hmac.new(
        vault.subject_pepper(), api_key_hash.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def request_commitment(request: Any) -> str:
    """Create a keyed, domain-separated commitment to a request.

    A bare SHA-256 of predictable E.164 JSON is a public receipt oracle: anyone
    can enumerate likely requests and compare their digest.  The commitment is
    signed with the verdict but remains non-enumerable without the server-side
    pepper.  ``model_dump_json`` provides one canonical representation for all
    Pydantic request models used by API routes.
    """
    if hasattr(request, "model_dump_json"):
        payload = request.model_dump_json().encode("utf-8")
    elif isinstance(request, bytes):
        payload = request
    elif isinstance(request, str):
        payload = request.encode("utf-8")
    else:
        raise TypeError("request commitment requires a Pydantic model, str, or bytes")
    return hmac.new(
        vault.subject_pepper(), b"isnad/request-commitment/v1\0" + payload, hashlib.sha256
    ).hexdigest()


def matches(verdict_subject_hash: str, e164: str) -> bool:
    """Whether a stored chain was really issued about this number."""
    if not verdict_subject_hash:
        return False
    return hmac.compare_digest(verdict_subject_hash, subject_hash(e164))
