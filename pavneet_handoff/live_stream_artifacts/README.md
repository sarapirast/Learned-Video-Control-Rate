# Live-stream rate control (D38–D43): data, models and results for replication

Everything needed to re-run or re-check the live-stream experiments described in
`../repo/docs/LIVE_STREAM_WRITEUP.md` (plain summary: `../repo/docs/LIVE_STREAM_FINDING_SIMPLE.md`). Code is in
`../repo/` (`rclib/bufenv.py`, `experiments/buffer_rl.py`, `buffer_rl2.py`, `buffer_rl3.py`, `buffer_oracle.py`,
`buffer_real.py`); the experiment log is `../repo/docs/JOURNAL.md` and `DECISIONS.md` (D38–D43).

## What is here

| Path | What it is |
|---|---|
| `data/v1/budgets.csv` | Dataset v1 clip-level bit budgets (Aayush Soni's dataset v1, shared with his agreement). Already folded into the GOP tables below; needed only to rebuild them (`../repo/experiments/v1_prep.py`). |
| `data/traces/belgium4g/throughput.pkl` | The 4G/LTE channel traces: `{"<mode>_<k>": bits/s per ~1 s}`, 40 logs, 18,036 s. Throughput only (GPS dropped). See "LTE traces" below. |
| `<codec>/results_yrd/frames.pkl` | Per-GOP, per-frame constant-QP bits and luma MSE (QP 18–50) of the v1 GOPs, derived from dataset v1's `rd_frames.parquet`. This is the "curve" every lookup uses. |
| `<codec>/results_buffer/` | Default setting (AR(1) channel ρ 0.8 σ 0.3, 1 s latency cap, 0.5 dB per % stalled). |
| `<codec>/results_buffer_trace/` | Same, on the LTE traces. |
| `<codec>/results_buffer_{sig0.15,sig0.5,cap0.5,cap2,lam0.25,lam1}/` | D39 one-at-a-time sweep (channel volatility, latency cap, stall weight). |
| `<codec>/results_buffer_ladder/`, `results_buffer_trace_ladder/` | D45 leak-fixed setting (`RC_BUF_LADDER=1`): budget and mean channel rate from a fixed bitrate ladder, AR(1) and LTE. vbv2 / mpc, ppo_v2 and il / il_ppo (3 seeds). |

Inside each `results_buffer*` folder:

| File | What it is |
|---|---|
| `baselines.pkl`, `baselines2.pkl`, `baselines2_wide.pkl` | Tuned hand rules (rule / vbv, then vbv2 / mpc; `_wide` = the 11-17 retune on wider grids): tuned parameters, val grid, and per-case rows on val / test / test16 |
| `<method>_L<L>_s<seed>/eval.pkl` | Per-case evaluation rows (score, dPSNR, budget use, stall %) on val, test (n = 8) and test16 (n = 16) |
| `<method>_L<L>_s<seed>/model.zip` | Trained policy (stable-baselines3 PPO), where saved. D42 runs (`il_*`, `ppo_mix*`, `ppo_wide`) did not save models; `il_ppo_rr` (D43) is a re-run of `il_ppo` seed 0 with its model. |
| `fresh.pkl` | D39 fresh-film evaluation (default setting) |
| `oracle/` | D41 hindsight oracle, per-case results by shard |
| `real/` | D40 / D43 real-encoder runs by shard (x265 / x264 actually encoding and decoding) |

Method names: `vbv2` (tuned hand rule), `mpc` (model-predictive rule), `ppo` (D38), `ppo_v2` (D39, RL on vbv2),
`il` / `il_ppo` (D42, oracle imitation, then PPO), `il_w*`, `ppo_wide`, `ppo_mix`, `ppo_mixh` (D42 variants),
`ppo_pc`, `il_pc`, `ppo_pred`, `il_ppo_rr` (D43). Not included: PPO training curves (`train_curve.npy`, 370 MB),
debug / quick runs. Raw video: see `VIDEO.md` (GitHub Release `pavneet-live-stream-video`).

## Also needed (already in this repo)

`../artifacts/<codec>/v1/results_infos/infos_slim.pkl` (v1 GOP tables, splits, budgets) and, for the fresh-film
check only, `../artifacts/<codec>/fresh/results_infos/infos_slim.pkl`.

## Setup

Software used: Python 3.12, numpy 2.5, pandas 3.1, torch 2.15 (CPU), stable-baselines3 2.9.2, gymnasium 1.4,
scikit-learn 1.9, scipy 1.18; x265 4.1 and x264 0.165 (only for the real-encoder check, D40). Runs were on the USC
CARC cluster with SLURM; the `.sbatch` / `submit_*.sh` scripts in `../repo/tools/` hard-code paths and the account
(`/scratch1/pbanga/...`, `rashidin_1753`), so change those (and `../repo/tools/job_env.sh`) before using them.

Lay out one work directory per encoder (`RC_WORK`), which is what the code reads:

```bash
W=/path/to/rcwork_v1/x265                       # repeat for x264
mkdir -p $W
cp -r ../artifacts/x265/v1/results_infos $W/
cp -r live_stream_artifacts/x265/results_* $W/  # results_yrd (curves) + all results_buffer* (results, models)
export RC_V1=1 RC_PRESET=medium RC_CODEC=x265 RC_WORK=$W
export RC_BUF_TRACES=/path/to/live_stream_artifacts/data/traces/belgium4g/throughput.pkl
export RC_FRESHWORK=/path/to/fresh/x265         # holding ../artifacts/x265/fresh/results_infos (fresh films only)
cd ../repo
```

With `results_yrd/frames.pkl` present the code never reads the original `rd_frames.parquet`. To rebuild it, delete
it and point `RC_V1_RD` at dataset v1's `rd_frames.parquet` (`RC_V1_BUDGETS` at `budgets.csv` for `v1_prep.py`).

## Re-checking the reported numbers (no training)

Reports are rebuilt from the shipped `eval.pkl` / `baselines*.pkl` / oracle / real files:

```bash
python experiments/buffer_rl.py --report                            # D38/D39 tables  -> results/v1_buffer/<codec>/buffer_report.md
RC_BUF_CHANNEL=trace python experiments/buffer_rl.py --report       # LTE             -> results/v1_buffer/<codec>/trace/
python experiments/buffer_oracle.py --report                        # D41 oracle, gap closed
python experiments/buffer_real.py --report                          # D40 / D43 real encoder
RC_BUF_SIGMA=0.5 python experiments/buffer_rl.py --report           # a sweep setting (also RC_BUF_CAP, RC_BUF_LAM)
```

A trained policy can be re-evaluated on the exact test cases (they are fixed by hash) by loading its `model.zip`
with `stable_baselines3.PPO.load` and running `experiments.buffer_rl.evaluate` on `experiments.buffer_rl.case_sets()`
(as `experiments/buffer_real.py --model <name>` does). Scores match `eval.pkl` to 0 (checked on all 48 D43 shards).

## Re-running from scratch (order of the experiments)

Each step's script header says what it runs; run lists are in `../repo/runs/`. All are curve lookups (no encoding)
except D40 / D43-real.

| Step | Script | What it does | Approx. cost per encoder |
|---|---|---|---|
| D38 | `tools/submit_buffer.sh` | tune rule / vbv on val, PPO (L = 0, 2) × 3 seeds | baselines ~5 min; 6 PPO runs × ~15 min |
| D39 | `tools/submit_buffer_sweep.sh` | tune vbv2 / mpc for 8 settings, ppo_v2 × 3 seeds × 8, fresh films | 8 tuning tasks × 20–30 min; 24 PPO runs × ~15 min |
| D40 | `tools/submit_buffer_real.sh` | real-encoder check (needs v1 GOP video and x265 / x264) | 44 shards × 10–35 min |
| D41 | `tools/submit_buffer_oracle.sh` | hindsight oracle | 16 shards, each under 1 h |
| D42 | `tools/submit_buffer_rl2.sh` | il / il_ppo, ppo_mix, ppo_mixh, ppo_wide × 3 seeds | 24 runs × 13–17 min |
| D43 | `tools/submit_buffer_rl3.sh` | ppo_pc, il_pc, ppo_pred × 3 seeds, il_rr; real-encoder check of il_ppo_rr | 20 × ~20 min + 24 × 10–30 min |

PPO runs on 2 CPUs; GPUs are not used. Seeds are fixed, but PyTorch on different hardware may not reproduce runs
bit for bit; compare at the level of the paired confidence intervals in the reports.

The real-encoder steps (D40, D43 real) also need dataset v1's video (`rclib/data.py`, `gop_path`). The
redistributable clips are in the GitHub Release `pavneet-live-stream-video`; the rest are rebuilt from their
sources. See `VIDEO.md`.

## LTE traces

From J. van der Hooft, S. Petrangeli, T. Wauters, R. Huysegems, P. Rondao Alface, T. Bostoen and F. De Turck,
"HTTP/2-Based Adaptive Streaming of HEVC Video Over 4G/LTE Networks", *IEEE Communications Letters* 20(11), 2016.
Logs: https://users.ugent.be/~jvdrhoof/dataset-4g/. Please cite that paper if you use them. `throughput.pkl` keeps
only the per-second throughput (bits/s = bytes × 8 × 1000 / interval ms). To rebuild it from the authors' download:

```bash
python ../repo/tools/prep_belgium4g.py logs_all.zip throughput.pkl  # reproduces the shipped file (max diff 1e-8)
```

Split by file name hash (`rclib/bufenv.py`, `trace_split`): 19 train / 10 val / 11 test logs. Each per-case channel
is a window of one log, normalised to mean 1 (floor 0.05).
