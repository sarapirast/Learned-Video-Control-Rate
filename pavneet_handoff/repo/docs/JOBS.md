# SLURM jobs

Account `rashidin_1753`. Estimates are refined after each finished job (actual vs estimate).

| Job ID | Name | Partition | Resources | Submitted | Est. runtime | Actual | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| 13543409 | (interactive Claude session) | main | 2 CPU / 8 GB | 2026-10-29 | – | – | running | setup, builds, quick tests |
| 13544960 | rc_fetch (all downloads + 320x180 conversion) | main | 16 CPU / 32 GB / 12 h | 2026-10-29 | 1.5–3 h (network bound, ~40 GB) | 0:21 h | done | 186 clips, 13 GB; Sintel URL 404 (fixed, refetched in session) |
| 13545865 | x265_infos (array 0-3) | main,oneweek | 4 × 20 CPU / 32 GB / 1 h | 2026-10-29 | ~5–10 min | 1.5 min | FAILED | x265 needs gcc/13.3.0 libstdc++ in jobs (fixed in job_env.sh) |
| 13545866 | x265_infos_gather | main,oneweek | 2 CPU / 16 GB | 2026-10-29 | ~1 min | | cancelled | |
| 13545867 | x264_infos (array 0-3) | main,oneweek | 4 × 20 CPU / 32 GB / 1 h | 2026-10-29 | ~4–8 min | 3.5 min | done | |
| 13545868 | x264_infos_gather | main,oneweek | 2 CPU / 16 GB | 2026-10-29 | ~1 min | <1 min | done | |
| 13546342–54 | first x265 chain attempt | main,oneweek | | 2026-10-29 | | | cancelled | hit oneweek QOS submit limit (50 jobs); resubmitted on main only |

### Full chains (submitted 2026-10-29 ~01:20, `tools/submit_chain.sh`, partition main)

| Stage | x265 job | x264 job | Resources | Est. wall | Depends on |
|---|---|---|---|---|---|
| infos array + gather | 13546384 + 13546385 | 13545867 + 13545868 (done) | 4×20 CPU | ~5 min | – |
| scenes fit / apply | 13546386 / 13546387 | 13546405 / 13546406 | 2 CPU | ~2 min | infos |
| search train (16) + gather | 13546388 + 13546389 | 13546407 + 13546408 | 20 CPU each | 30–60 min | infos |
| search val (6) + gather | 13546390 + 13546391 | 13546409 + 13546410 | 20 CPU each | 20–40 min | infos |
| search test (8) + gather | 13546392 + 13546393 | 13546411 + 13546412 | 20 CPU each | 20–40 min | infos |
| own RC (4) + gather | 13546395 | 13546414 | 20 CPU | 10–20 min | infos |
| static pattern (4) + gather | 13546397 | 13546416 | 20 CPU | 10–20 min | infos |
| rules (val tune + test) | 13546398 | 13546417 | 32 CPU / 48 GB | 1.5–3 h | scenes apply |
| scenes teacher | 13546399 | 13546418 | 2 CPU | ~2 min | search train + scenes |
| RL core (42) | 13546400 | 13546419 | 20 CPU / 60 GB each, ≤25 running | 30–60 min per run | search train + scenes |
| RL methods (90) | 13546401 | 13546420 | same | same | same |
| RL features (30) | 13546402 | 13546421 | same | same | same |
| RL scenes (33) | 13546403 | 13546422 | same | same | same |
| reports (afterany all) | 13546404 | 13546423 | 4 CPU | ~10 min | everything |

Expected total: search done ~1 h after start; RL ~3–5 h per encoder after that (both encoders share the 100-job / 2000-CPU user cap), reports at the end. Whole study ≈ 5–8 h if the queue cooperates.

### Overnight outcome (checked 2026-10-29 10:15)
- **x265: whole chain COMPLETED** (195/195 RL runs, all reports). RL run times: core 35 min mean (max 57), methods 22 (38), features 34 (55), scenes 44 (118).
- **x264:** everything done except: own_rc shards 0–1 FAILED (x264 2-pass at a ~3 kbps budget on a near-black Sintel GOP; fixed in code); rl_core task 4 (cql_ppo k1 s1) **hung** after building its dataset at 03:24 (killed at 10:15 after 6.9 h; siblings ~20 min); reports blocked. x264 RL run times: core 20 min, methods 12, features 20, scenes 23.

