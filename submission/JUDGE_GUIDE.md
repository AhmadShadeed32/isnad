# Judge guide — testing Isnad from scratch

**MENA Ignite Hackathon 2026 · Theme 4 · Team Isnad**

Everything below runs on your own machine, offline, with no Nokia or Google
credentials. Total time: about **15 minutes**, or **3 minutes** for steps 1–3
alone. Each step lists what you should see, so a mismatch is a finding, not a
guess.

If anything here does not behave as written, that is a bug and we want to know.

---

## Before you start

You need **Python 3.11** and about 400 MB of disk. Check the version:

```bash
python3.11 --version
```

If that fails, install Python 3.11 (`brew install python@3.11` on macOS,
`apt install python3.11 python3.11-venv` on Debian/Ubuntu) and try again.
Isnad's CI runs on 3.11; other versions are untested.

Clone and enter the repository:

```bash
git clone https://github.com/AhmadShadeed32/isnad.git
cd isnad
```

---

## Step 1 — Install (about 2 minutes)

```bash
make setup
```

This creates `.venv311/` and installs the runtime and development
dependencies. It touches nothing outside the repository directory.

**Expect:** the script prints the Python version it used and ends with
`Done. Activate with: source .venv311/bin/activate`.

---

## Step 2 — Start the demo

```bash
make judge
```

**Expect** four URLs printed, then `Application startup complete.`

```
Judge Mode  http://127.0.0.1:8010/judge
Lab         http://127.0.0.1:8010/lab
Console     http://127.0.0.1:8010/console
API docs    http://127.0.0.1:8010/docs
Planner: greedy (deterministic). Use 'make judge-ai' for the Gemini agent.
```

Leave this running and use a second terminal for the command-line steps.

> **Port 8010 already busy?** Run `make judge PORT=8011` and substitute 8011
> everywhere below.
>
> **What is that long hex string in the Makefile?** `ISNAD_VAULT_TRUSTED_PUBLIC_KEYS`
> is the *public* half of the Ed25519 key that signed the bundled caller
> registry (`app/registry/registry.yaml.sig`). Pinning it lets a fresh clone
> verify that file. It is not a credential and there is nothing secret about it.
> No private key ships in this repository; `make judge` generates its own on
> first run, under `.isnad/demo-vault-key.pem`.

---

## Step 3 — The core demo: a replaced SIM (2 minutes)

Open <http://127.0.0.1:8010/judge>.

The scenario: Noura replaced her SIM card, then placed a 1,500 USD
cash-on-delivery order on a brand-new account. A rule that declines every SIM
change loses her — and most people who replace a SIM simply lost a phone.

Press **Investigate the SIM change** and watch the trace build. It is paced at
650 ms per check so it is readable; that pacing is presentation, not operator
latency.

**Expect, in order:**

| What appears | Why it matters |
| --- | --- |
| `Agent selects Number Verification` with a rationale and `budget 12` | The agent's choice is shown, not hidden behind "AI" |
| ✓ Number Verification — number matches | Cheapest identity check first |
| `Agent selects SIM Swap`, then an **Operator change date** row | A second billable call, shown as its own cost |
| ! SIM Swap — swap inside the last 240 h | The adverse fact. It is not concealed or averaged away |
| ✓ Device Swap — no swap | Corroboration: same handset, new SIM |
| ✓ Location Verification — at the claimed location | Boolean against her own claim; no coordinate is stored |
| Device Roaming Status — roaming | Budget now exhausted; the agent stops |
| **Additional verification needed**, policy score **0.322** | CHALLENGE, with the thresholds (0.15 / 0.80) stated on screen |

Read the verdict paragraph. It separates supporting evidence from adverse
evidence and says explicitly that Isnad has *not* sent a one-time code — the
merchant runs their own step-up.

**The point of this step:** the SIM swap is real and it stays in the chain. The
engine still declines to decline, because three other links corroborate the
customer. That is the difference between an investigation and a rule.

---

## Step 4 — Prove the receipt is tamper-evident (3 minutes)

Under **Technical and audit details**, press **Check Ed25519 signature**.

**Expect:** `✓ Signature valid`.

Now do it yourself, offline, without trusting our page. Copy the `chain_id`
from the receipt (or from the API response in step 6), then:

```bash
CHAIN=chn_...                                    # paste yours
curl -s "http://127.0.0.1:8010/v1/receipts/$CHAIN" -o receipt.json
.venv311/bin/python scripts/verify_receipt.py receipt.json
```

**Expect:**

