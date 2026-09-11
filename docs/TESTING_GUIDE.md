# Isnad user test guide

**Updated 9 September 2026; originally written against commit `261ff64`.** One row per feature.
Each says what state it is actually in, how to set it up, exactly what to do,
what you should see, which command proves it automatically, what evidence
exists that it was really validated, and what it does not do.

Read the **Status** column literally:

| Status | Means |
| --- | --- |
| **Works offline** | Verified against local fixtures. No external call. |
| **Works, hosted-observed** | Also exercised against Nokia's hosted simulator, with a sanitized record in `docs/nac/observations/`. |
| **Built, never called** | The code and its tests exist; no operator has ever answered it. Do not demonstrate this as working integration. |
| **Draft** | Present and usable, but not finished to the standard the runbook sets. |
| **Open defect** | Known broken. Details in the row. |
| **Deferred** | Deliberately not built. The reason is in the row. |

## Setup

```sh
./setup.sh                                   # creates .venv311
.venv311/bin/python -m playwright install chromium   # once, for tests/browser
export ISNAD_PROVIDER=mock ISNAD_PLANNER=greedy ISNAD_GEMINI_API_KEY=
export ISNAD_DEMO_MODE=true
.venv311/bin/python -m uvicorn app.main:app --workers 1 --no-access-log
```

**Release review, 9 September 2026: 1,442 non-browser checks and 135 Playwright
checks passed** (1,577 total), on Python 3.11.15 with `ISNAD_PROVIDER=mock`
and `ISNAD_PLANNER=greedy`. **Re-run on 11 September 2026 after the judge
API-key feature: 1,458 non-browser and 147 Playwright checks passed** (1,605
total), ruff clean; the addendum in
[`RELEASE_VALIDATION_2026-09-09.md`](RELEASE_VALIDATION_2026-09-09.md) records it. The suites ran separately because the default
sandbox cannot bind the browser tests' local server; browser checks passed with
that permission. After the final quota/access changes, the affected 24 browser
checks passed again. The additions since 8 September cover the judge's
paired evidence source: contract parity (`tests/test_nac_mock_parity.py`), mode
authorization, isolation and the interrupted-demo matrix
(`tests/test_judge_evidence_modes.py`), the defects found in public peer
projects (`tests/test_nac_contender_regressions.py`), the selector and merchant
follow-up in a browser (`tests/browser/test_judge_evidence_modes.py`) and the
non-demo-mode deployment posture (`tests/browser/test_judge_production_posture.py`). The same run regenerates every capture in
`docs/ui/release/`. Alongside it: `ruff check app tests scripts demo deploy` clean,
`scripts/verify_runtime_lock.py` clean, `alembic upgrade head` on `sqlite://`
clean, `pip_audit --skip-editable` reporting no known vulnerabilities.
The local Docker build was unavailable because Docker Desktop could not start.
Hugging Face built the image and reported the exact uploaded revision RUNNING.
The deployed browser check then passed mock, two real Nokia/Gemini scenarios,
receipt verification, tamper rejection and zero-call replay. Details and remaining
limits: [release validation](RELEASE_VALIDATION_2026-09-09.md).

Open <http://localhost:8000/judge>. Everything below marked "Works offline"
needs nothing else. Those three exports matter: without them a developer `.env`
with a live provider and a real model key makes the demo bill someone.

The whole suite is one command:

```sh
.venv311/bin/python -m pytest -q
```

Use the command's current result rather than a historical test count. The Lab
mobile overflow fix is covered by regular browser assertions, with no xfail.
Shared-key quota and server responsiveness regressions run without real model
calls in `tests/test_model_budget_transport.py` and
`tests/test_model_responsiveness.py`. The recorded Lab benchmark is compared
with a fresh evaluation by `tests/test_lab_reproducibility.py`.

---

## The agent and its decision

