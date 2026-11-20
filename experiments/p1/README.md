# P1 experiments (x264 and x265; val, plus test2 for the k0 / k29 models)

Experiments by P1 (Ahhana) on top of the shim backend (`RC_BACKEND=shim`, see `P1_README.md` at the repo root): the
team's rclib environment with P1's x264 shim instead of the x264 command line, identical results and ~13× faster.
All training and selection used train data and val only. Test (the team's single pre-registered pass) was never
used here; test2 was used once per model in 05 (x264: re-run of Aayush's pre-registered evaluation; x265: post-hoc,
agreed with Aayush). Each folder has its own README (question, runs, how to rerun, checks, results).

**Paths:** the scripts use absolute paths: my scratch (`/scratch1/ahhanagu/ee599/`, all outputs, outside git), this
repo clone, and Aayush's read-only inputs and Python envs (`/scratch1/aayushso/`: data, infos, search plans, stored
runs, `envs/rc` for encodes/training, `envs/ee599` for scoring). They are a record of what ran; to rerun elsewhere,
change the paths at the top of each script (for 03/04: `env.sh`). Data, logs, models and result files are not in git.

## Experiments
**[01 · Shim vs CLI check](01_shim_vs_cli_check/).** final4 and R3 on 10 val GOPs × 4 budget levels with both
backends: per-frame QPs, bits, PSNR and score identical on 40/40 episodes; 12–13× faster (R3 training ~33 → ~4 min).

**[02 · Baseline reproduction](02_baseline_reproduction/).** final4 at k 0/2/5/10/29 and R3 k5 (seeds 3–5) re-run
on all of val; R3 reproduced exactly, final4's bits exactly. Found that final4's stored PSNR was not capped at 100 dB
per plane while the learners' was; Aayush adopted one cap (val x264 R3 − final4 +0.077, cut/gradual +0.069).

**[03 · R3 across lookahead](03_r3_lookahead/).** R3 and its BC start at k 0, 2, 5, 10, 29 (3 seeds at k0/k5/k29).
R3 beats final4 by +0.07 to +0.10 dB at every k; the BC start goes from far below final4 (k0) to above it (k ≥ 10),
and R2c (04) shows the imitation start + PPO together make the gain at every k (PPO alone never beats final4).
k5 retrains are bit-identical to Aayush's models. Final scores, one PSNR cap everywhere.

