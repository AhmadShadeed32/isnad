# Demo video — the rebuild, and the record of what it replaced

**Status on 11 September 2026: rebuilt again, and shipped.**
`submission/isnad-demo.mp4` is now a 2:55 capture of the 11 September build,
and `submission/isnad-demo.srt` is its caption track, generated from the
recorded audio. This cut adds one fourteen-second section, the new `/api-keys`
page, to the 10 September cut, whose sources and voice it reuses unchanged; the
10 September files are kept under `docs/_internal/superseded/` and are not
published. What was produced, and what is synthetic in it, is in *The rebuild,
as executed* below.

The section after that — *What was wrong with the cut this replaced* — is kept as the
dated record of why the old file could not simply be relabelled. Editing a
script does not change an exported MP4, and relabelling an old export as current
would be exactly the kind of claim this project spends its whole architecture
refusing to make.

## The rebuild, as executed

| | |
| --- | --- |
| Duration | **2:55** (175.4 s), inside the organizer's 3:00 limit. The 10 September cut was 2:46; the API-keys section added 14 s and three cues elsewhere were shortened by a few words to keep the margin |
| Format | 1920×1080, H.264 + AAC, faststart, CRF 16. Native resolution: the page is captured at a 1920 CSS-pixel viewport and encoded without a scale filter, because every resample between the browser and the file costs text sharpness. Playwright's screencast captures at the viewport's CSS size and *pads* rather than scales, so `device_scale_factor` and `record_video_size` cannot buy detail — only a larger viewport can |
| Picture | **Real screen capture** of the application driven by Playwright — `/judge`, the signed receipt, `/api-keys`, `/lab`, then `/judge` again. Mock provider, greedy planner, its own database and signing key, so nothing was sent to an operator. On `/api-keys` the organizer code is typed into a password field and never appears; the `mk_…` key that does appear was minted by that throwaway instance, which no longer exists, and authorizes nothing |
| Speed | **Natural. No time compression**, so the on-screen statement that section 4 of this document called for is a statement that none was applied |
| Narration | **Synthesised speech** — Kokoro-82M, voice `am_michael`, the neural TTS and the voice this repository's own pipeline (`docs/_internal/video/README.md`) records the earlier cut as using. No human voice was recorded, and a bar burned into every frame says so. Loudness normalised to −16 LUFS / −1.5 dBTP, the same target that pipeline used |
| Captions | Generated from the *measured* duration of each synthesised cue, never hand-timed, so the burned-in text and the `.srt` cannot drift from the audio |
| Script | The revised narration below, verbatim, minus its stage directions — with one deviation, recorded in the next paragraph |

**The one deviation from the script below.** The *0:15–0:45* section describes
the `llm` and `policy` row labels. Those appear under the Gemini planner; this
capture uses the deterministic greedy planner so that the walkthrough's numbers
reproduce, and every row therefore reads `greedy`. That paragraph was rewritten
to say what is on screen, and to describe the Gemini labels as what the same
column reads in that mode rather than implying the viewer is watching it. The
rest is the script as written.

**What a reader should still do:** watch it once with sound on. Every check in
this repository is mechanical — duration, audio level, frame contents, caption
timing — and none of them is a person confirming that the voice and the picture
tell the same story.

## What was wrong with the cut this replaced

| Problem | Evidence |
| --- | --- |
| The product was not visible until **1:16** | That cut's caption 10, "Here is the checkout", started at `00:01:16,073`; captions 1–9 were title slides, and a frame extracted at 0:18 was still a bulleted slide. |
| It carried claims that had since been removed | Its captions 2–6 stated "cash on delivery is most of e-commerce", "most people who replace a SIM lost a phone", "Generative A.I. has broken every soft proof", "the one thing a model cannot fake…", and "CAMARA is the first time that truth has been programmable". None has a dated primary source in this repository; all were removed from README, the submission docs and the deck on 8 September 2026. |
| Its provenance was never established | The build pipeline in `docs/_internal/video/` produces `isnad-pitch.mp4` at **179.7 s** with a **different** caption track. The cut that shipped was **219.2 s** (3:39) with 146 caption lines against that pipeline's 91. The two are different artifacts, and **the sources that produced the submitted cut are not in this repository.** |

That last row mattered most, and it is why the old file was replaced rather than re-exported: nothing in this repository could reproduce it. Both old files are gone from `submission/` as of 10 September 2026; the measurements above were taken while they were still there.

On the animation pipeline: `docs/_internal/video/README.md` describes a
scene-animation pitch cut whose own README says the receipt animation "is
explicitly an illustration, not a cryptographic check". Rebuilding *that*
pipeline would not regenerate the submitted demo, and shipping it as the demo
would present an animation as a verification. It was not run.

## The blocker, as it stood — and how each part was resolved

Kept as the record of what actually held this up. Re-exporting required all of:

1. **Narration audio.** The pipeline in `docs/_internal/video/` uses Kokoro
   ONNX TTS and needs `kokoro-onnx`, `soundfile`, `espeak-ng`, plus a ~300 MB
   model and voice pack downloaded from GitHub releases. None is installed
   here, and installing them would still produce the wrong artifact (see
   above).
2. **Screen capture of the running application.** The submitted cut shows the
   real `/judge` page being driven. There is no capture pipeline in the
   repository for it, and no record of how the existing footage was recorded.
3. **The organizer's current duration limit.** *Not confirmed.* It must not be
   inferred from the existing 3:39 file. This is an external input.
4. **A decision on time compression.** If the app is sped up, the cut must say
   so on screen. The existing file makes no such statement, and whether it is
   compressed is not documented.

