"""Verified Caller — the PBX/SIP answer, and the two tiers around it.

No CAMARA API can attest a call from a bank's SIP trunk: SIM Swap, Number
Verification, Device Swap, Reachability, Roaming and Location Verification are
all facts about a MOBILE SUBSCRIPTION, and a trunk has no SIM. CAMARA's own
VerifiedCaller sub-project inverts the question instead — the institution
announces the call from an authenticated channel, and the callee's check asks
whether a matching announcement exists.

The tests that matter most here are the ones asserting what CANNOT produce a
verified result, because the failure mode of this whole feature is a mechanism
that verifies the attack it was built to catch.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import announce
from app.config import settings
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}

BANK_NUMBER = "+96265000000"  # Demo Bank switchboard, outbound: true
BANK_HOTLINE = "+96280022222"  # published inbound-only
CUSTOMER = "+962790000001"


@pytest.fixture(autouse=True)
def _no_leftover_announcements():
    """The suite shares one in-memory database, so an announcement made by one
    test verifies calls in the next one. Every "this must NOT verify" assertion
    below would pass for the wrong reason without this."""
    from app.db.database import SessionLocal
    from app.db.models import CallAnnouncementRow

    with SessionLocal() as session:
        session.query(CallAnnouncementRow).delete()
        session.commit()
    yield


@pytest.fixture
def bound_key(monkeypatch):
    """demo-merchant-key, bound to the institution that owns BANK_NUMBER."""
    monkeypatch.setattr(
        settings, "institution_keys", "demo-merchant-key:demo-bank-jo", raising=False
    )
    return AUTH


@pytest.fixture
def two_bank_registry(tmp_path, monkeypatch):
    """A registry holding Demo Bank and one other institution.

    The shipped registry has a single institution, so nothing in it can name a
    DIFFERENT indexed institution — which is the only thing the screen is
    allowed to call a claim mismatch.
    """
    import yaml

    from app.registry.directory import get_directory

    path = tmp_path / "registry.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "institutions": [
                    {
                        "id": "demo-bank-jo",
                        "name": "Demo Bank",
                        "country": "JO",
                        "basis": "demo_fixture",
                        "source": "test fixture",
                        "numbers": [{"number": BANK_NUMBER, "kind": "landline", "outbound": True}],
                    },
                    {
                        "id": "other-bank-jo",
                        "name": "Other Bank",
                        "country": "JO",
                        "basis": "demo_fixture",
                        "source": "test fixture",
                        "numbers": [
                            {"number": "+96265111111", "kind": "landline", "outbound": True}
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "registry_path", str(path), raising=False)
    yield path
    get_directory.cache_clear()


def _announce(headers, **overrides):
    body = {
        "callingParticipant": BANK_NUMBER,
        "calledParticipant": CUSTOMER,
        "strategy": "BRAND_DISPLAY",
    }
    body.update(overrides)
    return client.post("/v1/verified-caller/pre-announce", json=body, headers=headers)


def _screen(caller=BANK_NUMBER, callee=CUSTOMER, claimed=""):
    return client.post(
        "/v1/screen",
        json={"caller_number": caller, "callee_number": callee, "claimed_identity": claimed},
        headers=AUTH,
    ).json()


# ---- who may announce ----


def test_an_unbound_key_cannot_announce_a_call():
    """The binding IS the mechanism. Without it anyone holding any key could
    announce a call "from" a bank and have their own spoofed call verified —
    the feature inverts into the attack it exists to stop."""
    response = _announce(AUTH)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "not_an_institution"


def test_an_institution_cannot_announce_from_another_institutions_number(bound_key):
    response = _announce(bound_key, callingParticipant="+96279999999")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "number_not_yours"


def test_a_published_inbound_only_number_cannot_be_announced_from(bound_key):
    """The institution's own entry says it never originates calls there.
    Accepting it would let the strongest spoof signal verify itself."""
    response = _announce(bound_key, callingParticipant=BANK_HOTLINE)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "inbound_only_number"


def test_the_institution_comes_from_the_key_not_the_body(bound_key):
    body = _announce(bound_key).json()
    assert body["institution_id"] == "demo-bank-jo"


# ---- the announcement window ----


def test_the_requested_window_is_capped(bound_key, monkeypatch):
    """The window IS the spoofing opportunity: while an announcement stands, a
    call presenting that number verifies. So a caller must not be able to ask
    for a long one.

    Asserted against a ceiling LOWER than the request. The old version asked for
    300 and asserted the answer was <= 300, the configured maximum, which is
    true whether the cap runs or not.
    """
    assert _announce(bound_key, timeToLive=99999).status_code == 422  # schema ceiling

    monkeypatch.setattr(settings, "announce_max_ttl_seconds", 30, raising=False)
    body = _announce(bound_key, timeToLive=300).json()
    assert body["time_to_live_seconds"] == 30, "the requested window was granted"

    # And the stored row agrees with the number in the response.
    import datetime as dt

    from app.db.database import SessionLocal
    from app.db.models import CallAnnouncementRow

    with SessionLocal() as session:
        row = (
            session.query(CallAnnouncementRow)
            .order_by(CallAnnouncementRow.created_at.desc())
            .first()
        )
    left = (row.expires_at - dt.datetime.now(dt.UTC)).total_seconds()
    assert 0 < left <= 30


def test_an_expired_announcement_does_not_verify(bound_key, monkeypatch):
    """The window is the spoofing opportunity: while an announcement stands, a
    call presenting that number verifies."""
    monkeypatch.setattr(settings, "announce_ttl_seconds", 1, raising=False)
    monkeypatch.setattr(settings, "announce_max_ttl_seconds", 1, raising=False)
    _announce(bound_key, timeToLive=1)

    import datetime as dt

    from app.db.database import SessionLocal
    from app.db.models import CallAnnouncementRow

    # Age the row rather than sleeping — a test that waits is a test that is
    # sometimes flaky and always slow.
    with SessionLocal() as session:
        row = (
            session.query(CallAnnouncementRow)
            .order_by(CallAnnouncementRow.created_at.desc())
            .first()
        )
        row.expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
        session.commit()

    assert announce.find(BANK_NUMBER, CUSTOMER) is None
    assert _screen()["label"] == "UNKNOWN"


def test_an_announcement_is_bound_to_both_ends(bound_key):
    """Matching the caller alone would let one genuine announcement verify a
    burst of spoofed calls to everyone else for as long as its window stood."""
    _announce(bound_key)
    assert _screen(callee=CUSTOMER)["label"] == "VERIFIED_INSTITUTION"
    assert _screen(callee="+962790009999")["label"] == "UNKNOWN"


def test_the_callee_is_stored_only_as_a_hash(bound_key):
    """An institution announcing a call is telling this service who it is about
    to ring. A plaintext column would turn that into a customer list."""
    _announce(bound_key)
    from app.db.database import SessionLocal
    from app.db.models import CallAnnouncementRow

    with SessionLocal() as session:
        rows = session.query(CallAnnouncementRow).all()
    assert rows
    assert all(CUSTOMER not in row.called_participant_hash for row in rows)
    assert all(len(row.called_participant_hash) == 64 for row in rows)


# ---- Tier 1: what can and cannot produce a verified label ----


def test_an_announced_call_screens_as_verified(bound_key):
    _announce(bound_key)
    body = _screen()
    assert body["label"] == "VERIFIED_INSTITUTION"
    assert body["basis"] == "pre_announcement"
    assert body["tier"] == 1


def test_a_registry_hit_alone_is_never_verified():
    """The load-bearing test of this whole feature.

    Caller ID is spoofable, so a scammer presenting the bank's real number
    produces exactly the same registry hit a genuine call does. Returning
    "verified" here would build a machine that trusts the attack.
    """
    body = _screen()
    assert body["label"] == "UNKNOWN"
    assert body["basis"] == "registry_match_unannounced"


def test_a_published_inbound_only_line_screens_as_spoof():
    body = _screen(caller=BANK_HOTLINE)
    assert body["label"] == "SUSPECTED_SPOOF"
    assert body["basis"] == "registry_inbound_only"


def test_a_claim_naming_another_indexed_institution_screens_as_spoof(two_bank_registry):
    """The mismatch that is real: this number is Demo Bank's, and the caller
    says they are the other bank in the registry."""
    body = _screen(claimed="Other Bank")
    assert body["label"] == "SUSPECTED_SPOOF"
    assert body["basis"] == "registry_claim_mismatch"


def test_a_claim_the_registry_has_never_heard_of_is_not_a_spoof_verdict():
    """ "Arab Bank" is not in the registry, so the registry knows nothing about
    whether this caller is it. Calling that a mismatch labelled honest callers
    SUSPECTED_SPOOF for naming an institution nobody had curated yet — and the
    same comparison feeds REGISTRY_CLAIM_MISMATCH into the signed chain."""
    body = _screen(claimed="Arab Bank")
    assert body["label"] == "UNKNOWN"
    assert body["basis"] == "registry_match_unannounced"


def test_a_caller_who_names_their_department_is_not_a_spoof_verdict():
    """The shape that broke: every extra honest word made condemnation more
    likely, because the claim's words all had to be indexed."""
    for claim in ("Demo Bank customer service", "Demo Bank Ltd", "Demo Bank, Fraud Dept."):
        body = _screen(claimed=claim)
        assert body["label"] == "UNKNOWN", claim
        assert body["basis"] == "registry_match_unannounced", claim


