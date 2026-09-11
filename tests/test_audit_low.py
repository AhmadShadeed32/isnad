"""The LOW cluster from the 31 Aug security audit.

Individually small. Together they are the shape of things that are fine until
the day they are not: a timing side channel on the one comparison that decides
who may speak for a bank, an anonymous caller with a higher allowance than a
paying one, caller text validated only for length, a KeyError waiting under a
call that has not been made yet, a naive/aware datetime trap, and a documented
per-request option no route ever passed.
"""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from app import announce
from app.config import settings
from app.db.database import SessionLocal
from app.db.models import CallAnnouncementRow
from app.domain.enums import Action
from app.main import app
from app.policy.engine import get_engine

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


def _engine():
    return get_engine(str(settings.policy_path))


# ---- the institution binding is compared in constant time ----


def test_the_institution_binding_still_resolves(monkeypatch):
    monkeypatch.setattr(settings, "institution_keys", "k1:bank-a,k2:bank-b", raising=False)
    assert announce.institution_for_key("k1") == "bank-a"
    assert announce.institution_for_key("k2") == "bank-b"


def test_a_wrong_key_speaks_for_nobody(monkeypatch):
    """It fails closed, and it does so without an early exit: this comparison
    decides whether a caller may announce a call as a bank, so a plain `==`
    leaks the shared prefix length through timing."""
    monkeypatch.setattr(settings, "institution_keys", "k1:bank-a", raising=False)
    for candidate in ("k", "k1x", "", "K1"):
        assert announce.institution_for_key(candidate) is None


def test_an_unbound_deployment_binds_nothing(monkeypatch):
    monkeypatch.setattr(settings, "institution_keys", "", raising=False)
    assert announce.institution_for_key("k1") is None


# ---- an anonymous screen does not get the raised ceiling ----


def test_an_unauthenticated_screen_uses_the_per_ip_ceiling(monkeypatch):
    """The 600/min screen bucket is for identified callers. Unauthenticated
    requests fell into it too, giving an anonymous caller a higher allowance
    than any authenticated route grants a paying one."""
    from app.api import rate_limit

    monkeypatch.setattr(settings, "rate_limit_enabled", True, raising=False)
    monkeypatch.setattr(rate_limit.per_ip, "limit", 2, raising=False)
    monkeypatch.setattr(rate_limit.per_screen, "limit", 10_000, raising=False)
    rate_limit.per_ip.reset()
    rate_limit.per_screen.reset()

    body = {"caller_number": "+96265000000", "callee_number": "+962790000001"}
    codes = [client.post("/v1/screen", json=body).status_code for _ in range(4)]
    rate_limit.per_ip.reset()
    assert 429 in codes, f"anonymous screens were never limited: {codes}"


# ---- caller text is constrained by shape, not only by length ----


@pytest.mark.parametrize(
    "claim",
    [
        "<img src=x onerror=alert(1)>",
        "Demo Bank\nX-Injected: yes",
        'Demo "Bank"',
    ],
)
def test_a_screen_claim_outside_the_charset_is_rejected(claim):
    body = {
        "caller_number": "+96265000000",
        "callee_number": "+962790000001",
        "claimed_identity": claim,
    }
    assert client.post("/v1/screen", json=body, headers=AUTH).status_code == 422


def test_an_ordinary_claim_still_passes():
    body = {
        "caller_number": "+96265000000",
        "callee_number": "+962790000001",
        "claimed_identity": "Demo Bank, Fraud Dept.",
    }
    assert client.post("/v1/screen", json=body, headers=AUTH).status_code == 200


# ---- local evidence is free, not a KeyError ----


def test_local_actions_are_priced_at_zero_rather_than_raising():
    """policy.yaml prices no `actions:` entry for them — they are answered from
    local state and never offered to the planner — so `action_cost` raised
    KeyError for anything that reached it with one."""
    engine = _engine()
    for action in (Action.REGISTRY_CHECK, Action.CALL_ANNOUNCEMENT):
        assert engine.action_cost(action) == 0.0
        assert engine.action_gain(action) == 0.0
        assert engine.action_friction(action) == 0.0


def test_an_action_the_policy_forgot_still_raises():
    """Free is the price of local evidence, not a blanket default. A network
    action missing from policy.yaml is a broken policy file and must say so."""
    from app.policy.engine import PolicyEngine

    # Its own instance: `get_engine` is cached and shared by the whole suite.
    engine = PolicyEngine(settings.policy_path)
    engine.cfg["actions"].pop("roaming")
    with pytest.raises(KeyError):
        engine.action_cost(Action.ROAMING)


# ---- datetimes come back aware ----


def test_a_stored_datetime_reads_back_timezone_aware():
    """SQLite's DATETIME ignores tzinfo, so an aware UTC value was written and
    read back NAIVE. Subtracting one of those from an aware `now` raises
    TypeError — correct today, a trap under every future "how long is left"."""
    announce.record(
        institution_id="demo-bank-jo",
        api_key="demo-merchant-key",
        calling_participant="+96265000000",
        called_participant="+962790000001",
        display_name="Demo Bank",
    )
    with SessionLocal() as session:
        row = (
            session.query(CallAnnouncementRow)
            .order_by(CallAnnouncementRow.created_at.desc())
            .first()
        )
        assert row.expires_at.tzinfo is not None
        assert row.created_at.tzinfo is not None
        # The trap itself: this used to raise.
        assert (row.expires_at - dt.datetime.now(dt.UTC)).total_seconds() < 400


# ---- parallel gathering is reachable per request ----


def test_a_caller_can_ask_for_parallel_gathering():
    """policy.yaml says "opt in per request, never globally" and no route let
    anyone do that, so the only way in was the policy-wide default the comment
    warns against."""
    body = {
        "phone_number": "+99999991000",
        "context": {
            "event": "checkout",
            "payment_method": "cod",
            "account_age_days": 0,
            "amount": {"value": 4200},
        },
        "options": {"return_chain": True, "parallel": True},
    }
    parallel = client.post("/v1/verify", json=body, headers=AUTH).json()

    body["options"]["parallel"] = False
    sequential = client.post("/v1/verify", json=body, headers=AUTH).json()

    # Parallel buys latency by paying for evidence sequential might never have
    # needed — that trade is the whole reason it is opt-in.
    assert parallel["evidence_steps"] >= sequential["evidence_steps"]


def test_the_default_is_still_sequential():
    body = {
        "phone_number": "+99999991000",
        "context": {
            "event": "checkout",
            "payment_method": "cod",
            "account_age_days": 0,
            "amount": {"value": 4200},
        },
    }
    default = client.post("/v1/verify", json=body, headers=AUTH).json()
    body["options"] = {"parallel": False}
    explicit = client.post("/v1/verify", json=body, headers=AUTH).json()
    assert default["evidence_steps"] == explicit["evidence_steps"]
