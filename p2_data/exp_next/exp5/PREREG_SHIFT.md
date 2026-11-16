# Experiment 5a: final4 + a fixed per-frame offset schedule distilled from the search -- pre-registration

Written 2026-11-13 after Exp 5 check (b) failed and before any shift was fitted or evaluated. Not to be edited after
results arrive. Deviation from exp_next/exp5/PREREG.md recorded there. In the report this is called what it is: a
schedule distilled from the search by supervised (weighted) averaging, not RL.

## Fit (no encodes)

- Data: the Exp 5 dataset (results_v1/next/exp5/data_<enc>_k<k>.npz: train minus the train-select fold, minus flat
  GOPs; labels = logged QP - final4's capped proposal at the replayed state, clipped to -6..+6).
- shift_t = sum(w * label_t) / sum(w) per frame index t, w = exp(Delta / beta) clipped at its 99th percentile (the BC
  weights), beta in {0.05, 0.1, 0.2}; one vector per (encoder, k in {0, 5}).
- Variants: pooled (one 30-vector) or per budget level (4 x 30; the level is known causally). Rounded to integers
  (QP is an integer): floor(x + 0.5). Identical integer vectors are evaluated once.
- Stability across levels reported: per-level vectors and their max |difference| from the pooled vector.

## Execution (real encodes, deterministic)

- R2's residual env (`resh`, RC_RES_RANGE = 6, no learner): frame t gets final4's proposal + shift_t.
- Cap rules (both evaluated): (i) no re-cap (`resh` behaviour; how the labels were defined and replayed in check
  (a)); (ii) re-cap (new option RC_RES_RECAP=1): final4's own limits re-applied after the offset, in decide()'s order:
  fcap floor, step limit |QP_t - ref| <= dmax (3), P QP >= I QP + pmin (1), QP 51 when the remaining budget <= 0,
  range 11..51; the I frame gets the range clip only (its i_cap is 1.0 x B, not binding). Default off; regression
  with the option off must stay exact.

## Selection on the train-select fold (exp_next/folds.json, 8 clips)

Per encoder: the variant (beta x pooled/per-level x cap rule) with the highest mean score pooled over k 0/5 and the
4 levels, level-24-hole episodes excluded. Ties within 0.005 dB -> pooled over per-level, then re-cap over no
re-cap, then the larger beta. final4's stored rows on the same episodes are reported alongside. Caveat: final4's
rate model was fitted on all train clips including the fold.

## Confirmation on val (once, selected variant only)

- Primary: (final4 + shift) - final4, paired on (GOP, level, k), pooled over both encoders and k 0/5, 95% clip
  bootstrap, hole excluded. "Helps" = CI above 0 and no encoder CI entirely below 0. If it helps, final4 + shift
  becomes the base for every RL rung not yet started (residual on top of it; stored paired-reward scores recomputed
  with one deterministic pass on train), and later gaps are reported against both final4 and final4 + shift.
- Decomposition (Exp 1): score, A (quality for the bits), E - P (landing), mean |spend error|, signed spend error,
  % over. Leak / level-effect check: if the signed spend error rises by > 1 percentage point or % over by > 10
  points vs final4, part of the shift is a level effect final4's feedback does not absorb -> reported as such.

## Centred-BC go/no-go (no encodes; decided before any BC training)

- Target: the Exp 5 label (clipped). Fitting clips only, 5-fold out-of-fold grouped by clip, weights w at
  beta = 0.1, a random subsample of plans (same plans for every model).
- Models: (i) position only = weighted mean label per frame index (and per (level, frame index), reported);
  (ii) HistGradientBoostingRegressor (default settings, random_state 0) on BC's full observation (351 features incl.
  the f4 final4-state features).
- Statistic: R^2 of (ii) on the position-centred label, i.e. 1 - SSE(ii) / SSE(i), out of fold.
- **Train centred BC only if this is >= 0.10 on both encoders at k5** (the threshold of Exp 1 stop rule 2). Below
  it, BC and R3 drop down the priority list (expected gain a few hundredths of a dB at most).
