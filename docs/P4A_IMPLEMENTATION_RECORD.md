# P4a implementation record

Archived the same way as [P1_P2_IMPLEMENTATION_RECORDS.md](P1_P2_IMPLEMENTATION_RECORDS.md):
detailed validation evidence kept out of the active handoff. For current
status and next steps, read [the active handoff](PHASE2_HANDOFF.md).

**P4a implementation — 6 Sep (same day, follow-up session):** built the local
live-consent journey and current OAuth contract per §3 P4a. Status: **DONE
LOCALLY** — every numbered step in §3 P4a has concrete test or browser
evidence; P4b (a real handset/operator) remains untouched and out of scope for
this session, as instructed.

## Contract decision, checked against the source before building

Before writing any code, fetched the official V1 documentation
(networkascode.nokia.io, reviewed 6 Sep 2026) rather than assuming the
handoff's prior summary was complete. It confirmed, with no surprises: the
authorization request needs `state` and a separate `nonce`, `prompt=none` for
network-based authentication, and PKCE is not mentioned (none was
implemented). The token endpoint returns both `access_token` and `id_token`;
the nonce is validated as an `id_token` claim. This matches §3 P4a step 1's
prior findings and is the contract every piece below implements.

## Consent-contract defects fixed first (before the OAuth work)

Five defects in the existing `app/consent.py`/`routes_consent.py`, each
confirmed failing against the pre-fix code before the fix, in
`tests/test_consent_contract.py`:

1. **`_sweep()` deleted a terminal record the instant *any* other `create()`
   ran**, regardless of that record's own retention window — a merchant
   polling a just-completed flow could see a 404 mid-poll. Added
   `ConsentRecord.terminal_at`, stamped on every transition into
   COMPLETED/DENIED/FAILED/EXPIRED (including the lazy `_expire()` path), and
   a new `ISNAD_NAC_CONSENT_TERMINAL_RETENTION_SECONDS` (default 300) that
   `_sweep()` respects before deleting a terminal record.
2. **The request commitment was recomputed at completion time** from
   `record.request` — the same mutable object handed in at `create()` — rather
   than frozen at approval. `create()` now deep-copies the request and
   computes `request_hash` once, stored on the record;
   `complete_number_verification` in `routes_consent.py` uses that stored
   hash instead of calling `request_commitment()` again.
3. **No `nonce` existed** — `state` was the only random value, and the OIDC
   contract requires a separate one. Added `ConsentRecord.nonce`
   (`secrets.token_urlsafe(32)`, independent of `state`), threaded through
   `begin_number_verification`/`exchange_number_verification_code`'s contract
   and every provider/test double that implements it.
