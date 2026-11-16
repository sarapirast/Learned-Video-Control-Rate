# Live-stream RL finding, in plain terms (D39)

**The setup.** We simulate a live video stream, like a Twitch or video call. Each second the encoder chooses a quality level, which decides how many bits that second of video costs. The bits go out over a network whose speed keeps changing, like a phone moving between good and bad signal. There's a small waiting buffer at the sender. If we send more than the network can carry, the buffer overflows and the viewer's video freezes (a stall).

So every second the controller faces a trade-off:
- **Higher quality** gives a better picture, but risks freezing if the network slows down.
- **Lower quality** is safe, but the picture looks worse than it needed to.

We score each method on overall picture quality, with a penalty for every freeze.

**What we compared.**
1. **A hand-made rule (`vbv2`).** It looks at how full the buffer is and how fast the network has been, then picks the quality. We tuned its settings carefully on validation data. It's the strongest rule we could build, and similar in spirit to how x264/x265 handle this.
2. **RL (`ppo_v2`).** It starts from that same rule's decision each second and learns when to go a bit higher or lower.

**The finding.** RL beats the best hand-tuned rule by about 0.35–0.45 dB of picture quality, after counting the freeze penalty. It does this in two ways at once:
- It pushes quality up when it's safe, so it uses the network more fully.
- It backs off earlier when trouble is coming, so it freezes less often (about 0.6% of the time vs 1.0%).

**Why we trust it.** The win held up when we changed things:
- calmer or rougher networks;
- tighter or looser latency limits;
- freezes counted as more or less bad;
- **real 4G phone network recordings** instead of simulated ones;
- new videos the model never saw in training.

It won in every case, on both encoders, with error bars that stay above zero.

**The honest part.** Our first live-stream result (D38) looked like a +0.5 dB win, but it was against a weak rule. Once we built a stronger rule, that old RL policy no longer beat it on short streams. The fix was to have RL build on the strong rule instead of replacing it. This version is the result that holds up.

## Checked with real encoders (D40)

**What we did.** We put the real x264 and x265 encoders in the loop. They actually encode and decode the video each second, while the network is still simulated or replayed from real 4G recordings. We used them in two ways:
1. **Replaying RL's choices with the real encoder.** The quality and bit counts came out exactly as our simulation predicted, so the simulation isn't flattering RL.
2. **Comparing against the encoders' own live mode.** This is the built-in way x264/x265 handle live streaming: aim at a fixed bitrate target with a buffer limit. We tuned that target on validation data. We also gave it an unfair advantage by picking its best target in hindsight on the test data itself.

**Result.** RL's gain over the encoders' live mode, even with the target picked in hindsight:

| Setting | x265 | x264 |
|---|---|---|
| Short streams | +0.4 dB | tie |
| Long streams | +1.4 dB | +1.1 dB |
| Real 4G traces | +2.2 dB | +2.2 dB |

Every gain except the x264 short-stream tie has error bars that stay above zero.

**Why RL wins.** The encoder's live mode needs one fixed bitrate target, and the best target changes a lot by situation. It's about 90% of the network speed on short streams, 70% on long ones and only 30–50% on real 4G. No single setting works everywhere. RL (and our rule) react to the network as it changes, so they don't need that guess.

**Honest notes.**
- On short streams, x264's own live mode ties RL.
- Telling the encoder's live mode to hit RL's chosen bitrate each second does worse than RL choosing the quality directly, because the encoder spends those bits less efficiently over such short windows. Letting RL set that target instead gave little or no gain.

**In one sentence:** on a changing network, RL balances picture quality against freezes better than both a carefully tuned rule (+0.4 dB) and the encoders' built-in live rate control (+1–2 dB on long streams and real 4G traces), confirmed with real x264/x265 encodes.

**The main limit:** the video encoding is now real, but the network is still simulated or replayed from recordings. We haven't streamed over a live network to real viewers.
