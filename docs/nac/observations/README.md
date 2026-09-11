# Hosted simulator observations

Sanitized records. Two kinds, and the distinction matters: the `.jsonl` files
are **standalone probe** runs from `scripts/nac_demo_probe.py`, and the
`2026-09-09-judge-*` files are **application** runs — Nokia calls made by Isnad
itself, through the authenticated judge endpoint, ending in a signed receipt. A
probe proves the credential and the contract; only an application run proves the
integration. See the entries at the end of this file.

One line per attempt,
including failed attempts. Each line carries the operation, host, path, UTC
observation time, masked device, our own request correlator, the bounded request
options, HTTP status, duration and an allowlisted normalized result — never a
response body, response headers, a traceback or an unmasked identifier.

`evidence_level` is `hosted_simulator` on every line. This account is in
Simulator mode: these are authenticated HTTP requests to Nokia's hosted
simulation, not radio measurements, and not proof of live-network entitlement.

## 2026-09-06-hosted-simulator.jsonl

Eleven calls, one attempt each (`max_retries: 0`, `timeout_in_seconds: 10`),
all against the catalog host `https://network-as-code.p-eu.apihub.nokia.io`.

| # | Operation | Device | Status | Result | ms |
| --- | --- | --- | --- | --- | --- |
| 1 | `sim_swap_check` (maxAge 24h) | `…1000` | 200 | `swapped: true` | 1821 |
| 2 | `sim_swap_check` (maxAge 24h) | `…1001` | 200 | `swapped: false` | 383 |
| 3 | `device_swap_check` (maxAge 24h) | `…1000` | 200 | `swapped: true` | 533 |
| 4 | `device_swap_check` (maxAge 24h) | `…1001` | 200 | `swapped: false` | 420 |
| 5 | `sim_swap_date` | `…1000` | 200 | `2026-09-06T19:53:10.195822+00:00` | 409 |
| 6 | `device_swap_date` | `…1000` | 200 | `2026-08-18T13:26:31.036260+00:00`, `monitoredPeriod` **absent** | 482 |
| 7 | `congestion_list` | — | 200 | `count: 0` | 352 |
| 8 | `forwarding_unconditional` | `…1000` | 200 | `active: true` | 372 |
| 9 | `forwarding_unconditional` | `…1001` | 200 | `active: false` | 384 |
| 10 | `forwarding_unconditional` | `…0422` | 422 | `http_422` | 342 |
| 11 | `forwarding_unconditional` | `…0503` | 503 | `http_503` | 324 |

### Two corrections to the 2026-09-06 file itself

Both were found while reviewing the runner after the batch, and both are
recorded rather than edited out of the data:

1. **`request_correlator` was generated locally and never sent** on those eleven
   calls. The runner created the UUID for the record but did not pass it to the
   SDK, so no `x-correlator` header travelled and the operator never saw these
   ids. They are local run ids for that file, nothing more. The runner now
   threads the correlator into every operation whose CAMARA contract accepts
   one, asserted by
   `tests/test_nac_demo_probe.py::test_the_recorded_correlator_is_the_one_the_operator_actually_saw`.
2. **Line 7 (`congestion_list`) records a device it never used.** That
   operation addresses the subscription collection, not a device; the runner
   demanded a number for it anyway. Fixed with a `needs_device` flag, so the
   field is now null for collection-level operations.

## 2026-09-06, second batch: Number Recycling

Four more calls, appended to the same file, same host and same bounds.

| # | Operation | Device | Reference date | Status | Result |
| --- | --- | --- | --- | --- | --- |
| 12 | `number_recycling` | `…1000` | 2026-01-15 | 200 | `phone_number_recycled: true` |
| 13 | `number_recycling` | `…1001` | 2026-01-15 | 200 | `phone_number_recycled: false` |
| 14 | `number_recycling` | `…1000` | **2030-01-15** | **400** | `http_400` |

