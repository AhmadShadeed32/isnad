from __future__ import annotations

import re

import segno
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.api.rate_limit import limit_per_ip
from app.chain.vault import vault
from app.db import store
from app.ui import page_path

# T6 — a public, read-only receipt anyone can verify on their own phone.
#
# Judges verifying a chain themselves is worth more than any claim made about
# tamper-evidence, so the page does the Ed25519 check in the browser with
# WebCrypto against the public key, with no library and no external origin.

router = APIRouter(tags=["receipt"])
_RECEIPT_HTML = page_path("receipt")

# Fields the page is allowed to show. Everything else in the signed payload is
# available for verification but is not rendered.
PUBLIC_FIELDS = ("decision", "chain_grade", "confidence", "hypothesis", "planner")


@router.get("/v1/receipts/{chain_id}", tags=["receipt"])
async def receipt_data(chain_id: str, request: Request) -> dict:
    """The exact signed bytes, the signature, and the key that signed them.

    Public and unauthenticated on purpose: a receipt nobody can fetch cannot be
    verified by anybody. It is rate limited per address, and it carries no
    phone number, no merchant identity, and no reason string — see
    store.get_public_record for why that is safe.
    """
    await limit_per_ip(request)
    record = store.get_public_record(chain_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "chain_not_found", "message": "No such chain"},
        )
    verdict = record.verdict
    return {
        # I7's portable-download contract: lets an offline verifier and this
        # endpoint's shape evolve independently without guessing a version
        # from field presence.
        "schema_version": 1,
        "chain_id": chain_id,
        # The bytes as stored, so the browser verifies what was actually signed
        # rather than a re-serialization — the detail most implementations get
        # wrong, and one the runbook lists as already correct here.
        "signed_payload": record.verdict_json,
        "signature": record.signature,
        "public_key": record.public_key,
        "algorithm": "Ed25519",
        "key_trusted": vault.trusts(record.public_key),
        "signed_at": verdict.signed_at or record.signed_at,
        "summary": {
            "decision": verdict.decision.value,
            "chain_grade": verdict.chain_grade.value if verdict.chain_grade else None,
            "confidence": verdict.confidence,
            "hypothesis": verdict.hypothesis,
            "planner": verdict.planner,
            "steps": [
                # Signals only. `detail` is prose that on the NaC path carries
                # operator-supplied strings, so it is not part of what we render.
                {
                    "step": link.step,
                    "api": link.api,
                    "signal": link.signal,
                    "result": link.result.value,
                    # The basis this check was gathered under. Already inside the
                    # signed bytes; surfaced so the consent trail is something a
                    # reader can check rather than a claim made about the system.
                    "consent_basis": link.consent_basis,
                    "requires_consent": link.requires_consent,
                    # How far this link moved the belief. Already inside the signed
                    # bytes; surfaced here so the page can show the arithmetic.
                    "delta_logodds": link.delta_logodds,
                    # The window the question covered, not the age of the event —
                    # CAMARA returns a boolean, never a timestamp.
                    "max_age_hours": link.max_age_hours,
                }
                for link in verdict.chain
            ],
        },
        # Everything needed to redo the decision rather than take it on trust.
        # Every value is from the signed verdict — never today's mutable policy.
        #
        # prior_logodds is null for a chain signed before the field existed.
        # Serving 0.0 as if it were the real prior would be showing a number the
        # vault never attested.
        "arithmetic": {
            "prior_logodds": verdict.prior_logodds or None,
            "allow_below": verdict.policy_snapshot.get("allow_below"),
            "decline_above": verdict.policy_snapshot.get("decline_above"),
        },
    }


@router.get("/r/{chain_id}", response_class=HTMLResponse, include_in_schema=False)
async def receipt_page(chain_id: str, request: Request) -> HTMLResponse:
    """The page a judge opens from the QR code."""
    await limit_per_ip(request)
    html = _RECEIPT_HTML.read_text(encoding="utf-8")
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


_SVG_SIZE = re.compile(r'^<svg width="(\d+)" height="(\d+)"')


def _with_viewbox(svg: str) -> str:
    """Give the QR a viewBox so it scales with its container."""
    m = _SVG_SIZE.match(svg)
    if not m or "viewBox" in svg:
        return svg
    w, h = m.group(1), m.group(2)
    return svg.replace(m.group(0), f'{m.group(0)} viewBox="0 0 {w} {h}"', 1)


@router.get("/v1/receipts/{chain_id}/qr", tags=["receipt"])
async def receipt_qr(chain_id: str, request: Request) -> dict:
    """An inline SVG QR for this receipt's public URL.

    Generated server-side and returned as markup the console embeds directly:
    console.html must keep zero external origins, so no CDN QR library and no
    image host. segno is pure Python with no runtime dependencies.
    """
    await limit_per_ip(request)
    if store.get_public_record(chain_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "chain_not_found", "message": "No such chain"},
        )
    url = str(request.url_for("receipt_page", chain_id=chain_id))
    # Dark modules on a transparent ground, so the console can set a light
    # plate behind it. Light-on-dark scans badly on a lot of phone cameras,
    # and this QR only exists to be scanned off a screen.
    svg = segno.make(url, error="m").svg_inline(scale=4, dark="#0E1330", light=None)
    # segno emits width/height but no viewBox, and an SVG without one does not
    # scale: CSS sizing would crop the code rather than shrink it. The QR grows
    # with the URL, so a long public hostname would otherwise overflow the card.
    svg = _with_viewbox(svg)
    return {"chain_id": chain_id, "url": url, "svg": svg}
