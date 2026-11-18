# 04 · R2c control: R3 without the BC start (2026-11-16)

**Question:** how much of R3's gain comes from starting PPO at the BC (imitation) network? R2c is Aayush's matched
control (`p2_data/exp_next/exp4/report_r3.py`): R3's exact setup (mean shift, bit cap, masked o[2], 20k critic-only
warm-up, λ 0.17, 180k steps) but the actor starts from `rl.py`'s standard residual init (P(offset 0) = 0.7) instead of
`--init-bc`. R3 − R2c = the effect of the BC start. Aayush ran R2c only at k5, seeds 0–2.

## What was run (x264, val, shim backend)
| Task | k | seed | Purpose |
|---|---|---|---|
| 0–2 | 0 | 3, 4, 5 | control for live (pairs with 03's R3 k0 seeds 3–5) |
| 3–5 | 29 | 3, 4, 5 | control for on-demand (pairs with 03's R3 k29 seeds 3–5) |
| 6 | 5 | 0 | reproduction check against Aayush's stored R2c k5 seed 0; also R2c's k5 row in the results (1 seed) |

`runs_r2c.txt` = R3's run-list arguments minus `--init-bc`. The 20k checkpoint of an R2c run is the standard-init
actor still frozen: it always picks offset 0, so it equals final4 + mean shift + bit cap (the "shift-only" baseline).

## How to rerun
```bash
bash submit_r2c.sh        # one array of 7 runs via ../03_r3_lookahead/train_r3.sbatch, ~4-6 min each, ~8 core-hours
/scratch1/aayushso/envs/rc/bin/python -I check_r2c_k5_repro.py     # reproduction check (task 6)
```
Diagnosing the failed reproduction check (below), in order:
```bash
P1=/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate/experiments/p1
# 1. retrain Aayush's R3 k5 seed 0 from his 11-14 morning job, with his exact arguments (one ~4 min job)
sbatch --array=0 --job-name=r3k_repro $P1/03_r3_lookahead/train_r3.sbatch $P1/04_r2c_control/runs_r3_k5_s0_repro.txt
/scratch1/aayushso/envs/rc/bin/python -I check_r2c_k5_repro.py res_k5_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s0
# 2. evaluate his STORED models with today's code, no training (~1 min each, compute node)
source ../03_r3_lookahead/env.sh; RC_WORKERS=2 $PY -I reeval_stored_model.py res_k5_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s0
RC_WORKERS=2 $PY -I reeval_stored_model.py res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s3
```
Outputs: `/scratch1/ahhanagu/ee599/results/r3_kcurve/work/results_rl/res_k*_..._meanpooled_wu20k_s*/` (no `bcinit` in
the name), `*_repro_check.txt`, `*_reeval_check.txt`.

## Checks
- All 7 tasks completed (job 14308917, exit 0), each with `eval.pkl` and `eval_ckpt.pkl`.
- **Reproduction check failed** (task 6): my R2c k5 seed 0 differs from Aayush's stored run (weights max |difference|
  0.17; identical QPs on 47/560 val episodes). Recorded arguments and config are identical apart from the checkpoint
  steps (`--save-at`), which did not matter for R3.
- **Cause found (2026-11-18): Aayush's training code changed during 11-14; the environment and evaluation did not.**

  | Test | Result |
  |---|---|
  | Retrain his R3 k5 seed 0 (his 11-14 morning job, 08:32–08:52), his exact arguments (job 14347705) | **different**: weights max \|diff\| 0.067; identical QPs 0/560 |
  | Retrain his R3 k5 seeds 3, 4, 5 (his 11-14 afternoon runs, ~16:00–17:00; done in 03) | **bit-identical** |
  | Evaluate his *stored* morning R3 seed-0 model with today's code (no training) | **identical** QPs and scores 560/560 |
  | Same for his stored afternoon R3 seed-3 model (control) | identical 560/560 |

  In simple words: today's code plays any given model exactly as his 11-14 code did (environment, final4, scoring
  unchanged), but training from the same start no longer reaches the morning models. Both morning runs (R3 and R2c
  seed 0) fail to reproduce, all afternoon runs do; so something in the training path changed between the two jobs.
  His changes of 11-12 to 11-16 were committed together on 11-16 (`repo-pavneet` ca1bd00), so the exact difference is
  not recorded. A different model picks different QPs on every episode, hence 0/560.
- Consequences: my R2c and R3 runs used the same (current) code and recipe, so **R3 − R2c within these runs is a fair
  comparison**. Aayush's stored seed 0–2 runs (R3 and R2c, k5) came from the earlier training code; the team's final
  results use seeds 3–5, which reproduce exactly.

## Results (final, scored together with 03 by `../03_r3_lookahead/score_final_capped.py`)
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

Setup-only terms (R2c's own checkpoints):

| k | shift-only − final4 (R2c at 20k) | R2c − shift-only (what PPO adds from the standard start) | R2c − final4 cut+gradual |
|---|---|---|---|
| 0 | −0.031 [−0.075, +0.019] | −0.033 [−0.059, −0.009] \* | +0.078 |
| 5 | −0.021 [−0.051, +0.010] | +0.003 [−0.048, +0.050] | +0.026 |
| 29 | −0.023 [−0.049, +0.005] | −0.021 [−0.039, −0.004] \* | −0.150 \* |

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
