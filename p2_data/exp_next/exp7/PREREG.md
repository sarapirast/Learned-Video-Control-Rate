# Experiment 7: stream level, controls first, then a zero-shot hierarchy -- pre-registration

Written 2026-11-14, after step 0 (STEP0.md) and during step 1 (reproduction, no new results), before any rule
retuning, PID-Lag retraining or Part 2 encode. Reproduction / extension of Pavneet's D34/D35 (commit eb08445) and
Sara's P4 (commit 1860557); their code is used from copies (exp_next/exp7/src_*), outputs go to
results_v1/next/exp7/ and /scratch1/aayushso/rcwork_exp7/. Brief Part C Exp 7 + Aayush's 11-14 instructions.
Goal: a frozen Exp 7 configuration in exp_next/final/PREREG.md by Monday morning; otherwise Exp 7 is reported as
val-only, labelled so, and left out of the test pass.

## Fixed setup (unchanged from D34)

- Metric: dPSNR_B - 0.17 dB per 1 % over budget, on the stream's pooled PSNR (rclib/metrics.py in Pavneet's copy).
- Streams and budgets as D34: same-clip windows of N consecutive GOPs of a v1 clip (splice clips excluded) and
  mixed streams; budget = s x sum of the GOPs' v1 budgets.csv budgets at q0, q0 in {24, 30, 36, 42},
  s in {0.85, 1, 1.18}. Outcomes from the real constant-QP curves (no encodes in Part 1).
- Rule = Pavneet's remaining-budget rule (margin m, rate slope qpd, prior weight cw, prior c0 from train).

## Part 1 (table lookups)

a. **Rule at 8 GOPs, retuned on val.** Lookahead L = 2 (as the RL candidates) and L = 0, tuned on val same-clip
   8-GOP streams (the primary population). Grid: margin 0.94-1.02 step 0.01; qpd 2.5-4.5 plus 5.0, 5.5, 6.0, 7.0
   (extended further, and cw beyond 1-12, until every optimum is interior, for both encoders and both L);
   cw 1, 3, 6, 12, 24. Reported in two versions everywhere: **"vs the rule as reported"** (Pavneet's rule_wide.pkl
   settings) and **"vs the retuned rule"**.
b. **Rule at 16 and 32 GOPs, retuned on train chains.** Consecutive clips of one source chained in clip order:
   bbb (6 clips, 60 GOPs) and sintel (6 clips, 60 GOPs); windows of 16 / 32 GOPs, stride 4. The RL policies were
   trained on train, so the rule gets the same footing. If the chained clips are not consecutive in the film, each
   join acts like a scene cut (noted, accepted). Val check, descriptive only: the `sita` chain (6 clips, 60 GOPs;
   single source, no conclusions). Test-side 16 / 32-GOP streams: the ED / ToS segments, as in D35. 16 / 32 is
   secondary; the primary is 8-GOP same-clip.
c. **Candidate stream policies (L = 2, Pavneet's stored checkpoints unless stated):** plain PPO (ppo_L2, seeds 0-2),
   BC->PPO (bc_ppo_L2), and Sara's PID-Lag PPO retrained by us: ppo_pid_L2 and bc_ppo_pid_L2, her train_pid.py at
   commit 1860557 unchanged (target 5 %, Kp 2, Ki 0.05, 2M steps, 3 seeds, both encoders), trained on train. No
   tuning. **PID-Lag enters the val selection only if all its runs finish by Sunday 2026-11-15 23:59**; otherwise it
   is dropped and the report says so. Sanity check before it enters (no stored numbers exist): its val share of
   streams > 1 % over should be broadly about half the rule's, with a score in the range Sara described.
d. **Selection (fixed now):** per encoder, the candidate with the highest mean score minus the retuned L = 2 rule on
   val same-clip 8-GOP streams (seeds averaged per case). Within 0.01 dB -> the simpler: plain PPO > BC->PPO >
   ppo_pid > bc_ppo_pid.
e. **Primary endpoint (test pass):** selected RL minus the retuned L = 2 rule on same-clip 8-GOP test streams, per
   encoder, 95 % cluster bootstrap over source groups (stream_rl.cboot), **CI above 0 on both encoders**. If it fails,
   the report says "lookahead helps", not "RL helps".
f. **Secondary:** vs the rule as reported; 16 / 32 GOPs vs the rule retuned at those lengths (train chains); mixed
   (spliced) streams as a stress test; BD-rate; over-budget rate and p90 |spend error|; L = 0 versions.

## Part 2 (only if Part 1's selected policy beats the retuned L = 2 rule on val; otherwise skipped and said so)

a. Per-GOP budget B_g = the stream policy's predicted spend for its chosen constant QP under its own causal rate
   model. b. final4 runs inside each GOP at budget B_g with real encodes; the actual GOP spend is fed back into the
   stream state. No retraining. c. Four systems: stream RL + final4, stream RL + constant QP, rule + final4, rule +
   constant QP. d. Check: with final4 inside, mean |GOP spend - B_g| about 2 % or less; distribution reported.
e. Val is descriptive only (few same-clip streams), and so is the test pass. f. Optional, val only, if compute is
   left: R3 (k5) inside instead of final4; descriptive, not in the frozen test configuration.

## Reporting

Decomposition (quality for the bits vs landing), signed spend error, over-budget rate, cluster-bootstrap CIs. D34/D35
stream results were already measured on v1 test and the "fresh" films (ED, ToS) are v1 test clips: Exp 7 test numbers
confirm already-reported results, not a first look at test. Credit Pavneet (D34/D35, eb08445) and Sara (P4, 1860557).
