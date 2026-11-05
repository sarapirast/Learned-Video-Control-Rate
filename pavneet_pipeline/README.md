# Learned per-frame QP rate control for x265 and x264: what a frame of lookahead buys

EE599 project. We study reinforcement learning for **per-frame QP rate control** inside real encoders:

- **Encoders:** x265 4.1 (HEVC) and x264 0.165 (H.264).
- **Budget:** a per-GOP bit budget.
- **Ceiling:** an offline hindsight search that tries about 300 real encodes per GOP and picks the best plan.

The central question: how much of the search's gain can a policy capture in a **single** encode, and how does that
change with the number of future frames it can see? We vary the lookahead `k` from 0 (strictly causal) to 29 (the
whole GOP).

The write-up is in [`paper/paper.pdf`](paper/paper.pdf). The tables behind every number are the markdown reports in
[`results/x265/`](results/x265) and [`results/x264/`](results/x264).

## Setting

| Item | Value |
|---|---|
| Episode | one GOP: 30 frames (IDR + 29 P), 320x180, preset fast, AQ and cutree/mb-tree off |
| Action | per-frame QP offset in −3..+3 on base QP b ∈ {30, 38}, applied on top of a fixed pattern STATIC (−6 on I, −3 on P1–9, +3 on P10–29) |
| Budget | bits the encoder's own constant-QP mode spends on that GOP at QP b |
| Score | % bits saved at equal PSNR vs the encoder's constant-QP curve (QP 18–50), minus 2 points per 1 % over budget |
| Ceiling / teacher | hindsight hill-climb search: 300 real encodes × 2 seeds per GOP and budget; its logs are the offline RL data |
| Data | Xiph (CIF/720p/1080p), Blender open films, YouTube UGC 360P, and spliced GOPs with known scene cuts; split by source into train/val/test |
| Learners | BC, CQL, IQL, CQL→PPO (core recipe), BC→PPO, PPO, A2C, DQN, Lagrangian and PID-Lagrangian PPO, MPC (learned model + CEM), ensembles, a GOP-level gate, model-based pre-training |
| Statistics | 3 seeds per configuration; 95 % paired bootstrap CIs over test (GOP, budget) cases |

Every bit count comes from the real bitstream, and every PSNR from decoding the real output with ffmpeg.

## Repository layout

```
rclib/          core library (imported by every script)
experiments/    one script per study phase; each caches its stages and writes a markdown report
tools/          environment, data download, SLURM job scripts, chain submission, checks
runs/           RL run lists: one line of experiments/rl.py (or clip_rl.py) arguments per array task
results/        generated markdown reports per encoder (no large data or models)
paper/          paper source, figure script, figures, compiled PDF
docs/           study plan, design decisions, journal, learnings, job log
REPRODUCE_HPC.md   the original runbook this rebuild started from (written for an older laptop code layout; kept for reference)
```

### `rclib/`: library

| File | What it does |
|---|---|
| `config.py` | Global settings and environment variables (`RC_CODEC`, `RC_WORK`, `RC_WORKERS`, `RC_ENVS`, `RC_TMP`), QP range, budgets, action set |
| `codec.py` | Encoder harness for x265/x264. Forces per-frame QPs, runs the encoders' own rate control, counts real bits from the bitstream, decodes with ffmpeg for PSNR |
| `data.py` | Clips, 30-frame GOP windows, train/val/test split by source, spliced GOPs, raw per-GOP file cache |
| `features.py` | Per-frame analysis computed only from the source: pixel complexity, first-pass bits, scene cuts/flashes/fades |
| `metrics.py` | Score: bits saved at equal PSNR vs the constant-QP curve, plus the over-budget penalty |
| `search.py` | Hindsight hill-climb over the 30 per-frame offsets (teacher and ceiling); logs every evaluated plan |
| `env.py` | Gymnasium env: one GOP per episode, one prefix encode per step, strict k-frame lookahead, several lookahead modes, feature-group ablation switches |
| `offrl.py` | Offline datasets from the search logs; BC, CQL, IQL (discrete, γ = 1) |
| `policies.py` | Every controller as `act(env, obs)`: STATIC, rules, lookahead rule, scene rule, SB3/torch policies, MPC. Includes a parallel evaluator |
| `mpc.py` | Learned per-frame bits/PSNR MLP plus receding-horizon CEM planner |
| `mbenv.py` | `ModelEnv`: the RL env with the encoder replaced by the learned model (model-based pre-training, D26) |
| `clipenv.py` | Multi-GOP env: 8 GOPs under one shared budget, outcomes from real constant-QP curves (D25) |
| `runner.py` | Shared CLI flags, job-array sharding, process pools, per-stage `.pkl` caches |

