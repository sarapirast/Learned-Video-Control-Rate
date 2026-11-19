"""Sara's PID-Lagrangian equal-reliability comparison (repo/p4/rule_margin_sweep.py) rescored in luma PSNR.

Final-report Table III row "PID-Lag. PPO - rule B at equal reliability" (+0.14 to +0.17 x264, +0.18 to +0.25 x265)
comes from repo/p4/README.md, scored with the 6:1:1 YUV PSNR of Pavneet's stream code. This repeats her comparison
(rule on its original tuning, margin 0.96, vs ppo_pid / bc_ppo_pid / bc_ppo_lag, 3 seeds, v1 test, L = 2 and 0) with
her code path (team repo pavneet_handoff/; her eval.pkl rows in repo/p4/models/<enc>/, bc_ppo_lag's in pavneet_handoff/artifacts; read only) and rescoring every row from its
per-GOP QPs in luma PSNR of pooled MSE, as exp_next/exp7/luma_rescore.py (Pavneet's D50 definition; luma MSE table
results_v1/final/luma_gop_mse.pkl, equal to his results_yrd/frames.pkl). No encodes, no training.
Check: the YUV numbers reproduce her README table.

  /scratch1/aayushso/envs/rc/bin/python -I exp_next/exp7/pid_luma.py
Out: results_v1/final/pid_luma.md
"""
import os
import pickle
import sys

import numpy as np

ROOT = "/scratch1/aayushso/ee599"
HO = f"{ROOT}/repo/pavneet_handoff"
OUT = f"{ROOT}/results_v1/final"
README = {  # repo/p4/README.md "Results (v1 test)", YUV
    ("x264", 2, "ppo_pid"): 0.158, ("x264", 0, "ppo_pid"): 0.136, ("x264", 2, "bc_ppo_pid"): 0.165,
    ("x264", 2, "bc_ppo_lag"): 0.165, ("x264", 0, "bc_ppo_lag"): 0.170,
    ("x265", 2, "ppo_pid"): 0.205, ("x265", 0, "ppo_pid"): 0.180, ("x265", 2, "bc_ppo_pid"): 0.240,
    ("x265", 2, "bc_ppo_lag"): 0.251, ("x265", 0, "bc_ppo_lag"): 0.188}


def ev(enc, work, name):
    """Her PID runs are in repo/p4/models/<enc>/<run>/; bc_ppo_lag (Pavneet's) in pavneet_handoff/artifacts."""
    for d in (f"{ROOT}/repo/p4/models/{enc}", f"{work}/results_stream"):
        if os.path.exists(f"{d}/{name}/eval.pkl"):
            return f"{d}/{name}/eval.pkl"
    raise FileNotFoundError(name)


