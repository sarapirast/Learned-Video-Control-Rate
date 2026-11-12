# Study plan

**Question.** How much does seeing the future help per-frame QP rate control under a per-GOP bit budget? How should
an RL rate controller use lookahead, which RL approach and which features work best, and can scene knowledge (where
the cuts are, what a scene costs) replace or steer lookahead? Everything runs in two real encoders, x265 and x264.

Everything below is measured on real encodes (bits from the bitstream, PSNR from decoding the output).
Model, threshold and k choices are made on **validation** only; **test** is touched once per method.

## Setting (shared by every study)

| Item | Value |
|---|---|
| Episode | one GOP: 30 frames, IDR + 29 P, 320x180, no B-frames, AQ and cutree/mb-tree off |
| Action | per-frame QP offset in {−3..+3} on base QP + STATIC (−6 I, −3 P1–9, +3 P10–29) |
| Budget | bits of the encoder's own constant-QP mode on that GOP at QP 30 or QP 38 |
| Score | % bits saved at equal PSNR vs the encoder's own constant-QP curve (QP 18–50, log-bits interpolation); penalised score subtracts 2 points per 1 % over budget; % GOPs over budget is always reported next to it |
| Teacher / ceiling | hindsight hill-climb, 300 encodes × 2 seeds per GOP and budget (best-so-far curve logged) |
| Data | Xiph CIF/720p/1080p, 5 Blender films, YouTube UGC 360P (13 categories), spliced GOPs with known cuts; split by source |

## Phase A — data and per-GOP information (`experiments/prep.py`, `experiments/infos.py`)
Manifest, GOP files, the constant-QP curve (33 encodes per GOP), first-pass bits, pixel features (spatial and temporal
complexity), scene analysis (cuts, flashes, fades, per-scene complexity). Sharded over GOPs as a job array.

## Phase B — baselines (`experiments/baselines.py`)
Constant QP; STATIC; best fixed pattern fitted on training data (`static_pattern`); the encoder's own rate control
(single-pass ABR, 2-pass, ABR+VBV; each with and without AQ + cutree/mb-tree); a causal feedback rule (gain tuned on
validation); a scene-aware rule (bits allocated per detected scene by first-pass complexity).

## Phase C — hindsight search (`experiments/search.py`)
Teacher plans for train, ceiling for val/test. Logs every evaluated plan for offline RL and the best-so-far curve
(does the search converge by 300 encodes?).

## Phase D — the lookahead curve (core result)
CQL on logged search plans → PPO fine-tune with relative reward (vs STATIC), 3 seeds, for
**k = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 29 (= full GOP)**. Reported: penalised saving, % over budget, share of the
search's gain captured at each k, paired CIs between neighbouring k.

## Phase E — RL approaches (at k = 0, 5, 10)
| Family | Methods |
|---|---|
| Imitation | BC on search-best plans |
| Offline RL | CQL, IQL (discrete) |
| Offline → online | BC→PPO, CQL→PPO (core recipe) |
| Online from scratch | PPO, A2C, DQN |
| Constrained | Lagrangian PPO (fixed multiplier), PID-Lagrangian PPO (budget as a constraint, not a penalty) |
| Model-based | MPC: learned per-frame bits/PSNR model + receding-horizon plan over the lookahead window |
| Gate | GOP-level switch between rule and RL (`switch`) |

## Phase F — feature ablations (at k = 5, CQL→PPO)
Groups: budget state (always on), history (last bits/QP, bits vs estimate), first-pass bits, pixel complexity (spatial,
temporal), scene features (cut flags, distance to cut, scene id, scene cost share), GOP-level difficulty (budget vs
first-pass cost). Leave-one-group-out and add-one-group-in, 3 seeds each.

## Phase G — scene intelligence and dynamic lookahead
1. **Scene detector** quality on spliced GOPs (ground-truth cuts): histogram, SAD and first-pass-bits detectors and a
   combined adaptive-threshold detector; flash and fade handling.
2. **Scene-aware lookahead modes** (one "any-k" policy trained with random masking of the window, so all modes share
   one network, plus dedicated policies for the best modes):
   - fixed k (reference)
   - *scene-truncated*: the window stops at the next cut (no information from the next scene)
   - *scene-extended*: the window always reaches the next cut (k varies per frame)
   - *cut-triggered*: k = 0 inside a stable scene, full window when a cut is within K frames
   - *learned per-GOP k*: a classifier on cheap GOP features picks k ∈ {0, 2, 5, 10, 29} (trained on validation
     outcomes of the fixed-k policies, evaluated on test)
   - *cost-adaptive*: k grows with predicted complexity variance in the window
3. **Scene budget prior**: per-scene bit plan from first-pass costs, given to the policy as a feature (the policy then
   only corrects the prior).
4. **Cut specialist** (`cutspec`): a separate policy for GOPs containing a cut, routed by the detector.
Each mode reports penalised saving vs average frames looked at (the cost of lookahead).

## Phase H — side studies (runbook)
`static_pattern`, `overshoot` (where and why GOPs go over budget), `switch`, `lagr`, `cutspec`, the encoder's own RC.

## Phase I — two encoders (`experiments/codecs.py`)
Same pipeline in x264. Side-by-side report: saving vs own CQP and vs x265 CQP (common yardstick), paired CIs for
RL k=5 vs best own RC, search vs RL, RL gain x264 vs x265, codec gap.

## Execution
Encode-heavy stages (infos, search, evaluation) run as SLURM job arrays sharded by GOP; every RL run (method × k ×
seed × encoder) is its own small job. Each stage writes `.pkl` per shard and is resumable. Order: `--quick` on
`debug`, then full.
