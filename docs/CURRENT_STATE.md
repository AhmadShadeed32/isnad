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
handset/operator) remains unproven. P3 (merchant CHALLENGE followup and
completion reporting, reusing the P4a harness) is also done locally, with 627
tests passing and a real browser pass proving the public receipt is unchanged
by a followup. P5 (merchant order-status/fraud-assessment outcome reporting
and an owner-scoped offline report) is also done locally, with 659 tests
passing and the same kind of browser pass on the same chain P3 verified.
This documentation revision changes no application behavior beyond what the
P3, P4a and P5 implementation records describe.
[Prior validation records](P1_P2_IMPLEMENTATION_RECORDS.md), the
[P4a record](P4A_IMPLEMENTATION_RECORD.md), the
[P3 record](P3_IMPLEMENTATION_RECORD.md) and the
[P5 record](P5_IMPLEMENTATION_RECORD.md) remain available.

Earlier detailed history is preserved in
[the previously pushed handoff](https://github.com/AhmadShadeed32/isnad-private/blob/faf467ffd1150127a0f16de3a1bea7936d60794e/docs/PHASE2_HANDOFF.md).
