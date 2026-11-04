# Experiments log (P2 workspace, EE599 RL rate control)

One place for every experiment run so far, with a short summary of findings and where the code and results are, plus
the experiments still pending. Day-to-day status and job IDs are in `docs/p2-tracker.md`; this file is the summary.
Update it whenever an experiment finishes or a new one is planned.

Conventions:
- **Paths:** relative to `/scratch1/aayushso/ee599` unless absolute.
- **Data:** data v1 at 320x180, 30-frame GOPs (IDR + 29 P), frozen 2026-11-03.
- **Score:** "score" = % bits saved at equal PSNR vs the GOP's own constant-QP curve, minus 2 points per 1% over
  budget. 0 = as efficient as the best constant QP in hindsight. This is Pavneet's metric (`rclib/metrics.py`).
- **"orig" / "dec":** Pavneet's budget (the GOP's own constant-QP spend; it leaks the GOP's cost) / that budget
  times a random factor of 0.8-1.25.
- **"Leak-free budgets":** `data/v1/320x180/budgets.csv` (clip-level, 4 levels).
- **k:** lookahead in frames.

---

## Done

### Data and settings

| Date | Experiment | Where | TL;DR |
|---|---|---|---|
| 10-29 to 11-02 | **Data v1**: 109 clips, 1,042 GOPs, splits by source group, cut labels (two detectors + manual review), SI/TI, 6 spliced clips (train only), 15 high-frame-rate clips decimated | `docs/data-v1-README.md`, `docs/clip-selection.md`, `scripts/` | Split 625 / 152 / 265 GOPs (66 / 16 / 27 clips). Test has 49 cut + 5 gradual GOPs. A second reviewer agreed with 89/110 cut verdicts exactly (100/110 on cut vs not-cut). |
| 11-03 | **Forced-QP check** on x264 (is every per-frame QP in a qpfile obeyed?) | `scripts/x264_forced_qp_check.sh` | Plain `--qp` + qpfile clamps 24/30 frames to ±3. `--crf` + qpfile (Pavneet) and `--qp 31 --ipratio 10 --pbratio 10` (Ahhana) obey 30/30, so Pavneet's x264 results are valid. The two methods differ by ≤0.3% in bits. x265 `--qp` + qpfile obeys 30/30 (checked 11-04). |
| 11-04 | **Constant-QP curves QP 18-50 + first-pass bits**, both encoders, P1's frozen settings | `scripts/rd_native.py`, `scripts/rd_summary.py`; `data/v1/320x180/rd/`, `features/fp_bits.parquet`; `docs/rd-native-summary.md` | Monotonic apart from ≤108 of 33,344 QP steps. x265 needs 5-12% fewer bits than x264 at equal PSNR. P1's settings use about 5% (x264) / 7-13% (x265) fewer bits than Pavneet's settings at equal QP. First pass at QP 32 tracks real bits slightly better than QP 30. |
| 11-04 | **Leak-free budget table + causal base-QP estimator** | `scripts/budgets_v1.py`; `data/v1/320x180/budgets.csv`; `docs/budget-estimator-v1.md` | Budget / own spend: median 1.02, range 0.66-2.1 (10th-90th percentile). Estimator val error 3.6-4.0 QP at k=0, 2.2-2.7 at k ≥ 2, so most of the gain comes from seeing the first P frames. At level 24, 10% of GOPs need QP < 18. |
| 11-04 | **Richer first-pass statistics** (x264/x265 `--pass 1 --stats`: tex/mv/misc bits, intra/inter/skip blocks) + **gate test** | `scripts/fp_stats.py`, `scripts/fp_stats_gate.py`; `features/fp_stats.parquet`; `docs/fp-stats-gate.md` | They improve prediction of a frame's own bits (median error 27% -> 21% x264, 22% -> 18% x265). No gain for GOP-level cost from frames 0-1, or for the base QP at k=0/2. The k=0 problem is missing future information, not features. |

### Pavneet's pipeline on data v1 (repo `repo-pavneet/`, local branch `v1-data`, never pushed)

