# Isnad — compact handoff

Updated 5 September 2026. **Read this file first.** It replaces the long running
log with current facts and the next work. The complete earlier log is preserved
in [commit faf467f](https://github.com/AhmadShadeed32/isnad-private/blob/faf467ffd1150127a0f16de3a1bea7936d60794e/docs/PHASE2_HANDOFF.md).

## 1. Current product and evidence

Isnad investigates an interaction using network evidence and returns ALLOW,
CHALLENGE or DECLINE with a signed chain. Lead with the legitimate SIM replacement
at checkout; keep caller verification and session revocation for follow-up questions.

- `/judge`: primary Act VI → CHALLENGE / DEGRADED, six checks, score 0.242.
  Secondary Act III → ALLOW / ATTESTED_FULL, two checks. Only the latter exposes
  the optional simulator continuity drill.
- Stage: `mock` provider, explicitly `greedy` planner. The LLM is optional and
  can STOP or fall back. Verdict labels report actual selection, including
  `policy` and `none`; never widen signed-field vocabulary casually.
- Scores are policy-derived and uncalibrated. See [RISK_SCORE.md](RISK_SCORE.md).
- Original synthetic harness: 58 versus 119 calls, 0/10 customer-case declines,
  1/7 two-adverse cases allowed; threshold 0.05 buys 82 calls and allows 0/7.
- Fixed 13-case set: 28 versus 78 calls, 3/13 CHALLENGE, six conservative
  expectation disagreements. These are synthetic judgments, not observed fraud
  outcomes. [Full evaluation](INDEPENDENT_EVALUATION.md).
- Last implementation verification: **506 tests passed**, Ruff and JS syntax
  clean. Browser verified both judge outcomes and valid → tampered-invalid →
  restored receipt signatures. A receipt proves issuance/integrity, not provider truth.

## 2. Mock parity — exact wording to preserve

Mock and NaC return the same **normalized EvidenceLink contract**, using shared
signal vocabulary and fact-rendering functions. Both feed the same investigator,
policy, budget accounting, grading and signing. The mock provides fixture facts,
not a prewritten verdict. Equivalent normalized facts get the same policy weights;
planner selection can still differ with an optional LLM.

The stage route creates `MockProvider(step_delay_ms=650)`: an actual sleep per
check for readable presentation. Mock link `latency_ms` values (normally 45/90/135)
are scripted metadata, separate from that sleep. Total verdict duration includes
pacing and execution. **Neither is measured operator latency.** Source, consent,
timestamps, timings and subscriber-specific answers differ from live operation;
never say the entire JSON is identical or that the delay reproduces live speed.

Sources: `app/providers/mock.py`, `nac.py`, `vocabulary.py`, and
`app/api/routes_console.py`. Historical NaC captures: `docs/nac/`.

## 3. Recommended app work — not implemented in this documentation pass

| Priority | Change | Acceptance criterion |
| --- | --- | --- |
| P0 | Give judges the focused entry point. `/` currently redirects to `/console`; use `/judge` as the demo landing page or publish its exact URL. | A judge's first visit opens the customer story, not the engineering console; production/demo gating remains intact. |
| P0 | Build a dedicated live consent journey over the existing consent APIs, separate from fixed stage buttons. | A supported subscriber approves operator consent, Number Verification returns `source=nac`, and a verifiable receipt is shown. No merchant/provider key is embedded in public HTML. |
| P1 | Translate the result into a merchant action. Lead with “Additional verification needed”; retain CHALLENGE and DEGRADED as secondary technical labels. | Judges understand that the order was not auto-declined and that the merchant owns the next step. Do not imply Isnad has sent an OTP. |
| P1 | Explain simulation and timing in the app. Add a short “Why simulated?” disclosure and label mock totals “Demo duration.” | It states same engine, fixture answers and 650 ms pacing; no scripted time is presented as operator performance. |
| P1 | Add a short deterministic outcome explanation naming the adverse and supporting facts. | The SIM-replacement result explains why it became a step-up; copy comes from observed links and does not invent facts or alter signed history. |
| P2 | Rehearse small-screen receipt and trace use before submission. | Verify readability at phone widths, signature/tamper controls and a clear return to the demo; keep provenance visible. |

Keep this list short. Do not add new product branches before the live consent
proof and the existing customer story are clear.

## 4. Path to a live product

**Hosted demo and live operator evidence are separate milestones.**

1. **Prepare a controlled deployment.** Use the existing Docker image, HTTPS,
   persistent `/srv/isnad` storage, and exactly one application worker/replica.
   Consent, sessions, SSE, rate limits and idempotency are in process. Do not
   enable multiple replicas before shared state exists. A public mock demo
   requires a review of demo access, shared state and abuse limits; do not tunnel
   the developer console as a production service.
2. **Obtain operator prerequisites.** NaC application access with Number
   Verification available for the test subscriber/operator, a supported handset,
   OAuth metadata/client credentials, and the exact registered callback:
   `https://<host>/v1/consents/number-verification/callback`.
3. **Start live mode.** `ISNAD_PROVIDER=nac`, `ISNAD_DEMO_MODE=false`, initially
   `ISNAD_PLANNER=greedy`; private merchant/provider credentials, persisted pepper
   and pre-provisioned signing key. Use a host secret store. `/readyz` must pass.
   A fresh live process refuses to create a missing signing key. Keep OAuth
   query strings out of application and reverse-proxy access logs.
4. **Prove one end-to-end flow.** Follow [HANDSET_VALIDATION.md](HANDSET_VALIDATION.md):
   subscriber consent → callback → Number Verification → signed receipt. Start
   on mobile data if required by the operator. An HTTP response alone does not
   establish live evidence: inspect `source=nac` and a usable result. Budget may
   permit additional policy checks if the first result is adverse or unresolved.
5. **Expand after that proof.** Exercise other available network APIs and failure
   paths, then evaluate against a merchant's appropriately handled outcomes.
   Calibrate scores and review correlated evidence. Never substitute mock facts
   on a failed live call.

**Still unproven:** physical handset/operator round trip, production accuracy,
operator coverage and commercial pricing. The local consent contract passes;
it cannot establish those facts. The old video binary is obsolete; corrected
sources need regenerated voiceover, captions and frames (ffmpeg unavailable in
the last review). Use the current live app recording script instead.

## 5. Code map and working rules

| Concern | Files |
| --- | --- |
| Investigation and STOP-proof policy checks | `app/agent/investigator.py`, `app/agent/planner.py` |
| Weights, budget, grading | `app/policy/engine.py`, `app/policy/policy.yaml` |
| Evidence and provenance | `app/providers/{mock,nac,vocabulary}.py` |
| Consent lifecycle | `app/api/routes_consent.py`, `app/consent/` |
| Receipt, signature and persistence | `app/chain/`, `app/db/`, `app/api/routes_receipt.py` |
| Judge presentation | `app/static/judge.html`, `app/api/routes_judge.py` |
| Reproduction | `scripts/evidence_pack.py`, `independent_evaluation.py`, `handset_validation.py` |

- Use `.venv311`; `.venv` is stale. Start with `graphify query "<focused question>"`.
- Read affected files and log intent before edits; record completion afterward.
- Policy-required checks use deterministic choreography, never model choice.
  Test with a STOP-capable planner and prove the regression fails before the fix.
- Granted consent requires Number Verification. All ALLOW candidates need the
  configured supporting network minimum; unaffordable support retains CHALLENGE.
- Local registry/announcement evidence costs zero and stays outside candidates.
- Re-sign `registry.yaml` after edits; preserve signer/pepper persistence and
  signed-field compatibility. Do not invent prices, signals or network facts.
- Run `.venv311/bin/python -m pytest -q` and
  `.venv311/bin/python -m ruff check app tests scripts demo` for implementation
  changes. Exercise the affected UI; greedy-only tests do not validate LLM STOP.
- Refresh Graphify after changes. When compacting documents, remove stale graph
  concepts tied to the replaced text before rebuilding their headings.
- Private remote: `AhmadShadeed32/isnad-private`, `main`; last pushed `568a828`.
  Public `origin` is a different destination. Do not infer a public push from a
  private publication request.

## 6. Latest session

**Intent — 5 Sep:** make README persuasive for judges while integrating technical
details into the story. User explicitly rejected numbered pitch-deck sections
and a separate technical appendix.

**Completion:** customer scenario flows into architecture, budget/policy loop,
signed receipts, mock/live parity, consent and measured evidence. Diagrams sit
beside the claims they explain; only API examples and test commands collapse.
Preserved limitations, 650 ms pacing and live prerequisites. No app behavior
changed. Local links, anchors and Markdown structure checked; graph refreshed.
User authorized publication to private/main; this documentation revision includes
the integrated README, diagrams and refreshed graph.