- Also reported: Exp 1's existing numbers (val, k5: position-only 0.159 / 0.182 vs full 0.331 / 0.375); the share
  of centred labels outside -3..+3 (R1's range); the share of logged plan frames a re-capped residual could not
  reproduce (step limit or pmin violated relative to the plan's own history).

## R1 vs R2 for R3

(Superseded 11-13 by exp_next/exp5/PREREG_BC.md REVISION 1: R2's setup unless R2 clearly loses to R1 on the fold.)
Decided only if centred BC goes ahead. R2 failed its val gate against R1, so by the rule "if R2 did not clearly beat
R1, use R1", R3 uses R1's setup unless a fold evaluation at the fixed 180k checkpoint shows R2 clearly ahead.

## REVISION 2 (Aayush 11-13, before any shift was evaluated with encodes; supersedes Fit, Execution, Selection and the
## Centred-BC go/no-go above where they differ)

What was already computed when this was written: shift_fit.md (rounded per-frame vectors; go/no-go on the full
observation, 0.52-0.60 at k5 -- not used for the decision, see below). No fold or val encode had been run.

- **Shift form.** Smooth 4 parameters per (encoder, k) [per level for the per-level arm]: I-frame offset, frame-1
  offset, linear ramp over frames 2-29 (value at frame 2 and at frame 29); weighted least squares on the clipped
  labels with the beta 0.1 BC weights (exp_next/exp5/shift_smooth.py -> shifts_smooth.json). Real-valued, added to
  final4's real-valued QP before its final rounding (controller decide() diag q_real; equals the integer when a cap or
  clip set the QP). Reason: the per-frame means are jagged because of the search's start-ramp rounding (corr 0.60-0.65
  with the ramp's rounding error; base QPs are integers), an artefact of the search, not of good allocation.
- **Cap arms, split by purpose.** none (resh); bit = budget limits only (fcap floor; QP 51 when the remaining budget
  is spent); full = also final4's shape limits (step limit 3, P >= I + 1). Env option RC_RES_RECAP = 0 / bit / full.
- **Arms (5, all at beta 0.1):** {pooled, per-level} x {none, bit} = 4 selectable arms + pooled x full as a
  reference arm (reported, not selectable). Fold selection: per encoder, highest mean paired score (shift - final4)
  pooled over k 0/5 and levels, hole excluded; ties within 0.005 dB -> pooled, then bit. A, E - P, mean |spend
  error|, p90 |spend error|, signed error and % over reported for every arm (watch % over and p90 in the "none" arms).
  The selected arm alone is run once on val (criterion and level-effect check unchanged from above).
- **Centred-BC go/no-go.** Decided on the full 4000-plan subsample, position-centred Exp 5 labels, with the plan's own
  history removed from the observation (slots o[5] last-frame bits / budget, o[6] previous offset, o[7] last-frame
  bits / first pass, o[8] bits spent / first pass); budget state and final4-state features kept
  (exp_next/exp5/gng_nohist.py). GO only if >= 0.10 at k5 on both encoders; BC is then trained without those slots.
  Exp 1's 0.20 / 0.24 (different labels) is reported only as an approximation.

## REVISION 3 (Aayush 11-13, after the fold run, before any val encode and before the per-qbin vectors were fitted)

What was known when this was written: the fold report (shift_fold.md). Best selectable arm perlevel:none, selected
by the tie-break perlevel:bit (x264 +0.032, x265 +0.103 vs final4); pooled arms about 0 (x264) / +0.04 (x265).

- **Why.** The budget level is not something a deployed encoder knows. v1 budgets are B = mean over the clip's GOPs
  of their constant-QP-L slice bits (scripts/budgets_v1.py), so the level tells the policy which constant QP fits B
  on the whole clip, including future GOPs: clip-level hindsight (not the GOP's own spend, not a fixed bits-per-pixel
  tier). final4 only sees B (its own planning level is causal). The per-level arms are therefore not deployable.
- **New arm per-qbin:bit.** Shift vector chosen by final4's own GOP-start planning QP (controller decide() diag
  "level" at frame 0: the P-frame QP its rate model needs to fit B with the frames visible at k; causal), binned with
  cut points halfway between the level QPs: < 27 -> bin 24, 27-33 -> 30, 33-39 -> 36, >= 39 -> 42. Fitted exactly as
  the per-level vectors (shift_smooth.py's 4-parameter weighted LS, beta 0.1, same fitting clips), with plans grouped
  by the bin of final4's frame-0 level instead of the budget level (exp_next/exp5/shift_qbin.py ->
  shifts_qbin.json; frame-0 level read from the Exp 5 observation, f4 slot 1). Same bit re-cap. Run on the same
  fold episodes.
- **Rule, per encoder** (fold, hole excluded, pooled over k 0/5 and levels, mean of shift - final4):
  per-qbin:bit >= perlevel:bit - 0.01 dB -> per-qbin:bit goes to val for that encoder. Otherwise no shift arm goes
  to val for that encoder; reported as "the shift's value depends on hindsight about the budget level", with the
  share of perlevel:bit's fold gain per-qbin:bit keeps. perlevel arms are never taken to val as the method.
- **Val reporting (replaces the primary above).** Primary: paired (shift - final4) per encoder, pooled over k 0/5,
  95% clip bootstrap, hole excluded; "helps" on an encoder = its CI above 0. Secondary: per k; cut/gradual vs stable
  GOPs (val: 22 vs 118 GOPs); score, A, E - P, mean / p90 |spend error|, signed error, % over vs final4 (so a gain
  from quality-for-the-bits is told apart from landing). Level-effect check unchanged. Expectation stated in advance
  (Aayush): smaller than fold (best of five arms on 8 clips), about +0.05..+0.08 on x265 and near 0 on x264.
- Note (before the fold run, after the fit): the bins in the fit come from the Exp 5 observation, where final4's
  frame-0 level was computed with the plan's own spend S as the budget (build.py's relabel, |S / B - 1| <= 0.15); in
  evaluation the arm uses final4's level for the real budget B, as a deployed encoder would. Parity: re-running
  final4 with budget S reproduces the stored level 12/12 (float16 storage, <= 0.003 QP); with B the level differs
  by 0.03-0.3 QP on the sampled plans, so only plans near a bin edge can change bin.

