# Experiment 1: score decomposition and learnable headroom -- pre-registration

Written 2026-11-13, before any Exp 1 numbers were computed. Not to be edited after results arrive.

## Hypothesis

The learners' deficit to final4 is mostly spend error (E - P), not allocation quality (A). Allocation headroom
above final4 (search A - final4 A) is large enough to be worth Experiments 4/5, and part of the search's shape
beyond final4's own shape is predictable from causal features.

## Definitions (per episode; `rclib/metrics.py` interpolation, lfq infos curves and budgets)

- rho = bits / B
- A = PSNR - PSNR_cq(bits)              (quality for the bits)
- E = PSNR_cq(bits) - PSNR_cq(B)        (spend effect)
- P = 0.17 x max(0, 100 (rho - 1))      (penalty)
- Check: score = A + E - P on every episode to 1e-6.

## Data and split

- **Primary split: val** (both encoders). Train is used for final4 / final3 / search (descriptive) and for fitting
  the shape models. **Test is not used** (protocol: test once, at the end).
- Flat GOPs excluded (`data/v1/320x180/rd/flat_gops.csv`; the lfq `infos_learn.pkl` set).
- Search: the stored best plan per (GOP, level) (k-independent). For shapes on train, the shape is averaged over
  all tied-best plans of the 600 logged encodes (amendment 4); val has only the stored best plan.

## Primary quantities and stop rules

1. **Allocation headroom H** = mean over val episodes of (search A - final4 A), paired on (GOP, level, k), pooled
   over both encoders and k in {0, 5}, with a 95% clip bootstrap.
   - **Stop rule 1:** if H < 0.05 dB (point estimate), report to the human that frame-level RL has little left to
     gain and that Experiments 4 and 5 should shrink.
2. **Shape predictability R2_diff(k=5)** = R^2 on val of a GBM predicting (search shape_t - final4 realised
   shape_t) from causal features at k = 5, fitted on train (clip-grouped out-of-fold R^2 also reported).
   - **Stop rule 2:** if R2_diff(k=5) < 0.1, record the expectation that Experiment 4 rung 3 gains at most a few
     hundredths of a dB.

Shapes: shape_t = QP_t - mean of the P-frame QPs (frames 1..29), frame 0 = the I-frame offset. final4's realised
shape uses its stored per-frame QPs for the same (GOP, level, k).

Causal features for frame t at lookahead k: frame index, frame type, budget level, log2 bits-per-frame budget vs
the visible first-pass mean, and first-pass bits (P1 settings, QP 32) of frames 0..t+k only, as relative log
ratios (frame t vs the visible mean, vs frame t-1, vs frame 0; max and mean over the visible window ahead).
Model: sklearn HistGradientBoostingRegressor, default settings, fixed seed 0; no tuning.

## Descriptive outputs (no thresholds)

- Per method x encoder x level x class x k: mean A, mean (E - P), mean |rho - 1|, signed mean (rho - 1),
  % over, p90 |rho - 1|. Methods: final4, final3, CQL->PPO@prev 60k / 180k / 540k, BC@prev, res@hist,
  res_st180k@hist, res_lv36-42@hist, search, ABR+VBV.
- Local R-D slope at B per level and encoder (dB per 1% of bits); the metric's optimal over-budget rate
  (slope / 0.17, first order) vs final4's actual rate per level.
- R^2 of the search shape from (i) frame index and type only and (ii) causal features at k in {0, 2, 5}.
- Level-24 hole: score distribution of the extrapolated episodes per method, and pooled results with and
  without them. No fix applied; a proposal goes to the human.
