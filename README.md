<div align="center">

# Isnad

### Network-verified trust decisions, with the chain of evidence attached

[![Verify](https://github.com/AhmadShadeed32/isnad/actions/workflows/ci.yml/badge.svg)](https://github.com/AhmadShadeed32/isnad/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)
![CAMARA](https://img.shields.io/badge/CAMARA-SIM%20Swap%20%C2%B7%20Number%20Verification-0A7CBC)
![Ed25519 signed](https://img.shields.io/badge/receipts-Ed25519%20signed-4C1)

</div>

## The customer this is built for

She loses her phone and replaces her SIM. Her bank sees a SIM change, the card
network sees a new device, the merchant sees a first-time customer paying on
delivery — and every one of those systems does the safe thing and says no.
**The signal that catches an account takeover is the same signal a stolen phone
produces.**

Isnad decides how much network evidence a risky interaction actually needs,
buys only that much, and returns `ALLOW` / `CHALLENGE` / `DECLINE` together with
the ordered, signed chain of evidence that produced it.

This is a hackathon prototype, and the README is written to be *checked*: every
claim below names the script that reproduces it, and every surface labels where
its evidence came from.

---

## Quick start

```bash
pip install -e ".[dev]"
pytest -q
python scripts/evidence_pack.py     # writes JSON + Markdown reports to .isnad/
```

Then open the console:

```bash
ISNAD_DEMO_MODE=true ISNAD_MERCHANT_API_KEYS=demo-merchant-key \
  uvicorn app.main:app --host 127.0.0.1 --port 8010 --proxy-headers
```

[Judge Mode](http://127.0.0.1:8010/judge) runs the 90-second customer checkout —
evidence trace, signed receipt, and the simulator-only trust-revocation beat.
[The full console](http://127.0.0.1:8010/console) plays every stage act. Both
surfaces show which provider is answering.

---

## The idea, in one line

**"We could not check" and "the check failed" are two different facts** — and
every stack that collapses them into one score manufactures false declines.
Merchants falsely decline **2–10% of all eCommerce orders, and one in five
decline more than 10%** (Merchant Risk Council, *Global eCommerce Payments &
Fraud Report* 2024/25 — an industry body surveying merchants, not a vendor
selling the fix).

So Isnad grades every chain on what it could actually establish:

| Grade | Means |
| --- | --- |
| `ATTESTED_FULL` / `ATTESTED_PARTIAL` | The network answered. |
| `UNRESOLVED` | The network could not be asked, or consent was withheld. |
| `DEGRADED` | Answered, but with evidence missing or stale. |
| `REFUTED` | The network answered against the subject. |

An `UNRESOLVED` link stays unresolved. It can never later be read as a pass.

## Two invariants the decision flow always holds

Evidence selection is free to choose the route. It gets no vote on these:

1. **Corroborate before declining.** When belief turns adverse, an exculpatory
   check named by policy is attempted first. One adverse signal never carries a
   decline alone. *(This is the gate that saves the customer above.)*
2. **An allow rests on a network fact.** Local evidence alone cannot buy an
   `ALLOW`; the chain must hold a supporting fact the network returned. *(This
   is the gate that stops a stolen API key talking its way to an instant pass.)*

---

## Measured, not asserted

### Same verdicts, shorter route

`scripts/planner_divergence.py` reproduces this. Across the scripted scenarios,
comparing the two available decision strategies:

| Measure | Result |
| --- | --- |
| Same decision state, both planners | **12/12 chose a different next check** |
| Different evidence path | **4/5 scenarios** |
| Different verdict or chain grade | **0/5** |
| Paid network checks to reach them | **17 → 14 (−18%)** |

Policy owns the verdict; evidence selection owns the route. Five scripted
scenarios and one run — a strategy comparison, not an accuracy study.

### Against the decision rules it replaces

`scripts/false_decline_baseline.py` compares Isnad with the two rules real
systems use, on a population generated from `policy.yaml`'s own signal
vocabulary — one case per adverse signal, one per unanswerable check, every pair
of strong adverse signals, and a multi-adverse control. Both baselines are given
the **full** evidence set, not the subset Isnad chose to buy.

| Rule | False declines |
| --- | --- |
| `single-signal` — any flagged check, decline | 5 of 10 |
| `collapse-unknowns` — any flagged *or unanswered* check, decline | 10 of 10 |
| **Isnad** | **0 of 10** |

Network checks bought: run-everything **119**, Isnad **58** — **51% fewer**.

**Against a stack that scores a missing check as a failed one, Isnad avoids
ten of ten false declines while buying half the network calls.**

### The dial, and where it is set

The same harness reports the other side of the trade. Of 7 cases where two
independent checks disagree with the customer, Isnad **allows 1** at the shipped
threshold: it had already formed a confident-clean belief on cheaper evidence
and stopped, and an unbought signal cannot move a verdict. That is the budget
working as designed — and it is a dial. `--sweep` prints the curve:

| `allow_below` | false declines | corroborated-adverse allowed | checks |
| --- | --- | --- | --- |
| 0.15 (shipped) | 0/10 | 1/7 | 58 |
| 0.10 | 0/10 | 1/7 | 59 |
| 0.05 | 0/10 | 0/7 | 82 |

One line in `policy.yaml` per row — no code, no retraining. A merchant picks the
point that matches what a lost customer costs them: tightening to 0.05 closes
the last corroborated-adverse allow and buys 24 more network checks to do it.

> [!NOTE]
> Scripted fixtures over a generated population, one run. These figures compare
> decision policy against stated baselines. They are not an accuracy study and
> claim no real-world decline rate.

---

## Demo scenarios

| Scenario | What it demonstrates | Intended decision |
| --- | --- | --- |
| Act I — clean signup | A supporting network fact can avoid OTP friction. | `ALLOW` |
| Act II — takeover risk | Multiple adverse facts are corroborated before stopping a high-risk checkout. | `DECLINE` |
| Act III — thin-file customer | Stable network evidence can support a low-friction decision. | `ALLOW` |
| Act V — evidence gap | Missing consent or provider evidence is uncertainty, not a false decline. | `CHALLENGE` / `UNRESOLVED` |
| Act VI — recent SIM change | A risk signal is investigated and stepped up rather than auto-rejected. | `CHALLENGE` / `DEGRADED` |

## What makes it different

- **Evidence-aware orchestration** — Isnad chooses the next affordable, relevant
  check and stops once policy has enough. A recent SIM change gets corroborated,
  not auto-declined.
- **Honest uncertainty** — unavailable evidence or withheld consent produces
  `CHALLENGE` / `UNRESOLVED`, never a fabricated pass or failure.
- **Verifiable receipts** — chain, decision, planner label, and subject binding
  are signed with Ed25519 and can be re-checked later.
- **Trust that can expire** — an accepted session can be rechecked and revoked
  when a scripted SIM or device change occurs.

---

## Architecture

```mermaid
flowchart LR
    M[Merchant, wallet, or bank] --> API[Isnad API]
    C[Customer consent when required] --> API
    API --> I[Investigator]
    I --> P[Policy: budget, thresholds, corroboration]
    I --> L[Configured planner]
    I --> E[Evidence provider]
    E --> MOCK[MockProvider: local scripted fixtures]
    E --> NAC[Nokia Network as Code: configured CAMARA APIs]
    I --> V[Decision + ordered evidence chain]
    V --> S[Ed25519-signed evidence vault]
    S --> R[Receipt, verification endpoint, and demo console]
```

Both providers travel the same investigator path. `MockProvider` gives
repeatable local demonstrations; `NacProvider` runs against sandbox credentials
and the applicable user consent.

### The evidence pack

`python scripts/evidence_pack.py` forces the local mock provider and the
deterministic planner before application code loads, runs five scripted cases,
persists each chain, recomputes its signature, and writes:

- `.isnad/evidence-pack/evidence-pack.json` — machine-readable scenario,
  evidence, provenance, signature, and counterfactual fields.
- `.isnad/evidence-pack/evidence-pack.md` — a concise review table.

The report states on its face that it contains local fixtures only. It calls
neither Nokia Network as Code nor an external decision service.

---

## Running against the live network

`ISNAD_PROVIDER=nac` reaches Nokia Network as Code from a non-demo deployment
with generated merchant credentials, a mounted vault key, a persisted pepper,
and an HTTPS consent callback. It is billable, and it carries no public demo
token and no scripted fallback by design:

```bash
export ISNAD_MERCHANT_API_KEYS=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
export ISNAD_SUBJECT_PEPPER=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
ISNAD_DEMO_MODE=false ISNAD_PROVIDER=nac \
  ISNAD_VAULT_KEY_PATH=/absolute/persistent/vault-key.pem \
  ISNAD_NAC_REDIRECT_URI=https://isnad.example/v1/consents/number-verification/callback \
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --proxy-headers
```

A provider failure becomes unresolved evidence — it never becomes a fixture
result. The stage console stays fully scripted, so a public demo control can
never authorize live spend; recorded NaC captures may be shown beside it as
historical evidence.

## What is real, and what is scripted

| | |
| --- | --- |
| **Real** | The evidence-selection loop, policy engine, budget and early stopping, chain grading, Ed25519 signing and verification, the signed institution registry, Tier 1 screening, session revocation, and the Nokia Network as Code adapter. |
| **Real, on request** | The live NaC path above, in a non-demo deployment. |
| **Scripted** | Everything else in the demo comes from deterministic local fixtures. Every surface labels its source. |
| **Scope of the prototype** | Decision policy and provenance. Accuracy, latency, production coverage, and an operator contract are outside it. |

CAMARA maturity, read from the specification repositories rather than recalled:
SIM Swap and Number Verification are **Incubating** (both v2.1.0, Number
Insights sub-project); VerifiedCaller is **Sandbox**, 0.1.0 in its current
release with a 0.2.0 alpha in pre-release, and does not yet belong to a
sub-project. We are early to that one, not late.

## Boundaries

- **Deterministic first.** The optional remote decision service answers about
  half the time under bursty sequential calls; every failure falls back to the
  deterministic strategy, and the verdict records which strategy ran. Demos use
  the deterministic path.
- **Sourced figures only.** No MENA-specific fraud figure appears anywhere,
  because none is published. US and UK regulator data is used only where it can
  be labelled a proxy.
- **Unpriced beats guessed.** Counterfactual pricing is `null` where no
  defensible public figure exists, and renders as "not priced —
  merchant-specific".
- **A link can only say what the network said.** Every evidence sentence comes
  from one table, `app/providers/vocabulary.py`, shared by the mock and the live
  NaC adapter. CAMARA SIM Swap and Device Swap answer a boolean against the
  `max_age` we send, so a link says "SIM swap inside the last 240 h" and never
  "the swap was 41 minutes ago". A test fails the build if a fixture invents one.
- **Device Intelligence is unresolved, not trusted.** Nokia Network as Code
  exposes no device-reputation product, so the agent cannot buy that check and
  no chain carries a reputation verdict. It stays priced in `policy.yaml` for the
  provider that could one day answer it.
- **Next: consent on a handset.** Number Verification's consent round trip is
  built but not yet exercised on real hardware, so it is not presented as
  working.
- **Receipts prove issuance.** A signed receipt shows that this Isnad instance
  issued the stored chain; fixture data stays fixture data.
- **Live deployments bring their own keys.** Generate merchant keys and mount a
  persisted signing-key volume (see the command above); the sample demo key is
  public and belongs to the demo. A production consent callback needs a public
  HTTPS URL registered with the provider — localhost is for local development.

---

## Useful endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/verify` | Run a forward trust investigation. |
| `GET /v1/chains/{id}/verification` | Recompute the stored chain signature. |
| `POST /v1/reverse-verify` | Check an incoming caller's claimed identity. |
| `POST /v1/sessions` | Create a time-limited trust session that can be revoked. |
| `GET /console` | Open the local stage console. |
