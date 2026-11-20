"""eval_test2_p1.py: evaluate my R3 models (k0 / k29, seeds 3-5, 180k) on Aayush's test2 set, evaluation only, along
exactly his test2 code path (p2_data/exp_next/test2/eval_ahhana.py, generalised to x264 and x265).

  x264 models: his PREREG secondary 10 (already evaluated by him) -> here a PARITY CHECK of this script against his stored
               rows results_v1/test2/r3k{0,29}a_test2_x264.pkl (identical QPs, bits, PSNR, scores required)
  x265 models: POST-HOC, NOT PRE-REGISTERED (agreed with Aayush 2026-11-19); only after my x265 val runs (seeds 3-5)
               are finished and scored on val (checked here) and the val parity line of this script is all equal

Same as eval_ahhana.py: rclib env (RC_ARM=res RC_RES_RANGE=6 RC_RES_RECAP=bit RC_METRIC=dpsnr, final4 setting), each
model's own mean[t] (my shifts file, asserted equal to Aayush's on shared keys), envkw as rl.py builds it for
evaluation, deterministic. RC_WORK must be Aayush's v1 work dir (--split val, parity with my stored eval.pkl rows) or his
test2 work dir /scratch1/aayushso/rcwork_t2/<enc>_resh (--split test2: test2 infos, flat GOPs already out). Both are
read in place; nothing of his is written (infos_slim.pkl exists in both). P2_DATA only matters for building infos, not
here. Backend: x264 may use the shim (identical to the CLI, 01 + parity below), x265 uses the CLI (his path exactly).
Gates: --split test2 refuses to run unless this script's own val parity file for the same (enc, model) exists with every
row equal; for x265 it also needs scored val rows for every seed (results/r3_kcurve/rows_final_x265.parquet).
--ckpt 20000: the same for each run's 20k checkpoint = its BC start (the actor is frozen during the 20k critic warm-up),
i.e. "BC alone" from the very network that R3 started from (val parity against the run's stored 20k evaluation).
Out: /scratch1/ahhanagu/ee599/results/test2_posthoc/r3k{0,29}[bc]_<split>_<enc>.pkl = {(seed, k): rows}, never
overwritten ("bc" = 20k checkpoint).
Run (via job_test2_eval.sbatch, env from 03_r3_lookahead/env.sh with P1_ENC):
  python -I eval_test2_p1.py --model k0 --split val      (parity gate)     then   --split test2
"""
import argparse
import json
import os
import pickle
import sys

REPO = "/scratch1/ahhanagu/ee599/Learned-Video-Control-Rate"
sys.path.insert(0, f"{REPO}/pavneet_pipeline")
sys.path.insert(0, REPO)                                     # x264env (shim backend)
from rclib import codec, config as C, policies as P, runner  # noqa: E402

