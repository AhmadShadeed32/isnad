"""Scripted evidence, except for the links deliberately made real.

Every winner found of this hackathon series demoed on a live network, and
Isnad's demo makes no live call at all. Running the whole
demo against Nokia Network-as-Code is not the answer: it is billable, it needs
consent flows the stage cannot perform, and it makes the flagship act depend on
conference Wi-Fi. What is wanted is narrower — **one genuinely live link inside
an otherwise deterministic chain**, so the judge page's `LIVE · Nokia NaC`
badge appears next to `simulator` badges on the same signed verdict, and the
provenance labelling stops being a claim and becomes a demonstration.

Two properties matter more than the feature:

* **The resting state is fully scripted.** With nothing configured this is a
  MockProvider with extra steps. Nobody starts spending money by surprise.
* **A live failure degrades to the fixture, never to an exception.** On stage a
  raised error is a dead demo; a fixture with an honest `mock` provenance badge
  is a demo that kept going. That is the same UNRESOLVED-is-not-REFUTED posture
  the product argues for, applied to its own plumbing.
"""

from __future__ import annotations

import logging

from app.chain.models import EvidenceLink
from app.domain.enums import Action
from app.domain.schemas import VerificationRequest
from app.providers.base import EvidenceProvider

log = logging.getLogger(__name__)


def _csv(raw: str) -> set[str]:
    return {item.strip() for item in (raw or "").split(",") if item.strip()}


class HybridProvider:
    """Delegate to `fallback`, except for `actions` on `numbers`, which are real."""

    def __init__(
        self,
        live: EvidenceProvider,
        fallback: EvidenceProvider,
        actions: str = "",
        numbers: str = "",
    ):
        self._live = live
        self._fallback = fallback
        # Compared against Action values (e.g. "sim_swap"), so the setting reads
        # the same as the action label that appears in the chain and the console.
        self._actions = {a.lower() for a in _csv(actions)}
        self._numbers = _csv(numbers)

    def _is_live(self, action: Action, request: VerificationRequest) -> bool:
        # No explicit empty-config guard: either set being empty already makes
        # the membership test below false, so a guard would be a line that reads
        # as load-bearing while never being the reason for an answer. The
        # unconfigured-means-scripted contract is covered by a test regardless.
        label = str(getattr(action, "value", action)).lower()
        return label in self._actions and request.phone_number in self._numbers

    async def gather(self, action: Action, request: VerificationRequest) -> EvidenceLink:
        if not self._is_live(action, request):
            return await self._fallback.gather(action, request)
        try:
            return await self._live.gather(action, request)
        except Exception:
            # Logged rather than surfaced: the chain still gets a link, and its
            # source says `mock`, so nothing scripted is ever labelled live.
            log.warning("live evidence for %s failed; using the fixture", action, exc_info=True)
            return await self._fallback.gather(action, request)
