# The 90-second Isnad demo

Start with the explicit mock/greedy command in the [README](../README.md).
Open `/judge`. All operator answers in this flow are simulated.

| Time | Show | Say |
| --- | --- | --- |
| 0–15 s | The replaced-SIM checkout | “She replaced her SIM. The signal is real. An account takeover is only one explanation.” |
| 15–40 s | Click **Investigate the SIM change** | “Isnad gathers the surrounding evidence. The handset is stable, and the device is at the claimed location. Each row shows its source.” |
| 40–55 s | CHALLENGE / DEGRADED | “The adverse fact stays in the chain. The merchant asks for a step-up instead of automatically declining the customer.” |
| 55–75 s | Open signed receipt; tamper and restore | “This receipt proves what Isnad issued. Change a byte and the signature fails. It does not prove that a provider is truthful.” |
| 75–90 s | Back to the checkout | “We have a reproducible engine, explicit uncertainty and inspectable decisions. The next proof is an operator handset flow and a merchant outcome evaluation.” |

If time permits, **Try a clean checkout** shows ALLOW after two checks. Only
that clean ALLOW exposes the optional simulator session and SIM-swap drill.
Keep caller screening and reverse verification for questions rather than adding
them to the main story.

## Answers worth rehearsing

**Is it live?** The stage fixture is mock and says so on each row. The NaC adapter
has historical response captures. A physical handset consent test remains open;
the local consent route sequence and receipt verification are automated.

**Does 0.242 mean a 24.2% fraud probability?** No. It is an uncalibrated policy
risk score. Priors and signal weights are configurable and its arithmetic is
reproducible. Outcome data is needed for calibration.

**How much does it save?** The original synthetic harness buys 58 checks versus
119. Its labels come from the policy vocabulary. The separately authored set
buys 28 versus 78, but has six conservative expectation disagreements. Present
both the savings and the tradeoff; neither result measures merchant revenue.

**Why use a planner?** It selects affordable evidence; policy enforces the
required checks. The reproducible demo uses greedy. Optional LLM runs record
which strategy actually answered, including fallback and policy-only runs.

**What do you need next?** A supported subscriber and registered HTTPS callback
for the operator flow, followed by a merchant's appropriately handled outcome
data to evaluate real decisions and correlated signals.