def test_an_unlisted_number_screens_as_unknown_not_spoof():
    """Absence from a hand-curated registry is not evidence. Almost every number
    in the world is missing from it and innocent."""
    body = _screen(caller="+96279999999")
    assert body["label"] == "UNKNOWN"
    assert body["basis"] == "no_local_evidence"


def test_tier_one_makes_no_network_call(monkeypatch):
    """It runs in front of a ringing phone. Observed CAMARA latencies are
    346-863ms per call and the agent gathers sequentially, so a real chain is
    well over a second — this path must not touch one.

    A provider that EXPLODES if it is asked for anything, rather than a latency
    bound: a fast local answer is what you would see anyway if the call were
    made and the mock answered instantly, so the timing assertion could not tell
    the two apart. This one can.
    """
    from app import providers
    from app.api import deps

    class _Forbidden:
        async def gather(self, action, request):  # pragma: no cover
            raise AssertionError(f"Tier 1 called the network for {action}")

    def _explode(**kwargs):
        raise AssertionError("Tier 1 resolved a network provider")

    # BOTH names. `app.api.deps` does `from app.providers import get_provider`
    # at import time, so patching the source module alone leaves the name the
    # routes actually call untouched — a spy that never fires, in the rewrite of
    # a test flagged for asserting nothing.
    monkeypatch.setattr(providers, "get_provider", _explode)
    monkeypatch.setattr(deps, "get_provider", _explode)

    body = _screen()
    assert body["tier"] == 1
    assert body["label"] in ("UNKNOWN", "VERIFIED_INSTITUTION", "SUSPECTED_SPOOF")
    assert body["elapsed_us"] < 100_000  # generous; typically ~1ms


