# RL models: review of Pavneet's implementations and proposals (2026-11-04)

- **Basis:** the v1 rerun of `pbanga-alt/ee599-rl-rate-control` (da7cc53, local branch `v1-data`), both
  encoders and both budget arms.
- **Numbers come from:**
  - `results_v1/v1_headline.md` (`scripts/v1_headline.py`)
  - `results_v1/v1_overshoot.md` (`scripts/v1_overshoot.py`)
  - `results_v1/<codec>_arm_compare.md`
- **Two numbers come from one-off checks in this session, not saved scripts:**
  - search action saturation (section 2)
  - training curves (section 3)

  They're reproducible from `search_train.pkl` and `results_rl/*/train_curve.npy`.

## 1. What is implemented (`experiments/rl.py`, `rclib/`)

Most implemented methods haven't been run on v1 yet:

| Method | What it is | Run on v1? |
|---|---|---|
| `bc` | MLP classifier on the search's best plan per GOP x budget (argmax at test) | yes |
| `cql`, `iql` | Offline discrete CQL(H) / IQL on 48 logged plans per GOP x budget | no |
| `cql_ppo` | CQL teacher distilled into PPO, then 60k PPO steps (his core recipe) | yes |
| `bc_ppo` | BC teacher, then PPO | no |
| `lagr` | `cql_ppo` with reward = saving - lambda x overshoot, lambda = 4 fixed | yes |
| `pid` | `cql_ppo` with lambda set by a PID controller targeting 5% of GOPs over budget | no |
| `lagr_ft`, `pid_ft` | continue a finished `cql_ppo` under the constraint, oversampling cut GOPs x4 | no |
| `ppo`, `a2c`, `dqn` | online from scratch | no |
| `cql_a2c`, `cql_dqn` | offline init, then online | no |
| `anyk` | one network trained with a random k per episode | no |
| `gate` | per-frame switch between a k=0 and a k=K policy, with a cost for lookahead | no |
| `ensemble` | argmax of mean action probabilities over 3 seeds (no training) | no |
| `mpc` | learned bits/PSNR model + receding-horizon CEM over the visible window, margin chosen on val | no |
| `mb`, `mb_ppo` | PPO inside the learned model, then on real encodes | no |
| `clip_rl` (`clipenv.py`) | multi-GOP stream under one shared budget, GOP-level QP, with a causal model QP | no |

How it's set up:
- **Action:** 7 offsets, -3..+3, added to `b + STATIC[t]`. b is the budget QP, which is also the oracle QP
  (finding U1).
- **Observation:** 16 global features plus 30 frame slots of 11 features each, 346 numbers in total.
  Slots beyond the visible lookahead are zero.
- **Reward:** given only at the end of the 30-frame episode, with gamma = 1:
  - `relative`: (score - STATIC score) / 10
  - `lagrangian`: (saving - STATIC saving - lambda x over) / 10, with lambda = 4. The evaluation penalty is
    2 per 1% over, so this reward punishes overshoot twice as hard as the score does.
- **Each env step** is a real prefix encode, so an episode costs about 465 frame-encodes.
- **PPO:** 60k steps (about 2,000 episodes) from 14 envs, lr 1e-4 when fine-tuning, entropy coefficient
  0.01, networks of 256x256.
- **Evaluation:** deterministic argmax; scores are on test, and the k grid is fixed.

## 2. What the results say

**Lagrangian PPO is the best method because it stays in budget, not because it saves the most.**
- Its score at k=0 is 4.67 on x264 and 4.12 on x265. It overshoots on only 2-3% of episodes and loses at
  most 0.5 points to the penalty.
- BC and CQL->PPO actually save **more** before the penalty:

  | Encoder | Method | k | Saving before penalty |
  |---|---|---|---|
  | x265 | CQL->PPO | 5 | 5.56 |
  | x265 | Lagrangian (best) | any | at most 4.95 |
  | x264 | CQL->PPO | 2 | 4.97 |
  | x264 | Lagrangian (best) | any | 4.78 |

- They lose 0.9-3.3 points to overshoot on the original budget, and 2.4-5.1 on the decoupled budget.

