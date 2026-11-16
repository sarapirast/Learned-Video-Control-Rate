# Experiment 3: residual on final4 at lambda 0.17 -- REPORT (2026-11-13)

Pre-registration `exp_next/exp3/PREREG.md`. Jobs x264 14189238, x265 14189239 (12 runs, all COMPLETED; x264
32-44 min, x265 85-103 min per run). Analysis `exp_next/exp3/report.py` -> `results_v1/next/exp3/report.md`.
Val only; level-24-hole episodes excluded from the primary endpoint.

## Primary: lambda 0.17 (180k) - lambda 0.34 (180k, item 37) -- PASS

| | difference (dB) |
|---|---|
| pooled, both encoders, k 0/5 | **+0.137 [+0.109, +0.166]** |
| x264 | +0.184 [+0.136, +0.234] |
| x265 | +0.090 [+0.058, +0.126] |
| k0 / k5 | +0.093 / +0.180 |
| seeds 0 / 1 / 2 | +0.195 / +0.104 / +0.112 |

All four pass conditions hold. With the hole included: +0.147 [+0.115, +0.179].

## Secondary: against final4 (val, hole excluded, seeds averaged)

| | x264 | x265 | both |
|---|---|---|---|
| lambda 0.17, 180k | -0.071 [-0.118, -0.029] | -0.003 [-0.058, +0.070] | -0.037 [-0.083, +0.015] |
| lambda 0.17, 60k checkpoint | -0.034 [-0.079, +0.002] | -0.003 [-0.041, +0.039] | -0.018 [-0.052, +0.012] |
| lambda 0.34, 180k | -0.255 [-0.334, -0.179] | -0.093 [-0.144, -0.031] | -0.174 [-0.232, -0.120] |

180k - 60k (lambda 0.17): -0.019 [-0.042, +0.009]: more steps did not help (as in item 37).

## Reading

- The price mismatch explains most of the old residual's deficit: at lambda 0.34 it under-spent (signed spend error
  -6% at k0, 16-18% of episodes over) to avoid overshoots the metric prices at half that. At 0.17 the bias shrinks
  to -2% / -0.1% (k0 / k5 x264) and it goes over on 33-43%.
- It now **ties final4** on x265 and pooled; on x264 it is still 0.07 dB below. It does not beat final4.
- Quality for the bits (A) is unchanged or slightly worse than final4's; the gain is spend error (k5 x264 mean
  |spend error| 3.5% -> 2.5%). The residual still has a fat tail at k0 (p90 |spend error| 14-16%).
- Policy use: at k5 it moves the QP on 72-82% of frames (mean |offset| 1.4-1.6) and lowers it on average at k5
  (x264 mean offset -0.87): it spends earlier/more than final4 and leaves final4 to re-plan.
- The 60k checkpoint is as good as 180k (slightly better on x264), so step count is not the limit here.

## Consequence

lambda 0.17 becomes R1, the base of Experiment 4's ladder (R2 compares against these runs).
