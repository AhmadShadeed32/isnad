# The 90-second live demo

For the Phase 2 demo round. Start with `make judge` and open `/judge`. Every
operator answer in this flow is simulated and the UI says so on each row —
lead with that rather than being asked.

> **Reconciled against the shipped page on 9 September 2026.** `/judge` gained
> an **Evidence source** panel at the top of the checkout card, and the three
> authored stories moved below the basket under **Custom mock scenarios**. The
> beats below name the controls as they now read. The numbers in this script
> (0.322, five links, 49 vs 78 operations) were **not** re-measured for this
> revision; they are the ones `submission/JUDGE_GUIDE.md` and the lab bundle
> carry. The recorded video was rebuilt against this page on 11 September; see
> `docs/VIDEO_REBUILD.md`.

| Time | Show | Say |
| --- | --- | --- |
| 0–15 s | The replaced-SIM checkout, and the **Evidence source** panel above it | "She replaced her SIM. That signal is real. Account takeover is only *one* explanation for it — and the cheap rule that declines her costs a real delivery van and a real customer. First, notice where the evidence comes from: this is set to **Mock**, and mock sends nothing to Nokia. The panel says so before I click anything." |
| 15–40 s | Under **Custom mock scenarios**, click **Investigate the SIM change** | "The agent picks each check itself and shows you why. Number verification first, cheapest. Then SIM swap — that's the adverse fact. Then device swap: same handset. Then location: she's where she said. Every row carries its own source." |
| 40–55 s | CHALLENGE / 0.322 | "The adverse fact stays in the chain. Three links corroborate her, so the merchant asks for a step-up instead of declining a customer who lost her phone. Isnad didn't send an OTP — the merchant runs their own." |
| 55–75 s | Open the signed receipt, check the signature, tamper, restore | "This proves exactly what Isnad issued. Change one byte and it fails. It does *not* prove the operator told us the truth — a signed mock receipt is still mock, and the page says so." |
| 75–90 s | Back to the checkout | "A reproducible engine, explicit uncertainty, inspectable decisions. Eight CAMARA APIs integrated on Nokia Network as Code, forty-nine provider operations on our synthetic set where a run-everything pipeline spends seventy-eight. Next proof: an operator handset flow and real merchant outcomes." |

If time allows, **A clean checkout** (under **Custom mock scenarios**) shows ALLOW after two
checks — that is the budget argument in one click, and only that clean ALLOW
exposes the continuity session and SIM-swap drill. Keep caller screening and
Reverse Isnad for questions rather than crowding the main story.

**If a judge asks to see a real Nokia call**, that is the panel's other radio:
*Real NaC — Nokia hosted simulator*, which needs an organizer access code and is
bounded per run, per session and per deployment-hour. It is **enabled on the
deployed Space**, behind the organizer code. Enter the code privately, select a
paired scenario, and press **Run**. State that these are actual requests to
Nokia's hosted simulator using test subscribers. The two paired scenarios in
that mode (`Both swaps occurred`, `Neither swap
occurred`) are the Nokia-contract cases; the three authored stories above are
not, and are mock-only.

## Answers worth rehearsing

**Is it live?**
Mock is the default. The real selector sends actual Nokia HTTPS requests after
an organizer-code exchange. On 9 September, the release check ran both paired
scenarios from the deployed page: **four HTTP 200 responses**, Gemini selections,
verified receipts, and replay with no new requests. The observations in
`docs/nac/observations/2026-09-09-deployed-judge-smoke.json` are separate from
the five earlier local runs and the 6 September probes. All use Nokia's hosted
simulator; no physical handset consent flow or live-network subscriber is proven.

**Does 0.322 mean a 32% chance of fraud?**
No. It is an uncalibrated policy score — reproducible arithmetic over
configured weights. Every prior and signal weight is in one readable YAML file.
Calibration needs outcome data we do not have, and inventing it would defeat
the point of the project.

**How much does it save?**
On the thirteen-case authored evaluation: 49 provider operations versus 78, for
six CHALLENGEs. The same command prints four cases where our planner disagrees
with the authored expectation, three by being less conservative. I quote both
halves — the expectations are synthetic, and neither number measures merchant
revenue.

**Why an agent rather than a rules pipeline?**
Because the cost is the constraint. At pennies per call against thin COD
margins, running every API on every request does not survive contact with a
real merchant. The model selects what to buy; policy alone decides what the
answer means, and can require a check the model skipped. The verdict records
which strategy actually ran, so a fallback never masquerades as an LLM run.

**Why is Congestion Insights in its own box?**
Because a congested cell explains a slow measurement. It is not a fact about a
person. It never touches the risk score and never waives a check — mixing the
two would be exactly the category error this project exists to avoid.

**What do you need next?**
A supported subscriber for the operator consent flow, then a Nokia congestion
subscription with an observed callback delivery. The deployed callback base is
now registered and its mock lifecycle passes, which proves configuration rather
than operator acceptance. After those, a merchant's appropriately handled
outcome data to calibrate real decisions.
