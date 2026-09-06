# Isnad: implementation and release runbook

**Updated 6 September 2026. This is the active execution order.** It supersedes
older next-step ordering in the handoff, not historical evidence or product contracts.
Read this file, `CLAUDE.md`, `docs/PHASE2_HANDOFF.md` §3 and §12, and
`docs/NAC_DEMO_REVIEW_2026-09-06.md` before implementing.

## Objective and completion standard

Deliver a tested bilingual trust application for the MENA Ignite hackathon:
Gemini primary planning, explicit no-answer greedy fallback, useful Nokia API
integration, trustworthy signed receipts, polished English/Arabic UI, reproducible
demo calls, comprehensive user testing instructions and a private-repository push.

“Perfect” is a quality target, not a provable promise of zero bugs. Completion means
all required acceptance gates below pass, limitations are visible, and another
person can reproduce the release. Never substitute test counts, screenshots of
static pages, an API catalog listing, or configured credentials for evidence that
a complete journey actually works.

## 0. Establish the exact starting point

1. Work from the user's Isnad checkout. Read applicable `AGENTS.md`/`CLAUDE.md`.
2. Run `git status --short`, `git log -5 --oneline`, `git remote -v`, and inspect
   the relevant diff. Query Graphify before navigating implementation:
   `graphify query "Gemini planner Nokia provider Arabic UI evidence receipt"`.
3. Private destination is `private` → `AhmadShadeed32/isnad-private`.
   `ca8fde4` contains the latest API review, not a completed feature release.
4. **The current local tree contains unfinished changes not present in that commit:**
   Gemini default/fallback code and tests; `.env.example`/README edits;
   broader en/ar dictionaries; shared locale rendering and controls across pages;
   merchant locale routes; updated locale tests. Inspect and finish these changes.
   A fresh clone must implement them from this contract; do not assume they exist.
5. Preserve unrelated user work. Never reset the checkout, replace `.env`, rotate
   keys, recreate the database or force-push to simplify the task.
6. Historical checks: 886 tests at the completed original review; 901 after Gemini
   changes but before the latest Arabic changes; 39 focused locale/pilot tests
   after those changes. Current Arabic browser behavior is unverified. One known
   Ruff failure is an unused `noqa` on the pilot locale import. These counts are
   dated evidence, not the new release's results.
7. Start a progress ledger in `docs/IMPLEMENTATION_PROGRESS.md` (new file):

| Step | Status | Files/commit | Test command and result | Browser/API evidence | Remaining issue |
| --- | --- | --- | --- | --- | --- |
| 0–15 below | NOT STARTED / IN PROGRESS / PASSED / EXTERNAL LIMIT | exact paths/hash | dated | sanitized artifact | concrete |

Every checkpoint must say what is finished, what is merely mocked, what was
actually called, and the exact next action. Do not leave a vague “continue fixes”.

## 1. Freeze the baseline and protect reproducibility

Run from the repository root using Python 3.11+ and `.venv311`. If absent, inspect
`setup.sh` then use `make setup`; do not replace a functioning environment blindly.

```sh
.venv311/bin/python -m pytest -q
.venv311/bin/python -m ruff check app tests scripts demo
.venv311/bin/python scripts/verify_runtime_lock.py
```

Tests pin mock/greedy settings in `tests/conftest.py`. Do not remove those pins.
Record failures before changing code. Avoid `make lint`: it also invokes the
external dependency audit. An earlier automatic approval review rejected sending
the dependency inventory to PyPI; do not bypass that rejection. Report that check
as unperformed unless authorized later.

Generate an isolated evidence pack with the existing `scripts/evidence_pack.py`
using an output directory under `/tmp`; save one exact signed payload, signature
and public key for backward-compatibility tests. Never reserialize that payload
when verifying it later. Keep the fixed evaluation inputs unchanged.

**Gate:** baseline recorded; existing failures distinguished from regressions;
no live model/operator requests from automated tests; an old receipt preserved.

## 2. Finish the Nokia contract matrix before changing provider behavior

Read the API review linked above. Inspect installed SDK request/response models
and compare with the authenticated catalog. Store the final matrix in that review
or a linked contract document, including method, version/path, base URL, fields,
authorization, entitlement status, timeout, retry behavior, simulator scenario,
last observation, and response limitations.

Known facts to retain:

- SDK 10.0.0 defaults to `network-as-code.p-eu.rapidapi.com`; catalog examples use
  `network-as-code.p-eu.apihub.nokia.io`. Both use RapidAPI authentication headers.
  Paths match in five locally intercepted requests; actual host compatibility
  remains untested. Verify before changing the application's host configuration.
- SIM date: `/passthrough/camara/v1/sim-swap/sim-swap/v0/retrieve-date`,
  `latestSimChange`. Device date: corresponding `device-swap/.../v1/retrieve-date`,
  `latestDeviceChange` and optional `monitoredPeriod` in days.
- Nullable dates require explicit unknown handling. Provider activation/first
  association dates are not necessarily replacement events.
- Congestion query: `/congestion-insights/v0/query`, `device`, optional start/end.
  The catalog query example mistakenly contains subscription fields.
- Congestion subscription responses expose `subscription_id` and `started_at` in
  the SDK. Do not copy tutorial `resource_id`/`starts_at` attribute names.
- The account is in Simulator mode. Catalog visibility and SDK availability do
  not establish live-network entitlement or physical handset proof.

Audit existing Number Verification, location, reachability and roaming contracts
as well as additions. Scope-specific access and valid input preconditions must
remain enforced; a missing location claim must cause zero location SDK calls.

**Tests:** extend `tests/test_nac_contract.py`, `test_nac_provider.py`,
`test_provider_preconditions.py`, `test_nac_capabilities.py` as applicable. Use
`httpx.MockTransport` against the real SDK, asserting serialized requests and
normalization, rather than mocks that only reproduce our own adapter interface.

**Gate:** every implementation assumption has a source or an explicitly unknown
status. No invented endpoints, scopes, scenario numbers or network guarantees.

## 3. Build a bounded simulator probe tool

**New planned files:** `scripts/nac_demo_probe.py`, `tests/test_nac_demo_probe.py`.
These do not exist at this checkpoint. The old `t1_probe.py` is reference material;
its raw exception logging and unspecified SDK retries need improvement before reuse.

Implement the following CLI contract, then document its actual syntax:

- Default invocation prints an execution plan and performs zero external requests.
- `--execute` explicitly runs one named operation against an allowlisted simulator
  number. Reject non-`+9999` input, invalid E.164, unknown operations and untrusted
  endpoint overrides before accessing the SDK.
- Each call uses 10-second timeout and `max_retries=0`. No hidden retries, loops
  or automatic model calls. Record attempted call count, even when calls fail.
- Credentials stay server-side in existing configuration, never command arguments,
  browser links, reports, screenshots or source control.
- Allowlist recorded fields: operation, endpoint version/host, UTC observation,
  duration, HTTP status, provider request ID when safe, normalized result and
  bounded error code. Do not dump raw exception bodies, headers or traceback.
- A subscription plan shows callback host, device, expiry, maximum calls and cleanup.
  Accept only the controlled configured callback. Return/persist the created ID
  for recovery. An uncertain create must be reconciled, not repeated blindly.
- Capture `hosted_simulator`, never `live_operator`, for this account's test numbers.
- Dry-run, invalid inputs, sanitized errors, null/malformed data, and enforced
  timeout/retry options must have offline tests. Assert no transport request on
  validation failures. Assert call counts for success and failure paths.

Run the first six calls sequentially: SIM and device checks on each documented
`+99999991000` and `+99999991001`; then SIM date and device date on `...1000`.
Inspect each result before proceeding. A boolean table does not guarantee a date
value or a final Isnad verdict. Do not claim calls ran if only the dry-run passed.

**Gate:** sanitized observations committed; errors understood; safe tool tests
pass. If access is externally unavailable, record it and continue isolated app
work without claiming hosted validation. Never use a successful local mock to
replace a failed hosted observation.

## 4. Complete Gemini-first selection

**Files:** `app/config.py`, `app/agent/gemini.py`, `app/agent/planner.py`,
`app/agent/investigator.py`, source labels, `.env.example`, README, `pyproject.toml` comments.

