"""Hindsight hill-climb over a GOP's 30 per-frame offsets: the teacher for offline RL and the ceiling for every report.

Starts from STATIC (all offsets 0), proposes local moves, keeps a move when the penalised score does not get worse,
and evaluates every proposal with a real encode. Every evaluated plan is logged (offline RL data) and the best-so-far
score after each encode is recorded (convergence curve).
"""
import numpy as np

from . import codec, config as C, data, metrics

NA = len(C.ACTIONS)
ZERO = C.ACTIONS.index(0)
STATIC_OFF = np.array(C.static_offsets())


def qps_of(base, acts):
    return [int(base + STATIC_OFF[t] + C.ACTIONS[a]) for t, a in enumerate(acts)]


def _propose(cur, rng):
    x = cur.copy()
    m = rng.random()
    if m < 0.35:                                   # one frame +-1
        t = rng.integers(C.GOP)
        x[t] += rng.choice((-1, 1))
    elif m < 0.65:                                 # a run of 2-6 frames +-1
        L = rng.integers(2, 7)
        t = rng.integers(0, C.GOP - L + 1)
        x[t:t + L] += rng.choice((-1, 1))
    elif m < 0.9:                                  # move bits: one frame down, another up
        i, j = rng.choice(C.GOP, 2, replace=False)
        x[i] -= 1
        x[j] += 1
    else:                                          # everything after a frame +-1 (shifts the spend curve)
        t = rng.integers(1, C.GOP)
        x[t:] += rng.choice((-1, 1))
    return np.clip(x, 0, NA - 1)


def hill_climb(info, budget, n_eval=300, seed=0, start=None):
    rng = np.random.default_rng(seed)
    path = data.gop_path(info["gop"])
    src = data.gop_frames(info["gop"])
    curve, B = info["curve"], info["budget"][budget]
    cur = np.full(C.GOP, ZERO) if start is None else np.asarray(start).copy()
    st = info["static"][budget]
    cur_score = st["score"] if start is None else None
    seen = {cur.tobytes(): cur_score}
    log, best_trace = [], []
    best = (cur_score if cur_score is not None else -np.inf, cur.copy(), None)
    tries = 0
    while len(log) < n_eval and tries < 50 * n_eval:
        tries += 1
        x = _propose(cur, rng) if (cur_score is not None) else cur
        key = x.tobytes()
        if key in seen and seen[key] is not None:
            continue
        r = codec.encode(path, qps_of(budget, x), src=src)
        s = float(metrics.score(r["total_bits"], r["mean_psnr"], curve, B))
        seen[key] = s
        log.append({"acts": x.astype(np.int8), "bits": r["bits"].astype(np.int32), "total_bits": r["total_bits"],
                    "psnr": r["mean_psnr"], "fpsnr": r["psnr"].astype(np.float16), "score": s})
        if cur_score is None or s >= cur_score:
            cur, cur_score = x, s
        if s > best[0]:
            best = (s, x.copy(), r)
        best_trace.append(best[0])
    return {"best_score": best[0], "best_acts": best[1].astype(np.int8), "log": log,
            "trace": np.array(best_trace, np.float32), "static_score": st["score"]}


def search_gop(info, budgets=C.BUDGET_QPS, n_eval=300, seeds=(0, 1)):
    out = {}
    for b in budgets:
        runs = [hill_climb(info, b, n_eval, seed=1000 * s + b) for s in seeds]
        i = int(np.argmax([r["best_score"] for r in runs]))
        best = runs[i]
        # evaluate the best plan's details once more for the report (bits/PSNR/over), from its log entry
        ent = max((e for r in runs for e in r["log"]), key=lambda e: e["score"])
        if ent["score"] < best["best_score"]:          # nothing beat STATIC: the best plan is STATIC itself
            s = info["static"][b]
            ent = {"total_bits": s["total_bits"], "psnr": s["mean_psnr"]}
        sav = float(metrics.saving(ent["total_bits"], ent["psnr"], info["curve"]))
        out[b] = {"best_score": best["best_score"], "best_acts": best["best_acts"], "saving": sav,
                  "over": ent["total_bits"] > info["budget"][b], "total_bits": ent["total_bits"], "psnr": ent["psnr"],
                  "static_score": best["static_score"], "traces": [r["trace"] for r in runs],
                  "logs": [r["log"] for r in runs]}
    return out
