# Journal

## 2026-10-29
- Found only `REPRODUCE_HPC.md` in `/scratch1/pbanga/ee599`; no code, data or results. User: build everything from scratch, don't fully trust the runbook.
- User approved: ~40 GB public video downloads; full runbook incl. side studies; extended study (lookahead sweep, RL approaches, feature ablations, scene-based dynamic lookahead, scene intelligence).
- Session node: b05-05 (`main`), only 2 CPU / 8 GB -> used for setup and quick tests only; real work goes to sbatch jobs.
- Cluster facts checked: account `rashidin_1753`, QOS `normal` (2000 CPUs, 100 running jobs per user); `oneweek` partition had 22 idle nodes, `main` had 0.
- Started conda env build at `/scratch1/pbanga/envs/rc` (python 3.12, ffmpeg, nasm, torch-cpu, SB3, gymnasium).
- Cloned x265 (tag 4.1 exists) and x264 (`origin/stable`) into `/scratch1/pbanga/src`.
- Verified Xiph derf listing: CIF clips, 720p50 clips, BBB / Elephants Dream / Sintel trailer as y4m(.xz) all available directly.
- Env built: `/scratch1/pbanga/envs/rc` (python 3.12, torch 2.15 cpu, SB3 2.9.2, ffmpeg from conda-forge). Encoders built from source into `/scratch1/pbanga/envs/codecs`: **x265 4.1, x264 0.165.3223** (matches runbook).
- Wrote `tools/fetch_data.sh` (Xiph CIF/720p/1080p, Blender films, UGC 360P ≤10/category -> 320x180 y4m), `tools/job_env.sh`, `tools/fetch.sbatch`; tested on one clip; submitted job 13544960.
- Started core library: `rclib/config.py`, `rclib/codec.py`.
- Wrote `rclib/data.py` (manifest, splits by source, spliced GOPs, GOP cache) and `tools/codec_check.py`. Codec checks found and fixed: x264 qpfile ignored under `--qp` (L3), PSNR-check frame sync, CSV/bitstream bit accounting. **`codec_check.py`: ALL PASS** for x265 4.1 and x264 0.165 on foreman.
- Fetch job done in 21 min: 186 clips / 13 GB (61 Xiph, 4 films, ~121 UGC). Sintel full-film URL was 404 (720p is only zipped); switched to the 1080p mkv streamed through the downscaler.
- Wrote the full code base: `rclib/{config,codec,data,features,metrics,env,search,offrl,policies,mpc,runner}.py`, `experiments/{infos,search,scenes,baselines,rl,analysis,codecs}.py`, `tools/{step,rl_batch}.sbatch`. See `STUDY_PLAN.md`.
- Unit checks on foreman: env replay of the search's best plan reproduces its score exactly; observations rebuilt from logged plans equal the live env's; lookahead modes give the expected windows around a cut; spliced-GOP cuts detected at the right frames.
- Running a `--quick` end-to-end on a 10-clip test work dir (`/scratch1/pbanga/rcwork_test`) on the session node.
- Sintel refetched (21313 frames). **Final data: 187 clips, 14.8 GB at 320x180. Manifest: 2061 GOPs — train 1196, val 386, test 479** (identical for x265 and x264; x264 work dir symlinks the clips).
- Quick search on test dir: STATIC overshoots QP-30 budgets heavily on static-content GOPs (I frame at −6 vs the encoder's CQP I frame at ≈ −3); see L-entry.
- Submitted infos arrays for both encoders (jobs 13545865–13545868).
- Submitted full dependency chains for x265 and x264 (see JOBS.md); ~470 jobs incl. array tasks. First attempt hit the oneweek QOS submit cap and the x265/gcc libstdc++ issue — both fixed.

### RESUME HERE (written 2026-10-29 ~01:25, before the session's 04:00 end)
State: both full chains submitted (JOBS.md). On resume:
1. `bash tools/status.sh` and `sacct -u pbanga -S 2026-10-29T01:20 -X --format=JobID%14,JobName%26,State,Elapsed` — list failures.
2. Check `/scratch1/pbanga/rcwork_test/quick_all.log` (`grep '### rc='`) — the quick test of every stage/method that was running at session end; fix any failing method, then resubmit only failed RL tasks (`sbatch --array=<ids> ... tools/rl_batch.sbatch runs/<list>.txt`; finished runs are skipped automatically because eval.pkl exists).
3. Failed array shards: resubmit the same `tools/step.sbatch` command with `--array=<failed ids>`; cached shard .pkl files are reused.
4. When both `*_reports` jobs are done: read `results/*_report.md` in each work dir's project (reports are written to `ee599/results/` — NOTE both encoders write there; x264 reports overwrite x265 ones with the same name -> see TODO below), then run `experiments/codecs.py`.
(Fixed before any report ran: reports now go to `results/x265/` and `results/x264/`; `codecs_report.md` lands in the folder of the encoder whose env ran it.)
- Fixed before any report job ran: per-encoder report folders `results/x265`, `results/x264` (x264 infos/scenes reports already written were moved there).

## 2026-10-29 (morning)
- Previous session timed out at ~04:00 before the x264 own_rc retry was submitted. Found: x265 chain fully done; x264 194/195 RL runs done, 1 hung, own_rc shards 0–1 failed, reports blocked. Cancelled stuck/blocked jobs and resubmitted (13561131–13561135).

## 2026-10-29 13:10 — both encoders complete
- x264 fix-up jobs all finished by 10:43; codecs_report.md written.
- BUG found: codecs "score common" for x264 own abr / abr+AQ is -1379 / -3e11 — log-bits extrapolation outside x265's QP 18–50 PSNR range explodes. metrics.saving needs clamping (or exclusion) before the common yardstick is reported.
- Done 14:40: codecs extrapolation fixed (D22) + report regenerated; DQN/MPC fixed (D20, D21) and resubmitted; own-RC sanity-checked (LEARNINGS); backup to /home1/pbanga/ee599_backup (code+docs+reports, no caches).

## 2026-10-31
- #1 constraint analysis done (constraint_report.md, both encoders). #2 multi-GOP done (clip_report.md, both encoders): BC→PPO L=2 beats the best constant QP in hindsight (+3.23 x265, +1.86 x264); imitation fails.
- #3 mb runs failed (model exploitation → NaN). Guards added; resubmission awaits approval.
- Fixed the analysis.py grouping bug (LEARNINGS) and regenerated the reports.
- Paper draft: paper/paper.tex → paper/paper.pdf (9 pages, IEEEtran); figures from paper/make_figs.py, built from the reports only.

## 2026-11-02
- Added README.md (what each script does, run order) and .gitignore; published code, tools, run lists, reports, docs and paper to private GitHub repo https://github.com/pbanga-alt/ee599-rl-rate-control (103 files; no data/models/pkl). #3 (mb) still awaiting resubmission approval.
- #3 model-based pre-training resubmitted with mbenv v2 guards (jobs 13682643–48), all COMPLETED (mb 18–26 min, mb_ppo x265 ~14 min / x264 ~5 min). Test score (score / saving / >1% over), k=5: x265 mb 0.61/1.30/7%, mb_ppo 0.96/1.69/7% vs CQL -1.77, CQL->PPO 3.48, Lagrangian 4.95; x264 mb -0.42/1.53/11%, mb_ppo 1.00/2.05/7% vs CQL->PPO 0.43, Lagrangian 4.07. k=0: x265 mb -0.73, mb_ppo 0.69 (CQL->PPO 0.74); x264 mb -0.54, mb_ppo 0.09 (CQL->PPO -1.17). Paper updated (methods item, Table VIII rows, Section VII-F paragraph, discussion, future work, abstract); now 10 pages.
- 2026-11-03: D28 wide-budget study (QP 26/30/34/38/42). Budget QPs configurable (RC_BUDGETS), continuous budget input, experiments/widen.py, budgets.py, reports_wide.py, tools/submit_wide.sh, runs/wide.txt. Debug test 13696608 passed; full chains submitted for both encoders.

## 2026-11-04
- D28 wide-budget runs all COMPLETED (69 RL runs per encoder, rules, reports in results/x265_wide, results/x264_wide). Search gain ~10 at every budget QP 26-42; constrained RL best at every budget, its lead over BC grows as budgets tighten (Lagr-BC k0 x265 +2.3 -> +5.4); lookahead worth more at tight budgets; 5-budget training mainly fixes CQL->PPO overshoot (k0 at QP30/38: x265 0.74 -> 3.42, x264 -1.17 -> 2.31).
- Reviewed Aayush's code/paper review (/scratch1/aayushso/ee599/docs/msg-pavneet-2026-11-03.md): budget-feature leak, oracle base QP, look-ahead scene flags, weak STATIC confirmed; not yet fixed.
- 3-page results report: paper/report3/report.pdf (numbers from extract.py -> data_*.json, figures from figs.py). Milestone report (Word): paper/milestone_x265.docx.
- TA feedback (Submission_Feedback.docx): added related work on Mao et al. 2020 (imitation-learning RC, arXiv:2012.05339) and MuZero RC to paper.tex and the 3-page report; added scene-cut vs stable table and cut-triggered lookahead results to the paper (Sec. "When is future information valuable?"), plus the review's caveats to Threats to validity. Paper now 11 pages.

## 2026-11-04 (cont.) — D29 fair head-to-head results, D30 started
- D29 (multi-GOP streams, no oracle QP, 912 cases, clip/stream cluster CIs). RL BC→PPO vs the encoder's single-pass ABR + cutree/mb-tree: x265 +23.3 score (+2.4 [+1.3, +3.7] saving at L=0; +4.0 at L=2); x264 +13.5 (+1.1 [−0.7, +3.0] saving, n.s. at L=0; +2.7 at L=2). Most of the score gap is overshoot (ABR >1 % over on 34–70 % of streams vs 1–2 % for RL). Non-causal two-pass with the encoder's defaults (AQ + cutree) scores 3.83 (x265) / 3.18 (x264), above the best causal RL (3.23 / 1.87), at 45 % / 22 % over. Both encoders clamp rc-lookahead to keyint (30): the "90-frame" configs equal the 30-frame ones.
- Re-analysis (x265, 2 budgets, clip-level CIs): most claims hold; CQL→PPO − BC at k=5 is n.s. (−0.28); k 2→3 case-level only; k=29 is 1.7 below k=3.
- Causal env: per-frame base QP rejected (±2 for 25 % at k=0); GOP-level rate model accepted (x265 ±2 for 75 %, x264 66 %; 54 % / 46 % of plans kept).
- Milestone report (3–4 pages, partial results): paper/milestone2/milestone_report.docx (tools/milestone2_docx.py).

## 2026-11-05
- Causal x265 RL finished (33/33); x264 running. Interim x265 read-out: RL beats imitation by 5.7–6.1 (clip-level, holds); lookahead gain +0.40 overall, concentrated on spliced GOPs. Reviewed Aayush's P2 update: leak-free clip-level budgets, a learning-free online controller and a k=0 that sees only the I frame. Our causal budget (s × GOP's own spend) and `gop_qhat` (whole-GOP first pass) are not leak-free by that standard.
- New milestone report `paper/milestone3/milestone_report.docx` (built by `tools/milestone3_docx.py`): 3 pages + references and appendix. Held for the final report: causal rerun, five budgets, BC + feedback, cut-triggered lookahead, ensembles. Work-split table is a draft for the team to confirm. Page count is from `tools/docx_pagecheck.py` (XeLaTeX + Carlito proxy), not Word.
- Decision from the user: run the experiments on dataset v1 too, with results kept separate from the current dataset.
- Revised the milestone after an external review (`milestone_feedback_from_claude.docx`). Checked against the data: lookahead saving at cuts is real (+3.2 to +5.7, all seeds), on stable GOPs the score gain is mostly penalty; seed spread reaches 4.5 points and the clip-level CIs average seeds first, so they omit it. Lagrangian's rescaled-budget share is 38–39% against that arm's own search. Figure 1 now shows share of search score with seed ranges. For v1: add a full Lagrangian sweep with more seeds, and Lagrangian on the streams.
- Second review (`feedback2.docx`) applied: leak caveat on the 39–47% headline; Lagrangian's flat curve called uninformative until rerun on leak-free budgets; natural-cut vs splice split restored; encoder two-pass row restored to Table 3; controller no longer called "strong"; proposed success criterion from v1 seed spread (Lagrangian SD 0.11–0.54): at least 1 point, clip-level CI excludes 0, all seeds agree. Feedback rule's gain was tuned on validation (chose 2); on clip-level budgets 0 = best constant QP in hindsight.
- v1 debug on x265 (13754428): port verified (budget/own 1.04, controller −3.12 / −0.30 with no overshoot, prefix property holds, 0.23 s per encode at preset medium), but only 4–5 % of search plans fit ±3 around the controller and the search from STATIC scored badly. Changed: search now starts from the controller's k=29 plan (`info["static"][b]["plan"]`), residual targets outside the range are clipped rather than dropped. Needs a re-test.

