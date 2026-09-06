# Isnad — start here

Updated 6 September 2026.

- **Judges:** [README](../README.md) → [90-second walkthrough](JUDGE_WALKTHROUGH.md).
- **Next developer session:** [compact handoff](PHASE2_HANDOFF.md). It holds the
  current evidence, the step-by-step P1–P5 implementation contract (see its current status ledger),
  live rollout plan and working rules. For the hackathon, read its §6 first: it
  prioritizes AI/NaC proof and submission readiness over the full pilot roadmap.
  Its [competition feature plan](PHASE2_HANDOFF.md#7-competition-feature-implementation-plan)
  adds fourteen ordered feature packages. At the user's explicit instruction,
  all fourteen (I1–I14) now have working, tested code — see §8's
  "I1–I14 implementation" entry for exactly what was built and what was
  deliberately left out of each one.
- **Code review:** [seven confirmed fixes for Sonnet](PHASE2_HANDOFF.md#9-sonnet-code-review--6-september-2026),
  all now fixed and verified (759 tests passing, plus a live two-session
  browser check for the cross-session isolation finding). The reviewed
  snapshot passed 661 existing tests but failed seven additional regression
  probes before the fixes; the newer I1–I14 judge-lab work was outside that
  review's own scope.
- **Score interpretation:** [risk score](RISK_SCORE.md).
- **Harder scenarios:** [fixed synthetic evaluation](INDEPENDENT_EVALUATION.md).
- **Real operator consent:** [handset validation](HANDSET_VALIDATION.md).
- **Next Nokia integration milestone:** [hosted simulator runbook](PHASE2_HANDOFF.md#h2a--live-api-calls-to-nokias-hosted-simulator).
  Genuine requests to Nokia with synthetic subscriber answers; physical P4b proof
  remains separate. This hosted demo has not yet been freshly validated.

The lead demo is a legitimate SIM replacement: CHALLENGE / DEGRADED. Its mock
answers run through the same decision engine as normalized live evidence, with
650 ms presentation pacing per check. Physical handset consent remains unproven.
P1 is complete; P2's two recorded gaps (keyboard traversal verification, the
375px receipt-table layout) are now closed, browser-verified, with one real
bug found and fixed at each (the table's missing scroll container; a weak
focus indicator on the console's ask-input). P4a (local live-consent journey
against an offline fake operator) is done locally with 596 tests passing;
P4b (a real handset/operator) remains unproven. P3 (merchant CHALLENGE
followup and completion reporting, reusing the P4a harness) is also done
locally, with 627 tests passing and a real browser pass proving the public
receipt is unchanged by a followup. P5 (merchant order-status/fraud-
assessment outcome reporting and an owner-scoped offline report) is also
done locally, with 659 tests passing and the same kind of browser pass on
the same chain P3 verified. All fourteen §7 competition feature packages
(I1–I14) have working, tested code as of the same day, built at the user's
explicit instruction; see §8 for what each one does and does not cover. A
same-day code review then found seven real defects across P3/P4a's harness
and provider code (§9); all seven are fixed, tested and one browser-verified
live. Full suite: 759 tests passing, Ruff clean.
[Prior validation records](P1_P2_IMPLEMENTATION_RECORDS.md), the
[P4a record](P4A_IMPLEMENTATION_RECORD.md), the
[P3 record](P3_IMPLEMENTATION_RECORD.md) and the
[P5 record](P5_IMPLEMENTATION_RECORD.md) remain available. The I1–I14 and
code-review work is recorded in [the active handoff](PHASE2_HANDOFF.md)'s
§8/§9 rather than in separate implementation-record files, given its scope.

Earlier detailed history is preserved in
[the previously pushed handoff](https://github.com/AhmadShadeed32/isnad-private/blob/faf467ffd1150127a0f16de3a1bea7936d60794e/docs/PHASE2_HANDOFF.md).
