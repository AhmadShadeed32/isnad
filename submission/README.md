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
   clone. Nine steps, ~15 minutes, no credentials needed. Each step states what
   you should see.
2. **[../README.md](../README.md)** — the problem, the solution, the AI agent
   layer, the API table, and what is real versus simulated.
3. **[CAMARA_API_USAGE.md](CAMARA_API_USAGE.md)** — every CAMARA API, how the
   agent chooses it, and exactly what has and has not been observed against
   Nokia's own endpoints.

The fastest possible look, if you have three minutes:

```bash
make setup && make judge     # then open http://127.0.0.1:8010/judge
```

## Mandatory requirements, and where each is met

| Requirement | Where |
| --- | --- |
| Uses ≥1 CAMARA API on Nokia Network-as-Code | Nine of them — [CAMARA_API_USAGE.md](CAMARA_API_USAGE.md); adapter at [`app/providers/nac.py`](../app/providers/nac.py) |
| AI agent layer orchestrating CAMARA as data sources, not buttons | [`app/agent/`](../app/agent/) — README section *The AI agent layer*; recorded run at [`docs/nac/observations/2026-09-07-gemini-rehearsal.json`](../docs/nac/observations/2026-09-07-gemini-rehearsal.json) |
| Agent built only with approved tooling | Google Gemini via a direct REST adapter, [`app/agent/gemini.py`](../app/agent/gemini.py). No third-party agent framework |
| Original code | Written by the team during the hackathon. 1,310 tests, full git history |
| Aligned to one of the seven themes | Theme 4. Theme 1 is the adjacent neighbour and the same engine serves it |

## Phase 1 material

[`Isnad_Idea_Capture_Phase1.pdf`](Isnad_Idea_Capture_Phase1.pdf) — the idea
capture template submitted in the Idea Phase, kept here for continuity. The
build has moved past it: nine CAMARA APIs rather than seven, recorded hosted
simulator calls, a bilingual UI and 1,310 tests.

## Still to attach before the deadline

These are submission artefacts, not code, and they are not in this repository:

- Updated Phase 2 pitch deck (the Idea Phase deck does not cover the built
  prototype).
- Demo video.
- Deployed URL for the published web app.

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
