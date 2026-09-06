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
| 4 Gemini-first selection | PASSED | `app/config.py`, `app/agent/gemini.py`, `app/agent/planner.py`, `tests/test_gemini_primary.py`, `tests/test_llm_planner.py`, `.env.example`, `README.md` | Runbook gate-4 line (`test_gemini_primary test_gemini test_llm_planner test_allow_evidence_gate test_hypothesis_relevance test_t4_ask_the_agent`) → **88 passed, 0.82 s** (2026-09-06) | Exception routing verified by test, not by reading: `httpx.TimeoutException`/`ConnectError` ⊂ `TransportError` → greedy with `NO_ANSWER_TRANSPORT`; `HTTPStatusError` (429/4xx/5xx), `JSONDecodeError`, schema failure, `blockReason`, non-STOP `finishReason` → stop, source `llm`. Alternate greedy paths audited: only `investigator._choreography`, labelled `policy`. Model prose rendered by `textContent` in `console.html:addRow` and `judge.html:appendTrace` | No live Gemini call yet — that is gate 11.2, deliberately separate from the Nokia probes |
| 5 Swap timestamps | NOT STARTED | | | | |
| 6 Congestion Insights | NOT STARTED | | | | |
| 7 Identity extensions | NOT STARTED | | | | |
| 8 Arabic + English | IN PROGRESS | `app/static/i18n.js`, `app/static/i18n/{en,ar}.json`, product HTML, `demo/merchant_pilot` | | | Executable DOM tests missing; translator is provisional |
| 9 UI verification | NOT STARTED | | | | |
| 10 Core re-audit | NOT STARTED | | | | |
| 11 Demo rehearsal | NOT STARTED | | | | |
| 12 Testing guide + README | NOT STARTED | `docs/TESTING_GUIDE.md` does not exist | | | |
| 13 Final offline release gate | NOT STARTED | | | | |
| 14 Commit and private push | NOT STARTED | remote `private` → `AhmadShadeed32/isnad-private` | | | |
| 15 Handover | NOT STARTED | | | | |

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

Next action: gate 5 — read `app/chain/models.py` and `app/chain/builder.py`
canonicalization before adding any field, decide and document where temporal
metadata lives, and keep `tests/fixtures/legacy_receipt_pre_swap_dates.json`
verifying byte-exact.
