# Isnad (إسناد) — Project Brief

**Purpose of this document:** This brief defines Isnad's product concept, rationale, scope, business model, and delivery plan.

**Context:** This idea was developed for the **MENA Open Gateway Hackathon 2026** (HackerEarth-hosted, online, Jul 1 – Sep 13, 2026; teams up to 5; winners showcase at MWC Doha, Nov 2026). Submissions must build an AI agent that orchestrates **CAMARA APIs** on **Nokia's Network-as-Code (NaC)** platform as real-time decision inputs (not user-triggered buttons), aligned to one of the hackathon's seven themes. Phase 1 is judged on an Idea Capture Template + Pitch Deck (relevance, impact, innovation, complexity, agent design). Phase 2 is a live demo.

The project is being developed by a five-person team at Princess Sumaya University for Technology (PSUT), Amman, Jordan. This brief is scoped to Isnad alone.

---

## 1. The Core Insight

**In 2026, generative AI has broken every soft proof that someone is human and genuine:**
- Deepfakes pass liveness/face checks
- Voice clones defeat phone/call-center verification
- Bots solve CAPTCHAs
- Stolen selfies + synthetic documents open accounts
- OTPs and passwords are phishable and forgeable at scale

**The one thing that remains hard to fake:** a physical SIM card, in radio range of a physical cell tower, with years of accumulated history behind it. This truth already lives inside telecom operator networks — and CAMARA (the open API standard behind this hackathon) is the first time in history that truth has become programmable by third parties.

**Thesis:** Whoever builds the trust layer on top of network-verified identity first, owns a foundational piece of infrastructure for the AI era — much as agentic commerce, deepfake-era fraud, and MENA's unique cash/trust economics all converge on the same underlying need at the same moment (2026).

---

## 2. The Name & Cultural Framing

**Isnad (إسناد)** is a real Islamic scholarly term: the "chain of transmission" used for over a thousand years to evaluate whether a hadith (a reported saying/tradition) could be trusted, by scrutinizing every person in the chain who transmitted it. It was arguably the world's first rigorous methodology for trust verification.

**The product literally reproduces this structure**: every verification Isnad issues is a chain of attested links (Human → SIM → Device → Location → History), each link backed by a specific CAMARA API call, rendered in human-readable form. This is not just a nice metaphor — it's the actual UX and audit model: "the internet never got its isnad; every Isnad verdict is one."

This framing matters strategically: it turns "the region that invented chains of trust builds the internet's" into a genuine emotional and cultural hook for MENA judges, distinct from a generic Silicon Valley fraud-detection pitch.

Related Arabic/Islamic-finance terms already identified as a naming system for future features (see Section 6):
- **Tazkiya (تزكية)** — vouching/endorsement (classical isnad science: chains strengthened when trusted people vouched for transmitters)
- **Wakala (وكالة)** — the classical contract of agency/power-of-attorney, still used in Islamic finance today

---

## 3. What Isnad Is (Core Product)

**One sentence:** An agentic trust engine. A merchant, wallet, or bank calls one API at a moment of risk (signup, checkout, payout, password reset) and asks: *"Can I trust this interaction?"* Isnad's agent investigates and returns a verdict — **ALLOW / CHALLENGE / DECLINE** — with a full, human-readable evidence chain attached.

### Why an "investigator agent," not a fixed pipeline
This is the key differentiator versus every other likely hackathon submission (which will wire static if-then API pipelines). Isnad's agent:
1. Forms a risk hypothesis from context (e.g., "new account + high value + COD" = elevated risk)
2. Gathers the **cheapest evidence first** — consent-gated Number Verification, then no OTP or extra friction after authorization
3. **Escalates only when suspicion warrants the cost** — SIM Swap check, Device Swap, Location Verification, Reachability patterns
4. Issues a verdict with the full chain attached — never a black-box score

This directly satisfies the hackathon's mandatory requirement that CAMARA calls be **agent-initiated decision inputs, not user-triggered buttons** — and does so more convincingly than a simple sequential check, because the *choice* of which API to call next is itself the agent's reasoning.

