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
# budget arm (data-v1 branch): "orig" = his budget; "dec" = budgets rescaled by tools/budget_arm.py and per-frame
# costs normalised by the episode's own budget (not the QP-30 budget); "lf" = leak-free (P2, 2026-11-09): clip-level
# budgets from P2's budgets.csv (4 levels), P1's frozen encoder settings, slice bits only, ramp pattern, offsets +-5
# (infos built by tools/lf_infos.py; search starts at the hindsight base q where the ramp fits the budget);
# "res" = residual RL on P2's causal controller (P2, 2026-11-09): lf settings and budgets, but each frame's QP is the
# controller's causal QP (rclib/controller.py) + the policy's offset in -3..+3; infos by tools/res_infos.py (flat GOPs
# dropped, P1-settings first pass, the controller's own result per GOP x level x k as the reward baseline)
# "lfq" (P2, 2026-11-09) = lf with the quality-at-budget metric (rclib/metrics.py METRIC = "dpsnr"): same infos as lf
# (tools: symlink results_infos), its own work dir, so the lf results are kept
ARM = os.environ.get("RC_ARM", "orig")
assert ARM in ("orig", "dec", "lf", "res", "lfq"), ARM
LF = ARM in ("lf", "res", "lfq")
RES = ARM == "res"
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
BUDGET_QPS = (30, 38)         # budget = bits of the encoder's own constant QP at this QP

# spend-early pattern: offsets for [I frame, P frames 1..9, P frames 10..29] (D7 in docs/DECISIONS.md)
STATIC = (-6, -3, 3)
STATIC_SPLIT = 10
ACTIONS = (-3, -2, -1, 0, 1, 2, 3)   # per-frame QP offset on top of STATIC (D8)
QP_LO, QP_HI = 0, 51                 # clip range of planned QPs

if LF:
    BUDGET_QPS = (24, 30, 36, 42)    # budget level keys (clip mean of constant-QP slice bits at this QP), not own spend
    ACTIONS = tuple(range(-5, 6))    # +-5: at +-3 the orig search sat at the limit on 26-30% of frames
    QP_LO, QP_HI = 11, 51            # P1's env range
    # P2's linear ramp (scripts/baselines_v1.py PATTERN): I q-6, P frames q-3 .. q+3; same float values so that
    # round(q + o) reproduces the ramp_best baseline exactly
    import numpy as _np
    RAMP = [-6.0] + [float(v) for v in _np.linspace(-3, 3, GOP - 1)]
# lfq LEARNERS (P2 2026-11-10, tracker 30d option (i)): frame QP = round(causal base + RAMP[t] + offset), causal base =
# P2's budgets.csv base_qp_est_k<k> (infos["base"][(level, k)], tools/lfq_infos.py); the hindsight search plans are
# re-expressed relative to it. Its error vs the hindsight base is ~3-5 QP (train sd 4.9 at k0, 2.9 at k29), so the
# learners' offsets are +-RC_ACT_RANGE (experiments/rl.py sets 10 for lfq; at +-5, 55% of the k0 best plans need an
# offset outside the range). The search itself keeps +-5 (RC_ACT_RANGE unset).
LFQ_LEARN = ARM == "lfq" and bool(os.environ.get("RC_ACT_RANGE"))
if LFQ_LEARN:
    _w = int(os.environ["RC_ACT_RANGE"])
    ACTIONS = tuple(range(-_w, _w + 1))
if RES:
    ACTIONS = tuple(range(-int(os.environ.get("RC_RES_RANGE", 3)), int(os.environ.get("RC_RES_RANGE", 3)) + 1))
    # residual offset on the controller's QP; RC_RES_RANGE (P2 next-exp R2, 11-13) widens it, default 3 = -3..+3
    # RC_RES_RECAP=1 (P2 next-exp Exp 5a, 11-13): re-apply the controller's own limits after the offset (fcap floor,
    # step limit dmax, pmin, QP 51 when the remaining budget is spent); default off = resh behaviour (not re-applied)
    # values: 0 = off; bit = budget limits only (fcap floor, QP 51 when the budget is spent); full (or 1) = also the
    # shape limits (step limit dmax, P QP >= I QP + pmin)
    RES_RECAP = {"0": "", "1": "full", "full": "full", "bit": "bit"}[os.environ.get("RC_RES_RECAP", "0")]
    # P2's published controller setting (results_v1/controller_final.md): margin:dI:i_cap:w0:dmax:fcap:init:pmin:a:b
    # RC_CTRL_SETTING overrides it (P2 2026-11-10: controller retuned under dPSNR_B, tracker 30e/30f); b (cut boost)
    # must be 0: the env has no first-pass cut flags
    CTRL_SETTING = tuple(float(v) for v in os.environ.get(
        "RC_CTRL_SETTING", "0.97:3.0:0.3:2.0:3.0:4.0:0.0:1.0:0.0:0.0").split(":"))
    # optional 11th field h (P2 2026-11-11, tracker 31 stage C2): the controller's previous-GOP history mode
    # (scripts/controller_real.py); the env replays it from info["ctrl_qhat"] / info["ctrl_r"] (tools/res_infos.py)
    assert len(CTRL_SETTING) in (10, 11) and CTRL_SETTING[9] == 0, CTRL_SETTING
    CTRL_MODEL = os.environ.get("RC_CTRL_MODEL", "/scratch1/aayushso/ee599/data/v1/320x180/rd/controller_model.json")


def static_offsets(pattern=STATIC, split=STATIC_SPLIT, n=GOP):
    if LF and pattern is STATIC and split == STATIC_SPLIT and n == GOP:
        return list(RAMP)
    return [pattern[0]] + [pattern[1]] * (split - 1) + [pattern[2]] * (n - split)


def results_dir(name):
    d = os.path.join(WORK, f"results_{name}")
    os.makedirs(d, exist_ok=True)
    return d