### 2026-11-05: v1 debug, anchored search
x264 debug 13754429 COMPLETED in 4:35, all stages rc=0, on the code where search starts from the controller's k=29 plan. Controller k0 -4.20, k5 -1.05 (Aayush -3.94, -0.94), 24 cases, 0% over by more than 1%. Plans inside +-3: 30% (k0), 40% (k5); frames inside 89-90%. Search (quick) 5.14/5.27/6.67/6.4 at levels 24/30/36/42, from a start of -0.95/-4.08/-4.14/-1.91. Quick Lagrangian: score -12.11, saving -4.68, 20.8% over, 46,080 transitions from 8 GOPs; a pipeline check only.
`tools/v1_debug.sbatch` gained optional `RC_TEST` folder prefix. x265 rerun 13757091 uses `rcwork_v1/test2_x265` and `test2_reports/x265`; pre-fix `test_x265` kept untouched for reference, nothing deleted.

### 2026-11-05: learning curve prepared
Added `--train-frac` to `experiments/rl.py`, `runs/learning_curve.txt` (24 runs), `tools/lc_debug.sbatch`, `tools/submit_lc.sh` (D32). Default off, so normal runs are unchanged. Not submitted yet.

### 2026-11-05: x265 v1 debug rerun passed
13757091 COMPLETED 6:25, all stages rc=0, in `rcwork_v1/test2_x265`. Plans inside +-3: 46% (k0), 50% (k5), up from 4-5%; frames 90-91%. Search (quick) 4.47/5.22/2.69/9.04 from a start of -3.48/-3.97/-7.49/-0.71. Quick Lagrangian test -10.79 (was -71.62), 46,080 transitions. Controller matches the first run (-3.12, -0.30).

