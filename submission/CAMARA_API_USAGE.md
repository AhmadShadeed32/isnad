# CAMARA API usage

How Isnad consumes GSMA Open Gateway CAMARA APIs through the Nokia
Network-as-Code platform, what has been observed against Nokia's own endpoints,
and what has not.

The hackathon's mandatory requirement is that CAMARA APIs act as *trusted
real-time data sources orchestrated by an AI agent*, not as user-triggered
buttons. In Isnad **no evidence call is bound to a UI control**. Every evidence
call is selected at run time by the investigator agent from the request
context, the hypothesis it has formed, the evidence gathered so far, and the
budget it has left. Pressing a button on `/judge` starts an *investigation*;
the agent then decides what to ask the network.

The one deliberate exception proves the rule. Congestion Insights **does** have
explicit buttons on `/judge` — subscribe, forecast, last hour, delete — because
it sits outside the agent by design. It is network information, not evidence
about a person, so it is never selected as part of an investigation, never
enters the risk score, and is requested only when a human explicitly asks for
it. Nothing is sent to the operator until that button is pressed.

---

## The eight integrated APIs, and one that is not

Costs and weights are the policy surface in
[`app/policy/policy.yaml`](../app/policy/policy.yaml). Costs are normalized
policy units, not operator prices.

### Digital identity and anti-fraud

**Number Verification** — cost 1, gain 1.2
Consent-based proof that the number belongs to this device. Replaces the OTP at
signup. Consent-gated through a server-side OAuth/OIDC exchange: an opaque
single-use state, an explicit authorization screen, then a short-lived token.
Tokens are never returned in API responses and never persisted into the chain.
Almost always the agent's first selection — it is the cheapest useful identity
signal, and `numberverify_weight: 2.2` in policy encodes that preference.

**SIM Swap** — cost 2, gain 2.0
The primary account-takeover signal, and the one the lead demo is built around.
Selected when takeover suspicion is live. Optionally enriched with
`sim_swap.retrieve_date`, which is billed as a **separate operator call** and
shown as its own row so the second charge is never hidden inside the first.

**Device Swap** — cost 2, gain 1.5
The mule-phone signal, and the corroborator that saves legitimate customers: a
new SIM in an unchanged handset reads very differently from a new SIM in a new
handset. Also supports a separately billed date retrieval.

**Number Recycling** — cost 1, gain 1.1
Was this number reassigned to a different person since the account was opened?
Isnad refuses an out-of-range reference date locally rather than spending a call
to be told (see the recorded 400 below).

### Network intelligence

**Location Verification** — cost 3, gain 1.5
A boolean answer against an address the customer already claimed. **Isnad never
receives or stores a coordinate.** Without a `claimed_location` on the request
the check is skipped and zero SDK calls are made — a guarantee under test, not
a convention.

**Device Reachability Status** — cost 2, gain 1.3
Bot-farm and burner-phone patterns, selected under synthetic-identity
suspicion.

**Device Roaming Status** — cost 2, gain 1.6
Impossible-travel detection, and a stability proxy when assessing a thin-file
customer for inclusion.

**Device Intelligence** — cost 2, gain 1.4 · **no Nokia adapter**
Device reputation, intended as corroboration when device evidence is contested.
The 30 August sandbox capture returned `EVIDENCE_UNAVAILABLE`, so there is no
NaC adapter for it: `app/providers/nac.py` returns unavailable by construction
and no scenario is allowed to assert a reputation verdict. It runs under the
mock provider only. Counted separately from the eight above, and named here
because deleting it would have been tidier than keeping it and saying why.

**Congestion Insights** — no evidence cost
Deliberately **quarantined from the verdict**. A congested cell can explain a
slow or failed verification, so `/judge` shows it in a panel that states in the
UI itself that it never changes the risk score and never waives a check.
Implemented as subscription create / list / query / delete plus a callback
route in [`app/network_conditions.py`](../app/network_conditions.py).

Network conditions explain a *measurement*. They are not a fact about a human
being, and mixing the two would be the exact category error this project
exists to avoid.

---

## Orchestration: how a call gets chosen

1. **Hypothesis.** The request context sets a prior — `new account + high value
   + cash on delivery` reads as `account_takeover`. Each hypothesis names the
   actions relevant to it, so the agent never shops outside the question it is
   asking.
2. **Selection.** Gemini picks the next action or STOP, with a rationale that
   is displayed rather than summarised. Without a key, or on any failure, a
   greedy information-per-cost planner takes over. The verdict records which
   one actually ran.
3. **Gate.** Policy can require a check the model did not pick, and can refuse
   one it did. The model cannot waive a gate, change a weight, exceed the
   budget, or reach a verdict.
4. **Normalization.** Each answer becomes an evidence link with an API, result,
   signal, consent basis, source, latency and log-odds contribution.
5. **Stop.** When policy is satisfied or the budget is spent. Stopping early is
   the design goal: gather the minimum necessary evidence, not a profile.
6. **Sign.** The exact receipt bytes are signed with Ed25519.

