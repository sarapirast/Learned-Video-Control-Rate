"""Global settings. Everything the pipeline shares lives here; experiment scripts only add their own CFG dicts.

Environment variables (no code edits needed per node):
  RC_CODEC    x265 | x264           encoder used for every encode
  RC_WORK     work directory        clips, GOP cache, results (one per encoder)
  RC_WORKERS  int                   processes for independent encodes
  RC_ENVS     int                   parallel PPO environments (part of the training recipe: keep 14 for baselines)
  RC_TMP      dir                   scratch space for encoder output (node-local RAM disk by default)
"""
import os

CODEC = os.environ.get("RC_CODEC", "x265")
assert CODEC in ("x265", "x264"), CODEC
WORK = os.environ.get("RC_WORK", f"/scratch1/{os.environ.get('USER', 'user')}/rcwork")
WORKERS = int(os.environ.get("RC_WORKERS", max(1, (os.cpu_count() or 4) - 2)))
N_ENVS = int(os.environ.get("RC_ENVS", 14))
TMP = os.environ.get("RC_TMP") or ("/dev/shm" if os.path.isdir("/dev/shm") else "/tmp")

CLIPS = os.path.join(WORK, "clips")
GOPS = os.path.join(WORK, "gops")
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(PROJECT, "results", CODEC)   # one report folder per encoder

# picture and GOP
W, H = 320, 180
FRAME_BYTES = W * H * 3 // 2
GOP = 30                      # IDR + 29 P frames
QP_MIN, QP_MAX = 18, 50       # constant-QP curve range
QPS = list(range(QP_MIN, QP_MAX + 1))
BUDGET_QPS = (30, 38)         # budget = bits of the encoder's own constant QP at this QP

# spend-early pattern: offsets for [I frame, P frames 1..9, P frames 10..29] (D7 in docs/DECISIONS.md)
STATIC = (-6, -3, 3)
STATIC_SPLIT = 10
ACTIONS = (-3, -2, -1, 0, 1, 2, 3)   # per-frame QP offset on top of STATIC (D8)


def static_offsets(pattern=STATIC, split=STATIC_SPLIT, n=GOP):
    return [pattern[0]] + [pattern[1]] * (split - 1) + [pattern[2]] * (n - split)


def results_dir(name):
    d = os.path.join(WORK, f"results_{name}")
    os.makedirs(d, exist_ok=True)
    return d
