# 03 · R3 and BC across lookahead (2026-11-16)

**Question:** how much lookahead does R3 (PPO nudging final4, started from an imitation (BC) network) need? Live
encoding (small k) vs on-demand (large k). And at each k, how much comes from the BC start vs from PPO?

## What was run (x264, val, shim backend)
| k | seeds | BC network | Notes |
|---|---|---|---|
| 0 | 3, 4, 5 | new, trained on Aayush's k0 data | |
| 2 | 3 | new (new k2 data + shift) | |
| 5 | 3, 4, 5 | Aayush's | reruns of his runs, for the 20k BC checkpoint + a reproduction check |
| 10 | 3 | new (new k10 data + shift) | |
| 29 | 3, 4, 5 | new (new k29 data + shift) | |

Recipe = Aayush's stored R3 run: `rl.py --method res`, λ 0.17, f4 features, o[2] dropped, res-mean pooled, bit cap,
BC actor, 20k critic-only warm-up, 180k steps; 14 envs on 16 cores. Checkpoints at 20k (= the BC start: the actor is
frozen during the warm-up), 60k, 120k; all evaluated on val (560 episodes).

## Files
| File | What |
|---|---|
| `env.sh` | shared environment (modules, Aayush's `rc` env, rclib variables); sourced by every job |
| `bc_data_build.py` | P1 copy of P2's `build.py`: BC dataset at any k (no encodes); changes marked "P1 copy" |
| `bc_shift_fit.py` | smooth pooled mean shift at a new k (P2's `shift_smooth.py` fit), merged into a shifts file |
| `bc_data_compare.py` | checks a rebuilt dataset equals Aayush's as a set of rows |
| `job1_prep_k29.sbatch` | batch 1: data + shift for k29 (with k5 checks); ~10 min |
| `job2_bc_k29_k0_seed3.sbatch` | batch 1: BC k29 then k0, seed 3, one after the other |
| `job4_bc_k0_k29_seeds45.sbatch` | batch 2: BC k29 and k0, seeds 4, 5 |
| `job5_prep_bc_k2_k10.sbatch` | batch 2: data + shifts for k2, k10 (with k5 checks), BC seed 3 |
| `train_r3.sbatch` | one `rl.py` run per array task (also used by 04) |
| `runs_*.txt` | run lists: line i = array task i−1 |
| `submit_*.sh` | queue the jobs with their dependencies |
| `check_k5_r3_weights.py` | k5 reruns vs Aayush's models (weights) |
| `score_lookahead_batch1.py`, `score_lookahead_all.py` | scoring vs final4 at the same k |

## How to rerun, in order
1. **Batch 1.** `bash submit_batch1.sh`: job 1 (k29 data + shift, k5 checks) → job 2 (BC k29 and k0 seed 3, one after
   the other, ~6 min each) → R3 array (k5, k0, k29 seed 3). As first run, job 1 also trained both BC networks at once
   and timed out (job 14304096); that step now lives only in job 2. If job 1 already ran: `submit_batch1_bc_then_r3.sh`.
2. **Batch 2.** `bash submit_batch2.sh`: chain A = job 4 → R3 array (k0, k29, k5 × seeds 4, 5); chain B = job 5 → R3
   array (k2, k10 seed 3, with the shifts file that has k2/k10). The chains run side by side.
3. **Checks and scoring** (compute node or login node, seconds):
   ```bash
   /scratch1/aayushso/envs/rc/bin/python -I check_k5_r3_weights.py /scratch1/ahhanagu/ee599/results/r3_kcurve/weights_check.txt 3
   /scratch1/aayushso/envs/rc/bin/python -I check_k5_r3_weights.py /scratch1/ahhanagu/ee599/results/r3_kcurve/weights_check_b2.txt 4 5
   /scratch1/aayushso/envs/ee599/bin/python -I score_lookahead_all.py      # needs 02's final4 rows
   ```
Outputs: `/scratch1/ahhanagu/ee599/results/r3_kcurve/` (`exp5/`, `exp5_k2k10/` data and BC networks, `work/results_rl/`
runs, `logs/`, `summary_all.md`, `rows_all.parquet`). Cost as run: ~27 core-hours for batch 2; R3 runs ~4 min each.

## Checks that passed
- Every data chain also rebuilds k5: its shift equals Aayush's (max difference 0.00e+00) and its v2 data equals his row
  for row (3,057,000 rows), else the job stops.
- k5 reruns for seeds 3, 4, 5 are **bit-identical** to Aayush's models (all 12 weight tensors; QPs and scores 560/560).
- Fold protocol: all 8 new BC networks use Aayush's settings (40,000 steps, batch 1,024, lr 3e-4) and the same 5
  hold-out clips; data from the same 101,900 plans over 56 clips; 0 train-select fold clips.

## Results (provisional: scored before Aayush's capped constant-QP curves; differences vs final4 should not change)
| k | seeds | final4 score | BC − final4 | **R3 − final4** | R3 − BC | R3 − final4 stable | R3 − final4 cut+gradual |
|---|---|---|---|---|---|---|---|
| 0 | 3–5 | −0.364 | −0.533 \* | **+0.069 \*** | +0.602 \* | +0.048 | +0.182 |
| 2 | 3 | −0.155 | −0.234 \* | **+0.072 \*** | +0.306 \* | +0.100 \* | −0.080 |
| 5 | 3–5 | −0.122 | −0.155 \* | **+0.077 \*** | +0.231 \* | +0.078 \* | +0.069 |
| 10 | 3 | −0.126 | +0.058 \* | **+0.102 \*** | +0.044 \* | +0.113 \* | +0.044 |
| 29 | 3–5 | −0.149 | +0.057 \* | **+0.097 \*** | +0.041 | +0.088 \* | +0.150 |

dB, val, seeds averaged per episode, paired with final4 at the same k (02's shim re-run, same 100 dB cap), level-24
hole excluded (n = 548); \* = 95 % clip bootstrap excludes 0. Full table with CIs: `results/r3_kcurve/summary_all.md`.

**Reading:** R3 beats final4 by +0.07 to +0.10 dB at every k (k2 and k10 one seed). The BC start alone goes from far
below final4 (k0) to above it (k ≥ 10), and PPO's share shrinks accordingly (+0.60 at k0 → +0.04 at k29). Absolute
quality levels off around k5–k10. The k29 BC network fits held-out data worst but runs best in closed loop.

## Lessons
- Train BC networks **one after the other**: `bc_train.py` sets torch threads = `SLURM_CPUS_PER_TASK`, so two at once
  oversubscribe the cores (~4 vs ~100 steps/s).
- `env.sh` turns off `set -eu` while `/etc/profile` and Lmod load (`lang.sh` reads an unset `LC_ALL`); without this the
  first job died after 2 s with an empty log.