| Job ID | Name | Resources | Est. | Status | Notes |
|---|---|---|---|---|---|
| 13561131 | x264_own_rc_retry (array 0-1) | 20 CPU / 32 GB | ~2 min | submitted 10:16 | |
| 13561132 | x264_own_rc_gather | 2 CPU | <1 min | after 13561131 | |
| 13561133 | x264_rl_core_retry (task 4 = cql_ppo k1 s1) | 20 CPU / 60 GB, 2 h cap | ~20 min | submitted | cap so a repeat hang fails fast |
| 13561134 | x264_reports | 4 CPU | ~10 min | after 13561132, 13561133 | |
| 13561135 | codecs (x265 vs x264) | 4 CPU | ~5 min | after 13561134 | writes results/x265/codecs_report.md |

## 2026-10-29 fix-up round — all COMPLETED
| job | what | actual |
|---|---|---|
| 13561131_[0-1] | x264 own_rc retry | 1 min each |
| 13561132 | own_rc gather | 5 s |
| 13561133_4 | x264 rl_core cql_ppo k1 s1 rerun (no hang this time) | 22.8 min |
| 13561134 | x264 reports | 1.2 min |
| 13561135 | codecs report -> results/x265/codecs_report.md | 22 s |
Nothing queued after 10:43. Both pipelines complete.

## 2026-10-29 14:35 — DQN/MPC v2 reruns (D20, D21)
| job | what | est. |
|---|---|---|
| 13577154 [0-17] | x265 rl_fix (runs/fix_dqn_mpc.txt: 9 DQN + 9 MPC) | DQN ~25 min, MPC ~20 min (5-margin val sweep) |
| 13577156 [0-17] | x264 rl_fix | same |
| 13577155 / 13577157 | x265 / x264 reports (afterany) | ~2 min |
| 13577158 | codecs report (afterany both reports) | <1 min |
ETA all done ≈ 15:15 if nodes are free.

## 2026-10-29 15:30 — extensions (D23, runs/extend.txt, 28 per encoder)
| job | what | est. |
|---|---|---|
| 13582182 [0-27] | x265 rl_extend | 20–40 min each (fb/sum ~1.5x; ensemble ~5 min) |
| 13582185 [0-27] | x264 rl_extend | same |
| 13582183 / 13582186 | breakdown x265 / x264 (after extend + rl_fix) | ~2 min |
| 13582184 / 13582187 | reports x265 / x264 | ~2 min |
| 13582188 | codecs | <1 min |
Queue status 15:39: x265 rl_fix 18/18 running, x264 rl_fix 1/18 running; extend pending (Priority).

## 2026-10-29 16:15 — MPC margin sweep widened to 0.60–1.0 (all x265 v2 runs chose 0.80, the grid edge)
| job | what | est. |
|---|---|---|
| 13585313 [0-8] | x265 MPC v3 (runs/mpc_margin.txt); v2 moved to rcwork/results_rl_v2 | ~15 min each (9-margin val sweep) |
| 13585314 | x264: move MPC v2 dirs to results_rl_v2 after 13577156 ends | seconds |
| 13585315 [0-8] | x264 MPC v3 (afterok 13585314) | ~15 min each |
Breakdown/report jobs 13582183/84/86/87 updated to also wait for these.
| 13587066 [21] | x265 retry of gate lam3 s2 (SIGBUS 135 on d11-41, no output) | ~20 min |
| 13587637 [24] / 13587638 [0] | retries (SIGBUS on d11-41/d11-22); d11-41,d11-22 excluded from all pending jobs | ~20–30 min |

## Phase K: making RL shine (#1 analysis done locally; #2 / #3 submitted 2026-10-31)
| job | what | est. |
|---|---|---|
| 13631975 [0-5] / 13631990 [0-5] | x265 / x264 `mb` (runs/mb.txt) | ~30–45 min each |
| 13631976 [0-5] / 13631991 [0-5] | x265 / x264 `mb_ppo` (aftercorr on mb) | ~25–35 min each |
| 13631987 / 13631992 | x265 / x264 breakdown rerun (after mb_ppo) | ~2 min |
| 13631988 [0-17] / 13631993 [0-17] | x265 / x264 multi-GOP runs (runs/clip.txt) | ~10–30 min each |
| 13631989 / 13631994 | x265 / x264 clip report (computes rule/hindsight baselines) | ~5–10 min |
Earlier: x264 retry 13618352 [1,12] completed (28:53, 20:13); x264 breakdown/reports/codecs 13582186/87/88 completed.

