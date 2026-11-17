# P1 experiments (x264, val only)

Scripts behind P1's results since the shim backend (`RC_BACKEND=shim`, see `P1_README.md`). Code only: results,
logs, datasets and models live outside git under `/scratch1/ahhanagu/ee599/` (paths below). The scripts were run
from those folders and use absolute paths (my scratch, Aayush's read-only inputs in `/scratch1/aayushso/`), so they
are a record of what ran, not a portable package. Python: Aayush's `rc` env (`stable_baselines3`, torch) for
encodes / training, his `ee599` env (pyarrow) for scoring. Test was never used.

## `shimcheck/` (2026-11-16): shim vs x264 CLI inside rclib
`run.py` plays final4 and R3 (k5, seed 3) on 10 val GOPs (5 stable, 5 cut) x 4 levels with either backend; `go.sh`
sets the environment. Result: per-frame QPs, bits, PSNR and score identical on 40/40 episodes for both methods;
12-13x faster (`P1_README.md`). Note: `run.py` imports rclib from the pre-branch sandbox copy
(`/scratch1/ahhanagu/tmp/mainpp`), identical to this branch's `pavneet_pipeline/rclib/codec.py`.

## `baselines_val/`: frame-level baselines re-run on the shim
`run_val.py` + `go.sh`: final4 at k 0/2/5/10/29 and R3 k5 seeds 3-5 (180k) on all 140 val GOPs x 4 levels.
`score.py`: scores them with `rclib.metrics.score` against final4 at the same k (stable vs cut+gradual), adds the
stored constant-QP / ABR rows and all x265 rows, and checks every number against the stored results.
Outputs: `/scratch1/ahhanagu/ee599/results/baselines_val/` (`summary.md`, `rows_scored.parquet`).
Finding: final4's stored rows (P2 `rd_native.psnr`) do not cap PSNR at 100 dB, rclib does (R3's rows); on two cut
GOPs this inflates final4, so the team's x264 R3 - final4 (+0.068) is +0.077 with one convention.

## `r3_kcurve/`: R3 across lookahead (k 0/2/5/10/29) and the R2c control
Recipe = the stored R3 run (`rl.py --method res`, lambda 0.17, f4, drop level, res-mean pooled, 20k critic-only
warm-up, BC actor, 180k steps), 14 envs on 16 cores, shim backend. `env.sh` = modules + rclib variables (all writes to
`/scratch1/ahhanagu/ee599/results/r3_kcurve/`; `work/` links Aayush's `x264_resh` inputs read-only).

| Step | Scripts |
|---|---|
| BC data + shift at a new k (no encodes) | `exp5_build.py` (P1 copy of P2's `build.py`: k from `EXP5_KS`, shift file from `RC_SHIFTS`, ordered rows; changes marked "P1 copy"), `exp5_shift.py` (P2's `shift_smooth.py` fit), `exp5_compare.py` |
| Check before use | every chain rebuilds k5 too: its shift must equal Aayush's and its v2 data must equal his row for row, else the job stops |
| BC networks | P2's `bc_train.py` unchanged; one process at a time (two at once oversubscribe the cores ~20x) |
| Jobs | `prep.sbatch` + `bc.sbatch` (k29, k0 seed 3), `bc2.sbatch` (k0/k29 seeds 4-5), `prep2.sbatch` (k2, k10), `rl.sbatch` (array; args = run list, shift file), `submit*.sh` |
| Run lists | `runs.txt` (k5/k0/k29 s3), `runs_b2a.txt` (k0/k29/k5 s4-5), `runs_b2b.txt` (k2/k10 s3), `runs_r2c.txt` (R2c: k0/k29 s3-5, k5 s0 repro) |
| Scoring | `score_kcurve.py` (batch 1), `score_all.py` (all runs: BC = 20k checkpoint, R3 = final, vs final4 at the same k), `weights_check.py` |

Checks passed: k5 retrains (seeds 3, 4, 5) are bit-identical to Aayush's models; BC networks use his fold protocol
(fitting clips only, same 5 hold-out clips, 0 fold clips). Outputs: `results/r3_kcurve/summary_all.md`,
`rows_all.parquet`. R2c = R3 without `--init-bc` (Aayush's definition, `p2_data/exp_next/exp4/report_r3.py`).
