# Isnad — implementation handoff

## Current code review — 7 September 2026

**This checkpoint supersedes current-state claims in the historical sections below.**
The user requested a codebase review, proposed fixes in the handoff, and a README
rewrite. This pass changes documentation and adds an offline reproduction script;
the application defects below are **open**, not implemented fixes. Existing local
lab, browser-test and screenshot changes were present before this review.

### Validation of this checkout

| Check | Observed result |
| --- | --- |
| Full `pytest -q` inside the sandbox | **1,105 passed**, 61 browser setup errors, 3 warnings. All browser errors were local socket permission failures, not assertion failures. |
| Browser suite rerun with local server/browser permission | **60 passed, 1 xfailed** in 87.69 seconds. The expected failure is English `/lab` at 375 px. |
| `ruff check app tests scripts demo` | Passed. The old unused-noqa warning is no longer current. |
| `scripts/verify_runtime_lock.py` | Passed: 38 exact pins cover direct runtime dependencies. This is not an advisory audit or a clean installation test. |
| Offline evidence pack | Five scenarios completed; all five stored receipt signatures valid and trusted. |
| Fixed independent synthetic evaluation | 13/13 completed, zero errors; **34/78 evidence calls**, **6/13 CHALLENGE**, **4 authored-expectation disagreements**. |
| Review probes | Reproduced cross-device queries, unthrottled repeats, callback-ID omission, mock provenance error, uncertain/empty-ID creates, concurrent quota bypass, contradictory hybrid guards and expired-session behavior. |

Together the separate test runs cover **1,165 passes and one expected failure**;
a single unsandboxed full-suite run was not performed. No Nokia/Gemini calls,
physical handset trial, fresh dependency advisory audit, Docker build or Postgres
integration run was performed in this pass. Those are not implied by passing tests.
This was a broad source review with focused reproductions, not proof that every
possible defect has been found.

Fresh offline scenario outputs (default repository policy, mock/greedy):

| Case | Decision / grade | Evidence links | Cost units | Uncalibrated score |
| --- | --- | ---: | ---: | ---: |
| Clean signup | ALLOW / ATTESTED_FULL | 2 | 3 | 0.041 |
| Account takeover | DECLINE / REFUTED | 4 | 10 | 0.981 |
| Clean checkout | ALLOW / ATTESTED_FULL | 2 | 4 | 0.096 |
| Evidence unavailable | CHALLENGE / UNRESOLVED | 3 | 7 | 0.280 |
| SIM replacement | CHALLENGE / DEGRADED | **5** | **12** | **0.322** |

The old six-link / 0.242 replacement and 38/78 evaluation claims are stale.
Swap-date enrichment consumes separate budget without adding an evidence link;
link counts are not total provider-operation counts. The evidence-pack table's
per-link costs also omit those extra operations, although its total includes them.
Do not advertise the evaluator's 34/78 link count as total paid API-call savings.

### Open findings and concrete fixes

Priorities: **P1** before relying on paid calls, trust expiry or callbacks;
**P2** before a release claiming complete functionality. Each item includes its
own completion test; preserve issuing policy and exact historical receipt bytes.

#### R01 · P1 — Subscription queries are not bound to the subscribed device

**Source:** `app/network_conditions.py::query`, `app/db/models.py::NetworkConditionSubscriptionRow`.
Creation stores `device_hash`, but query checks only owner and active status before
sending the request body's phone to the provider. The probe subscribes phone A,
queries phone B twice, and records two calls for B. Owner isolation works; the
same owner's device/subscription prerequisite does not.

**Fix:** compare the request phone's keyed hash with the stored device binding
before any provider call. Also bind subscriptions to the provider that created
them so configuration changes cannot reinterpret an old provider ID.
**Acceptance:** same-owner wrong-device and wrong-provider queries make zero
provider calls; matching-device queries work; foreign owners still receive 404.

#### R02 · P1 — Registered callback URLs cannot identify a newly created subscription

**Source:** `app/network_conditions.py::create`,
`app/api/routes_network_conditions.py::receive_event`,
`app/providers/nac.py::create_congestion_subscription`.
The receiver is `/v1/network-conditions/callbacks/{subscription_id}`, but create
passes the fixed configured URL unchanged. The generated local ID is never added
to it or sent separately. A static URL cannot name each newly generated row.
Tests call `accept_event` with a known local ID and therefore miss this wiring gap.

**Fix:** define configuration as a validated callback base and append the local ID,
or implement one receiver that resolves a provider ID/token to the local row.
Validate the actual provider payload against an explicit adapter; the current
custom `event_id/level/occurred_at` schema alone is not wire-contract proof.
**Acceptance:** a fake provider POSTs to the exact URL it receives at creation,
with the exact documented fixture payload and token; the event reaches the right
row. Multiple subscriptions, wrong tokens and duplicate events are covered.

#### R03 · P1 — Subscription quotas and query pacing do not bound concurrent spend

**Source:** `app/network_conditions.py::_active_counts/create/query`,
`app/config.py::network_conditions_min_query_interval_seconds`.
Counts are read before a separate insert, with no serialized reservation. Routes
run this in worker threads, so one worker does not prevent the race. A barrier
probe creates **two active subscriptions for one device** despite the limit of
one. Query never reads the configured five-second interval; immediate repeats
both reach the provider. The general 60/minute route limit is a separate guard.

**Fix:** reserve owner/device capacity atomically using database locking or a
transactional quota record; for the supported single process, a lock can be an
interim guard. Atomically reserve per-subscription query times and in-flight
slots before SDK calls. Validate positive limits/TTLs at startup.
**Acceptance:** concurrent same-device creates produce one provider create;
owner limits hold across different devices; simultaneous/repeated queries yield
one call plus a stable retry response until the configured interval elapses.

#### R04 · P1 — Uncertain creates lose recovery and empty provider IDs become active

**Source:** `app/network_conditions.py::create/delete`,
`app/providers/nac.py::create_congestion_subscription`.
Every exception marks the reservation `failed`, which is terminal and excluded
from quotas. A timeout after remote success can therefore be followed by another
create; no listing/reconciliation path recovers the first remote ID. The probe
produces two failed rows with no provider IDs. An empty response ID is accepted
as `active`; delete then skips the provider and reports local deletion.

**Fix:** distinguish definite rejection from uncertain completion. Keep an
`unknown/pending_reconciliation` state that consumes capacity, expose a durable
operation handle, and reconcile through the supported provider listing/get
contract before retrying. Add owner-scoped creation idempotency. Require a
nonempty valid remote ID before activation; never confirm remote deletion when
remote state is unknown.
**Acceptance:** timeout-after-success plus retry creates at most one remote
subscription; empty IDs never become active; response loss and failed cleanup
remain recoverable across restart.

#### R05 · P1 — Trust sessions stay active and perform checks after their TTL

**Source:** `app/session/manager.py::get/_monitor`, `app/api/routes_session.py`.
Expiry is checked before sleeping, but not on reads or immediately after sleep.
The probe uses a shortened TTL/poll interval: a read after TTL still returns
`ACTIVE`, then both SIM/device calls run after expiry. Normal operation has the
same window, enlarged by the live provider's 30-second polling floor.

**Fix:** derive effective expiry on every read/use, bound sleep to remaining TTL,
and recheck expiry before each provider call. Make the terminal transition/event
idempotent. Consumers must compare expiry even when the monitor is delayed.
**Acceptance:** a fake-clock test reads after TTL while the monitor sleeps and
gets EXPIRED; no new provider call starts after TTL, including between SIM and
device checks and under a delayed event loop.

#### R06 · P2 — Mock congestion data is falsely labeled hosted-simulator data

**Source:** `app/network_conditions.py::_scope/query`,
`app/domain/schemas.py::NetworkConditionSubscription/NetworkConditionQueryResponse`.
`_scope()` returns `hosted_simulator` for every current configuration, including
`MockProvider`. The probe confirms this label on a wholly local mock query.
That confuses authored fixtures with an actual hosted Nokia simulator response.

**Fix:** record explicit provider provenance at creation (`mock`, `nac_fake`,
`hosted_simulator`, and separately verified live scope), and project that stable
value through queries and both locale dictionaries. Do not infer live access
from a successful call or retrofit claims into signed historical receipts.
**Acceptance:** mock/fake data never carries a hosted/live label; simulator data
is labeled as such; language switching preserves provenance meaning.

#### R07 · P2 — Network-condition records have no terminal retention

**Source:** `app/network_conditions.py`, `app/retention.py::purge_once`.
Expired/deleted/failed subscription rows are never purged; their event rows are
only capped per subscription. Repeated create/delete cycles grow both tables
over time, and `_active_counts` scans all rows for an owner. Expiry changes the
reported status but does not reclaim anything.

**Fix:** define a terminal retention window, sweep child events and terminal
subscriptions in bounded batches, and keep unresolved remote-cleanup records
until reconciliation. Query active rows using an indexed status/expiry predicate.
**Acceptance:** an idle fake-clock sweep reclaims eligible rows and events, keeps
active/unreconciled records, and remains bounded with many historical rows.

#### R08 · P2 — Network-condition input/output validation is incomplete

**Source:** `app/domain/schemas.py::NetworkConditionSubscribeRequest/NetworkConditionQueryRequest`,
`app/network_conditions.py::validate_period/query`.
The phone fields only check length: `notaphone` passes. Any two ordered bounds
within the maximum span are called `history`, even if both are in the future.
Provider intervals have no count limit or local chronology/timezone checks;
missing keys/null dates escape normalization and can become 500 responses.

**Fix:** reuse the application's E.164 validation, define permitted temporal
ranges explicitly, bound result counts, and validate each provider interval
before response construction. Map malformed provider data to a stable sanitized
unavailable/502 result instead of an uncaught validation exception.
**Acceptance:** invalid phones/periods cause zero calls; null/missing/reversed
intervals and oversized arrays produce bounded, controlled responses. Empty data
remains unknown, never Low.

#### R09 · P2 — Ended trust sessions keep raw phone numbers until another create

**Source:** `app/session/manager.py::_prune/end/_monitor`, `app/retention.py`.
`_prune()` is called only by `create()`. After the last session expires, is ended,
or is revoked, its record still holds the raw phone for the life of an idle
process. The merchant harness's five-minute cleanup does not purge this API store.

**Fix:** define a bounded terminal session retention period, clear raw phones
once monitoring ends (retain only a masked display value if required), and run
cleanup independently of new-session traffic. Preserve a brief terminal-status
window so clients can observe expiry/revocation.
**Acceptance:** after all terminal transitions, idle cleanup removes PII within
the documented window; one merchant's polling cannot prolong another's retention.

#### R10 · P2 — The Docker image cannot serve the lab

**Source:** `Dockerfile` runtime COPY instructions,
`app/api/routes_lab.py::_BUNDLE/_live_identity`.
The runtime copies `app/` and `pyproject.toml` but no `demo/` package or recorded
bundle. `/lab` unconditionally imports `demo.lab.runner`, so this path fails in
the image even though `/readyz` can succeed. Wheel packaging already includes
`demo`; a wheel smoke test does not verify the Docker file layout.

