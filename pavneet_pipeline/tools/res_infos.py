"""Build the residual arm's infos.pkl (RC_ARM=res; v1-data branch, P2 2026-11-09) from the lf arm's. No encodes.

Changes vs the lf infos (tools/lf_infos.py):
  - flat (grayscale) GOPs are dropped (data/v1/320x180/rd/flat_gops.csv, scripts/flat_gops_v1.py): their score is not
    meaningful under the mean-of-frames YUV PSNR and would wreck the reward
  - fp_bits = P2's first pass on P1's settings at QP 32 for this encoder (features/fp_bits.parquet), the input of
    P2's controller; it replaces the orig harness's first pass, which used Pavneet's settings
  - ctrl[(level, k)] = P2's controller run on its own with real encodes (results_v1/controller_real/final2_*,
    setting CTRL_SETTING): score, saving, over_pct, qps, bits. The env's reward baseline; tools/res_parity.py checks
    that the env with offset 0 replays these exactly.
  - base[(level, k)] = budgets.csv base_qp_est_k<k> (P2 2026-11-10): the controller's qhat for init = 1 settings
Options (P2 2026-11-10, tracker 30f): --tag/--setting pick another controller run (e.g. the dPSNR_B retune);
--metric dpsnr stores ctrl score = dPSNR_B - 0.17 x %over (the env's score under RC_METRIC=dpsnr) and ctrl dpsnr
(no over penalty, the Lagrangian reward's baseline); score_old keeps the original score.
Links clips/, gops/ and manifest.json from the lf work dir. Run with P2's project env (pyarrow):
  /scratch1/aayushso/envs/ee599/bin/python -I tools/res_infos.py <x264|x265> <lf RC_WORK> <res RC_WORK> \
      [--allow-missing SPLIT,...] [--force] [--tag final2] [--setting ...] [--metric score|dpsnr]
--allow-missing train: build without the train controller results (parity tests on val/test only; rl.py will fail).
"""
import argparse
import glob
import os
import pickle

import numpy as np
import sys

import pandas as pd

D = "/scratch1/aayushso/ee599/data/v1/320x180"
CTRL_DIR = "/scratch1/aayushso/ee599/results_v1/controller_real"
SETTING = "0.97:3.0:0.3:2.0:3.0:4.0:0.0:1.0:0.0:0.0"     # == rclib.config.CTRL_SETTING
LEVELS, KS = (24, 30, 36, 42), (0, 2, 5, 10, 29)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("enc", choices=("x264", "x265"))
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--allow-missing", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--tag", default="final2")
    ap.add_argument("--setting", default=SETTING)
    ap.add_argument("--metric", default="score", choices=("score", "dpsnr"))
    a = ap.parse_args()
    os.environ["RC_METRIC"] = a.metric
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from rclib import metrics
    allow = {s for s in a.allow_missing.split(",") if s}

    os.makedirs(os.path.join(a.dst, "results_infos"), exist_ok=True)
    for name in ("clips", "gops", "manifest.json"):
        if not os.path.lexists(os.path.join(a.dst, name)):
            os.symlink(os.path.realpath(os.path.join(a.src, name)), os.path.join(a.dst, name))
    out = os.path.join(a.dst, "results_infos", "infos.pkl")
    if os.path.exists(out) and not a.force:
        raise SystemExit(f"{out} exists; --force to rebuild")
    with open(os.path.join(a.src, "results_infos", "infos.pkl"), "rb") as f:
        infos = pickle.load(f)

    flat = pd.read_csv(f"{D}/rd/flat_gops.csv")
    flat = set(flat.gid[flat.flat])
    fp = pd.read_parquet(f"{D}/features/fp_bits.parquet").query("encoder == @a.enc and fp_qp == 32")
    fp = {k: v.sort_values("frame").fp_slice_bits.to_numpy(float) for k, v in fp.groupby(["clip_id", "gop"])}
    files = sorted(glob.glob(f"{CTRL_DIR}/{a.tag}_{a.enc}_*.parquet"))
    ctrl = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
    setting = ":".join(str(float(v)) for v in a.setting.split(":"))
    ctrl = ctrl[ctrl.setting == setting]
    assert len(ctrl), f"no episodes with setting {setting} in {a.tag}"
    dup = ctrl.duplicated(["clip_id", "gop", "level_q0", "k"]).sum()
    assert dup == 0, f"{dup} duplicate controller episodes"
    ctrl = {k: v.set_index(["level_q0", "k"]) for k, v in ctrl.groupby(["clip_id", "gop"])}

    res, missing = {}, {}
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
        c = ctrl.get(key)
        sp = x["gop"]["split"]
        if c is None or len(c) != len(LEVELS) * len(KS):
            missing[sp] = missing.get(sp, 0) + 1
            if sp not in allow:
                continue
            y["ctrl"] = {}
        else:
            y["ctrl"] = {}
            for (lv, k), r in c.iterrows():
                dq = float(metrics.dpsnr_budget(r.psnr_yuv, x["curve"], x["budget"][int(lv)]))
                sc = float(metrics.score(r.bits, r.psnr_yuv, x["curve"], x["budget"][int(lv)]))
                if a.metric == "score":
                    assert abs(sc - r.score) < 1e-6, (gid, lv, k, sc, r.score)
                y["ctrl"][(int(lv), int(k))] = {"score": sc, "score_old": float(r.score), "dpsnr": dq,
                                                "saving": float(r.saving), "over_pct": float(r.over_pct),
                                                "bits": float(r.bits), "qps": [int(q) for q in r.qps]}
            for lv in LEVELS:      # same budget as the env uses
                assert np.isclose(c.loc[(lv, 0), "budget_bits"], x["budget"][lv]), (gid, lv)
            hmode = int(float(setting.split(":")[10])) if len(setting.split(":")) == 11 else 0
            if hmode:   # previous-GOP history controller (tracker 31): what it used on this GOP (its own GOP n-1)
                y["ctrl_qhat"], y["ctrl_r"] = {}, {}
                for (lv, k), r in c.iterrows():
                    hp = bool(r.has_prev)
                    y["ctrl_qhat"][(int(lv), int(k))] = (float(r.qhat_prev) if hp and hmode in (1, 3)
                                                         else y["base"][(int(lv), int(k))])
                    y["ctrl_r"][(int(lv), int(k))] = float(r.r_prev) if hp and hmode in (2, 3) else 1.0
        res[gid] = y
    bad = {s: n for s, n in missing.items() if s not in allow}
    if bad:
        raise SystemExit(f"controller results missing for {bad} GOPs (run scripts/controller_real.py --tag final2), "
                         f"or pass --allow-missing")
    tmp = out + ".part"
    with open(tmp, "wb") as f:
        pickle.dump(res, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, out)
    slim = os.path.join(a.dst, "results_infos", "infos_slim.pkl")
    if os.path.exists(slim):       # rl.py caches a slim copy; it is stale now
        os.remove(slim)
    n = pd.Series([v["gop"]["split"] for v in res.values()]).value_counts().to_dict()
    print(f"{out}: {len(res)} GOPs {n}; dropped flat {sum(g in flat for g in infos)}; "
          f"without controller results: {missing or 'none'}")


if __name__ == "__main__":
    main()
