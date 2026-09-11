"""Versioned artifacts for the judge lab (I1's shared contract).

A `LabRun` is a fully offline, reproducible record of one investigation run
against a fixed synthetic fixture — never a second decision engine, never a
substitute for the real signed `Verdict`. Everything here is exported
allowlisted/structured data; nothing here enters the signed payload.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

SCHEMA_VERSION = 2

# What a diagnostic on a TraceEvent may say when a step did not simply pass or
# flag. Never free text, never an exception message (I1 step 2).
DIAGNOSTIC_CODES = frozenset(
    {"no_key", "timeout", "malformed", "invalid_action", "call_cap", "provider_error"}
)


@dataclass
class TraceEvent:
    run_id: str
    sequence: int
    event_type: str
    phase: str
    selection_source: str | None = None
    action: str | None = None
    rationale: str | None = None
    budget_before: float | None = None
    budget_after: float | None = None
    evidence_step_ref: int | None = None
    diagnostic: str | None = None
    # What the network actually answered, for the evidence events. Without
    # these a trace row says only "evidence link #3", and I1's acceptance —
    # an auditor reconciling every check with its evidence link — has nothing
    # to reconcile against. Strictly the bounded vocabulary this codebase
    # defines (see providers/vocabulary.py): `detail` is deliberately absent
    # because on the NaC path it carries operator-supplied prose, and
    # `max_age_hours` is the window the question covered, never the age of an
    # event, because CAMARA answers with a boolean and no timestamp.
    api: str | None = None
    signal: str | None = None
    result: str | None = None
    max_age_hours: float | None = None
    belief_after: float | None = None

    def __post_init__(self) -> None:
        if self.diagnostic is not None and self.diagnostic not in DIAGNOSTIC_CODES:
            raise ValueError(f"unknown diagnostic code: {self.diagnostic!r}")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LabRun:
    run_id: str
    scenario_id: str
    fixture_digest: str
    policy_digest: str
    code_revision: str
    dirty: bool
    generated_at: str
    planner_source: str
    timing_basis: str
    events: list[TraceEvent] = field(default_factory=list)
    outcome: dict | None = None
    receipt_ref: str | None = None
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "fixture_digest": self.fixture_digest,
            "policy_digest": self.policy_digest,
            "code_revision": self.code_revision,
            "dirty": self.dirty,
            "generated_at": self.generated_at,
            "planner_source": self.planner_source,
            "timing_basis": self.timing_basis,
            "events": [e.to_dict() for e in self.events],
            "outcome": self.outcome,
            "receipt_ref": self.receipt_ref,
        }
