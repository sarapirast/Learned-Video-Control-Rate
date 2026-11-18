# 01 · Shim vs x264 CLI check (2026-11-16)

**Question:** does rclib's env give *exactly* the same results when its encodes go through the P1 shim
(`RC_BACKEND=shim`, one open encoder per episode, only the newest frame encoded) instead of the x264 command line
(the whole prefix re-encoded at every step)? And how much faster is it?

## What was run
- 10 val GOPs (5 stable, 5 cut, one per clip, picked by `shim_vs_cli_check.py`) × 4 budget levels = 40 episodes.
- final4 (offset 0 every frame, k5) and R3 (k5, seed 3, Aayush's `model_180993.zip`), each with both backends.
- x264, Aayush's `x264_resh` infos/GOPs, `RC_METRIC=dpsnr`, the env arguments of `p2_data/exp_next/final/eval_r3.py`.

## How to rerun (on a compute node, a few minutes)
```bash
bash run_shim_vs_cli_check.sh shim final4 --pixels   # also checks rclib's GOP .yuv against the clip y4m
bash run_shim_vs_cli_check.sh cli  final4
bash run_shim_vs_cli_check.sh shim r3
bash run_shim_vs_cli_check.sh cli  r3
```
Then compare `rows_<method>_cli.pkl` with `rows_<method>_shim.pkl` (per-frame `qps`, `bits`, `res["psnr"]`, `score`).
Outputs: `/scratch1/ahhanagu/ee599/shimcheck/` (outside git).

## Checks that passed
| Check | final4 | R3 |
|---|---|---|
| Input pixels: rclib's `.yuv` vs the clip read with P1's `read_y4m` | 10/10 GOPs identical | 10/10 |
| Shim vs CLI: per-frame QPs, bits, PSNR, score | **40/40 exactly equal** | **40/40** |
| Shim vs Aayush's stored results (with `RC_METRIC=dpsnr`) | total bits and score 40/40 | QPs and score 40/40 |

## Results (final, not affected by later scoring changes)
| Method | CLI | Shim | Speed-up |
|---|---|---|---|
| final4 | 0.39 episodes/s | 5.15 episodes/s | **13.2×** |
| R3 | 0.38 episodes/s | 4.67 episodes/s | **12.2×** |

One core, same 40 episodes. Training R3 (180k steps) dropped from ~33 min to ~4 min per run.

## Lessons
- rclib's `res` arm scores with the old "% bits saved" metric unless `RC_METRIC=dpsnr` is set (bits and actions are
  unaffected, only the score).
- The shim's own `slice_bits` include Annex-B start codes; rclib's do not. The adapter therefore counts bits with
  rclib's own `frame_bits()` on the shim's bitstream.
