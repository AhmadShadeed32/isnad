# Isnad — compact handoff

Updated 6 September 2026. **Read this file first.** It replaces the long running
log with current facts and an implementation plan. Read §6 first for the hackathon deadline; use the ledger in §3 for product work. The complete earlier log is preserved
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
- P2 (6 Sep, see §7) added a plain-language presenter (`app/presentation.py`)
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
| P1 | Honest location fixtures and provider preconditions | Baseline checks | COMPLETE (implementation record in §7) |
| P2 | Plain-language merchant result and focused demo entry | P1 | PARTIAL (6 Sep implementation session; see §7) |
| P4a | Local live-consent journey and current OAuth contract | P1, P2 | NOT STARTED |
| P3 | Merchant challenge attempt and completion reporting | P2; reuse P4a harness | NOT STARTED |
| P5 | Merchant outcome collection and evaluation report | P3 event/ownership conventions | NOT STARTED |
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

## 7. Latest session

**Intent — 6 Sep:** compare Isnad with the MENA Ignite event's public materials
and add a competition-specific delivery plan. Preserve P1–P5 as the product
roadmap, distinguish verified event facts from recommendations, and avoid
inventing unavailable rubric weights or submission requirements.

**Completion — documentation only:** added §6 with verified source links, an
explicit unknown-rubric warning, the 11/13 September deadline discrepancy and
H0–H5 submission work. It prioritizes honest AI-planner proof, NaC provenance,
one regional buyer, reproducible comparisons and remotely accessible artifacts;
full P3/P5 work is deferred for the submission. Preserved the detailed product
plan and refreshed its entry point. Links/anchors and diff whitespace checked;
Graphify refreshed. No product code, model/provider run, outreach, upload,
deployment, commit or push was performed by this research pass. Concurrent
implementation work was left intact; its committed P1 record is preserved below.

### Preserved P1 implementation record

The following record is preserved from the implementation agent's committed
handoff; this research pass did not rerun its tests.

**P1 implementation — 5 Sep (same day, follow-up session):** Fixed the
location-evidence provider boundary per §3 P1.

*Defect confirmed before the fix.* Added `tests/test_provider_preconditions.py`
first and ran it against the unfixed code: `NacProvider` already returned
INFO/`EVIDENCE_UNAVAILABLE` with no claim and never called the live SDK (it was
already correct, just used a hand-written detail string); `MockProvider`
returned its scripted match/mismatch fixture regardless of
`request.context.claimed_location`, confirmed failing for the intended reason
(`assert link.result == Result.INFO` saw `PASS`/`FLAG`).

*Fix.* `app/providers/mock.py`: `MockProvider.gather` now checks
`action == LOCATION_VERIFY and claimed_location is None` before fixture
selection and returns INFO/`EVIDENCE_UNAVAILABLE` (normal `EvidenceLink`
wrapper, provenance and accounting intact). `app/providers/nac.py`: aligned its
existing no-claim branch to `detail_for("EVIDENCE_UNAVAILABLE")` instead of a
one-off string, for parity with the mock. `RequestContext.claimed_location`
stayed optional; no schema, policy weight or threshold changed.

*Claim added at request-construction sites whose story assumes one* (a
synthetic `Area(lat=31.9539, lon=35.9106, radius_m=2000)`, never persisted into
`EvidenceLink`/receipts/logs — confirmed by grepping the signed verdict JSON):
`app/api/routes_console.py` (`DEMO_ACTS["act2"]`, `["act6"]`),
`demo/run_acts.py` (Act II), `tests/scenarios/test_acts.py` (Act II),
`tests/test_chain_grade.py` (`_ACT6`, both Act-II-shaped tests, the
`/v1/verify` HTTP body test), `tests/test_parallel_gather.py` (the interleaving
test's per-scenario request), `scripts/false_decline_baseline.py` (`CONTEXT`,
since its CLEAN/ADVERSE population scripts location signals), and all 13 cases
in `tests/fixtures/independent_evaluation.json` (every case scripts a
`location_verify` entry). Act I, Act V and the Act-VIII/Reverse-Isnad fixtures
were deliberately left without a claim — their stories never assumed one.
`scripts/evidence_pack.py` and `scripts/planner_divergence.py` import
`DEMO_ACTS` directly and needed no edits; `evidence_pack.py` was run and its
output (below) confirms they still work.

