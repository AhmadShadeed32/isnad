from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import ClassVar

import yaml

from app.domain.enums import Action, ChainGrade, Decision, Hypothesis
from app.domain.schemas import RequestContext


def p_to_logodds(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def logodds_to_p(lo: float) -> float:
    return 1.0 / (1.0 + math.exp(-lo))


class PolicyEngine:
    """Loads policy.yaml and answers every question the agent asks of policy."""

    def __init__(self, path: Path):
        with open(path) as fh:
            self.cfg = yaml.safe_load(fh)
        # Resolved once, at load. An action name that is not in the enum raises
        # here rather than silently resolving to no corroboration at all — a
        # typo in this map would otherwise reinstate the false decline it exists
        # to prevent, and nothing would say so.
        self.corroboration: dict[str, list[Action]] = {
            signal: [Action(name) for name in actions]
            for signal, actions in (self.cfg.get("corroboration") or {}).items()
        }

    # ---- thresholds ----
    @property
    def allow_below(self) -> float:
        return float(self.cfg["thresholds"]["allow_below"])

    @property
    def decline_above(self) -> float:
        return float(self.cfg["thresholds"]["decline_above"])

    # ---- prior ----
    def prior_logodds(self, ctx: RequestContext) -> float:
        pr = self.cfg["prior"]
        lo = p_to_logodds(float(pr["base_p"]))
        if ctx.account_age_days is not None and ctx.account_age_days <= 1:
            lo += float(pr["new_account_logodds"])
        if (ctx.payment_method or "").lower() == "cod":
            lo += float(pr["cod_logodds"])
        if ctx.amount and ctx.amount.value >= float(pr["high_value_threshold"]):
            lo += float(pr["high_value_logodds"])
        if ctx.event in ("payout", "password_reset", "profile_change"):
            lo += float(pr["sensitive_event_logodds"])
        return lo

    def reverse_prior_logodds(self) -> float:
        """Prior for Reverse Isnad: an unverified inbound caller starts uncertain."""
        return p_to_logodds(float(self.cfg["prior"]["reverse_base_p"]))

    # ---- signals ----
    def signal_delta(self, signal: str) -> float:
        return float(self.cfg["signals"].get(signal, 0.0))

    def corroboration_for(self, signal: str) -> list[Action]:
        """Checks to attempt before this signal alone may carry a DECLINE.

        The counterpart to `min_links` on the grading side: one link is not a
        chain, whichever way it points.
        """
        return self.corroboration.get(signal, [])

    # ---- gathering mode ----
    def gather_mode(self) -> str:
        return str((self.cfg.get("gather") or {}).get("mode", "sequential"))

    def parallel_batch(self) -> int:
        """How many actions to fire at once in parallel mode. Bounded: a batch
        larger than the affordable set just spends the whole budget at once."""
        return max(1, int((self.cfg.get("gather") or {}).get("parallel_batch", 3)))

    # ---- velocity ----
    def velocity_window(self) -> int:
        return int((self.cfg.get("velocity") or {}).get("window_seconds", 600))

    def velocity_threshold(self) -> int:
        """Distinct callees in the window before a number counts as a campaign.

        0 disables the check. The shipped value is invented, not measured — see
        the comment in policy.yaml.
        """
        return int((self.cfg.get("velocity") or {}).get("distinct_callees_flag", 0))

    # ---- budget ----
    def budget_for(self, ctx: RequestContext) -> int:
        b = self.cfg["budget"]
        if ctx.amount and ctx.amount.value >= float(self.cfg["prior"]["high_value_threshold"]):
            return int(b["high_value"])
        return int(b["default"])

    # ---- actions ----
    # Local evidence is answered from this service's own state in microseconds
    # and is never offered to the planner, so policy.yaml prices no `actions:`
    # entry for it — and `self.cfg["actions"][action.value]` would raise
    # KeyError for one. Free is the honest price, and a caller that reaches
    # here with a local action wants zero, not an exception. An action that is
    # neither local nor priced is a policy file missing an entry, and still
    # raises.
    _FREE: ClassVar[set[Action]] = {Action.REGISTRY_CHECK, Action.CALL_ANNOUNCEMENT}

    def _action(self, action: Action) -> dict:
        return self.cfg["actions"][action.value]

    def action_cost(self, action: Action) -> float:
        if action in self._FREE:
            return 0.0
        return float(self._action(action)["cost"])

    def action_gain(self, action: Action) -> float:
        if action in self._FREE:
            return 0.0
        return float(self._action(action)["gain"])

    def action_friction(self, action: Action) -> float:
        if action in self._FREE:
            return 0.0
        return float(self._action(action).get("friction", 0.0))

    def score(self, action: Action, hypothesis: Hypothesis) -> float:
        """Expected information per unit cost, weighted by hypothesis relevance."""
        pl = self.cfg["planner"]
        relevant = self.cfg["hypotheses"].get(hypothesis.value, {}).get("relevant", [])
        if action == Action.NUMBER_VERIFY:
            weight = float(pl["numberverify_weight"])
        elif action.value in relevant:
            weight = float(pl["relevant_weight"])
        else:
            weight = float(pl["base_weight"])
        return self.action_gain(action) * weight / self.action_cost(action)

    # ---- decision ----
    def decide(self, p_fraud: float) -> Decision:
        if p_fraud <= self.allow_below:
            return Decision.ALLOW
        if p_fraud >= self.decline_above:
            return Decision.DECLINE
        return Decision.CHALLENGE

    def is_decisive(self, p_fraud: float) -> bool:
        return p_fraud <= self.allow_below or p_fraud >= self.decline_above

    # ---- chain grade ----
    def adverse_delta(self) -> float:
        return float(self.cfg.get("grading", {}).get("adverse_delta", 0.4))

    def min_network_links_for_allow(self) -> int:
        """Network facts required before a clean belief may stop the agent."""
        return int(self.cfg.get("grading", {}).get("min_network_links_for_allow", 0))

    def min_links_for(self, hypothesis: Hypothesis | str) -> int:
        g = self.cfg.get("grading", {})
        key = hypothesis.value if isinstance(hypothesis, Hypothesis) else str(hypothesis)
        return int((g.get("min_links") or {}).get(key, g.get("default_min_links", 2)))

    def grade(
        self,
        p_fraud: float,
        unresolved: bool,
        link_deltas: list[float],
        hypothesis: Hypothesis | str,
    ) -> ChainGrade:
        """What the chain itself was worth.

        Ordered so the strongest claim about the evidence wins: an unobtainable
        link is reported as UNRESOLVED even when the remaining evidence looks
        clean, because a chain with a hole in it was never fully attested. A
        chain that is entirely hole — no links at all — is the same statement
        at full strength.
        """
        if unresolved:
            return ChainGrade.UNRESOLVED
        if not link_deltas:
            # Nothing was gathered. Every other grade below is a claim ABOUT
            # links — "the links resolved and nothing contradicted",
            # "one or more came back adverse", "a link directly contradicts" —
            # and each of them is a lie told about zero links. An empty chain
            # graded ATTESTED_PARTIAL, which is green in the console, for a
            # verdict resting on no evidence whatsoever. Above the band checks
            # so it is honest in all three of them, not only in ALLOW.
            return ChainGrade.UNRESOLVED
        if p_fraud >= self.decline_above:
            return ChainGrade.REFUTED
        if p_fraud > self.allow_below:
            return ChainGrade.DEGRADED
        # Cleared. Full attestation needs enough corroborating links and no
        # adverse signal among them.
        threshold = self.adverse_delta()
        if any(d >= threshold for d in link_deltas):
            return ChainGrade.ATTESTED_PARTIAL
        if len(link_deltas) < self.min_links_for(hypothesis):
            return ChainGrade.ATTESTED_PARTIAL
        return ChainGrade.ATTESTED_FULL


@lru_cache(maxsize=8)
def get_engine(policy_path: str) -> PolicyEngine:
    """Load the policy once and reuse it — avoids re-reading/parsing YAML per request."""
    return PolicyEngine(Path(policy_path))
