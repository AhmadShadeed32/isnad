# Narration lines. Every claim is checked against the cited evidence.
# (id, text, tail_pause_seconds)
LINES = [
 ("s1a", "Her SIM stopped working on Tuesday. She replaced it. By Friday, that routine change blocked her checkout.", 0.7),
 ("s1b", "The network saw a recent SIM change. The handset was unchanged and still at the claimed location. The merchant saw a first-time customer paying on delivery.", 0.5),
 ("s1c", "Every fact was true. Treating the SIM change as a verdict was the mistake.", 0.9),

 ("s2a", "The signal that catches an account takeover is also produced by a legitimate SIM replacement.", 0.6),
 ("s2b", "And when a check simply cannot be run, consent withheld, an operator that has not switched the A P I on, a rule that treats missing evidence as adverse counts that against you too.", 0.5),
 ("s2c", "We could not check, and the check failed, are not the same fact. Isnad is built on that distinction.", 0.9),

 ("s3a", "We measured the policy on ten synthetic customer cases, each with one adverse or unavailable reading.", 0.5),
 ("s3b", "A single-signal rule declines five. A rule that counts missing evidence as adverse declines all ten.", 0.5),
 ("s3c", "Isnad declines none. Across the full seventeen-case set, it buys fifty-eight checks instead of one hundred and nineteen. The script is in the repo.", 0.9),

 ("s4a", "Here is the product. A cross-border checkout. Cash on delivery, new customer, no history.", 0.4),
 ("s4b", "Instead of automatically adding friction, the agent decides what evidence this actually needs.", 0.6),

 ("s5a", "It forms a hypothesis, buys the cheapest check that could settle it, and stops the moment the answer is decided.", 0.9),
 ("s5b", "Number verification: the network number matches. SIM swap: no SIM swap in the last two hundred and forty hours.", 0.8),
 ("s5c", "That is enough, so it stops. Two checks, three units of budget, allowed. And every row shows what it asked, why it asked, and what came back.", 0.9),

 ("s6a", "Now the checkout this is built for. The customer replaced her SIM after it stopped working.", 0.7),
 ("s6b", "The SIM signal is adverse, but policy keeps investigating. The handset is stable, the device is at the claimed location, and every row is labelled as simulated evidence.", 0.7),
 ("s6c", "Six evidence links end in a challenge, not an automatic decline. The displayed risk value is a policy score, not a calibrated fraud probability.", 0.9),

 ("s7a", "Every verdict is signed. Anyone with the link can check that this Isnad instance issued the unchanged payload.", 0.6),
 ("s7b", "Change one byte and verification fails. The receipt proves issuance and integrity, not that a provider response is true.", 0.9),

 ("s8a", "Here is the tradeoff. At the shipped threshold, one of seven synthetic two-signal cases is allowed because the agent stops before seeing the second signal.", 0.5),
 ("s8b", "Tighten one policy threshold and that becomes zero of seven, while checks bought rise from fifty-eight to eighty-two.", 0.9),

 ("s9a", "The network APIs are the evidence rails. Isnad is the policy-controlled decision layer that runs on top.", 0.5),
 ("s9b", "We need an operator sandbox and a merchant willing to replay declined orders. That is how synthetic policy tests become measured outcomes.", 1.4),
]
