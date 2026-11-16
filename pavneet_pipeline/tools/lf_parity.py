"""Parity check for the leak-free arm (P2, 2026-11-09): the search's start plan (rclib/search.py lf_start) must reproduce
P2's ramp_best baseline rows (scripts/baselines_v1.py, results_v1/baselines_v1.parquet) on val/test GOPs: same base q,
slice bits, PSNR and score. Run with RC_ARM=lf and the v1 job env sourced:
  RC_ARM=lf RC_CODEC=x264 source tools/job_env_v1.sh; python tools/lf_parity.py [n_gops]
"""
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, search  # noqa: E402

assert C.LF, "set RC_ARM=lf"
n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
infos = pickle.load(open(os.path.join(C.WORK, "results_infos", "infos.pkl"), "rb"))
ref = pickle.load(open("/scratch1/aayushso/tmp/ramp_ref.pkl", "rb"))[C.CODEC]   # {(clip, gop, level): row}
keys = sorted({(c, g) for c, g, _ in ref})
pick = keys[:: max(1, len(keys) // n)][:n]
bad = 0
for gid, x in infos.items():
    k = (x["gop"]["clip"], int(x["gop"]["v1_gop"]))
    if k not in pick:
        continue
    for lv in C.BUDGET_QPS:
        st = search.lf_start(x, lv)
        r = ref[(*k, lv)]
        ok = st["q"] == r["param"] and st["total_bits"] == r["bits"] and abs(st["mean_psnr"] - r["psnr_yuv"]) < 1e-6 \
            and abs(st["score"] - r["score"]) < 1e-6
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {gid} L{lv}: q {st['q']}/{r['param']} bits {st['total_bits']}/{r['bits']} "
              f"psnr {st['mean_psnr']:.4f}/{r['psnr_yuv']:.4f} score {st['score']:.3f}/{r['score']:.3f} "
              f"encodes {st['n_encodes']}")
print(f"{C.CODEC}: {'ALL OK' if bad == 0 else f'{bad} MISMATCHES'}")
sys.exit(1 if bad else 0)
