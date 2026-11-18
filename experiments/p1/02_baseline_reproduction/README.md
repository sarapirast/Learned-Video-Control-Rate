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
/scratch1/aayushso/envs/ee599/bin/python -I score_baselines_val.py --psnr-cap   # final: one PSNR cap everywhere
/scratch1/aayushso/envs/ee599/bin/python -I score_baselines_val.py              # earlier: stored curves (summary.md)
```
Outputs: `/scratch1/ahhanagu/ee599/results/baselines_val/` (`rows_*.pkl`; final: `summary_cap.md`, `rows_scored_cap.parquet`;
earlier: `summary.md`, `rows_scored.parquet`).

## Checks
| Check | Result |
|---|---|
| R3 (3 seeds × 560): QPs, bits, score vs stored | identical |
| final4 (5 k × 560): bits vs stored | identical 2,800/2,800 |
| final4 PSNR vs stored, stored curves | **27/2,800 differ**: two cut GOPs (`MusicVideo_360P-5f07@30`, `@180`) |
| final4 vs stored with Aayush's capped final4 PSNR (`cap_fix_x264.pkl`) | identical 2,800/2,800 (bits, PSNR, score) |
| Every number in the table below vs the team's capped `report_val_cap.md` | match (final4 at all k, R3, ABR, both encoders; R3 − final4 overall, per seed, per class) |

**PSNR-cap finding:** the stored final4 rows (`p2_data/scripts/rd_native.py` PSNR) did not cap each plane at 100 dB;
rclib does (every learner's rows). A losslessly coded plane then scores 148.13 dB instead of 100, which moves the GOP
mean by exact steps of 0.2005 dB. Aayush confirmed and adopted one cap everywhere (`p2_data/docs/team-update-2026-11-16.txt`
§7, `p2_data/exp_next/final/cap_fix.py`): val x264 R3 − final4 **+0.077**, cut/gradual **+0.069** (was +0.068 / +0.016).

## Results (final: one PSNR cap everywhere)
| enc | method | source | k | score | Δ vs final4 [clip bootstrap] (paired_ci) |
|---|---|---|---|---|---|
| x264 | final4 | re-run | 0 / 2 / 5 / 10 / 29 | −0.358 / −0.148 / −0.115 / −0.119 / −0.142 | reference |
| x264 | R3 180k (s3–5) | re-run | 5 | −0.038 | **+0.077 [+0.020, +0.143] \*** (± 0.037); stable +0.078 \*, cut+gradual +0.069 |
| x264 | ABR m0.90 | stored | 0 / 5 | −1.518 / −1.253 | −1.160 / −1.138 |
| x264 | CQP best (hindsight) | stored | 29 | −0.299 | −0.158 (± 0.051) |
| x265 | final4 | stored | 0 / 2 / 5 / 10 / 29 | −0.470 / −0.262 / −0.254 / −0.243 / −0.237 | reference |
| x265 | R3 180k (s3–5) | stored | 5 | −0.045 | **+0.209 [+0.093, +0.346] \*** (± 0.062); stable +0.224 \*, cut+gradual +0.126 |
| x265 | ABR m0.93 | stored | 0 / 5 | −1.395 / −1.010 | −0.925 / −0.756 |
| x265 | CQP best (hindsight) | stored | 29 | −0.304 | −0.067 (± 0.063) |

Score in dB (dPSNR_B − 0.17 dB per 1 % over); every plane's PSNR capped at 100 dB, including the constant-QP curves and
final4's stored rows (Aayush's `cap_fix_<enc>.pkl`); ABR rows are not re-measured (uncapped, at most 1 GOP × 4 levels
per k), as in the team's capped report. Level-24 hole excluded (n = 548 x264, 550 x265). With the capped curves x264's
differences are unchanged and absolute scores move by ≤ 0.007; on x265 final4's own PSNR is also re-measured, so
R3 − final4 moves from +0.204 to +0.209. Full table (all k, CQP causal estimate, class splits):
`results/baselines_val/summary_cap.md`.