## 2026-11-02 — #3 model-based resubmitted (mbenv v2 guards); stuck 13631976/87/91/92 cancelled
| job | what | est. |
|---|---|---|
| 13682643 [0-5] / 13682646 [0-5] | x265 / x264 `mb` (runs/mb.txt) | ~30–45 min each |
| 13682644 [0-5] / 13682647 [0-5] | x265 / x264 `mb_ppo` (aftercorr) | ~25–35 min each |
| 13682645 / 13682648 | x265 / x264 breakdown (afterany) | ~2 min |
All COMPLETED 2026-11-02 ~17:49 (mb 18–26 min, mb_ppo 13–15 min x265 / 5–6 min x264, breakdown <1 min).

## 2026-11-03 — D28 wide-budget study (tools/submit_wide.sh; debug test 13696608 passed)
| stage | x265 | x264 | resources | est. |
|---|---|---|---|---|
| prep / infos (8) / gather | 13696849 / 50 / 51 | 13696864 / 65 / 66 | 20 CPU | ~10 min |
| search train (16) + gather | 13696852 + 53 | 13696867 + 68 | 20 CPU / 32 G; gather 96 G | ~45 min |
| search val (6) + gather | 13696854 + 55 | 13696869 + 70 | | ~40 min |
| search test (8) + gather | 13696856 + 57 | 13696871 + 72 | | ~40 min |
| spend / own_rc (4)+gather / rules | 13696858 / 60 / 61 | 13696873 / 75 / 76 | rules 64 CPU / 96 G | rules 2–5 h |
| RL (runs/wide.txt, 69, ≤25 running) | 13696862 | 13696877 | 20 CPU / 100 G | 30–40 min each, ~2 h |
| reports_wide (afterany) | 13696863 | 13696878 | 4 CPU / 64 G | ~10 min |
| 13697483 [0] | x265 search train shard 0 rerun (13696852_0 SIGBUS 135 on d11-42; d11-42 now excluded on all pending jobs; gather 13696853 -> afterany:13696852,afterok:13697483) | 20 CPU | ~45 min |
| 13697493 [1,3,6,8,10] / 13697494 [2] / 13697495 [4,5] / 13697496 [2] | reruns of x265 train / val / test and x264 train shards (SIGBUS on xeon-4116 nodes); all pending jobs moved to --constraint=epyc-7513|epyc-7542; gathers rewired to afterany:orig + afterok:rerun | 20 CPU | ~45 min |
| 13697516 [10] | x264 train shard 10 rerun (13696867_10 SIGBUS on xeon-4116) | 20 CPU | ~45 min |
| 13697573 [5,11,14] / 13697574 [14,15] / 13697575 [0] | x265 train / x264 train / x264 val: Xeon-node tasks cancelled or failed, rerun on EPYC; no task left on xeon-4116 |  | ~45 min |

## 2026-11-04 — D29 fair head-to-head, D30 validity fixes (tools/submit_d30.sh)
Debug tests: 13726162/63 (own_rc_stream quick, passed), 13726780 (re-analysis + BC+fb quick passed; smoke OOM, fixed), 13727235 (per-frame base QP: rejected), 13727480 (GOP-level base QP: passed).
| job | what | est. |
|---|---|---|
| 13729080 / 13729081 | x265 / x264 own RC on multi-GOP streams (D29), 912 cases × 6 configs | ~20–40 min |
| 13729082-83 / 85-86 / 88-89 / 91-92 | BC + feedback k=0,5: x265_2 / x264_2 / x265_5 / x264_5 | 30 min – 2 h |
| 13729084 / 87 / 90 / 93 | re-analysis (afterany BC+fb) per run | ~5 min |
| x265 causal: 13729094 prep, 95 spend, 96+97 own_rc, 98 rules, 99 RL (33), 100/101 BC+fb, 102 breakdown, 103 re-analysis | D30 causal rerun, rcwork_wide_causal | rules 2–5 h; RL ~2–3 h |
| x264 causal: 13729104 prep, 105 spend, 106+107 own_rc, 108 rules, 109 RL (33), 110/111 BC+fb, 112 breakdown, 113 re-analysis | D30 causal rerun, rcwork_x264_wide_causal | same |
13729093 (x264_5 re-analysis) FAILED 2026-11-04: KeyError 26 when reading the 2-budget work dir with 5 budget QPs; fixed in breakdown.collect; needs resubmitting. Causal RL/rules still queued at 18:09 (reason Priority, group fairshare low, no start estimate).