**Fix:** ship the lab runtime and bundle in the image, preferably move required
runtime resources under `app/`, or explicitly disable lab routes/links in that
artifact. Keep fake-operator development dependencies out of runtime imports.
**Acceptance:** start the built image in isolated mock/demo mode with the registry
public-key pin; request `/lab`, `/lab/bundle.json`, `/judge`, `/receipt/...`, and
`/readyz`. Verify readable bundle/identity output even without `.git` or git.

#### R11 · P2 — CI installs Playwright but never installs its Chromium build

**Source:** `.github/workflows/ci.yml`, `requirements-dev.txt`,
`tests/browser/conftest.py::browser`.
The suite now unconditionally imports Playwright and launches its bundled
Chromium. CI installs the Python package and runs all tests without
`python -m playwright install --with-deps chromium`. A fresh runner with no
matching Playwright browser cache cannot run these tests. The old README also
omitted this setup step; that omission is corrected by this rewrite.

**Fix:** install Chromium and its Linux dependencies before pytest; optionally
split browser checks into a dedicated required CI job. Keep dev extras in
`pyproject.toml` aligned too: `pip install '.[dev]'` currently omits Playwright.
**Acceptance:** a clean Linux job with an empty browser cache executes browser
and async tests, with only the explicitly tracked mobile-lab xfail remaining.

#### R12 · P2 — No configuration can run the advertised selective-live hybrid mode

**Source:** `app/config.py::check_startup_posture/makes_billable_calls`,
`app/providers/__init__.py::get_provider`.
With nonempty action/number allowlists, demo=false is rejected because hybrid is
demo-only, while demo=true is rejected because public demo credentials would
permit billable calls. Both rejections were reproduced. The protections are
sensible individually, but the documented selective-live feature is unreachable.

**Fix:** either formally retire selective-live hybrid and remove its setup claims,
or add an authenticated private rehearsal mode that never mints public demo
tokens and still enforces explicit action/subscriber allowlists and spend limits.
Do not simply remove the billable-demo guard.
**Acceptance:** an explicit configuration matrix permits only the intended
private rehearsal path, or consistently rejects a documented unsupported mode;
public demo tokens can never authorize paid calls.

#### R13 · P1 — Verification idempotency is not durable with its signed result

**Source:** `app/api/routes_verify.py::verify`, `app/cache.py`, `app/db/store.py`.
The chain commits before the `done` cache entry. A crash, cancellation, or cache
write failure in that interval leaves a signed chain without a durable mapping
from the idempotency key. The default memory cache also loses completed entries
on restart. A retry can issue a second investigation and paid calls. This is a
source-confirmed crash window; this review did not execute a paid crash test.

**Fix:** persist owner/key/request commitment and operation state in the database;
commit the response-to-chain mapping atomically with the signed chain. Treat
uncertain upstream work as reconciliation-required, not safe to repeat. Redis
can accelerate replay but must not be the only mapping to the committed result.
**Acceptance:** inject failure after chain commit but before response/cache write,
restart, and retry the same key: return/reconcile the original operation with no
second provider work. Preserve 409 for changed bodies and concurrent requests.

#### R14 · P2 — Requested Redis caching silently falls back and blocks async routes

**Source:** `app/cache.py::get_cache/RedisCache`, `app/api/routes_verify.py::verify`.
A Redis selection with no URL or missing optional package silently becomes
memory caching. The configured durability behavior therefore changes without a
startup failure. With Redis installed, synchronous network operations execute
directly inside the async verification handler with no explicit socket timeout.
A stalled cache can block the event loop and unrelated requests.

**Fix:** validate cache backend/URL/package at startup and fail when the requested
backend cannot be constructed. Use an async client or bounded worker-thread
calls with explicit connection/read timeouts and sanitized availability errors.
Redis alone does not remove the one-worker/one-replica restriction.
**Acceptance:** invalid Redis config refuses startup; an unavailable/hung Redis
returns bounded errors while liveness and unrelated requests remain responsive.

#### R15 · P2 — Mobile lab overflow is an acknowledged failing browser check

**Source:** `tests/browser/test_surfaces.py::LAB_MOBILE_OVERFLOW`,
`app/static/lab.html`.
English `/lab` at 375 px still has a strict xfail for root horizontal movement
(the marker records 422 px). This browser run reproduced the expected failure;
it is not evidence that all responsive layouts pass.

**Fix:** inspect the actual root overflow in Chromium, including grid/flex minimum
sizes and positioned elements; contain wide tables locally without hiding page
content or keyboard focus. Remove the xfail only after the defect is fixed.
**Acceptance:** the existing check passes normally at 375 px in both languages,
with all controls reachable and wide tables scrolling inside their own container.

#### R16 · P2 — Current documentation and evaluation totals mix different budgets

**Source:** historical README/handoff, `scripts/evidence_pack.py::_step_summary`,
`scripts/independent_evaluation.py`, `app/agent/investigator.py::_enrich_timing`.
The old docs promise six links/0.242 and three evaluation disagreements. Fresh
runs produce five links/0.322 and four disagreements. Date enrichment is a
separate charged operation, but the evidence-pack per-link breakdown omits it
and the evaluation's "calls" count counts evidence links. This makes a claimed
paid-call saving or a manual cost reconciliation misleading.

**Fix:** README and this checkpoint now report fresh outputs. Next update the
presenter script, CURRENT_STATE and recorded lab artifacts from the same build;
report evidence calls, date-enrichment operations and total cost separately in
both evaluators. Review the four expectation disagreements without silently
retuning fixture labels or calling a synthetic score measured fraud accuracy.
**Acceptance:** a recording provider's operation count equals report totals;
per-operation cost sums match `evidence_cost`; all current-facing docs agree on
one artifact's policy/code identity, with older numbers explicitly historical.

### Recommended implementation order

1. R01–R04: repair network subscription binding, callback delivery, atomic limits
   and recovery as one coherent lifecycle; add migration(s) only after checking
   the current Alembic head (`0006_network_conditions`).
2. R05 and R13: enforce trust expiry and durable verification replay before any
   paid deployment or merchant order-release reliance.
3. R06–R09 and R14: finish provenance, data validation, retention and cache failure
   behavior. Keep provider payloads/secrets out of error messages and artifacts.
4. R10–R12 and R15: verify the actual deployment artifact, clean CI and mobile UI;
   make the hybrid feature's supported status explicit.
5. R16: regenerate evaluation/lab artifacts and synchronize remaining presenter
   docs. Rerun affected regressions, the full suite, browser checks and image
   smoke; report unresolved xfails and external validation separately.

Existing operational limits remain: one worker/replica; process-local consent,
sessions and demo tokens; API-key-derived ownership means key rotation needs an
explicit tenant migration strategy; public full receipts are bearer-capability
URLs and persist independently of expiring shared summaries. Physical handset
proof, current advisory auditing and real fraud calibration remain separate work.

### Reproduce the review locally

From the repository root:

```bash
.venv311/bin/python docs/reviews/codebase_review_2026_09_07.py
.venv311/bin/python -m pytest -q --ignore=tests/browser
.venv311/bin/python -m pytest tests/browser -q
.venv311/bin/python -m ruff check app tests scripts demo
.venv311/bin/python scripts/verify_runtime_lock.py
.venv311/bin/python scripts/evidence_pack.py --output-dir /tmp/isnad-review-evidence
.venv311/bin/python scripts/independent_evaluation.py
```

The review probe forces mock/greedy, uses a temporary SQLite database and signing
key, and makes no external calls. It **prints current defects**, not passing
acceptance assertions; convert each relevant probe into a focused failing
regression before fixing the corresponding code. The browser suite requires
installed Chromium and permission to bind loopback ports and launch it.

---

## Historical handoff — checkpoints through 6 September 2026

The remaining text preserves prior decisions and work history. Its test totals,
"current" status, completion claims and execution ordering are historical; use
the checkpoint above for this review's findings and observed validation.


Updated 6 September 2026. **Read this file first.**

