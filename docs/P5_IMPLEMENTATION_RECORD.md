# P5 implementation record

Archived the same way as [P1_P2_IMPLEMENTATION_RECORDS.md](P1_P2_IMPLEMENTATION_RECORDS.md),
[P4A_IMPLEMENTATION_RECORD.md](P4A_IMPLEMENTATION_RECORD.md) and
[P3_IMPLEMENTATION_RECORD.md](P3_IMPLEMENTATION_RECORD.md): detailed
validation evidence kept out of the active handoff. For current status and
next steps, read [the active handoff](PHASE2_HANDOFF.md).

**P5 implementation — 6 Sep (same day, follow-up session):** built merchant
outcome reporting (order status, fraud assessment) per §3 P5. Status: **DONE
LOCALLY** — every numbered step has concrete test or browser evidence.

## Contract decisions made explicit before writing code

- **Challenge execution is not a reportable dimension.** The handoff names
  three independent dimensions, but only two — `order_status` and
  `fraud_assessment` — are ever POSTed through `/v1/chains/{chain_id}/outcomes`.
  Challenge execution already exists in P3's own `ChallengeAttemptRow`/
  `ChallengeEventRow`; it is read fresh from there whenever a report needs it
  (`outcomes.challenge_execution_summary`), so there is exactly one place that
  fact can come from. `tests/test_outcomes_contract.py::
  test_a_passed_challenge_does_not_fill_in_a_fraud_label` guards against a
  future change accidentally deriving a fraud label from a challenge result.
- **No decision gate**, unlike P3. The handoff is explicit — "Outcome APIs
  may refer to any owned decision, including ALLOW/DECLINE" — so
  `routes_outcomes.py` checks ownership only, never `verdict.decision`.
- **Exactly one current (non-superseded) event per (owner, chain, dimension)
  at a time.** A first report on a dimension takes no `supersedes_event_id`;
  every later report on that dimension must name the current head or the
  write is a 409 `dimension_already_labelled`. This is enforced by a partial
  unique index (`ux_outcome_current_per_dimension`, `WHERE superseded_by IS
  NULL`) on `MerchantOutcomeEventRow`, not only by the store's own
  read-then-write check — two concurrent *first* reports on the same
  dimension collide on that index and the loser gets
  `DimensionAlreadyLabelled`, the same class of error a stale correction gets.

## Schema: a discriminated union, not one validated field

`OrderStatusReport`/`FraudAssessmentReport` (`app/domain/schemas.py`), joined
as `OutcomeReportRequest = Annotated[Union[...], Field(discriminator="dimension")]`
so FastAPI parses the right shape per `dimension` rather than one loose model
validated ad hoc in the route. Both are `extra="forbid"`. `FraudAssessmentReport`
has a `model_validator` requiring `basis` for `CONFIRMED_FRAUD`/
`CONFIRMED_LEGITIMATE` and forbidding it otherwise — the schema itself is what
keeps a payment dispute or a lack of feedback from carrying a confirmed label,
not a convention a route author has to remember. `occurred_at` rejects a naive
datetime via `field_validator`; `late_report: bool = False` is stored as told,
never itself a validation gate — "accept explicitly labelled late reports"
literally.

## Idempotency: durable, plus its own audit columns

Reuses P3's `IdempotencyRecordRow` for the actual replay/conflict mechanism
(same owner+operation+key primary key, same fingerprint-mismatch-is-a-409
behavior). Additionally, `MerchantOutcomeEventRow` carries its own
`idempotency_key`/`request_fingerprint` columns — P3's own known-gap review
(see its record) noted that the shared table alone is TTL-purged, so an
outcome event's audit trail would otherwise not survive past
`idempotency_ttl_seconds`. `app.chain.subject.idempotency_fingerprint` is new,
alongside `request_commitment`: same keyed, domain-separated HMAC, but folding
`chain_id` (and `attempt_id` for P3) into the input so a key reused against a
different target with an identical body is still a 409.

## Insert-then-single-transaction, not two-phase

The whole write — insert the new event, CAS-supersede the old head if there
was one, insert the idempotency row — happens in one `SessionLocal()`
transaction, committed once. On `IntegrityError`, the handler disambiguates
by whether the idempotency row now exists: if so, a concurrent retry of the
same key won the race and this call replays it; if not, two concurrent
*first* reports collided on the partial unique index and this call raises
`DimensionAlreadyLabelled`. No separate "pending" reservation exists —
unlike `/v1/verify`'s idempotency cache, the guarded work here is local
database writes, not an external paid call, so there is nothing to reserve
before doing.

## Retention

`purge_outcomes()` (`app/db/outcomes.py`) deletes by `reported_at` past
`outcome_retention_seconds` (default 15552000 = 180 days) — **current heads
included**, not just superseded history. This is a literal reading of "purge
by server-reported time": a dimension whose only event ages out reverts to
"not yet reported" rather than being kept forever by virtue of being current.
Documented on the config field and in `/v1/privacy/posture`'s retention list,
not left implicit.

## Merchant pilot harness