### 2026-11-05: v1 Stage 1 prepared, not submitted
`tools/submit_v1.sh`, `runs/v1_stage1.txt` (26 runs: `ctrl` at k=0,5 plus BC, CQL→PPO, Lagrangian, PID at k=0,5, 3 seeds), `experiments/v1_report.py` (paired difference against the controller, source-group bootstrap, per-seed differences). `rl.py --method ctrl` is the controller with all residual actions zero. Report ran on the quick folder; its controller-difference columns have not been exercised because no `ctrl` run exists yet.

### 2026-11-05: milestone report edits (user request)
Removed "To our knowledge"; removed v1 and Aayush from Setup (v1 now defined in one sentence next to Table 3, the only place its results appear); added an "Expand the data" bullet to the plan.

### 2026-11-05: milestone report, v1 removed (user request)
All v1 mentions and results removed: Table 3 and its paragraph, shield sentence, v1 wording in Holes, Plan and Appendix B. Plan now says "close the holes" and describes the same steps without naming v1. The v1 experiments themselves continue.

### 2026-11-05: learning curve finished (x265c_lc 13757936, 24/24 COMPLETED)
CQL→PPO, causal x265, five budgets, initial dataset; `results/x265_causal/learning_curve_report.txt`, script `tools/lc_summary.py`. Test score at 12.5/25/50/100% of clips: k0 -1.33/0.65/-0.10/1.03, k5 -0.15/-1.02/0.63/1.42. Saving flat (k0 3.0/2.97/2.57/3.0, k5 3.63/3.07/3.23/3.5); over budget falls (k0 16.5→6.7%, k5 16.8→7.6%). Train-test gap falls from about 4 to under 1. 100% minus 50%: +1.13 [0.68, 1.77], +0.80 [0.15, 1.39] (clip CI, seed-averaged). Not monotonic; 3 seeds with spread up to 4.4 at small shares.