# ---- Tier 2: the same evidence inside a signed chain ----


@pytest.mark.asyncio
async def test_tier_two_carries_the_announcement_as_a_chain_link(bound_key):
    from app.api.routes_reverse import run_reverse
    from app.providers.mock import MockProvider

    _announce(bound_key)
    verdict = await run_reverse(
        BANK_NUMBER,
        MockProvider(),
        callee_number=CUSTOMER,
        claimed_identity="Demo Bank",
    )
    signals = [link.signal for link in verdict.chain]
    assert "CALL_PRE_ANNOUNCED" in signals
    # It must be IN the chain, not a note beside it: a verdict that turned on
    # the announcement has to be able to show it, inside the signed payload.
    assert verdict.chain[0].signal == "CALL_PRE_ANNOUNCED"


@pytest.mark.asyncio
async def test_a_registry_match_alone_does_not_move_belief():
    """REGISTRY_MATCH_UNANNOUNCED is zeroed in policy.yaml on purpose."""
    from app.api.routes_reverse import run_reverse
    from app.providers.mock import MockProvider

    with_registry = await run_reverse(BANK_NUMBER, MockProvider(), claimed_identity="Demo Bank")
    link = next(link for link in with_registry.chain if link.signal == "REGISTRY_MATCH_UNANNOUNCED")
    assert link.delta_logodds == 0.0


