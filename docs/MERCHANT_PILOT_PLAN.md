# Merchant pilot plan

**Status on 8 September 2026: proposal. No merchant is engaged, no pilot has
run, and no real customer data has been processed.** Every quantity below marked
*(proposed)* is a design parameter chosen for this document, not a figure agreed
with anyone. Nothing here authorizes contacting a merchant, processing customer
data, or spending on provider calls.

This plan exists so that the first real-world evidence Isnad collects is
collected against a protocol written before the results are known.

## Why a pilot is the next milestone

Everything measured so far is synthetic. `docs/INDEPENDENT_EVALUATION.md`
compares three decision methods over 13 reviewer-authored cases; the mock
provider answers every check. That establishes what the policy does. It cannot
establish whether the policy is *right*, because the dataset has no observed
fraud outcomes. The four "authored-expectation disagreements" there are
disagreements with a reviewer's judgement, and calling them false positives or
false negatives would be the single most misleading thing this project could
claim.

A pilot is the only thing that changes that, and only for the dimensions the
merchant can actually report.

## What is being tested

**Decision under test:** for a checkout where the network reports a SIM change,
does Isnad's ALLOW / CHALLENGE / DECLINE produce fewer lost legitimate orders
than the merchant's current rule, without admitting more confirmed fraud?

Stated as two questions the merchant can answer from their own records:

1. Among orders Isnad would have **declined**, how many did the merchant
   independently confirm were legitimate customers?
2. Among orders Isnad would have **allowed**, how many did the merchant
   independently confirm were fraudulent?

Both are counted only from explicit merchant labels — never inferred.

## Target merchant and use case

*(proposed)* A single cash-on-delivery e-commerce merchant with:

- cross-border or domestic COD checkout, where a fake order costs real delivery
  spend and a false decline costs a real sale;
- an existing manual-review queue, so a CHALLENGE has somewhere to go;
- enough SIM-change traffic to produce a non-trivial denominator;
- subscribers on an operator whose CAMARA endpoints Isnad can actually reach.

The last point is a hard prerequisite, not a preference: a pilot on a mock
provider measures nothing about the network.

## Shadow evaluation first

**The pilot runs in shadow mode before it changes any real customer decision.**

Isnad receives the checkout, runs the investigation, and writes a signed chain.
The merchant's existing rule decides the order. Nobody is declined, challenged
or allowed because of Isnad. The comparison is between what Isnad *would* have
done and what the merchant's rule *did* do, on the same orders.

Only after shadow results are reviewed, and only on the merchant's explicit
decision, does any Isnad decision become binding — and then for CHALLENGE
first, since a CHALLENGE routes to a review the merchant already performs. An
automatic DECLINE is the last thing to enable, if ever.

## Baseline comparison

The baseline is **the merchant's current production rule, on the same orders,
over the same window** — not a rules engine Isnad wrote, and not
`corroboration-aware-rules` from the synthetic evaluation. A baseline the
evaluated system authored is not a baseline.

Record for every order in the window: the merchant's decision, Isnad's shadow
decision, and the outcome labels below. Orders where the two agree are as
important as the ones where they differ; reporting only the differences inflates
apparent impact.

## Required fields, and where each comes from

Nothing new is built for this. The pilot uses the outcome contracts already in
the codebase (`app/domain/schemas.py`, `app/db/outcomes.py`) and reports through
`scripts/merchant_outcome_report.py`. Adding a second reporting system would put
two sets of numbers in circulation.

| Field | Source | Vocabulary |
| --- | --- | --- |
| Signed chain, decision, grade, evidence cost | Isnad, per checkout | — |
| `order_status` | merchant reports | `ACCEPTED`, `FULFILLED`, `CANCELLED`, `UNKNOWN` |
| `fraud_assessment` | merchant reports | `CONFIRMED_FRAUD`, `CONFIRMED_LEGITIMATE`, `INCONCLUSIVE`, `UNKNOWN` |
| `basis` | merchant reports | `manual_investigation` or `customer_confirmation` — **required** for either CONFIRMED value and rejected otherwise |
| `occurred_at` | merchant reports | timezone-aware; naive timestamps are rejected |
| `late_report` | merchant reports | disclosed in the report, never a validation gate |
| Challenge execution | read fresh from Isnad's own challenge tables | not merchant-reported |

Two properties of that schema matter more than any metric here. The `basis`
requirement means a payment dispute, or the absence of one, cannot by itself
produce a confirmed label. And outcomes are append-only with explicit
supersession, so a correction is visible as a correction rather than as a
rewritten history.

