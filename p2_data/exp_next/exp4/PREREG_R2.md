# Experiment 4, rung R2: residual on final4, range -6..+6 + final4-state features -- pre-registration

Written 2026-11-13 before any R2 run was submitted. Not to be edited after results arrive.

## Hypothesis

With twice the offset range and direct access to final4's internal state, the residual (otherwise identical to R1)
learns more of the shape signal Exp 1 found (R^2 0.33-0.40 for search - final4 shape), and scores above R1.

## Configuration (one joint change vs R1; amendment 5: R2's effect is reported jointly, not attributed)

- R1 = Exp 3: arm `resh`, lambda 0.17, 180k PPO steps, offsets -3..+3, P(offset 0) = 0.7 at init, full train set.
- R2 = R1 + `RC_RES_RANGE=6` (offsets -6..+6, 13 actions; same init rule, P(offset 0) = 0.7) + `--extra f4`
  (5 features appended to the observation, computed in `_obs` before frame t is encoded, from final4's
  `decide(..., diag=...)`): final4's planned QP for frame t, final4's level L_t, log2(predicted spend of final4's
  plan over the remaining frames / remaining budget), log2(calibrated c_P / its prior), frames left.
- Caps: `resh` behaviour (amendment 12): offsets added after final4's caps, not re-applied. Each evaluated episode
  logs how often the offset takes the QP beyond final4's step limit (dmax) or fcap floor, or is clipped by 11..51.
- k in {0, 5}, seeds 0-2, both encoders: 12 runs; checkpoint saved at 60k (descriptive); val only, deterministic.
- Code: repo-pavneet branch `next-exp` (controller `diag`, env `f4` + counters, config `RC_RES_RANGE`); regression
  with defaults: parity 24/24 per encoder, stored-episode check 5/5 per encoder (11-13).

## Gate (primary)

R2 (180k) minus R1 (Exp 3, 180k), on val, paired on (GOP, level, k), seeds averaged per episode, pooled over both
encoders and k in {0, 5}; 95% bootstrap over clips (each clip carries both encoders); level-24-hole episodes
excluded. **Pass** requires all of: CI above 0; neither encoder's CI entirely below 0; point estimate >= 0 at k0
and k5 separately; the mean difference has the same sign for seeds 0, 1, 2.

## Checks reported before R3

- Share of non-zero offsets that go beyond dmax / fcap or are range-clipped; if > 20%, reported to the human before
  R3 is trained.
- Action histogram, mean |offset|, budget use, mean |spend error|; collapse to all-zero or one extreme = red flag.

## Also reported

R2 - final4 (same pooling), decomposition (A, E - P, spend error), 60k vs 180k.
