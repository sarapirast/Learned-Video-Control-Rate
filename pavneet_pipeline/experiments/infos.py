"""Phase A: per-GOP information every later stage needs.

For each GOP: the encoder's own constant-QP curve over QP 18-50 (33 measured encodes), the budgets (curve bits at
QP 30 and 38), a first-pass encode (ultrafast, QP 30), pixel features and scene analysis, and the STATIC plan's
encode at both budgets (the reference for the relative reward).

  python experiments/infos.py --stage manifest            # once, before the array
  RC_NSHARDS=16 sbatch --array=0-15 ... infos.py          # one shard per array task
  python experiments/infos.py --stage gather              # merge -> results_infos/infos.pkl
  python experiments/infos.py --report
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import codec, config as C, data, features, metrics, runner  # noqa: E402
from rclib.runner import log  # noqa: E402


def quick_subset(gops, per_split=6):
    out = []
    for split in ("train", "val", "test"):
        g = sorted([x for x in gops if x["split"] == split], key=lambda x: x["id"])
        nat = [x for x in g if x["family"] != "splice"]
        spl = [x for x in g if x["family"] == "splice"]
        step = max(1, len(nat) // per_split)
        out += nat[::step][:per_split] + spl[:2]
    return out


def all_gops(quick):
    g = data.load_manifest()["gops"]
    return quick_subset(g) if quick else g


def static_plan(base):
    return [base + o for o in C.static_offsets()]


def gop_info(g):
    p = data.gop_path(g)
    src = data.gop_frames(g)
    fp = codec.first_pass(p)
    an = features.gop_analysis(src, fp)
    curve = {"qps": list(C.QPS), "bits": [], "psnr": [], "frame_bits": []}
    for q in C.QPS:
        r = codec.encode_cqp(p, q, src=src)
        curve["bits"].append(r["total_bits"])
        curve["psnr"].append(r["mean_psnr"])
        curve["frame_bits"].append(r["bits"].astype(np.int32))
    curve["bits"] = np.array(curve["bits"])
    curve["psnr"] = np.array(curve["psnr"])
    curve["frame_bits"] = np.stack(curve["frame_bits"])
    budget = {b: int(curve["bits"][C.QPS.index(b)]) for b in C.BUDGET_QPS}
    static = {}
    for b in C.BUDGET_QPS:
        r = codec.encode(p, static_plan(b), src=src)
        static[b] = {"bits": r["bits"], "psnr": r["psnr"], "total_bits": r["total_bits"], "mean_psnr": r["mean_psnr"],
                     "saving": float(metrics.saving(r["total_bits"], r["mean_psnr"], curve)),
                     "score": float(metrics.score(r["total_bits"], r["mean_psnr"], curve, budget[b])),
                     "over": r["total_bits"] > budget[b]}
    return g["id"], {"gop": g, "fp_bits": fp, "an": an, "curve": curve, "budget": budget, "static": static}


def main():
    a = runner.args()
    st = runner.Stages("infos", a.quick)
    if a.stage == "manifest" or not os.path.exists(data.MANIFEST):
        if not os.path.exists(data.MANIFEST):
            g = data.build_manifest()
            log(f"manifest: {len(g)} GOPs")
        if a.stage == "manifest":
            return
    if a.report:
        return report(st)
    gops = all_gops(a.quick)
    if a.stage in (None, "infos"):
        mine = data.shard(gops, a.nshards, a.shard)
        st.run("infos", lambda: dict(runner.pmap(gop_info, mine, desc="infos")), a.shard, a.nshards)
    if a.stage == "gather" or (a.stage is None and a.nshards == 1):
        st.gather("infos", a.nshards)
        report(st)


def load(quick=False):
    return runner.Stages("infos", quick).load("infos")


def report(st):
    inf = st.load("infos")
    import pandas as pd
    rows = []
    for gid, x in inf.items():
        g = x["gop"]
        for b in C.BUDGET_QPS:
            s = x["static"][b]
            rows.append({"split": g["split"], "family": g["family"], "budget": b, "static_saving": s["saving"],
                         "static_over": s["over"], "cuts": int(x["an"]["cut"].sum()),
                         "fp_cv": float(np.std(x["fp_bits"][1:]) / max(np.mean(x["fp_bits"][1:]), 1))})
    df = pd.DataFrame(rows)
    n = df[df.budget == C.BUDGET_QPS[0]].groupby("split").size()
    lines = [f"# GOP information ({C.CODEC})", "", f"GOPs per split: {dict(n)}", "",
             "STATIC vs constant QP (saving %, % over budget):", "",
             df.groupby(["split", "budget"]).agg(saving=("static_saving", "mean"),
                                                 over=("static_over", "mean"), n=("static_saving", "size")).round(3)
             .to_markdown(), "", "Detected cuts per GOP by family:", "",
             df[df.budget == C.BUDGET_QPS[0]].groupby("family").agg(cuts=("cuts", "mean"), fp_cv=("fp_cv", "mean"))
             .round(3).to_markdown()]
    os.makedirs(C.REPORTS, exist_ok=True)
    out = os.path.join(C.REPORTS, f"infos{'_quick' if st.quick else ''}_report.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
