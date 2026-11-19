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

### 2026-11-12 — handoff package (user request)
- `/scratch1/pbanga/ee599_handoff/` (+ `ee599_handoff.zip`, 58 MB): README (project, standing rules, environment, history, D34/D35 setup, code map, how to run), RESULTS_AND_INTERPRETATION.md, NEXT_STEPS.md, a copy of the repo without .git, and artifacts (D34 policies + eval, baselines, v1 and fresh curves, D35 results). Train curves and raw video not included.
- Uploaded (user approved, incl. force-adding past Sara's .gitignore) to the public repo sarapirast/Learned-Video-Control-Rate, folder `pavneet_handoff/`, commit eb08445 on main (365 files). Clone used: /scratch1/pbanga/tmp/sara_repo.

### 2026-11-12 — D36 meta-RL prepared and tested (user: "run it")
- New `rclib/metastream.py` (variable-length / playlist streams, length + quality-feedback observations), `experiments/stream_meta.py` (PPO / RecurrentPPO, evaluation on v1 val/test and fresh n = 8/16/32, report vs rule and D34 ppo), `runs/stream_meta.txt` (12 runs), `tools/submit_meta.sh`. D34 code unchanged.
- Quick tests in the interactive allocation (14067045): rppo_fb 40k steps ~1 min incl. evaluation (x265); ppo_fb and rppo on x264 OK; report OK. Quick outputs in `rcwork_v1/<codec>/results_stream_meta_quick` (not results). Estimated 2M-step runs: 30–50 min (LSTM), ~6 min (MLP).

### 2026-11-13 — D36 results (`results/v1_stream_meta/<codec>/meta_report.md`)
- x264 12/12 runs; x265 10/12 (rppo_fb L2 s0 and ppo_fb L2 s1 died at ~7 min, empty logs, rc 135 / cancelled; x265 rows for those two methods are 2-seed means).
- H10 PASS: rppo_fb L2 vs rule, v1 test: x265 +0.161 [+0.117, +0.215], x264 +0.112 [+0.049, +0.160].
- H11 SPLIT: fresh n=8 vs rule: x265 +0.046 [−0.007, +0.107] FAIL, x264 +0.083 [+0.035, +0.133] PASS (same pattern as D34 H6). ppo_fb L2 on x265: +0.061 [+0.010, +0.121] (not the pre-registered method).
- H12 SPLIT: vs D34 ppo L2, fresh n=32: x265 +0.044 [−0.047, +0.136] FAIL, x264 +0.083 [+0.020, +0.150] PASS. All D36 variants are above D34 ppo at n=32 (+0.04 to +0.08) and above the rule by +0.20 to +0.23 (D34 ppo +0.15/+0.16).
- H13 PASS (point estimate): v1 test vs D34 ppo: x265 −0.041, x264 −0.028 (x265 CI [−0.076, −0.015] is below 0: a small real cost at n = 8).
- H14 FAIL at fresh n=32 only (144 cases): >1 % over 9 % vs rule 3 % (x265), 10 % vs 3 % (x264); within 5 pts on every other set.
- Ablations (L=2, score differences, seeds averaged): memory (rppo_fb − ppo_fb) −0.03 to +0.02, feedback (rppo_fb − rppo) −0.01 to +0.04. Neither the LSTM nor quality feedback gives a consistent gain; the effect of D36 comes from variable-length training (helps long streams, costs ~0.03–0.06 dB at n = 8).
- L=0 at n=32: rppo_fb +0.46/+0.48 vs rule and +0.06/+0.10 vs D34 ppo (x264 CI > 0), but the rule is tuned at n = 8, so not claimed.

### 2026-11-13 — user: "do all 3, reruns, direction B, direction A with the message to aayush"
- Reruns of the two dead x265 D36 runs submitted (14188936, report 14188937).
- A (D37): built `rclib/yrd.py`; found our controller port far weaker than final3 (−1.6 vs −0.24 dB per GOP), so A is not run until Aayush allows using final3; message drafted in `docs/MESSAGE_TO_AAYUSH.md`. Found the YUV-vs-luma PSNR scale difference (D34–D36 dB ≈ 3/4 of luma dB).
- B (D38): `rclib/bufenv.py`, `experiments/buffer_rl.py`, `runs/buffer.txt`, `tools/submit_buffer.sh`; pyarrow installed into /scratch1/pbanga/envs/rc to read the v1 per-frame table. Quick tests: buffer-blind rule stalls 4–11 % of the time, vbv rule ~1 %; quick ppo +0.12 vs vbv (60k steps, not a result). Submitted 14190548–53.

### 2026-11-13 — D38 results and D36 x265 reruns
- D36 x265 now 3 seeds everywhere (reruns 14188936 OK). rppo_fb L2: v1 test vs rule +0.160 [+0.119, +0.213]; fresh n=8 +0.042 [−0.012, +0.103] (H11 x265 still FAIL); vs D34 ppo at n=32 +0.066 [−0.011, +0.145] (H12 x265 still FAIL); v1 test vs D34 ppo −0.041 (H13 pass). Conclusions unchanged.
- D38 (`results/v1_buffer/<codec>/buffer_report.md`), ppo L=2 vs tuned vbv rule: v1 test x265 +0.559 [+0.475, +0.678], x264 +0.432 [+0.374, +0.495] (HB1 PASS); test playlists n=16 x265 +0.483 [+0.429, +0.521], x264 +0.436 [+0.378, +0.488] (HB2 PASS); stall % ppo ≤ vbv on every set (x265 test 0.44 vs 0.74, x264 0.68 vs 0.74) (HB3 PASS); vbv > buffer-blind rule +0.40 to +2.6 (HB4 PASS). L=0 similar (+0.40 to +0.73 vs vbv). Gain = more of the channel used (use 79 vs 74 %) with fewer stalls. Best constant QP (offline, buffer-blind) stalls 10–25 % of the time. Caveats: synthetic AR(1) channel, stall weight 0.5 dB/% chosen by us, vbv is our analogue of encoder VBV (not x264/x265 VBV itself), no hindsight ceiling under the buffer.

### 2026-11-13 — D39 submitted (user: "do all 3")
- Real traces: Norway HSDPA site is gone; used the Belgium 4G/LTE logs from the authors' site (users.ugent.be/~jvdrhoof/dataset-4g, 393 KB zip, 40 logs) in /scratch1/pbanga/data/traces/belgium4g; kept throughput only (throughput.pkl). 1-s log-rate change std 1.2 (vs 0.3 synthetic).
- Added vbv2 / mpc baselines, ppo_v2, RC_BUF_* settings, trace channel, fresh-film evaluation; `tools/buf_task.sbatch`, `runs/buffer_sweep*.txt`. Quick tests: vbv2 beats vbv by ~0.37 dB on val (default) — the D38 margin will likely shrink; trace setting: vbv2 / mpc / ppo_v2 all run.
- Submitted x265 14228788–91, x264 14228792–95.

### 2026-11-13 — D39 interim (base tuning done; ppo_v2 running)
- Default setting, L=2, v1 test: vbv2 beats the D38 vbv rule by +0.48 (x265) / +0.50 (x264) dB; mpc ≈ vbv2 (−0.02). The D38 policy (ppo on vbv) vs vbv2: x265 +0.081 [−0.029, +0.241], x264 −0.064 [−0.179, +0.077] — not significant. On n=16 playlists ppo vs vbv2 still +0.255 [+0.138, +0.360] / +0.213 [+0.109, +0.311]; vs mpc +0.167 [+0.082, +0.316] / −0.027 [−0.131, +0.088].
- So most of the D38 margin was a weak baseline. Whether RL on top of vbv2 (ppo_v2) adds anything is what the running jobs test.

### 2026-11-14 — D39 final (all 66 jobs COMPLETED)
- ppo_v2 (PPO on vbv2, L=2, 3 seeds) vs vbv2, default setting: v1 test x265 +0.436 [+0.366, +0.539], x264 +0.347 [+0.262, +0.435]; n=16 playlists +0.576 / +0.576. vs mpc: +0.459 / +0.370 (v1 test).
- Sweep, ppo_v2 vs vbv2 on v1 test (x265 / x264): sigma 0.15 +0.43 / +0.37; sigma 0.5 +0.52 / +0.41; cap 0.5 s +0.62 / +0.55; cap 2 s +0.47 / +0.30; stall weight 0.25 +0.46 / +0.33; weight 1 +0.53 / +0.43; real LTE traces +0.23 [+0.06, +0.44] / +0.41 [+0.26, +0.60]. All CIs > 0.
- Fresh films (6:1:1 YUV): n=16 +0.19 / +0.23, n=32 +0.30 / +0.40 vs vbv2; vs mpc +0.12 / +0.15 (n=16), +0.24 / +0.03 [−0.13, +0.20] (n=32).
- HC1–HC5 all pass. The gain is both quality (ppo_v2 spends ~3 % more of the channel) and fewer stalls (0.61 vs 0.97 % on x265 default).
- Caveats: curve lookups and simulated buffer, not real encodes; mpc is a crude planner (it loses to vbv2 at sigma 0.15 and cap 2 s), so HC2 is weaker evidence than HC1; real traces have deep fades and every method stalls ~2–2.5 %.

### 2026-11-14 — D40 built and debug-tested (real encoder in the loop)
- Why: a real encode of our per-GOP constant-QP decisions equals the curve lookups (closed GOPs; D34 check), so the real gaps are the baseline (encoder's own frame-level RC) and the simulated network. D40 adds E2 (encoder ABR+VBV, channel-blind, target fraction tuned on val) and E3 (encoder ABR+VBV per second, target set by vbv2 or ppo_v2).
- Debug (debug partition; x265 14246288, 14246393; x264 14246459): replay = lookups exactly; lookups = D39 rows exactly after the psi/alpha env fix (ppo_v2 had been trained with the tuned alpha 0.6, vbv2 with 0.5; 4/12 cases differed before the fix). Report code dry-run OK. Timing ~20 s per n=8 case (x265), about half on x264.
- Full run (44 shards per encoder + report) waiting for approval.

### 2026-11-14 — D40 results (real encoder in the loop; all 92 tasks COMPLETED)
- E1 replay: real encodes of vbv2's / ppo_v2's QPs = lookups exactly (96 cases per set, all four reports, both encoders).
- ppo_v2 vs E2 (encoder ABR+VBV whole stream, target 0.9 x channel mean tuned on val): x265 n=8 +0.41 [+0.16, +0.60], n=16 +2.97; x264 n=8 −0.05 [−0.45, +0.22] (tie), n=16 +2.81; traces (f = 0.6, grid edge) +2.83 / +2.46. Untuned E2 (target = channel mean) stalls 3.5–25 % of the time.
- ppo_v2 vs E3 (encoder ABR+VBV per second, target from vbv2): x265 +0.49 / +0.77 / trace +0.64; x264 +1.25 / +1.01 / trace +1.99. All CIs > 0. E3 is weaker than vbv2 with constant QP (enc_vbv2 − vbv2 −0.02 to −1.71): the encoders' 1-s ABR is less RD-efficient than a constant QP per GOP.
- RL as the E3 target setter (enc_ppo_v2 − enc_vbv2): x265 −0.05 / −0.07 / trace −0.81; x264 +0.56 / −0.05 / trace +0.34. The QP-trained policy does not transfer to setting encoder bit targets (it was never trained with the encoder in the loop).
- Caveat: E2's trace tuning picked the lowest grid value (f = 0.6); a wider grid could make E2 stronger on traces.

### 2026-11-14 — D40 E2 caveat closed (trace targets 0.2–0.5; all 20 tasks COMPLETED)
- Trace val now picks f = 0.3 (interior of 0.2–1.0) on both encoders. ppo_v2 vs E2: x265 +2.86 [+2.20, +3.43], x264 +3.09 [+2.09, +3.80]. vs E2 with f picked on test in hindsight (0.4 / 0.5): +2.22 [+1.59, +2.90] / +2.15 [+1.28, +3.14].
- Also added the hindsight E2 everywhere. n=16 playlists: E2 was tuned on n=8 val (f 0.9), but f 0.7 is best at n=16, so the +2.97 / +2.81 overstated it; vs hindsight E2 RL is +1.42 [+1.17, +1.61] / +1.11 [+0.84, +1.37]. n=8 unchanged (0.9 is best on test too): x265 +0.41, x264 −0.05 (tie).
- E2 needs very different targets by setting (0.9 at n=8, 0.7 at n=16, 0.3–0.5 on LTE traces); the rule/RL adapt to the channel online.

## 2026-11-15 — D41 hindsight oracle (headroom check), debug passed
- `experiments/buffer_oracle.py`: per case, knows every GOP's curve and the whole future channel; Lagrangian DP over the binned buffer level + exact local search, seeded with the vbv2 / mpc / ppo_v2 QP sequences (never below them). Exact scorer reproduces stored scores (max diff 1e-14).
- Debug (10–20 cases per set, single clip each, so no real CIs): oracle 0.6–3.0 dB above vbv2; ppo_v2 closes roughly 10–35 % of that gap (one x264 set −5 %).
- Caveat: the oracle also knows future content, not only the future channel, so 100 % is not reachable by a live controller; it is an upper bound, not a target.
- Next: full run (tools/submit_buffer_oracle.sh, 16 shards + report per encoder), awaiting approval.

## 2026-11-15 — D41 oracle full results (36 tasks COMPLETED; x265 14261514/15, x264 14261516/17)
Oracle − vbv2 (dB) and share of that gap ppo_v2 closes (95 % cluster bootstrap):
| setting | x265 oracle gap | x265 RL closes | x264 oracle gap | x264 RL closes |
|---|---|---|---|---|
| sim n=8 | +1.68 | 26 % [23, 29] | +1.92 | 18 % [13, 22] |
| sim n=16 | +1.74 | 33 % [29, 36] | +1.96 | 29 % [26, 32] |
| LTE n=8 | +3.03 | 8 % [2, 14] | +3.55 | 12 % [8, 15] |
| LTE n=16 | +2.69 | 7 % [1, 13] | +3.24 | 8 % [4, 11] |
- Oracle beats every seeded method on 100 % of cases; mpc closes ≤ 12 %, often < 0.
- vbv2's stall penalty is about 30 % (sim) to 35 % (LTE) of the gap; the rest is quality allocation, part of which needs future content and is not reachable live.
- Headroom is largest, and RL's share smallest, on real LTE traces (RL is trained only on the AR(1) channel) → priority: mixed / trace training (idea 2) and oracle imitation (idea 1).

## 2026-11-15 — D42 RL variants built; debug 14261600 (x265) ran all paths
- Correction to an earlier claim: D39 trace ppo_v2 *was* trained on the LTE training traces (runs/buffer_sweep.txt 22–24), with trace-tuned vbv2. The small trace gap closure is not from never seeing traces.
- `experiments/buffer_rl2.py`: ppo_mix (AR(1) rho/sigma randomised + LTE train traces, one policy, per-channel base), ppo_mixh (+ last 8 channel rates), il (DAgger on the D41 oracle, 4 iters x 1000 eps, beta 0.5^k) and il_ppo (critic warm-up + 1M PPO steps at lr 1e-4).
- Debug finding: with offsets +-6 the oracle teacher's QP was clipped on 24 % of labels (median -3, 5th pct -15 vs the vbv2 base), so the student could not follow it. vbv2 is often too conservative for +-6 to reach the best QP; this also limits ppo_v2.
- Added --wide (offsets -24..+6): clipped labels 2.5 %, teacher-followed episodes match the teacher's plan exactly on 32 / 40 (mean gap -0.015 dB). Control: ppo_wide (ppo_v2 with the wide range) so il_w vs ppo_wide separates imitation from range.
- Full plan: 24 runs per encoder (runs/buffer_rl2.txt) + report (D39 buffer report and D41 oracle report regenerated with the new methods).

## 2026-11-15 — D42 results (52 tasks COMPLETED; x265 14261624/25, x264 14261626/27)
Paired vs ppo_v2 (seeds averaged, 95 % cluster bootstrap), test n=8 / test16 n=16:
| | x265 sim | x265 LTE | x264 sim | x264 LTE |
|---|---|---|---|---|
| il_ppo − ppo_v2 | +0.07 [+0.03,+0.11] / +0.08 [+0.02,+0.13] | +0.26 [+0.14,+0.37] / +0.09 [+0.02,+0.18] | +0.10 [+0.06,+0.15] / +0.05 [+0.01,+0.08] | +0.15 [+0.04,+0.24] / +0.14 [+0.06,+0.21] |
- il_ppo (oracle imitation -> PPO fine-tune, same +-6 action space as ppo_v2) beats ppo_v2 in 8 / 8 settings, CI > 0 in all, with ~1.06 M env steps vs ppo_v2's 2 M. Gap to oracle closed: x265 sim 30 % / 38 % (ppo_v2 26 / 33), LTE 16 / 10 (8 / 7); x264 sim 23 / 32 (18 / 29), LTE 16 / 12 (12 / 8).
- Imitation alone (il, il_w) is far worse than vbv2 (−0.7 to −6 dB, stalls 4–18 %): the student matches the teacher on only 25–42 % of training labels because the teacher's choices depend on the future. Useful only as an initialisation.
- Wide action range (−24..+6): no consistent gain (ppo_wide ≈ ppo_v2, worse on x265 LTE n=16 −0.19; il_w_ppo mixed).
- Mixed-channel training (ppo_mix): worse on the simulated channel (−0.06 to −0.14), ≈ ppo_v2 on LTE except x265 n=8 (+0.13). Rate history (ppo_mixh): no consistent effect.

## 2026-11-15 — D43 build + debug (privileged critic, throughput predictor, il_ppo real-encoder check)
- New: `experiments/buffer_rl3.py` (ppo_pc, il_pc, ppo_pred, il_rr), `buffer_real.py --model NAME`, `tools/rl3_task.sbatch`, `tools/rl3_debug.sbatch`, `tools/submit_buffer_rl3.sh`, runs/buffer_rl3{,_debug,_report}.txt, runs/buffer_real_model.txt. `buffer_rl2.py`: make_env2 / evaluate_all / run_il take env extras, a model builder, output names and save=True (defaults unchanged, D42 behaviour identical).
- D42 never saved its models, so il_ppo is re-run (seed 0) as il_ppo_rr with model.zip for the real-encoder check; D42's il_ppo numbers stay as reported.
- Debug (x265, run in the interactive allocation on a01-16, not sbatch; all --quick): all 5 lines rc 0 after one fix (sklearn 1.9 MLPRegressor takes hidden_layer_sizes by keyword only).
  - Privileged critic mask: policy probabilities change by exactly 0 when the privileged inputs are randomised, the value changes (2.0 / 8.1) — before and after training. Saved PCPolicy reloads with PPO.load; actions identical with zero or random privileged inputs (so buffer_real can pad with zeros).
  - Predictor (trace, debug size): val R^2 next-1..4 / min = 0.20 / 0.07 / 0.03 / 0.04 / 0.19, vs last-value −0.05 / −0.38 / −0.56 / −0.62 / −0.34: the last rate is a poor forecast on LTE; a learned forecast is better.
  - buffer_real --model ppo_v2 --limit 2: lookup = ppo_v2 eval rows (0 diff), real replay = lookup.

## 2026-11-15 — D43 results (96 tasks COMPLETED, no failures; x265 14267390–93, x264 14267394–97)
Paired, seeds averaged (il_ppo_rr: 1 seed), 95 % cluster bootstrap, test n=8 / test16 n=16 (* = CI excludes 0):
| | x265 sim | x265 LTE | x264 sim | x264 LTE |
|---|---|---|---|---|
| ppo_pc − ppo_v2 | −0.04* / +0.01 | −0.08 / −0.30* | +0.00 / +0.01 | −0.15* / −0.04 |
| ppo_pred − ppo_v2 | −0.02 / +0.02 | +0.07 / +0.02 | −0.00 / −0.01 | −0.09 / +0.14* |
| il_pc − il_ppo | −0.06* / +0.00 | −0.06 / −0.08 | −0.01 / +0.02* | −0.15* / −0.03 |
| il_ppo_rr − il_ppo | −0.00 / −0.01 | +0.05 / −0.02 | −0.01 / −0.01 | +0.03 / −0.04 |
- Privileged critic: no gain, sometimes worse (ppo_pc and il_pc). A better value estimate does not fix the imitation gap; il_ppo stays the best learner.
- Throughput predictor: better forecasts than last-value (debug R^2) but ≈ ppo_v2 except x264 LTE n=16 (+0.14 [+0.02, +0.29]); one positive of 8, not a consistent gain.
- il_ppo reproduces (il_ppo_rr within noise of the 3-seed il_ppo everywhere).
- Real encoder (il_ppo_rr, buffer_real --model): lookup = eval rows on all 48 shards (0 diff); real constant-QP replay = lookups (0.000 on every set). il_ppo_rr − vbv2 +0.46 to +0.68 (all CI > 0); vs the encoder's own live RC with hindsight-best target: x265 +0.45 (n=8), +1.44 (n=16), +2.39 (LTE); x264 +0.06 [−0.28, +0.29] (n=8, tie as ppo_v2), +1.14 (n=16), +2.52 (LTE). vs ppo_v2 on the real-encoder subset: +0.04 / +0.02 (x265), +0.11* / +0.03 (x264), LTE +0.17 / +0.37*.
- Reports: results/v1_buffer/<codec>/{,trace/}buffer_report.md, .../oracle/oracle_report.md, results/v1_buffer/<codec>/{real,trace/real}/real_report.md. Paired table above from a scratchpad script (seeds averaged, S.cboot).
- 2026-11-15: Pushed (user: "push the new stuff to the sara repo") live-stream work D36–D43 to the public repo sarapirast/Learned-Video-Control-Rate, folder pavneet_handoff/ (repo/ copy updated, README update note), commit 3bbe360 on main (82 files). Clone fast-forwarded to Sara's P4 merge 72e0b1d first. Excluded docs/MESSAGE_TO_AAYUSH.md (private draft); no models or traces.
- 2026-11-15: Pushed the live-stream replication package (user: "upload the data set for the live stream and anything needed to replicate the results too to the sara repo"; confirmed Aayush agrees to v1 being public; traces as throughput-only + rebuild script) to sarapirast/Learned-Video-Control-Rate, pavneet_handoff/live_stream_artifacts/ (398 MB, 509 files), commit 52b7c8a on main, rebased onto Sara's P4 merge 534b0da (no overlap). Contents: v1 frames.pkl + budgets.csv, Belgium 4G throughput.pkl, all results_buffer* (eval.pkl, model.zip, baselines, oracle, real) for both encoders, README with replication steps. Check: all reports rebuilt byte-identically from the uploaded files alone (original data paths disabled). New tools/prep_belgium4g.py rebuilds throughput.pkl from logs_all.zip (max diff 1e-8).
- 2026-11-15: Video upload (user: "upload the raw video too and the video we tested it on"; chose shareable-only + links, GitHub Release). Release pavneet-live-stream-video on sarapirast/Learned-Video-Control-Rate (target 926ec76): v1_clips_blender_sita (34 clips), v1_clips_youtube_ugc (42), v1_clips_uvg (7), fresh_test_films_gops_320x180 (384 GOPs), SHA256SUMS; ~1.0 GB xz, sizes verified after upload; 3 clips round-tripped = manifest MD5. Not re-hosted: 20 Xiph NTIA/SVT/LDV clips (research-only / no licence) and the 6 splices containing them (VIDEO.md has rebuild steps with p2_data scripts; rebuild not tested by us). Commit 926ec76 adds live_stream_artifacts/VIDEO.md + v1 manifest, spliced pieces, clip candidates, UGC credits. gh = module gcc/13.3.0 gh/2.43.1 (already logged in). Staging copy: /scratch1/pbanga/tmp/video_release.

### 2026-11-17 — TA milestone feedback (13/15): analysis, no new runs yet
- Feedback: (M) budgets and base QP from full-GOP encodes leak the future; use decision-time budgets and initialisation. (R) report quality and budget violations separately; count the scene detector's lookahead in the latency claim. (P) finish causal reruns and matched encoder comparisons before adding algorithms. (F) keep assumptions next to headline tables.
- New `experiments/quality_violations.py` (no encodes): dPSNR_B (quality at the budget, no penalty), saving, spend, unused, >1 % over, mean / p95 over, paired clip-cluster CIs vs k = 0 and vs the feedback rule; dynamic-lookahead table with the detector's reads counted. Reports `results/<codec>[_causal]/quality_violations.md`.
- Milestone x265: every learner is below the feedback rule on dPSNR_B (−0.3 to −1.5 dB) and far below it on >1 % over (rule 63 %, Lagrangian 1 %); learners leave 5–25 % of the budget unused (Lagrangian 13–16 %). CQL→PPO k = 5 vs k = 0: dPSNR_B −0.02 [−0.06, +0.03], >1 % over −7 pts. Lookahead bought reliability, not quality.
- Detector delay: a causal detector for a cap-K trigger must read min(K, frames left) ahead at every step (+2 for flashes): cut_trig:5 = 4.5 (6.1) frames, same as fixed k = 5 (4.5), not 0.2. In the milestone runs the flags were from the whole GOP.
- D30 "causal" rerun is only partly causal: budget = s × the GOP's own constant-QP bits (s hidden, ±18 %), and gop_qhat (rclib/env.py:105) uses the whole GOP's first pass, i.e. 29 frames of lookahead for the base QP even at k = 0.
- Content-independent ladder check (train median constant-QP bits at QP 26–42): feasible (QP 18–50 can hit it) for 79 / 90 / 96 / 98 / 98 % of x265 test GOPs (x264 78–97 %); oracle QP p10–p90 spans ~16 QP, so the budget no longer reveals the GOP's cost.
- quality_violations.py: the reference budget is clamped to the measured QP 18–50 curve (1 x264 causal case was outside and extrapolated to −9e5 dB). All four reports rebuilt: results/{x265,x264,x265_causal,x264_causal}/quality_violations.md.
- Same picture in all four settings: every learner is 0.3–1.2 dB below the feedback rule on dPSNR_B and 30–80 points lower on >1 % over; learners leave 6–23 % of the budget unused (causal: 18–23 %). Lookahead k 0→5 on dPSNR_B: CQL→PPO −0.02 / +0.07 (milestone x265 / x264), +0.02 / +0.04 (causal); Lagrangian +0.19 / +0.35 and +0.02 / +0.13; PID +0.01 / +0.21 and +0.31 / +0.22. own 2pass +AQ ties or beats the rule on dPSNR_B on x265 at 57–58 % over.
- Live-stream note: rclib/bufenv.py sets the channel mean to B / n with B = s × the v1 budgets of the stream's GOPs, so the live task carries a milder form of the same leak (the controller knows the content-derived mean rate).
- 2026-11-17: user asked to upload the milestone report (Word) to Sara's repo: paper/milestone3/milestone_report.docx -> pavneet_handoff/milestone_report.docx, README note; commit b267c9e pushed.
- 2026-11-17 decision: build on P2's v1 results (D44 not run). Reviewed Sara's repo at 849c0c0: P2 final write-up (R3 on final4 beats final4 on test, +0.07 / +0.16 dB; vs encoder ABR+VBV +1.05 / +0.71) and team update with 5 checks on our live-stream work.
- Check 4 done (no runs): `tools/buffer_split.py` -> `results/v1_buffer/split_by_stream_type.md`. il_ppo - vbv2 on same-clip test streams: +0.34 / +0.35 (AR(1), x265 / x264), +0.33 / +0.47 (LTE), all CI > 0; mixed streams larger (+0.53 to +0.64). ppo_v2 - vbv2 on same-clip LTE x265 +0.03 n.s. (the one weak cell).
- Checks 1-2 prepared: `buffer_rl.py --baselines2-wide` (coordinate search over wider vbv2 grids from the D39 optimum + wider mpc gamma x H grid, val; RL unchanged), `runs/buffer_wide.txt`, `tools/submit_buffer_wide.sh`, `tools/buffer_wide_report.py`. Quick smoke test on x265 passed (2.5 min). Not submitted yet.
- 2026-11-17: submitted widened retune (user: yes): x265 14321358, x264 14321366 (8 settings each, 4 at a time, 2 CPU, 2 h limit).
- 2026-11-17 D45 leak-fixed live stream: debug 14322445 passed (il step needed RC_V1=1 in the debug script; rerun in the interactive allocation passed; rl2_task.sbatch sets it for the full run). Full run submitted (user: yes): x265 base 14322584 / wide 85 / ppo_v2 86 / il 87 / report 88; x264 base 14322589 / wide 90 / ppo_v2 91 / il 92 / report 93.
- 2026-11-17 widened vbv2 / mpc retune (14321358, 14321366): all 16 tasks COMPLETED (16-36 min). Report `results/v1_buffer/baselines_wide_report.md` (tools/buffer_wide_report.py). Val gain of the retune <= +0.13 dB (largest x265 trace +0.13, cap2 +0.11 / +0.08). RL unchanged still beats the retuned vbv2 in all 8 settings x 2 codecs overall (ppo_v2 +0.23 to +0.58; il_ppo +0.38 to +0.56 where run), CI > 0. Same-clip streams: CI > 0 everywhere except ppo_v2 x265 LTE (+0.10 n.s.) and ppo_v2 x264 lam0.25 (+0.04 n.s.); il_ppo same-clip +0.23 to +0.47, all CI > 0. Edges still hit: alpha = 1.0 (natural bound of the EMA weight), mpc H = 1 (natural bound), mpc gamma = 0.0003 (lowest tried; mpc's val score already at or below vbv2's, i.e. mpc tends towards vbv2).
- 2026-11-17 D45 finished (52 tasks COMPLETED). BUG (mine): experiments/buffer_rl2.py chose folders by channel only (DIRS), ignoring the ladder tag, so the 12 D45 il tasks (a) trained on the LEAKY setting's tuned rule/vbv2 parameters (tuned(ch)), in the ladder env, and (b) wrote over D42's il_L2_s* / il_ppo_L2_s* eval.pkl in results_buffer{,_trace} (both codecs, 24 files, 17:05). Repair: the 24 overwritten files copied (cp -n, cmp-checked) to rcwork_v1/<codec>/results_buffer{,_trace}_ladder/<run>/eval.pkl (D45-il-v1, invalid: wrong base tuning); D42 originals restored from the 11-15 handoff (pavneet_handoff/live_stream_artifacts, cmp-identical); D42 il_ppo - vbv2 wide re-checked: +0.463 / +0.379 as before. DIRS now includes the ladder tag. D45 il needs a rerun.
- D45 ppo_v2 (clean; baselines tuned in the ladder setting), ppo_v2 - vbv2 wide, test: AR(1) x265 +0.43* (same-clip +0.09 n.s., mixed +0.71*, n=16 +0.36*), x264 +0.27* (same-clip +0.15 n.s., mixed +0.37*, n=16 +0.42*); LTE x265 +0.19* (same-clip +0.00, mixed +0.34*, n=16 +0.16*), x264 +0.13 n.s. (vs the D39 grid +0.30*). Leaky setting for comparison: same-clip +0.18* / +0.14* (AR(1)), +0.10 / +0.25* (LTE). Removing the leak leaves ppo_v2's overall gain but its same-clip gain is no longer significant.

## 2026-11-18 — Leak audit across the team repo; D46 framing; D45 il rerun
- Audited main / p2-data-v1 / sara-p4 / p1. Per-GOP v1 (P2) and all stream-level work use clip-level budgets; the live stream fixed to the ladder (D45). User chose to frame the clip-level budget as the two-pass (VOD) setting (D46) instead of a ladder rerun of R3. Draft text in docs/FINAL_REPORT_BUDGET_FRAMING.md.
- D45 il rerun submitted with the fixed DIRS: x265 14346012 (+report 14346013), x264 14346014 (+report 14346015).
- D45 il rerun done (all 16 tasks COMPLETED, ~17 min). results/v1_buffer/baselines_wide_report.md regenerated (replaces the 11-17 version whose ladder il rows were invalid). Leak-fixed il_ppo - vbv2 wide (test; overall / same-clip / mixed / 16-GOP): AR(1) x265 +0.66* / +0.19 [-0.001, +0.67] / +1.03* / +0.48*; AR(1) x264 +0.45* / +0.23* / +0.63* / +0.50*; LTE x265 +0.34* / +0.12* / +0.51* / +0.28*; LTE x264 +0.25* / +0.24* / +0.25 n.s. / +0.26*. il_ppo keeps a significant same-clip gain in 3 of 4 cells (ppo_v2 lost it in all 4).
- 11-18 recheck of the team repo (all branches fetched; the clone had tracked only main). New: Ahhana's p1-fast-backend (11-18): x264 shim backend (identical, ~13x faster); R3 across lookahead k 0/2/5/10/29 on val (R3 - final4 +0.07 to +0.10* at every k; R2c = PPO without the BC start never beats final4; BC start + PPO together make the gain); one PSNR cap everywhere. No new commits on main / p2-data-v1 / sara-p4 since 11-17.
- Remaining gap vs TA item 4 (matched encoder comparison): the live-stream real-encoder checks (D40 E2 encoder ABR+VBV, D43 il_ppo with real encodes) exist only in the leaky (clip-level budget) setting. buffer_real.py writes under BR.OUT, which follows the ladder tag, so a ladder rerun would not overwrite D40/D43.
- 11-18 pushed to GitHub main bc20570 (sarapirast/Learned-Video-Control-Rate): pavneet_handoff/repo synced (40 changed files), live_stream_artifacts + results_buffer{,_trace}_ladder for both codecs and baselines2_wide.pkl in the 8 D39 settings; README notes for D44-D46.
- 11-18 D47 built (leak-fixed real-encoder check); x265 debug job 14352570 submitted (debug partition).
- 11-18 D47 debug 14352570 passed (4 min): ladder lookups vs D45 rows max |diff| 0; replay = lookup; val E2 tuning and il_rr --quick ran. E2 rows identical across channels for the first case, as in D40 (channel-blind encode, no stall on that case).
- 11-18 D47 full run submitted (user: yes); job ids in JOBS.md.
- 11-18 First draft of the final report: paper/final/final_report.tex -> final_report.pdf (IEEEtran conference, 5 pages incl. refs; v1 only; per-GOP, stream, live). Red placeholder: D47 real-encoder (ladder). Build: PATH=/apps/generic/texlive/2024/bin/x86_64-linux:$PATH pdflatex x2.
- 11-18 D49 VMAF scripts written; waiting for the user to install the vmaf binary (download blocked for the agent).
- 11-18 D50 submitted: x265 ladder oracle 14354166-68 (done except report), x264 via submit_buffer_ladder_oracle.sh; luma stream encoder RC x265 14354274/75, x264 14354276/77.
- 11-18 D47 x264 result: ladder E2 (encoder ABR+VBV, f val-tuned 0.9) beats il_ppo_rr on AR(1) n=8 (-1.67 [-3.37, -0.75]); ties on n=16 and LTE (LTE f at grid edge 0.6). E2 extension f 0.2-0.5 (LTE) submitted for both codecs + report rerun.
- 11-18 D47 done (both codecs, + E2 extension f 0.2-0.5 on LTE; val f: x265 AR1 0.9, LTE 0.3; x264 AR1 0.9, LTE 0.4). Replay = lookup (0.000) everywhere. il_ppo_rr - encoder whole-stream ABR+VBV (val-tuned f), test every 3rd case: x265 AR1 n8 -0.50 [-1.73, +0.12], n16 +1.28 [-0.31, +2.20]; x265 LTE +0.64 [-1.21, +1.97]; x264 AR1 n8 -1.67 [-3.37, -0.75]*, n16 +0.09 [-2.30, +1.43]; x264 LTE -0.78 [-3.33, +1.04]. => with the ladder budget RL never beats the encoder's tuned ABR+VBV (ties; loses x264 AR1 n8). Paper updated.
- 11-18 D50 oracle (ladder): oracle - vbv2 1.7-1.9 dB (AR1), 2.7-3.1 (LTE); il_ppo closes 24-34 % / 12-15 %.
- 11-18 D50 luma stream level: BC->PPO L2 - encoder ABR+VBV x265 +0.61 [+0.49, +0.74], x264 +0.29 [+0.21, +0.40]; - two-pass x265 +0.03 (tie), x264 -0.31*. Reports results/v1_stream/<codec>/own_rc_stream_v1_luma_report.md. Paper Table III updated (Exp 7 / P4 rows still 6:1:1, footnoted).
- 11-18 Paper now 6 pages, no placeholders.
- 11-18 D49 VMAF full submitted: x265 native 14357516 / 1080 14357517, x264 native 14357518 / 1080 14357519 (debug timing 14 s native, 240 s 1080 per GOP; VMAF 3.0.0 built from source, /scratch1/pbanga/envs/vmaf/bin/vmaf, official binary needs glibc 2.34).
- 11-18 D51 paper fixes applied (paper/final/final_report.tex, 6 pages; backup /scratch1/pbanga/tmp/final_report_v1.tex). 3-seed il_ppo - encoder E2: x265 AR1 -0.51 [-1.74,+0.11], LTE +0.96 [-0.86,+2.25]; x264 AR1 -1.67*, LTE -0.52 [-2.97,+1.25]; n16 +1.25 / +0.10.
- 11-18 D49 VMAF curves done (all 96 tasks, 0 bits mismatch; 1080p shards <= 49 min). D52 VMAF rescoring -> results/v1_vmaf/; paper Table VI + VMAF paragraph; last red placeholder removed (6 pages).
