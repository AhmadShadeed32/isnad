# Isnad — MENA Ignite Hackathon 2026 submission

**Theme 4 — Secure Fintech, Payments & Anti-Fraud Innovation**
Team Isnad · Ahmad Shadeed (lead), Yousef Al Masri · Princess Sumaya University
for Technology, Amman, Jordan · <ahmadshadeed4321@gmail.com>

An agentic trust engine. A merchant calls one API at a moment of risk; an
investigator agent orchestrates CAMARA APIs on Nokia Network-as-Code as
real-time evidence, and returns ALLOW / CHALLENGE / DECLINE with the full chain
of reasoning and an Ed25519 signature over it.

---

## For a judge, in order

1. **[JUDGE_GUIDE.md](JUDGE_GUIDE.md)** — install, run and verify from a clean
   clone. Ten steps, ~20 minutes; only step 7 needs a key. Each step states what
   you should see, so a mismatch is a finding rather than a guess.
2. **[../README.md](../README.md)** — the problem, the solution, the AI agent
   layer, the API table, and what is real versus simulated.
3. **[CAMARA_API_USAGE.md](CAMARA_API_USAGE.md)** — every CAMARA API, how the
   agent chooses it, and exactly what has and has not been observed against
   Nokia's own endpoints.
4. **[MOCK_VS_NAC.md](MOCK_VS_NAC.md)** — why the demo runs on fixtures, what
   mock shares with Nokia, and precisely where it does not. Read this if the
   word "mock" makes you suspicious; it should.
5. **[VIRTUAL_DEMO.md](VIRTUAL_DEMO.md)** — the Virtual Demo deliverable in
   writing: what the demo shows, the API usage synopsis, the commercial value
   and business impact, and the exact state of the recorded video.
6. **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)** — the 90-second live-demo running order
   and the questions we expect.

**The fastest possible look — nothing to install:** <https://ahmadshadeed32-isnad-trust-engine.hf.space/judge>

Choose **Mock — Nokia-compatible demo**, **Both swaps occurred**, and **Greedy**,
then press **Run**. Expect two checks and a DECLINE / REFUTED verdict with a
signed receipt. Mock sends nothing to Nokia. Select Gemini to use the site's
model key, or unlock **Real NaC — Nokia hosted simulator** with an organizer
code to send actual Nokia requests. The separate **Custom mock scenarios** group
contains the five-check SIM replacement story described in the longer guide.

Or on your own machine, in three minutes:

```bash
make setup && make judge     # then open http://127.0.0.1:8010/judge
```

## Mandatory requirements, and where each is met

| Requirement | Where |
| --- | --- |
| Uses ≥1 CAMARA API on Nokia Network-as-Code | Eight with a working adapter — [CAMARA_API_USAGE.md](CAMARA_API_USAGE.md), [`app/providers/nac.py`](../app/providers/nac.py) |
| AI agent layer orchestrating CAMARA as data sources, not buttons | [`app/agent/`](../app/agent/) — README section *The AI agent layer*; observed run at [`docs/nac/observations/2026-09-07-gemini-judge-run.json`](../docs/nac/observations/2026-09-07-gemini-judge-run.json), where the model selects, policy corroborates, the model stops and policy overrules it |
| Agent built only with approved tooling | Google AI Studio (Gemini), listed in the Resource & Tooling Guide as a free-tier model API. One provider, no second model, no third-party agent framework — [`app/agent/gemini.py`](../app/agent/gemini.py) |
| Original code | Written by the team during the hackathon window. The Idea Phase submission of 20 August names this repository; public snapshots were pushed 2 September and 7 September. 1,605 checks passed on 11 September 2026. The full working history is available to the panel on request |
| Aligned to one of the seven themes | Theme 4. Theme 1 is the adjacent neighbour and the same engine serves it |

## Against the Resource & Tooling Guide's own advice

The guide closes with tips for participants. They read like a checklist, so
here is ours:

| Their tip | Isnad |
| --- | --- |
| "Treat each CAMARA API as a tool the agent decides when to call, not a button the user presses" | No evidence call is bound to a control. Pressing a button starts an *investigation*; the agent decides what to ask |
| "Have a clear fallback when an API or model is rate-limited — agents that gracefully degrade demo much better" | A missing key, transport failure, empty answer or exhausted shared quota falls back to greedy; a rejected/invalid answer or the model call ceiling *stops* model selection instead of silently substituting greedy. The verdict records which strategy ran |
| "Cache demo data. Live API calls fail at the worst moment" | The demo path is authored fixtures through the real engine; `/lab` replays a committed bundle with no operator or model calls |
| "Show the agent's reasoning trace on screen during the demo" | The trace *is* the demo — every selection, its rationale, its source and the remaining budget |
| "Pick one focus area on day one and resist scope creep" | One question, asked well: can this interaction be trusted right now? |

## What changed since the Idea Phase

Eight integrated CAMARA APIs rather than the seven proposed, now including
Congestion Insights and Number Recycling. Recorded calls to Nokia's hosted
simulator. A Gemini planner whose selections and overrides are visible in the
trace. A full RTL Arabic interface, with the composed verdict prose still
English and labelled as such. 39 tests became 1,605 passing checks.

## Submission artefacts

The three required deliverables, in the organizer's order. All of them were
regenerated on 11 September 2026 against the build deployed that day, which
added the `/api-keys` page.

