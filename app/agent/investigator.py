from __future__ import annotations

import asyncio
import time

from app.agent import hypothesis as hypo
from app.agent.belief import Belief
from app.agent.planner import Choice, GreedyPlanner, Observation, get_planner
from app.chain.models import Chain, EvidenceLink, Verdict
from app.config import settings
from app.domain.enums import API_LABEL, Action, Decision, Hypothesis
from app.domain.schemas import VerificationRequest
from app.events import emit
from app.policy.engine import PolicyEngine, get_engine
from app.presentation import present
from app.providers.base import EvidenceProvider

_UNRESOLVED_SIGNALS = {"CONSENT_REQUIRED", "PROVIDER_UNAVAILABLE", "EVIDENCE_UNAVAILABLE"}


class Investigator:
    """The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,
    escalates only when suspicion warrants, and issues a verdict + chain."""

    def __init__(
        self,
        engine: PolicyEngine,
        provider: EvidenceProvider,
        *,
        planner=None,
        event_sink=None,
    ):
        self.engine = engine
        self.provider = provider
        self.planner = planner or get_planner(engine)
        # Defaults to the shared SSE bus; a lab/replay caller can inject its own
        # per-run recording sink instead without touching that bus, so a demo
        # run never leaks into (or is throttled by) another owner's stream.
        self._emit = event_sink or emit
        # Choreographed steps NEVER go through self.planner.
        #
        # This is the fourth time the same trap has been walked into. A rule the
        # investigator must enforce cannot be expressed as a question to a
        # planner, because LLMPlanner.next_best() is self.choose().action — it
        # asks the model, and the model's own prompt tells it to STOP once
        # belief has moved decisively. Every such rule then holds under greedy
        # (which the suite pins) and silently fails under llm (which the console
        # runs). cheapest_stepup already routes to greedy for this reason.
        self._choreography = GreedyPlanner(engine)

    async def investigate(
        self,
        request: VerificationRequest,
        hypothesis_override: Hypothesis | None = None,
        prior_override: float | None = None,
        run_id: str | None = None,
        local_evidence: list[EvidenceLink] | None = None,
        parallel: bool | None = None,
        required_action: Action | None = None,
    ) -> Verdict:
        started = time.perf_counter()
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

        await self._emit(
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

        observations: list[Observation] = []
        planner_sources: set[str] = set()
        choreographed = False

        # --- local evidence first: free, and already in hand ---
        # The registry and any Verified Caller pre-announcement are answered from
        # this service's own state, so they cost nothing and are applied before
        # the budget is opened. They enter the chain as real links — a verdict
        # that turned on "the institution announced this call" must be able to
        # show that, and it must be inside the signed payload like every other
        # link, not a note beside it.
        for link in local_evidence or []:
            link.step = chain.next_step()
            link.delta_logodds = self.engine.signal_delta(link.signal)
            chain.add(link)
            belief.apply(link.detail, link.delta_logodds)
            observations.append(
                Observation(
                    action=link.action, signal=link.signal, delta_logodds=link.delta_logodds
                )
            )
            await self._emit_link(link, belief, run_id)

        # A caller may arrive with authorization for one specific provider
        # action already granted. That authorization is part of the request's
        # contract, not a suggestion to the planner: asking the model whether to
        # use it lets STOP produce a completed consent with no Number
        # Verification evidence. Run it once, within the same policy budget and
        # accounting as every other network call, before either planner mode.
        if required_action is not None:
            action_cost = self.engine.action_cost(required_action)
            if action_cost > budget_left:
                raise ValueError("required evidence action exceeds the policy budget")
            required = Choice(
                required_action,
                "policy: use the provider authorization granted for this request",
                "policy",
            )
            await self._emit(
                self._with_run_id(
                    self._selection_event(
                        required,
                        hypothesis,
                        budget_left,
                        phase="authorization",
                    ),
                    run_id,
                )
            )
            link = await self._call(required_action, request, chain)
            belief.apply(link.detail, link.delta_logodds)
            evidence_cost += action_cost
            budget_left -= action_cost
            if link.signal in _UNRESOLVED_SIGNALS:
                unresolved_signals.add(link.signal)
            used.add(required_action)
            observations.append(
                Observation(
                    action=required_action,
                    signal=link.signal,
                    delta_logodds=link.delta_logodds,
                )
            )
            await self._emit_link(link, belief, run_id)
            choreographed = True

        # --- optional parallel batch, for latency-critical callers only ---
        # Fires the top N affordable actions at once instead of one at a time.
        # It buys wall-clock at the cost of the thing that makes the cost story
        # true: sequential stops as soon as belief is decisive, so it often pays
        # for one call where this pays for three. evidence_cost rises and the T5
        # counterfactual gets weaker. Off unless a caller asks.
        use_parallel = self.engine.gather_mode() == "parallel" if parallel is None else parallel
        if use_parallel and not self.engine.is_decisive(belief.p_fraud):
            before = len(chain.links)
            budget_left, evidence_cost = await self._gather_parallel(
                hypothesis,
                request,
                chain,
                belief,
                used,
                observations,
                unresolved_signals,
                budget_left,
                evidence_cost,
                run_id,
                planner_sources,
            )
            choreographed = choreographed or len(chain.links) > before

        # --- gather loop: cheapest evidence first, stop when decisive ---
        # `observations` is what the planner is allowed to see. It carries the
        # normalized signal name and the delta, never link.detail — see the
        # prompt-injection boundary in planner.py.
        while budget_left > 0:
            if self.engine.is_decisive(belief.p_fraud):
                # Belief is decisive — but a single adverse signal is not allowed
                # to carry a DECLINE on its own while policy still names a check
                # that could exonerate. Declining on SIM_SWAPPED alone is exactly
                # the false decline this agent exists to avoid, and whether it
                # happened used to depend on the order the planner picked in.
                # Choreographed, not planned: `corroboration` in policy.yaml.
                action = self._next_corroboration(observations, used, belief, budget_left)
                rationale = "policy: corroborate before this signal alone can decline"
                if action is None:
                    # Clean — but possibly on local evidence alone. An
                    # announcement is somebody proving they held a key, not
                    # proof that this call is real.
                    #
                    # Asked rather than choreographed, this rule would not hold:
                    # the planner is free to STOP on a clean belief, and the LLM
                    # planner does. It would then survive the suite (which runs
                    # greedy, which never stops) and fail in the console (which
                    # runs llm) — the exact shape of the Act VI regression.
                    if not self._needs_a_network_fact(belief, chain, hypothesis):
                        break
                    action = self._choreography.next_best(hypothesis, used, budget_left)
                    if action is None:
                        break  # nothing affordable; the local chain stands
                    rationale = "policy: an allow must rest on a network fact"
                    phase = "attestation"
                else:
                    phase = "corroboration"
                choice = Choice(action, rationale, "policy")
                # Tracked separately from planner_sources: "policy" is not a
                # planner, and the label is a signed field whose vocabulary is
                # llm / greedy / llm+greedy. What was wrong was only the empty
                # case — a run reporting "none" beside a chain of real network
                # calls reads as "nothing was decided".
                choreographed = True
            else:
                phase = "investigation"
                choice = self.planner.choose(
                    hypothesis, used, budget_left, belief.p_fraud, observations
                )
                planner_sources.add(choice.source)
            if choice.stops:
                # The agent decided it has enough. A first-class outcome.
                await self._emit(
                    self._with_run_id(
                        {
                            "type": "decision",
                            "phase": "investigation",
                            "action": "stop",
                            "api": "—",
                            "hypothesis": hypothesis.value,
                            "rationale": choice.rationale,
                            "planner": choice.source,
                            "cost": 0.0,
                            "budget_left": round(budget_left, 3),
                        },
                        run_id,
                    )
                )
                break
            action = choice.action
            await self._emit(
                self._with_run_id(
                    self._selection_event(choice, hypothesis, budget_left, phase=phase),
                    run_id,
                )
            )
            link = await self._call(action, request, chain)
            belief.apply(link.detail, link.delta_logodds)
            action_cost = self.engine.action_cost(action)
            evidence_cost += action_cost
            budget_left -= action_cost
            if link.signal in _UNRESOLVED_SIGNALS:
                unresolved_signals.add(link.signal)
            used.add(action)
            observations.append(
                Observation(action=action, signal=link.signal, delta_logodds=link.delta_logodds)
            )
            await self._emit_link(link, belief, run_id)

        decision = self.engine.decide(belief.p_fraud)

        # --- CHALLENGE: choreograph the single cheapest doubt-resolving step ---
        if decision == Decision.CHALLENGE:
            action = self.planner.cheapest_stepup(used, budget_left)
            if action is not None:
                # The step-up is a policy choreography, not a planner decision:
                # it is the cheapest doubt-resolving move, chosen deterministically.
                stepup = Choice(action, "cheapest step that could resolve the doubt", "policy")
                await self._emit(
                    self._with_run_id(
                        self._selection_event(stepup, hypothesis, budget_left, phase="step_up"),
                        run_id,
                    )
                )
                link = await self._call(action, request, chain)
                belief.apply(link.detail, link.delta_logodds)
                evidence_cost += self.engine.action_cost(action)
                if link.signal in _UNRESOLVED_SIGNALS:
                    unresolved_signals.add(link.signal)
                used.add(action)
                await self._emit_link(link, belief, run_id)
        decision = self.engine.decide(belief.p_fraud)
        missing_support = self._needs_a_network_fact(belief, chain, hypothesis)
        evidence_unresolved = bool(unresolved_signals) or missing_support
        if decision == Decision.ALLOW and evidence_unresolved:
            decision = Decision.CHALLENGE

        grade = self.engine.grade(
            p_fraud=belief.p_fraud,
            unresolved=evidence_unresolved,
            link_deltas=[link.delta_logodds for link in chain.links],
            hypothesis=hypothesis,
        )

        verdict = Verdict(
            decision=decision,
            prior_logodds=round(prior, 6),
            planner=self._planner_label(planner_sources, choreographed),
            policy_snapshot={
                "allow_below": self.engine.allow_below,
                "decline_above": self.engine.decline_above,
            },
            chain_grade=grade,
            confidence=round(belief.p_fraud, 3),
            hypothesis=hypothesis.value,
            # One definition of "material", read from policy rather than
            # duplicated as a literal in two files that could drift apart.
            reason=belief.explain(
                decision.value,
                unresolved=evidence_unresolved,
                material=self.engine.adverse_delta(),
            ),
            chain_id=chain.id,
            chain=chain.links,
            evidence_cost=round(evidence_cost, 2),
            # Wall clock for the whole investigation, NOT the sum of the link
            # latencies. The sum was a number parallel mode could never move:
            # three 300ms calls fired at once still summed to 900, so the mode
            # whose entire purpose is latency reported no improvement, and the
            # T5 counterfactual published that sum as `basis="measured"` beside
            # an OTP round trip in seconds. This is the time the customer
            # actually waited, which is the only number that comparison means.
            latency_ms=int((time.perf_counter() - started) * 1000),
            provider_sources=sorted({link.source for link in chain.links}),
        )
        await self._emit(
            self._with_run_id(
                {
                    "type": "verdict",
                    "chain_id": chain.id,
                    "decision": decision.value,
                    "planner": verdict.planner,
                    "chain_grade": grade.value,
                    "confidence": verdict.confidence,
                    "reason": verdict.reason,
                    "evidence_steps": len(verdict.chain),
                    "evidence_cost": verdict.evidence_cost,
                    "latency_ms": verdict.latency_ms,
                    # Same projection HTTP responses carry (P2), computed from
                    # this same already-finalized verdict object -- not a
                    # second decision, just the plain-language view of the one
                    # already made above. Emitted here, before the caller has
                    # persisted anything, is why judge.html must not treat the
                    # SSE 'verdict' event alone as proof of a saved receipt.
                    "presentation": present(verdict).model_dump(mode="json"),
                },
                run_id,
            )
        )
        return verdict

    async def _gather_parallel(
        self,
        hypothesis,
        request,
        chain,
        belief,
        used,
        observations,
        unresolved_signals,
        budget_left,
        evidence_cost,
        run_id,
        planner_sources,
    ):
        """Fire a batch of affordable actions concurrently.

        Chosen with the deterministic planner rather than the model — really
        deterministic, via self._choreography: a batch is a spend decision made
        before any of its answers are known, so there is nothing for a reasoning
        planner to reason about, and asking one meant the model could STOP and
        silently collapse parallel mode back to sequential. Belief is applied after
        the batch returns, in a fixed order, so two runs over the same evidence
        produce the same number regardless of which call finished first.
        """
        batch: list = []
        remaining = budget_left
        for _ in range(self.engine.parallel_batch()):
            action = self._choreography.next_best(hypothesis, used | set(batch), remaining)
            if action is None:
                break
            batch.append(action)
            remaining -= self.engine.action_cost(action)
        if not batch:
            return budget_left, evidence_cost

        for action in batch:
            choice = Choice(action, "policy: parallel batch", "policy")
            await self._emit(
                self._with_run_id(
                    self._selection_event(choice, hypothesis, budget_left, phase="parallel"),
                    run_id,
                )
            )

        links = await asyncio.gather(*(self._call(action, request, chain) for action in batch))
        # Sorted by step so the belief update order is the chain order, not the
        # order the network happened to answer in.
        for link in sorted(links, key=lambda item: item.step):
            belief.apply(link.detail, link.delta_logodds)
            cost = self.engine.action_cost(link.action)
            evidence_cost += cost
            budget_left -= cost
            if link.signal in _UNRESOLVED_SIGNALS:
                unresolved_signals.add(link.signal)
            used.add(link.action)
            observations.append(
                Observation(
                    action=link.action, signal=link.signal, delta_logodds=link.delta_logodds
                )
            )
            await self._emit_link(link, belief, run_id)
        return budget_left, evidence_cost

    def _needs_a_network_fact(
        self, belief: Belief, chain: Chain, hypothesis: Hypothesis | None = None
    ) -> bool:
        """Is this a clean verdict resting on local evidence alone — or on local
        evidence plus a network fact that contradicts it?

        Only the ALLOW side. A decline already has its own gate (corroboration),
        and a chain in the uncertain band has not stopped anyway.
        """
        if belief.p_fraud > self.engine.allow_below:
            return False
        # A clean prior is not evidence either. Apply the same minimum to
        # empty chains and local-only chains; otherwise low-risk context can
        # bypass the very provider check the ALLOW claims to rest on.
        # Counted SUPPORTING, not merely present. A network link that came back
        # adverse is not the fact the gate is asking for: an announcement worth
        # -2.5 outweighs a NUMBER_MISMATCH worth +1.5, so a chain of
        # "announced, and the network says the call is not coming from that
        # line" cleared the allow threshold and stopped — the announcement had
        # bought a pass past the very evidence that contradicts it.
        #
        # It held under greedy, which never stops and would have gone on to the
        # swap and the bot pattern, and failed under any planner that stops when
        # belief is decisive — which is what the LLM planner's prompt tells it to
        # do. The same trap as C1, a fifth time.
        # Strictly negative, not merely "not adverse". A network link worth 0.0
        # is the could-not-check family — LOCATION_UNKNOWN, LOCATION_PARTIAL,
        # and the mock's own catch-all — and a link that moved belief by nothing
        # attests nothing. Counting it would leave the same hole one notch
        # weaker: announcement (-2.5) plus one zero-information network call,
        # gate satisfied, ALLOW. Supporting means it moved belief TOWARD the
        # customer.
        #
        # And the supporting fact has to bear on what was suspected. A day-zero
        # signup is investigated as a bot farm; Number Verification is the
        # cheapest check priced, so it went first, came back NUMBER_MATCH, and
        # satisfied this gate on its own. But a match establishes that the
        # handset presenting the number holds that SIM, and a bot farm runs
        # real SIMs in real handsets — so the chain cleared on a check that
        # could not distinguish the thing it was looking for. The same hole
        # sits under account_takeover: a swapped SIM still number-matches.
        # Every number in those chains was right; the sentence a merchant
        # reads was not, and the sentence is the product.
        #
        # Only applied where the hypothesis names its checks. `legit` and
        # `legit_thin_file` list none, and an empty list is an answer — no
        # hypothesis-driven check — not a wildcard; filtering on their behalf
        # would make the gate unsatisfiable and loop until the budget ran out.
        relevant = self.engine.relevant_actions(hypothesis) if hypothesis else set()
        supporting = sum(
            1
            for link in chain.links
            if link.source != "local"
            and link.delta_logodds < 0
            and (not relevant or link.action.value in relevant)
        )
        return supporting < self.engine.min_network_links_for_allow()

    def _next_corroboration(
        self,
        observations: list[Observation],
        used: set,
        belief: Belief,
        budget_left: float,
    ):
        """The next outstanding exculpatory check, or None.

        Only ever gates the DECLINE side: a chain that has cleared stops as soon
        as it clears, and pays for nothing further. Affordability is checked per
        action, so a budget that cannot cover the corroboration lets the decline
        stand rather than looping.
        """
        if belief.p_fraud < self.engine.decline_above:
            return None
        for obs in observations:
            for action in self.engine.corroboration_for(obs.signal):
                if action not in used and self.engine.action_cost(action) <= budget_left:
                    return action
        return None

    async def _call(self, action, request: VerificationRequest, chain: Chain) -> EvidenceLink:
        t0 = time.perf_counter()
        link = await self.provider.gather(action, request)
        if not link.latency_ms:
            link.latency_ms = int((time.perf_counter() - t0) * 1000)
        link.step = chain.next_step()
        link.delta_logodds = self.engine.signal_delta(link.signal)
        chain.add(link)
        return link

    async def _emit_link(self, link: EvidenceLink, belief: Belief, run_id: str | None) -> None:
        await self._emit(
            self._with_run_id(
                {
                    "type": "evidence",
                    "step": link.step,
                    "api": link.api,
                    "result": link.result.value,
                    "signal": link.signal,
                    "detail": link.detail,
                    "source": link.source,
                    "max_age_hours": link.max_age_hours,
                    "p_fraud": round(belief.p_fraud, 3),
                },
                run_id,
            )
        )

    @staticmethod
    def _planner_label(sources: set[str], choreographed: bool = False) -> str:
        """Which planner produced this run.

        "llm+greedy" when the run fell back partway through — the honest label,
        and the one that makes the fallback visible rather than something the
        badge quietly rounds off.

        "policy" when no planner was consulted but policy choreographed real
        calls: corroboration, the attestation gate, or a parallel batch. That
        case used to report "none", which reads as "nothing was decided" beside
        a chain of network evidence.
        """
        if not sources:
            return "policy" if choreographed else "none"
        if sources == {"llm"}:
            return "llm"
        if sources == {"greedy"}:
            return "greedy"
        return "+".join(sorted(sources))

    @staticmethod
    def _with_run_id(event: dict, run_id: str | None) -> dict:
        if run_id:
            event["run_id"] = run_id
        return event

    def _selection_event(
        self, choice: Choice, hypothesis: Hypothesis, budget_left: float, phase: str
    ) -> dict:
        """The event the console renders as the agent's reasoning.

        The rationale is whoever decided's own words, verbatim. This used to be an
        if/elif template that produced a sentence no component had actually
        reasoned — a heuristic dressed as reasoning, which is worse than a
        heuristic. `planner` says who decided, so greedy is never mistaken for the
        model, and the console badges it.
        """
        action = choice.action
        return {
            "type": "decision",
            "phase": phase,
            "action": action.value,
            "api": API_LABEL[action],
            "hypothesis": hypothesis.value,
            "rationale": choice.rationale,
            "planner": choice.source,
            "cost": self.engine.action_cost(action),
            "score": round(self.engine.score(action, hypothesis), 3),
            "budget_left": round(budget_left, 3),
        }


def build_investigator(
    provider: EvidenceProvider,
    *,
    engine: PolicyEngine | None = None,
    planner=None,
    event_sink=None,
) -> Investigator:
    engine = engine or get_engine(str(settings.policy_path))
    return Investigator(engine, provider, planner=planner, event_sink=event_sink)


def build_engine_for_pricing() -> PolicyEngine:
    """The same cached policy the agent ran on, for the T5 counterfactual.

    Read at response time rather than stored on the verdict: the counterfactual
    needs the subject's country, and the signed payload deliberately contains no
    phone number (S5).
    """
    return get_engine(str(settings.policy_path))