## What gets measured, and how

Run:

```bash
ISNAD_MERCHANT_API_KEY=<the pilot merchant's key> \
  .venv311/bin/python scripts/merchant_outcome_report.py --out <path>
```

The script reads its configured database directly (`ISNAD_DATABASE_URL`).
**Point it only at the explicitly selected, authorized pilot database.** It
already excludes synthetic runs (`mock`, `nac_fake` provider sources).

| Measure | Definition | Denominator |
| --- | --- | --- |
| Operations and cost | `evidence_cost_total`, plus per-chain `operations` | eligible chains |
| Challenge completion | opened / completed / abandoned / pending | opened challenges |
| Challenge review time | `challenge_completion_time_seconds` | attempts that reached a terminal state |
| Manually accepted orders | `manually_accepted_orders` | eligible chains |
| False declines | DECLINE chains labelled `CONFIRMED_LEGITIMATE` | **labelled** DECLINE chains, not all of them |
| Adverse allows | ALLOW chains labelled `CONFIRMED_FRAUD` | **labelled** ALLOW chains |

Every one of these is reported beside its own denominator and its own missing
count. `missing` and `explicit_unknown` stay separate; folding them together is
how an unlabelled pilot starts looking like a clean one.

### Things this pilot may not conclude

- **An abandoned challenge is not confirmed fraud.** A customer who did not
  finish a step-up may have been busy, confused, or on a bad connection. It is
  reported as `abandoned`, in the challenge block, and nowhere near the fraud
  counts.
- **An unreported dispute is not proof of legitimacy.** Silence is `missing`.
- **A fulfilled order is not a fraud assessment.** Order status and fraud
  assessment are independent dimensions on purpose.
- **Financial savings remain a hypothesis.** The `business_impact_worksheet` in
  the report computes only from assumptions the merchant typed in — a review
  cost and a margin percent — and is labelled as such. Configured evidence-cost
  units are policy budget units, not an operator invoice.

## Observation window and volume

*(proposed, all of it)*

- Shadow window: 4 weeks, or until 200 checkouts with a SIM-change signal,
  whichever comes first.
- Outcome follow-up: 30 days after each order, so a chargeback or a delivery
  failure has time to appear. The report's `observation_window` field states the
  actual span of eligible chains and does **not** enforce this horizon; the
  horizon has to be applied when reading the numbers.
- Minimum before any decision is made binding: enough labelled outcomes that the
  false-decline denominator is not a single-digit number. This document does not
  claim a power calculation; it claims that reporting a rate over five labelled
  orders would be meaningless.

## Exclusions, declared in advance

- Test and staff orders.
- Any chain with a `mock` or `nac_fake` provider source (the script already
  excludes these).
- Orders whose subscriber is not on a supported operator, since the network
  evidence would be absent for reasons unrelated to the customer.
- Orders outside the follow-up horizon at the time of reporting — reported as a
  count, not silently dropped.

## Success criteria

The pilot **succeeds as a measurement** if it produces a labelled denominator
large enough to state both rates with their unknowns, whatever those rates are.
A pilot that shows Isnad performing worse than the merchant's rule is a
successful pilot and must be reported as such.

The pilot supports **adoption** if, over the same orders:

- false declines are lower than the merchant's current rule's, and
- adverse allows are not higher, and
- challenge completion is high enough that the CHALLENGE path is a real
  resolution rather than an abandonment funnel, and
- the per-decision operation count is one the merchant is willing to pay.

All four, with their denominators and unknown counts stated. Any one of them
alone is a headline, not a result.

## Data protection

- Only the fields above leave the merchant. Isnad stores no phone number in a
  signed chain (subject binding is an HMAC under a server pepper).
- The pilot database is the merchant's own scope; the report is owner-scoped and
  reads only that merchant's chains.
- No OAuth URL, authorization code, token, phone number or API key is retained
  in any pilot artifact, matching the redaction rules the handset contract
  report already enforces.
- Retention follows the deployment's configured policy; outcome events are
  purged by server-reported time, current heads included.

## Prerequisites still missing

1. A named merchant, and their agreement.
2. A data-processing agreement covering shadow evaluation of real checkouts.
3. Operator coverage for that merchant's subscribers.
4. Authorization for the provider spend the pilot implies.
5. An agreed labelling routine — who reports `fraud_assessment`, on what
   trigger, and within what window.

Until all five exist, this document is a protocol and nothing in it has been
executed. See `docs/HANDSET_VALIDATION.md` for the separate, and equally
pending, physical-handset track.