**[04 · R2c control](04_r2c_control/).** R3 without the BC start at k0 and k29 (seeds 3–5), for the BC-start effect.
Scored (final, with 03): R2c − final4 −0.06 / −0.02 / −0.04 at k0 / k5 / k29, R3 − R2c +0.13 / +0.10 / +0.14 \*.
The k5 check against Aayush's stored R2c failed; tested cause: his *training* code
changed during 11-14 (his morning runs don't retrain identically, his afternoon runs do; his stored models evaluate
identically with today's code, so the environment and scoring did not change). R3 − R2c within my runs is unaffected.

**[05 · test2 post-hoc](05_test2_posthoc/).** My R3 k0 / k29 models (seeds 3–5) and their BC starts on Aayush's
test2 (fresh clips), after val was final. x264 reproduces his pre-registered rows exactly (R3 − final4 +0.097 /
+0.032 \*); x265, post-hoc and not pre-registered: +0.166 / +0.098 \*.

## Leak checks
Read-only audit of 03, 04 and 05 (2026-11-19), covering every BC dataset, BC network, run and score used in the
results. Both encoders; the x265 k2 / k5 inputs (Aayush's) were checked too where they enter my tables.

| # | Check | Verdict |
|---|---|---|
| 1 | BC data: train clips only, fold and flat GOPs excluded, every k, both encoders | **PASS** |
| 2 | Inputs: o[2] masked in every BC dataset and run; nothing beyond k frames; no use of the GOP's own encode | **PASS** |
| 3 | Shift files fitted on training data only | **PASS** |
| 4a | My choices: checkpoints fixed in advance, all seeds reported | **PASS** |
| 4b | The inherited R3 recipe was chosen without val | **UNSURE**: partly chosen on val (see below) |
| 5 | test2: one evaluation per model, after val was final, nothing tuned on it | **PASS** |
| 6 | Scoring: same episodes, flat-GOP rule and PSNR cap for every compared method | **PASS** |

1. **BC data.** `bc_data_build.py` `load()` keeps GOPs with split `train`, not flat, and not in the 8 fold clips
   (`exp_next/folds.json`); BC picks its checkpoint on 10 % of those fitting clips (`bc_train.py`), never on val. Measured
   on the plan files behind every BC network (x264 k0/2/5/10/29, x265 k0/2/5/29; mine and Aayush's): 515 GOPs each, all
   `train`, 0 fold clips, 0 flat GOPs, 0 test2 clips. Clip sets are disjoint: train ∩ val, train ∩ test, train ∩ test2
   and val ∩ test2 are all empty.
2. **Inputs.** All 25 stored runs (x264 R3 / R2c, x265 R3) have `drop = level`, which zeroes o[2] through the env mask
   (`rclib/env.py`, group `"level": [2]`). All 13 BC dataset builds record 0 nonzero entries in o[2] (and in the
   dropped history o[5..8]) on the saved arrays (`labels_v2_*.md`). Lookahead: per-frame slots exist only for the
   `visible_len` frames (fixed mode: min(k, frames left)); cut distance, window cost and scene flags use the visible
   window; the controller (`rclib/controller.py`) sees first-pass bits of frames t..t+k only and replaces later frames
   with an estimate from the visible ones. The GOP's own constant-QP encodes (`curve`, `static`) enter only the reward
   shaping, which sums to 0 per episode, never the observation. Budgets are the team's leak-free clip-level targets
   (clip mean of constant-QP bits per level, `rclib/config.py`), identical for every method.
   Note, not a leak: in BC data building each plan is replayed with the budget set to its own spend, so BC's
   training observations differ slightly from what it sees at evaluation.
3. **Shift files.** `bc_shift_fit.py` fits on the BC data of item 1 (train only). New entries (x264 k2/10/29, x265 k29)
   are mine; the others are Aayush's, fitted the same way on his train-only data. My refit of k5 equals his exactly in
   each prep job (`max |mine - stored| = 0` for x264 and x265, logs `r3k_prep*`).
4. **Selection.** (a) Every run list fixes 180k steps, the 20k BC / shift-only checkpoint and `--eval-splits val`;
   nothing was picked from the saved 60k / 120k checkpoints. Every finished run is scored (x264: 11 R3, 7 R2c; x265:
   6 R3) except the R3 k5 seed-0 retrain, a reproduction check reported in 04. Single-seed points are marked.
   (b) The recipe (λ 0.17, 180k steps, f4) is Aayush's: λ was compared on val (`exp_next/exp3/PREREG.md`) and 180k is
   "the validated checkpoint" (`exp_next/final/PREREG.md`). So val is not fully unseen for R3, most of all at k5. I
   did not retune at other k, and the pre-registered test and test2 results are the clean check.
5. **test2.** `eval_test2_p1.py` loads stored models only (no training), refuses to run before a val parity gate
   passes (1,680/1,680 per model) and before all x265 seeds are scored on val, and never overwrites an output. One test2
   file per (model, checkpoint, encoder). The first x265 submission (14391564–69) crashed at the gate before loading
   any test2 GOP. x264 test2 repeats Aayush's pre-registered evaluation (identical rows); x265 is post-hoc, agreed
   with Aayush, run once after val was final.
6. **Scoring.** `score_final_capped.py` uses one metric function, one capped curve per GOP (`cap_fix_<enc>.pkl`) and
   one hole rule for every method. Measured: every method has exactly the same (GOP, level) set at every k (548 x264,
   550 x265). The infos contain no flat GOPs (0 of 140 val GOPs). test2 uses Aayush's `report.py` rules (cap, hole,
   pairing) for every method (`score_test2_p1.py`).

## Lessons learned
- **Train BC networks one after the other, not in parallel.** `bc_train.py` uses as many torch threads as the job has
  cores; two at once oversubscribe them and run ~20× slower (job 14304096 timed out).
- **`env.sh` strict-mode fix.** Job scripts use `set -euo pipefail`, but `/etc/profile` (`lang.sh`: `LC_ALL` unbound)
  and Lmod are not safe under `set -u`: switch it off while they load (the first prep job died after 2 s, empty log).
- **Set `RC_METRIC=dpsnr`.** Without it rclib's `res` arm scores with the old % saving metric (bits/actions unchanged).
- **Git: fetch from the login node if a compute node is slow.** The first fetch on a compute node timed out (the remote
  holds large result pickles); later fetches took seconds.
- **Merge `main` into a shared branch; don't rebase it.** Rebasing would flatten the p1 merge and need a force-push.
- **Fit on held-out data does not predict closed-loop quality for BC** (k0 fits best and drifts worst; k29 the reverse).
- **One scoring convention everywhere:** rescore every method with the same function, curves and PSNR cap before
  comparing; a mixed convention moved the team's x264 cut/gradual number from +0.016 to +0.069.
