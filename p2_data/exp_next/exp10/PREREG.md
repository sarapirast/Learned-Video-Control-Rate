# Experiment 10: ABR+VBV with a tuned target margin -- pre-registration

Written 2026-11-13 before any Exp 10 encode. Not to be edited after results arrive.

## Purpose

The codec-to-oracle gap uses the encoder's own rate control. ABR+VBV was run at exactly the budget and goes over on
66-71% of val episodes, so it never got the margin final4 and the learners effectively have. This gives it one.

## Configuration

- `exp_next/exp10/abr_margin.py`: the same 1-pass ABR+VBV encode as `results_v1/baselines_v1` (P1 settings,
  --bitrate = --vbv-maxrate = m x B rate, --vbv-bufsize = m x B, --rc-lookahead k), margins m in
  {0.95, 0.97, 0.99}; m = 1.00 = the existing abr_vbv rows. Val only, k in {0, 5}, both encoders.
- Scored on the dB metric against the real budget B (lfq infos curves and budgets), flat GOPs excluded.

## Selection rule (no gate)

Per encoder, pick the m in {0.95, 0.97, 0.99, 1.00} with the highest mean val score pooled over k in {0, 5} and the
4 levels, level-24-hole episodes excluded. Ties within 0.005 dB go to the larger m. The selected m per encoder is
run in the single final test run at k in {0, 2, 5, 10, 29}, and the codec-to-oracle gap uses it.

## Reported

Score, decomposition (A, E - P, mean |spend error|, signed error, % over), per m, k and level; the rate
quantisation (integer kbit/s) per level.

## Extension (Aayush 11-14, before any new encode)

The selected margin 0.95 sat on the grid edge. Margins 0.90 and 0.93 are added on val (same encode, k 0 / 5, both
encoders; abr_margin.py --margins 0.90,0.93 --tag ext); selection rule unchanged over {0.90, 0.93, 0.95, 0.97, 0.99,
1.00}. If 0.90 is selected it is reported as on the grid edge. The selected margin is frozen into
exp_next/final/PREREG.md before the test pass.
