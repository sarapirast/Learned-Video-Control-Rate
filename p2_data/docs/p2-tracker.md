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
- [x] v0: superseded by data v1 (decided 2026-10-29); the pilot clips are no longer needed.
- [~] Source ~80-150 clips with licences (Fri). Candidate list done: 142 clips (103 priority 1), see `docs/clip-selection.md`. Downloaded 2026-10-29 (103 P1 clips, 52.9 GB in `data/raw/`). Decoded 2026-10-29: 88 accepted P1 clips -> `data/v1/320x180/clips/` (880 GOPs, 2.2 GB, `manifest.csv`); 38 flagged clips wait on the team decision (decided 2026-11-02: decimate and keep; 15 P1 clips added, item 8). Pilot dataset superseded (agreed with Pavneet). Next: cut labels, then freeze v1.
- [x] Splits by group (film/shoot/uploader): proposed in `data/clip_candidates.csv`, 87/21/34 clips (hash per group, stable when the list changes). Test cut-GOP count (>= 40 from >= 5 clips) still to be confirmed by the cut detector. FINAL in v1: 66/16/27 clips, 78 groups, 625/152/265 GOPs (`docs/data-v1-README.md`).
- [~] Cut labels: `scripts/cut_labels.py`. 2026-10-29: signals for all 88 clips; 99 uncertain frames reviewed independently by Claude and Aayush (80% exact agreement, kappa 0.64; 89% on cut vs not-cut), 20 disagreements settled (`config/cut_review_v1.csv`). Round 2: all 144 rejected frames + 16 both-detector frames reviewed by Claude (4 missed cuts, 48 gradual). Webdriver Torso dropped, replaced by Animation_480P-52af. Now 141 cuts; test 49 cut GOPs / 18 clips / 7 groups. Round-2 blind check by Aayush: 10/15 agreed, 5 settled. Open: histogram definition vs pilot code, dissolve detection untested.
- [x] SI/TI per frame (2026-10-29, `data/v1/320x180/features/siti.csv`)
- [x] Data README: `docs/data-v1-README.md` via `scripts/data_readme.py`; regenerated at the freeze 2026-11-03 (marked frozen; numbers unchanged)