| Condition | Required behavior |
| --- | --- |
| Valid affordable unused action | Execute Gemini's choice once, source `llm` |
| Valid STOP | End discretionary selection; policy gates still apply |
| Timeout/connection failure/no candidate text | Greedy may choose, visibly labelled with a bounded no-answer reason |
| Missing model key | Explicit unavailable status; greedy no-model path |
| Returned invalid JSON/schema/action, repeated/unaffordable action | Stop selection; no greedy replacement or invalid API call |
| Explicit model refusal, HTTP rejection including 429/4xx/5xx | Stop selection; diagnostic without response secrets |
| Per-investigation call cap | Stop selection; reaching the cap is not no-response |
| Mandatory policy check | Preserve and label as `policy`; do not mislabel as model choice |

Preserve original budgets, model cap and policy thresholds. Display-only narrative
fallback is a separate contract. Never feed caller/provider prose into the planner
as instructions. Never render model text through unsafe HTML.

```sh
.venv311/bin/python -m pytest -q tests/test_gemini_primary.py tests/test_gemini.py tests/test_llm_planner.py tests/test_allow_evidence_gate.py tests/test_hypothesis_relevance.py tests/test_t4_ask_the_agent.py
```

Add integration checks through completed investigations for STOP, invalid output,
partial fallback, and required-policy checks. Read all alternate evidence selection
paths so an unnoticed greedy helper cannot violate the contract.

**Gate:** normal configuration uses Gemini; explicit offline mode remains greedy;
recorded source labels reflect actual execution. Later capture one bounded Gemini
run over mock network data separately from the Nokia probes.

## 5. Add swap timestamps without changing receipt history

**Files:** provider normalization in `app/providers/nac.py` and `mock.py`,
`app/chain/models.py`, relevant schemas/investigator/presentation and UI renderers.
First decide and document whether temporal metadata belongs in a versioned evidence
extension or another compatible structure; do not casually alter signing behavior.

1. Add optional normalized date metadata: provider time, retrieved-at time, UTC age,
   source operation, availability/error reason, semantic ambiguity and actual
   monitoring horizon. Distinguish unsupported, no-date, denied, timeout, invalid.
2. Reject naive or implausible future timestamps; define any clock-skew tolerance
   explicitly. Never invent an event time from the boolean's `max_age` window.
3. Date retrieval is another external operation. Either expose it as a priced
   optional enrichment within budget, or document a new operation contract; never
   hide a second paid call behind a one-call cost. Do not double-count risk weight.
4. Preserve boolean evidence when enrichment fails. Do not silently convert null
   into “never swapped” or assume a date proves fraud.
5. Store age relative to the observation instant for reproducible audits. If the UI
   shows a live relative age, distinguish it from age at the decision.
6. Add Arabic/English human-readable display and LTR-isolated exact timestamp.
   Show unknowns and monitoring days rather than a broken date or fabricated age.
7. Confirm old receipt bytes/signatures remain verifiable; new receipts commit to
   the intended metadata with explicit compatibility handling.

**New proposed tests:** `tests/test_swap_timestamps.py`: timezone offsets, null,
activation ambiguity, monitoring horizon, malformed/future/naive times, provider
failure, budget too small, extra-call accounting, cache behavior, exact old receipt
verification, tamper detection on newly signed date fields, and bilingual display.

**Gate:** dates improve explanation with honest uncertainty; accounting and policy
are correct; no changed historical receipt and no regression in boolean checks.

## 6. Implement Congestion Insights as network condition information

**New proposed modules:** `app/network_conditions.py`,
`app/api/routes_network_conditions.py`, `tests/test_network_conditions.py`.
Names are proposals; adapt to established architecture and record final paths.

Before writing routes, define the request/response contracts and limits. Prefer
owner-scoped resources under `/v1/network-conditions` with explicit create, query,
get and delete operations. Public callback handling is a separate authenticated
route. These routes are not present yet; add OpenAPI examples only after implementation.

1. Persist the owning merchant, internal/provider IDs, test/live scope, expiry,
   device binding and callback secret securely. Follow established retention and
   database patterns; document worker/restart behavior rather than promise durability.
2. Use server-configured HTTPS callback and finite limits: subscription TTL, active
   count per owner/device, query interval/window, rate limit, request size and timeout.
   Propose 15-minute demo TTL; verify provider constraints before treating it as valid.
3. Require subscription before query per Nokia docs. Empty start/end is a forecast;
   validate explicit chronological timezone-aware historical intervals. Return mode,
   interval, level, nullable confidence, observation time and provenance.
