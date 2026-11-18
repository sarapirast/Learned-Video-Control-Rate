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
| `score_lookahead_batch1.py`, `score_lookahead_all.py` | earlier scoring vs final4 (before the capped curves) |
| `score_final_capped.py` | **final scoring** of 03 and 04 with one PSNR cap everywhere (table below) |

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
   /scratch1/aayushso/envs/ee599/bin/python -I score_lookahead_all.py      # earlier scoring; needs 02's final4 rows
   /scratch1/aayushso/envs/ee599/bin/python -I score_final_capped.py       # final scoring (03 + 04, capped curves)
   ```
Outputs: `/scratch1/ahhanagu/ee599/results/r3_kcurve/` (`exp5/`, `exp5_k2k10/` data and BC networks, `work/results_rl/`
runs, `logs/`, `summary_final.md` + `rows_final.parquet` (final), `summary_all.md` (earlier)). Cost as run: ~27 core-hours for batch 2; R3 runs ~4 min each.

## Checks that passed
- Every data chain also rebuilds k5: its shift equals Aayush's (max difference 0.00e+00) and its v2 data equals his row
  for row (3,057,000 rows), else the job stops.
- k5 reruns for seeds 3, 4, 5 are **bit-identical** to Aayush's models (all 12 weight tensors; QPs and scores 560/560).
- Final scoring: my final4 re-run equals Aayush's re-measured capped final4 (PSNR and bits) on all 40 episodes he
  re-measured; with the capped curves every difference vs final4 is unchanged, only absolute scores moved (≤ 0.007).
- Fold protocol: all 8 new BC networks use Aayush's settings (40,000 steps, batch 1,024, lr 3e-4) and the same 5
  hold-out clips; data from the same 101,900 plans over 56 clips; 0 train-select fold clips.

## Results (final)
| k | seeds R3 / R2c | final4 | BC − final4 | **R3 − final4** | R3 − BC | R2c − final4 | **R3 − R2c** |
|---|---|---|---|---|---|---|---|
| 0 | 3–5 / 3–5 | −0.358 | −0.533 [−0.734, −0.348] \* | **+0.069 [+0.005, +0.138] \*** | +0.602 [+0.440, +0.775] \* | −0.064 [−0.114, −0.015] \* | **+0.133 [+0.086, +0.187] \*** |
| 2 | 3 / – | −0.148 | −0.234 [−0.308, −0.165] \* | **+0.072 [+0.020, +0.128] \*** | +0.306 [+0.225, +0.408] \* | – | – |
| 5 | 3–5 / 0 | −0.115 | −0.155 [−0.314, −0.050] \* | **+0.077 [+0.020, +0.143] \*** | +0.231 [+0.131, +0.374] \* | −0.018 [−0.087, +0.050] | **+0.095 [+0.043, +0.147] \*** |
| 10 | 3 / – | −0.119 | +0.058 [+0.015, +0.099] \* | **+0.102 [+0.040, +0.168] \*** | +0.044 [+0.007, +0.085] \* | – | – |
| 29 | 3–5 / 3–5 | −0.142 | +0.057 [+0.009, +0.103] \* | **+0.097 [+0.039, +0.154] \*** | +0.041 [−0.001, +0.084] | −0.044 [−0.064, −0.021] \* | **+0.141 [+0.090, +0.187] \*** |

| k | R3 − final4 stable | R3 − final4 cut+gradual | R3 − R2c stable | R3 − R2c cut+gradual |
|---|---|---|---|---|
| 0 | +0.048 | +0.182 | +0.139 \* | +0.104 \* |
| 2 | +0.100 \* | −0.080 | – | – |
| 5 | +0.078 \* | +0.069 | +0.105 \* | +0.043 |
| 10 | +0.113 \* | +0.044 | – | – |
| 29 | +0.088 \* | +0.150 | +0.112 \* | +0.300 \* |

dB, x264, val. Score = dPSNR_B − 0.17 dB per 1 % over, with **one PSNR convention everywhere**: each plane capped at
100 dB, including the constant-QP curves (Aayush's `cap_fix_x264.pkl`). Level-24 hole excluded (n = 548 per k); seeds
averaged per episode, then paired with final4 (02's shim re-run) on (GOP, level); [95 % clip bootstrap], \* = excludes 0.
BC = R3's 20k checkpoint (the imitation start), R2c = the same PPO training from the standard start (04). R2c at k5 is
one seed (seed 0, current code); k2 and k10 have one R3 seed and no R2c. Full table, setup-only terms and every class
split: `results/r3_kcurve/summary_final.md` (from `score_final_capped.py`).

**Does "RL adds most at small k" still hold once R2c separates the BC start from the setup changes? Only in a narrow
sense.**
- *R3 − BC* (what PPO adds on top of its imitation start) is indeed largest at small k: +0.60 at k0, +0.04 at k29.
  But at small k most of that is PPO **repairing the BC start**, which drifts badly when it runs on its own
  (BC − final4 = −0.53 at k0).
- *R2c* is the same PPO training without the imitation start. It never beats final4: −0.064 \* at k0, −0.018 at k5,
  −0.044 \* at k29. The setup changes alone (mean shift + bit cap, R2c's 20k checkpoint) cost about −0.02 to −0.03
  (not significant), and PPO from the standard start adds nothing on top (R2c − shift-only: −0.033 \*, +0.003,
  −0.021 \*). So **RL on its own does not help at any k**.
- *R3 − R2c* (the effect of the imitation start, same setup, same PPO) is about the same at every k: +0.133 (k0),
  +0.095 (k5), +0.141 (k29), all significant. On cut+gradual GOPs it is largest with full lookahead (+0.300 \* at k29).
- In simple words: R3's gain over final4 comes from **PPO and the imitation start together**, at every lookahead. At
  small k the imitation start is poor and PPO has to fix it; at large k the start is already good and PPO only polishes
  it. Neither part works alone: PPO without the start loses to final4, and the start without PPO loses badly at small k.
- Absolute quality still levels off around k5–k10 (R3: −0.289 at k0, −0.038 at k5, −0.017 at k10, −0.044 at k29).

## Lessons
- Train BC networks **one after the other**: `bc_train.py` sets torch threads = `SLURM_CPUS_PER_TASK`, so two at once
  oversubscribe the cores (~4 vs ~100 steps/s).
- `env.sh` turns off `set -eu` while `/etc/profile` and Lmod load (`lang.sh` reads an unset `LC_ALL`); without this the
  first job died after 2 s with an empty log.
