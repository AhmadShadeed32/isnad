# Isnad — current state

Updated 5 September 2026. Start here for a short orientation. The local
[`PHASE2_HANDOFF.md`](PHASE2_HANDOFF.md) preserves the historical session log;
its dated entries are history, not a current configuration reference.

## Product and demo

The lead story is a legitimate customer replacing a SIM. The judge page opens
with **Investigate the SIM change** (Act VI): CHALLENGE / DEGRADED. The secondary
**Try a clean checkout** (Act III) produces ALLOW and exposes the simulator
continuity drill. A challenge means the merchant supplies its own step-up.

Use the [README](../README.md) launch command: explicitly set mock provider,
greedy planner and demo mode so a developer's `.env` cannot select a live route
or optional LLM. The default planner is greedy; configured LLM runs remain
optional and report fallbacks. Tests force greedy and use fake STOP-capable
planners to exercise policy gates. Neither a simulator fixture nor a recorded
provider response is a live handset test.

## What changed in this review

- Judge-focused README and walkthrough; corrected video source claims.
- UI/CLI use **policy risk score**, not a calibrated fraud probability. Signed
  `confidence` and internal/event `p_fraud` names remain compatible. Weights,
  thresholds and receipt field vocabulary are unchanged. See [score limits](RISK_SCORE.md).
- [Fixed synthetic evaluation](INDEPENDENT_EVALUATION.md) uses separately
  authored cases and stronger full-evidence baselines. It reports disagreements
  and challenges, not a claimed production accuracy rate.
- [Consent validation](HANDSET_VALIDATION.md) exercises the whole flow offline.
  A granted consent now requires Number Verification before planner choice;
  a STOP-capable planner can no longer skip the authorized check.
- Empty-chain ALLOW is closed: the network-fact minimum applies even at a
  clean prior, with CHALLENGE when no supporting check is affordable.
- The standalone evidence-pack command initializes its own in-memory schema;
  pytest setup is no longer required to run the README proof command.
- Graphify is refreshed locally; `.graphifyignore` keeps local documentation
  discoverable even where `.gitignore` intentionally excludes it.

## Navigation

| Question | Read |
| --- | --- |
| What should a judge see? | [README](../README.md), [walkthrough](JUDGE_WALKTHROUGH.md) |
| How does the decision happen? | `app/agent/investigator.py`, `app/policy/engine.py` |
| What does the score establish? | [Risk score](RISK_SCORE.md) |
| What breaks on harder scenarios? | [Evaluation](INDEPENDENT_EVALUATION.md) |
| What remains for a real phone? | [Handset validation](HANDSET_VALIDATION.md) |
| How to change code safely? | Local `docs/PHASE2_HANDOFF.md` §0, `CLAUDE.md` |

Run `graphify query "<focused question>"` before broad source searches. Use
`.venv311`; `.venv` is the old Python environment. Preserve deterministic policy
gates, explicit evidence provenance, and registry signatures. Root logs intent
before edits and completion after verification. This session used three lighter
subagents on separate file scopes, explicitly authorized by the user.

## Open evidence gaps

The handset/operator consent round trip is **not yet run**. Local protocol
proof does not resolve operator coverage, authorization behavior, or subscriber
support. The prepared procedure states the remaining resources in plain terms.

The numeric policy remains uncalibrated, and synthetic expectations do not
establish real-world false-positive/false-negative rates. Correlated signals and
early stopping need outcome-based evaluation. The supplied pitch video binary
has not been regenerated; current source corrections do not update an old MP4.

The implementation review made no deployment, live provider call or external
message. The user subsequently authorized committing and pushing the reviewed
changes, handoff and graph to `AhmadShadeed32/isnad-private` on `main`.
Publication status is recorded in the task; the public `origin` is not a target.
