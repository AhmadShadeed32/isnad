"""Run the demo acts from the CLI and print each verdict's rendered chain.

    python -m demo.run_acts
"""
from __future__ import annotations

import asyncio

from app.agent.investigator import build_investigator
from app.chain.builder import render_text
from app.domain.schemas import Money, RequestContext, VerificationRequest
from app.providers.mock import MockProvider

ACTS = [
    ("ACT I — Kill the OTP", VerificationRequest(
        phone_number="+99999991001",
        context=RequestContext(event="signup", account_age_days=0))),
    ("ACT II — Catch the ghost", VerificationRequest(
        phone_number="+99999991000",
        context=RequestContext(event="checkout", payment_method="cod",
                               account_age_days=0, amount=Money(value=4200)))),
    # No merchant-side history (account_age_days=0) + high-value COD => an
    # uncertain start; 6 years of SIM tenure is what actually clears them.
    ("ACT III — Approve the invisible", VerificationRequest(
        phone_number="+99999991002",
        context=RequestContext(event="checkout", payment_method="cod",
                               account_age_days=0, amount=Money(value=1500)))),
]


async def main() -> None:
    inv = build_investigator(MockProvider())
    for title, req in ACTS:
        print("\n" + "=" * 64 + f"\n{title}\n" + "=" * 64)
        verdict = await inv.investigate(req)
        print(render_text(verdict))


if __name__ == "__main__":
    asyncio.run(main())
