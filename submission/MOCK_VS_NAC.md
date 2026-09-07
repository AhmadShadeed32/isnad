# Why the demo runs on mock, and how close mock is to Nokia

Short version: **the demo swaps the operator's answers, and nothing else.** The
investigator, the planner, the policy engine, the normalization layer, the
signing vault and the UI are the same objects on the same code path whether the
answer came from Nokia or from a fixture. And a fixture is not allowed to say
anything the network has not been recorded saying.

This document is precise about where that stops being true, because the whole
project is an argument about provenance and it would be absurd to be vague here.

---

## Why not just demo against Nokia live

Four reasons, in the order they matter.

1. **A demo that depends on someone else's network fails on stage.** The
   hackathon's own Resource & Tooling Guide says it plainly: *"Cache demo data.
   Live API calls fail at the worst moment; a recorded fallback keeps the demo
   running."* A judge following `submission/JUDGE_GUIDE.md` at midnight with bad
   hotel wifi gets the same result as a judge on a conference stage.
2. **A judge needs a result they can check against a written expectation.** The
   guide states the expected decision, grade and score at every step. That is
   only honest if the run is deterministic. Live answers move — Nokia's
   simulator regenerates its SIM-swap date relative to the request, so no fixed
   date can be asserted in a script or a caption.
3. **Live calls are billable and rate-limited.** Judges should be able to run
   the demo as many times as they like, from a clean clone, without a Nokia
   account or our credentials.
4. **We would have to ship a credential to make it work.** No private key,
   Nokia key or Gemini key is in this repository, and none will be.

What we *did* do live is recorded rather than demonstrated: 14 authenticated
calls to Nokia's hosted simulator on 6 September, failures included, in
[`docs/nac/observations/`](../docs/nac/observations/). Those exist so the
choice above costs you no evidence.

---

## What is actually shared between mock and Nokia

### One interface

Every evidence source implements the same `EvidenceProvider` protocol in
[`app/providers/base.py`](../app/providers/base.py):

```python
async def gather(self, action: Action, request: VerificationRequest) -> EvidenceLink
async def enrich_timing(self, action, request, signal) -> EvidenceTiming
```

The agent never sees a raw CAMARA payload. It receives a normalized
`EvidenceLink`, so no coordinate and no raw phone metadata reaches the reasoning
layer or is persisted — under mock *or* under Nokia. Selecting a provider is one
environment variable; nothing downstream knows which one answered.

### One vocabulary, and it came from the network

[`app/providers/vocabulary.py`](../app/providers/vocabulary.py) holds every
sentence an evidence link may carry. Both `mock.py` and `nac.py` call the same
`detail_for(signal)` to produce the text a judge reads on screen.

A mock scenario is therefore **not prose**. It is a mapping of action to
`(Result, signal)`:

```python
_GHOST: Scenario = {
    Action.NUMBER_VERIFY:  (Result.PASS, "NUMBER_MATCH"),
    Action.SIM_SWAP:       (Result.FLAG, "SIM_SWAPPED"),
    Action.DEVICE_SWAP:    (Result.FLAG, "DEVICE_SWAPPED"),
    ...
}
```

The scenarios differ only in *which checks come back adverse*. They all draw
from the same fixed sentence table — `vocabulary.SPEAKABLE_SIGNALS` is 21
signals, of which 3 are marked unbacked and may never be emitted. A fixture
author cannot write a more convincing sentence, because they cannot write a
sentence at all.

### The vocabulary is constrained by what Nokia actually returned

This is the part worth checking yourself. `docs/nac/*.json` holds one recorded
response per action from the 30 August sandbox run, each with the SDK version,
the RapidAPI host and a capture timestamp:

```json
{
  "action": "sim_swap", "api": "SIM Swap",
  "sdk": "network-as-code", "sdk_version": "10.0.0",
  "captured_at": "2026-08-30T12:07:22.145633+00:00",
  "normalized": { "result": "Result.FLAG", "signal": "SIM_SWAPPED",
                  "detail": "recent SIM swap detected", "source": "nac" }
}
```

Four tests bind the mock to those recordings, and they fail the build:

| Test | What it forbids |
| --- | --- |
| `test_signals_match_the_captured_nac_responses` | A fixture signal that no recorded Nokia response returned |
| `test_a_fixture_exists_for_every_action` | Shipping a new CAMARA call with no recorded response |
| `test_the_provider_still_normalizes_the_observed_response` | The adapter drifting from what the recording says it produced |
| `test_swap_details_carry_the_window_not_a_timestamp` | A fixture claiming precision CAMARA does not offer |

