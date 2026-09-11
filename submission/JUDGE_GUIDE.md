# Judge guide — testing Isnad from scratch

**MENA Ignite Hackathon 2026 · Theme 4 · Team Isnad**

## Start here: 90 seconds, nothing installed

**<https://ahmadshadeed32-isnad-trust-engine.hf.space/judge>**

> **Deployed and checked on 9 September 2026.** The page offers **Mock —
> Nokia-compatible demo** and **Real NaC — Nokia hosted simulator**. An organizer
> code unlocks real calls; both simulator scenarios passed from this deployed
> page. The 90-second story below uses the separate **Custom mock scenarios**
> group. For the paired mock/real flow, see "Choosing the evidence source"
> below. [Deployed evidence](../docs/nac/observations/2026-09-09-deployed-judge-smoke.json).

1. **Set the planner to Greedy.** Open **Demo settings — planner and your own
   Gemini key** at the top of the page and set **Planner** to
   **Greedy · deterministic**. A site Gemini key is configured there, so a fresh
   tab opens in Gemini mode and the exact numbers below will vary; the header's
   `planner:` pill always says which one is running. Greedy is deterministic and
   is what this guide's expected values are written against. *(~10 s)*
2. Under **Custom mock scenarios**, press **"Investigate the SIM change"**.
   Watch the trace fill in: each row is
   one CAMARA check, with the reason it was chosen, its source badge, and the
   risk score after it. *(~30 s)*
3. **Read the result.** **CHALLENGE**, risk score **0.322**, chain grade
   **DEGRADED**, over five checks. The SIM did change — and the handset did
   not, and the device is where the customer said it was. That is a step-up,
   not a decline. *(~20 s)*
4. **Open the signed receipt and press "Check Ed25519 signature".** It reports
   valid. Change one character of the payload and it fails. *(~30 s)*

Every operator answer in that custom story is **simulated**, and each row says so on its own
badge. A signed mock receipt is still a mock receipt: the signature proves what
Isnad issued, never that an operator told the truth.

That is the whole product. Everything below is for checking that the 90 seconds
were not a trick.

---

## The longer audit

Everything below runs on your own machine, offline. Steps 1–6 and 8–10 need no
credentials at all; step 7 needs a free Google AI Studio key. Total time: about
**20 minutes**, or **3 minutes** for steps 1–3 alone. Each step lists what you
should see, so a mismatch is a finding, not a guess.

Note the deliberate difference between the two paths: the hosted site defaults
to **Gemini** (a site key is configured), while the local `make judge` path
defaults to **greedy** so a reviewer following these steps gets a byte-identical
result every time. `make judge-ai` is the local Gemini path.

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

This creates `.venv311/` inside the repository and installs the runtime and
development dependencies into it. Nothing is installed system-wide (pip's own
download cache in your home directory is the only thing written outside).

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

Now do it yourself, offline, without trusting our page. Press **Open signed
receipt ↗** — the `chn_…` you need is the last path segment of the URL that
opens. Then:

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

Back on `/judge`, under **Other cases**, press **A clean checkout**.

**Expect: Proceed** (an ALLOW) after **two** checks instead of five — Number
Verification and SIM Swap, both clean. The agent stopped early because policy
was already satisfied. A **Continue trust after checkout** panel also appears,
offering a short continuity session; it is labelled demo-only, because a live
deployment would wait for a real network signal instead of a simulated one.

That is the commercial argument in one click. A fixed pipeline runs every API
on every request; at pennies per call against thin COD margins, that pricing
does not survive contact with a real merchant. Budgeted selection does.

Then press **Unresolved evidence**, next to it.

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

