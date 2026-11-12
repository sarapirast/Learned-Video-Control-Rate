# Week 4 hypotheses: expected shape of every k-curve (written before the W4 runs)

Written 2026-11-09 18:30 (P2, tracker item 26), BEFORE any result of the residual RL sweep (array 13918676) and
before any W4 curve was split by class. Purpose (docs/p2-plan.md, week 3): commit to the expected shapes now, so
that the W4 curves test them instead of being explained after the fact. Do not edit the predictions below once W4
results exist; add outcomes in the "Outcome" lines only.

Conventions: score = % bits saved at equal PSNR vs the GOP's constant-QP curve, minus 2 per 1% over budget
(docs/EXPERIMENTS.md). "Leak-free" = budgets.csv (4 clip-level levels), P1 settings, flat GOPs excluded. Test split
unless stated. "k-gain" = score(k) - score(0) for the same method. All CIs: 95% bootstrap over clips.

## Evidence these predictions rest on (all measured, W1-W3)

| # | Fact | Source |
|---|---|---|
| E1 | Leak-free search, test: 10.3 (x264) / 10.0 (x265); gain over its ramp start: stable +7.0, cut +10.6, gradual +13.7 (x264). Cut GOPs are 196 of 1008 test rows (19%); gradual 16 (2%) | `results_v1/w3/search_gain_<codec>_lf.md` |
| E2 | Around natural cuts the search raises QP on frames c-4..c-1 (+0.5..+1.4 QP vs stable GOPs) and lowers it at c..c+5 (-2.0 at the cut, about -0.6 after). Before (c-3..c-1) is 43% (x264) / 39% (x265) of the QP-change magnitude. Magnitude, not gain: no counterfactual encodes yet | same, sections 2-3 |
| E3 | Base-QP estimator error: 3.6-4.0 QP at k=0, 2.2-2.7 at k >= 2. Most of the information is in the first 1-2 P frames | `docs/budget-estimator-v1.md` |
| E4 | Without feedback, k matters a lot (GOP-start estimate: -90 at k0, -48 at k2, -31 at k29); with online feedback the k effect is small but real | `results_v1/controller_final.md` |
| E5 | Controller v1 (leak-free), x264 stable / cut by k: k0 -3.84 / -4.66, k2 -2.37 / -1.79, k5 -1.03 / -0.25, k10 -0.97 / -0.59, k29 -1.92 / -3.26. x265: k0 -4.25 / -5.68, k5 -0.26 / +0.21, k29 -1.84 / -3.43. So k5-k0 = +2.8 stable, +4.4 cut (x264); +4.0 / +5.9 (x265), and k=29 drops, mostly on cut GOPs | `results_v1/w3/methods_by_class_<codec>_lf.md` |
| E6 | Controller final2 (the residual's base, i_cap 0.3), x264 test, flat included: -3.94 / -2.39 / -1.41 / -1.74 / -3.06 (k 0/2/5/10/29) | `results_v1/controller_final2.md` |
| E7 | On the LEAKY budgets (orig arm) Lagrangian PPO is flat in k (k0 4.67, best k>0 -0.12 +- 0.20, x264); the decoupled budget lowers k0 to 3.37 and gives a small positive k effect (+0.52 +- 0.27) | `results_v1/v1_headline.md` |
| E8 | On the orig arm, CQL->PPO and BC have large k-gains (+3.2 to +3.9) that are mostly smaller budget penalties, not better allocation; shaping removes CQL->PPO's k-gain | `results_v1/v1_overshoot.md`, `results_v1/shaping_compare_x264.md` |
| E9 | Encoder ABR+VBV: -26 to -35 at every k, no gain from rc-lookahead | `results_v1/baselines_v1_table.md` |

## Back-of-envelope: how much of the search's gain can lookahead alone explain?

Mean search gain over the ramp start, x264 test, all rows: (796 x 7.01 + 196 x 10.64 + 16 x 13.66) / 1008 = 7.8.
If the before-cut share of the cut GOPs' gain equals its share of the QP change (43%, E2), the part that strictly
needs seeing a cut in advance is 196 x 10.64 x 0.43 / 1008 = 0.9 points, about 11% of the search's gain. Everything
else is either reachable at k=0 in principle (reaction at/after the cut, the general spend profile), or is
"how expensive is this GOP" information that the first 1-2 frames reveal (E3). This is an upper-bound style
estimate: magnitude is not gain, and the counterfactual encodes (tracker item 22) would replace it.

## Hypotheses

### H1. Every leak-free method's k-curve is "steep then flat": most of the k-gain arrives by k=2, all of it by k=5.
- Prediction: for the controller and the residual RL, score(k=5) - score(k=2) < score(k=2) - score(k=0), and
  score(10) - score(5) is within +-0.5 (CI includes 0).
- Why: E3 (the estimator's error halves between k0 and k2), E5 (controller k2 already takes 50-65% of its k0->k5
  gain), and the cut anticipation window in E2 is only 4-5 frames wide.
- Falsified if: any leak-free method gains >= 1 point (CI excluding 0) from k=5 to k=10 or k=29.
- Outcome: (11-11, quality-at-budget metric, test; results_v1/w5/w5_numbers.md; thresholds converted at 12.5 points/dB; controller = final4 [final3], residual = res@hist on final4 [res on final3]) SUPPORTED. final4 k2-k0 +0.19 dB (x264) / +0.16 (x265), k5-k2 +0.03 / +0.07, k10-k5 +0.01 / +0.01
  (CIs include 0); same shape for final3 and both residuals. No k5 -> k10/k29 gain >= 0.08 dB with CI excluding 0 (largest:
  x265 res@hist k29-k5 +0.07 [+0.03, +0.12], under the threshold). Residuals lose from k5 to k10 (-0.06 both encoders).

### H2. Cut GOPs gain more from lookahead than stable GOPs, and their curve keeps rising longer.
- Prediction: k5-k0 is larger on cut than on stable GOPs by +1 to +3 points (already true for the controller, E5:
  +1.6 x264, +1.9 x265; predicted to hold for the residual RL). On stable GOPs the curve is flat from k=2 (k5-k2
  within +-0.7); on cut GOPs k5-k2 > +0.7.
- Why: on stable GOPs lookahead only refines the GOP's cost estimate, which saturates by k=2 (E3); on cut GOPs the
  search's pre-cut QP raise starts 4 frames ahead (E2), so k must reach about 4 to see it.
- Falsified if: the cut - stable difference in k5-k0 has a CI including 0 for the residual RL on both encoders.
- Outcome: (11-11, quality-at-budget metric, test; results_v1/w5/w5_numbers.md; thresholds converted at 12.5 points/dB; controller = final4 [final3], residual = res@hist on final4 [res on final3]) SUPPORTED FOR THE CONTROLLER, FALSIFIED FOR THE RESIDUAL. final4 cut - stable k5-k0 +0.20 [+0.04, +0.39] dB
  x264, +0.19 [-0.01, +0.41] x265 (inside the predicted +0.08..+0.24); cut k5-k2 +0.08 / +0.12 (> 0.056 as predicted); stable
  k5-k2 +0.03 / +0.06 (x265 just above the +-0.056 band). Residual cut - stable: res@hist +0.00 [-0.12, +0.13] / +0.03
  [-0.07, +0.13], res +0.10 / +0.19, all CIs include 0 on both encoders -> falsified by its own criterion.

### H3. Lookahead explains only a small part of the search's gain: the best causal-to-lookahead step closes <= 20% of the gap.
- Prediction: for any single method, (best-k score - k0 score) / (search - k0 score) <= 0.2 on the residual RL,
  and <= 0.3 on the controller (E6 gives about 0.18 for final2 at k5: (-1.41 + 3.94) / (10.3 + 3.94); approximate, final2's
  mean includes flat GOPs and the search's does not).
  The remaining gap is allocation quality at a given k, not information.
- Why: back-of-envelope above (about 11% of the gain needs advance sight of a cut) plus a small cost-estimate share.
- Falsified if: some leak-free method's best k closes > 30% of its own k0 gap to the search.
- Outcome: (11-11, quality-at-budget metric, test; results_v1/w5/w5_numbers.md; thresholds converted at 12.5 points/dB; controller = final4 [final3], residual = res@hist on final4 [res on final3]) FALSIFIED: lookahead closes MORE of the gap than predicted. Gap closed (best k vs k0): final4 0.36
  [0.26, 0.44] x264 / 0.34 [0.25, 0.42] x265; final3 0.48 / 0.43; res@hist 0.43 / 0.35; res 0.45 / 0.38 (all > 0.3). Note
  the absolute sizes are small in dB (final4 +0.23 / +0.24 of a 0.65 / 0.72 dB k0 gap); the learners on the prev-GOP base
  close 0.51-0.72 because their k0 is far lower (budget handling, not lookahead; see tracker item 22).

### H4. k=29 is worse than k=5 for every method with a fixed capacity or fixed settings, and the loss sits in cut / gradual GOPs.
- Prediction: score(29) < score(5) for the controller (already true, E5/E6) and for the residual RL, with >= 60%
  of the drop coming from cut + gradual rows (they are 21% of rows).
- Why: E5 (controller k29 cut -3.3 vs stable -1.9) and the earlier diagnosis (full lookahead over-plans the I frame
  and mid-GOP cuts; EXPERIMENTS P1). The residual sees the controller's QP and only a fixed-size summary of the
  window, so it is unlikely to fully undo it; on the orig arm, CQL->PPO also dropped at k29 (2.09 vs 3.75).
- Falsified if: the residual RL at k=29 is >= its k=5 score (CI of the difference excluding negative values).
- Outcome: (11-11, quality-at-budget metric, test; results_v1/w5/w5_numbers.md; thresholds converted at 12.5 points/dB; controller = final4 [final3], residual = res@hist on final4 [res on final3]) MOSTLY FALSIFIED. With history the controller's k29 drop is gone on x264 (k29-k5 +0.00 [-0.03, +0.04]) and
  small on x265 (-0.04 [-0.08, -0.00], 81% of it in cut/gradual rows, as predicted); final3 -0.04 / -0.09 (n.s.). Residual:
  x264 res@hist k29 < k5 (-0.10 [-0.15, -0.05]) but only 24% of the drop is in cut/gradual rows (21% of rows: not
  concentrated); x265 res@hist k29 > k5 (+0.07 [+0.03, +0.12]) -> falsified by the stated criterion.

### H5. The residual on the controller beats the controller at every k, most at k=0, and its k-curve is flatter.
- Prediction (x264 test, sweep 13918676): res - ctrl > 0 at every k with CIs excluding 0 at k=0; size +1 to +3 at
  k=0 and +0.5 to +2 at k=5; gap_closed (share of the controller-to-search gap) 10-30%. The residual's k5-k0 is
  smaller than the controller's (+2.5 for final2). Over-budget rate within +2 percentage points of the
  controller's. Mean |offset| 0.5-1.5 QP; offsets concentrated on the I frame, the first P frames and the frames
  at/after a visible cut.
- Why: the residual cannot add information, but at k=0 the controller is weakest where a learned prior helps:
  the start-of-GOP cost guess (E3) and the reaction to a cut it can see. Reward is relative to the controller's own
  result, so a policy that does nothing scores 0 and PPO starts at P(offset 0) = 0.7.
- Falsified if: res - ctrl CI includes 0 at k=0 (no learned gain at all), or the residual buys its gain with a
  higher over-rate (> +2 pp).
- Outcome: (11-09, sweep 13918676) FALSIFIED as stated / not a valid test. Score res - ctrl +2.8 (k0), +1.6 (k2),
  n.s. at k5/k10, +2.7 (k29), but by under-spending (budget use 0.66-0.86 vs 0.87-0.89; mean |offset| 1.1-2.6, all
  above the predicted 0.5-1.5); quality at the budget is lower than the controller's at every k (-0.12 to -1.23 dB).
  The reward (old score) does not penalise unused budget. Rerun with a quality-at-budget reward before testing H5/H6.
  Outcome 11-11 (rerun): (11-11, quality-at-budget metric, test; results_v1/w5/w5_numbers.md; thresholds converted at 12.5 points/dB; controller = final4 [final3], residual = res@hist on final4 [res on final3]) FALSIFIED. With the dB reward the residual no longer under-spends but is BELOW its
  controller at every k: res@hist - final4 -0.20 / -0.05 / -0.06 / -0.12 / -0.16 dB (x264, k 0/2/5/10/29, all CIs
  < 0), x265 -0.12 / -0.12 / -0.13 / -0.20 / -0.03 (k29 n.s.); res - final3 -0.01 to -0.15 dB.

### H6. On leak-free budgets, the "lookahead does not help" result of the leaky pipeline disappears.
- Prediction: the residual RL's k-gain (best k vs k0) is positive with a CI excluding 0, unlike Lagrangian PPO on
  the orig arm (-0.12 +- 0.20, E7). Size: +0.5 to +2.5 points.
- Why: on the orig arm the budget is the GOP's own constant-QP spend, which tells a k=0 policy the GOP's cost, so
  lookahead has nothing left to add (E7: removing part of the leak lowers k0 by 1.3 and creates a +0.5 k effect).
  With clip-level budgets the cost has to come from the frames, which lookahead supplies (E3, E4).
- Falsified if: residual best-k minus k0 has a CI including 0 on both encoders.
- Outcome: (11-11, quality-at-budget metric, test; results_v1/w5/w5_numbers.md; thresholds converted at 12.5 points/dB; controller = final4 [final3], residual = res@hist on final4 [res on final3]) SUPPORTED (and larger than predicted). Residual best k - k0: res@hist +0.36 [+0.27, +0.46] dB (k5, x264),
  +0.29 [+0.20, +0.38] (k29, x265); res +0.36 / +0.32. Predicted +0.04..+0.20 dB.

### H7. Both encoders give the same curve shapes; x265's lookahead effect is somewhat larger.
- Prediction: H1-H6 hold on x265 if it is run; k5-k0 is larger on x265 than on x264 for the same method
  (controller: +4.1 vs +2.5, E5/E6).
- Why: observed for the controller on val and test (larger k0 loss on x265, E5/E6); no mechanism established.
- Falsified if: the order of the x264 and x265 k-gains flips for the residual RL with CIs not overlapping.
- Outcome: (11-11, quality-at-budget metric, test; results_v1/w5/w5_numbers.md; thresholds converted at 12.5 points/dB; controller = final4 [final3], residual = res@hist on final4 [res on final3]) NOT SUPPORTED (not falsified). k5-k0: final4 +0.22 x264 vs +0.23 x265, final3 +0.37 vs +0.36 (equal);
  residual res@hist +0.36 vs +0.22, res +0.36 vs +0.28 (x264 larger; CIs overlap, so the falsification criterion is not met).

### H8. Budget level: the tightest-QP (most generous) level 24 shows the smallest learned gain and the noisiest curves.
- Prediction: res - ctrl at level 24 is below the all-level mean; per-level k-curves have the widest CIs at 24.
- Why: at level 24, 10% of GOPs need QP < 18 (E3 source), outside the constant-QP reference curve (18-50), and
  the residual's QP floor (11) is reached more often, so offsets have less room and the score is extrapolated.
- Falsified if: level 24's res - ctrl is the largest of the 4 levels.
- Outcome: (11-11, quality-at-budget metric, test; results_v1/w5/w5_numbers.md; thresholds converted at 12.5 points/dB; controller = final4 [final3], residual = res@hist on final4 [res on final3]) MOSTLY SUPPORTED. res@hist - final4 by level (all k): x264 24 -0.18, 30 -0.16, 36 -0.12, 42 -0.02;
  x265 24 -0.29, 30 -0.23, 36 -0.11, 42 +0.15 [+0.03, +0.30] (level 24 smallest on both). res - final3: x265 24 smallest
  (-0.09); x264 24 -0.06 is mid (42 -0.08 smallest). New: on x265 at level 42 (lowest rate) the residual BEATS final4,
  the only learner win with a CI above 0 in the pooled-k tables (one of 8 level cells; check per k before using it).

### Not hypotheses (already measured or too small)
- Search: k-independent by construction (hindsight); the ceiling for all curves (E1).
- Encoder ABR+VBV: flat and far below everything at every k (E9); no W4 work needed.
- Gradual GOPs: 4 test GOPs (16 rows). Report them, but no claim either way.
- Orig-arm curves of BC / CQL->PPO: their k-gain is budget handling (E8); they stay in the report as the leaky
  reference, not as evidence about lookahead.

## What these imply for the W4 adaptive-lookahead gate

If H1 and H2 hold, a gate that uses k=2 on stable stretches and k=5 when a cut is detected in the window should
match the best fixed k (within CI) at a mean lookahead of about 2.5-3 frames instead of 5. If H1 fails (gains keep
coming past k=5), the gate saves less delay than this. Thresholds are chosen on val only. The gate changes the
trajectory, so it needs new encodes (controller) or new eval episodes (residual RL), not a re-mix of stored runs.
- Outcome (11-11, results_v1/w5/w5_numbers.md section 3; hindsight bound from stored runs, not the real gate): FALSIFIED.
  k2 on stable GOPs + k5 on cut/gradual GOPs (mean delay 2.6 frames) is BELOW fixed k5: final4 -0.023 [-0.044, -0.004]
  dB x264, -0.049 [-0.088, -0.016] x265 (res@hist -0.01 n.s. / -0.05). Reason: stable GOPs also gain from k2 to k5
  (+0.03 / +0.06 dB), so lookahead can't be dropped on them. Against fixed k2 it gains only +0.01 / +0.03.

## How W4 tests them

| Hypothesis | Script / output |
|---|---|
| H1, H2, H4 (controller) | `scripts/w3_methods_by_class.py <codec> lf` (by class and k) |
| H1-H6 (residual RL) | `scripts/res_compare.py <codec>` -> `results_v1/res_compare_<codec>.md` (by k and class, res - ctrl CI, gap_closed_%, %over, mean |off|) |
| H3 | gap_closed by k from the two outputs above |
| H8 | to add: a per-level split in `scripts/res_compare.py` (and the level-24 report, tracker item 22) |
| Before-cut gain (back-of-envelope) | counterfactual encodes, tracker item 22 (needs approval, ~1,100 encodes) |
