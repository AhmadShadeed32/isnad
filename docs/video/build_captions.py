import json, os
BASE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{BASE}/out", exist_ok=True)
T = json.load(open(f"{BASE}/timings.json"))
DISPLAY = {
 "s1a": "Her SIM stopped working on Tuesday. She replaced it. By Friday, that routine change blocked her checkout.",
 "s1b": "The network saw a recent SIM change. The handset was unchanged and still at the claimed location. The merchant saw a first-time customer paying on delivery.",
 "s1c": "Every fact was true. Treating the SIM change as a verdict was the mistake.",
 "s2a": "The signal that catches an account takeover is also produced by a legitimate SIM replacement.",
 "s2b": "And when a check simply can't be run — consent withheld, an operator that hasn't switched the API on — most systems count that against you too.",
 "s2c": "“We couldn't check” and “the check failed” are not the same fact. Isnad is built on that distinction.",
 "s3a": "We measured the policy on ten synthetic customer cases, each with one adverse or unavailable reading.",
 "s3b": "A single-signal rule declines five. A rule that counts missing evidence as adverse declines all ten.",
 "s3c": "Isnad declines none, buying 58 checks instead of 119. The script is in the repo.",
 "s4a": "Here's the product. A cross-border checkout. Cash on delivery, new customer, no history.",
 "s4b": "Instead of automatically adding friction, the agent decides what evidence this actually needs.",
 "s5a": "It forms a hypothesis, buys the cheapest check that could settle it, and stops the moment the answer is decided.",
 "s5b": "Number verification: the network number matches. SIM swap: no SIM swap in the last 240 hours.",
 "s5c": "That's enough, so it stops. Two checks, three units of budget, allowed — and every row shows what it asked, why it asked, and what came back.",
 "s6a": "Now the checkout this is built for. The customer replaced her SIM after losing her phone.",
 "s6b": "The SIM signal is adverse, but policy keeps investigating. The handset is stable, the device is at the claimed location, and every row is labelled as simulated evidence.",
 "s6c": "Six evidence links end in a challenge, not an automatic decline. The risk value is a policy score, not a calibrated fraud probability.",
 "s7a": "Every verdict is signed. Anyone with the link can check that this Isnad instance issued the unchanged payload.",
 "s7b": "Change one byte and verification fails. The receipt proves issuance and integrity, not that a provider response is true.",
 "s8a": "At the shipped threshold, one of seven synthetic two-signal cases is allowed because the agent stops before seeing the second signal.",
 "s8b": "Tighten one policy threshold and that becomes zero of seven, while checks bought rise from 58 to 82.",
 "s9a": "The network APIs are the evidence rails. Isnad is the policy-controlled decision layer that runs on top.",
 "s9b": "We need an operator sandbox and a merchant willing to replay declined orders. That is how synthetic policy tests become measured outcomes.",
}
caps = [{"id": l["id"], "start": l["start"], "dur": l["dur"], "text": DISPLAY[l["id"]]} for l in T["lines"]]
open(f"{BASE}/captions.js", "w").write("window.CAPTIONS=" + json.dumps(caps, ensure_ascii=False) + ";\n")

def srt_ts(s):
    h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")
with open(f"{BASE}/out/isnad-pitch.srt", "w") as f:
    for i, c in enumerate(caps, 1):
        f.write(f"{i}\n{srt_ts(c['start'])} --> {srt_ts(c['start']+c['dur']+0.3)}\n{c['text']}\n\n")
print("captions:", len(caps), "last ends", round(caps[-1]['start']+caps[-1]['dur'], 2))
