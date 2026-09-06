# Isnad — compact handoff

Updated 6 September 2026. **Read this file first.** It replaces the long running
log with current facts and an implementation plan. Read §6 for submission gates,
§7 for the competition feature build order, and §3 for the underlying product
contracts. The complete earlier log is preserved
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
- P1 implementation record reports **516 tests passed** and Ruff clean. The
  earlier 506-test review also browser-verified both judge outcomes and valid →
  tampered-invalid → restored receipt signatures; P1 did not repeat that browser check. A receipt proves issuance/integrity, not provider truth.
- P2 (6 Sep, see §8) added a plain-language presenter (`app/presentation.py`)
  and re-verified all of the above by browser: ALLOW, CHALLENGE (both the
  DEGRADED-corroboration and UNRESOLVED-provider shapes), and tamper detection,
  at desktop and 375 px width. **541 tests passed**, Ruff clean.

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

This is the implementation contract for the five product suggestions. **Use the
status ledger below; P1 has been implemented.** New files/routes/models in unfinished
packages remain proposals until their implementation is verified. Inspect the current checkout before applying the plan;
record any justified change to these contracts here before implementing it.

### Execution order and completion ledger

| Package | Deliverable | Depends on | Status |
| --- | --- | --- | --- |
| P1 | Honest location fixtures and provider preconditions | Baseline checks | COMPLETE (implementation record in §8) |
| P2 | Plain-language merchant result and focused demo entry | P1 | PARTIAL (6 Sep implementation session; see §8) |
| P4a | Local live-consent journey and current OAuth contract | P1, P2 | DONE LOCALLY (6 Sep implementation session; see §8) |
| P3 | Merchant challenge attempt and completion reporting | P2; reuse P4a harness | DONE LOCALLY (6 Sep implementation session; see §8) |
| P5 | Merchant outcome collection and evaluation report | P3 event/ownership conventions | DONE LOCALLY (6 Sep implementation session; see §8) |
| P4b | Physical handset/operator proof | P4a + external prerequisites in §4 | NOT STARTED |

For the full product roadmap, build in table order; §6 gives a smaller submission scope.
P4b can run as soon as its prerequisites exist; an absent
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

## 6. MENA Ignite submission priorities — reviewed 6 September 2026

**Read this section before executing the full P1–P5 roadmap.** This is a
competition delivery plan, not a claim that these changes guarantee a win.
All H-items below are recommendations and NOT STARTED. Preserve the larger
merchant pilot plan; do not attempt to finish its entire scope before submission.

### Verified event facts and unresolved requirements

