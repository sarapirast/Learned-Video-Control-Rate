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