4. Never turn missing confidence into zero or 100. Never treat an empty list as Low.
5. Verify callback bearer token with constant-time comparison, schema and subscription
   binding. Deduplicate event IDs and reject stale/out-of-order updates. Bound storage.
6. Handle expiry/delete idempotently. Reconcile uncertain upstream writes; surface
   cleanup failures. Delete only resources owned by the authenticated merchant.
7. No provider request on page load or locale change. User action starts a bounded
   request. Polling must stop on expiry/terminal state and back off on transient errors.
8. UI shows network conditions separately from trust verdict: level, forecast/history,
   period, confidence/unknown, updated-at, provenance and retry action. Preserve form
   input and order state. Congestion does not prove a failure's cause or justify
   waiving verification or increasing fraud score.

**Tests:** two-owner isolation for every operation, invalid callback/auth, duplicate
and out-of-order events, provider denial/timeout, empty data, unknown confidence,
subscription expiry, deletion/recovery, concurrency, restart limits, quotas and
zero calls on passive UI rendering. Use SDK transport fixtures for wire contract.

**Hosted gate:** create → get → forecast query → historical query → delete → get
confirms deletion; six outbound calls maximum in the normal plan. Observe callback
delivery separately. If unavailable, expose the limitation and use visibly authored
fixtures for UI demonstrations. Never advertise delivered notifications from a
successful create alone.

## 7. Add the relevant identity extensions, in this order

These extend the API review; do not bolt them on as an untested array of checks.
Apply the same contract, quota, consent, source-label and test requirements as above.

### 7a. Number Recycling

Inspect installed `number_recycling.check` and authenticated schema first. Add a
merchant-supplied/maintained last-verified ownership date with clear provenance,
not an arbitrary signup date guessed by the backend. Check continuity before
reusing established-customer trust. A recycled number triggers fresh verification;
out-of-range or unavailable data remains unknown. Update action/policy definitions
only with explicit budget/relevance semantics, tests and documented tradeoffs.

Tests: recycled/not recycled, invalid/out-of-range/missing reference date, future
date, no prior verification, wrong owner, denied/unavailable service, correct cache
key including reference date, no automatic ALLOW from a non-recycled number.

### 7b. Network SIM Swap subscriptions

Verify catalog v0.3.0 request/callback/error/consent contract and whether an SDK
resource exists; 10.0.0 inspection found none. Use a narrowly implemented REST
adapter or a justified tested SDK upgrade, not a guessed method. Connect authenticated
network events to existing trust-session revocation with ownership, expiry, replay
and duplicate protections. Preserve the explicit local simulation control.

Tests: forged event, stale event, unrelated subject, duplicate, post-expiry event,
revoked session, blocked order release and provider disconnect. Hosted callback
proof is a separate gate; absent access is an external limit, not a completed integration.

### 7c. Consent Info

Check permission for the exact scopes and purpose; follow a permitted operator
capture URL when needed. Do not treat API-key possession or Number Verification
consent as universal permission. Protect callback/redirect ownership, state and
replay; validate destinations under the provider trust configuration.

Tests: allowed, denied, capture needed, no capture URL, unsafe URL, expiry, scope
mismatch and unavailable service. Consent status never counts as fraud evidence.

### 7d. Optional after required gates: forwarding and tenure

Call Forwarding is relevant to voice-dependent recovery; it does not imply SMS
forwarding or fraud by itself. KYC tenure can corroborate subscription continuity;
it does not prove identity or merchant history. Implement only with a demonstrated
product path, normalized costs, source labels and adversarial/unknown tests.

Defer KYC Fill-in/Match/Age, location retrieval/geofencing, QoD and slicing unless
the user expands the use case. Keep the decision and reason in the feature inventory.
“Everything” includes an explicit disposition for each API, not indiscriminate calls.

## 8. Complete Arabic and English behavior on every surface

**Files:** `app/static/i18n.js`, `app/static/i18n/{en,ar}.json`, all product HTML,
`app/presentation.py`, locale routes, merchant HTML/login framing and fake operator UI.

The local generic exact-text translator is unfinished. Review it as provisional:
static catalogue coverage is not full localization. Prefer stable keys and structured
interpolation for dynamic states; preserve originals and application state.

1. Inventory visible copy: navigation, headings, actions, tooltips, accessible names,
   placeholders, validation, loading/empty/errors, scenario descriptions, deterministic
   explanations, evidence labels, session/outcome states and network conditions.