4. **`deny()` never cleared `access_token`** — unreachable via the current API
   (deny only fires from PENDING/EXCHANGING, where a token isn't set yet), but
   the stated contract is "every terminal transition clears it," not "only
   when one happens to be present." Fixed defensively.
5. **A record could expire without ever getting a `terminal_at`**, which
   would have left it stuck in the store forever once retention-based
   deletion replaced the old unconditional sweep. `_sweep()` now calls
   `_expire()` (which stamps `terminal_at`) on every record before deciding
   whether to delete it.

## ID-token validation, shared rather than duplicated

New `app/oidc.py`: JWKS-based `validate_id_token()` (signature, issuer,
audience, expiry with configurable leeway, and the nonce claim compared with
`hmac.compare_digest`). Fetches JWKS with the caller's own `httpx.AsyncClient`
instead of PyJWT's built-in `PyJWKClient` (which uses `urllib`), specifically
so tests can bind it to `httpx.ASGITransport` against an in-process fake with
no real socket. Added `pyjwt>=2.13.0` to `requirements.txt`/`pyproject.toml`
and regenerated `requirements.lock.txt` (checked for open advisories at
2.13.0: none). `tests/test_oidc.py` (10 cases): valid token, mismatched
nonce, missing nonce claim, wrong audience, wrong issuer, expired token, a
token forged with a different signing key, an unknown `kid`, `alg=none`
forgery, and a malformed JWKS document — all against a real RSA keypair and a
hand-built JWKS served through `httpx.MockTransport`.

New `app/providers/oidc_flow.py`: `build_authorization_url()` (always
includes `state`, `nonce`, `prompt=none`) and
`complete_number_verification_exchange()` (exchanges the code, requires both
`access_token` and `id_token` in the response — a bare access-token response
is treated as a contract violation, not "compatible anyway" — then validates
the id_token via `app/oidc.py`). This module is the **one** implementation of
the manual OAuth flow; `NacProvider`'s non-SDK path and the new
`FakeNacProvider` both call it, so the offline fake exercises the same
validation a real deployment would rather than a parallel stand-in.
`tests/test_oidc_flow.py` (8 cases) covers the URL builder, HTTPS
enforcement, Basic-auth client secret handling, a provider HTTP failure, a
full successful exchange, a missing id_token, a missing access_token, and a
replayed/stale nonce.

`NacProvider.begin_number_verification`/`exchange_number_verification_code`
now require `nonce` and pass it (with `prompt=none`) to both the SDK path and
the manual fallback. The SDK path's old behavior — retry a `TypeError` with
`scope` silently dropped — is removed for `nonce`/`prompt` specifically:
silently dropping them would ship a request the documented contract calls
replay-vulnerable, so a `TypeError` now falls through to the next candidate
method or the manual builder instead. The manual exchange path requires
`ISNAD_NAC_ISSUER`/`ISNAD_NAC_JWKS_URI` to be configured and fails closed
(clear `RuntimeError`) if they are not. `tests/test_nac_provider.py` gained
cases for: the SDK path forwarding nonce/prompt, a `TypeError`-raising SDK
method falling through to the manual URL instead of retrying with fewer args,
a successful manual exchange with a real generated id_token, a rejected
replayed nonce, a rejected missing id_token, and the missing-issuer-config
failure.

## The offline fake operator

New `demo/fake_operator/app.py`: a small separate FastAPI app implementing
discovery, JWKS, an authorize screen, single-use codes, Basic-auth'd token
exchange issuing a real RS256 id_token, and `/verify`. Two departures from
real operator behavior are stated in its own module docstring rather than
left implicit: `prompt=none` means no interactive screen in production (this
fake still renders one, as a testing convenience), and the approval screen
lets the tester pick NUMBER_MATCH/NUMBER_MISMATCH/deny — a real subscriber
never gets to choose their own verification result.

New `app/providers/fake_nac.py` (`FakeNacProvider`, selected via
`ISNAD_PROVIDER=nac_fake`, added to `Settings.provider`'s `Literal` and
excluded from `makes_billable_calls()`) drives the fake operator through the
same `oidc_flow`/`oidc` modules `NacProvider` uses. It implements Number
Verification only; every other action reports `EVIDENCE_UNAVAILABLE` with a
detail naming that limitation, rather than fabricating SIM/device/location
signals the fake has no API for.

`tests/test_fake_operator.py` (9 cases, all over `httpx.ASGITransport` — no
real socket) drives the full authorize → decide → exchange → gather round
trip for NUMBER_MATCH, NUMBER_MISMATCH, and denial; confirms a code is
single-use, wrong client credentials are rejected, every non-Number-Verify
action reports unavailable, a missing token reports `CONSENT_REQUIRED`, and
`makes_billable_calls()` stays `False` for `nac_fake`.
`python-multipart` (needed for FastAPI's `Form()` parsing) was added to
`requirements-dev.txt`/`pyproject.toml`'s `dev` extra only — `demo.fake_operator`
is never imported by `app.main`, so the production lock is untouched.

## The browser-preferring callback redirect (§3 P4a step 8)

`tests/test_consent_html_redirect.py` written and confirmed failing first (4
of 7 cases): a request to
`/v1/consents/number-verification/callback` whose `Accept` header explicitly
prefers `text/html` over `application/json` is now redirected 303 to a new
generic `/consent/complete` page — for every outcome (success, denial,
replay-conflict, expiry, unknown state, exchange failure), not only success.
Absent, wildcard-only, or tied preferences keep JSON, so
`scripts/handset_validation.py` and every existing API test is unaffected
(confirmed: `_prefers_html()` counts only an explicit, strictly-higher
`text/html` quality — a bare `*/*` credits neither type). `Vary: Accept` and
`Cache-Control: no-store` are set on both branches. New
`app/static/consent_complete.html` and `routes_consent.page_router` (no `/v1`
prefix, matching `routes_judge.page_router`'s split), registered in
`app/main.py`.

## The single-merchant reference harness

New `demo/merchant_pilot/app.py` (+ `static/index.html`, `static/flow.html`):
a standalone FastAPI app that calls Isnad's existing consent API over `httpx`
with `ISNAD_MERCHANT_API_KEY` read from the environment — the browser never
receives it (confirmed by a test asserting the key string never appears in
any HTTP response body). An authenticated operator session (random
server-side ID, HttpOnly/`SameSite=Lax` cookie, `PILOT_SESSION_TTL_SECONDS`
expiry, bounded login attempts via a fixed-window `LoginThrottle`,
`secrets.compare_digest` credential comparison) gates every route; mutating
routes require a synchronizer-pattern CSRF token plus an `Origin` check. A
middleware rejects any client whose address is not loopback/private unless
`PILOT_ALLOW_PUBLIC=true` is set. The app refuses to start at all without
`ISNAD_MERCHANT_API_KEY`/`PILOT_OPERATOR_USERNAME`/`PILOT_OPERATOR_PASSWORD`
configured — no default credential exists to forget to change.

Creating a flow (`POST /api/flows`) calls Isnad's
`/v1/consents/number-verification` and returns a QR code (`segno`, inlined
SVG, no external origin) over the authorization URL; the flow page
(`GET /flow/{id}`) polls `GET /api/flows/{id}` with bounded exponential
backoff (1.5s → 8s cap) and stops at a terminal state. That endpoint calls
Isnad's status endpoint and, once `AUTHORIZED`, calls the single-use `/verify`
exactly once per flow — guarded by a `threading.Lock` plus a `verifying` flag
so two concurrent polls (e.g. two open tabs) cannot both fire it. The
completed result is rendered through the existing `Presentation` fields
already on `VerificationResponse` — no new presentation logic was written for
this harness.

`tests/test_merchant_pilot.py` (10 cases, `httpx.MockTransport` standing in
for Isnad): public-client rejection, login throttling, session creation and
the merchant key's absence from the dashboard HTML, unauthenticated
redirects, CSRF enforcement (missing and wrong token), a full create → poll →
COMPLETED round trip via mocked Isnad responses, phone validation, logout,
and a regression (below) for a transient Isnad outage.

## A real defect found during browser verification, not just written to pass tests

Running the actual three processes (Isnad on `nac_fake`, the fake operator,
and the merchant pilot) and driving them through the Browser tool — not a
background agent, per this session's explicit instruction — surfaced a real
bug no unit test had caught: restarting the Isnad server mid-poll produced an
unhandled `httpx.ConnectError` inside `get_flow`, a raw 500 to the operator's
browser, and left `FlowRecord.verifying` stuck `True` forever (the
exception unwound past the line that resets it), permanently blocking that
flow from ever completing even after Isnad came back. Wrote a regression test
using `httpx.MockTransport` raising `ConnectError`, confirmed it failed
against the pre-fix code for that exact reason (via `git stash` of just the
fix), then wrapped the poll in `try/except httpx.HTTPError` and the verify
call's `verifying` reset in a `finally`.

## Browser evidence, actually performed

Ran three local uvicorn processes (`app.main:app` with
`ISNAD_PROVIDER=nac_fake ISNAD_PLANNER=greedy ISNAD_DEMO_MODE=false`,
`demo.fake_operator.app:app`, `demo.merchant_pilot.app:app`) via
`.claude/launch.json` and drove them with the Browser tool across three
tabs — not delegated to a background agent. Found and fixed a real issue
along the way: the repo's local `.env` sets `ISNAD_NAC_REDIRECT_URI` to a
Cloudflare tunnel hostname from a prior live-demo setup, which silently
leaked into the harness's authorization URL until explicitly overridden in
the launch script; documented here so the next session isn't surprised by
the same thing. Also needed an isolated `ISNAD_REGISTRY_PATH` with no `.sig`
sibling, since the committed `registry.yaml.sig` is signed by the real
developer vault key and a fresh isolated test vault key correctly reports it
as untrusted (working as designed — not a P4a bug).

Confirmed, with `get_page_text`/screenshots, all at desktop and 375 px width:

- **Full ALLOW journey:** merchant pilot → Isnad consent create → fake
  operator "Approve — this is my number" → browser redirected to the generic
  `/consent/complete` page with **no code, state, or error in the URL**
  (checked via `window.location.href`) → merchant pilot poll transitions
  PENDING → COMPLETED and renders "Proceed" with the correct supporting fact.
- **Full CHALLENGE journey:** "Approve — but I'm signed in with a different
  number" → NUMBER_MISMATCH → the presenter correctly renders "Additional
  verification needed" with the mismatch as an **adverse** fact and the
  fake's other unimplemented actions correctly listed as **unresolved**
  (distinct categories, matching P2's presenter design) — not conflated into
  one generic failure.
- **Denial:** "Deny" → harness shows `Status: DENIED` cleanly, polling stops,
  no crash, no leaked error text.
- No JS console errors other than the one 500 above (now fixed and covered by
  a regression test).

## Test and lint evidence

Full suite: **541 → 596 passed** (`.venv311/bin/python -m pytest -q`). Ruff
(`app tests scripts demo`): clean. `scripts/handset_validation.py contract`
re-run after every provider-contract change and still passes (its
`ContractProvider` test double was updated for the new `nonce` parameter,
same as the two other pre-existing test doubles in `tests/test_consent.py`
and `tests/test_s9_consent_replay.py`). `scripts/verify_runtime_lock.py`
passes; `pip-audit` against the regenerated lock shows only the pre-existing,
already-documented `pip` advisories (pip itself is not part of the lock).
Saved a signed receipt under the pre-P4a code, confirmed it still verifies
after all P4a changes — expected, since none of this touches
`Verdict`/`EvidenceLink` shape or the signing path.

## Known gaps, stated plainly

1. **No migration was added** — correct for this package (consent state is
   in-memory; migrations start at P3), noted here so nobody looks for one.
2. **The manual (non-SDK) NacProvider exchange path is what's fully
   validated end-to-end** against a real id_token; the vendor SDK's own
   `number_verification` object, where present, still owns its result
   untouched, matching H2's existing framing that this is a separately, less
   verifiable path. This was a deliberate scope decision (see
   `app/providers/nac.py`'s inline comment), not an oversight.
3. **PKCE was not implemented** — the official V1 documentation fetched for
   this session does not mention it. If a later contract review finds it
   required, that is a new, dated finding to add here, not evidence this
   session missed something already documented.
4. **The merchant pilot harness is a reference implementation, not a
   template for production onboarding** — one hardcoded operator account,
   in-memory everything, no real request-context input for `claimed_location`
   (P1's open question, explicitly carried forward to P4a in the prior
   session's record, remains open: this harness does not collect a location
   claim from the operator, matching option (b) from that record — out of
   scope for this pilot until a merchant integration contract defines how a
   claim is captured).
5. **Keyboard-Tab traversal was not independently exercised** on the new
   harness pages, for the same tooling-limitation reason recorded in P2's
   implementation record. Every interactive element is a native
   `<button>`/`<a>`/`<input>`/`<select>` with no `tabindex` override, so
   keyboard operability rests on standard HTML semantics, not on anything
   confirmed by a real keystroke in this pass.

## Files changed

`app/consent.py`, `app/api/routes_consent.py`, `app/config.py`,
`app/providers/nac.py`, `app/providers/__init__.py`, `app/main.py`,
`app/oidc.py` (new), `app/providers/oidc_flow.py` (new),
`app/providers/fake_nac.py` (new), `app/static/consent_complete.html` (new),
`demo/fake_operator/__init__.py` (new), `demo/fake_operator/app.py` (new),
`demo/merchant_pilot/__init__.py` (new), `demo/merchant_pilot/app.py` (new),
`demo/merchant_pilot/static/index.html` (new),
`demo/merchant_pilot/static/flow.html` (new), `requirements.txt`,
`requirements.lock.txt`, `requirements-dev.txt`, `pyproject.toml`,
`tests/test_consent_contract.py` (new), `tests/test_oidc.py` (new),
`tests/test_oidc_flow.py` (new), `tests/test_fake_operator.py` (new),
`tests/test_merchant_pilot.py` (new), `tests/test_consent_html_redirect.py`
(new), `tests/test_consent.py`, `tests/test_s9_consent_replay.py`,
`tests/test_nac_provider.py`, `scripts/handset_validation.py`, this file
(new), `docs/PHASE2_HANDOFF.md`, and the Graphify outputs.
