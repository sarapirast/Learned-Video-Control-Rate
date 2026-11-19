"""Final-week item 2: R3 with its OWN previous-GOP history (EXPLORATORY, val only; rule in exp_next/fw/PLAN.md).

R3's env replays the history final4 recorded on GOP n-1 in its own sequential run (tools/res_infos.py: ctrl_qhat =
base_prev estimate from final4's GOP n-1, ctrl_r = final4's real / predicted bits on GOP n-1; final4 setting h = 3
uses both). A deployed R3 would have only its own GOP n-1. Here each (clip, level, seed) chain runs the val GOPs in
order and GOP n gets the history computed from R3's own encode of GOP n-1 with final4's functions
(scripts/controller_real.py: history_features, qhat_prev). If GOP n-1 is not scored (flat GOP, not in the infos) the
stored history is kept and counted.

Checks:
  --formula   no encodes: recomputing the history from final4's stored GOP n-1 rows must equal the replayed values
  --mode stored --clips N   chains with the stored history must reproduce the stored val rows exactly

  RC_ARM=res RC_METRIC=dpsnr RC_RES_RANGE=6 RC_RES_RECAP=bit RC_CODEC=<enc> RC_CTRL_SETTING=1.0:6:1.0:2:3:4:1:1:1:0:3 \
  RC_WORK=/scratch1/aayushso/rcwork_v1/<enc>_resh ... python -I exp_next/fw/seq_history.py --formula
                                                          ... --mode stored --clips 2       (parity)
                                                          ... --mode own                     (the run)
  python -I exp_next/fw/seq_history.py --report           (any env; reads both encoders)
Out: results_v1/next/fw/seqhist_<mode>_val_<enc>.pkl = {seed: rows (+ "hist_src")}, seqhist_val.md
"""
import argparse
import glob
import importlib.util
import json
import os
import pickle
import sys

import numpy as np

ROOT = "/scratch1/aayushso/ee599"
sys.path.insert(0, f"{ROOT}/repo-pavneet")
OUT = f"{ROOT}/results_v1/next/fw"
OUT_T2 = f"{ROOT}/results_v1/test2"   # test2 (exp_next/test2/PREREG.md secondary 8): RC_WORK=rcwork_t2/<enc>_resh
D = f"{ROOT}/data/v1/320x180"
RUN = "res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s{s}"
SM = f"{ROOT}/results_v1/next/exp5/shifts_smooth.json"
K = 5
_spec = importlib.util.spec_from_file_location("controller_real", f"{ROOT}/scripts/controller_real.py")


def _cr():
    m = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(m)
    return m


def gop_index(gid):
    return int(gid.rsplit("@", 1)[1]) // 30


def history(CR, x, lv, prev, M, pm):
    """GOP n's (qhat, r) from GOP n-1's (fp, qps, total bits, B), exactly as controller_real.chain does."""
    fp_prev, qps_prev, bits_prev, B_prev = prev
    qeq, lcal, r = CR.history_features(fp_prev, [bits_prev], qps_prev, B_prev, M)
    fp = np.maximum(np.asarray(x["fp_bits"], float), 8)
    return float(CR.qhat_prev(pm, x["budget"][lv], fp, K, qeq, lcal)), float(r)


def chain(item):
    from rclib import env as E, policies as P
    seed, path, ipath, gids, lv, envkw, M, pm, mode = item
    CR = _cr()
    infos = P._infos(ipath)
    pol = P.make({"kind": "sb3", "path": path, "algo": "ppo"})
    rows, prev = [], None
    for gid in gids:
        x = infos[gid]
        src = "stored"
        if mode == "own" and prev is not None and prev[0] == gop_index(gid) - 1:
            qh, r = history(CR, x, lv, prev[1:], M, pm)
            x = dict(x, ctrl_qhat={**x["ctrl_qhat"], (lv, K): qh}, ctrl_r={**x["ctrl_r"], (lv, K): r})
            src = "own"
        elif mode == "own" and gop_index(gid) > 0:
            src = "stored (GOP n-1 not scored)"
        env = E.make_env({gid: x}, **envkw)
        env.force(gid, lv)
        obs, _ = env.reset()
        done = False
        while not done:
            obs, _, done, _, res = env.step(pol(env, obs))
        res = dict(res, seed=seed, hist_src=src, qhat=x["ctrl_qhat"][(lv, K)], r=x["ctrl_r"][(lv, K)])
        rows.append(res)
        prev = (gop_index(gid), np.maximum(np.asarray(x["fp_bits"], float), 8), res["qps"], float(res["bits"]),
                float(x["budget"][lv]))
    return rows


def stored_rows(enc, s, split):
    """R3 180k rows as stored: val = the F run's 180,993 checkpoint eval; test = the 11-16 test pass (eval_r3.py)."""
    if split == "test":
        return pickle.load(open(f"{ROOT}/results_v1/final/r3_test_{enc}.pkl", "rb"))[(s, "180k")]
    if split == "test2":   # exp_next/test2/eval_t2.py --model r3k5 --split test2 (same models, stored final4 history)
        return pickle.load(open(f"{OUT_T2}/r3k5_test2_{enc}.pkl", "rb"))[(s, K)]
    d = f"/scratch1/aayushso/rcwork_v1/{enc}_resh/results_rl/{RUN.format(s=s)}"
    return pickle.load(open(f"{d}/eval_ckpt.pkl", "rb"))["res"][(180993, "fixed", K, "val")]


