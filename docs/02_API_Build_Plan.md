# Isnad — API Build Plan (Python / FastAPI)

**Scope:** Full engine + external API. This covers the investigator agent, the policy / evidence-cost logic, the CAMARA integration layer on Nokia Network-as-Code (NaC), the chain/evidence model, and the public verification API a merchant or bank calls.

**Target:** A working, demo-able MVP over the 10-week hackathon window, built so the same code path serves both the live NaC sandbox and the on-stage three/four-act demo.

**Grounding:** CAMARA fraud/identity APIs (Number Verification, SIM Swap, Device Swap, Location Verification, Device Reachability Status, Device Roaming Status) are consumed through Nokia's **Network as Code Python SDK** (`network-as-code`, Apache-2.0). Number Verification uses the documented authorization-code consent flow: Isnad creates the authorization URL, receives the redirect code, exchanges it for a single-use token, and resumes the investigation. See Sources at the end.

---

## 1. Guiding principles

1. **The agent decides which API to call — never the caller.** The external API exposes one intent ("can I trust this interaction?"), not seven buttons. This is the hackathon's hard requirement and the core differentiator.
2. **Provider-agnostic core.** Every CAMARA call goes through an adapter interface. A `MockProvider` (deterministic, scriptable) and a `NacProvider` (real SDK) implement the same interface, so the agent, the tests, and the stage demo all run identical logic.
3. **Cheapest evidence first.** The agent holds an explicit cost model and a confidence target; it stops as soon as it can justify a verdict, or escalates when suspicion warrants the spend.
4. **Evidence, not scores.** Every verdict carries a human-readable chain of attested links. No black-box number.
5. **No raw signals stored.** Location returns yes/no vs a claim; only the resulting chain evidence is persisted.

---

## 2. Architecture

```
                         ┌─────────────────────────────────────────────┐
   Merchant / Bank ──────▶  FastAPI  (public API surface)               │
   POST /v1/verify       │   - auth (API key), rate limit, idempotency  │
                         │   - request validation (Pydantic)            │
                         └───────────────┬─────────────────────────────┘
                                         │  VerificationRequest
                                         ▼
                         ┌─────────────────────────────────────────────┐
                         │  Investigator Agent (orchestrator)           │
                         │   1. build hypothesis from context           │
                         │   2. loop: pick cheapest useful evidence     │
                         │   3. call provider, update belief            │
                         │   4. stop at confidence target / budget      │
                         │   5. emit verdict + chain                    │
                         └───┬───────────────┬───────────────┬─────────┘
                             │               │               │
                   ┌─────────▼──────┐ ┌──────▼───────┐ ┌─────▼────────┐
                   │ Policy /       │ │ Evidence     │ │ Chain Builder│
                   │ Cost Model     │ │ Providers    │ │ (audit doc)  │
                   │ (YAML config)  │ │ (adapters)   │ │              │
                   └────────────────┘ └──────┬───────┘ └──────────────┘
                                             │
                              ┌──────────────┴──────────────┐
                              │                             │
                     ┌────────▼────────┐          ┌─────────▼─────────┐
                     │ NacProvider     │          │ MockProvider      │
                     │ (network-as-code│          │ (scripted, demo & │
                     │  SDK → CAMARA)  │          │  tests)           │
                     └─────────────────┘          └───────────────────┘

   Cross-cutting: Postgres (chains, sessions), Redis (session TTL, idempotency,
   token cache), structured event stream (the live console), OpenTelemetry traces.
```

---

## 3. Tech stack & repository layout

| Concern | Choice |
|---|---|
| Language / runtime | Python 3.12 |
| API framework | FastAPI + Uvicorn (async) |
| Data validation | Pydantic v2 |
| CAMARA access | `network-as-code` (Nokia NaC Python SDK) |
| HTTP (fallback / direct CAMARA) | `httpx` (async) |
| Agent reasoning | Deterministic policy engine first; optional LLM planner behind a flag |
| Persistence | PostgreSQL (SQLAlchemy 2.0 + Alembic) |
| Cache / sessions / TTL | Redis |
| Event stream (live console) | Redis pub/sub → WebSocket / SSE |
| Config | `pydantic-settings` + `policy.yaml` |
| Tests | pytest + pytest-asyncio + respx (HTTP mocking) |
| Packaging / deploy | Docker + docker-compose (dev), single container (demo) |
| Signing (evidence vault) | `cryptography` (Ed25519 signatures on chains) |

