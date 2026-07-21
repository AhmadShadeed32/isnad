from __future__ import annotations

from typing import Optional, Protocol

from app.config import settings
from app.domain.enums import Action, Hypothesis
from app.policy.engine import PolicyEngine

# Actions the agent may take to gather low-friction evidence. step_up_otp is excluded
# here — it is reserved for the CHALLENGE step-up path (adds user friction).
_CANDIDATES = [a for a in Action if a != Action.STEP_UP_OTP]


class Planner(Protocol):
    def next_best(
        self, hypothesis: Hypothesis, used: set, budget_left: float
    ) -> Optional[Action]: ...

    def cheapest_stepup(self, used: set, budget_left: float) -> Optional[Action]: ...


class GreedyPlanner:
    """Deterministic evidence selection: pick the highest information-per-cost
    action that is relevant to the current hypothesis and still affordable.

    The *choice itself* is the agent's reasoning — this is what makes the CAMARA
    calls agent-initiated rather than a fixed pipeline.
    """

    def __init__(self, engine: PolicyEngine):
        self.engine = engine

    def next_best(
        self, hypothesis: Hypothesis, used: set[Action], budget_left: float
    ) -> Action | None:
        best: Action | None = None
        best_score = 0.0
        for action in _CANDIDATES:
            if action in used:
                continue
            if self.engine.action_cost(action) > budget_left:
                continue
            score = self.engine.score(action, hypothesis)
            if score > best_score:
                best_score, best = score, action
        return best

    def cheapest_stepup(self, used: set[Action], budget_left: float) -> Action | None:
        """For CHALLENGE: cheapest low-friction step that could resolve doubt,
        falling back to an OTP step-up only if nothing remains affordable."""
        low_friction = [
            a
            for a in (Action.LOCATION_VERIFY, Action.NUMBER_VERIFY, Action.REACHABILITY)
            if a not in used and self.engine.action_cost(a) <= budget_left
        ]
        if low_friction:
            return min(low_friction, key=self.engine.action_cost)
        if self.engine.action_cost(Action.STEP_UP_OTP) <= budget_left:
            return Action.STEP_UP_OTP
        return None


class LLMPlanner:
    """Optional planner that asks an LLM to choose the next evidence step, given
    the belief state, the affordable actions, and their costs.

    The interface is identical to GreedyPlanner, so it drops into the loop with
    no other changes. When no LLM client is configured (no API key / SDK), it
    transparently falls back to greedy selection so the system always runs.
    """

    def __init__(self, engine: PolicyEngine):
        self.engine = engine
        self._greedy = GreedyPlanner(engine)
        self._client = self._maybe_client()

    @staticmethod
    def _maybe_client():
        if not settings.anthropic_api_key:
            return None
        try:  # pragma: no cover - exercised only with the SDK + key present
            import anthropic

            return anthropic.Anthropic(api_key=settings.anthropic_api_key)
        except ImportError:
            return None

    def next_best(
        self, hypothesis: Hypothesis, used: set, budget_left: float
    ) -> Optional[Action]:
        if self._client is None:
            return self._greedy.next_best(hypothesis, used, budget_left)
        return self._ask_llm(hypothesis, used, budget_left)  # pragma: no cover

    def cheapest_stepup(self, used: set, budget_left: float) -> Optional[Action]:
        return self._greedy.cheapest_stepup(used, budget_left)

    def _ask_llm(  # pragma: no cover - requires a live LLM
        self, hypothesis: Hypothesis, used: set, budget_left: float
    ) -> Optional[Action]:
        affordable = [
            a for a in _CANDIDATES
            if a not in used and self.engine.action_cost(a) <= budget_left
        ]
        if not affordable:
            return None
        menu = "\n".join(
            f"- {a.value}: cost={self.engine.action_cost(a)}, "
            f"info={self.engine.action_gain(a)}"
            for a in affordable
        )
        prompt = (
            f"You are a fraud-investigation agent. Hypothesis: {hypothesis.value}. "
            f"Pick the single most cost-effective next evidence check. "
            f"Reply with ONLY the action id.\nAvailable:\n{menu}"
        )
        try:
            resp = self._client.messages.create(
                model=settings.llm_model,
                max_tokens=16,
                messages=[{"role": "user", "content": prompt}],
            )
            choice = resp.content[0].text.strip()
            for a in affordable:
                if a.value == choice:
                    return a
        except Exception:
            pass
        # Any failure or unparsable answer -> greedy fallback.
        return self._greedy.next_best(hypothesis, used, budget_left)


def get_planner(engine: PolicyEngine) -> Planner:
    """Select the planner from config: greedy (default, demo-safe) or llm."""
    if settings.planner == "llm":
        return LLMPlanner(engine)
    return GreedyPlanner(engine)
