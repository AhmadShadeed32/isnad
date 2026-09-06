# Hosted simulator observations

Sanitized records produced by `scripts/nac_demo_probe.py`. One line per attempt,
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

- Any congestion subscription create/get/query/delete. `congestion_list`
  returned 200 with an empty list, so the account is entitled to read the
  collection and no subscription is currently leaked — but no subscription has
  been created, because no reachable HTTPS callback is configured. Creating one
  pointed at an unowned destination is refused by the probe.
- Any callback delivery.
- Number recycling, consent info and KYC tenure.
- Number Verification's consent round trip.
- Anything at all on a live network. Simulator mode, throughout.
