# Final-week experiments: rules written before results (2026-11-17)

Plan: docs/final-week-experiments-2026-11-17.md (approved by Aayush 11-17: "go ahead"). Freeze: no new launches after
Thu 11-19 12:00; results by Fri 11-20.

Common protocol:
- val only, EXPLORATORY in every report; no test re-analysis or re-measurement without Aayush's approval
- paired on identical (GOP, level, k); 95 % clip bootstrap; hole excluded
- 100 dB per-plane PSNR cap (results_v1/final/cap_fix_<enc>.pkl)
- final4 frozen; o[2] removed; BC fitted on the fitting clips only (train-select fold excluded)

Verify-first answers (11-17, from code):
- V1: R3's env replays final4's own GOP n-1 history (tools/res_infos.py: ctrl_qhat / ctrl_r from the stored final4 run) -> item 2 runs.
- V2: checkpoints at 60k (all seeds) and 180,993 (s3-5), final 180k (s0-2) and 360k (s3-5), all val-scored; step 0 is
  rebuildable (exp_next/exp4/r3_step0.py); end of warm-up not saved.
- V3: the 20k critic warm-up is counted inside the 180k total (rl.py --warmup).
- V4: Ahhana's k0/k29 details unknown -> ask her (k2 planned? seeds? own mean[t] / BC at k29?).
- V5: rclib/search.py hill_climb(start=...) accepts a plan; 600 = 2 seeds x 300 whole-GOP encodes.

## Claim rules (fixed before results)

| Item | Rule |
|---|---|
| 1 R3 / BC alone across k | Descriptive k-curve. "RL adds over BC at k" only if R3 - BC alone at that k has a pooled CI excluding 0. The hypothesis "RL adds most at small k" is reported as supported only if R3 - BC alone at k0 exceeds the k5 value and the paired difference (k0 - k5) has a CI excluding 0. |
| 2 history source | Sequential (own GOP n-1) - stored (final4's GOP n-1) history, R3 k5, val. abs(pooled diff) <= 0.02 dB: one sentence in the report. Larger: escalate to Aayush before anything on test. |
| 3 learning curve | Descriptive only (score and breakdown against encodes). |
| 4 warm-up ablation | "The warm-up matters" only if R3 - no-warm-up (paired, val, 3 seeds, both encoders pooled) has a CI excluding 0; otherwise "no detectable effect". |
| 5 metric sensitivity | Descriptive: R3 - final4 at lambda in {0, 0.085, 0.17, 0.34, 0.68} dB per 1 %; the crossing lambda (if any) reported with the caveat that R3 was trained at 0.17 and not retrained. |
| 7 search ceiling | If the best restart plan beats the stored search plan by more than 0.05 dB on average, the "fraction of the search's gain" statements are flagged as overstated. |
