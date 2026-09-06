# Isnad — start here

Updated 6 September 2026.

- **Judges:** [README](../README.md) → [90-second walkthrough](JUDGE_WALKTHROUGH.md).
- **Next developer session:** [compact handoff](PHASE2_HANDOFF.md). It holds the
  current evidence, the step-by-step P1–P5 implementation contract (see its current status ledger),
  live rollout plan and working rules. For the hackathon, read its §6 first: it
  prioritizes AI/NaC proof and submission readiness over the full pilot roadmap.
  Its [competition feature plan](PHASE2_HANDOFF.md#7-competition-feature-implementation-plan)
  adds fourteen ordered feature packages, with a smaller submission shortlist.
  All I-items remain proposals; implemented work is recorded separately.
- **Score interpretation:** [risk score](RISK_SCORE.md).
- **Harder scenarios:** [fixed synthetic evaluation](INDEPENDENT_EVALUATION.md).
- **Real operator consent:** [handset validation](HANDSET_VALIDATION.md).

The lead demo is a legitimate SIM replacement: CHALLENGE / DEGRADED. Its mock
answers run through the same decision engine as normalized live evidence, with
650 ms presentation pacing per check. Physical handset consent remains unproven.
P1 is complete; P2 is partial with 541 tests and browser checks reported by its
implementation session. Remaining P2 work is keyboard traversal verification and
mobile receipt-table layout. P4a (local live-consent journey against an offline
fake operator) is done locally with 596 tests passing; P4b (a real
handset/operator) remains unproven. This documentation revision changes no
application behavior beyond what P4a's own implementation record describes.
[Prior validation records](P1_P2_IMPLEMENTATION_RECORDS.md) and the
[P4a record](P4A_IMPLEMENTATION_RECORD.md) remain available.

Earlier detailed history is preserved in
[the previously pushed handoff](https://github.com/AhmadShadeed32/isnad-private/blob/faf467ffd1150127a0f16de3a1bea7936d60794e/docs/PHASE2_HANDOFF.md).