| Date | Experiment | Where | TL;DR |
|---|---|---|---|
| 11-03 | **Review of Pavneet's code and paper** | `docs/review-paper-draft-2026-11-03.md`, `docs/msg-pavneet-2026-11-03.md` | **C1:** the budget leaks the whole GOP's cost. **U1:** the base QP is the oracle QP. **C2:** cut/flash/fade flags look 2-4 frames ahead. STATIC is x265-tuned. The test set is mostly spliced cuts. |
| 11-03/04 | **v1 rerun**, both encoders × both budget arms; BC, CQL->PPO, Lagrangian PPO at k = 0/2/5/10/29, 3 seeds (about 1,400 CPU-h) | `jobs/rc_v1_*`, `runs_v1/`; `results_v1/<codec>_<arm>/`, `results_v1/v1_headline.md` (`scripts/v1_headline.py`) | Lagrangian PPO is best: 4.67 (x264) / 4.12 (x265) at k=0, 66-75% of the search's gain, 3% over budget. Lookahead adds at most about +0.6 to it. Search: 9.09 / 9.62. Encoders' own ABR+VBV: about -28, over budget on 85-93% of GOPs. |
| 11-04 | **Budget-leak test** (orig vs dec arm) | `results_v1/{x264,x265}_arm_compare.md` (`scripts/v1_arm_compare.py`) | The decoupled budget lowers the k=0 scores (Lagrangian 4.67 -> 3.37 x264, 4.12 -> 3.45 x265; BC drops 2.8-3.6), so the leak inflates the "causal" results. Only a partial test: the budget still tracks the GOP's cost to about ±12%. |
| 11-04 | **Overshoot size** | `results_v1/v1_overshoot.md` (`scripts/v1_overshoot.py`) | BC and CQL->PPO go over on 14-37% of episodes (median 1-6% over, worst 48-61%). They save MORE than Lagrangian before the penalty; most of their lookahead gain is a smaller penalty. Cut GOPs go over 1.4-3.5× as often. |
| 11-04 | **RL model review** | `docs/rl-models-review-2026-11-04.md` | About 18 methods are implemented, 3 run. The action range ±3 is too narrow (search plans at the limit on 26-30% of frames). PPO is unstable (peaks mid-training). Proposals A-E are listed there. |
| 11-04 | **A: budget shield** at inference (raise QP when the predicted spend exceeds the budget) | `repo-pavneet` `rclib/policies.py` (Shield), `tools/shield_eval.py`; `results_v1/x264_orig_shield_val.md` (`scripts/v1_shield_compare.py`) | **NEGATIVE.** It lowers every method's val score (BC 2.67 -> 2.22, CQL->PPO 2.89 -> 2.25, Lagrangian 3.45 -> 2.71). Early predictions are ±10-20% noisy and the overshoots it prevents are small. Closed; the end-game variant was not run. |

### P2 causal controller (learning-free baseline, leak-free budgets, real encodes)

| Date | Experiment | Where | TL;DR |
|---|---|---|---|
| 11-04 | **Offline prototype** (replays stored constant-QP frames) | `scripts/controller_v1.py` | **INVALID for quality:** a P frame's distortion depends on its reference's QP (artifacts of +70% / -236%). Kept as a record only. |
| 11-04 | **Real-encode controller, tuning v1** | `scripts/controller_real.py`, `jobs/p2_step.sbatch` | Exposed 2 flaws: one odd frame set the whole P estimate (frame 1 at QP 11), and the I frame was starved at k=0 on low-motion GOPs. The scoring chain was checked (forced-QP = plain constant QP within 0.4%). |
| 11-04 | **Controller with safeguards, tuning v2 + final run** (val and test, k = 0/2/5/10/29, 4 levels) | `results_v1/controller_final.md` (`scripts/controller_report.py`); setting `0.97:3:1.0:2:3:4:0:1` | Test score: x264 -3.9 / -2.2 / -0.9 / -1.0 / -2.5; x265 -4.5 / -2.0 / -0.2 / -0.8 / -2.2 (k = 0/2/5/10/29). 2-4.5% of runs over budget, mean 0.1-0.35% over. The start-of-GOP estimate held fixed scores -25 to -103, so online feedback is essential. First clean, leak-free k-curve. |
| 11-04 | **k=29 anomaly diagnosis** | `docs/p2-tracker.md` item 18 | With full lookahead the plan flattens to one QP, ignoring that early and post-cut frames are references. Losses are concentrated in cut (-3.0) and gradual (-6.3) GOPs. Smaller k front-loads by accident. Fix: controller v2. |