```
VALID — signature matches the payload, under the supplied public key
This proves issuance and integrity at signing time only, not current status or network truth.
```

Now break it. Change one word inside the signed payload:

```bash
python3 -c "
import json; d=json.load(open('receipt.json'))
d['signed_payload']=d['signed_payload'].replace('CHALLENGE','ALLOW',1)
json.dump(d,open('receipt-tampered.json','w'))"
.venv311/bin/python scripts/verify_receipt.py receipt-tampered.json
```

**Expect:** `INVALID — signature does not match the payload`, exit code 1.

`scripts/verify_receipt.py` makes no network call and reuses no server-side
trust decision. Note what the tool refuses to overclaim: a valid signature
proves *we issued exactly these bytes*. It does not prove the operator told us
the truth. A signed mock receipt is still mock, and the page says so.

---

## Step 5 — Compare against a clean customer (1 minute)

Back on `/judge`, press **Try a clean checkout**.

**Expect: Proceed** (an ALLOW) after **two** checks instead of five — Number
Verification and SIM Swap, both clean. The agent stopped early because policy
was already satisfied. A **Continue trust after checkout** panel also appears,
offering a short continuity session; it is labelled demo-only, because a live
deployment would wait for a real network signal instead of a simulated one.

That is the commercial argument in one click. A fixed pipeline runs every API
on every request; at pennies per call against thin COD margins, that pricing
does not survive contact with a real merchant. Budgeted selection does.

Then press **Show an unresolved-evidence case**.

**Expect: Additional verification needed** — a CHALLENGE at grade UNRESOLVED,
not a DECLINE. Read the paragraph carefully:

> This is 'we could not check', NOT 'the check failed'.

Consent was withheld on one link, the provider errored on another, and a third
produced no evidence. A customer whose operator did not answer has not failed
anything, and Isnad refuses to say they did. Every unresolved link is listed by
name with its own reason.

---

## Step 6 — The API a merchant would actually call (1 minute)

```bash
curl http://127.0.0.1:8010/v1/verify \
  -H 'Authorization: Bearer demo-merchant-key' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: judge-test-1' \
  -d '{
    "phone_number": "+99999991006",
    "context": {
      "event": "checkout",
      "payment_method": "cod",
      "account_age_days": 0,
      "amount": {"value": 1500, "currency": "USD"},
      "claimed_location": {"lat": 31.9539, "lon": 35.9106, "radius_m": 2000}
    }
  }'
```

**Expect:** `"decision": "CHALLENGE"`, `"chain_grade": "DEGRADED"`,
`"confidence": 0.322`, `"hypothesis": "account_takeover"`, and a `chain` array
where every link names its API, result, signal, consent basis, source, latency
and log-odds contribution.

Run the identical command a second time. **Expect the identical `chain_id`** —
the idempotency key replays the stored result rather than paying for the
provider calls again. Change the amount while keeping the key and you get
**409**.

`confidence` is a legacy field name for an uncalibrated policy score, not a
fraud probability. See [`docs/RISK_SCORE.md`](../docs/RISK_SCORE.md).

Interactive OpenAPI is at <http://127.0.0.1:8010/docs> (demo mode only).

---

## Step 7 — The AI agent layer, with Gemini in the seat (2 minutes, optional)

Steps 3–6 use the deterministic `greedy` planner so your results match this
document byte for byte. To watch the model choose instead, you need a free
Google AI Studio key from <https://aistudio.google.com/apikey>.

Stop the server (Ctrl-C), then:

```bash
export ISNAD_GEMINI_API_KEY=your-key-here
make judge-ai
```

Run the SIM-change investigation again.

**Expect:** the trace header now reads `planner: llm`, and each
`Agent selects …` row carries the model's own rationale instead of the greedy
heuristic's fixed sentence. The verdict is reached the same way — the model
picks *which evidence to buy*; policy alone decides what the evidence means.

**No key? Nothing breaks, and nothing lies.** Missing credentials, a transport
failure, an empty answer or a hit call ceiling all fall back to greedy, and the
verdict records which strategy actually ran. A run never claims an LLM chose
when it did not.

If you would rather not spend a key at all, a recorded Gemini run is committed
at [`docs/nac/observations/2026-09-07-gemini-rehearsal.json`](../docs/nac/observations/2026-09-07-gemini-rehearsal.json)
— two model selections, both labelled `planner: llm`, with the model's own text
and a note on how to read it.

---

## Step 8 — Verify our claims about Nokia (2 minutes)

