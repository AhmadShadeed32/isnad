# Isnad implementation progress ledger

Started 6 September 2026 against `docs/EXECUTION_RUNBOOK.md`.
Baseline commit at start: `ac8740a`. Working tree carried unfinished Gemini,
`.env.example`/README, i18n dictionary and shared-locale changes; those are being
finished here, not replaced.

Status vocabulary: NOT STARTED / IN PROGRESS / PASSED / EXTERNAL LIMIT.
Nothing in this file may be marked PASSED on the strength of a configured key,
a mock response or a dated test count.

| Step | Status | Files/commit | Test command and result | Browser/API evidence | Remaining issue |
| --- | --- | --- | --- | --- | --- |
| 0 Starting point | PASSED | `docs/IMPLEMENTATION_PROGRESS.md`, `.gitignore` | n/a | `git status`/`git log`/`git remote` inspected 2026-09-06; graphify query run | `docs/*.md` is gitignored; added `!` exceptions for the runbook, NaC review, this ledger and the testing guide |
| 1 Baseline freeze | PASSED | none (read-only) | Re-verified on the current tree 2026-09-06: `pytest -q` → **909 passed, 3 warnings, 20.6 s**; `ruff check app tests scripts demo` → **All checks passed** (the RUF100 `noqa` was removed with the pilot locale import); `verify_runtime_lock.py` → 38 exact pins OK | `scripts/evidence_pack.py` written to an isolated scratchpad dir; one exact signed payload/signature/public key preserved as `tests/fixtures/legacy_receipt_pre_swap_dates.json` | Dependency audit (`make lint`) deliberately **not run** — the earlier PyPI-inventory rejection stands. Report as unperformed. |
| 2 Nokia contract matrix | PASSED | `docs/NAC_CONTRACT_MATRIX.md` (new), `docs/NAC_SDK_CONTRACTS.json`, `scripts/export_nac_contracts.py`, `tests/test_nac_wire_contract.py` (new), `.gitignore` | `pytest -q tests/test_nac_wire_contract.py` → **19 passed, 0.14 s** (2026-09-06); `ruff check app tests scripts demo` → clean | Wire assertions drive the real `NetworkAsCodeApi` through `httpx.MockTransport`, not an imitation of our adapter: paths, bodies, `subscription_id`/`started_at`, nullable dates, `monitoredPeriod`, null confidence, unconstrained level vocabulary, `x-rapidapi-*` headers on the catalog host, and one attempt under `max_retries=0`. Zero external requests | Every row's "Last observation" for the new operations is **none** — entitlement and host compatibility stay unknown until gate 3 |
| 3 Bounded simulator probe | PASSED (congestion lifecycle EXTERNAL LIMIT) | `scripts/nac_demo_probe.py`, `tests/test_nac_demo_probe.py`, `app/config.py` (callback settings), `docs/nac/observations/` | `pytest -q tests/test_nac_demo_probe.py` → **38 passed, 0.17 s** (2026-09-06); ruff clean | **11 real authenticated calls** to the hosted simulator, one attempt each, catalog host, sanitized records in `docs/nac/observations/2026-09-06-hosted-simulator.jsonl`. Six planned swap calls + `congestion_list` + four call-forwarding calls incl. documented 422/503 | Congestion **create/get/query/delete and callback delivery were not attempted**: no reachable HTTPS callback is configured, and the probe refuses to point an operator at an unowned destination. `…1000`'s 24-hour device boolean contradicts its 19-day-old device date — recorded, and gate 5 must not merge them |
| 4 Gemini-first selection | PASSED | `app/config.py`, `app/agent/gemini.py`, `app/agent/planner.py`, `tests/test_gemini_primary.py`, `tests/test_llm_planner.py`, `.env.example`, `README.md` | Runbook gate-4 line (`test_gemini_primary test_gemini test_llm_planner test_allow_evidence_gate test_hypothesis_relevance test_t4_ask_the_agent`) → **88 passed, 0.82 s** (2026-09-06) | Exception routing verified by test, not by reading: `httpx.TimeoutException`/`ConnectError` ⊂ `TransportError` → greedy with `NO_ANSWER_TRANSPORT`; `HTTPStatusError` (429/4xx/5xx), `JSONDecodeError`, schema failure, `blockReason`, non-STOP `finishReason` → stop, source `llm`. Alternate greedy paths audited: only `investigator._choreography`, labelled `policy`. Model prose rendered by `textContent` in `console.html:addRow` and `judge.html:appendTrace` | Gate 11.2 later spent this for real: 2 live calls, both labelled `llm`, no fallback — `docs/nac/observations/2026-09-07-gemini-rehearsal.json` |
| 5 Swap timestamps | PASSED | `app/chain/models.py` (`EvidenceTiming`), `app/providers/timing.py` (new), `nac.py`, `mock.py`, `hybrid.py`, `base.py`, `app/agent/investigator.py`, `app/policy/policy.yaml`, `app/policy/engine.py`, `app/static/{judge,console}.html`, `app/static/i18n{.js,/en.json,/ar.json}`, `tests/test_swap_timestamps.py` (new, 37) | `pytest -q` → **1012 passed, 20.1 s** (2026-09-06); ruff clean | Legacy receipt verifies byte-for-byte against its own recorded key; a new receipt's `provider_time` and `disagrees_with_window` are inside the signature (tamper tests); the authored fixture reproduces the hosted contradiction | Documented cost delta: pricing the date as a second call changes evaluation numbers — the takeover fixture now spends 7 on three links instead of 8 on four. Gate 13 must record the difference rather than retune it |
| 6 Congestion Insights | PASSED offline; hosted lifecycle **EXTERNAL LIMIT** | `app/network_conditions.py`, `app/api/routes_network_conditions.py`, `app/db/models.py`, `migrations/versions/0006_network_conditions.py`, `app/domain/schemas.py`, `app/config.py`, `app/providers/{nac,mock}.py`, `app/static/judge.html`, `app/static/i18n/*`, `tests/test_network_conditions.py` (new, 60) | `pytest -q` → **1072 passed, 20.5 s** (2026-09-06); ruff clean | Two-owner isolation on every operation, forged/missing/cross-subscription callback tokens, duplicate and out-of-order events, bounded event storage, provider denial, empty result, unknown confidence, expiry without a worker, idempotent delete, surfaced cleanup failure, and zero provider calls on verify/page-load/locale-change | **No hosted create/get/query/delete and no callback delivery.** No reachable HTTPS callback is configured, so `nac_congestion_callback_url` is empty and creation is refused by design. `congestion_list` on 2026-09-06 returned 200 with an empty collection: the account can read, and nothing is leaked |
| 7a Number Recycling | PASSED | `app/domain/{enums,schemas}.py`, `app/providers/{nac,mock,vocabulary}.py`, `app/policy/policy.yaml`, `app/agent/{planner,investigator}.py`, `docs/nac/number_recycling.json`, `tests/test_number_recycling.py` (new, 26) | `pytest -q` → **1102 passed, 21.5 s** (2026-09-06); ruff clean | **Three more hosted calls**: `…1000`+2026-01-15 → recycled `true`; `…1001` → `false`; a **future** reference date → **400**, which is why an out-of-range date is refused locally | Merchant must supply `context.last_verified_at`; there is no backfill for merchants that do not hold one |
| 7b Network SIM Swap subscriptions | **DEFERRED, recorded** | none | n/a | SDK 10.0.0 exposes no `sim_swap_subscriptions` resource (verified against the exported operation list); the catalog lists v0.3.0 but catalog visibility is not entitlement | Needs a narrowly scoped REST adapter or a justified SDK upgrade **and** a reachable callback — the same missing prerequisite as gate 6. The existing local simulation control stays, clearly labelled |
| 7c Consent Info | **DEFERRED, recorded** | none | n/a | Contract pinned in `tests/test_nac_wire_contract.py` (v0.1 path, scopes/purpose/requestCaptureUrl); **never called** | Deferred because it reports status and may hand back an operator capture URL — a redirect-ownership surface that needs its own state/replay protection, and no product path needs it before the required gates |
| 7d Forwarding and tenure | **DEFERRED, recorded** | none | Call forwarding was **observed** (gate 3: active/inactive plus documented 422 and 503) | Contract and hosted behaviour known | No demonstrated product path. Forwarding is voice-only and not fraud by itself; tenure is not merchant history. Implementing either without a path would be an untested array of checks |
| 8 Arabic + English | PASSED, with two recorded limits | `app/static/i18n.js`, `app/static/i18n/{en,ar}.json`, `app/static/judge.html`, `tests/browser/` (new), `tests/test_i18n.py`, `requirements-dev.txt` | `pytest -q` → **1118 passed, 39.2 s** (2026-09-07), browser tests included in that single command, **0 skipped**; ruff clean | Chromium 151.0.7922.34 driving a real uvicorn instance: rapid switching, dynamic results, aborted dictionary, stored preference, input/focus preservation, byte-identical signed payload, zero `/v1/` calls on a switch, no console errors | The deterministic explanation paragraph is composed server-side from this chain's numbers and is **marked English, not translated**. CAMARA API names stay English by choice. Arabic remains **draft, human review pending** |
| 9 UI verification | PASSED; the `/lab` xfail is now fixed (R15) | `tests/browser/test_surfaces.py`, `tests/browser/test_journeys.py`, `docs/ui/release/` (35 screenshots), `app/static/lab.html` | `pytest -q` → **1187 passed, 1 xfailed** (2026-09-07) | Chromium 151.0.7922.34. Judge/console/lab/privacy/consent-landing at 375 and 1440 in EN and AR; three judge cases; receipt valid and unavailable; network-conditions subscribe→read→delete; console run. Contrast measured against each element's own backdrop; accessible names and focus ring asserted per surface | The `/lab` overflow is **fixed** and the strict xfail removed; the browser suite is 61 passed, 0 xfailed. **Not visited:** 200% zoom, the merchant/fake-operator three-service journey, shared proof page states. 320px and tablet are covered for `/lab` by the R15 verification |
| 10 Core re-audit | PASSED | `app/network_conditions.py`, `app/db/models.py`, `app/domain/schemas.py`, `migrations/0006`, `.github/workflows/ci.yml`, `pyproject.toml` | `pytest -q` → **1187 passed, 1 xfailed**; ruff clean | Seven defects this session introduced were found and fixed (SDK hidden retries, probe record honesty ×2, `window.Isnad`, dynamic re-translation, panel contrast) plus six from the parallel review (R01–R04, R06, R08, R11) | **All closed** in the 7 September defect-clearing session: R05, R07, R09, R10, R12, R13, plus R14 and R16 which were still open, and R15. R10's file layout is fixed but the **image was never built** — no Docker daemon — so its acceptance run is outstanding |
| 11 Demo rehearsal | PARTIAL | `docs/nac/observations/2026-09-07-gemini-rehearsal.json` | Mock/greedy journeys rehearsed through the browser suite and the installed wheel; **11.2 spent** — one bounded run, `gemini-3.6-flash` over mock network data, **2 selection calls against a cap of 6**, both `planner="llm"`, no fallback, 4.1 s, DECLINE/REFUTED | Local deterministic journeys, the hosted swap/recycling/forwarding observations, the Gemini run and the wheel smoke are four separate records and are not merged. The Gemini run used the **mock** provider: no operator was called by it | **Not done:** the hosted congestion lifecycle (no reachable callback) and the handset trial (needs onboarding). Both are external limits, not choices |
| 12 Testing guide | PASSED (README rewritten separately) | `docs/TESTING_GUIDE.md` (new) | Every `-k` selector in the guide was run to confirm it selects the tests it claims | One row per feature with a status that must be read literally, including **Built, never called** for congestion callbacks and Number Verification (the Gemini row moved to **Works, one observed run** after 11.2 was spent) | The README rewrite in this working tree is a parallel reviewer's work, not this session's |
| 13 Final offline release gate | PASSED, with the dependency audit unperformed | `scripts/independent_evaluation.py`, `docs/INDEPENDENT_EVALUATION.md`, `demo/lab/artifacts/bundle.json` | `pytest -q` → **1187 passed, 1 xfailed, 99.7 s**; `ruff` clean; `verify_runtime_lock.py` → 38 exact pins | Evidence pack: 5 scenarios, all signatures valid and trusted. Legacy receipt verifies byte-for-byte. Wheel built, installed into a clean 3.11 venv and launched outside the repo: `/judge`, `/console`, `/lab`, `/privacy`, `/ui/i18n.js`, `/ui/i18n/ar.json`, `/readyz`, `/lab/bundle.json`, `/consent/complete` all 200, and a real verification returned DECLINE with swap-date timing and the disagreement flag. `graphify update .` run | **`make lint` not run** — the PyPI dependency-inventory rejection stands. The wheel needs `ISNAD_VAULT_TRUSTED_PUBLIC_KEYS` pinned or startup fails closed on the signed registry (correct behaviour, now documented) |
| 14 Commit and private push | PASSED | 13 commits, `ac8740a..b45d25f` | Pre-push: `pytest -q` **1187 passed, 1 xfailed**; ruff clean; `test_s14_no_tracked_secrets` passed; `git diff --check` clean | `git push private main` → `ac8740a..b45d25f`. Verified: local HEAD and `git ls-remote private refs/heads/main` are both `b45d25f134a497c709adbe053647add6c7ecc6b9`. No `.env`, database, key or credential file is in the diff | The remote had not moved since `ac8740a`, so nothing needed integrating |
| 15 Handover | PASSED | `docs/PHASE2_HANDOFF.md` (session record), `docs/TESTING_GUIDE.md`, this ledger | n/a | Commit/remote, what changed and why, actual results, tested browser states, actual hosted calls, startup commands and material limitations are all written down | — |

