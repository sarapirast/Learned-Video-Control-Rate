"""Gate test: do the richer first-pass statistics (features/fp_stats.parquet) predict what the controller and the
policies need better than first-pass bits alone? Offline, no encodes. Fit on TRAIN, evaluate on VAL (test also
reported). First pass at QP 32. Both encoders.

Targets
  (a) frame bits: log2 real slice bits of a P frame in the constant-QP encode at QP q (q in 22, 30, 38, 46),
      from rd_frames.parquet. The controller's per-frame rate model.
  (b) GOP P cost from frames 0-1 only: log2 mean real constant-QP-30 bits of P frames 1..29, using only frame 0
      and frame 1. The k=0 weakness that starved the I frame on low-motion GOPs.
  (c) base QP: q_fit (budgets.csv, 4 levels) from the budget plus the first pass of frames 0..k, k in 0, 2.
Feature sets
  base   first-pass bits only (+ q / budget as needed)
  rich   base + per-frame tex, mv, misc bits (log2) and intra / inter / skip block fractions
Models: linear (OLS) and gradient boosting (sklearn HistGradientBoosting).
Metrics: MAE (log2 units for a, b; QP for c), and for (a, b) the median absolute % error of the bits.

  python scripts/fp_stats_gate.py   -> docs/fp-stats-gate.md (+ results_v1/fp_stats_gate.csv)
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression

D = "/scratch1/aayushso/ee599/data/v1/320x180"
FPQ = 32
st = pd.read_parquet(f"{D}/features/fp_stats.parquet").query("fp_qp == @FPQ")
for c in ("tex", "mv", "misc", "slice_bits"):
    st[f"l_{c}"] = np.log2(st[c].clip(lower=1) + 8)
for c in ("intra", "inter", "skip"):
    st[f"f_{c}"] = st[f"{c}_blocks"] / 240.0
RICH = ["l_tex", "l_mv", "l_misc", "f_intra", "f_inter", "f_skip"]
gops = pd.read_csv(f"{D}/gops.csv")[["clip_id", "gop", "split"]]
fr = pd.read_parquet(f"{D}/rd/rd_frames.parquet", filters=[("kind", "==", "cqp")])
bud = pd.read_csv(f"{D}/budgets.csv")
MODELS = {"linear": LinearRegression,
          "gbm": lambda: HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                                      random_state=0)}
rows = []


def run(task, enc, df, y, base, rich, unit):
    tr, ev = df.split == "train", df.split.isin(["val", "test"])
    for fs_name, cols in (("base", base), ("rich", base + rich)):
        for mname, mk in MODELS.items():
            m = mk().fit(df.loc[tr, cols], y[tr])
            p = m.predict(df[cols])
            for split in ("val", "test"):
                s = (df.split == split).to_numpy()
                e = np.abs(p[s] - y[s])
                r = {"task": task, "encoder": enc, "features": fs_name, "model": mname, "split": split,
                     "n": int(s.sum()), f"MAE ({unit})": float(e.mean())}
                if unit == "log2":
                    r["median |% err| of bits"] = float(100 * np.median(np.abs(2 ** (p[s] - y[s]) - 1)))
                rows.append(r)


for enc in ("x264", "x265"):
    s = st[st.encoder == enc].merge(gops, on=["clip_id", "gop"])
    # (a) frame bits at QP q, P frames
    f = fr[(fr.encoder == enc) & (fr.frame > 0) & (fr.qp.isin([22, 30, 38, 46]))][["clip_id", "gop", "frame", "qp", "slice_bits"]]
    a = f.merge(s, on=["clip_id", "gop", "frame"], suffixes=("_real", ""))
    a["qp_c"] = a.qp - 30
    run("(a) frame bits", enc, a, np.log2(a.slice_bits_real.clip(lower=1) + 8).to_numpy(),
        ["l_slice_bits", "qp_c"], RICH, "log2")
    # (b) GOP mean P cost (real CQP-30) from frames 0 and 1
    real = fr[(fr.encoder == enc) & (fr.qp == 30) & (fr.frame > 0)].groupby(["clip_id", "gop"]).slice_bits.mean()
    w = s[s.frame <= 1].pivot_table(index=["clip_id", "gop"], columns="frame",
                                     values=["l_slice_bits"] + RICH)
    w.columns = [f"{a_}_{b_}" for a_, b_ in w.columns]
    w = w.join(np.log2(real + 8).rename("y")).reset_index().merge(gops, on=["clip_id", "gop"])
    run("(b) GOP P cost from frames 0-1", enc, w, w.y.to_numpy(), ["l_slice_bits_0", "l_slice_bits_1"],
        [f"{c}_{i}" for c in RICH for i in (0, 1)], "log2")
    # (c) q_fit from budget + first pass of frames 0..k
    b = bud[bud.encoder == enc][["clip_id", "gop", "level_q0", "budget_bits", "q_fit", "split"]].copy()
    b["lb"] = np.log2(b.budget_bits / 30)
    for k in (0, 2):
        vis = s[s.frame <= k]
        agg = vis.groupby(["clip_id", "gop"]).apply(lambda d: pd.Series({
            "l_fp0": d.l_slice_bits.iloc[0],
            "l_fpP": np.log2((2 ** d.l_slice_bits.iloc[1:]).mean()) if len(d) > 1 else np.nan,
            **{f"{c}_0": d[c].iloc[0] for c in RICH},
            **({f"{c}_P": d[c].iloc[1:].mean() for c in RICH} if len(d) > 1 else {})})).reset_index()
        c = b.merge(agg, on=["clip_id", "gop"])
        base = ["lb", "l_fp0"] + (["l_fpP"] if k > 0 else [])
        rich = [f"{x}_0" for x in RICH] + ([f"{x}_P" for x in RICH] if k > 0 else [])
        run(f"(c) base QP, k={k}", enc, c, c.q_fit.to_numpy(), base, rich, "QP")

R = pd.DataFrame(rows)
R.to_csv("/scratch1/aayushso/ee599/results_v1/fp_stats_gate.csv", index=False)
L = ["# Gate test: richer first-pass statistics vs first-pass bits alone", "",
     "Generated by `scripts/fp_stats_gate.py` (targets and features in its docstring). Fit on train; val is the "
     "decision split. 'base' = first-pass bits only; 'rich' = + tex/mv/misc bits and intra/inter/skip fractions.", ""]
for task in R.task.unique():
    t = R[(R.task == task)]
    metric = [c for c in t.columns if c.startswith("MAE") and t[c].notna().any()][0]
    cols = [metric] + (["median |% err| of bits"] if "median |% err| of bits" in t and t["median |% err| of bits"].notna().any() else [])
    piv = t.pivot_table(index=["encoder", "model", "split"], columns="features", values=cols).round(3)
    piv.columns = [f"{a_} [{b_}]" for a_, b_ in piv.columns]
    L += [f"## {task}", "", piv.reset_index().to_markdown(index=False), ""]
open("/scratch1/aayushso/ee599/docs/fp-stats-gate.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
