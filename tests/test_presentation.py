"""P2 — app/presentation.py: a deterministic, plain-language projection of an
already-signed Verdict. See docs/PHASE2_HANDOFF.md, package P2.

Real synthetic Verdicts come from running the actual investigator over the
console's own DEMO_ACTS fixtures (mock provider, greedy planner — same as the
suite's baseline), never hand-typed, so these tests exercise the same
decision/grade combinations the judge page actually shows: act3 (ALLOW /
ATTESTED_FULL), act6 (CHALLENGE / DEGRADED — the SIM-replacement,
budget-exhausted case), act2 (DECLINE / REFUTED), act5 (CHALLENGE / UNRESOLVED
— the withheld-consent, provider-dark case).
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.agent.investigator import build_investigator
from app.api.routes_console import DEMO_ACTS
from app.chain.models import EvidenceLink, Verdict
from app.domain.enums import Action, ChainGrade, Decision, Result
from app.events import subscribe
from app.main import app
from app.ownership import owner_hash
from app.presentation import MAX_FACTS, Presentation, present
from app.providers.mock import MockProvider

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


def _run_act(act: str) -> Verdict:
    return asyncio.run(build_investigator(MockProvider()).investigate(DEMO_ACTS[act]))


def _facts_known_to_the_chain(verdict: Verdict) -> set[str]:
    return {f"{link.api}: {link.detail}" for link in verdict.chain}


# --- the display mapping, kept separate from the signed enum -----------------


def test_allow_maps_to_proceed():
    verdict = _run_act("act3")
    assert verdict.decision == Decision.ALLOW  # the real fixture, not assumed
    assert present(verdict).title == "Proceed"


def test_challenge_maps_to_additional_verification_needed():
    verdict = _run_act("act6")
    assert verdict.decision == Decision.CHALLENGE
    assert present(verdict).title == "Additional verification needed"


def test_decline_maps_to_do_not_proceed():
    verdict = _run_act("act2")
    assert verdict.decision == Decision.DECLINE
    assert present(verdict).title == "Do not proceed"


# --- no invented facts: every fact traces to an actual link ------------------


@pytest.mark.parametrize("act", ["act2", "act3", "act5", "act6"])
def test_every_displayed_fact_traces_to_a_real_link_in_the_chain(act):
    verdict = _run_act(act)
    presentation = present(verdict)
    known = _facts_known_to_the_chain(verdict)

    for fact in (
        presentation.supporting_facts + presentation.adverse_facts + presentation.unresolved_checks
    ):
        assert fact in known, f"invented fact not in the chain: {fact!r}"


def test_supporting_facts_are_exactly_the_pass_results():
    verdict = _run_act("act6")
    presentation = present(verdict)
    expected = {f"{l.api}: {l.detail}" for l in verdict.chain if l.result == Result.PASS}

    assert presentation.supporting_facts  # act6 has real corroboration
    assert set(presentation.supporting_facts) == expected


def test_adverse_facts_are_exactly_the_flag_results():
    verdict = _run_act("act6")
    presentation = present(verdict)
    expected = {f"{l.api}: {l.detail}" for l in verdict.chain if l.result == Result.FLAG}

    assert presentation.adverse_facts  # act6's SIM swap
    assert set(presentation.adverse_facts) == expected


# --- CHALLENGE must be explained specifically, not with one generic line -----


def test_the_degraded_corroboration_case_is_not_described_as_a_consent_failure():
    """Act VI-shaped: the score lands between thresholds after every check
    that ran was resolved. Not a consent failure."""
    verdict = _run_act("act6")
    assert verdict.chain_grade == ChainGrade.DEGRADED
    presentation = present(verdict)

    assert not presentation.unresolved_checks  # nothing was actually unavailable
    assert "not a case of withheld consent" in presentation.summary
    assert "not a failed identity check" in presentation.summary


def test_the_unresolved_provider_case_names_the_specific_unavailable_checks():
    """Act V-shaped: consent withheld and a provider that cannot answer. The
    presenter must name what specifically could not be obtained."""
    verdict = _run_act("act5")
    assert verdict.chain_grade == ChainGrade.UNRESOLVED
    presentation = present(verdict)

    assert presentation.unresolved_checks
    for check in presentation.unresolved_checks:
        assert check in presentation.summary
    # It is the network's own vocabulary describing an absence, not this
    # module inventing what the customer refused or what the provider said.
    for link in verdict.chain:
        if link.signal in {"CONSENT_REQUIRED", "PROVIDER_UNAVAILABLE", "EVIDENCE_UNAVAILABLE"}:
            assert f"{link.api}: {link.detail}" in presentation.unresolved_checks


def test_the_two_challenge_cases_read_differently():
    """The acceptance criterion: not one generic CHALLENGE message."""
    degraded = present(_run_act("act6"))
    unresolved = present(_run_act("act5"))

    assert degraded.summary != unresolved.summary
    assert degraded.title == unresolved.title == "Additional verification needed"


def test_missing_support_without_any_unresolved_signal_does_not_name_a_check():
    """If metadata cannot establish exactly why the engine stopped (thin
    corroboration, nothing actually failed), the presenter must omit that
    claim rather than guess at a specific check."""
    chain = [
        EvidenceLink(
            step=1,
            action=Action.NUMBER_VERIFY,
            api="Number Verification",
            result=Result.PASS,
            signal="NUMBER_MATCH",
            detail="network number matches the provided number",
            source="mock",
        ),
    ]
    verdict = Verdict(
        decision=Decision.CHALLENGE,
        chain_grade=ChainGrade.UNRESOLVED,
        confidence=0.05,
        hypothesis="legit_thin_file",
        reason="",
        chain_id="chn_missing_support_only",
        chain=chain,
    )
    presentation = present(verdict)

    assert not presentation.unresolved_checks
    assert "No single check failed" in presentation.summary
    assert "Number Verification" not in presentation.summary


def test_a_challenge_never_reads_like_an_isnad_sent_otp():
    """The done bar: cannot be mistaken for a one-time code Isnad itself sent."""
    for act in ("act5", "act6"):
        presentation = present(_run_act(act))
        assert presentation.title == "Additional verification needed"
        lowered = presentation.next_action.lower()
        assert "isnad" in lowered
        assert "has not sent" in lowered or "does not send" in lowered


def test_no_temporal_age_is_invented_from_a_bounded_window():
    """CAMARA's swap APIs answer a boolean against a window, never a
    timestamp. A 240-hour window must never become 'three days ago'."""
    verdict = _run_act("act6")  # carries a real SIM_SWAPPED link
    presentation = present(verdict)
    text = " ".join(
        [presentation.summary, *presentation.adverse_facts, *presentation.supporting_facts]
    )

    for banned in ("days ago", "hours ago", "minutes ago", "yesterday", "recently"):
        assert banned not in text.lower()
    assert any("the last 240" in fact for fact in presentation.adverse_facts)


# --- decision/grade combinations that do not occur in the fixed demo acts ----


def test_decline_with_an_unresolved_link_does_not_claim_direct_contradiction():
    """grade() checks `unresolved` before `decline_above` (see
    app/policy/engine.py), so DECLINE can pair with UNRESOLVED. The REFUTED
    "directly contradicted" language must not leak into that combination."""
    chain = [
        EvidenceLink(
            step=1,
            action=Action.SIM_SWAP,
            api="SIM Swap",
            result=Result.INFO,
            signal="PROVIDER_UNAVAILABLE",
            detail="provider request failed",
            source="mock",
        ),
    ]
    verdict = Verdict(
        decision=Decision.DECLINE,
        chain_grade=ChainGrade.UNRESOLVED,
        confidence=0.9,
        hypothesis="account_takeover",
        reason="",
        chain_id="chn_decline_unresolved",
        chain=chain,
    )
    presentation = present(verdict)

    assert "directly contradicted" not in presentation.summary
    assert presentation.unresolved_checks == ["SIM Swap: provider request failed"]
    assert presentation.title == "Do not proceed"


def test_an_ungraded_legacy_verdict_does_not_claim_a_grade():
    """A chain signed before chain_grade existed. None must not be served as
    if it were a real grade (same rule Verdict.chain_grade's own docstring
    states)."""
    verdict = Verdict(
        decision=Decision.ALLOW,
        chain_grade=None,
        confidence=0.02,
        hypothesis="legit",
        reason="",
        chain_id="chn_ungraded",
        chain=[],
    )
    presentation = present(verdict)

    assert "before chain grading existed" in presentation.summary
    assert presentation.title == "Proceed"


def test_an_older_chain_with_no_policy_snapshot_gets_no_threshold_sentence():
    """policy_snapshot can be {} on a chain signed before it existed. The
    DEGRADED threshold context must be omitted, not defaulted to today's
    live policy."""
    chain = [
        EvidenceLink(
            step=1,
            action=Action.SIM_SWAP,
            api="SIM Swap",
            result=Result.FLAG,
            signal="SIM_SWAPPED",
            detail="SIM swap inside the last 240 h",
            source="mock",
        ),
    ]
    verdict = Verdict(
        decision=Decision.CHALLENGE,
        chain_grade=ChainGrade.DEGRADED,
        confidence=0.4,
        hypothesis="legit",
        reason="",
        chain_id="chn_no_snapshot",
        chain=chain,
        policy_snapshot={},
    )
    presentation = present(verdict)

    assert "policy snapshot" not in presentation.summary
    assert "allows automatically" not in presentation.summary


# --- caps ----------------------------------------------------------------


def test_facts_are_capped_at_max_facts():
    chain = [
        EvidenceLink(
            step=i + 1,
            action=Action.NUMBER_VERIFY,
            api="Number Verification",
            result=Result.PASS,
            signal="NUMBER_MATCH",
            detail=f"network number matches the provided number ({i})",
            source="mock",
        )
        for i in range(MAX_FACTS + 3)
    ]
    verdict = Verdict(
        decision=Decision.ALLOW,
        chain_grade=ChainGrade.ATTESTED_FULL,
        confidence=0.01,
        hypothesis="legit",
        reason="",
        chain_id="chn_capped",
        chain=chain,
    )
    presentation = present(verdict)

    assert len(presentation.supporting_facts) == MAX_FACTS


# --- the signed Verdict is never touched --------------------------------


def test_verdict_model_has_no_presentation_field():
    """The signed model itself was never touched. `presentation` lives only
    on VerificationResponse, which is not the object vault.sign() ever sees."""
    assert "presentation" not in Verdict.model_fields


def test_present_does_not_mutate_the_verdict_it_is_given():
    verdict = _run_act("act6")
    before = verdict.model_dump_json()

    presentation = present(verdict)

    assert verdict.model_dump_json() == before
    assert isinstance(presentation, Presentation)


def test_signed_bytes_carry_no_presentation_key():
    """What store.save() actually signs (verdict.model_dump_json()) is
    unaffected by presentation ever having been computed -- byte-for-byte."""
    verdict = _run_act("act6")
    present(verdict)  # computed once, as the SSE emit path now does

    signed_json = verdict.model_dump_json()

    assert '"presentation"' not in signed_json


# --- HTTP and SSE agree -----------------------------------------------------


@pytest.mark.asyncio
async def test_http_response_and_sse_verdict_event_carry_the_same_presentation():
    owner = owner_hash("demo-merchant-key")
    events: list[dict] = []

    async def collect():
        async for event in subscribe(owner):
            events.append(event)
            if event.get("type") == "verdict":
                return

    task = asyncio.create_task(collect())
    await asyncio.sleep(0.05)  # let the subscriber register before the run starts

    response = client.post(
        "/v1/verify",
        headers={**AUTH, "X-Console-Run-Id": "presentation-agreement-test"},
        json={
            "phone_number": "+99999991006",
            "context": {
                "event": "checkout",
                "payment_method": "cod",
                "account_age_days": 0,
                "amount": {"value": 1500},
                "claimed_location": {"lat": 31.9539, "lon": 35.9106, "radius_m": 2000},
            },
        },
    )
    await asyncio.wait_for(task, timeout=2.0)

    assert response.status_code == 200
    body = response.json()
    assert events and events[-1]["type"] == "verdict"
    assert events[-1]["presentation"] == body["presentation"]
    assert body["presentation"]["title"] == "Additional verification needed"


# --- old cached responses without the field still work -----------------------


def test_a_response_missing_presentation_still_parses_and_defaults_to_none():
    """A response cached (or a client built) before this field existed."""
    from app.domain.schemas import VerificationResponse

    legacy = {
        "decision": "CHALLENGE",
        "planner": "greedy",
        "confidence": 0.242,
        "hypothesis": "legit",
        "reason": "some earlier reason text",
        "chain_id": "chn_legacy",
    }
    response = VerificationResponse.model_validate(legacy)

    assert response.presentation is None
    assert response.reason == "some earlier reason text"  # the documented UI fallback


def test_the_console_run_endpoint_carries_the_same_presentation_as_verify():
    """P2 requires both the consent flow and ordinary verification to use the
    same projection function. console_run (the judge page's fixture path) is
    a third caller of the same present() -- confirm it agrees too."""
    body = client.post("/v1/console/run/act6", headers=AUTH).json()

    assert "presentation" in body
    assert body["presentation"]["title"] == "Additional verification needed"
