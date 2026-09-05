from __future__ import annotations

from dataclasses import dataclass, field

from app.policy.engine import logodds_to_p


@dataclass
class Belief:
    """The agent's running policy risk score.

    Configured weights add in log-odds space, then a logistic transform maps
    the sum to 0..1. This resembles naive Bayes but is not calibrated against
    observed outcomes; correlated signals can count the same event twice.
    ``p_fraud`` is retained as an internal compatibility name.
    """

    logodds: float
    trace: list[tuple[str, float]] = field(default_factory=list)

    @property
    def p_fraud(self) -> float:
        return logodds_to_p(self.logodds)

    def apply(self, label: str, delta: float) -> None:
        self.logodds += delta
        self.trace.append((label, delta))

    def explain(self, decision: str, unresolved: bool = False) -> str:
        if unresolved:
            return "Insufficient network evidence — consent or a provider result was unavailable."
        flags = [lbl for lbl, d in self.trace if d > 0.4]
        clears = [lbl for lbl, d in self.trace if d < -0.4]
        if decision == "DECLINE":
            return (
                "Fraud indicators: " + ", ".join(flags) + "." if flags else "Multiple risk signals."
            )
        if decision == "ALLOW":
            return "Cleared by: " + ", ".join(clears) + "." if clears else "No risk signals found."
        return "Unresolved doubt — cheapest step-up needed before trusting."
