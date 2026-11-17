# Learned per-frame rate control on data v1: final results (P2 write-up, 2026-11-16)

Source of every number: results_v1/final/report_test.md (exp_next/final/report.py), results_v1/next/*,
docs/EXPERIMENTS.md. Pre-registration: exp_next/final/PREREG.md and exp_next/*/PREREG*.md.

## 1. Setting

- Data v1: 109 clips (66 train / 16 val / 27 test, split by source group), 1,042 GOPs of 30 frames at 320x180,
  x264 and x265 with P1's frozen settings. Clip-level budgets at 4 levels (q0 24 / 30 / 36 / 42); a GOP's budget
  never comes from its own encode.
- Metric: dPSNR_B - 0.17 dB per 1 % over budget, where dPSNR_B = PSNR - the GOP's constant-QP PSNR at exactly the
  budget (0 = the hindsight constant QP that spends exactly B). Unused budget is not rewarded.
- Baseline: final4, the causal online controller (rate model with previous-GOP history), frozen 11-11.
- Lookahead k = number of future frames whose first-pass cost is visible.

## 2. Protocol

- Every experiment pre-registered its pass/fail rule before results; post-hoc changes labelled as such.
- Selection on a train-select fold (8 train clips), confirmation on val, test used once (11-16) for the frozen
  configuration. Paired comparisons on identical (GOP, level, k); 95 % bootstrap over clips; level-24 "hole"
  episodes (budget above the QP-18 curve point) excluded from primaries.
- Every method rescored with one metric function on the same curves and budgets; stored scores re-derived exactly.

## 3. Main result (test)

R3 = PPO residual on final4: per frame, QP = round(final4's real-valued QP + mean[t]) + offset (-6..+6), bit-budget
re-cap; mean[t] = a fixed per-position shift distilled from the hindsight search; the actor is initialised from a
behaviour-cloning classifier on search plans (labels centred on final4; own history and the level flag removed),
then PPO at the metric's price (lambda 0.17), 180k steps, 20k critic-only warm-up. k5, fresh seeds 3-5.

| k5, test, hole excluded | x264 | x265 |
|---|---|---|
| **R3 - final4 (primary)** | **+0.066 [+0.022, +0.106]** | **+0.162 [+0.085, +0.243]** |
| per seed | +0.064 / +0.028 / +0.107 | +0.156 / +0.160 / +0.170 |
| R3 - (final4 + per-frame shift) | -- | +0.074 [+0.041, +0.105] |
| R3 - CQL->PPO 540k | +0.129 * | +0.199 * |
| R3 - encoder ABR+VBV (margin 0.90 / 0.93) | +1.047 * | +0.711 * |
| R3 360k - R3 180k | +0.028 (n.s.) | -0.022 (n.s.) |

Decomposition (test, k5): quality for the bits A = R3 +0.130 vs final4 +0.067 (x264), +0.120 vs -0.030 (x265);
episodes over budget 24 % / 21 % vs final4 55 % / 55 %; signed spend error -1.5 % (R3 lands slightly under, which
costs less than going over). By class: stable GOPs +0.069 * / +0.179 *, cut/gradual +0.056 / +0.098 (n.s.).
By level the x265 gain grows with budget tightness (L42 +0.40).

Attribution (val, k5): the BC start is the active ingredient (R3 - same setup from the standard init +0.131 *);
the setup changes alone cost -0.066 * on x264 and are neutral on x265. BC alone, without RL, loses to final4
(-0.33 / -0.19 *) through closed-loop drift.

## 4. What did not work (val unless stated)

| Experiment | Result |
|---|---|
| Exp 2 handoff (learner first, final4 for the last m frames) | non-inferiority failed (-0.05, spend error 4.2 % vs 2.6 %) |
| Exp 4 R2 (offsets -6..+6 + final4-state features) | ties final4 (+0.003) |
| Exp 5a fixed shift, per budget level | needs budget-level hindsight; causal version helps x265 at k5 only (+0.153 * val) |
| Exp 6 per-context choice of final4's setting | +0.027 [-0.000, +0.050], below the +0.03 bar |
| Exp 10 encoder ABR+VBV with a tuned margin | still about 1 dB below final4 |
| o[2] level flag in learner inputs | at evaluation <= 0.02 dB effect; training effect untested |

## 5. Stream level (Exp 7; reproduction / extension of Pavneet's D34/D35 and Sara's P4)

- Pavneet's 24 stream policies and rule reproduce exactly. Retuning the rule past its grid edge (qpd, prior weight)
  gains +0.13 / +0.16 dB on val.
- Test, pre-registered primary (selected RL policy - retuned rule, same-clip 8-GOP streams): x264 -0.026
  [-0.089, +0.036], x265 +0.050 [-0.008, +0.141] -> **not met: the claim is "lookahead helps", not "RL helps"**.
  RL wins on spliced streams (+0.51 / +0.47 *) and on x265 film streams of 16 / 32 GOPs (+0.10 *).
- Hierarchy (x264, descriptive): final4 inside each GOP at the stream controller's per-GOP budget adds +0.35 to
  +0.71 dB over constant-QP GOPs; retuned rule + final4 is best (+0.36, lands on budget); RL + final4 is 0.39 dB
  below it *. Per-GOP |spend - B_g| mean 2.6-3.0 % (median 0.5 %), above the 2 % target.

## 6. Caveats

- PSNR-cap correction (11-16, from Ahhana): one convention everywhere, each plane's per-frame PSNR capped at 100 dB (curves recomputed from rd_frames; final4 re-measured by re-encoding its stored QPs, bits identical; exp_next/final/cap_fix.py, report.py --psnr-cap -> results_v1/final/report_{val,test}_cap.md). Affected scored GOPs: MusicVideo_360P-5f07 @30/@180 (val), MusicVideo_360P-5699 @0 (test). Test R3 - final4: x264 +0.066 -> +0.067 [+0.023, +0.107], x265 +0.162 -> +0.163 [+0.086, +0.243]; x265 vs final4 + shift unchanged +0.074; cut/gradual +0.056 -> +0.060 / +0.098 -> +0.102. Val: x264 +0.068 -> +0.077, cut/gradual +0.016 -> +0.069 (= Ahhana's), x265 +0.204 -> +0.209. Exp 7 unchanged. Numbers above are before the correction; the corrected ones differ by at most +0.001 dB on test.

- final4's test rows (run 11-11) and the 540k learner's test rows existed before the test pass; Pavneet's stream
  results had already been measured on test; Elephants Dream and Tears of Steel are v1 test clips.
- R3 was tested only at k5; the k-curve in the report comes from final4, ABR and the 540k learner.
- x264's ABR margin (0.90) is on its grid edge.
- final4 was tuned on val; its val numbers favour it slightly.
- 320x180, 30-frame GOPs, one encoder setting per codec.

## 7. Conclusion

At the frame level inside a GOP, the recipe "strong controller + imitation of the hindsight search + RL
correction" is the first learned method to beat the tuned controller on held-out test clips on both encoders
(+0.07 / +0.16 dB), mostly by spending bits more wisely and overshooting less. At the stream level without a
network, a properly tuned lookahead rule matches RL on real (same-clip) streams; RL's advantage there comes from
spliced or long streams. Pavneet's live-stream work (network + buffer) is where RL gains are largest and is
reported separately (different metric and setting).
