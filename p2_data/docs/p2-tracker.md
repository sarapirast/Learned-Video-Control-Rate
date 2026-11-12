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
