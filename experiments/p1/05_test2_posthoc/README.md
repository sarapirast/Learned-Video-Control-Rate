# 05 · R3 at k0 / k29 on test2 (post-hoc for x265)

**Question:** do my R3 models at k0 and k29 (03) hold up on Aayush's second held-out set, test2 (93 unseen UGC clips)?

**Status of each part:**
- **x264:** Aayush already evaluated my x264 k0 / k29 models on test2 as PREREG secondary 10 (`p2_data/exp_next/test2/
  eval_ahhana.py`; R3 − final4 k0 +0.097 [+0.051, +0.149] \*, k29 +0.032 [+0.005, +0.061] \*). Here that evaluation is
  re-run with my scripts as a **parity check** of this code path: every test2 row must equal his stored rows.
- **x265: POST-HOC, NOT PRE-REGISTERED** (agreed with Aayush on 2026-11-19). Run once, only after all x265 seeds 3-5
  are trained and scored on val; every printed line carries this label.
- **BC alone** on test2 = each run's own 20k checkpoint (the BC start R3 began from), not Aayush's BC seeds 0-2.

## Files
| File | What |
|---|---|
| `eval_test2_p1.py` | `eval_ahhana.py` generalised to x264 / x265 and my runs; `--ckpt 20000` = the BC start. Gates: `--split test2` needs this script's own val parity file (all rows equal, same seeds); for x265 also val scores for every seed |
| `score_test2_p1.py` | scores exactly as his `report.py` secondary 10 (test2 infos without flat GOPs, test2 cap_fix curves and final4, cut labels from `data/t2/320x180/gops.csv`, hole excluded, seeds averaged, clip bootstrap); x264: row-level parity with his stored rows and the reported +0.097 / +0.032 |
| `job_test2_eval.sbatch` | runs steps `model:split[:ckpt]` in order (val gate first; a failed gate stops the job) |

## How to run
```bash
# x264 parity (shim, ~10 min)
sbatch --export=ALL,P1_ENC=x264 job_test2_eval.sbatch k0:val k29:val k0:test2 k29:test2
# x265, post-hoc, after all seeds 3-5 are scored on val (CLI, one job per model and checkpoint, ~1.2 h each)
for m in k0 k29; do for c in final 20000; do
  sbatch --export=ALL,P1_ENC=x265 --time=3:00:00 job_test2_eval.sbatch $m:val:$c $m:test2:$c; done; done
# score (Aayush's ee599 env)
/scratch1/aayushso/envs/ee599/bin/python -I score_test2_p1.py --enc x264    # or --enc x265
```
Everything of Aayush's (test2 work dirs `rcwork_t2/<enc>_resh`, infos, cap_fix, final4 rows) is read in place; outputs go
to `/scratch1/ahhanagu/ee599/results/test2_posthoc/`. `P2_DATA` only matters for building infos, so it is not needed
here. x264 uses the shim (identical to the CLI, see 01); x265 uses the CLI, his path exactly.

## Results
Pending: the x264 parity job and the x265 runs.