### 2026-11-05: v1 Stage 1, x264 finished
26/26 RL runs and report done (`results/v1/x264/v1_stage1_report.md`). Against the controller (test -3.67 k0, -1.13 k5): CQL→PPO +2.72 / +3.50, Lagrangian +2.66 / +3.24, PID +1.54 / +2.43, BC -10.09 / +2.97. All but BC k0 and PID k0 meet the D31 criterion. Report's controller-difference columns worked. x265 RL still running.

### 2026-11-05: milestone report, no dataset change in the plan (user request)
Removed the "Expand the data" bullet and every mention of a new dataset. Holes sentence now says (1)–(3) and (4) are addressed; hole (5), artificial splices, is stated with no planned fix. feedback3's dataset paragraph was not applied.

### 2026-11-05: v1 Stage 1, x265 finished; Stage 1 complete
26/26 RL runs and report done (`results/v1/x265/v1_stage1_report.md`). Against the controller (test -3.86 k0, -0.38 k5): CQL→PPO +3.66 / +2.02, Lagrangian +3.12 / +2.78, PID +2.55 / +0.92, BC -20.86 / +1.97. CQL→PPO and Lagrangian meet the D31 criterion at both k on both encoders; BC at k=5 only; PID k=5 fails on x265. Stage 2 prepared with Lagrangian (`tools/submit_v1_stage2.sh`, `runs/v1_stage2.txt`), not submitted.

