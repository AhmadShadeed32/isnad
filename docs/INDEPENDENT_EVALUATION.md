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
and the shipped policy, and **re-measured unchanged on 8 September 2026** after
the corroboration gate landed (see `docs/_internal/HACKATHON_FINISHING_RECORD.md`
Step 3). Every figure in the table below reproduced exactly. The gate binds the
DECLINE side when an adverse signal has no resolved corroboration, and no case in
this dataset reaches that condition — each one either corroborates its adverse
signal or never crosses the decline threshold — so the boundary change is
correctly invisible here. That is a fact about the dataset's coverage, not
evidence that the gate does nothing: the paths where it does fire are exercised
in `tests/test_planner_path_safety.py`.

| Method | Completion coverage | Automatic decisions | CHALLENGE | Authored-expectation disagreements | Execution errors | Evidence calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Isnad, sequential greedy | 13/13 | 7/13 (53.8%) | 6/13 (46.2%) | 4 | 0 | **49 total** (3.77/case): 34 evidence checks + 15 swap-date enrichments |
| Corroboration-aware rules | 13/13 | 5/13 (38.5%) | 8/13 (61.5%) | 0 | 0 | 78 total (6/case) |
| Full-evidence same policy | 13/13 | 6/13 (46.2%) | 7/13 (53.8%) | 3 | 0 | 78 total (6/case) |

Completion coverage means the method returned a result for every case.
Automatic-decision coverage counts ALLOW plus DECLINE, so Isnad's 13/13
completion and 7/13 automatic decisions describe different properties.

Re-run on 7 September 2026 after swap-date enrichment was added. Two corrections
to how this table must be read:

**The call count is provider OPERATIONS, not evidence links.** A swap date is a
second billable call that adds no link to the chain, so counting links reported
34 where 49 operations were actually made — understating what Isnad spends and
overstating the saving. `scripts/independent_evaluation.py` now counts both and
reports `enrichment_calls` separately per case. Quote **49 versus 78**, and say
that 15 of the 49 buy explanation rather than evidence.

**The numbers moved because the agent now spends differently.** A unit spent on
a date is a unit not available for another check, so early stopping happens on
less corroboration: automatic decisions fell from 8/13 to 7/13 and authored
disagreements rose from three to four. That is a real trade, not a regression to
tune away, and neither the fixture labels nor the policy weights were adjusted
to recover the old figures.

The investigator disagreed with four authored expectations: three ALLOW results
where CHALLENGE was expected, and one CHALLENGE where DECLINE was expected.
These are synthetic expectation differences, not observed false negatives.
Early stopping can still miss later evidence; the 49-versus-78 call result is
inseparable from that tradeoff.

On 8 September 2026, the Lab's recorded table was found to disagree with the
standalone evaluator: it showed six automatic decisions and three disagreements.
Report generation inherited a planner from already-loaded deployment settings.
Both evaluators now explicitly construct GreedyPlanner with the same policy,
and generated scenarios stay local to each provider. Regression tests compare
the standalone result with bundle generation under conflicting host settings
and compare the committed table with a fresh evaluation. No fixture expectations
or policy weights were changed to reconcile the results.

The relevance-aware ALLOW gate now requires supporting evidence that bears on
the active hypothesis. Compared with the prior 28-call/six-disagreement run,
this bought more checks and resolved authored-expectation differences.
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