## Checkpoint log

### 2026-09-06 — gate 0/1 complete

Finished: repository state inspected; ledger created; `.gitignore` exceptions added so
the runbook, NaC review, this ledger and the coming testing guide can actually be
committed; full baseline recorded (901 tests pass, one known Ruff error, runtime lock
clean); an exact pre-change signed receipt preserved for gate 5's compatibility test.

Mocked only: nothing yet.

Actually called: no external Nokia or model request. `ISNAD_PROVIDER=mock`,
`ISNAD_PLANNER=greedy`, `ISNAD_GEMINI_API_KEY=` exported for every script run.

Superseded — see the gate 4 checkpoint below. Original next action: finish gate 4 (`app/agent/planner.py` fallback labelling and lint),
then gate 2's contract matrix.

### 2026-09-06 — gate 4 complete

Finished: Gemini is the configured default (`planner: Literal["llm","greedy"] = "llm"`);
`GeminiNoResponse` separates an absent answer from a returned rejection; `LLMPlanner`
routes each condition of the runbook's table to the required behaviour; the no-answer
rationale carries a bounded reason so an offline greedy run cannot be confused with a
Gemini run that fell back; integration tests drive real investigations through
`/v1/verify` for the answered, STOP, invalid-output, transport-failure and
policy-required cases.