## REVISION 4 (Aayush 11-13, POST-HOC, written after the REVISION 3 fold result and before any val encode)

What was known: REVISION 3 fold result (shift_fold.md). per-qbin:bit failed the 0.01 dB rule on both encoders; the
failure is at k0 (x264 -0.034, x265 +0.032); at k5 per-qbin:bit +0.050 (x264) / +0.132 (x265) vs perlevel:bit
+0.062 / +0.116. Choosing k5 is a selection made on the fold after seeing it (post-hoc), labelled as such. Val has not
been used for anything in Exp 5a.

- **Test.** One arm, per-qbin:bit (shifts_qbin.json, k5 vectors; bins from final4's frame-0 planning QP), k5 only,
  both encoders, run once on val (shift_eval.py --split val --variants perqbin:bit --ks 5 --tag qbin_k5).
- **Primary.** Paired (shift - final4) per encoder at k5, 95% clip bootstrap, hole excluded; "holds" on an encoder =
  its CI above 0. Pooled over encoders reported.
- **Also reported.** p90 |spend error| and % over vs final4 (fold x265: p90 4.7% -> 7.0%); A and E - P; mean and
  signed spend error; cut/gradual vs stable; level-effect check as before.
- **Use.** If it holds, final4 + per-qbin shift at k5 is a stronger non-RL baseline at k5, and RL gains at k5 are
  reported against both final4 and it. If not, the row is closed. Either way k0 has no shift.