### 2026-11-05: milestone plan rewritten (user request)
Section 4 now has "Remaining work" and "Results held for the final report". Removed the "Fix success criteria first" bullet and hole (6); the 1-point rule is stated inside the rerun bullet. Added the training-clip analysis to the held results.

### 2026-11-05: milestone plan wording (user request)
Removed the 1-point rule from the report; "Results held for the final report" is back to "Further analyses. The final report will also cover...". The rule stays in D31 for internal use.

### 2026-11-05: milestone report, dynamic lookahead added (user request)
New Table 2 and paragraph on cut-triggered lookahead (CQL→PPO, cap 5, original dataset); head-to-head is now Table 3. Scores 3.32 / 1.67 at 0.2 frames; gain over k=0 +2.58 [+1.80, +3.23], +2.84 [+1.98, +3.97]; x264 seeds +5.08, -0.92, +4.36. "Frames seen" excludes the scene detector, which needs its own lookahead, so the delay saving is not yet measured; earlier claim that this reduces delay was too strong.

### 2026-11-10: under-spending check (teammate reported reward ignores unused budget)
Our reward/score has no term for unused budget (score = saving at equal PSNR vs constant QP − 2 × % over). Checked test evals (3 seeds pooled) against oracle STATIC at the same budget level. Causal 5-budget runs: learners spend 78–85% of budget, PSNR 1.0–1.2 dB below STATIC, below STATIC on 78–85% of GOPs (BC: 91–95%, −0.54 dB). Original 2-budget runs: spend 87–96%, −0.27 to −0.58 dB, below STATIC on 61–84%. So the issue applies to us; positive "saving" coexists with lower delivered quality. Script: scratchpad underspend.py (not in repo). No change made; waiting for the teammate's fix to align.

### 2026-11-10: D33 under-budget penalty, v1 Stage 1 rerun started (user request)
Added `metrics.undershoot/under_cost` (RC_UNDER_PENALTY, RC_UNDER_TOL), `under_pct` in env results, spend/budget and PSNR vs controller in `v1_report.py`, `experiments/v1_rescore.py`, `tools/v1u_debug.sbatch`, `tools/submit_v1u.sh`. Debug jobs 13992008 (x265), 13992009 (x264) submitted to debug. Old Stage 1 untouched.
Debug passed (quick subset, pipeline check only): spend/budget ctrl 89.8% / 94.5%, quick Lagrangian 99.8% / 103.5% (+0.29 / +0.23 dB vs controller); controller score under the penalty −4.07 → −9.55 (x265 quick). Full Stage 1 submitted for both encoders (see JOBS).