*Metrics reverified, not assumed* (isolated `ISNAD_PROVIDER=mock`,
`ISNAD_PLANNER=greedy`, matching `tests/conftest.py` — a developer `.env` in
this repo sets `ISNAD_PLANNER=llm`/`ISNAD_PROVIDER=hybrid`, which will silently
change ad hoc verification if not overridden):
- Act VI: CHALLENGE / DEGRADED, confidence 0.242, 6 steps — unchanged, matches
  the doc and README.
- Act III: ALLOW / ATTESTED_FULL, confidence 0.096, 2 steps — unchanged.
  (Act III never reaches `location_verify`: it clears on `number_verify` +
  `sim_swap` alone, so it needed no claim.)
- Act II: DECLINE / REFUTED, confidence 0.981, 4 steps
  (`NUMBER_MATCH, SIM_SWAPPED, DEVICE_SWAPPED, NOT_AT_CLAIMED_LOCATION`) — an
  adverse/decline demonstration, as required, once given its intended claim.
- **Act V moved and this is expected, not a regression:** confidence
  0.105 → 0.28, steps unchanged at 4. Decision (CHALLENGE) and chain_grade
  (UNRESOLVED) are unchanged. Before the fix, Act V's `location_verify` step
  silently returned the fabricated `AT_CLAIMED_LOCATION` (delta −1.2) despite
  Act V's story ("the gap: consent withheld and a provider that cannot
  answer") never supplying a claim — the same bug this package exists to fix,
  just not the instance the task named. After the fix it honestly reports
  `EVIDENCE_UNAVAILABLE`, so the chain now shows two unresolved checks
  (`device_swap`, `location_verify`) instead of one, and the resulting score
  is higher. No claim was added for Act V — its story is exactly the
  intentional-missing-input case the audit was supposed to leave alone.
- `scripts/false_decline_baseline.py` (no `--sweep`): 58 vs 119 calls, 0/10
  false declines, 1/7 corroborated-adverse allowed — identical to the figures
  already recorded in §1. `--sweep`: 0.15→58, 0.10→59, 0.05→82, 0.02→87 calls,
  also identical to §1's "threshold 0.05 buys 82 calls and allows 0/7."
  Unaffected because the fix only changes behavior when no claim is present,
  and this script's `CONTEXT` now carries one.
- `scripts/independent_evaluation.py`: unit tests unaffected; running it live
  now gives `isnad-greedy` fidelity to the fixture's scripted `location_verify`
  answers that it did not reliably have before (13 cases previously risked
  silently downgrading to `EVIDENCE_UNAVAILABLE` mid-run for any case relying
  on a location signal). No test pins its exact per-case decisions, only totals
  and that a named disagreement appears, both of which still hold.

*Signed-receipt compatibility.* Saved a receipt under the pre-fix
`app/providers/mock.py`/`nac.py` (via `git stash` of just those two files, an
isolated sqlite DB and vault key, `ISNAD_PROVIDER=mock`), captured its exact
`verdict_json`, `signature` and `public_key`, restored the fix, and verified:
`vault.verify_with(public_key, verdict_json, signature)` returns `True`. The
fix touches only provider evidence-gathering, never `Verdict`/`EvidenceLink`
shape or the signing path, so this was expected and confirmed.

