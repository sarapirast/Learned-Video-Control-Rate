# EE599 Learned Video Rate Control: P1 (encoder & env)

An RL agent picks the QP of every frame in x264 so that each 30-frame GOP fits
a bit budget with maximum PSNR. This branch (`p1`) holds the encoder shim and
the Gym environment.

| Path | What it is |
|---|---|
| `env.sh` | CARC modules + conda env; `source` it first |
| `environment.lock.txt` | Exact conda packages (P2's lock + gymnasium) |
| `encoder_shim.c`, `Makefile` | C shim over libx264, built to `build/libx264shim.so` |
| `x264env/encoder.py` | ctypes wrapper (`Encoder`), y4m reader, PSNR |
| `x264env/env.py` | `RateControlEnv`, the gymnasium env |
| `x264env/complexity.py` | Placeholder frame-complexity features (to be replaced by P2's) |
| `ENCODER_SETTINGS.md` | Frozen x264 settings and why |
| `tests/` | Smoke test for the encoder, test script for the env |

Only code and configs go in this repo. Video (`*.y4m`, `*.yuv`, `*.264`,
`*.mkv`, `*.mp4`), `results/` and `build/` are git-ignored.

## Setup (CARC)

One time, create the conda env (package cache on scratch, not `/home1`):

```bash
module purge && module load conda/25.11.0
export CONDA_PKGS_DIRS=/scratch1/$USER/conda_pkgs
mamba create --prefix /scratch1/$USER/envs/ee599 -c conda-forge --file environment.lock.txt
```

Every session (and at the top of every SLURM script):

```bash
source env.sh     # modules: ver/2506 gcc/14.3.0 x264/20250608 ffmpeg/7.1.1 conda/25.11.0
make              # builds build/libx264shim.so
```

`env.sh` activates `/scratch1/$USER/envs/ee599`; set `EE599_ENV` to use a
different env. The Python comes from the conda env (3.11, numpy, gymnasium);
no `python` module is loaded, so the two never shadow each other.

> **Never install `ffmpeg` or `x264` (or anything that pulls them in) into the
> conda env.** Its `bin/` comes first on `PATH`, so conda's copies would
> silently replace CARC's module versions, and encodes would no longer match
> the frozen x264 build. After `source env.sh`, check that `which x264 ffmpeg`
> both point under `/apps/spack/2506/`.

## Encoder shim

`encoder_shim.c` wraps libx264 (CARC `x264/20250608`, API build 165) behind a
small C API that takes and returns plain byte buffers, so Python never depends
on x264's struct layout. Settings are applied with `x264_param_parse`.

```python
from x264env import Encoder, read_y4m, y4m_header
w, h, fn, fd, frames = read_y4m("clip.y4m")
with Encoder(w, h, fn, fd, sar=y4m_header("clip.y4m")["sar"]) as enc:
    out = enc.encode(next(frames), qp=30)   # contiguous I420 bytes in
```

`sar` is written to the SPS as the aspect ratio, as the x264 CLI does with the
y4m's `A` value. The env passes it automatically.

Each `EncodedFrame` has:
- `pts`, `qp`, `frame_type` (`"IDR"` / `"P"`)
- `bits` = `slice_bits` + `header_bits`
  - `slice_bits`: the coded picture
  - `header_bits`: SPS/PPS/SEI. Nonzero only on IDRs; the first frame carries
    about 4.4 kbit of x264 version-and-options text.
- `recon`: reconstructed frame as I420. x264's internal NV12 is converted.
- `bitstream`: Annex-B bytes for the frame

There is zero frame delay: `encode()` always returns the frame just submitted.
`enc.qp_range` is `(11, 51)`. A QP outside it raises `ValueError` instead of
being silently clamped by x264.

Settings: the frozen list plus `qp=31`, `ipratio=10`, `pbratio=10` (widens
x264's CQP clamp to [11, 51]) and `force-cfr=1` (removes a 1-frame delay).
Details are in [ENCODER_SETTINGS.md](ENCODER_SETTINGS.md).

## Gym env: `RateControlEnv`

```python
from x264env.env import RateControlEnv
env = RateControlEnv(clip="clip.y4m", budget=45000, k=5, base_qp=31, dqp_mode="prev")
obs, info = env.reset(options={"clip": "clip.y4m", "gop": 0, "budget": 45000, "k": 5, "base_qp": 31})
obs, reward, terminated, truncated, info = env.step(action)
```

`reset()` takes `clip`, `gop`, `budget`, `k` and `base_qp` through `options`,
because gymnasium requires the signature `reset(seed, options)`. The
constructor's arguments are the defaults.

- **Episode:** frames `[gop*30, gop*30+30)` of the clip. Frame 0 is the IDR.
  A fresh encoder is opened every episode, and the GOP's frames are cached in
  RAM.
- **Action:** `Discrete(9)`, giving `dqp = action - 4` in {-4..+4}.
  - `dqp_mode="prev"` (default): `qp_t = qp_{t-1} + dqp`, where `qp_{t-1}`
    is the QP actually used, including one forced by the shield.
  - `dqp_mode="base"`: `qp_t = base_qp + dqp`.
  - The first frame is relative to `base_qp` in both modes. QP is clipped to
    [11, 51].
- **Reward:** PSNR-Y (dB) of the frame just encoded, capped at 100.
- **Budget:** counts slice bits only. Header bits are reported but not counted.
- **Shield:** before frame t, if the budget left is less than a conservative
  QP-51 cost of the remaining frames, frame t is forced to QP 51 and
  `info["shield_fired"]=True`. The defaults are I 6500 / P 800 slice bits per
  frame, the measured maxima on the 320x180 testsrc clip rounded up.
  Re-measure on real clips and pass `shield_bits_i` / `shield_bits_p`. If the
  budget is below the true all-QP-51 cost, overshoot is unavoidable.
- **info (each step):** `bits`, `slice_bits`, `header_bits`, `mse`, `psnr`
  (luma), `qp`, `shield_fired`, `frame_type`, `budget_left`. The last frame
  also has `total_slice_bits` and
  `overshoot = (total slice bits - budget) / budget`.
- **`env.step_qp(qp)`:** encodes the next frame at an explicit QP in [11, 51],
  with no action mapping and no shield. It returns the same tuple as `step()`.
  It's for tests and baselines (e.g. QP jumps bigger than ±4).
- **`env.episode_bitstream` / `env.episode_recon`:** the episode's Annex-B
  stream and I420 recon so far.

### Observation: `float32[16]`, normalised (`OBS_FIELDS`)

| idx | field | normalisation |
|---|---|---|
| 0 | budget left | / budget, clipped to [-1, 1] |
| 1 | frames left | / 30 |
| 2-4 | last 3 QPs (most recent first) | (qp - 11) / 40 |
| 5-7 | last 3 slice bits | / budget, clipped to [0, 1] |
| 8-10 | complexity of last 3 encoded frames | [0, 1] |
| 11-12 | lookahead mean / max complexity | [0, 1] |
| 13 | frames to next cut in lookahead | / k; 1 if none |
| 14 | cut present in lookahead | 0/1 |
| 15 | lookahead mask | 1 if k > 0, else 0 (and 11-14 are 0) |

- The lookahead covers frames t..t+k-1: the frame about to be encoded and the
  ones after it, within the GOP.
- History slots before the first frame hold `qp=base_qp`, bits 0 and
  complexity 0.

### Complexity (placeholder)

`x264env/complexity.py` has `compute_features(luma[N,H,W], prev_luma) ->
{"complexity": float32[N], "cut": bool[N]}`. Per frame, it combines mean
absolute luma difference against the previous frame (temporal) with luma std
(spatial), scaled into [0, 1]. The cut flag is set when the temporal difference
is over 30. P2's features can replace it through
`RateControlEnv(features_fn=...)`, using the same signature.

## Tests

```bash
python3 tests/smoke_encode.py clip.y4m --qp 26           # per-frame bits + PSNR at constant QP
python3 tests/test_env.py clip.y4m [--budget 45000]      # env_checker + episodes
python3 tests/test_parity.py --clip a.y4m:GOP [--clip b.y4m:GOP ...]   # env vs x264 CLI
```

`test_env.py` runs gymnasium's `env_checker`, then three episodes with
per-frame output (constant dqp=0, random actions, and random actions with
half the budget to exercise the shield). It also checks the `k=0` mask,
`dqp_mode="base"` and QP clipping.

Test clip: `ffmpeg -f lavfi -i testsrc=size=320x180:rate=30 -frames:v 30
-pix_fmt yuv420p clip.y4m`. Keep clips outside the repo.

### Parity test: env vs x264 CLI

`test_parity.py` checks that the env's encodes are exactly what the CARC
`x264` CLI produces for the same QPs. For each clip:GOP and QP sequence:

1. Run an env episode and keep its bitstream and recon.
2. Encode the same 30 frames with the `x264` CLI: the frozen flags plus
   `--qp 31 --ipratio 10 --pbratio 10 --force-cfr`, reading the original y4m
   with `--seek gop*30 --frames 30`, and a `--qpfile` with the same QPs
   (frame 0 `I`, the rest `P`).
3. Compare the full bitstream NAL by NAL, the per-frame slice sizes, and the
   ffmpeg-decoded frames (plus the env's own recon) byte for byte. A case
   passes only if all three match. A difference confined to the x264 options
   SEI would be reported with the differing options.

QP sequences: constant 26, constant 11, constant 51, random across 11..51
(seed 0), and a shield case. In the shield case, dqp = -1 every frame from
base QP 31, with the constant-QP-31 spend as the budget. The shield fires
part-way, and the QPs the env actually used, forced ones included, go to the
CLI. Work files go to `/scratch1/$USER/tmp/ee599_parity` (`--workdir`) and
are deleted when everything passes.

Two things the test found, both fixed:
- **The x264 CLI numbers `--qpfile` lines by absolute input frame,** counting
  the frames skipped by `--seek`. GOP g therefore needs lines `g*30 .. g*30+29`.
  Lines that don't match are ignored without a warning, and x264 falls back
  to its default CQP QPs (I ≈ 11, P = 31 here).
- **The CLI writes the y4m's sample aspect ratio (`A1:1`) into the SPS** as
  `aspect_ratio_idc=1`. The shim now does the same (`sar`), which costs 8
  header bits on each IDR.

## Parity results (2026-11-03)

**25/25 PASS.** In every case the bitstream, the per-frame slice bits and the
decoded frames were byte-identical to the CLI's, including the x264 options
SEI. Real clips were read in place from P2's data v1
(`/scratch1/aayushso/ee599/data/v1/320x180/clips`); nothing was copied.

| clip | GOP | fps | content |
|---|---|---|---|
| testsrc (synthetic) | 0 | 30 | test pattern |
| Animation_360P-3e40 | 0 | 30 | stable |
| Gaming_360P-3eb6 | 1 | 18595/622 | scene cut at frame 8 |
| aspen | 2 | 30000/1001 | stable |
| bbb_s00 | 3 | 24 | stable |

Each GOP was tested with constant 26, 11 and 51, random 11..51, and the shield
case. The shield fired on 4, 16, 19, 22 and 19 frames respectively.

## Verification results (2026-11-03, 320x180 testsrc)

- **Recon:** byte-identical to ffmpeg's decode of the shim's bitstream.
- **QP range:** every QP 11..51 is honoured exactly (x264 per-frame debug
  log). 10 and 52 are rejected.
- **Old vs new QP window at constant QP 26:** identical recon, +1 byte per
  slice (`slice_qp_delta` coding; see ENCODER_SETTINGS.md).
- **Env, budget 45000:**
  - Constant dqp=0 (QP 31): 42,960 slice bits (-4.5%), PSNR-Y 44.66 dB, no
    shield.
  - Random actions: -10.3%, shield fired on 7 frames.
  - Half budget: shield fired on every frame. The budget (22,500) is below the
    all-QP-51 cost (23,928), so +6.3% overshoot was unavoidable.