### Core CAMARA APIs used (7, all available on NaC)
| API | Role in the chain |
|---|---|
| Number Verification | Consent-based authentication at signup — no OTP after authorization |
| SIM Swap | Detects recent SIM swap — the account-takeover signal |
| Device Swap | Detects new/unusual device — the mule-phone signal |
| Location Verification | Yes/no check against a claimed address — never raw tracking |
| Device Reachability | Detects bot-farm / burner-phone patterns |
| Device Intelligence | Device reputation and risk scoring |
| Device Roaming Status | Detects impossible-travel patterns; also doubles as an income proxy (see Jadara overlap, Section 8) |

**Privacy design (important, and already a differentiator vs. naive competitors):** Location Verification returns a yes/no against a claim, not a coordinate. Isnad never sees or stores a map. No raw signals are retained — only chain evidence.

---

## 4. The Three-Act Demo (Phase 2 concept)

Designed to work as a live, on-stage demo for judges:

- **Act I — "Kill the OTP."** A judge signs up for a demo wallet and approves the network consent screen once. No code arrives. The agent verifies them via Number Verification; the chain renders on screen link by link, in under a second.
- **Act II — "Catch the ghost."** A simulated fraudster whose SIM was swapped 40 minutes ago tries to order 5 iPhones, cash-on-delivery, from a new account. The investigation runs live in a console (styled like a terminal log) and ends in a DECLINE, with the full evidence chain shown.
- **Act III — "Approve the invisible."** A customer with no formal bank/credit record is APPROVED — six years of SIM tenure and a stable home location function as a credit history. **This is the act investors remember**: fraud tools shrink markets; Isnad grows one.

A draft live-console log style (used in the existing deck) narrates timestamps and agent reasoning step by step — this format should be reused/extended for any new features (e.g., a fourth act for Reverse Isnad, see Section 6).

---

## 5. Business Model & Market

**The wedge: Cash on Delivery (COD) fraud in MENA e-commerce.**
- Multiple industry sources put COD at roughly **70–80% of MENA e-commerce transactions** (sources: Aramex operations leadership statements; regional payments industry reports/PayPal-Ipsos MENA insights; go-globe.com and istizada.com industry summaries — figures range 70–80% depending on country and year, with UAE/KSA/Egypt cited most often).
- COD orders are reported to have **return/rejection rates many times higher** than card transactions (informal industry estimate cited: up to ~12–13x), because there's no verified buyer commitment at checkout.
- Fake orders and refused COD deliveries are a direct, quantifiable cost line for every MENA e-commerce merchant and courier — a concrete, provable pain point to lead with in any pitch or customer conversation.

**Pricing model:** Per-verification fee (pennies per check), priced against the cost of a single wasted delivery run. This is **transactional/usage-based revenue**, not a grant or government license — explicitly framed as more fundable/investable than the ministry-sales model used by the team's other two ideas (Nabd, Mawsim).

**Platform expansion beyond the COD wedge (roadmap, not core build):**
- Deepfake-proof eKYC for banks/wallets onboarding at scale
- Account-takeover defense at password reset / payout / profile change
- Marketplace trust (verified buyers/sellers with attached chains)
- **The agent economy:** as AI agents begin transacting on behalf of people, Isnad becomes the way a merchant proves a real human stands behind the agent — a genuinely forward-looking, differentiated investor narrative for 2026+.

**Comparable/precedent companies:** Prove and Boku are cited as proof that "telecom-identity" is a fundable, working venture category — but both are Western-market, pre-CAMARA, and pre-agentic. The explicit claim is: nobody currently owns this category in MENA.

---

## 6. Feature Roadmap (Tiered)

The roadmap is organized by delivery horizon:

### Tier 1 — Build now (make the 10-week MVP and demo stronger)
1. **Reverse Isnad** — flips the direction of verification: instead of the merchant verifying the customer, the *caller* (e.g., a bank's outbound call center) is verified to the *customer* before the customer trusts them. Directly targets vishing/impersonation scams (fake "bank security officer," fake delivery driver, fake police calls) — a scam type virtually every judge has personally experienced. Reuses the same APIs, aimed the other direction. Strong candidate for a 4th demo act.
2. **Trust with a TTL (session revocation)** — Isnad doesn't just issue a verdict once; it subscribes to the underlying signals for the session duration. If the SIM swaps or the device changes mid-session, the session is revoked live. Strong demo moment: swap a simulated SIM on stage, watch the judge's session die in ~2 seconds. Answers the hardest anticipated judge question: "what if the fraud happens after your check?"
3. **Choreographed step-up challenges** — when the verdict is CHALLENGE (not ALLOW/DECLINE), the agent selects the *cheapest* verification step that would resolve its specific doubt (e.g., silent re-verification or location re-check before ever falling back to OTP). Reinforces the "agent reasons about cost" narrative that differentiates Isnad from a static rules pipeline.

### Tier 2 — Moat-building features (for investor-facing roadmap slides, not the 10-week build)
4. **Isnad Passport ("Login with Isnad")** — a portable, reusable trust credential; verify once, carry it everywhere. Converts a per-check product into an identity *network* (the "Visa Checkout" analogy).
5. **The Isnad Graph** — cross-merchant fraud graph. When the same device fingerprint / SIM-swap pattern is detected across multiple merchants, all of them get warned. This is the standard "consortium data" moat used by fraud-detection leaders like Sift and Forter — each new customer makes the product more valuable to every other customer (a genuine network effect, a strong point for investors).
6. **Evidence vault** — chains stored as signed, replayable records, used to resolve COD disputes and chargebacks with evidence instead of he-said/she-said. Deepens the core COD wedge: not just preventing fake orders, but winning disputes about real ones.

### Tier 3 — Vision-layer / long-horizon (for a single roadmap slide and future planning — not for the core build or demo)
7. **Tazkiya (تزكية) — human vouching.** Named after the classical isnad concept of trusted people vouching for a transmitter. A thin-file/no-tenure person's chain can be strengthened by a vouch from an employer or long-tenured family member — extends the financial-inclusion narrative (Act III) using the region's own historical mechanism.
8. **Wakala (وكالة) — agent delegation / power of attorney.** Wakala is a real, current Islamic-finance contract type (delegated agency). When a person authorizes an AI agent to transact on their behalf, Isnad issues a scoped, expiring, spend-limited "wakala" — a mandate chaining every agent action back to a verified human SIM. This turns the "agent economy" pitch (Section 5) into a named, culturally-grounded product rather than a vague claim — a strong closing-slide concept: *"the power-of-attorney layer of the agent economy."*
9. **Resurrection (account recovery)** — replaces "mother's maiden name"-style security questions with network-based recovery: years of SIM tenure, home-cell stability, and reachability rhythm are used to recover an account with no security questions.

**Strategic guardrail:** Hackathon judges penalize submissions that try to "do everything." Build and demo **Tier 1** only; present **Tier 2/3** as future roadmap items. Do not let the core 10-week build balloon in scope.

---

## 7. Build Plan (10 weeks, as scoped for the hackathon)

| Weeks | Milestone |
|---|---|
| W1–2 | Policy engine + evidence-cost model (the logic for "cheapest evidence first, escalate on suspicion") |
| W3–5 | Investigator agent + CAMARA API integration on NaC simulators |
| W6–7 | Merchant-facing SDK + chain-view dashboard |
| W8 | Red-team week — the team plays the fraudster against their own system |
| W9–10 | Pitch deck, filmed three-act demo, final submission |

**Consent & privacy framing:** Consent-based by design. Location Verification returns yes/no against a claim, never a raw coordinate. No raw signals are stored — only the resulting evidence chain.

---

## 8. Scope Boundary

Isnad's current scope is the Tier 1 verification and trust-session features described above. Tier 2 and Tier 3 concepts remain roadmap items and are not part of the core demo or production API.

---

## 9. Next Steps

The next delivery steps are:
1. **Lock the MVP scope**: keep Reverse Isnad, session TTL revocation, and choreographed step-up within Tier 1; keep Tier 2/3 roadmap-only.
2. **Complete the Idea Capture Template** required for Phase 1, using the product definition and agent design in this brief.
3. **Refresh the pitch deck** with the fourth demo act and one concise future-roadmap slide without diluting the core COD-fraud story.
4. **Verify market figures** with dated, named sources before using them in investor or public materials.
5. **Finalize the technical architecture** and data-flow diagram for the production API.
6. **Validate the NaC integration** with simulator credentials, callback configuration, integration tests, and deployment hardening.

---

*This document is a product and engineering brief. Validate market data and legal, privacy, and financial requirements before external use.*