*Test/lint evidence.* New `tests/test_provider_preconditions.py` (10 tests:
both providers × {no claim, match, mismatch, provider failure} — Mock's
"failure" analogue is a scripted unavailable/unknown result WITH a claim
present, since Mock itself never raises, and this pins that the precondition
only fires when the claim is absent, never masking a scripted failure when a
claim exists — plus a Mock-other-actions-unaffected check). Full suite:
506 → 516 passed. Ruff (`app tests scripts demo`): clean. README's example
curl body and score explanation updated from these same verified outputs; the
"fixture gap" caveat paragraph removed now that the regression passes and both
providers agree.

*Known gaps for P2:* no browser/UI click-through of `/console` or `/judge` was
done in this pass — P1's own "Required evidence" list doesn't call for one
(only P2 touches the presenter/rendering surface), and `test_console.py`/
`test_judge.py` continue to pass unmodified. P2 should also decide how (or
whether) a real merchant integration is expected to supply `claimed_location`
in practice, since today it is an optional, silently-skippable field with no
UI affordance to collect it outside the two demo acts wired above.

*Files changed:* `app/providers/mock.py`, `app/providers/nac.py`,
`app/api/routes_console.py`, `demo/run_acts.py`,
`scripts/false_decline_baseline.py`,
`tests/fixtures/independent_evaluation.json`, `tests/scenarios/test_acts.py`,
`tests/test_chain_grade.py`, `tests/test_parallel_gather.py`,
`tests/test_provider_preconditions.py` (new), `README.md`, this file, and the
Graphify outputs.

### P2 implementation — 6 Sep (follow-up session)

Built the plain-language merchant presenter and focused demo entry per §3 P2.
Status: **PARTIAL** — every numbered step below has concrete evidence, but two
items are flagged as known gaps rather than claimed complete (keyboard-Tab
traversal, and a pre-existing receipt-table overflow at 375 px). Never claim
COMPLETE on a happy-path screenshot; see the checklist this ledger asks for.

*What changed.* New `app/presentation.py`: a pure function
`present(verdict: Verdict) -> Presentation` with no I/O, no LLM call, and no
import of `app.config`/`app.policy` (so it can never compare an old chain
against today's live policy — only against whatever `policy_snapshot` that
chain itself carries, or nothing for a chain signed before that field
existed). It maps ALLOW/CHALLENGE/DECLINE to "Proceed" / "Additional
verification needed" / "Do not proceed", derives supporting/adverse/unresolved
facts as `f"{link.api}: {link.detail}"` for actual chain links only (capped at
`MAX_FACTS = 5` each), and writes two genuinely different CHALLENGE summaries:
the DEGRADED case (Act VI-shaped: every check resolved, one came back adverse,
score lands between thresholds) explicitly says this is not a failed identity
check or withheld consent; the UNRESOLVED case (Act V-shaped) names each
specific unavailable check by API label, and when neither an unresolved
signal nor any link is present to blame, the summary says only that
corroboration was insufficient rather than guessing at a cause. Every
`next_action` for CHALLENGE states plainly that Isnad has not sent a one-time
code, per the done bar.

`presentation: Presentation | None = None` was added to `VerificationResponse`
only (never to the signed `Verdict`/`EvidenceLink`) and wired into four
callers of the same `present()`: `routes_verify.verify`, `routes_verify.get_chain`
(recomputed fresh from the immutable stored Verdict every read — safe, since
`present()` never touches the live engine), `routes_consent._verification_response`,
and the SSE `"verdict"` event emitted from inside
`app/agent/investigator.py` (the only place that event is built — this was
the one line touching that file, adding the field to the emitted dict, not
altering any decision/budget/planner logic). `app/api/routes_console.py`'s
`console_run` endpoint (the judge page's fixture path) also got the same field
in its HTTP response, as a resilience fallback for when a stream drops before
the first byte.

`app/static/judge.html`: outcome now renders action (plain title) → explanation
(summary, supporting/adverse/unresolved fact lists, next action) → a collapsed
`<details>` "Technical and audit details" panel (raw enum, reason, chain grade)
last, in that order. Added a third fixed control, "Show an unresolved-evidence
case," wired to the existing `/v1/console/run/act5` fixture (demo-gated, no new
provider surface) so Act V's UNRESOLVED shape has a UI path, not just an API
one. Fixed a real bug found while wiring this: the SSE `'verdict'` event fires
*before* the caller (`routes_console.py`) calls `store.save_async`, so the
receipt link/button used to appear before a receipt necessarily existed.
`renderVerdict(data, {persisted})` now only reveals the receipt once the
*HTTP response* (which is only returned after persistence) confirms it, and a
`completedRunId` guard drops a duplicate/late SSE verdict for an
already-persisted run rather than re-rendering over it. Grade line now reads
"demo duration NNN ms (paced ~650 ms per check for readability, not a latency
measurement)". `app/static/receipt.html` got one small addition outside the
originally listed file set: a same-origin "← Back to the checkout demo" link
to `/judge`, since there was previously no way back from a receipt except the
browser back button.

