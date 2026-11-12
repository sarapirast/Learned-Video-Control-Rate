"""Wide-budget study (D28): extend a finished two-budget work directory to more budget QPs without redoing what exists.

The source run ($RC_SRC_WORK, budgets 30/38) already has every GOP's constant-QP curve over QP 18-50, so a budget at any
QP in that range is free. What each new budget QP needs is the STATIC encode (reference of the relative reward) and the
hindsight search (ceiling, and offline data on train). The search of a budget does not depend on other budgets (its
seeds are 1000 x seed + b), so the source run's 30/38 results are reused as they are and only the new QPs are searched.

stages (run with RC_WORK = the new directory, RC_BUDGETS = all budget QPs, RC_SRC_WORK = the source directory)
  prep     link clips/gops/src, copy manifest and the scene-detector results
  infos    STATIC encodes at the new budget QPs for every GOP, merged into the source infos [sharded]; then --stage gather
  search   hindsight search at the new budget QPs on --split, merged with the source search [sharded]; then gather

  python experiments/widen.py --stage prep
  RC_NSHARDS=8 sbatch --array=0-7 ... widen.py --stage infos ;  widen.py --stage gather_infos
  RC_NSHARDS=24 sbatch --array=0-23 ... widen.py --stage search --split train ;  widen.py --stage gather --split train

--quick uses a few GOPs per split and a 40-encode search, written to the *_quick stage folders that every other script's
--quick mode reads.
"""
import os
import pickle
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import codec, config as C, data, metrics, runner, search  # noqa: E402
from rclib.runner import log  # noqa: E402
from experiments.infos import static_plan  # noqa: E402

SRC = os.environ.get("RC_SRC_WORK", "")
SRC_BUDGETS = tuple(int(q) for q in os.environ.get("RC_SRC_BUDGETS", "30,38").split(","))   # budgets the source run searched
QUICK_N = {"train": 6, "val": 3, "test": 3}


def cli(ap):
    ap.add_argument("--split", default="train")


def src_load(name, stage):
    with open(os.path.join(SRC, f"results_{name}", f"{stage}.pkl"), "rb") as f:
        return pickle.load(f)


def new_qps(info):
    return [b for b in C.BUDGET_QPS if b not in info["static"]]


def prep():
    assert SRC and os.path.isdir(SRC) and os.path.realpath(SRC) != os.path.realpath(C.WORK), "set RC_SRC_WORK"
    for d in ("clips", "gops", "src", "more"):
        s, t = os.path.join(SRC, d), os.path.join(C.WORK, d)
        if os.path.exists(s) and not os.path.lexists(t):
            os.symlink(os.path.realpath(s), t)
    shutil.copy(os.path.join(SRC, "manifest.json"), os.path.join(C.WORK, "manifest.json"))
    for q in ("", "_quick"):
        s = os.path.join(SRC, "results_scenes")
        t = os.path.join(C.WORK, f"results_scenes{q}")
        if os.path.isdir(s) and not os.path.exists(t):
            shutil.copytree(s, t)
    log(f"prep: {C.WORK} linked to {SRC}")


def subset(infos, quick):
    if not quick:
        return infos
    keep = []
    for s, n in QUICK_N.items():
        keep += sorted(g for g, x in infos.items() if x["gop"]["split"] == s)[:n]
    return {g: infos[g] for g in keep}


def _static(info):
    g = info["gop"]
    p, src = data.gop_path(g), data.gop_frames(g)
    curve = info["curve"]
    out = {"budget": {}, "static": {}}
    for b in new_qps(info):
        B = int(curve["bits"][list(curve["qps"]).index(b)])
        r = codec.encode(p, static_plan(b), src=src)
        out["budget"][b] = B
        out["static"][b] = {"bits": r["bits"], "psnr": r["psnr"], "total_bits": r["total_bits"],
                            "mean_psnr": r["mean_psnr"], "saving": float(metrics.saving(r["total_bits"], r["mean_psnr"], curve)),
                            "score": float(metrics.score(r["total_bits"], r["mean_psnr"], curve, B)), "over": r["total_bits"] > B}
    return g["id"], out


def infos_stage(a):
    st = runner.Stages("infos", a.quick)
    if a.stage == "infos":
        src = subset(src_load("infos", "infos"), a.quick)
        ids = sorted(src)[a.shard::a.nshards]
        st.run("widen", lambda: dict(runner.pmap(_static, [src[g] for g in ids], desc="static")), a.shard, a.nshards)
    if a.stage == "gather_infos" or (a.stage == "infos" and a.nshards == 1):
        st.gather("widen", a.nshards)
        add = st.load("widen")
        infos = subset(src_load("infos", "infos"), a.quick)
        for g, x in infos.items():
            x["budget"].update(add[g]["budget"])
            x["static"].update(add[g]["static"])
            assert set(x["static"]) == set(C.BUDGET_QPS), (g, sorted(x["static"]))
        st.save("infos", infos)
        slim = os.path.join(st.dir, "infos_slim.pkl")
        if os.path.exists(slim):
            os.remove(slim)
        log(f"infos: {len(infos)} GOPs with budgets {sorted(next(iter(infos.values()))['budget'])}")


def _search(args):
    info, n_eval, keep_logs = args
    r = search.search_gop(info, budgets=[b for b in C.BUDGET_QPS if b not in SRC_BUDGETS], n_eval=n_eval)
    if not keep_logs:
        for b in r:
            r[b].pop("logs")
    return info["gop"]["id"], r


def search_stage(a):
    st = runner.Stages("search", a.quick)
    stage = f"search_{a.split}"
    part = f"widen_{a.split}"
    if a.stage == "search":
        infos = runner.Stages("infos", a.quick).load("infos")
        ids = sorted(g for g, x in infos.items() if x["gop"]["split"] == a.split)[a.shard::a.nshards]
        items = [(infos[g], 40 if a.quick else 300, a.split == "train") for g in ids]
        st.run(part, lambda: dict(runner.pmap(_search, items, desc=part)), a.shard, a.nshards)
    if a.stage == "gather" or (a.stage == "search" and a.nshards == 1):
        st.gather(part, a.nshards)
        add = st.load(part)
        old = src_load("search", stage)
        out = {g: {**old[g], **add[g]} for g in add}
        for g, r in out.items():
            assert set(r) == set(C.BUDGET_QPS), (g, sorted(r))
        st.save(stage, out)
        log(f"{stage}: {len(out)} GOPs x budgets {sorted(next(iter(out.values())))}")


def main():
    a = runner.args(cli)
    if a.stage == "prep":
        return prep()
    if a.stage in ("infos", "gather_infos"):
        return infos_stage(a)
    if a.stage in ("search", "gather"):
        return search_stage(a)
    raise SystemExit(f"unknown stage {a.stage}")


if __name__ == "__main__":
    main()
