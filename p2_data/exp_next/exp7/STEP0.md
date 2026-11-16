# Exp 7 step 0: inventory, provenance, leakage (reading only, 2026-11-14)

Reproduction / extension of Pavneet's D34/D35 stream work and Sara's P4 stream work. Nothing of theirs was edited;
copies in exp_next/exp7/src_pavneet (pavneet_handoff/) and exp_next/exp7/src_sara (p4/), see PROVENANCE.txt.

## Provenance

| Component | Where | Commit |
|---|---|---|
| Pavneet D34/D35 (stream env, rule, BC/PPO/BC->PPO/BC->PPO-Lag, fresh films, encoder RC) | team repo main, `pavneet_handoff/` (code in `repo/`, policies + curves in `artifacts/<codec>/`) | eb08445394aea4e1097a5a8f2f68c5755d7aa3f4 (main now 72e0b1d) |
| Sara P4 (per-length rule LOFO, PID-Lagrangian PPO, rule margin sweep, long streams) | team repo branch `sara-p4`, `p4/` | 1860557246e69ff66b9740f92e586bbec7b783d0 (3 commits past what main merged) |

Pavneet's own repo (github pbanga-alt/ee599-rl-rate-control, last commit 20c3862) holds D31+ uncommitted; the handoff
copy is the only versioned record of the D34/D35 code.

## Checkpoints that exist

- Pavneet, per encoder (x264, x265), `artifacts/<codec>/v1/results_stream/`: bc, ppo, bc_ppo, bc_ppo_lag x L 0 / 2 x
  seeds 0-2 = 24 model.zip + eval.pkl (val and test rows); baselines.pkl (equal split, rule at L 0 / 2), rule_wide.pkl
  (rule grid widened until interior, L 0 / 2). Fresh-film results n8 / n16 / n32.pkl; v1 + fresh curves (infos_slim).
- Sara: **no checkpoints and no result files committed** (models trained on her laptop; only training logs in
  p4/logs). PID-Lag policies (ppo_pid L0/L2, bc_ppo_pid L2, target variants) would have to be retrained.

## Leakage check (clips used and their v1 split)

| Component | Data | Split | Verdict |
|---|---|---|---|
| Pavneet PPO / BC / BC->PPO / -Lag training | v1 stream windows + 100 mixed streams, splice clips excluded | train | OK |
| Rate-model prior c0 | train GOPs | train | OK |
| Rule tuning (margin, qpd, cw), L 0 and L 2 | v1 8-GOP streams | **val** | OK (already has the same 2-GOP lookahead as RL; grid widened twice) |
| Pavneet results (D34 main, D35 encoder RC, fresh films) | v1 streams / ED + ToS segments | test | evaluation only; **ED and ToS are v1 test clips (ed_s*, tos_s*)**, so the "fresh" films are not outside v1 |
| Sara rule LOFO retuning at 16 / 32 GOPs | ED / ToS segments (tune one film, test the other) | **test** | **FLAG: tuned on test clips** -> not usable; retune on val |
| Sara rule margin 0.96 ("equal reliability") | picked to match RL's over-rate on v1 **test** streams | **test** | **FLAG: chosen on test** -> not usable |
| Sara PID target 5 %, Kp 2, Ki 0.05 | defaults stated a priori; the 2 / 5 / 10 % sweep was read on test | train (training) / test (reading) | defaults OK; any target choice from the sweep is test-tuned. No checkpoints anyway |

## Feasibility issues for the Exp 7 plan

1. **No 16- or 32-GOP same-clip streams on val (or train).** Every v1 clip has <= 15 GOPs (val: 10). Long
   same-source streams exist only by chaining consecutive clips of one source: val has one such group (`sita`,
   6 clips, 60 GOPs); train has two (bbb, sintel). Retuning the rule "at 16 and 32 GOPs on val" therefore means
   either (a) val same-source chains = one group (sita) only, (b) val mixed (spliced) 16 / 32-GOP streams, or
   (c) train chains (bbb, sintel; legitimate for a rule, not val). Test-side long streams are ED / ToS segments.
2. **Sara's PID-Lag** needs retraining (no checkpoints) before it can be a candidate; its stored test numbers
   cannot be reproduced on val (no val numbers stored).
3. **Pavneet's rule already has the 2-GOP lookahead and was tuned on val, but its optimum is NOT interior.**
   rule_wide.pkl best (margin, qpd, cw): x264 L0 and L2 (0.98, 4.5, 3.0), x265 L0 (0.98, 4.0, 3.0), x265 L2
   (0.98, 4.5, 6.0); qpd grid 2.5-4.5, so qpd sits on the grid's upper edge for x264 (both L) and x265 L2.
   Part 1a: widen qpd (and re-check margin 0.96-1.00, cw 1-12) until the optimum is interior, on val.
4. Step 1 reproduction is possible: eval.pkl stores val rows (1704 per policy) for all 24 policies per encoder, and baselines.pkl /
   rule_wide.pkl the rule's val rows. Table lookups only (no encodes).
