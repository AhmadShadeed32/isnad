# Nokia simulator setup runbook

Written 9 September 2026 against the code in this repository. Every command
below was run; where a step could not be completed, it says so rather than
describing what it would have done.

This runbook covers the **judge-selectable evidence source** on `/judge`. It is
not Nokia platform documentation and adds no Nokia requirements; it is how this
application is configured to use them.

## What you are setting up

| Choice on `/judge` | What happens | What it needs |
| --- | --- | --- |
| **Mock — Nokia-compatible demo** (default) | The real `network_as_code` SDK serializes the request; a local `httpx.MockTransport` answers with the pinned Nokia-shaped response; the shared adapter normalizes it. | Nothing. No Nokia account, no network, no key. |
| **Real NaC — Nokia hosted simulator** | The same SDK and adapter send actual HTTPS requests to Nokia using the documented simulator numbers. | A Nokia application key, an organizer access code, and the limits below. |

Both use the same investigator, policy, journal, receipt and signature. Only the
transport and the recorded provenance differ.

The evidence source is **independent of the planner**. A mock run may still call
Gemini. Only *mock evidence + Greedy planner* is independent of both services.

## Install and start (tested)

```sh
python3.11 -m venv .venv311
.venv311/bin/pip install -r requirements.lock.txt
cp .env.example .env      # then fill in the values below
.venv311/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

The runtime lock pins `network_as_code==10.0.0`. Do not upgrade it to follow a
tutorial: an upgrade has to update `requirements.lock.txt`, pass
`tests/test_nac_wire_contract.py` and `tests/test_nac_mock_parity.py`, and be
recorded as a new `contract_version` in `app/providers/nac_contract.json`.

Verify the pin:

```sh
.venv311/bin/python scripts/verify_runtime_lock.py
```

## Configuration

Secrets are server-side only. None of these values is ever rendered into a page,
passed as a command argument, written to a record, or printed by any script here.

| Setting | Needed for | Notes |
| --- | --- | --- |
| `ISNAD_NAC_API_KEY` | real only | The Nokia application API key. Sent by the SDK as `x-rapidapi-key`. |
| `ISNAD_NAC_RAPIDAPI_HOST` | real only | Gateway host header. Default `network-as-code.nokia.rapidapi.com`. This is a **header**, not the destination. |
| `ISNAD_JUDGE_NAC_BASE_URL` | real only | The HTTPS destination. Defaults to `https://network-as-code.p-eu.apihub.nokia.io`, the only host this account has been observed to answer from. Restricted to two allowlisted Nokia hosts; not caller-supplied. |
| `ISNAD_NAC_TIMEOUT_SECONDS` | real only | Per-call bound. SDK retries are forced to 0 at every call site. |
| `ISNAD_JUDGE_REAL_NAC_ENABLED` | real only | `false` by default. While false, `/judge` shows the real option as unavailable with the reason, and mock is unaffected. |
| `ISNAD_JUDGE_ACCESS_CODES` | real only | Comma-separated organizer codes, each at least 12 characters. Refused at startup if empty or guessable while real mode is on. |
| `ISNAD_SUBJECT_PEPPER` | real only | Must be persisted. |
| `ISNAD_VAULT_KEY_PATH` | real only | Must already exist. Startup refuses to generate one, because a fresh key makes every previously issued receipt report invalid. |
| `ISNAD_GEMINI_API_KEY` | Gemini planner | A separate choice from the evidence source, in either mode. |

Limits, all positive and all validated at startup when real mode is on:

| Setting | Default | Meaning |
| --- | --- | --- |
| `ISNAD_JUDGE_NAC_ATTEMPTS_PER_RUN` | 2 | Outbound HTTP attempts one run may make, counted at the transport. |
| `ISNAD_JUDGE_NAC_ATTEMPTS_PER_SESSION` | 6 | Per judge session. |
| `ISNAD_JUDGE_NAC_ATTEMPTS_PER_HOUR` | 24 | Deployment-wide, rolling hour. |
| `ISNAD_JUDGE_GEMINI_CALLS_PER_RUN` | 3 | Model calls per investigation on this path; may only tighten the deployment ceiling. |
| `ISNAD_JUDGE_MAX_CONCURRENT_REAL_RUNS` | 2 | Concurrent real runs. |
| `ISNAD_JUDGE_SESSION_TTL_SECONDS` | 1800 | Judge session lifetime. |
| `ISNAD_JUDGE_API_KEY_TTL_SECONDS` | 7200 | Lifetime of a merchant key a judge mints on `/api-keys` behind the same code. Mock provider only; refused where the default provider bills. |

These are starting caps chosen to bound a demonstration. They are not a claim
about price, entitlement, or what Nokia permits.

## Supported test cases

Only the two documented simulator subscribers, and only the two boolean swap
checks, in **both** modes.

| Scenario id | Subscriber | SIM Swap check | Device Swap check |
| --- | --- | --- | --- |
| `swapped_subscriber` | `+99999991000` | `swapped: true` | `swapped: true` |
| `stable_subscriber` | `+99999991001` | `swapped: false` | `swapped: false` |

Sources and coverage: [`docs/NAC_MOCK_PARITY.md`](NAC_MOCK_PARITY.md).

