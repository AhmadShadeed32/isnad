# Fixed synthetic evaluation

This evaluation is a separate check on Isnad's decision behavior. Its 13 cases
are written explicitly in
`tests/fixtures/independent_evaluation.json`; the harness does not generate them
from `app/policy/policy.yaml`. Each case states its context, every provider
answer, an expected safe decision, an evidence-independence group, and the
reviewer's rationale.

“Separate” describes authorship and construction. The cases remain synthetic,
their expected decisions are conservative reviewer judgments, and the run is
not independent real-world validation. There are no observed fraud outcomes or
production traffic in this dataset, so expectation disagreements must not be
reported as false positives, false negatives, or an accuracy rate.

## What it compares

All methods receive the same six provider-backed facts prescribed by a case.

- **`isnad-greedy`** runs the current sequential investigator with the mock
  provider and deterministic greedy planner. It can stop before observing every
  prescribed fact, which is the behavior being evaluated.
- **`corroboration-aware-rules`** reads all six facts, treats unavailable
  evidence as a gap, and declines only when flags span at least two authored
  independence groups. SIM Swap and Device Swap share `subscriber_change`, so
  two API answers about one replacement event do not automatically become two
  independent votes.
- **`full-evidence-same-policy`** reads all six facts, then applies Isnad's
  current context prior, signal deltas, and thresholds. This isolates the
  effect of sequential stopping from the effect of the policy weights. An
  otherwise-ALLOW result with unavailable evidence is reported as CHALLENGE.

The full-evidence comparators are stronger than an “any flag declines” rule.
They also cost six evidence calls per case. The corroboration groups are
explicit assumptions open to review, rather than a claim that the underlying
operator systems are statistically independent.

## Cases

The set covers two clean flows, a legitimate SIM replacement, consent and
provider unavailability, an unresolved location response, a single adverse
signal, correlated SIM/device changes, independent adverse combinations,
legitimate travel with a recent SIM change, and a broad takeover pattern. The
authored expectations contain 2 ALLOW, 8 CHALLENGE, and 3 DECLINE outcomes
across 6 scenario categories.

## Measured result

Measured 6 September 2026 with `.venv311`, the mock provider, greedy planner,
and the shipped policy:

| Method | Completion coverage | Automatic decisions | CHALLENGE | Authored-expectation disagreements | Execution errors | Evidence calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Isnad, sequential greedy | 13/13 | 8/13 (61.5%) | 5/13 (38.5%) | 3 | 0 | 38 total (2.92/case) |
| Corroboration-aware rules | 13/13 | 5/13 (38.5%) | 8/13 (61.5%) | 0 | 0 | 78 total (6/case) |
| Full-evidence same policy | 13/13 | 6/13 (46.2%) | 7/13 (53.8%) | 3 | 0 | 78 total (6/case) |

Completion coverage means the method returned a result for every case.
Automatic-decision coverage counts ALLOW plus DECLINE, so Isnad's 13/13
completion and 8/13 automatic decisions describe different properties.

The investigator disagreed with three conservative expectations, returning ALLOW:
`location_could_not_resolve`, `single_number_mismatch`, and
`travel_with_recent_sim_change`. These are synthetic expectation differences,
not observed false negatives. Early stopping can still miss later evidence;
the 38-versus-78 call result is inseparable from that tradeoff.

The relevance-aware ALLOW gate now requires supporting evidence that bears on
the active hypothesis. Compared with the prior 28-call/six-disagreement run,
this buys ten more checks and resolves three authored-expectation differences.
The fixture labels and policy weights were not tuned to recover old metrics.

The first run exposed an empty-chain ALLOW path at a low prior. That violated
the stated evidence minimum and was fixed without changing weights: all ALLOW
candidates now require supporting network evidence, and an insufficient budget
retains CHALLENGE. This also changed the consent-unavailable case to CHALLENGE.
The table above reports the corrected engine; the fixture labels were not tuned.

The full-evidence same-policy result has three expectation disagreements. It
allows the isolated number mismatch and the travel/SIM-change case after clean
facts offset the adverse weight, and challenges the number-plus-location
mismatch rather than declining it. The corroboration-aware comparator matches
all authored expectations by construction of its explicit safety rule; that is
a useful reference behavior, not evidence of empirical superiority.

## Reproduce it

```bash
.venv311/bin/python scripts/independent_evaluation.py
.venv311/bin/python scripts/independent_evaluation.py --json
.venv311/bin/python -m pytest -q tests/test_independent_evaluation.py
```

The harness overwrites provider and planner configuration before importing the
application: `mock`, `greedy`, empty Gemini/NaC credentials, and an in-memory
SQLite URL. It performs no network access. The JSON form includes every case,
decision, confidence where applicable, call count, execution error, expectation
disagreement, and pairwise method disagreement.

## Limits

- The fixture is small, fixed, and deliberately rich in boundary cases. It does
  not estimate case prevalence or customer impact.
- Expected safe decisions are review positions. A different risk appetite may
  reasonably relabel individual CHALLENGE and DECLINE cases.
- Prescribing later evidence lets the harness expose early-stopping behavior,
  but it assumes those checks could be obtained within the stated budget.
- The mock provider verifies orchestration and policy behavior, not live API
  latency, consent completion, carrier coverage, or normalization drift.
- Policy changes can move the result. The report should be regenerated whenever
  priors, deltas, thresholds, evidence availability, or planner behavior change.
