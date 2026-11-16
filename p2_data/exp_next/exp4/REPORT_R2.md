# Exp 4 R2 report (2026-11-13)

Full tables: results_v1/next/exp4/r2_report.md (exp_next/exp4/report_r2.py; episodes in r2_episodes.parquet).
Runs: rcwork_v1/<enc>_resh/results_rl/res_k{0,5}_fixed_f4_lam0.17_st180k_r6_s{0,1,2}; jobs x264 14213909,
x265 14213910, 12/12 COMPLETED. Val only.

## Gate (PREREG_R2.md): FAIL

R2 - R1 (180k), pooled, hole excluded: +0.040 [+0.023, +0.061] (n 2196). x264 +0.070 *, x265 +0.010 n.s.
Fails two of the four conditions: k0 -0.004 (needs >= 0) and seed 1 -0.016 (seeds 0/2 +0.035/+0.100).
The whole gain is at k5 (+0.083); at k0 R2 = R1.

## Descriptive

- R2 vs final4: x264 -0.001, x265 +0.007, pooled +0.003 [-0.041, +0.047] (R1 was -0.037). R2 is the first learner
  that ties final4 on both encoders, but does not beat it.
- 60k checkpoint: pooled -0.008 vs final4; 180k - 60k +0.010 n.s. At 60k the policy still outputs offset 0 on
  88-94% of frames.
- Caps check: at k5, 27-28% of non-zero offsets go beyond final4's step limit dmax (k0: 5-10%); fcap < 0.4%;
  range clip 3-4%. Worst cell (sum) 32.7% > 20% -> reported to Aayush before R3 (pre-registered flag).
- Offsets are concentrated on a few values per (encoder, k), e.g. x265 k0 +1 on 59% of frames; no collapse to 0
  or to an extreme. Mean |offset| 0.9-1.1. Spend error: k5 1.9-2.0% (R1 2.5-2.7%), x265 k0 worse (5.2% vs 4.2%,
  signed -4.1%).
