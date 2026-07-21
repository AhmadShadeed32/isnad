# Isnad — Trust Engine API

An agentic, network-verified trust engine. A merchant, wallet, or bank calls **one**
API at a moment of risk and asks *"Can I trust this interaction?"* — Isnad's agent
investigates using CAMARA APIs on Nokia Network-as-Code and returns
**ALLOW / CHALLENGE / DECLINE** with a full, human-readable evidence chain.

This repository is the **vertical slice** from the build plan: the reasoning engine,
the scripted `MockProvider`, and the `/v1/verify` API work end-to-end locally. The
`NacProvider` includes the SDK adapter for SIM Swap, Device Swap, Reachability,
Roaming, Location Verification, and consent-gated Number Verification; it requires
sandbox credentials to run.

## What's implemented

- **Investigator agent** (`app/agent/`) — forms a hypothesis, then gathers the
  *cheapest useful evidence first* and escalates only when suspicion warrants. The
  choice of which CAMARA call to make next is the agent's own reasoning (satisfies
  the "agent-initiated decision inputs" requirement).
- **Policy / evidence-cost model** (`app/policy/policy.yaml`) — the single tuning
  surface: costs, signal weights, thresholds, per-hypothesis relevance.
- **Provider adapter** (`app/providers/`) — `MockProvider` (scripted acts) and
  `NacProvider` (real SDK adapter) behind one `gather()` contract. Swap with
  `ISNAD_PROVIDER=mock|nac` — no other code changes.
- **API** (`app/api/`) — `POST /v1/verify` (with `Idempotency-Key` support),
  `GET /v1/chains/{id}`, `GET /v1/chains/{id}/verification` + `GET /v1/vault/public-key`
  (signed, tamper-evident chains), `POST /v1/reverse-verify` (Reverse Isnad),
  `POST/GET/DELETE /v1/sessions` (Trust with a TTL — live revocation),
  Number Verification consent at `POST/GET /v1/consents/number-verification*`,
  live console SSE at `GET /v1/console/stream`, API-key auth.
- **Persistence** (`app/db/`) — chains stored via SQLAlchemy (SQLite by default,
  Postgres via `ISNAD_DATABASE_URL`); each chain signed with Ed25519 (`app/chain/vault.py`).
- **Planner** — deterministic greedy by default; optional LLM planner behind
  `ISNAD_PLANNER=llm` (falls back to greedy when no API key is set).
- **Cache** (`app/cache.py`) — in-memory by default, Redis via `ISNAD_CACHE_BACKEND=redis`.
- **Tests** — 39 tests: the demo acts, Reverse Isnad, session revocation, the
  vault, idempotency, and planner selection all run the real engine.

## Quickstart

```bash
pip install -e ".[dev]"          # or: pip install fastapi uvicorn pydantic pydantic-settings pyyaml httpx pytest pytest-asyncio

# 1. Run the demo acts from the CLI
python -m demo.run_acts

# 2. Run the tests
pytest -q

# 3. Serve the API
uvicorn app.main:app --reload
#    docs at http://localhost:8000/docs
```

### Live agent console (the on-stage demo)

With the server running, open **http://localhost:8000/console**. It's a
terminal-styled page that streams the agent's reasoning link-by-link over SSE.
Click **Act I / II / III / IV** to watch a paced investigation: the hypothesis, each
CAMARA call as it happens (PASS/FLAG), the P(fraud) meter moving, and the final
ALLOW / CHALLENGE / DECLINE verdict with its reason. Act IV is Reverse Isnad — a
spoofed "bank officer" caller failing network attestation.

The console also includes a **Live demo runbook**. **Run full stage demo** exercises
all four scripted acts, starts a trust session, injects a simulated swap, and waits
for revocation. **Run live API checks** calls the configured provider through health,
forward verification, Reverse Isnad, idempotency replay, and evidence-vault
verification. **Start real NaC consent** opens the actual Number Verification
authorization flow and resumes the investigation after the callback. The runbook
labels hybrid mode clearly: with `ISNAD_PROVIDER=nac` and `ISNAD_DEMO_MODE=true`,
NaC calls and consent remain real while stage acts and session attacks use the
deterministic simulator.

- Page: `GET /console`  ·  Stream: `GET /v1/console/stream` (SSE)
- Trigger (unauthenticated demo control): `POST /v1/console/run/{act1|act2|act3}`
- Pacing lives in `MockProvider(step_delay_ms=...)` — set to 0 for tests.

Example call:

```bash
curl -s http://localhost:8000/v1/verify \
  -H "Authorization: Bearer demo-merchant-key" \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"+99999991000",
       "context":{"event":"checkout","payment_method":"cod",
                  "account_age_days":0,"amount":{"value":4200}}}'
```

## Going live on Nokia NaC

1. Use Python 3.11+ for the NaC SDK path, then run `pip install -e '.[nac]'` and get a sandbox key from the NaC developer portal.
2. Copy `.env.example` to `.env`, set `ISNAD_PROVIDER=nac` and
   `ISNAD_NAC_API_KEY`, and register `ISNAD_NAC_REDIRECT_URI` with the Number
   Verification application.
3. Start the API and use the consent flow below before calling `/v1/verify` for
   a consent-gated investigation.

### Number Verification consent flow

Number Verification is not a silent backend call. Isnad creates an opaque,
single-use state, returns the NaC authorization URL, receives the provider
callback, exchanges the callback code for a short-lived token, and then resumes
the same investigation. Tokens are never returned in API responses or persisted
in the evidence chain.

```bash
# 1. Start consent; open authorization_url on the user's mobile data connection.
curl -s http://localhost:8000/v1/consents/number-verification \
  -H 'Authorization: Bearer demo-merchant-key' \
  -H 'Content-Type: application/json' \
  -d '{"phone_number":"+962790000001","context":{"event":"signup","account_age_days":0}}'

# 2. The provider redirects to the configured callback with code and state.
GET /v1/consents/number-verification/callback?code=...&state=...

# 3. After status becomes AUTHORIZED, resume the original investigation.
curl -s -X POST http://localhost:8000/v1/consents/{consent_id}/verify \
  -H 'Authorization: Bearer demo-merchant-key'
```

The SDK 10 path discovers the NaC OAuth client credentials and authorization
metadata automatically. The endpoint/client variables in `.env.example` are
fallbacks for older or custom SDK clients.

## Built beyond the core

- Reverse Isnad — `POST /v1/reverse-verify` + console Act IV.
- Trust-with-a-TTL live revocation — `/v1/sessions/*` + console session panel
  (start a session, "Inject SIM swap", watch it die).
- Evidence vault — every chain Ed25519-signed; verify via
  `GET /v1/chains/{id}/verification`; tamper is detected.
- Persistence — SQLAlchemy (SQLite default, Postgres via `ISNAD_DATABASE_URL`).
- Idempotency — `Idempotency-Key` header replays the original verdict.
- Optional LLM planner (`ISNAD_PLANNER=llm`) and Redis cache
  (`ISNAD_CACHE_BACKEND=redis`), both graceful no-ops without their deps.

## Still on the roadmap

Real multi-worker consent storage/token caching, Alembic migrations, choreographed
step-up tuning, and the Tier-2/3 moat features
(Passport, Graph). See
`Isnad_API_Build_Plan.md`.