@pytest.mark.asyncio
async def test_the_spoofed_caller_still_rejects_with_local_evidence_added():
    """Act IV must not regress: adding local evidence to the chain must not
    rescue a caller the network already contradicts."""
    from app.api.routes_reverse import run_reverse
    from app.domain.enums import Decision
    from app.providers.mock import MockProvider

    verdict = await run_reverse("+96279999999", MockProvider(), claimed_identity="Demo Bank")
    assert verdict.decision == Decision.DECLINE
    assert "REGISTRY_UNLISTED" in [link.signal for link in verdict.chain]


@pytest.mark.asyncio
async def test_an_announcement_cannot_outvote_a_network_contradiction(bound_key, monkeypatch):
    """The combination that matters: the bank's real number, announced, but the
    network says the call is not coming from that line. An announcement is
    strong evidence, not a trump card.
    """
    from app.agent import investigator as investigator_module
    from app.agent.planner import Choice, GreedyPlanner
    from app.api.routes_reverse import run_reverse
    from app.domain.enums import Action, Decision, Result
    from app.providers.mock import MockProvider

    class _StopsImmediately:
        """A planner that stops the moment belief is decisive — which is what
        the LLM planner's own prompt tells it to do.

        Without this the test pinned nothing: greedy never stops, so the
        invariant held for the wrong reason and the same test passed while the
        console (which runs llm) skipped the network entirely. That is exactly
        the C1 regression, and this stub is what would have caught it.
        """

        source = "llm"

        def __init__(self, engine):
            self.engine = engine

        def choose(self, hypothesis, used, budget_left, p_fraud, observations):
            return Choice(None, "stub: belief has moved decisively", self.source)

        def next_best(self, hypothesis, used, budget_left):
            return None

        def cheapest_stepup(self, used, budget_left):
            return GreedyPlanner(self.engine).cheapest_stepup(used, budget_left)

    monkeypatch.setattr(
        investigator_module, "get_planner", lambda engine: _StopsImmediately(engine)
    )

    # The bank's real number, announced — and a network that says the call is
    # not coming from that line.
    contradicted = {
        BANK_NUMBER: {
            Action.NUMBER_VERIFY: (
                Result.FLAG,
                "NUMBER_MISMATCH",
                "caller ID is not associated with this device",
            ),
            Action.SIM_SWAP: (Result.FLAG, "SIM_SWAPPED", "swap detected 20 min ago"),
            Action.REACHABILITY: (
                Result.FLAG,
                "REACHABLE_BOTPATTERN",
                "VoIP / burner pattern",
            ),
        }
    }

    _announce(bound_key, calledParticipant=CUSTOMER)
    verdict = await run_reverse(
        BANK_NUMBER,
        MockProvider(scenarios=contradicted),
        callee_number=CUSTOMER,
        claimed_identity="Demo Bank",
    )
    signals = [link.signal for link in verdict.chain]
    assert "CALL_PRE_ANNOUNCED" in signals, "the announcement should be in the chain"
    # The announcement did not buy a free pass past the network.
    assert any(link.source != "local" for link in verdict.chain)
    assert "NUMBER_MISMATCH" in signals
    # And it did not outvote what the network said.
    assert verdict.decision != Decision.ALLOW


