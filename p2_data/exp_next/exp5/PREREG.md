# Experiment 5: quality-weighted, budget-relabelled BC on search shapes (initialiser for Exp 4 R3) -- pre-registration

Written 2026-11-13 before any Exp 5 data was built. Not to be edited after results arrive. Brief Exp 5 with Part E
amendments 1 (fold), 3 (labels) and 11 (level-24 hole).

## Data

- Train GOPs minus the train-select fold (`exp_next/folds.json`, 8 clips) and minus flat GOPs; both encoders;
  the lfq search logs (600 encodes per (GOP, level), per-frame QPs and bits).
- Plans de-duplicated by action sequence; only plans whose spend S is within 15% of their level's budget
  (|S / B_level - 1| <= 0.15) are kept, so final4's stored history inputs for that level stay approximately valid.
- Weights: per GOP, all its plans (all levels) plus its constant-QP points as (log2 bits, PSNR); upper envelope
  env(x) = max PSNR among points with bits <= x; Delta = PSNR - env(S) <= 0; w = exp(Delta / beta), clipped at the
  99th percentile, beta in {0.05, 0.1, 0.2} dB. Keep the 50 highest-Delta plans per (GOP, level) (independent of
  beta). Effective sample size reported per beta.

## Replay and labels (amendment 3)

- Residual env of R2 (`resh` arm, RC_RES_RANGE = 6, `--extra f4`), forced to (GOP, level, k), budget set to S after
  reset (the frame table keeps its level-24 normalisation, as in training). For each frame t, the env state is set
  to the logged QPs and bits of frames < t and the observation is built by `_obs()` (which runs final4's `decide`).
- Label o_t = logged QP_t - final4's proposed QP_t at that state, clipped to -6..+6 (clipped share reported). The
  previous-action observation slot uses the clipped label of frame t - 1.
- Checks before training: (a) round trip: execute final4 + the clipped labels with real encodes on 20 train plans
  per encoder; the logged QPs must be reproduced on >= 95% of frames (mismatches from clipping reported
  separately); (b) level bias: mean and sd of the label by frame index; if |mean| > 0.5 QP at any frame index it is
  reported to the human before training.

## Model and training

Same actor as R2's PPO policy: MLP 351 -> 256 -> 256 -> 13 (ReLU), weighted cross-entropy, Adam lr 3e-4, batch 1024,
20,000 steps, one model per (encoder, k in {0, 5}, beta, seed 0-2). No tuning beyond beta.

## Selection (beta) and evaluation

- beta is chosen per encoder by the mean real-encode score of the deterministic policy (argmax) inside the R2 env,
  pooled over k 0/5 and seeds, on the train-select fold (level-24-hole episodes excluded). Ties within 0.005 dB ->
  the larger beta. (Offline imitation loss is not used to select.)
- The selected models are evaluated on val inside the R2 env, without PPO: descriptive "BC only" point vs final4,
  R1 and R2 (paired, same conventions as Exp 3).
- Coverage: distribution of (final4 level at frame t - plan-implied level) in the replayed data vs in val rollouts
  of the selected BC policy; overlap reported.

## Caveat stated with any fold result

final4's rate model and every earlier learner were fitted on all train clips including the fold, so fold numbers
are optimistic and used only to choose beta.

## Decision log (added after check (a); the rules above are unchanged)

- 2026-11-13, check (a): x264 547/600 frames (91.2%), x265 549/600 (91.5%), below 95%. All mismatches come from
  2 plans per encoder whose label at frame 0 or 1 is outside -6..+6 (raw -8, +7, -8, -7); clipping changes that
  frame and the rest of the GOP diverges. The other 18/18 plans per encoder reproduce all 30 QPs with identical
  bits; 0 mismatches from any other cause. Aayush (11-13): option (a), treat as a pass with clipping reported
  separately; keep all plans with labels clipped to -6..+6 (the clipped share is in labels_<enc>.md).
- Output format: plans_<enc>.pkl instead of .parquet (the job env has no parquet engine).
- 2026-11-13, check (b) FAILED (max |mean label| 2.03 / 1.90 x264 k0 / k5, 2.18 / 1.87 x265): I frame +0.6..+0.7,
  frame 1 -1.7..-2.2, frames 2-29 -0.15..-1.9. Reported to Aayush before any training.
  **PRE-REGISTRATION DEVIATION (Aayush 11-13, recorded before any training):** (1) raw (uncentred) labels are not
  used for BC. (2) The per-frame mean label is first tested on its own as a fixed schedule on top of final4
  (Exp 5a, exp_next/exp5/PREREG_SHIFT.md). (3) BC, if trained at all, uses labels centred per frame position
  (label minus the weighted mean label at that frame index; per level if Exp 5a selects per-level vectors), and
  only if the decision rule in PREREG_SHIFT.md ("Centred-BC go/no-go") passes. Reason: check (b) failed.
