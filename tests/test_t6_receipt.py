"""T6 — the public, independently verifiable receipt."""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi.testclient import TestClient

from app.config import settings
from app.db import store
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}
SUBJECT = "+962790000002"

RECEIPT_HTML = Path("app/static/receipt.html").read_text(encoding="utf-8")
CONSOLE_HTML = Path("app/static/console.html").read_text(encoding="utf-8")


@pytest.fixture
def chain_id() -> str:
    response = client.post(
        "/v1/verify",
        headers=AUTH,
        json={
            "phone_number": SUBJECT,
            "context": {
                "event": "checkout",
                "payment_method": "cod",
                "account_age_days": 0,
                "amount": {"value": 4200},
            },
        },
    )
    assert response.status_code == 200
    return response.json()["chain_id"]


# --- public and read-only -----------------------------------------------------


def test_the_receipt_is_readable_without_a_key(chain_id):
    """A receipt nobody can fetch cannot be verified by anybody."""
    assert client.get(f"/v1/receipts/{chain_id}").status_code == 200
    assert client.get(f"/r/{chain_id}").status_code == 200


def test_a_missing_chain_is_a_404_with_a_constant_message():
    response = client.get("/v1/receipts/chn_00000000000000000000")
    assert response.status_code == 404
    assert response.json()["detail"]["message"] == "No such chain"


def test_the_receipt_route_is_read_only(chain_id):
    for method in ("post", "put", "delete", "patch"):
        response = getattr(client, method)(f"/v1/receipts/{chain_id}")
        assert response.status_code == 405


# --- no PII -------------------------------------------------------------------


def test_the_receipt_contains_no_phone_number(chain_id):
    """The acceptance criterion."""
    body = client.get(f"/v1/receipts/{chain_id}").text

    assert SUBJECT not in body
    assert SUBJECT.lstrip("+") not in body
    # And no E.164-shaped string anywhere, not just this one.
    assert re.search(r'"\+\d{8,15}"', body) is None


def test_the_rendered_summary_exposes_signals_not_details(chain_id):
    """`detail` is prose that on the NaC path carries operator-supplied text."""
    summary = client.get(f"/v1/receipts/{chain_id}").json()["summary"]

    assert summary["steps"]
    for step in summary["steps"]:
        # An allow-list, not a length check: the point is that `detail` — prose
        # that on the NaC path carries operator-supplied strings — never
        # appears. delta_logodds is a float and carries no text.
        assert set(step) == {
            "step",
            "api",
            "signal",
            "result",
            "delta_logodds",
            "max_age_hours",
            # Added deliberately, and only because they are a bounded
            # vocabulary set by this codebase rather than text any provider can
            # put there. The consent trail is the answer to "which regulator
            # permits this", and an answer nobody can read off the receipt is
            # not an answer. The membership check below is what keeps this
            # widening safe: if a provider ever starts passing its own string
            # through consent_basis, that assertion goes red, not this one.
            "consent_basis",
            "requires_consent",
        }
        assert "detail" not in step
        assert isinstance(step["requires_consent"], bool)
        assert step["consent_basis"] in {
            "n/a",
            "simulator authorization",
            "3-legged CIBA token",
            "device reputation lookup",
            "NaC authorization / end-user consent",
        }, step["consent_basis"]


def test_the_receipt_does_not_say_which_merchant_it_belongs_to(chain_id):
    from app.ownership import owner_hash

    body = client.get(f"/v1/receipts/{chain_id}").text
    assert owner_hash("demo-merchant-key") not in body


def test_the_page_renders_no_reason_string():
    """S11's rule carried into T6: the reason is not part of the receipt."""
    assert "reason" not in RECEIPT_HTML.lower().split("<script>")[0]


# --- the signature actually verifies ------------------------------------------


def test_the_published_bytes_verify_against_the_published_key(chain_id):
    """What the browser does, done here: import the key, verify the bytes."""
    data = client.get(f"/v1/receipts/{chain_id}").json()

    key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(data["public_key"]))
    key.verify(bytes.fromhex(data["signature"]), data["signed_payload"].encode("utf-8"))


def test_one_flipped_bit_breaks_verification(chain_id):
    """The tamper control, and the reason it is worth putting on stage."""
    from cryptography.exceptions import InvalidSignature

    data = client.get(f"/v1/receipts/{chain_id}").json()
    payload = bytearray(data["signed_payload"].encode("utf-8"))
    payload[len(payload) // 2] ^= 0x01

    key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(data["public_key"]))
    with pytest.raises(InvalidSignature):
        key.verify(bytes.fromhex(data["signature"]), bytes(payload))


