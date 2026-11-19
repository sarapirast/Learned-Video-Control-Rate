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

## 10. Execution log (11-17)

- Download done (Aayush). Code: see docs/p2-tracker.md item 44. Submissions: exp_next/test2/submit.sh (waves).
- Wave A submitted (decode 14323981 -> merge 14324115 -> cut signals 14324116 -> labels 14324117 -> curves 14324118 /
  14324120, first-pass stats 14324119 / 14324121 -> gathers 14324122 / 14324123).
- Cut labels: option 1 (Aayush 11-17) = v1 protocol. exp_next/test2/cut_review.py --make builds round 1 (blind sheets
  for Aayush + Claude's scored strips) and round 2 (Claude only); --merge -> config/cut_review_t2.csv, then
  cut_labels.py --label is rerun. Labels only feed the stable / cut breakdown: the report reads them from
  data/t2/320x180/gops.csv at report time (the 'label' copies inside budgets.csv / rc manifests may predate the review
  and are not used).
- Wave B fix (11-17 18:20): v1's orig infos had Pavneet's experiments/scenes.py --stage apply run on them (frozen
  detector fit results_scenes/fit.pkl, fitted on v1 train splices; backup infos.pkl.pre_scenefit), which rewrites
  an[cut/flash/fade/scene/v_*]. Missing from the test2 chain -> parity caught it (ed_s05@120, NewsClip@210/@270).
  Fix: copy v1 fit.pkl (identical bytes) to rcwork_t2/<enc>_orig/results_scenes/, run --stage apply (no refit), rebuild
  lf / lfqp / resh infos from it. x264 done: orig / lf / lfqp parity OK. x265: lf job 14324253 held until apply.
- Flat GOPs (QP-50 YUV PSNR rule): 71 of 958 (70 test2) dropped from scoring, as in v1.

- Cut review done (11-17): round 1 Claude vs Aayush blind 80 % exact / 90 % cut-vs-not (kappa 0.62; v1 0.64); 19
  disagreements settled in review/settle.csv (Aayush: Claude's proposals except LyricVideo_720P-47a9 f47/f107 = cut,
  "strong black<->white transition within a single frame"). Round 2 (Claude): 50 rejected -> 3 cut / 5 gradual / 42
  no_cut; 16 both-detector -> 12 cut / 4 no_cut (precision 75 %; the 4: whip pan + auto-exposure, glitch build-up,
  single glitch frame, film flicker one frame after a cut). config/cut_review_t2.csv 159 verdicts. Relabel: test2
  843/84/3 -> 851 stable / 73 cut / 6 gradual GOPs (15 GOPs changed); parity labels unchanged (cuts parity OK).
- Parity 11-17 evening: prev x264/x265, ctrl final4/final3 x264/x265, infos orig/lf/lfqp both + resh x265 all OK.
  x264 resh blocked: final4 x264 test2 shard 7 (14324220_7) failed on d18-14 (signal 53, no log) -> resh 14324229
  DependencyNeverSatisfied.
- PREREG.md FROZEN 11-17 (Aayush; sha256 prefix eb6e94bfbdad6776, file made read-only). Ahhana messaged by Aayush about her
  k0/k29 models (secondary 10; descriptive, only if models + settings arrive before Thu 11-19 12:00).
- 11-17 evening: x264 shard 7 rerun 14327054 + resh 14324229 done -> parity gate OK for every data stage (decode ...
  infos, all 8 arm/encoder infos). seq_history.py: --split test2 added (stored rows = eval_t2 r3k5 test2, t2final4
  for the formula check, out results_v1/test2, RC_WORK must be rcwork_t2; report() refuses test2). Formula check on
  test2 (ee599 env, no encodes): 3084 (GOP, level) per encoder, max diff 1e-14. Slim infos pre-built for all four t2
  work dirs. Wave C script exp_next/test2/submit_c.sh (25 jobs; dry run shown to Aayush).
- Wave C submitted 11-17 (Aayush OK): 14327702-14327726 (25 jobs, exp_next/test2/submit_c.sh go).
- cap_fix.py: P2_DATA test2 mode (t2final4 test2/parity rows, out results_v1/test2/cap_fix_<enc>.pkl); jobs submitted 11-17.
- Wave C checks (11-17 ~21:15): eval-level parity R3 k5 324/324 and CQL->PPO 648/648 per encoder; ABR 224 rows and
  shift 108/108 equal to v1; cap_fix parity GOP equal to v1's. bc_eval --check (offset 0 + mean 0 + bit cap = final4
  stored row) 30/32 x264, 31/32 x265: every mismatch is Animation_720P-57d9@210, k0, L36/L42 (final4 overshoots an
  8-15 kbit budget; the BIT re-cap then raises QPs from frame 8). Replay of that GOP: recap '' and 'full' reproduce
  final4 exactly, 'bit' does not (masked or not) -> a property of the pre-registered bit-cap rule (R3 / BC / shift),
  not of the test2 pipeline; v1's 12-episode check never sampled such a GOP. seqhist x264: 3427/10320 rows equal
  to stored (episodes with stored history all equal).
- 11-17 23:10: all wave C jobs done (bc25_x265 14327721, seqhist_x265 14327724, cqlppo_x265 14327725 exit 0; seqhist
  x265: episodes without own history reproduce the stored rows: all). report.py re-run -> results_v1/test2/report_test2.md
  complete, gate PASSED. Primary replicated on both encoders (x264 +0.044 [+0.008, +0.082], x265 +0.187 [+0.138,
  +0.235]). No deviation from PREREG; amendments none. Open: Ahhana k0/k29 (secondary 10) only before Thu 11-19 12:00.
- 11-18: Ahhana's R3 k0 / k29 (x264, s3-5, 180k) received before the freeze (PREREG secondary 10). Her eval.pkl args
  match the R3 recipe; her shifts_smooth.json equals ours on every shared key (new key x264|29|pooled). New
  exp_next/test2/eval_ahhana.py (eval_t2.py untouched): parity = her models through our v1 x264_resh env on v1 val
  must equal her stored eval.pkl val rows; then test2. Wave D (exp_next/test2/submit_d.sh, Aayush OK 11-18):
  parity 14347706 (k0) / 14347708 (k29), test2 14347707 (k0) / 14347709 (k29). Test2 rows read only after parity.
- 11-18: 14347709 (r3k29a test2) FAILED on b10-21: seed 5 stalled 7 min, then 4/3440 ffmpeg decode failures (empty
  stderr); s3/s4 ran clean but rows are written only at the end. b10-21 -> bad_nodes; rerun 14351320 (Aayush OK).
- 11-18 14:45: rerun 14351320 OK (0 errors, a03-17). report.py re-run, gate PASSED. Secondary 10 (x264, descriptive):
  R3 (Ahhana) - final4 k0 +0.097 [+0.051, +0.149] *, k29 +0.032 [+0.005, +0.061] *; k0 vs BC alone (ours) +0.647 *,
  vs CQL->PPO +0.302 *. test2 complete; no PREREG deviation.