### `experiments/`: study scripts

| Script | Phase | What it does |
|---|---|---|
| `infos.py` | A | Per-GOP information: the constant-QP curve (33 encodes), budgets, first-pass encode, features, scene analysis, STATIC encodes |
| `scenes.py` | G.1 | Fits the scene-cut detector on spliced GOPs and applies it to every GOP (`--stage apply` must run before rules/RL). Also analyses the teacher's behaviour around cuts |
| `search.py` | C | Hindsight search on train (full logs = offline data), val and test (ceilings) |
| `baselines.py` | B | Encoders' own rate control (ABR, 2-pass, ABR+VBV, ± AQ), fixed-pattern refit, hand-designed rules tuned on val |
| `rl.py` | D–G, K | One RL run = (method, k, lookahead mode, dropped features, seed). All learners listed in its docstring |
| `analysis.py` | – | Aggregates RL runs into the lookahead, methods, features, scene, overshoot and headline (`expand2`) reports |
| `reports.py` | – | Writes every report for the current encoder; skips reports whose inputs are missing |
| `breakdown.py` | J | Per-method breakdowns by GOP type (cut/stable/fade), clipped saving, where the policy wins and loses |
| `codecs.py` | I | x265 and x264 side by side, scored against own and common (x265) constant-QP curves |
| `constraint.py` | K #1 | Imitation vs offline RL vs Lagrangian/PID RL on budget reliability |
| `clip_rl.py` | K #2 | Multi-GOP shared-budget RL (BC, PPO, BC→PPO) plus hand rule / constant-QP / hindsight baselines |

### `tools/`: environment and jobs

| File | What it does |
|---|---|
| `job_env.sh` | Sourced by every job: `module purge`, gcc, conda/codec prefixes on PATH, thread limits, temp dirs |
| `fetch_data.sh` / `fetch.sbatch` | Download all public test video and convert to 320x180 y4m in `$RC_WORK/clips` (~40 GB transferred, resumable) |
| `codec_check.py` | Verifies the harness: forced QPs obeyed, bit counting, prefix property, determinism, PSNR. All lines must say PASS |
| `make_runs.py` | Writes `runs/{core,methods,features,scenes}.txt` |
| `step.sbatch` | Generic job: one Python stage, optionally as a sharded array |
| `rl_batch.sbatch` | Array job: task *i* runs `rl.py` with line *i* of a run list |
| `submit_chain.sh` | Submits one encoder's whole pipeline with SLURM dependencies (infos → scenes → search → baselines → RL → reports) |
| `status.sh` | Shows the job queue, finished stage files and RL runs per encoder |

## How to run it, in order

Everything is resumable. Each stage caches its output as `.pkl` under `$RC_WORK/results_<name>/` and is skipped on
the next run, so a failed or timed-out job is simply resubmitted. Every script has a `--quick` mode that runs in
minutes; use it first. The pipeline runs **once per encoder**, each in its own work directory.

> **Before running elsewhere:** these paths are hard-coded for our cluster. Change them first:
> - the SLURM account `rashidin_1753` and the `/scratch1/pbanga/...` paths in `tools/*.sbatch`, `tools/job_env.sh`, `tools/submit_chain.sh` and `tools/status.sh`;
> - the defaults in `experiments/codecs.py`.

### 0. Software (once)

- Conda env with Python 3.12, ffmpeg, numpy/scipy/pandas, matplotlib, torch 2.15 (CPU), stable-baselines3 2.9.2,
  sb3-contrib and gymnasium 1.4.0.
- Build **x265 4.1** and **x264 0.165** from source into a separate prefix placed first on `PATH`. conda-forge's
  ffmpeg ships older x265/x264 binaries.
- x265 4.1 needs CMake 3.x, not 4.x.
- Set both prefixes in `tools/job_env.sh`.

### 1. Data (once, shared by both encoders)

```bash
RC_WORK=/scratch1/$USER/rcwork sbatch tools/fetch.sbatch all     # Xiph, Blender films, YouTube UGC -> $RC_WORK/clips
python tools/codec_check.py                                      # inside a debug allocation; must be all PASS
```

