"""Phase G.1: scene detector study and refit, and what the hindsight teacher does around cuts.

stages
  fit      grid-search detector thresholds on TRAIN splices (known cut frames); precision/recall/F1 of each single
           detector and the combined one on TEST splices; detected-cut rates on natural GOPs by family
  apply    rewrite every GOP's cut/flash/fade/scene arrays in infos.pkl with the fitted detector (keeps a backup);
           must run before any RL stage (search does not use cut flags)
  teacher  mean hindsight-search offset (and gain) as a function of distance to a cut, on train
"""
import itertools
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, features, runner  # noqa: E402
from rclib.runner import log  # noqa: E402

GRID = {"hist": (0.15, 0.2, 0.3, 0.4, 0.5), "msad_ratio": (2.0, 3.0, 4.0), "fp_ratio": (1.8, 2.5, 3.5),
        "flash_back": (0.08, 0.12)}


def prf(pred, truth):
    tp = sum(len(set(p) & set(t)) for p, t in zip(pred, truth))
    npred, ntrue = sum(map(len, pred)), sum(map(len, truth))
    p = tp / npred if npred else 1.0
    r = tp / ntrue if ntrue else 1.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def detect(x, params, which="cut"):
    an = x["an"]
    px = {k: an[k] for k in ("hist_d", "msad", "mean", "sad", "spatial", "var")}
    px["hist"] = an["hist"] if "hist" in an else np.zeros((C.GOP, 48), np.float32)
    d = features.detect_cuts(px, x["fp_bits"], params)
    return np.flatnonzero(d[which]).tolist()


def fit(infos):
    tr = [x for x in infos.values() if x["gop"]["family"] == "splice" and x["gop"]["split"] == "train"]
    te = [x for x in infos.values() if x["gop"]["family"] == "splice" and x["gop"]["split"] == "test"]
    if not te:   # data v1: splices are train only; evaluate on natural test GOPs with reviewed cut labels instead
        te = [x for x in infos.values() if x["gop"]["split"] == "test" and "cuts" in x["gop"]]
    truth_tr = [x["gop"]["cuts"] for x in tr]
    best = None
    for vals in itertools.product(*GRID.values()):
        prm = dict(zip(GRID, vals))
        f = prf([detect(x, prm) for x in tr], truth_tr)[2]
        if best is None or f > best[0]:
            best = (f, prm)
    prm = best[1]
    out = {"params": prm, "train_f1": best[0], "test": {}}
    truth_te = [x["gop"]["cuts"] for x in te]
    for which in ("cut", "v_hist", "v_msad", "v_fp"):
        out["test"][which] = prf([detect(x, prm, which) for x in te], truth_te)
    nat = {}
    for x in infos.values():
        if x["gop"]["family"] != "splice":
            nat.setdefault(x["gop"]["family"], []).append(len(detect(x, prm)))
    out["natural_cuts_per_gop"] = {k: float(np.mean(v)) for k, v in nat.items()}
    out["natural_gops_with_cut"] = {k: float(np.mean(np.array(v) > 0)) for k, v in nat.items()}
    return out


def apply(st_infos, prm):
    p = st_infos.path("infos")
    bak = p + ".pre_scenefit"
    if not os.path.exists(bak):
        shutil.copy(p, bak)
    infos = st_infos.load("infos")
    for x in infos.values():
        an = x["an"]
        px = {k: an[k] for k in ("hist_d", "msad", "mean", "sad", "spatial", "var")}
        px["hist"] = an.get("hist", np.zeros((C.GOP, 48), np.float32))
        d = features.detect_cuts(px, x["fp_bits"], prm)
        an.update(d)
        an["scene"] = features.scene_ids(d["cut"])
    st_infos.save("infos", infos)
    slim = os.path.join(st_infos.dir, "infos_slim.pkl")
    if os.path.exists(slim):
        os.remove(slim)          # rebuilt by the next consumer
    return {"applied": prm}


def teacher(infos, search_train):
    """Mean best offset (actions in QP units) at distance d from a cut (d = frame - cut frame), vs no-cut GOPs."""
    by_d, base = {}, []
    for g, r in search_train.items():
        cuts = np.flatnonzero(infos[g]["an"]["cut"])
        for b, x in r.items():
            acts = np.array([C.ACTIONS[a] for a in x["best_acts"]])
            if len(cuts) == 0:
                base.append(acts)
                continue
            for c in cuts:
                for d in range(-3, 6):
                    if 0 <= c + d < C.GOP:
                        by_d.setdefault(d, []).append(acts[c + d])
    gain_cut = [r[b]["best_score"] - r[b]["static_score"] for g, r in search_train.items() for b in r
                if infos[g]["an"]["cut"].sum() > 0]
    gain_nocut = [r[b]["best_score"] - r[b]["static_score"] for g, r in search_train.items() for b in r
                  if infos[g]["an"]["cut"].sum() == 0]
    return {"offset_by_distance": {d: float(np.mean(v)) for d, v in sorted(by_d.items())},
            "offset_nocut_by_frame": np.mean(base, 0).tolist() if base else [],
            "gain_cut": float(np.mean(gain_cut)) if gain_cut else float("nan"),
            "gain_nocut": float(np.mean(gain_nocut)) if gain_nocut else float("nan"),
            "n_cut": len(gain_cut), "n_nocut": len(gain_nocut)}


def main():
    a = runner.args()
    st = runner.Stages("scenes", a.quick)
    ist = runner.Stages("infos", a.quick)
    if a.report:
        return report(st)
    if a.stage in (None, "fit"):
        st.run("fit", lambda: fit(ist.load("infos")))
    if a.stage in (None, "apply"):
        st.run("apply", lambda: apply(ist, st.load("fit")["params"]))
    if a.stage in (None, "teacher"):
        sst = runner.Stages("search", a.quick)
        if sst.done("search_train"):
            st.run("teacher", lambda: teacher(ist.load("infos"), sst.load("search_train")))
    report(st)


def report(st):
    lines = [f"# Scene analysis ({C.CODEC})", ""]
    if st.done("fit"):
        f = st.load("fit")
        lines += [f"Detector fitted on train splices: {f['params']} (train F1 {f['train_f1']:.3f})", "",
                  "| detector | precision | recall | F1 (test splices) |", "|---|---|---|---|"]
        lines += [f"| {k} | {p:.3f} | {r:.3f} | {f1:.3f} |" for k, (p, r, f1) in f["test"].items()]
        lines += ["", "Natural GOPs: detected cuts per GOP / share of GOPs with a cut:", ""]
        lines += [f"- {k}: {v:.3f} / {f['natural_gops_with_cut'][k]:.3f}" for k, v in f["natural_cuts_per_gop"].items()]
    if st.done("teacher"):
        t = st.load("teacher")
        lines += ["", "Hindsight teacher around cuts (mean QP offset on top of STATIC; negative = more bits):", "",
                  "| frame - cut | " + " | ".join(str(d) for d in t["offset_by_distance"]) + " |",
                  "|---" * (1 + len(t["offset_by_distance"])) + "|",
                  "| offset | " + " | ".join(f"{v:+.2f}" for v in t["offset_by_distance"].values()) + " |", "",
                  f"Search gain over STATIC: GOPs with a cut {t['gain_cut']:.2f} (n={t['n_cut']}), "
                  f"without {t['gain_nocut']:.2f} (n={t['n_nocut']})"]
    out = os.path.join(C.REPORTS, f"scenes{'_quick' if st.quick else ''}_report.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
