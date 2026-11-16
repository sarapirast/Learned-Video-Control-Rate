# Exp 5b: centred BC on search plans, then R3 (PPO from the BC actor) -- pre-registration

Written 2026-11-13 (Aayush's design points), before any BC code or training. Follows exp_next/exp5/PREREG.md
(Exp 5 dataset), PREREG_SHIFT.md (Exp 5a; REVISION 2 centred-BC go/no-go: GO, R^2 0.417 / 0.420 at k5 without the
plan's own history). Val untouched by BC until the confirmation step.

## What BC learns and what is deployed

- Label: the Exp 5 clipped label (search plan QP - final4's capped QP, -6..+6), beta 0.1 weights.
- Centring is for analysis, not for deployment. The plan's correction is mean[t] + centred part. Deployed policy:
  **final4 + mean[t] + BC(obs)**, where mean[t] = the pooled (over levels) weighted per-position mean label for
  that encoder and k (causal: depends only on the frame index; the per-level mean is never used, it is hindsight).
  BC is trained on the centred label (label - mean[t]); the R^2 of the centred label is what is reported.
- Rounding: the real-valued mean[t] + BC output is added to final4's real-valued QP before its rounding (as in
  Exp 5a, env.res_float + integer action), bit re-cap as in Exp 5a's "bit" arm.

## Observation

- Removed for BC: o[2] (budget level != 24; clip-level hindsight) and o[5..8] (the plan's own history: in BC they
  let the model copy the plan's previous QP).
- Kept: budget state, final4-state features (f4), first-pass / scene / lookahead slots.

## Rungs

1. **BC only (imitation rung).** Evaluate final4 + mean[t] + BC on the train-select fold (real encodes, k 0/5,
   both encoders) before any RL. This is the "imitation only" row of the ladder and the reference for how much
   R3's RL adds.
2. **R3 = PPO initialised from the BC actor** (R1's setup unless a fold eval shows R2 clearly ahead; lambda 0.17).
   - Observation: o[2] stays zeroed. If R3 keeps o[5..8] (legitimate in RL: the policy's own history), their
     input weights are zero-initialised when loading BC, so the starting policy equals BC exactly.
   - Initial action spread: PPO's initial log-std set to the size of BC's residual error (weighted RMS of the
     centred label minus BC's prediction on held-out fitting clips), not the default.
   - Value-head warm-up with the actor frozen for the warm-up steps.
3. Expectation stated in advance: gains mostly at k5 (Exp 5a: the k0 shift gain needed budget-level hindsight);
   a gain at k0 would be a surprise.

Details of the BC network, steps and the R3 gate are added here before training (as a dated revision).

## REVISION 1 (Aayush 11-13, before any BC code; supersedes the R3 lines above and PREREG_SHIFT.md "R1 vs R2 for R3")

- **Setup: R2's, not R1's.** Offsets -6..+6 (R1's -3..+3 would clip what BC learned: 10-15% of centred labels fall
  outside +-3) and the f4 final4-state features (at k5 the budget-tightness signal comes through final4's planning
  QP, f4 slot 1; Exp 5a showed it is the feature that matters). R1's setup is used only if R2 clearly loses to R1
  on the fold (R2 - R1 95% clip CI entirely below 0), from a fold evaluation of the stored 180k R1 / R2 models run
  before R3 training (val already has R2 - R1 +0.040 [+0.023, +0.061]).
- **BC's observation = R3's observation.** Same feature vector (base slots + f4). o[2] and o[5..8] are removed in
  BC (masked to 0, env drop groups "level" + "history"); in R3 o[2] stays masked and o[5..8] are present but their
  first-layer input weights are zero at initialisation.
- **Action parameterisation.** BC is a regressor on the centred label. R3 is PPO with a Gaussian policy whose mean
  is that network (initialised from BC) and whose initial log-std is the size of BC's residual error. The applied
  offset is mean[t] + network output (sampled in training, the mean in evaluation): frame t's QP = round(final4's
  real-valued QP + mean[t] + output), output clipped so the total stays within -6..+6, then the cap rule below.
  This replaces R1 / R2's discrete offset index (new env action mode; noted as a change from R2's setup).
- **Reproduction check (like the a = 0 parity).** The BC-initialised R3 policy at step 0, evaluated
  deterministically, must reproduce the BC-only rung's rows exactly (same QPs, bits, score) on the fold episodes
  before any PPO update is trusted.
- **Cap rule after mean[t] + BC: bit cap only** (fcap floor; QP 51 when the remaining budget is spent;
  RC_RES_RECAP=bit), as selected in Exp 5a. No shape re-cap (step limit / P >= I + 1): the full re-cap would cancel
  the frame-1 correction, as in the shift smoke run.

## REVISION 2 (Aayush 11-13, before any BC training; supersedes REVISION 1's "Action parameterisation")

R2 picks from a fixed set of offsets (gym Discrete(13) over -6..+6, SB3 PPO MlpPolicy, pi 256-256 ReLU + linear
action head). To keep R3 different from R2 only in its starting weights:

- **BC is a classifier over R2's 13 offsets** (weighted cross-entropy, beta 0.1 weights), with exactly the
  architecture of R2's actor (pi 256-256 ReLU + 13-way linear head), so its weights load into the PPO policy
  unchanged. R3 keeps R2's action head; the "initial spread" is BC's softmax as trained. No continuous action mode.
- **mean[t]** = the pooled smooth Exp 5a vector shifts_smooth.json "<enc>|<k>|pooled" (causal: frame index only;
  never the per-level vector), applied as the env's real-valued res_float.
- **Rounding order (env.step):** q = round(final4's real-valued QP + mean[t]) + offset (Python round), clipped to
  11..51, then the bit cap (RC_RES_RECAP=bit: fcap floor; QP 51 when the remaining budget is spent). No shape re-cap.
- **Class target:** label2 = clip(plan QP - round(q_real + mean[t]), -6, 6), q_real = final4's real-valued QP under
  the plan's history at budget S (build.py --v2 -> data_v2_<enc>_k<k>.npz).
- **Checks (done before submission, 11-13):**
  - offset 0 with mean 0 reproduces final4's stored rows 12/12 per encoder, all cap rules (shift_eval.py --check);
  - v2 round trip (real encodes, smoke, x264): executing mean[t] + label2 with the bit cap reproduces the plan on
    7 of 8 plans exactly; the 8th diverges from frame 0 where its target was clipped at +-6 (as Exp 5 check (a));
  - fold isolation: build.py keeps train clips only, minus the 8 train-select fold clips and flat GOPs (load());
  - leakage, measured on the saved arrays: obs columns 2, 5, 6, 7, 8 have 0 nonzero entries (asserted in build.py
    --v2 and written to labels_v2_<enc>.md).
- **Step-0 reproduction for R3:** the PPO policy with BC's weights loaded, evaluated deterministically (argmax),
  must reproduce the BC-only rung's fold rows exactly before any PPO update is trusted.

## REVISION 3 (11-13, training and BC-only rung details, before any BC training)

- **Training (bc_train.py).** One model per (encoder, k 0/5, seed 0/1/2). Adam lr 3e-4, batch 1024, 40,000 steps,
  rows sampled in proportion to the beta 0.1 weights (= weighted cross-entropy). Hold-out: a fixed 10% of the
  fitting clips (seed 0); checkpoint = lowest hold-out weighted CE, evaluated every 2,000 steps. Reported: hold-out
  CE vs the per-frame class prior, accuracy, R^2 of the expected offset vs the per-frame mean (centred R^2), share
  of argmax = 0. First-layer weights of columns 2, 5..8 set to 0 at save (inputs always 0 in BC).
- **BC-only rung (bc_eval.py, bc_report.py).** Fold (8 train-select clips), k 0/5, seeds 0/1/2, deterministic argmax,
  final4 + mean[t] + BC, bit cap. Reported per encoder and k: BC - final4, BC - mean-only (Exp 5a pooled:bit fold
  rows: same mean[t] and cap, offset 0), mean-only - final4; per seed; cut/gradual vs stable; A / E-P / spend
  decomposition. Seeds averaged per episode, clip bootstrap, hole excluded. Parity before the run: offset 0 + mean 0
  + bit cap + masked obs reproduces final4's stored rows 12/12 per encoder (bc_eval.py --check, done 11-13).
- No gate on the BC-only rung: it is a reported rung ("imitation only") and R3's starting point. The R3 gate and the
  R1 / R2 fold check are added before R3.

## REVISION 4 (Aayush 11-14, after the BC-only fold result, before any R3 run): R3 at k5 only, with a control

What was known: bc_fold.md. BC-only - final4: x264 -0.327 (k0 -0.549, k5 -0.105), x265 -0.193 (k0 -0.426, k5 +0.040
n.s.); a landing failure from closed-loop drift (offsets unbiased on logged states, +0.8..+1.4 QP in closed loop at
k0). Restricting R3 to k5 is a selection made on the fold (post-hoc); val is still unused. k0 BC is reported as the
imitation-only failure.

- **R3 (3 seeds x 2 encoders, k5):** R2's recipe (res arm, offsets -6..+6, f4 features, lambda 0.17, 180k PPO steps,
  60k checkpoint, val eval) + o[2] masked (drop "level") + mean[t] (--res-mean pooled) + bit cap (RC_RES_RECAP=bit)
  + actor from BC (--init-bc, same seed) + critic warm-up: the first 20,000 of the 180,000 timesteps update the
  critic only (actor frozen). Run list runs_v1/next_exp4_r3.txt lines 1-3.
- **R2c control (same, lines 4-6):** identical to R3 except no BC initialisation (rl.py's res init: P(offset 0) 0.7).
  R3 - R2c isolates the BC start; R2c - R2 shows what mean[t] + bit cap + masked o[2] do under RL.
- **Checks done:** step 0 reproduces the BC-only fold rows 12/12 per encoder (exp_next/exp4/r3_step0.py; o[5..8]
  live but zero-weighted); actor bit-identical during the warm-up, critic updated, actor moves after it; rl.py eval
  path runs with res_mean + drop level + bit cap.
- **Precondition:** fold R2 vs R1 at k5 (exp_next/exp4/fold_r1r2.py). If R2 - R1's CI is entirely below 0, R3 is not
  interpreted (BC has R2's observation and action shape, so R1's setup cannot be initialised from it).
- **Gate (brief, Exp 4 R3; val, k5, hole excluded, seeds averaged, clip bootstrap):** R3 - final4 pooled over both
  encoders: point >= +0.03 dB and CI lower bound > 0. Also reported: R3 - R2c (the BC-start effect), R3 - R2 (stored
  R2 k5 val rows), R2c - R2, per encoder and seed; the 60k checkpoint; A / E-P / spend; on x265 also vs final4 +
  per-qbin shift (Exp 5a REVISION 4 val rows, k5).