Run them:

```bash
.venv311/bin/python -m pytest -q tests/test_nac_contract.py tests/test_provider_vocabulary.py
```

### The mock inherits Nokia's limitations, not just its answers

This is the strongest evidence that the fixtures were written from real
responses rather than from imagination — the awkward parts survived.

- **SIM Swap and Device Swap answer a boolean against a window, not a
  timestamp.** No link may say "swapped 41 minutes ago" or "SIM active 6
  years". The mock says `SIM swap inside the last 240 h` because 240 h is the
  `max_age` we sent. A test enforces it.
- **The change date is a second billable call**, not a field of the first
  answer. The judge trace shows it as its own row with its own cost, under
  mock exactly as it would bill under Nokia.
- **The date and the boolean may disagree**, because on the hosted simulator
  they did — the `device_swap` boolean said *swapped* while `device_swap_date`
  returned a date nineteen days earlier. So the UI shows both with separate
  provenance and never presents the date as *why* the boolean is true.
- **How far back the operator looked is often unknown.** `monitoredPeriod` was
  absent from the real response, so the mock displays unknown-horizon rather
  than "no change since".
- **Device Intelligence returns unavailable.** The sandbox capture came back
  `EVIDENCE_UNAVAILABLE`, so `mock.py` hard-codes unavailable and
  `test_device_intelligence_is_never_a_verdict` forbids any scenario from
  asserting a reputation. A convenient fiction was available here and is
  refused.
- **Signals with no CAMARA source cannot be emitted at all.**
  `UNBACKED_SIGNALS` — `DEVICE_TRUSTED`, `DEVICE_RISKY`,
  `REACHABLE_BOTPATTERN` — are priced in policy so a future provider inherits a
  weight, and nothing may produce them today.

### Every row says so on screen

No inference required. Under mock, every evidence row in the UI is stamped
`SIMULATOR · mock fixture`, the header carries `SIMULATOR · mock provider ·
stage mode`, and the receipt page says a signed mock receipt is still mock.

---

## Where mock is *not* the same as Nokia

Stated plainly. If you only read one section, read this one.

| | Mock | Nokia |
| --- | --- | --- |
| **Truth of the answer** | Authored to tell a story | Whatever the operator says |
| **Latency** | Scripted, plus 650 ms of deliberate readability pacing in Judge Mode | Real, and observed at 324–1821 ms on the hosted simulator |
| **Failure modes** | Only the ones we scripted | Timeouts, 422, 503, quota, entitlement, partial outages |
| **Consent** | Simulated basis string | A real OAuth/OIDC round trip to a real handset |
| **Coverage** | Every action answers | Device Intelligence has no adapter; several APIs are unexercised |

**"Identical" is the wrong word and we will not use it.** The correct claim is:
*the same code path, the same interface, the same sentence vocabulary, and
fixtures that are contract-tested against recorded Nokia responses — carrying
answers we chose.* The engine cannot tell the difference. A judge can, because
we label it.

A third provider, `nac_fake`, sits between the two: it speaks the **real
OAuth/OIDC consent contract** against `demo/fake_operator/` without leaving
localhost. That is how the consent journey — single-use callbacks, owner
binding, replay refusal, expiry, completion recovery — is tested without a
handset. It is a contract test, not a handset trial, and it is not proof that a
physical SIM completes the flow.

---

## Check it in ninety seconds

```bash
# The fixtures are bound to recorded Nokia responses
.venv311/bin/python -m pytest -q tests/test_nac_contract.py \
  tests/test_provider_vocabulary.py tests/test_consent.py \
  tests/test_s9_consent_replay.py tests/test_consent_contract.py
# -> 70 passed

# What Nokia actually returned, one file per action
cat docs/nac/sim_swap.json

# The only sentences any provider may speak
sed -n '1,40p' app/providers/vocabulary.py

# The mock's scenarios: signals, never prose
grep -n "_GHOST" -A 12 app/providers/mock.py
```

## Switching providers

One environment variable. Nothing else in the application changes.

| `ISNAD_PROVIDER` | What answers | Needs |
| --- | --- | --- |
| `mock` | Authored fixtures through the real engine | Nothing. This is the demo |
| `nac_fake` | Local fake operator speaking the real consent contract | `demo/fake_operator` on 8801 |
| `nac` | Nokia Network-as-Code | A Nokia key, supported subscribers, and demo mode off |
| `hybrid` | Provider-level test seam. **Selective-live is retired** — a non-empty `ISNAD_LIVE_EVIDENCE_*` allowlist is refused at startup, so this can never reach the network | — |
