# The 90-second live demo

For the Phase 2 demo round. Start with `make judge` and open `/judge`. Every
operator answer in this flow is simulated and the UI says so on each row —
lead with that rather than being asked.

| Time | Show | Say |
| --- | --- | --- |
| 0–15 s | The replaced-SIM checkout | "She replaced her SIM. That signal is real. Account takeover is only *one* explanation for it — and the cheap rule that declines her costs a real delivery van and a real customer." |
| 15–40 s | Click **Investigate the SIM change** | "The agent picks each check itself and shows you why. Number verification first, cheapest. Then SIM swap — that's the adverse fact. Then device swap: same handset. Then location: she's where she said. Every row carries its own source." |
| 40–55 s | CHALLENGE / 0.322 | "The adverse fact stays in the chain. Three links corroborate her, so the merchant asks for a step-up instead of declining a customer who lost her phone. Isnad didn't send an OTP — the merchant runs their own." |
| 55–75 s | Open the signed receipt, check the signature, tamper, restore | "This proves exactly what Isnad issued. Change one byte and it fails. It does *not* prove the operator told us the truth — a signed mock receipt is still mock, and the page says so." |
| 75–90 s | Back to the checkout | "A reproducible engine, explicit uncertainty, inspectable decisions. Nine CAMARA APIs, forty-nine calls where a run-everything pipeline spends seventy-eight. Next proof: an operator handset flow and real merchant outcomes." |

If time allows, **Try a clean checkout** shows ALLOW after two checks — that is
the budget argument in one click, and only that clean ALLOW exposes the
continuity session and SIM-swap drill. Keep caller screening and Reverse Isnad
for questions rather than crowding the main story.

## Answers worth rehearsing

**Is it live?**
The demo is mock, and every row is stamped `SIMULATOR · mock fixture`. What is
real: fourteen recorded HTTP calls to Nokia's hosted simulator on 6 September,
failures included, in `docs/nac/observations/`; and recorded Gemini selections
with the model's own rationales. A physical handset consent round trip is open,
and I would rather tell you that than have you find it.

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
A supported subscriber and a registered HTTPS callback for the operator flow,
then a merchant's appropriately handled outcome data to calibrate real
decisions.
