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
- [x] (11-04, item 13: `features/fp_bits.parquet`; richer stats `fp_stats.parquet`) First-pass bits (pilot: ultrafast at QP 32; Pavneet: QP 30; run on P1's frozen settings) -> work-queue item 13
- [x] (11-04, item 13: `rd/rd_native.parquet`, `rd_frames.parquet`; STATIC curves 11-05 `rd/static_rd.parquet`) Native R-D curves, QP 18-50 per GOP (item 13), both PSNR conventions (`rd_native.parquet`). Note: pilot "native" = IDR at q-3, P at q.
- [x] (11-04, item 14: `budgets.csv`, 4 levels QP 24/30/36/42) Budget table: 3-4 levels per GOP, `how_set` recorded (`budgets.csv`); NOT from the GOP's own encodes (item 14)
- [x] (11-04, item 14: `docs/budget-estimator-v1.md`) Causal base-QP estimator, fit on train, MAE in QP on val (item 14)
- [x] (11-04/05: `results_v1/baselines_v1_table.md`, incl. STATIC via `scripts/static_rd.py`) Baselines (Pavneet's pipeline on v1 already gives his versions; P2's on P1's settings still to do): native constant QP; fixed pattern with hindsight shift (reference); causal fixed pattern (pilot's naive causal version went over budget on 91% of GOPs, so use the estimator shift or a budget shield)

### Week 1 checkpoint
- [~] Manifest, YUV, GOP table, feature files, budget table, R-D curves and estimator all exist and the README describes them
  (11-05: all exist; README NOT yet regenerated for rd/, budgets, fp_stats, static_rd -> extend `scripts/data_readme.py`)

### Later weeks
- [x] W2: native QP, ABR+VBV, CRF and two-pass (references), `rc-lookahead` over k (mb-tree off; defaults separately), fixed pattern (both versions); baseline table in results-row format
  IN PROGRESS 2026-11-04 17:45 (Aayush asked): scripts/baselines_v1.py, P1 settings, leak-free budgets, both encoders,
  val+test: cqp_best (all splits, also P3's search start), cqp_est (estimator, constant), abr_vbv (1-pass ABR with
  VBV = one GOP, rc-lookahead k in 0/2/5/10/29; mb-tree off), two_pass, crf_best (hindsight), fixed_best (pattern I
  q-6, P q-3..q+3, hindsight base) and fixed_causal (estimator base at k). Jobs 13732323/25/26/27 + gather
  13732328 -> results_v1/baselines_v1.parquet + results_v1/baselines_v1_table.md (also includes controller v1 rows).
  Smoke (2 val GOPs): ABR+VBV over budget on 50-100% of GOPs; crf_best/fixed_best +1.5..+3.3; fixed_causal
  overshoots almost always (estimator 3-4 QP off, no feedback). x264/x265 need integer --bitrate/--vbv-*.
  DONE 17:38 (17/17 OK; counts complete). TEST score (% GOPs over), x264 / x265: fixed_best +2.62 (0.5) / +1.96 (0);
  cqp_best 0 / 0; crf_best -1.04 / -1.46; two_pass -4.59 (3%) / -12.23 (45%; 86% over at level 42); controller v1 k5
  -0.94 / -0.20; abr_vbv -27..-35 (48-83%) / -26..-27 (47-91%), no k effect; cqp_est k0->29 -90 -> -31 / -103 -> -26;
  fixed_causal -100 -> -37 / -115 -> -33. cqp_best also for all train GOPs (P3's search start).
  CORRECTION 11-05: fixed_* used a linear ramp, not the pilot's STATIC step; relabelled ramp_best/ramp_causal.
  STATIC itself (scripts/static_rd.py, every GOP x base q 12-51, all splits): test static_best +0.14 / -1.81,
  static_causal -85 -> -30 / -98 -> -26 (k=0 -> 29). The ramp beats STATIC by ~2.5-3.8 points.
- [x] W3: gain breakdown by GOP class; QP trajectories around cuts; before vs at/after cut measurement; written hypotheses
  (done 11-11 on the quality-at-budget search + final4; see item 22)
- [x] W4: split k-curves; adaptive gate (k=0/k=1 sub-policies; fixed rule on stable + learned around cuts)
  (done 11-11 as analysis of existing runs: results_v1/w3/class_kcurves_<enc>.md; gate bound ~0, see item 22.
  k=0/k=1 sub-policies not trained: no learner beats the controller on any class, so nothing to gate to)
- [x] W5: quality vs delay figure; report section
  (done 11-11, Aayush: "do W5 next"; no encodes) scripts/w5_numbers.py -> results_v1/w5/w5_numbers.md + curve_points.csv
  (curve points, W4 hypothesis tests H1-H8, adaptive-lookahead gate bound, final4 - final3 by k);
  scripts/w5_figures.py -> results_v1/figures/w5_quality_vs_delay{,_by_class}.{png,pdf}; report section
  docs/report-w5-quality-vs-delay.md (every number cited to its results file); Outcome lines filled in
  docs/w4-hypotheses.md (predictions untouched). Scorecard: H1 supported; H2 controller yes / residual no; H3
  falsified (lookahead closes 34-48% of the k0 gap, more than predicted); H4 mostly falsified (history removes the
  k29 drop); H5 falsified (residual below its controller); H6 supported; H7 not supported (equal); H8 mostly
  supported. Adaptive k2/k5 gate: -0.02 / -0.05 dB vs fixed k5 (falsified). New lead: x265 level 42 res@hist -
  final4 +0.15 [+0.03, +0.30] (pooled k; check per k). Dataviz validator not run (no node on CARC); palette = the
  skill's validated reference slots 1-5.

## Week 3 (decided 2026-11-09 with Aayush)

- [x] 21. LEAK-FREE SEARCH (rerun Pavneet's hindsight hill-climb without the budget leak). Decisions (Aayush 11-09):
  all splits (train+val+test; train is needed for BC/CQL/MPC on the leak-free setup), both encoders, budgets from
  budgets.csv (4 levels, lowest = QP 24), P1 frozen encoder settings, start = linear ramp (I q-6, P q-3..q+3) at the
  hindsight base q that fits the budget, action range +-5 (was +-3), 300 encodes x 2 seeds as before.
  Est. cost ~460 alloc CPU-h (x264 ~160, x265 ~300; from sacct of last week's search x2 for 4 levels). Steps:
  - [x] 21a. code: leak-free arm RC_ARM=lf in repo-pavneet (local commit bf01223 on v1-data): rclib/config.py (levels,
    actions -5..5, QP 11-51, ramp), codec.py (P1 settings: preset medium, psy off, x264 --qp 31 --ipratio 10
    --pbratio 10, slice bits only), search.py (lf_start: ramp at the hindsight base q, same bisection as ramp_best).
    Infos: tools/lf_infos.py -> rcwork_v1/{x264,x265}_lf/results_infos/infos.pkl (curves from rd_native, budgets.csv;
    fp_bits/an still orig-harness). Parity tools/lf_parity.py: start plan == ramp_best 40/40 (q, bits, PSNR, score).
    Frame rate does not change slice bits under forced QP (25 vs 30 fps identical), so the harness's fixed 30 fps is
    fine. One-GOP run: ~0.17 s/encode x264, ~410 CPU-s per GOP (4 levels x 2 seeds x 300). jobs/rc_v1_submit.sh: arm
    lf (AB = search only, RC_SPLITS, 8 h limit), RC_PART for partitions. Debug smoke 13875602 (x264) / 13875603 (x265)
    in rcwork_v1/*_lf_smoke (2 val GOPs). Aayush approved: if smoke OK, submit full x264 + x265 on main,oneweek.
  - [~] 21b. Smoke 13875602/03 OK (2 val GOPs: x264 ~300 s/GOP, x265 ~460 s/GOP; every level improved on its start;
    smoke dirs removed). FULL submitted 2026-11-09 ~10:45 on main,oneweek (Aayush approved): x264 train 13878135
    (+gather 36), val 13878137 (+38), test 13878139 (+40); x265 train 13878141 (+42), val 13878143 (+44), test
    13878145 (+46). Revised cost from smoke: ~100 (x264) + ~155 (x265) alloc CPU-h. Output:
    rcwork_v1/{x264,x265}_lf/results_search/search_{train,val,test}.pkl; report: experiments/search.py --report
    (RC_ARM=lf) -> results_v1/<codec>_lf/. Note for analysis: level 24 has big gains on some GOPs (snow_mnt@60 13 -> 25)
    where the budget sits below the QP-18 end of the curve, so the score is extrapolated there; report separately.
    10:50: x264 train shard 0 (13878135_0) died on d05-07 after 92 s, signal 53, no stdout (same signature as d05-06
    on 11-03; d05-07's 11-05 entries had expired) -> d05-07 re-added to bad_nodes. With Aayush's OK: rerun 13878948
    (shard 0), new gather 13878949 (afterok:13878948, afterany:13878135), old gather 13878136 cancelled.
    DONE: all 30 search shards COMPLETED (x264 train shard 0 via 13878948). 4 gathers (13878142/44/46, 13878949)
    died on d05-06 (signal 53, no stdout) -> d05-06 re-added to bad_nodes; the merges (pure pickle merge, <1 min)
    were run on the interactive node 13896535 on 11-09 14:16. All 6 search_*.pkl complete: 1042 GOPs x 4 levels each.
  - [x] 21c. gather + search report (ceiling per split/level/class). Gather done (above). ISSUE before the report:
    ~4-5% of GOP x level rows have scores < -100 (down to -1e34 on train; test min about -2000/-4300). These are
    near-static/flat GOPs (e.g. ed_s07, LyricVideo_720P-2d24, Animation_360P-3e40, TelevisionClip_720P-1862;
    constant-QP PSNR ~59 dB even at QP 50, ~80 dB at QP 18). The ramp/search plans have a lower mean frame PSNR at
    more bits than CQP, so "bits saved at equal PSNR" is hugely negative; not above the curve range. Medians are
    sane (best ~7-9, start ~1-3 on every split/level). Need a rule (exclude flat GOPs / median / clip) before means.
    RESOLVED 11-09 (Aayush: exclude by the QP-50 rule): scripts/flat_gops_v1.py -> data/v1/320x180/rd/flat_gops.csv;
    flat = CQP YUV PSNR at QP 50 > 45 dB on EITHER encoder (normal content max 41.0, next 45.1). 60 GOPs, 14 clips
    (train 35, val 12, test 13). Cause: grayscale GOPs, chroma MSE 0 on 48 of 60 (luma PSNR @QP50 normal ~25 dB),
    so capped U/V PSNR dominates the mean-of-frames YUV PSNR. After exclusion every test/val row >= -36.
    Both W3 scripts drop them (RC_KEEP_FLAT=1 keeps). Report = results_v1/w3/search_gain_<codec>_lf.md section 1
    (Pavneet's search.py --report has no filter, not run). Test lf search (x264 / x265): best 10.3 / 10.0, ramp
    start ~2.4 / ~1.9, gain by class stable +7.0 / +7.5, cut +10.6 / +10.5, gradual +13.7 / +11.8.
- [x] 22. W3 analysis: gain by GOP class (search, baselines, learned methods, controller), search QP trajectories
  around cuts, before vs at/after cut; scripts written first on last week's search logs, rerun on 21's logs
  11-09: scripts/w3_search_gain.py <codec> <arm> -> results_v1/w3/search_gain_<codec>_<arm>.{md,csv} (+ search_cuts_*.csv):
  gain by class, offsets around cuts (residual vs stable-GOP mean at same frame/budget, clip bootstrap), before
  (c-3..c-1) vs at/after (c..c+2). Run on orig (leaky budgets, Pavneet settings), val+test single-cut GOPs (65 x 2):
  x264 before +0.65 [+0.43, +0.83] QP (spend less), at/after -0.65 [-0.98, -0.28] (spend more), 46% of the change
  magnitude is before the cut; x265 +0.16 / -0.80, 40%. Strongest single frame: the cut frame (-1.3 QP x264) and
  the frame just before it (+1.0). Caveat: magnitude, not gain; a score split needs counterfactual encodes
  (best plan with only the before- or only the after-changes) -> planned once lf is in (~1,100 encodes, minutes).
  11-09 lf rerun (flat GOPs excluded): before/after cut on val+test, x264 before +0.98 [+0.66, +1.26] / at-after
  -1.06 [-1.49, -0.54] QP, 43% of the change before the cut; x265 +0.47 / -0.84, 39%. Same picture as orig.
  methods_by_class_<codec>_lf.md part B: captured_% is not useful for the causal baselines (their scores are
  very negative, e.g. -900%); read the score columns. Still to do: level-24 split, counterfactual encodes.
  11-09: scripts/w3_methods_by_class.py <codec> [orig|lf|both] -> results_v1/w3/methods_by_class_<codec>_<arm>.{md,csv}.
  Two measures: captured_% = method score / search score (from best CQP = 0, pattern-independent) and gain_share_%
  = (method - start) / (search - start) = Pavneet's "share of search gain" (reproduces the headline: lagr k0 75% x264,
  66% x265). Part A (orig, test): lagr k0 captures 51% (x264) / 43% (x265) of the search's score; on CUT GOPs BC and
  CQL->PPO at k=0 are below constant QP (-64 / -87% x264) and lookahead fixes most of it (BC cut 31% at k=10-29),
  Lagrangian is flatter (cut 34% k0 -> 47% k5 x264). Gradual: 10 GOP x budget per cell, too noisy. Part B (lf:
  baselines + controller vs leak-free search) runs once search_test.pkl exists.
  TODO: rerun both scripts on lf when 21 is done; counterfactual before/after-cut encodes (proposal).
  11-11 DONE ON THE QUALITY-AT-BUDGET METRIC (Aayush: "do the bookkeeping and W3/W4 first"; no encodes):
  (1) scripts/w3_search_gain.py got arm lfq (dB) -> results_v1/w3/search_gain_<enc>_lfq.md. TEST gain (best - start,
      dB): x264 stable +0.44 [+0.39,+0.50], cut +0.49 [+0.43,+0.56]; x265 +0.45 / +0.50. The search's final score is
      a bit LOWER on cut GOPs (x264 +0.25 vs +0.30 stable). Around a single cut (val+test, 64 GOPs x 4 budgets): frame
      c-1 +0.51 QP (save), cut frame -0.68 (spend); before c-3..c-1 +0.20 [+0.03,+0.32], at/after -0.22 [-0.40,-0.03];
      48% of the change magnitude is BEFORE the cut (x265 46%). Same picture as the lf/orig arms.
  (2) NEW scripts/w4_class_kcurves.py <enc> (reads lfq_compare_<enc>_final4.csv + lfq_compare_<enc>.csv) ->
      results_v1/w3/class_kcurves_<enc>.{md,csv}: A score by class x k (search, final4, final3, all learners);
      B split k-curves (score(k) - score(k0), paired; cut - stable); C each method - final4 per class; D gate bound
      (per class pick the best method on val, apply on test; class is hindsight so this is an upper bound).
      TEST results:
      - Lookahead helps cut GOPs about twice as much, for the controller: final4 k5 - k0 stable +0.18 [+0.10,+0.27],
        cut +0.38 [+0.24,+0.55], cut - stable +0.20 [+0.04,+0.37] (x264); x265 +0.18 / +0.38, +0.19 [+0.00,+0.40].
        k5 is enough: k29 is no better (cut: x264 -0.34 at k29 vs -0.28 at k5; x265 -0.38 vs -0.26).
      - Learners' k-curves are mostly base-QP repair: bc k29 - k0 +2.4 (stable) / +3.2 (cut) dB on the budgets.csv
        base, +1.0 / +2.2 with the previous-GOP base (x264).
      - Per class vs final4: every learner is below final4 on STABLE GOPs at every k. On CUT GOPs the residuals tie
        final4 (x264 res@hist cut k0 +0.04 [-0.09,+0.20], k2..k29 within +-0.03; x265 res@hist cut k29 +0.04
        [+0.00,+0.08], the only CI >= 0, one of ~90 comparisons); bc/bc@prev tie at k29 on cut GOPs.
      - Gate bound (D): x264 +0.01 [-0.02,+0.04] at k0 (picks res@hist on cut), 0 elsewhere; x265 0 at every k.
        => a "fixed rule on stable + learned around cuts" gate has nothing to gain with the current learners.
      Gradual: 16 test GOP x budget rows, too few to read.
  WRITTEN HYPOTHESES (for W5 / report; to test, not facts):
      H1 The search's cut handling is half anticipation (save just before the cut) and half reaction (spend on the
         cut frame), so k=0 can at most reach the reaction half; matches final4's larger k-gain on cut GOPs.
      H2 Beyond k~5 the controller gains nothing because its rate model averages first-pass cost over the visible
         frames; with a cut late in the window that average misprices the frames before the cut (k29 cut < k5 cut).
         Test: per-cut-position split of final4 k5 vs k29.
      H3 The learners' deficit is budget handling (base QP + spend tracking), not cut handling: they tie the
         controller on cut GOPs at k29 but lose on stable GOPs, where a model-based spend rule is near-optimal.
      H4 A learner would add value only as a residual specialised to cut GOPs (cut flag in the lookahead), trained
         on cut GOPs only; current residuals spend their capacity on stable GOPs and lose there.
- [x] 23. Reward shaping (potential-based, predicted overshoot) on x264, Lagrangian PPO (+ CQL->PPO) k=0/5, 3 seeds,
  old setup (orig arm). Aayush 11-09: run it ourselves; tell Sara/Pavneet only if the results look good.
  Code (local commit 9e031fe on v1-data): rclib/env.py shaping F = shape x (Phi(s') - Phi(s)), Phi = -pen x predicted
  overshoot % / 10 (pen = lam 4 for lagr, 2 for relative), prediction = spent + remaining frames at the default plan
  from its real encode (info static bits; Phi(s_0) exact), calibrated by actual/predicted so far (slopes 6.8 I /
  5.0 P, weight t/(t+3)); Phi relative to start and 0 at the end -> shaping terms sum to exactly 0 (checked, also
  stored per episode as shaping_sum). First version (constant-QP table, uncalibrated at t=0) gave a spurious
  step-0 reward (+0.5), fixed. experiments/rl.py --shape (run names ..._shape1_sN). Quick end-to-end run OK.
  Submitted 11:06: array 13880327 -> BROKEN (relative RC_RUNS path, job cds first -> empty args -> rl.py defaults
  = existing cql_ppo_k5_s0, skipped; nothing overwritten, checked); cancelled. Fixes: rc_v1_submit.sh makes RC_RUNS
  absolute + checks it; rc_v1_rl.sbatch exits 2 on an empty run line. RESUBMITTED 11:18 (Aayush OK): array 13881998
  (runs_v1/shape.txt, 12 runs: lagr + cql_ppo x k0/5 x seeds 0-2), main,oneweek, ~80 alloc CPU-h.
  RESULT (11:40, 12/12 OK, ~17 min each): scripts/shaping_compare.py -> results_v1/shaping_compare_x264.{md,csv}
  (paired shaped - unshaped, same method/k/seed/GOP x budget, clip bootstrap). TEST score base -> shaped:
  cql_ppo k0 -0.17 -> 4.10 (+4.27 [+3.30, +5.19]; over-rate 37.5% -> 3.8%; all 3 seeds; val +3.49);
  cql_ppo k5 3.75 -> 3.79 (+0.04, n.s.; over 13.8% -> 11.1%); lagr k0 4.67 -> 3.15 (-1.52 [-1.90, -1.18]); lagr k5
  4.10 -> 2.42 (-1.68); val the same direction. Lagrangian loses SAVING (-1.6) and becomes more conservative (over
  2.9% -> 0.8%): it was already in budget, and the shaping penalises early spending (which is good here) right
  away while refunding it only at the end. CQL->PPO: shaping removes the k=0 overshoot, and its k0 -> k5 "lookahead
  gain" (+3.9 unshaped) disappears (shaped k0 4.10 vs k5 3.79), i.e. that gain was budget handling, not lookahead.
  Best score is still unshaped Lagrangian k0 (4.67). Caveats: orig arm (leaky budgets), one shaping weight (1.0),
  last-checkpoint selection. Aayush to decide whether this counts as "good" for telling Sara/Pavneet. Compare with the existing orig runs (same method/k/seed, no shaping) in
  rcwork_v1/x264_orig/results_rl/<run>/eval.pkl.
  - [x] 23b. FOLLOW-UP (Aayush 11-09): why shaping hurts Lagrangian PPO. Shaped runs were fresh (same CQL init), and
    gamma=1, so not a theory issue; train curves plateau ~3.5 vs ~4.5 unshaped. Suspects: GAE lambda 0.95 (late
    refund under-credited), critic initialised from unshaped Q, and lagr's shaping is 2x stronger (pen = lam 4).
    runs_v1/shape2.txt: lagr k0 x 3 seeds x {shape 0.5; shape 1 + --gae-lambda 1}; new flag in repo-pavneet
    experiments/rl.py (uncommitted until all done, per Aayush). Submitted 13902049 (6 tasks, ~30 alloc CPU-h).
    Then: extend scripts/shaping_compare.py to these runs and report.
    RESULT (13902049, all 6 COMPLETED; results_v1/shaping_compare_x264.md): NEITHER FIX RECOVERS IT. Test, vs
    unshaped 4.67: shape1 3.15 (-1.52), shape0.5 3.38 (-1.29 [-1.69, -0.92]), shape1+gae1 3.35 (-1.33 [-1.72,
    -0.98]); val the same (-1.19 / -1.08 / -1.29). Each fix gains only ~0.2 of the 1.5 lost; all 3 seeds below base.
    So neither shaping strength nor GAE credit is the main cause. Remaining candidate: the critic starts from the
    unshaped CQL Q (off by the shaping offset from step 0) and 60k steps don't fix it. Not pursued: conclusion =
    shaping helps only the unconstrained CQL->PPO (budget handling); keep Lagrangian unshaped.
- [~] 24. Loose ends: data README for rd/budgets/fp_stats/static; merge fp_bits/fp_stats into frames.parquet;
  3 uncertain frames in decimated clips; repo + project2 sync. (Aayush: delete data/v1/320x180/rd/smoke/; CARC ticket)
  11-09 DONE: (a) frames.parquet now has first-pass columns (scripts/build_features.py): fp_bits = x264 QP 32 default,
  fp_bits_<enc>_q<30|32>, fps_<enc>_<tex|mv|misc|intra|inter|skip> at QP 32; old columns unchanged (checked);
  feature-spec row updated. (b) docs/data-v1-README.md has an "Encoder-derived data" section (scripts/data_readme.py,
  run with the project env): file table, CQP curve medians + non-monotonic steps (58 / 50 of 33,344), budget ratios
  and flagged q_fit per level, first pass vs real bits. (c) The 3 unreviewed frames were Gaming_360P-3eb6 f19/38/200
  (train, hist-only): all clear hard cuts (cinematic <-> top-down HUD view), added to config/cut_review_v1.csv as
  claude-only round 3; labels unchanged (gops.csv identical), README now 270 verdicts. (d) repo + project2 sync: held
  until the lf search results are in.
- [x] 27. (superseded 11-10 by 30f / 31 C2) RESIDUAL RL ON THE CAUSAL CONTROLLER, leak-free (EXPERIMENTS P3 / proposal D). Decided 2026-11-09 with
  Aayush (we cover Sara's RL load this week; data v1 canonical): Pavneet's pipeline, new arm RC_ARM=res; frame QP =
  P2 controller (setting 0.97:3:0.3:2:3:4:0:1, rclib/controller.py = copy of scripts/controller_real.py decide) +
  offset -3..+3; reward = Lagrangian (lam 4) relative to the controller's own result per GOP x level x k; lagr PPO
  settings (lr 1e-4, 60k steps), no offline data, policy starts at P(offset 0) = 0.7; flat GOPs dropped; first pass =
  P2 fp_bits (P1 settings, QP 32). Sweep x264 k 0/2/5/10/29 x 3 seeds, then x265 if it works.
  - [x] 27a. code (uncommitted until all done): rclib/config.py (arm res), rclib/controller.py, rclib/env.py,
    rclib/offrl.py (slim without static), experiments/rl.py (method res), tools/res_infos.py, tools/res_parity.py.
    x264 res infos built (982 GOPs: train 590 / val 140 / test 252; train controller results pending).
    PARITY: offset 0 replays the published controller exactly, 144/144 episodes (val k 0/5, test k 2/10/29).
  - [x] 27b. controller on TRAIN (reward baseline): controller_real.py --split train --tag final2 (~6 CPU-h)
    13902696 (shards 1-7 OK; shard 0 hung on d05-08 -> cancelled, d05-08 to bad_nodes) + rerun 13905875 OK.
    res infos rebuilt: 982 GOPs, controller results for all.
  - [x] 27c. rebuild res infos with train; debug smoke of rl.py --method res --quick
    Train parity 48/48. Smoke 13907877 (debug) FAILED in 27 s: --quick reads results_infos_quick/ (fixed: symlink
    rcwork_v1/x264_res/results_infos_quick/infos.pkl -> ../results_infos/infos.pkl). Then checked locally on the
    interactive node: training (2 envs, quick) runs, starts at P(0)=0.7, 1,536 steps (train score -1.54, 2% over);
    12 eval episodes in-process reproduce the controller exactly (argmax still offset 0 after so few steps), all
    fields present (qps, ctrl_qps, k, static_score = controller score).
  - [x] 27d. sweep x264 (15 runs, ~80 CPU-h) -> compare with controller + lf search, by class, flat excluded
    Submitted 2026-11-09 (user went straight to the sweep, no 2nd smoke): array 13918676, runs_v1/res.txt,
    main 16 CPU/48G/4 h, excl d05-06/07/08. Then: python -I scripts/res_compare.py x264.
    PARTIAL (k0, k2 done, 11-09 ~19:20): score res - ctrl +2.78 [+1.46, +4.28] (k0), +1.59 (k2), over 4.3% -> 1.1%.
    BUT IT GAMES THE SCORE: scripts/res_offsets.py -> results_v1/res_offsets_x264.md: offsets are 0 or +3 (87% of
    frames at +3 at k0, never negative), i.e. it raises QP everywhere; budget use 0.66 vs controller 0.87 (search
    0.86-0.92); PSNR at the budget vs best CQP at the budget: res -2.04 dB, ctrl -0.81 -> res - ctrl -1.23 [-1.38,
    -1.10] dB (k0), -0.67 (k2). The score (saving at equal PSNR vs the CQP curve, minus over penalty) does not
    penalise unused budget, so spending less is free and avoids the overshoot penalty. res_compare.py now reports
    budget use and dPSNR@B. TEAM ISSUE: the project metric measures R-D efficiency, not quality under the budget;
    affects every result (search also leaves 8-14% unused). Next: reward = dPSNR@B (or score + under-use term), rerun.
    FINAL (all 15 COMPLETED, results_v1/res_compare_x264.md): score res - ctrl k0 +2.78, k2 +1.59, k5 -0.20 (n.s.),
    k10 +0.20 (n.s.), k29 +2.72; dPSNR@B res - ctrl ALWAYS NEGATIVE: -1.23 / -0.67 / -0.12 / -0.38 / -0.40 dB; budget
    use 0.66 / 0.76 / 0.86 / 0.80 / 0.78 vs ctrl 0.87-0.89. At k5/k10 seeds disagree (mean offset -0.7..+1.9). Verdict:
    with the old score as reward, the residual learns to under-spend; redo with a quality-at-budget reward.
- [ ] 25. Optional: MPC at k=0/2/5/10/29 on the leak-free setup after 21 (needs causal base QP), ~30 CPU-h x264
- [x] 26. W3 written hypotheses for the W4 k-curves
  11-09 18:30, before any res-sweep result: docs/w4-hypotheses.md, H1-H8 with predictions, evidence (W1-W3 files),
  falsification rules and an empty Outcome line each. Key: steep-then-flat by k=2-5; cut GOPs gain more and longer;
  lookahead closes <= 20% of the gap to search (back-of-envelope: ~11% of the search gain needs advance sight of a
  cut); k29 < k5; residual beats controller most at k0; leak-free removes the orig arm's flat k-curve.

- [x] 28. Feature gates (Aayush 11-09: which features would actually predict what the controller/learner needs).
  No encodes, interactive node. (a) scripts/prevgop_gate.py -> results_v1/gates/prevgop_gate.md: the PREVIOUS GOP of
  the same clip (budgets are clip-level, GOPs consecutive; unused anywhere so far) cuts the k=0 base-QP error on test
  from 3.67 to 2.36 QP (x264, realistic: from P2's controller run on GOP n-1; -1.31 [-1.72, -0.93]) / 2.24 (ideal);
  x265 ideal 3.69 -> 2.21. k=0 + previous GOP beats k=2 without it (2.58). Still -0.3..-0.5 at k=2/5. Rows = 933 GOPs
  with a predecessor (first GOP of a clip unchanged). (b) scripts/slope_gate.py -> results_v1/gates/slope_gate.md:
  P-frame rate slope varies a lot (x264 s 3.7 / 5.0 / 8.2 QP per halving at p10/50/90; controller uses one s = 5.5).
  Oracle per-frame slope would cut the GOP error left after calibration at QP 32 from 7-23% to 1.4-9% (test); first-
  pass make-up (tex/skip fractions, 2-point fp 30/32) recovers only a small part (mainly the p90 tail at QP 42:
  75% -> 50%). Strongest single predictor: the 2-point first-pass slope (rho +0.38/+0.59) even with QP 30/32 only 2
  apart -> a wider first-pass pair (e.g. 26/38) is the cheap next test. Next if pursued: previous-GOP calibration
  in the controller (c_P start) and as a res-arm obs feature.

- [x] 29. Budget-aware RESCORING of every stored result (Aayush 11-09; no encodes). scripts/rescore_budget.py ->
  results_v1/rescore_budget/ (rescore_<codec>.md, summary_<codec>.csv, episodes_<codec>.parquet). score_B = project
  score with max(bits, B) in place of bits (unused budget counts as spent); dPSNR_B = PSNR - CQP PSNR at exactly B.
  Old scores reproduced exactly (max diff ~1e-13). x264 test: search lf 10.29 -> -2.42 (dPSNR -0.12 dB, use 0.89);
  orig Lagrangian k0 4.68 -> -11.42 (use 0.86; was 'best learned'); orig CQL->PPO k10 3.25 -> -3.48 (use 0.94, but
  13-38% of GOPs over); orig BC k29 3.92 -> -4.76; controller v1 k5 -0.85 -> -17.47 (use 0.90, p10 0.71); residual
  k0 -1.22 -> -74.4; best hindsight baselines crf_best -2.84, ramp_best -3.72, cqp_best -7.90 (integer QP: 1 QP ~ 12%
  bits, so it leaves ~7% unused). x265 same picture. => Under quality-at-budget nothing beats a (fractional) constant
  QP at the budget; most of every method's 'saving' was unused budget; the ranking changes (Lagrangian falls, CQL->PPO
  rises but overshoots often, so the soft over penalty matters more under score_B). Team issue: metric + ceiling.

- [x] 30. REDO ON THE QUALITY-AT-BUDGET METRIC (Aayush 11-09: proceed with Step 0 as decided: metric/reward =
  dPSNR_B with 0.17 dB per 1% over (soft constraint), data v1 + leak-free budgets, Pavneet's pipeline). Plan, in order:
  (1) metric plumbing; (2) references: controller margin retune on val + new search (ceiling AND BC/CQL teacher);
  (3) BC -> CQL->PPO -> Lagrangian on the new search, k 0/2/5/10/29 x 3 seeds, x264 then x265; residual RL on the
  retuned controller in parallel; (4) W4 analysis + gate; (5) prev-GOP / wider first pass if time; (6) report.
  - [x] 30a. code (repo-pavneet, uncommitted): rclib/metrics.py METRIC (RC_METRIC, default dpsnr for RC_ARM=lfq):
    score() = PSNR - PSNR_CQP(B) - 0.17 x %over; psnr_at_bits, dpsnr_budget, score_old. rclib/config.py arm lfq (= lf,
    own work dir). jobs/rc_v1_submit.sh AB accepts lfq. Work dirs rcwork_v1/<codec>_lfq link the lf infos/clips/gops.
    Local test: 40-encode search on one val cut GOP: start (use 0.97) -> +2.34 dB at use 0.995; psnr_at_bits matches
    scripts/rescore_budget.py. NOT YET: env reward (rclib/env.py line ~314 computes the score by hand), report scripts.
  - [x] 30b. search lfq, both encoders, all splits (~255 alloc CPU-h; like 21). SUBMITTED 11-09 19:45 (Aayush OK):
    x264 train 13932337 (+gather 38), val 13932346 (+47), test 13932348 (+49); x265 train 13932350 (+51), val 13932352
    (+53), test 13932354 (+55). Out: rcwork_v1/<codec>_lfq/results_search/search_<split>.pkl. If a gather dies
    (signal 53 on d05-* last time), merge interactively as in item 21. Then: rescore check + W3 scripts on lfq.
    11-10: 26 of 30 shards OK; 4 FAILED: x264 val s1 (d11-24, signal 53, no stdout), x264 test s3 + x265 train s7
    (b05-16: every ffmpeg decode failed from 22:06, empty stderr), x265 test s1 (a02-11, x265 version guard). Shards
    cache only whole shards -> rerun from scratch. b05-16, d11-24, a02-11 -> bad_nodes. Gathers done: x264 train,
    x265 val. Stuck gathers 13932347/49/51/55 cancelled. RERUNS (Aayush OK, 11-10 ~17:05): x264 val s1 13989249
    (+gather 50), x264 test s3 13989251 (+52), x265 train s7 13989253 (+54), x265 test s1 13989255 (+56).
    13989255 died again on d18-14 (signal 53, no stdout, 13 min) -> d18-14 to bad_nodes; rerun 2 (Aayush OK):
    13989829 (+gather 13989830; 13989256 cancelled).
    11-10 ~19:25: ALL 6 search pickles gathered (x264 + x265, train/val/test). Search DONE; rescore check + W3 open.
  STANDING APPROVALS (Aayush, 2026-11-10 ~18:30, while he is logged off; for this session's item-30 work only):
    (1) x265 controller: pick the setting by the x264 rule (best val dPSNR_B score pooled over k, flat excluded,
        scripts/controller_dpsnr.py x265 tune3) and run final3 on train/val/test (3 x 8 shards);
    (2) x265 learners 30g: after the x265 gathers, lfq_infos x265 job + 45-run array (runs_v1/lfq.txt, RC_TLIM 6:00:00);
    (3) x265 residual RL 30f: after x265 final3 train, resq infos + parity, then 15 runs (runs_v1/res.txt);
    (4) node-failure reruns: resubmit a shard/run/gather that dies on a bad node, once per item, node excluded.
    If the x264 learners look broken (crashes / clearly broken training in the first runs): CANCEL the rest of the
    array, diagnose, write up here; no resubmit without Aayush. Still NO commits until everything is done.
  NEXT SESSION, in order (each sbatch needs approval):
  - [x] 30c. env reward under METRIC=dpsnr (repo-pavneet rclib/env.py result(), ~line 310): score is computed by hand
    (sav - OVER_PENALTY x over) -> use metrics.score; 'relative' = (score - base score) / REWARD_SCALE and
    'lagrangian' = (sav - base saving - lam x over) / REWARD_SCALE are in % units: for dpsnr use dPSNR_B - base
    dPSNR_B - lam_dB x over with lam_dB ~ 0.34 (= lam 4 / 2 x 0.17) and REWARD_SCALE ~1 (dB is ~10-20x smaller than %).
    Base entries need dPSNR_B: info['static'] (not in lf infos) / info['ctrl'] (res_infos.py stores no psnr: add
    psnr_yuv from final2 parquet). Also _phi/shield use OVER_PENALTY (only for shaping/shield; parked).
    DONE 11-10 (repo-pavneet, uncommitted): env.REWARD_SCALE = 1 under dpsnr; result() uses metrics.score and, for
    'lagrangian', dPSNR_B - base dPSNR_B - lam x %over (st['dpsnr']); rows also carry dpsnr_b, score_old, use;
    _phi uses OVER_PENALTY_DB under dpsnr. rl.py: lam = cfg lagr_lam_db 0.34 under dpsnr (lagr and res).
  - [x] 30d. DESIGN DECISION before BC/CQL/Lagrangian on lf: their QP = base + ramp + offset, and the lf base is the
    HINDSIGHT q (fine for the search, a leak (U1) for a policy). Options: (i) causal base = budgets.csv
    base_qp_est_k<k> (linear, out-of-fold) with search plans re-expressed relative to it (offset + q_hind - q_est,
    clipped to +-5); (ii) every learned method as a residual on the controller (res design), BC/CQL targets = search
    QP - controller QP. Recommend (i) for BC/CQL/Lagrangian (keeps Pavneet's methods) + (ii) = residual RL.
    DECIDED 11-10 (Aayush): (i). DONE (repo-pavneet, uncommitted): config.LFQ_LEARN (RC_ARM=lfq + RC_ACT_RANGE, which
    rl.py sets to 10 for lfq; the search keeps +-5); env.frame_qp = round(base + RAMP[t] + offset), base =
    info['base'][(level, k)] = budgets.csv base_qp_est_k<k>, shown in obs slot 15 ((base-30)/10); offrl.trajectories
    re-expresses each logged plan (QPs at the hindsight base) as offsets around the causal base (env.offsets_for) and
    DROPS plans needing an offset outside +-10 (exact outcomes only). Why +-10: train q_hind - q_est is +1.2 +- 4.9 QP
    at k0 (+-2.9 at k29); at +-5, 55% of k0 best plans (25% of frames) fall outside; at +-10, 10% (3.6%); smoke k0:
    3.6% of plans dropped. tools/lfq_infos.py -> rcwork_v1/<enc>_lfq/results_infos/infos_learn.pkl (flat GOPs dropped,
    P2 first pass QP 32, base, static = the search's start plan as reward offset; start score reproduced exactly);
    rl.py loads infos_learn for lfq. tools/lfq_parity.py: 24/24 exact (bits, PSNR, dB score, observations) on 3 train
    GOPs x 4 levels x k 0/29, incl. bases 7 QP off. rl.py --quick smoke (lagr k5, bc k0) OK on a 10-GOP subset
    (results_infos_quick/infos_learn.pkl = subset file, results_search_quick -> symlink).
  - [x] 30e. controller retune on val under dPSNR_B (scripts/controller_real.py scores with the old metric: add dPSNR_B;
    sweep margin 0.97-1.02 (+ w0); real encodes, a few CPU-h); then final test run; then res infos rebuilt on it.
    11-10: every stored val tuning run rescored under dPSNR_B - 0.17 x %over, flat excluded
    (results_v1/controller_dpsnr/val_rescored.parquet): the published final2 setting (dI 3, i_cap 0.3) is the WORST,
    -1.13 dB x264 / -1.29 x265 (use 0.84 / 0.81); best tried v2tune 0.97:7:1:2:3:4:0:1:1:0 -0.68 / -0.63 (use 0.91);
    dI 7 > 5 > 3 by ~0.2-0.5 dB each, i_cap 1 > 0.3, margin 1.0 + init 1 better on tune2, ramp a=1 +0.02. dI not
    peaked -> new grid tune3 (Aayush OK): margin {0.97,1.0,1.02} x dI {7,9,11} x init {0,1} x a {0,1}, i_cap 1,
    w0 2, dmax 3, fcap 4, pmin 1, b 0; val, k 0/2/5/10/29: x264 13989663, x265 13989664 (8 shards each).
    x264 shard 2 died on d18-14 -> rerun 13989867. x264 RESULT (scripts/controller_dpsnr.py -> results_v1/controller_dpsnr/
    tune3_x264_val.md; flat excluded, pooled over k/levels): best 1.0:9:1:2:3:4:0:1:1:0 -0.332 dB (dPSNR_B -0.155, use
    0.985, 49% of episodes over, mean 1.0% over) vs final2 -1.132 (+0.80 dB); dI 9 ~ 11 (peaked); margin 0.97 best
    0.97:11 -0.389 with only 9.5% over; margin 1.02 worse. Aayush chose 1.0:9 (best score). final3 x264 (that setting)
    submitted: train 13990608, val 13990609, test 13990610 -> results_v1/controller_real/final3_x264_*.
    final3 x264 DONE (all 24 shards): val -0.332 (= tune3, deterministic), TEST -0.220 dB (dPSNR_B -0.065, use
    0.994, 54% of episodes over, mean 0.9% over; k0 -0.49, k2 -0.24, k5 -0.12, k10 -0.11, k29 -0.15)
    (results_v1/controller_dpsnr/final3_x264_{val,test}.md). x265: tune3 13989664 still running.
    x265 tune3 20:50: 7/8 shards done in 0.9-1.4 h; shard 6 at 3h15 on b09-18 (node overloaded by another user's
    jobs, kswapd 100%, our x265 at 10-19% CPU each) -> slow, not dead; 7 h limit. Aayush OK ~21:00: PARALLEL rerun
    13999255 (array 6, b09-18 excluded); cancel whichever copy finishes second.
    11-10 22:23: original 13989664_6 finished first (4h49) -> 13999255 cancelled. x265 tune3 RESULT
    (results_v1/controller_dpsnr/tune3_x265_val.md): best 1.0:9:1:2:3:4:0:1:1:0 -0.406 dB (dPSNR_B -0.253, use 0.983,
    48% over, mean 0.9%) = the x264 winner; 1.0:7 -0.407 (tie), 0.97:9 -0.447 with only 6.5% over.
    final3 x265 SUBMITTED 11-11 08:08 (standing approval 1; delayed by the session dying at ~22:26):
    train 14007318, val 14007319, test 14007320 (b04-16 + b09-18 added to bad_nodes).
  - [x] 30f. residual RL with the new reward (new arm or RC_WORK so x264_res is kept), 15 runs ~80 CPU-h.
    11-10: code: RC_CTRL_SETTING (config), env passes qhat = info['base'] to the controller (init 1 settings),
    tools/res_infos.py --tag/--setting/--metric dpsnr (ctrl score in dB + dpsnr + score_old; old setting/metric
    rebuild reproduces the stored scores exactly), jobs/rc_v1_submit.sh RC_WORKNAME. Infos: rcwork_v1/x264_resq
    (final3, 1.0:9:1:2:3:4:0:1:1:0, dpsnr). Parity 24/24 exact (test, k 0/5/29). SUBMITTED (Aayush OK) 18:20:
    RC_WORKNAME=resq RC_METRIC=dpsnr RC_CTRL_SETTING=<final3> rc_v1_submit.sh x264 res C -> 13991362 (runs_v1/res.txt).
    Compare: python -I scripts/lfq_compare.py x264 --ctrl-tag final3.
    x264 DONE 11-10 19:05 (15/15, ~10 min each, like the old res runs). TEST (results_v1/lfq_compare_x264.md; diff vs
    final3 controller at the same k, 95% clip bootstrap): k0 -0.51 (ctrl -0.49; -0.02 [-0.03,-0.01]), k2 -0.29 (-0.05),
    k5 -0.14 (-0.03 [-0.04,-0.01]), k10 -0.17 (-0.06), k29 -0.30 (-0.15 [-0.24,-0.07]). The residual stays at the
    controller (use 0.97-0.99) and never beats it; slightly worse at every k. x265: waits for x265 final3 train.
  - [x] 30g. after 30b train gathers: BC -> CQL->PPO -> Lagrangian on lfq, k 0/2/5/10/29 x 3 seeds, x264 then x265
    (~350 CPU-h per encoder); needs 30c + 30d. Then W4 analysis (H1-H8 vs the new metric), report tables.
    x264 SUBMITTED 11-10 17:45 (Aayush OK): infos job 13989843 (tools/lfq_infos.py x264 --force, afterok gathers
    13989250/52) -> RL array 13989844 (runs_v1/lfq.txt = orig.txt list, 45 runs, 16 CPU/48G/4h, %20, afterok
    13989843). Out: rcwork_v1/x264_lfq/results_rl/<run>/eval.pkl (rows carry score (dB), dpsnr_b, score_old, use).
    x264: 39/45 DONE by 20:45 (bc ~6 min, cql_ppo/lagr ~20-28 min); 6 lagr runs (k10 s0, k29 x3, ...) running. No crashes;
    scores rise with k and agree across seeds -> judged NOT broken, so x265 went ahead (standing approval 2).
    TEST vs final3 controller (score dB; ctrl k0 -0.49, k2 -0.24, k5 -0.12, k10 -0.11, k29 -0.15; search ceiling +0.30):
      bc      k0 -2.83 (use 1.06, 52% over), k2 -1.11, k5 -0.68, k10 -0.43, k29 -0.27 (-0.11 [-0.18,-0.04] vs ctrl)
      cql_ppo k0 -1.67, k2 -1.10, k5 -0.73, k10 -0.51, k29 -0.43 (use 0.91-0.98)
      lagr    k0 -1.56, k2 -1.19, k5 -0.92, k10 -0.77 (use 0.82-0.91: UNDER-spends; lam 0.34 = 2x the metric's 0.17)
    Every learner is significantly below the causal controller at every k (CIs exclude 0). Reading: BC copies
    hindsight plans whose offsets carry the hindsight-vs-causal base error (sd 4.9 QP at k0) it cannot see -> k0
    overspends; lagr's 2x over-penalty -> under-spends. Open for Aayush: lagr with lam 0.17? reward rescale (Pavneet Q2)?
    LAGR lam 0.17 (Aayush OK 11-10 ~21:00): rl.py --lam override (run name adds lam0.17, so the 0.34 runs stay);
    smoke --quick OK (log shows lam 0.17); runs_v1/lfq_lam017.txt (15 runs) -> x264 array 13999266. lfq_compare.py
    reports it as method lagr_lam0.17.
    RESULT 11-11 (all 15 + the 6 late lam-0.34 runs done; results_v1/lfq_compare_x264.md), TEST score dB / use:
      lam 0.34: k0 -1.56/0.82, k2 -1.19/0.86, k5 -0.92/0.91, k10 -0.71/0.93, k29 -0.69/0.92
      lam 0.17: k0 -1.85/0.97, k2 -0.94/0.95, k5 -0.76/0.95, k10 -0.51/0.97, k29 -0.49/0.95
    lam 0.17 spends more and gains 0.15-0.25 dB at k>=2 (val agrees: +0.18-0.25 at k2/k10/k29), loses 0.3 at k0;
    still below the controller at every k (test k29 -0.34 [-0.41,-0.27]). Learner ranking at k29 test:
    res -0.30 ~ bc -0.27 > lagr0.17 -0.49 > cql_ppo -0.43 ... all < ctrl -0.15.
    REWARD SCALE (Pavneet Q2) measured 11-10: 1 dB ~ 12-13 old points on the same episodes (x264 test k5), so the dB
    reward is ~0.8x the old /10 reward; per-episode reward sd old orig 1.5-1.7 vs lfq 1.6-2.1. Same order -> no
    rescale needed (the "0.1-1 vs 1-2" claim in START_HERE was wrong; corrected there, patch regenerated 21:05).
    lfq_compare.py bug fixed 11-10 20:55: y.clip was DataFrame.clip (method), so the CIs were garbage; now y["clip"].
    x265 SUBMITTED 20:50 (standing approval 2): infos 13999152 (lfq_infos.py x265 --force) -> RL array 13999153
    (45 runs, RC_TLIM 6:00:00, afterok 13999152).
    x265: 44/45 DONE by 22:56 (10-55 min each); task 21 (cql_ppo k5 s0) FAILED at start on b04-16 (x265 version
    guard; no auto-retry for RL arrays) -> b04-16 to bad_nodes, rerun 14007317 (standing approval 4).

- [x] 31. PREVIOUS-GOP HISTORY (Aayush 11-11: A approved + done; C approved in principle; B grid proposed). Causal base QP.
  DONE 11-11 ~14:20: A gate PASS; B final4 = new best controller (x264 test -0.177, x265 -0.270); C1/C2 learners all
  below final4 (best: x265 k29 break-even). Details at the end of this item.
  Why: under item 30 no learner beats the retuned controller (x264 test: ctrl -0.22 dB pooled; every learner below it
  at every k, CIs exclude 0). The main handicap is the GOP-start base QP: causal estimate vs hindsight base +1.2 +- 4.9
  QP at k0 (+-2.9 at k29); the ramp at the HINDSIGHT base alone scores -0.15 dB test (search start plan), better than
  the causal controller (-0.49 at k0). The earlier "wins" came from the leaked base (orig arm) or the old metric
  (see the 11-11 answer: 3 reasons). The controller's own init 1 (I QP from budgets.csv qhat) is WORSE than init 0 by
  ~0.25 dB on val (tune3 x264: 1.0:9 init0 -0.33 vs init1 -0.60) because qhat is off by ~3.9 QP (val MAE).
  Evidence it can help (item 28, results_v1/gates/prevgop_gate.md, linear, test, x264): k0 base-QP MAE 3.67 -> 2.36
  with what the encoder REALLY has after GOP n-1 (+ctrl: q_eq from P2's controller run on GOP n-1 = mean P QP +
  s_p x log2(bits / budget), plus log2(bits / its first-pass total)), -1.31 [-1.72, -0.93]; ideal 2.24; k0 + previous
  GOP beats k2 without it (2.58). x265 ideal 3.69 -> 2.21 (no realistic x265 row yet: needs an x265 train controller
  run, which final3 x265 train 14007318 now provides). Gain shrinks with k (-0.3..-0.5 QP at k2/k5). Valid because
  budgets are clip-level and GOPs of a clip are consecutive; nothing in the env or controller uses history today.
  Hypothesis: most of the gain is at k0/k2 and on stable GOPs; cut GOPs (new scene) gain less.
  Causality rules: only GOP n-1 of the SAME clip, only quantities known after encoding it (its bits, its QPs, its
  first-pass), same budget level. The first GOP of each clip (109 of 1042) has no predecessor -> falls back to
  budgets.csv base_qp_est_k (report it separately). q_eq depends on which policy encoded GOP n-1: use the policy's own
  encode when it can be run clip-sequentially; otherwise the final3 controller's encode of GOP n-1 at the same level
  and k (approximation; check: spread of q_eq for the same GOP across k and across settings, should be << 2 QP).
  Stages, each with a gate (stop if the gate fails):
   A. Estimator only, no encodes, interactive OK (few min). Refit prevgop_gate's +ctrl model on the FINAL3 controller
      runs (both encoders, k 0/2/5/10/29), train only, out-of-fold by source group like budgets_v1.py; write
      data/v1/320x180/budgets_prev.csv (gid, encoder, level, k, base_qp_prev_k, has_prev, q_eq, fp ratio).
      GATE A: val k0 MAE better than base_qp_est_k0 by >= 1 QP (CI excludes 0) on both encoders.
   B. Controller with the history (real encodes; val tune then test). Two uses, tested separately and together:
      (B1) I-frame QP from base_qp_prev (init 1 with the new qhat); (B2) start c_P from GOP n-1's realised
      bits / first-pass ratio instead of the train prior (the same w0 shrinkage). Small grid around final3
      (init {0,1} x c_P start {prior, prev} x margin {0.97, 1.0}; dI 9 fixed): 8 settings, val, then the winner on
      test and train. Needs scripts/controller_real.py to read budgets_prev.csv (qhat column choice + c_P prior per
      GOP); scripts/controller_dpsnr.py unchanged. GATE B: val score >= +0.10 dB pooled or >= +0.15 at k0 vs final3.
      Cost ~3.5 CPU-h per setting per split per encoder -> ~30 val + ~10 test + ~25 train per encoder, ~130 CPU-h total.
   C. Learners on the better base (only if B passes; else only C2 with the old controller is worth a look).
      (C1) lfq: tools/lfq_infos.py --base prev (infos['base'] = base_qp_prev_k); offsets could narrow from +-10 to +-6
      (recheck the share of search plans out of range, as in 30d); re-run lfq_parity. Runs: bc, cql_ppo, lagr lam 0.17,
      k 0/2/5/10/29 x 3 seeds (45 runs; x264 ~300 alloc CPU-h). (C2) residual RL on the B controller (res_infos on
      the new final run + parity, 15 runs, ~40 CPU-h), and optionally the history as observation features
      (q_eq of GOP n-1 - base, its bits/budget, has_prev) in a free obs slot. Compare with scripts/lfq_compare.py
      against BOTH final3 and the B controller.
  Report: base-QP MAE by k and class (A); controller score vs final3 by k and class (B); learner gap closed (C).
  Total if all stages run: ~130 (B) + ~350 per encoder (C) CPU-h. Starting point if approved: stage A on x264 now
  (final3 x264 train/val/test exist), x265 after final3 x265 train/val/test (14007318-20).
  Open for Aayush: (1) approve A (no compute); (2) B grid size; (3) whether learners (C) are worth it if B alone
  closes most of the k0 gap.
  11-11 Aayush: run A on x264, suggest a B grid, and run C anyway (numbers for the final presentation).
  [x] A DONE both encoders (scripts/base_prev.py -> data/v1/320x180/budgets_prev_<enc>.csv, results_v1/gates/
      base_prev_<enc>.md; history = final3 on GOP n-1; linear fixed in advance). GATE A PASS both:
      x264 val k0 MAE 3.97 -> 2.54, -1.43 [-2.18, -0.70]; test 3.68 -> 2.38 (-1.30 [-1.70, -0.91]);
      x265 val k0 3.60 -> 2.39, -1.20 [-1.80, -0.58]; test 3.69 -> 2.34 (-1.35 [-1.75, -0.94]).
      Gain at k2..k29 -0.3..-0.5 QP (linear); gbm +prev is better at k10/k29 (x264 val k29 1.34 vs 2.27 linear) but
      the model was fixed as linear before the run (gbm = a follow-up option). Bias ~0 with +prev (est: -0.9..-1.2 at k0).
      CAVEAT: prev_qeq depends on how GOP n-1 was encoded: range across k for the same GOP x level median 1.2, p90
      4.7-5.0, max 31 QP -> not policy-insensitive in the tail; B should use the policy's OWN GOP n-1 (sequential).
  [~] C1 prep DONE (no jobs yet): tools/lfq_infos.py --base-csv budgets_prev_<enc>.csv --workname lfqp ->
      rcwork_v1/<enc>_lfqp (links lfq clips/gops/search; base = base_qp_prev, base_est kept); lfq_parity x264 30 OK
      (2 plans out of range), x265 32 OK. runs_v1/lfqp.txt = bc + cql_ppo (lfq.txt) + lagr --lam 0.17, 45 runs.
      lfq_compare.py lists them as <method>@prev. History for C1 = final3 controller's GOP n-1 (approximation, see
      caveat). Submit (needs OK): RC_WORKNAME=lfqp RC_RUNS=runs_v1/lfqp.txt bash jobs/rc_v1_submit.sh x264 lfq C
      (+ x265 with RC_TLIM=6:00:00).
  B PROPOSED GRID (11-11, needs OK + code): controller_real.py --history prev: clip-SEQUENTIAL chains (clip x level x
      k x setting; GOPs in order), each GOP's history from the SAME chain's GOP n-1 (exactly causal); first GOP of a
      clip = no history. Two uses: (B1) init 1 with qhat = base_prev linear model (coefficients exported by
      base_prev.py) on the chain's own prev_qeq/prev_lcal; (B2) rate-model prior scaled by GOP n-1's realised/predicted
      bits ratio r (pred = prior model at its actual QPs; c_i, c_p x r), w0 = shrinkage weight towards it.
      Fixed at final3: margin 1.0, i_cap 1, dmax 3, fcap 4, pmin 1, a 1, b 0. 8 settings on val:
        B1:    init 1, dI {6, 9}, w0 2, prior train            (2)
        B2:    init 0, dI 9, w0 {2, 4}, prior x r              (2)
        B1+B2: init 1, dI {6, 9} x w0 {2, 4}, prior x r        (4)
      reference = final3 val (no history; reuse). Pick by pooled val score; GATE B >= +0.10 pooled or >= +0.15 at k0;
      winner then on train/val/test (train needed for C2). Cost ~28 CPU-h val + ~27 train/test per encoder, ~110 total.
      C2 (after B): res infos on the B winner + parity, 15 runs per encoder (~40 CPU-h each).
  11-11 ~08:35 Aayush: C1 both encoders; B grid + margin 0.97 round. SUBMITTED:
      C1 x264 14007457, x265 14007458 (RC_WORKNAME=lfqp, runs_v1/lfqp.txt, 45 each; x265 RC_TLIM 6:00:00).
      B code (scripts/controller_real.py, 11th setting field h; base_prev.py exports data/v1/320x180/
      base_prev_model.json): local tests OK -- h=0 sequential == final3 exactly (bits, qps, PSNR; 6 episodes x264
      val), qhat_prev == budgets_prev csv exactly; h=3 x265 runs (I QP 23 vs solver 16, use 0.997-0.999).
      B round 1 (Aayush OK): tag hist1, val, 8 shards by clip (16 val clips): x264 14007551, x265 14007552.
      Settings: B1 1.0:{6,9}:1:2:3:4:1:1:1:0:1; B2 1.0:9:1:{2,4}:3:4:0:1:1:0:2; B1+B2 1.0:{6,9}:1:{2,4}:3:4:1:1:1:0:3.
      Next: scripts/controller_dpsnr.py <enc> hist1 vs final3 val (x264 -0.332, x265 -0.406); round 2 = margin 0.97
      on the top 2 (show sbatch, ask); winner on train/val/test if gate B passes.
      ROUND 1 RESULT (results_v1/controller_dpsnr/hist1_<enc>_val.md; val, flat excluded, pooled over k/levels):
        x264 best 1.0:6:1:4:3:4:1:1:1:0:3 (B1+B2, dI 6) -0.217 vs final3 -0.332 (+0.115) -> GATE B PASS
             per k: k0 -0.41 vs -0.77 (+0.36), k2 -0.20 vs -0.33, k5 -0.16 vs -0.18, k10 -0.15 vs -0.15, k29 -0.16 vs -0.23;
             use 0.998, 54% eps over, mean 1.1%. w0 2 next (-0.224).
        x265 best 1.0:6:1:2:3:4:1:1:1:0:3 -0.339 vs final3 -0.406 (+0.067; k0 -0.53 vs -0.89, +0.35) -> PASS via k0;
             k5/k10 slightly worse (-0.29 vs -0.26/-0.24), k29 +0.02.
        Pattern (both): dI 6 >> dI 9 under init 1 (dI 6 is the grid EDGE); h3 (both uses) > h1 (I QP only) by 0.07-0.09;
        h2 alone (init 0) ~ final3 pooled (helps k10/k29 on x264, hurts k0). Attribution open: init 1 dI 6 WITHOUT
        history was never run (tune3 had dI 7-11 only).
      ROUND 2 (Aayush OK 11-11 ~09:20), tag hist2, val: x264 14007647, x265 14007648. Settings: margin 0.97 on the
        top 2 (0.97:6:1:{2,4}:3:4:1:1:1:0:3), dI edge (1.0:{4,5}:1:2:3:4:1:1:1:0:3), no-history control
        1.0:6:1:2:3:4:1:1:1:0:0 (init 1 with budgets.csv qhat; attributes the gain to the history).
      ROUND 2 RESULT (hist2_<enc>_val.md; pooled val score dB):
        x264: dI 5 -0.247, margin 0.97 -0.273/-0.280 (only 9% eps over, use 0.971), dI 4 -0.315; CONTROL (no history,
              init 1 dI 6) -0.371 = WORSE than final3 -0.332. Round-1 best 1.0:6:1:4 h3 -0.217 stays best.
        x265: dI 5 -0.337 ~ round-1 best dI 6 w0 2 -0.339; dI 4 -0.347; margin 0.97 -0.395; CONTROL -0.534 (final3 -0.406).
        => the gain IS the history: best vs control +0.15 dB (x264) / +0.20 (x265); dI peaks at 5-6; margin 0.97 trades
        ~0.05 dB for far fewer over-budget episodes (9% vs 54%).
        Rule pick (best pooled val): x264 1.0:6:1.0:4:3:4:1:1:1:0:3 (-0.217), x265 1.0:5:1.0:2:3:4:1:1:1:0:3 (-0.337).
        One common setting 1.0:6:1.0:2:3:4:1:1:1:0:3 is within 0.01 of both (-0.224 / -0.339).
      FINAL4 (Aayush chose the common setting 1.0:6:1.0:2:3:4:1:1:1:0:3, 11-11): train/val/test both encoders:
        x264 14007815/16/17, x265 14007818/19/20 -> results_v1/controller_real/final4_<enc>_<split>_*.
      C2 prep: repo-pavneet config CTRL_SETTING accepts the 11th field h; rclib/controller.py decide(h ignored);
        env reset uses info ctrl_qhat / ctrl_r (qhat and rate-prior scale the history controller used on this GOP,
        i.e. its OWN GOP n-1 -- the residual policy's own n-1 would differ: approximation as in C1); res_infos.py fills
        them for 11-field settings. Regression: x264_resq (final3) parity still 24/24 exact.
        Next: res_infos <enc> -> rcwork_v1/<enc>_resh --tag final4 --setting <S> --metric dpsnr, res_parity, then
        (ask) RC_WORKNAME=resh RC_METRIC=dpsnr RC_CTRL_SETTING=<S> rc_v1_submit.sh <enc> res C.
      FINAL4 RESULT (results_v1/controller_dpsnr/final4_<enc>_{val,test}.md; val = round 1 exactly):
        TEST x264 -0.177 dB (final3 -0.220; k0 -0.35, k2 -0.16, k5 -0.13, k10 -0.12, k29 -0.13; use 0.996)
             x265 -0.270 dB (final3 -0.315; k0 -0.43, k2 -0.28, k5 -0.21, k10 -0.19, k29 -0.24; use 0.997)
        Paired test diff final4 - final3 (95% clip bootstrap): x264 pooled +0.042 [-0.004, +0.091], k0 +0.137 [+0.037,
        +0.239], k2 +0.074 [+0.011, +0.158], k5/k10/k29 ~0; x265 pooled +0.045 [-0.054, +0.145], k0 +0.121 [-0.026,
        +0.297] (27 test clips: wide). => a clear gain only at small k on x264; elsewhere positive but not significant.
      [~] C2 SUBMITTED 11-11 10:05 (Aayush: submit when parity passes): resh infos (final4, dpsnr) both encoders,
        res_parity 36/36 exact each (2 of 3 GOPs with history, r 0.93 / 1.52); x264 14008008, x265 14008023 (6 h).
        lfq_compare.py: resh runs = res@hist; --ctrl-tag final4 writes lfq_compare_<enc>_final4.md.
      C2 BUG (found 11-11 ~11:40, my code): rclib/offrl.slim() (the infos copy experiments/rl.py gives the env workers)
        kept only known keys and DROPPED ctrl_qhat / ctrl_r, so every C2 run trained and evaluated a residual on the
        NO-HISTORY control controller (init 1, budgets.csv qhat, dI 6; val -0.371 x264), while the reward baseline was
        final4's result (a wrong per-episode offset). Symptom: x264 res@hist k0 seed 1 used offset 0 on 99% of frames
        yet scored -0.595 vs final4 -0.349. tools/res_parity.py passed because it read the FULL infos, not slim.
        FIX: slim() keeps ctrl_qhat/ctrl_r; res_parity now builds the env from offrl.slim() like rl.py; stale
        <enc>_resh/results_infos/infos_slim.pkl removed. Check: parity 36/36 exact both encoders with the fix; one
        history GOP replayed with the OLD slim -> qps/bits mismatch, reward +2.49 (so parity now catches it).
        x264 C2 14008008: INVALID (results in rcwork_v1/x264_resh/results_rl). x265 C2 14008023: CANCELLED.
        Not affected: C1 lfqp (uses 'base', kept), resq (final3, no history keys), lfq runs.
        Resubmit needs Aayush's OK.
        Aayush OK 11-11 ~11:50: invalid outputs moved to rcwork_v1/<enc>_resh/results_rl_invalid_slim (kept);
        C2 RESUBMITTED x264 14010713, x265 14010714 (6 h). x264 tables regenerated without the invalid rows.
      [x] C1 + C2 DONE 11-11 ~14:00: x265 C1 14007458 45/45, C2 x264 14010713 15/15, x265 14010714 15/15.
        Tables: results_v1/lfq_compare_<enc>_final4.md (vs final4) and lfq_compare_<enc>.md
        (vs final3). NOTE: the x264-vs-final3 run hung in write() on /scratch1 (results_v1/lfq_compare_x264.md left
        0 bytes, process unkillable, state I); its CSV lfq_compare_x264.csv (14:09) was complete, so the table was
        rebuilt from the CSV; the hung write then completed at 15:07 and matched the rebuild exactly (rebuild deleted).
        RESULT (test, score dB, paired diff vs final4 with 95% clip bootstrap):
          C2 res@hist (residual RL on final4): BELOW final4 at every k on both encoders.
            x264: k0 -0.549 vs -0.349 (-0.20 [-0.27,-0.14]), k2 -0.05 [-0.08,-0.02], k5 -0.06 [-0.09,-0.03],
                  k10 -0.12 [-0.18,-0.08], k29 -0.16 [-0.22,-0.11]. Val the same sign at every k.
            x265: k0 -0.12 [-0.18,-0.06], k2 -0.12 [-0.20,-0.03], k5 -0.13 [-0.20,-0.06], k10 -0.20 [-0.28,-0.13],
                  k29 -0.03 [-0.10,+0.06] (break-even). Val all below (k29 -0.10 [-0.16,-0.03]).
          C1 @prev learners (base_prev): base_prev helps them a lot (x265 bc k0 -2.41 -> -1.37, cql_ppo k0 -> -1.12)
            but all stay below final4 at k<=10; at k29: x265 bc@prev +0.03 [-0.06,+0.11] (break-even; val -0.20
            [-0.58,+0.05]), x264 bc@prev -0.08 [-0.14,-0.02].
          => No learner beats the controller with or without history; best case is break-even at k29 on x265.
        FINDING (not a bug): on x265 cql_ppo@prev and lagr_lam0.17@prev are IDENTICAL per GOP (same QP plans, same
          train curve except the lam column). Under METRIC=dpsnr, 'relative' reward = (dPSNR - 0.17 over) - (dPSNR_ref
          - 0.17 over_ref) and 'lagrangian' lam 0.17 = dPSNR - dPSNR_ref - 0.17 over: they differ only by 0.17 x
          over_ref, a per-episode constant that is 0 when the reference (search start) plan is within budget. x265
          lfqp train refs: 0 of 2360 over -> identical training with the same seed; x264: 5 of 2360 over -> the runs
          drift apart (seed-like). So "lagr lam 0.17" = cql_ppo's own objective; the item-30 lam 0.17 vs 0.34 gain is
          really "default reward vs a 2x over-penalty". Report lagr0.17 as a duplicate, not a separate method.
      Team note 11-11: parallel-experiment menu for Pavneet/Atharva in Aayush's mail (MPC with base_prev; learners
        with their own history; lam sweep/PID + val checkpoint; gbm estimator / wide first-pass pair; dB figures).
        Patch 2 regenerated 09:40; data synced to /project2 (sync_project2.sh all).

- [x] 34. BASELINE FROZEN (Aayush 11-11): final4 (1.0:6:1.0:2:3:4:1:1:1:0:3) is the classical baseline for the
  report; no further controller tuning. Context: x265 level 42 res@hist beats final4 (+0.15 [+0.03, +0.30] test,
  +0.16 [+0.02, +0.33] val, k0 +0.27 / +0.22; x264 no gain). Diagnosis: final4 hits QP 51 in 38% / 35% of level-42
  episodes (x265 / x264), which end 4.9% / 6.9% over; budgets are feasible (constant QP 50 meets all x265 and 99% of
  x264). First guess (solver plans frames above QP 51) was WRONG: a clipped solver gave bit-identical results on 12
  local x265 L42 val episodes (edit reverted, test files deleted). Likely cause: one rate slope s_p (5.04 x265 / 5.49
  x264 QP per halving) while the constant-QP curves flatten to 5.8 / 6.4 at QP 47-50. Proposed fix (QP-band slope)
  NOT pursued: Aayush asked why improve the controller at all; answer = it is the fair deployable baseline, the
  oracle is not deployable; further tuning would only make the learners look worse. Reported instead as a case where
  the residual corrects the controller's high-QP mis-modelling (x265 only; x264 unexplained). Numbers:
  results_v1/w5/w5_numbers.md section 5; report docs/report-w5-quality-vs-delay.md findings 9-10 + "Baseline choice".
- [x] 34b. ENCODER RATE CONTROL ON THE dB METRIC (Aayush 11-11: "did we check how the latest models fare against
  ABR+VBV?"; no encodes): scripts/abr_dpsnr.py rescores results_v1/baselines_v1.parquet (week-2 encodes) exactly like
  lfq_compare scores the controller (budgets checked equal to the lfq infos) -> results_v1/w5/abr_dpsnr.md. TEST:
  abr_vbv -1.52..-1.65 dB (x264), -1.16..-1.25 (x265), flat in k, over budget on 50-86% / 49-92% of GOPs. final4 -
  abr +1.29..+1.48 (x264) / +0.82..+0.99 (x265); res@hist +1.08..+1.43 / +0.70..+0.96; bc@prev from k2 (x264) / k5
  (x265); all CIs > 0. Added to the W5 report (finding 5a).
- [x] 35. TARGETED RESIDUAL (Aayush 11-11: "lets do the targeted residual"). Residual RL on final4 (arm res, work dir
  resh, dB reward, same settings as C2) trained ONLY on budget levels 36 and 42 (high-QP regime where final4's single
  rate slope is wrong; tracker 34); evaluated on all levels. Deployment rule (causal: the budget is known up front):
  residual at levels 36/42, plain final4 at 24/30. Code: repo-pavneet experiments/rl.py --train-levels (run name part
  lv36-42; env budgets restricted for TRAINING only); checked: training env draws only 36/42 (200 resets: 99 / 101),
  run name res_k0_fixed_lv36-42_s0 -> lfq_compare label res_lv36-42@hist. Run list runs_v1/res_lv3642.txt (15 runs,
  k 0/2/5/10/29 x 3 seeds). Gate (written before the runs): on VAL, the combined rule beats final4 pooled over k and
  levels with a CI excluding 0 on at least one encoder, and does not lose at 36/42 vs plain res@hist. Report test
  either way.
  SUBMITTED 11-11 16:24 (Aayush OK): x264 14024909, x265 14024910 (RC_WORKNAME=resh RC_METRIC=dpsnr
  RC_CTRL_SETTING=1.0:6:1.0:2:3:4:1:1:1:0:3 RC_RUNS=runs_v1/res_lv3642.txt; x265 RC_TLIM 6:00:00; 16 CPU / 48G).
  x264 task 4 (k2 s1) FAILED 17:43 on b22-07: an x264 encode in a training worker failed 3x after 1 frame (input
  intact, /dev/shm empty, 3.7G of 48G; other tasks on b22-07 fine) -> transient; b22-07 added to bad_nodes, task 4
  RERUN 18:01 as 14027731 (Aayush OK).
  11-12: x264 complete. x265 13/15: task 10 died on b05-21 (numpy import) -> rerun 14044103 (Aayush OK 06:46); task
  9 was requeue-held since 20:53 (auto-retry helper timed out) -> released by hand 06:40 with b05-21 excluded.
  RESULT (11-12, all 15 runs per encoder; scripts/gates_35_36.py -> results_v1/w5/gates_35_36.md): GATE FAIL.
    Combined rule (res_lv at 36/42, final4 at 24/30) - final4, val, pooled over k and levels: x264 -0.148 [-0.212,
    -0.084], x265 +0.026 [-0.020, +0.085] (test x265 +0.036 [-0.017, +0.096]). x265 at level 42 alone: +0.239 [+0.080,
    +0.431] val, +0.227 test (the level-42 finding holds; res@hist was +0.15) but level 36 gives it back. x264: the
    targeted residual is worse than final4 (-0.30) and than res@hist (-0.22) at 36/42. A level-42-only rule was not
    pre-registered; it would be a post-hoc pick on val (report as exploratory only). Untrained levels 24/30: -0.3..-0.8.
  Was: Next when done: lfq_compare.py <enc> --ctrl-tag final4 (rows res_lv36-42@hist), then the combined-rule table
  (targeted residual at 36/42, final4 at 24/30) vs final4 and res@hist, val gate first.
- [x] 36. ARCHITECTURE: SHARED PER-FRAME ENCODER (Aayush 11-11: "go ahead with the day-1 offline test. make sure to
  document this line of experiments"). Budget: at most ~1 week of experimentation before the final proposal.
  Why: every learner uses Pavneet's flat MLP (2 x 256 ReLU) on the 346-dim observation (16 global + 30 frame slots x
  11 features, slots beyond k zeroed): separate weights per (slot, feature), so "a cut d frames ahead" is learned
  separately for each d from ~80 single-cut train GOPs; one model per k. Proposed: one small network phi applied to
  every visible frame (11 features + relative position j/29 + absolute position (t+j)/29), pooled over the visible
  window, then a head on [global, frame t, pooled]: weight sharing across offsets (CNN-like), explicit positions
  (LLM-like), one model for all k. Not this week: attention/transformer policies (data-hungry; only as an attention
  pooling variant in the offline test) and LSTM / cross-GOP memory (needs clip-long episodes + recurrent PPO; future work).
  PLAN (gated; stop at the first failed gate):
  Day 1 (offline, no encodes): BC on the lfqp training data (search plans re-expressed around the previous-GOP base,
    exactly what bc@prev trains on), val = the search's best val plans re-expressed the same way. Nets: mlp (current
    2x256), set_mm (shared phi width 32, mean+max pooling), set_attn (attention pooling queried by frame t + global);
    trained per k (0/2/5/10/29) and on all k pooled ("anyk"; mlp too, as the control for pooling data). Same BC
    recipe as rl.py (Adam 3e-4, 20k steps, batch 512, best plans only). Metrics on val, per k: per-frame offset MAE
    (QP) vs the search, accuracy, NLL; split stable / cut; CIs = 95% bootstrap over clips.
    GATE 1 (written before any result): a shared-encoder net has lower val offset MAE than the per-k mlp, pooled over
    k, with a CI excluding 0, on both encoders, and is not worse on cut GOPs. Choosing the better of set_mm/set_attn
    on the same val data makes this slightly optimistic; the real test is days 2-3.
  Days 2-3 (if gate 1 passes): BC with the winner, real-encode eval at all k, both encoders (sbatch, ask) vs bc@prev.
  Days 3-5 (if BC improves on bc@prev): residual RL on final4 with the winner as the PPO feature extractor (sbatch, ask)
    vs res@hist and final4, val gate first. Days 6-7: analysis + report.
  Code: repo-pavneet rclib/nets.py (FrameSetNet), offrl.train_bc(net=...), tools/arch_offline.py.
  11-11 change before any result: the val split's search results keep only each best plan's actions (no per-frame
    bits), so val observations cannot be rebuilt offline. Day-1 validation = a held-out quarter of the NATURAL train
    clips (seed 0; spliced clips stay in training), split by clip; gate 1 reads "held-out" for "val". Data shortcut:
    top 4 plans per GOP x budget (BC uses the best ones only). Smoke test (1000 steps, k 0/5) ran end to end in 209 s;
    nets: mlp 160k params, set_mm 35k, set_attn 35k. Full run = jobs/arch_offline.sbatch (2 tasks: x264, x265; seeds
    0,1; 20k steps; 8 CPU / 16G / 4 h). SUBMITTED 11-11 17:36 (Aayush OK): 14026936 (flaky nodes excluded).
    DAY-1 RESULT (14026936 done 19:13; results_v1/arch/offline_<enc>_d1.md; held-out 14 clips / 130 GOPs; seeds 0,1):
    held-out offset MAE vs the search (QP), pooled over k: mlp per-k 1.197 (x264) / 1.184 (x265); set_attn anyk
    1.128 / 1.103 (best on both); set_mm anyk 1.133 / 1.111; mlp anyk 1.143 / 1.125.
    GATE 1: PASS as written. vs mlp per-k: set_attn anyk -0.069 [-0.115, -0.032] (x264), -0.081 [-0.138, -0.034]
    (x265); cut GOPs -0.124 / -0.097 (not worse; better). Per-k set nets also below mlp per-k (-0.027..-0.050).
    BUT most of the gain is POOLING k, not the architecture: mlp anyk alone -0.054 / -0.059. Architecture at equal
    data (set - mlp, both anyk, paired; computed ad hoc 11-11 20:50, not yet in a results file): set_attn -0.015
    [-0.038, +0.004] (x264, n.s.) / -0.023 [-0.046, -0.004] (x265); on CUT GOPs x264 -0.054 [-0.106, -0.019],
    x265 -0.019 n.s.; set_mm -0.010 n.s. / -0.015. Size: about 6% lower MAE overall (1.20 -> 1.13 QP), accuracy
    0.30 -> 0.31. Reading: a structured encoder + pooling k imitates the oracle slightly better, mostly via k
    pooling; the architecture adds a small extra gain, larger on cut GOPs for x264. Whether ~0.07 QP better
    imitation moves the encode score is the day-2 question (bc@prev's deficit is mostly the base QP, so expect
    small effects). Day 2 needs: rl.py BC with --arch and k-pooled training, eval at every k; candidates set_attn
    anyk + mlp anyk (control, separates pooling from architecture). Waiting for Aayush's go.
  DAY 2 (Aayush 11-11 ~20:55: "go ahead with day 2"): repo-pavneet experiments/rl.py --arch {mlp,set_mm,set_attn}
    (BC only; nets.make) and --train-ks 0,2,5,10,29 (one BC net on the pooled k datasets, evaluated at each k);
    run name part "attn-kall" / "mlp-kall" -> lfq_compare labels bc_attn-kall@prev / bc_mlp-kall@prev. Smoke (x264_lfq
    --quick, set_attn, ks 0,5): trained + evaluated at k0 and k5 on val/test, eval.pkl + policy.pt written; the
    process then hung at exit on a /scratch1 read of a package METADATA file (filesystem, node b22-06; unkillable),
    and rm of the smoke dir rcwork_v1/x264_lfq/results_rl_quick/bc_k0_fixed_attn-kall_s0 hung too (delete it later).
    Run list runs_v1/arch_bc.txt: set_attn and mlp, train-ks 0,2,5,10,29, seeds 0-2 (6 runs per encoder). Work dir
    lfqp (same data/base as bc@prev). Expected ~30-45 min per x264 run (old per-k BC ~6-8 min, now 5 evals).
    GATE 2 (written before the runs): on VAL, bc_attn-kall@prev beats bc@prev (per-k mlp) pooled over k with a CI
    excluding 0 on both encoders; the mlp-kall control tells how much is pooling vs architecture. Test reported
    either way; also vs final4.
    SUBMITTED 11-11 21:09 (Aayush OK; b22-06 added to bad_nodes first): x264 14032845, x265 14032846
    (RC_WORKNAME=lfqp RC_RUNS=runs_v1/arch_bc.txt; x265 RC_TLIM 6:00:00). Next when done: lfq_compare.py <enc>
    --ctrl-tag final4 (rows bc_attn-kall@prev, bc_mlp-kall@prev vs bc@prev), gate 2 on val.
    11-12: ALL 12 OUT OF MEMORY at 48G (peak 49.5G after building the dataset): pooling 5 k = 5x the single-k
    dataset (single-k BC peaks ~21.5G). Fix (before any result): rclib/offrl.trajectories_best keeps only the best
    plans per GOP x budget inside each worker (all BC trains on; same targets, checked equal on 12 GOP x k cases);
    rl.py uses it only for --method bc with --train-ks. Keeps ~7% of plans (100 GOPs, k5), so ~0.36x one k's data.
    Side note: ties for the best plan are common (up to 110 of 192 plans), so day-1's top-4 shortcut truncated
    some targets (footnote; day-1 is a relative comparison on the same data). RESUBMITTED 11-12 06:46 (Aayush OK):
    x264 14044104, x265 14044105.
    GATE 2 RESULT (11-12 ~08:30; scripts/gates_35_36.py -> results_v1/w5/gates_35_36.md; x265 mlp-kall 2 of 3 seeds,
    the 3rd still running): FAIL. bc_attn-kall@prev - bc@prev, val, pooled over k: x264 +0.015 [-0.071, +0.089], x265
    -0.037 [-0.087, +0.016]; test +0.025 n.s. / -0.024 n.s. Pattern on both encoders: one net over pooled k is much
    better at k0 (+0.53 / +0.20 val) and worse at k>=5 (about -0.1..-0.2), i.e. pooling helps where data per k is
    least useful and costs where per-k nets were best. Architecture at equal data (attn - mlp-kall), val: -0.054 n.s.
    (x264), +0.008 n.s. (x265); test x264 -0.024 [-0.042, -0.007] (attn worse). Day 1's ~6% better imitation did not
    move the encode score (consistent with bc@prev's deficit being the base QP, not the offsets). Both still far below
    final4 (-0.64 / -0.53 val). LINE STOPPED per the plan (no days 3-5 residual RL with the new net).
- [x] 37. UNDER-TRAINING TEST, RESIDUAL (Aayush 11-11 ~21:15: line up 2-3 overnight tests and submit). res@hist used
  60k PPO steps; does 3x (180k) beat it? New rl.py flag --ppo-steps (run-name part st180k; label res_st180k@hist).
  runs_v1/res_st180k.txt: k 0/5/29 x seeds 0-2, work dir resh, final4 setting, dB reward (same as C2 otherwise).
  GATE (before results): on VAL, res_st180k@hist - res@hist (same k and seed, paired) > 0 pooled over the 3 k with a
  CI excluding 0 on at least one encoder -> "under-trained"; also report vs final4 on val/test.
  SUBMITTED 11-11 ~21:20 (Aayush OK): x264 14032893 (8 h limit), x265 14032905 (12 h).
  11-12: x265 9/9 done; x264 3/9 done, 6 died at start on node b05-21 (numpy import failed, rc 1; not caught by the
  auto-retry). Rerun tasks 1,3,4,5,7,8 as 14044101 (Aayush OK 06:46).
  RESULT (11-12 ~09:00; scripts/gates_37_38.py -> results_v1/w5/gates_37_38.md): NOT under-trained; GATE FAIL.
    180k - 60k, val, pooled k 0/5/29: x264 -0.085 [-0.173, -0.003] (WORSE; test -0.119 [-0.165, -0.074]), x265 +0.028
    [-0.050, +0.097] n.s. (test +0.016 n.s.). k0 gains ~+0.1 on both, k5 loses (x264 -0.28). Still below final4:
    val -0.28 (x264) / -0.12 (x265). Runs took 21-25 min (x264) / ~1 h (x265), far below the 8/12 h limits.
- [x] 38. UNDER-TRAINING TEST, CQL->PPO ON THE PREV-GOP BASE: same flag, runs_v1/lfqp_st180k.txt (cql_ppo, k 0/5/29
  x seeds 0-2, 180k PPO steps; work dir lfqp; label cql_ppo_st180k@prev). GATE: on VAL, vs cql_ppo@prev (60k) paired,
  pooled over k, CI excluding 0 on at least one encoder.
  SUBMITTED 11-11 ~21:20 (Aayush OK): x264 14032920 (8 h), x265 14032921 (12 h).
  11-12: x265 7/9 done, tasks 0,3 died on b05-21 -> rerun 14044102 (Aayush OK 06:46). x264: all 9 were requeue-held
  by the auto-retry since 22:06 (its helper job never ran: all 4 debug nodes drained); released by hand 06:40 with
  b05-21 excluded. Until debug is back, auto-retry holds do not clear themselves.
  RESULT (11-12 ~09:00; scripts/gates_37_38.py -> results_v1/w5/gates_37_38.md; x265 k0/k5 seed 0 still queued
    (14044102), so x265 = 7 of 9 runs): GATE PASS, CQL->PPO WAS UNDER-TRAINED. 180k - 60k, val, pooled k 0/5/29:
    x264 +0.428 [+0.376, +0.474], x265 +0.318 [+0.257, +0.371]; test +0.391 / +0.293. Largest at k0 (+0.78 / +0.60
    val), then k5 (+0.39 / +0.26), k29 (+0.11 / +0.17). Mechanism: budget use 0.93 -> 0.99, but MORE episodes over
    (x264 val 28% -> 37%, k0 44%): it learned to spend the whole budget, overshooting by small amounts.
    vs final4 (180k), pooled: x264 val -0.24 [-0.38, -0.12], test -0.15 [-0.21, -0.09]; x265 val -0.18 [-0.32,
    -0.04], test -0.07 [-0.17, +0.04] n.s. Per k test: x264 -0.21 / -0.15 / -0.10 (k0/5/29, all CIs < 0); x265 -0.11
    / -0.12 n.s. / -0.01 n.s. First learner that is not significantly below final4 somewhere (x265 k5/k29 test), but
    not above it either. Train-curve scores are still noisy at 150k, so a plateau is not shown.
  FINAL x265 (11-12 ~11:50, all 9 runs after 14044102): 180k - 60k val +0.328 [+0.266, +0.383], test +0.304 [+0.260,
    +0.357] (k0 +0.56, k5 +0.25, k29 +0.17 val); use 0.93 -> 0.98, % eps over 24 -> 30; vs final4 val -0.193 [-0.353,
    -0.050], test -0.090 [-0.188, +0.020] n.s. Verdict unchanged.
- [x] 39. LAGRANGIAN PENALTY SWEEP ON THE PREV-GOP BASE (EXPERIMENTS P4, reduced): lam 0.17 = cql_ppo's own reward
  (11-11 finding), so test stricter penalties: lam 0.34 (default, label lagr@prev) and 0.68 (lagr_lam0.68@prev), k
  0/5/29 x seeds 0-2 (runs_v1/lfqp_lam.txt, 18 runs per encoder). The learners' main deficit is budget handling
  (cql_ppo@prev over budget on ~28-38% of test episodes). Report score, dPSNR_B, budget use and % over vs lam
  (0.17 = cql_ppo@prev); pick lam on VAL, report test; vs final4.
  SUBMITTED 11-11 ~21:20 (Aayush OK): x264 14032955 (4 h), x265 14032956 (6 h).
  RESULT (11-12; both 18/18 done; scripts/lam_sweep.py -> results_v1/w5/lam_sweep.md, from lfq_compare_<enc>_final4.csv;
    k 0/5/29 pooled, seeds averaged; x264 also has the older lagr_lam0.17@prev, which differs from cql_ppo@prev there):
    a higher price cuts overshoot but costs more quality than it saves. x264 val score / use / % eps over:
    rel(cql_ppo) -0.919 / 0.93 / 28%; 0.17 -0.869 / 0.95 / 31%; 0.34 -1.063 / 0.90 / 21%; 0.68 -1.495 / 0.80 / 9%.
    x265 val: 0.17(=rel) -0.885 / 0.93 / 24%; 0.34 -1.003 / 0.90 / 20%; 0.68 -1.458 / 0.82 / 12%.
    vs lam 0.17 (val, paired): 0.34 -0.194 [-0.307, -0.063] (x264) / -0.118 [-0.157, -0.079] (x265); 0.68 -0.63 / -0.57.
    Pick on val: lam 0.17 (both encoders; on x265 = cql_ppo@prev). Test: x264 -0.689 vs final4 -0.487 [-0.609, -0.385];
    x265 -0.687, vs final4 -0.394 [-0.521, -0.266]. Every lam is below final4 at every k on both splits.
    Reading: the learners' overshoot is not a missing incentive. A stricter price makes them underspend across the
    board (use 0.93 -> 0.80) while 9-12% of episodes still go over: they cannot track the budget precisely, so the
    price only moves the operating point along a worse trade-off. Budget tracking (feasibility) is the deficit.
  After 37-39 finish: lfq_compare.py <enc> --ctrl-tag final4 picks up all new rows (labels above).
- [x] 40. CQL->PPO, 540k PPO STEPS (9x the original; Aayush 11-12 ~09:05: "set up the 540k runs with k2 and k10").
  Follow-up of item 38 (180k gained +0.3..+0.4 dB over 60k). runs_v1/lfqp_st540k.txt: cql_ppo, k 0/2/5/10/29 x seeds 0-2
  (15 runs per encoder), --ppo-steps 540000, work dir lfqp (previous-GOP base), label cql_ppo_st540k@prev. Time
  limits from the 180k run times (x264 33-41 min, x265 1.2-2.1 h, so ~3x): x264 6 h, x265 12 h.
  GATES (written before results), val, paired same k and seed, CIs = 95% bootstrap over clips:
    (a) still improving: 540k - 180k pooled over k 0/5/29 > 0 with CI excluding 0 on at least one encoder.
    (b) vs the baseline: 540k - final4 pooled over k 0/2/5/10/29 > 0 with CI excluding 0 on at least one encoder
        ("a standalone learner beats the frozen controller"); report per k and test either way.
  Also reported: budget use and % episodes over vs steps (60k / 180k / 540k), since the 180k gain came from spending
  the full budget with more small overshoots.
  SUBMITTED 11-12 09:05 (Aayush OK): x264 14049395 (6 h), x265 14049410 (12 h).
  11-12 09:12: x265 task 1 failed in 1 s at the x265 version guard on b09-17 although the log shows "version 4.1".
    Cause (verified with strace): x265 --version writes its 3 lines as 3 separate unbuffered stderr writes; 'x265
    --version 2>&1 | grep -q ...' under set -o pipefail fails whenever grep -q exits before the 2nd/3rd write (x265
    gets SIGPIPE). A timing race (0/1000 on the interactive node), so the earlier "x265 version guard failed after
    1 s" bad-node entries (a02-17, a01-08, a02-11, b10-19, b04-16, a01-02) were probably false alarms. Fixed in
    repo-pavneet tools/job_env_v1.sh (grep on the captured output); jobs/rd_native.sbatch and p2_step.sbatch keep the
    old pattern (not in use now).
    Task 1 RERUN 09:20 as 14050090 (Aayush OK).
  x264 RESULT (11-12 ~12:00, 15/15; scripts/gates_40.py -> results_v1/w5/gates_40.md; x265 still running):
    (a) 540k - 180k, val, pooled k 0/5/29: +0.094 [-0.001, +0.183] (CI just touches 0 -> not passed on x264);
        test +0.103 [+0.068, +0.137]. Per k about +0.08..+0.10. Diminishing: 60k -> 180k was +0.43.
    (b) 540k - final4, val, pooled k: -0.150 [-0.373, +0.013] (not passed); test -0.069 [-0.132, -0.007]. Per k
        test: k0 -0.08 *, k2 -0.13 *, k5 -0.05, k10 -0.06, k29 -0.02 (last three n.s.).
    Budget: use 1.00 (val) / 0.99 (test); % eps over falls back to 30% / 29% (180k: 37%). Verdict waits for x265
    (both gates need only one encoder).
  11-12 13:02 (Aayush OK): the 12 queued x265 tasks had waited 4 h on main (1,171 jobs pending); scontrol update
    Partition=main,oneweek on 14049410 and 14050090 -> 12 tasks started at once on oneweek nodes d18-22..d18-33. Next when done: lfq_compare.py <enc>
  --ctrl-tag final4, then extend scripts/gates_37_38.py (or a sibling) for gates (a) and (b).
  FINAL RESULT (11-13 08:45, x265 15/15; results_v1/w5/gates_40.md, lfq_compare_x265_final4.{md,csv}):
    (a) PASS on x265: 540k - 180k, val, pooled k 0/5/29 +0.149 [+0.088, +0.220] (test +0.116 [+0.082, +0.153]);
        x264 val +0.094 n.s. -> still improving, with diminishing steps (60k -> 180k was +0.3..+0.4).
    (b) FAIL: 540k - final4, val, pooled k: x264 -0.150 [-0.373, +0.013], x265 -0.060 [-0.199, +0.073];
        test x264 -0.069 * (worse), x265 +0.003 [-0.086, +0.107] (TIE; per k all n.s., k29 +0.08).
    x265 540k test -0.267 vs final4 -0.270: the first standalone learner to tie the frozen controller (x265 only).
    Why it still loses on x264: quality before the penalty is as good or better (test dPSNR_B +0.008 vs final4
    -0.018; x265 -0.074 vs -0.120), but it overshoots more: 29% / 26% of episodes over by 5.2% / 4.4% on average
    when over (final4: 54-56% of episodes, about 1.7% when over). Penalty 0.25 vs 0.16 dB (x264).

- [x] 41. NEXT EXPERIMENTS (Aayush 11-13: docs/next-experiments-2026-11-13.md + agent brief, amendments in its
  Part E). Work in exp_next/, results in results_v1/next/.
  - [x] Exp 0 first-hour checks -> exp_next/exp0/CHECKS.md (train parity 40/40 exact per encoder, run on the
    interactive node). Open decision for Aayush: R2 cap handling (recommend (a), keep resh behaviour).
  - [x] Exp 1 decomposition + headroom -> exp_next/exp1/REPORT.md. Both stop rules clear (H +0.37 dB, R^2 0.33 /
    0.38). Brief A2 slope correction proposed (0.036-0.064 dB per 1%, not 0.085). Level-24 hole fix: proposal only.
  - Code (repo-pavneet branch next-exp, uncommitted; diff before at exp_next/repo_before.patch): rl.py --eval-splits
    (default val,test) and --save-at (checkpoint + eval_ckpt.pkl). Regression 5/5 exact (exp_next/regress_eval.py);
    smoke exp_next/smoke_resh_x264 OK. jobs/p2_step.sbatch version guards fixed (here-string, no SIGPIPE race).
  - [x] Exp 3 residual lam 0.17 (exp_next/exp3/PREREG.md, runs_v1/next_exp3.txt): x264 14189238, x265 14189239
    (Aayush OK 11:20), 12/12 COMPLETED (x264 32-44 min, x265 85-103 min). REPORT exp_next/exp3/REPORT.md: PRIMARY
    lam0.17 - lam0.34 (180k) val pooled +0.137 [+0.109, +0.166] PASS (x264 +0.184, x265 +0.090, k0 +0.093, k5 +0.180,
    all seeds +). vs final4: x264 -0.071 *, x265 -0.003 n.s., pooled -0.037 n.s.; 60k ckpt -0.018 n.s. (180k - 60k
    -0.019 n.s.). => R1 = lam 0.17 for Exp 4.
  - [x] Exp 10 ABR margin (exp_next/exp10/PREREG.md, abr_margin.py): x264 14189250, x265 14189252 (Aayush OK 11:20),
    COMPLETED in 2-3 min. Report results_v1/next/exp10/abr_margin.md (abr_margin_report.py). Val score, hole excluded,
    m 1.00 / 0.99 / 0.97 / 0.95: x264 -1.70 / -1.62 / -1.51 / -1.43, x265 -1.51 / -1.43 / -1.31 / -1.22. A stays
    -0.69 / -0.75 at every m (the margin only fixes overshoot). SELECTED m = 0.95 both encoders (grid edge: a lower m
    might score more; extending the grid would change the PREREG, not done).
  - Train-select fold frozen: exp_next/folds.json (exp_next/make_folds.py; 8 single-group train clips, 75 GOPs, 3 with
    natural cuts).
  - Exp 2 handoff: exp_next/exp2/handoff.py + PREREG.md; parity m=0 vs learner 8/8, m=30 vs final4 8/8 exact (both
    encoders).
    SUBMITTED 11-13 12:38 (Aayush OK): x264 14200366, x265 14200367 -> ALL 8 TASKS FAILED at the final write (10-28
    min in): the torch env envs/rc has no pyarrow, so to_parquet raised ImportError and the episodes were lost (~22
    CPU-h of allocation). Fix: write a pickle (.pkl) + --limit smoke option; smoke of the full path incl. the write
    in the job env OK. RESUBMITTED 11-13 13:28 (Aayush OK): x264 14207330, x265 14207331.
    [x] DONE (x264 12-15 min, x265 27-28 min per shard). REPORT exp_next/exp2/REPORT.md: GATE FAIL on all three
    conditions: m=10 hybrid - final4 -0.052 [-0.146, +0.056] (x264 -0.109 *, x265 +0.005), spend error 4.16% vs
    final4 2.55%. Handoff helps the learner +0.02..+0.04 (m 3-10) but a longer handoff under-spends more (signed -3..-4%
    at m=20): final4's single-slope rate model, calibrated at the learner's QPs, over-predicts the rest. Line stopped.
  - [~] Exp 4 R2 (exp_next/exp4/PREREG_R2.md, runs_v1/next_exp4_r2.txt): code on next-exp (controller decide(diag=),
    env --extra f4 + cap counters, config RC_RES_RANGE, run name gets _r6); regression defaults parity 24/24 and
    stored-episode 5/5 per encoder; smoke + forced-offset check (exp_next/exp4/check_f4.py) OK.
    SUBMITTED 11-13 (Aayush OK): x264 14213909 (2 h), x265 14213910 (5 h), RC_RES_RANGE=6, main,oneweek.
    [x] DONE 12/12 (x265 ~85 min). REPORT exp_next/exp4/REPORT_R2.md (report_r2.py -> results_v1/next/exp4/
    r2_report.md): GATE FAIL: R2 - R1 pooled +0.040 [+0.023, +0.061] (x264 +0.070 *, x265 +0.010), but k0 -0.004
    and seed 1 -0.016. Gain all at k5 (+0.083). R2 vs final4 +0.003 n.s. (ties on both encoders). Caps flag: at k5
    27-28% of non-zero offsets go beyond final4's dmax (> 20%) -> report to Aayush before R3.
  - [~] Exp 5 shape BC (exp_next/exp5/PREREG.md, build.py): check (a) 91.2% / 91.5% (< 95%), all mismatches from
    labels clipped at frames 0-1; Aayush 11-13: option (a), accept with clipping reported. Smoke of the full build
    (6 GOPs) OK; already shows check (b) |mean label| up to 2.5 QP (> 0.5 -> report before training).
    SUBMITTED 11-13 ~16:00 (Aayush OK): build x264 14218410, x265 14218411 (16 CPU, 64G, 2 h).
    DONE (x264 7.7 min, x265 3.9 min): 515 GOPs, ~102k plans per encoder, ~3.06M rows per k (data_<enc>_k<k>.npz
    2.2 GB each, labels_<enc>.md). Clipped labels 0.5-0.9%. CHECK (b) FAILS: mean label I frame +0.6..+0.7, frame 1
    -1.7..-2.2, frames 2-29 -0.15..-1.9 (avg P -0.9..-1.1 QP), max |mean| 1.87-1.90 > 0.5 -> stopped before training,
    reported to Aayush.
    Aayush 11-13: option 3 (shift-only test) first, then centred BC (option 1); raw labels never used. Recorded as a
    PREREG deviation (exp_next/exp5/PREREG.md) + new exp_next/exp5/PREREG_SHIFT.md (Exp 5a) before any fit/training.
    build.py labels confirmed to be against final4's CAPPED proposal (env.q_ctrl = decide() after fcap/dmax/pmin).
    Code: RC_RES_RECAP=1 (rclib/config.py + env.step; default off) re-applies final4's limits after the offset.
    exp_next/exp5/shift_fit.py (no encodes) -> shifts.json, shift_fit.md; shift_eval.py (--check: offset 0 = final4
    10/10 x264, 6/6 x265, recap 0 and 1); shift_report.py. First fold submission rejected by Aayush (revised plan below).
    REVISION 2 (Aayush 11-13, PREREG_SHIFT.md, before any encode): smooth 4-param shift (I, frame 1, ramp f2-f29),
    real-valued, added before final4's rounding (decide diag q_real; env.res_float) -- the per-frame means are jagged
    from the search's start-ramp rounding (corr 0.60-0.65). Cap arms split: none / bit (fcap + spent->51) / full
    (RC_RES_RECAP=0|bit|full). Arms {pooled,perlevel} x {none,bit} + pooled:full reference, beta 0.1. shift_smooth.py
    -> shifts_smooth.json (I offset by level -0.5 (L24) .. +2.0 (L42)). Parity offset 0 = final4 12/12 per encoder,
    all cap rules. Go/no-go redone without own history (gng_nohist.py; full-obs 0.52-0.60 at k5 not used).
    SUBMITTED 11-13 (Aayush OK): fold x264 14230659 (1 h), x265 14230660 (1.5 h), 16 CPU, 16G.
    x264 fold DONE (6 min, 3000 episodes). Go/no-go without own history (gng_nohist.md): R^2 of the centred label
    at k5 x264 0.417, x265 0.420 (k0 0.53 / 0.55; drop o[6] only 0.465) -> GO for centred BC without o[5..8]. Caveat:
    budget state and final4-state features still carry the plan's past spend.
    x265 fold DONE (19.5 min). Fold report (shift_report.py --split fold -> shift_fold.md, shift_selected.json):
    best selectable arm perlevel:none on both (x264 +0.036, x265 +0.105 vs final4); perlevel:bit within 0.005
    (+0.032 / +0.103) -> SELECTED perlevel:bit on both encoders (pre-registered tie-break). Selected by k: x264 k0
    +0.001 (n.s.), k5 +0.062 *; x265 k0 +0.089 *, k5 +0.116 *. Pooled arms ~0 (x264) / +0.04 (x265); pooled:full ref
    +0.009 / +0.069. Spend: % over +4.5 / +6.3 pts vs final4, signed err -0.67 / -0.55 pp (under the +10 / +1 flags).
    Val run of perlevel:bit HELD (Aayush 11-13): the budget level is clip-level hindsight (B = clip mean of
    constant-QP-L bits), so per-level arms are not deployable. REVISION 3 in PREREG_SHIFT.md (before fit/encode):
    causal arm per-qbin:bit = vector picked by final4's frame-0 planning QP binned at 27/33/39; per encoder, goes to
    val only if >= perlevel:bit - 0.01 dB on the fold, else no val run ("gain depends on level hindsight"). Val primary
    now per encoder; + per k, cut/gradual vs stable, spend split. shift_qbin.py -> shifts_qbin.json, shift_qbin.md
    (bin = budget level on 54-57% of plans at k0, 70-72% at k5; k5 qbin vectors close to per-level, k0 differ).
    shift_eval.py arm perqbin + --tag; parity: final4 frame-0 level reproduces the dataset 12/12 when run at the plan's
    spend S (dataset relabel; eval uses B, 0.03-0.3 QP apart). Smoke OK both encoders; report dry-run on synthetic rows OK.
    FOUND: env obs slot o[2] = (budget level != 24) is in every learner's observation (Pavneet's pilot flag; R1, R2,
    lfq runs and the Exp 5 BC data) -- a clip-level-hindsight bit; final4 does not see it. Reported to Aayush.
    SUBMITTED 11-13 21:27 (Aayush OK): fold perqbin:bit x264 14233506, x265 14233507 (16 CPU, 16G, 1 h).
    o[2]: Aayush OK to zero it for BC and R3 (not started); R1/R2 results keep a caveat, no retraining.
    DONE (x264 1.3 min, x265 3.1 min). shift_fold.md REVISION 3: per-qbin:bit x264 +0.008 (25% of perlevel:bit's
    +0.032; qbin - level -0.024 [-0.052, -0.004]; k0 -0.034, k5 +0.050 *), x265 +0.082 (80% of +0.103; -0.020
    [-0.040, +0.001]; k0 +0.032, k5 +0.132 *) -> FAILS the 0.01 dB rule on BOTH encoders: shift_selected.json all null,
    no REV3 val run; final4 stays the RL base. Failure confined to k0 (final4's GOP-start QP a poor proxy for the
    level); at k5 the causal shift recovers the per-level gain. Not confirmed on val. EXPERIMENTS row added (wording
    corrected per Aayush 11-13). REVISION 4 (Aayush 11-13, post-hoc): per-qbin:bit k5 only, val once.
    REV4 written in PREREG_SHIFT.md; shift_eval.py --ks, shift_report.py --rev4 (-> shift_val_rev4.md); dry run on
    synthetic rows OK.
    BC plan: exp_next/exp5/PREREG_BC.md (deploy final4 + mean[t] + BC(obs), mean = pooled per-position; drop o[2],
    o[5..8]; BC-only rung on the fold first; R3 zero-init for o[5..8], log-std = BC residual size, frozen-actor
    value warm-up). Not implemented yet.
    o[2] ablation (eval only, exp_next/o2/o2_eval.py, o2_report.py; env drop group "level" = slot 2, opt-in):
    unmasked re-eval reproduces stored val rows 8/8 for R2, R1, 540k on both encoders.
    SUBMITTED 11-13 ~22:35 (Aayush OK): REV4 val x264 14234291, x265 14234295; o2 R2/R1/L540 x264 14234292-94,
    x265 14234296-98.
    REV4 DONE (x264 1 min, x265 2.5 min; shift_val_rev4.md): x265 +0.153 [+0.044, +0.283] * HOLDS (A +0.136, mostly
    L42 +0.48); x264 -0.025 [-0.081, +0.034] does NOT. p90 |err| 3.4 -> 4.6% (x265), 3.7 -> 6.3% (x264); % over +8 / +6
    pts; level check none. -> stronger non-RL baseline at k5 on x265 only (RL k5 gains on x265 reported vs both).
    Aayush 11-13: o[2] zero arm overstates (tells the policy every GOP is level 24) -> causal stand-in arm added
    (o[2] = 1 if final4's frame-0 planning QP >= 27; f4_level0.py table, agrees with the true bit 88%; env o2_table
    hook, opt-in; checks 40/40 + stored-row parity 8/8). Zero-arm jobs left running. Stand-in SUBMITTED (Aayush OK):
    R2/R1/L540 x264 14234394-96, x265 14234397-99.
    Zero arm DONE (x264 ~6 min, x265 ~15 min); stand-in x264 DONE, x265 running. Partial o2_report.md: zero arm
    changes QPs on ~75% of episodes but the score barely moves (pooled R2 +0.005 *, R1 +0.002, 540k +0.006; largest
    cell 540k x264 k5 -0.045 n.s., L42 -0.20); stand-in within +-0.005 everywhere so far -> 'no change' row of
    Aayush's table (pending x265 stand-in).
    o[2] DONE (all 12 jobs; o2_report.md final): stand-in within +-0.005 dB in every cell except 540k x265 k0 -0.020
    [-0.045, -0.002]; pooled per group -0.005..0.000; zero arm pooled < 0.01. 'No change' row; caveat 'at evaluation'
    (training effect untested; BC / R3 trained without o[2]). EXPERIMENTS row added. NEXT: BC-only rung (PREREG_BC.md).
    PREREG_BC.md REVISION 2 (Aayush 11-13): R2 is Discrete(13) -> BC = classifier with R2's actor architecture, R3 keeps
    R2's head (no continuous mode); mean[t] = pooled smooth shift as res_float; target label2 = clip(plan -
    round(q_real + mean[t])). build.py --v2 (masked obs + q_real + label2). Checks: offset-0 parity 12/12 both encoders;
    v2 round trip 7/8 plans exact (8th = frame-0 clip); fold excluded in load(); smoke: obs cols 2,5-8 all zero.
    build v2 SUBMITTED 11-13 (Aayush OK): x264 14235662, x265 14235663. bc_train.py, bc_eval.py (--check 12/12 both
    encoders), bc_report.py written + smoked; PREREG_BC REVISION 3 (training details). SUBMITTED (Aayush OK), chained
    afterok: BC train x264 14235702 -> eval 14235703; x265 14235704 -> 14235705. x265 build DONE 3.5 min: obs cols 2,5-8
    zero on all 3.06M rows (k0, k5); label2 per-frame means within +-0.63; same plan set as v1 (pid order differs).
    ALL DONE 11-14 (x264 build 8 min, train 31 min, eval 3 min; x265 train 19, eval 8). x264 v2 checks: cols zero on
    3.06M rows. bc_fold.md: BC-only - final4 x264 -0.327 * (k0 -0.549, k5 -0.105 *), x265 -0.193 * (k0 -0.426, k5 +0.040
    n.s.); landing failure (k0 mean |err| 15% / 11%, signed -13% / -9%), A equal or better. On logged states offsets
    unbiased; in closed loop +0.8..+1.4 QP at k0 -> closed-loop drift. EXPERIMENTS row added. R3 decision -> Aayush.
    Aayush 11-14: option 2 = R3 at k5 only. PREREG_BC REVISION 4: R3 (R2 recipe + o[2] masked + mean[t] + bit cap + BC
    init + 20k critic warm-up) and control R2c (same, no BC init), 3 seeds x 2 enc; gate R3 - final4 val k5 >= +0.03,
    CI > 0. Code (opt-in, names of old runs unchanged): env res_mean; rl.py --res-mean/--init-bc/--warmup + run-name
    parts. Checks: step-0 reproduces BC-only rows 12/12 per enc (exp_next/exp4/r3_step0.py); actor frozen in warm-up;
    eval path OK; smoke run deleted. fold_r1r2.py (precondition). runs_v1/next_exp4_r3.txt.
    SUBMITTED 11-14 (Aayush OK): R3+R2c arrays x264 14239343 (3 h), x265 14239344 (5 h); fold R2/R1 x264 14239345/46,
    x265 14239347/48.
    Fold precondition DONE (fold_r1r2.md): R2 - R1 at k5 +0.093 [+0.068, +0.121] * -> R2 setup stands.
    x264 R3/R2c DONE (33 min each). x265 task 1 (R3 s1) hit SIGBUS on d18-35 (already in bad_nodes 11-03); auto-retry
    helper ran but did not apply -> manually excluded d18-35 and released 14239344_1 (restarts from scratch).
    exp_next/exp4/report_r3.py written. PARTIAL x264 (r3_report_x264.md, not the gate): R3 - final4 +0.066 [+0.012,
    +0.124] *, R3 - R2c +0.118 *, R3 - R2 +0.052 *, R2c - R2 -0.066 *, R3 180k - 60k +0.069 *; all seeds > 0; gain in A
    (+0.036) and E-P (+0.029); % over 27% vs 56%. Waiting for x265 (gate pooled over both).
    Aayush 11-14: report_r3.py relabelled (R2c = control: R3 setup, standard init; R3 - R2c = BC-start effect; R2c - R2
    = cost of setup changes -0.066 *, incl. 20k frozen warm-up); x265 vs final4 + shift printed next to the gate;
    signed spend error note. F drafted: exp_next/final/PREREG.md (branch A = R3 recipe k5 / B = R2 recipe no o[2]),
    fresh seeds 3-5, 180k fixed (360k optional secondary in A). 36-hour fallback (Aayush, other session): if R3 is not
    finished and read on val in time, run F with R2's recipe -- recorded in exp_next/final/PREREG.md. (Aayush 11-14: ignore it for now.)
    x265: 5/6 done (~1h26 each); R3 s1 (restarted) at 104k at 10:30. Interim (per seed, no bootstrap): R3 s0 / s2 vs
    final4 +0.213 / +0.164, vs final4 + shift +0.060 / +0.011, % over 13% / 25%; R2c s0-2 vs final4 +0.04..+0.06,
    vs final4 + shift -0.10..-0.11.
    Exp 6 gate DONE (exp_next/exp6/PREREG.md + gate.py -> results_v1/next/exp6/gate.md): FAIL +0.027 [-0.000, +0.050]
    (x264 +0.000, x265 +0.054 *; oracle +0.109) -> stop, no bandit. EXPERIMENTS row added.
    R3 cut breakdown x264 (exp_next/exp4/r3_cuts.py -> r3_cuts_x264.md; descriptive): stable +0.080 *; cut groups
    small (early 4 / mid 35 / late 23 / no detected cut 24 episodes, few clips): mid -0.031 n.s., late -0.056 *;
    R3 raises QP before the cut (+0.3..+1.0 vs stable -0.42) and lowers after (-0.2): saves for the cut, no gain.
    Rerun with x265 when R3 s1 is done.
    R3 ALL DONE 11-14 (x265 s1 1h27 after restart). r3_report.md: GATE PASS R3 - final4 pooled +0.128 [+0.050, +0.216]
    (x264 +0.066 *, x265 +0.190 *); R3 - R2c +0.131 *; R3 - R2 +0.105 *; x265 R3 - (final4 + shift) +0.037 [-0.000,
    +0.071]; 180k - 60k +0.056 *. Cuts (r3_cuts_x264_x265.md): stable +0.146 *, cut groups small / mixed. EXPERIMENTS
    row added. -> F = BRANCH A (exp_next/final/PREREG.md). Next: F code (test splits, BC seeds 3-5), sbatch to Aayush.
    Aayush 11-14: 360k as secondary. rl.py LR / entropy / clip constant -> one 360k run per seed, primary = checkpoint
    --save-at 180993 (= end of a plain 180k run: 896 steps/update, warm-up ends 20,608, 180k run ends 180,992);
    verified bit-identical on a scaled pair (test runs deleted). runs_v1/final_r3_s345.txt (seeds 3-5, val only).
    F stage-1 sbatch (BC seeds 3-5 -> R3 array) awaiting OK.
- [x] 42. Exp 7 (Aayush 11-14: run it ourselves this weekend; freeze into exp_next/final/PREREG.md by Monday; F stage 1
  first; --exclude d18-35 + flaky list on every sbatch). STEP 0 DONE (exp_next/exp7/STEP0.md, PROVENANCE.txt;
  copies in exp_next/exp7/src_pavneet (eb08445), src_sara (1860557)): Pavneet clean (train / val); Sara's LOFO and
  margin 0.96 tuned on test (flag); Sara has no checkpoints; ED/ToS are v1 test clips; no v1 clip >= 16 GOPs (val
  chain: sita only); rule optimum on the qpd grid edge. Reported to Aayush; nothing launched for Exp 7.
  Aayush 11-14: 16/32 rule retuning on train chains bbb + sintel (c), sita as descriptive val check (a), no spliced
  tuning; widen qpd until interior, report rule 'as reported' and 'retuned'; Sara's PID-Lag: one retrain, her
  defaults, enters val selection only if done by Sun 11-15 23:59, sanity check vs her description.
  F stage 1 SUBMITTED (Aayush OK): BC x264 14245950 -> R3 14245951, BC x265 14245952 -> R3 14245953.
  STEP 1 DONE: all 24 Pavneet policies + rule (rule_wide, baselines, L0/L2) reproduce exactly on val, both encoders
  (results_v1/next/exp7/repro_<enc>.md, exp_next/exp7/repro.py). STEP 2 PREREG written (exp_next/exp7/PREREG.md).
  PID-Lag: work copy /scratch1/aayushso/rcwork_exp7/<enc>_v1; exp_next/exp7/run_pid.py + pid_launch.py (her
  train_pid.py byte-identical to 1860557, test eval skipped); smoke OK (ppo_pid + bc_ppo_pid). SUBMITTED (Aayush OK):
  x264 14247200, x265 14247201. Rule retuning running locally (exp_next/exp7/rule_tune.py; 0.4 s per setting).
  F stage 1: BC s3-5 done (x264 21 min, x265 10 min); x264 R3 360k done (42 min each, full 360k, ckpts 60000 /
  180993 saved). x264 val R3 - final4 per seed (hole excl.): 180k +0.054 / +0.063 / +0.089 (mean +0.069; R3 was
  +0.066), 360k +0.103 / +0.104 / +0.040 (secondary). x265 R3 running.
  Rule retuning run 1 (results_v1/next/exp7/rule_{8,chain}_<enc>.md): retuned rule much stronger on val same-clip 8-GOP:
  L2 x264 -0.623 -> -0.497, x265 -0.453 -> -0.294 (qpd 4.5-5.5, cw -> small). cw stopped at 0.0625 on the edge ->
  v2 rerun with cw down to 1e-6 (natural 0+ limit; cw = 0 is 0/0 on GOP 1) running locally (rule_*_v2).
  Candidates (stored val, same-clip, L2, seeds avg): x264 ppo -0.483, bc_ppo -0.469, bc_ppo_lag -0.490; x265 ppo
  -0.373, bc_ppo -0.373 -> vs retuned rule (run 1): x264 +0.01..+0.03, x265 about -0.08 (rule tuned in-sample on
  these val streams). Selection + Part 2 decision wait for v2 + PID-Lag.
  PID-Lag retrain DONE (x264 17 min, x265 38 min; Sat, before the Sun deadline). Rule v2 8-GOP: x264 L2 (1.0, 5.0,
  0.0625) -0.4995, x265 L2 (0.99, 4.5, 0.0625) -0.2937, interior. SELECTION (select_policy.py -> select_<enc>.md):
  x264 bc_ppo, - retuned rule +0.030 [-0.127, +0.401] (ppo +0.017, bc_ppo_pid +0.013, ppo_pid -0.049) -> Part 2
  ALLOWED (point > 0); x265 ppo (ppo = bc_ppo), - retuned rule -0.079 [-0.172, +0.077] -> Part 2 SKIPPED. vs rule as
  reported: +0.15 / +0.08. PID sanity OK: > 1 % over 4.5-8.1 % vs rule as reported 7.7-12.9 % (0.6-0.8x).
  Retuned rule lands closer (p90 |err| 7.4 / 5.4 %) but goes > 1 % over more (22 % / 10.5 %).
  Part 2 (x264 only; Aayush approved design 11-14, k5 inside, no R3): exp_next/exp7/part2_prep.py (analysis env ->
  part2_inputs_x264.pkl) + part2.py (rc env; controller_real.run_episode at B_g = controller's own predicted spend,
  h=3 history from the stream's previous GOP, first GOP qhat = base_qp_est_k5 interpolated in log B). Checks: (a)
  '+ constant QP' == Part 1 rows 144/144; (b) run_episode == stored final4 rows 3/3. Smoke: per-GOP |bits - B_g| mean
  1.0 %, 14 s per stream episode. Full run (2016 stream episodes: rule + bc_ppo s0-2 x 504 cases) SUBMITTED (Aayush OK): 14249071.
  Part 2 DONE (46 min; part2_x264.md, descriptive): score RL+CQP -0.469, RL+final4 +0.259, rule+CQP -0.500, rule+final4
  +0.543. final4 inside adds +0.73 (RL) / +1.04 (rule) over constant-QP GOPs (wide CIs); RL+final4 - rule+final4
  -0.284 [-0.534, -0.120]; rule+final4 lands best (signed -0.42 %, p90 1.86 %, 6.3 % over). Per-GOP |bits - B_g|:
  mean 3.6 / 3.8 % (check NOT met), median 0.5 %, p90 9-10 %, max 133-366 % (tail).
  F test-pass code (11-14/16): exp_next/final/eval_r3.py (val parity 48/48 both enc), shift_eval --split test,
  exp_next/exp7/test_eval.py (val check exact), part2 test split (val checks 144/144, 3/3), abr_margin.py --margins/
  --ks/--tag/--split test (smoke OK). Handoff dropped from the test pass (Aayush). ABR extension 0.90/0.93 on val
  SUBMITTED 11-16 (Aayush OK): x264 14289185, x265 14289186 (Exp 10 PREREG extension written first).
  ABR extension DONE (2.5 / 3 min): selected x264 0.90 (grid edge, -1.392 vs 0.93 -1.403), x265 0.93 (interior) ->
  FROZEN in exp_next/final/PREREG.md; EXPERIMENTS Exp 10 row updated; pre-extension report kept as abr_margin_before_ext.md.
  exp_next/final/report.py written; val dry run OK (results_v1/final/report_val.md; all stored scores = recomputed):
  R3 180k - final4 x264 +0.068 [+0.005, +0.139] *, x265 +0.204 [+0.081, +0.346] *; x265 vs final4 + shift +0.051 *.
  Part 2 test inputs prepared (part2_inputs_x264_test.pkl; inputs only).
  TEST PASS SUBMITTED 11-16 (Aayush OK): R3 14289635 (x264) / 14289638 (x265); ABR 14289636 / 14289639; Exp 7
  Part 1 14289637 / 14289640; shift x265 14289641; Part 2 x264 14289642. Then report.py --split test,
  part2_report.py x264 test, EXPERIMENTS + tracker.
  TEST RESULTS (results_v1/final/report_test.md): R3 - final4 x264 +0.066 [+0.022, +0.106] *, x265 +0.162 [+0.085,
  +0.243] * -> PRIMARY PASS both; x265 vs final4 + shift +0.074 *; 360k n.s. Exp 7 primary NOT met (x264 -0.026,
  x265 +0.050, CIs incl. 0). EXPERIMENTS row added. Part 2 x264 test DONE (54 min; part2_x264_test.md): rule + final4
  +0.364 best, RL + final4 - rule + final4 -0.388 *, per-GOP check mean 2.6-3.0 % (not met). TEST PASS COMPLETE 11-16.
  COMMITTED 11-16 (Aayush): repo-pavneet next-exp ca1bd00 (local only; Pavneet's private remote, never pushed); team repo
  p2-data-v1 fast-forwarded to origin/main 72e0b1d, then 9e4839f (p2_data sync + p2_data/exp_next + pavneet_pipeline
  refreshed from ca1bd00). origin/main moved to 926ec76 (Pavneet live-stream handoff, Sara P4 models; no overlap) ->
  merged into p2-data-v1 as 046d1f9 (2 ahead of origin/main, 0 behind). Aayush pushes: git push origin p2-data-v1 &&
  git push origin p2-data-v1:main. PUSHED 11-16 (verified: origin/main = origin/p2-data-v1 = 046d1f9).
  11-16 wrap-up (Aayush): team message docs/team-update-2026-11-16.txt; final write-up docs/final-writeup-2026-11-16.md;
  TA briefing section 6 correction (spend-error spread + local slope, Exp 1) and R3 'superseded' note added;
  deleted empty rcwork_v1/x264_lfq/results_rl_quick/bc_k0_fixed_attn-kall_s0; scripts/sync_to_repo.sh now also syncs
  exp_next/ (code/docs/logs only); scripts/sync_project2.sh all DONE 10:54 (about 19 GB copied, exit 0; log
  logs/sync_project2_2026-11-16.log).
  11-17: team repo commit 849c0c0 (final write-up, team update, cap_fix.py, report --psnr-cap, EXPERIMENTS/tracker,
  sync script) on p2-data-v1; PUSHED 11-17 (origin/main = 849c0c0, verified). TA briefing and the reply to Ahhana stay local.
  Ahhana 11-16 update: reply drafted docs/reply-ahhana-2026-11-16.txt. PSNR-cap correction (11-16, from Ahhana): one convention everywhere, each plane's per-frame PSNR capped at 100 dB (curves recomputed from rd_frames; final4 re-measured by re-encoding its stored QPs, bits identical; exp_next/final/cap_fix.py, report.py --psnr-cap -> results_v1/final/report_{val,test}_cap.md). Affected scored GOPs: MusicVideo_360P-5f07 @30/@180 (val), MusicVideo_360P-5699 @0 (test). Test R3 - final4: x264 +0.066 -> +0.067 [+0.023, +0.107], x265 +0.162 -> +0.163 [+0.086, +0.243]; x265 vs final4 + shift unchanged +0.074; cut/gradual +0.056 -> +0.060 / +0.098 -> +0.102. Val: x264 +0.068 -> +0.077, cut/gradual +0.016 -> +0.069 (= Ahhana's), x265 +0.204 -> +0.209. Exp 7 unchanged.
  F stage 1 DONE: fresh seeds 3-5 val R3 - final4 at 180k: x264 +0.054/+0.063/+0.089 (mean +0.068), x265 +0.178/
  +0.207/+0.227 (mean +0.204) -- replicate R3 (+0.066 / +0.190); 360k secondary +0.082 / +0.198; 60k +0.026 / +0.139.
    PREREG_BC.md REVISION 1: R2's setup (R1 only if R2 clearly loses on the fold), BC obs = R3 obs, Gaussian PPO
    with mean = BC net + mean[t], step-0 reproduction check vs the BC-only rung, bit cap only. Next in item 41: centred BC (GO) without o[2], o[5..8].
  - [x] Exp 4 R3, Exp 6 gate, Exp 7: all done 11-16 (stale line kept for history);
    every sbatch shown to Aayush first.
- [ ] 32. PROPOSED (Aayush 11-11, not approved to run). BLOCK-LEVEL STATISTICS for the per-frame rate slope (gate).
  Idea (Aayush): texture/motion/noise at a finer level than the frame. Our action is ONE QP per frame (AQ off, forced
  QP), so finer features cannot say WHERE in a frame to spend; they can only improve the frame-level rate (and
  distortion) prediction: bits(q) = sum over blocks c_b 2^(-q/s_b), so a frame half flat (goes to skip) / half
  textured has a different slope than its average suggests. Item 28: per-frame P slope varies a lot (x264 3.7 / 5.0 /
  8.2 QP per halving at p10/50/90; controller uses one s = 5.5); the oracle slope would cut the post-calibration GOP
  spend error from 7-23% to 1.4-9%; frame-level first-pass make-up recovered little.
  Test (no encodes, few CPU-h, interactive or one small sbatch): per 16x16 macroblock (240 per 320x180 frame, the
  encoder's unit; 128x128 tiles are ~2x1.5 per frame, too coarse) compute spatial activity (luma variance / log
  energy, as x264 AQ), temporal activity (SAD vs previous frame, small motion search), a noise estimate; summarise per
  frame as a DISTRIBUTION (quantiles, flat-block fraction, high-motion fraction, entropy), not a position grid (66
  train clips: positions do not generalise). Target: each frame's true slope (and bits at q) from rd/rd_frames.parquet
  (constant-QP 18-50 per frame). Compare out-of-fold by source group: (a) current frame-level first-pass features,
  (b) a + block distributions, (c) a + a wider first-pass QP pair (26/38, the cheap alternative from item 28).
  Metrics: per-frame slope error; controller GOP spend error after calibration (as scripts/slope_gate.py).
  GATE: (b) beats (a) and (c) clearly, e.g. halves the gap to the oracle slope (CI over clips excluding 0). Only then:
  into the controller's rate model and/or the RL observation. Caveats: P-frame bits also depend on the reference's
  quality (no input feature sees it). Per-REGION QP (policy chooses where) would need the encoder C API (libx264
  quant offsets), a new action space and a change to P1's frozen settings: out of scope, separate project.
  Good parallel task for Pavneet/Atharva (only /project2 shared data needed).

- [ ] 33. PROPOSED (Aayush 11-11, not approved to run). FROZEN PRETRAINED VISION EMBEDDINGS (ViT) as features (gate).
  Question (Aayush): add a vision transformer for a deeper understanding of image content? Doubts: the ceiling is small
  (x264 test search +0.30 dB vs controller -0.18..-0.22); the first pass already measures rate-relevant content in
  the encoder's own terms (item 13 gate: richer first-pass stats help per-frame bits, not the GOP base QP; "k=0
  problem is missing future information"); the metric is PSNR (semantics/saliency matter for perceptual metrics; no
  libvmaf on CARC); 590 train GOPs / 66 clips -> end-to-end ViT would overfit, only a FROZEN pretrained model is
  realistic; literature: encoder RL uses encoder statistics, pixel CNNs are supervised rate predictors (~1-2% BD-rate).
  Plausible gains: gradual transitions (fades/dissolves), per-frame rate-distortion slope.
  Test (no encodes, few CPU-h): embed every frame (1042 x 30) with a frozen pretrained model (e.g. DINOv2-small, 224 px,
  CPU ~1 h); ridge regression, train only, out-of-fold by source group, on the RESIDUALS of the current best
  estimators: k0 base-QP error after the previous-GOP model (item 31), per-frame bits/slope error after first-pass
  (+ item 32's block statistics if run). GATE: k0 base-QP MAE -0.3 QP or a clear slope-error cut, CI excluding 0;
  otherwise stop. Same as EXPERIMENTS.md P9 (pixel features, gate first). Run after (or alongside) 32: 32 is cheaper
  and more targeted.

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
- [x] 12. Settle one canonical dataset/split with Pavneet (data v1 vs his 189-source windows); first-pass QP 30 vs 32
  DECIDED 2026-11-09 (Aayush): data v1 is canonical; all final results on data v1. (First-pass QP / codebase still open.)
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
- [x] 16. (DONE 11-05: Pavneet's V3 `docs/milestone_report_v3.docx` approved by Aayush; v1 data not in the body by choice, kept for the final report) (2026-11-03 call w/ Atharva, docs/zoom_meeting_summary.txt) MILESTONE REPORT due Wed 2026-11-04: lock readings
  by then. Aayush: post group summary (draft given in session 2026-11-03), shared clips (done). Atharva: wider budget
  QP range, longer clips, bare-bones vs full-feature encoders. Open from P1 (docs/Ahhana_update.txt): encoder flags
  differ from Pavneet's harness (preset medium vs fast, psy off vs on); forced-QP clamp check (ipratio/pbratio vs
  --crf+qpfile); action space relative vs fixed base; slice bits only (agreed by P2).
  FORCED-QP CHECK DONE 2026-11-03 (scripts/x264_forced_qp_check.sh, 1 GOP Animation_360P-3e40@0, x264 0.165.3222):
  Pavneet's --crf+qpfile = requested QP on 30/30 frames (incl. 11 and 51); Ahhana's --qp 31 --ipratio 10 --pbratio 10
  also 30/30; plain --qp clamps 24/30 frames into base +-3 (her finding, only for --qp). So Pavneet's x264 results are
  NOT affected. But the two forced-QP methods are not bit-identical (6-27 of 30 frames differ by a few bytes, totals
  within 0.3%), and preset fast/psy-on vs medium/no-psy changes total bits by 1.8% at the same QPs.
- [x] 18. (2026-11-04; PAUSED by Aayush 17:30) Causal online base-QP controller = P2's causal baseline, under the clip-level budgets
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
  REVISED 11-04 12:20: v2 implemented (a = ramp, b = cut boost on first-pass-flagged cuts: intra share > threshold,
  F1-fit on train: recall 0.95-0.97, precision 0.52-0.70 at 0.7). Equivalence a=b=0 vs final run 16/16 identical.
  4-GOP check (stable GOPs): ramp a=2 HURTS (k5 3.49 -> 2.51, k29 -1.19 -> -2.84), cut boost b=3 helps a little
  (k5 4.06). Likelier cause of the k=29 drop: I frame gets fewer bits with more lookahead (I QP 29.0 -> 30.4) and
  settings were tuned only at k=0/5. v2 tuning per k on val submitted: 13718830 (x264), 13718831 (x265), tag v2tune,
  grid dI {3,5,7} x a {0,1} x b {0,3}, every 3rd val GOP.
  v2 TUNING RESULT (13718830/31, all OK): small, inconsistent gains at k<=10 (best per k vs v1: x264 +0.0..0.4,
  x265 +0.0..0.4), within noise; k=29 not fixed (x264 -10.3 -> -8.7, x265 -5.7 -> -4.3) and 11-15% of runs over
  budget at k=29 vs 2-5% at k<=5. Tail problem: median k29-k5 drop only -0.76, worst 10% of episodes = 76% of the
  drop. Worst: LyricVideo_720P-2d24 (near-static) at level 42: at k29 the controller sees P frames are nearly free,
  plans almost the whole budget on the I frame (I QP 35), I-frame cost is under-predicted (train-median
  calibration, no feedback) -> I frame alone 157% of budget, score -115; at k5 the reserve for unseen frames
  acts as a safety margin (I QP 40). ROOT CAUSE: I-frame rate-model error amplified by full lookahead. Test of
  an I-frame budget cap (i_cap 1.0/0.7/0.5) at all k submitted: 13720914 (x264), 13720915 (x265), tag icap.
  I-CAP RESULT (12:44, 8/8 OK, val every 3rd GOP): cap 0.5 is best at every k and fixes the tail. x264 score
  k0/2/5/10/29 = -4.15/-2.40/-2.01/-2.06/-2.64 (no cap: .../-2.26/-3.12/-6.42); x265 -4.35/-1.74/-0.75/-0.76/-1.17
  (no cap: .../-0.86/-1.40/-3.70); k=29 over-rate 9.1% -> 2.4% (x264), 7.7% -> 0.5% (x265). k<=2 unchanged (cap never
  binds). 0.5 is the edge of the grid -> check 0.3/0.4 on val before the final test run.
  CAP 0.3/0.4 (13731127/31): mean val score over k: x264 -2.43 (0.3) / -2.46 (0.4) / -2.65 (0.5) / -3.67 (none);
  x265 -1.57 / -1.63 / -1.75 / -2.41 -> plateau, chose 0.3. (Earlier icap files backed up as icap*A*_*.parquet;
  controller_real.py now never overwrites results files.)
  FINAL v2 (cap 0.3) 13731564-67 + rerun 13731810 (shard 3 failed on a01-08: x265 version check; a01-08 added to
  bad_nodes; version-check failures now trigger auto-retry in p2_step/rd_native sbatch). Report:
  results_v1/controller_final2.md (scripts/controller_report.py final2). TEST, v1 -> v2, score (% over):
  x264 k0 -3.94 (4.2) = ; k2 -2.21 (3.6) -> -2.39 (2.8); k5 -0.94 (2.6) -> -1.41 (1.5); k10 -1.02 (2.2) -> -1.74 (1.2);
  k29 -2.48 (2.1) -> -3.06 (1.3). x265 k0 = ; k2 -1.96 -> -1.87; k5 -0.20 -> -0.39; k10 -0.81 -> -0.92; k29 -2.19 ->
  -1.80; over-rate down by 1/3-1/2 at k>=2. VAL improved strongly (as tuned). => The cap mostly fixed one near-static
  VAL clip (LyricVideo_720P-2d24, 7 GOPs); on test it trades efficiency (x264 -0.2..-0.7) for fewer overshoots.
  Report v1 as the efficiency number and v2 as the overshoot-safe variant. Lookahead (test, v2, paired vs k0):
  x264 k5 +2.53 +- 0.72, x265 k5 +4.06 +- 1.50. k=29 on TEST still below k5, driven by cut/gradual GOPs (x264 -3.63
  vs -0.15) in both versions: second, unexplained issue -> next: analyse stored QP sequences around cuts (no compute).
  Cut analysis (test, x264, v1): k29-k5 on cut GOPs = -3.0, all efficiency; mid-GOP cuts worst (frames 8-15: -6.2,
  16-22: -5.4). k29 reserves bits for the expensive second scene (I QP 30.4 vs 29.5 at k5) and spends MORE on the
  frames just before the cut (QP -0.6 vs mean), which nothing references. Idea parked: v3 reference-aware offsets.
  DECISION (Aayush 17:30): report v1 as the controller result; v2 = "tried, didn't work well"; controller work paused
  (it went beyond the plan's simple causal fixed-pattern baseline).
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
- [~] 43. FINAL WEEK (Aayush 11-17: docs/final-week-experiments-2026-11-17.md, "go ahead"; rules exp_next/fw/PLAN.md;
  freeze: no launches after Thu 11-19 12:00). Val only, exploratory.
  - [x] V1-V5 answered (PLAN.md): R3 replays final4's GOP n-1 history (item 2 needed); ckpts 60k/181k(/360k); warm-up
    inside the 180k; Ahhana's k0/k29 details unknown (ask); hill_climb(start=) exists, 600 = whole-GOP encodes.
  - [x] Item 5 metric sensitivity (exp_next/fw/metric_sens.py -> results_v1/next/fw/metric_sens_val.md): R3 - final4
    x264 -0.026 n.s. at lambda 0 (sign flip ~0.05), +0.077 * at 0.17, +0.384 * at 0.68; x265 +0.108 * at 0 ...
    +0.511 * at 0.68. TEST (post-hoc re-analysis of the sealed rows, Aayush OK 11-17; metric_sens_test.md; the 0.17 row
    reproduces the capped test pass +0.067 / +0.163 / shift +0.074): R3 - final4 x264 +0.010 n.s. at 0, +0.038 * at
    0.085, +0.240 * at 0.68 (no sign change in [0, 1]); x265 +0.088 * at 0 ... +0.388 * at 0.68.
  - Item 2 x264 DONE (14315512, 3 min): own - stored history -0.013 [-0.023, -0.002] * val (<= 0.02 -> one sentence);
    89 % of episodes used own GOP n-1; L42 -0.025, cut/gradual -0.018.
  - Item 2 code exp_next/fw/seq_history.py: formula check 496/496 both enc, stored-mode parity 20/20 (x264, 1 clip).
  - Exp 5 scripts: EXP5_KS env (k2 own plans/labels files), shift_smooth add-only, bc_eval --tag; originals in
    exp_next/fw/orig_*.py, shifts_smooth.json backup exp_next/fw/shifts_smooth_before_k2.json.
  - SUBMITTED 11-17 (Aayush OK, exp_next/fw/submit.sh go):
    x264: seqhist 14315512, BC-alone k0 14315513, no-warm-up RL 14315514, curve RL 14315515, build k2 14315516,
          build v2 k2 14315527, BC k2 14315528, BC-alone k2/k5 14315529, R3 k2 RL 14315530
    x265: seqhist 14315517, BC-alone k0 14315518, no-warm-up RL 14315519, curve RL 14315520, build k2 14315521,
          build v2 k2 14315531, BC k2 14315532, BC-alone k2/k5 14315533, R3 k2 RL 14315534
    shift k2 (both enc) 14315522.
  - x264 ALL DONE (RL arrays ~23 min each). Report exp_next/fw/report_fw.py -> results_v1/next/fw/report_fw_val.md
    (+ fig_kcurve.png, fig_curve.png). x264 val: item 1 R3 - final4 k2 +0.035 n.s., k5 +0.077 *; BC alone - final4
    k0 -0.531 *, k2 -0.241 *, k5 -0.155 *; R3 - BC alone k2 +0.276 *, k5 +0.231 *. Item 3: determinism exact (re-run
    = F seed 3 at 60k and 180k, 548/548); end of warm-up = BC alone exactly (560/560 QPs); s3 curve -0.231 (BC) ->
    +0.041 (40k) -> -0.002 (60k) -> +0.094 (90k) -> +0.114 (120k) -> +0.062 (180k); A and spend error both improve.
    Item 4 x264: R3 - no warm-up +0.007 [-0.025, +0.039] (s3 -0.044, s4 +0.099, s5 -0.032).
  - Item 2 x265 DONE (10 min): own - stored -0.041 [-0.079, -0.010] * (L42 -0.130, stable -0.050 *, cut +0.006);
    pooled -0.027 [-0.049, -0.009] * -> EXCEEDS the 0.02 rule -> ESCALATED to Aayush 11-17. R3 (own history) - final4
    val: x264 +0.064 [+0.006, +0.133] *, x265 +0.168 [+0.065, +0.291] * (was +0.077 / +0.209 with final4's history).
  - Aayush 11-17: option 1 = deployment-faithful re-measurement on TEST (post-hoc, frozen models, same episodes, own
    history; primary unchanged). seq_history.py --split test (formula check test 900/900 both enc; no-own-history
    episodes must equal the stored rows: val 192/192 both enc). SUBMITTED (Aayush OK): x264 14316551, x265 14316552.
  - [x] Item 2 TEST DONE (14316551/2, 34 min; results_v1/next/fw/seqhist_test.md): own - stored x264 +0.004
    [-0.004, +0.012], x265 -0.012 [-0.021, -0.004] *, pooled -0.004 [-0.010, +0.002]. R3 (own history) - final4 TEST:
    x264 +0.071 [+0.024, +0.114] *, x265 +0.151 [+0.078, +0.233] * (pre-registered +0.067 / +0.163 stand).
  - [x] x265 DONE (all RL arrays COMPLETED). Item 1 x265 val: R3 - final4 k2 +0.152 *, k5 +0.209 *; BC alone - final4
    k0 -0.558 *, k2 -0.155 *, k5 -0.003 n.s.; R3 - BC alone k2 +0.307 *, k5 +0.212 *. Item 3 x265: determinism exact
    (550/550 at 60k and 180k); s3 curve +0.023 (20608) -> +0.132 (40k) -> +0.122 (60k) -> +0.115 (90k) -> +0.065
    (120k) -> +0.183 (180k). Item 4 x265: +0.016 [-0.001, +0.034] (cut/gradual +0.080 *); POOLED +0.012 [-0.007,
    +0.029] -> "no detectable effect" (rule).
  - [x] EXPERIMENTS row added (11-17).
  - Next: ask Ahhana (k2? seeds? own mean[t]/BC at k29?); item 7 optional.
- [ ] 44. TEST2: fresh held-out evaluation set for the frozen models (Aayush 11-17: Tier 1 + Tier 2, evaluation only).
  Plan exp_next/test2/PLAN.md (UGC only, 12 categories x 8 clips, data/t2/320x180, split label test2, parity gate on
  3 v1 test clips, PREREG before eval jobs, drop if parity not exact by Thu 11-19 10:00).
  - [x] plan written 11-17
  - [x] selection script exp_next/test2/select_t2.py -> data/t2/clip_candidates.csv, selection.md (93 clips, 930 GOPs,
    52 GB incl. parity); [ ] Aayush approves list
  - [ ] download (Aayush, hpc-transfer1), decode, cut labels, curves, budgets, final4, rc work dirs
  - [ ] audit items (PLAN.md section 4) + parity gate
  - [ ] PREREG.md frozen; eval jobs (Aayush OK); report
