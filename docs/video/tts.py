"""Narration -> audio/<id>.wav + timings.json, using Kokoro (ONNX)."""
import json, os, sys, wave
import numpy as np, soundfile as sf
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from narration import LINES
from kokoro_onnx import Kokoro

MODEL = os.environ.get("KOKORO_MODEL", "/tmp/kokoro-v1.0.onnx")
VOICES = os.environ.get("KOKORO_VOICES", "/tmp/voices-v1.0.bin")
VOICE = os.environ.get("KOKORO_VOICE", "am_michael")
SPEED = float(os.environ.get("KOKORO_SPEED", "1.08"))
PAUSE = float(os.environ.get("PAUSE_SCALE", "0.80"))
LANG = "en-gb" if VOICE[0] == "b" else "en-us"

k = Kokoro(MODEL, VOICES)
os.makedirs(f"{BASE}/audio", exist_ok=True)
out, t = [], 1.2  # lead-in silence
for lid, text, pause in LINES:
    s, sr = k.create(text, voice=VOICE, speed=SPEED, lang=LANG)
    # trim the near-silent head/tail Kokoro leaves on each utterance
    amp = np.abs(s); thr = max(amp.max() * 0.02, 1e-4)
    idx = np.where(amp > thr)[0]
    if len(idx):
        s = s[max(0, idx[0] - int(0.04 * sr)): min(len(s), idx[-1] + int(0.10 * sr))]
    sf.write(f"{BASE}/audio/{lid}.wav", s, sr)
    dur = len(s) / sr
    out.append({"id": lid, "text": text, "start": round(t, 3),
                "dur": round(dur, 3), "pause": round(pause * PAUSE, 3)})
    t += dur + pause * PAUSE

json.dump({"voice": VOICE, "speed": SPEED, "pause_scale": PAUSE, "rate": sr, "total": round(t, 3), "lines": out},
          open(f"{BASE}/timings.json", "w"), indent=1)
print("voice", VOICE, "· total", round(t, 2), "s")
for o in out:
    print(f"{o['id']:5s} {o['start']:7.2f} +{o['dur']:5.2f}")