The third of those is the useful one: a reference date in the future is an
operator **error**, not a `false`. Isnad therefore refuses an out-of-range date
locally and records it as unknown, rather than spending a call to be told.

(The file holds 14 lines: the eleven above plus these three.)

## What these observations settled

- **The catalog host answers.** `network-as-code.p-eu.apihub.nokia.io` returned
  200 for every read with the RapidAPI headers the SDK sends. That was an open
  unknown; it is now observed. The SDK default host remains untested, so the
  application default is unchanged and this host is passed explicitly.
- **Boolean scenarios match the published tables.** `…1000` swapped for both
  SIM and device, `…1001` neither; unconditional forwarding active then
  inactive; the documented error numbers return exactly 422 and 503.
- **Both date operations returned a real, timezone-aware value** for `…1000`.
  Nullable-date handling is still required — it was not exercised here.

## What these observations contradicted

**The `…1000` boolean and its date disagree, and the demo must not hide it.**
`device_swap_check` with a 24-hour window answered `swapped: true`, while
`device_swap_date` reported 2026-08-18 — nineteen days earlier. The simulator's
boolean is scenario-driven and is not derived from the date it will hand back.

Consequences, which gate 5 implements rather than papers over:

- Never compute a verdict by combining the two as if they described one event.
- Never present the date as "why" the boolean is true.
- Show both, each with its own provenance, and say when they disagree.

**The SIM date moves.** It was ten minutes old at observation time and appears
to be generated relative to the request, so no fixed date may be asserted in a
script, a fixture or a screenshot caption as "the" simulator value.

**`monitoredPeriod` was absent** from the device-date response. The horizon the
operator actually looked back over is therefore unknown, and a null or old date
must be displayed as unknown-horizon rather than "no change since".

## What remains unobserved

- Any **Nokia** congestion subscription create/get/query/delete. `congestion_list`
  returned 200 with an empty list, so the account is entitled to read the
  collection and no subscription is currently leaked — but no subscription has
  been created there. On 9 September the deployed app gained a reachable HTTPS
  callback base and its mock create/query/delete lifecycle passed, but that sent
  nothing to Nokia. Creating a Nokia subscription pointed at an unowned
  destination remains refused by the probe.
- Any callback delivery.
- Number recycling, consent info and KYC tenure.
- Number Verification's consent round trip.
- Anything at all on a live network. Simulator mode, throughout.


## 2026-09-09-judge-paired-rehearsal.json

**Application** runs, not probe runs: made by Isnad through
`POST /v1/judge/run` on a local instance, with the judge's evidence source set
to *Real NaC — Nokia hosted simulator*. Each one ends in a signed receipt whose
chain id is recorded beside it.

| Scenario | Device | Operations | Status | Planner asked / ran | Decision | Chain |
| --- | --- | --- | --- | --- | --- | --- |
| `swapped_subscriber` | `…1000` | `sim_swap_check`, `device_swap_check` | 200 (443 ms), 200 (175 ms) | gemini / **llm** | DECLINE | `chn_5663387814954fbdaac9` |
| `stable_subscriber` | `…1001` | `sim_swap_check`, `device_swap_check` | 200 (341 ms), 200 (duration not captured) | gemini / **llm** | CHALLENGE | `chn_ea46c6d30d774c6a869a` |

The second run's second attempt returned 200; its **transport** duration and
timestamp were truncated out of the captured output and stay `null` rather than
estimated. The signed verdict for that chain does carry the investigator's own
measurement of the same call (167 ms, 10:51:02.635 UTC), and the file records it
under separate keys — a wider interval than the transport figure, and not a
substitute for it.

`planner: "llm"` means every **planner** selection came from the model. It does
not mean the model chose both checks — see the journal below.

## 2026-09-09-judge-gemini-journal.json

The event journal of an equivalent run on the **mock** source (so it cost
nothing), showing which component chose what:

* seq 2 — `decision`, `planner: "llm"`: Gemini selects `sim_swap`, with its own
  rationale.