| Feature | Status | Do this | You should see | Automated | Evidence | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| Judge: SIM replacement case | Works offline | `/judge` → **Investigate the SIM change** | CHALLENGE, a trace of the checks chosen, and a signed receipt link | `pytest -q tests/test_judge.py tests/browser/test_journeys.py` | `docs/ui/release/judge-en-replacement-1440.png` | The operator answers are a local fixture, badged `simulator` |
| Judge: clean checkout | Works offline | `/judge` → **Other cases** → **A clean checkout** | ALLOW resting on a supporting network fact | same | `judge-en-clean-1440.png` | — |
| Judge: unresolved evidence | Works offline | `/judge` → **Other cases** → **Unresolved evidence** | CHALLENGE with a hole in the chain, not a failed check | same | `judge-en-gap-1440.png` | This is "we could not check", never "the check failed" |
| Console Acts I–IX | Works offline | `/console` → **Run the stage suite** | Rows per act with source labels and a risk meter | `pytest -q tests/test_console.py tests/scenarios/` | `console-en-connected-1440.png` | Demo mode only; the console mints its own short-TTL credential |
| Gemini chooses the next check | **Works, one observed run** | Set `ISNAD_GEMINI_API_KEY` and `ISNAD_PLANNER=llm` | Evidence rows labelled `llm` with the model's own one-sentence rationale | `pytest -q tests/test_gemini_primary.py tests/test_llm_planner.py` (88 tests) | Every exchange in those tests is stubbed. One real run was made against `gemini-3.6-flash` over **mock** network data: 2 selection calls, both labelled `llm`, no fallback — `docs/nac/observations/2026-09-07-gemini-rehearsal.json` | One request shape, one fixture. The degraded-model and fallback-label paths have only ever run against stubs |
| Model STOP | Works offline | — | Selection ends; policy gates still apply | `pytest -q tests/test_gemini_primary.py -k stop` | — | Stopping is a decision, not a failure |
| Greedy fallback, and only for no answer | Works offline | Unset the key, or interrupt the network | Source `greedy` with a bounded reason naming which no-answer condition allowed it | `pytest -q tests/test_gemini_primary.py` | — | Invalid output, an explicit refusal, a 4xx/5xx and the call ceiling **stop selection** instead of falling back |
| Policy-choreographed checks | Works offline | Any case that reaches the ALLOW gate | Trace rows labelled `policy`, never `llm` | `pytest -q tests/test_allow_evidence_gate.py` | — | The signed `planner` field's vocabulary is llm/greedy; `policy` appears in the trace |
| Ask the agent | Works offline | `/console` → ask a question about a decision | A display-only answer, never fed back into a decision | `pytest -q tests/test_t4_ask_the_agent.py` | — | Needs a model key to produce prose; the decision is unaffected either way |

## Network evidence

| Feature | Status | Do this | You should see | Automated | Evidence | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| SIM Swap check | **Works, hosted-observed** | Any takeover case | `SIM swap inside the last 240 h`, or `no SIM swap …` | `pytest -q tests/test_nac_contract.py tests/test_nac_wire_contract.py` | 2026-09-06: `…1000` true, `…1001` false | A **boolean against a window**. It carries no date |
| Device Swap check | **Works, hosted-observed** | same | same shape | same | same | Path is v1 while SIM swap is v0 |
| Swap dates | **Works, hosted-observed** | Any case that buys a swap check | A separate row: the operator's change time, its age at the check, and a note that "latest change" may be an activation | `pytest -q tests/test_swap_timestamps.py` (37) | `…1000` returned `2026-09-06T19:53Z` (SIM) and `2026-08-18T13:26Z` (device) | **A second billed call**, priced separately. `monitoredPeriod` was absent, so the horizon is unknown |
| Boolean/date disagreement | Works offline | `/judge` → SIM replacement case | An explicit note that the operator's own two answers disagree | `pytest -q tests/test_swap_timestamps.py -k disagree` | The hosted contradiction it reproduces is real; the fixture is authored | Never derive one answer from the other |
| Reachability, roaming, location | Works offline (hosted-observed 2026-08-30) | Cases that select them | Normalized sentences only | `pytest -q tests/test_nac_provider.py tests/test_provider_preconditions.py` | `docs/nac/*.json` | A request with no `claimed_location` makes **zero** location calls |
| Number Verification | **Built, never called** | Needs the operator/device OAuth round trip | `CONSENT_REQUIRED` until a token exists | `pytest -q tests/test_consent.py tests/test_oidc_flow.py` | none | A desktop request with a phone number alone does not demonstrate silent verification |
| Number Recycling | **Works, hosted-observed** | Send `context.last_verified_at` on `/v1/verify` | A `policy` row checking subscriber continuity before stored trust is reused | `pytest -q tests/test_number_recycling.py` (26) | 2026-09-06: `…1000` recycled, `…1001` not, a future date → **400** | No date means no call. "Not recycled" is weighted at **zero** and can never buy an ALLOW; "recycled" blocks one outright |
| Call Forwarding Signal | **Deferred** | — | — | — | Hosted-observed anyway: active/inactive plus 422 and 503 | No demonstrated product path. Voice only, and not fraud by itself |
| KYC tenure | **Deferred** | — | — | — | none | Operator tenure is not merchant history |
| SIM Swap subscriptions | **Deferred** | — | — | — | none | SDK 10.0.0 has no such resource. The public callback now supports the mock congestion lifecycle; a real operator subscription and delivery remain unproved |
| Consent Info | **Deferred** | — | — | Contract pinned in `tests/test_nac_wire_contract.py` | none | Opens a redirect-ownership surface no current product path needs |
| Device Intelligence | **Deferred** | — | `EVIDENCE_UNAVAILABLE` | `pytest -q tests/test_nac_contract.py` | `docs/nac/device_intelligence.json` | Nokia exposes no device-reputation product. Priced but never selected |