def test_the_published_bytes_are_the_stored_bytes_not_a_reserialization(chain_id):
    """Verifying a re-serialization is the detail most implementations get wrong."""
    from app.db import store

    record = store.get_public_record(chain_id)
    published = client.get(f"/v1/receipts/{chain_id}").json()["signed_payload"]

    assert published == record.verdict_json


def test_the_summary_agrees_with_the_signed_payload(chain_id):
    """The rendered summary must not be able to disagree with what was signed."""
    data = client.get(f"/v1/receipts/{chain_id}").json()
    signed = json.loads(data["signed_payload"])

    assert data["summary"]["decision"] == signed["decision"]
    assert data["summary"]["chain_grade"] == signed["chain_grade"]
    assert data["summary"]["confidence"] == signed["confidence"]
    assert [s["signal"] for s in data["summary"]["steps"]] == [
        link["signal"] for link in signed["chain"]
    ]


# --- the page itself ----------------------------------------------------------


def test_the_page_verifies_client_side_with_webcrypto_and_no_library():
    assert "crypto.subtle.importKey" in RECEIPT_HTML
    assert "'Ed25519'" in RECEIPT_HTML
    assert "crypto.subtle.verify" in RECEIPT_HTML


def test_the_page_has_a_tamper_control():
    assert 'id="tamperBtn"' in RECEIPT_HTML
    assert "^ 0x01" in RECEIPT_HTML  # flips one bit
    assert 'id="resetBtn"' in RECEIPT_HTML  # and can restore


def test_the_receipt_page_has_zero_external_origins():
    """The console's rule applies here too: a venue may be locked down."""
    assert re.findall(r'(?:src|href)\s*=\s*["\'](?:https?:)?//', RECEIPT_HTML) == []


def test_the_page_renders_untrusted_values_as_text_not_markup():
    script = RECEIPT_HTML.split("<script>")[-1].split("</script>")[0]
    for sink in (r"\.innerHTML\s*=", r"\.insertAdjacentHTML\s*\(", r"document\.write\s*\("):
        assert re.search(sink, script) is None, sink


def test_the_page_carries_security_headers(chain_id):
    headers = client.get(f"/r/{chain_id}").headers

    assert "content-security-policy" in headers
    assert headers["x-content-type-options"] == "nosniff"


# --- the QR -------------------------------------------------------------------


def test_the_qr_points_at_this_chains_receipt(chain_id):
    data = client.get(f"/v1/receipts/{chain_id}/qr").json()

    assert data["url"].endswith(f"/r/{chain_id}")
    assert data["svg"].startswith("<svg")


def test_the_qr_is_inline_svg_with_no_external_origin(chain_id):
    svg = client.get(f"/v1/receipts/{chain_id}/qr").json()["svg"]

    assert "http://" not in svg and "https://" not in svg
    assert "<image" not in svg


def test_the_qr_404s_for_an_unknown_chain():
    assert client.get("/v1/receipts/chn_00000000000000000000/qr").status_code == 404


def test_the_console_shows_the_qr_after_a_verdict():
    assert "showReceiptQr" in CONSOLE_HTML
    assert 'id="qrBox"' in CONSOLE_HTML


SVG_NS = "http://www.w3.org/2000/svg"


def test_the_qr_markup_renders_once_the_console_declares_the_namespace(chain_id):
    """The QR is served without an xmlns, so the console must add one.

    segno's svg_inline() omits the namespace deliberately: it is meant to be
    dropped straight into HTML, where the parser infers it. The console parses
    it as XML instead, and an undeclared root there lands in the *null*
    namespace — which still answers to nodeName 'svg', so it was appended and
    then laid out as an unknown inline element that drew nothing.
    """
    svg = client.get(f"/v1/receipts/{chain_id}/qr").json()["svg"]

    # As served: parses, but into no namespace at all — this is why it must
    # not be handed to DOMParser as-is.
    assert ET.fromstring(svg).tag == "svg"

    declared = svg.replace("<svg ", f'<svg xmlns="{SVG_NS}" ', 1)
    root = ET.fromstring(declared)
    assert root.tag == f"{{{SVG_NS}}}svg"
    assert root[0].tag == f"{{{SVG_NS}}}path"
    # Without a viewBox an SVG does not scale: CSS sizing crops it instead.
    assert root.get("viewBox")


