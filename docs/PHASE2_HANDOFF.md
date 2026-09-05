# Isnad — compact handoff

Updated 5 September 2026. **Read this file first.** It replaces the long running
log with current facts and an implementation plan. Read the ledger in §3 to resume. The complete earlier log is preserved
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

This is the implementation contract for the five product suggestions. **Every
package below is NOT STARTED.** Named new files/routes/models are proposals, not
existing functionality. Inspect the current checkout before applying the plan;
record any justified change to these contracts here before implementing it.

### Execution order and completion ledger

| Package | Deliverable | Depends on | Status |
| --- | --- | --- | --- |
| P1 | Honest location fixtures and provider preconditions | Baseline checks | NOT STARTED |
| P2 | Plain-language merchant result and focused demo entry | P1 | NOT STARTED |
| P4a | Local live-consent journey and current OAuth contract | P1, P2 | NOT STARTED |
| P3 | Merchant challenge attempt and completion reporting | P2; reuse P4a harness | NOT STARTED |
| P5 | Merchant outcome collection and evaluation report | P3 event/ownership conventions | NOT STARTED |
| P4b | Physical handset/operator proof | P4a + external prerequisites in §4 | NOT STARTED |

Build in table order. P4b can run as soon as its prerequisites exist; an absent
SIM or operator setup must not prevent local P3/P5 work. Do not label P4 complete
until P4b passes. One agent owns schema/migration integration; agents can review
or work on separate files, but must not independently allocate migration numbers
or change shared response models. Complete and validate one package before merging
its behavior into the next.

### Before implementation

1. Read this file, `README.md`, affected source/tests and a focused Graphify query.
   Inspect `git status`, branch and remotes. Preserve unrelated work. Use
   `.venv311`; do not use the stale `.venv` or read secrets into tool output.
2. Run the existing suite and Ruff commands in §5 to establish a baseline. The
   historical 506-pass result is context, not evidence that the new checkout passes.
   Record existing failures separately from regressions introduced by this work.
3. Save a signed test receipt and its exact payload, signature and public key for
   compatibility checks. Use synthetic subjects and an isolated database/key.
4. For each defect fix, add the focused failing test first and observe it fail
   for the intended reason. Tests must exercise the affected path directly: a
   greedy run that never selects location cannot validate location preconditions.
5. Keep policy weights, thresholds, signed field names and planner vocabulary
   fixed during these packages. If a correctness fix changes results, explain
   and remeasure them; never tune policy just to recover a demo number.

### P1 — Fix location evidence at the provider boundary

**Existing files:** `app/providers/mock.py`, `nac.py`, `vocabulary.py`,
`app/domain/schemas.py`, `app/api/routes_console.py`; tests named below.

1. Confirm the defect with direct `gather(Action.LOCATION_VERIFY, request)` tests:
   `NacProvider` returns INFO / `EVIDENCE_UNAVAILABLE` when
   `request.context.claimed_location` is absent; `MockProvider` currently returns
   its scripted match/mismatch. Assert the live SDK is never called without a claim.
2. Keep `claimed_location` optional on `RequestContext`. Add the same precondition
   to mock location gathering, before fixture selection. Preserve the normal
   `EvidenceLink` wrapper, provenance, consent metadata and accounting. Reuse a
   shared fact description if introduced; do not invent a provider result.
3. Add an explicit synthetic `Area(lat=31.9539, lon=35.9106, radius_m=2000)` at
   request construction sites whose story assumes a location claim. These are
   demo input coordinates, not an observed subscriber location. Start with
   `DEMO_ACTS['act6']` and Act II in `routes_console.py`.
4. Audit all duplicated requests: `demo/run_acts.py`, `tests/scenarios/test_acts.py`,
   `tests/test_chain_grade.py`, `tests/test_parallel_gather.py`,
   `scripts/false_decline_baseline.py`, `tests/fixtures/independent_evaluation.json`,
   and the README API example. `scripts/evidence_pack.py` and `scripts/planner_divergence.py` import the console acts.
   Add a claim only when the scenario explicitly assumes one. Keep intentional
   missing-input cases missing; document changed evaluation assumptions.
5. Test both providers with no claim, valid claim/match, valid claim/mismatch,
   and provider failure. The live fake must receive the exact circle/radius;
   the missing-claim test must assert zero SDK calls. Do not persist coordinates
   into `EvidenceLink`, prompts, receipts or diagnostic logs.