### 2026-11-10: full project report (user request)
`paper/full_report/full_report.pdf` (15 pages, LaTeX source `full_report.tex`): infrastructure, data, formulation, every experiment family with numbers from the reports, validity work, causal rerun, learning curve, v1 Stage 1, under-spending and D33, comparison with Aayush's dB-metric rerun, documents, bugs, D1–D33, compute (~1,280 allocations, ~9,800 CPU-h, ~870 RL runs), open items. Noted: `codecs_report.md` RL rows predate the 10-31 analysis fix.

### 2026-11-10 — D33 full v1 Stage 1 finished (under-budget penalty on)
- All jobs COMPLETED (x265 13993253–61, x264 13993262–70). Reports: `results/v1u/{x265,x264}/v1_stage1_report.md`.
- Spend rose from the controller's 86–91% to 94–98% for lagr/pid/cql_ppo; PSNR vs controller +0.37 to +0.51 dB (both codecs, k=0 and k=5); diff vs controller +4.2 to +7.6 points, CIs above 0.
- Cost: mean overshoot rose to 10–19% (old v1 Stage 1: 2.5–6.7% for lagr/cql_ppo). The penalty trades unused budget for overshoot; 1 pt/% under vs 2 pt/% over is too weak an over/under asymmetry for these learners, or tolerance needs to be one-sided.
- Scores are not comparable with old v1 scores (the score now includes the under-cost); compare on PSNR and spend.

### 2026-11-11 — D34 stream-level RL: debug passed, baseline strengthened
- Debug 14016963/64 (7 min each): H1 passes — hindsight plan vs margin-tuned rule on val +0.98 dB (x265, rule L=2) / +1.10 (x264); equal split ≈0.5 dB below the rule (H5). Quick learners (1 seed, 1 % of PPO steps): bc_ppo L=2 +0.19 / +0.22 dB vs rule on val, CI > 0; ppo alone ≈ 0.
- The margin-only rule scored below the best constant QP, so it was widened before the full runs: rule tuned on val over margin x rate-model slope (4.5–6.5 QP/doubling) x calibration prior weight (0.5/1/3), 120 settings. At slope 5.5 / weight 1 it reproduces the old rule exactly. Margin-only baselines kept in rcwork_v1/old_stream_debug/.
- A BeeGFS write to rclib/streamenv.py stalled ~20 min (file showed 0 bytes) and then completed; contents verified.

### 2026-11-11 — D34 stream-level RL: full results (first fair RL win)
- Jobs 14028588–93 all COMPLETED (baselines 9 min; 48 learner runs). Reports: `results/v1_stream/{x265,x264}/stream_report_{val,test}.md`.
- Test, vs the val-tuned remaining-budget rule at the same lookahead (dB, 95 % cluster bootstrap, 3 seeds): bc_ppo L=2 +0.213 [+0.152, +0.301] x265, +0.136 [+0.087, +0.201] x264; ppo, bc_ppo_lag at L=0/2 all +0.12 to +0.21 with CIs > 0 on both encoders. BC alone is below the rule (−0.21 to −0.60): imitation fails, the reward-driven PPO stage is what wins.
- H1 pass (hindsight − rule +0.85/+0.93 dB test), H2 pass, H3 pass (gain on mixed streams +0.32/+0.20 vs same-clip +0.08/+0.06), H4 pass (>1 % over: rule 12–13 %, bc_ppo 10–12 %, bc_ppo_lag 5–8 %), H5 pass (equal split −0.43/−0.49 vs rule). Share of the rule→hindsight gap closed: 16–33 %.
- Rule tuning sat at the grid edge (slope 4.5, weight 3); re-tuned on val over slope 2.5–4.5 x weight 1–12 x margin 0.96–1.00 (`tools/stream_rule_wide.py`, run in the interactive allocation, `results_stream/rule_wide.pkl`): optimum now interior (slope 4.0–4.5, weight 3–6), val gain ≤ 0.015 dB, test −0.634/−0.424 (x265 L0/L2) and −0.710/−0.517 (x264) vs −0.627/−0.423 and −0.710/−0.517 before. Conclusions unchanged.
- Limits: per-GOP constant QP from curves (no encodes, no frame-level control on either side); not comparable with P2's per-GOP −0.22 dB; the offline best constant QP still beats every causal method.

