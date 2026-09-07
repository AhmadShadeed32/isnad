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
5. **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)** — the 90-second live-demo running order
   and the questions we expect.

The fastest possible look, if you have three minutes:

```bash
make setup && make judge     # then open http://127.0.0.1:8010/judge
```

## Mandatory requirements, and where each is met

| Requirement | Where |
| --- | --- |
| Uses ≥1 CAMARA API on Nokia Network-as-Code | Eight with a working adapter — [CAMARA_API_USAGE.md](CAMARA_API_USAGE.md), [`app/providers/nac.py`](../app/providers/nac.py) |
| AI agent layer orchestrating CAMARA as data sources, not buttons | [`app/agent/`](../app/agent/) — README section *The AI agent layer*; observed run at [`docs/nac/observations/2026-09-07-gemini-judge-run.json`](../docs/nac/observations/2026-09-07-gemini-judge-run.json), where the model selects, policy corroborates, the model stops and policy overrules it |
| Agent built only with approved tooling | Google AI Studio (Gemini), listed in the Resource & Tooling Guide as a free-tier model API. One provider, no second model, no third-party agent framework — [`app/agent/gemini.py`](../app/agent/gemini.py) |
| Original code | Written by the team during the hackathon window. The Idea Phase submission of 20 August names this repository; public snapshots were pushed 2 September and 7 September. 1,329 tests. The full working history is available to the panel on request |
| Aligned to one of the seven themes | Theme 4. Theme 1 is the adjacent neighbour and the same engine serves it |

## Against the Resource & Tooling Guide's own advice

The guide closes with tips for participants. They read like a checklist, so
here is ours:

| Their tip | Isnad |
| --- | --- |
| "Treat each CAMARA API as a tool the agent decides when to call, not a button the user presses" | No evidence call is bound to a control. Pressing a button starts an *investigation*; the agent decides what to ask |
| "Have a clear fallback when an API or model is rate-limited — agents that gracefully degrade demo much better" | Missing key, transport failure, empty answer or call ceiling all fall back to greedy, and the verdict records which strategy ran |
| "Cache demo data. Live API calls fail at the worst moment" | The demo path is authored fixtures through the real engine; `/lab` replays a committed bundle with no operator or model calls |
| "Show the agent's reasoning trace on screen during the demo" | The trace *is* the demo — every selection, its rationale, its source and the remaining budget |
| "Pick one focus area on day one and resist scope creep" | One question, asked well: can this interaction be trusted right now? |

## What changed since the Idea Phase

Eight integrated CAMARA APIs rather than the seven proposed, now including
Congestion Insights and Number Recycling. Recorded calls to Nokia's hosted
simulator. A Gemini planner whose selections and overrides are visible in the
trace. A full RTL Arabic interface, with the composed verdict prose still
English and labelled as such. 39 tests became 1,329.

## Submission artefacts

| File | What it is |
| --- | --- |
| [`isnad-demo.mp4`](isnad-demo.mp4) | 3:39 demo video. The application footage is the real product running at natural speed — no re-created interfaces — and every figure spoken is one produced by a command in this repository. Captions: [`isnad-demo.srt`](isnad-demo.srt) |
| [`Isnad_Pitch_Phase2.pptx`](Isnad_Pitch_Phase2.pptx) | Phase 2 pitch deck, ten slides, with speaker notes |
| [`Isnad_Idea_Capture_Phase1.pdf`](Isnad_Idea_Capture_Phase1.pdf) | The Idea Phase template, kept for continuity |

**Still outstanding:** a deployed URL for the published web app. The Dockerfile
builds and passes an HTTP smoke check, so any container host will serve it; the
deployment itself is the team's to make.

---

## One paragraph, if that is all there is time for

A rule that declines every SIM change is cheap and wrong: most people who
replace a SIM lost a phone, and cash on delivery is 70–80% of MENA
e-commerce, so every wrong decline is a real van sent to nobody *and* a
customer walking to a competitor. Isnad treats a SIM change as the **start** of
an investigation. An agent forms a hypothesis, buys the cheapest useful CAMARA
evidence until the answer is justified — 49 provider operations where a
run-everything pipeline spends 78 — and hands the merchant a decision with
every link, its source, and a signature that fails the moment a byte changes.
The engine is built so that a judge can check it: the demo is deterministic,
the receipts verify offline, the Nokia calls are recorded with their failures
intact, and the things we have not proven are listed by name.
