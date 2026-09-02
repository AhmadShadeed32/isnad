# Isnad Implementation Status

## Working locally

- FastAPI verification API with bearer API-key authentication.
- Idempotent verification requests with request-body mismatch protection.
- Hypothesis formation, policy thresholds, greedy evidence planning, and
  explicit agent-selection events.
- Scripted MockProvider for the three forward acts and Reverse Isnad.
- Evidence chains with normalized signals, provider source, latency, cost, and
  safe event redaction.
- SQLAlchemy persistence with Ed25519 tamper detection.
- Trust-with-a-TTL session monitor and demo swap injection.
- Browser console with SSE investigation events and efficiency metrics.
- 279 automated tests covering the engine, API, demo, sessions, vault,
  idempotency, validation, redaction, and provider normalization.

## NaC integration — OBSERVED, 30 Aug 2026

`network-as-code` **10.0.0** against `network-as-code.nokia.rapidapi.com`, one
real call per action. Raw responses are recorded verbatim in `docs/nac/` with SDK
version and UTC timestamp, device identifier redacted to its last two digits.
`tests/test_nac_contract.py` asserts `NacProvider` still normalizes each recorded
response to the signal the live API produced; those tests run offline and make no
call.

**Verified live — a real response was observed:**

| API | Observed signal | Latency |
|---|---|---|
| SIM Swap | `SIM_SWAPPED` | 863 ms |
| Device Swap | `DEVICE_SWAPPED` | 433 ms |
| Device Reachability | `REACHABLE_NORMAL` | 438 ms |
| Device Roaming | `ROAMING_NETWORK` | 346 ms |
| Location Verification | `NOT_AT_CLAIMED_LOCATION` | 555 ms |

Five live calls, 346–863 ms, median ~438 ms. Too few samples for a p95; that
needs a repeated run and is not claimed here.

**NOT verified — no call was made, and these must not be presented as working:**

| API | Why | What it needs |
|---|---|---|
| Number Verification | returns `CONSENT_REQUIRED` without a consent token | an OAuth round trip on real mobile data, plus a registered redirect URI |
| Step-up (OTP) | not a network provider call by design | nothing |
| Device Intelligence | no adapter is configured in `NacProvider` | an adapter, if the API is in scope |

The provider's normalization was written before any response had been seen, and
the recordings confirm the field handling it assumed — `swapped` on the swap
responses, `reachable`/`connectivity`, `roaming`, and the
`verification_result` enum — was correct.

## Remaining external setup

- **Number Verification consent round trip on real mobile data, recorded on
  video** — the one T1 item still outstanding. Needs the redirect URI
  registered against the NaC application and a public HTTPS callback.
- Note whether consent works over Wi-Fi as well as mobile data.

- Register the callback URI and Number Verification scope in the NaC application.
- Set `ISNAD_NAC_API_KEY`; SDK 10 discovers OAuth client credentials and metadata,
  while the endpoint/client settings remain fallbacks for older/custom clients.
- Replace in-process cache/events/session state with Redis for multi-worker use.
- Add Alembic migrations before using Postgres in deployment.
- Review the optional planner against the model and tooling requirements in the
  hackathon Resource & Tooling Guide.
