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
| 3 Bounded simulator probe | NOT STARTED | `scripts/nac_demo_probe.py`, `tests/test_nac_demo_probe.py` do not exist | | | |
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

Next action: gate 2 — reconcile `docs/NAC_SDK_CONTRACTS.json` with the authenticated
catalog rows in the NaC review and add `httpx.MockTransport` wire tests over the real
SDK for the five swap/congestion operations.
