# What showed an RL benefit (D34/D35)

RL showed a real benefit once we changed the task: instead of picking QP frame by frame inside one GOP, RL **splits one bit budget across a stream of GOPs**. Every result below uses Aayush's dB metric (dPSNR_B − 0.17 dB per 1% over), his v1 budgets and his encoder settings. That avoids the three problems he found in the earlier wins.

**1. Stream-level budget allocation (D34)**
- **Setup:** an episode is 8 GOPs under one budget. At each GOP, RL picks a QP offset of −6 to +6 on a causal rate model. Outcomes are read from the real constant-QP curves.
- **Strongest baseline:** a remaining-budget rule whose margin, rate slope and calibration prior I tuned on val (the grid was widened twice until the best setting sat inside it).
- **Result (v1 test, BC→PPO with 2 GOPs of lookahead, vs the tuned rule):** **+0.21 dB** [+0.15, +0.30] on x265 and **+0.14 dB** [+0.09, +0.20] on x264.
  - Every PPO variant had a CI above 0, and all 5 hypotheses written before the results passed.
  - That is about **4–5% bitrate** on x265 and 1.5–3% on x264.
- **Where the gain comes from:** mostly mixed streams, where clips are spliced together. On same-clip streams it is smaller (+0.06 to +0.11 dB with lookahead, about 0 without).

**2. RL vs the encoders' own rate control (D35)**
- **Setup:** the same 724 test cases, each coded as one real 240-frame encode at Aayush's budgets.
- **vs ABR+VBV (Aayush's baseline):** **+0.44 dB** [+0.35, +0.54] on x265 and **+0.17 dB** [+0.09, +0.26] on x264. This holds even though the encoder can change QP every frame and RL only every GOP.
- **vs ABR+cutree:** +2.5 dB on x265 and +0.6 dB on x264.
- **Why RL wins:** the encoders overshoot. They go more than 1% over on 27–56% of streams, against 10–12% for RL.
- **What beats RL:** only two-pass, which sees the whole stream first. It ties on x265 and is 0.27 dB ahead on x264.

**3. Fresh long films, policies applied unchanged (D35)**
- **Setup:** Elephants Dream and Tears of Steel, which were never seen in training.
- **Plain PPO with lookahead vs the tuned rule:**

| Stream length | x265 | x264 |
|---|---|---|
| 8 GOPs | +0.05 dB (not significant) | +0.07 dB |
| 16 GOPs | +0.12 dB | +0.09 dB |
| 32 GOPs | +0.16 dB | +0.15 dB |

All results except the x265 8-GOP one are significant. The gain grows with stream length.

**4. The gain comes from RL itself, not imitation**
- Behaviour cloning of the rule alone always scores below the rule.
- PPO, trained on the reward, is what moves the policies above it.

**Limits to state alongside these results:**
- The main pre-registered test on fresh films (BC→PPO at 8 GOPs) failed on x265.
- The fresh set is only 12 segments from 2 films.
- RL controls one QP per GOP, with no frame-level control inside a GOP.
- RL does not beat Aayush's final3 controller at frame level. The benefit is at the stream budget-allocation level.

**Where the results are:**
- `results/v1_stream/<codec>/stream_report_test.md` (part 1)
- `results/v1_stream/<codec>/own_rc_stream_v1_report.md` (part 2)
- `results/fresh_stream/<codec>/fresh_stream_report.md` (part 3)

---

The fresh-film test asks whether the RL policies still beat the tuned rule on real video they never saw.

## The fresh long-film test

**Why we ran it.** The D34 win on v1 had two weak points:
- It came mostly from "mixed" streams, which are different clips spliced together. Real video doesn't look like that.
- The v1 test streams are short (8 GOPs).

So we needed continuous footage that was never used for training or tuning.

**Data**
- Two open films: *Elephants Dream* and *Tears of Steel*. Neither is in Aayush's v1 dataset.
- From each film we took 6 segments of 32 consecutive GOPs (30 frames each, about 32 s), spread between 2% and 85% of the film. That gives 12 segments.
- We encoded every GOP at every constant QP with the v1 encoder settings, which gives the real bits/PSNR curves.

**Streams and budgets**
- A stream is a window of N consecutive GOPs inside a segment, with N = 8, 16 or 32. Windows overlap by half.
- The budget is built exactly like v1's: the segment's average constant-QP bits at q0 ∈ {24, 30, 36, 42}, times s ∈ {0.85, 1, 1.18}.
- That gives 1008 cases at N=8 and 432 at N=16.

**What was applied**
- The D34 policies and the D34-tuned rule were applied **unchanged**: no retraining and no retuning.
- Everything was trained or tuned on 8-GOP streams, so 16 and 32 GOPs are also a test of whether it holds on longer streams.
- CIs come from a bootstrap over the 12 segments.

**Result, plain PPO with 2 GOPs of lookahead, gain over the rule:**

| Stream length | x265 | x264 |
|---|---|---|
| 8 GOPs | +0.05 dB (CI includes 0) | +0.07 dB |
| 16 GOPs | +0.12 dB | +0.09 dB |
| 32 GOPs | +0.16 dB | +0.15 dB |

- The gain holds on real continuous video and grows on longer streams. A longer stream gives more room to move bits between easy and hard parts.
- The main pre-registered method, BC→PPO, was weaker: +0.03 dB on x265 (not significant) and +0.07 dB on x264 at 8 GOPs.
- Without lookahead, RL is +0.2–0.4 dB ahead at 16/32 GOPs. That is inflated because the rule, tuned at 8 GOPs, degrades on long streams, so we don't claim it.

## What "dB" means here

Yes, it is PSNR in dB, measured at a fixed bit budget with a penalty for overshooting. The score for each stream is:

**score = dPSNR_B − 0.17 × (% over budget)**

- **dPSNR_B** is the stream's PSNR minus the PSNR that constant QP would reach if it spent exactly the budget. The stream's PSNR is pooled over the MSE of all its frames. The constant-QP value is read from the stream's real curve.
- **The 0.17 dB penalty** is charged per 1% of overshoot (Aayush's value). Unused budget isn't rewarded, because it just shows up as lower PSNR.

So "+0.12 dB over the rule" means that at the same budget, RL's video is about 0.12 dB higher PSNR, after charging both methods for any overshoot.

For example, at 8 GOPs on x265:
- Rule: dPSNR_B −0.22, score −0.26.
- PPO: dPSNR_B −0.16, score −0.21.

The PSNR difference is about 0.06 dB, and the overshoot penalty accounts for the rest.

## How to read the size

- **Both methods score below 0.** Neither beats "the constant QP that lands exactly on the budget". That reference is only knowable in hindsight, so it's a high bar for any causal method.
- **The hindsight per-GOP plan** (the best possible with full knowledge) scores +0.08 dB at N=8. So the whole available gap over the rule is about 0.57 dB, and PPO closes about 15% of it.
- **In bitrate terms**, on v1 we measured about 0.2 dB as worth about 4–5% bitrate on x265. By that scale, the fresh-film gains of 0.05–0.16 dB are roughly 1–3% bitrate. That's small but real, and it is consistent across both encoders at 16/32 GOPs.

The report with all methods and lengths is `results/fresh_stream/<codec>/fresh_stream_report.md`.