Mocked only: every Gemini exchange in these tests is a stubbed client or a patched
`httpx.post`. No model request left this machine.

Actually called: nothing external. Baseline re-run under
`ISNAD_PROVIDER=mock ISNAD_PLANNER=greedy ISNAD_GEMINI_API_KEY=`.

Superseded by the gate 2/3 checkpoint below.

### 2026-09-06 — gates 2 and 3 complete

Finished: `docs/NAC_CONTRACT_MATRIX.md` reconciles the installed SDK's request AST
with the authenticated catalog and now carries real "last observation" values;
`tests/test_nac_wire_contract.py` (19) makes those claims executable against the
real SDK through `httpx.MockTransport`; `scripts/nac_demo_probe.py` is the bounded
runner the review asked for, with `tests/test_nac_demo_probe.py` (38) covering
dry-run, every refusal path, sanitized errors, null/malformed data, one-attempt
retry behaviour and record appending.

Mocked only: everything in both test files. No test makes an external request.

Actually called: **eleven** authenticated requests to Nokia's hosted simulator on
2026-09-06, listed and sanitized in `docs/nac/observations/`. Each was one attempt
with `timeout_in_seconds=10, max_retries=0`. Nothing was created; `congestion_list`
returned an empty collection, so no subscription is outstanding and none needs
cleanup. No live-network call, no model call.

