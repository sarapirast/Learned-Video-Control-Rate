"""o[2] ablation, evaluation only (Aayush 11-13). Observation slot o[2] = (budget level != 24) is a bit of clip-level
hindsight under v1's clip-mean budgets (B = clip mean of constant-QP-L bits); every learner saw it in training. Re-run
stored policies on val with o[2] zeroed (env drop group "level") and compare with their stored val rows.

Groups (env set by the caller, checked here):
  R2   RC_ARM=res RC_RES_RANGE=6 RC_CTRL_SETTING=<final4> RC_WORK=rcwork_v1/<enc>_resh   res_k<k>_fixed_f4_lam0.17_st180k_r6_s<s>
  R1   RC_ARM=res (range 3)       RC_CTRL_SETTING=<final4> RC_WORK=rcwork_v1/<enc>_resh   res_k<k>_fixed_lam0.17_st180k_s<s>
  L540 RC_ARM=lfq RC_ACT_RANGE=10                          RC_WORK=rcwork_v1/<enc>_lfqp   cql_ppo_k<k>_fixed_st540k_s<s>
All with RC_METRIC=dpsnr.

  python exp_next/o2/o2_eval.py --group R2 [--ks 0,5] [--seeds 0,1,2]
  python exp_next/o2/o2_eval.py --group R2 --check 4     unmasked, first 4 val GOPs: must equal the stored rows
  --arm standin (Aayush 11-13): o[2] = 1 if final4's frame-0 planning QP >= 27 else 0 (causal stand-in; table from
  f4_level0.py) instead of zeroing it (which tells the policy every GOP is level 24).
Out: results_v1/next/o2/o2_<group>_<enc>[_standin].pkl = {(k, seed): rows} (never overwritten)
"""
import argparse
import os
import pickle
import sys
import time

sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C, policies as P, runner  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
OUT = f"{ROOT}/results_v1/next/o2"
TMPL = {"R2": "res_k{k}_fixed_f4_lam0.17_st180k_r6_s{s}", "R1": "res_k{k}_fixed_lam0.17_st180k_s{s}",
        "L540": "cql_ppo_k{k}_fixed_st540k_s{s}"}


def check_env(group):
    w = os.environ["RC_WORK"]
    if group in ("R1", "R2"):
        assert C.RES and w.endswith("_resh"), (C.ARM, w)
        assert max(C.ACTIONS) == (6 if group == "R2" else 3), C.ACTIONS
        assert os.environ.get("RC_CTRL_SETTING") == "1.0:6:1.0:2:3:4:1:1:1:0:3"
    else:
        assert C.LFQ_LEARN and w.endswith("_lfqp") and max(C.ACTIONS) == 10, (C.ARM, w, C.ACTIONS)
    assert os.environ.get("RC_METRIC") == "dpsnr" and not getattr(C, "RES_RECAP", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", required=True, choices=tuple(TMPL))
    ap.add_argument("--ks", default="0,5")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--check", type=int, default=0)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--arm", default="zero", choices=("zero", "standin"))
    a = ap.parse_args()
    check_env(a.group)
    rl = C.results_dir("rl")
    infos_st = runner.Stages("infos")
    iname = "infos_learn" if C.LFQ_LEARN else "infos"
    ipath = os.path.join(infos_st.dir, f"{iname}_slim.pkl")          # the file rl.py evaluated with
    assert os.path.exists(ipath), ipath
    infos = pickle.load(open(ipath, "rb"))
    val = sorted(g for g, x in infos.items() if x["gop"]["split"] == "val")
    dest = f"{OUT}/o2_{a.group}_{C.CODEC}{'_standin' if a.arm == 'standin' else ''}.pkl"
    o2 = None
    if a.arm == "standin":
        lv0 = pickle.load(open(f"{OUT}/f4_level0_{C.CODEC}.pkl", "rb"))
        o2 = {key: float(v >= 27) for key, v in lv0.items()}
    if not a.check:
        assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    res = {}
    for k in [int(x) for x in a.ks.split(",")]:
        for s in [int(x) for x in a.seeds.split(",")]:
            run = TMPL[a.group].format(k=k, s=s)
            ev = pickle.load(open(os.path.join(rl, run, "eval.pkl"), "rb"))
            ra = ev["args"]
            assert ra["k"] == k and ra["mode"] == "fixed" and not ra["prior"], ra
            drop = tuple(x for x in ra["drop"].split(",") if x)
            assert "level" not in drop
            envkw = {"k": k, "mode": "fixed", "prior": ra["prior"], "extra": ra.get("extra") or "", "k_sampler": None}
            stored = {(r["gid"], r["budget"]): r for r in ev["res"][("fixed", k, "val")]}
            t0 = time.time()
            if a.check:
                ids = val[:a.check]
                rows = P.evaluate(ev["spec"], ipath, ids, workers=a.workers, desc=f"check {run}", drop=drop, **envkw)
                ok = sum(abs(r["score"] - stored[(r["gid"], r["budget"])]["score"]) < 1e-9 and
                         list(r["qps"]) == list(stored[(r["gid"], r["budget"])]["qps"]) for r in rows)
                print(f"check {C.CODEC} {run}: unmasked reproduces stored val rows {ok}/{len(rows)}", flush=True)
                continue
            arm = {"drop": drop + ("level",)} if a.arm == "zero" else {"drop": drop, "o2_table": o2}
            rows = P.evaluate(ev["spec"], ipath, val, workers=a.workers, desc=f"o2 {a.arm} {run}", **arm, **envkw)
            assert {(r["gid"], r["budget"]) for r in rows} == set(stored)
            res[(k, s)] = rows
            print(f"{C.CODEC} {run}: {len(rows)} val episodes, arm {a.arm}, {time.time() - t0:.0f}s", flush=True)
    if a.check:
        return
    os.makedirs(OUT, exist_ok=True)
    with open(dest + ".part", "wb") as f:
        pickle.dump(res, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(dest + ".part", dest)
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