B = "/scratch1/ahhanagu/ee599/results"
OUT = f"{B}/test2_posthoc"
AY = "/scratch1/aayushso/ee599/results_v1"
SM_AY = f"{AY}/next/exp5/shifts_smooth.json"
SM_MINE = {"x264": f"{B}/r3_kcurve/exp5/shifts_smooth.json", "x265": f"{B}/r3_kcurve/exp5_x265/shifts_smooth.json"}
RUNS = {"x264": f"{B}/r3_kcurve/work/results_rl", "x265": f"{B}/r3_kcurve/work_x265/results_rl"}
RUN = "res_k{k}_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s{s}"
F4 = "1.0:6:1.0:2:3:4:1:1:1:0:3"
MODELS = {"k0": 0, "k29": 29}
WORKS = {"val": "/scratch1/aayushso/rcwork_v1/{enc}_resh", "test2": "/scratch1/aayushso/rcwork_t2/{enc}_resh"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=tuple(MODELS), required=True)
    ap.add_argument("--split", choices=tuple(WORKS), required=True)
    ap.add_argument("--seeds", default="3,4,5")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--ckpt", choices=("final", "20000"), default="final",
                    help="final = R3 (180k model.zip); 20000 = the BC start (model_20000.zip)")
    a = ap.parse_args()
    enc, k = C.CODEC, MODELS[a.model]
    seeds = [int(x) for x in a.seeds.split(",")]
    # ---- same environment checks as eval_ahhana.py
    assert os.path.realpath(C.WORK) == os.path.realpath(WORKS[a.split].format(enc=enc)), (C.WORK, a.split)
    assert C.RES and max(C.ACTIONS) == 6 and C.RES_RECAP == "bit"
    assert os.environ.get("RC_CTRL_SETTING") == F4 and os.environ.get("RC_METRIC") == "dpsnr"
    assert enc == "x264" or codec.BACKEND == "cli", "x265: CLI backend only (the shim is x264 only)"
    sm, ay = json.load(open(SM_MINE[enc])), json.load(open(SM_AY))
    for key in set(sm) & set(ay):        # my shifts file = Aayush's on every shared key
        assert sm[key] == ay[key], f"shift files differ on {key}"
    mean = sm[f"{enc}|{k}|pooled"]
    tag = f"r3k{k}" + ("" if a.ckpt == "final" else "bc")
    os.makedirs(OUT, exist_ok=True)
    # ---- gates for test2
    if a.split == "test2":
        par = f"{OUT}/{tag}_val_{enc}.pkl"
        assert os.path.exists(par), f"run --split val first (parity gate): {par} missing"
        pv = pickle.load(open(par, "rb"))
        assert pv["parity"] == "all equal", f"val parity gate failed: {pv['parity']} rows equal"
        got = sorted(s for s, _ in pv["rows"])
        assert got == seeds, f"val parity file covers seeds {got}, test2 asked for {seeds}"
        if enc == "x265":
            sc = json.load(open(f"{B}/r3_kcurve/scored_runs_x265.json"))   # written by score_final_capped.py --enc x265
            got = sorted(s for m, kk, s, src in sc if m == "R3" and kk == k and src == "mine")
            assert got == seeds, f"x265 k{k}: val scores exist for seeds {got}, need {seeds} before test2"
    # ---- models and their env, as rl.py / eval_ahhana.py
    ipath = os.path.join(runner.Stages("infos").dir, "infos_slim.pkl")
    infos = pickle.load(open(ipath, "rb"))
    ids = sorted(g for g, x in infos.items() if x["gop"]["split"] == a.split)
    assert ids, f"no {a.split} GOPs in {ipath}"
    jobs = []
    for s in seeds:
        d = f"{RUNS[enc]}/{RUN.format(k=k, s=s)}"
        e = pickle.load(open(f"{d}/eval.pkl", "rb"))
        ra = e["args"]
        assert (ra["method"], ra["k"], ra["mode"], ra["drop"], ra["res_mean"], ra["extra"], ra["ppo_steps"], ra["lam"],
                ra["seed"], ra["prior"]) == ("res", k, "fixed", "level", "pooled", "f4", 180000, 0.17, s, False), ra
        envkw = {"k": k, "mode": "fixed", "drop": ("level",), "prior": False, "extra": "f4", "res_mean": mean,
                 "k_sampler": None}
        if a.ckpt == "final":
            model, ref = f"{d}/model.zip", e["res"][("fixed", k, "val")]
        else:                                # the BC start and its stored val evaluation (rl.py eval_ckpt.pkl)
            model = f"{d}/model_{a.ckpt}.zip"
            ref = pickle.load(open(f"{d}/eval_ckpt.pkl", "rb"))["res"][(int(a.ckpt), "fixed", k, "val")]
        jobs.append((s, {"kind": "sb3", "path": model, "algo": "ppo"}, envkw, ref))
    what = "R3" if a.ckpt == "final" else "BC start (20k checkpoint)"
    label = what + ": " + ("post-hoc, NOT pre-registered" if (enc == "x265" or a.ckpt != "final") and a.split == "test2" else
             "parity re-run of Aayush's PREREG secondary 10" if a.split == "test2" else "val parity gate")
    print(f"{enc} {tag} {a.split} ({label}): seeds {seeds}, {len(ids)} GOPs, backend {codec.BACKEND}, infos {ipath}")
    res, ok, tot = {}, 0, 0
    for s, spec, envkw, ref in jobs:
        rows = P.evaluate(spec, ipath, ids, workers=a.workers, desc=f"{enc} {tag} {a.split} s{s}", **envkw)
        res[(s, k)] = rows
        if a.split == "val":                 # parity with my stored val rows (rl.py's own evaluation)
            st = {(r["gid"], r["budget"]): r for r in ref}
            same = [(r["gid"], r["budget"]) in st and abs(r["score"] - st[(r["gid"], r["budget"])]["score"]) < 1e-9
                    and list(r["qps"]) == list(st[(r["gid"], r["budget"])]["qps"]) for r in rows]
            print(f"  s{s}: {sum(same)}/{len(same)} equal to my stored val rows")
            ok, tot = ok + sum(same), tot + len(same)
    dest = f"{OUT}/{tag}_{a.split}_{enc}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    out = {"rows": res, "label": label, "enc": enc, "k": k, "seeds": seeds, "backend": codec.BACKEND, "ckpt": a.ckpt}
    if a.split == "val":
        out["parity"] = "all equal" if ok == tot and tot > 0 else f"{ok}/{tot}"
        print(f"PARITY {enc} {tag}: {ok}/{tot} rows equal")
    pickle.dump(out, open(dest, "wb"))
    print(f"-> {dest} ({sum(len(r) for r in res.values())} rows)")


if __name__ == "__main__":
    main()
