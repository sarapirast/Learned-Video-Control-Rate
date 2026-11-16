# Experiment 3: residual RL at the metric's price (lambda 0.17) -- pre-registration

Written 2026-11-13 before any Exp 3 run was submitted. Not to be edited after results arrive.

## Hypothesis

The residual on final4 was trained at lambda 0.34 (twice the metric's 0.17). At the matched price it does better
than at 0.34, and is no worse than final4.

## Configuration

- Arm `resh` (residual on final4, setting 1.0:6:1.0:2:3:4:1:1:1:0:3), offsets -3..+3, existing observation,
  existing initialisation (P(offset 0) = 0.7), PPO lr 1e-4, as in item 37.
- Only change: `--lam 0.17`. Reward = dPSNR_B - final4's stored dPSNR_B - 0.17 x %over (Exp 0 item 2: the
  existing controller-relative reward; it differs from the paired score difference by 0.17 x final4's own %over,
  a per-episode constant independent of the actions).
- 180k PPO steps, checkpoint also saved at 60k (`--save-at 60000`, descriptive only). Full train set (amendment 1).
- k in {0, 5}, seeds 0, 1, 2, both encoders: 12 runs. Evaluation deterministic, val only (`--eval-splits val`).
- Code: repo-pavneet branch `next-exp` (rl.py flags `--eval-splits`, `--save-at`; env unchanged).

## Primary endpoint

Residual(lambda 0.17, 180k) minus residual(lambda 0.34, 180k) (item 37 runs `res_k<k>_fixed_st180k_s<seed>` in
`rcwork_v1/<enc>_resh`), on val, paired on (GOP, level, k), seeds averaged per episode first, pooled over both
encoders and k in {0, 5}; 95% bootstrap over clips (each clip carries all its GOPs, levels, k and both encoders).
Level-24-hole episodes (budget above the QP-18 curve point) are excluded from the primary endpoint; results with
them are reported alongside.

**Pass** requires all of:
- the primary CI lies above 0;
- neither encoder's CI lies entirely below 0;
- the point estimate is >= 0 at k = 0 and at k = 5 separately;
- the mean difference has the same sign for seeds 0, 1, 2 (seed s of the new run vs seed s of the old).

Checkpoint: the final 180k model only.

## On pass / fail

- Pass: lambda 0.17 becomes R1, the base of Exp 4's ladder.
- Fail: R1 still = this configuration (Exp 4 compares R2 against it), and the report says the price change did not
  help.

## Secondary (descriptive)

Each run vs final4 (paired, same pooling); the 60k checkpoint vs 180k; decomposition (A, E - P, mean |spend
error|, signed error, % over, p90 |spend error|) per k and level; action histogram and mean |offset|.