**Start implementation here:** [step-by-step execution runbook](EXECUTION_RUNBOOK.md).
It is the active order and acceptance contract for any next model: baseline,
API contracts/probes, Gemini, new capabilities, Arabic/UI, browser rehearsal,
complete test guide, release checks and private push. The [API review](NAC_DEMO_REVIEW_2026-09-06.md)
contains source-backed recommendations and simulator limitations. [§12](#12-active-user-requests-and-implementation-plan--6-september-2026)
retains the original scope and historical checkpoint details.

**Current checkpoint:** Gemini and cross-page Arabic edits are local and unfinished;
no new Nokia API integration or external call was completed. The 901-test result
predates the latest Arabic changes; 39 focused locale/pilot tests subsequently
passed, but browser verification and a known Ruff cleanup remain. Follow the
runbook's fresh checks rather than treating historical totals as release proof.

**Latest review:** [fixes, verification and hackathon priorities](REVIEW_2026-09-06.md).
886 tests pass. F1/F3 were already implemented in this checkout; F2 is now closed
with idle cleanup, terminal authorization clearing, and a bounded five-minute
phone retention window for continuity-session opt-in. Packaging and polling fixes
are also included. The latest 13-case result is 38/78 calls, five CHALLENGEs and
three authored-expectation disagreements; historical results below remain dated
records. The capability manifest now lives at `app/nac_capabilities.json`.
This handoff replaces the long running
log with current facts and an implementation plan. Read §6 for submission gates,
§7 for the competition feature build order, and §3 for the underlying product
contracts. Before further implementation, read §9 for seven confirmed code-review
fixes and their regression checks. The complete earlier log is preserved
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

### H2a — Live API calls to Nokia's hosted simulator

**Status: NOT STARTED as a newly validated demo.** Historical captures and the
completed local `nac_fake` journey do not establish a fresh Nokia-hosted run.
This is the recommended intermediate integration milestone before physical P4b.

**What it proves:** Isnad sends genuine HTTP requests through Nokia NaC and
processes Nokia's simulated subscriber answers. It exercises the external API
integration; it does not establish facts about a real subscriber. A physical test
SIM is not needed to start hosted simulator checks such as SIM Swap. P4b's handset
requirement applies to physical operator proof, which remains a separate milestone.

| Mode | Execution / answer source | Demonstrated claim |
| --- | --- | --- |
| `mock` | Local fixture provider | Isnad engine and presentation behavior |
| `nac_fake` | Our local fake operator | Local HTTP/OAuth contract and merchant journey |
| `nac` with Nokia simulator identifiers | Nokia-hosted service, synthetic answers | Live API integration with Nokia's simulator |
| `nac` with an authorized supported subscriber | Actual operator path, once validated | Physical subscriber/operator integration |

**Official sources reviewed 6 Sep 2026:** Nokia's
[getting-started guide](https://networkascode.nokia.io/_docs/getting-started)
documents simulator routing with the `+9999` prefix. The
[SIM Swap scenario table](https://networkascode.nokia.io/_docs/sim-swap/sim-swap)
documents `+99999991000` as swapped and `+99999991001` as not swapped. The
[Number Verification V1 guide](https://networkascode.nokia.io/_docs/number-verification/number-verification-v1)
has simulator cases too: those identifiers respectively verify and fail to verify.
Its authorization/callback requirements still need to be exercised against Nokia;
do not substitute the local fake operator or skip OAuth and call it sponsor proof.

1. Confirm the team's Nokia application/test-mode access and required API
   subscriptions. Select the documented simulator identifiers for each API and
   record expected responses before running. H0 still owns confirmation of the
   hackathon's simulator acceptance rules; platform support alone does not settle
   the judging requirements. No real-subscriber lookup is needed for this milestone.
2. Reuse `NacProvider` and the installed SDK in a separate authenticated Isnad
   instance. Set `ISNAD_PROVIDER=nac`, `ISNAD_DEMO_MODE=false`, the server-side
   Nokia API key and a generated merchant key. Preserve a dedicated vault key and
   subject pepper; configure the required registered HTTPS callback. Current
   startup checks require these even for hosted simulator traffic. Do not weaken
   those checks to reuse public demo tokens or print secrets in a runbook/capture.
3. Use an isolated test database and explicit run metadata
   `environment_scope=nokia_hosted_simulator`. Keep that metadata outside signed
   `Verdict`/`EvidenceLink`; source `nac` identifies the adapter, not whether the
   subscriber is simulated. Exclude these runs from real merchant outcome/impact
   reports. A filter excluding only `mock`/`nac_fake` would miss hosted simulations.
4. Start with a bounded SIM Swap match to each documented expected answer using
   the existing `scripts/t1_probe.py`/`t1_capture.py` after reviewing their inputs
   and side effects. Then exercise the authenticated verification API or merchant
   harness and save a persisted signed receipt. Retain one subject throughout each
   investigation; do not mix different simulator numbers' API answers to manufacture
   an ALLOW or reproduce a local Act exactly. Measure the result rather than promise it.
   `t1_probe.py` supports SIM Swap, Device Swap, reachability and roaming, requires
   `ISNAD_T1_ARM`, and appends to `docs/T1_OBSERVATIONS.md`. `t1_capture.py` calls
   `_gather_sync` and then `gather` for the same action, potentially making two SDK
   requests; do not budget it as one call per action or treat both passes as one
   observed response. Prefer the bounded probe initially, or refactor a capture
   helper to normalize the same response once before using it for that claim.
5. For Number Verification, configure the real Nokia client/authorization metadata
   and callback, then use P4a's implemented state/nonce/token-validation flow with
   Nokia's supported simulator setup. Record match, mismatch and failure outcomes
   separately. `CONSENT_REQUIRED`, `PROVIDER_UNAVAILABLE` or a fake-operator success
   is not successful hosted Number Verification. Keep any blocker documented;
   another working hosted API can still demonstrate partial sponsor integration.
6. Capture timestamp, SDK/API version, action, expected versus observed normalized
   answer, measured request duration, actual source, environment scope and receipt
   verification. Keep tokens, codes, raw subject data and credentials out of shared
   artifacts. Use a named case ID in public evidence, with simulator inputs in the
   operator's reproduction manifest. Store the sanitized run pack under
   `docs/nac/hosted_simulator/` (proposed); classify adapter reports accurately.
7. Keep `/judge` clearly mocked: `routes_console.py` constructs `MockProvider`
   explicitly, so a provider environment change alone cannot make its controls
   call Nokia. Use the authenticated harness for the hosted demo and show a separate
   recording/entry point. Strict `nac` provides clearer evidence than `hybrid`, whose
   fallback can substitute local facts. Never present mixed evidence as all-Nokia.

**Acceptance:** at least one fresh successful hosted API response matches its
documented simulator case; an actual Isnad API investigation persists a verifiable
receipt; each demonstrated API has its own evidence/status; simulator provenance
and measured timing are visible; no local fallback is represented as Nokia success.
Number Verification is complete only after its hosted authorization flow succeeds.
Neither this milestone nor its latency measures physical operator performance.

**Approved descriptive wording after the run is verified:**
“Live API integration with Nokia Network as Code, demonstrated against Nokia's
hosted simulator.” Keep the physical handset/operator milestone marked unproven
until P4b independently passes. This documentation edit does not execute any call.

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

**Update — 6 Sep, same day, follow-up session:** at the user's explicit
instruction, overriding this section's own deferral advice above, all
fourteen I-items now have working, tested code — see the "I1–I14
implementation — 6 Sep" entry under §8 for exactly what was built and, for
each item, what was deliberately left out to keep this pass honest. This
does not retroactively make §7 a requirement; the instruction to defer broad
extensions until after submission stands for any future session that has
not been given the same explicit override.

**Concurrent implementation update:** P4a, P3 and P5 are now recorded as DONE
LOCALLY in §3/§8. Where I5/I11/I12 say to implement these dependencies, inspect
and reuse that existing work first; do not recreate its harness, tables, routes
or migrations. The additional competition experiences still require their own
acceptance checks. Local fake-operator results do not complete physical proof P4b.

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

**Hosted simulator guidance — 6 Sep, documentation only:** added H2a at the user's
request, including official simulator identifiers, the strict NaC setup, a bounded
validation sequence, synthetic-run isolation, Number Verification's separate OAuth
proof and accurate judge-facing wording. No provider call or configuration change
was made by this pass; concurrent application edits were preserved.

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

**Validation for this planning pass:** local documentation links/anchors, the
fourteen-item ledger and whitespace checked; graph refreshed and feature headings
queried. P1/P2 archival content was verified against the preserved source. No
application tests were rerun by this documentation pass. Concurrent implementation
records below are preserved and attributed to their own sessions. No model/provider
trial, outreach, deployment, commit or push was performed by the planning pass.

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

**P2 gap closure — 6 Sep, same day, follow-up session:** browser-verified P2's
two recorded gaps at 375px and via keyboard. Found and fixed a real bug: the
receipt's six-column steps table had no scroll container, so it overflowed
its card and stretched the whole page wider than the device viewport (mobile
browsers then grow their own layout viewport to match, clipping the
right-hand columns with no way to reach them) — scoped the scroll to a new
`.table-wrap` so the rest of the page stays fixed at device width. Reviewed
keyboard access: tab order reaches every real control, focus is visibly
indicated everywhere checked, and no `keydown` handler anywhere blocks native
button activation (grep-verified) — found and strengthened one weak focus
indicator (`console.html`'s `.ask input` removed its outline for a 1px
border-color change alone; matched the `:focus-visible` pattern `judge.html`
already uses elsewhere). Real keyboard activation (Enter/Space synthesizing a
click) could not be demonstrated in this session's browser-automation pane —
confirmed as a tool limitation, not an app defect, against a freshly created
vanilla button. Full suite unaffected, Ruff clean.

**I1–I14 implementation — 6 Sep, same day, follow-up session, at the user's
explicit instruction to build all fourteen despite §7's own deferral advice:**
built working, tested code for every I-item, reusing P3/P4a/P5's existing
harness/tables/routes rather than duplicating them per §7's own rule.
Deliberately lighter-weight than P1–P5's own rigor given the combined scope;
each item's own commit states exactly what was and was not built.

- **Shared contract:** `Investigator`/`build_investigator` gained optional
  `planner`/`event_sink` keyword args, defaulting to the existing planner and
  the shared SSE bus — every existing caller unaffected (confirmed by the
  full suite unchanged). `demo/lab/` is the new shared judge-lab package.
- **I1** (`demo/lab/runner.py`, `models.py`): `run_scenario()` produces a
  versioned `LabRun` — fixture/policy digests, code revision, the actual
  decision/evidence/verdict event sequence via an injected per-run sink, no
  `store.save` call. Deterministic under the pinned mock provider + greedy
  planner. `scripts/build_judge_lab.py` generates one artifact per scenario.
  Not built: the full replay UI, a real-model evidence pack, the H1 CLI's
  model-attempt-cap extension.
- **I2** (`demo/lab/compare.py`): the one honestly-supportable "one fact
  changed, rest fixed" variant — removing `claimed_location` on the same
  phone number (so every network signal stays fixed) — reruns through the
  same shared runner and reports `changed`/`no_observed_effect`. Not reused:
  `app/policy/counterfactual.py` (compares pricing, not evidence), per the
  shared contract's own instruction.
- **I3** (`scripts/build_evidence_comparison.py`): loads
  `independent_evaluation.py` and `false_decline_baseline.py` as unmodified
  modules and combines their already-produced results into one report with
  named denominators, a dataset digest and a code revision. No new decision
  logic. No web UI/download-link view.
- **I4** (`demo/lab/faults.py`): `FaultInjectingProvider` wraps a fresh
  provider instance (never shared) and returns a normalized, allowlisted
  EvidenceLink for `timeout`/`unavailable`/`consent_required` profiles, or a
  bounded delay for `delayed` — never raises, since `Investigator._call()`
  has no provider-exception handling. No "Replay recovery" UI.
- **I5:** P3/P4a's existing merchant timeline (CHALLENGE → attempt pending →
  merchant-reported result → separate order decision) already satisfied
  I5's own "implement P4a and P3 exactly once" rule. Added a subscriber-side
  storyboard (why held, required action, expiry, return path) inside the
  existing challenge panel, since there is no separate customer-facing app.
- **I6** (`app/static/i18n/en.json`/`ar.json`, `app/api/routes_i18n.py`):
  locale dictionaries for decision/grade/UI strings behind
  `GET /ui/i18n/{locale}.json`, typed `Literal["en","ar"]` so FastAPI itself
  rejects any other locale before a path ever reaches the filesystem.
  `ar.json` carries its own `review_status: draft` field — no Arabic-speaking
  reviewer was available. Not built: judge.html/receipt.html language
  switching, `lang`/`dir` attributes, `bdi` isolation.
- **I7** (`scripts/verify_receipt.py`): offline Ed25519 verification of a
  downloaded receipt bundle, over the exact stored `signed_payload` string
  (never reparsed/reserialized), with an optional `--trusted-keys` file
  separating "signature valid" from "key trusted". Added `schema_version` to
  the existing `GET /v1/receipts/{chain_id}` response.
- **I8:** the merchant-pilot harness gained a trust session bound to a flow
  (its own stand-in for an order id, since I11's full order-mapping
  subsystem was not built) — release-order re-checks the session's status
  fresh against Isnad on every call, never a stale copy, and a revoked
  session blocks release with 409 while leaving fulfillment HELD.
- **I9** (`demo/lab/challenge.py`): a small versioned `CASES` set built
  entirely on I2's `request_override` and I4's `FaultInjectingProvider`
  through the shared runner; `seeded_order()` gives a reproducible shuffle.
- **I10** (`docs/nac_capabilities.json`, `app/nac_capabilities.py`):
  summarizes H2's own recorded per-action captures into one status manifest;
  `preflight()` answers readiness from local state only, never a provider
  call, mirroring P1's zero-SDK-call missing-claim guarantee. Kept OUT of
  `docs/nac/` itself after it broke `test_nac_contract.py`'s glob over raw
  capture fixtures on first placement.
- **I11:** the merchant-pilot harness already served as the "first reference
  shop" across P4a/P3/P5/I5/I8. Closed the two genuine gaps: an optional
  `claimed_location` on the checkout form (forwarded as a customer/merchant
  CLAIM, never an observed location) and a `SUPPORTED_CURRENCIES={"USD"}`
  guard enforced in the adapter before calling Isnad.
- **I12:** extended P5's existing offline report (not a second one) with
  `manually_accepted_orders` and challenge completion time, plus an optional
  business-impact worksheet that is `None` unless a merchant explicitly
  passes `--review-cost` — report-only, never touching a policy or verdict.
- **I13** (`app/db/proof_shares.py`, migration `0004_proof_shares`): expiring
  reviewer links onto a separately issued, domain-separated attestation
  (`isnad_proof_share_attestation_v1`) recomputed deterministically from an
  immutable row rather than stored twice. Missing/expired/revoked all answer
  with the same 404. Idempotent creation's response is Fernet-encrypted at
  rest (it contains a bearer token), unlike P3/P5's plaintext idempotency
  responses. Not built: `app/static/proof.html`, access-log redaction for
  the token in the URL path (an operational/deployment concern).
- **I14** (`app/db/run_events.py`, migration `0005_run_events`):
  `app.events.emit()` now persists an event before fan-out when it carries a
  `run_id` (most never do), keyed by the unique `(owner, run_id, sequence)`
  constraint racing concurrent writers with a bounded retry — proven not to
  regress the hot path by running the full 740+ test suite unchanged after
  touching it. New `GET /v1/console/runs/{run_id}/events` is a polling
  replay endpoint with an explicit `gap` flag, not a splice of replay into
  the live SSE generator itself.

Test/lint evidence per item is in each item's own commit message. Full suite
661 → 751 passed across the whole sequence (before the §9 review fixes, which
brought it to 759), Ruff clean throughout. See §9 immediately below for
seven real defects a concurrent review found in this same work and their
fixes.

## 9. Sonnet code review — 6 September 2026

**Fix queue: R1 → R5 → R2 → R6 → R3/R4 → R7, before hosted merchant-demo
claims or further feature expansion.** These are confirmed gaps in the reviewed
implementation, not a reversal of the historical local implementation records.
No application code was changed by this review; no push was performed.

**Evidence and scope.** An isolated copy of `95090f1`, including the then-working
Investigator planner/event-sink injection subsequently committed as `2af25b1`,
passed **661 tests**. Seven additional required-behavior probes each failed.
Later judge-lab work (`88cc8c7` and concurrent changes) was outside this snapshot
and is **not approved by this review**. Initial missing-file failures in the
review copy were resolved before the 661-test run; they are not product defects.
The probes are preserved in [review regressions](reviews/sonnet_review_regressions.py).
In an isolated checkout with dev dependencies, copy that file to
`tests/test_review_regressions.py`, then run
`python -m pytest -q tests/test_review_regressions.py`. They use synthetic inputs
and mocked upstream responses, require the existing `tests/conftest.py`, and
intentionally fail on the reviewed code. Keep them outside the normal suite until
implementing the fixes; then integrate them as ordinary regression tests. Adapt
fixture construction when adding ownership fields, without weakening assertions.

### R1 — Bind merchant harness flows to their creating session (high)

**Location:** `demo/merchant_pilot/app.py`: `FlowRecord`, `FlowStore.get`,
`flow_page`, status/challenge/outcome routes. Two valid operator sessions A/B
were created; B could load A's `/flow/{id}` with HTTP 200. Authentication alone
is checked, but flow ownership is not. This violates P4a's session-isolation
contract; it is not evidence of a cross-merchant defect in the core API.

1. Store the creating session identifier server-side on every flow.
2. Centralize an owned-flow lookup and use it for HTML, status, challenge and
   outcome reads/writes, before any upstream request. Never trust a client owner.
3. Return the same 404 for missing and foreign flows. Under the existing contract,
   a new login session must not silently inherit another session's flow.
4. Test A success, B read/write rejection, expired-session rejection and zero
   upstream calls for unauthorized lookups. Make the preserved R1 probe pass.

### R2 — Recover completed verification after a lost response (high)

**Location:** `demo/merchant_pilot/app.py`: `_poll_and_maybe_complete`.
A successful upstream verification followed by a lost response produces
`COMPLETED` with `result=None` on the next poll. The harness only fetches results
for `AUTHORIZED`, so it never retrieves the cached receipt and the UI stops polling.

1. When status is `COMPLETED` and the local result is absent, call the core
   consent `/verify` endpoint to retrieve its existing cached response.
2. Preserve the per-flow concurrency guard. Do not start another investigation
   or create another charge/chain to recover a receipt.
3. Handle transient failures/VERIFYING conflicts as retryable; surface expired
   or missing upstream records explicitly instead of leaving an endless spinner.
4. Test commit-then-lost-response recovery, concurrent polling and cached replay;
   assert one investigation and the original chain. Make R2 pass.

### R3 — Enforce harness flow retention on reads and while idle (medium)

**Location:** `demo/merchant_pilot/app.py`: `FlowStore.add/get/_sweep`.
Sweeping occurs on creation only. A flow older than `FLOW_RETENTION_SECONDS`
was still returned with HTTP 200. Terminal records also retain phone and original
operator authorization URL/QR beyond their useful lifetime.

1. Enforce retention at every owned read/write boundary, with a controllable clock.
2. Add lifespan-managed periodic cleanup so idle processes also discard records.
3. Clear phone/authorization URL/QR once no longer needed by terminal flows;
   retain only explicitly needed result identifiers/data for the bounded TTL.
4. Validate positive bounded retention settings. Test expired reads, idle cleanup,
   terminal data clearing and fresh-flow survival; make R3 pass after R1 fixture updates.

### R4 — Enforce terminal consent retention without new traffic (medium)

**Location:** `app/consent.py`: `owned`, `by_state`, `_sweep`; `app/retention.py`.
A failed consent with a one-second terminal retention was still returned by
`owned` ten seconds later. Lookup expires active consent but does not sweep
terminal retention; the periodic retention service does not purge this store.

1. Apply terminal-retention checks on both consent-ID and state lookups.
2. Expose a lock-safe purge operation and integrate it with lifespan cleanup.
3. Measure retention from `terminal_at`, preserving the promised recovery window;
   remove unnecessary raw request/auth material when safe for the lifecycle.
4. Test lookup-only expiry, zero-traffic cleanup, active expiry and no early
   deletion of newly terminal consent. Make R4 pass.

### R5 — Remove the unvalidated SDK token-exchange branch (high, conditional)

**Location:** `app/providers/nac.py`: `exchange_number_verification_code`.
The optional SDK-method branch passes only code/redirect URI and returns an
access token without binding the expected nonce or invoking shared ID-token
validation. A stub SDK returning only an access token was accepted. The manual
branch does validate; this finding concerns the compatibility branch and does
not establish exploitation with the currently installed SDK.

1. Route supported exchanges through the shared validated full token-response
   path, or disable the compatibility branch unless a pinned SDK contract proves
   signature/issuer/audience and this request's nonce are validated.
2. Never infer validation from a method name or a comment. Ensure the expected
   nonce actually reaches the validator; reject access-token-only responses.
3. Replace existing tests that accept bare SDK tokens. Cover missing/bad nonce,
   missing/invalid ID token and valid exchange on every enabled path.
4. Make R5 pass and rerun existing OIDC/fake-operator tests before H2a. Do not
   mark physical handset validation complete on the basis of simulator tests.

### R6 — Freeze outcome operations for safe retries (high)

**Location:** `demo/merchant_pilot/app.py`: `report_flow_outcome`.
After an upstream write commits but its response is lost, retry creates a new
`occurred_at` with the same idempotency key. The reproduced retry returned 409:
identical key, different body. The initial transport failure also escapes as 500.

1. Persist an in-flight operation in the server-side flow before sending:
   stable operation ID/key and the complete frozen body, including timestamp,
   basis and `supersedes_event_id`.
2. Retry ambiguous failures using that exact key/body. Catch transport errors
   and return a recoverable state rather than an unhandled exception.
3. Serialize/version operations per flow dimension; reconcile the current
   upstream outcome after ambiguous writes. An explicit new correction gets
   a new operation, not an accidental duplicate from a button retry.
4. Preserve the core API's strict fingerprint validation. Test committed/lost
   response, rapid duplicate submissions and intentional corrections. Make R6 pass.

### R7 — Validate flow context before constructing upstream input (medium)

**Location:** `demo/merchant_pilot/app.py`: `NewFlowRequest`, `create_flow`.
An invalid event with negative `account_age_days` returned 500 because constrained
`RequestContext` construction occurs outside the validation error handler.

1. Validate the complete input using the domain's event/age constraints before
   creating a flow or making an upstream request; avoid duplicating looser rules.
2. Handle malformed JSON and validation errors consistently as 400/422; forbid
   unexpected fields where required by the contract.
3. Test invalid event, negative age, wrong types and malformed JSON separately,
   plus a valid request. Assert zero upstream calls on invalid input; make R7 pass.

**Completion gate for the implementing agent:** integrate and extend all seven
probes, run the full suite and Ruff, then browser-check two independent sessions,
receipt recovery and outcome retry behavior. Record actual results and commit
IDs here. Re-review the newer judge lab separately. These findings remain OPEN
until fixes and evidence are recorded; passing the previous suite alone is insufficient.

**Closed — 6 Sep, same day, follow-up session (commit `9498cf9`).** All seven
findings fixed in the order specified (R1 → R5 → R2 → R6 → R3/R4 → R7):

- **R1:** `FlowRecord.owner_session_id` set at creation; every route now goes
  through `FlowStore.get_owned(flow_id, session_id)` instead of a bare
  `flows.get(flow_id)`, returning the same 404 for missing and foreign flows.
  Browser-checked live (not only the integrated probe) against the real
  running merchant-pilot server with two independently logged-in operator
  sessions via separate cookie jars: session A creates a flow and reads it
  (200); session B is refused on both the JSON API and the HTML page (404).
- **R2:** `_poll_and_maybe_complete` now also re-fetches `/verify` when a
  consent reads back COMPLETED with no locally cached result. Isnad's own
  `/verify` returns the cached response for an already-COMPLETED consent
  (`routes_consent.complete_number_verification`) rather than investigating
  again, so recovery can never buy a second chain or charge.
- **R3:** `FlowStore.get_owned` sweeps expired flows on every read, not only
  at creation.
- **R4:** `ConsentStore.owned`/`by_state` apply the terminal-retention check
  inline on every read; `ConsentStore.purge_expired()` is new and wired into
  `retention.purge_once()` so an idle process reclaims these without needing
  new consent-creation traffic to trigger a sweep.
- **R5:** `NacProvider`'s SDK compatibility branch no longer infers id_token
  validation from a method's existence. It now requires an `id_token` in the
  SDK's response and validates it (signature, issuer, audience, and THIS
  request's nonce) through the same shared validator the manual path already
  uses; a bare access-token response is rejected with a clear `RuntimeError`.
  `tests/test_nac_provider.py`'s fixture updated to return a real signed
  id_token, plus a new test proving the bare-token case fails closed.
- **R6:** `report_flow_outcome` freezes the complete operation body
  (including `occurred_at`) before sending, keyed per flow+dimension, so a
  retry of the same logical action reuses the exact frozen request rather
  than generating a fresh timestamp that Isnad's own idempotency fingerprint
  would see as a conflicting reuse of the same key. Transport failures are
  now caught and returned as a recoverable 503 instead of an unhandled 500.
- **R7:** `RequestContext` construction moved inside `create_flow`'s existing
  validation `try`/`except`, so its own constraint failures (invalid event,
  negative `account_age_days`) are a 422 like any other validation error
  instead of an unhandled `ValidationError` escaping as a 500. Malformed JSON
  is now handled explicitly as 400.

All seven of the review's own probes now pass, integrated verbatim (with
`FlowRecord`'s new `owner_session_id` threaded through the fixture, per the
review's own instruction) as `tests/test_review_regressions.py`. Full suite
751 → 759 passed, Ruff clean. The newer judge lab (§7, I1–I14) was not
in scope for this review and is not re-reviewed here.

## 10. Follow-up code review — 6 September 2026

Reviewed through `e6c4e39`, including `9498cf9` review fixes and selected new
judge-lab/share code. `app/static/receipt.html` had an ongoing uncommitted edit;
this review did not modify it or approve its evolving UI. **771 tests passed
(3 deprecation warnings); Ruff passed for app/tests/scripts/demo/lab and the
merchant harness.** All seven original regression tests now pass. However,
§9's broader acceptance criteria are not all satisfied: R2 and R3 remain partial.
This supersedes the blanket “all fixed” interpretation of the implementation
record, while preserving its historical test results. No app changes or push
were made by this follow-up review.

### F1 — Keep polling while a completed receipt is still missing (high; R2)

`demo/merchant_pilot/app.py::_poll_and_maybe_complete` now correctly attempts
cached recovery for COMPLETED. But it sets `flow.status` before that recovery;
if the recovery POST also fails, the API returns COMPLETED with no result.
`demo/merchant_pilot/static/flow.html::poll` then stops on every COMPLETED state,
so the operator must reload manually to recover. The original Python regression
calls the poller twice itself and therefore misses the browser stopping condition.

1. Treat COMPLETED-without-result as still recovering in the browser (or expose
   a separate recovery state); stop only once the receipt is present.
2. Display a retryable recovery message. Explicitly handle a missing/expired
   upstream consent instead of silently preserving an old state indefinitely.
3. Add a browser test: verification commits, response is lost, the first cached
   recovery also fails, the next succeeds. Assert automatic recovery, original
   chain ID and exactly one investigation, without page reload.

### F2 — Finish idle cleanup and terminal data minimization (medium; R3)

`FlowStore.get_owned` now enforces read-time TTL, which fixes the original probe.
However, the harness still creates `FastAPI` without a cleanup lifespan/task;
`_sweep` only runs on add/owned lookup. Idle records remain indefinitely in memory.
`FlowRecord` also retains raw phone, authorization URL and QR after terminal
completion and returns authorization material on status reads.

1. Add a lock-safe public purge method and a bounded lifespan cleanup task;
   cancel and await it on shutdown. Validate the retention interval/settings.
2. Clear authorization URL/QR at terminal transition and remove phone once no
   longer needed. Check I8's trust-session dependencies before removing phone:
   either bind necessary server-side data earlier or explicitly document and
   enforce the smallest required retention window.
3. Test expiry without any new request, terminal material removal, clean shutdown
   and fresh-flow survival using a fake clock. Keep ownership regression coverage.

### F3 — Pin the offline lab's default planner (high; I1/I2/I4/I9)

`demo/lab/runner.py::run_scenario` passes `planner=None` to the investigator;
`Investigator` then calls `get_planner`, which selects LLM whenever global settings
say `llm`. `scripts/build_judge_lab.py` uses `os.environ.setdefault`, so an existing
LLM environment overrides its documented offline/greedy guarantee. Tests pin
settings to greedy, masking this. A no-network probe replacing the global planner
factory with an exception confirmed the offline runner reaches that factory.
With configured credentials this can call a model and invalidate deterministic
comparisons; no real model call was made by this review.

1. Construct a fresh `GreedyPlanner(engine)` inside the lab runner when its
   explicit planner argument is None. Preserve intentional injected planners,
   and label any explicitly supported model-backed mode separately.
2. Do not mutate global settings to enforce isolation. Make the CLI's offline
   guarantee hold even when the surrounding app uses LLM/live configuration.
3. Test with global `settings.planner='llm'`, a fake configured credential and
   model/network entry points replaced by failing spies. Default lab scenarios,
   counterfactuals and fault cases must complete deterministically with zero
   model/network calls. Explicit injection should still work and be labeled.

**Next validation:** fix F1–F3, extend tests beyond the original seven probes,
rerun the suite/Ruff and record evidence here. This was a focused review, not an
exhaustive approval of every I1–I14 feature. Local main server was started in
mock/greedy mode on port 8000; `/judge` returned HTTP 200. No hosted simulator or
physical handset proof was performed.

## 11. UI review and implementation plan — 6 September 2026

**Review method:** opened the actual `/judge` UI, then used a local browser at
1440×1000 and 375×812 to run the replacement scenario through CHALLENGE and open
its signed receipt. Screenshots: [desktop idle](reviews/ui-2026-09-06/desktop-idle.png),
[desktop result](reviews/ui-2026-09-06/desktop-result.png),
[mobile result](reviews/ui-2026-09-06/mobile-result.png).
Receipt UI had concurrent uncommitted changes; findings below describe what was
rendered, not approval of that unfinished change. Merchant and shared-proof UI
recommendations are source-reviewed follow-ups, not claimed browser passes.
This pass changes documentation only. Keep the navy/gold palette and existing
honest provider labels; improve hierarchy, readability and completion first.

**Build order:** U1 → U2 → U3 → U4 → U5 → U6; then U7/U8. Complete §10's
recovery fixes alongside U1/U5. Do not change policy, signed payloads or provider
behavior to make the interface look better.

### U1 — Make the first visit usable, including failure states (P0)

Observed: the server originally ran with demo mode disabled. `/judge` returned
200, showed SERVER MODE UNKNOWN, disabled all three actions and put “Bearer API
key required” near the bottom. This review corrected its own local startup to
mock + greedy + demo mode; that is not a production authentication change.

1. In `app/static/judge.html`, model loading, ready, unavailable and expired-demo
   states explicitly. Put the state beside the primary action with an actionable
   message; reserve raw technical error details for an expandable section.
2. Add a retry/reload action for transient failure or an expired short-lived
   demo credential. Keep investigation actions disabled until readiness succeeds.
3. Document a loopback-only demo startup command using `ISNAD_PROVIDER=mock`,
   `ISNAD_PLANNER=greedy`, `ISNAD_DEMO_MODE=true`. Preserve production auth and
   never make demo mode the global default or embed a merchant key in HTML.
4. Acceptance: fresh demo visit works; demo-off, mode-fetch failure and token
   expiry explain the next step at the button; no silent or unauthorized fallback.

### U2 — Bring the action into the first mobile screen (P1)

Observed: at 375×812, the main button's top was about **891 CSS pixels** from the
page top. The hero, simulator paragraph and repeated customer story delay use.
The desktop empty trace also occupies substantial space before any useful result.

1. In `judge.html`, shorten the hero to “A new SIM. A fairer checkout decision.”
   with one sentence explaining network evidence and a signed merchant decision.
   Keep exact final wording editable, but avoid repeating the story in three places.
2. Reduce mobile hero/card padding; make basket details compact. Put the primary
   scenario action immediately after the short customer story, before optional
   basket detail. Target the full primary button within the first 812px at 375px.
3. Replace the two large secondary scenario buttons with a clearly labeled
   scenario selector or compact secondary controls; preserve keyboard operability
   and the current distinct replacement/clean/unresolved fixtures.
4. Replace the long simulator paragraph with a visible “Simulated network
   evidence” label and a disclosure explaining fixture parity and presentation
   delay. Keep per-evidence provenance, and distinguish mock from hosted simulator.
5. Acceptance: check 375/390/768/1440px, no page overflow, action discoverable
   before scrolling on the target phone; desktop still communicates the problem.

### U3 — Show the decision first, with concise supporting reasons (P1)

Observed: the “plain-language” result is a long paragraph including thresholds,
uncalibrated score, consent caveats and policy mechanics. The action paragraph
adds another large block. The important merchant instruction gets buried.

1. Update `app/presentation.py` and its consumers with a compact summary separate
   from the existing detailed explanation. For this case: “A recent SIM change
   needs a second check. The same handset and matching location support the
   customer.” Action: “Complete merchant verification before proceeding.”
2. Show decision, action and the strongest two supporting/adverse facts before
   the scrolling trace. Preserve unresolved evidence as its own distinct category;
   never imply missing evidence is a failed identity check or an OTP was sent.
3. Put exact thresholds, numeric score and full explanation under “Why this
   decision?” / technical details. Keep a short uncalibrated-score note beside any
   score actually displayed. Do not alter existing signed fields.
4. Use normal sans-serif for the customer-facing headline; reserve monospace for
   identifiers and code. Prevent the left checkout card stretching into a tall
   empty panel merely to match the result column.
5. Acceptance: replacement, clean and unresolved cases each show a correct
   one-sentence result and next action; a reader can identify both in five seconds.
   Retain existing presenter tests and add assertions for the distinct summaries.

### U4 — Repair mobile trace layout and make progress meaningful (P1)

Observed: `.trace-row` uses `24px minmax(0,1fr) auto` while `.trace-meta` forbids
wrapping. On mobile, metadata consumes the row and check names/details collapse
into narrow columns. The page itself fits (375px scroll width), so an overflow
check alone does not catch this. The four unlabeled progress bars also give no
clear relationship to the six checks in this run.

1. Below the mobile breakpoint, use icon + flexible content columns and place
   metadata on a second row under the content. Allow wrapping; apply `min-width:0`.
2. Combine each selection/result pair into one expandable check card, keyed by
   stable event/step identity. Show check name, plain result and provenance first;
   rationale, budget and score remain available in expanded details.
3. Replace the fixed four bars with named lifecycle states (checking, deciding,
   receipt ready) and an actual “N checks completed” count. Do not promise a
   fixed number of calls when the planner can stop early.
4. Auto-scroll only while the user is following the latest item. If they scroll
   back, preserve their position and offer “Jump to latest”. Keep earlier adverse
   evidence easy to find after completion.
5. Acceptance: inspect real rendered rows at 375px, not just document width;
   check names remain readable, all metadata is accessible, replay/reconnect
   does not duplicate cards, and progress reflects the actual lifecycle.

### U5 — Give CHALLENGE a visible continuation (P1)

Observed: the lead story ends with instructions to do merchant verification,
while the visible next interaction is opening a receipt. This makes the product
feel unfinished even though the separate merchant harness implements followup.

1. Add a primary “See merchant verification” continuation beside the result and
   demote receipt/audit actions to secondary prominence. For the judge demo,
   initially use a clearly labeled explanatory panel showing the next workflow.
2. Show pending → merchant-reported passed/failed/abandoned states only when
   backed by the existing challenge API. If integrating the actual harness,
   implement authenticated server-side flow/session transfer first; do not send
   API keys in URLs or assume a judge demo chain belongs to the harness merchant.
3. Reuse P3 followup records without changing the original signed decision.
   Label the outcome “Merchant-reported”; never claim Isnad sent a code.
4. Preserve a safe “Try another scenario” action and receipt access. Resolve
   pending/missing-result recovery per F1 before treating a flow as complete.
5. Acceptance: the lead scenario has an obvious next step; explanatory mock
   states are visibly labeled, and real transitions remain owner-scoped and
   leave the original receipt bytes unchanged.

### U6 — Make receipt verification understandable (P1)

Observed on mobile: the receipt switches to a dense monospace visual style,
leads with a tampering button, shows a long raw timestamp, and displays only the
first columns of a horizontally scrollable table without an obvious scroll cue.
The scoped table overflow fix works; do not undo it.

1. In `app/static/receipt.html`, use the judge palette/typography for framing,
   with a concise decision summary and a separate “Signature valid” result.
   Keep the distinction between valid bytes, trusted signer and true evidence.
2. Make download the primary utility. Move byte tampering into an explicitly
   labeled “Try the integrity check” disclosure; provide a restore-original action.
3. Format visible dates for humans with explicit timezone; keep exact signed
   timestamps in audit details. Formatting must never modify verification bytes.
4. Add a visible horizontal-scroll hint and accessible table-region name, or
   render the same rows as labeled mobile cards. Keep every signal/result/delta
   available. Preserve the arithmetic verifier, public key and signature details.
5. Apply the same framing to `app/static/proof.html`, but label it “Shared
   summary” and keep expiry/revocation separate from signature validity. Never
   portray its separately signed attestation as the original full receipt.
6. Acceptance: valid → tampered-invalid → restored-valid, download byte equality,
   readable timestamps, all six evidence columns reachable by keyboard/touch,
   and expired/missing shared links explain their unavailable state.

### U7 — Make the new features discoverable without crowding checkout (P2)

1. Add a compact “Explore Isnad” area after the result, with receipt verification,
   trust continuity and advanced console links. Show only implemented destinations.
2. Build a `/lab` presentation page only after F3 isolates the offline runner.
   Start with versioned pre-generated artifacts and an authored-case selector;
   show fixture/code/policy identity and simulated provenance. Do not add a
   public arbitrary-provider-call endpoint just for interactive controls.
3. Include comparison, missing-location and outage cases with their stated
   limitations. Do not label authored fixtures as independent validation.
4. Provide return navigation and consistent active-page labels across judge,
   lab, receipt and separately served merchant app. Avoid dead localhost links
   to a merchant server that has not been configured or started.
5. Acceptance: every visible link resolves in the documented demo deployment;
   a judge can discover a comparison without CLI instructions or API credentials.

### U8 — Finish keyboard, motion and language behavior (P1 before submission)

Source review found no live-region or reduced-motion handling in `judge.html`;
this is a follow-up verification requirement, not a claimed screen-reader test.

1. Add visible focus styles for all actions and a polite live region for concise
   progress/result announcements. Do not announce every incoming trace token.
2. Keep keyboard focus stable during updates; focus a summary only following an
   intentional user action. Provide accessible names for scroll/disclosure areas.
3. Respect `prefers-reduced-motion` for animation/scroll transitions while keeping
   loading and completion visible. Use text/icons as well as result colors.
4. Extend the existing locale dictionaries to judge and shared-summary UI only
   with complete reviewed strings; mark incomplete Arabic clearly. Use `lang`,
   `dir` and logical CSS, keeping hashes/IDs in LTR isolation. Translate display
   labels without rewriting signed content or provider provenance.
5. Acceptance: keyboard-only run and receipt visit; screen-reader announcement
   check; 200% zoom; reduced-motion pass; Arabic RTL layout with English fallback
   for missing entries. Target at least 44px primary touch controls and verify
   actual text contrast rather than assuming the palette passes.

**Delivery gate:** implement in small commits by U-item. Record screenshots at
375×812 and 1440×1000 for idle/running/ALLOW/CHALLENGE/unresolved/error states,
run the relevant existing tests and targeted interaction checks, then review the
complete journey. Do not call this plan implemented until those results exist.

## 12. Active user requests and implementation plan — 6 September 2026

**Read this section before continuing implementation.** The user explicitly asked
that every new request and the plan for tackling it be added to the handoff
before further work. This section supersedes earlier recommendations to keep
Gemini optional, defer Arabic beyond labels, or treat swap evidence as necessarily
boolean-only. Earlier implementation/evaluation records remain historical facts.

### Requested outcomes

1. Make **Gemini the primary/default planner**. Use greedy fallback **if and only
   if Gemini does not respond**; do not silently replace a returned answer.
2. Provide **everything that was added and how to test it**, including previously
   implemented features, new fixes, configuration, UI entry points, expected
   outcomes, and limitations.
3. Fix **Arabic everywhere**. The user clarified that the problem affects all
   pages, not just one screen or a single untranslated label.
4. Add **Nokia Network Intelligence / Congestion Insights** and explain its use.
5. Use the user's [NaC getting-started documentation](https://networkascode.nokia.io/docs/getting-started)
   to improve the integration rather than relying on old SDK assumptions.
6. Use **actual SIM/device swap timestamps where available** to improve the
   evidence, explanations, and agent context.
7. Record this entire plan first, preserve existing work, validate the completed
   behavior, update README/current state/testing instructions, and push the
   completed changes to the **private** Isnad remote under the existing request.

### Exact current state at this planning checkpoint

Last completed/pushed review: `167dcd30d98b0c94cafb6c6e33aef5148eaa5cf2` on
`private/main`. Its full suite passed **886 tests**, Ruff and the runtime lock
check. See [the review record](REVIEW_2026-09-06.md) for the delivered fixes.

**Uncommitted work already in progress before the user requested this checkpoint:**

- `app/config.py`: planner default changed to `llm`; planner values restricted
  to `llm` or `greedy`.
- `app/agent/gemini.py`: introduced `GeminiNoResponse` to distinguish missing
  candidate text from explicit refusal/invalid output.
- `app/agent/planner.py`: narrowed fallback to missing client/no answer or
  transport timeout/failure. Invalid responses, invalid actions and the call
  ceiling now yield an explicit stopped selection rather than greedy selection.
- `tests/test_llm_planner.py` and new `tests/test_gemini_primary.py`: updated
  regressions. **17 required-behavior probes failed before the code changes;
  the focused Gemini/planner/adapter set now passes 52 tests.** The full suite
  has not been rerun for this in-progress change; comments/docs still need cleanup.
- `app/static/i18n/en.json` / `ar.json`: drafted a broader UI phrase catalogue.
  **Not wired into all pages and not browser-verified. Arabic is not fixed yet.**
- No Congestion Insights or swap-date integration has been implemented.
- Local configuration was inspected without exposing secrets: planner already
  says `llm`, and a Gemini key is configured. No live model call was made.

Do not discard these changes, mark them complete, or claim new test totals based
on the previous commit. Continue from the actual diff and inspect it first.

### Delivery order and gates

| Order | Package | Current status | Completion gate |
| --- | --- | --- | --- |
| 1 | N1 — Gemini-first selection | IN PROGRESS | Default/config/UI agree; strict fallback regressions and integration tests pass |
| 2 | N2 — Arabic across product pages | CATALOGUE DRAFT ONLY | Real browser passes in Arabic/English, including dynamic results and mobile RTL |
| 3 | N3 — NaC contract audit | INITIAL SOURCE/SDK INSPECTION | Versioned capability matrix and direct SDK contract tests; verified docs links |
| 4 | N4 — Swap timestamps | NOT STARTED | Normalized dates/unknowns, budget correctness, preserved old receipts, English/Arabic display |
| 5 | N5 — Congestion Insights | NOT STARTED | Owner-scoped lifecycle, bounded queries, honest mock/live labels, UI and tests |
| 6 | N6 — Complete feature/testing guide | PLANNED | Every delivered feature has an executable test path and honest status |
| 7 | N7 — Release verification and private push | PLANNED | Full checks, updated records/artifacts, reviewed commit and verified remote HEAD |

N3's contract checks can be read before N1/N2 finish, but do not mix new network
behavior into the application until its contract and tests are understood.
Maintain the guide while delivering each package rather than reconstructing it
from memory at the end. No additional model, quota, or timeout changes are implied.

### N1 — Gemini is primary; greedy only when no answer arrives

**Files:** `app/config.py`, `app/agent/gemini.py`, `app/agent/planner.py`, relevant
investigator/console labels, `.env.example`, README and planner tests.

1. Finish the default change to `llm` and update the normal launch instructions.
   Preserve explicit greedy configuration for offline tests, reproducible
   evaluations and recorded lab artifacts. Distinguish those commands from the
   primary interactive Gemini path.
2. Define the fallback boundary explicitly:
   - Timeout, connection/transport failure, empty candidate/no model answer:
     greedy may choose, with the actual source visible.
   - Missing Gemini credentials: explain unavailability; greedy is the no-model
     path, never label it as a successful Gemini run.
   - Valid action: use it. Valid STOP: honor model stopping subject to unchanged
     policy-required checks.
   - Returned malformed JSON/schema, unavailable/repeated/unknown action,
     provider rejection/refusal: stop model selection with a bounded diagnostic;
     do not substitute greedy and do not execute the invalid action.
   - Call ceiling: stop selection, keep the cap, and explain it. Reaching the cap
     is not a failure to respond and must not trigger greedy fallback.
3. Keep mandatory consent checks, corroboration and evidence-support gates
   enforced and visibly labeled `policy`. They are not planner fallback.
4. Clean up old broad-fallback comments in both adapter and planner. Display-only
   narrative/explanation fallback is a separate contract from evidence selection.
5. Test actual adapter response shapes, timeout/transport exceptions, empty text,
   refusal, 429/4xx/5xx responses, invalid JSON, repeated/overspend choices, STOP,
   missing credentials and call ceiling. Test source labels through a completed
   investigation, not only direct `choose()` calls.
6. Keep model responses out of HTML interpolation, secrets out of prompts/logs,
   and signed planner vocabulary compatible. Record whether a live model test
   actually ran rather than infer it from configuration.

### N2 — Arabic everywhere, including changing state

**Observed cause:** the Arabic dictionary originally covered only a few labels.
Judge sections were hard-coded `lang="en" dir="ltr"`; most page copy and dynamic
results bypassed the dictionary. Console/lab/shared-summary/merchant pages did
not share a complete language control. Merely flipping the root direction cannot
translate or repair these pages.

**Surfaces:** Judge Mode, full console, receipt, shared summary, lab, consent
completion, privacy page, merchant checkout/flow/readiness pages and their login
framing. Operator simulator labels should also be reviewed as part of the local
journey. Machine-facing JSON/OpenAPI field names are not translated API contracts.

1. Extend the single shared locale mechanism and provide consistent visible
   English/Arabic switching, saved preference, and safe English fallback.
   The separately served merchant app must serve its own same-origin locale
   assets, not assume the main server's origin or leak credentials in links.
2. Translate complete static copy, buttons, descriptions, validation/errors,
   empty/loading/recovery states, hints, placeholders and accessible names.
   The current draft phrase catalogue is input material, not completion evidence.
3. Translate dynamic scenario descriptions, deterministic presentation summaries,
   evidence fact labels, verdict explanations where structured facts permit,
   congestion status, timestamps and session/consent/challenge/outcome states.
   Prefer stable keys/structured templates. If using a shared renderer for existing
   text nodes, preserve original text, handle updates without mutation loops,
   and never change form values or use DOM text as application state.
4. Keep original signed enums/identifiers and raw provider facts inspectable.
   Add Arabic glosses beside audit tokens rather than rewriting receipt bytes.
   Do not invent Arabic model explanations or claim arbitrary operator/model
   prose has been translated; explicitly mark remaining English free text.
5. Replace inappropriate forced-English regions with inherited language/direction.
   Use logical spacing/borders/alignment, Arabic-capable system fonts, natural
   Arabic line heights and no Latin letter spacing on Arabic sentences. Isolate
   phone numbers, currency codes, hashes, timestamps and signed tokens LTR.
6. Prevent racing language loads from reverting a newer selection. Locale changes
   must redraw current results without restarting an investigation or losing form
   inputs, focus, receipt bytes, download contents or signature state.
7. Validate English → Arabic → English, persisted preference after navigation,
   missing dictionary/network failure, live trace updates, ALLOW/CHALLENGE/
   unresolved/error screens, 375px/mobile, desktop, 200% zoom and keyboard use.
   Exercise the shared logic, not just source-string assertions; capture real
   browser evidence. Keep the human translation-review status honest.

### N3 — Reconcile the NaC docs with the installed SDK

**User-supplied authenticated API reference:**
[Network as Code API catalog](https://networkascode.nokia.io/network-as-code-network-as-code-default/api/network-as-code).
Authenticated access verified on 6 September 2026 after the user signed in.
The account banner explicitly says **Simulator mode**; live networks require
onboarding/billing. Documentation inspection made no API calls and proves no
operator coverage or entitlement. No credentials are recorded here.

Verified catalog findings:

- SIM Swap is labelled v1.0.0, but generated requests use
  `https://network-as-code.p-eu.apihub.nokia.io/passthrough/camara/v1/sim-swap/sim-swap/v0/retrieve-date`.
  The 200 schema requires `latestSimChange`, a nullable RFC3339 timestamp with a
  timezone. This schema has no monitoring-period field. Preserve unknown dates.
- Congestion Insights is labelled v1.0.0, with create/delete/get/list subscription
  operations and POST `fetch`. The latter targets `/congestion-insights/v0/query`.
  Its schema requires `device`; optional nullable `start`/`end` are date-times.
  Neither supplied means a forecast for the upcoming 15 minutes; only one supplied
  gives a 15-minute window on the corresponding side.
- **Catalog example defect:** the fetch request example contains subscription
  fields (`webhook`, `subscriptionExpireTime`) instead of its query schema.
  Follow the schema and installed SDK, not that example.
- Fetch response is an array with required `timeIntervalStart`, `timeIntervalStop`,
  `congestionLevel` (`Low`, `Medium`, `High`) and optional nullable integer
  `confidenceLevel` in 0–100. Empty example timestamps are placeholders, not data.
- Generated requests use the apihub host with `x-rapidapi-host` set to
  `network-as-code.nokia.rapidapi.com`. Do not blindly replace the installed SDK
  host or infer API versions from the catalog heading.

Device Swap date schema is now verified: `latestDeviceChange` is required and
nullable with a timezone; optional `monitoredPeriod` records supervision days.
Five SDK requests were intercepted locally and matched the catalog paths;
no external call was made. SDK default rapidapi host differs from catalog apihub.

Still to verify: subscription callback and error contracts, consent scopes,
host compatibility in an actual response, and bounded
simulator requests. Successful login is not successful live validation. Public
sources and local SDK inspection below remain supporting evidence.

**Sources already checked:**

- [User-supplied getting-started entry](https://networkascode.nokia.io/docs/getting-started).
  The web reader returned an API Hub shell with no extractable content; use the
  linked official detailed documentation and browser/API definitions as needed.
- [SIM Swap](https://networkascode.nokia.io/_docs/sim-swap/sim-swap).
- [Device Swap](https://networkascode.nokia.io/_docs/device-swap/device-swap).
- [Congestion notifications](https://networkascode.nokia.io/_docs/network-insights/congestion-notifications).
- [Congestion subscription retrieval](https://networkascode.nokia.io/_docs/network-insights/get-congestion).

Initial local SDK inspection confirms `client.sim_swap.retrieve_date`,
`client.device_swap.retrieve_date`, and `client.congestion_insights.query` /
`create_subscription` exist. Some tutorial snippets use older resource names;
verify installed generated request/response models before copying them.

1. Build a concise matrix of the APIs Isnad actually uses: operation/version,
   installed SDK method, request fields, response fields, required authorization,
   simulator support, last observed run and limitations.
2. Audit Number Verification consent/OIDC, location claims, SIM/device swap,
   reachability and roaming against current documented contracts. Fix confirmed
   mismatches with regressions rather than add every advertised API indiscriminately.
3. Update `app/nac_capabilities.json`, provider preflight and runbooks from evidence.
   Entitlement, subscriber coverage, API version and successful live validation are
   different fields; SDK method availability proves none of the latter.
4. Bound request timeouts/retries and preserve provider failure/consent-required
   distinctions. Do not automatically retry billed writes or silently mix mocks
   into a failed live query. Do not assume Number Verification consent grants
   permission for every other API.

### N4 — Use real SIM/device change times

**Confirmed:** Nokia documents separate `retrieve_date` operations. SIM response
uses `latest_sim_change`; Device Swap uses `latest_device_change`. The current
adapter uses `.check(...)` and normalizes the boolean only. The boolean's
`max_age` window is not the event timestamp. Nokia also documents that a retrieved
date may represent activation/first device association, and a null date has
limited semantics. Do not equate every date with a fraudulent replacement.

1. Inspect returned SDK types, timestamp timezone/null behavior and monitored-period
   metadata. Add mocked contract tests for both operations before integrating.
2. Design an optional normalized temporal record: provider-reported change time,
   time retrieved, source/operation, meaning (change-or-activation when ambiguous),
   date availability, and monitoring horizon when actually returned. Distinguish
   no date, unsupported, consent missing, provider failure and malformed time.
3. Reject naive/impossible future dates; preserve timezone-aware UTC instants.
   Derive age relative to the observation/issuance time, not a later replay clock.
   At render time show a human date with explicit timezone plus the exact value
   in audit details. Arabic must use the same instant and meaning.
4. Prefer one date lookup that answers the needed recency question when its
   contract supports that inference; otherwise model boolean check and date
   retrieval as distinct operations. Every extra network call must count against
   a configured cost/call budget. Do not silently double provider spend or apply
   the same adverse evidence weight twice.
5. Add date/age to the normalized planner context where useful and explain
   “reported change/activation at …” versus “change within the last N hours.”
   Do not change fraud weights merely because a timestamp is more precise.
   Any recency-based policy change needs explicit scenarios and remeasured
   decisions/costs, with policy-derived scores still labeled uncalibrated.
6. Add temporal fields compatibly to newly issued evidence/receipts if appropriate.
   Existing stored signed payloads must remain byte-for-byte unchanged and verify
   with existing keys; no reserialization or backfilling invented dates. Keep
   precise timestamps out of shared summaries unless explicitly needed.
7. Mock dates must be deterministic and visibly synthetic. Test boundary hours,
   timezone offsets, null/activation ambiguity, retained-window limits, failures,
   unavailable operations, budget exhaustion, old receipt compatibility, tamper
   detection and English/Arabic presentation.

### N5 — Add Congestion Insights as network-quality context

**Purpose:** Nokia describes congestion information for a device's surrounding
network area, useful for anticipating bandwidth/latency constraints. Isnad can
show network conditions and recommend a lighter or retryable verification flow.
Congestion does not establish fraud, explain every timeout, or prove an OTP delay.
It must not independently raise a fraud score or decline an order.

**Confirmed prerequisites:** official docs require a congestion subscription
before querying/inspecting congestion levels. The installed SDK offers
`query(device=..., start=..., end=...)`; omitted times request an upcoming
15-minute prediction. Inspect exact response level/interval/confidence fields
before designing the normalized schema. Never label a forecast as an observation.

1. Add an owner-scoped network-insights service and request/response schema,
   independent of the fraud-evidence weights. Expose query results, intervals,
   forecast/history basis, source and availability explicitly.
2. Implement required subscription setup/get/delete, bounded TTL and per-owner
   limits. Reuse existing auth, ownership and idempotency conventions. If durable
   subscription ownership needs a migration, inspect the current migration head
   first and allocate one shared revision deliberately.
3. Use a configured server-side HTTPS notification URL/token for live subscriptions;
   do not accept arbitrary callback destinations from an untrusted browser.
   Authenticate notifications, bound payloads, deduplicate event IDs, reject
   foreign/expired subscriptions and prevent stale/out-of-order updates from
   replacing newer conditions. Clean up expiry and deletion.
4. Bound query windows, result sizes, call frequency and concurrency. Require
   configured credentials, supported subscribers and API-specific authorization.
   No subscription/query is created by visiting a page. Unsupported regions and
   absent subscriptions get an actionable unavailable result.
5. Add deterministic mock scenarios for low/high congestion, no data, expired
   subscription and provider failure. Live failure never selects a mock fallback.
6. Add a discoverable, bilingual network-insights panel/page linked from the
   console/judge exploration area. Explain levels and operational suggestions,
   show freshness/forecast interval and mock/live provenance. Preserve the
   original verification verdict and signed chain.
7. Test SDK serialization, subscription ownership, replay/idempotency, notification
   auth/deduplication/order, query limits, cleanup and zero calls before preflight.
   Prove that changing congestion alone does not change fraud verdicts.
   Distinguish local fixture tests from an actually executed Nokia simulator trial.

### N6 — Give the user a complete feature inventory and test guide

Create a linked `docs/TESTING_GUIDE.md` (and add its ignore exception) with a
copy/paste local launch, required processes/ports, exact UI route or API request,
fixture inputs, expected observable output and reset/cleanup steps for each item.
Do not include credentials, real phone numbers, or a stale fixed port assumption.

Inventory to cover, based on existing handoff §7 and delivered code:

- Judge replacement/clean/unresolved cases and console Acts I–IX, including the
  established-customer example and their actual current decisions/grades.
- Gemini selection, no-response fallback, STOP and invalid-response handling;
  deterministic offline mode and honest planner/provenance labels.
- Forward verification, inbound caller/announcement checks, caller velocity,
  idempotent request replay, and owner-scoped trace recovery.
- Evidence receipt verification, deliberate tampering/restoration, exact-byte
  download and offline verifier; shared summary creation, expiry and revocation.
- Local fake operator consent success/denial/expiry and recovery after response
  loss; physical handset proof listed separately as unproven.
- Merchant CHALLENGE follow-up, reported result, order/fraud outcome corrections,
  trust-session revocation and blocked order release, retention and recovery fixes.
- Recorded lab replay, seeded case order, missing-location comparison, injected
  outages, evidence-budget comparison and recorded-artifact drift.
- Arabic switching, dynamic results, RTL layout and language persistence across
  every UI surface, plus remaining untranslated free-text limitations.
- New swap date/recency behavior and Congestion Insights, only once implemented.
- Provider readiness, dependency/runtime/package checks and privacy posture.

For each row distinguish **implemented/tested**, **implemented but not live-validated**,
**in progress**, and **planned**. Include the exact automated test command and a
manual user path. No need for the user to read implementation history to test it.

### N7 — Finish, verify and publish the actual result

1. Run focused failing regressions before each fix, then relevant integration
   checks. Preserve a pre-change receipt for compatibility verification.
2. Run the full `.venv311` suite, Ruff, runtime lock, consent contract, evidence
   pack, fixed evaluation and a standalone wheel smoke after final changes.
   Regenerate affected lab artifacts and document changed costs/outcomes.
3. Exercise the actual browser journey in both languages; record tested sizes,
   states, screenshots and limits. Source-string tests alone do not prove RTL.
4. Update README, CURRENT_STATE, this section's status ledger, capability matrix,
   testing guide and Graphify. Do not present 886 or 52 as the final new test count.
5. Commit coherent reviewed packages and push to `private`, preserving remote
   history. Confirm remote HEAD and report the commit plus testing-guide link.
6. The earlier dependency-inventory audit was blocked by automatic approval
   review. Do not bypass that rejection or claim the advisory check passed;
   it remains a separately disclosed approval requirement.

**Checkpoint rule:** this section is the requested plan, not an implementation
claim. Next work should start at N1's unfinished items and update this ledger as
each package actually passes its completion gate.


### API review checkpoint — user requested before resuming app changes

See [API additions and demo call plan](NAC_DEMO_REVIEW_2026-09-06.md) for ranked
additions, authenticated schema corrections, local SDK checks, six-call initial
simulator matrix, callback lifecycle and the five-minute demo sequence.
No Nokia API calls were executed in this review. App work is paused for this
review; existing Gemini/Arabic edits remain unfinished in the working tree.
Before the latest Arabic edits, full regression suite passed 901 tests. The
latest locale/pilot focused run passed 39 tests; browser coverage is unfinished
and Ruff reported an unused noqa in the pilot locale import. These are checkpoint
results, not final validation of the full requested release.


---

# Session record — 6–7 September 2026 (runbook gates 0 to 9)

Written for someone who has to pick this up cold. It says what was built, what
was actually run, what came back, and what is still broken. Nothing here is
inferred from a configured key, a mock response or an older test result.

Baseline at the start: commit `ac8740a`, 901 tests, one Ruff error.
Head at the time of writing: `af6936b`, **1,187 passed + 1 xfailed**, Ruff clean.

## Commits, in order

| Commit | What it did |
| --- | --- |
| `0127024` | Gemini made primary; Nokia SDK wire contract pinned (gates 4 and 2) |
| `e41419a` | Bounded simulator probe; 11 real hosted observations (gate 3) |
| `0bc026a` | SDK hidden-retry fix; two probe record corrections |
| `2e173cc` | Swap dates as separately priced evidence metadata (gate 5) |
| `4b7aee4` | Congestion Insights as network conditions (gate 6) |
| `8b08411` | Number Recycling (gate 7a) + recorded deferrals for 7b–7d |
| `45fc292` | Bilingual UI fixed and proven in a browser (gate 8) |
| `f2a6e37` | Browser surface matrix and screenshots (gate 9) |
| `af6936b` | P1 fixes for defects this repo's own review found in gate 6 |

## What actually ran against Nokia

**Fifteen authenticated calls to the hosted simulator**, one attempt each
(`timeout_in_seconds=10, max_retries=0`), all on the catalog host
`https://network-as-code.p-eu.apihub.nokia.io`. Sanitized records:
`docs/nac/observations/2026-09-06-hosted-simulator.jsonl`.

| Operation | Device | Result |
| --- | --- | --- |
| `sim_swap_check` | `…1000` / `…1001` | `true` / `false` |
| `device_swap_check` | `…1000` / `…1001` | `true` / `false` |
| `sim_swap_date` | `…1000` | `2026-09-06T19:53:10Z` |
| `device_swap_date` | `…1000` | `2026-08-18T13:26:31Z`, `monitoredPeriod` **absent** |
| `congestion_list` | — | 200, empty collection |
| `forwarding_unconditional` | `…1000` / `…1001` / `…0422` / `…0503` | `true` / `false` / **422** / **503** |
| `number_recycling` | `…1000` ref 2026-01-15 | `true` |
| `number_recycling` | `…1001` ref 2026-01-15 | `false` |
| `number_recycling` | `…1000` ref **2030**-01-15 | **400** |

### Three findings that changed the implementation

1. **The catalog host answers.** That was an open unknown. The SDK default host
   is still untested, so the application default is unchanged.
2. **`…1000`'s device boolean contradicts its device date.** `swapped: true`
   for a 24-hour window beside a date nineteen days old. The simulator's
   boolean is not computed from its date, so Isnad shows both with separate
   provenance, never derives one from the other, and carries an explicit
   `disagrees_with_window` flag. Reproduced offline as a *visibly authored*
   fixture — never presented as an observation.
3. **A future reference date is a 400, not a `false`.** Number Recycling
   therefore refuses an out-of-range date locally instead of paying to be told.

**No Gemini call was made in this session.** No live-network call, no physical
handset, no congestion subscription created, no callback ever delivered.

## What was built

- **Gate 4 — Gemini primary.** `GeminiNoResponse` separates an absent answer
  from a returned one. Missing key, transport failure or an empty candidate
  permits greedy with a bounded reason label; invalid output, an explicit
  rejection, a 4xx/5xx and the call ceiling stop selection instead. Exception
  routing verified by test, not by reading.
- **Gate 2 — contract matrix.** `docs/NAC_CONTRACT_MATRIX.md`, made executable
  by `tests/test_nac_wire_contract.py`, which drives the real SDK through
  `httpx.MockTransport`.
- **Gate 3 — bounded probe.** `scripts/nac_demo_probe.py`: plan by default,
  one operation per `--execute`, `+9999` only, two named hosts, no free
  endpoint override, allowlisted record fields, credentials never in argv.
- **Gate 5 — swap dates.** Optional nested `EvidenceLink.timing`
  (`swap_timing/1`), priced separately in `policy.yaml`, never touching
  `result`, `signal` or `delta_logodds`. Old receipts stay byte-identical.
- **Gate 6 — network conditions.** Owner-scoped `/v1/network-conditions` plus a
  separately authenticated callback. Empty is never Low; missing confidence is
  never 0 or 100; a successful create is never a delivered notification.
- **Gate 7a — Number Recycling.** Merchant-supplied `last_verified_at`,
  choreographed rather than planner-selected, `NUMBER_CONTINUOUS` weighted at
  exactly zero, `NUMBER_RECYCLED` blocking an ALLOW outright.
- **Gates 8–9 — bilingual UI and browser proof.** `tests/browser/`, 61 tests,
  Chromium 151.0.7922.34, 35 screenshots under `docs/ui/release/`.

## What failed, and what came of it

### Defects found in this session's own code

| Found by | Defect | Status |
| --- | --- | --- |
| Asserting SDK behaviour instead of assuming it | network-as-code retries 408/429/500/502/503 **twice** by default. Every provider hiccup was three billed calls while the signed chain claimed one. | **Fixed** — `_bounded()` on every call site |
| Reviewing the probe after the batch | `request_correlator` was generated locally and never sent | **Fixed**; the 2026-09-06 file is annotated, not edited |
| Same | `congestion_list` recorded a device it never used | **Fixed** with a `needs_device` flag |
| Writing browser tests | `window.Isnad` was never defined, so every `window.Isnad ? … : fallback` had silently taken the fallback | **Fixed** |
| Same | Dynamic rows never re-translated: strings resolved once into `textContent` | **Fixed** with `data-i18n` on every generated node |
| A release screenshot | The network-conditions panel was authored against a light ground on a dark page and was close to illegible | **Fixed** |
| The parallel codebase review | Query was not bound to the subscribed device | **Fixed** (R01) |
| Same | A static callback URL could not identify a subscription | **Fixed** (R02) |
| Same | Quota race and no query pacing | **Fixed** (R03) |
| Same | Uncertain creates went terminal and leaked remote state; empty ids became active | **Fixed** (R04) |
| Same | Mock data labelled `hosted_simulator` | **Fixed** (R06) |
| Same | Phone/period/interval validation gaps | **Fixed** (R08) |
| Same | CI installed Playwright but never its Chromium | **Fixed** (R11) |

### Still open

- **`/lab` drags sideways 422px at 375px.** A strict `xfail` in
  `tests/browser/test_surfaces.py`, not a deleted test. Ruled out by
  measurement: the audit table's wrapper is 299px with `overflow-x: auto` and
  `min-width: 0` and scrolls correctly on its own, and a sweep for any element
  wider than the viewport whose ancestors are all `overflow-x: visible` comes
  back empty. Something else contributes to the root's scrollable area.
- **R05, R09, R13** (trust-session TTL, terminal session PII retention,
  durable verification idempotency) are pre-existing and **not fixed here**.
- **R07, R10, R12** (network-condition retention, Docker lab layout,
  unreachable hybrid mode) are **not fixed here**.
- The deterministic explanation paragraph is composed server-side from each
  chain's own numbers and is marked `lang="en"` rather than translated.
- Arabic is a **draft**. `review_status` still says so on the page. No
  automated test may be read as native review.

### Dead ends worth not repeating

- **`pytest-playwright` breaks this suite.** Its `pytest_runtest_call` wrapper
  runs ahead of pytest-asyncio and left 213 coroutine tests unawaited. The
  fixtures are built on the sync API instead.
- **A session-scoped Playwright context also breaks it.** Held open, it leaves a
  running event loop in the thread and every later async test dies with
  "Runner.run() cannot be called from a running event loop". Function-scoped.
- **Browser journeys need their own server.** This build keeps at most 32 live
  demo credentials and a bounded subscriber set; a matrix that renders dozens of
  pages exhausts both, and the next file's journey then fails for reasons that
  have nothing to do with it. The `server` fixture is module-scoped.

## Documented consequences a future run will see

- Pricing the swap date as a second call changed evaluation numbers. The
  takeover fixture now spends **7 on three links** where it spent 8 on four:
  the same decision on less corroboration. That is a real trade, not a saving,
  and both numbers are pinned in `tests/test_swap_timestamps.py`.
- `ISNAD_NAC_CONGESTION_CALLBACK_URL` was renamed
  **`ISNAD_NAC_CONGESTION_CALLBACK_BASE_URL`** and its meaning changed: it is a
  base, and the subscription id is appended.
- `EvidenceLink` gained `timing`; `Verdict` serialization therefore contains
  `"timing": null` on links without it. Historical `verdict_json` bytes are
  untouched and still verify.

## Exact commands

```sh
export ISNAD_PROVIDER=mock ISNAD_PLANNER=greedy ISNAD_GEMINI_API_KEY=
.venv311/bin/python -m pytest -q                 # 1187 passed, 1 xfailed
.venv311/bin/python -m ruff check app tests scripts demo
.venv311/bin/python scripts/verify_runtime_lock.py
.venv311/bin/python -m playwright install chromium   # once, for tests/browser
.venv311/bin/python scripts/nac_demo_probe.py        # plan only, zero requests
```

`make lint` is still **not run**: it invokes the dependency audit, and the
earlier rejection of sending the dependency inventory to PyPI stands. Report it
as unperformed.