6. Rerun affected scenarios and evaluations. Baseline Act VI is six checks,
   CHALLENGE / DEGRADED, score .242; Act III is two checks, ALLOW /
   ATTESTED_FULL, .096. Act II should remain an adverse/decline demonstration
   when supplied its intended claim. Verify rather than assume these results.
7. Refresh reports, README example/caveat, screenshot and walkthrough only from
   the new outputs. Remove the fixture-gap caveat only after the regression passes.

**Required evidence:** direct parity regression; affected tests in
`tests/test_nac_provider.py`, `test_mock_scenarios.py`, `test_provider_vocabulary.py`,
`test_console.py`, `test_chain_grade.py`, `test_parallel_gather.py`, plus the two
benchmark tests and `test_evidence_pack.py`. A new
`tests/test_provider_preconditions.py` is appropriate for the shared contract.

**Done:** missing input produces unavailable in both adapters; intended fixtures
supply their claim; signatures still verify; all changed metrics are explained.

### P2 — Show the merchant what to do and why

**Existing files:** `app/static/judge.html`, `app/main.py`,
`app/api/routes_verify.py`, `routes_consent.py`, `app/agent/investigator.py`,
`app/domain/schemas.py`, `app/agent/explain.py`. **Proposed new file:**
`app/presentation.py` for a pure, deterministic projection of an existing Verdict.

1. Define the display mapping: ALLOW → “Proceed”; CHALLENGE → “Additional
   verification needed”; DECLINE → “Do not proceed”. Keep the original enum,
   grade and uncalibrated score visible as secondary details. Never rename fields
   inside signed `Verdict` or alter the decision to improve the presentation.
2. Build a deterministic presenter from normalized links, decision, grade and
   the issuing policy snapshot. Return a title, short summary, observed adverse
   facts, supporting facts and next action. Use signal templates; no LLM call
   or operator free-text interpolation. Cap displayed facts and use `textContent`.
3. Explain different CHALLENGEs accurately. The replacement case has a score
   between thresholds after exhausting its budget; it is not a consent failure.
   An unresolved-provider case must identify the unavailable check. If metadata
   cannot establish why the engine stopped, omit that claim. Never infer an
   event's exact age from a 240-hour yes/no query window.
4. Add optional `presentation: Presentation | None = None` to HTTP verification responses
   and the verdict SSE event, derived from the same presenter. Do not add it to
   `Verdict` or call `store.save` again. Both consent and ordinary verification
   must use the projection. Existing clients and cached responses lacking the
   field keep working; the UI falls back to the existing reason text. Cache the
   projection with new responses; never backfill old cached responses using today's
   policy or regenerate their signed history.
5. In `judge.html`, render the action first, then explanation, then audit details.
   Keep provenance visible. Label mock time “Demo duration”, explain the 650 ms
   pacing, and show receipt controls only after persistence succeeds. A stream
   disconnect/reconnect must not overwrite a completed result or revive old runs.
6. In `main.py`, redirect `/` to `/judge` only when demo mode is enabled; preserve
   the current non-demo route and credential gating. Do not expose arbitrary
   billable verification through the fixed judge fixture controls.
7. Align `app/agent/explain.py` prompt vocabulary with “uncalibrated policy score”
   rather than probability. Its optional answer remains read-only, grounded in
   structured evidence, and cannot change the signed verdict.
8. Browser-check both outcomes, a provider-unavailable outcome and signature
   tampering at desktop and 375 px width. Verify keyboard access, wrapping,
   long explanations, visible simulation labels and a clear return from receipt.

**Required evidence:** presenter tests against real synthetic Verdicts for all
three decisions and unresolved evidence; no invented facts; serialized signed
Verdict unchanged by presentation; HTTP/SSE agreement; old-response fallback;
`tests/test_judge.py`, `test_console.py`, `test_t4_ask_the_agent.py`,
`test_s10_xss_and_headers.py`, `test_s4_demo_mode.py` remain passing.

**Done:** a first-time visitor can identify the action and evidence without
reading a technical enum, and cannot mistake a CHALLENGE for an OTP Isnad sent.

### P4a — Build the live-consent journey locally

This package precedes P3/P5 because its small merchant harness is reused. The
public judge page remains a fixed mock demonstration.