## Network conditions (Congestion Insights)

| Feature | Status | Do this | You should see | Automated | Evidence | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| Subscribe / forecast / history / delete | Works offline; deployed mock observed | `/console` → the **Network conditions** panel | Level with a glyph as well as a colour, forecast or history, the period, confidence **or "not reported"**, updated-at, provenance | `pytest -q tests/test_network_conditions.py` (82) | Deployed Space lifecycle returned 201 / 200 / 200 / 200 on 9 September; release validation records the scope | The deployed result says `mock`. No Nokia congestion subscription was created |
| Callback delivery | **Built, never called by Nokia** | Configure `ISNAD_NAC_CONGESTION_CALLBACK_BASE_URL` (HTTPS, a host you control) | Events accepted only with the per-subscription token | `pytest -q tests/test_network_conditions.py -k "callback or event"` | none | A successful mock create is **not** proof a Nokia notification was delivered |
| Empty and unknown readings | Works offline | Query `+962790000005` | "The operator returned no reading. The condition is unknown." | `pytest -q tests/test_network_conditions.py -k empty` | — | An empty list is unknown, **never Low** |
| Missing confidence | Works offline | Query `+962790000002` | "confidence not reported" | `pytest -q tests/test_network_conditions.py -k confidence` | — | Never rendered as 0 or 100 |
| Isolation and limits | Works offline | — | Another tenant gets 404; one device holds one subscription; repeat queries are paced | `pytest -q tests/test_network_conditions.py -k "tenant or concurrent or paced"` | — | The reservation lock is scoped to the documented **single-worker** deployment |
| Congestion never affects the verdict | Works offline | Run a verification with the panel open | Nothing in the receipt mentions congestion | `pytest -q tests/test_network_conditions.py -k "never"` | — | It cannot raise a score and cannot waive a check |

## Receipts, proof and sessions

| Feature | Status | Do this | You should see | Automated | Evidence | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| Signed receipt | Works offline | Follow **Open signed receipt** | The exact signed bytes, the signature and the public key | `pytest -q tests/test_t6_receipt.py tests/test_receipt_download.py` | `receipt-en-valid-1440.png` | The signature proves issuance by this deployment, not that the customer is honest |
| Tamper detection | Works offline | Edit one character of the payload and re-verify | Verification fails | `pytest -q tests/test_vault.py tests/test_swap_timestamps.py -k tamper` | — | — |
| Backward compatibility | Works offline | — | A receipt signed before swap dates still verifies byte-for-byte | `pytest -q tests/test_swap_timestamps.py -k before_this_extension` | `tests/fixtures/legacy_receipt_pre_swap_dates.json` | Never reserialize a stored payload to verify it |
| Unavailable receipt | Works offline | Open `/r/chn_00000000000000000000` | A readable "not found", not a blank page | `pytest -q tests/browser/test_journeys.py -k unknown_receipt` | `receipt-en-unavailable-1440.png` | — |
| Shared proof link | Works offline | Create a share, open it | A separately signed attestation, never the original bytes | `pytest -q tests/test_proof_shares.py` | — | Expiry and revocation disable that link only |
| Trust session and revocation | Works offline | `/judge` → **Continue trust**, then **Simulate SIM swap** | The session is revoked and order release is blocked | `pytest -q tests/test_session.py tests/test_r05_r09_session_lifetime.py` | — | Expiry is checked on access as well as by the monitor |
| Outcome correction | Works offline | Report a merchant outcome | The correction is recorded without rewriting history | `pytest -q tests/test_outcomes_contract.py` | — | — |
| Idempotency and trace replay | Works offline | Repeat a request with the same `Idempotency-Key` | The same chain, no second billed investigation | `pytest -q tests/test_run_replay.py tests/test_r13_durable_idempotency.py` | — | Durable claims and stored completion are tested across crashes and retries |

