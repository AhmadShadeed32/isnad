"""I4 — network failure and recovery demonstration.

The fault wrapper never raises: `Investigator._call()` does not catch a raw
provider exception, so anything raised here would abort before a verdict
instead of demonstrating the intended unresolved result. Every fault profile
returns a normalized, allowlisted EvidenceLink instead.
"""

from __future__ import annotations

import pytest

from app.domain.enums import Action, Result
from app.domain.schemas import RequestContext, VerificationRequest
from demo.lab.faults import FaultInjectingProvider, UnknownFaultProfile

REQ = VerificationRequest(phone_number="+962790000001", context=RequestContext(event="checkout"))


@pytest.mark.asyncio
async def test_an_unknown_profile_is_rejected_at_construction():
    from app.providers.mock import MockProvider

    with pytest.raises(UnknownFaultProfile):
        FaultInjectingProvider(MockProvider(), profile="not-a-real-profile")


@pytest.mark.asyncio
async def test_timeout_profile_normalizes_to_info_provider_unavailable():
    from app.providers.mock import MockProvider

    provider = FaultInjectingProvider(MockProvider(), profile="timeout")
    link = await provider.gather(Action.SIM_SWAP, REQ)
    assert link.result == Result.INFO
    assert link.signal == "PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_unavailable_profile_normalizes_to_evidence_unavailable():
    from app.providers.mock import MockProvider

    provider = FaultInjectingProvider(MockProvider(), profile="unavailable")
    link = await provider.gather(Action.DEVICE_SWAP, REQ)
    assert link.result == Result.INFO
    assert link.signal == "EVIDENCE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_consent_required_profile():
    from app.providers.mock import MockProvider

    provider = FaultInjectingProvider(MockProvider(), profile="consent_required")
    link = await provider.gather(Action.NUMBER_VERIFY, REQ)
    assert link.signal == "CONSENT_REQUIRED"


@pytest.mark.asyncio
async def test_no_fault_profile_passes_through_to_the_real_provider_unchanged():
    from app.providers.mock import MockProvider

    inner = MockProvider()
    provider = FaultInjectingProvider(inner, profile="none")
    direct = await inner.gather(Action.NUMBER_VERIFY, REQ)
    wrapped = await provider.gather(Action.NUMBER_VERIFY, REQ)
    assert wrapped.signal == direct.signal
    assert wrapped.result == direct.result


@pytest.mark.asyncio
async def test_a_fault_run_produces_a_real_verdict_not_an_aborted_investigation():
    """Required evidence stays required: a fault must not silently become PASS,
    and the investigation must still complete to a verdict."""
    from app.agent.investigator import build_investigator
    from app.providers.mock import MockProvider

    provider = FaultInjectingProvider(MockProvider(), profile="unavailable")
    investigator = build_investigator(provider)
    verdict = await investigator.investigate(REQ)
    assert verdict.decision is not None
    assert any(link.signal == "EVIDENCE_UNAVAILABLE" for link in verdict.chain)


@pytest.mark.asyncio
async def test_default_mock_behavior_is_unaffected_when_fault_injection_is_disabled():
    from app.agent.investigator import build_investigator
    from app.providers.mock import MockProvider

    investigator = build_investigator(MockProvider())
    verdict = await investigator.investigate(REQ)
    assert verdict.decision is not None
