# Greedy vs Gemini, on identical evidence

Run 9 September 2026. Reproducible; the exact command and every input identity
are recorded below and in the saved result.

This is a **behavioural** comparison of two planners on fixed fixtures. It is
not a fraud-accuracy study, not a latency benchmark, and not a claim that
either planner is better at detecting fraud. Both planners were given the same
evidence, request context, available actions, policy, operation budget,
enrichment setting and isolated provider state. The only difference is which
one was asked what to check next.

## How to reproduce

```sh
ISNAD_GEMINI_API_KEY=... .venv311/bin/python scripts/planner_divergence.py \
  --trials 8 --max-requests 60 --budget-seconds 420 --json result.json
```

| Input | Value for the run below |
| --- | --- |
| Revision | `4b8fc6a` plus the uncommitted judge paired-source change (`working_tree_dirty: true`) |
| Contract version | `2026-09-09.1` |
| Policy digest | `3c3c77aae2a9` |
| SDK | `network_as_code==10.0.0` |
| Model | `gemini-3.6-flash` |
| Nokia HTTP | **none.** The script pins `ISNAD_PROVIDER=mock` before importing settings, and additionally replaces `nac_contract.build_hosted_client` with a function that raises — so a measurement run cannot open an operator transport through ambient configuration even by accident. |

Saved result: [`docs/_internal/planner/2026-09-09-planner-comparison.json`](_internal/planner/2026-09-09-planner-comparison.json).

## Two cohorts, never averaged

| Cohort | What it is | Actions available |
| --- | --- | --- |
| `nokia_paired` | The two documented simulator subscribers, answered by the Nokia-contract transport through the real SDK — the same thing the judge demo exposes. | SIM Swap check, Device Swap check |
| `custom_mock` | The authored console stories. Richer, and **not** Nokia contracts. | The full action set |

They have different action sets, so one divergence rate across both would be a
number nobody could interpret. Every rate below carries its own denominator.

## A. One fixed decision state, 8 trials

Act II's state (`account_takeover`, p=0.5, full budget, nothing used).

| Measure | Result |
| --- | --- |
| Model answered | **8 / 8** — no fallback, no timeout, no refusal |
| Agreed with greedy | 0 |
| Differed | **8 / 8** |

Greedy picked `number_verify` every time; Gemini picked `sim_swap` every time.
That is a real, stable difference in what each considers the highest-value first
question — and it is *only* a difference. This measurement says nothing about
which is the better first check.

## B1. `nokia_paired` — whole investigations, 2 scenarios

| Scenario | Greedy | Gemini | Path | Label |
| --- | --- | --- | --- | --- |
| `stable_subscriber` | CHALLENGE / DEGRADED · 2 ops · 2 transport attempts | CHALLENGE / DEGRADED · 2 ops · 2 attempts | same | `llm` |
| `swapped_subscriber` | DECLINE / REFUTED · 2 ops · 2 attempts | DECLINE / REFUTED · 2 ops · 2 attempts | same | `llm` |

**verdict differs 0/2 · grade differs 0/2 · path differs 0/2 · genuine `llm`
labels 2/2.**

With only two checks available and a corroboration rule that requires the
second one, there is almost nothing for a planner to decide. Gemini adds
**nothing measurable here**, and saying so is the point: the paired
demonstration is a contract and provenance demonstration, not a planner
demonstration.

## B2. `custom_mock` — whole investigations, 6 scenarios

| Act | Greedy | Gemini | Path | Label |
| --- | --- | --- | --- | --- |
| act1 | ALLOW / ATTESTED_FULL · 2 ops · 3 units | ALLOW / **ATTESTED_PARTIAL** · 1 op · 2 units | different | `llm` |
| act2 | DECLINE / REFUTED · 6 ops · 10 units | DECLINE / REFUTED · 5 ops · 9 units | different | `llm` |
| act3 | ALLOW / ATTESTED_FULL · 3 ops · 4 units | ALLOW / ATTESTED_FULL · **5 ops · 7 units** | different | `llm` |
| act5 | CHALLENGE / UNRESOLVED · 5 ops · 7 units | CHALLENGE / UNRESOLVED · 5 ops · 7 units | different | `llm` |
| act6 | CHALLENGE / DEGRADED · 7 ops · 12 units | CHALLENGE / DEGRADED · 6 ops · 10 units | different | `llm` |
| act9 | ALLOW / ATTESTED_PARTIAL · 1 op · 1 unit | ALLOW / ATTESTED_PARTIAL · 1 op · 1 unit | same | **`policy`** |

**verdict differs 0/6 · grade differs 1/6 · path differs 5/6.**
Billable operations: greedy 24, Gemini 23. Evidence cost: greedy 37 units,
Gemini 36 units (**−3%**).

Model requests across the whole run: **21 scheduled, 21 answered, 0 failed, 0
fell back**. Ceiling 60; nothing was skipped for budget.

## What this actually shows

**Where Gemini helps.** It reaches the same verdict with slightly fewer
operations on the two adverse cases (act2: 5 vs 6; act6: 6 vs 7). A different
evidence path to the same answer is a real behavioural difference, and on these
fixtures it is marginally cheaper.

**Where it is equal.** Every verdict, on every scenario, in both cohorts. 0/8
verdict differences. On the paired Nokia cohort it is equal in every respect
including the path.

**Where it is worse.** act3: Gemini spent **5 operations and 7 units** where
greedy spent 3 and 4, for the same ALLOW / ATTESTED_FULL. act1: Gemini stopped
a check earlier and got a **weaker chain grade** — ATTESTED_PARTIAL instead of
ATTESTED_FULL — for the same decision. That is a worse outcome on the axis the
grade exists to measure.

**What must not be read into it.** Divergence is not improvement: 5 of 6 custom
paths differed and 0 of 6 verdicts did. `act9` is labelled `policy`, not `llm` —
no planner was consulted at all there, because policy choreographed the single
check. Counting it as model agreement would be wrong, which is why the label is
carried per row.

## Limitations

* **8 fixed-state trials and 8 investigations.** Small. A different day, a
  different model version, or a different temperature can move the paths.
* **One run.** No repetition, so nothing here has an error bar.
* **Fixtures, not fraud.** These scenarios were authored to demonstrate
  behaviour. Nothing here measures detection accuracy.
* **Costs are policy budget units**, not money. `operations` counts billable
  provider operations *attempted*; on these cohorts none of them left the
  process. A chain-link count is not an API-call count.
* **No tuning was done to make either planner win.** The prompt, the policy and
  the fixtures are the shipped ones.
* **Live model, real answers.** All 21 requests were answered by
  `gemini-3.6-flash`; none were intercepted. A run with intercepted answers
  would be a regression test, not this.