```
isnad/
├── app/
│   ├── main.py                 # FastAPI app factory, routers, middleware
│   ├── config.py               # settings, secrets, env
│   ├── api/
│   │   ├── routes_verify.py     # POST /v1/verify, GET /v1/chains/{id}
│   │   ├── routes_reverse.py    # POST /v1/reverse-verify  (Reverse Isnad)
│   │   ├── routes_session.py    # session subscribe / status / revoke
│   │   ├── routes_console.py    # WS/SSE live event stream (demo)
│   │   └── deps.py              # auth, rate limit, idempotency deps
│   ├── agent/
│   │   ├── investigator.py      # the decision loop
│   │   ├── hypothesis.py        # context → risk hypothesis
│   │   ├── belief.py            # Bayesian-ish belief state
│   │   └── planner.py           # evidence selection (cost model)
│   ├── policy/
│   │   ├── engine.py            # loads policy.yaml, scores actions
│   │   └── policy.yaml          # costs, signal weights, thresholds
│   ├── providers/
│   │   ├── base.py              # EvidenceProvider Protocol + result types
│   │   ├── nac.py               # NacProvider (real SDK)
│   │   ├── mock.py              # MockProvider (scripted scenarios)
│   │   └── camara/              # per-API wrappers (number_verify, sim_swap, ...)
│   ├── chain/
│   │   ├── models.py            # EvidenceLink, Chain, Verdict
│   │   ├── builder.py           # assemble + render chain
│   │   └── vault.py             # sign + persist (Tier-2 stub)
│   ├── domain/
│   │   ├── schemas.py           # Pydantic request/response
│   │   └── enums.py             # Verdict, Signal, ProviderName
│   ├── db/                      # SQLAlchemy models, session, migrations
│   ├── events.py               # emit(step) → console stream
│   └── security/               # API-key auth, HMAC, secrets
├── tests/
│   ├── scenarios/              # scripted demo scenarios (act I–IV)
│   ├── unit/
│   └── integration/
├── demo/
│   ├── console/                # terminal-style live log UI
│   └── seed_scenarios.py
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 4. The CAMARA evidence layer

### 4.1 Adapter contract (`providers/base.py`)

Every provider implements one Protocol so the agent never knows whether it is talking to the network or a mock.

```python
from typing import Protocol
from app.domain.enums import Signal
from app.chain.models import EvidenceLink

class EvidenceProvider(Protocol):
    async def number_verify(self, phone: str, ctx: "Ctx") -> EvidenceLink: ...
    async def sim_swap(self, phone: str, max_age_hours: int, ctx: "Ctx") -> EvidenceLink: ...
    async def device_swap(self, phone: str, max_age_hours: int, ctx: "Ctx") -> EvidenceLink: ...
    async def location_verify(self, phone: str, claim: "Area", ctx: "Ctx") -> EvidenceLink: ...
    async def reachability(self, phone: str, ctx: "Ctx") -> EvidenceLink: ...
    async def roaming(self, phone: str, ctx: "Ctx") -> EvidenceLink: ...
    async def device_intelligence(self, phone: str, ctx: "Ctx") -> EvidenceLink: ...
