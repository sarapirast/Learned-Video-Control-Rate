# test2: a fresh held-out evaluation set for the frozen models (PLAN, 2026-11-17)

Status: PLAN ONLY. Nothing downloaded, decoded or submitted. Approved scope (Aayush 11-17): Tier 1 + Tier 2 models,
evaluation only (no training, no tuning, no refitting of anything on test2).

## 1. Why

The sealed v1 test set is narrower than its 27 clips suggest:
- 589 of 993 scored test episodes (59 %) come from two Blender films (ED, ToS); 35 of its 49 cut GOPs too.
- 13 independent sources; no Gaming, Sports, Animation, HowTo, Vlog or CoverSong content.
- Headline under a source-level bootstrap still holds: x264 +0.067 [+0.026, +0.122], x265 +0.163 [+0.102, +0.262];
  ED+ToS alone x264 +0.045 n.s., the rest +0.099 *.
test2 = a replication of the frozen models on new, more varied content, plus a per-content-type map ("where RL
works and where it doesn't").

## 2. Models (all frozen; per encoder; k = lookahead)

| Tier | Model | k | Seeds / models | Runs on |
|---|---|---|---|---|
| 1 | constant QP: causal estimate (cqp_est) and hindsight best (cqp_best) | 0, 5 | - | curves (no encodes) |
| 1 | encoder ABR+VBV at the frozen margin (x264 0.90, x265 0.93) | 0, 5 | - | encodes |
| 1 | final4 controller (1.0:6:1.0:2:3:4:1:1:1:0:3, h = 3), sequential per clip | 0, 2, 5, 10, 29 | - | encodes |
| 1 | final4 + causal per-qbin shift (perqbin:bit) | 5 | - | encodes |
| 1 | **R3** (180k models of the 11-16 test pass) | 5 | s3, s4, s5 | encodes |
| 1 | BC alone (final4 + mean[t] + BC argmax, bit cap) | 5 | s3, s4, s5 | encodes |
| 2 | R3 at k2 (final-week models) | 2 | s3, s4, s5 | encodes |
| 2 | BC alone | 0 (s0-2), 2 (s3-5) | 3 + 3 | encodes |
| 2 | CQL->PPO 540k, previous-GOP base | 0, 5 | 3 seeds | encodes |
| 2 | Ahhana's R3 k0 / k29 | 0, 29 | hers | only if she provides models + env settings |

Not on test2: the hindsight search (about 255 CPU-h; the "fraction of the search's gain" stays on v1 test), R3 360k,
no-warm-up, R1 / R2 / R2c, Lagrangian, stream level, Pavneet's live-stream work.

R3 history: the primary uses final4's GOP n-1 history (the definition pre-registered for v1 test). R3 with its own
history (exp_next/fw/seq_history.py, deployment-faithful) is a secondary.

## 3. Clips

Source: YouTube UGC only (CC BY 4.0, the same download and decode path as the 54 UGC clips in v1; categories give
the "application" axis). The local catalogue (data/meta/) has 822 unused clips from 679 unused uploaders in the 12
categories v1 uses (HDR, VR and VerticalVideo excluded, as in v1).

Selection (exp_next/test2/select_t2.py, deterministic, written 11-17 before any download):
- 12 categories x 8 clips (6 spread over temporal complexity + 2 with the highest chunk-complexity variation, i.e.
  likely natural cuts); 300 frames = 10 GOPs per clip.
- One clip per uploader; no uploader that appears anywhere in v1 (any split, priority 1 or 2); no v1 clip;
  config/exclude_clips.csv respected; frame-rate rule and 16:9 filter as v1; >= 300 output frames.
- Pools: 360P/480P first, all resolutions (incl. 720P) when fewer than 16 unused clips remain (as in v1).
- RESULT (data/t2/clip_candidates.csv, data/t2/selection.md): **93 clips, 930 GOPs, 93 uploaders**. TelevisionClip
  has only 5 eligible uploaders (7 eligible clips), so it has 5 clips and no separate likely-cut picks; every other
  category has 8. Sources 46 x 720P, 27 x 360P, 20 x 480P-ish; 3 clips at 50/60 fps are decimated.
- Download: 52.0 GB in total (49.1 GB new + 2.9 GB for the 3 parity sources, re-downloaded so parity covers download
  and decode too).
- Same decode rules and 320x180 centre-crop as v1 (docs/clip-selection.md).
- Optional, not planned: unused Blender open films for more natural cuts.

Reported content groups: the 12 UGC categories. Bootstrap unit: uploader (= clip here, one clip per uploader).

## 4. Pipeline

Rule: nothing is fitted on test2. Fitted inputs come from v1 unchanged: budget estimator (fit on v1 train),
controller_model.json, base_prev_model.json, shifts_smooth.json / shifts_qbin.json, BC classifiers, RL checkpoints.
Per-clip data products go to a separate root, **data/t2/320x180/** (same layout as data/v1/320x180), with split label
**test2**, so no v1 file or v1 result file is touched and no output name can clash with the sealed test (*_test_*).
Code change: the scripts on this path read the data root from an env var (P2_DATA, default = the v1 path, so v1
behaviour is unchanged) and accept split "test2"; outputs get no-overwrite asserts. Originals backed up first.

| Step | Script (existing) | Output (test2 root / dirs) | Change needed |
|---|---|---|---|
| 1 select | exp_next/test2/select_t2.py (imports select_clips.py) | data/t2/clip_candidates.csv | DONE 11-17 |
| 2 download | scripts/download_clips.py on hpc-transfer1 (**Aayush runs it**) | data/t2/raw/ | candidates path |
| 3 decode | scripts/decode_clips.py + jobs/decode_v1.sbatch | data/t2/320x180/clips, manifest.csv | root |
| 4 cut labels | scripts/cut_labels.py --signals / --label / --review | gops.csv, cuts/ | root |
| 5 curves + first pass | scripts/rd_native.py (both encoders) + fp_stats.py | rd/, features/ | root |
| 6 flat GOPs | scripts/flat_gops_v1.py | rd/flat_gops.csv | root |
| 7 budgets | scripts/budgets_v1.py | budgets.csv | fit on v1 train, predict test2 |
| 8 final4 | scripts/controller_real.py (sequential per clip, all k) | results_v1/controller_real/final4_<enc>_test2_* | root; models from v1 |
| 9 prev-GOP base | scripts/base_prev.py (predict only) | data/t2/.../budgets_prev_<enc>.csv | predict-only mode |
| 10 rc work dirs | v1_rc_manifest.py, Pavneet infos.py (orig), lf_infos.py, res_infos.py, lfq_infos.py --allow-missing | rcwork_t2/<enc>_{orig,lf,lfq,resh} | root; audit what orig infos fields the envs read |
| 11 PSNR cap | exp_next/final/cap_fix.py logic | results_v1/test2/cap_fix_<enc>.pkl | root |
| 12 evaluations | eval_r3.py, seq_history.py, bc_eval.py, shift_eval.py, abr_margin.py, CQL->PPO eval | results_v1/test2/ | split test2; RC_WORK = rcwork_t2 |
| 13 report | new exp_next/test2/report.py (report.py Scorer, source bootstrap) | results_v1/test2/report.md | new |

Audit items before any job (found while planning; each must be resolved and written here):
- Which fields of Pavneet's orig infos (pixel features, scene analysis) the res / lfq envs actually read. If any,
  infos.py (orig) must run on test2 (it encodes; cheap at 320x180).
- Where eval_r3.py / bc_eval.py / the lfq eval load checkpoints from (absolute rcwork_v1 path vs RC_WORK).
- Which controller run produced budgets_prev_<enc>.csv for CQL->PPO's previous-GOP base, and that its test2
  equivalent is the final4 run of step 8.
- Every place that assumes split in {train, val, test}.

## 5. Parity gate (must pass before any test2 result is looked at)

Three v1 TEST clips go through the whole test2 path alongside the new clips, labelled split "parity" (one ED
segment, one UGC clip with cuts, one Xiph clip). Required, exactly (bit-identical where encodes are involved):
curves and first pass, budgets and causal estimates, flat flags, final4 QPs / bits / scores, previous-GOP base,
infos fields, and the per-episode rows of R3 s3, BC alone s3, final4 + shift, ABR and CQL->PPO against the stored
v1 test rows. Parity clips are excluded from every test2 analysis. Any mismatch -> stop and fix; if not exact by
Thu 11-19 10:00, test2 is dropped from the report.

## 6. Pre-registration (draft; frozen in exp_next/test2/PREREG.md before the evaluation jobs run)

- Primary (replication), per encoder: R3 - final4 at k5 on test2, paired on (GOP, level), 3 seeds averaged per
  episode, 100 dB cap, flat GOPs and level-24 hole excluded, 95 % bootstrap over clips (= uploaders).
  Replicated if the CI excludes 0 and the sign is positive. Reported next to v1 test whatever the outcome.
- Secondary (descriptive unless stated): per category; stable vs cut/gradual and their paired difference; the
  k-curve (final4 k0-29, R3 k2/k5, BC alone k0/k2/k5); R3 - BC alone per k ("RL adds over BC at k" only if the CI
  excludes 0); R3 - (final4 + shift) (x265 as in v1; x264 descriptive); R3 - CQL->PPO 540k; R3 - ABR; constant QP;
  overshoot profile; R3 with its own history; pooled v1 test + test2 (descriptive, source bootstrap).
- Cut labels: detector rule + Aayush's review of disagreements if done before any result; otherwise rule only.
  Whatever is used is fixed before results.
- If test2 has fewer than 60 cut/gradual GOPs, the cut slice is reported as descriptive only.

## 7. Compute (estimates from v1 jobs)

Data prep: decode seconds per clip; curves + first pass about 5 min per encoder for all 1,042 v1 GOPs (16-CPU
shards); final4 1-4 min per k-set; orig infos minutes. Evaluations: R3 test (265 GOPs, 3 seeds) about 35 min per
encoder with own history, so about 1-2 h per job on test2 with shards. About 10 eval jobs per encoder, about 20 in
total, plus about 10 data-prep jobs. Every sbatch is shown to Aayush first and logged in jobs/jobs.tsv.

## 8. Timeline (freeze: no new launches after Thu 11-19 12:00)

| When | What |
|---|---|
| Tue 11-17 eve | this plan; selection script + clip list (Aayush approves list) |
| Wed 11-18 am | download (Aayush, hpc-transfer1); decode; cut signals; curves; code changes + audit |
| Wed 11-18 pm | budgets, final4, rc work dirs; parity gate on the 3 parity clips; cut review (Aayush, optional) |
| Wed 11-18 eve | PREREG.md frozen; evaluation jobs submitted (Aayush OK) |
| Thu 11-19 am | stragglers / reruns before 12:00; report script |
| Fri 11-20 | report |

Risk: the plumbing (section 4) is the critical path, not compute or download. The parity gate is the guard.

## 9. Decisions needed from Aayush

1. Clip list (section 3) once generated.
2. Run the download on hpc-transfer1 (command given with the list).
3. Cut review: do it (about 30-60 min of contact sheets) or rule only.
4. Team: ask Ahhana whether her k0 / k29 models should be included; heads-up to Pavneet (report owner).
