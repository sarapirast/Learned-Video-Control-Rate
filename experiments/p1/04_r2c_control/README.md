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
Outputs: `/scratch1/ahhanagu/ee599/results/r3_kcurve/work/results_rl/res_k*_..._meanpooled_wu20k_s*/` (no `bcinit` in
the name), `r2c_k5_repro_check.txt`.

## Checks
- All 7 tasks completed (job 14308917, exit 0), each with `eval.pkl` and `eval_ckpt.pkl`.
- **Reproduction check FAILED** (task 6): my R2c k5 seed 0 differs from Aayush's stored run (weights max |difference|
  0.17; identical QPs on 47/560 val episodes). The recorded arguments and config are identical apart from the
  checkpoint steps (`--save-at`), which did not matter for R3. Aayush's run trained on 11-14 at ~08:30; his R3 seed 3
  (reproduced bit-for-bit in 03) at 16:53. His pipeline changes of 11-12 to 11-16 were committed together on 11-16
  (`repo-pavneet` ca1bd00), so the exact code of the morning run is unknown. **Likely cause: a code change on 11-14
  between the two runs (not yet proven).** Test: rerun his R3 k5 seed 0 from the same morning job; if it also differs,
  the cause is the code version, not R2c.
- My R2c and R3 runs used the same code and recipe, so **R3 − R2c within these runs is a fair comparison**; only a
  direct comparison with Aayush's stored R2c k5 numbers is affected.

## Results
Not scored yet: scoring waits for Aayush's PSNR-capped constant-QP curves. Planned: per k, R2c − final4, R3 − R2c
(the BC-start effect) and R2c's 20k checkpoint (shift-only) − final4, split stable vs cut+gradual.