```

Each method returns a normalized `EvidenceLink` (see §6), **not** the raw CAMARA payload — so the agent reasons over a uniform signal type and no raw coordinates or MSISDN metadata leak upstream.

### 4.2 CAMARA API map

| Method | CAMARA API | Call shape (sandbox) | Normalized signal |
|---|---|---|---|
| `number_verify` | Number Verification | verify `phoneNumber` matches device on network | `NUMBER_MATCH` / `NUMBER_MISMATCH` |
| `sim_swap` | SIM Swap | `check` with `maxAge` hours → swapped bool | `SIM_STABLE` / `SIM_SWAPPED` |
| `device_swap` | Device Swap | `check` within period → swapped bool | `DEVICE_STABLE` / `DEVICE_SWAPPED` |
| `location_verify` | Location Verification | verify device vs claimed `area` → TRUE/FALSE/PARTIAL | `AT_CLAIMED_LOCATION` |
| `reachability` | Device Reachability Status | connectivity: DATA / SMS / NOT_CONNECTED | `REACHABLE_NORMAL` / burner pattern |
| `roaming` | Device Roaming Status | roaming bool + country | `HOME_NETWORK` / `ROAMING_NETWORK` |
| `device_intelligence` | Device Identifier / risk (NaC value-add) | device reputation | `DEVICE_TRUSTED` / `DEVICE_RISKY` |

### 4.3 Auth & consent (`security/` + `providers/nac.py`)

- **App auth:** client credentials issued from the NaC developer portal → cached, refreshed.
- **User-consented calls:** Number Verification uses the authorization-code flow exposed at `/v1/consents/number-verification*`; the opaque state is bound to the merchant and original request, and the single-use token stays in short-lived process memory.
- **Consent record:** every verification stores which consent basis was used, as a chain link — this is also your "privacy by design" answer to judges.
- **Sandbox first:** develop against NaC simulated devices; flip an env flag (`ISNAD_PROVIDER=nac|mock`) to switch. No code change between demo and live.

---

## 5. The investigator agent

### 5.1 Decision loop (`agent/investigator.py`)

```
investigate(request):
    ctx      = build_context(request)             # amount, channel, account age, claim
    hypo     = hypothesis.form(ctx)               # e.g. ACCOUNT_TAKEOVER | MULE | LEGIT_THIN_FILE
    belief   = Belief.prior(hypo)                 # P(fraud) prior from context
    budget   = policy.budget_for(ctx)             # cost ceiling (latency + $ + friction)
    chain    = Chain.start(ctx, hypo)

    while not belief.decisive(policy.thresholds) and budget.remaining():
        action = planner.next_best(belief, budget, policy)   # highest info-gain per cost
        if action is None:                                   # nothing worth buying
            break
        link   = await provider.call(action, ctx)            # one CAMARA call
        emit(link)                                            # → live console
        chain.add(link)
        belief = belief.update(link)                         # move P(fraud)
        budget.spend(action.cost)

    verdict = policy.decide(belief)                          # ALLOW | CHALLENGE | DECLINE
    if verdict == CHALLENGE:
        verdict, chain = choreograph_stepup(belief, chain)  # cheapest doubt-resolving step
    return Verdict(verdict, chain.render(), belief.explain())
```

Two implementations of `planner.next_best`, selectable by flag:

- **`greedy` (default, ship this):** deterministic. For the current hypothesis, each candidate action has a precomputed *expected information gain* and a *cost*; pick `argmax(gain / cost)` among actions not yet run and affordable. Transparent, fast, trivially testable — ideal for a live demo.
- **`llm` (optional depth):** an LLM planner receives the belief state + available actions + costs and returns the next action with a one-line rationale. Same interface, so it drops in without touching the loop. Keep it behind a flag; the greedy planner is the safe default on stage.

### 5.2 Policy / evidence-cost model (`policy/policy.yaml`)

```yaml
thresholds:
  allow_below:   0.15    # P(fraud) below → ALLOW
  decline_above: 0.80    # P(fraud) above → DECLINE
  # between the two → CHALLENGE

budgets:
  default_ms: 1500       # wall-clock ceiling
  high_value_ms: 3000

actions:                 # cost = normalized (latency, money, user-friction)
  number_verify:   { cost: 1, friction: 0, gain: { number_match: 0.40 } }
  sim_swap:        { cost: 2, friction: 0, gain: { takeover: 0.55 } }
  device_swap:     { cost: 2, friction: 0, gain: { mule: 0.45 } }
  location_verify: { cost: 3, friction: 0, gain: { takeover: 0.35, mule: 0.30 } }
  reachability:    { cost: 2, friction: 0, gain: { botfarm: 0.40 } }
  roaming:         { cost: 2, friction: 0, gain: { roaming_network: 0.35 } }
  step_up_otp:     { cost: 4, friction: 5, gain: { number_match: 0.60 } }  # last resort

hypotheses:
  account_takeover: { priors: { sim_swap: high, location: high } }
  mule:             { priors: { device_swap: high, reachability: high } }
  legit_thin_file:  { inclusion: { sim_tenure: positive, location_stable: positive } }
```

The cost model is the artifact you tune in W1–2; everything downstream reads from it.

---

## 6. Data model — the chain

```python
class EvidenceLink(BaseModel):
    step: int
    api: str                     # "SIM Swap"
    signal: Signal               # SIM_STABLE, SIM_SWAPPED, ...
    result: Literal["PASS","FLAG","INFO"]
    detail: str                  # "swap detected 41 min ago"
    consent_basis: str           # "NaC authorization / end-user consent"
    latency_ms: int
    at: datetime

class Verdict(BaseModel):
    decision: Literal["ALLOW","CHALLENGE","DECLINE"]
    confidence: float
    hypothesis: str
    chain: list[EvidenceLink]    # Human → SIM → Device → Location → History
    reason: str                  # plain-language explanation
    chain_id: str

