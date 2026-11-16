# Quality vs delay (W5 report section, draft 2026-11-11)

Every number below comes from a results file written by a script (sources in brackets):
[N] = `results_v1/w5/w5_numbers.md` (`scripts/w5_numbers.py`), [C] = `results_v1/w3/class_kcurves_<enc>.md`
(`scripts/w4_class_kcurves.py`), [S] = `results_v1/w3/search_gain_<enc>_lfq.md` (`scripts/w3_search_gain.py`),
[L] = `results_v1/lfq_compare_<enc>_final4.md` (`scripts/lfq_compare.py`). Figures: `results_v1/figures/w5_*.{png,pdf}`
(`scripts/w5_figures.py`).

## Setup

- Data v1: 109 clips, 30-frame GOPs (IDR + 29 P), 320x180, x264 and x265 with P1's frozen settings; clip-level
  budgets at 4 levels (no information from the GOP's own encode); flat (grayscale) GOPs excluded.
  Test = 252 GOPs x 4 budgets = 1008 rows (796 stable, 196 cut, 16 gradual).
- Score: quality at the budget, dPSNR_B = PSNR - PSNR of a constant QP that spends exactly the budget, minus
  0.17 dB per 1% over budget. 0 = that constant QP; positive = better.
- Delay = lookahead k in frames (k/30 s at 30 fps): k = 0 (strictly causal), 2, 5, 10, 29 (whole GOP).
- Methods: the hindsight search (Pavneet's hill-climb with ~600 real encodes per GOP x level, the ceiling, not
  deployable); the causal rate controller final3 and final4 (final4 adds the previous GOP's outcome); residual RL on
  the controller (offset -3..+3 per frame); BC and CQL->PPO on the previous-GOP base QP (offset +-10). All learners
  3 seeds, averaged. CIs: 95% bootstrap over the 26 test clips that remain after flat GOPs are excluded [N section 4].

## Figure 1: quality vs delay

`results_v1/figures/w5_quality_vs_delay.png`

Test score by k [N section 1]:

| method | x264 k0 | k2 | k5 | k10 | k29 | x265 k0 | k2 | k5 | k10 | k29 |
|---|---|---|---|---|---|---|---|---|---|---|
| search (ceiling) | +0.30 | | | | | +0.28 | | | | |
| controller + history (final4) | -0.35 | -0.16 | -0.13 | -0.12 | -0.13 | -0.43 | -0.28 | -0.21 | -0.19 | -0.24 |
| controller (final3) | -0.49 | -0.24 | -0.12 | -0.11 | -0.15 | -0.56 | -0.32 | -0.20 | -0.21 | -0.29 |
| residual RL on final4 | -0.55 | -0.21 | -0.19 | -0.24 | -0.29 | -0.56 | -0.40 | -0.34 | -0.40 | -0.27 |
| BC, prev-GOP base | -1.49 | -0.86 | -0.56 | -0.41 | -0.21 | -1.37 | -0.88 | -0.60 | -0.40 | -0.21 |
| CQL->PPO, prev-GOP base | -1.27 | -0.76 | -0.58 | -0.43 | -0.38 | -1.12 | -0.79 | -0.54 | -0.43 | -0.41 |

Findings:

1. **No single-encode method reaches constant-QP quality at the budget.** The best causal-to-lookahead method, the
   rule-based controller with history, stays 0.12-0.16 dB (x264) and 0.19-0.28 dB (x265) below 0 at k >= 2, and
   0.42 dB (x264) / 0.47 dB (x265) below the search at its best k (k10). The search's +0.30 dB needs hindsight and ~600 encodes per GOP.
2. **Lookahead's value is front-loaded.** For final4, k0 -> k2 gains +0.19 dB (x264) / +0.16 (x265); k2 -> k5 adds
   +0.03 / +0.07; beyond k5 nothing (k10 - k5 +0.01, CIs include 0) [N H1]. About 67-167 ms of delay buys all of it.
   Full-GOP lookahead (967 ms) is no better than k5, and slightly worse for final3 and on x265.
3. **History substitutes for delay at small k.** Knowing how the previous GOP went raises the k0 score by +0.14 dB
   [+0.03, +0.24] (x264) and +0.12 [-0.03, +0.30] (x265, n.s.); at k >= 5 final3 and final4 are equal (all |diff| <=
   0.05 dB, CIs include 0) [N section 4].
4. **The learners' k-curves are mostly budget repair.** BC and CQL->PPO gain 0.7-1.3 dB from k0 to k29, far more than
   the controller, because at small k they set the GOP's base QP poorly; they never pass the controller, and the
   residual RL, which starts from the controller, ends below it at every k (-0.05 to -0.20 dB, all CIs below 0 on
   x264; x265 k29 -0.03 n.s.) [N H5].

5a. **Against the encoders' own rate control, every single-pass method here wins clearly.** x264/x265 1-pass ABR
   with VBV sized to the GOP budget and --rc-lookahead k scores -1.52 to -1.65 dB (x264) and -1.16 to -1.25 dB
   (x265) at every k, over budget on 50-86% (x264) / 49-92% (x265) of GOPs. final4 beats it by +1.29 to +1.48 dB
   (x264) and +0.82 to +0.99 dB (x265), the residual RL by +0.70 to +1.43 dB, and BC on the prev-GOP base from k2
   (x264) / k5 (x265) on, all CIs above 0 (rescored from the week-2 encodes, no new encodes)
   [`results_v1/w5/abr_dpsnr.md`, `scripts/abr_dpsnr.py`]. ABR+VBV does not improve with lookahead.

## Figure 2: stable vs cut GOPs

`results_v1/figures/w5_quality_vs_delay_by_class.png`

5. **Where the search gains.** Its gain over its start plan is similar on stable and cut GOPs (x264 +0.44 vs +0.49 dB)
   [S]. Around a single cut it raises QP by 0.5 on the frame before the cut and lowers it by 0.7 on the cut frame;
   48% (x264) / 46% (x265) of its QP change is BEFORE the cut, i.e. needs lookahead [S section 3].
6. **Lookahead matters about twice as much on cut GOPs, for the controller.** final4 k5 - k0: stable +0.18, cut
   +0.38 dB; cut - stable +0.20 [+0.04, +0.39] (x264), +0.19 [-0.01, +0.41] (x265) [N H2]. The residual shows no
   such difference (+0.00 / +0.03, CIs include 0).
7. **On cut GOPs the residual ties the controller; on stable GOPs it loses** (x264 cut k0 +0.04 [-0.09, +0.20],
   stable k0 -0.26 [-0.34, -0.19]) [C section C]. A gate that runs the controller on stable GOPs and the best
   learner around cuts gains at most +0.01 [-0.02, +0.04] dB, even with the class known in hindsight [C section D].
8. **An adaptive-lookahead gate does not save delay for free.** k2 on stable GOPs and k5 on cut GOPs (mean 2.6
   frames) is below fixed k5 by 0.02 dB (x264) / 0.05 dB (x265), CIs below 0, because stable GOPs also gain from
   k2 to k5 [N section 3]. (Hindsight bound from stored runs; a real gate needs new encodes.)

## Where a learner does beat the baseline: lowest rate on x265

9. **At budget level 42 on x265, residual RL on final4 beats final4**: +0.15 [+0.03, +0.30] dB on test and
   +0.16 [+0.02, +0.33] on val, largest at k0 (+0.27 test, +0.22 val) [N section 5]. It is the only learner result
   above the controller with a CI excluding 0 on both splits. x264 shows no such gain (-0.02 test, -0.00 val).
10. **Likely reason: the controller's rate model is wrong near QP 50.** It assumes one slope (bits halve every 5.04
    QP on x265, 5.49 on x264); the constant-QP curves flatten at high QP (5.8 / 6.4 QP per halving at QP 47-50), so
    near the cap raising QP saves fewer bits than planned. At level 42 final4 reaches QP 51 in 38% (x265) / 35%
    (x264) of episodes and those end 4.9% / 6.9% over budget, vs 0.7% / 0.4% otherwise [N section 5]. A residual
    trained on real encodes can learn to correct such a systematic error, which a hand-built rule cannot see; this is
    an explanation consistent with the data, not a tested mechanism, and it does not explain why the x264 residual,
    facing the same saturation, does not gain.

## Baseline choice

The causal controller with previous-GOP history (final4, setting 1.0:6:1.0:2:3:4:1:1:1:0:3) is the frozen
classical baseline (decided 2026-11-11). It is not an industry encoder's rate control: x264/x265 ABR+VBV were run in
week 2 and are far worse under a hard per-GOP budget (tracker W2; `results_v1/baselines_v1_table.md`: -26 to -35 points on the old score, over budget on 47-91% of GOPs). It stands for what a competent
non-learned design reaches: a train-fitted rate model, online calibration, lookahead and the previous GOP's outcome,
tuned on val. It is not tuned further (for example, its high-QP slope is left as is), so that the learned methods are
compared against a fixed, fair reference rather than one improved until they lose.

## Pre-registered hypotheses (docs/w4-hypotheses.md, written 11-09 before the runs)

| # | Prediction (short) | Outcome |
|---|---|---|
| H1 | k-curves steep then flat; all gain by k5 | supported (both encoders, controller and residual) |
| H2 | cut GOPs gain more from lookahead | supported for the controller, falsified for the residual |
| H3 | best k closes <= 20-30% of the gap to the search | falsified: 34-48% (but small in dB: +0.23-0.38) |
| H4 | k29 < k5, loss in cut GOPs | mostly falsified: with history the k29 drop is gone (x264) or small (x265) |
| H5 | residual beats its controller at every k | falsified: below at every k |
| H6 | residual gains from lookahead | supported: +0.29-0.36 dB, more than predicted |
| H7 | x265 gains more from lookahead than x264 | not supported: equal for the controller |
| H8 | residual's deficit largest at level 24 | mostly supported; new: x265 level 42 residual > final4 (findings 9-10) |
| gate | k2/k5 adaptive gate matches fixed k5 | falsified: -0.02 / -0.05 dB |

## Caveats

- 26 test clips; per-class and per-level cells are smaller (196 cut rows; 16 gradual rows, not interpreted).
- History for the learners and the residual is the controller's own GOP n-1 (an approximation; a learner deployed
  clip-sequentially would see its own previous GOP).
- Class (stable / cut) is a hindsight label from the cut detector; the gate bounds use it, a deployed gate could not.
- Lagrangian PPO at lam 0.17 has the same reward as CQL->PPO's default under this metric (differs only by a
  per-episode constant), so it is not a separate method; it is left out of the figures.
- The x265 level-42 residual win was found after the fact (one of 8 level cells); it holds per k at k0/k2/k29 on
  test and is reproduced on val (pooled and k0), which is why it is reported, but it was not a pre-registered test.