* seq 3, 6 — `enrichment`, `availability: "unsupported"`: the separately priced
  `retrieve-date` operations are visibly disabled, in both modes, so the paired
  comparison stays like-for-like.
* seq 5 — `decision`, `planner: "policy"`: the corroborating `device_swap` is
  required by policy, **not** chosen by the model.
* seq 8 — `verdict`, `planner: "llm"`.

Kept because the honest sentence is "the model chose the first check and policy
choreographed the second", and a run-level label alone cannot say that.

## 2026-09-09-judge-browser-real-runs.json

The other three real runs: same endpoint, same instance, driven from the
`/judge` page during the Step 13 walkthrough rather than from the CLI.

| Time (UTC) | Scenario | Planner | Decision | Chain |
| --- | --- | --- | --- | --- |
| 11:10:08 | `stable_subscriber` | greedy | CHALLENGE | `chn_22ea4ac639044cbd8a84` |
| 11:12:07 | `stable_subscriber` | greedy | CHALLENGE | `chn_ba95c1361a304534a4b0` |
| 11:25:17 | `stable_subscriber` | greedy | CHALLENGE | `chn_c7acd8d29ece47fd9f70` |

Reconstructed after the fact from the signed verdicts themselves, because the
per-attempt transport records were not captured for these three. That bounds
what the file claims: every duration in it is the investigator's measurement
inside the signed chain, and per-attempt HTTP status is asserted only for the
11:25 run, whose on-screen panel was captured in the walkthrough screenshot.
For the other four attempts the file says what is actually provable — each step
carries a normalized signal sourced `nac`, which this pipeline produces only
from a 2xx whose body parsed, so the responses were usable.

**Five real runs, ten outbound attempts, in total.** Two from the CLI, three
from the browser. That is the whole of it, and it was checked rather than
assumed: a real run that reached Nokia and then failed before saving would leave
no chain but *would* leave an `uncertain` idempotency row and a journal without a
verdict event. There are none — all 17 operations on that instance are `done`,
and every journalled run has its verdict.

## 2026-09-11-deployed-api-key-smoke.json

Not a Nokia observation, and filed here so the distinction is on the record: a
**judge-minted merchant key** exercising the merchant API on the deployed Space
(revision `ffa73f71`, source `6a8f2e2`), following the
guide's "Calling the hosted API" section step for step at 15:44:33 UTC.
`evidence_level` is `mock_provider`. The Space's default provider is the mock,
so no request left for Nokia; the sequence proves the key path, the tenancy
and the signature, not the operator.

| Step | Result |
| --- | --- |
| Mint behind the access code | 201, `mk_…`, 7199 s |
| `/v1/verify` with `X-Isnad-Planner: greedy` | CHALLENGE / DEGRADED / 0.322, planner `greedy`, five links, every source `mock` |
| Same request without the header | CHALLENGE, planner `llm`, 0.28 — the site's Gemini default, and why the header is in the printed command |
| Chain read with the key, and with the minting session | 200, 200 |
| Chain read with a different judge's session | 404 |
| `/verification` | `valid: true`, trusted key `ecaba3a8…0d341` |
| Replay with the same `Idempotency-Key` | same `chain_id`; changed amount, same key: 409 |
| Public receipt | 200 |

The record carries the chain id and the signed payload's SHA-256, never the
code or the key. The key is gone: it expired on its own two-hour TTL.

The first row of the file, `published_local_key_refused`, is the README's
local `demo-merchant-key` being sent to the Space and getting **403**. An
earlier run the same afternoon had it **accepted**: the Dockerfile default had
not been overridden by a Space Secret, which made every caller of that key one
tenant, the property the minted keys exist to avoid. `ISNAD_MERCHANT_API_KEYS`
was then rotated to a generated value in the Space settings and the sequence
re-run; the file records the re-run. Nothing on the demo pages depends on that
secret, and they were checked keyless afterwards.
