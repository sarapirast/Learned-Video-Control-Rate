# Experiment 1: score decomposition and learnable headroom -- REPORT (2026-11-13)

Pre-registration: `exp_next/exp1/PREREG.md` (written before results). No encodes. Val only for every number below;
test not read. Flat GOPs excluded.
Scripts: `exp_next/exp1/decompose.py`, `exp_next/exp1/shape_r2.py`.
Outputs: `results_v1/next/exp1/{headroom.md, decomposition_<enc>.md, episodes_<enc>.parquet, shape_r2.md}`.

## Verdict on the stop rules

| Rule | Quantity | Result | Threshold | Outcome |
|---|---|---|---|---|
| 1 | Allocation headroom H = search A - final4 A, val, both encoders, k 0/5 | **+0.369 dB [+0.269, +0.489]** | < 0.05 stops | Not triggered: Exp 4/5 keep full scope |
| 2 | R^2 on val of (search shape - final4 shape), k = 5, GBM | **x264 0.331, x265 0.375** | < 0.1 stops | Not triggered |

## 1. Decomposition (val, k 0 and 5 pooled)

score = A + E - P checked on every episode (exact); the 52,080 stored learner scores are reproduced with max
difference 0. (The `controller_real` parquets store the old %-saving score, so final3/final4 are recomputed only.)

| Method | x264 score | A | E - P | mean \|spend err\| | signed | % over | x265 score | A | E - P | mean \|spend err\| | signed | % over |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| search | +0.316 | +0.329 | -0.012 | 0.2% | -0.1% | 24 | +0.274 | +0.293 | -0.019 | 0.2% | -0.2% | 26 |
| final4 | -0.293 | +0.020 | -0.313 | 3.1% | -0.6% | 53 | -0.414 | -0.136 | -0.277 | 2.8% | -0.7% | 47 |
| CQL->PPO 540k | -0.430 | -0.030 | -0.400 | 4.7% | -1.1% | 26 | -0.439 | -0.074 | -0.365 | 5.0% | -2.3% | 24 |
| res@hist | -0.471 | -0.007 | -0.464 | 6.1% | -4.9% | 33 | -0.584 | -0.112 | -0.472 | 6.7% | -5.8% | 26 |
| final3 | -0.476 | -0.076 | -0.400 | 4.8% | -2.7% | 46 | -0.572 | -0.166 | -0.406 | 4.9% | -3.2% | 46 |
| CQL->PPO 180k | -0.532 | -0.002 | -0.530 | 5.7% | -0.6% | 38 | -0.591 | -0.053 | -0.538 | 6.6% | -2.5% | 31 |
| CQL->PPO 60k | -1.117 | +0.036 | -1.152 | 14.9% | -8.0% | 29 | -0.999 | -0.043 | -0.956 | 13.6% | -8.8% | 23 |
| BC@prev | -1.179 | +0.082 | -1.261 | 13.2% | -1.2% | 40 | -1.094 | -0.003 | -1.091 | 12.1% | -1.5% | 41 |
| ABR+VBV | -1.726 | -0.718 | -1.008 | 10.4% | +3.9% | 66 | -1.537 | -0.777 | -0.760 | 7.4% | +3.2% | 71 |

Reading:
- **Every causal method's quality for the bits (A) is within about 0.1 dB of final4's; the differences between
  them are almost entirely spend error.** BC@prev has the best A on x264 (+0.08) and the second-worst score.
- **final4 itself loses about equally to spend (-0.28..-0.31) and to allocation (0.33-0.43 below the search).**
  "final4 with perfect landing" = its A: +0.02 (x264), -0.14 (x265).
- More PPO steps (60k -> 180k -> 540k) cut the learner's spend error 14.9% -> 5.7% -> 4.7% (x264) and barely
  moved A. The residual's spend is biased low (-5 to -6%).
- ABR+VBV also has poor A (-0.7 dB): its loss is not only overshoot.

Per level and per GOP class: `decomposition_<enc>.md`.

## 2. Allocation headroom by k (search A - final4 A, val)

| k | x264 | x265 |
|---|---|---|
| 0 | +0.356 [+0.259, +0.467] | +0.479 [+0.367, +0.609] |
| 2 | +0.278 [+0.187, +0.402] | +0.382 [+0.240, +0.548] |
| 5 | +0.261 [+0.185, +0.360] | +0.379 [+0.238, +0.535] |
| 10 | +0.285 [+0.215, +0.367] | +0.388 [+0.267, +0.518] |
| 29 | +0.321 [+0.250, +0.396] | +0.388 [+0.294, +0.491] |

