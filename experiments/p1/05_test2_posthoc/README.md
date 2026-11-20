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
**x264 (parity with Aayush's pre-registered secondary 10):** this script reproduces his stored test2 rows exactly,
10,320/10,320 rows for each model, and the scores match his report: R3 - controller k0 +0.097 \*, k29 +0.032 \*
(n 3,326, 88 clips). The CIs to quote are his (`report_test2.md`: [+0.051, +0.149] and [+0.005, +0.061]); this
re-score draws its own bootstrap and gives [+0.052, +0.146] and [+0.003, +0.062]. Source: `results/test2_posthoc/summary_x264.md`.

**x265 (POST-HOC, NOT PRE-REGISTERED; agreed with Aayush 2026-11-19).** Run once, after all x265 val runs (seeds 3-5)
were final and scored; each model first passed its val parity gate (1,680/1,680 rows). Jobs 14391845-48 (test2 steps;
the first submission 14391564-69 failed at the gate on a parquet read, before any test2 evaluation). BC start = each
run's own 20k checkpoint.

| x265 test2, post-hoc (n 3,320, 88 clips) | k0 | k29 |
|---|---|---|
| R3 - controller | +0.166 [+0.109, +0.228] * | +0.098 [+0.050, +0.145] * |
| BC start - controller | -0.340 [-0.431, -0.242] * | +0.140 [+0.087, +0.193] * |
| R3 - BC start | +0.506 [+0.420, +0.587] * | -0.042 [-0.067, -0.014] * |

Source: `results/test2_posthoc/summary_x265.md` (rows `r3k{0,29}[bc]_test2_x265.pkl`). At k29 the BC start alone beats
the controller and R3 ends slightly below it. The k0 and k29 CIs overlap, so no claim that the edge changes with k.