### Week 1: encoder-dependent (UNBLOCKED 2026-11-03: P1 froze x264 settings; x265 4.1 available)
- [ ] First-pass bits (pilot: ultrafast at QP 32; Pavneet: QP 30; run on P1's frozen settings) -> work-queue item 13
- [ ] Native R-D curves, QP 18-50 per GOP (item 13), both PSNR conventions (`rd_native.parquet`). Note: pilot "native" = IDR at q-3, P at q.
- [ ] Budget table: 3-4 levels per GOP, `how_set` recorded (`budgets.csv`); NOT from the GOP's own encodes (item 14)
- [ ] Causal base-QP estimator, fit on train, MAE in QP on val (item 14)
- [ ] Baselines (Pavneet's pipeline on v1 already gives his versions; P2's on P1's settings still to do): native constant QP; fixed pattern with hindsight shift (reference); causal fixed pattern (pilot's naive causal version went over budget on 91% of GOPs, so use the estimator shift or a budget shield)

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
| Ahhana (P1) | Encoder choice and frozen settings (x264 vs x265, resolution, GOP length) | First-pass, R-D curves, budgets, baselines | DONE 2026-11-03 for x264 settings (`docs/Ahhana_update.txt`); team keeps x265 too; resolution/GOP length still open |
| Atharva/Pavneet (P3) | Pilot clips and code: cut detector, first-pass, fixed pattern | v0 | superseded: v1 replaced v0; his full repo is cloned at `repo-pavneet/` |
| Atharva/Pavneet (P3) | Leak answer: does the residual correct the *shifted* pattern? | Causal fixed pattern, budget proposal | answered by the code check 2026-11-03 (findings C1/U1 in `docs/review-paper-draft-2026-11-03.md`) |
| Atharva/Pavneet (P5) | Shared directory and results-row format | Output location, baseline rows | shared dir: our scratch via ACLs (done); results-row format open |
| Sara (P4) | Agreement on the lookahead summary | `features.parquet` spec | open (no reply yet; status unknown) |
| Team | Budget definition, file formats, PSNR convention, VMAF, action space, canonical codebase | Budget table, final formats | open; slice bits only agreed with P1 2026-11-03 |
| Team | GitHub repo: https://github.com/sarapirast/Learned-Video-Control-Rate (empty as of 2026-10-29; cloned to `repo/`) | Code in git | done |

## Others waiting on me

| Who | Needs | Status |
|---|---|---|
| Ahhana (P1) | Clips, YUV, features | clips + YUV shared 2026-11-02 (`data/v1/`); SI/TI done; `fp_bits` pending (item 13) |
| Atharva/Pavneet (P3) | GOPs, budgets, best feasible constant QP (the search's starting point) | GOPs shared (`gops.csv`); budgets + CQP curves pending (items 13/14) |
| Sara (P4) | Feature spec | draft in `docs/feature-spec-draft.md`, waiting on her answers |
| Atharva/Pavneet (P5) | Native R-D curves, cut labels | cut labels shared (`gops.csv`, reviewed); R-D curves pending (item 13) |

## Open decisions

- Encoder: DECIDED 2026-11-02, both x264 and x265. P1 froze the x264 settings 2026-11-03; x265 4.1 is Pavneet's build. Still to align: Pavneet's harness (preset fast, psy on) vs P1 (medium, psy off).
- First-pass definition: pilot ultrafast at QP 32 vs Pavneet's QP 30; compute on P1's frozen settings (item 12/13).
- Resolution and GOP length (pilot: 320x180, 30 frames).
- Budget definition (P2 draft, revised 2026-11-03: policy sees only B; budgets NOT from the GOP's own encodes, clip-level targets, wider range; base QP from the causal estimator; `docs/p2-plan.md`).
- Action space: dqp relative to the previous QP (P1) vs offset on a fixed base QP (Pavneet).
- Canonical codebase: team repo + P1 env vs Pavneet's repo.
- Lookahead summary features (draft, needs Sara).
- File formats and results-row schema (draft).
- PSNR convention: mean of per-frame PSNR vs PSNR from mean MSE.
- VMAF: in the results row, but CARC's ffmpeg has no libvmaf and there is no module.
- Causal fixed pattern: estimator-based shift or budget shield.
- Whether to keep the `gradual` class (first thing cut if a week slips).
- Frame-rate rule decided 2026-10-29: accept 23.976-30 fps. High-frame-rate clips DECIDED 2026-11-02 (team): decimate (120/60 -> 30, 50 -> 25) and keep them in all splits; the 15 priority-1 ones are in v1 (work-queue item 8).
- Clip processing (proposal in `docs/clip-selection.md`): at most 300 frames per clip, centre-crop to 16:9.
- Whether the pilot's test clips stay in test: superseded by work-queue item 12 (one canonical split; v1 proposed).

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
  `logs/` (`#SBATCH --output=/scratch1/aayushso/ee599/logs/%x-%A_%a.out`), never to `/home1`. Exception: the
  `rc_v1` pipeline jobs log to `/scratch1/aayushso/rcwork_v1/logs/`.
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

- [x] 10. Reviewed Pavneet's mid-project draft (`paper.pdf`, 2026-11-03) -> `docs/review-paper-draft-2026-11-03.md`.
  Verdict: continue, with urgent fixes U1-U5 (oracle base QP in per-GOP budget; soft vs hard budget;
  spliced GOPs in val/test; no stable/cut split; iid bootstrap). His repo is private (404), so the code
  checks are pending access. Team decision 2026-11-02: keep both x265 and x264
- [x] 11. Code check of Pavneet's repo (cloned at `repo-pavneet/`, da7cc53): findings C1 (budget = GOP's own CQP
  spend leaks whole-GOP cost even at k=0; same flaw in our p2-plan budget proposal) and C2 (cut/flash/fade flags
  look 2-4 frames ahead) added to the review
- [ ] 12. Settle one canonical dataset/split with Pavneet (data v1 vs his 189-source windows); first-pass QP 30 vs 32
- [x] 13. fp_bits + CQP 18-50 curves on v1 for both encoders (DONE 2026-11-04 09:32, P1 frozen settings; x265 4.1 =
  Pavneet's build). Jobs 13713474/75 (4 shards each) + gather 13713476, ~4 min, all rc 0, 1042/1042 GOPs per encoder.
  scripts/rd_native.py + jobs/rd_native.sbatch -> data/v1/320x180/rd/{rd_native,rd_frames}.parquet,
  features/fp_bits.parquet (fp at QP 30 and 32). Checks/summary: docs/rd-native-summary.md (scripts/rd_summary.py).
  Findings: x265 5-12% fewer bits than x264 at equal PSNR; P1 settings use ~5% (x264) / 7-13% (x265) fewer bits
  than the v1 rerun's harness at equal QP; first pass at QP 32 tracks CQP bits slightly better than QP 30 (log corr
  0.969 vs 0.964 x264, 0.977 vs 0.969 x265). fp_bits not yet merged into frames.parquet. Smoke outputs left in
  data/v1/320x180/rd/smoke/ (removal blocked by the safety check; Aayush to delete).
- [x] 14. Causal base-QP estimator + budget table (P2 task 5); fixes U1. Budgets must NOT be the GOP's own
  CQP spend (C1): use clip-level targets or a wide random factor
  DONE 2026-11-04 (v1): scripts/budgets_v1.py -> data/v1/320x180/budgets.csv (8,336 rows = 1042 GOPs x 4 levels x
  2 encoders) + docs/budget-estimator-v1.md. Budgets = clip mean of constant-QP slice bits per GOP at q0 in
  {24,30,36,42} (never the GOP's own spend): budget / own CQP spend has median 1.02, p10 0.66, p90 1.7-2.1.
  q_fit (hindsight QP spending exactly B) clipped at QP 18 for 10% of GOPs at level 24 (209/2084): extend curves
  below 18 (P1 env allows 11) or move the lowest level to 26 - team decision.
  Estimator (train only, out-of-fold by group on train): val MAE in QP, linear, fp QP 32: x264 3.95 (k=0) ->
  2.73 (k=2) -> 2.71 (k=29); x265 3.58 -> 2.37 -> 2.17. GBM better at large k (k=29: 1.70 / 1.37) but worse at
  k=0. Budget only (no first pass): 4.17 / 3.94. Cut/gradual GOPs ~1 QP harder. fp QP 30 vs 32: no clear winner.
  So a GOP-start estimate is off by 2.4-4 QP: the base QP needs online recalibration per frame (next step), and
  the biggest lookahead gain for rate estimation is k=0 -> 2 (seeing the first P frames).
- [ ] 16. (2026-11-03 call w/ Atharva, docs/zoom_meeting_summary.txt) MILESTONE REPORT due Wed 2026-11-04: lock readings
  by then. Aayush: post group summary (draft given in session 2026-11-03), shared clips (done). Atharva: wider budget
  QP range, longer clips, bare-bones vs full-feature encoders. Open from P1 (docs/Ahhana_update.txt): encoder flags
  differ from Pavneet's harness (preset medium vs fast, psy off vs on); forced-QP clamp check (ipratio/pbratio vs
  --crf+qpfile); action space relative vs fixed base; slice bits only (agreed by P2).
  FORCED-QP CHECK DONE 2026-11-03 (scripts/x264_forced_qp_check.sh, 1 GOP Animation_360P-3e40@0, x264 0.165.3222):
  Pavneet's --crf+qpfile = requested QP on 30/30 frames (incl. 11 and 51); Ahhana's --qp 31 --ipratio 10 --pbratio 10
  also 30/30; plain --qp clamps 24/30 frames into base +-3 (her finding, only for --qp). So Pavneet's x264 results are
  NOT affected. But the two forced-QP methods are not bit-identical (6-27 of 30 frames differ by a few bytes, totals
  within 0.3%), and preset fast/psy-on vs medium/no-psy changes total bits by 1.8% at the same QPs.
- [~] 18. (2026-11-04) Causal online base-QP controller = P2's causal baseline, under the clip-level budgets
  (budgets.csv). Offline prototype scripts/controller_v1.py: PSNR side INVALID (it reads P-frame distortion from
  constant-QP encodes, but a skipped P frame's quality follows its reference's QP; e.g. near-static lyric GOP gave
  +70% / -236% artifacts) -> kept only as a record. Real-encode version scripts/controller_real.py (prefix re-encodes,
  P1 settings, x264 forced QP via --qp 31 --ipratio 10 --pbratio 10, x265 via --qp + qpfile, both checked 30/30;
  train-only rate model in data/v1/320x180/rd/controller_model.json; generic job script jobs/p2_step.sbatch).
  Smoke OK (1.8 / 3.8 CPU-s per episode x264 / x265). Tuning on val submitted 2026-11-04: 13714557 (x264),
  13714558 (x265), 12 settings (margin x dI x i_cap) x k0/5 x 4 levels x every 2nd val GOP. NEXT: pick setting on val
  (python scripts/controller_real.py --report), then final val+test run (all GOPs, k 0/2/5/10/29) with approval.
  Tuning v1 (13714557/58) exposed two flaws: (1) one odd first-pass frame set the whole P estimate -> frame 1 at
  QP 11 spent 4-6x the budget; (2) at k=0 the I frame was starved on low-motion GOPs (I QP above P QPs), saving -26
  to -56%. Checked the scoring chain: forced-QP encodes = plain CQP within 0.4% bits, same PSNR. Fixes in
  controller_real.py: P first-pass estimate shrunk to fp_0/(I-P ratio); per-frame spend cap fcap; QP change limit
  dmax; option init=1 (I QP from budgets.csv estimator - dI); P QP >= I QP + pmin. Hard-case check (6 GOPs, levels
  36/42): -26 -> +0.5 (k0), +1.75 (k5). Tuning v2 submitted: 13715965 (x264), 13715966 (x265), tag tune2.
  Tuning v2 (val, k0/5 pooled): best for both encoders 0.97:3:1.0:2:3:4:0:1 (margin 0.97, dI 3, solver start):
  x264 -3.48 / x265 -2.99 (clamped scoring), 2.7% / 1.4% over; margin 1.0 -> 23-28% over; estimator start
  (init 1) worse overall. Scoring switched to Pavneet's linear extrapolation beyond the curve (level 24 had been
  biased): chosen setting -> x264 -2.82, x265 -2.29. Final run submitted 2026-11-04: 13716235 (x264 val), 13716236
  (x264 test), 13716237 (x265 val), 13716250 (x265 test), tag final. Report: scripts/controller_report.py ->
  results_v1/controller_final.md.
  FINAL (2026-11-04 10:44, 32/32 tasks OK): results_v1/controller_final.md (scripts/controller_report.py). Test score
  by k (0/2/5/10/29): x264 -3.94/-2.21/-0.94/-1.02/-2.48; x265 -4.45/-1.96/-0.20/-0.81/-2.19 (0 = best constant QP
  in hindsight); 2-4.5% of runs over budget, mean over 0.07-0.35%. The GOP-start estimate held constant (no feedback)
  scores -25 to -103 (overshoots on ~50-60% of GOPs), so online feedback is what makes a causal base QP work.
  Lookahead helps up to k=5-10; k=29 is worse than k=5 (to investigate).
  k=29 anomaly DIAGNOSED (no encodes, from stored QP sequences, test): with more lookahead the plan flattens
  (P QP std 1.6 -> 1.0; first-5 vs last-5 P QP 32.9->35.1 at k0 vs 33.7->33.8 at k29; I QP 29.0 -> 30.4). The rule
  "constant QP that spends the remaining budget" converges to flat QP with perfect information, which ignores that
  early frames (and post-cut frames) are references for later ones (spend-early / mb-tree effect). Small k front-
  loads by accident. Loss k10 -> k29 concentrated in cut (-3.0) and gradual (-6.3) GOPs vs stable (-0.95). Fix for
  controller v2: explicit spend-early QP profile + QP boost on the first frame after a visible cut, tuned on val.
- [x] 20. (2026-11-04) Richer first-pass statistics (x264/x265 --pass 1 --stats): scripts/fp_stats.py -> features/
  fp_stats.parquet (jobs 13717883/84/85; pass-1 stream bits identical to fp_bits). Gate test scripts/fp_stats_gate.py
  -> docs/fp-stats-gate.md: (a) per-frame bits at a QP: GBM median error 27% -> 21% (x264), 22% -> 18% (x265) =
  helps; (b) GOP P cost from frames 0-1: no consistent gain; (c) base QP at k=0/2: within +-0.2 QP. So the stats help
  per-frame prediction of visible frames, not the k=0 problem (that is missing future information). Next option:
  GBM per-frame model in the controller (k>=2 gains expected, small headroom).
- [x] 19. (2026-11-04) Literature survey on feature extraction for RL/learned control on video:
  docs/lit-survey-features-2026-11-04.md (21 refs). Encoder RL (MuZero-RC, Mao 2020, DDPG-x265) uses first-pass /
  encoder statistics + budget bookkeeping, never raw pixels; MuZero-RC learns a Transformer embedding over the
  per-frame first-pass statistic sequence (20k training videos). Pixel CNNs in codecs are supervised R-D parameter
  predictors (0.7-2% BD-rate). General RL-from-pixels: pretrain/freeze encoders with proxy tasks (ATC, CPC, CURL,
  world models, pretrained vision models). Cheapest upgrade for us: x264 --pass 1 --stats per-frame tex/mv/misc bits
  + intra/inter/skip MB counts (verified on a v1 GOP), x265 per-frame stats.
  Repo: Aayush pushed p2-data-v1 1ec4df0 (2026-11-04).
- [x] 17. (2026-11-04, side-step; closed 09:25 by Aayush after A came out negative) Overshoot size + RL model review. Done: results_v1/v1_overshoot.{md,csv}
  (scripts/v1_overshoot.py), docs/rl-models-review-2026-11-04.md. Proposed experiments A (budget shield at
  inference, no retraining), B (lambda sweep + PID + val checkpoints), C (MPC, implemented, not run on v1),
  D (residual on causal controller, needs item 14), E (DT / attention encoder). Aayush picked A (2026-11-04).
  A in progress: Shield in repo-pavneet rclib/policies.py + env hook (q_override, shield_fires) + tools/shield_eval.py
  (writes results_rl/<run>/shield_<split>.pkl, never eval.pkl). Smoke (x264 cql_ppo k0 s0, 10 val GOPs): 0% over but
  score 2.44 -> -2.40 (lenient) / -9.09 (strict): fires on GOPs that were within budget (bits model too pessimistic,
  2^(-dq/6) slope + calibration). NEXT: fit bits-vs-QP slope on train, test the predictor offline, then re-smoke.
  Fixed model (train-fitted slopes P 5.0 / I 6.8 QP per halving, shrinkage w0=3, tolerance schedule tol), commit
  9f60b0f (local). Val sweep 13713117 (x264 orig, 15 models seed 0 x tol 0.1/0.2/0.3/0.5; one task auto-retried
  off d05-08, mechanism worked): results_v1/x264_orig_shield_val.md (scripts/v1_shield_compare.py). NEGATIVE: the
  shield lowers every method's val score (best tol 0.5: BC 2.67->2.22, CQL->PPO 2.89->2.25, Lagr 3.45->2.71); saving
  drops 1-1.2 pts, over-rate only 24->19% / 21->17% / 12->9%. Overshoots are frequent but small (mean ~0.6%), the
  early prediction is +-10-20% noisy, so firing costs more than the penalty it saves. Possible last test: end-game
  shield (act only in the last 5-10 frames, where prediction is +-3%).
  CLOSED: A recorded as negative (end-game variant not run). B-E remain proposals in docs/rl-models-review-2026-11-04.md.
- [x] 15. Run Pavneet's pipeline on data v1 (agreed 2026-11-03): stages A (infos/scenes/baselines), B (search),
  C (BC, CQL->PPO, Lagrangian at k 0/2/5/10/29, 3 seeds), x265 + x264, two budget arms (original;
  decoupled = CQP spend x s~U(0.8,1.25) + causal normalisation). Local branch `v1-data` in `repo-pavneet/`,
  never pushed. Work dirs `/scratch1/aayushso/rcwork_v1/{x265,x264}`. Steps:
  - [x] 15a. x265 4.1: Pavneet granted ACL 2026-11-03. Binary copied to /scratch1/aayushso/envs/codecs/bin/x265
    (sha256 3042edd5..., SHA256SUMS + SOURCE.txt there; GCC 13.3 static libx265, needs gcc/14.3.0 libstdc++ from
    job_env_v1.sh). --quick smoke test on v1 OK (infos, scenes, search, lagr k2). x264 = module 0.165.3222
  - [x] 15b. RL env at `/scratch1/aayushso/envs/rc` (py3.12, torch 2.15 CPU, SB3 2.9.2, gym 1.3, numpy 2.5.4)
  - [x] 15c. (2026-11-03) x264 --quick smoke test OK end to end on v1 (infos, scenes fit/apply, search, lagr k2 RL
    eval, budget_arm.py). Job scripts: jobs/rc_v1_submit.sh (stage AB / C), jobs/rc_v1_step.sbatch, jobs/rc_v1_rl.sbatch;
    run lists runs_v1/orig.txt (45), runs_v1/dec.txt (24); reports -> results_v1/<codec>_<arm>/. Adapter `scripts/v1_rc_manifest.py` done (manifest for rcwork_v1/x265_orig built, counts match v1); branch v1-data commit has RC_ARM switch, tools/budget_arm.py, tools/job_env_v1.sh. --quick smoke test waits on x265. SCOPE (Aayush, 2026-11-03): TRIMMED ~1,000 CPU-h: both encoders; orig arm A+B + BC/CQL->PPO/Lagr at k 0/2/5/10/29 x3 seeds;
    dec arm search train+test + BC/Lagr at k 0/2/10/29 x3 seeds; RL jobs 16 CPUs. x264 can start before x265
  - [x] 15d. x264 orig AB: jobs 13695385-13695399, all COMPLETED rc 0 by 10:19 (2026-11-03), ~100 alloc CPU-h.
    Reports: results_v1/x264_orig/{infos,scenes,search,baselines}_report.md. Split counts match v1 (625/152/265).
    Search test gain 13.7 (@QP30) / 21.4 (@QP38), still rising at 300 encodes. FINDING: STATIC (-6,-3,3,10) is
    x265-tuned; on x264 v1 train it scores -9.7 vs refit best (-4,0,3,5) +2.9 (his own x264 run: -14.4 vs +2.5).
    Kept unchanged for comparability with his paper; noted in msg to Pavneet.
  - [~] 15e. x264 dec: budget_arm.py done (1042 GOPs, factor 0.80-1.25, mean 1.025). dec AB (search train+test)
    submitted 2026-11-03: 13696483/84 (train), 13696485/86 (test). dec C (24 RL runs) 13696793, held on 13696484.
  - [~] 15f. x264 orig C (45 RL runs) submitted 2026-11-03: array 13696487 (%20).
    Node failures (/scratch1 client lost, SIGBUS rc 135 / I/O error): tasks 4 (d06-19), 11, 34, 35 (d11-42) FAILED;
    33 (d06-19, hung) cancelled. RERUN LATER together with any other failures: RC_TASKS=4,11,33,34,35
    bash jobs/rc_v1_submit.sh x264 orig C (approval). Excludes now come from jobs/bad_nodes.txt (dated, expire
    after 3 days; scripts/bad_nodes.sh exclude|add|failed|list); sbatch files have a scratch check at start (rc 75).
  - [~] 15h. x265 orig AB submitted 2026-11-03: 13696775-13696789 (infos 75/76, scenes 77/78, own_rc 79/80,
    static 81/82, rules 83, search train 84/85, val 86/87, test 88/89). Next (each with approval): budget_arm.py
    x265_orig -> x265_dec, `x265 dec AB`; `RC_DEP=<85> x265 orig C`; then `x265 dec C`.
    11:35: x265 budget_arm done (x265_dec infos.pkl, 1042 GOPs). CPU-h used 642 by 11:35; full-scope projection ~1,400
    (x265 is 1.7-2x slower; the earlier ~1,000 figure was low). DECISION (Aayush, 11:40): hold all further x265
    submissions until x264 RL reports are in (~12:30-13:00), then decide x265 scope.
    More node failures: x265 static_pattern shard 2 (d11-32) -> gather 13696782 DependencyNeverSatisfied (scancel +
    rerun shard 2 + gather); x264 dec RL tasks 7 (d06-19), 9 (d11-42). Rerun batch: x264 orig RL 4,11,33,34,35;
    x264 dec RL 7,9; x265 static_pattern shard 2 + gather.
    12:10: x264 RL done both arms -> results_v1/x264_{orig,dec}/*_report.md and results_v1/x264_arm_compare.md
    (scripts/v1_arm_compare.py). Result: dec lowers k=0 (Lagr 4.67->3.37, BC 0.75->-2.86), lookahead gain stays small
    (Lagr +0.5 at k=2; BC +2.6 at k=29). Best x264: Lagr k=0 orig (4.67, 75% of search gain, 3% over).
    a02-17 added to bad_nodes (x265 version guard failed, cause unknown; guard now prints the version output).
    DECISION (Aayush, 12:15): rerun all failures + FULL x265 scope. Submitted: scancel 13696782; reruns x264 orig RL
    13697800 (tasks 4,11,33,34,35), x264 dec RL 13697801 (7,9), x265 static shard2 13697802 + gather 13697803, x265
    val gather 13697804; x265 dec AB 13697810-14; x265 orig RL 13697815 (45); x265 dec RL 13697816 (24, held on 13697811).
    TODO when done: rerun scripts/v1_arm_compare.py x264 (fills Lagr k=2 orig) and x265; analysis.py per arm.
    12:56: x264 orig reruns done; x264_arm_compare.md regenerated (orig Lagr k=2 4.55, -0.12 vs k=0). main queue
    jammed (994 pending, our jobs on Priority, no start estimate) -> Aayush OK'd Partition=main,oneweek via scontrol
    update for pending jobs: 13697801/10/11/13/14 updated; 13697815 tasks 0-10 and 13697816 hit oneweek's 50-job
    submit cap and stay main-only. x265 search runs fine on oneweek Xeon nodes (d18-*).
    13:20-13:35: d18-35 black hole (5 SIGBUS in 20 min after passing scratch check) + d05-06 (killed, no stdout) added
    to bad_nodes. With Aayush's OK: ExcNodeList updated on pending 13697815/16; reruns x265 dec search train 5,6
    (13699422), test 0,3 (13699423), x264 dec RL 7 (13699426); new gathers 13699424 (train) / 13699425 (test) with
    afterok:rerun,afterany:original; old gathers 13697811/14 cancelled; 13697816 now depends on 13699424.
    Node stats today: 14 of 215 jobs failed, on 6 of 71 nodes; repeat failures on the same node within 20-35 min.
    OPEN for next session: (a) DONE 14:15: x265 orig RL task 11 rerun 13700380; (b) DONE 14:15: x265 dec test shard 1
    failed on d05-06 (13:54) -> rerun 13700379, test gather 13699425 dependency updated to afterok:13699423,13700379;
    (c) DONE 14:20 (code): auto-retry block in both jobs/rc_v1_*.sbatch (+ --requeue --open-mode=append): on rc 135/75 or
    unreadable scratch -> debug helper job adds node to ExcNodeList + bad_nodes.txt, requeuehold/release, max 2 retries.
    Only affects NEW submissions. TESTED 14:17-14:20 (debug job 13700447, fake rc 135): attempt 1 on d05-41 -> helper
    13700448 set ExcNodeList=d05-41 + released -> attempt 2 on d05-42 rc 0, Restarts=1, same job ID;
    (d) DONE 14:22 (draft): docs/carc-ticket-scratch1-2026-11-03.md - Aayush sends it from his account; (e) reports: analysis.py per arm,
    scripts/v1_arm_compare.py x265 (and x264 again once dec RL 7 is in).
  - [x] 15g. (2026-11-04 08:10) All runs complete (x265 orig RL 45/45 incl. rerun 13700380; x265 dec search + 24 RL;
    x264 dec task 7). Reports: results_v1/{x264,x265}_{orig,dec}/*_report.md, {x264,x265}_arm_compare.{md,csv}
    (scripts/v1_arm_compare.py), and results_v1/v1_headline.md (scripts/v1_headline.py) for the milestone.
    x265: Lagr orig k=0 4.12, best k=29 4.75 (+0.63 +- 0.26); dec k=0 3.45 (leak drop 0.67 vs 1.31 on x264);
    CQL->PPO x265 3.49 at k=0 (x264 -0.17); BC gains most from lookahead but overshoots 20-30%.
    Correction: x264 ABR+VBV over budget = 85% pooled over both budgets (62-76% was QP38 only).