def test_the_console_declares_the_svg_namespace_before_parsing():
    assert f"const SVG_NS = '{SVG_NS}'" in CONSOLE_HTML
    assert "'<svg xmlns=\"' + SVG_NS + '\" '" in CONSOLE_HTML
    assert "svg.namespaceURI === SVG_NS" in CONSOLE_HTML


# ---- the arithmetic (item 2 of the 31 Aug plan) ----


def test_the_receipt_publishes_everything_needed_to_redo_the_decision(chain_id):
    """A verdict a judge can recompute beats a verdict they must believe."""
    data = client.get(f"/v1/receipts/{chain_id}").json()
    arithmetic = data["arithmetic"]

    assert arithmetic["prior_logodds"] is not None
    assert arithmetic["allow_below"] and arithmetic["decline_above"]

    total = arithmetic["prior_logodds"] + sum(
        step["delta_logodds"] for step in data["summary"]["steps"]
    )
    p = 1 / (1 + math.exp(-total))
    assert p == pytest.approx(data["summary"]["confidence"], abs=0.001)

    expected = (
        "ALLOW"
        if p <= arithmetic["allow_below"]
        else "DECLINE"
        if p >= arithmetic["decline_above"]
        else "CHALLENGE"
    )
    assert expected == data["summary"]["decision"]


def test_the_threshold_snapshot_is_inside_the_signed_payload(chain_id):
    """A receipt must replay the issuing policy, not today's configuration."""
    data = client.get(f"/v1/receipts/{chain_id}").json()
    signed = json.loads(data["signed_payload"])

    assert signed["policy_snapshot"] == {
        "allow_below": data["arithmetic"]["allow_below"],
        "decline_above": data["arithmetic"]["decline_above"],
    }


def test_the_prior_is_inside_the_signed_bytes(chain_id):
    """Published beside the deltas but outside the signature, the starting point
    would be the one number in the chain nobody could check."""
    data = client.get(f"/v1/receipts/{chain_id}").json()
    assert '"prior_logodds"' in data["signed_payload"]


def test_a_chain_without_a_recorded_prior_reports_null_not_zero():
    """0.0 means "not recorded". Serving it as the real prior would show a
    number the vault never attested — the chain_grade rule, applied again."""
    from app.chain.models import Verdict
    from app.domain.enums import ChainGrade, Decision

    verdict = Verdict(
        decision=Decision.ALLOW,
        chain_grade=ChainGrade.ATTESTED_PARTIAL,
        confidence=0.05,
        hypothesis="legit",
        reason="",
        chain_id="chn_x",
    )
    assert verdict.prior_logodds == 0.0

    store.save(verdict)
    body = client.get("/v1/receipts/chn_x").json()
    assert body["arithmetic"]["prior_logodds"] is None


def test_the_receipt_page_shows_the_arithmetic_and_flags_a_mismatch():
    assert 'id="mathCard"' in RECEIPT_HTML
    assert "renderArithmetic" in RECEIPT_HTML
    # It must say so when its own sum disagrees with the signed decision rather
    # than quietly rendering the server's answer.
    assert "MISMATCH" in RECEIPT_HTML


def test_the_receipt_reports_the_window_asked_about_not_an_event_age():
    """CAMARA's SIM Swap and Device Swap take a max_age and return a BOOLEAN.

    Verified against the real recorded responses in docs/nac/, which carry no
    timestamp of any kind. So "the swap was four hours ago" is not a fact this
    system can state, and the field must never be presented as one.
    """
    from app.domain.enums import Action
    from app.providers.nac import _window_hours

    assert _window_hours(Action.SIM_SWAP) == float(settings.nac_max_age_hours)
    assert _window_hours(Action.DEVICE_SWAP) == float(settings.nac_max_age_hours)
    # Reachability and roaming ask about now; there is no window to report, and
    # inventing one would be worse than the honest absence.
    assert _window_hours(Action.REACHABILITY) is None
    assert _window_hours(Action.ROAMING) is None


def test_no_recorded_camara_response_carries_a_timestamp():
    """The evidence for the claim above, pinned so a future SDK that DOES return
    an event time is noticed rather than silently ignored."""
    for path in Path("docs/nac").glob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8")).get("raw", {})
        assert not any(key in raw for key in ("date", "timestamp", "swapped_at", "last_swap")), (
            f"{path.name} now carries an event time — evidence age could be real"
        )
