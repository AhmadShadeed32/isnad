# Isnad release review — 9 September 2026

Reviewed the agent's uncommitted implementation before the requested private
GitHub push and Hugging Face deployment. This release includes the paired judge
selector, shared verification service, contract mock, scoped access, signed
provenance, trace recovery, merchant follow-up, tests, and documented rehearsals.

## Defects fixed during review

- Two concurrent real runs from one judge session settled a shared reservation,
  counting four outbound requests as two. Reservations now belong to individual
  runs; refunds remove only that run's entries and settlement is idempotent.
  A synchronized HTTP regression reproduced the original failure before the fix.
- SDK work arriving after a run finished could otherwise use a refunded slot.
  The transport ledger now closes admission before signing and settlement;
  already admitted attempts stay counted.
- Forged authorization headers could change the rate-limit bucket on judge
  endpoints. Valid judge sessions now determine their bucket, and session minting
  has an independent IP limit. Both bypasses have regression tests.
- README retained a second, obsolete future-tense description below the
  implemented feature. Removed the contradictory text.

## Validation

| Check | Result |
| --- | --- |
| Non-browser suite after fixes | **1,442 passed**, five existing deprecation warnings |
| Full browser suite | **135 passed** |
| Judge evidence/production browser paths after final access changes | **24 passed** (subset of the browser suite) |
| Ruff, including deployment scripts | Passed |
| Runtime lock | 38 exact pins cover direct runtime dependencies |
| Dependency audit | No known vulnerabilities found |
| Alembic migrations on a fresh isolated SQLite database | Passed through `0007_verification_operations` |
| Changed-file credential-pattern scan | No matches; private deployment credentials are Git-ignored |
| `git diff --check` | Passed |
| Graphify AST update | Completed without model/API calls |
| Local Docker build | Unavailable: Docker Desktop could not start. Hugging Face subsequently built and started the uploaded image successfully. |

## Deployment preparation

Verified targets: private `AhmadShadeed32/isnad-private`, default branch `main`,
and existing Hugging Face Space `AhmadShadeed32/isnad-trust-engine`. The public
GitHub `origin` is outside this push.

The dedicated Space package under `deploy/huggingface/` uses locked dependencies
and restores a stable Ed25519 identity from a Space Secret before startup. Nokia
and Gemini credentials already existed there. Organizer access and subject
binding are also stored as secrets; no secret is in the upload package. The
database and judge sessions remain ephemeral. No hardware/storage upgrade or
visibility change is part of this release.

## Publication and deployed verification

- Private GitHub `main` received code release
  `c32a24ec50ed0f0009d7d2c96c9771cc9d8368f2`. A subsequent documentation commit
  records these deployment results; runtime source remains that code revision.
- Hugging Face upload `1c866dbfecc6a5755d9c5115895bded78d8a6ed5` was confirmed
  **RUNNING**, with the runtime reporting that exact SHA and the app domain READY.
- Anonymous `/readyz`, `/judge` and `/v1/judge/capabilities` requests returned
  HTTP 200. Mock is default; real evidence requires the organizer-code exchange.
- Chromium completed one mock case and both real Nokia simulator cases from
  the deployed `/judge` page. The code exchange succeeded and cleared its input.
- Both real cases returned two Nokia HTTP 200 responses: **four real attempts
  total**. The adverse subscriber ended DECLINE / REFUTED; the stable subscriber
  ended CHALLENGE / DEGRADED. Both journals recorded Gemini selections, with the
  adverse case's second check labelled as policy corroboration.
- All three exact signed payloads verified independently with Ed25519, and
  altered copies failed. Each public receipt also verified in browser WebCrypto,
  failed the page's tamper test and verified again after restoring its bytes.
- Replaying each original request returned its original chain, zero new
  transport attempts, and unchanged session and deployment allowance.
- No browser page errors occurred. Mock's two transport records are synthetic,
  not Nokia requests. Real quota declined from 24 to 20 deployment attempts and
  from six to two session attempts across the two real runs.