def run(enc):
    os.environ.update(RC_CODEC=enc, RC_WORK=f"{HO}/artifacts/{enc}/v1", RC_V1="1", RC_BUDGETS="24,30,36,42",
                      RC_METRIC="dpsnr")
    sys.path.insert(0, f"{HO}/repo")
    for m in [m for m in sys.modules if m.split(".")[0] in ("rclib", "experiments")]:
        del sys.modules[m]
    from experiments import stream_rl as S
    from rclib import clipenv as CE, config as C, streamenv as SE
    infos = S.load_infos()
    mse = pickle.load(open(f"{OUT}/luma_gop_mse.pkl", "rb"))[enc]
    tabs = {}
    for g in infos:
        b, p = np.full(C.QP_MAX + 1, np.nan), np.full(C.QP_MAX + 1, np.nan)
        b[C.QPS] = infos[g]["curve"]["bits"]
        p[C.QPS] = 10 * np.log10(255.0 ** 2 / np.maximum(mse[g], 1e-10))
        tabs[g] = {"bits": b, "psnr": p}

    def luma(rows):
        out = []
        for x in rows:
            tb = [tabs[g] for g in x["stream"]]
            q = [int(v) for v in x["qps"]]
            tot = float(sum(t["bits"][v] for t, v in zip(tb, q)))
            assert abs(tot / x["bits"] - 1) < 1e-6, (x["stream"], tot, x["bits"])
            mp = float(CE.pooled([t["psnr"][v] for t, v in zip(tb, q)]))
            out.append({**x, "score": SE.stream_score(tb, tot, mp, x["budget"])[2]})
        return out

    base = pickle.load(open(os.path.join(C.WORK, "results_stream", "baselines.pkl"), "rb"))
    zero = lambda o: SE.ZERO  # noqa: E731
    res = []
    for look in (2, 0):
        rule = S.evaluate(zero, infos, "test", look, base["c0"], 0.96, "rule", base["tune"][("rule", look)]["rp"])
        groups = np.array([r["group"] for r in rule])
        over_rule = 100 * np.mean([r["over"] for r in rule])
        for run_ in ("ppo_pid", "bc_ppo_pid", "bc_ppo_lag"):
            if look == 0 and run_ == "bc_ppo_pid":
                continue
            seeds = [pickle.load(open(ev(enc, C.WORK, f"{run_}_L{look}_s{s}"), "rb"))["res"]["test"] for s in (0, 1, 2)]
            assert all(a["stream"] == b["stream"] and a["q0"] == b["q0"] and a["s"] == b["s"] for a, b in zip(rule, seeds[0]))
            over = 100 * np.mean([[r["over"] for r in rows] for rows in seeds])
            row = {"enc": enc, "L": look, "run": run_, "n": len(rule), "over_rl": over, "over_rule": over_rule}
            for lab, f in (("yuv", lambda r: r), ("luma", luma)):
                rl = np.mean([[r["score"] for r in f(rows)] for rows in seeds], axis=0)
                row[lab] = S.cboot(rl - np.array([r["score"] for r in f(rule)]), groups)
            assert abs(row["yuv"][0] - README[(enc, look, run_)]) < 6e-4, (enc, look, run_, row["yuv"][0])
            res.append(row)
    sys.path.remove(f"{HO}/repo")
    return res


def fmt(t):
    m, lo, hi = t
    return f"{m:+.3f} [{lo:+.3f}, {hi:+.3f}]" + (" *" if lo > 0 or hi < 0 else "")


def main():
    rows = run("x264") + run("x265")
    L = ["# PID-Lagrangian PPO vs the rule at equal reliability, in luma PSNR (exp_next/exp7/pid_luma.py)", "",
         "Sara's comparison (repo/p4/rule_margin_sweep.py: the rule on its original tuning at margin 0.96, ~6-7 % of "
         "streams > 1 % over, vs her constrained PPO runs, 3 seeds averaged, 8-GOP v1 test streams) with every row "
         "rescored from its per-GOP QPs in luma PSNR of pooled MSE (Pavneet's D50 definition). Rows: team repo "
         "p4/models/<enc>/ (PID runs) and pavneet_handoff/artifacts/<enc>/v1/results_stream (bc_ppo_lag, rule tuning); read only. No encodes. CIs: her cluster "
         "bootstrap (stream_rl.cboot); * = CI excludes 0. Over = % of streams > 1 % over budget (bits only, the same "
         "in both conventions).", "",
         "| enc | L | RL run - rule@0.96 | YUV 6:1:1 (her README) | luma | n | over: RL / rule (%) |",
         "|---|---:|---|---|---|---:|---|"]
    for r in rows:
        L.append(f"| {r['enc']} | {r['L']} | {r['run']} | {fmt(r['yuv'])} | {fmt(r['luma'])} | {r['n']} "
                 f"| {r['over_rl']:.1f} / {r['over_rule']:.1f} |")
    for enc in ("x264", "x265"):
        y = [r["yuv"][0] for r in rows if r["enc"] == enc]
        lu = [r["luma"][0] for r in rows if r["enc"] == enc]
        L.append(f"\n{enc} range over the rows above: YUV {min(y):+.2f} to {max(y):+.2f}; luma {min(lu):+.2f} to {max(lu):+.2f}")
    L += ["", "Check passed: every YUV mean reproduces her README table to 3 decimals; the luma tables' bits equal every "
          "row's stored bits."]
    open(f"{OUT}/pid_luma.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
