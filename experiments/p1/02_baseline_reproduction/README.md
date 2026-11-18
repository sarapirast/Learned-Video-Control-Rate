# 02 · Baseline reproduction on val (2026-11-16)

**Question:** with the shim backend, do we reproduce the team's frame-level numbers on val (final4 at every k, R3 at
k5), and do all methods use the same scoring?

## What was run
- x264 re-run on the shim, all 140 val GOPs × 4 budget levels (560 episodes; 548 after the level-24 "hole"):
  final4 at k = 0, 2, 5, 10, 29 and R3 k5 seeds 3, 4, 5 (180k checkpoints).
- Constant QP and ABR do not run through rclib: their stored rows are rescored. All x265 numbers are stored rows.
- Scoring = `p2_data/exp_next/final/report.py`: `rclib.metrics.score` (dPSNR_B − 0.17 dB per 1 % over), paired with
  final4 at the same k, stable vs cut+gradual, `metrics.paired_ci` and the team's 95 % clip bootstrap.

## How to rerun
```bash
bash run_rerun_baselines_val.sh final4     # ~9 min, one core (compute node)
bash run_rerun_baselines_val.sh r3         # ~6 min
/scratch1/aayushso/envs/ee599/bin/python -I score_baselines_val.py     # seconds; Aayush's ee599 env (pyarrow)
```
Outputs: `/scratch1/ahhanagu/ee599/results/baselines_val/` (`rows_*.pkl`, `rows_scored.parquet`, `summary.md`).

## Checks
| Check | Result |
|---|---|
| R3 (3 seeds × 560): QPs, bits, score vs stored | identical |
| final4 (5 k × 560): bits vs stored | identical 2,800/2,800 |
| final4 PSNR vs stored | **27/2,800 differ**: two cut GOPs (`MusicVideo_360P-5f07@30`, `@180`) |
| x265 rows and stored ABR rows vs the team's `report_val.md` | match |

**PSNR-cap finding:** the stored final4 rows (`p2_data/scripts/rd_native.py` PSNR) did not cap each plane at 100 dB;
rclib does (every learner's rows). A losslessly coded plane then scores 148.13 dB instead of 100, which moves the GOP
mean by exact steps of 0.2005 dB. Aayush confirmed and adopted one cap everywhere (`p2_data/docs/team-update-2026-11-16.txt`
§7, `p2_data/exp_next/final/cap_fix.py`): val x264 R3 − final4 **+0.077**, cut/gradual **+0.069** (was +0.068 / +0.016).

## Results (provisional: absolute scores will move with Aayush's capped constant-QP curves; differences vs final4 should not)
| enc | method | source | k | score | Δ vs final4 (paired_ci) |
|---|---|---|---|---|---|
| x264 | final4 | re-run | 0 / 2 / 5 / 10 / 29 | −0.364 / −0.155 / −0.122 / −0.126 / −0.149 | reference |
| x264 | R3 180k (s3–5) | re-run | 5 | −0.045 | **+0.077 ± 0.037** (clip boot [+0.020, +0.143] \*) |
| x264 | ABR m0.90 | stored | 0 / 5 | −1.525 / −1.260 | −1.160 / −1.138 |
| x264 | CQP best (hindsight) | stored | 29 | −0.306 | −0.158 ± 0.051 |
| x265 | final4 | stored | 0 / 2 / 5 / 10 / 29 | −0.472 / −0.265 / −0.256 / −0.248 / −0.237 | reference |
| x265 | R3 180k (s3–5) | stored | 5 | −0.052 | **+0.204 ± 0.063** |
| x265 | ABR m0.93 | stored | 0 / 5 | −1.401 / −1.017 | −0.929 / −0.761 |

Score in dB; level-24 hole excluded (n = 548 x264, 550 x265). Full table (all k, CQP causal estimate, class splits):
`results/baselines_val/summary.md`.
