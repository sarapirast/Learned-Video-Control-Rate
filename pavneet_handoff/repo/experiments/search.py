"""Phase C: hindsight search on every GOP. Train keeps the full logs (offline RL data); val/test keep best plan and
the best-so-far traces (ceilings and the convergence curve).

  RC_NSHARDS=24 sbatch --array=0-23 ... search.py --split train
  python experiments/search.py --split train --stage gather
  python experiments/search.py --report
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, runner, search  # noqa: E402

CFG = {"n_eval": 300, "seeds": (0, 1)}
QUICK = {"n_eval": 40}


def cli(ap):
    ap.add_argument("--split", default="train")


def _one(args):
    info, n_eval, seeds, keep_logs = args
    r = search.search_gop(info, n_eval=n_eval, seeds=seeds)
    if not keep_logs:
        for b in r:
            r[b].pop("logs")
    return info["gop"]["id"], r


def main():
    a = runner.args(cli)
    cfg = {**CFG, **(QUICK if a.quick else {})}
    st = runner.Stages("search", a.quick)
    if a.report:
        return report(st)
    stage = f"search_{a.split}"
    if a.stage in (None, "search"):
        infos = runner.Stages("infos", a.quick).load("infos")
        ids = sorted(g for g, x in infos.items() if x["gop"]["split"] == a.split)
        # interleave by family so every shard gets a similar mix of cheap/expensive GOPs
        mine = ids[a.shard::a.nshards]
        items = [(infos[g], cfg["n_eval"], cfg["seeds"], a.split == "train") for g in mine]
        st.run(stage, lambda: dict(runner.pmap(_one, items, desc=stage)), a.shard, a.nshards)
    if a.stage == "gather" or (a.stage is None and a.nshards == 1):
        st.gather(stage, a.nshards)


def report(st):
    import pandas as pd
    infos = runner.Stages("infos", st.quick).load("infos")
    rows, traces = [], []
    for split in ("train", "val", "test"):
        if not st.done(f"search_{split}"):
            continue
        for g, r in st.load(f"search_{split}").items():
            for b, x in r.items():
                rows.append({"split": split, "family": infos[g]["gop"]["family"], "budget": b,
                             "best": x["best_score"], "static": x["static_score"], "gain": x["best_score"] - x["static_score"],
                             "saving": x["saving"], "over": x["over"]})
                traces.append(np.maximum.accumulate(np.max(np.stack([t[:min(map(len, x["traces"]))] for t in x["traces"]]), 0)))
    df = pd.DataFrame(rows)
    L = min(map(len, traces))
    tr = np.mean([t[:L] for t in traces], 0)
    lines = [f"# Hindsight search ({C.CODEC})", "",
             df.groupby(["split", "budget"]).agg(n=("best", "size"), static=("static", "mean"), best=("best", "mean"),
                                                 gain=("gain", "mean"), saving=("saving", "mean"),
                                                 over=("over", "mean")).round(3).to_markdown(), "",
             "By family (all splits):", "",
             df.groupby("family").agg(n=("best", "size"), gain=("gain", "mean"), best=("best", "mean")).round(3).to_markdown(),
             "", "Convergence: mean best score after n encodes (both seeds, per seed budget):", "",
             " | ".join(f"{n}: {tr[n - 1]:.3f}" for n in (10, 25, 50, 100, 150, 200, 250, 300) if n <= L)]
    out = os.path.join(C.REPORTS, f"search{'_quick' if st.quick else ''}_report.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