We claim recorded HTTP calls to Nokia's hosted simulator. Check them:

```bash
cat docs/nac/observations/README.md
wc -l docs/nac/observations/2026-09-06-hosted-simulator.jsonl   # 14
```

**Expect** 14 JSON lines, one per attempt against
`network-as-code.p-eu.apihub.nokia.io`, each with operation, path, UTC
timestamp, masked number, HTTP status, duration and normalised result.
**Including the failures** — a 422, a 503, and a 400 from an out-of-range date.

Two things in that file are worth a judge's minute, because we wrote them down
rather than cleaning them up:

1. For the same subscriber, `device_swap` answered *swapped* while
   `device_swap_date` returned a date nineteen days earlier. The simulator's
   boolean is scenario-driven and not derived from its own date. Isnad
   therefore never presents the date as the reason the boolean is true.
2. On that batch our correlator IDs were generated locally and never sent, so
   the operator never saw them. The runner now threads the correlator into
   every operation whose CAMARA contract accepts one, and a test asserts it:
   `tests/test_nac_demo_probe.py::test_the_recorded_correlator_is_the_one_the_operator_actually_saw`.

The full API-by-API breakdown is in
[CAMARA_API_USAGE.md](CAMARA_API_USAGE.md).

---

## Step 9 — Run the tests and the reproducible experiments (4 minutes)

```bash
.venv311/bin/python -m playwright install chromium    # once
make test
```

**Expect:** `1310 passed` in roughly 160 seconds, including Playwright coverage
of both English and Arabic. Three Starlette deprecation warnings are known and
harmless.

For a backend-only run with no Chromium needed: `make test-fast` →
`1245 passed` in about 25 seconds.

```bash
.venv311/bin/python scripts/evidence_pack.py --output-dir /tmp/isnad-evidence
```

**Expect:** five offline scenarios, each with its evidence chain and a
recomputed Ed25519 signature check. All five report `valid`. Read
`/tmp/isnad-evidence/evidence-pack.md`.

```bash
.venv311/bin/python scripts/independent_evaluation.py
```

**Expect:** 13 authored cases, three strategies, and

```
isnad-greedy                  13/13   7/13 (53.8%)  6/13 (46.2%)   4   0   49/3.77
corroboration-aware-rules     13/13   5/13 (38.5%)  8/13 (61.5%)   0   0   78/6.00
full-evidence-same-policy     13/13   6/13 (46.2%)  7/13 (53.8%)   3   0   78/6.00
```

**49 provider operations versus 78.** The evaluation also prints four cases
where the greedy planner disagrees with the authored expectation, three of them
by being less conservative than the rule-based comparator. That output is not
suppressed. The expectations are synthetic; nothing here measures real fraud
outcomes, and we would not claim otherwise on a slide.

---

## Also worth a look, if you have time

| Where | What |
| --- | --- |
| The language switcher on `/judge` | The whole interface in Arabic, RTL, including the verdict prose. Arabic wording is a draft pending native review |
| <http://127.0.0.1:8010/lab> | Recorded cases replayed against alternative strategies. Selecting a recording makes no operator or model calls |
| <http://127.0.0.1:8010/console> | The full operator console: live SSE trace, caller screening, continuity sessions, network conditions |
| The **Network conditions** panel on `/judge` | Congestion Insights, deliberately quarantined from the verdict. It explains a slow measurement; it is never a fact about a person |
| `app/policy/policy.yaml` | Every weight, cost, threshold and budget in one readable file. Change a number, restart, watch the verdict move |

---

## What we have not proven

Stated plainly, because a judge who finds these unnamed is right to discount
everything else:

- **A physical handset completing an operator consent round trip.** The consent
  route sequence, replay controls and recovery are automated against a local
  fake operator; a real SIM on a real network is not.
- **A congestion subscription create-and-callback cycle.** It needs a
  registered public HTTPS callback. `congestion_list` returned 200 with an
  empty collection; no subscription has been created.
- **Measured fraud accuracy.** Every number in this repository is either a
  reproducible arithmetic result or a synthetic scenario. None of it is a
  measurement of real fraud, and the risk score is uncalibrated by construction.

What we would need next, in order: a supported subscriber and a registered
HTTPS callback for the operator flow, then a merchant's appropriately handled
outcome data to calibrate against real decisions.

---

## Cleaning up

Ctrl-C the server. The demo wrote `isnad-demo.db*` and
`.isnad/demo-vault-key.pem` inside the repository directory and nothing else.
Delete the directory and it is gone.
