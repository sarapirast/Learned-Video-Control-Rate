# P2 tracker (Aayush)

Last updated: 2026-10-27. Update it as items move. The sources are `docs/p2-plan.md` (full plan) and
`docs/Report.pdf` (pilot). Workspace is on `/scratch1`, which is not backed up: once the team repo exists,
keep a copy of this file there.

Status marks: `[ ]` not started, `[~]` in progress, `[x]` done, `[!]` blocked.

## Trajectory (5 weeks from 2026-10-26)

Research question: how much of an offline hindsight search's gain can a single-encode policy capture,
and how does that change with lookahead k? Results are split into cut, gradual and stable GOPs.

| Week | Team goal | P2 part |
|---|---|---|
| 1 | Data foundation, formats agreed | v0 data (Wed), full clip set (Fri), cut labels, features, budgets + estimator, baselines started, README |
| 2 | Baselines at scale | All baselines on all GOPs × budgets as job arrays; `rc-lookahead` over the k grid |
| 3 | Where the search's gain comes from | Gain split by cut/gradual/stable; QP changes before vs at/after cuts; written hypotheses |
| 4 | Lookahead sweep, adaptive lookahead | Split every k-curve by cut vs stable; adaptive-lookahead gating script (thresholds on val) |
| 5 | Evaluation and write-up | Quality vs delay figure; data and baselines section of the report |

## My work

### Week 1: can start now (no encoder needed)
- [!] v0: repackage the 21 pilot clips into `manifest.csv`, YUV, `gops.csv` (Wed). Blocked on the pilot clips/code.
- [~] Source ~80-150 clips with licences (Fri). Candidate list done: 142 clips (103 priority 1), see `docs/clip-selection.md`. Downloaded 2026-10-29 (103 P1 clips, 52.9 GB in `data/raw/`). Decoded 2026-10-29: 88 accepted P1 clips -> `data/v1/320x180/clips/` (880 GOPs, 2.2 GB, `manifest.csv`); 38 flagged clips wait on the team decision. Pilot dataset superseded (agreed with Pavneet). Next: cut labels, then freeze v1.
- [~] Splits by group (film/shoot/uploader): proposed in `data/clip_candidates.csv`, 87/21/34 clips (hash per group, stable when the list changes). Test cut-GOP count (>= 40 from >= 5 clips) still to be confirmed by the cut detector.
- [~] Cut labels: `scripts/cut_labels.py`. 2026-10-29: signals for all 88 clips; 99 uncertain frames reviewed independently by Claude and Aayush (80% exact agreement, kappa 0.64; 89% on cut vs not-cut), 20 disagreements settled (`config/cut_review_v1.csv`). Round 2: all 144 rejected frames + 16 both-detector frames reviewed by Claude (4 missed cuts, 48 gradual). Webdriver Torso dropped, replaced by Animation_480P-52af. Now 141 cuts; test 49 cut GOPs / 18 clips / 7 groups. Round-2 blind check by Aayush: 10/15 agreed, 5 settled. Open: histogram definition vs pilot code, dissolve detection untested.
- [x] SI/TI per frame (2026-10-29, `data/v1/320x180/features/siti.csv`)
- [~] Data README: draft generated 2026-11-02 (`docs/data-v1-README.md` via `scripts/data_readme.py`); rerun at the freeze

