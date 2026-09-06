# P3 implementation record

Archived the same way as [P1_P2_IMPLEMENTATION_RECORDS.md](P1_P2_IMPLEMENTATION_RECORDS.md)
and [P4A_IMPLEMENTATION_RECORD.md](P4A_IMPLEMENTATION_RECORD.md): detailed
validation evidence kept out of the active handoff. For current status and
next steps, read [the active handoff](PHASE2_HANDOFF.md).

**P3 implementation — 6 Sep (same day, follow-up session):** built merchant
CHALLENGE followup and completion reporting per §3 P3. Status: **DONE
LOCALLY** — every numbered step has concrete test or browser evidence.

## Insert-only `store.save` (step 1)

`store.save()` used `s.get(ChainRow, chain_id) or ChainRow(...)`: an upsert.
A second call with a colliding `chain_id` silently replaced the decision,
payload and signature — the one thing a signed receipt exists to make
impossible. Confirmed failing first (`tests/test_store_insert_only.py`: a
second `save()` for the same id overwrote the row instead of raising).
Fixed by always inserting a fresh row and catching the primary key's own
`IntegrityError` as `store.ChainAlreadyExists`, mirroring `announce.find`'s
existing IntegrityError-as-race-resolution pattern rather than a
Python-level check-then-write. `chain_id` carries 80 bits of randomness, so
a legitimate caller never collides — a collision is a bug or an attempt to
rewrite a previous verdict, and both now fail loud.

## CHALLENGE followups, in their own tables

New `ChallengeAttemptRow`, `ChallengeEventRow`, `IdempotencyRecordRow`
(`app/db/models.py`), migration `0002_challenge_followups` (verified: upgrade
on an empty database, downgrade back to `0001_initial_schema`, and upgrade
from a real `0001`-only database, all against a real SQLite file via
`alembic upgrade`/`downgrade`; `database._assert_schema_current()` confirmed
the migrated schema matches the models). Never a column on `ChainRow` — a
followup happens strictly after the signature is fixed, and nothing here is
ever folded back into `verdict_json`.

Store layer in `app/db/challenges.py`; routes in `app/api/routes_challenge.py`:

- `POST /v1/chains/{chain_id}/challenges` — opens an attempt. 404 for a
  missing or foreign chain (reuses `store.get_record_async`'s existing
  ownership check, so existence is not probeable across owners — same
  reasoning as `store._owned`). 409 `not_challenged` if the chain's signed
  decision was not CHALLENGE.
- `POST /v1/chains/{chain_id}/challenges/{attempt_id}/events` — reports
  PASSED/FAILED/ABANDONED. 404 for a missing or foreign attempt (including
  one that belongs to a *different* chain than the URL). 409
  `attempt_not_pending` if the attempt already has a terminal result, from a
  prior report or from expiry.
- `GET /v1/chains/{chain_id}/challenges` — the owned timeline. Available on
  any decision: empty on ALLOW/DECLINE and on a CHALLENGE chain with no
  attempts, never a 409 — a read costs nothing and checking is not an error.

**Contract decisions made explicit, not left implicit:**
- An `EXPIRED` transition is server-side only and mints no `ChallengeEventRow`
  — every event row is `provenance: "merchant_reported"` by construction,
  because there is no merchant submission to attribute a timeout to.
- Attempt transitions are compare-and-swap
  (`UPDATE ... WHERE status='PENDING'`, rowcount checked), not read-then-write.
  The expiry check runs *before* the CAS, so a report against an
  already-overdue attempt and a report racing the retention sweeper's own
  expiry both resolve the same way regardless of which side reaches the
  database first — both orderings are covered in
  `test_an_expired_attempt_cannot_be_reported_against`.

## Idempotency, durable rather than in-memory

`/v1/verify`'s `Idempotency-Key` cache (`app/cache.py`) is in-process memory
by design — acceptable there because a lost reservation just means a retry
recomputes evidence. The handoff is explicit that a challenge followup must
not rely on that: a merchant might not poll again for hours. New
`IdempotencyRecordRow`, keyed by `(owner_hash, operation, idempotency_key)`,
written in the *same* transaction as the attempt/event it guards — no
separate "pending" reservation phase, since the guarded work is local
database writes, not an external paid call. A concurrent retry for the same
key hits the row's own primary key `IntegrityError`; the loser re-reads what
the winner wrote and replays it.

New `app.chain.subject.idempotency_fingerprint(operation, *target, body=...)`,
alongside the existing `request_commitment` — keyed and domain-separated the
same way, but folding the target segments (`chain_id`, `attempt_id`) into the
HMAC input, not just the body. Without that, replaying the same key against a
*different* chain or attempt with an identical body would look like a valid
replay instead of a conflict. Confirmed by test: same key + same body + same
target replays; same key + different chain is a 409; same key + different
body against the same attempt is a 409 (`tests/test_challenge_contract.py`).
Durability itself confirmed by reading the row back through a brand-new
`SessionLocal()`, not by asserting on any process-local state.

## Retention and posture