2. Add one shared language control and persistence on each surface. Merchant service
   must serve locale assets on its own origin. Handle absent storage/dictionaries.
3. Audit mutation-observer logic for loops, lost updates, event-listener loss and
   performance on long traces. Ensure the newest language request wins races.
4. Do not mutate form values, selected option values, machine IDs, signed bytes,
   verification requests, or text tokens used as state. Decouple DOM text comparisons
   from logic where needed. Locale changes must not generate model/operator requests.
5. Remove inappropriate forced-English sections; use logical CSS properties, readable
   Arabic font/line height and no Latin letter spacing. Isolate dates, hashes,
   phone numbers and codes LTR. Add Arabic glosses beside signed enums.
6. Mark untranslatable arbitrary provider/model prose honestly. All authored product
   copy must be localized; do not use that exception to leave routine UI English.
7. Correct draft translations by context. Human review stays “pending” until a human
   actually reviews it; never claim native review from automated tests.

```sh
.venv311/bin/python -m pytest -q tests/test_i18n.py tests/test_judge.py tests/test_console.py tests/test_presentation.py tests/test_receipt_download.py tests/test_proof_shares.py tests/test_merchant_pilot.py tests/test_pilot_polling.py tests/test_pilot_retention.py
```

Add executable browser/DOM tests for rapid switching, dynamic inserted results,
failed dictionary loads, stored preference, input/focus preservation, unchanged
receipt bytes and no extra API calls. Source-string tests alone do not pass this gate.

## 9. Polish and verify the actual UI

Preserve the established product design; improve hierarchy and clarity consistently.
Judge view leads with the customer problem, a clear primary action, evidence trace,
plain-language result and receipt. Secondary network details must not overwhelm
checkout. Console remains useful for technical inspection. Use honest provenance
badges on actual results, not a global misleading “live” label.

Run the application locally in isolated mock mode with demo enabled and Gemini
key explicitly empty for browser regression work. Use a dedicated temporary DB/key
and test merchant credential; do not reuse production data. Serve one worker with
`--no-access-log` to avoid OAuth code logging. Use existing pilot/fake-operator
setup from `docs/P4A_IMPLEMENTATION_RECORD.md` for the three-service journey.

| Surface | Mandatory states and interactions |
| --- | --- |
| `/judge` | Initial, all three cases, in-progress trace, signature check, continuity session and revocation |
| `/console` | Credential entry, Acts I–IX, source labels, errors, reconnect, trace recovery, Ask the agent |
| `/r/{chain_id}` | Valid/invalid/untrusted signature, exact-byte download, long identifiers, unavailable receipt |
| Shared proof page | Create/open, missing/expired/revoked link, clear limits vs full receipt |
| `/lab` | Case selection, steps, shuffle/reset, comparison/fault states, artifact provenance |
| `/privacy` | Actual posture response, loading/unavailable; readable retention values |
| Consent completion | Success landing and return-to-merchant instruction; no leaked callback values |
| Merchant login/checkout/flow/readiness | Login error, validation, consent QR, pending/terminal/error recovery, order/review/outcome/session controls |
| Fake operator | Consent allow/deny and return; clear local simulation label |
| New network condition UI | Unknown/Low/Medium/High, stale/expired/denied, forecast/history, create/delete/retry |

For **every surface**, test English and Arabic at 375px mobile and 1440px desktop.
Also inspect 320px and tablet breakpoints; test 200% zoom and keyboard-only critical
paths. Save screenshots under `docs/ui/release/` with page/language/state/size names.

Acceptance:

- No clipped Arabic, hidden controls or page-wide horizontal overflow; wide raw
  audit tables may scroll inside a labelled container.
- Contrast meets WCAG AA targets; text/glyphs accompany state colors.
- Visible keyboard focus, meaningful accessible names, usable touch targets,
  correct reading order and no focus traps. Verify measurements, not visual guesses.
- Buttons show progress and prevent duplicate writes; failures offer actionable
  recovery without discarding user input. Reload/back navigation is coherent.
- Screen remains stable after rapid locale changes and dynamic updates; no browser
  console errors, unhandled promise rejections or unexpected network requests.
- Secrets never appear in URL, DOM, screenshot or browser console. Signed values
  and copy/download outputs stay exact.