def load_common():
    from rclib import config as C, runner
    assert C.RES and max(C.ACTIONS) == 6 and C.RES_RECAP == "bit"
    assert os.environ.get("RC_CTRL_SETTING") == "1.0:6:1.0:2:3:4:1:1:1:0:3"
    assert os.environ.get("RC_METRIC") == "dpsnr", "R3 rows are scored with RC_METRIC=dpsnr"
    ipath = os.path.join(runner.Stages("infos").dir, "infos_slim.pkl")
    infos = pickle.load(open(ipath, "rb"))
    M = json.load(open(f"{D}/rd/controller_model.json"))[C.CODEC]
    pm = json.load(open(f"{D}/base_prev_model.json"))[C.CODEC]["k"][str(K)]
    return C, runner, ipath, infos, M, pm


def formula_check(split):
    import pandas as pd
    C, _, _, infos, M, pm = load_common()
    CR = _cr()
    d = pd.concat(pd.read_parquet(f) for f in glob.glob(f"{ROOT}/results_v1/controller_real/{'t2final4' if split == 'test2' else 'final4'}_{C.CODEC}_{split}_*.parquet"))
    d = d[d.k == K]
    d["gid"] = d.clip_id + "@" + (30 * d.gop).astype(str)
    byk = {(r.clip_id, int(r.gop), int(r.level_q0)): r for r in d.itertuples()}
    eq, er, n = 0.0, 0.0, 0
    for r in d.itertuples():
        if r.gid not in infos or not r.has_prev:
            continue
        p = byk[(r.clip_id, int(r.gop) - 1, int(r.level_q0))]
        x, lv = infos[r.gid], int(r.level_q0)
        pg = f"{p.clip_id}@{30 * int(p.gop)}"
        fp_prev = np.maximum(np.asarray(infos[pg]["fp_bits"], float), 8) if pg in infos else None
        if fp_prev is None:
            continue
        qh, rr = history(CR, x, lv, (fp_prev, list(p.qps), float(p.bits), float(p.budget_bits)), M, pm)
        eq = max(eq, abs(qh - x["ctrl_qhat"][(lv, K)]))
        er = max(er, abs(rr - x["ctrl_r"][(lv, K)]))
        n += 1
    print(f"formula check {C.CODEC}: {n} {split} (GOP, level) with history; max |qhat diff| {eq:.2e}, max |r diff| {er:.2e}")
    assert n > 0 and eq < 1e-6 and er < 1e-6, "recomputed history does not match the replayed values"


def run(mode, clips, seeds, workers, split):
    C, runner, ipath, infos, M, pm = load_common()
    assert ("rcwork_t2" in C.WORK) == (split == "test2"), f"RC_WORK {C.WORK} does not fit split {split}"
    mean = json.load(open(SM))[f"{C.CODEC}|{K}|pooled"]
    envkw = {"k": K, "mode": "fixed", "drop": ("level",), "prior": False, "extra": "f4", "res_mean": mean,
             "k_sampler": None}
    byclip = {}
    for g, x in infos.items():
        if x["gop"]["split"] == split:
            byclip.setdefault(g.rsplit("@", 1)[0], []).append(g)
    cl = sorted(byclip)[:clips] if clips else sorted(byclip)
    items, stored = [], {}
    for s in seeds:
        d = os.path.join(C.results_dir("rl"), RUN.format(s=s))
        stored[s] = {(r["gid"], r["budget"]): r for r in stored_rows(C.CODEC, s, split)}
        for c in cl:
            for lv in C.BUDGET_QPS:
                items.append((s, f"{d}/model_180993.zip", ipath, sorted(byclip[c], key=gop_index), lv, envkw, M, pm,
                              mode))
    out = runner.pmap(chain, items, workers, desc=f"seqhist {mode} {C.CODEC}")
    res = {s: [] for s in seeds}
    for rs in out:
        for r in rs:
            res[r["seed"]].append(r)
    same = tot = 0
    for s, rows in res.items():
        for r in rows:
            st = stored[s][(r["gid"], r["budget"])]
            ok = abs(r["score"] - st["score"]) < 1e-9 and list(r["qps"]) == list(st["qps"])
            same, tot = same + ok, tot + 1
            if not ok and tot - same <= 6:
                print("  mismatch", s, r["gid"], r["budget"], f"score {r['score']:.4f} vs {st['score']:.4f}",
                      "qps", list(r["qps"])[:8], "vs", list(st["qps"])[:8])
    print(f"{mode} {C.CODEC}: rows equal to the stored {split} rows {same}/{tot}"
          + ("  (must be all for --mode stored)" if mode == "stored" else ""))
    if mode == "stored":
        assert same == tot
        return
    bad = [(s, r["gid"], r["budget"]) for s, rows in res.items() for r in rows if r["hist_src"] != "own" and not (
        abs(r["score"] - stored[s][(r["gid"], r["budget"])]["score"]) < 1e-9
        and list(r["qps"]) == list(stored[s][(r["gid"], r["budget"])]["qps"]))]
    print(f"episodes without own history reproduce the stored rows: {'all' if not bad else bad[:5]}")
    assert not bad, "an episode with the stored history differs from the stored row"
    out = OUT_T2 if split == "test2" else OUT
    os.makedirs(out, exist_ok=True)
    dest = f"{out}/seqhist_{mode}_{split}_{C.CODEC}{'_check' if clips else ''}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    pickle.dump(res, open(dest, "wb"))
    print(f"-> {dest}")