### 2026-11-11 — D34 follow-up: gain vs stream variation, gain in bitrate (`tools/stream_analysis.py`)
- Reports: `results/v1_stream/{x265,x264}/stream_variation_test.md`. Variation = std of log2 first-pass bits over the 8 GOPs.
- L=0: gain rises with variation (mixed-stream slope +0.30–0.46 dB per unit, CI > 0); same-clip gain ≈ 0 or negative in every quartile. L=2: gain on same-clip streams is positive in the lowest-variation quartile (ppo +0.083/+0.087 dB, CI > 0 both encoders) and does not grow with variation (slopes ≈ 0).
- At equal variation (quartile 2), mixed streams gain more than same-clip (x265 bc_ppo L2 +0.33 vs +0.11): part of the mixed-stream advantage is not variation; likely the rule's online calibration carrying over between unrelated clips. Same-clip streams never reach the top variation quartile (max ~1.2 vs 2.1).
- Bits the rule needs to match the method's PSNR (L=2, test): x265 +4.2 to +5.1 %, x264 +1.5 to +3.1 %; same-clip only: x265 +1.0 to +2.4 %, x264 +0.3 to +1.9 % (ppo L2 best: +2.4 / +1.9 %). Over penalty not included.

### 2026-11-11/12 — D35 debug (run in the interactive allocation; debug partition nodes all drained)
- First encoder-RC check failed (stream encodes 7–19 % off the v1 curves): it ran without RC_V1=1, so psy was on; v1 curves use psy off (codec.py V1 branch). own_rc_stream_v1.py now asserts RC_V1 and gives the plain and cutree configs psy off. Rerun: stream encode reproduces the v1 curves exactly (bits ≤ 0.05 %, PSNR 0.0000 dB), both encoders.
- Quick numbers (16 cases, not conclusive): x265 single-pass ABR overshoots ~37 % (RL far ahead); vs ABR+VBV RL bc_ppo L2 +0.49 dB; vs non-causal two-pass ≈ equal. x264 ABR+mbtree close to RL; x264 two-pass ahead of RL by ~0.8 dB on these 16.
- Fresh set: 384 GOPs / 12 segments built (shared GOP files in rcwork_fresh/gops). Curves 9 s (x265) / 7 s (x264) per GOP on one core. Timing: encoder RC ~18 s (x265) / ~8 s (x264) per case per core.

### 2026-11-12 — D35 full results (all 16 jobs COMPLETED)
- Reports: `results/v1_stream/{x265,x264}/own_rc_stream_v1_report.md`, `results/fresh_stream/{x265,x264}/fresh_stream_report.md`. Stream-encode check exact on both encoders. Fresh budgets / own CQP-30 bits: median 1.10 (10–90 % 0.6–2.3).
- H9 (encoder RC) PASS: bc_ppo L=2 vs ABR+VBV +0.44 [+0.35, +0.54] dB (x265), +0.17 [+0.09, +0.26] (x264); vs ABR+cutree +2.54 / +0.57; ABR alone and encoder defaults far worse (overshoot 6–15 % mean). Non-causal two-pass: tie on x265 (+0.01 [−0.04, +0.06]), x264 two-pass ahead of RL by 0.27 dB.
- H6 (fresh films, N=8, bc_ppo L=2 vs rule) SPLIT: x265 +0.032 [−0.040, +0.110] FAIL; x264 +0.065 [+0.016, +0.119] PASS. ppo L=2: x265 +0.051 [−0.012, +0.121], x264 +0.071 [+0.025, +0.122].
- H7 PASS: gain does not shrink with length; ppo L=2 grows (x265 +0.05 / +0.12 / +0.16 at N = 8 / 16 / 32, CIs > 0 at 16 and 32; x264 +0.07 / +0.09 / +0.15, all CIs > 0). L=0 learners +0.20 to +0.40 at N = 16/32, mainly because the N=8-tuned rule degrades on long streams (rule L0 −0.50 → −0.81).
- H8 PASS: >1 % over within 1–2 points of the rule; bc_ppo_lag 1–5 %.
- Net: on unseen films the stream gain shrinks to +0.03–0.07 dB at N=8 (≈ the v1 same-clip number), and is clearest for plain PPO on longer streams. 12 segments from 2 films; rule and policies both tuned/trained at N=8.
