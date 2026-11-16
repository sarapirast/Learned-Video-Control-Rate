"""Build the lfq LEARNERS' infos (RC_ARM=lfq, tracker 30d option (i); v1-data branch, P2 2026-11-10). No encodes.

Writes $RC_WORK(lfq)/results_infos/infos_learn.pkl (experiments/rl.py loads it for lfq; the search keeps infos.pkl,
which is the lf arm's). Changes vs the lf infos (tools/lf_infos.py):
  - flat (grayscale) GOPs dropped (data/v1/320x180/rd/flat_gops.csv), as in tools/res_infos.py
  - fp_bits = P2's first pass on P1's settings at QP 32 (features/fp_bits.parquet), as in tools/res_infos.py
  - base[(level, k)] = P2's CAUSAL base-QP estimate budgets.csv base_qp_est_k<k> (k 0/2/5/10/29; linear, fit on train,
    out-of-fold there): the learners' QPs are round(base + RAMP[t] + offset) (rclib/env.py frame_qp)
  - static[level] = the lfq search's start plan (ramp at the hindsight base q that fits the budget; rclib/search.py
    lf_start): score (METRIC dpsnr), dpsnr (no over penalty), saving, bits. Used only as the reward offset (a constant
    per GOP x level, so it does not change the optimal policy) and as 'static_score' in the episode rows.
Needs the lfq search results of every split (results_search/search_<split>.pkl); --allow-missing val,test builds
without them (those GOPs get no 'static'; for smoke tests only).

Previous-GOP base (P2 2026-11-11, tracker 31 stage C1): --base-csv data/v1/320x180/budgets_prev_<enc>.csv takes
base[(level, k)] = its base_qp_prev (scripts/base_prev.py: + the controller's result on GOP n-1 of the same clip; the
first GOP of a clip keeps base_qp_est_k) and --workname lfqp writes to rcwork_v1/<enc>_lfqp, a new work dir that links
the lfq clips/gops/manifest, results_infos/infos.pkl and results_search (nothing in <enc>_lfq is touched).

  /scratch1/aayushso/envs/ee599/bin/python -I tools/lfq_infos.py <x264|x265> [--allow-missing SPLITS] [--force]
      [--base-csv PATH --workname NAME]
"""
import argparse
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["RC_METRIC"] = "dpsnr"
from rclib import metrics  # noqa: E402

D = "/scratch1/aayushso/ee599/data/v1/320x180"
LEVELS, KS = (24, 30, 36, 42), (0, 2, 5, 10, 29)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("enc", choices=("x264", "x265"))
    ap.add_argument("--allow-missing", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--base-csv", default="", help="take base[(level, k)] from this csv's base_qp_prev column")
    ap.add_argument("--workname", default="lfq", help="work dir rcwork_v1/<enc>_<workname>")
    a = ap.parse_args()
    assert (a.workname == "lfq") == (not a.base_csv), "a non-default base needs its own --workname (and vice versa)"
    allow = {s for s in a.allow_missing.split(",") if s}
    work = f"/scratch1/aayushso/rcwork_v1/{a.enc}_{a.workname}"
    if a.workname != "lfq":
        src = f"/scratch1/aayushso/rcwork_v1/{a.enc}_lfq"
        os.makedirs(os.path.join(work, "results_infos"), exist_ok=True)
        for name in ("clips", "gops", "manifest.json", "results_search", "results_infos/infos.pkl"):
            dst = os.path.join(work, name)
            if not os.path.lexists(dst):
                os.symlink(os.path.realpath(os.path.join(src, name)), dst)
    bprev = None
    if a.base_csv:
        b = pd.read_csv(a.base_csv).query("encoder == @a.enc")
        bprev = {(r.clip_id, int(r.gop), int(r.level_q0), int(r.k)): float(r.base_qp_prev) for r in b.itertuples()}
    out = os.path.join(work, "results_infos", "infos_learn.pkl")
    if os.path.exists(out) and not a.force:
        raise SystemExit(f"{out} exists; --force to rebuild")
    with open(os.path.join(work, "results_infos", "infos.pkl"), "rb") as f:
        infos = pickle.load(f)
    srch = {}
    for sp in ("train", "val", "test"):
        p = os.path.join(work, "results_search", f"search_{sp}.pkl")
        if os.path.exists(p):
            with open(p, "rb") as f:
                srch.update(pickle.load(f))
        elif sp not in allow:
            raise SystemExit(f"{p} missing (search gather not done?); --allow-missing {sp} for a smoke build")

    flat = pd.read_csv(f"{D}/rd/flat_gops.csv")
    flat = set(flat.gid[flat.flat])
    fp = pd.read_parquet(f"{D}/features/fp_bits.parquet").query("encoder == @a.enc and fp_qp == 32")
    fp = {k: v.sort_values("frame").fp_slice_bits.to_numpy(float) for k, v in fp.groupby(["clip_id", "gop"])}

    res, nostatic, worst = {}, {}, 0.0
    for gid, x in infos.items():
        if gid in flat:
            continue
        key = (x["gop"]["clip"], int(x["gop"]["v1_gop"]))
        f = fp[key]
        assert len(f) == 30, gid
        y = dict(x)
        y["fp_bits"] = f
        y["fp_source"] = f"P2 fp_bits.parquet, {a.enc} QP 32, P1 settings (fp_slice_bits)"
        y["base"] = {(lv, k): float(x["budget_meta"][lv][f"base_qp_est_k{k}"]) for lv in LEVELS for k in KS}
        if bprev is not None:
            y["base_est"] = y["base"]
            y["base"] = {(lv, k): bprev[(key[0], key[1], lv, k)] for lv in LEVELS for k in KS}
        assert all(np.isfinite(v) for v in y["base"].values()), gid
        e = srch.get(gid)
        if e is None:
            sp = x["gop"]["split"]
            assert sp in allow, (gid, sp)
            nostatic[sp] = nostatic.get(sp, 0) + 1
            y["static"] = {}
        else:
            y["static"] = {}
            for lv in LEVELS:
                st, B, c = e[lv]["start"], x["budget"][lv], x["curve"]
                dq = float(metrics.dpsnr_budget(st["mean_psnr"], c, B))
                sc = float(metrics.score(st["total_bits"], st["mean_psnr"], c, B))
                worst = max(worst, abs(sc - st["score"]), abs(sc - e[lv]["static_score"]))
                y["static"][lv] = {"score": sc, "dpsnr": dq, "saving": float(metrics.saving(st["total_bits"],
                                                                                            st["mean_psnr"], c)),
                                   "bits": np.asarray(st["bits"]), "total_bits": int(st["total_bits"]),
                                   "q": int(st["q"])}
        res[gid] = y
    assert worst < 1e-6, f"search start score not reproduced (max diff {worst})"
    tmp = out + ".part"
    with open(tmp, "wb") as f:
        pickle.dump(res, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, out)
    slim = os.path.join(work, "results_infos", "infos_learn_slim.pkl")
    if os.path.exists(slim):       # rl.py caches a slim copy; it is stale now
        os.remove(slim)
    n = pd.Series([v["gop"]["split"] for v in res.values()]).value_counts().to_dict()
    print(f"{out}: {len(res)} GOPs {n}; dropped flat {sum(g in flat for g in infos)}; start score max diff "
          f"{worst:.1e}; without search start: {nostatic or 'none'}")


if __name__ == "__main__":
    main()
