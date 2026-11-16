# Experiment 0: first-hour checks (2026-11-13)

Reading only, no jobs submitted. Brief: `docs/next-experiments-agent-brief-2026-11-13.md` (Part E amendments
included). Scripts: `exp_next/exp0/count_search_logs.py`, `exp_next/exp0/coverage_checks.py`; parity logs
`exp_next/exp0/parity_train_<enc>.log`.

## Summary

| # | Check | Answer | Consequence |
|---|---|---|---|
| 1 | Per-frame data in the search logs | **Train: yes.** 600 logged encodes per (GOP, level) (2 seeds x 300), each with per-frame action index, bits and PSNR. **Val/test: best plan only.** | Experiments 4/5 can proceed: Exp 5 trains on train only. |
| 2 | `resh` reward, lambda, caps | Reward = dPSNR_B - final4's stored dPSNR_B - 0.34 x %over. Offsets are added after final4's caps, which are **not** re-applied. Parity on train: **40/40 exact per encoder** (20 per k) | Exp 3 needs only `--lam 0.17` (no code). Exp 4 R2 needs a decision on caps (below). |
| 3 | final4's built-in shape | Formula below. The I frame is anchored to the estimator's qhat, not to the solved level. | Matters for Exp 1's "final4 shape"; Exp 5's amended labels don't need it. |
| 4 | final4 train results | **Complete:** 12,500 rows per encoder = every train (GOP, level, k), 11,800 of them non-flat. | Stored-row baseline is usable. |
| 5 | Critic explained variance | **Not logged** (SB3 verbose 0, no logger; `train_curve.npy` holds score / over / saving only). | Needs an offline estimate. Only Exp 9 (if time) depends on it. |
| 6 | PPO settings; deterministic eval | GAE lambda 0.95; separate actor and critic MLPs (2x256 each, ReLU); SB3 advantage normalisation on (default); gamma 1; 896-step rollouts (64 x 14 envs), batch 128, 5 epochs, clip 0.2, entropy 0.01, lr 1e-4. **Evaluation is deterministic (argmax)** for every SB3 policy, including all past residual runs. | Past residual results stand as read; no exploration noise in them. |
| 7 | Level-24 hole | Linear extrapolation in log-bits beyond the QP-18 point. Smaller than the brief's 10%: test 13/252 (x264) and 12/252 (x265) level-24 episodes, val 10/140 and 8/140; 2 per split at level 30. | Exp 1 reports the effect; fix proposal goes to you. |
| 8 | Reference frames | No `--ref` override anywhere (`rd_native.py`, `rclib/codec.py`); preset medium default **ref = 3** on both encoders. | Exp 8's rate model needs the 3 previous frames' QPs. |

## Details

### 1. Search logs (`rcwork_v1/<enc>_lfq/results_search/search_<split>.pkl`)

- Per (GOP, level), train entries hold `logs`: 2 lists (seeds) x 300 dicts with `acts` (30 action indices),
  `bits` (30, per frame), `fpsnr` (30, per frame), `total_bits`, `psnr`, `score`. Also `traces`, `start` (the
  ramp start plan: q, per-frame bits and PSNR) and `base_q`.
- Per-frame QP is exact from the code: `qp_t = clip(round(base_q + STATIC_OFF[t] + ACTIONS[a_t]), 11, 51)`
  (`rclib/search.py` qps_of, lfq arm), ACTIONS = -5..+5.
- Counts, non-flat (GOP, level): train 2,360 per encoder, every one with 600 logged encodes (1,416,000 per
  encoder). Val 560 and test 1,008 have only `best_acts`, `total_bits`, `psnr`, scores.
- The logs include the 35 flat train GOPs with meaningless scores (savings near -3e9): every script must filter
  `data/v1/320x180/rd/flat_gops.csv` first.

### 2. Residual arm (`repo-pavneet/rclib/env.py`, `experiments/rl.py`)

- `rl.py`: method `res` uses reward kind `lagrangian`, lam `lagr_lam_db` = 0.34 (dB per 1% over); `--lam`
  overrides it (flag exists).
- `env.py` result(): `rew = dPSNR_B - ctrl["dpsnr"] - lam x %over`, where `ctrl` = `info["ctrl"][(level, k)]`, the
  **stored** final4 row for that episode (filled by `tools/res_infos.py` from
  `results_v1/controller_real/final4_*`). The env does not run a separate final4-only encode.
- Relation to the brief's paired reward: score - score_final4 = (dPSNR_B - 0.17 x over) - (ctrl dPSNR_B - 0.17 x
  ctrl over). At lam 0.17 the existing reward differs only by + 0.17 x ctrl over, a per-episode constant that
  does not depend on the actions (same expected gradient). Per amendment 2, Exp 3 uses the existing reward with
  `--lam 0.17`. (An exact paired version is reward kind `relative`, which also exists in the env; `rl.py` would
  need a one-line flag to select it for `res`.)
- Stored rows are complete on all splits: 0 missing (GOP, level, k) rows for 590 / 140 / 252 non-flat
  train / val / test GOPs, both encoders. The history inputs (`ctrl_qhat`, `ctrl_r`) are the stored controller's
  own GOP n-1 chain.