`app/main.py`: `/` now redirects to `/judge` only when `settings.demo_mode` is
true (read at request time, so a monkeypatched test sees the change); the
non-demo route (`/console`) and its existing credential gating are unchanged.
`app/agent/explain.py`: the LLM system prompt now says "uncalibrated policy
score" instead of "the probability"; the `chain_facts()` JSON key stayed
`p_fraud` because `tests/test_t4_ask_the_agent.py` asserts that key directly
and only the prompt vocabulary was in scope.

*Deviations from the listed file set, justified here per this doc's own
"record any justified change to these contracts" rule:* `app/api/routes_console.py`
(added `presentation` to `console_run`'s response — SSE-drop resilience),
`app/static/receipt.html` (back link — step 8 explicitly requires checking
"a clear way to return from the receipt view," which did not exist before),
and the new Act V button in `judge.html` (needed so step 8's
"provider-unavailable outcome" browser check has a UI path at all, not only
`/v1/console/run/act5` called directly).

*Test/lint evidence.* New `tests/test_presentation.py` (25 tests): real
synthetic Verdicts run through `build_investigator(MockProvider())` over the
console's own `DEMO_ACTS` (act2 → DECLINE/REFUTED, act3 → ALLOW/ATTESTED_FULL,
act5 → CHALLENGE/UNRESOLVED, act6 → CHALLENGE/DEGRADED) plus hand-built
`Verdict`s for combinations the fixed acts do not produce (an ungraded legacy
chain, a chain with no `policy_snapshot`, DECLINE paired with UNRESOLVED —
`grade()` checks `unresolved` before `decline_above`, so that combination is
real and must not claim "directly contradicted"). Assertions include: every
displayed fact traces to an actual chain link (no invented facts); the two
CHALLENGE cases produce different summaries; no temporal phrase ("days ago",
"recently") is ever produced from a bounded window; `"presentation"` never
appears in `Verdict.model_fields` or in `verdict.model_dump_json()`
(byte-for-byte: the signed model was never touched); an HTTP `/v1/verify` call
and its concurrently-subscribed SSE `"verdict"` event carry identical
`presentation` dicts for the same run; a `VerificationResponse` built from a
dict missing `presentation` still validates with the field defaulting to
`None`. Full suite: **516 → 541 passed** (`.venv311/bin/python -m pytest -q`).
Ruff (`app tests scripts demo`): clean. `scripts/evidence_pack.py` reproduced
unchanged: Act VI CHALLENGE/DEGRADED/6 steps/0.242, Act III ALLOW/ATTESTED_FULL/
2 steps/0.096, Act V CHALLENGE/UNRESOLVED/4 steps, Act II DECLINE/REFUTED/4
steps, all signatures valid — none of P2's changes touch provider/policy
behavior.

