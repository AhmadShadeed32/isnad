import json, os, wave, array
BASE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{BASE}/out", exist_ok=True)
T = json.load(open(f"{BASE}/timings.json"))
RATE = T.get("rate", 24000)
TOTAL = T["total"] + 4.0
buf = array.array("h", [0]) * int(RATE * TOTAL)
for l in T["lines"]:
    with wave.open(f"{BASE}/audio/{l['id']}.wav") as w:
        assert w.getframerate() == RATE and w.getnchannels() == 1, (w.getframerate(), RATE)
        a = array.array("h"); a.frombytes(w.readframes(w.getnframes()))
    off = int(l["start"] * RATE)
    for i, v in enumerate(a):
        j = off + i
        if j < len(buf):
            buf[j] = max(-32768, min(32767, buf[j] + v))
with wave.open(f"{BASE}/out/narration.wav", "wb") as o:
    o.setnchannels(1); o.setsampwidth(2); o.setframerate(RATE)
    o.writeframes(buf.tobytes())
print("narration.wav", round(len(buf)/RATE, 2), "s")