Sanitized attempt records, journal selections, exact signed payloads and receipt
checks: [deployed smoke observation](nac/observations/2026-09-09-deployed-judge-smoke.json).
The older local Nokia rehearsals remain dated local evidence, not deployed proof.
The observation was made by this project's agent; independent judging and
physical-subscriber verification are not implied.

## Lab recording refresh after deployment

The deployed Lab correctly warned that its saved recordings predated the
reviewed runtime: the bundle still carried the 8 September fingerprint
`sha256:5ac6eaabd33c1ed085ece764f7f776e7fa6195541aadad995fb2d4ac3860b9aa`.
Regenerated it with `scripts/build_lab_artifacts.py` using mock evidence and the
Greedy planner. Its fingerprint now matches the current application:
`sha256:e2772f9f2bb391beb0e4c39e052d906e5eb1cf449b2c278f9eea468d7c081740`.

All five outcomes, evidence traces, comparison and benchmark results were
unchanged; only source identity, timestamps and recording IDs changed. The
regeneration made no model or Nokia calls. A new committed-recording freshness
test reproduced the failure before regeneration and passed afterwards, so
future runtime changes require refreshed artifacts to pass release validation.
The browser playback check also now requires both provenance warnings to be
hidden for the committed bundle.

Validation: **37 focused Lab checks** and **10 Lab browser checks** passed;
Ruff and `git diff --check` passed. The English/Arabic desktop/mobile Lab
screenshots were regenerated. Packaging preserves all fingerprinted sources,
and the artifact itself is excluded from its source fingerprint, so committing
the regenerated bundle does not invalidate it.

## Network-conditions callback correction

The deployed `/console` initially returned `callback_not_configured` when a
reviewer pressed **Start a network condition subscription**. The application
guard was working as designed; the Space was missing its deployment-specific
public callback base. Added the public Space Variable:

```text
ISNAD_NAC_CONGESTION_CALLBACK_BASE_URL=https://ahmadshadeed32-isnad-trust-engine.hf.space/v1/network-conditions/callbacks
```

After restart, Chromium completed the full deployed mock lifecycle: subscribe
HTTP 201, forecast HTTP 200, one-hour history HTTP 200, and delete HTTP 200.
The forecast returned one normalized interval with `mock` provenance, the page
reported no browser errors, and only that test's uniquely identified
subscription was deleted. This exercise made no Nokia or Gemini request. It
proves the hosted mock lifecycle and the callback configuration, not operator
subscription acceptance or callback delivery.

## Remaining submission work

The pitch deck and the video/captions were labelled stale at the time of this
review; both were rebuilt on 10 September 2026 (see `docs/VIDEO_REBUILD.md` and
`submission/README.md`), which is outside the scope of this dated record. A
genuinely independent reviewer has not completed a walkthrough of the deployed
build.
Physical-subscriber consent and production-operator access remain unproven;
the real judge option uses Nokia's hosted simulator.

## Addendum — re-run on 11 September 2026

After the judge-minted merchant API key and the `/api-keys` page shipped
(source `6a8f2e2`, Space revision `ffa73f71`), the same suites were run again
on the same machine and interpreter.

| Check | Result |
| --- | --- |
| Non-browser suite | **1,458 passed**, five existing deprecation warnings |
| Full browser suite, one clean run | **147 passed** in 5:24, regenerating every capture in `docs/ui/release/` including the six new `api-keys-*` files |
| Ruff, including deployment scripts | Passed |
| Deployed check of the new path | Mint, verify, tenancy, signature, replay and 409 as the guide states — [`nac/observations/2026-09-11-deployed-api-key-smoke.json`](nac/observations/2026-09-11-deployed-api-key-smoke.json) |

The 12 browser checks added since 9 September are
`tests/browser/test_api_keys_page.py` (4) and the `api-keys` row of the browser
surface matrix (8). Of the 16 non-browser checks added, 11 are
`tests/test_judge_api_keys.py`; the rest arrived with the 10 September lab
provenance commit. The 9 September figures above are unchanged as the record of
that review.