*Browser evidence, actually performed (not assumed).* Ran the app locally with
`ISNAD_PROVIDER=mock ISNAD_PLANNER=greedy ISNAD_DEMO_MODE=true` (the repo
`.env`'s `llm`/`hybrid` would have silently mislabeled the mode pill and run
the wrong planner). Confirmed: `/` redirects to `/judge` in demo mode; Act VI
("Investigate the SIM change") renders "Additional verification needed" with
the DEGRADED-specific explanation and correct supporting/adverse fact lists at
both 1280 px and 375 px, wrapping cleanly with no clipping; Act III ("Try a
clean checkout") renders "Proceed" with its supporting facts and the
continuity-session beat; the new Act V button ("Show an unresolved-evidence
case") renders "Additional verification needed" naming all four unavailable
checks by API label, at both widths; the receipt link only appears after the
HTTP response returns (persistence-confirmed) and the status line updates
correctly; the Ed25519 tamper control still flips to "✗ signature INVALID" and
back at both widths; the new "← Back to the checkout demo" link on the receipt
page returns to `/judge`; no `innerHTML`/`outerHTML`/`insertAdjacentHTML` was
introduced anywhere in `judge.html`, and no JS console errors were observed
during any run.

*Known gaps, stated plainly rather than glossed over:*
1. **Keyboard-Tab traversal was not confirmed by an automated keystroke.** The
   browser automation tool used for this session could not reliably dispatch
   synthetic Tab/Enter key events that the page's focus/activation model
   registered (a tooling limitation observed on this session's `<summary>`
   toggle, not something specific to code written for P2). Every new
   interactive element is a native `<button>`, `<a>`, or `<details>/<summary>`
   with no `tabindex` override and no `outline` suppression anywhere in
   `judge.html`'s CSS, plus one added `:focus-visible` style for the new
   details toggle — so keyboard operability rests on standard HTML semantics
   that were not independently exercised end-to-end with a real keystroke in
   this pass. A follow-up session with working Tab-key automation (or a human
   pass) should confirm this directly before calling P2 fully done.
2. **`receipt.html`'s evidence table can overflow horizontally at 375 px.**
   Observed during this session's mobile check; the table has no
   `overflow-x: auto` wrapper and was not part of this package's listed file
   set or the presenter it exists to test. Pre-existing, not introduced by
   P2. Flagged here rather than fixed, since `receipt.html`'s layout was out
   of P2's scope beyond the one added back-link.
3. P2 does not resolve the open question P1 raised: how a real merchant
   integration is meant to supply `claimed_location` in practice (see below).

*The P1-flagged `claimed_location` question, carried forward for P4a:* today
`RequestContext.claimed_location` is populated only inside the two wired demo
acts (`act2`, `act6`) as a hardcoded synthetic `Area`; there is still no UI
affordance — in `judge.html`, the P4a merchant harness, or anywhere else — for
a real merchant to supply an actual claimed address/geofence per transaction.
P2 did not add one, deliberately: the judge page's controls must stay scoped
to the fixed demo acts (§3 P2 step 6), and a general "enter a location" field
belongs to a real verification request path, not the fixed public
demonstration. P4a's `demo/merchant_pilot` harness is the right place to
decide this, since it is the first place a real (if synthetic) merchant
request gets built server-side: it should either (a) collect a claimed address
from the operator and geocode it before constructing `RequestContext`, or (b)
explicitly document that location verification is out of scope for the pilot
until a merchant integration contract defines how a claim is captured
(checkout address? a separate attestation step?). Either way, P4a should reuse
`app/presentation.py`'s `present()` unchanged for its own result display — it
was built as a shared, decision/session-agnostic projection for exactly this
reuse, and `_verification_response` in `routes_consent.py` already calls it,
so P4a's harness calling the same consent-completion endpoint gets the
presentation for free.

*Files changed:* `app/presentation.py` (new), `tests/test_presentation.py`
(new), `app/domain/schemas.py`, `app/api/routes_verify.py`,
`app/api/routes_consent.py`, `app/api/routes_console.py`,
`app/agent/investigator.py`, `app/agent/explain.py`, `app/main.py`,
`app/static/judge.html`, `app/static/receipt.html`, this file, and the
Graphify outputs.