### Week 1: waits for the encoder decision
- [!] First-pass bits (pilot: ultrafast at QP 32)
- [!] Native R-D curves, QP 18-50 per GOP, both PSNR conventions (`rd_native.parquet`). Note: pilot "native" = IDR at q-3, P at q.
- [!] Budget table: 3-4 levels per GOP, `how_set` recorded (`budgets.csv`)
- [!] Causal base-QP estimator, fit on train, MAE in QP on val
- [!] Baselines: native constant QP; fixed pattern with hindsight shift (reference); causal fixed pattern (pilot's naive causal version went over budget on 91% of GOPs, so use the estimator shift or a budget shield)

### Week 1 checkpoint
- [ ] Manifest, YUV, GOP table, feature files, budget table, R-D curves and estimator all exist and the README describes them

### Later weeks
- [ ] W2: native QP, ABR+VBV, CRF and two-pass (references), `rc-lookahead` over k (mb-tree off; defaults separately), fixed pattern (both versions); baseline table in results-row format
- [ ] W3: gain breakdown by GOP class; QP trajectories around cuts; before vs at/after cut measurement; written hypotheses
- [ ] W4: split k-curves; adaptive gate (k=0/k=1 sub-policies; fixed rule on stable + learned around cuts)
- [ ] W5: quality vs delay figure; report section

## Waiting on others

| From | What | Blocks | Status |
|---|---|---|---|
| Ahhana (P1) | Encoder choice and frozen settings (x264 vs x265, resolution, GOP length) | First-pass, R-D curves, budgets, baselines | open |
| Atharva/Pavneet (P3) | Pilot clips and code: cut detector, first-pass, fixed pattern | v0 | open |
| Atharva/Pavneet (P3) | Leak answer: does the residual correct the *shifted* pattern? | Causal fixed pattern, budget proposal | open |
| Atharva/Pavneet (P5) | Shared directory and results-row format | Output location, baseline rows | open |
| Sara (P4) | Agreement on the lookahead summary | `features.parquet` spec | open |
| Team | Budget definition, file formats, PSNR convention, VMAF | Budget table, final formats | open |
| Team | GitHub repo: https://github.com/sarapirast/Learned-Video-Control-Rate (empty as of 2026-10-29; cloned to `repo/`) | Code in git | done |

## Others waiting on me

| Who | Needs | Status |
|---|---|---|
| Ahhana (P1) | Clips, YUV, features | not started |
| Atharva/Pavneet (P3) | GOPs, budgets, best feasible constant QP (the search's starting point) | not started |
| Sara (P4) | Feature spec | draft in `p2-plan.md` |
| Atharva/Pavneet (P5) | Native R-D curves, cut labels | not started |

## Open decisions

- Encoder: x264 vs x265. CARC has x264 (CLI, `libx264.so`, headers); no x265 module, and ffmpeg has no libx265.
- First-pass definition if the encoder changes from the pilot's x265.
- Resolution and GOP length (pilot: 320x180, 30 frames).
- Budget definition (P2 draft: policy sees only B; base QP from the causal estimator).
- Lookahead summary features (draft, needs Sara).
- File formats and results-row schema (draft).
- PSNR convention: mean of per-frame PSNR vs PSNR from mean MSE.
- VMAF: in the results row, but CARC's ffmpeg has no libvmaf and there is no module.
- Causal fixed pattern: estimator-based shift or budget shield.
- Whether to keep the `gradual` class (first thing cut if a week slips).
- Frame-rate rule decided 2026-10-29: accept 23.976-30 fps; 50/60 fps-family sources flagged. Open: what to do with the 38 flagged clips (15 priority 1: SVT, UVG 120 fps, 3 UGC): drop, decimate, or train only.
- Clip processing (proposal in `docs/clip-selection.md`): at most 300 frames per clip, centre-crop to 16:9.
- Whether the pilot's test clips stay in test (needs their IDs from Pavneet).

## Environment notes (checked 2026-10-27)

```bash
module purge
module load ver/2506 gcc/14.3.0 ffmpeg/7.1.1 x264/20250608   # not gcc/12.3.0
module load ver/2506 gcc/14.3.0 poppler/25.06.0              # pdftotext/pdftoppm
```

ffmpeg 7.1.1 has libx264, `psnr`, `ssim`, `xpsnr`, `scdet`; no libx265, no libvmaf.

## Running jobs

**Rules.**
- The interactive allocation is finite, and anything started in it dies when it ends. Check time left
  with `scripts/joblog.sh left` (= `squeue -h -j $SLURM_JOB_ID -o "%L"`).
- Only short tests that finish well inside the remaining time run in the interactive session. Everything
  else goes through `sbatch`, which survives the session ending.
- Test new job scripts on `--partition=debug` first. Use `main` or `oneweek` for real runs.
- Every job script starts with `module purge` plus explicit `module load` lines and writes its output to
  `logs/` (`#SBATCH --output=/scratch1/aayushso/ee599/logs/%x-%A_%a.out`), never to `/home1`.
- Every data step is a re-runnable script, since `/scratch1` can be purged.

**Ledger.** `jobs/jobs.tsv` lists every submission (time, job id, script, purpose, notes).
`jobs/submitted/<jobid>.sbatch` keeps the exact script that ran.

```bash
jid=$(sbatch --parsable jobs/foo.sbatch) && scripts/joblog.sh add "$jid" jobs/foo.sbatch "purpose"
scripts/joblog.sh status            # all logged jobs, from sacct
scripts/joblog.sh active            # pending/running, from squeue
scripts/joblog.sh note <jid> "outputs in data/..., 3 tasks failed: OOM"
```

Check on jobs when needed, not in a tight loop (the API limit is shared across sessions).

## Work queue (started 2026-10-29)

Sessions can expire, so mark each item when it finishes and resume from the first unchecked one. The
order was agreed with Aayush.

- [x] 0. CLAUDE.md brought up to date (current state, modules, checks done)
- [x] 1. SI/TI per frame for the 88 v1 clips. `scripts/frame_features.py --siti` ->
  `data/v1/320x180/features/siti.csv` (26,417 rows); verified against a plain-Python P.910 implementation
- [x] 2. First repo commit: `d2cc27c` on branch `p2-data-v1` (24 files under `p2_data/`), authored by
  Aayush Soni <75730831+AayushSo@users.noreply.github.com> (GitHub no-reply; email privacy is on). Pushed 2026-11-02; it is the repo's only branch, so GitHub shows it as the default branch.
  Later changes: run `scripts/sync_to_repo.sh`, then commit in `repo/`
- [x] 3. Project conda env at `/scratch1/aayushso/envs/ee599` (2026-11-02): Python 3.11, numpy, pandas,
  pyarrow, scipy, scikit-learn, matplotlib. Spec in `environment.yml`, exact versions in
  `environment.lock.txt`, package cache in `/scratch1/aayushso/conda_pkgs`. Use:
  `module purge && module load conda/25.11.0 && conda activate /scratch1/aayushso/envs/ee599`
- [x] 4. Data README draft: `scripts/data_readme.py` -> `docs/data-v1-README.md`, all numbers generated
  (counts, cut labels, review agreement, SI/TI quantiles and binned histograms, licences, UGC
  attributions). Rerun at the freeze. Plotted histograms can be added once the conda env exists
- [x] 5. Spliced clips (train only): `scripts/make_spliced.py` -> `spliced_01..06` (4 at ~30 fps, 2 at
  25 fps), exact labels, byte-identical pieces. +60 train GOPs (34 cut). Manifest, labels, SI/TI and the
  README were regenerated (94 clips, 940 GOPs)
- [x] 6. Feature-spec draft for Sara: `docs/feature-spec-draft.md`. Reference lookahead implementation
  in `scripts/lookahead.py` (self-tested). Per-frame table `features/frames.parquet` built by
  `scripts/build_features.py` (conda env), with `fp_bits` empty until the encoder is decided. Key point:
  the policy uses the automatic `cut_flag` (97% recall, 78% precision on natural clips), not the
  reviewed labels. Waiting on Sara's answers to the 6 questions
- [x] 8. High-frame-rate clips decimated and integrated (2026-11-02): 15 P1 clips decoded (job 13668089),
  manifest/labels/SI-TI/frames.parquet/README regenerated: 109 clips, 1042 GOPs
  (train 531/87/7, val 128/21/3, test 211/49/5). Open: 3 uncertain frames in the new clips not yet
  reviewed (cuts/disagreements.csv); repo sync + commit pending
- [x] 9. Shared read-only via ACLs (2026-11-02): pirasteh, pbanga, ahhanagu, atharvam have traverse (x) on /scratch1/aayushso; everything else stays private
- [x] 7. Dissolve-detection test: about 1 in 6 precision, so it stays off. It surfaced 1 missed cut
  (red_kayak f148) and 1 dissolve (controlled_burn), now added to the review file. Labels, feature
  table and README regenerated: train 447/84/7, val 123/21/3, test 201/49/5 (stable/cut/gradual)