**How big the overshoots are** (`v1_overshoot.md`, per episode):
- **How often:** BC and CQL->PPO go over on 14-37% of episodes (original budget) and 20-32% (decoupled).
  Lagrangian goes over on 2-10%.
- **By how much, when over:** a median of 1-6% and a mean of 1.8-8%. The 90th percentile is 4-18%.
- **Worst cases:** 61% (BC, x264 k=2, a stable lecture GOP) and 48% (CQL->PPO, x264 k=0, a Tears of Steel cut
  GOP).
- **Under a hard per-GOP budget,** which is how the project question is framed, every one of these is a
  violation. A 15-37% violation rate isn't acceptable for a rate controller.
- **Cut and gradual GOPs** go over 1.4-3.5 times as often as stable GOPs, and by more.

**Most of the "lookahead gain" for BC and CQL->PPO is a smaller overshoot penalty.**

| Change | Saving | Penalty | Score |
|---|---|---|---|
| x264 CQL->PPO, k=0 -> k=5 | +1.56 | -2.36 | +3.9 |
| x264 BC, k=0 -> k=29 | +1.78 | -1.45 | +3.2 |

So lookahead mainly helps these policies avoid overspending. It does much less for allocating bits
better. Lagrangian, which already stays in budget, gains at most +0.6 from lookahead.

**The decoupled budget raises overshoot for every method.** The policies learned to rely on the leaked
relation between the budget and the GOP's cost (finding C1).

**The action range is too narrow.**
- The search's best plans on train use offset +3 on 20-23% of frames and -3 on 6-7%.
- That's 26-30% of all frames at a limit.
- The STATIC base spends too much late in the GOP, especially on x264, where STATIC is badly tuned.

**PPO is unstable rather than undertrained.**

| Train score (mean over 15 runs) | First quarter | Middle half | Last quarter |
|---|---|---|---|
| Lagrangian | 3.0 | 4.4-4.7 | 3.9 |
| CQL->PPO | 2.3-2.4 | 2.9-3.7 | 2.4-2.8 |

Only 1-2 of 15 runs per method are still improving at the end. The final checkpoint, which is the one
evaluated, is past the best one. CQL->PPO's training overshoot rate (20-25%) stays high throughout.

## 3. Tuning the existing models (cheap, in his code)

Ranked by expected value per CPU-hour:

1. **Budget shield at inference (no retraining).**
   - Before each frame, project the remaining spend at the chosen action. Use first-pass bits x
     2^(-(QP-30)/6), calibrated online on the frames already coded, which is the same model `clipenv`
     uses.
   - If the remaining budget can't cover it, raise the QP. As a last resort, force QP 51, as P1's env does.
   - Apply it to the saved BC, CQL->PPO and Lagrangian models. Evaluation only: a few CPU-minutes per model.
   - **Expected:** most of the 0.9-3.3 penalty points on BC and CQL->PPO come back, the violation rate falls
     towards 0, and the cost in saving is small.
   - **The test:** do BC and CQL->PPO with a shield beat Lagrangian? They already save more.
2. **Pick the checkpoint on val.**
   - Save checkpoints during PPO (e.g. every 5k steps) and choose the best by val score.
   - The training curves say the last checkpoint isn't the best one.
   - Small retraining cost; no change to the method.
3. **Sweep lambda for Lagrangian (2, 4, 8) and run `pid` (target over-budget rate of 1-5%).**
   - lambda = 4 is a single, untuned guess.
   - A sweep turns "Lagrangian vs the rest" into a trade-off curve of saving against violation rate. That's
     the fair way to compare methods.
4. **Widen the action range to +-5, or refit STATIC per encoder.** The +3 limit binds on 20% of the
   search's frames, so both the policies and the search are capped.
5. **Ensembles over seeds (`ensemble`, already implemented, no training).** Usually lowers variance and
   overshoot.
6. **A compact lookahead summary (`--extra sum`, already implemented).**
   - It replaces the 319 lookahead slot features (29 slots of 11) with summary statistics.
   - It may let the MLP policies use lookahead better.
   - It's also P2's feature-spec proposal.

