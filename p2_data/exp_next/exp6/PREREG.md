# Experiment 6 gate (no encodes): per-context choice among final4-family settings -- pre-registration

Written 2026-11-14 before any per-context number was computed. Brief Part C Exp 6 step 1 + amendment 8 ("run the
free gate, expect it to fail; spend nothing more if it does").

- **Data.** Stored val rows of the final4-family settings with previous-GOP history, all on the same episodes:
  hist1 (8 settings) and hist2 (4 settings; its no-history control 1.0:6:1:2:3:4:1:1:1:0:0 excluded) =
  12 settings, incl. final4 = 1.0:6:1.0:2:3:4:1:1:1:0:3. Both encoders, k {0, 2, 5, 10, 29}, 4 levels.
  Rescored on the project metric (dPSNR_B - 0.17 x %over, as scripts/controller_dpsnr.py); flat GOPs and
  level-24-hole episodes excluded.
- **Contexts (causal at k).** k; the causal base-QP estimate base_qp_est_k<k> (budgets.csv), bins < 27 / 27-33 /
  33-39 / >= 39; the previous GOP's real / predicted bits ratio r_prev, bins none (first GOP) / < 0.9 / 0.9-1.1 /
  > 1.1; visible first-pass complexity = log2(mean first-pass bits of frames 0..k / (B / 30)), 2 bins at its val
  median per (encoder, k). **Deviation from the brief:** the budget level is NOT a context -- under v1's clip-mean
  budgets it is clip-level hindsight (Exp 5a REVISION 3); the base-QP estimate carries the causal part. GOP class
  not used.
- **Leave-one-clip-out (16 val clips).** For each held-out clip and each context cell, on the other 15 clips: per
  setting the mean paired difference vs final4 and its standard error (clip-clustered); pick the setting with the
  largest lower bound (mean - 1 SE) if that bound is > 0, else final4 (pessimism). Score the held-out clip's
  episodes with the picked settings.
- **Gate.** Pooled over both encoders, k and levels: (picked - final4) mean >= +0.03 dB and 95% clip-bootstrap CI
  lower bound > 0. Fail -> stop (no bandit, no encodes). Also reported: per encoder, per k, how often a setting
  other than final4 is picked, and the oracle per-cell best (in-sample, upper bound, not the gate).
