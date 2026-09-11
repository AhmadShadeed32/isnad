from __future__ import annotations

from app.domain.enums import Hypothesis
from app.domain.schemas import RequestContext


def form(ctx: RequestContext) -> Hypothesis:
    """Read the request context and commit to a risk hypothesis.

    This is what makes the CAMARA calls *agent-initiated*: the hypothesis
    decides which evidence the planner will prioritise.
    """
    new_account = ctx.account_age_days is not None and ctx.account_age_days <= 1
    cod = (ctx.payment_method or "").lower() == "cod"
    high_value = bool(ctx.amount and ctx.amount.value >= 1000)

    if ctx.event in ("password_reset", "payout", "profile_change"):
        return Hypothesis.ACCOUNT_TAKEOVER
    if new_account and (cod or high_value):
        # New account moving real value on COD: classic takeover / mule setup.
        return Hypothesis.ACCOUNT_TAKEOVER
    if ctx.event == "signup" and new_account:
        return Hypothesis.BOT_FARM
    return Hypothesis.LEGIT