**Existing:** `app/consent.py` (a file, not a package),
`app/api/routes_consent.py`, `app/providers/nac.py`, `app/config.py`,
`app/api/security_headers.py`, `scripts/handset_validation.py`.
**Proposed:** `demo/merchant_pilot/app.py`, `demo/merchant_pilot/static/index.html`,
`app/static/consent_complete.html`, `tests/test_merchant_pilot.py` and a sanitized
`docs/nac/number_verification_contract.json`.

1. Pin the current operator contract before wiring the UI. Record the official
   documentation URL, review date, installed SDK version, authorization parameters
   and expected token fields. The V1 documentation reviewed on 5 Sep requires
   separate state/nonce values, `prompt=none`, and a mobile connection. For its
   standard token flow, nonce is checked through the returned ID token. The
   current fallback URL omits nonce/prompt and the exchange reduces its result to
   an access-token string: this must be addressed, not assumed compatible.
   [Official V1 contract](https://networkascode.nokia.io/_docs/number-verification/number-verification-v1).
2. Retain independent random state and nonce in `ConsentRecord`; extend the
   internal provider begin/exchange contracts and all SDK/fake implementations.
   Preserve token-response fields long enough to validate the documented ID-token
   signature, issuer, audience, expiry and nonce using trusted discovery/JWKS.
   Never trust an unverified decoded JWT or silently drop mandatory arguments in
   an SDK compatibility fallback. Validate any required PKCE behavior against
   current docs. If provider behavior differs, document and resolve the contract
   before live use; do not bypass validation or invent an ID token in production.
3. Freeze the canonical request and its keyed commitment at consent creation,
   use that snapshot for verification, and test final `request_hash` against it.
   A mutable request object must not change the subject/context after approval.
   Preserve the existing API lifecycle and ownership: authenticated start,
   single-use public callback, authenticated status, then exactly one required
   NUMBER_VERIFY before optional planning. Test concurrent callbacks and duplicate
   completion. Keep successful completion responses available for their documented
   TTL even if another consent starts; audit `_sweep`, which currently removes
   terminal records on new record creation. Clear tokens on terminal transitions.
4. Build a separate single-merchant reference harness. Its server reads Isnad's
   base URL and merchant key from environment and calls the existing APIs with
   `httpx`; provider secrets stay only in Isnad. The browser must never receive,
   prompt for, store, or transmit either API key. Do not copy the console's
   sessionStorage credential pattern into this product flow.
5. For the initial pilot, bind the harness to loopback/private operator access
   and use an authenticated operator session: environment-configured pilot login,
   a random server-side session identifier, HttpOnly/SameSite cookie, expiry,
   logout, bounded login attempts, constant-time credential comparison and
   CSRF/origin checks for mutations. Require Secure cookies when
   deployed over HTTPS. This is a single operator harness, not a new SaaS identity
   system. Do not publish it unauthenticated or accept an arbitrary Isnad base URL.
6. Implement same-origin harness routes `POST /api/flows` and
   `GET /api/flows/{flow_id}`. At creation, validate phone/context and retain the
   immutable original request server-side; bind random flow ID, consent ID and
   eventual chain ID to the operator session. Reject changed request context on
   retry. Return only scoped display data, expiry and authorization QR. The
   subscriber must receive the provider authorization URL to authorize, but it
   must never expose merchant/provider keys. Mark responses no-store; keep URLs,
   phone inputs, state, code and tokens out of logs and retained screenshots.
7. Show “Scan on the phone being verified” and mobile-data instructions, with
   a server-generated QR pointing to the provider authorization URL. The operator
   page stays on the laptop; the subscriber needs no operator login or harness
   session. Show PENDING/EXCHANGING, AUTHORIZED/VERIFYING,
   COMPLETED, DENIED, FAILED and EXPIRED explicitly. Poll with bounded backoff,
   stop at expiry/terminal state, and perform completion once per flow on the
   server when authorized. A 409 in-progress response polls again; a completed
   response is reused. A failed or lost flow offers a fresh attempt, never an allow.
8. Keep the existing callback JSON contract for API/script clients. For browser
   requests whose positive `text/html` preference exceeds `application/json`,
   use a 303 to a generic same-origin
   `/consent/complete` page after handling the callback; no code, state, phone,
   consent ID or provider error text in the destination. Absent Accept, wildcard-only
   and tied preferences keep JSON. Set `Vary: Accept` and `Cache-Control: no-store`.
   Tell the subscriber to return to the merchant; do not invent a return URL or
   accept one from the request. Do not claim a redirect erases proxy logs or
   previously recorded history; application and proxy logs need separate redaction.
9. Display the persisted verdict through P2's presenter, its actual source and
   receipt link. Clear unnecessary raw request/token state at expiry/completion;
   retain only what permits scoped result retrieval for the stated session TTL.
   Keep browser refresh from triggering another operator call. Do not expand
   the public receipt API to expose merchant-flow state.

**Required evidence:** offline fake-provider contract plus browser journey;
`tests/test_consent.py`, `test_s9_consent_replay.py`, `test_nac_contract.py`,
`test_nac_provider.py`, `test_handset_validation.py`; new harness tests covering
no-key-in-browser-HTML/storage/network, unauthorized/cross-session access, CSRF, bad
state/nonce/ID token, token exchange once, denied/expired/provider failure,
non-HTTPS authorization URL, duplicate/reloaded completion, terminal-cache TTL,
HTML redirect vs JSON compatibility and unchanged signed receipt verification.

**Done locally:** a subscriber can use the consent journey with an offline fake,
all failure states are usable, and no real credentials or provider calls were used.
**Live completion is P4b below and remains separate.**

### P3 — Finish CHALLENGE without rewriting its receipt

This package records and displays the merchant's verification workflow. It does
not build an SMS/passkey provider or establish that a completed challenge proves
legitimacy. The minimal pilot supports manual review; other methods appear only
when connected to an actual merchant-owned integration.

**Existing:** `app/db/models.py`, `app/db/store.py`, `app/domain/schemas.py`,
`app/main.py`, `app/retention.py`, `app/api/routes_privacy.py`.
**Proposed:** `app/db/challenges.py`, `app/api/routes_challenge.py`,
`tests/test_challenge_followups.py`, a new migration under `migrations/versions/`.

1. Add an insert-only safeguard to `store.save`: an existing chain ID must not
   be overwritten with a new decision, timestamp, payload or signature. Resolve
   races with database constraints/transactions. Verification replay already
   returns a cached response; do not implement replay by re-signing the chain.
   Audit callers/tests that intentionally create legacy rows and keep migration
   fixtures separate from production save behavior.
2. Define a `ChallengeAttemptRow` (random ID, chain ID, database owner hash,
   method, created/expiry times) and append-only `ChallengeEventRow` (event ID,
   attempt ID, result, server reported time, reporting provenance, durable request
   fingerprint). Do not add these fields to `Verdict` or `EvidenceLink`.
   Authenticate ownership using the same owner context as `ChainRow.owner_hash`;
   it is distinct from the HMAC owner commitment inside the signed Verdict.
3. Proposed endpoints: `POST /v1/chains/{chain_id}/challenges` creates an attempt;
   `POST /v1/chains/{chain_id}/challenges/{attempt_id}/events` reports a result;
   `GET /v1/chains/{chain_id}/challenges` returns the owned timeline.
   Use merchant authentication/rate limits and a required bounded Idempotency-Key
   for writes. Enforce original decision CHALLENGE (409 otherwise); missing and
   foreign chains/attempts both return 404. Do not authorize with public receipt
   links or a caller-supplied owner field.
4. Define the attempt lifecycle: PENDING → PASSED / FAILED / ABANDONED / EXPIRED.
   Result provenance is always `merchant_reported` for merchant submissions;
   EXPIRED is a server timeout. Browser closure is not proof of abandonment.
   Capture one timestamp for ordering/expiry checks per transaction.
   Permit only one terminal result per attempt atomically; same retry replays,
   conflicting terminal result is 409. A deliberate new attempt receives a new
   ID and does not erase the earlier attempt. P5 handles later outcome corrections.
5. Persist idempotency with a unique owner/operation/key fingerprint and a
   domain-separated keyed fingerprint of the canonical request. Do not rely on
   the in-memory verification cache for durable followups. Same key/body returns
   the original response; same key/different body or target returns 409, including
   concurrent requests and restart. Reject extra JSON fields and free-text notes.
6. Extend the P4a harness with “Continue merchant verification” for CHALLENGE.
   Start the attempt, show the configured manual review or connected merchant
   verification, and let only the authenticated merchant backend report results.
   A subscriber callback/page must never self-assert PASSED. Keep simulated
   completion controls restricted to explicit mock demo flows.
7. Render verification outcome separately from order status: “Merchant reports
   verification passed” can enable the merchant to accept the order; it must not
   rewrite CHALLENGE to ALLOW or claim fulfillment. Show the original signed
   decision plus the later merchant report. Failed, abandoned and expired attempts
   retain their actual state and offer the merchant's configured next action.
8. Add an Alembic migration after the current head (do not edit applied 0001).
   Verify new tables on fresh SQLite and an upgrade from the existing schema.
   Add `challenge_attempt_ttl_seconds` (proposed pilot default 900) and
   `challenge_followup_retention_seconds` (proposed pilot default 2592000), with
   positive validation and documented configuration. These are product defaults,
   not legal requirements. Expire pending attempts at their deadline on reads/
   writes and by sweeper; retain their history until the retention deadline.
   Purge child events/attempts consistently, update privacy posture and `.env.example`,
   and test sweeper failure recovery within P3. Do not defer this to P5 or expose
   the reports in `/r/` or `/v1/receipts/`.

**Required evidence:** new challenge API/store tests, original payload/signature/
signed_at byte equality before and after all followups, insert-only regression,
owner and attempt isolation, all transitions, repeated/concurrent/restarted
idempotency, expired-attempt race, no raw identifiers/free text, authenticated
merchant reporting, migration upgrade/downgrade and browser refresh recovery.

**Done:** the pilot can reach an honestly labelled merchant-reported challenge result from
CHALLENGE while the original receipt remains independently verifiable.

### P5 — Collect outcomes before calibrating scores

**Proposed:** `app/db/outcomes.py`, `app/api/routes_outcomes.py`,
`tests/test_outcomes.py`, `scripts/merchant_outcome_report.py`, and the next
Alembic migration. Reuse P3's ownership/idempotency conventions, not its result
semantics. Outcome APIs may refer to any owned decision, including ALLOW/DECLINE.

1. Define an append-only `MerchantOutcomeEventRow`: random ID, chain ID, database
   owner hash, dimension/value, constrained basis, merchant occurred time, server
   reported time, optional supersedes event ID and durable idempotency fields.
   Fixed provenance is `merchant_reported`. Store no raw phone, coordinates,
   order/customer identifier, OAuth value or arbitrary notes. `extra='forbid'`
   should reject accidental sensitive payloads rather than silently ignore them.
2. Keep three dimensions independent: challenge execution comes from P3;
   order status is ACCEPTED/FULFILLED/CANCELLED/UNKNOWN; fraud assessment is
   CONFIRMED_FRAUD/CONFIRMED_LEGITIMATE/INCONCLUSIVE/UNKNOWN. A challenge pass,
   an accepted/delivered order, a payment dispute or a lack of feedback alone
   does not establish either confirmed fraud label. Record the merchant's basis
   (e.g. manual investigation or customer confirmation) with the assessment.
3. Add authenticated/rate-limited POST/GET
   `/v1/chains/{chain_id}/outcomes`. Enforce chain ownership first and use durable
   idempotency as in P3. Validate UTC timestamps, reject impossible future reports
   outside documented clock tolerance, and accept explicitly labelled late
   reports. The reporting time is server-owned and cannot be backdated.
4. Correct by appending an event that supersedes a current event of the same
   owner, chain and dimension. Atomically reject cross-chain supersession,
   competing corrections of an already superseded event and cycles. Never UPDATE
   a past label. Provide an authenticated projection of current labels plus the
   timeline; no outcome is added to signed network evidence or public receipts.
5. Add a small merchant reporting panel to the harness. Show “Not yet reported”
   for missing outcomes and distinguish it from INCONCLUSIVE or explicit UNKNOWN.
   Permit order and fraud updates separately; report PASSED in P3 without filling
   a fraud outcome automatically. Keep demo observations excluded from live reports.
6. Add explicit positive retention settings for challenge and outcome metadata;
   document the pilot's chosen durations and their purpose before rollout, without
   presenting them as legal requirements. Purge by server-reported time and remove
   dependent attempt/event rows consistently. Update `retention.py`, `/v1/privacy/posture`,
   `.env.example`, tests and operator documentation. Disclose the existing signed
   chain retention separately (currently indefinite); do not promise chain deletion
   that the application cannot perform. Any new export must have a defined retention.
7. Build an owner-scoped offline report first, not a public dashboard. Join current
   labels to original signed decisions; filter synthetic/mock runs and show
   observation date, follow-up horizon, eligible denominator, labelled count,
   missing/unknown count, challenge completion, reported abandonment and recorded
   costs. Report false declines only among independently labelled legitimate
   cases and adverse allows only among labelled fraud cases. State selection and
   delayed-reporting limits; never turn unreported/expired cases into negatives.
8. Tests must separate PASSED from confirmed legitimacy, retain unknown and late
   feedback, ignore superseded assessments in current counts, and exclude mock
   fixtures. Include ownership, concurrent idempotency/correction, timestamp,
   migration, retention boundary and no-leak tests. Confirm original signatures
   and public receipt output are unchanged by all reports.
9. Do not automatically retrain or tune policy in this package. A later calibration
   proposal needs adequate real labels, a defined observation window, evaluation
   on held-out outcomes, correlation review and documented operating tradeoffs.
   Keep the current score explicitly uncalibrated until such evidence exists.

**Done:** merchants can report what actually happened, corrections are auditable,
and the report exposes unknowns and denominators without claiming production accuracy.

### P4b — Prove one supported handset end to end

1. Finish P4a and the external prerequisites in §4. Recheck the current operator
   contract and registration; configure the applicable subscriber consent copy.
   Do not assume a paid/live run is authorized by this planning request.
2. Use `scripts/handset_validation.py contract` first, then follow
   [HANDSET_VALIDATION.md](HANDSET_VALIDATION.md) on a controlled HTTPS deployment
   with one worker **and one replica**, persistent signer/pepper, demo off and
   actual supported operator/subscriber. Follow the current V1 mobile-data requirement.
3. Retain a redacted report: PENDING → AUTHORIZED → COMPLETED; exactly one required
   Number Verification link with `source=nac` and NUMBER_MATCH or NUMBER_MISMATCH;
   valid receipt under a trusted key; duplicate completion reuses the result.
   An HTTP 200 or `source=nac` plus unavailable evidence alone is not a pass.
4. Exercise denial/expiry and operator failure locally, and live only when that
   particular test is available and authorized. Record unsupported cases honestly.
   `physical_handset_reported` is a tester declaration, not device telemetry.
5. Record actual operator/version, test date, redacted report path and remaining
   gaps. Mark P4b complete only on this evidence. If operator inputs are unavailable,
   state exactly which input is missing and finish all independent local packages.

### Package exit checklist and next-agent record

- Run focused tests, the full suite and Ruff after implementation; run UI checks
  for the affected flows. Run migrations against a disposable old database when
  adding tables. Record PostgreSQL validation separately if no test server exists.
- Reproduce evidence pack, both evaluations and local consent contract when a
  provider/fixture/policy/consent change affects them. Verify old and new signed
  receipts. Do not retain a stale “506 tests” or benchmark count after a new run.
- Refresh affected README text, demo screenshots and docs from observed results;
  update this status ledger and Graphify. Avoid another chronological log dump.
- Record per package: commit/worktree, changed files, contract decisions, failing
  regression observed, passing commands/counts, UI evidence, metric differences,
  local/live status, known gaps and the exact next step. Mark partial work PARTIAL,
  never COMPLETE because a happy-path screenshot exists.
- These plans do not authorize deployment, provider spend or publication. During
  implementation, apply the user's then-current authorization; do not request
  approval again for already authorized work. Use the private remote only when
  a push is requested and never infer a public push.

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
| Consent lifecycle | `app/api/routes_consent.py`, `app/consent.py` |
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
- Private remote: `AhmadShadeed32/isnad-private`, `main`; last pushed `942dcc2`.
  Public `origin` is a different destination. Do not infer a public push from a
  private publication request.

## 6. Latest session

**Intent — 5 Sep:** add a source-checked, step-by-step implementation plan for
all five product recommendations, including dependency order, proposed contracts,
file ownership, failure tests and completion evidence. This request is for the
plan only; app changes, deployment and provider calls are not part of this pass.

**Completion — documentation only:** all five recommendations now have ordered
packages, dependency/status ledger, source files, proposed contracts, failure tests
and objective exit criteria. A second review checked auth/callback compatibility,
retention dependencies and receipt immutability. Updated the entry-point note and
replaced the handset procedure's untracked runbook reference with this plan.
Local links/anchors and diff whitespace verified; Graphify refreshed. No app
implementation, deployment, provider calls, commit or push in this pass.
