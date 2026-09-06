"""The consent and retention posture, published.

§0.8.5 Q9 is the sharpest question available to a regional executive: *you HMAC
subscriber numbers and query their location — which regulator permits that, and
who carries the exposure?* Every element of the answer already existed —
`chain/subject.py` binds to an HMAC instead of a number, every EvidenceLink
carries the consent basis it was gathered under, and `retention.py` deletes what
is past its window — and none of it was visible on any surface. A privacy
property nobody can inspect is indistinguishable from a claim.

Everything here is derived from live settings rather than written as prose, for
the same reason the counterfactual refuses to invent a price: a hard-coded
"one hour" becomes a lie the first time somebody tunes the window.

The endpoint is deliberately public. It discloses no fact about any subject —
only what this deployment does and does not keep, which is the kind of thing a
privacy notice is supposed to state out loud. It is rate limited per address.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.api.rate_limit import limit_per_ip
from app.config import settings

router = APIRouter(tags=["privacy"], dependencies=[Depends(limit_per_ip)])

_PAGE = Path(__file__).parent.parent / "static" / "privacy.html"


def _human(seconds: int) -> str:
    """Format the window where the number lives, not in the page.

    The page deliberately holds no duration arithmetic: a literal like 3600 in
    the markup is the seed of a page that keeps saying "one hour" after someone
    changes the window.
    """
    if seconds % 3600 == 0 and seconds >= 3600:
        hours = seconds // 3600
        return f"{hours} hour" + ("" if hours == 1 else "s")
    if seconds % 60 == 0:
        return f"{seconds // 60} minutes"
    return f"{seconds} seconds"


@router.get("/v1/privacy/posture")
async def posture(request: Request) -> dict:
    """What this deployment keeps, for how long, and what it never holds."""
    await limit_per_ip(request)
    return {
        "subject_binding": {
            # The number is the input, never the stored value. This is what lets
            # a signed verdict be published (T6 does exactly that) while still
            # being provably about one subscriber to anyone who can supply the
            # number and ask.
            "method": "HMAC-SHA256 under a server-side pepper",
            "stored": "a 64-character binding",
            "not_stored": "the phone number itself, in the signed payload or the receipt",
        },
        "evidence": {
            "normalized": (
                "Providers return a normalized EvidenceLink. No raw CAMARA payload, "
                "coordinate, or operator-supplied string reaches the reasoning layer "
                "or is persisted."
            ),
            "consent_recorded_per_link": True,
            "consent_bases_in_use": sorted(_CONSENT_BASES),
        },
        "retention": [
            {
                "name": "screen_events",
                "seconds": settings.velocity_retention_seconds,
                "human": _human(settings.velocity_retention_seconds),
                "why": (
                    "They answer one question about the recent past — how many "
                    "different people has this number reached. Kept longer they "
                    "become a record of who was screened against whom, for no benefit."
                ),
            },
            {
                "name": "call_announcements",
                "seconds": settings.announce_max_ttl_seconds,
                "human": _human(settings.announce_max_ttl_seconds),
                "why": "An institution saying who it is about to ring. Useless after the call.",
            },
            {
                "name": "challenge_followups",
                "seconds": settings.challenge_followup_retention_seconds,
                "human": _human(settings.challenge_followup_retention_seconds),
                "why": (
                    "What a merchant reported after a CHALLENGE decision. Kept for "
                    "dispute resolution, not indefinitely."
                ),
            },
        ],
        "sweeper": {
            "enabled": settings.purge_interval_seconds > 0,
            "interval_seconds": settings.purge_interval_seconds,
            # Named because it was once true and is the kind of thing that
            # quietly becomes true again.
            "note": "Both purge functions once existed with no caller, so nothing was deleted.",
        },
        "limits": [
            (
                "Consent is recorded as the basis a check was gathered under. It is not "
                "a substitute for a lawful basis assessment in any jurisdiction."
            ),
            (
                "No MENA regulator currently mandates cryptographic caller attestation. "
                "Saudi Arabia's CST mandated caller name and identity display from "
                "1 October 2023, which is a display-layer requirement, not attestation."
            ),
            (
                "A deployment serving real subscribers must complete its own regulatory "
                "assessment per market. This page describes the software's behaviour, "
                "not a legal opinion."
            ),
        ],
    }


# The vocabulary the providers actually stamp on a link, read once at import so
# the page lists what this build can emit rather than a maintained guess.
def _consent_bases() -> set[str]:
    from app.providers.mock import _CONSENT

    return {basis for basis in _CONSENT.values() if basis and basis != "n/a"} | {
        "NaC authorization / end-user consent"
    }


_CONSENT_BASES = _consent_bases()


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page() -> HTMLResponse:
    return HTMLResponse(_PAGE.read_text(encoding="utf-8"))
