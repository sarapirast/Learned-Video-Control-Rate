"""Table of final4's frame-0 planning QP (controller decide() diag "level" at t = 0, causal) for every val (GOP,
budget level, k), for the o[2] causal stand-in arm: o[2] = 1 if that QP >= 27 (outside the bin that covers level 24,
Exp 5a REVISION 3 cut points) else 0. Env resets only, no encodes. Run in the resh env (final4 setting, history).

  RC_ARM=res RC_CODEC=<enc> RC_CTRL_SETTING=1.0:6:1.0:2:3:4:1:1:1:0:3 RC_WORK=rcwork_v1/<enc>_resh ... \
      python exp_next/o2/f4_level0.py
Out: results_v1/next/o2/f4_level0_<enc>.pkl = {(gid, level, k): planning QP}
"""
import os
import pickle
import sys

sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C, env as E, offrl  # noqa: E402

assert C.RES and os.environ.get("RC_CTRL_SETTING") == "1.0:6:1.0:2:3:4:1:1:1:0:3"
OUT = "/scratch1/aayushso/ee599/results_v1/next/o2"
full = pickle.load(open(f"/scratch1/aayushso/rcwork_v1/{C.CODEC}_resh/results_infos/infos.pkl", "rb"))
val = sorted(g for g, x in full.items() if x["gop"]["split"] == "val")
tab = {}
for g in val:
    info = offrl.slim(full[g])
    for k in (0, 5):
        env = E.make_env({g: info}, k=k)
        for lv in C.BUDGET_QPS:
            env.force(g, lv, k)
            env.reset()
            tab[(g, lv, k)] = float(env.ctrl_diag["level"])
os.makedirs(OUT, exist_ok=True)
dest = f"{OUT}/f4_level0_{C.CODEC}.pkl"
pickle.dump(tab, open(dest, "wb"))
on = sum(v >= 27 for v in tab.values())
agree = sum((v >= 27) == (lv != 24) for (g, lv, k), v in tab.items())
print(f"{C.CODEC}: {len(tab)} entries; stand-in o[2] = 1 on {on}; agrees with the true o[2] on {agree} "
      f"({100 * agree / len(tab):.1f}%) -> {dest}")