Evidence-support rules mean a single adverse signal cannot carry a decision
alone; `default_min_links: 2` and `min_network_links_for_allow: 1` are in
policy, not in code.

---

## What has been observed against Nokia

### Hosted simulator, 6 September 2026 — 14 recorded calls

Full records: [`docs/nac/observations/2026-09-06-hosted-simulator.jsonl`](../docs/nac/observations/2026-09-06-hosted-simulator.jsonl),
with a written reading in [`docs/nac/observations/README.md`](../docs/nac/observations/README.md).
Host `network-as-code.p-eu.apihub.nokia.io`, one attempt each, no retries, 10 s
timeout. One line per attempt **including the failures**; no response bodies,
no unmasked numbers.

| Operation | Result | Status |
| --- | --- | ---: |
| `sim_swap_check` ×2 | `swapped: true` / `false` | 200 |
| `device_swap_check` ×2 | `swapped: true` / `false` | 200 |
| `sim_swap_date` | a real timezone-aware date | 200 |
| `device_swap_date` | a real date, `monitoredPeriod` **absent** | 200 |
| `congestion_list` | empty collection | 200 |
| `forwarding_unconditional` ×2 | `active: true` / `false` | 200 |
| `forwarding_unconditional` (error numbers) | documented error paths | 422, 503 |
| `number_recycling` ×2 | `recycled: true` / `false` | 200 |
| `number_recycling` (future reference date) | operator error, not a `false` | 400 |

**This is Simulator mode.** These are authenticated HTTP requests to Nokia's
hosted simulation. They are not radio measurements and not proof of live-network
entitlement.

### What those calls settled

- The catalog host answers with the headers the SDK sends. That was an open
  unknown; the host is now passed explicitly rather than assumed.
- The documented boolean scenarios match the published tables, and the
  documented error numbers return exactly 422 and 503.
- Both date operations returned real, timezone-aware values.

### What those calls contradicted, and what we changed

**The boolean and the date disagree.** For the same subscriber,
`device_swap_check` over a 24-hour window said `swapped: true`, while
`device_swap_date` reported a date nineteen days earlier. The simulator's
boolean is scenario-driven and is not derived from the date it hands back.

Isnad does not paper over this. It never computes a verdict by combining the
two as if they described one event, never presents the date as *why* the
boolean is true, and shows both with separate provenance and a note when they
disagree. The 400 on a future reference date is the reason Isnad now range-checks
dates locally instead of spending a call to be refused.

**`monitoredPeriod` was absent** from the device-date response, so the horizon
the operator actually looked back over is unknown. A null or old date is
displayed as unknown-horizon, never as "no change since".

**Our correlator IDs were generated locally and never sent** on that batch, so
the operator never saw them. Recorded rather than edited out. The runner now
threads the correlator into every operation whose CAMARA contract accepts one,
asserted by
`tests/test_nac_demo_probe.py::test_the_recorded_correlator_is_the_one_the_operator_actually_saw`.

### Sandbox captures, 30 August 2026

Per-API response captures in [`docs/nac/`](../docs/nac/), compiled into the
runtime capability manifest [`app/nac_capabilities.json`](../app/nac_capabilities.json)
with adapter version, environment scope, timestamp and an explicit coverage
caveat per capability. Number Verification's capture returned
`CONSENT_REQUIRED`, so the manifest records that the reachable/consent-required
path is verified and a consented PASS is not.

A green capture is not an uptime probe, an entitlement guarantee, or a coverage
claim. It records that one call on one date returned one signal.

---

## What has not been observed

- **Any congestion subscription create, get, query or delete**, and any
  callback delivery. `congestion_list` returned 200 with an empty collection —
  the account can read the collection and nothing is leaked — but no
  subscription has been created, because no reachable HTTPS callback is
  configured. The probe refuses to create one pointed at a destination we do
  not own.
- **Number Verification's consent round trip on a physical handset.** The route
  sequence, single-use callbacks, owner binding, replay control and completion
  recovery are automated against a local fake operator
  ([`demo/fake_operator/`](../demo/fake_operator/)), which speaks the same
  OAuth/OIDC contract without leaving localhost. That is a contract test, not a
  handset trial.
- **Anything on a live network.** Simulator and sandbox throughout.

The contract-level reconciliation between the CAMARA specifications, the Nokia
SDK surface and Isnad's adapter is in
[`docs/NAC_CONTRACT_MATRIX.md`](../docs/NAC_CONTRACT_MATRIX.md). The procedure
we would follow for a real handset is in
[`docs/HANDSET_VALIDATION.md`](../docs/HANDSET_VALIDATION.md).

---

## Reproducing this

```bash
cat docs/nac/observations/README.md
wc -l docs/nac/observations/2026-09-06-hosted-simulator.jsonl   # 14
```

With your own Nokia Network-as-Code key, the probe that produced those records:

```bash
.venv311/bin/python scripts/nac_demo_probe.py --help
```

It records every attempt including failures, masks identifiers, and refuses to
create a subscription pointed at a callback you do not control.
