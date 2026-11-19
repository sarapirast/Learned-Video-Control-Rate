# test2 pre-registration: frozen models on a fresh held-out UGC set (evaluation only)

Status: FROZEN 2026-11-17 (approved by Aayush), written after the cut labels were fixed and before any test2 score was
computed. Changes are made only as dated amendments at the end, never edits.
Plan and execution log: exp_next/test2/PLAN.md. Nothing is trained, refitted or tuned on test2.

## 1. Data (fixed)

- test2 = 93 new YouTube-UGC clips (exp_next/test2/select_t2.py; data/t2/clip_candidates.csv, split "test2"):
  12 categories, one clip per uploader, no uploader shared with v1, 320x180, GOPs of 30 frames (930 GOPs).
- Scored: 860 GOPs in 88 clips after the flat-GOP rule (70 test2 GOPs dropped, as in v1). 4 budget levels per GOP,
  as built by budgets_t2.py from the v1-train fit.
- Labels (fixed 11-17, before any result): config/cut_review_t2.csv (v1 protocol: blind two-reviewer round 1 +
  settlement, Claude-only round 2), applied by cut_labels.py to data/t2/320x180/gops.csv. Scored GOPs: 788 stable,
  69 cut, 3 gradual (72 cut/gradual GOPs in 36 clips).
- The 3 parity clips (ed_s05, NewsClip_360P-1b1c, park_joy; v1 test clips) are never part of a test2 result.

## 2. Gate before any test2 score is read

Every exp_next/test2/parity.py stage is OK, and each eval-level parity pass reproduces its stored v1 test rows exactly
(R3 k5 per seed; CQL->PPO 540k per seed and k; final4 / final3 controller rows; ABR; final4 + shift). Models with no
stored v1 test rows (R3 k2, BC alone) are checked through the shared pieces (infos, env settings asserted against each
run's eval.pkl). A failed gate stops the pass until it is fixed; the fix and its cause go in PLAN.md section 10.

## 3. Metric and statistics (same code path as results_v1/final/report_test_cap.md)

- Score per episode: dPSNR_B - 0.17 x %over (100 dB PSNR cap, cap_fix logic), rescored with one metric function on
  the test2 constant-QP curves and budgets. Flat GOPs excluded; level-24-hole episodes (budget above the GOP's
  constant-QP curve maximum) excluded in the primary and reported with them included as well.
- Differences are paired on (GOP, level); learned models: seeds averaged per episode first.
- 95 % CI: percentile bootstrap over clips, 2,000 resamples (exp_next/exp5/shift_report.boot). Every test2 clip has
  its own uploader, so this is also the source bootstrap.
- Per encoder; no pooling across encoders in the primary.

## 4. Primary endpoint (replication of the v1 test result)

**R3 (180k, seeds 3-5) - final4, k5, per encoder, on test2.**
- Replicated on an encoder if the 95 % CI lies above 0. If the CI includes 0: "not replicated on test2" (no
  claim of harm unless the CI lies below 0). Reported next to v1 test (capped: x264 +0.067 [+0.023, +0.107],
  x265 +0.163 [+0.086, +0.243]) whatever the outcome.
- Two separate tests (one per encoder), no multiplicity correction; both are always reported.
- R3 uses final4's stored GOP n-1 history (the v1 pre-registered definition).

## 5. Secondary analyses (descriptive unless a rule is stated)

1. **By class:** stable vs cut/gradual, and their paired difference in (R3 - final4). 72 cut/gradual GOPs >= 60,
   so the cut slice gets a CI (a claim only if the CI excludes 0).
2. **By category** (12 UGC categories, ~7-8 clips each): CIs shown, descriptive only; no per-category claim.
3. **k-curve:** final4 at k 0/2/5/10/29; R3 at k2 and k5; BC alone at k0 (s0-2), k2 and k5 (s3-5); CQL->PPO 540k
   @prev at k0 and k5; ABR+VBV at k0 and k5; constant QP (cqp_est causal, cqp_best hindsight) from the curves.
4. **RL over BC:** R3 - BC alone per k (k2, k5). "RL adds over BC at k" only if that CI lies above 0.
5. **R3 - (final4 + per-qbin shift), k5:** x265 is the v1 val-confirmed comparison; x264 descriptive.
6. **R3 - CQL->PPO 540k @prev**, k5; **R3 - ABR** (frozen margins x264 0.90, x265 0.93), k5.
7. Decomposition as in v1 (mean / p90 / signed spend error, % over) and the overshoot profile per method.
8. **R3 with its own history** (exp_next/fw/seq_history.py, deployment-faithful), k5: reported next to the primary,
   never instead of it.
9. **Pooled v1 test + test2** (R3 - final4, k5, per encoder; clip bootstrap over the union): descriptive.
10. Ahhana's R3 k0 / k29: only if her models and env settings arrive before the freeze (Thu 11-19 12:00); then
    descriptive, with the same metric.

## 6. Not on test2

The hindsight search (the "fraction of the search's gain" stays on v1 test), R3 360k, no-warm-up runs, R1 / R2 / R2c,
Lagrangian, stream-level policies (Exp 7), Pavneet's live-stream work.

## 7. Known biases, stated in the report

- final4 and the ABR margins were tuned on v1 val; the learners were selected on v1 val. test2 is UGC only (no
  Xiph / Blender / Netflix sources), so it differs in content mix from v1 test.
- Cut labels: round-1 agreement 80 % exact / 90 % cut vs not-cut (kappa 0.62; v1 0.64); round-2 precision check
  12/16 both-detector frames were real cuts. Labels affect only the stable / cut breakdown, not the primary.

## Amendments

(none)