### Surveys and explainers

| Date | What | Where | TL;DR |
|---|---|---|---|
| 11-04 | **Literature survey:** how features are extracted for RL / learned control on video | `docs/lit-survey-features-2026-11-04.md` (21 refs) | Encoder RL (MuZero-RC, Mao 2020, DDPG on x265) uses first-pass / encoder statistics + budget state, never pixels. MuZero-RC learns a Transformer embedding over the per-frame statistic sequence (20k videos). Pixel CNNs in codecs are supervised rate-model predictors (about 1-2% BD-rate). Cheapest upgrade: richer first-pass statistics (done). |
| 11-04 | **RL explainer for the team** | `docs/rl-field-guide.html` (also published as a private artifact) | Basics, the methods run, the proposals, how to read the results. |

---

## Pending (roughly in priority order)

| # | Experiment | Why | Needs | Cost |
|---|---|---|---|---|
| P1 | **Controller v2**: QP profile `q + offset[j]` with a spend-early ramp (±a) and a boost (-b) on the first frame after a visible cut; same binary search for q; tune a, b on val; then the final val/test run | Fixes the k=29 anomaly and cut GOPs; shows what lookahead is worth when used sensibly | nothing | about 30 CPU-h |
| P2 | **Reward shaping for RL:** potential-based shaping on predicted overshoot (then optionally a per-frame rate-distortion reward); Lagrangian PPO at k = 0/5, 3 seeds, with vs without | Dense reward without changing the optimum; targets overshoot and instability | team decision (meeting 11-04, decision 6); RL stream | tens of CPU-h |
| P3 | **Residual RL on the causal controller** (proposal D) under the leak-free budgets | The honest version of every learned result (removes C1 + U1) | controller v2; agreement on codebase and action space | ~100+ CPU-h |
| P4 | **λ sweep + PID-Lagrangian with val checkpoint selection** (proposal B) | Turns the method comparison into a savings vs violation-rate curve; fixes the instability | best done on the leak-free setup | ~150 CPU-h |
| P5 | **MPC with the learned rate model** (proposal C, implemented in Pavneet's code, never run on v1) | Lookahead-aware model-based baseline | nothing | ~30 CPU-h |
| P6 | **Richer first-pass statistics in the controller's per-frame rate model** (gradient boosting) | The gate test showed better per-frame prediction | nothing | ~15-20 CPU-h |
| P7 | **Richer first-pass statistics in the RL observation** | The literature's mainstream state; the gate says they help per frame | Sara (P4) agreement on the observation spec | with P3 |
| P8 | **Decision Transformer / attention encoder over the visible frames** (proposal E); a learned embedding over per-frame statistic sequences (as in MuZero-RC) | Uses lookahead structurally | after P3 | new code |
| P9 | **Pixel CNN features** (supervised on the R-D curves, or self-supervised temporal / contrastive, frozen) | Only if the statistics show remaining headroom | gate first (offline prediction test) | deferred |

**Smaller pending items:**
- **Budget levels:** extend the curves below QP 18 (P1's env allows 11) or move the lowest level to 26; team decision.
- **Merge first-pass data:** `fp_bits` / `fp_stats` into `features/frames.parquet`.
- **Shield end-game variant:** acts only in the last 5-10 frames. Not run; low priority.
- **Open decisions** (see `docs/p2-update-2026-11-04-eod.txt`): canonical codebase, encoder settings, first pass at QP 30 vs 32, action space.