`ffmpeg` and `ffprobe` **are** available here (used for the measurements
above), so encoding is not the blocker. Narration, capture, the duration limit
and the missing provenance are.

## Revised narration, timed

Ordered so the real checkout is on screen within 20 seconds, per the finishing
guide. Timings are targets for the recording, not measurements.

### 0:00–0:15 — the customer, and the cost of both mistakes

> **[On screen: the `/judge` checkout, before any click.]**
>
> This is a cash-on-delivery checkout. The customer replaced her SIM this week.
>
> A fake order costs a merchant a real delivery run. Automatically declining a
> legitimate customer loses the sale. A SIM change on its own does not tell
> those two apart — a takeover and a replaced lost phone produce the same
> signal.

*(The product is visible from the first frame. No title card precedes it.)*

### 0:15–0:45 — the investigation, and who decides what

> **[Click "Investigate the SIM change". Let the trace fill in at natural speed.]**
>
> The agent picks each check itself, and shows you why. Number verification
> first: cheapest useful check, and the network number matches.
>
> Then SIM swap. It comes back adverse — and it stays in the chain. The
> operator's change date is a separate row, because it is a second billable
> call.
>
> Device swap: the handset is unchanged. Location: she is where she said she
> is.
>
> Watch the label on each row. **`llm`** means the model chose that check.
> **`policy`** means policy required it, and the model cannot waive it. The
> model decides what to buy. Policy decides what the answer means.

### 0:45–1:05 — the result and the merchant's next action

> **[The result panel.]**
>
> CHALLENGE. Not a decline. The adverse fact is still there, and three checks
> corroborate her, so the merchant asks for their own step-up instead of
> turning away a customer who lost her phone.
>
> Isnad did not send a one-time code. The merchant runs that, in a channel we
> do not own.
>
> The score is 0.322. That is an uncalibrated policy score, not a measured
> probability of fraud, and the page says so.

### 1:05–1:30 — the signature, and its limit

> **[Open the receipt. Press "Check Ed25519 signature". Then tamper, and check again.]**
>
> This is the signed receipt. The signature is over the exact stored bytes.
>
> Change one character — the signature fails.
>
> What that proves is what Isnad issued, and that it has not been altered
> since. It does **not** prove the operator told us the truth. Every row in
> this run is a simulated operator answer, and each one says so on its own
> badge. A signed mock receipt is still a mock receipt.

### 2:05–2:19 — the API, as a merchant would call it *(added 11 September)*

> **[Open `/api-keys`. Type the organizer code, press "Generate key". The key
> appears once, with three filled-in `curl` commands under it.]**
>
> A judge can call the API directly: the organizer's code mints a merchant
> key, shown once. The same request from a terminal returns the same signed
> verdict — from the mock, never from Nokia.

### Optional tail, if the duration limit allows

> The same engine against a run-everything pipeline on a thirteen-case authored
> set: forty-nine provider operations against seventy-eight. That is a count of
> calls, not money — the cost figures are the policy's own budget units, not an
> operator's prices.
>
> Eight CAMARA APIs are integrated on Nokia Network as Code, and the recorded
> calls to Nokia's hosted simulator are in the repository with their failures
> intact.
>
> What we have not proven, we name: no physical handset has completed an
> operator consent round trip, and no merchant outcomes have been measured.

## Claims this script deliberately does not make

- No market-share statistic.
- No "most SIM replacements are…" claim.
- No "generative AI has broken every soft proof".
- No "impossible to fake" and no "first programmable network evidence".
- No financial saving. The operation count is described as a count.
- No claim that a specific Gemini run will reproduce specific numbers.

## Caption file

Captions were generated from the audio that was actually produced, cue by cue,
rather than hand-timed from the target timings above. Each cue is synthesised as
its own file, measured with `ffprobe`, and its start and end come from that
measurement — so the burned-in captions, the `.srt` and the voice cannot drift
apart. `docs/_internal/video/build_captions.py` was **not** used; it belongs to
the scene-animation pipeline described above, which produces a different
artifact.

The captions are burned in by the page itself rather than by `ffmpeg`. The
`ffmpeg` on the build machine carries no `libass`, `freetype` or `drawtext`
filter, so no text can be composited after the fact; the capture harness renders
the caption bar and the disclosure into the live page instead, which has the
useful side effect that the caption a frame shows is the one that was on screen
at that instant. `submission/isnad-demo.srt` is the sidecar for players that
prefer their own rendering, and it carries the same text and the same timings.

## How the four blockers were resolved

1. **Duration limit — confirmed.** The organizer's submission requirements state
   a maximum of 3 minutes. The cut is 2:55.
2. **Screen capture — solved with what was already here.** Playwright drives
   every surface in `tests/browser/`, and the capture harness reuses that same
   isolated-server pattern: mock provider, greedy planner, its own database and
   signing key. The footage is the real application.
3. **Narration — synthesised, and disclosed.** Kokoro-82M with the
   `am_michael` voice, which is what this repository's own pipeline specifies:
   `kokoro-onnx` installs from PyPI, `espeak-ng` was already present, and the
   model and voice pack were fetched from the release URLs that pipeline's
   README names. A first pass used macOS `say` and was replaced because it did
   not sound human. No human voice was recorded, and a bar burned into every
   frame says so.
4. **Time compression — none applied.** The driver waits on wall-clock time to
   each measured cue start before moving the camera, so the picture is paced to
   the voice without touching the application's own speed.

## What is still owed

**Nobody has watched it with sound on.** Duration, audio level, frame contents
and caption timing were all checked mechanically. A person confirming that the
voice and the picture tell the same story is the one step that was not done, and
it should be done before the deadline.