`POST /api/flows/{flow_id}/outcomes`, session+CSRF gated like every other
mutation. The Idempotency-Key folds in the *current head's own event id* (or
`"none"` for a first report): resubmitting the exact same value replays,
while choosing a different value against the same starting point is always a
fresh, successful correction — never a confusing "key reused" 409 for what is,
from the operator's chair, just clicking a different button. `flow.html`
renders order-status and fraud-assessment reporting as its own `.outcomes`
card, available regardless of decision (unlike the P3 `.challenge` card,
which only ever appears for CHALLENGE).

**A real defect found live, not by any unit test:** the fraud-assessment
`<select>`'s first (default) option is `CONFIRMED_FRAUD`, which needs a
basis — but the basis field's visibility only updated on a `change` event,
which a default, untouched selection never fires. Clicking "Report" with the
default value silently sent no `basis`, and Isnad correctly rejected it with
no visible reason why. Confirmed via `javascript_tool` inspection
(`getComputedStyle(basis).display` was `"none"` while `fraud-value` already
read `"CONFIRMED_FRAUD"`), fixed by initializing the basis field's visibility
from the live value at render time in addition to reacting to `change`, and
re-confirmed the same way after the fix. No Python test could have caught
this — it is pure client-side DOM state — so it is recorded here as browser
evidence rather than as a `pytest` regression.

## Browser evidence (this session, real processes, not mocked)

Reused the exact same three-process setup and CHALLENGE journey P3's own
verification proved (`isnad-nac-fake` :8000, `fake-operator` :8801,
`merchant-pilot` :8802; NUMBER_MISMATCH on the fake operator's approval
screen), then continued past where P3 stopped:

1. Reported the CHALLENGE followup as FAILED (P3's own panel), confirming the
   two panels — P3's `.challenge` card and P5's new `.outcomes` card — render
   side by side without interfering with each other.
2. Found and fixed the basis-visibility defect above.
3. Reported `order_status: CANCELLED` (first report on that dimension, no
   `supersedes_event_id`) — UI showed "Current: CANCELLED".
4. Reported `fraud_assessment: CONFIRMED_FRAUD` with `basis:
   manual_investigation` — UI showed "Current: CONFIRMED_FRAUD
   (manual_investigation)".
5. Verified independently via `curl` against Isnad directly (not through the
   harness): `GET /v1/chains/{chain_id}/outcomes` returned both events as
   current heads with the correct timeline; `GET /v1/chains/{chain_id}/challenges`
   still showed the FAILED attempt from step 1, unaffected; `GET
   /v1/receipts/{chain_id}` (the public receipt) contained neither
   "CANCELLED" nor "CONFIRMED_FRAUD" anywhere in its `signed_payload` — the
   one occurrence of the substring "challenge" in the response was the
   signed `"decision":"CHALLENGE"` field itself, not a leak.
6. Ran `scripts/merchant_outcome_report.py` directly against that same live
   database (`ISNAD_DATABASE_URL` pointed at the browser-check SQLite file,
   `ISNAD_MERCHANT_API_KEY=pilot-test-key`): it correctly reported **0
   eligible chains**, because the chain's `provider_sources` was `["nac_fake"]`
   — proving the synthetic-run filter works against a real chain produced by
   a real (if offline) provider, not only against a hand-built fixture.

No console errors, no server errors, in either the Isnad or merchant-pilot
process logs, at any point in the sequence.

## Test and lint evidence

Full suite: 627 → 659 passed after this session's additions
(`test_outcomes_contract.py`: +22; `test_outcome_report.py`: +6;
`test_merchant_pilot.py`: +4). `ruff check app tests scripts demo`: clean.
Migration `0003_outcomes` verified the same three ways as `0002` before it:
upgrade on an empty database, downgrade back to `0002_challenge_followups`,
and upgrade from a real `0002`-only database — plus
`database._assert_schema_current()` confirming the migrated schema matches
`models.py`.

## Known gaps

1. No load/concurrency test exercises two simultaneous *first* reports on the
   same (owner, chain, dimension) under real thread/process parallelism —
   the partial-unique-index collision path is reasoned to be correct (same
   IntegrityError-disambiguation pattern P3 already uses) but not
   stress-tested.
2. Postgres was not exercised directly for the partial unique index
   (`postgresql_where=...`); only SQLite's `sqlite_where` path was actually
   exercised end-to-end. The Alembic migration defines both, but only one was
   run.
3. `scripts/merchant_outcome_report.py` reads `ISNAD_MERCHANT_API_KEY` from
   the environment and computes `owner_hash()` itself — there is no
   authenticated HTTP path for a merchant-wide report; a real deployment
   would need this run in a context that already has the key (an operator
   shell, not a public surface).
4. The merchant pilot harness's `.outcomes` card re-renders (and resets its
   `<select>`s to their defaults) on every poll tick rather than preserving
   an in-progress, unsubmitted selection — a minor UX rough edge, not a
   correctness issue, consistent with how the `.challenge` card already
   behaves.
5. No calibration proposal exists or was attempted, per the handoff's own
   instruction not to retrain or tune policy in this package.
