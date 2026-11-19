# Final configuration (F) and the single test run -- pre-registration DRAFT

Status: DRAFT written 2026-11-14 while x265 R3 / R2c runs finish (Aayush's two-branch plan). The branch is fixed by
the pooled R3 gate in results_v1/next/exp4/r3_report.md (exp_next/exp4/report_r3.py) as soon as x265 is in; nothing
here runs before that report exists and Aayush approves the test run. Test has not been used for any decision so
far (val only, fold for selection). Brief Part D applies where this file does not override it.

## BRANCH: A (decided 11-14 by results_v1/next/exp4/r3_report.md: R3 - final4 pooled +0.128 [+0.050, +0.216], gate passed)

## Branch selection (decided mechanically by the R3 report)

| Branch | Condition (exp_next/exp5/PREREG_BC.md REVISION 4 gate) | F learner |
|---|---|---|
| A | R3 - final4 on val, k5, pooled over both encoders: point >= +0.03 dB and CI lower bound > 0 | R3's recipe at k5 |
| B | otherwise | R2's recipe with o[2] removed (drop "level"), k0 and k5 (the k it was tested at) |

- **Branch A recipe:** res arm, offsets -6..+6, f4 features, o[2] masked, mean[t] = pooled smooth Exp 5a shift
  before final4's rounding, bit cap, lambda 0.17, 180,000 PPO steps (20,000 critic-only warm-up included), actor
  from Exp 5b BC (same data and recipe; BC retrained with the fresh seeds), k5 only.
- **Branch B recipe:** R2 as run (res arm, -6..+6, f4, lambda 0.17, 180,000 steps, standard residual init) with
  drop "level".
- **36-hour fallback (agreed by Aayush in another session; recorded here 11-14):** if R3 is not finished and read on
  val in time (the 36-hour mark), stop waiting and run F with branch B's recipe (R2's). As of 11-14 ~09:30, x264 R3
  is read and x265 R3 is due within ~1.5 h, so the branch is expected to come from the gate, not the fallback.
- **Fresh seeds 3, 4, 5** (never used before), both encoders. Step count fixed at **180k** (the validated
  checkpoint). Optional secondary arm, branch A only: the same at 360k, reported alongside, never instead of 180k.

## Not in F (stated in the report)

- R3 was tested only at k5; BC at k0 failed on the fold (closed-loop drift). No R3 at k0 or other k in F.
- The k-curve {0, 2, 5, 10, 29} is reported from the baselines (final4, ABR) and from existing learner runs,
  labelled as existing runs, with the statement that R3 was only tested at k5.

## Test run (once, after Aayush's approval)

Methods, both encoders, test split, hole excluded in the primary (reported with it too):
- F's learner (branch A: k5; branch B: k0 and k5), 3 fresh seeds;
- final4 at all k {0, 2, 5, 10, 29};
- final4 + per-qbin shift, x265 k5 only (the Exp 5a REVISION 4 val-confirmed baseline);
- ABR+VBV at margin 0.95 (Exp 10), k {0, 5};
- references per brief Part D: CQL->PPO@prev 540k; the Exp 7 frozen systems (below); [Exp 2 handoff dropped:
  failed on val, closed (Aayush 11-14)];
  Exp 6 bandit only if its gate passes.

**Primary endpoint:** paired score (F - final4) at k5, per encoder, 95% clip bootstrap, seeds averaged per episode.
Secondary: F - (final4 + shift) on x265 k5; F - ABR; decomposition (A, E-P, mean / p90 / signed spend error,
% over); per level and per class (cut/gradual vs stable); total real encodes; the history source. State the
val-tuning bias in final4's favour, and that the 540k reference's test rows already exist on disk from Pavneet's
pipeline default (eval-splits val,test), produced before this pre-registration but never used for a decision.

## Code needed before submission (none written yet)

- shift_eval.py: a test split (currently fold / val only).
- ABR margin script (Exp 10) and the Exp 2 handoff: test split.
- R3 runs with fresh seeds: BC retrain for seeds 3-5 (bc_train.py --seeds 3,4,5, new output names), run list with
  --eval-splits test (val also, for a check against the val result).
- One report script for the test run (exp_next/final/report.py).

## Stage 1 details (Aayush 11-14, before any F run)

- **360k secondary, one run per seed.** rl.py's learning rate (1e-4), entropy coefficient (0.01) and clip range (0.2)
  are constants, so nothing depends on the total step count. Each fresh seed (3, 4, 5) trains once to 360,000
  steps. The **primary 180k model** is the checkpoint taken right after the update a plain 180k run ends on:
  14 envs x 64 steps = 896 per update; warm-up ends at 20,608, a 180k run at 180,992 -> `--save-at 180993`
  (also 60000, as R3). Verified 11-14 on a scaled pair (2 envs): the checkpoint inside the longer run is
  bit-identical to the shorter run's final weights. The 360k final model is the secondary arm, reported next to
  the 180k primary, never instead of it.
