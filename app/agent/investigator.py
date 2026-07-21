from __future__ import annotations

import time

from typing import Optional

from app.agent import hypothesis as hypo
from app.agent.belief import Belief
from app.agent.planner import get_planner
from app.chain.models import Chain, EvidenceLink, Verdict
from app.config import settings
from app.domain.enums import API_LABEL, Action, Decision, Hypothesis
from app.events import emit
from app.policy.engine import PolicyEngine, get_engine
from app.providers.base import EvidenceProvider
from app.domain.schemas import VerificationRequest


class Investigator:
    """The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,
    escalates only when suspicion warrants, and issues a verdict + chain."""

    def __init__(self, engine: PolicyEngine, provider: EvidenceProvider):
        self.engine = engine
        self.provider = provider
        self.planner = get_planner(engine)

    async def investigate(
        self,
        request: VerificationRequest,
        hypothesis_override: Optional[Hypothesis] = None,
        prior_override: Optional[float] = None,
        run_id: Optional[str] = None,
    ) -> Verdict:
        ctx = request.context
        hypothesis = hypothesis_override or hypo.form(ctx)
        if prior_override is not None:
            prior = prior_override
        elif hypothesis == Hypothesis.IMPERSONATION:
            prior = self.engine.reverse_prior_logodds()
        else:
            prior = self.engine.prior_logodds(ctx)
        belief = Belief(logodds=prior)
        budget_left = float(self.engine.budget_for(ctx))
        evidence_cost = 0.0
        unresolved_signals: set[str] = set()
        chain = Chain(hypothesis=hypothesis.value)
        used: set = set()

        await emit(
            self._with_run_id(
                {
                    "type": "start",
                    "chain_id": chain.id,
                    "hypothesis": hypothesis.value,
                    "prior_p_fraud": round(belief.p_fraud, 3),
                },
                run_id,
            )
        )

        # --- gather loop: cheapest evidence first, stop when decisive ---
        while not self.engine.is_decisive(belief.p_fraud) and budget_left > 0:
            action = self.planner.next_best(hypothesis, used, budget_left)
            if action is None:
                break
            await emit(self._with_run_id(
                self._selection_event(action, hypothesis, budget_left, phase="investigation"),
                run_id,
            ))
            link = await self._call(action, request, chain)
            belief.apply(link.detail, link.delta_logodds)
            action_cost = self.engine.action_cost(action)
            evidence_cost += action_cost
            budget_left -= action_cost
            if link.signal in {"CONSENT_REQUIRED", "PROVIDER_UNAVAILABLE", "EVIDENCE_UNAVAILABLE"}:
                unresolved_signals.add(link.signal)
            used.add(action)
            await self._emit_link(link, belief, run_id)

        decision = self.engine.decide(belief.p_fraud)

        # --- CHALLENGE: choreograph the single cheapest doubt-resolving step ---
        if decision == Decision.CHALLENGE:
            action = self.planner.cheapest_stepup(used, budget_left)
            if action is not None:
                await emit(self._with_run_id(
                    self._selection_event(action, hypothesis, budget_left, phase="step_up"),
                    run_id,
                ))
                link = await self._call(action, request, chain)
                belief.apply(link.detail, link.delta_logodds)
                evidence_cost += self.engine.action_cost(action)
                if link.signal in {"CONSENT_REQUIRED", "PROVIDER_UNAVAILABLE", "EVIDENCE_UNAVAILABLE"}:
                    unresolved_signals.add(link.signal)
                used.add(action)
                await self._emit_link(link, belief, run_id)
        decision = self.engine.decide(belief.p_fraud)
        if decision == Decision.ALLOW and unresolved_signals:
            decision = Decision.CHALLENGE

        verdict = Verdict(
            decision=decision,
            confidence=round(belief.p_fraud, 3),
            hypothesis=hypothesis.value,
            reason=belief.explain(decision.value, unresolved=bool(unresolved_signals)),
            chain_id=chain.id,
            chain=chain.links,
            evidence_cost=round(evidence_cost, 2),
            latency_ms=sum(link.latency_ms for link in chain.links),
            provider_sources=sorted({link.source for link in chain.links}),
        )
        await emit(self._with_run_id(
            {"type": "verdict", "chain_id": chain.id, "decision": decision.value,
             "confidence": verdict.confidence, "reason": verdict.reason,
             "evidence_steps": len(verdict.chain), "evidence_cost": verdict.evidence_cost,
             "latency_ms": verdict.latency_ms},
            run_id,
        ))
        return verdict

    async def _call(self, action, request: VerificationRequest, chain: Chain) -> EvidenceLink:
        t0 = time.perf_counter()
        link = await self.provider.gather(action, request)
        if not link.latency_ms:
            link.latency_ms = int((time.perf_counter() - t0) * 1000)
        link.step = chain.next_step()
        link.delta_logodds = self.engine.signal_delta(link.signal)
        chain.add(link)
        return link

    async def _emit_link(self, link: EvidenceLink, belief: Belief, run_id: Optional[str]) -> None:
        await emit(self._with_run_id(
            {
                "type": "evidence",
                "step": link.step,
                "api": link.api,
                "result": link.result.value,
                "signal": link.signal,
                "detail": link.detail,
                "source": link.source,
                "p_fraud": round(belief.p_fraud, 3),
            },
            run_id,
        ))

    @staticmethod
    def _with_run_id(event: dict, run_id: Optional[str]) -> dict:
        if run_id:
            event["run_id"] = run_id
        return event

    def _selection_event(self, action, hypothesis: Hypothesis, budget_left: float, phase: str) -> dict:
        relevant = self.engine.cfg["hypotheses"].get(hypothesis.value, {}).get("relevant", [])
        if action == Action.NUMBER_VERIFY:
            rationale = "lowest-cost identity check; useful before spending on deeper evidence"
        elif action.value in relevant:
            rationale = f"relevant to the {hypothesis.value.replace('_', ' ')} hypothesis"
        else:
            rationale = "best remaining information-per-cost option"
        return {
            "type": "decision",
            "phase": phase,
            "action": action.value,
            "api": API_LABEL[action],
            "hypothesis": hypothesis.value,
            "rationale": rationale,
            "cost": self.engine.action_cost(action),
            "score": round(self.engine.score(action, hypothesis), 3),
            "budget_left": round(budget_left, 3),
        }


def build_investigator(provider: EvidenceProvider) -> Investigator:
    engine = get_engine(str(settings.policy_path))
    return Investigator(engine, provider)
