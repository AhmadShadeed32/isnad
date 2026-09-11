# What the risk score means

Isnad returns a **policy-derived risk score between 0 and 1**. Higher means more
risk under the configured policy. It is **uncalibrated**: a score of 0.8 does not
establish an 80% chance of fraud.

The API keeps the historical field name `confidence`; event streams and Python
internals retain `p_fraud`. These compatibility names do not turn the number into
an observed probability. Existing signed receipts remain verifiable: this change
clarifies interpretation and display labels without changing their fields,
values, thresholds, or signature algorithm.

## How it is calculated

The engine starts with a configured prior, adds context weights and each observed
signal's `delta_logodds`, then applies `1 / (1 + exp(-total))`. See
[`policy.yaml`](../app/policy/policy.yaml) and
[`Belief`](../app/agent/belief.py). The receipt includes the prior and link deltas,
so its arithmetic can be checked. Arithmetic reproducibility is distinct from
statistical calibration.

The shipped thresholds are 0.15 for ALLOW and 0.80 for DECLINE. Policy gates also
matter: unavailable evidence can retain CHALLENGE despite a low score. A
threshold calculation alone is not a replay of the full decision procedure.

## Correlation is an open evaluation concern

Replacing a handset can also replace its SIM. Two API results may describe one
underlying event. Adding both configured weights can overstate the evidence;
calling two endpoints does not establish statistical independence.

This revision leaves decision weights unchanged. A blanket correlation discount
would be another unvalidated assumption. The fixed synthetic evaluation includes
related-event cases so disagreements remain visible rather than being removed
by tuning against the test set.

## What would establish a useful probability

Use consented, appropriately handled outcome data collected separately from
policy design. Define the target and outcome window (for example, confirmed
account takeover rather than any abandoned checkout), preserve uncertain labels,
and account for selective outcomes: declined orders do not reveal what would
have happened if accepted.

Freeze the policy before evaluating a held-out period; group related accounts or
events so they cannot leak across development and evaluation. Report calibration
alongside ALLOW errors, legitimate-user declines, CHALLENGE/abstention rate,
coverage, evidence spend and end-to-end latency. Compare with the merchant's
actual policy and a full-evidence baseline. Inspect correlated signal groups and
operator/customer slices. Use sufficient samples and uncertainty intervals before
claiming production performance.

The [fixed synthetic evaluation](INDEPENDENT_EVALUATION.md) is a software and
policy stress test. It does not supply the outcome data this validation requires.
