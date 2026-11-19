# P2 results pack for the final report (Aayush, 2026-11-18; addendum 2026-11-19)

A self-contained summary of every P2-workspace result on learned per-frame rate control, positive and negative,
prepared so that a person or an agent can draft the team's final report from it together with the teammates'
own reports (`p4/README.md` for Sara's PID-Lagrangian work, `pavneet_handoff/` for Pavneet's live-stream work).

## Read in this order

1. `RESULTS.md` - the write-up: setting, protocol, main result, test2, the path to it, negative results,
   caveats, suggested claims (with strength) and things not to claim. Start here.
2. `figures/` - eight PNGs referenced from RESULTS.md:

   | File | Shows |
   |---|---|
   | fig1_primary_replication.png | R3 - final4 at k5 on v1 val, v1 test, test2, pooled (the headline) |
   | fig2_test2_kcurve.png | mean score vs lookahead k on test2, every method, both encoders |
   | fig3_test2_comparisons.png | R3 vs each comparator on test2 (final4, shift, BC, CQL->PPO, by class, k2, own history) |
   | fig4_dev_experiments.png | every pre-registered development experiment and whether it met its rule |
   | fig5_test2_overshoot.png | how R3 wins: % episodes over budget and mean score per method (test2, k5) |
   | fig6_test2_categories.png | R3 - final4 by content category on test2 (descriptive) |
   | fig7_learning_curve_val.png | R3 learning curve and the no-warm-up control (val) |
   | fig8_quality_vs_delay_v1test_pre_r3.png | quality vs lookahead on v1 test for the controllers and standalone learners (before R3) |

3. `tables/experiment_ledger.csv` - one row per experiment: question, comparison, result, verdict, source report.
4. `tables/key_numbers.csv` - every number plotted in figures 1-6, with the report and the exact line it came from.
5. `source_reports/` - verbatim copies of the result reports (`results_v1/**/*.md`, two figures, and the two
   test pre-registrations) as they stood on 2026-11-18, plus three 11-19 rescorings in `results_v1/final/`
   (`table1_cap.md`: the v1 test k-curve with the PSNR cap; `exp7_luma.md`, `pid_luma.md`: stream-level rows in
   luma PSNR). RESULTS.md cites them by their `results_v1/...` path.

## Conventions (short version; details in RESULTS.md sections 2-3)

- Score in dB: dPSNR_B - 0.17 x (% over budget); 0 = constant QP spending exactly the budget; higher is better.
- Differences are paired per (GOP, budget level); 95 % clip-bootstrap CI; `*` = CI excludes 0; seeds averaged.
- k = lookahead in frames; final4 = the frozen causal controller (baseline); R3 = PPO residual on final4 from a BC
  start (the method that works); test2 = second held-out set of 93 new UGC clips.
- Reports written before 11-13 use slightly different conventions (hole episodes included, uncapped PSNR, or the old
  points scale); compare numbers only within one table.

## Regenerating

`python report_pack/scripts/make_figures.py` rebuilds figures 1-6 and `tables/key_numbers.csv` from
`source_reports/` alone (numpy, pandas, matplotlib; the team env `p2_data/environment.yml` has them). The reports
themselves are produced by the scripts named in RESULTS.md section 14 (in git under `p2_data/`), from data and raw
result rows that are kept on CARC scratch and not in git.

## Credits

P2 workspace (Aayush, with Claude): data v1 and test2, metric, final4, the residual-RL line and R3, all evaluations
here. Ahhana (P1): encoder settings, the PSNR-cap correction, R3 models at k0 / k29. Pavneet (P3/P5): the original
pipeline, search and learners that the RL code builds on, stream policies reproduced in Exp 7. Sara (P4):
PID-Lagrangian stream policies used in Exp 7.
