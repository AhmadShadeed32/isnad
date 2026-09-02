"""One real CAMARA call inside an otherwise-scripted chain.

Every winner found of this hackathon series demoed on a live network;
Isnad's demo makes none. The hybrid provider makes exactly
one designated link genuinely live, so the judge page's `LIVE · Nokia NaC`
badge sits beside `simulator` badges in the same signed chain and the
provenance feature stops being decorative.

The rule that matters most here is the fallback: a demo that dies because a
network blipped is strictly worse than one that degrades and says so.
"""

from __future__ import annotations

import pytest

from app.chain.models import EvidenceLink
from app.domain.enums import Action, Result
from app.domain.schemas import Money, RequestContext, VerificationRequest

REQUEST = VerificationRequest(
    phone_number="+99999991000",
    context=RequestContext(amount=Money(value=1500, currency="USD"), channel="checkout"),
)


def _link(source: str) -> EvidenceLink:
    return EvidenceLink(
        step=1,
        action=Action.SIM_SWAP,
        api="SIM Swap",
        result=Result.FLAG,
        signal="SIM_SWAP_RECENT",
        detail="no swap in the last 240 hours",
        source=source,
    )


class _Stub:
    def __init__(self, source, boom=False):
        self.source, self.boom, self.calls = source, boom, 0

    async def gather(self, action, request):
        self.calls += 1
        if self.boom:
            raise RuntimeError("network blipped")
        return _link(self.source)


def _hybrid(live, mock, actions="sim_swap", numbers="+99999991000"):
    from app.providers.hybrid import HybridProvider

    return HybridProvider(live=live, fallback=mock, actions=actions, numbers=numbers)


@pytest.mark.asyncio
async def test_the_designated_action_and_number_goes_live():
    live, mock = _Stub("nac"), _Stub("mock")
    link = await _hybrid(live, mock).gather(Action.SIM_SWAP, REQUEST)
    assert link.source == "nac"
    assert (live.calls, mock.calls) == (1, 0)


@pytest.mark.asyncio
async def test_every_other_action_stays_scripted():
    """Exactly ONE live link. The rest of the chain must stay deterministic, or
    the flagship act becomes a live-network dependency rather than a demo."""
    live, mock = _Stub("nac"), _Stub("mock")
    link = await _hybrid(live, mock).gather(Action.DEVICE_SWAP, REQUEST)
    assert link.source == "mock"
    assert (live.calls, mock.calls) == (0, 1)


@pytest.mark.asyncio
async def test_another_number_stays_scripted():
    live, mock = _Stub("nac"), _Stub("mock")
    other = REQUEST.model_copy(update={"phone_number": "+99999991002"})
    link = await _hybrid(live, mock).gather(Action.SIM_SWAP, other)
    assert link.source == "mock"
    assert (live.calls, mock.calls) == (0, 1)


@pytest.mark.asyncio
async def test_a_live_failure_falls_back_to_the_fixture_rather_than_breaking():
    """The whole point. On stage, an exception here is a dead demo."""
    live, mock = _Stub("nac", boom=True), _Stub("mock")
    link = await _hybrid(live, mock).gather(Action.SIM_SWAP, REQUEST)
    assert link.source == "mock"
    assert (live.calls, mock.calls) == (1, 1)


@pytest.mark.asyncio
async def test_no_configuration_means_no_live_call_at_all():
    """The resting state is fully scripted: someone who sets ISNAD_PROVIDER
    without naming an action must not start spending money by surprise.

    Note for whoever refactors `_is_live`: this assertion currently holds
    structurally — empty sets make the membership test false — so it does NOT
    go red on its own if a guard is removed. It is here as a contract on the
    behaviour, not as cover for any particular line."""
    live, mock = _Stub("nac"), _Stub("mock")
    link = await _hybrid(live, mock, actions="", numbers="").gather(Action.SIM_SWAP, REQUEST)
    assert link.source == "mock"
    assert live.calls == 0


# --- startup posture: hybrid spends money too ---------------------------------


def _cfg(**over):
    from app.config import Settings

    base = {
        "provider": "hybrid",
        "merchant_api_keys": "demo-merchant-key",
        "live_evidence_actions": "sim_swap",
        "live_evidence_numbers": "+99999991000",
    }
    base.update(over)
    return Settings(**base)


def test_hybrid_with_the_published_key_refuses_to_start():
    """`check_startup_posture` guarded `provider == "nac"` only. `hybrid` makes
    real, billable CAMARA calls and slipped straight past it — so a tunnelled
    demo with the published demo key let a stranger spend the operator budget.
    The guard has to key on whether calls can reach the network, not on one
    provider name."""
    from app.config import InsecureConfiguration, check_startup_posture

    with pytest.raises(InsecureConfiguration, match="demo"):
        check_startup_posture(_cfg())


def test_hybrid_with_no_live_targets_is_not_billable_and_may_start():
    """Both lists empty is a MockProvider with extra steps — no call can leave
    the process, so the guard must not block a local run."""
    from app.config import check_startup_posture

    check_startup_posture(_cfg(live_evidence_actions="", live_evidence_numbers=""))