## Consent, merchant journey and the rest

| Feature | Status | Do this | You should see | Automated | Evidence | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| Consent allow / deny / expiry / recovery | Works offline | Use the bundled fake operator (`demo/fake_operator/`) | Single-use callbacks, owner binding, cached completion | `pytest -q tests/test_consent.py tests/test_s9_consent_replay.py` | — | The fake operator is a local simulation and says so |
| Consent completion landing | Works offline | `/consent/complete` | A generic page carrying no code, state or phone number | `pytest -q tests/test_consent_html_redirect.py` | `consent-complete-en-initial-1440.png` | — |
| Merchant login / checkout / flow | Works offline | Start `demo/merchant_pilot` per the P4A record | Login errors, validation, consent QR, terminal states, recovery | `pytest -q tests/test_merchant_pilot.py tests/test_pilot_polling.py tests/test_pilot_retention.py` | **Not visited in a browser this release** | The three-service journey was not driven end-to-end in a browser here |
| Verified Caller announcements | Works offline | `/console` → reverse check | Pre-announcement rows, Tier 1 screen, velocity | `pytest -q tests/test_verified_caller.py tests/test_velocity.py` | — | An announcement cannot outvote a contradicting network fact |
| Lab comparisons and faults | Works offline | `/lab` → pick a case | Step-through, shuffle, reset, fault states, artifact provenance | `pytest -q tests/test_lab_page.py tests/test_lab_faults.py tests/test_lab_reproducibility.py` | `lab-en-case-1440.png` | Playback is offline; the separate Gemini button uses model quota. Mobile overflow is covered in `tests/browser/test_i18n_dom.py` |
| Judge-minted merchant API key | Works offline | `/api-keys` → enter the organizer code → **Generate key**, then paste the printed `curl` | A key shown once, three filled-in commands, `CHALLENGE / 0.322` from the terminal, the chain readable from the same tab | `pytest -q tests/test_judge_api_keys.py tests/browser/test_api_keys_page.py` | `api-keys-en-issued-1280.png`, `api-keys-ar-issued-375.png` | Mock provider only; refused where the default provider bills. In memory, two hours, gone on restart |
| Privacy and retention | Works offline | `/privacy` | The actual posture, readable retention values | `pytest -q tests/test_privacy.py tests/test_retention.py tests/test_r05_r09_session_lifetime.py` | `privacy-en-initial-1440.png` | Ended-session phone cleanup no longer depends on creating another session |
| Arabic / English on every surface | **Draft** | Use the language control on any page | Full RTL, isolated identifiers, no clipped text | `pytest -q tests/test_i18n.py tests/browser/` (147 browser tests) | 42 screenshots, both languages | Arabic is a **draft awaiting human review** — the page says so. The deterministic explanation paragraph is generated server-side and marked English |
| Offline receipt verifier | Works offline | `scripts/evidence_pack.py --output-dir /tmp/pack` | Every signature verifies without the service | `pytest -q tests/test_evidence_pack.py` | — | — |
| Bounded Nokia probe | **Works, hosted-observed** | `scripts/nac_demo_probe.py` (plan), then `--execute` | A plan and zero requests; then one call and one sanitized record | `pytest -q tests/test_nac_demo_probe.py` (38) | `docs/nac/observations/` | `+9999` numbers only. One operation per invocation, one attempt, no retries |

## What this release does not do

- **Real Gemini observations cover mock network evidence**, including the
  rehearsal and judge run under `docs/nac/observations/`. Quota exhaustion,
  concurrency and degraded-model behavior are tested with a fake HTTP transport.
- **No physical-handset operator consent or measured merchant fraud outcomes
  have been established.** The local consent contract passes. Follow
  [HANDSET_VALIDATION.md](HANDSET_VALIDATION.md) for the deployment preflight and
  separately armed live procedure.
- **Deployment evidence and CI are distinct.** Hugging Face runs a Docker
  deployment. CI is configured to build the repository image and run dependency
  audit; consult the relevant CI run for its result rather than treating this
  guide as a record of every build.
- **Not browser-verified:** 320px and tablet widths, 200% zoom, keyboard-only
  critical paths, the merchant three-service journey, and the shared proof
  page's expired and revoked states.
- **Earlier R05/R07/R09/R10/R12/R13 defects have regression coverage** in the
  corresponding `tests/test_r*.py` files; the old list of open defects is
  superseded. Passing synthetic tests does not establish live operator behavior.
