# Isnad pitch — current recording plan

Updated 5 September 2026. Use [JUDGE_WALKTHROUGH.md](JUDGE_WALKTHROUGH.md) for
the current 90-second take. The previous MP4 is an obsolete historical cut;
correcting source text does not regenerate its voiceover, captions or frames.

## Current claims and their evidence

| Claim | Source and limit |
| --- | --- |
| Replaced SIM → CHALLENGE / DEGRADED, score 0.242, six checks | Act VI under mock/greedy; simulated provider facts, not observed fraud outcomes |
| Clean checkout → ALLOW after two checks | Act III under mock/greedy; score 0.096, evidence cost 3 |
| 5/10 and 10/10 baseline declines versus 0/10 for Isnad | `scripts/false_decline_baseline.py`; synthetic policy-derived single-adverse/unavailable cases |
| 119 → 58 calls; one of seven two-adverse cases still allowed | Same harness, whole 17-case population; do not attach this call total only to the ten legitimate cases |
| Tightening 0.15 → 0.05 closes that case at 82 calls | Same harness `--sweep`; no production accuracy claim |
| Fixed 13-case comparison: 28 versus 78 calls, six expectation disagreements | `scripts/independent_evaluation.py`; conservative authored expectations, no observed labels |
| The receipt's bytes verify under its signing key | Browser Ed25519 check; issuance and integrity, not proof of upstream truth |
| Handset consent is prepared, locally tested, not yet proven with an operator | `scripts/handset_validation.py contract`, `HANDSET_VALIDATION.md` |

All SIM and device swap sentences refer to the requested 240-hour window. The
APIs used here return booleans against that window; never narrate an event age,
years of subscriber history, or an unavailable device reputation result.

## Recording

Launch using the explicit mock/greedy command in the README. Open `/judge`,
reload for a fresh demo credential, and rehearse the primary replacement case
once. Record the trace, its simulator badges, CHALLENGE, and the signed receipt.
An optional second clean checkout shows early stopping and session revocation.
The stage actions never make live operator calls.

Record the live application in one take where practical. Avoid opening secret
configuration, OAuth callback address bars or credential prompts on camera.
A phone opening a localhost receipt needs a separately configured HTTPS receipt
host; it is not evidence of an operator consent flow.

## Rendered source status

`docs/video/narration.py`, `scene.html` and `timeline.js` contain corrected
story copy and synthetic figures. They are an animated explanatory rendition,
not footage of a current execution. Use the live judge page for current signed
receipts. Any illustrated key or signature in animation is not independently
verifiable evidence of the updated example.

Rebuilding requires the toolchain documented in `docs/video/README.md`, including
ffmpeg, Kokoro voice/model files and a browser renderer. ffmpeg is unavailable in
this review environment. No replacement MP4, narration audio, caption timing,
or frame set was generated. Do not submit an older binary as this revised take.
