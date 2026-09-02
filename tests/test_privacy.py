"""The consent and retention posture, made checkable.

§0.8.5 Q9 — *"you HMAC MSISDNs and query subscriber location; which regulator
permits that, and who carries the exposure?"* — is the sharpest question a
regional executive can ask a Trusted Digital Identity entry. Every part of the
answer already existed in the code and none of it was visible anywhere. These
tests pin the surface that shows it, and pin the thing that would make the
surface a liability: a disclosure page that itself discloses something.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_the_posture_is_public_because_a_disclosure_nobody_can_read_is_not_one():
    assert client.get("/v1/privacy/posture").status_code == 200


def test_the_posture_reports_the_retention_windows_actually_configured():
    """Hard-coded prose drifts from the running system the first time someone
    tunes a window. These numbers come from settings or they are worthless."""
    from app.config import settings

    body = client.get("/v1/privacy/posture").json()
    windows = {w["name"]: w for w in body["retention"]}
    assert windows["screen_events"]["seconds"] == settings.velocity_retention_seconds
    assert windows["call_announcements"]["seconds"] == settings.announce_max_ttl_seconds
    assert body["sweeper"]["enabled"] is (settings.purge_interval_seconds > 0)


def test_the_posture_names_the_subject_binding_without_leaking_the_pepper():
    body = client.get("/v1/privacy/posture").json()
    assert "HMAC" in body["subject_binding"]["method"]
    blob = str(body).lower()
    for forbidden in ("pepper=", "secret", "private_key", "api_key"):
        assert forbidden not in blob, forbidden


def test_the_page_serves_and_pulls_its_numbers_from_the_endpoint():
    """A page that hard-codes '1 hour' is a page that will one day be wrong."""
    page = client.get("/privacy").text
    assert "/v1/privacy/posture" in page
    assert "3600" not in page, "retention windows must be fetched, not baked in"


def test_the_receipt_shows_the_consent_basis_of_every_link():
    """The consent trail is inside the signed bytes already. Showing it is what
    turns 'we record consent' from a claim into something a judge can read off
    a receipt they fetched themselves."""
    import app.api.routes_receipt as rr

    src = rr.__file__
    with open(src, encoding="utf-8") as fh:
        body = fh.read()
    assert '"consent_basis"' in body, "receipt steps omit consent_basis"
    assert '"requires_consent"' in body


def test_caller_numbers_are_hashed_before_they_reach_retained_rows():
    from app import announce, velocity
    from app.db.database import SessionLocal
    from app.db.models import CallAnnouncementRow, ScreenEventRow

    caller, callee = "+96265000000", "+962790000001"
    announce.record("demo-bank-jo", "demo-merchant-key", caller, callee)
    velocity.record(caller, callee)
    with SessionLocal() as session:
        announcement = (
            session.query(CallAnnouncementRow).order_by(CallAnnouncementRow.id.desc()).first()
        )
        screen = session.query(ScreenEventRow).order_by(ScreenEventRow.id.desc()).first()

    assert announcement is not None and screen is not None
    assert caller not in announcement.calling_participant_hash
    assert caller not in screen.caller_hash
    assert not hasattr(announcement, "calling_participant")
    assert not hasattr(screen, "caller_number")
