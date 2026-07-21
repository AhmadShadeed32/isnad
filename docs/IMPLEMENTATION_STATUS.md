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
- 39 automated tests covering the engine, API, demo, sessions, vault,
  idempotency, validation, redaction, and provider normalization.

## NaC integration

`NacProvider` uses the Network as Code Python SDK when
`ISNAD_PROVIDER=nac` and `ISNAD_NAC_API_KEY` is set. It normalizes SIM Swap,
Device Swap, Reachability, Roaming, and Location Verification results and runs
synchronous SDK calls off the FastAPI event loop with a timeout.

Number Verification now has an explicit authorization-code lifecycle:
`POST /v1/consents/number-verification` creates a state-bound authorization URL,
`GET /v1/consents/number-verification/callback` exchanges the provider code, and
`POST /v1/consents/{consent_id}/verify` resumes the original investigation. The
single-use access token stays in short-lived process memory and is never returned
or persisted in the evidence chain. A normal investigation without that consent
still reports `CONSENT_REQUIRED`.

## Remaining external setup

- Register the application and obtain NaC simulator credentials.
- Verify the exact SDK version and simulator responses in an integration test.
- Register the callback URI and Number Verification scope in the NaC application.
- Set `ISNAD_NAC_API_KEY`; SDK 10 discovers OAuth client credentials and metadata,
  while the endpoint/client settings remain fallbacks for older/custom clients.
- Replace in-process cache/events/session state with Redis for multi-worker use.
- Add Alembic migrations before using Postgres in deployment.
- Review the optional planner against the model and tooling requirements in the
  hackathon Resource & Tooling Guide.