Findings that change later gates:
1. The catalog host answers — one unknown resolved.
2. `…1000`'s device boolean (24 h, true) contradicts its device date (2026-08-18).
   Gate 5 must present the two as separate observations and never derive one from
   the other.
3. The SIM date is generated relative to the request, so no fixed date may be
   quoted anywhere as the simulator's value.
4. `monitoredPeriod` was absent, so the device-date horizon is unknown.

Superseded by the gate 5 checkpoint below.

### 2026-09-06 — gate 5 complete

Decision, recorded because the runbook asked for it before any field was added:
temporal metadata lives in an **optional nested `EvidenceLink.timing`** carrying
`schema_version: "swap_timing/1"`, not in new top-level link fields. The signed
bytes are `Verdict.model_dump_json()` stored verbatim and served back for
verification, so an additive optional field leaves every historical
`verdict_json` byte-identical while new receipts commit to the metadata inside
the same signature. Signing behaviour is unchanged.

Also decided: **no new `Action`.** A date is an enrichment of a link that already
ran, not evidence the planner may choose — giving it an action would have pulled
it into affordability, hypothesis relevance and chain grading. It is priced
separately in `policy.yaml` under `enrichments.swap_date` (cost 1, no gain), and
the investigator charges it at each of the four sites where budget is accounted.