The separately priced `retrieve-date` operations are **disabled in both modes**,
so the two are comparable. The three authored teaching stories on `/judge`
(`Investigate the SIM change`, `A clean checkout`, `Unresolved evidence`) are
mock-only fixtures with no Nokia simulator scenario; they are labelled as such
in the page and cannot be selected as a real run.

## Offline readiness check

```sh
.venv311/bin/python scripts/nac_simulator_demo.py --readiness
```

It reports the SDK version, the selected host, the supported scenarios, whether
each credential is *present*, whether judge access is configured, and every
limit — with no secret values and **no external request**. A passing check
prints `"status": "configured_connection_not_verified"`.

That sentence is the whole point. Configuration readiness is not a successful
call. Constructing an SDK client, rendering the selector, or seeing a green
badge proves nothing about Nokia. Only a completed real run does, and its
result carries its own provenance inside the signature.

## Running it

Plan first; nothing external happens without `--execute`:

```sh
.venv311/bin/python scripts/nac_simulator_demo.py --mode mock_nokia --scenario stable_subscriber
```

Execute a mock run against a locally started server:

```sh
.venv311/bin/python scripts/nac_simulator_demo.py --mode mock_nokia --scenario stable_subscriber --execute
```

Execute a real run. The access code is read from the environment so it never
reaches a shell history, a process list or a screenshot:

```sh
.venv311/bin/python scripts/nac_simulator_demo.py --mode nokia_simulator --scenario swapped_subscriber --execute
```

Both go through `POST /v1/judge/run` — the same authenticated endpoint the page
uses. The helper has no investigator, no provider and no idempotency rules of
its own.

Supply `ISNAD_JUDGE_ACCESS_CODE` through your secret manager or a protected
environment file before executing the real command. Do not type its value into
the shell command. Hugging Face packaging, secret placement and signing-key
restoration are deployment operations for whoever runs the Space rather than
part of this submission, and are kept with the project's other working notes
outside `docs/`.

## Recovery

| Symptom | What it means | What to do |
| --- | --- | --- |
| Real option shown greyed with "not enabled on this deployment" | `ISNAD_JUDGE_REAL_NAC_ENABLED` is false or no Nokia key is configured | Configure both, restart. Mock is unaffected throughout. |
| `invalid_access_code` | The code did not match any configured code | Ask the organizer for the current code. No request was made; nothing was spent. |
| `judge_session_required` | The session expired (default 30 minutes) | Reload `/judge`. A new session is minted automatically; re-enter the access code for real runs. |
| `judge_allowance_exhausted` | This session used its Nokia allowance | Previous results are unaffected. Mock still runs. A new session gets its own allowance. |
| `deployment_allowance_exhausted` | The hourly deployment-wide cap is reached | Wait, or raise `ISNAD_JUDGE_NAC_ATTEMPTS_PER_HOUR` deliberately. |
| `real_runs_busy` | Concurrency bound reached | Wait for the in-flight run. |
| A real run returns a decision with `PROVIDER_UNAVAILABLE` / `CONSENT_REQUIRED` rows | Nokia answered with an error, or the request timed out | The run keeps its real source label and its attempted-spend accounting. It is **never** refilled with mock data. Choose Mock and run again for a separate, clearly mock run with its own receipt. |
| Startup refuses with "No vault signing key" | The signing key is missing | Mount the volume holding it. Starting without it would invalidate every receipt already issued. |
| Startup refuses with "ISNAD_JUDGE_ACCESS_CODES is empty" | Real mode is on with no code | Generate one: `python3 -c 'import secrets; print(secrets.token_urlsafe(16))'` |

## Production prerequisites (review section E)

This runbook gets you the **simulator**. None of the following is a prerequisite
for the two-check judge demonstration, and simulator success does not establish
any of them.

| Prerequisite | Status for this project |
| --- | --- |
| Nokia business profile | Owner-supplied. Not completed as part of this work. |
| Application profile: intended APIs, countries, use case, processing purpose, consent approach, data locations | Owner-supplied. Not completed. |
| Billing account and selected price plan | Not set up. The account is in **Simulator** mode; catalog visibility is not entitlement. |
| Country/operator coverage for live subscribers | Unknown. No live-network call has been made from this project. |
| Consent approach and the B2B authorization workbook | Not prepared. Resubmitting an authorization list can revoke omitted devices, so it needs the account owner's input before any submission. |
| Registered HTTPS redirect/callback | `ISNAD_NAC_REDIRECT_URI` exists and startup refuses a localhost value on the billable path. Number Verification remains disabled on the judge path. |
| Physical-handset validation | Not performed. Number Verification V1 needs the subscriber's cellular connection; V2 is a separate Android/TS.43 client this project does not have. |

## What this setup deliberately does not do

* It does not add QoD, geofencing, slicing, KYC, Location Retrieval, Number
  Verification or congestion subscriptions to the judge path. Those are recorded
  deferrals in [`docs/NAC_DOCUMENTATION_REVIEW.md`](NAC_DOCUMENTATION_REVIEW.md),
  not oversights.
* It does not accept a caller-supplied endpoint, proxy or subscriber. The
  destination is one of two allowlisted hosts and the subscriber comes from the
  pinned scenario.
* It does not accept a Nokia key on a request. A model key on a request is a
  reviewer spending their own quota; an operator key is money.
