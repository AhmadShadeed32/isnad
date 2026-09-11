# Virtual demo package

**Isnad (إسناد) · Team Isnad · MENA Ignite Hackathon 2026 · Theme 4 — Secure
Fintech, Payments & Anti-Fraud Innovation**
Ahmad Shadeed (lead) · Yousef Al Masri · Princess Sumaya University for
Technology, Amman, Jordan · <ahmadshadeed4321@gmail.com>

Regenerated 10 September 2026 against the build validated on 9 September. This
covers every part of the Virtual Demo deliverable: repository link, demo
description, commercial value, API usage synopsis, business impact, and the
screen-recorded video — which was rebuilt on the same date. What is real in that
video and what is synthesised is stated plainly in §6 rather than implied.

---

## 1 · Links

| | |
| --- | --- |
| **Code repository** | <https://github.com/AhmadShadeed32/isnad> |
| **Live demo — nothing to install** | <https://ahmadshadeed32-isnad-trust-engine.hf.space/judge> |
| **Run it locally** | `make setup && make judge` → <http://127.0.0.1:8010/judge> |
| **Step-by-step verification** | [`JUDGE_GUIDE.md`](JUDGE_GUIDE.md) — ten steps, ~20 minutes, one optional key |
| **Demo video** | [`isnad-demo.mp4`](isnad-demo.mp4) — 2:55 · captions [`isnad-demo.srt`](isnad-demo.srt). Real capture of this build, synthesised narration — see §6 |

The hosted site opens with a configured Gemini key and **Gemini · LLM**
selected. Select **Greedy** for the deterministic numbers quoted below; under
Gemini the checks chosen, the score and the chain grade vary between runs, and
only the decision boundary is fixed.

---

## 2 · Demo description

One question, asked well: *can this interaction be trusted right now?*

A merchant calls one endpoint at a moment of risk. An investigator agent forms
a hypothesis, buys the cheapest useful network evidence until the answer is
justified, and returns **ALLOW**, **CHALLENGE** or **DECLINE** with the full
chain of reasoning attached and an Ed25519 signature over the exact stored
receipt bytes.

### The lead case, as a reviewer sees it

A cash-on-delivery checkout for 1,500 USD. The customer replaced her SIM this
week — the signal a conventional rule declines on.

| Step | What happens on screen |
| --- | --- |
| 1 | The **Evidence source** panel declares the source *before* anything runs. Mock is the default and states that no requests are sent to Nokia. |
| 2 | Press **Investigate the SIM change**. The agent selects Number Verification first — the cheapest check that could resolve the doubt. The number matches. |
| 3 | SIM Swap comes back **adverse**, and stays in the chain under ADVERSE EVIDENCE rather than being averaged away. |
| 4 | Device Swap: the handset is unchanged. Location Verification: she is where she said. Device Roaming Status closes the history link. |
| 5 | Verdict: **CHALLENGE / DEGRADED**, at an uncalibrated policy score of **0.322**. Five CAMARA checks. The merchant runs its own step-up; Isnad sends no one-time code. |
| 6 | Open the signed receipt, press **Check Ed25519 signature**, change one character, check again — it fails. Restore the byte and it verifies. |

Every row carries its own provenance badge. In the demo path each one reads
`SIMULATOR · mock fixture`, on the face of the evidence rather than in a
footnote.

### Five surfaces

| URL | What it is |
| --- | --- |
| `/judge` | The merchant story: one checkout, the agent's reasoning, the verdict, the receipt |
| `/api-keys` | Mint a merchant API key behind the organizer's access code; the page prints the `curl` commands, filled in, for `/v1/verify`, the chain read-back and the signature check |
| `/lab` | Recorded cases replayed side by side against alternative strategies, from a committed bundle with no operator or model calls |
| `/console` | The operator console — live SSE trace, caller screening, session controls |
| `/docs` | OpenAPI, interactive, enabled in demo mode |

Full English and Arabic including RTL layout. The composed verdict paragraph is
still English, and the page carries a banner saying so rather than implying
otherwise.

### What makes it an agent rather than a pipeline

No evidence call is bound to a control. Pressing a button starts an
*investigation*; the agent decides what to ask. The trace labels every
selection with who made it — **`llm`** where the model chose, **`policy`**
where policy required a check the model cannot waive. The model chooses what to
buy; policy decides what the answer means.

Recorded twice, in the repository:

- `docs/nac/observations/2026-09-07-gemini-judge-run.json` — a local run.
  Gemini opens with one adverse signal, policy refuses to let one signal carry
  a decline, the model says stop, and policy overrules it.
- `docs/nac/observations/2026-09-09-deployed-judge-smoke.json` — the same
  boundary on the **deployed** build against **real Nokia calls**. In the
  adverse `swapped_subscriber` run, `journal_decisions` records `sim_swap` with
  `planner: "llm"` and the model's own rationale, then `device_swap` with
  `planner: "policy"` and the rationale *"corroborate before this signal alone
  can decline"*. In the paired `stable_subscriber` run the model chose both
  checks and then stopped — so it is the adverse case that demonstrates the
  override, and that distinction is worth stating rather than blurring.