## 3. Local R-D slope and the metric's optimal over-budget rate (val)

| Level | x264 slope (dB per 1% bits) | optimal over rate | final4 over rate | x265 slope | optimal | final4 |
|---|---|---|---|---|---|---|
| 24 | 0.064 | 37% | 45% | 0.056 | 33% | 43% |
| 30 | 0.051 | 30% | 51% | 0.048 | 29% | 44% |
| 36 | 0.044 | 26% | 55% | 0.042 | 25% | 52% |
| 42 | 0.043 | 25% | 65% | 0.036 | 21% | 60% |

- **Correction to the brief (Part A2):** 1% more bits buys 0.036-0.064 dB at the budget, not 0.085. The metric
  is therefore not symmetric: going 1% over nets about -0.11 to -0.13 dB, going 1% under about -0.04 to -0.06 dB.
- First-order optimum: P(over) = slope / 0.17 = 21-37%. **final4 goes over more often than that at every level
  (43-65%)**, most at the tight levels, so a slightly lower margin would likely help it (the 0.97 test
  overshot the other way: 9% over, -0.05 dB). final4 is frozen; this is descriptive. It does mean "% over" near
  50% is not automatically optimal, and that the best learner's lower over rate (24-26%) is about right.
- Mean |spend error| remains the main quantity: the brief's "score ~ A - c x |spend error|" holds with an
  asymmetric c (larger over, smaller under).

## 4. Search shape predictability (val)

shape_t = QP_t - mean P-frame QP. Train shapes average the tied-best plans: 55-56% of train (GOP, level) have ties
(median 2, mean 9-10 plans).

| Target | k | x264 val R^2: index only / GBM | x265 val R^2: index only / GBM |
|---|---|---|---|
| search shape | 5 | 0.710 / 0.742 | 0.709 / 0.741 |
| search - final4 shape | 0 | 0.042 / 0.350 | 0.081 / 0.394 |
| search - final4 shape | 2 | 0.093 / 0.341 | 0.129 / 0.403 |
| search - final4 shape | 5 | 0.159 / 0.331 | 0.182 / 0.375 |

Train out-of-fold R^2 is similar (0.27-0.37 for search - final4 with the GBM).

Reading:
- The search shape is mostly the spend-early ramp it starts from (index alone explains 0.71); causal first-pass
  features add only 0.03.
- **The part a residual on final4 must learn (search - final4) is a third predictable from causal features** and
  hardly depends on k (0.33-0.40 for k 0/2/5). Part of that is final4's own feature-driven deviations (caps,
  history), which a residual with final4-state features can also see.
- R^2 is on QP shape, not dB; it bounds the label's learnability, not the gain.

## 5. Level-24 hole (val)

10 (x264) / 8 (x265) of 140 level-24 episodes, plus 2 at level 30, have budgets above the QP-18 curve point
(reference PSNR extrapolated linearly in log bits). Pooled scores with and without them are in
`decomposition_<enc>.md`.
- They are 60 (x264) / 50 (x265) of 2,800 val episodes (all k), but every causal method scores very badly on them:
  final4 -2.42 / -2.70 dB, CQL->PPO 540k -1.69 / -2.23, res@hist -3.48 / -4.01 (search +0.04 / -0.21).
- Excluding them moves pooled val scores by 0.03-0.07 dB and favours final4 slightly more than the 540k learner
  (final4 -0.224 -> -0.176, 540k -0.374 -> -0.345 on x264). **No fix applied.** Proposal for you: exclude these episodes from primary endpoints
(simplest, documented), or extend the constant-QP curves down to QP 11 (about 1,000 GOP encodes per encoder,
a few CPU-h) and rescore everything.

## Consequences for the plan

- Exp 4 and 5 go ahead at full scope (both stop rules clear).
- The allocation target is large (+0.37 dB of A) but the learners' current loss is spend error. A residual on
  final4 keeps final4's landing (3% error) and has a 0.33-0.40-R^2 shape signal to learn; that is the case for
  R2/R3.
- Brief Part A2 needs the slope correction above; gates already use mean |spend error|, which stays right.
