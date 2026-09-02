from __future__ import annotations

import hashlib

# One definition of "who does this belong to", shared by the event bus (S2), the
# chain and session stores (S3), and the consent store, which already used this
# exact construction. An API key is a bearer secret, so nothing keeps the key
# itself — only a hash of it, which is enough to compare two callers and not
# enough to impersonate one from a database dump.

# A distinguishable owner for anything issued outside a request — a background
# task, a unit test calling emit() directly. It is not derived from any key, so
# it can never collide with a real owner.
ANONYMOUS = "anonymous"


def owner_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
