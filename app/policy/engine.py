from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import yaml

from app.domain.enums import Action, Decision, Hypothesis
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

    # ---- budget ----
    def budget_for(self, ctx: RequestContext) -> int:
        b = self.cfg["budget"]
        if ctx.amount and ctx.amount.value >= float(self.cfg["prior"]["high_value_threshold"]):
            return int(b["high_value"])
        return int(b["default"])

    # ---- actions ----
    def action_cost(self, action: Action) -> float:
        return float(self.cfg["actions"][action.value]["cost"])

    def action_gain(self, action: Action) -> float:
        return float(self.cfg["actions"][action.value]["gain"])

    def action_friction(self, action: Action) -> float:
        return float(self.cfg["actions"][action.value].get("friction", 0.0))

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


@lru_cache(maxsize=8)
def get_engine(policy_path: str) -> PolicyEngine:
    """Load the policy once and reuse it — avoids re-reading/parsing YAML per request."""
    return PolicyEngine(Path(policy_path))
