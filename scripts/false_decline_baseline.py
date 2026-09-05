"""What does the agent actually save, against the stack it replaces?

Isnad's thesis is that collapsing "we could not check" into "the check failed"
manufactures false declines. That is an assertion until someone measures it, so
this script measures it — against the two decision rules real stacks actually
use, on identical evidence.

**The population is not hand-picked.** It is generated from `policy.yaml`'s own
signal vocabulary, which makes it exhaustive over the signals this system knows
rather than a set of examples chosen to flatter it:

* **ADVERSE-1** — one adverse signal, every other check clean. One case per
  adverse forward signal in the policy. This is the archetype the product
  exists for: the customer who replaced a SIM after losing a phone looks
  exactly like this.
* **UNKNOWN-1** — one *unanswerable* check, every other check clean. One case
  per zero-delta "could not determine" signal. This is the thesis, stated as
  data: consent withheld, or an operator that has not lit the API up.
* **FRAUD** — several adverse signals at once, the authored Act II shape. A
  control. Any system that fails to decline these is not safer, just looser.

**Both baselines see the same chain the agent built.** Only the decision rule
differs, so nothing here is a straw man built by feeding the baseline less
evidence:

* `single-signal` — any FLAG in the chain, decline. What a rules engine does.
* `collapse-unknowns` — any FLAG *or* any could-not-determine, decline. What a
  scoring model does when a missing feature is scored as a bad feature.

**A decline and a challenge are not comparable outcomes.** A decline is a
customer lost; a challenge is friction survived. So the metric is not "did it
allow" — it is *"did it decline a case that did not deserve it."*

    .venv311/bin/python scripts/false_decline_baseline.py

Scripted fixtures over a generated population, one run. This measures decision
*policy* against stated baselines. It is not an accuracy study, it is not
production traffic, and it does not claim a real-world false-decline rate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("ISNAD_DATABASE_URL", "sqlite://")
# Deterministic and free: this measures the policy, and a planner that stops in
# a different place must not move the number between runs.
os.environ["ISNAD_PROVIDER"] = "mock"
os.environ["ISNAD_PLANNER"] = "greedy"
os.environ.setdefault("ISNAD_MERCHANT_API_KEYS", "demo-merchant-key")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.investigator import build_investigator
from app.config import settings
from app.domain.enums import Action, Decision, Result
from app.domain.schemas import Area, Money, RequestContext, VerificationRequest
from app.policy.engine import get_engine
from app.providers import mock as mock_mod
from app.providers.mock import MockProvider

# The clean baseline every generated case is a single mutation of.
#
# Device Intelligence is UNRESOLVED here rather than PASS, because Nokia
# Network as Code exposes no device-reputation product: `docs/nac/
# device_intelligence.json` came back INFO / EVIDENCE_UNAVAILABLE. A population
# built on a reading no operator can return would measure a system that does not
# exist. See `app/providers/vocabulary.py`.
CLEAN: dict[Action, tuple[Result, str]] = {
    Action.NUMBER_VERIFY: (Result.PASS, "NUMBER_MATCH"),
    Action.SIM_SWAP: (Result.PASS, "SIM_STABLE"),
    Action.DEVICE_SWAP: (Result.PASS, "DEVICE_STABLE"),
    Action.LOCATION_VERIFY: (Result.PASS, "AT_CLAIMED_LOCATION"),
    Action.REACHABILITY: (Result.PASS, "REACHABLE_NORMAL"),
    Action.ROAMING: (Result.PASS, "HOME_NETWORK"),
    Action.DEVICE_INTELLIGENCE: (Result.INFO, "EVIDENCE_UNAVAILABLE"),
}

# Which action emits which signal, so a generated case stays coherent: a SIM
# Swap check cannot come back saying the device is risky.
#
# Only signals a CAMARA API can actually return appear here. DEVICE_RISKY and
# REACHABLE_BOTPATTERN were dropped on 2 Sep 2026: no Nokia NaC response
# produces either, so a case built on one was measuring fiction. That costs the
# population two adverse cases, and the figures below moved accordingly.
EMITS: dict[str, tuple[Action, Result]] = {
    "NUMBER_MISMATCH": (Action.NUMBER_VERIFY, Result.FLAG),
    "SIM_SWAPPED": (Action.SIM_SWAP, Result.FLAG),
    "DEVICE_SWAPPED": (Action.DEVICE_SWAP, Result.FLAG),
    "NOT_AT_CLAIMED_LOCATION": (Action.LOCATION_VERIFY, Result.FLAG),
    "REACHABLE_UNAVAILABLE": (Action.REACHABILITY, Result.FLAG),
    "ROAMING_NETWORK": (Action.ROAMING, Result.INFO),
    # Zero-delta: the network could not answer. Not evidence against anyone.
    "CONSENT_REQUIRED": (Action.NUMBER_VERIFY, Result.INFO),
    "PROVIDER_UNAVAILABLE": (Action.SIM_SWAP, Result.INFO),
    "LOCATION_UNKNOWN": (Action.LOCATION_VERIFY, Result.INFO),
    "LOCATION_PARTIAL": (Action.LOCATION_VERIFY, Result.INFO),
}

FRAUD = {
    **CLEAN,
    Action.SIM_SWAP: (Result.FLAG, "SIM_SWAPPED"),
    Action.DEVICE_SWAP: (Result.FLAG, "DEVICE_SWAPPED"),
    Action.LOCATION_VERIFY: (Result.FLAG, "NOT_AT_CLAIMED_LOCATION"),
    Action.NUMBER_VERIFY: (Result.FLAG, "NUMBER_MISMATCH"),
}

# Deliberately Act VI's context — a new account, cash on delivery, mid-value.
# The population is then "the customer this product exists for, holding each
# bad or missing reading in turn", rather than a context chosen to suit the
# answer. Every case shares it, so only the signal differs.
#
# claimed_location is set because the CLEAN baseline and several generated
# cases script a location_verify answer (AT_CLAIMED_LOCATION or
# NOT_AT_CLAIMED_LOCATION): without a claim on the request the provider
# boundary now returns EVIDENCE_UNAVAILABLE regardless of what is scripted
# here (P1), which would silently turn this population into one that never
# actually measures the location signal it is supposed to hold constant.
CONTEXT = RequestContext(
    event="checkout",
    payment_method="cod",
    account_age_days=0,
    amount=Money(value=1500),
    claimed_location=Area(lat=31.9539, lon=35.9106, radius_m=2000),
)


def baselines(chain) -> dict[str, Decision]:
    """The two rules being replaced, applied to a full evidence set.

    The baseline is given EVERY check, not the subset the agent chose to buy.
    That is deliberate and it is the conservative direction: a rules engine has
    no cost budget and runs its whole ruleset, so giving it less evidence than
    it would really have would be a straw man — and giving it more can only
    make it look better at catching fraud, never worse.
    """
    flagged = any(link.result == Result.FLAG for link in chain)
    unknown = any(link.result == Result.INFO for link in chain)
    return {
        "single-signal": Decision.DECLINE if flagged else Decision.ALLOW,
        "collapse-unknowns": Decision.DECLINE if (flagged or unknown) else Decision.ALLOW,
    }


def population(signal_deltas: dict[str, float]) -> list[dict]:
    """Every single-signal case the policy vocabulary admits, plus a control."""
    cases: list[dict] = []
    n = 0
    for signal, (action, result) in EMITS.items():
        if signal not in signal_deltas:
            continue
        delta = signal_deltas[signal]
        n += 1
        cases.append(
            {
                "name": signal,
                "group": "ADVERSE-1" if delta > 0 else "UNKNOWN-1",
                "number": f"+9995550{n:04d}",
                "scenario": {**CLEAN, action: (result, signal)},
                # One bad or missing reading on an otherwise clean line does not
                # justify losing the customer. A step-up does.
                "deserves_decline": False,
            }
        )
    # CORROBORATED-2 — every pair of STRONG adverse signals that different
    # checks can hold at once. Two independent checks disagreeing with the
    # customer is the case the product says SHOULD be declined, so this is
    # where leakage would show. Reported separately rather than folded into the
    # false-decline figure: labelling these "fraud" would be assuming the
    # answer, so what is reported is simply what each system does with them.
    strong = [
        sig
        for sig, (_a, res) in EMITS.items()
        if signal_deltas.get(sig, 0.0) >= 1.0 and res == Result.FLAG
    ]
    for i, first in enumerate(strong):
        for second in strong[i + 1 :]:
            a1, r1 = EMITS[first]
            a2, r2 = EMITS[second]
            if a1 == a2:
                continue  # one check cannot return two answers
            n += 1
            cases.append(
                {
                    "name": f"{first[:12]}+{second[:12]}",
                    "group": "CORROBORATED-2",
                    "number": f"+9995550{n:04d}",
                    "scenario": {**CLEAN, a1: (r1, first), a2: (r2, second)},
                    "deserves_decline": True,
                }
            )
    cases.append(
        {
            "name": "MULTI_ADVERSE",
            "group": "CORROBORATED-4",
            "number": "+9995559999",
            "scenario": FRAUD,
            "deserves_decline": True,
        }
    )
    return cases


async def run(cases: list[dict], engine) -> list[dict]:
    rows = []
    for case in cases:
        mock_mod.SCENARIOS[case["number"]] = case["scenario"]
        request = VerificationRequest(phone_number=case["number"], context=CONTEXT)

        # What a run-everything stack would hold: every check, always.
        provider = MockProvider()
        full = [await provider.gather(action, request) for action in CLEAN]

        verdict = await build_investigator(MockProvider()).investigate(request)
        rows.append(
            {
                **{k: case[k] for k in ("name", "group", "deserves_decline")},
                "isnad": verdict.decision,
                "grade": str(getattr(verdict.chain_grade, "value", verdict.chain_grade)),
                "isnad_checks": len(verdict.chain),
                "baseline_checks": len(full),
                "baseline": baselines(full),
            }
        )
    return rows


def sweep(engine) -> int:
    """The operating curve, because the honest answer to "you allow some
    corroborated-adverse cases" is not a denial — it is a dial.

    `allow_below` is what stops the agent early. Tighten it and it keeps buying
    evidence, so fewer adverse signals go unseen and more checks get paid for.
    Every point on this curve is one line in policy.yaml, no code change. A
    black-box score cannot be moved deliberately; this can, and a merchant
    picks the point that matches what a lost customer costs them.
    """
    original = engine.cfg["thresholds"]["allow_below"]
    print("allow_below   false declines   corroborated-adverse allowed   checks bought")
    print("-" * 78)
    try:
        for value in (0.15, 0.10, 0.05, 0.02):
            engine.cfg["thresholds"]["allow_below"] = value
            rows = asyncio.run(run(population(engine.cfg.get("signals", {})), engine))
            innocent = [r for r in rows if not r["deserves_decline"]]
            guilty = [r for r in rows if r["deserves_decline"]]
            fd = sum(1 for r in innocent if r["isnad"] == Decision.DECLINE)
            missed = sum(1 for r in guilty if r["isnad"] == Decision.ALLOW)
            checks = sum(r["isnad_checks"] for r in rows)
            flag = "  <- shipped default" if value == original else ""
            print(
                f"   {value:<11.2f}  {fd:2}/{len(innocent):<13} "
                f"{missed:2}/{len(guilty):<27} {checks:3}{flag}"
            )
    finally:
        engine.cfg["thresholds"]["allow_below"] = original
    print("\nOne line in policy.yaml per row. No code change, no retraining.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", help="write the full result here")
    ap.add_argument(
        "--sweep", action="store_true", help="report the operating curve across allow_below values"
    )
    args = ap.parse_args()

    engine = get_engine(str(settings.policy_path))

    if args.sweep:
        return sweep(engine)
    rows = asyncio.run(run(population(engine.cfg.get("signals", {})), engine))

    print(f"{'case':26} {'group':10} {'isnad':9} {'single-signal':14} {'collapse-unknowns':17}")
    print("-" * 82)
    for r in rows:
        b = r["baseline"]
        print(
            f"{r['name']:26} {r['group']:10} {r['isnad'].value:9} "
            f"{b['single-signal'].value:14} {b['collapse-unknowns'].value:17}"
        )

    innocent = [r for r in rows if not r["deserves_decline"]]
    guilty = [r for r in rows if r["deserves_decline"]]

    def declines(rows_, key=None):
        return sum(
            1 for r in rows_ if (r["baseline"][key] if key else r["isnad"]) == Decision.DECLINE
        )

    n = len(innocent)
    isnad_fd = declines(innocent)
    single_fd = declines(innocent, "single-signal")
    collapse_fd = declines(innocent, "collapse-unknowns")
    stepped_up = sum(1 for r in innocent if r["isnad"] == Decision.CHALLENGE)

    print("\n" + "=" * 82)
    print(f"Cases that did NOT deserve a decline: {n}\n")
    print(f"  declined by `single-signal`      {single_fd:2}/{n}   ({100 * single_fd / n:.0f}%)")
    print(
        f"  declined by `collapse-unknowns`  {collapse_fd:2}/{n}   ({100 * collapse_fd / n:.0f}%)"
    )
    print(f"  declined by Isnad                {isnad_fd:2}/{n}   ({100 * isnad_fd / n:.0f}%)")
    print(f"  stepped up by Isnad instead      {stepped_up:2}/{n}")
    print(f"\n  false declines avoided vs single-signal:     {single_fd - isnad_fd}")
    print(f"  false declines avoided vs collapse-unknowns: {collapse_fd - isnad_fd}")

    isnad_checks = sum(r["isnad_checks"] for r in rows)
    base_checks = sum(r["baseline_checks"] for r in rows)
    print(
        f"\n  network checks bought — run-everything {base_checks}, Isnad {isnad_checks} "
        f"({100 * (isnad_checks - base_checks) / base_checks:+.0f}%)"
    )

    caught = sum(1 for r in guilty if r["isnad"] == Decision.DECLINE)
    stepped = sum(1 for r in guilty if r["isnad"] == Decision.CHALLENGE)
    allowed = sum(1 for r in guilty if r["isnad"] == Decision.ALLOW)
    print(f"\nCorroborated adverse — two or more checks disagree: {len(guilty)}")
    print(f"  declined by Isnad                {caught:2}/{len(guilty)}")
    print(f"  stepped up by Isnad              {stepped:2}/{len(guilty)}")
    print(
        f"  ALLOWED by Isnad                 {allowed:2}/{len(guilty)}   "
        f"{'(nothing waved through)' if allowed == 0 else '*** LOOK AT THIS ***'}"
    )
    print("\nScripted fixtures over a generated population, one run. This compares")
    print("decision policy against two stated baselines on identical evidence.")
    print("It is not an accuracy study and claims no real-world decline rate.")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "cases": [
                        {
                            **r,
                            "isnad": r["isnad"].value,
                            "baseline": {k: v.value for k, v in r["baseline"].items()},
                        }
                        for r in rows
                    ],
                    "summary": {
                        "innocent": n,
                        "isnad_declines": isnad_fd,
                        "isnad_checks": isnad_checks,
                        "baseline_checks": base_checks,
                        "single_signal_declines": single_fd,
                        "collapse_unknowns_declines": collapse_fd,
                        "stepped_up": stepped_up,
                        "fraud_caught": caught,
                        "fraud_total": len(guilty),
                    },
                },
                indent=1,
            ),
            encoding="utf-8",
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
