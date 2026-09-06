"""Whether a caller is a browser navigating or a script fetching.

Extracted from routes_consent (P4a), where this first appeared, so the proof
share route (I13) uses the same implementation rather than a second copy that
could drift from it.
"""

from __future__ import annotations


def accept_quality(accept: str, media_type: str) -> float:
    """The q-value Accept assigns to an exact media type (no wildcard credit).

    A `*/*` or `text/*` entry does not count toward a specific type's score
    here — "prefers html" must mean an explicit `text/html`, not a browser's
    catch-all fallback, or "wildcard-only... keep JSON" would break.
    """
    best = 0.0
    for part in accept.split(","):
        part = part.strip()
        if not part:
            continue
        type_part, *params = part.split(";")
        if type_part.strip() != media_type:
            continue
        quality = 1.0
        for param in params:
            param = param.strip()
            if param.startswith("q="):
                try:
                    quality = float(param[2:])
                except ValueError:
                    quality = 1.0
        best = max(best, quality)
    return best


def prefers_html(accept: str | None) -> bool:
    """Whether a browser's Accept header prefers text/html over JSON.

    Absent, wildcard-only, or tied preferences all keep JSON — this only
    fires for an explicit, strictly higher preference for text/html, which is
    what an ordinary browser navigation (not a fetch()/curl/script client)
    sends.
    """
    if not accept:
        return False
    return accept_quality(accept, "text/html") > accept_quality(accept, "application/json")