- **BC for the fresh seeds:** bc_train.py --ks 5 --seeds 3,4,5 (same data, recipe and hold-out as Exp 5b).
- **Stage 1 evaluates val only** (180k checkpoint, 60k checkpoint, 360k final): a check against the R3 val result.
  Test is evaluated later by one eval-only pass over the stored models, after Aayush approves the test run.
- Run list: runs_v1/final_r3_s345.txt.

## Exp 7 frozen configuration (written 2026-11-14 from the val results; exp_next/exp7/PREREG.md, select_<enc>.md)

Reproduction / extension of Pavneet's D34/D35 (team repo main, `pavneet_handoff/`, commit
eb08445394aea4e1097a5a8f2f68c5755d7aa3f4) and Sara's P4 (branch sara-p4, commit 1860557246e69ff66b9740f92e586bbec7b783d0).
D34/D35 stream results were already measured on v1 test, and ED / ToS are v1 test clips: these test numbers confirm
already-reported results, not a first look at test.

- **Stream policy per encoder (Part 1d selection on val):** x264 = Pavneet's bc_ppo_L2 (seeds 0-2, stored
  model.zip in artifacts/x264/v1/results_stream); x265 = Pavneet's ppo_L2 (seeds 0-2). Applied unchanged at every N.
- **Rule (comparator), prior c0 from train, prior per qpd = streamenv.prior_c0 on train GOPs:**

  | enc | N | L | (margin, qpd, cw) retuned | tuned on |
  |---|---|---|---|---|
  | x264 | 8 | 2 | (1.00, 5.0, 0.0625) | val same-clip 8-GOP |
  | x264 | 8 | 0 | (1.00, 5.5, 0.015625) | val same-clip 8-GOP |
  | x264 | 16 | 2 / 0 | (0.99, 5.5, 0.015625) / (1.00, 5.0, 0.0625) | train chains bbb + sintel |
  | x264 | 32 | 2 / 0 | (1.00, 5.5, 0.015625) / (1.00, 5.5, 1e-6) | train chains |
  | x265 | 8 | 2 | (0.99, 4.5, 0.0625) | val same-clip 8-GOP |
  | x265 | 8 | 0 | (1.00, 5.0, 0.25) | val same-clip 8-GOP |
  | x265 | 16 | 2 / 0 | (1.00, 4.5, 0.0625) / (0.99, 5.0, 0.0625) | train chains |
  | x265 | 32 | 2 / 0 | (1.00, 5.0, 3.0) / (1.00, 5.0, 1e-6) | train chains |

  Also reported: the rule as reported (rule_wide.pkl: x264 (0.98, 4.5, 3.0) at L 0 and 2; x265 (0.98, 4.0, 3.0) L0,
  (0.98, 4.5, 6.0) L2).
- **Test streams:** same-clip 8-GOP windows of v1 test clips (stream_rl.cases(infos, "test"), kind "clip"), primary;
  the 100 mixed test streams (stress test); 16 / 32-GOP windows of the ED / ToS segments (artifacts/<enc>/fresh,
  stride N / 2, as D35), secondary.
- **Primary endpoint (Exp 7):** selected policy - retuned L = 2 rule, same-clip 8-GOP test streams, per encoder,
  cluster bootstrap over source groups, CI above 0 on both encoders; else "lookahead helps", not "RL helps". (Val
  already points to a fail on x265: -0.079.)
- **Part 2 (x264 only, descriptive):** the four systems of exp_next/exp7/part2.py on the same-clip 8-GOP test streams
  (final4 1.0:6:1.0:2:3:4:1:1:1:0:3, k5, at B_g = the controller's own predicted spend; real encodes); per-GOP
  |spend - B_g| distribution. Val: per-GOP mean 3.6-3.8 % (the 2 % check was not met; median 0.5 %, heavy tail).
- **Code still needed:** test split in part2_prep.py / part2.py and the Exp 7 test evaluator (Part 1 rows for the
  test streams, rule as reported + retuned, 16 / 32 on ED / ToS); a test-split slot in exp_next/final/report.py.

## ABR margin, frozen 2026-11-16 (Exp 10 + extension, exp_next/exp10/PREREG.md; results_v1/next/exp10/abr_margin.md)

Val, k 0/5 pooled, hole excluded, ties within 0.005 to the larger m, grid {0.90, 0.93, 0.95, 0.97, 0.99, 1.00}:
**x264 m = 0.90** (-1.392; 0.93 -1.403; ON THE GRID EDGE, reported as such per the extension rule), **x265 m = 0.93**
(-1.209; 0.95 -1.216; interior). The test pass runs ABR+VBV at these margins, k 0 and 5
(abr_margin.py --split test --margins <m> --ks 0,5).
