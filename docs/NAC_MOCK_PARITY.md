# Nokia contract parity: what is covered, and what is not

Compiled 9 September 2026. This document states the **exact** scope of the claim
"the local mock reproduces Nokia's documented contracts". Anything not listed
here is not covered, and nothing here is evidence that a live Nokia call
succeeded — that is a separate record, in the implementation record and in
`docs/nac/observations/`.

## The claim, precisely

> For the two operations and two simulator scenarios below, at the pinned
> versions, the request Isnad puts on the wire and the way it parses the
> response are the same in mock mode and in real mode.

Not claimed: identical live timing, identical dynamic values, identical quota
state, identical error behaviour beyond the documented statuses, or that the
mock is a replica of Nokia's service.

## How it is proved

The pieces are deliberately independent of each other:

| Piece | File | What it is |
| --- | --- | --- |
| Pinned contract the mock serves | `app/providers/nac_contract.json` | Hand-compiled from Nokia's public operation pages and this project's own hosted observations. Carries `contract_version`, currently **2026-09-09.1**. |
| Independently written expectations | `tests/fixtures/nac_contract/expected_wire.json` | Written by hand from the same public sources, **not** generated from Isnad's normalizer, adapter or policy. |
| Executable parity | `tests/test_nac_mock_parity.py` | 28 checks comparing the SDK's real serialization, the mock's answers, and the adapter's normalization against that file. |
| SDK wire behaviour | `tests/test_nac_wire_contract.py` | The installed SDK driven through `httpx.MockTransport`; zero external requests. |
| Mode isolation and bounds | `tests/test_judge_evidence_modes.py` | 30 checks over intercepted transports; no credentials. |
| UI paths | `tests/browser/test_judge_evidence_modes.py` | 14 checks in a real browser. |

The parity assertion that carries the weight is
`test_one_response_body_normalizes_identically_through_both_paths`: the same
response bytes go through the application mock and through the real adapter's
intercepted transport, and the resulting normalized evidence must be equal apart
from three declared fields — `source`, `latency_ms`, `at`.

## Coverage matrix

| Operation | Path | Version | Mock | Real adapter | Parity test | Hosted observation |
| --- | --- | --- | --- | --- | --- | --- |
| SIM Swap check | `POST /passthrough/camara/v1/sim-swap/sim-swap/v0/check` | v0 | yes | yes | yes | 2026-09-06, HTTP 200, both numbers |
| Device Swap check | `POST /passthrough/camara/v1/device-swap/device-swap/v1/check` | v1 | yes | yes | yes | 2026-09-06, HTTP 200, both numbers |
| SIM Swap `retrieve-date` | `.../v0/retrieve-date` | v0 | **not exposed** | implemented | wire test only | 2026-09-06 |
| Device Swap `retrieve-date` | `.../v1/retrieve-date` | v1 | **not exposed** | implemented | wire test only | 2026-09-06 |
| Everything else in `app/providers/nac.py` | — | — | **not exposed** | implemented | adapter tests only | see contract matrix |

"Implemented" and "exposed in this demo" are different columns on purpose. The
adapter has eight actions. The judge's paired demonstration exposes **two**.
Parity is verified for those two. No total may be quoted across those columns.

`retrieve-date` is a separately priced operation and is disabled in **both**
paired modes, so a mock run and a real run buy the same operations. It is
disabled by the paired provider not exposing the method, not by editing
`policy.yaml` — which would have changed every other run in the deployment.

## Scenario coverage

| Scenario | Subscriber | SIM Swap | Device Swap | Coverage level |
| --- | --- | --- | --- | --- |
| `swapped_subscriber` | `+99999991000` | `true` | `true` | Documented example, also observed on the hosted simulator 2026-09-06 |
| `stable_subscriber` | `+99999991001` | `false` | `false` | Documented example, also observed 2026-09-06 |

Both true and false are covered for both operations, which is the case a
`swapped=false` default would silently pass.

## Authored fault cases

These are **tests**, not Nokia observations. The statuses are documented on
Nokia's error-handling page; the JSON error **bodies are not documented
anywhere**, so the bodies below are authored, and this file says so rather than
letting a fixture imply Nokia returned them.

| Case | Status | Coverage | Isnad's answer |
| --- | --- | --- | --- |
| `sim_swap_unauthorized` | 403 | authored fault injection | `INFO` / `CONSENT_REQUIRED` |
| `device_swap_no_data` | 422 | authored fault injection (422 itself is documented for Device Swap) | `INFO` / `EVIDENCE_UNAVAILABLE` |
| `sim_swap_unavailable` | 503 | authored fault injection | `INFO` / `PROVIDER_UNAVAILABLE` |
| `sim_swap_missing_boolean` | 200, `{}` | authored fault injection | `INFO` / `PROVIDER_UNAVAILABLE` — never `false` |

The last row is the one that matters most. The contender review found a peer
project reading a missing boolean as `swapped=false`, which turns an outage into
a clean SIM. Here the SDK's own response model refuses the body and the adapter
reports a provider failure; `test_a_malformed_success_is_never_read_as_false`
asserts the negative separately so the expectation cannot be weakened without
the claim failing.

## Sources, with dates

| Id | Source | Accessed | Establishes |
| --- | --- | --- | --- |
| `nokia-sim-swap` | <https://networkascode.nokia.io/_docs/sim-swap/sim-swap> | 2026-09-09 | check/date split, `max_age` in hours 1–2400, `swapped` boolean, simulator table |
| `nokia-device-swap` | <https://networkascode.nokia.io/_docs/device-swap/device-swap> | 2026-09-09 | same, plus default 240 h and the documented 422 |
| `nokia-error-handling` | <https://networkascode.nokia.io/_docs/general-concepts/error-handling> | 2026-09-09 | the status vocabulary; **the JSON error body is not documented** |
| `isnad-wire-contract` | `tests/test_nac_wire_contract.py` | 2026-09-09 | what SDK 10.0.0 actually serializes |
| `isnad-hosted-observation` | `docs/nac/observations/2026-09-06-hosted-simulator.jsonl` | 2026-09-06 | responses this project actually received |

## Permitted differences

| Difference | Why it is permitted |
| --- | --- |
| `source` (`nac_contract_mock` vs `nac`) and `evidence_environment` | This is the provenance. It is *supposed* to differ, and it is inside the signature. |
| `latency_ms`, `at`, chain id, run id, signature | Per-run values. A mock's timing is synthetic and the UI says so. |
| Live Gemini may select a different path | A model is not deterministic. Exact parity is asserted with a fixed planner; the live comparison is a separate, bounded observation. |
| Nokia's dynamic values may move | `retrieve-date` returns a value generated relative to the request; it is not exposed here for exactly this reason. |

## Not verified

* Whether the SDK's own default host (`p-eu.rapidapi.com`) answers this account.
  Only the catalog host has, so the judge's real path uses the catalog host and
  a test asserts the outgoing URL.
* Any operation other than the two swap checks, under this demonstration.
* Any live-network (non-simulator) behaviour. The account is in Simulator mode.
* Whether Nokia's real error bodies match the authored fault bodies above.