- `docs/nac/observations/2026-09-09-judge-gemini-journal.json` — the same
  boundary seq by seq (seq 2 model, seq 5 policy), recorded **locally on the
  mock source** so it cost nothing. It is the clearest view of the mechanism
  and it is not deployed evidence.

Degradation is explicit. A missing key, transport failure, empty answer or
exhausted quota falls back to greedy; a rejected answer or the model-call
ceiling *stops* model selection instead of silently substituting greedy. The
verdict records which strategy actually ran, so a fallback can never be
presented as a model run.

---

## 3 · API usage synopsis

Eight CAMARA APIs with a working adapter on Nokia Network-as-Code. The agent
selects which to call at run time from the hypothesis, the evidence so far and
the budget remaining.

| CAMARA API | Role in the evidence chain | Recorded against Nokia |
| --- | --- | --- |
| Number Verification | Proves the number belongs to this device. Replaces the OTP. | Sandbox — capture returned `CONSENT_REQUIRED` |
| SIM Swap | The primary account-takeover signal. | Hosted simulator |
| Device Swap | The mule-phone signal, and the corroborator that saves customers. | Hosted simulator |
| Location Verification | Boolean against an address the customer already claimed. Never a coordinate. | Sandbox |
| Device Reachability | Bot-farm and burner-phone patterns. | Sandbox |
| Device Roaming Status | Impossible travel; a stability proxy for thin-file customers. | Sandbox |
| Number Recycling | Was this number reassigned to someone else? | Hosted simulator |
| Congestion Insights | Network information only — quarantined from the verdict, never touches the risk score. | Hosted simulator |

A ninth, Device Intelligence, has **no** Nokia adapter: the sandbox capture
returned `EVIDENCE_UNAVAILABLE`, so the engine returns unavailable rather than
inventing a reputation verdict.

### What has been observed against Nokia

- **14 standalone probe calls**, 6 September 2026, one line per attempt with
  the failures intact — a 422, a 503, and a 400 for an out-of-range reference
  date. `docs/nac/observations/2026-09-06-hosted-simulator.jsonl`.
- **14 attempts made by the application itself**, 9 September 2026 — ten
  locally and four driven from the deployed `/judge` page. **Ten of the 14 have
  a per-attempt HTTP 200 recorded.** For the other four the status was not
  separately captured, and the record claims only what is provable: each
  carries a normalized signal sourced `nac`, which this pipeline produces only
  from a 2xx whose body parsed, so those responses were usable. Every run ended
  in a signed receipt. A probe proves the credential and the contract; only an
  application run proves the integration.
- **28 recorded attempts in total**, all against Nokia's *hosted simulator*.

The observations also record a contradiction rather than hiding it: for the
same subscriber, `device_swap_check` on a 24-hour window answered
`swapped: true` while `device_swap_date` reported a date nineteen days earlier.
The simulator's boolean is scenario-driven and is not derived from the date it
returns, so the engine shows both with their own provenance and says when they
disagree — it never presents the date as the reason the boolean is true.

Not observed: anything at all on a live network, any Nokia congestion
subscription or callback delivery, and any physical-handset consent round trip.
Simulator mode throughout.

### Judge-selectable evidence source

Mock is the default and sends nothing to Nokia. An organizer access code
unlocks **Real NaC — Nokia hosted simulator**, bounded per run, per session and
per deployment hour. On 9 September both paired real scenarios were driven from
the deployed page: four Nokia HTTP 200 responses, actual Gemini selections,
verified signed receipts, tamper rejection, and replay returning the original
chain with zero new transport attempts.

---

## 4 · Commercial value summary

**Priced per decision.** Merchants, PSPs and wallets pay for a decision
requested at a moment of risk — checkout, signup, payout, password reset. One
endpoint, one answer, one receipt. The cost of serving that decision is the
provider operations the agent chooses to buy, and the agent stops buying when
the answer is justified.

**Why per-decision pricing can work at all.** A pipeline that runs every API
spends the same on a clean checkout as on a suspicious one. An agent that stops
when the answer is justified does not: **49 provider operations against 78**
over the same thirteen authored cases. At pennies per call against thin COD
margins, that difference is the difference between a product and a demo.

**What the operator gets.** A per-call CAMARA revenue line, and a recurring
commercial reason for merchants to consume network capability rather than
integrate once and stop.

> **49 vs 78 is a count of calls, not money.** `policy.yaml`'s costs are
> normalized budget units the engine uses to rank checks — not Nokia's prices,
> and not convertible to them by anything in this repository. No price has been
> set. Revenue, margin and willingness to pay are unmeasured.

