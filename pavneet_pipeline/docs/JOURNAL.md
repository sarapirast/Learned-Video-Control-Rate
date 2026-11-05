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
