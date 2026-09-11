# Judge walkthrough report

## Reviewer and scope — read this before the results

| | |
| --- | --- |
| Reviewer | **An agent (this implementation's own), not a human judge and not an independent party.** |
| What it followed | `submission/JUDGE_GUIDE.md` → "Choosing the evidence source", plus the organizer access code a judge would be handed. No developer knowledge, no console, no source. |
| Environment | Clean Chromium context: no saved storage, no cookies, no preconfigured credential. |
| Target | A **local** instance (127.0.0.1:8123) with `ISNAD_DEMO_MODE=false` and real NaC enabled. |
| Date | 9 September 2026 |
| Revision | `4b8fc6a` plus the uncommitted judge paired-source change |

**This does not meet the guide's independent-deployed-walkthrough criterion,
and it is not presented as if it does.** Two things are missing and both are
named in the limitations at the end: the reviewer is this project's own agent
rather than an independent one, and the target is a local instance rather than
the deployed Space. A self-review finds real friction — it found three items
below, two of which were product defects — but it cannot tell you whether a
stranger would have got stuck somewhere an insider walks past.

## Results

Every row is what the browser actually showed. Timings are wall-clock for the
step, on a local instance, and are not a latency claim about anything.

| # | Task | Result | What was observed |
| --- | --- | --- | --- |
| 1 | Open `/judge`, identify the two evidence sources | **PASS** | Both visible without opening anything; **Mock preselected**; page interactive in 0.2 s |
| 1b | Identify the planner choice | **PASS** | `greedy`, `gemini` |
| 1c | Read the readiness wording | **PASS** | "Real NaC configured · access code required · **Nokia connection not yet verified**" — configuration, never a connection claim |
| 2 | Select a supported scenario, run mock + Greedy | **PASS** | 0.1 s → "Additional verification needed" |
| 2b | Identify the source of the result | **PASS** | "This result: Nokia-compatible responses answered locally · **no requests were sent to Nokia** · contract 2026-09-09.1" |
| 3 | Explain the outcome and the next merchant action from the UI alone | **PASS** | Summary, supporting evidence and the merchant's next step all on screen. **Friction 1 found here — see below.** |
| 3b | Complete the simulated merchant follow-up | **PASS** | "Open a manual review" → "Record: passed" → "Merchant review recorded · PASSED" |
| 4 | Verify the receipt's signature | **PASS** | "✓ Signature valid". **Friction 2 found here.** |
| 4b | Find and open the signed receipt | **PASS** | `/r/chn_8ea5b5d41f0e42f69f04`, titled "Isnad — evidence receipt" |
| 5 | Change the selector; check the finished result keeps its source | **PASS** | Label unchanged; "Applies to the next run" appeared |
| 6 | A wrong access code | **PASS** | "That access code was not recognized. Ask the organizer for the current code; mock evidence needs no code at all." No run was attempted. |
| 6b | The documented access step | **PASS** | Status became "configured and authorized for this session · Nokia connection not yet verified" |
| 6c | Allowance visible before spending | **PASS** | "Real NaC allowance · 6 / 24 · 2". **Friction 3 found here.** |
| 6d | **One real NaC run, from the page** | **PASS** | 0.7 s → "Additional verification needed", labelled "actual requests to Nokia's hosted simulator · contract 2026-09-09.1" |
| 6e | Request/response details | **PASS** | `POST …/sim-swap/v0/check → 200 (414 ms)`, `POST …/device-swap/v1/check → 200 (172 ms)`. No headers, no bodies, no credential. |
| 7 | Refresh recovery | **PASS** | A reload mints a fresh judge session; the previous receipt stays reachable and verifiable at its own URL |
| 8 | Arabic at 375 px | **PASS** | No horizontal overflow; the source explanation is translated |

One console error was recorded: the **403 from the deliberately wrong access
code** in task 6. That is the refusal working. Nothing else appeared.

## Friction found, and what was done about it

**1. A clean run was described as adverse. Fixed.**
`stable_subscriber` returns `swapped: false` from both checks — nothing came
back adverse — yet the plain-language summary read *"the links resolved and one
or more came back adverse to the claim."* The chain grades DEGRADED because two
links is a thin chain, and DEGRADED's shared sentence only describes the *other*
situation it covers (an adverse signal left uncorroborated). Telling a merchant
that evidence came back adverse when none did is precisely the error this
project exists not to make. `app/presentation.py` now states what actually
happened when no link is FLAG: *"the links resolved and none of them
contradicted the claim, but there were too few of them to settle it."* Both
halves are pinned:
`test_a_clean_two_check_run_is_not_described_as_adverse` and
`test_an_uncorroborated_adverse_run_still_says_adverse`. Task 3 retested: pass.

**2. The signature check's progress text is indistinguishable from a result.**
"Checking signed evidence…" is non-empty, so an automated reader that waits for
"some text" reads the placeholder as the answer — which is what happened on the
first pass of this walkthrough. A human sees it resolve. **Not changed in the
product**, because for a human the transient state is correct and useful; the
walkthrough now waits for the result instead. Recorded because a scripted
reviewer will hit it again.

**3. The allowance line is compact to the point of being cryptic.**
"Real NaC allowance · 6 / 24 · 2" needs the tooltip-free reader to know the
three numbers are session-left, deployment-left-this-hour, and per-run.
**Not changed**, deliberately: the long form ran over two lines on a 1280×720
laptop and pushed the Run button below the fold, which is a worse failure than
a terse line. Named here so the trade is visible rather than silent.

**Also changed while retesting** (found by the layout tests, not by the
walkthrough): the scenario and planner selects were truncating to "Si…" and
"Gre…" on a narrow column, and the header pill read "SIMULATOR · mock provider"
beside a real Nokia result. The selects now get the full row width with
accessible labels, and the pill says "SIMULATOR · **configured provider**: mock"
so it cannot be read as a claim about the run on screen.

## Screenshots

No secrets: the access code was typed into a password field, and no credential
appears in any request detail shown.

| File | What it shows |
| --- | --- |
| [`ui/walkthrough/01-mock-result.png`](ui/walkthrough/01-mock-result.png) | Mock run complete, with its source line |
| [`ui/walkthrough/02-merchant-review.png`](ui/walkthrough/02-merchant-review.png) | The simulated merchant review, recorded |
| [`ui/walkthrough/03-receipt.png`](ui/walkthrough/03-receipt.png) | The signed receipt page |
| [`ui/walkthrough/04-real-result.png`](ui/walkthrough/04-real-result.png) | A real Nokia run and its request/response details |
| [`ui/walkthrough/05-ar-mobile.png`](ui/walkthrough/05-ar-mobile.png) | Arabic at 375 px |

## Limitations

* **The reviewer is this project's own agent.** Not an independent reviewer, and
  certainly not a human judge. The guide's independent walkthrough criterion is
  **not met**.
* **The target is a local instance, not the deployed Space.** Deployed judge
  access is untested and is listed as pending in the README.
* **One pass of the task list, but not one real run.** No repetition of the
  walkthrough, no second reviewer, no measured comparison. The real-NaC step
  itself ran three times during the session — 11:10:08, 11:12:07 and 11:25:17
  UTC — and row 6d/6e documents the last of them, the one whose request/response
  panel is in `04-real-result.png`. All three are recorded in
  [`nac/observations/2026-09-09-judge-browser-real-runs.json`](nac/observations/2026-09-09-judge-browser-real-runs.json);
  what each attempt did and did not record is stated there rather than smoothed
  over here.
* **The injected-failure matrix was not exercised here.** It runs in isolated
  test fixtures (`docs/_internal/NAC_SIMULATOR_IMPLEMENTATION_RECORD.md`,
  Step 12) rather than by disturbing a running instance's quotas or credentials.