**Status 2026-11-05 10:21 PST (D30 causal rerun).** x265c_rl 13729099: 32/33 done, task 32 (`pid k=5 s2`) running; tasks took 0.65 h on average (max 0.88 h, peak RSS 34 GB of the 100 GB asked for) but ran about 2.5 per hour because of queue limits, so 13 h in all. x264c_rl 13729109: 1/33 done, 4 running. Rules 13729098 and 13729108 still pending, Slurm estimate 2026-11-06 14:30; breakdown and re-analysis wait on them. 13729089 and 13729090 completed. `bc_fb2` on the four original work dirs and the x264 five-budget re-analysis (failed 13729093) are not submitted.

**2026-11-05 `bc_fb2` batch (approved; `tools/submit_d30.sh bc_fb2`).** BC + remaining-budget feedback on the four original work dirs, then re-analysis: x265_2 13752267/68 → 13752269; x264_2 13752270/71 → 13752272; x265_5 13752273/74 → 13752275; x264_5 13752276/77 → 13752278 (replaces failed 13729093).

**2026-11-05 D31 v1 port ready, not submitted.** `rclib/controller.py`, `experiments/v1_prep.py`, `tools/v1_smoke.py`, `tools/v1_debug.sbatch`; all changes to shared code are behind `RC_V1` (off by default), so the pending causal jobs are unaffected. Next: the debug job on each encoder, on approval.

- 13754429 v1_debug_x264: COMPLETED 4:35 (debug). 13757091 v1_debug_x265 rerun on anchored search: submitted 2026-11-05, work dir `/scratch1/pbanga/rcwork_v1/test2_x265`.

- lc_debug 13757920: COMPLETED 0:46, train-fraction path works. x265c_lc 13757936: 24-run learning curve array (D32), submitted 2026-11-05, results in `/scratch1/pbanga/rcwork_wide_causal/results_rl_lc`.

- v1 Stage 1 submitted 2026-11-05 (D31):
  - x265 infos / gather / scenes / prep -> 13759290 / 13759291 / 13759292+13759293 / 13759294
  - x265 search train -> 13759295 + gather 13759296
  - x265 search val -> 13759297 + gather 13759298
  - x265 search test -> 13759299 + gather 13759300
  - x265 rl (26 runs) / report -> 13759301 / 13759302
  - x264 infos / gather / scenes / prep -> 13759303 / 13759304 / 13759305+13759306 / 13759307
  - x264 search train -> 13759308 + gather 13759309
  - x264 search val -> 13759310 + gather 13759311
  - x264 search test -> 13759312 + gather 13759313
  - x264 rl (26 runs) / report -> 13759314 / 13759321

## 2026-11-10: D33 debug (under-budget penalty)
- 13992008 v1u_debug_x265, 13992009 v1u_debug_x264 (debug partition, rcwork_v1/testu_<codec>)
- Debug: 13992008 x265 COMPLETED 5:58; 13992009 x264 failed (wrong source dir test2_x264), resubmitted 13992454 COMPLETED 2:57 from test_x264.
- Full v1 Stage 1 with penalty (submit_v1u.sh), x265: rescore 13993253, search 13993254/56/58 (+gathers 55/57/59), rl 13993260 (26), report 13993261.
- x264: rescore 13993262, search 13993263/65/67 (+gathers 64/66/68), rl 13993269 (26), report 13993270.
- 2026-11-10: D33 jobs 13993253–13993270 all COMPLETED.
- 2026-11-11: D34 stream debug: x265 14016963, x264 14016964 (debug, 4 CPU, 50 min).
- 2026-11-11: D34 full stream runs. x265: baselines 14028588, rl 14028589 (24, %8), report 14028590. x264: baselines 14028591, rl 14028592, report 14028593. main, 2 CPU / 8G each.
- 2026-11-11: D35 debug: x265 14034168, x264 14034169 (debug, 8 CPU, 50 min).
- 2026-11-11: D35 debug 14034168/69 cancelled (all debug nodes drained); same steps run in interactive allocation 14028565.
- 2026-11-12: D35 full. x265: ownrc check 14053031, run 14053032 (8), gather 14053033; fresh infos 14053034 (4), gather 14053035, prep 14053036, eval 14053037, report 14053038. x264: 14053039–46 same order.