The x264 work directory links to the same clips.

### 2. Run lists

```bash
python tools/make_runs.py          # runs/core.txt (k sweep), methods.txt, features.txt, scenes.txt
```

The other lists in `runs/` were written by hand for later rounds: `fix_dqn_mpc`, `mpc_margin`, `extend`, `mb`,
`mb_ppo` and `clip`.

### 3. Main pipeline per encoder (phases A–G)

```bash
bash tools/submit_chain.sh x265
bash tools/submit_chain.sh x264
```

This submits the following chain:

1. `infos.py`, sharded, then gathered.
2. `scenes.py --stage fit`, then `--stage apply`.
3. `search.py` for train/val/test, sharded, then gathered.
4. `baselines.py`: own_rc, static_pattern, rules. Also `scenes.py --stage teacher`.
5. RL arrays over `runs/core|methods|features|scenes.txt`.
6. `reports.py`.

The same steps can be run by hand in that order, with `--stage gather` after each sharded stage.

### 4. Follow-up RL rounds (per encoder)

Each list is submitted as an array with `tools/rl_batch.sbatch`:

```bash
RC_CODEC=x265 RC_WORK=/scratch1/$USER/rcwork \
  sbatch --export=ALL --partition=main --cpus-per-task=20 --mem=60G --time=12:00:00 \
         --array=0-$(( $(wc -l < runs/extend.txt) - 1 )) --job-name=x265_rl_extend tools/rl_batch.sbatch runs/extend.txt
```

| Order | Run list | What it adds |
|---|---|---|
| a | `runs/fix_dqn_mpc.txt` | DQN and MPC with corrected settings (D20, D21) |
| b | `runs/mpc_margin.txt` | MPC with a wider budget-margin sweep |
| c | `runs/extend.txt` | ensembles, gate, extra features (fb/sum), Lagrangian/PID fine-tunes (D23) |
| d | `runs/mb.txt`, then `runs/mb_ppo.txt` | model-based pre-training, then real-encode fine-tuning (D26). `mb` needs the MPC model from (b) |

Then run:

```bash
python experiments/breakdown.py && python experiments/reports.py     # per encoder (RC_CODEC / RC_WORK set)
```

### 5. Cross-encoder comparison and Phase K analyses

```bash
python experiments/codecs.py --x265 <x265 work dir> --x264 <x264 work dir>   # results/x265/codecs_report.md
python experiments/constraint.py                                             # per encoder: constraint_report.md
```

Multi-GOP RL needs no encodes, only the infos from step 3:

```bash
RC_CODEC=x265 RC_WORK=... sbatch --export=ALL --partition=main --cpus-per-task=4 --mem=16G --time=2:00:00 \
     --array=0-17 --job-name=x265_clip tools/step.sbatch experiments/clip_rl.py --list runs/clip.txt
python experiments/clip_rl.py --report                                        # clip_report.md
```

### 6. Paper

```bash
python paper/make_figs.py          # figures from the markdown reports -> paper/figs/
cd paper && pdflatex paper.tex && pdflatex paper.tex
```

## Reports and where each result comes from

| Report (`results/<codec>/`) | Content |
|---|---|
| `infos_report.md`, `scenes_report.md`, `search_report.md` | Data, scene detector, search ceiling and convergence |
| `baselines_report.md` | Encoders' own rate control and hand rules |
| `lookahead_report.md`, `expand2_report.md` | **Core result:** score and share of search gain vs lookahead k |
| `methods_report.md` | RL approaches compared at k = 0, 5, 10 |
| `features_report.md`, `scene_report.md` | Feature ablations; scene-aware lookahead modes |
| `overshoot_report.md`, `breakdown_report.md` | Over-budget analysis; per-method breakdowns by GOP type |
| `constraint_report.md` | Constrained RL vs imitation on budget reliability |
| `clip_report.md` | Multi-GOP shared-budget RL |
| `codecs_report.md` (x265 folder) | x265 vs x264 side by side |

Design choices and their reasons are numbered D1–D27 in [`docs/DECISIONS.md`](docs/DECISIONS.md). Problems found
along the way are in [`docs/LEARNINGS.md`](docs/LEARNINGS.md).

## Status

- Model-based pre-training (`mb`/`mb_ppo`, D26) is not finished. The first attempt diverged, and guards have since
  been added to `rclib/mbenv.py`.
- Every other result in the paper is final.