The same call against the hosted deployment, with a key you mint yourself, is
under **[Calling the hosted API](#calling-the-hosted-api)** at the end.

---

## Step 7 — The AI agent layer, with Gemini in the seat (2 minutes)

Steps 3–6 use the deterministic `greedy` planner so your results match this
document byte for byte. To watch the model choose instead, you need a free
Google AI Studio key from <https://aistudio.google.com/apikey>.

**The easy way — no restart, no environment variables.** Open **Demo settings —
planner and your own Gemini key** at the top of the `/judge` page (it is a
disclosure, closed by default so the scenario stays on the first screen), set
**Planner** to **Gemini · LLM**, then open **Gemini API key** inside it, paste
the key and press **Save key**. That is it; the next run uses the model.
Saving a key also switches the planner for you. The key panel only appears when
the deployment can honour it, and it tells you exactly what happens to your key:

> Stored in this tab’s session storage. Sent to this app’s server for model
> requests, then to Google. The app does not write it to its database,
> receipts, or logs. Calls use your saved key’s quota, or the site key when
> none is saved.

Which planner is actually running is shown outside the disclosure, in the
`planner:` pill in the page header — you never have to open anything to see
whether the model or the deterministic planner selected the checks.

**Two different retentions, and the panel's wording covers both.** In *your
browser*, the key sits in that tab's `sessionStorage` under
`isnad.byok.gemini`, so it survives a page reload and is shared with the
Console and Lab tabs of the same session — that is what makes a saved key work
across the site without retyping. It is discarded when the tab closes, or
immediately when you press **Forget key**. On the *server*, there is no
retention at all: the key arrives as one request header, lives in a
`ContextVar` reset in a `finally`, and cannot survive into the next request on
the same worker.

That server half is enforced, not just promised —
[`tests/test_request_supplied_model_key.py`](../tests/test_request_supplied_model_key.py)
asserts the key never survives into the next request, never reaches any
database table, never appears in a receipt or a response, and is refused
outright by any deployment that could spend money. The browser half is
`sessionStorage`, with the ordinary properties of `sessionStorage`.

Press **Forget key** when you are done, or just close the tab.

**Or the environment-variable way**, if you prefer. Stop the server (Ctrl-C),
then:

```bash
export ISNAD_GEMINI_API_KEY=your-key-here
make judge-ai
```

Run the SIM-change investigation again. **This is what we saw on 7 September**
(recorded at [`docs/nac/observations/2026-09-07-gemini-judge-run.json`](../docs/nac/observations/2026-09-07-gemini-judge-run.json)):

The trace header reads **`planner: llm`**, and the first row is the model's own
sentence, not a heuristic's fixed one:

> **Agent selects SIM Swap** — *"Checking for a recent SIM swap provides the
> highest relevant information value to investigate the account takeover
> hypothesis."* · `llm · budget 12`

Then watch what happens to it. The next two rows are labelled **`policy`**, not
`llm`:

> **Agent selects Device Swap** — *"corroborate before this signal alone can
> decline"* · `policy · budget 9`

The model had produced a single adverse signal. Policy would not let that
signal carry a decline on its own, so it required corroboration and the UI
names the gate rather than dressing the check up as the model's idea.

Then the model says stop:

> **Agent stops** — *"None of the remaining affordable actions are relevant to
> assessing the account takeover hypothesis."* · `llm · budget 3`

And policy overrules it:

> **Agent selects Number Verification** — *"cheapest step that could resolve
> the doubt"* · `policy · budget 3`

**That sequence is the whole architecture in four rows.** The model chooses
what evidence to buy. Policy decides what the evidence means, what may not be
skipped, and when a single adverse fact is not enough. Neither one can do the
other's job, and the trace tells you which is speaking at every step.

The verdict on that run: **CHALLENGE / DEGRADED at 0.28**, over four links,
where greedy reached CHALLENGE / DEGRADED at 0.322 over five.

**Your run may differ, and that is the honest part.** The model is not
deterministic, and which checks it buys changes the score, the number of links
and the chain grade. Greedy is the reproducible planner precisely so the rest
of this guide can state exact expected values; the model is the one that gets
to surprise you.

> **Historical observation, and its dated resolution.** An earlier run of ours
> on this same fixture bought three links and reached **DECLINE**. That
> observation is real and is kept here rather than deleted. It was possible
> because the corroboration gate only ran while the agent was still choosing
> its next action, so a run that stopped early could decline on the SIM change
> before anything corroborated it.
>
> **Resolved 8 September 2026.** The gate now runs once after every gathering
> path — early stop, exhausted budget, parallel batch, step-up alike — and an
> attempted check that answers "we could not check" no longer counts as
> corroboration. All 3,600 scripted planner paths over this fixture (every
> ordering of the six affordable checks × five stopping points) were
> re-measured: **1,508 of them bought the SIM check and saw it flag, and every
> single one ended in CHALLENGE. None reached DECLINE, and none reached ALLOW
> after seeing the flag.** The remaining paths cleared without ever buying the
> SIM check, which is a different chain rather than a different judgement of
> the same one.
>
> This bounds the deterministic paths. It is not a guarantee about a specific
> future Gemini sampling, and it is not a fraud-accuracy claim.

What does not change is the boundary — whatever the model picks, policy still
grades it, still demands corroboration before one adverse signal can decline,
and still names which of the two is speaking on every row.

**No key? Nothing breaks, and nothing lies.** Two different things happen, and
the difference matters:

- **No answer arrived** — missing credentials, a transport failure, an empty
  response, or the shared hourly model quota being exhausted. Greedy selects,
  and the row names the condition that allowed it.
- **An answer arrived and was not usable** — output that failed the schema, an
  explicit rejection, an action that is not affordable, or the per-investigation
  model call ceiling being reached. Model selection **stops**; greedy does not
  substitute for it, because something did answer and quietly overriding it
  would be the system deciding the model's rejection did not happen.

Either way the verdict records which strategy actually ran, and a run never
claims an LLM chose when it did not. See
[`app/agent/planner.py`](../app/agent/planner.py) — `LLMPlanner._ask` and
`_no_answer` are the two branches above.

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
# on a fresh Linux runner: python -m playwright install --with-deps chromium
make test
```

**Expect:** `1329 passed` in roughly 155 seconds, including Playwright coverage
of both English and Arabic. Three Starlette deprecation warnings are known and
harmless.

For a backend-only run with no Chromium needed: `make test-fast` →
`1264 passed` in about 25 seconds.

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

## Step 10 — Satisfy yourself about the mock (3 minutes)

The demo runs on authored fixtures, and you should want to know how far that
is from Nokia. The full answer is in
[MOCK_VS_NAC.md](MOCK_VS_NAC.md); here is how to check it rather than read it.

```bash
.venv311/bin/python -m pytest -q tests/test_nac_contract.py \
  tests/test_provider_vocabulary.py tests/test_consent.py \
  tests/test_s9_consent_replay.py tests/test_consent_contract.py
```

**Expect:** `70 passed`. Those tests enforce that a fixture cannot emit a signal
no recorded Nokia response returned, that every action the agent can take has a
recorded response on file, and that no fixture claims a precision CAMARA does
not offer.

Then look at what the mock is actually made of:

```bash
cat docs/nac/sim_swap.json          # what Nokia returned, 30 Aug, with SDK version
sed -n '1,40p' app/providers/vocabulary.py   # the only sentences any provider may speak
grep -n "_GHOST" -A 12 app/providers/mock.py # a scenario: signals, never prose
```

**What you should conclude:** a mock scenario is a mapping of action to
`(Result, signal)`. The sentence a judge reads comes from `detail_for()` —
the same function `nac.py` calls. A fixture author cannot write a more
convincing sentence because they cannot write a sentence at all.

**And what you should not conclude:** that mock equals live. It does not.
Mock's answers are chosen, its latencies are scripted, its failure modes are
only the ones we wrote, and its consent basis is a string rather than a round
trip. What is shared is the code path, the interface, the vocabulary and the
contract tests — the engine cannot tell the difference, and we label it so you
can.

The one detail that shows the fixtures came from real responses: the mock
inherits Nokia's *limitations*. SIM Swap answers a boolean against a window, so
no row may say "swapped 41 minutes ago". The change date is a second billable
call, shown as its own row. The date and the boolean can disagree — because on
the hosted simulator they did. Device Intelligence returns unavailable, because
the capture did, and a test forbids any scenario from inventing a reputation
verdict. Those are inconvenient, and they survived.

---

## Also worth a look, if you have time

| Where | What |
| --- | --- |
| The language switcher on `/judge` | Full RTL layout in Arabic. Honest gap: the composed verdict paragraph and evidence sentences are still English, and the page says so in its own banner — the dictionary covers authored strings, not sentences assembled from policy state |
| <http://127.0.0.1:8010/lab> | Recorded cases replayed against alternative strategies. Selecting a recording makes no operator or model calls |
| <http://127.0.0.1:8010/console> | The full operator console: live SSE trace, caller screening, continuity sessions, network conditions |
| The **Network conditions** panel on `/console` | Congestion Insights, deliberately quarantined from the verdict. It explains a slow measurement; it is never a fact about a person |
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

Ctrl-C the server. Inside the repository directory the demo wrote
`isnad-demo.db*`, `.isnad/demo-vault-key.pem`, `.venv311/` and the usual
`__pycache__/` folders — and nothing anywhere else. Delete the clone and it is
gone.

Every step in this guide was run end to end before it was written down, on
macOS with Python 3.11 — steps 1–6 and 8–10 against a clean `git clone`, and
step 7 against the same build with a real Gemini key. Nothing here is
described from reading the code.


---

## Choosing the evidence source

Deployed on the Space and exercised there on 9 September 2026. The same flow
also works on a suitably configured local instance:

1. Open `/judge`. The **Evidence source** panel sits with the run controls. It
   defaults to **Mock — Nokia-compatible demo**, and both choices are visible
   without opening anything.
2. Pick a **Nokia simulator scenario**: `+9999…1000` (both swaps occurred) or
   `+9999…1001` (neither did). These are Nokia's own documented simulator
   subscribers. The three authored stories above are now grouped separately as
   **Custom mock scenarios** — they have no Nokia scenario and are mock-only.
3. Choose **Greedy** for the expected values below, or **Gemini** to observe
   model selections. Press **Run**. In mock, no request is sent to Nokia; the
   real Nokia SDK builds the request and a local transport answers it with the
   pinned Nokia-shaped response.
4. Open **Request and response details** to see the method, path, status and
   duration of every outbound attempt. In mock it says in as many words that the
   status and timing are synthetic and not a measured Nokia latency.
5. To use **Real NaC** you need an organizer-issued access code, entered in the
   page. Selecting the option does not send anything; only the code exchange
   grants the capability, and only a run spends it. Limits are shown beside the
   selector: attempts left for your session, for the deployment this hour, and
   per run.
6. The result carries its own source, and so does the receipt: the evidence
   source and environment are **inside** the signed bytes. Change the selector
   afterwards and the completed result keeps the source it was produced with —
   the page says "Applies to the next run".

### Expected values (Greedy, either source)

| Scenario | Decision | Chain grade | Checks |
| --- | --- | --- | --- |
| `+9999…1000` both swaps | **DECLINE** | REFUTED | 2 |
| `+9999…1001` neither swap | **CHALLENGE** | DEGRADED | 2 |

`CHALLENGE` on the clean subscriber is not a bug: two checks is a thin chain,
and the grade says so. Press **Open a manual review** to complete the simulated
merchant follow-up — and then re-verify the receipt. It is byte-identical: a
passed review is a separately recorded fact, not a rewrite of the decision.

Coverage and permitted differences: [`../docs/NAC_MOCK_PARITY.md`](../docs/NAC_MOCK_PARITY.md).
Setup and limits: [`../docs/NAC_SIMULATOR_SETUP.md`](../docs/NAC_SIMULATOR_SETUP.md).

---

## Calling the hosted API

> **Checked on the deployed Space on 11 September 2026**: every step below
> returned what it says, including the 0.322 with the planner header and a
> different score without it.
> [Record](../docs/nac/observations/2026-09-11-deployed-api-key-smoke.json).

Step 6 sends the merchant's call to a local server with the published local
key. The hosted deployment refuses that key (**403**); it issues you one of
your own instead, behind the same organizer access code that unlocks Real NaC,
and everything you create with it is yours alone, readable by no other judge.
About 2 minutes.

1. Open **<https://ahmadshadeed32-isnad-trust-engine.hf.space/api-keys>**.
   The page first states what a key from it does: the evidence source it will
   drive (the mock), the deployment's default planner, and how long the key
   lives. Nothing has been issued yet.
2. Enter the organizer access code and press **Generate key**. The code is
   checked by the server and not kept; the key comes back once, as
   `mk_…`, and the page prints three `curl` commands with it and the
   deployment's address already filled in.
3. Paste the first command into a terminal. It is step 6's request, with one
   addition: `X-Isnad-Planner: greedy`. The hosted deployment defaults to the
   Gemini planner, and that header is what makes the answer match this guide.

   **Expect:** `"decision": "CHALLENGE"`, `"chain_grade": "DEGRADED"`,
   `"confidence": 0.322`, `"planner": "greedy"`, and a five-link chain whose
   every link says `mock` for its source. Note the `chain_id`.
4. Paste the second command with `CHAIN_ID` replaced. **Expect** the same
   verdict. Reads are scoped to the key's tenant, so a `chain_id` from another
   judge's key returns **404**.
5. Paste the third. **Expect** `"valid": true` with the Ed25519 signature and
   the public key that made it. To watch the same check fail, take the chain
   to the receipt page (`/r/CHAIN_ID` on the same host) and press **tamper
   with one byte and re-verify**, or run the offline verifier from step 4.

Run the first command twice with the same `Idempotency-Key`: the second reply
is the first one replayed, same `chain_id`, with no second investigation.
Change the amount and keep the key: **409**.

What the key is, and is not: it is a merchant credential for **this
deployment's mock provider**. A call with it sends nothing to Nokia; the only
route to Nokia's simulator is the bounded **Real NaC** path on `/judge`. It
lives in the server's memory for two hours and is forgotten when the Space
restarts, so mint another if a command starts answering **403**. The chains
you create with it belong to the tab that minted it: the page's "Keys minted
from this tab" list and its judge session can read them, and no other judge
can. A deployment whose default provider makes billable calls refuses to issue
these keys at all; the same guard that keeps public demo tokens off the
billable path keeps this page off it too.
