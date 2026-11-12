"""D35: the D34 stream policies and baselines on the fresh long-film test set (tools/fresh_streams.py). Nothing is
trained or tuned here: policies come from the v1 work dir (RC_V1WORK), the rule's settings and c0 from its v1
val tuning (results_stream/baselines.pkl). Streams = windows of N consecutive GOPs inside each 32-GOP film segment,
N in NS, stride N / 2; budgets = s x sum of the GOPs' segment-mean budgets at q0 in {24, 30, 36, 42}, s in
{0.85, 1, 1.18}. Clusters for the CIs = film segments (12).

  RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_fresh/x265 RC_V1WORK=/scratch1/pbanga/rcwork_v1/x265 \
      python experiments/stream_fresh.py [--n 8] [--report]
"""
import argparse
import glob
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import stream_rl as S  # noqa: E402
from rclib import clipenv as CE, config as C, streamenv as SE  # noqa: E402

V1WORK = os.environ.get("RC_V1WORK", f"/scratch1/pbanga/rcwork_v1/{C.CODEC}")
NS = (8, 16, 32)
OUT = C.results_dir("stream_fresh")
REPORTS = os.path.join(C.PROJECT, "results", "fresh_stream", C.CODEC)
METHODS = ("bc_ppo", "ppo", "bc_ppo_lag", "bc")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def cases(infos, n):
    by = {}
    for g, x in infos.items():
        by.setdefault(x["gop"]["clip"], []).append((x["gop"]["start"], g))
    out = []
    for c, lst in sorted(by.items()):
        lst = [g for _, g in sorted(lst)]
        for i in range(0, len(lst) - n + 1, max(1, n // 2)):
            out += [("clip", c, tuple(lst[i:i + n]), q0, s) for q0 in SE.LEVELS for s in SE.EVAL_S]
    return out


def evaluate(act, infos, n, look, c0, margin=1.0, mode="rule", rp=None):
    env = SE.StreamEnv(infos, list(infos), look=look, c0=c0, margin=margin, mode=mode, rp=rp, n=n)
    rows = []
    for kind, grp, st, q0, s in cases(infos, n):
        env.force(st, q0, s)
        o, _ = env.reset()
        if act == "hindsight":
            for q in SE.hindsight(env.tabs, env.B):
                o, _, done, _, res = env.step(SE.ZERO, q=int(q))
        else:
            done = False
            while not done:
                o, _, done, _, res = env.step(act(o))
        rows.append({**res, "kind": kind, "group": grp})
    return rows


def run(n):
    from stable_baselines3 import PPO
    torch.set_num_threads(1)
    infos = S.load_infos()
    v1 = pickle.load(open(os.path.join(V1WORK, "results_stream", "baselines.pkl"), "rb"))
    c0 = v1["c0"]
    p = os.path.join(OUT, f"n{n}.pkl")
    R = pickle.load(open(p, "rb")) if os.path.exists(p) else {}
    zero = lambda o: SE.ZERO  # noqa: E731
    for (mode, look), t in v1["tune"].items():
        k = (mode, look, 0)
        if k not in R:
            R[k] = evaluate(zero, infos, n, look, c0, t["best"][0], mode, t["rp"])
            log(f"n={n} {mode} L={look}: {np.mean([r['score'] for r in R[k]]):+.3f} dB")
    if ("hindsight", -1, 0) not in R:
        R[("hindsight", -1, 0)] = evaluate("hindsight", infos, n, 0, c0)
        log(f"n={n} hindsight: {np.mean([r['score'] for r in R[('hindsight', -1, 0)]]):+.3f} dB")
    for m in METHODS:
        for L in (0, 2):
            for d in sorted(glob.glob(os.path.join(V1WORK, "results_stream", f"{m}_L{L}_s*"))):
                seed = int(d.rsplit("_s", 1)[1])
                k = (m, L, seed)
                if k in R or not os.path.exists(os.path.join(d, "model.zip")):
                    continue
                pol = PPO.load(os.path.join(d, "model.zip"), device="cpu").policy
                R[k] = evaluate(lambda o: int(pol.predict(o, deterministic=True)[0]), infos, n, L, c0)
                log(f"n={n} {m} L={L} s{seed}: {np.mean([r['score'] for r in R[k]]):+.3f} dB")
        pickle.dump(R, open(p, "wb"))
    pickle.dump(R, open(p, "wb"))


def report():
    lines = [f"# Fresh long-film streams ({C.CODEC}, Elephants Dream + Tears of Steel, never in v1 train)", "",
             "Policies and rule settings from D34 (v1 train / val), applied unchanged. Score = dPSNR_B - 0.17 dB per 1 % "
             "over on the stream's pooled PSNR. 'vs rule' = paired difference to the tuned rule at the same lookahead, "
             "95 % cluster bootstrap over the 12 film segments, seeds averaged.", ""]
    for n in NS:
        p = os.path.join(OUT, f"n{n}.pkl")
        if not os.path.exists(p):
            continue
        R = pickle.load(open(p, "rb"))
        F = {}
        for (m, L, seed), rows in R.items():
            F.setdefault((m, L), []).append(rows)
        F = {k: S.frame(v) for k, v in F.items()}
        hs = F[("hindsight", -1)]
        rows = []
        for (m, L), df in sorted(F.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            ref = F.get(("rule", max(L, 0)))
            r = {"method": m, "L": L, "seeds": int(df.n_seeds.iloc[0]), "cases": len(df), "score (dB)": df.score.mean(),
                 "dPSNR_B": df.dpsnr.mean(), "use": f"{100 * df.use.mean():.1f}%",
                 ">1% over": f"{100 * df.over.mean():.0f}%", "s=1": df[df.s == 1.0].score.mean()}
            if m != "rule" and ref is not None:
                t = S.cboot(df.score.values - ref.loc[df.index].score.values, df.group.values)
                r["vs rule (same L)"] = f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"
                gap = hs.score.mean() - ref.score.mean()
                r["share of ceiling gap"] = (df.score.mean() - ref.score.mean()) / gap if gap > 0 else np.nan
            rows.append(r)
        lines += [f"## Streams of {n} GOPs", "", pd.DataFrame(rows).round(3).to_markdown(index=False), ""]
    os.makedirs(REPORTS, exist_ok=True)
    out = os.path.join(REPORTS, "fresh_stream_report.md")
    open(out, "w").write("\n".join(lines))
    print("\n".join(lines))
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report()
    else:
        for n in ([a.n] if a.n else NS):
            run(n)
