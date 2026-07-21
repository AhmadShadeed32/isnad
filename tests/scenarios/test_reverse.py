"""Reverse Isnad — verify an inbound caller to the customer (Act IV)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.routes_reverse import run_reverse
from app.domain.enums import Decision
from app.main import app
from app.providers.mock import MockProvider

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


@pytest.mark.asyncio
async def test_genuine_caller_is_trusted():
    """The real institution line is network-attested -> TRUST (ALLOW)."""
    verdict = await run_reverse("+96265000000", MockProvider())
    assert verdict.decision == Decision.ALLOW
    assert verdict.hypothesis == "impersonation"


@pytest.mark.asyncio
async def test_spoofed_caller_is_rejected():
    """A spoofed 'bank officer' fails network attestation -> REJECT (DECLINE)."""
    verdict = await run_reverse("+96279999999", MockProvider())
    assert verdict.decision == Decision.DECLINE
    signals = {link.signal for link in verdict.chain}
    assert "NUMBER_MISMATCH" in signals  # caller ID not on the network device


def test_reverse_endpoint_maps_trust_vocabulary():
    r = client.post(
        "/v1/reverse-verify",
        headers=AUTH,
        json={"caller_number": "+96279999999", "claimed_identity": "Bank of Jordan"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["trust"] == "REJECT_CALLER"
    assert "Bank of Jordan" in body["reason"]
    assert body["chain"]  # chain returned by default


def test_reverse_endpoint_requires_auth():
    r = client.post(
        "/v1/reverse-verify",
        json={"caller_number": "+96265000000", "claimed_identity": "Bank of Jordan"},
    )
    assert r.status_code == 401