`purge_followups()` and `purge_idempotency_records()` (`app/db/challenges.py`)
wired into `retention.purge_once()` alongside the existing announcement/screen
sweeps. New settings `challenge_attempt_ttl_seconds` (900) and
`challenge_followup_retention_seconds` (2592000), both `Field(gt=0)`-validated,
added to `.env.example` and to `/v1/privacy/posture`'s retention list.
Retention is measured from `terminal_at`, stamped by whichever transition
resolves the attempt (report or expiry) — never from `created_at`, which
would let a still-open attempt be swept just for being old (the consent
store's own P4a fix for exactly this bug is the direct precedent).

## Merchant pilot harness: "Continue merchant verification"

Extended `demo/merchant_pilot` with `POST /api/flows/{flow_id}/challenge` and
`POST /api/flows/{flow_id}/challenge/events`, both session+CSRF gated like
the existing `/api/flows` mutation. The harness derives its own stable
Idempotency-Key from `(flow_id[, attempt_id, result])` so a double-submit
click reopens or replays rather than minting a duplicate. `flow.html` renders
the followup as its own separate `.challenge` card, entirely apart from
`renderOutcome()`'s presentation of the signed decision — confirmed by
`tests/test_merchant_pilot.py`'s new tests (3 of which were confirmed failing
— 404, since the routes did not exist — against the pre-implementation code
via `git stash`) and, live, in a real browser below.

## Browser evidence (this session, real processes, not mocked)

Started `isnad-nac-fake` (port 8000), `fake-operator` (port 8801) and
`merchant-pilot` (port 8802) as real local uvicorn processes, exactly as
P4a's own verification did, and drove the whole path through the Browser
tool:

1. Logged into the merchant pilot dashboard, started a consent for
   `+15551234567`.
2. On the fake operator's approval screen, chose "signed in with a different
   number" (`NUMBER_MISMATCH`) to reach a real CHALLENGE decision rather than
   asserting it exists.
3. The flow page showed the existing "Additional verification needed"
   presentation (`chain_grade: UNRESOLVED`, decision `CHALLENGE`), and below
   it, unprompted, the new "Continue merchant verification" panel — proving
   the panel gates correctly on `result.decision === "CHALLENGE"` rather than
   always rendering.
4. Clicked "Start a followup" — a real `POST /v1/chains/{chain_id}/challenges`
   round trip created attempt `chgat_2c18980c9a6942529ea7`, `PENDING`.
5. Clicked "Failed" — a real `POST .../events` resolved it; the UI replaced
   the buttons with "Merchant verification: FAILED", and the presentation
   card above was untouched, character for character.
6. Verified independently via `curl` against Isnad directly (not through the
   harness): `GET /v1/chains/{chain_id}/challenges` returned the same
   attempt/event; `GET /v1/receipts/{chain_id}` (the public receipt) returned
   a `signed_payload` with no mention of the followup anywhere in it — the
   thing P3 exists to guarantee, confirmed on a real signed chain, not just
   in a unit test.

No console errors, no server errors, in either the Isnad or merchant-pilot
process logs, at any point in the sequence.

## Test and lint evidence

Full suite: 623 → 627 passed after this session's additions (`store` insert-
only: +2; `test_challenge_contract.py`: +25; `test_merchant_pilot.py`: +4;
one `test_retention.py` assertion loosened to match the sweep's new return
keys). `ruff check app tests scripts demo`: clean.
`scripts/handset_validation.py contract`: still passes (unaffected by P3,
confirmed rather than assumed).

## Known gaps

1. Idempotency replay of a **conflicting business state** (e.g. retrying the
   exact same key+body against an attempt that expired *after* the original
   write) was not separately exercised — only the two orderings of the race
   itself were. Low risk: the CAS and the idempotency table are independent
   mechanisms and neither depends on the other's timing.
2. The merchant pilot harness does not expose the timeline (`GET
   /v1/chains/{chain_id}/challenges`) itself — it only shows the single
   attempt it created. A merchant integrating directly against the Isnad API
   gets the full timeline; the harness's own UI does not surface a second
   attempt if one were opened outside the harness (e.g. directly via curl).
3. No load/concurrency test exercises two simultaneous event reports against
   the same attempt with different results under real thread/process
   parallelism — the CAS logic is reasoned to be correct (same pattern as
   `announce.find`'s proven IntegrityError handling) but not stress-tested.
4. Postgres was not exercised directly; `_assert_schema_current()` was
   verified against a migrated SQLite database, which is dialect-independent
   SQLAlchemy inspection but not a substitute for a real Postgres run.
5. `ChallengeEventRow` does not itself carry `idempotency_key`/
   `request_fingerprint` columns — only the shared `idempotency_records` table
   does, which is TTL-purged. Functionally correct (no replay/conflict
   behavior depends on it), but an audit that outlives that TTL loses the
   original request's fingerprint. P5's `MerchantOutcomeEventRow` carries both
   as columns for exactly this reason; retrofitting `ChallengeEventRow` the
   same way was not done here to avoid re-touching P3 code after it shipped.
6. P5 ("collect outcomes before calibrating scores") is now also DONE
   LOCALLY — see [P5_IMPLEMENTATION_RECORD.md](P5_IMPLEMENTATION_RECORD.md).
