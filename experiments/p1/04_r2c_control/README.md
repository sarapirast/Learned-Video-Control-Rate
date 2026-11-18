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
| 6 | 5 | 0 | reproduction check against Aayush's stored R2c k5 seed 0 |

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

## Results
Not scored yet: scoring waits for Aayush's PSNR-capped constant-QP curves. Planned: per k, R2c − final4, R3 − R2c
(the BC-start effect) and R2c's 20k checkpoint (shift-only) − final4, split stable vs cut+gradual.
