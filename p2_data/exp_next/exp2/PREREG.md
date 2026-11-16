# Experiment 2: handoff (learner first, final4 for the last m frames) -- pre-registration

Written 2026-11-13 before any Exp 2 evaluation run (only the m = 0 / m = 30 parity checks were run: 8/8 and 8/8
exact on both encoders). Not to be edited after results arrive.

## Hypothesis

The CQL->PPO@prev 540k learner allocates at least as well as final4 but lands the budget worse. Letting final4
re-plan the last m frames from the real remaining budget keeps the learner's allocation and fixes the landing.

## Configuration

- `exp_next/exp2/handoff.py`: the stored 540k checkpoints (k 0 and 5, seeds 0-2, deterministic) choose frames
  0..29-m; final4 (setting 1.0:6:1.0:2:3:4:1:1:1:0:3, its stored history inputs for the GOP) chooses frames
  30-m..29 from the real bits and QPs of every frame already coded. Real encodes, both encoders.
- m in {3, 5, 10, 15, 20}; val; no training. The learner was trained on all train clips; the train-select fold is
  not used here (m = 10 is fixed in advance).

## Primary endpoint and gate (non-inferiority)

Hybrid at **m = 10** minus final4, on val, paired on (GOP, level, k), seeds averaged per episode first, pooled over
both encoders and k in {0, 5}; 95% bootstrap over clips (each clip carries both encoders). Level-24-hole episodes
excluded (results with them reported alongside).

**Pass** requires all of:
- point estimate >= 0;
- 95% CI lower bound above -0.05 dB;
- mean |spend error| of the hybrid at most final4's + 0.5 percentage points (same episodes).

## On pass / fail

- Pass: the handoff hybrid goes into the final test run as a candidate system (as the brief lists).
- Fail: recorded; it is still reported descriptively in the final run list only if the human asks.

## Descriptive

All m: score, paired difference vs final4 and vs the learner alone (m = 0 = its stored val rows), decomposition
(A, E - P, mean |spend error|, signed error, % over, p90 |spend error|), per k, level and encoder; per-seed means.
A tie is informative: the learner's quality edge was then mostly its spend pattern, not allocation.