Preserved: the boolean's `result`, `signal` and `delta_logodds` are untouched by
the date. A failed, denied, timed-out or unaffordable date leaves the check
exactly as it was and says which of those happened.

Mocked only: every provider exchange in the tests. `MockProvider.enrich_timing`
is an authored fixture — including the number that reproduces the hosted
`swapped: true` / 19-day-old-date contradiction, which is never presented as an
observation.

Actually called: nothing external in this gate.

Superseded by the gate 6 checkpoint below.

### 2026-09-06 — gate 6 complete offline; hosted lifecycle is an external limit

Finished: owner-scoped `/v1/network-conditions` create/get/query/delete plus a
separately authenticated public callback; two new tables with an Alembic
migration; finite limits for TTL, active count per owner and per device, query
window, event age and stored events per subscription; and a judge-page panel that
renders level, mode, period, confidence-or-unknown, updated-at, provenance and a
retry that preserves the page.

The three refusals the whole feature rests on are tested rather than commented:
an empty interval list is `unknown` and not `Low`; a missing confidence stays
`None` and never becomes 0 or 100; a successful create is never presented as a
delivered notification. Congestion reaches no belief, no score and no signed
chain — asserted by running a verification and checking the provider was not
called at all.

Mocked only: every provider exchange. `MockProvider.query_congestion` is an
authored operator, including a number that returns nothing and one that returns
a level with no confidence.

Actually called: nothing external in this gate. The only hosted congestion
observation remains `congestion_list` → 200, empty, from gate 3.

External limit, stated plainly: **no subscription has ever been created at the
operator, and no callback has ever been delivered.** That needs a reachable
HTTPS endpoint this project owns; until one exists the probe and the API both
refuse to point an operator at an unowned destination, which is the correct
behaviour rather than a gap to work around.

Superseded by the gate 8 checkpoint below.

### 2026-09-07 — gate 8 complete, with limits stated

Three real defects were found by writing the browser tests, not by reading:

1. **`window.Isnad` was never defined.** `const Isnad = (...)()` in a classic
   script makes a lexical binding, not a window property, so every
   feature-detecting caller (`window.Isnad ? … : fallback`) had been taking the
   fallback branch silently. Now assigned explicitly.
2. **Dynamic rows never re-translated.** The swap-date and network-condition
   renderers resolved their strings once at insertion time into `textContent`,
   and those keys live in the `ui` catalog the exact-text observer does not walk
   — so switching to Arabic after a result rendered left the result English.
   Every such node now carries `data-i18n` and is re-applied by `setLocale`.
3. **The network-conditions panel was authored against a light ground** on a
   dark page and was close to illegible. Caught by the release screenshot; it
   uses the page's own tokens now.

Also: the mutation observer re-walked the whole body per mutation (quadratic on
a long console trace) and is coalesced to one pass per frame; evidence sentences
are keyed on the **signal** rather than on the sentence, because the English
detail interpolates a policy window; and the English dictionary values for the
decision title and next action are asserted equal to `app/presentation.py`'s own
copy, so the screen cannot say something the API did not.