| # | Deliverable | File | State |
| --- | --- | --- | --- |
| 1 | Idea Capture template | [`Isnad_Idea_Capture_2026-09-11.pdf`](Isnad_Idea_Capture_2026-09-11.pdf) · [`.docx`](Isnad_Idea_Capture_2026-09-11.docx) | **Current.** All eight sections restated against this build: eight CAMARA APIs rather than the seven proposed, five surfaces including the judge's API-key page, 1,605 checks, 28 recorded Nokia attempts, and the unsourced claims removed rather than restated |
| 2 | Pitch deck | [`Isnad_Pitch_Phase2.pptx`](Isnad_Pitch_Phase2.pptx) | **Current.** Fourteen slides with speaker notes, updated 11 September: the architecture, numbers, team and closing slides name the `/api-keys` page and the 11 September check counts. The product capture is cropped from the 9 September release screenshot |
| 3 | Virtual demo — video | [`isnad-demo.mp4`](isnad-demo.mp4) · [`isnad-demo.srt`](isnad-demo.srt) | **Current.** 2:55, 1920×1080, rebuilt 11 September with a section on `/api-keys`. Real screen capture of this build; **synthesised narration** (Kokoro `am_michael`), disclosed on screen. See below |
| 3 | Virtual demo — written | [`VIRTUAL_DEMO.md`](VIRTUAL_DEMO.md) | **Current.** Repository link, demo description, commercial value, API usage synopsis and business impact |

The Idea Phase template of 20 August 2026 is **not** in this folder. It
described a seven-API proposal and carried claims this repository has since
removed, so keeping it beside the current document would only invite a judge to
read the wrong one. It is retained outside the submission, in the working
directory `docs/_internal/superseded/`, and it remains in this repository's git
history. The originality point it supports is unchanged and is stated in the
requirements table above: the Idea Phase submission of 20 August names this
repository.

**About the video.** The picture is real screen capture of this application
being driven — `/judge`, the signed receipt with a byte tampered so the
signature visibly fails, `/api-keys` where a judge mints a merchant key behind
the organizer code, `/lab`, and back — at natural speed, with no time
compression. It runs on the mock provider with its own database and signing key,
so nothing was sent to an operator. The **narration is synthesised speech**, not
a recorded human voice, and a bar burned into every frame says so alongside the
natural-speed and simulated-operator statements. Captions were generated from
the measured duration of each synthesised cue, so the burned-in text, the
`.srt` and the audio cannot drift apart. The 3:39 cut this replaced carried the
market statistic and the categorical AI/CAMARA claims removed on 8 September and
did not show the product until 1:16; what was wrong with it, and how the rebuild
was produced, are recorded in
[`../docs/VIDEO_REBUILD.md`](../docs/VIDEO_REBUILD.md).

**Deployed and checked, 9 September 2026:**
<https://ahmadshadeed32-isnad-trust-engine.hf.space/judge>. No sign-in or install.
Mock is the default; the organizer code unlocks bounded real Nokia simulator
calls. Both paired real scenarios were driven from this deployed page: four
HTTP 200 responses, actual Gemini selections, verified signed receipts,
tamper rejection and replay without new calls. Evidence:
[`…-deployed-judge-smoke.json`](../docs/nac/observations/2026-09-09-deployed-judge-smoke.json).
The five earlier local rehearsal runs remain separately recorded; they are not
deployed observations. This was the project's agent checking its own release,
not an independent judge review or a physical-subscriber verification.

Nokia, Gemini, organizer access and signing credentials are private Space
Secrets. The signing identity survives container replacement; receipt storage
and sessions remain ephemeral. Download receipts you want to keep.

**The hosted site does have a model credential.** A site Gemini key is
configured there as a Space Secret, so a fresh tab reports that a site key is
available and opens with **Gemini · LLM** selected; the page's planner selector
lets any visitor switch to **Greedy** for a deterministic run, and that choice
is sticky for the tab. This is the opposite default from the local `make judge`
path, which is greedy so a reviewer following the written walkthrough gets the
same numbers every time (`make judge-ai` is the local Gemini path). Both are
deliberate. `render.yaml`, a different deployment target, pins
`ISNAD_PLANNER=greedy` with no keys at all — deployment targets differ on
purpose, and each one's setting is in its own config file.

Consequence for a reviewer: **on the hosted site, expected values in the
walkthrough hold only after selecting Greedy.** Under Gemini the checks chosen,
the score, the link count and the chain grade all vary between runs. What does
not vary is the decision boundary — see the dated path-coverage result in
[`JUDGE_GUIDE.md`](JUDGE_GUIDE.md) step 7.

(The Hugging Face project page behind it is deliberately not public, so the
deployment is not browsable or scrapeable. The application URL above is, and is
the one to use.)

---

## One paragraph, if that is all there is time for

Fake orders can waste delivery costs; automatically declining legitimate
customers loses sales. A SIM change on its own does not tell those two apart —
a takeover and a replaced lost phone produce the same signal — so a rule that
declines on it alone pays for both mistakes. Isnad treats a SIM change as the
**start** of an investigation. An agent forms a hypothesis, buys the cheapest useful CAMARA
evidence until the answer is justified — 49 provider operations where a
run-everything pipeline spends 78 — and hands the merchant a decision with
every link, its source, and a signature that fails the moment a byte changes.
The engine is built so that a judge can check it: the demo is deterministic,
the receipts verify offline, the Nokia calls are recorded with their failures
intact, and the things we have not proven are listed by name.