- **Parity on train (amendment 2):** `tools/res_parity.py 5 train 0,5` (5 GOPs x 4 levels x k 0/5 = 20 episodes
  per encoder and k; all offsets 0 in the env vs the stored final4 rows; same per-frame QPs, same bits, score
  within 1e-6). **Result: 40/40 exact on x264 and 40/40 on x265, max |d score| 0, no mismatches** (logs `exp_next/exp0/parity_train_<enc>.log`; run on the interactive node, about 2 min, no sbatch). Earlier val parity: 36/36 exact on both encoders (11-11, after the slim() fix).
- **Caps after the offset:** `q = clip(q_ctrl + offset, 11, 51)`. final4's single-frame spend cap (fcap) and
  QP-step limit (dmax 3) act inside `decide()` *before* the offset and are **not** re-applied. On the next frame
  `decide()` uses the actual previous QP (offset included) as its dmax reference, so the step limit follows the
  residual's QPs. With range -3..+3 this rarely matters; with R2's -6..+6 the offset can step up to 9 QP from
  the previous frame.
- **Decision for you (Exp 4 R2 step 2):** the brief says "apply the caps after the offset, the same as in `resh`
  if Exp 0 shows it does that". It doesn't. Options:
  - (a) keep `resh` behaviour (no re-application; log how often the offset exceeds what dmax/fcap would allow);
  - (b) re-apply dmax and fcap after the offset (code change behind a flag; then R2 differs from R1 in three
    things, range + features + caps).
  
  I'd take (a): R1 and R2 then share the cap behaviour, and the log tells us whether it matters.

### 3. final4's planned QP (setting `1.0:6:1.0:2:3:4:1:1:1:0:3`)

Fields: margin 1.0, dI 6, i_cap 1.0, w0 2, dmax 3, fcap 4, init 1, pmin 1, a 1, b 0, h 3
(`rclib/controller.py` decide, verbatim copy of `scripts/controller_real.py`).

- **Level L_t** (re-solved before every frame t >= 1): the real number q such that
  `c_P,t x sum_{j=t..29} fh_j x 2^(-(q + off_j - 30)/s_P) = 1.0 x B - bits spent so far` (bisection),
  with `off_j = -1 + 2 (j - 1) / 28` (the ramp: -1 at frame 1 to +1 at frame 29), `fh_j` = first pass of
  frame j if visible (j <= t + k), else the shrunk mean of the visible P frames, and c_P,t calibrated online
  from frames 1..t-1 (shrinkage weight w0 = 2 towards the train prior).
- **P frame t:** `qt = round(L_t + off_t)`; then raised by 1 while the predicted bits of frame t exceed
  4 x (remaining budget / frames left) (fcap); then clipped to [ref - 3, ref + 3] with ref = previous frame's QP
  (frame 1: I QP + 6) (dmax); then `qt >= I QP + 1` (pmin); clip to 11..51.
- **I frame:** `q_I = round(qhat - 6)` (init 1: qhat = the previous-GOP base-QP estimate with history h 3,
  `budgets_prev_<enc>.csv`), raised by 0.5 while the predicted I bits exceed 1.0 x B. Rate-model priors c_I, c_P
  are scaled by the previous GOP's real / predicted bits (h 3).
- **Built-in shape relative to the level:** P frames `off_t = -1 + 2 (t - 1)/28` (fixed), I frame
  `q_I - L_1 = (qhat - 6) - L_1` (**not fixed**: it depends on how far the estimator's qhat is from the level the
  controller solves at frame 1). The fcap / dmax / pmin adjustments make the realised shape differ from the
  formula on some frames; Exp 1 should measure the realised final4 shape from the stored per-frame QPs rather
  than the formula.

### 5. Critic explained variance

Not in any log. Options if Exp 9 becomes live:
- Standalone CQL->PPO 180k / 540k (`lfqp`): rebuild the observations along the stored val eval episodes with
  `env.plan_observations` (exact by the prefix property, no encodes), run the saved value head, compare with the
  terminal reward. About 1-2 h of code.
- Residual runs: observations need the controller state, so a replay through the env with the stored offsets
  (real encodes, small sample).

Exp 9 is "if time", so I'd defer this until Exp 4 reads out.

### 6. PPO details (`experiments/rl.py`)

- `PPO("MlpPolicy", n_steps=64, batch_size=128, n_epochs=5, gae_lambda=0.95 (--gae-lambda), ent_coef=0.01,
  clip_range=0.2, policy_kwargs={"net_arch": {"pi": [256, 256], "vf": [256, 256]}, ReLU}, gamma=1.0)`, 14 envs.
- Residual: lr 1e-4, actor bias set so P(offset 0) = 0.7, PPO from scratch otherwise (no offline stage).
- CQL->PPO: the value head is initialised from the CQL Q-function (`distill_into_ppo(..., value_from_q=True)`),
  so Part B item 9's re-initialisation and warm-up is a real change for any CQL-initialised run.
- Evaluation: `rclib/policies.py` SB3 wrapper calls `model.predict(obs, deterministic=True)`; `rl.py` evaluates
  through it for every method. All past gate numbers are deterministic.

### Cost calibration (for the CPU-h estimates)

RL array tasks use 16 CPUs. Measured from sacct: residual at 180k steps (item 37, 18 runs) took 0.39 h (x264) and
1.17 h (x265) per run, about 6 and 19 CPU-h. Exp 3 (12 runs) should cost about 150 CPU-h, below the brief's
250-400.
