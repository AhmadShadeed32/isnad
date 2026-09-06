"""P3 step 1 — a signed chain must be written once.

Before this, `save()` did `s.get(ChainRow, chain_id) or ChainRow(...)`: an
upsert. Any caller minting a second Verdict with a colliding chain_id (a bug,
or someone trying to rewrite a previously issued verdict) silently replaced
the original decision, payload and signature — the one thing a signed receipt
exists to make impossible.
"""

from __future__ import annotations

import pytest

from app.chain.models import Verdict
from app.db import store
from app.domain.enums import ChainGrade, Decision


def _verdict(chain_id: str, decision: Decision = Decision.ALLOW) -> Verdict:
    return Verdict(
        decision=decision,
        chain_grade=ChainGrade.ATTESTED_PARTIAL,
        confidence=0.1,
        hypothesis="legit",
        reason="",
        chain_id=chain_id,
    )


def test_saving_the_same_chain_id_twice_is_refused_not_overwritten():
    chain_id = "chn_insert_only_probe"
    first = store.save(_verdict(chain_id, Decision.ALLOW))

    with pytest.raises(store.ChainAlreadyExists):
        store.save(_verdict(chain_id, Decision.DECLINE))

    # The original signed record must read back byte-identical.
    reread = store.get_record(chain_id)
    assert reread is not None
    assert reread.verdict_json == first.verdict_json
    assert reread.signature == first.signature
    assert reread.signed_at == first.signed_at


@pytest.mark.asyncio
async def test_the_async_wrapper_also_refuses_a_collision():
    chain_id = "chn_insert_only_probe_async"
    await store.save_async(_verdict(chain_id))

    with pytest.raises(store.ChainAlreadyExists):
        await store.save_async(_verdict(chain_id, Decision.DECLINE))