def report(split):
    assert split != "test2", "test2 is reported by exp_next/test2/report.py"
    import pandas as pd
    os.environ["RC_METRIC"] = "dpsnr"
    sys.path.insert(0, f"{ROOT}/exp_next/final")
    import report as R
    from shift_report import boot, fmt
    L = [f"# R3 with its own previous-GOP history ({split}; exp_next/fw/seq_history.py)", "",
         "R3 k5, 180k model, seeds 3-5; 'stored' = final4's GOP n-1 history as replayed in every R3 number so far, "
         "'own' = computed from R3's own encode of GOP n-1 (sequential per clip and level). 100 dB cap, hole excluded. "
         "Rule (exp_next/fw/PLAN.md): |pooled diff| <= 0.02 dB -> one sentence; larger -> escalate.", ""]
    if split == "test":
        L += ["**POST-HOC deployment-faithful re-measurement on test (Aayush OK 11-17, option 1 after the val escalation):** "
              "the frozen R3 models of the 11-16 test pass, same test episodes, run in clip order with R3's own GOP n-1 "
              "history; no training, no choices. The pre-registered primary (final4's history) is unchanged.", ""]
    else:
        L += ["EXPLORATORY (val).", ""]
    allp = []
    for enc in ("x264", "x265"):
        f = f"{OUT}/seqhist_own_{split}_{enc}.pkl"
        if not os.path.exists(f):
            L.append(f"- {enc}: not run")
            continue
        S = R.Scorer(enc, cap=True)
        own = pickle.load(open(f, "rb"))
        st = {s: stored_rows(enc, s, split) for s in own}
        rows = []
        for lab, src in (("own", own), ("stored", st)):
            for s, rr in src.items():
                for r in rr:
                    row = S.row(lab, r["gid"], r["budget"], K, r["bits"], r["psnr"], s)
                    row["hist_src"] = r.get("hist_src", "stored")
                    rows.append(row)
        rows += [r for r in R.load_final4_k(enc, split, S) if r["k"] == K]
        x = pd.DataFrame(rows)
        x = x[~x.hole]
        key = ["gid", "clip", "level", "cls"]
        p = x.groupby(key + ["method"]).score.mean().unstack("method").reset_index().dropna()
        p["enc"] = enc
        allp.append(p)
        n_own = (x[x.method == "own"].hist_src == "own").mean()
        L += [f"## {enc}", "",
              f"- own - stored history, pooled: {fmt(boot(p.own - p.stored, p['clip']))} (n {len(p)}; "
              f"{100 * n_own:.0f} % of episodes used their own GOP n-1)",
              "- by class: " + "; ".join(f"{c} {fmt(boot(q.own - q.stored, q['clip']))}" for c, q in p.groupby("cls")),
              "- by level: " + "; ".join(f"L{lv} {(q.own - q.stored).mean():+.3f}" for lv, q in p.groupby("level")),
              f"- R3 (stored history) - final4: {fmt(boot(p.stored - p.final4, p['clip']))}",
              f"- **R3 (own history) - final4: {fmt(boot(p.own - p.final4, p['clip']))}**",
              "- R3 (own history) - final4 by class: " + "; ".join(
                  f"{c} {fmt(boot(q.own - q.final4, q['clip']))}" for c, q in p.groupby("cls")),
              "", pd.DataFrame([{"history": m, **R.dec(q)} for m, q in x.groupby("method")]).round(3).to_markdown(index=False), ""]
    if len(allp) == 2:
        p = pd.concat(allp)
        p["c2"] = p.enc + ":" + p["clip"]
        L += [f"- **Both encoders pooled: own - stored {fmt(boot(p.own - p.stored, p.c2))}**", ""]
        if split == "test":
            L.append("(pooled over encoders for the history effect only; R3 - final4 is per encoder, as pre-registered)")
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/seqhist_{split}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--formula", action="store_true")
    ap.add_argument("--mode", choices=("own", "stored"))
    ap.add_argument("--clips", type=int, default=0)
    ap.add_argument("--seeds", default="3,4,5")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--split", default="val", choices=("val", "test", "test2"))   # test2: run only (report in exp_next/test2)
    a = ap.parse_args()
    if a.report:
        return report(a.split)
    if a.formula:
        return formula_check(a.split)
    run(a.mode, a.clips, [int(s) for s in a.seeds.split(",")], a.workers, a.split)


if __name__ == "__main__":
    main()