Use a real browser; record browser/version, viewport and completed interactions.
When automation is unavailable, manual browser checks are required and should be
recorded as manual. Do not claim screenshot coverage for unvisited states.

## 10. Re-audit core behavior while integrating additions

Run relevant existing suites rather than create redundant tests. Add a regression
for every confirmed new bug. Inspect these invariants explicitly:

- Consent state/nonce, owner binding, single-use callbacks, expiration, cached
  completion and recovery after lost responses.
- Tenant isolation for traces, receipts, sessions, outcomes and new resources.
- Idempotency under concurrent writes, timeout recovery, no duplicate billed checks.
- Evidence support/relevance/ALLOW gates, unknown and contradictory evidence,
  signed thresholds and normalized costs; no fixture tuning to improve a score.
- QR/authorization link clearing at terminal state; phone retention limited to
  the established five-minute continuity opt-in window; idle cleanup works.
- One trust session per flow, revocation blocking order release, merchant-reported
  outcome correction without rewriting history.
- XSS, request limits, unsafe redirects, startup posture, package assets and secrets.

Use `tests/test_s*.py`, consent/challenge/session/outcome tests, plus
`test_allow_evidence_gate.py`, `test_hypothesis_relevance.py`, `test_review_regressions.py`,
`test_pilot_retention.py`, and `test_pilot_polling.py` as the existing coverage map.

## 11. Run a bounded end-to-end demo rehearsal

Keep three separate evidence records: local deterministic, hosted Nokia simulator,
and physical handset. Do not merge their success claims.

1. Rehearse mock/greedy full journey and failure paths; save baseline receipt.
2. Rehearse Gemini with mocked network responses; cap the investigation using the
   existing limits and record model actually used, selections, STOP/fallback and latency.
3. Rehearse the hosted simulator checks from step 3; observe real responses before
   presenting the integrated hosted case. API response examples are not executions.
4. Run hosted congestion lifecycle and cleanup if available. Show callback delivery
   only when captured; controlled event fixtures remain visibly simulated.
5. Replay the authored new-SIM/same-handset story separately. Nokia `...1000`
   documents both swaps and `...1001` neither: never mix device identities to fake it.
6. Exercise provider unavailable and model no-answer states independently. Confirm
   no live-provider failure silently turns into mock success.
7. If authorized/onboarded, use `scripts/handset_validation.py live` following its
   documented arming/configuration requirements. User completes handset steps.
   A local `contract` run does not substitute for this trial.

**Gate:** five-minute script works with honest labels; no leftover subscription;
call/latency totals and external limitations documented; receipts verify afterward.

## 12. Publish a complete user test guide and improve README

**New planned file:** `docs/TESTING_GUIDE.md`. One row per feature with: status,
setup, exact user action, expected visible result, automated test command, actual
validation evidence and known limits. Include existing functionality, not only new APIs.

Mandatory inventory: Judge three cases; console Acts I–IX; Gemini/action/STOP/
fallback; forward and caller verification; announcements and velocity; consent
allow/deny/expiry/recovery; challenges and outcome corrections; trust sessions and
revocation; idempotency and trace replay; receipt/tamper/download/offline verifier;
shared proof expiry/revocation; lab comparisons/faults; privacy/retention/readiness;
Arabic switching; swap dates; recycling; network conditions and notifications;
conditional integrations and deferred APIs. Never leave a planned feature looking tested.

README must let a new reader understand the problem, start locally, run a demo and
assess proof quickly. Include architecture, setup, environment-variable meanings
without values, separate offline/Gemini/hosted commands, screenshots from the actual
UI, API examples, demo sequence, tests, limits and links to detailed guides. Remove
stale fallback descriptions, old test totals and unsupported marketing claims.
Update `docs/CURRENT_STATE.md` if present, the handoff, capability manifest and
implementation status. SDK method availability alone must never become “verified”.

## 13. Final offline release gate

Run from the final working tree. Record output and exit code. Explicitly disable
external providers/models in the shell used for artifact/evaluation scripts so
local `.env` cannot silently initiate billable work:

```sh
export ISNAD_PROVIDER=mock
export ISNAD_PLANNER=greedy
export ISNAD_GEMINI_API_KEY=
.venv311/bin/python -m pytest -q
.venv311/bin/python -m ruff check app tests scripts demo
.venv311/bin/python scripts/verify_runtime_lock.py
.venv311/bin/python scripts/evidence_pack.py --output-dir /tmp/isnad-release-evidence
.venv311/bin/python scripts/independent_evaluation.py --json
.venv311/bin/python scripts/false_decline_baseline.py --sweep
.venv311/bin/python scripts/handset_validation.py contract --output /tmp/isnad-release-consent.json
```

Use a fresh output directory if those locations already contain another run.
Confirm Node.js/browser test dependencies are available and JS tests really ran;
a skipped behavioral test is not a pass. Review warnings and justify any remaining.
Recheck the preserved old receipt and every new evidence-pack signature.

Regenerate affected lab artifacts with `scripts/build_lab_artifacts.py --out` to a
review location first. Compare before replacing committed artifacts; record changed
calls/outcomes and genuine code identity, including dirty state. Never hand-edit
provenance to look current. Graph update: `graphify update .` after final code edits.

Build a wheel using the project's existing packaging flow, install into a clean
Python 3.11+ environment, and launch outside the repository directory with isolated
DB/key and offline settings. Smoke product pages, locale assets, policy, signed
registry and lab bundle. A source-checkout launch cannot establish wheel completeness.
Repeat only checks affected by subsequent changes; run final full checks after any
material integration fix. Do not claim the advisory audit passed if it remained blocked.

**Gate:** clean relevant checks, complete runtime assets, documented evaluation
differences, verified browser matrix and accurate evidence ledger.

## 14. Commit, push and confirm the actual release

1. Inspect `git diff --check` and the staged diff. Stage specific reviewed files;
   exclude secrets, local databases, private callback URLs, auth headers and debug dumps.
2. This repository ignores many docs; add narrowly scoped exceptions or explicitly
   add the intended documentation. Verify that linked deliverables are actually tracked.
3. Commit coherent packages with accurate messages. A docs-only checkpoint is not
   an app release. Preserve the user's unrelated edits.
4. Push to the existing authorized private remote with normal history-preserving
   Git operations. No public push, force push or deployment is implied.
5. Compare local HEAD with `git ls-remote private refs/heads/main` after pushing the
   intended branch. If the remote moved, inspect and integrate without overwriting it.
6. Reconcile artifact identity without inventing a self-referential final commit hash.
   Record which code revision generated artifacts and which release contains them.

**Gate:** private remote contains the reviewed release and all instructions needed
for a fresh clone; pending work and external limits are clearly stated.

## 15. Final handover format

Report: commit/remote, what changed and why, actual test results, tested browser
states, actual hosted calls and cleanup, user test-guide link, startup commands,
and material limitations. Provide a compact inventory of everything added.

Completion checklist:

- [ ] Gemini is primary; strict no-answer fallback and source labels verified.
- [ ] Arabic/English complete authored UI and dynamic states pass real browser checks.
- [ ] Swap dates preserve semantics, budgets and old signatures.
- [ ] Congestion lifecycle/ownership/cleanup/UI pass tests; hosted status is honest.
- [ ] Recycling and chosen identity extensions have complete contracts and user paths.
- [ ] Existing checkout, consent, merchant, receipt and session flows still work.
- [ ] Safe probe runner and actual observation records exist.
- [ ] Test guide covers all existing/new features and explicit deferred work.
- [ ] Full release checks, package smoke and Graphify are current.
- [ ] Private push verified; no secrets or unfinished work represented as finished.

If a gate cannot pass, identify the exact failure, evidence, impact and next action.
Continue independent authorized work. Do not claim perfection or mark a failed
external call successful to satisfy the checklist.

## Resume prompt for another model

> Continue Isnad from `docs/EXECUTION_RUNBOOK.md`. Read the handoff and API review,
> inspect the current diff and progress ledger, and start at the first incomplete
> gate. Preserve existing work. Implement and verify the full scope, not just docs.
> Keep Gemini primary, greedy only for no answer, preserve policy and signed data,
> finish Arabic and the actual browser journeys, and keep all API evidence honest.
> Use bounded simulator calls with sanitized records. Update the guide and ledger
> as you go, then push the reviewed result to the authorized private repository.
> Report exact tests, calls, commit and remaining limits; never infer completion
> from a configured key, mock response or older test result.
