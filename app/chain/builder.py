from __future__ import annotations

from app.chain.models import Verdict


def render_text(verdict: Verdict) -> str:
    """Render a verdict's chain as the human-readable 'isnad' — the ordered,
    timestamped links a judge or auditor reads top to bottom."""
    lines = [f"VERDICT: {verdict.decision.value}  (P(fraud)={verdict.confidence})",
             f"Hypothesis: {verdict.hypothesis}",
             f"Evidence: {len(verdict.chain)} checks · cost={verdict.evidence_cost} · latency={verdict.latency_ms}ms",
             f"Reason: {verdict.reason}",
             "Chain:"]
    for link in verdict.chain:
        mark = {"PASS": "✓", "FLAG": "✗", "INFO": "·"}.get(link.result.value, "·")
        lines.append(f"  {link.step}. [{mark}] {link.api}: {link.detail}  ({link.consent_basis})")
    return "\n".join(lines)
