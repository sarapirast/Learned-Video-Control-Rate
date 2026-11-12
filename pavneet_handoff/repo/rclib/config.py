"""Global settings. Everything the pipeline shares lives here; experiment scripts only add their own CFG dicts.

Environment variables (no code edits needed per node):
  RC_CODEC    x265 | x264           encoder used for every encode
  RC_WORK     work directory        clips, GOP cache, results (one per encoder)
  RC_WORKERS  int                   processes for independent encodes
  RC_ENVS     int                   parallel PPO environments (part of the training recipe: keep 14 for baselines)
  RC_TMP      dir                   scratch space for encoder output (node-local RAM disk by default)
  RC_BUDGETS  e.g. 26,30,34,38,42   budget QPs (default 30,38; the wide-budget study D28 uses five)
  RC_REPORTS  dir                   report folder (default results/<codec>; the wide study writes results/<codec>_wide)
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
REPORTS = os.environ.get("RC_REPORTS") or os.path.join(PROJECT, "results", CODEC)   # one report folder per encoder

# picture and GOP
W, H = 320, 180
FRAME_BYTES = W * H * 3 // 2
GOP = 30                      # IDR + 29 P frames
QP_MIN, QP_MAX = 18, 50       # constant-QP curve range
QPS = list(range(QP_MIN, QP_MAX + 1))
BUDGET_QPS = tuple(int(q) for q in os.environ.get("RC_BUDGETS", "30,38").split(","))   # budget = bits of the encoder's own constant QP at this QP
BUDGET_REF = 30               # budget QP that per-frame cost features are normalised by (fixed, so features do not depend on RC_BUDGETS)
# causal per-GOP setting (D30): RC_CAUSAL=1 -> the budget is s x (the GOP's constant-QP bits at a budget QP) with s
# unknown to the controller, the base QP comes from a first-pass rate model, scene flags use visible frames only
CAUSAL = os.environ.get("RC_CAUSAL", "0") == "1"
# dataset v1 (D31): RC_V1=1 -> clip-level budgets, P1's frozen encoder settings, action = residual on the online controller
V1 = os.environ.get("RC_V1", "0") == "1"
CAUSAL = CAUSAL or V1
V1_BUDGETS = os.environ.get("RC_V1_BUDGETS", "/scratch1/aayushso/ee599/data/v1/320x180/budgets.csv")
CAUSAL_S_TRAIN = (0.8, 1.25)          # training: s uniform in this range
CAUSAL_S_EVAL = (0.85, 1.0, 1.18)     # evaluation: s per (GOP, budget QP) case, fixed by a hash (env.causal_scale)


def budget_level(b):
    """Budget input of the policy and the MPC model: 0 at the lowest budget QP, 1 at the highest (0/1 for 30/38, as before)."""
    lo, hi = min(BUDGET_QPS), max(BUDGET_QPS)
    return float((b - lo) / (hi - lo)) if hi > lo else 0.0

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