# ---- announcement reuse cap (item 5 of the 31 Aug plan) ----


def test_an_announcement_verifies_one_call_not_a_burst(bound_key):
    """An announcement described ONE call.

    It was already bound to both ends, so a different victim was never
    verifiable by it. What was unbounded is the same victim being rung
    repeatedly inside the window: a genuine announcement for a call to Alice
    also verified an attacker who spoofed the number and called Alice during
    those 45 seconds.
    """
    _announce(bound_key)
    assert _screen()["label"] == "VERIFIED_INSTITUTION"
    assert _screen()["label"] == "UNKNOWN"
    assert _screen()["label"] == "UNKNOWN"


def test_a_reader_that_never_screened_cannot_inspect_an_announcement(bound_key):
    """A non-spending read is for a party that already holds the use. Anyone
    else gets nothing — otherwise somebody else's announcement is readable."""
    _announce(bound_key)
    assert announce.find(BANK_NUMBER, CUSTOMER, consume=False) is None


@pytest.mark.asyncio
async def test_an_announcement_is_worth_one_verification_not_two(bound_key):
    """Both tiers consume. A client uses Tier 1 OR Tier 2 for a given call, and
    whichever runs first gets the credit.

    A non-spending read on the evidence path let a party replay somebody else's
    announcement into unlimited signed, publicly fetchable TRUST_CALLER receipts
    for a bank's number.
    """
    from app.api.deps import owner_for
    from app.api.routes_reverse import run_reverse
    from app.events import current_owner
    from app.providers.mock import MockProvider

    _announce(bound_key)
    assert _screen()["label"] == "VERIFIED_INSTITUTION"  # Tier 1 spends it

    # Uses are PER READER, so the direct call has to run as the same tenant the
    # screen ran as — otherwise this would be a different reader getting its own
    # use, which is the intended behaviour and not what is being tested here.
    current_owner.set(owner_for("demo-merchant-key"))
    verdict = await run_reverse(
        BANK_NUMBER,
        MockProvider(),
        callee_number=CUSTOMER,
        claimed_identity="Demo Bank",
    )
    assert "CALL_PRE_ANNOUNCED" not in [link.signal for link in verdict.chain]


@pytest.mark.asyncio
async def test_tier_two_alone_still_gets_the_announcement(bound_key):
    """The standalone reverse-verify path must keep working — it is a public API
    in its own right, not only a follow-on from a screen."""
    from app.api.routes_reverse import run_reverse
    from app.providers.mock import MockProvider

    _announce(bound_key)
    verdict = await run_reverse(
        BANK_NUMBER,
        MockProvider(),
        callee_number=CUSTOMER,
        claimed_identity="Demo Bank",
    )
    assert "CALL_PRE_ANNOUNCED" in [link.signal for link in verdict.chain]


@pytest.mark.asyncio
async def test_a_replayed_chain_cannot_be_minted_twice(bound_key):
    """The H3 exploit: one announcement, repeated reverse-verify calls, each
    minting a signed public TRUST_CALLER receipt for the bank's number."""
    from app.api.routes_reverse import run_reverse
    from app.providers.mock import MockProvider

    _announce(bound_key)
    first = await run_reverse(BANK_NUMBER, MockProvider(), callee_number=CUSTOMER)
    second = await run_reverse(BANK_NUMBER, MockProvider(), callee_number=CUSTOMER)
    assert "CALL_PRE_ANNOUNCED" in [link.signal for link in first.chain]
    assert "CALL_PRE_ANNOUNCED" not in [link.signal for link in second.chain]


def test_a_second_announcement_gives_a_second_call(bound_key):
    """The cap is per announcement, not a lockout. A bank that really is calling
    twice announces twice."""
    _announce(bound_key)
    assert _screen()["label"] == "VERIFIED_INSTITUTION"
    _announce(bound_key)
    assert _screen()["label"] == "VERIFIED_INSTITUTION"