class Chain(BaseModel):
    id: str
    verdict: Verdict
    signed: bytes | None         # Ed25519 signature (evidence vault, Tier 2)
```

`chain.render()` produces the human-readable "isnad" — the ordered links with timestamps that appear on screen and in the API response.

---

## 7. External API surface

All routes under `/v1`, API-key auth (`Authorization: Bearer <merchant_key>`), JSON, idempotency via `Idempotency-Key` header.

### `POST /v1/verify` — the one call
```jsonc
// request
{
  "phone_number": "+9627xxxxxxxx",
  "context": {
    "event": "checkout",          // signup | checkout | payout | password_reset
    "amount": { "value": 4200, "currency": "USD" },
    "payment_method": "cod",
    "account_age_days": 0,
    "claimed_location": { "lat": 31.95, "lon": 35.91, "radius_m": 2000 }  // optional
  },
  "options": { "return_chain": true }
}
// response
{
  "decision": "DECLINE",
  "confidence": 0.86,
  "hypothesis": "account_takeover",
  "reason": "SIM swapped 41 min ago; device new today; not at claimed address.",
  "chain_id": "chn_01J...",
  "chain": [
    { "step": 1, "api": "Number Verification", "result": "PASS", "detail": "MSISDN matches session" },
    { "step": 2, "api": "SIM Swap", "result": "FLAG", "detail": "swap 41 min ago" },
    { "step": 3, "api": "Device Swap", "result": "FLAG", "detail": "new handset today" },
    { "step": 4, "api": "Location Verification", "result": "FLAG", "detail": "not at claimed address" }
  ]
}
```

### `GET /v1/chains/{chain_id}` — replayable evidence (dispute resolution)
### Number Verification consent flow
`POST /v1/consents/number-verification` returns a short-lived `consent_id` and
`authorization_url`. NaC redirects to
`GET /v1/consents/number-verification/callback?code=...&state=...`; the callback
stores only the resulting authorization state. After the status is `AUTHORIZED`,
the merchant calls `POST /v1/consents/{consent_id}/verify` to resume the original
request with the consent token. `GET /v1/consents/{consent_id}` exposes status but
never exposes the token.

### `POST /v1/reverse-verify` — **Reverse Isnad**: verify a *caller* to a customer
Same engine, direction flipped: input is the calling party's number + the customer being called; returns whether the caller is a genuine, network-attested party.
### `POST /v1/sessions` / `GET /v1/sessions/{id}` / `DELETE /v1/sessions/{id}` — **Trust-with-a-TTL**: subscribe to SIM/device change for a session; revoke live if signals change.
### `GET /v1/console/stream` (WS/SSE) — live agent event stream for the demo console.

Standard error model: `400` validation, `401/403` auth, `409` idempotency conflict, `422` unverifiable (e.g. no network consent), `503` provider unavailable — always with a machine code + message.

---

## 8. Step-by-step build plan (mapped to the 10 weeks)

### Phase 0 — Foundations (W1)
1. Create repo, `pyproject.toml`, pre-commit (ruff, black, mypy), CI (pytest on push).
2. Scaffold FastAPI app, health check, settings, docker-compose (api + Postgres + Redis).
3. Register on the **Nokia NaC developer portal**; obtain sandbox credentials; add `network-as-code` SDK; confirm one simulated call end-to-end (`number_verify` on a test device).
4. Define `EvidenceProvider` Protocol and the `EvidenceLink`/`Verdict`/`Chain` models.

### Phase 1 — Policy engine + cost model (W1–2) *(brief milestone W1–2)*
5. Implement `policy/engine.py`: load `policy.yaml`, expose `budget_for`, `thresholds`, `decide`.
6. Implement `agent/belief.py` (prior + Bayesian-style update per signal) and `hypothesis.py`.
7. Unit-test the cost model: given hypotheses and signals, assert the chosen action order and verdict. This is where "cheapest evidence first, escalate on suspicion" becomes concrete.

### Phase 2 — Providers + CAMARA integration (W3–5) *(brief milestone W3–5)*
8. Build `MockProvider` with scriptable scenarios (deterministic pass/flag per API) — unblocks all downstream work without the network.
9. Build `NacProvider`: wrap each CAMARA API via the SDK; implement the Number Verification authorization-code callback and one-time token handoff; normalize each response to `EvidenceLink`.
10. Map failure modes (no consent, device unreachable, provider timeout) to normalized `INFO`/error links so the agent degrades gracefully.
11. Contract tests: the same scenario suite runs against both providers and must produce the same verdicts.

### Phase 3 — Investigator agent (W3–5, parallel)
12. Implement `planner.next_best` (greedy) and the `investigate()` loop.
13. Wire the event emitter (`events.py`) so every step publishes to Redis → console stream.
14. Implement `choreograph_stepup` for the CHALLENGE branch (cheapest doubt-resolving step before any OTP).
15. Add the optional `llm` planner behind `ISNAD_PLANNER=greedy|llm`.

### Phase 4 — External API + chain (W6–7) *(brief milestone W6–7)*
16. Implement `/v1/verify`, `/v1/chains/{id}`; API-key auth, rate limiting, idempotency.
17. Implement `chain/builder.py` render + Postgres persistence (store chains, not raw signals).
18. Publish OpenAPI docs; write a minimal merchant SDK snippet (Python + cURL) for the pitch.
19. Implement `/v1/console/stream` and the terminal-style console UI in `demo/console/`.

### Phase 5 — Tier-1 features (W6–7)
20. **Session TTL / revocation:** `/v1/sessions/*` — subscribe to SIM Swap / Device Swap for the session; background task revokes on change; console shows the session dying live.
21. **Reverse Isnad:** `/v1/reverse-verify` — reuse the engine with a caller-side hypothesis set.

### Phase 6 — Red-team & hardening (W8) *(brief milestone W8)*
22. Team runs adversarial scenarios (swapped SIM, mule device, bot farm, impossible travel, thin-file-but-legit) against the system; log every miss.
23. Tune `policy.yaml` thresholds/costs from red-team results; add regression tests for each caught case.
24. Security pass: secret handling, token TTLs, PII minimization audit (confirm no raw location/MSISDN persisted), rate-limit + abuse tests.

### Phase 7 — Demo & submission (W9–10) *(brief milestone W9–10)*
25. Freeze four scripted scenarios (Acts I–IV) as `tests/scenarios/` fixtures that drive the *real* engine via `MockProvider` — the demo runs the production code path, only the provider is swapped.
26. Rehearse the live console timing; record the filmed three/four-act demo.
27. Finalize README, architecture diagram, and API docs for submission.

---

## 9. Testing strategy

- **Unit:** policy engine, belief updates, planner selection (deterministic, no network).
- **Contract:** one scenario suite, run against `MockProvider` and `NacProvider` sandbox — verdicts must match.
- **Scenario/E2E:** Acts I–IV as full `/v1/verify` calls asserting decision + chain shape.
- **Adversarial (W8):** red-team cases become permanent regression tests.
- **Load (light):** confirm p95 latency under the `default_ms` budget with concurrent verifies.

---

## 10. Demo/production parity (why this design wins on stage)

The stage demo calls the exact same `/v1/verify` endpoint and the exact same agent loop as production; only `ISNAD_PROVIDER` differs (`mock` on stage for determinism, `nac` for a live sandbox device). Judges see the real decision engine reason in real time — the choice of which API to call next is visibly the agent's, satisfying the "agent-initiated decision inputs, not user-triggered buttons" requirement.

---

## 11. Milestone checklist

- [ ] W1 — repo, CI, NaC sandbox, one live simulated call, core models
- [ ] W2 — policy engine + cost model + belief, unit-tested
- [ ] W3–5 — MockProvider, NacProvider (consent auth), agent loop, contract tests green
- [ ] W6–7 — `/v1/verify` + chain persistence + console stream + session TTL + Reverse Isnad
- [ ] W8 — red-team, threshold tuning, security/PII audit
- [ ] W9–10 — four scripted acts, filmed demo, docs, submission

---

## Sources

- [Nokia Network as Code — developer portal](https://networkascode.nokia.io/)
- [Nokia Network as Code SDKs (GitHub, Apache-2.0)](https://github.com/nokia/network-as-code-sdks)
- [Network as Code — getting started / API Hub](https://networkascode.nokia.io/docs/getting-started)
- [CAMARA Project — API overview](https://camaraproject.org/api-overview/)
- [CAMARA — SIM Swap](https://camaraproject.org/sim-swap/) · [Number Verification](https://camaraproject.org/number-verification/) · [Device Swap](https://camaraproject.org/device-swap/) · [Location Verification](https://camaraproject.org/location-verification/)
