# docs/video — how the rendered pitch cut is built

Source copy was corrected on 5 September 2026. **The old MP4 is obsolete and
has not been regenerated.** Narration audio, captions, timings and frames must
be rebuilt together before exporting a revised cut. ffmpeg is unavailable in
this review environment.

Nothing here talks to the app at runtime. These scenes illustrate synthetic
policy examples; the receipt animation is explicitly an illustration, not a
cryptographic check. Use the live `/judge` page for a verifiable receipt and the
current [recording plan](../VIDEO_SCRIPT.md) for claims and provenance.

## Files

| File | What it is |
|---|---|
| `narration.py` | The narration, line by line, with the pause after each. **Start here.** |
| `tts.py` | Synthesises each line to `audio/<id>.wav` and writes `timings.json`. Voice, speed and pause length are env vars: `KOKORO_VOICE`, `KOKORO_SPEED`, `PAUSE_SCALE` |
| `timings.json` | Start time and duration of every line — the spine everything else keys off |
| `build_captions.py` | `captions.js` (burned-in) and `isnad-pitch.srt` (sidecar) |
| `scene.html` / `scene.css` | The seven scenes, in the product's own design tokens |
| `timeline.js` | `setT(t)` — one function that fully describes any frame. No transitions, no rAF |
| `capture.py` | Steps time frame by frame in headless Chromium; `--probe 68,110,146` writes single frames to `probe/` |
| `mixaudio.py` | Lays the lines onto one 163.5 s track at their `timings.json` offsets |
| `encode.sh` | Frames + audio → `out/isnad-pitch.mp4` and `out/isnad-pitch-silent.mp4` |

## Prerequisites

```bash
pip install kokoro-onnx soundfile playwright && playwright install chromium
apt-get install -y espeak-ng          # Kokoro phonemises through it
curl -L -o /tmp/kokoro-v1.0.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -o /tmp/voices-v1.0.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

54 voices ship in `voices-v1.0.bin`; `am_michael` is what the current cut uses.
`af_heart`, `bm_george` and `bf_emma` are the other three worth auditioning.

Fonts: **Inter** and **JetBrains Mono** must be installed system-wide or the
frames fall back to a default sans and the layout shifts. ffmpeg is required by
`encode.sh`.

## Rebuild

```bash
python3 tts.py && python3 build_captions.py && python3 capture.py
python3 mixaudio.py && ./encode.sh
```

The commands create their generated `audio/`, `frames/`, `out/`, and `probe/`
directories as needed, so the sequence also works from a clean checkout.

Audio was normalised to −16 LUFS / −1.5 dBTP after `mixaudio.py`:

```bash
ffmpeg -i out/narration.wav -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ac 2 out/narration_norm.wav
```

## Beats are anchored to narration lines, not to seconds

Nothing in the render is scheduled at an absolute time. A trace row is
`s6b+2.1` — 2.1 s after the line about the live call begins. The three checkout
cards are `s1b@0.20`, `s1b@0.48`, `s1b@0.72` — fractions of the line that names
them. The DECLINED stamps are `s1c@0.52` and friends. Scene boundaries are
`s3a-0.28`. The grammar is documented at the top of `timeline.js`:

| Spec | Means |
|---|---|
| `s5b` | when line s5b starts |
| `s5b+1.2` | 1.2 s after it starts |
| `s5b-0.3` | 0.3 s before it starts |
| `s5b@0.55` | 55% of the way through it |
| `s5b$0.4` | 0.4 s after it ends (`$-2` = 2 s before it ends) |

So a new voice, a different speed or a reworded line re-times the entire video
off `timings.json` with nothing to re-tune by hand. Probe a couple of frames
anyway before committing to a full render.
