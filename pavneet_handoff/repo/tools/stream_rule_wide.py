"""Wider val grid for the stream rule (slope and prior weight were at the grid edge). Writes results_stream/rule_wide.pkl."""
import os, sys, pickle, numpy as np
sys.path.insert(0, "/scratch1/pbanga/ee599")
from experiments import stream_rl as S
from rclib import streamenv as SE, clipenv as CE, config as C
inf = S.load_infos(); tr = S.split_ids(inf, "train"); tabs = {g: CE.gop_table(inf[g]) for g in tr}
c0 = S.train_c0(inf); zero = lambda o: SE.ZERO
QP, CW, M = (2.5, 3.0, 3.5, 4.0, 4.5), (1.0, 3.0, 6.0, 12.0), (0.96, 0.98, 1.00)
c0q = {q: SE.prior_c0(tabs, tr, q) for q in QP}
out = {}
for look in (0, 2):
    val = {}
    for m in M:
        for q in QP:
            for w in CW:
                rp = {"qpd": q, "cw": w, "c0": c0q[q]}
                val[(m, q, w)] = np.mean([r["score"] for r in S.evaluate(zero, inf, "val", look, c0, m, "rule", rp)])
    best = max(val, key=val.get)
    rp = {"qpd": best[1], "cw": best[2], "c0": c0q[best[1]]}
    rows = {s: S.evaluate(zero, inf, s, look, c0, best[0], "rule", rp) for s in ("val", "test")}
    out[look] = {"val": val, "best": best, "rp": rp, "rows": rows}
    top = sorted(val.items(), key=lambda kv: -kv[1])[:4]
    print(C.CODEC, f"L={look} best", best, "val %.3f test %.3f" % tuple(np.mean([r["score"] for r in rows[s]]) for s in ("val", "test")),
          "| top:", "; ".join(f"{k}: {v:+.3f}" for k, v in top), flush=True)
pickle.dump(out, open(os.path.join(C.WORK, "results_stream", "rule_wide.pkl"), "wb"))