Tooling decision: `pytest-playwright` is **not** used. Its `pytest_runtest_call`
wrapper runs ahead of pytest-asyncio and left 213 coroutine tests unawaited. The
browser fixtures are built on the sync API instead, and the Playwright context is
function-scoped — held open across the session it leaves a running event loop in
the thread and every later async test dies. The cost is about a second per
browser test; the benefit is that `pytest -q` remains one command.

Two limits, recorded rather than papered over:
- the deterministic explanation paragraph is generated server-side from this
  chain's own numbers and thresholds, so there is no fixed sentence to key. It
  is marked `lang="en"` rather than left looking like a missing translation.
- Arabic is a **draft**. `review_status` still says so in the page banner, and
  no automated test may be read as native review.

Next action: gate 9 — extend the browser matrix past `/judge` (console, receipt,
proof, privacy, merchant journey), and record honestly which states were visited
by automation, which by hand and which not at all.

### 2026-09-07 — gates 9 and 10, and a review of this session's own work

A parallel codebase review landed in `docs/PHASE2_HANDOFF.md` and found five P1
defects in the network-conditions feature added earlier the same day. They were
real, and they are fixed here with tests that assert the **provider was not
called** — "it now returns an error" is not the same as "it no longer spends
money". See the commit `af6936b` message and the handoff's R01–R13 list.

The full session record — every commit, all fourteen hosted calls and what came
back, every defect found and by what, the dead ends, and what is still open —
is appended to `docs/PHASE2_HANDOFF.md` under "Session record — 6–7 September
2026".

Mocked only: every provider and model exchange in the test suite.

Actually called: nothing external since the fourteen hosted simulator calls
recorded in `docs/nac/observations/`. Still no Gemini call, no live network, no
congestion subscription, no callback delivery.

Next action: gate 12 — write `docs/TESTING_GUIDE.md` with one row per feature
(status, setup, user action, expected result, test command, actual evidence,
known limits), then gate 13's release checks, then the private push.

### 2026-09-07 — gates 12 and 13

A correction that changes a headline number. `scripts/independent_evaluation.py`
counted **evidence links**, not provider operations, so it reported 34 calls
where 49 were actually made: a swap date is a second billable call that adds no
link. Counting both, Isnad spends **49 versus 78** — a 37% saving, not 56% — and
15 of the 49 buy explanation rather than evidence. The evaluator now reports
`enrichment_calls` per case and `docs/INDEPENDENT_EVALUATION.md` is corrected.

The same change moved the other figures honestly: automatic decisions fell from
8/13 to 7/13 and authored disagreements rose from three to four, because a unit
spent on a date is a unit not available for another check. Neither the fixture
labels nor the policy weights were touched to recover the old numbers.

Lab artifacts were regenerated to a review location and diffed before replacing
the committed bundle. The only change is the new `enrichment` event type in
every case. The bundle records `dirty: true`, which is true.

Wheel smoke found one real deployment fact: a fresh install fails closed on the
signed registry unless `ISNAD_VAULT_TRUSTED_PUBLIC_KEYS` pins the shipped
public key. That is the guard working, and it is now written down.

Actually called: nothing external. Still no Gemini request, no live network, no
congestion subscription, no callback delivery.

Next action: gate 14 — stage the reviewed files, commit, push to `private`, and
compare local HEAD with `git ls-remote private refs/heads/main`.

### 2026-09-07 — gate 14: pushed

`git push private main` moved `AhmadShadeed32/isnad-private` from `ac8740a` to
**`b45d25f`**, thirteen commits. Local HEAD and `git ls-remote private
refs/heads/main` agree. The remote had not moved since the baseline, so nothing
needed integrating and no force was involved.

Checked before pushing: full suite (1187 passed, 1 xfailed), Ruff, the
no-tracked-secrets test, `git diff --check`, and a name sweep of the diff for
`.env`, database, key and credential files. None present.

Still outstanding, and stated in the handoff rather than implied away: gate 11.2
(one bounded Gemini run over mock network data) was not spent; the hosted
congestion lifecycle needs a reachable HTTPS callback that does not exist; the
handset trial needs onboarding; and R05, R07, R09, R10, R12, R13 plus the `/lab`
mobile overflow remain open.

### 2026-09-07 — gate 11.2 spent, and two corrections