## 4. New models worth trying

1. **A residual policy on a causal rate controller.** This is the main recommendation, since it's needed for
   the research claim anyway.
   - Replace the base `b + STATIC` with a causal model QP: budget per frame plus first-pass bits, giving a
     QP with online calibration. That's P2 task 5 / tracker item 14, and the same idea as `clipenv`'s model
     QP.
   - The RL policy then learns offsets on a controller that is already feasible.
   - This removes the oracle base QP (U1). With clip-level budgets it also removes the leak (C1).
   - The policy no longer has to learn rate control from scratch, which is why BC and CQL->PPO overshoot.
2. **Shielded, constrained PPO.**
   - Train with the shield from section 3.1 active, so the agent only explores feasible plans.
   - Use PID-Lagrangian on the remaining risk.
   - This is the standard safe-RL setup, and it directly targets a hard budget.
3. **MPC with the learned rate model (`mpc`, already implemented, not run on v1).**
   - Model-based planning is how rate control is usually done.
   - It uses lookahead explicitly, through planning over the visible window, so the k curve may show a
     clearer effect than with model-free MLPs.
   - Training uses only the search logs; evaluation needs encodes.
   - Suggested: k = 0/2/5/10/29 on x264, 1 seed first.
4. **Return-conditioned offline RL (Decision Transformer style).**
   - Condition the policy on the target score and the remaining budget, and train on all 48 logged plans per
     GOP x budget, not just the best.
   - The budget becomes an explicit input, so one model covers every budget.
   - New code, moderate effort.
5. **An attention or 1-D convolution encoder over the visible lookahead slots** in place of the flat 346-input
   MLP.
   - It handles any k, and is the natural way to test whether lookahead helps when the model can use it.
   - Moderate effort; pairs well with item 1.

Not recommended for now:
- **Online PPO/A2C/DQN from scratch.** His paper already shows these are weak at this encode budget.
- **More PPO steps.** The curves show instability, not undertraining.

## 5. Suggested order and cost (x264 first)

| Step | What | Training? | Cost |
|---|---|---|---|
| A | Shield at inference on the 45 + 24 existing x264 models (then x265) | no | ~5-10 CPU-h per encoder |
| B | Lagrangian lambda in {2, 8} + `pid` at 1% and 5%, k = 0/2/10, 3 seeds, with val checkpoint selection | yes | ~150 CPU-h |
| C | MPC at k = 0/2/5/10/29, 1 seed | model training only | ~30 CPU-h |
| D | Residual on a causal controller + clip-level budgets | needs item 14 first | after P2's estimator |
| E | DT or attention encoder | new code | after D |

A, B and C can run on the existing v1 setup. D is the principled fix and depends on the P2 estimator.

## 6. Result of A (2026-11-04): the budget shield doesn't pay off as designed

Val, x264 original budget, seed 0, all k pooled (`results_v1/x264_orig_shield_val.md`):

| Method | Score: none -> best shield (tol 0.5) | Runs over budget |
|---|---|---|
| BC | 2.67 -> 2.22 | 24% -> 19% |
| CQL->PPO | 2.89 -> 2.25 | 21% -> 17% |
| Lagrangian PPO | 3.45 -> 2.71 | 12% -> 9% |

- **Saving falls by 1-1.2 points.** Overshoot shrinks only partly.
- **Why:**
  - The overshoots are small (a mean of about 0.6%, costing about 1.2 score points).
  - The shield's prediction of total bits is noisy early in the GOP (the 10th-90th percentile spans about 0.77-1.17 of
    the true value at frame 5, and narrows to about ±3% only by frame 25).
  - So it fires 1-3 times per GOP, mostly on GOPs that would have finished within budget, and each firing raises the
    QP sharply.
- **Conclusion:** under this score, shielding doesn't let BC or CQL->PPO overtake Lagrangian. Under a hard budget
  this shield also doesn't enforce the budget reliably.
- **Possible last test:** an end-game shield that acts only in the last 5-10 frames.