- The [HackerEarth event page](https://www.hackerearth.com/community/challenges/hackathon/mena-ignite-hackathon/)
  lists prototype close as **13 Sep 2026, 18:29 UTC / 21:29 Asia/Riyadh** and
  teams of 1–5. Its detailed judging/rules/submission tabs could not be reliably
  retrieved in this review; their weights, file limits and access rules are **unverified**.
- [GSMA's announcement](https://www.gsma.com/solutions-and-impact/gsma-open-gateway/gsma_events/gsma-mena-ignite-open-gateway-hackathon/)
  requires CAMARA APIs and AI applied to regional problems. It describes telecom
  executive judges and a later winners' showcase. Its overall event window extends
  beyond the prototype deadline; do not treat that as an extension for submission.
- The [organizer's event post](https://www.linkedin.com/posts/hackerearth_menaignitehackathon-opengateway-camaraapis-activity-7480246882603270144-QrtM)
  names Nokia NaC, agent orchestration, and themes including digital identity and
  fintech. Isnad fits those themes; confirm the exact selected track in the team's form.

**Deadline conflict:** the older local `docs/PROJECT_BRIEF.md` says 11 September,
while the public portal says 13 September. The former is an internal note, not
fresh official evidence. Ask for the team's Phase 2 email/form and resolve the
conflict. Until resolved, plan delivery by **11 September** and aim for an internal
artifact freeze on **10 September**. These are conservative planning targets,
not newly invented official deadlines. Exact evaluation weights, video length,
required deck/template, repository visibility, AI/tool restrictions, simulator
acceptability and any existing-code disclosure rules must be checked in the
current team submission instructions. Do not guess them from Phase 1 material.

### H0 — Confirm the submission contract before building more

1. Obtain/read the authenticated Phase 2 instructions or organizer email without
   submitting or messaging anyone automatically. Record deadline/timezone, rubric,
   required files, length/size limits, repo/demo access, track and tool requirements.
   Resolve the 11/13 Sep conflict. Replace the unknowns above only with a dated source.
2. Prepare one submission manifest: artifact name, local path, delivery URL,
   revision, access-test result and requirement satisfied. Proposed path:
   `docs/submission/SUBMISSION_MANIFEST.md`. Do not add inaccessible local-only
   runbooks or an old video just because those files already exist.
3. Verify that judges can access the **private** repository through the permitted
   sharing mechanism. A private GitHub URL alone does not grant access. Do not
   make `origin` public, invite accounts, upload files or submit on the user's
   behalf without the applicable authorization.

**Pass:** every required artifact/access rule is sourced and the submission
manifest has no unknown mandatory field. Current portal-tab access trouble is a
verification gap, not evidence that no requirements exist.

### H1 — Make the AI contribution visible and measurable

**Why this changes priority:** the README launch command explicitly uses greedy
planning. That is a reproducible baseline, but it does not demonstrate the
existing model planner. This review does not establish that an LLM is mandatory
or that greedy disqualifies the entry; it recommends showing the implemented AI
rather than leaving the judges to infer it from an “agent” label.

1. Confirm the completed P1 regression still passes and finish essential P2 result copy. Review
   `app/agent/planner.py`, `app/agent/gemini.py`, `app/agent/investigator.py`,
   `scripts/planner_divergence.py` and `tests/test_llm_planner.py`.
2. Use a separately configured, operator-controlled LLM demo process with the
   model key only on the server. Do not mutate global `settings.planner` per
   browser request or turn a public toggle into unrestricted model spend.
   Keep the greedy baseline available as a clearly labelled separate run.
3. Show the model's actual next-check selection, concise selection rationale,
   remaining evidence budget and stop decision. These are observable outputs,
   not hidden chain-of-thought. One scenario button starts the merchant intent;
   the user must not choose each network API by hand.
4. Compare LLM and greedy on the same fixed requests, evidence fixtures and policy.
   Use the divergence script with an explicitly bounded model-call budget when
   authorized. Report answer/fallback rate, evidence path, calls, verdict/grade
   disagreements and model waiting time. Do not reuse the older untracked brief's
   “18% fewer checks” claim or select only favorable trials.
5. The comparison script does not persist/sign its investigation results. Record
   a separate actual API/UI run for a signed AI-planned receipt. Each receipt and
   trace must retain the actual `llm`, `greedy`, mixed or policy-only label.
   A fallback is never presented as a successful model decision.
6. Exercise timeout, malformed model output and a STOP-capable planner against
   required-check gates. Do not loosen policy or remove fallback to manufacture
   visible divergence. If the model adds no measured benefit, report that result
   and explain its bounded role rather than claiming superior accuracy.

**Pass:** a judge can see which action the AI selected, verify that policy still
controls safety boundaries, and inspect a genuine run plus an honest baseline.
Do not make the whole submission depend on a model request succeeding on stage.

### H2 — Show verifiable Nokia NaC integration, with precise scope

1. Create a small API evidence inventory using `docs/nac/`,
   `scripts/t1_probe.py`, `scripts/t1_capture.py` and `tests/test_nac_contract.py`.
   For each used action record SDK/API version, test date, environment,
   normalized result and reproduction path. Identify adapter reports as such;
   a JSON key called `raw` is not proof that it contains a raw operator response.
2. Separate three claims in the UI and recording: local MockProvider fixtures,
   requests to a vendor simulator through NaC, and actual supported-subscriber
   operator evidence. A historical NaC capture is useful integration evidence,
   but is not today's live run or a physical handset consent proof.
3. After confirming permitted tools/simulation with H0, prefer a narrowly scoped
   authorized NaC demonstration using an API the team can actually exercise.
   Keep SDK keys, test identifiers and transient authorization values out of
   screenshots/logs. Never count `CONSENT_REQUIRED` as working Number Verification.
4. Complete P4a/P4b if the supported handset, operator registration and time are
   available. Otherwise preserve that milestone as unproven and use accurately
   labelled evidence; do not bypass OAuth to finish a recording.
5. `routes_console.py` explicitly constructs `MockProvider(step_delay_ms=650)`:
   setting a provider environment variable alone does not turn Judge Mode into
   a live demo. Use the authenticated provider path or P4 harness for that proof.
   Do not expose arbitrary live requests through fixed stage controls.
6. Do not use `HybridProvider` as proof that no fallback occurred: it intentionally
   substitutes a mock link after a live exception. Any mixed run must show sources
   per link and be called mixed. Use strict NaC mode for a claimed live proof.

**Pass:** judges can distinguish fixture execution from sponsor-platform access
and physical operator proof. Every claimed working API has inspectable evidence.

### H3 — Make one MENA customer problem specific

1. Choose one initial buyer and workflow: for example, a Jordanian merchant
   reviewing a high-value cash-on-delivery order. Keep caller attestation and
   session monitoring for questions; avoid presenting three businesses at once.
2. Make the product action concrete with P2: hold for merchant verification,
   proceed, or stop. Show the warning, supporting facts and remaining uncertainty.
   Do not frame a COD example as a card chargeback workflow.
3. Add Arabic/English action labels and a tested RTL layout to the judge/receipt
   presentation if the team can review the translation. Keep source/signed enum
   values unchanged and test phone widths, digits and mixed-direction API names.
   This is a proposed usability improvement, not a published scoring requirement.
4. Keep monetary inputs consistent. Relabelling USD as JOD/SAR would change the
   meaning of a model that currently compares raw amounts to a fixed threshold.
   Preserve existing synthetic amounts/currency until currency handling is designed
   and tested; localize the story without inventing financial comparisons.
5. Prepare three discovery questions for a merchant/mentor: what currently triggers
   manual review, what evidence would justify releasing the hold, and what outcome
   data they can supply for evaluation. Conduct contact only with explicit permission.
   Record actual feedback with attribution permission; never invent a pilot, quote,
   regional market statistic or saved-revenue figure.

**Pass:** a judge understands who buys Isnad, where it fits, and what the customer
experiences. At least one real feedback item is desirable, not falsely mandatory.

### H4 — Demonstrate the benefit without hiding the tradeoff

1. Put the replaced-SIM CHALLENGE and clean ALLOW beside a clearly defined baseline.
   A “decline every SIM change” rule is an illustrative baseline, not a claim about
   all banks. Use the existing authored evaluation/full-evidence comparators for
   quantitative statements; P1 may change their inputs and requires a fresh run.
2. Show decision, evidence-call count, evidence strength and unavailable checks.
   Include adverse and unavailable cases as well as favorable ones. Keep the known
   expectation disagreements visible; do not equate fewer calls with higher accuracy.
3. Present network/model cost as unpriced or normalized until actual contracted
   prices exist. Separate 650 ms stage pacing from measured provider/model latency.
4. Explain the receipt's advantage by verifying it and altering a byte. This is
   a demonstrable integrity benefit; it does not establish provider truth, regulatory
   acceptance or a “fraud-proof” system.
5. Explain how merchant-reported outcomes in P5 would validate business impact.
   For this submission, a concrete evaluation plan is preferable to building the
   entire analytics subsystem without any real merchant labels.

**Pass:** every number on screen can be reproduced, scoped and challenged.

### H5 — Ship one coherent, remotely accessible demonstration

1. Review H0's delivery format before deciding video/deck duration. The previous
   `docs/demo/isnad-demo.mp4` is obsolete; the corrected video sources have not
   established that the shipped binary matches the app. Do not reuse it blindly.
2. Record the actual current application: customer problem → AI selection →
   evidence/provenance → merchant action → receipt verification/tampering →
   clean-case early stop. Include NaC evidence as its own accurately labelled beat.
   Use the allowed runtime and keep a shorter backup cut only if useful.
3. Use the operator-controlled demo/harness with a remote access setup already
   reviewed for its exposed routes. A localhost README link cannot be opened by a
   remote judge. Test delivery from a separate device/session with no developer
   login or cached secrets. If hosting is not ready, provide an accessible recording
   and reproducible setup where the submission rules permit it.
4. Keep the demo bounded: fixed synthetic requests, rate limits, no merchant/model
   keys in browser code, no arbitrary billable API surface, and no live-mode fixture
   injection. An unlisted URL is not authentication for paid operations.
5. Freeze one commit and reconcile README, screen labels, video, idea-capture form,
   any required deck and benchmark report against it. Check all links and judge
   access. Record artifacts and access tests in H0's manifest. Prepare a replay
   recording for network/model failure; identify replay as recorded.

**Pass:** a remote judge can see the product and supporting proof without local
setup surprises, contradictory metrics, stale footage or missing permissions.

### Recommended time allocation, not the official rubric

- **6–7 Sep:** H0 confirmation; verify P1 and finish essential P2; prepare H1's model comparison.
- **7–9 Sep:** H1 bounded run and H2 proof that is feasible with available access;
  H3 focused merchant story/translation; rehearse H4's evidence comparison.
- **10 Sep:** freeze, record, reconcile artifacts and test judge access under H5.
- **By 11 Sep:** target delivery until the conflicting internal deadline is resolved.
  Use any confirmed remaining time for defects and rehearsal, not new product branches.

Defer full P3 challenge persistence, P5 outcome analytics, multi-replica state,
new network products and broad merchant onboarding until after submission unless
H0 explicitly makes one essential. P4 live proof is valuable but must not consume
the entire window if operator inputs are unavailable. These priorities supersede
§3's execution order **for the hackathon submission only**; they do not mark any
unfinished product package complete.

## 7. Competition feature implementation plan

**Status: planning only, 6 Sep 2026.** Every I-item below is NOT STARTED as an
extension, even where it builds on working functionality. This section collects
the competitive lessons and additional product suggestions in one build order.
It does not supersede P1–P5's correctness contracts or H0–H5's submission gates.

### Evidence behind the recommendations

No other MENA Ignite submission was verified in the public search. These are
lessons from the **March 2026 Barcelona Open Gateway hackathon**, not claims
about this event's competitors or judging rubric. In
[GSMA's recap](https://www.gsma.com/solutions-and-impact/gsma-open-gateway/open-gateway-hackathon-at-talent-arena-showcases-developer-innovation-using-network-apis/),
Stage Flow won with event safety/response coordination; Smart Focus placed second
with AI video optimization and reported bandwidth savings; ResiliNet placed third
with location-based personal safety. Our inference is to make the buyer, essential
network contribution, measurable benefit and resulting user action equally clear.
These proposed features are not a claim of global novelty or a guaranteed win.

### Shortlist, dependencies and scope

| ID | User-visible result | Reuses / depends on | Delivery priority |
| --- | --- | --- | --- |
| I1 | Inspect and replay the AI's actual check selections | H1, P2, existing SSE | Core submission proof |
| I2 | Change one synthetic fact and compare the resulting investigation | I1 artifacts, shared runner below | First optional demo extension |
| I3 | Compare evidence budget, calls and decisions fairly | H4, shared runner | Core submission proof; static report first |
| I4 | Demonstrate honest behavior when evidence or the model fails | Shared runner, P2 | Alternative optional demo extension |
| I5 | Complete a challenged customer's recovery journey | P4a, P3 | Pilot stretch; simulated storyboard first |
| I6 | Arabic/English merchant journey with accessible mobile receipts | P2, H3 | Core usability; translation review required |
| I7 | Download and verify the exact receipt without the server | Existing receipts, H4 | Small proof extension after core gates |
| I8 | Show what changes after checkout trust is revoked | Existing sessions, I11 order mapping | Mock extension first; real enforcement later |
| I9 | Let a judge choose a bounded unfamiliar scenario | I2 or I4 | Optional, after one extension is stable |
| I10 | Know which provider capabilities are actually ready | H2, P4a | Read-only evidence inventory first |
| I11 | Integrate a merchant order and explicit location claim | P4a, P2; P3 for challenge result | Pilot work after submission |
| I12 | Measure outcomes and compare a future policy safely | P5, I3 | Post-submission; authored demo report only now |
| I13 | Issue a reviewer link with a limited access window | Existing receipts, P3 persistence conventions | Post-submission |
| I14 | Resume an interrupted evidence trace from its last event | I1, durable event storage | Post-submission unless remote demo requires it |

**Minimum submission:** H0–H5, remaining P2 fixes, I1's recorded real-model run,
I3's reproducible report, and I6's reviewed merchant wording. Full Arabic support
can stay incomplete if no reviewer is available. Then select **I2 or I4** as the
main interactive extension; I7 is useful if time remains. Do not start all fourteen
at once. The full plans remain available for later agents without turning the
deadline into a requirement to ship fourteen unfinished features.

**Coverage of earlier advice:** Stage Flow's clear buyer maps to H3/I5/I11;
Smart Focus's measurable efficiency maps to H1/H4/I1/I3; ResiliNet's actionable
outcome maps to P2/I4/I8. Receipt proof maps to I7, regional usability to I6,
live evidence to H2/P4/I10, and merchant learning to P5/I12. Original P1–P5
remain the implementation source for those packages; do not create duplicate
challenge, consent, or outcome subsystems under an I-number.

### Shared implementation contract for I1–I4 and I9

1. First close P2's recorded gaps: exercise real Tab/Enter traversal and visible
   focus, and wrap the receipt evidence table for usable 375 px scrolling. Do not
   change scores, thresholds or signed fields. Re-read the current ledger before
   assigning work; new migrations still have one integration owner.
2. Proposed shared files: `demo/lab/models.py`, `demo/lab/runner.py`,
   `demo/lab/fixtures.json`, `scripts/build_judge_lab.py`, `tests/test_judge_lab.py`.
   Start as an offline generator of fixed synthetic artifacts. Pin mock provider,
   deterministic planner/hypothesis and isolated state before application imports.
   Reuse `Investigator`, `PolicyEngine` and normalized provider vocabulary; do not
   implement a second decision engine in JavaScript or calculate grades ad hoc.
3. Define a versioned `LabRun` artifact with `schema_version`, `run_id`,
   `scenario_id`, fixture digest, full policy-file digest, code revision/dirty flag,
   generated UTC time, actual planner/source labels, timing basis, ordered events,
   outcome and optional receipt reference. Export only allowlisted synthetic context;
   use `claimed_location_present`/variant IDs, not coordinates, in trace/export JSON.
   Keep any required coordinates in the private authored input fixture only.
   Include the exact fixture/policy files in a private reproduction pack; the public
   pack references redacted fixture IDs. For a dirty tree, include the relevant
   source patch privately or mark full reproduction unavailable. A digest identifies
   a file; it is not a signature or proof of trustworthy origin.
4. Each trace event has `run_id`, monotonic `sequence`, event type, phase,
   actual selection source, action, bounded public rationale, budget before/after
   and evidence step reference when applicable. Treat optional trace fields as
   additive. Labels must distinguish a performed run, prerecorded replay and a
   hypothetical branch. Trace/export metadata stays outside signed `Verdict`.
5. Use an allowlisted `variant_id` to select an authored synthetic change. Do not
   accept raw phones, arbitrary signal/weight overrides, provider URLs or model
   configuration from the public page. If later executed server-side, add a
   separately reviewed demo-only fixed-fixture route with the same demo-token,
   owner isolation, rate/concurrency and request-size gates as the existing console.
   Serve generated artifacts first; they need no new billable endpoint.
6. Add explicit optional keyword-only `planner` and async `event_sink(dict)`
   injection to `Investigator` alongside its existing engine/provider arguments.
   Route its emissions through that sink, defaulting to existing `emit`; extend
   `build_investigator` with optional engine/planner/sink overrides and test unchanged
   defaults. The lab passes fresh per-run instances plus a private recording sink.
   Never mutate process-global `settings`, the cached engine, mock
   trip state or production policy to service a web request. For CLI isolation,
   subprocesses with fixed environment are acceptable. LLM trials remain a separate
   bounded operator job under H1, not a model toggle on the public lab.
7. Historical `Verdict.policy_snapshot` contains only part of the policy. It is
   insufficient to reproduce every planner/grade decision. Replay complete captured
   synthetic packs; an old receipt can show its signed arithmetic but must report
   full policy replay as unavailable when the required inputs are absent.

**Shared acceptance:** repeatable deterministic fixture paths/outcomes; unchanged
original signed payloads; no model/network call in offline tests; cross-run state
isolation; provenance visible on every artifact; malformed/oversized input rejected;
and all existing consent, required-check, signature and ownership regressions pass.

### I1 — Decision trace and honest AI replay

**Moment to demonstrate:** the judge sees which check the AI selected, what the
provider answered, and when deterministic policy required another check.
Existing SSE already exposes selections; the new work is coherent capture/replay
and a real-model evidence pack, not a new claim that traces have just been invented.

1. Audit `app/agent/investigator.py`, `planner.py`, `gemini.py`, `hypothesis.py`,
   `app/events.py`, `app/static/judge.html` and `scripts/planner_divergence.py`.
   Reuse existing `decision`, evidence and verdict events. Add sequence/order
   metadata where needed and a per-run recording sink; do not subscribe across
   merchants or export unrestricted event dictionaries.
2. Render action → normalized answer → budget movement → merchant result.
   Label each selection `llm`, `greedy` or `policy` from its actual source. Show
   only the brief returned rationale and structured facts, never invented model
   reasoning. If a rationale was not captured, say so; do not generate it later.
   Existing fallback code discards its failure reason: add optional bounded internal
   diagnostics to `Choice` and trace events (`no_key`, `timeout`, `malformed`,
   `invalid_action`, `call_cap`, `provider_error`, or absent when unknown). Never
   export exception text or rename signed planner labels. Align the planner prompt's
   current probability wording with the documented uncalibrated policy score.
3. Extend the H1 CLI comparison with a hard total model-attempt cap in addition
   to its existing wall-time/trial limits. Count actual HTTP attempts at the shared
   client wrapper, including `_install_retries`, across all trials/investigations.
   The current hypothesis function is deterministic; do not count fictitious model
   calls for it. Report timeouts/fallbacks and stop scheduling at the cap. Separate
   production-timeout runs from experiments with longer retry windows.
4. Capture all trials under fixed fixtures/policy, then obtain a separate signed
   verdict through the actual API path. Export allowlisted synthetic trace plus
   the exact receipt bytes. Replay controls scrub the recorded timeline without
   resending requests; display recording time and original model identity.
5. Test missing/duplicate/out-of-order events, disconnect during execution,
   reconnect after persistence, model timeout/malformed output and STOP against
   required checks. `done` in the display requires persistence confirmation;
   selecting a new run cancels old rendering, not another owner's work.

**Accept:** an auditor can reconcile every check with its evidence link, see
fallbacks, reproduce the greedy comparison, and verify the separately saved AI
receipt. A replay is visibly recorded and cannot incur additional model spend.

### I2 — One-fact counterfactual explorer

**Moment:** “What if the SIM had not changed?” produces a separate hypothetical
investigation beside the original, including cases where the decision stays the same.

1. Create a small authored matrix in `demo/lab/fixtures.json`: original replaced
   SIM, stable SIM, mismatched number, unavailable location, and missing location
   claim. Use legal action/result/signal combinations from `vocabulary.py`; each
   variant names exactly the changed input/fact and leaves the rest fixed.
2. Run base and variant through the shared runner with the same deterministic
   planner and full policy. Recompute all affected choices and grades. Changing a
   final score alone misses required checks, budget exhaustion and stopping rules.
   Do not reuse `app/policy/counterfactual.py` for this: it currently compares
   pricing/OTP assumptions, not alternate network evidence.
3. Produce `Comparison` with base/variant run IDs, changed field, before/after
   synthetic value, verdict/grade, path, cost units and unchanged policy digest.
   If a changed action is never reached, explicitly say it had no observed effect
   in this run. An unavailable required input must not become a positive fact.
4. Add side-by-side read-only controls to the judge lab. Visually retain the
   original result and signature, captured separately through the normal API path.
   Branches are unsigned and labelled “Hypothetical fixture”; do
   not persist them as real merchant decisions or suggest customers change answers
   to obtain approval. Require a new real verification for any real-world change.
5. Test no-change parity, one-change isolation, identical-decision variants,
   missing-claim precondition, and byte-identical original receipt after exploring
   every variant. Test concurrent comparisons so one cannot alter another's fixture.

**Accept:** the comparison demonstrates policy sensitivity, not a prediction that
changing a fact will prevent fraud or guarantee ALLOW. No invented live answer,
current-policy rewrite of an old receipt, or hidden production threshold change.

### I3 — Evidence budget and decision comparison

**Moment:** see where Isnad stops early and where more evidence changes the answer.

1. Reuse `scripts/independent_evaluation.py`, `false_decline_baseline.py` and H1's
   planner comparison. Freeze the complete authored dataset before running; include
   clean, adverse, conflicted and unavailable cases. Keep independent expectation
   labels separate from generated outcomes. `false_decline_baseline.py` currently
   mutates global `SCENARIOS` and engine thresholds: use it as an isolated CLI
   reference, or refactor those helpers to fresh explicit inputs before reuse.
2. Generate rows for greedy, full-evidence/same-policy and the existing authored
   corroboration comparator. Add actual LLM rows only when H1 produced them.
   Display calls, configured cost units, decision, grade where defined, expectation
   disagreement, fallback and unavailable checks. Preserve every row/error.
3. Optional budget exploration uses a small fixed server-authored budget grid
   with isolated policy copies. Mark these as experimental policy variants; all
   other policy fields stay fixed. Show CHALLENGE when evidence cannot be afforded,
   and report rather than hide non-monotonic outcomes. Never change live defaults.
4. Build a comparison view from generated JSON with dataset/policy/code digests
   and a download link. Distinguish paid provider attempts from successful answers,
   zero-cost local checks, model attempts and stage pacing. Keep unknown USD prices
   null with a basis/source; configured units are not actual contracted charges.
5. Verify totals against raw rows, zero-denominator handling, partial-run reporting,
   known expectation disagreements and failed calls. Check calculations directly
   with a small hand-audited fixture as well as the full dataset.

**Accept:** every displayed saving has a named baseline/denominator and every
tradeoff is visible. Synthetic expectation agreement is not production accuracy;
lower call count alone is not proof that AI helped.

### I4 — Network failure and recovery demonstration

**Moment:** a judge selects “provider unavailable” and sees the unresolved check,
honest merchant action and an independently recorded recovery attempt.

1. Add a lab-only provider wrapper in `demo/lab/faults.py` around mock fixtures.
   Allowlist normalized timeout, unavailable evidence, synthetic `CONSENT_REQUIRED`
   and delayed-result profiles. This does not test real OAuth expiry; use P4a for
   that lifecycle. Use fake clocks/delays in tests; never inject faults into NaC
   or monkeypatch a shared provider used by other sessions. Normalize simulated
   timeout inside the wrapper to INFO/`PROVIDER_UNAVAILABLE`. `_call()` currently
   does not catch raw provider exceptions; raising `TimeoutError` there would abort
   before a verdict, not demonstrate the planned unresolved result.
2. Run each profile through the real investigator. Required evidence remains
   required, and missing answers stay unavailable rather than PASS. If remaining
   adverse evidence supports DECLINE, retain that outcome; a provider failure does
   not imply that every scenario must return CHALLENGE.
3. Extend P2's unresolved display with recorded check status and next action.
   Separate “network did not answer” from “network reported a mismatch”. Demonstrate
   model failure through I1's fallback path separately from telecom failure.
4. Offer “Replay recovery” against an authored healthy fixture as a new run.
   Retain the original outcome and show the difference. A fresh real-provider retry
   belongs to P4's authenticated flow with new verification/idempotency semantics;
   refreshing the display must not silently buy new checks.
5. Test bounded attempts, cancellation, slow late replies after a new run,
   missing required evidence, cross-run isolation and default mock behavior with
   fault injection disabled. Assert zero external calls in the lab.

**Accept:** the demonstration exposes failure behavior and recovery without
pretending a live outage occurred, silently substituting mock evidence, or claiming
guaranteed availability. Only display a specific stop reason when it was recorded.

### I5 — Customer recovery after a challenged checkout

**Moment:** a legitimate customer is given a clear next step; the merchant sees
the original evidence and the later verification outcome in one timeline.

1. Implement P4a and P3 exactly once. Reuse their merchant harness, attempt/event
   tables, authentication, retention and durable idempotency. There is no second
   `/recovery` backend and no new way to modify a signed CHALLENGE.
2. In `demo/merchant_pilot/static/index.html` (proposed), distinguish merchant and
   subscriber steps: why the order is held, required action, expiry, status and
   return path. Default to a merchant-owned manual review; render OTP/passkey
   methods only after an actual integration exists.
3. Make the merchant timeline read: network CHALLENGE → attempt pending →
   merchant-reported result → separate order decision. A reported pass neither
   changes the network verdict to ALLOW nor proves legitimacy or fulfillment.
   Order/fulfillment state belongs exclusively to the merchant harness, not a new
   Isnad case API; Isnad owns its existing verdict/consent/session and P3/P5 contracts.
4. Before backend completion, a judge may view an explicitly labelled synthetic
   storyboard. Do not show a working “customer verified” button that fabricates
   completion on a production flow. Consent denial, expired attempts and abandoned
   merchant-reported reviews need usable outcomes too.
5. Exercise P3's race/restart/expiry tests and a full browser flow including refresh,
   retry, denial and unauthorized reporting. Snapshot original signature bytes
   before and after every terminal state.

**Accept:** a human can finish the merchant workflow, while the signed network
decision and later merchant claims remain distinct. Full persistence is still
post-submission unless H0 makes it essential and P4a/P3 are genuinely complete.

### I6 — Arabic-first clarity, English parity and accessible receipts

**Moment:** switch languages during a result without changing its meaning or proof.

1. Reuse `app/presentation.py`, `app/static/judge.html` and `receipt.html`.
   Add proposed `app/static/i18n/en.json` and `ar.json` dictionaries keyed by
   decision, grade, normalized signal and UI control. Translate templates and
   recorded numeric placeholders, not signed bytes or arbitrary provider prose.
   These pages have no generic static mount: add one explicit same-origin
   `/ui/i18n/{locale}.json` read route restricted to `en`/`ar`, or inject dictionaries
   safely at page rendering. Do not interpolate arbitrary paths. Locale is UI-only
   and must not enter verification request commitments or policy decisions.
2. Set `lang` and `dir` on the page; use CSS logical properties and `bdi`/LTR
   isolation for chain IDs, API names, timestamps and numeric fields. Persist only
   locale preference. Unknown translation keys fall back visibly to English.
3. Have an Arabic reader review CHALLENGE versus DECLINE, consent versus fraud,
   and the difference between query window and actual event age. Mark translation
   review pending until performed; automatic translation is a draft, not validation.
4. Fix P2's 375 px receipt-table overflow with an accessible scroll region or
   stacked cards. Verify keyboard focus/activation, status announcements, text
   zoom, contrast and reduced-motion behavior. Never encode the verdict only in color.
5. Test language switching before/during/after a run, long Arabic text, mixed
   numerals, all decisions/grades, missing data and receipt verification. Preserve
   USD synthetic inputs until I11's explicit currency contract exists.

**Accept:** both languages give the same action and evidence, every key has a
fallback, and neither a small screen nor keyboard use hides receipt controls.
No claim that Arabic support is itself an official judging criterion.

### I7 — Portable receipt verification and privacy explanation

**Moment:** download a receipt, disconnect from Isnad, verify it, alter one byte,
and observe failure. Online QR verification and tamper controls already exist.

1. Extend `app/api/routes_receipt.py`/`receipt.html` with a download of the
   existing eligible public record: schema version, **exact stored signed-payload
   string**, signature, public key and algorithm. Never reconstruct signed JSON
   from display fields or imply that hiding a field removes it from the payload.
   Verify the stored `signed_payload.encode("utf-8")`; do not parse and reserialize it.
2. Add `scripts/verify_receipt.py` (proposed) using the existing Ed25519 library
   for offline verification. Accept an independently supplied expected key or
   trusted-key file; separate valid signature from known issuer. A key included
   in the bundle alone cannot establish who issued it.
3. Optional browser import can reuse the existing WebCrypto verification logic
   with a bounded file size and strict fields. A locally served offline page is
   acceptable; report unsupported crypto/context instead of a green result.
   No CDN or server request is necessary after the verifier/bundle are obtained.
4. Explain what is stored versus omitted from the actual payload. Subject/owner
   commitments are pseudonymous and potentially linkable, not anonymous. An
   offline receipt proves past issuance/integrity; current session status,
   current key trust and provider truth require separate evidence. Don't promise
   that a downloaded receipt can be revoked or erased remotely.
5. Test valid/tampered payload, wrong/untrusted key, malformed/oversized bundle,
   legacy signed fields and exact UTF-8 bytes across download/import. Audit exports
   for raw identifiers and secrets; use synthetic receipts for public demonstrations.

**Accept:** independent verification works with an external trust anchor and
honest offline limitations. Redaction or selective disclosure would require a
separately designed proof scheme; never claim existing Ed25519 provides it.

### I8 — Trust continuity connected to a merchant action

**Moment:** after a clean checkout, a simulated SIM/device change puts an
unfulfilled order back on hold while the original receipt stays intact.

1. Reuse `app/session/manager.py`, `app/api/routes_session.py` and the existing
   clean-case continuity drill. Document current polling, TTL/quota limits and
   process-local state. Do not present this as operator push notifications or as
   new functionality already missing from Isnad.
2. Extend I11's merchant order mapping to retain an owned session ID and explicit
   fulfillment state. Only a valid current session may authorize the demo's
   sensitive follow-up action. Display ACTIVE, REVOKED, EXPIRED, ENDED and unknown
   distinctly; an unavailable lookup is not permission to proceed.
   Current session APIs bind only phone/owner, not an order: the harness must
   privately bind `(order_id, chain_id, request_hash, session_id)` to the same
   immutable checkout and subject. Reject a caller-supplied unrelated ACTIVE session.
3. Add a proposed server-side “release demo order” action in the harness. Check
   order ownership and session state there, not solely in JavaScript. A revocation
   holds future fulfillment; it cannot undo a shipment/payment already completed.
   For the in-process simulator, synchronize revocation and release under the same
   state guard. If revocation wins, release must fail. A process-local lock cannot
   guarantee ordering across a separate remote merchant and Isnad service; do not
   advertise atomic real-commerce enforcement based on a last-moment HTTP lookup.
4. Show observation time, monitoring expiry and current state beside the historical
   network receipt. A new decision, if needed, requires fresh verification. Real
   commerce enforcement needs transactional handling of the check/action race and
   durable event delivery; keep the first version explicitly a simulator.
5. Test expiry, provider failure, changed signal, repeated revocation, restart,
   concurrent release and attempted cross-owner use. Preserve billable polling
   floors and caps. Session loss after restart must lead to explicit unknown/hold,
   not a fresh ACTIVE session inferred from the old receipt.

**Accept:** the simulator shows a concrete merchant consequence. Production
integration is not claimed until state persistence and action-race semantics are
implemented; historical ALLOW does not grant indefinite authorization.

### I9 — Judge-controlled scenario challenge

**Moment:** the judge chooses the case, rather than watching only a favorable path.

1. Build on I2/I4's bounded fixture runner. Add named cases for legitimate SIM
   replacement, clean checkout, two adverse signals, absent location claim and
   provider outage. Keep a versioned authored challenge set separate from the lead
   demo and publish its limitations; do not call authored data independent ground truth.
2. Offer fixed case buttons or a seeded shuffle of that set. Inputs must not select
   live phone numbers, raw provider responses, thresholds or free-text model tasks.
   Show scenario assumptions before running so the surprise is not a hidden policy change.
3. Show selected check path, actual result, required-check behavior and comparison
   with the authored expectation. Preserve disagreements. A case not used in the
   lead recording is not automatically a statistically held-out test.
4. Supply a replay artifact for each case and clear reset behavior. Enforce one
   active render per viewer, bounded history and accessible controls; reset must
   not clear another viewer's state or mutate global mock fixtures.
5. Test that every allowed selection resolves, rejected IDs cause no work, seeded
   order reproduces, and aggregate counts equal I3's underlying rows. Record a
   run through the least favorable case, not only the best result.

**Accept:** judges can challenge the demonstration while the input surface stays
bounded, accurately labelled and reproducible. Execute only the shared injected
mock/fault runner, never arbitrary `/v1/verify` inputs. Add this after I2 or I4 works.

### I10 — Provider capability and consent readiness

**Moment:** the merchant sees what is ready, what is simulated and what still
needs consent or operator setup before attempting a real verification.

1. Extend H2's evidence inventory with a proposed versioned
   `docs/nac/capabilities.json`: action, adapter/SDK version, environment scope,
   status (`verified`, `unverified`, `unavailable`), checked time, source reference,
   consent requirement and coverage caveat. Public exports contain no subscribers,
   credentials or private endpoint configuration.
   Allowlist public source references; readiness metadata stays outside evidence
   links, verdicts, planner candidates and `provider_sources`.
2. Add a read-only readiness view to the authenticated P4a harness. Keep static
   configuration, historical test success and current per-request result separate.
   A green past test is not an uptime probe, entitlement guarantee or nationwide
   operator coverage claim. Do not infer supported operator from a phone prefix.
3. Define local preflight validation for missing claim, invalid input and absent
   consent configuration without contacting a provider. Let the actual adapter
   report current availability. Keep unknowns explicit rather than faking a
   successful readiness result to unblock the user.
4. Record required setup next to each blocked capability with H2/P4 links. Capability
   discovery itself may be billable; no automatic phone probes or polling. Operator
   review/import is sufficient for the first version.
5. Test missing/stale manifest, contradictory sources, simulated versus physical
   scope, absent consent and missing location claim. Preserve P1's zero-SDK-call
   missing-claim guarantee and normal provider error handling.

**Accept:** the UI prevents misleading readiness claims and makes a live pilot
easier to configure. It is supporting integration evidence, not a new trust signal
or a substitute for P4b's physical handset test.

### I11 — Reference merchant integration and location-claim capture

**Moment:** an actual order in the reference shop receives a useful action and
traceable receipt without the merchant learning individual telecom APIs.

1. Extend P4a's harness as the first reference shop; avoid a second app or an
   untested Shopify/WooCommerce plugin before submission. Add a documented
   server-side adapter for existing verify/consent/status APIs, timeouts and
   idempotency. Keep merchant/provider keys out of browser bundles and logs.
2. Store a scoped merchant-side mapping of internal order ID to immutable request,
   consent/chain/attempt IDs and fulfillment state. Do not put raw order IDs in
   public receipts. Retry with the same idempotency key and immutable body;
   changed order context starts an explicit new verification version.
3. Resolve the P1/P2 claim gap with an explicit claimed checkout area. For the
   reference pilot allow operator-supplied validated coordinates/radius, or omit
   the optional claim and show that location cannot be verified. Label this a
   customer/merchant claim, never an observed phone location. Automatic address
   geocoding is later work with a reviewed service contract and error handling.
   Raw claims stay private inputs with bounded P4a request retention: no coordinates
   in prompts, receipts, event logs, screenshots or public trace/export artifacts.
4. Preserve current demo currency. Before accepting multiple currencies, define
   per-currency policy thresholds or an explicit sourced conversion policy, reject
   unsupported currencies, and test amount boundaries. Never compare arbitrary
   raw JOD/SAR values to a USD threshold or merely change the currency label.
   Enforce the supported-currency guard in the adapter before calling Isnad; its
   current general Money model accepts any three-character code.
5. Connect P2's action, P3's merchant-reported challenge result and P5's separate
   order outcome. Test clean/challenged/declined/expired flows, API outage, duplicate
   checkout, changed body, reload and foreign order access. Provide a minimal
   reproducible integration example with synthetic requests and no inline secrets.

**Accept:** a merchant can integrate one workflow end to end, including unavailable
evidence. Conversion uplift, saved revenue and retailer adoption remain unproven
until real data/feedback supports them.

### I12 — Outcome learning and safe policy comparison

**Moment:** the merchant can see where review worked, which outcomes remain unknown,
and what a proposed policy would change before enabling it.

1. Complete P5's append-only outcome contract first. Build an owner-scoped report
   from merchant-reported order/fraud dimensions and P3 challenge events. Exclude
   demo runs; show missing/unknown labels and observation windows. Do not infer
   fraud from cancellation or legitimacy from challenge completion.
2. Add review metrics: challenge completion/time, merchant-reported abandonment,
   manually accepted orders and per-case evidence usage. Each metric carries its
   definition, denominator, time basis and missing count. Until real labels exist,
   present an authored example report clearly marked synthetic.
3. A business-impact worksheet may accept merchant-entered review cost and margin
   assumptions with explicit currency and source. Calculate scenario ranges as
   assumptions, not actual recovered revenue. Keep missing prices null and costs
   separate from full order value; don't equate avoiding a hold with making a sale.
   These inputs are report-only and must never modify the policy, provider calls
   or any past or new merchant verdict.
4. Post-submission, add offline shadow-policy comparison using I3's fully captured
   fixtures first. Real early-stopped receipts lack unrequested evidence and may
   lack full original context/policy: mark them insufficient for full replay instead
   of inventing answers or querying phones retroactively. Do not automatically
   deploy weights, recalibrate scores or update old signed decisions.
5. Require prospective data collection design, a defined holdout, label-quality
   review and documented tradeoffs before a real calibration proposal. Test late
   labels, corrections, unknowns, zero denominators, selection bias disclosures,
   ownership, retention and policy changes that perform worse on some cases.

**Accept:** the product exposes what is known and what still needs validation.
Any later model/policy release is a separate reviewed change with a version and
rollback plan, not self-learning silently applied to merchant decisions.

### I13 — Expiring reviewer links with explicit disclosure scope

**Moment:** a merchant issues a limited reviewer link and later disables future
access through it. This does not revoke the already public original receipt or
erase downloaded evidence; the UI must state that distinction.

1. Proposed files: `app/db/proof_shares.py`, `app/api/routes_proof_shares.py`,
   `app/static/proof.html`, `tests/test_proof_shares.py`, a new migration and
   retention/privacy-posture updates. Reuse P3's owner and idempotency conventions.
   Store random share ID, keyed bearer-token digest, chain ID, owner, purpose,
   scope and server issue/expiry/revocation times. Purpose is a display label,
   not proof of the viewer's identity; real audience restriction needs viewer auth.
2. Propose owner-authenticated `POST /v1/chains/{chain_id}/proof-shares` and
   `DELETE /v1/chains/{chain_id}/proof-shares/{share_id}`, plus a bounded read-only
   `/p/{token}` route. Use a cryptographically random token, no-store/no-referrer
   responses, rate limits and access-log redaction. Never embed tokens in analytics.
   For creation retries, retain the response only encrypted under a separate
   server key for the documented idempotency TTL; do not persist plaintext tokens.
3. Start with one summary scope: a **separately issued attestation** containing
   decision, grade, source payload digest, issuance/expiry, issuer key and signature.
   Domain-separate its format/type from `Verdict`; keep its record insert-only.
   It is not a selectively redacted original signature, zero-knowledge proof or
   cryptographic proof that omitted source facts were true. Do not include the
   original chain URL/ID when the summary does not need to reveal it.
4. Evaluate expiry/revocation on every server access; return the same unavailable
   response for missing, expired and revoked shares. Leave original `/r/` semantics
   and original bytes unchanged. A downloaded summary can still verify after link
   expiry; show signature integrity separately from current access/validity state.
5. Test owner isolation, concurrent/repeated creation and revocation, key trust,
   token/log leaks, expiry boundaries and the absence of full payload, raw subject,
   merchant, session and challenge/outcome data. Verify both original and summary
   signatures independently. Include encrypted-response/key retention in operations.

**Accept:** disclosure and access limits are accurately described and enforceable
on the new route. Do not advertise anonymous credentials, revocable downloaded
receipts or restricted access to an already shared original receipt.

### I14 — Durable trace recovery after a disconnect

**Moment:** disconnect during an investigation, reconnect, and recover missing
evidence events and the same persisted receipt without buying the checks again.

1. Extend I1 with proposed `app/db/run_events.py`, `RunEventRow` in
   `app/db/models.py`, a migration and `tests/test_run_replay.py`. Store owner,
   run ID, event ID, per-run sequence, event type, allowlisted structured body and
   server time. Enforce unique `(owner, run_id, sequence)` transactionally.
   Exclude raw numbers, prompts, tokens and unrestricted model/provider prose.
2. Persist an event before fan-out from `app/events.py`; define explicit behavior
   if persistence fails. Do not claim a complete replay when events could not be
   stored. Final completion must reference an already persisted chain. If database
   event and chain writes cannot be atomic, implement reconciliation/outbox logic
   and test a crash between them before advertising durable completion.
3. Extend the authenticated console stream with an optional owned `run_id` and
   replay cursor (`Last-Event-ID` or validated `after`). Authorize the run before
   reading journal rows; a run-ID filter alone is not access control. Bound replay
   page size and retained events. Use a watermark/buffer handoff to live fan-out
   so events created during replay are neither silently skipped nor reordered.
4. Deliver at least once; the UI deduplicates by run/sequence and renders in order.
   A retention gap returns an explicit gap/reset signal and fetches the final
   persisted result if available. Do not reconstruct absent events or rerun the
   investigation. Preserve existing cursorless live clients and P2's final-result guard.
5. Test disconnect/reconnect, duplicate/out-of-order delivery, concurrent runs,
   replay-to-live races, server restart, persistence failure, retention gaps and
   foreign cursors. Apply bounded positive retention settings and privacy disclosures.
   Journal recovery cannot resume an interrupted billable investigation by itself;
   report an interrupted run separately from a completed one.

**Accept:** retained events can be recovered without duplicate UI effects or new
provider calls. Do not claim exactly-once network delivery or multi-replica task
recovery merely because events are now persisted.

### Agent execution and release checklist

1. Pick the earliest unblocked item in the shortlist; name the exact deliverable
   in the session intent. Read its P/H dependencies and source files. Record any
   contract deviation before changing shared schemas. One writer owns each file.
2. Implement the smallest complete vertical slice: fixture/data contract → pure
   computation/backend → UI → exported evidence. For larger items commit-sized
   local checkpoints are useful, but neither this plan nor a feature completion
   authorizes pushing, deployment, outreach or submission.
3. Run the item's meaningful negative-path tests and §5's suite/Ruff for code
   changes; perform the specified browser checks for UI work. Keep an original
   signed receipt as a compatibility fixture. Do not report tests run by another
   session as tests performed in this one.
4. Change status only with evidence: implementation revision, exact validation
   command/result, browser evidence where required, artifact path and limitations.
   `PARTIAL` means remaining steps are listed. Merely adding this plan or using a
   fake provider does not complete an implementation or prove a live integration.
5. Refresh the graph and reconcile README, walkthrough, recording and H0 manifest.
   Public claims describe only implemented/validated behavior. Freeze at H5's
   agreed cutoff; defer unstable features and preserve the last working demo.

**Suggested demonstration sequence, adapted to the verified submission limit:**
regional order problem → I1 actual AI selection → P2 merchant action → I3 honest
comparison → one I2/I4 judge-selected variation → I7 receipt verification.
Use I5 recovery or I8 continuity as a follow-up only if that slice works. Maintain
an accurately labelled recording of the same version for connectivity failures.

## 8. Latest session

**Intent — competition feature planning, 6 Sep:** turn all competitive lessons
and product suggestions into buildable plans, preserving P1–P5 and H0–H5.

**Completion — documentation only:** added fourteen I-items in §7 with ordered
steps, integration points, contracts, dependencies, acceptance evidence and a
small submission shortlist. Two lighter-model reviewers checked the plans
against the code; their corrections are incorporated. No proposed feature is
marked implemented, and no application behavior, policy or signed schema changed.
The earlier §6 research remains the source for event facts and unknowns.

**Preserved implementation evidence:** [full P1/P2 session records](P1_P2_IMPLEMENTATION_RECORDS.md)
are archived verbatim rather than repeated in this active plan. P1 is COMPLETE
(516 tests reported); P2 is PARTIAL (541 tests reported, Ruff clean, described
browser checks). These are previous implementation results, not tests rerun here.
P2 still needs actual keyboard traversal verification and the 375 px receipt table
fix; P4a/I11 own the unresolved real merchant location-claim input contract.

**Validation for this pass:** pending final documentation and graph checks.
No model/provider trial, outreach, deployment, commit or push performed.

**P4a implementation — 6 Sep (concurrent follow-up session):** built the
local live-consent journey and current OAuth contract per §3 P4a — fixed
five pre-existing consent-store defects (each with a failing test confirmed
against the pre-fix code first), added shared id_token/JWKS validation
(`app/oidc.py`, `app/providers/oidc_flow.py`) used by both `NacProvider`'s
manual exchange path and a new offline fake operator
(`demo/fake_operator`, `ISNAD_PROVIDER=nac_fake`), added the browser-preferring
callback redirect to a generic `/consent/complete` page, and built the
single-merchant reference harness (`demo/merchant_pilot`). Actually ran all
three as local processes and drove them through a real browser (not a
background agent) for ALLOW, CHALLENGE and denial outcomes, which surfaced
and fixed one real defect (an unhandled transient-outage error) that no unit
test had caught. Full suite 541 → 596 passed, Ruff clean, `scripts/
handset_validation.py contract` still passes. Status: **DONE LOCALLY**; P4b
(a real handset/operator) is untouched, as instructed. Full record:
[P4A_IMPLEMENTATION_RECORD.md](P4A_IMPLEMENTATION_RECORD.md).

**P3 implementation — 6 Sep (same day, follow-up session):** built merchant
CHALLENGE followup and completion reporting per §3 P3. Made `store.save`
insert-only first (it was silently upsertable — a confirmed, then fixed,
defect unrelated to P3's own scope but load-bearing for it). Added
`ChallengeAttemptRow`/`ChallengeEventRow` in their own tables (never a column
on `ChainRow`), migration `0002_challenge_followups`, and three endpoints
under `/v1/chains/{chain_id}/challenges` with merchant auth, ownership
scoping and compare-and-swap transitions (PENDING → PASSED/FAILED/ABANDONED/
EXPIRED). Idempotency is durable (a new `IdempotencyRecordRow`, not the
in-memory cache `/v1/verify` uses), keyed by owner+operation+key and a
fingerprint binding the full target and body, so a reused key against a
different chain, attempt or body is a 409. Extended the P4a merchant-pilot
harness with a "Continue merchant verification" panel, then ran all three
processes again and drove a real CHALLENGE (NUMBER_MISMATCH) through to a
reported FAILED result in a real browser, confirming by direct `curl` that
the public receipt's signed payload is untouched by the followup. Full suite
623 → 627 passed, Ruff clean, `scripts/handset_validation.py contract` still
passes. Status: **DONE LOCALLY**. Full record:
[P3_IMPLEMENTATION_RECORD.md](P3_IMPLEMENTATION_RECORD.md).

**P5 implementation — 6 Sep (same day, follow-up session):** built merchant
outcome reporting (order status, fraud assessment) per §3 P5. Challenge
execution, the third dimension the handoff names, is deliberately not
reported through this API at all — it is read fresh from P3's own attempt/
event tables whenever a report is assembled, so there is exactly one place
that fact can come from. No decision gate, unlike P3: an outcome may be
reported on any owned chain, including ALLOW/DECLINE. Exactly one current
event per (owner, chain, dimension) is enforced by a partial unique index
(`superseded_by IS NULL`), not just a read-then-write check; a correction
must name the current head or the write is a 409, and two concurrent first
reports on the same dimension resolve the same way via the same index.
`FraudAssessmentReport`'s schema itself (a Pydantic discriminated union with
`extra="forbid"`) requires a basis for CONFIRMED_FRAUD/CONFIRMED_LEGITIMATE
and forbids one otherwise, so a weak signal can never carry a confirmed
label. New migration `0003_outcomes`; new owner-scoped offline report
(`scripts/merchant_outcome_report.py`) excludes synthetic (mock/nac_fake)
runs and separates missing from explicit UNKNOWN per dimension. Extended the
merchant-pilot harness with order-status/fraud-assessment reporting, ran all
three processes again continuing the exact CHALLENGE chain P3's own pass
proved, and found (and fixed) a real live-only defect: the fraud-assessment
basis field's visibility only reacted to a `change` event a default
selection never fires. Confirmed by direct `curl` that the public receipt
remains untouched, and that the offline report correctly excludes the
`nac_fake` chain used for the browser pass itself. Full suite 627 → 659
passed, Ruff clean. Status: **DONE LOCALLY**. Full record:
[P5_IMPLEMENTATION_RECORD.md](P5_IMPLEMENTATION_RECORD.md).