**Gemini was called for real.** One bounded in-process run, `ISNAD_PROVIDER=mock
ISNAD_PLANNER=llm`, against `gemini-3.6-flash`: **2 selection calls** against a
cap of 6, 4.1 s wall clock, verdict DECLINE / REFUTED. Both selections came back
`planner="llm"` with the model's own rationales — the second one refers to the
first result — so no greedy or policy fallback fired and no `NO_ANSWER` label
appeared. The provider was the mock, so **no operator was called** by this run.
Sanitized record: `docs/nac/observations/2026-09-07-gemini-rehearsal.json`.

What this does and does not establish: the live request/response contract works
on one fixture, in one request shape. The fallback reason labels, degraded-model
behaviour and the call ceiling have still only ever run against stubs. Gate 11
stays **PARTIAL** — the congestion lifecycle and the handset trial remain
externally blocked.

**Correction — fourteen hosted calls, not fifteen.** `wc -l` on
`docs/nac/observations/2026-09-06-hosted-simulator.jsonl` is 14: 6 swap, 1
`congestion_list`, 4 forwarding, 3 recycling. The observations README was
right; the handoff's session record and this ledger's gate 9/10 note said
fifteen. Both fixed. The commit message that carried the wrong number stands as
written — a wrong count is not worth a rewritten history, and this entry is the
correction of record.

**Correction — the browser-journey failure was never diagnosed.** The handoff
stated the demo-token cap and subscriber eviction as the cause. A module-scoped
`server` fixture does fix it reliably, but resetting the token budget alone did
not, so the cause is **not isolated**. Recorded now as a working remedy with an
unconfirmed explanation, to the same standard as the `/lab` overflow xfail.

Actually called since gate 14: 2 Gemini requests. Nothing else — no operator
call, no live network, no congestion subscription, no callback delivery.

### 2026-09-07 — the defect-clearing session: R05, R07, R09, R10, R12–R16

Every open review item is now closed. Nine commits, one per item, each with the
handoff's own acceptance criteria as its tests.

| Item | Closed by |
| --- | --- |
| R05 / R09 | `e00cb7d` — expiry derived from the clock on every read and before every provider call; sleep bounded by the remaining TTL; one idempotent terminal transition; the raw phone cleared at that transition and the record swept on retention's own timer |
| R13 / R14 | `a87a7fd` — a durable reservation row committed in the same transaction as the signed chain; uncertain work refused rather than repeated; a cache backend that cannot be built refuses to start, and its calls are bounded and off the event loop |
| R07 | `290b88e` — expiry settled, then bounded sweeps of subscriptions and their events; `unknown` never swept; the quota check moved onto a new index |
| R12 | `7672b48` — selective-live hybrid retired in one place with one reason, plus a configuration matrix |
| R10 | `b614d29` — `demo/lab` shipped in the image; signing posture written down |
| R15 | `b5400ce` — `/lab`'s sideways drag fixed; the strict xfail removed |
| R16 | `6beae9e` — evidence and enrichment costs reported separately, with the reconciliation invariant under test |

Three things worth carrying forward.

**R15's cause was the absence of evidence, not a harder-to-find element.** The
earlier investigation ruled out the audit table and swept for a border box
escaping a clipping ancestor, found nothing, and recorded that as not yet
knowing. Scrolling the root 422px right and taking a screenshot settles it: the
region is empty. The scrollable area was phantom, and the empty sweep had been
the answer all along. Tablet was affected too, which nobody had measured.

**R13 forced a decision about what to do when we cannot know.** A failure after
the investigation has begun cannot be distinguished from one that reached the
operator, so the key stays spent and a retry is refused for reconciliation. That
is deliberately unfriendly: the alternative is charging a merchant twice for one
question, and `uncertain` rows outlive settled ones for the same reason.

**A schema-parity test was overdue.** SQLite demos take `create_all` and
everything else takes Alembic, and nothing compared them. The test found drift
on its first run — `ix_call_announcements_called_participant_hash` was on the
model and in no migration — repaired in `0007`.

Actually called: nothing external in this session. No operator call, no model
call, no live network, no congestion subscription, no callback delivery. The
Docker image was **not built**: no daemon was available, so R10's file layout is
fixed and asserted while its container acceptance run is outstanding.
