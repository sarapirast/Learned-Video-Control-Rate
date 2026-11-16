"""Regression check (brief Part B item 2): an existing run's stored val episodes must be reproduced exactly by the
current code (same QPs, bits, score). Usage (inside the job env of the run's arm):
  python -I exp_next/regress_eval.py <run_dir> [n_episodes]
"""
import os
import pickle
import sys

sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C, offrl, policies as P  # noqa: E402

run, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 5
ev = pickle.load(open(os.path.join(run, "eval.pkl"), "rb"))
spec, args = ev["spec"], ev["args"]
(m, k, s), rows = next(((key, r) for key, r in ev["res"].items() if key[2] == "val"))
infos = pickle.load(open(os.path.join(C.WORK, "results_infos", "infos.pkl"), "rb"))
ipath = P.save_infos_for_workers({g: offrl.slim(x) for g, x in infos.items()},
                                 os.path.join(os.environ.get("RC_TMP", "/tmp"), f"regress_{os.path.basename(C.WORK)}_slim.pkl"))
ok = 0
for r in rows[:n]:
    new = P.evaluate(spec, ipath, [r["gid"]], budgets=[r["budget"]], workers=1, desc="regress", k=k, mode=m,
                     k_sampler=None)[0]
    same = new["qps"] == r["qps"] and new["bits"] == r["bits"] and abs(new["score"] - r["score"]) < 1e-9
    ok += same
    print(r["gid"], r["budget"], "OK" if same else f"MISMATCH score {r['score']:.4f} -> {new['score']:.4f}")
print(f"{ok}/{min(n, len(rows))} stored val episodes reproduced exactly ({run})")