**Route to market.** Shadow mode first: Isnad receives the checkout, runs the
investigation and writes a signed chain, while the merchant's existing rule
still decides the order. Nobody is declined, challenged or allowed because of
Isnad until the shadow results are reviewed and the merchant explicitly says
so — and CHALLENGE is enabled before DECLINE, because a CHALLENGE routes to a
review the merchant already performs. The protocol is
[`docs/MERCHANT_PILOT_PLAN.md`](../docs/MERCHANT_PILOT_PLAN.md), written before
the results are known.

---

## 5 · Business impact statements

**None of the following is measured.** It is the intended shape of the impact,
and it stays a hypothesis until a merchant pilot produces outcome data. Stating
it as anything firmer would defeat the point of a project whose entire argument
is provenance.

- **Merchants and couriers** — fewer fake and refused COD orders, and fewer
  vans sent to nobody. A fake order costs a real delivery run; a false decline
  costs a real sale plus the customer.
- **Banks and wallets** — account-takeover defence at payout and password reset
  that does not depend on OTPs, selfies or documents.
- **Customers** — a legitimate SIM replacement gets a step-up instead of a
  decline. A clean signup gets no OTP at all.
- **Financial inclusion** — thin-file customers with no bank record assessed on
  SIM tenure and location stability. Most fraud tools shrink a market; this one
  is designed to grow one.
- **Operators** — a measurable revenue line for CAMARA, and a repeatable reason
  for merchants to consume network capability.
- **One engine, two themes** — Theme 1's cross-border identity verification is
  the same evidence chain with a different hypothesis.

### What we have not proven, named

- No physical handset has completed an operator consent round trip; the flow is
  contract-tested against a local fake operator, not a real SIM.
- No Nokia congestion subscription has been created and no callback delivery
  observed. The deployed callback base is registered and its mock lifecycle
  passes — that proves configuration, not operator acceptance.
- The risk score is uncalibrated. No real fraud outcomes exist to calibrate it
  against, and we will not invent any. **0.322 is not a 32% chance of fraud.**
- No independent reviewer has walked through the deployed build; the
  9 September checks were run by this project's own agent.
- A signed mock receipt is still a mock receipt, and the receipt page says so.

---

## 6 · The screen-recorded video

**[`isnad-demo.mp4`](isnad-demo.mp4) — 2:55, 1920×1080, H.264 + AAC.** Captions:
[`isnad-demo.srt`](isnad-demo.srt). Rebuilt on 11 September 2026 against the
build deployed that day, inside the 3-minute limit.

| | |
| --- | --- |
| Picture | **Real screen capture** of this application being driven: `/judge`, the signed receipt, `/api-keys`, `/lab`, then `/judge` again. Native 1080p — the page renders at 1920 CSS pixels and each one becomes exactly one video pixel, with no rescaling anywhere between the browser and the file |
| Speed | **Natural. No time compression** — the camera waits on the narration, the application is never sped up |
| Provider | Mock, greedy planner, its own database and signing key. **Nothing was sent to an operator** to make this video |
| Narration | **Synthesised speech, not a recorded human voice** — Kokoro-82M, voice `am_michael`, the neural TTS this repository's own video pipeline specifies. Disclosed in a bar burned into every frame, and normalised to −16 LUFS |
| Captions | Generated from the measured duration of each synthesised cue, so the burned-in text, the `.srt` and the audio cannot drift apart |

Every frame carries the same statement: *synthesised narration · real
application, natural speed, no time compression · simulated operator answers.*

What it shows, in order: the cash-on-delivery checkout with its evidence source
declared before anything runs; the agent selecting five checks and naming its
reason and remaining budget for each; the adverse SIM Swap staying in the chain;
CHALLENGE at 0.322 with the page's own statement that the score is uncalibrated;
the signed receipt verifying, then **one byte changed and the signature visibly
failing**, then the limit of what a signature proves; a judge on `/api-keys`
entering the organizer code and receiving a merchant key with the `curl`
commands filled in, which the narration says reaches the mock and never Nokia;
and finally the budget comparison in `/lab`, the Nokia evidence-source selector, and the page's own
uncalibrated-score disclaimer under the closing line about what has not been
measured.

The narration is `docs/VIDEO_REBUILD.md`'s revised script, spoken verbatim, with
one deviation recorded there: that script's paragraph on the `llm` and `policy`
row labels describes a Gemini run, and this capture uses the deterministic
greedy planner so the walkthrough's numbers reproduce. The line was rewritten to
say what is on screen.

**What the cut this replaced got wrong**, and why it could not simply be
re-exported, is kept in [`../docs/VIDEO_REBUILD.md`](../docs/VIDEO_REBUILD.md):
its narration carried a market statistic and categorical AI/CAMARA claims that
have no dated primary source in this repository, the product did not appear
until 1:16, and the sources that produced it were never in the repository at
all.

**One check remains outstanding.** Duration, audio level, frame contents and
caption timing were all verified mechanically. Nobody has yet watched the file
end to end with sound on — that should happen before submission.

**The live site remains the fastest look**, and needs no install or sign-in:
<https://ahmadshadeed32-isnad-trust-engine.hf.space/judge>.
