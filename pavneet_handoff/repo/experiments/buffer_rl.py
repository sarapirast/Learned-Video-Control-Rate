"""D38: RL rate control through a varying channel with a latency (sender-buffer) limit (rclib/bufenv.py). No encodes.

Baselines (--baselines, tuned on val before any learner is looked at; quality = luma PSNR, so the D34 rule is retuned):
  rule  D34 remaining-budget rule, buffer-blind (margin, slope, prior weight tuned on val under the D38 score)
  vbv   rule + VBV-style clamp on the predicted buffer level (psi, alpha tuned on val, rule part fixed)
  const best constant QP in hindsight (offline, buffer-blind)
Learner: ppo = feedforward PPO, offset -6..+6 on the vbv QP, reward = D38 score, stream length n ~ U{4..24} in training
(D36 showed this helps long streams; LSTM and quality feedback did not), random channels.
Evaluation: v1 val / test cases of D34 (n = 8) and n = 16 test playlists, each with a fixed channel per case.

  RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 python experiments/buffer_rl.py --baselines
  ... --method ppo --look 2 --seed 0 | --list runs/buffer.txt | --report
"""
import argparse
import glob
import itertools
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import stream_rl as S  # noqa: E402
from rclib import bufenv as BE, config as C, streamenv as SE, yrd  # noqa: E402

CFG = {"ppo_steps": 2_000_000, "n_envs": 16, "n_steps": 128, "batch": 256, "epochs": 5, "lr": 3e-4, "ent": 0.01}
MARGINS = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00)
QPDS = (5.0, 5.5, 6.0)
CWS = (1.0, 3.0)
PSIS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.9)
ALPHAS = (0.3, 0.6, 1.0)
V2_GRID = {"psi": (0.2, 0.35, 0.5, 0.7, 0.85, 1.0, 1.3), "beta": (0.3, 0.6, 1.0), "kappa": (0.0, 0.5, 1.5, 3.0),
           "alpha": (0.6, 1.0),
           "rmargin": (None, 0.9, 1.05, 1.2)}
MPC_GRID = {"gamma": (0.0025, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32), "H": (2, 4)}
TAG = BE.tag()
LOOKS = (0, 2) if not TAG else (2,)       # sweep variants: L = 2 only
OUT = C.results_dir("buffer" + (f"_{TAG}" if TAG else ""))
REPORTS = os.path.join(C.PROJECT, "results", "v1_buffer", C.CODEC, *((TAG,) if TAG else ()))
FRESH = os.environ.get("RC_FRESHWORK", f"/scratch1/pbanga/rcwork_fresh/{C.CODEC}")
log = S.log
_D = {}


def data():
    if not _D:
        infos = S.load_infos()
        _D.update(infos=infos, Y=yrd.load(infos))
    return _D["infos"], _D["Y"]


def playlist_cases(infos, Y, n=16, n_streams=150):
    env = BE.BufEnv(infos, S.split_ids(infos, "test"), Y, seed=12345, rp=None)
    out = []
    for j in range(n_streams):
        st = env._playlist(n)
        out += [("playlist", infos[st[0]]["gop"]["group"], st, q0, s) for q0 in SE.LEVELS for s in SE.EVAL_S]
    return out


def case_sets(quick=False):
    infos, Y = data()
    sets = {"val": S.cases(infos, "val"), "test": S.cases(infos, "test"), "test16": playlist_cases(infos, Y)}
    if quick:
        sets = {k: v[::10] for k, v in sets.items()}
    return sets


def make_env(split, look, c0, rp, base, psi=0.9, alpha=0.5, n=SE.N_GOP, bp=None):
    sp = "val" if split == "val" else "test"
    if split.startswith("fresh"):
        fr = pickle.load(open(os.path.join(FRESH, "results_infos", "infos_slim.pkl"), "rb"))
        env = BE.BufEnv(fr, list(fr), None, look=look, c0=c0, rp=rp, base=base, psi=psi, alpha=alpha, n=n,
                        nrange=None, split=sp, bp=bp)
    else:
        infos, Y = data()
        env = BE.BufEnv(infos, S.split_ids(infos, sp), Y, look=look, c0=c0, rp=rp, base=base, psi=psi, alpha=alpha,
                        n=n, nrange=None, split=sp, bp=bp)
    env.margin = rp["margin"] if rp and "margin" in rp else 1.0
    return env


def n_of(split):
    return {"test16": 16, "fresh16": 16, "fresh32": 32}.get(split, SE.N_GOP)


def mpc_channel():
    """Channel model the MPC baseline is given: the true AR(1) for synthetic channels; for traces an AR(1) on the
    normalised log rate fitted on the training traces (16-s windows)."""
    if BE.CHANNEL == "ar1":
        return BE.RHO, BE.SIGMA
    xs, ys = [], []
    for t in BE.trace_split("train"):
        for i in range(0, len(t) - 16, 8):
            m = np.maximum(t[i:i + 16] / max(t[i:i + 16].mean(), 1.0), BE.M_FLOOR)
            x = np.log(m / m.mean())
            xs += list(x[:-1])
            ys += list(x[1:])
    rho = float(np.polyfit(xs, ys, 1)[0])
    sig = float(np.std(np.array(ys) - rho * np.array(xs)))
    return rho, sig


def evaluate(act, cases, env, const=False):
    rows = []
    for kind, grp, st, q0, s in cases:
        env.force(st, q0, s)
        o, _ = env.reset()
        if hasattr(act, "reset"):
            act.reset()
        if const:
            tabs = env.tabs
            best = max(range(yrd.QLO, yrd.QHI + 1), key=lambda q: SE.stream_score(
                tabs, sum(t["bits"][q] for t in tabs), SE.CE.pooled([t["psnr"][q] for t in tabs]), env.B)[2])
            for _ in st:
                o, _, done, _, res = env.step(SE.ZERO, q=best)
        else:
            done = False
            while not done:
                o, _, done, _, res = env.step(act(o))
        rows.append({**res, "kind": kind, "group": grp})
    return rows


def zero(o):
    return SE.ZERO


def baselines(quick=False):
    p = os.path.join(OUT, "baselines.pkl" if not quick else "baselines_quick.pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    infos, Y = data()
    tr = S.split_ids(infos, "train")
    c0 = S.train_c0(infos)
    tabs = {g: SE.CE.gop_table(infos[g]) for g in tr}
    c0q = {q: SE.prior_c0(tabs, tr, q) for q in QPDS}
    cs = case_sets(quick)
    val = cs["val"][::3]                       # tuning subset (every third val case)
    R, tune = {}, {}
    for look in LOOKS:
        sc = {}
        for m, q, w in itertools.product(MARGINS, QPDS, CWS):
            rp = {"qpd": q, "cw": w, "c0": c0q[q]}
            env = make_env("val", look, c0, rp, "rule")
            env.margin = m
            sc[(m, q, w)] = np.mean([r["score"] for r in evaluate(zero, val, env)])
        m, q, w = max(sc, key=sc.get)
        rp = {"qpd": q, "cw": w, "c0": c0q[q], "margin": m}
        log(f"rule L={look}: best m{m} qpd{q} cw{w} val {sc[(m, q, w)]:+.3f}")
        sv = {}
        for psi, al in itertools.product(PSIS, ALPHAS):
            env = make_env("val", look, c0, rp, "vbv", psi, al)
            env.margin = m
            sv[(psi, al)] = np.mean([r["score"] for r in evaluate(zero, val, env)])
        psi, al = max(sv, key=sv.get)
        log(f"vbv L={look}: best psi{psi} alpha{al} val {sv[(psi, al)]:+.3f}")
        tune[look] = {"rule": sc, "vbv": sv, "rp": rp, "psi": psi, "alpha": al}
        for split, c in cs.items():
            for base in ("rule", "vbv"):
                env = make_env(split, look, c0, rp, base, psi, al, n=n_of(split))
                env.margin = m
                R[(base, look, split)] = evaluate(zero, c, env)
    for split, c in cs.items():
        env = make_env(split, 0, c0, tune[min(tune)]["rp"], "rule", n=n_of(split))
        R[("const", -1, split)] = evaluate(zero, c, env, const=True)
    out = {"rows": R, "tune": tune, "c0": c0}
    pickle.dump(out, open(p, "wb"))
    for k, v in R.items():
        log(k, f"score {np.mean([r['score'] for r in v]):+.3f} stall {np.mean([r['stall_pct'] for r in v]):.2f}%")
    return out


def baselines2(quick=False):
    """Stronger hand baselines at L = 2 (D39): vbv2 (buffer-tracking rule, 5 parameters) and mpc (vbv2 + a planner
    that knows the channel model), tuned on val after the D38 results were seen."""
    p = os.path.join(OUT, "baselines2.pkl" if not quick else "baselines2_quick.pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    bs = baselines(quick)
    tu, c0, look = bs["tune"][2], bs["c0"], 2
    cs = case_sets(quick)
    val = cs["val"][::3]
    sv = {}
    keys = list(V2_GRID)
    for vals in itertools.product(*V2_GRID.values()):
        bp = dict(zip(keys, vals))
        env = make_env("val", look, c0, tu["rp"], "vbv2", bp=bp)
        sv[vals] = np.mean([r["score"] for r in evaluate(zero, val, env)])
    best = dict(zip(keys, max(sv, key=sv.get)))
    log(f"vbv2: best {best} val {max(sv.values()):+.3f} (vbv was {max(tu['vbv'].values()):+.3f})")
    rho, sig = mpc_channel()
    sm = {}
    for g, H in itertools.product(*MPC_GRID.values()):
        bp = dict(best, gamma=g, H=H, rho=rho, sig=sig)
        env = make_env("val", look, c0, tu["rp"], "mpc", bp=bp)
        sm[(g, H)] = np.mean([r["score"] for r in evaluate(zero, val, env)])
    g, H = max(sm, key=sm.get)
    bmpc = dict(best, gamma=g, H=H, rho=rho, sig=sig)
    log(f"mpc: best gamma {g} H {H} (rho {rho:.2f} sigma {sig:.2f}) val {sm[(g, H)]:+.3f}")
    R = {}
    for split, c in cs.items():
        R[("vbv2", look, split)] = evaluate(zero, c, make_env(split, look, c0, tu["rp"], "vbv2", n=n_of(split), bp=best))
        R[("mpc", look, split)] = evaluate(zero, c, make_env(split, look, c0, tu["rp"], "mpc", n=n_of(split), bp=bmpc))
    out = {"rows": R, "vbv2": best, "mpc": bmpc, "val_vbv2": sv, "val_mpc": sm}
    pickle.dump(out, open(p, "wb"))
    for k, v in R.items():
        log(k, f"score {np.mean([r['score'] for r in v]):+.3f} stall {np.mean([r['stall_pct'] for r in v]):.2f}%")
    return out


def fresh_eval():
    """Default setting only: baselines and the trained L = 2 policies, unchanged, on the D35 fresh films (n = 16 / 32).
    Fresh films have no per-frame luma table, so quality there is our 6:1:1 YUV PSNR (comparisons within a set)."""
    from stable_baselines3 import PPO
    from experiments.stream_meta import fresh_cases
    fr = pickle.load(open(os.path.join(FRESH, "results_infos", "infos_slim.pkl"), "rb"))
    bs, b2 = baselines(), baselines2()
    tu, c0 = bs["tune"][2], bs["c0"]
    R = {}
    for n in (16, 32):
        cs = fresh_cases(fr, n)
        sp = f"fresh{n}"
        R[("rule", 2, sp)] = evaluate(zero, cs, make_env(sp, 2, c0, tu["rp"], "rule", n=n))
        R[("vbv", 2, sp)] = evaluate(zero, cs, make_env(sp, 2, c0, tu["rp"], "vbv", tu["psi"], tu["alpha"], n=n))
        R[("vbv2", 2, sp)] = evaluate(zero, cs, make_env(sp, 2, c0, tu["rp"], "vbv2", n=n, bp=b2["vbv2"]))
        R[("mpc", 2, sp)] = evaluate(zero, cs, make_env(sp, 2, c0, tu["rp"], "mpc", n=n, bp=b2["mpc"]))
        for d in sorted(glob.glob(os.path.join(OUT, "ppo*_L2_s*"))):
            if not os.path.exists(os.path.join(d, "model.zip")):
                continue
            meth = os.path.basename(d).rsplit("_L2_", 1)[0]
            seed = int(d.rsplit("_s", 1)[1])
            model = PPO.load(os.path.join(d, "model.zip"), device="cpu")
            base, bp = ("vbv2", b2["vbv2"]) if meth == "ppo_v2" else ("vbv", None)
            R[(meth, 2, sp, seed)] = evaluate(Actor(model), cs, make_env(sp, 2, c0, tu["rp"], base, tu["psi"],
                                                                         tu["alpha"], n=n, bp=bp))
        log(f"fresh n={n} done")
    pickle.dump(R, open(os.path.join(OUT, "fresh.pkl"), "wb"))
    return R


class Actor:
    def __init__(self, model):
        self.m = model

    def __call__(self, o):
        return int(self.m.predict(o, deterministic=True)[0])


def run(a):
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import DummyVecEnv
    name = f"{a.method}_L{a.look}_s{a.seed}"
    out = os.path.join(OUT, name)
    os.makedirs(out, exist_ok=True)
    if os.path.exists(os.path.join(out, "eval.pkl")):
        log(f"{name}: done")
        return
    torch.set_num_threads(2)
    t0 = time.time()
    bs = baselines(a.quick)
    tu = bs["tune"][a.look]
    base, bp = "vbv", None
    if a.method == "ppo_v2":
        base, bp = "vbv2", baselines2(a.quick)["vbv2"]
    infos, Y = data()
    tr = S.split_ids(infos, "train")

    def mk(i):
        e = BE.BufEnv(infos, tr, Y, look=a.look, c0=bs["c0"], seed=1000 * a.seed + i, rp=tu["rp"], base=base,
                      psi=tu["psi"], alpha=tu["alpha"], split="train", bp=bp)
        e.margin = tu["rp"]["margin"]
        return e
    venv = DummyVecEnv([(lambda i=i: mk(i)) for i in range(CFG["n_envs"])])
    pk = {"net_arch": {"pi": [128, 128], "vf": [128, 128]}, "activation_fn": torch.nn.ReLU}
    model = PPO("MlpPolicy", venv, learning_rate=CFG["lr"], n_steps=CFG["n_steps"], batch_size=CFG["batch"],
                n_epochs=CFG["epochs"], gamma=1.0, gae_lambda=0.95, ent_coef=CFG["ent"], policy_kwargs=pk,
                seed=a.seed, device="cpu", verbose=0)
    curve = []

    class Track(BaseCallback):
        def _on_step(self):
            for inf, d in zip(self.locals["infos"], self.locals["dones"]):
                if d and "score" in inf:
                    curve.append((self.num_timesteps, inf["score"], inf["stall_pct"], inf["over"], inf["use"]))
            if self.num_timesteps % 200_000 < CFG["n_envs"] and curve:
                r = np.array(curve[-2000:])
                log(f"  steps {self.num_timesteps}: score {r[:, 1].mean():+.3f} dB, stall {r[:, 2].mean():.2f}%, "
                    f"over {100 * r[:, 3].mean():.1f}% ({(time.time() - t0) / 60:.0f} min)")
            return True
    model.learn(total_timesteps=CFG["ppo_steps"], callback=Track())
    np.save(os.path.join(out, "train_curve.npy"), np.array(curve, float))
    model.save(os.path.join(out, "model.zip"))
    res = {}
    for split, c in case_sets(a.quick).items():
        env = make_env(split, a.look, bs["c0"], tu["rp"], base, tu["psi"], tu["alpha"], n=n_of(split), bp=bp)
        res[split] = evaluate(Actor(model), c, env)
        log(f"{name} {split}: score {np.mean([r['score'] for r in res[split]]):+.3f}, stall "
            f"{np.mean([r['stall_pct'] for r in res[split]]):.2f}%")
    pickle.dump({"args": vars(a), "cfg": CFG, "res": res, "seconds": time.time() - t0},
                open(os.path.join(out, "eval.pkl"), "wb"))
    log(f"{name}: {(time.time() - t0) / 60:.1f} min")


def frame(seeds):
    df = [pd.DataFrame([{k: x[k] for k in ("kind", "group", "score", "dpsnr", "use", "over", "stall_pct", "stalled")}
                        | {"key": (x["stream"], x["q0"], x["s"])} for x in rows]).set_index("key") for rows in seeds]
    m = df[0].copy()
    for c in ("score", "dpsnr", "use", "over", "stall_pct", "stalled"):
        m[c] = np.mean([d[c].astype(float).values for d in df], 0)
    m["n_seeds"] = len(df)
    return m


def report(quick=False):
    bs = baselines(quick)
    b2p = os.path.join(OUT, "baselines2.pkl" if not quick else "baselines2_quick.pkl")
    b2 = pickle.load(open(b2p, "rb")) if os.path.exists(b2p) else {"rows": {}}
    fp = os.path.join(OUT, "fresh.pkl")
    fresh = pickle.load(open(fp, "rb")) if os.path.exists(fp) else {}
    runs = {}
    for p in sorted(glob.glob(os.path.join(OUT, "*_L*_s*", "eval.pkl"))):
        r = pickle.load(open(p, "rb"))
        runs.setdefault((r["args"]["method"], r["args"]["look"]), []).append(r["res"])
    chan = (f"AR(1) rho {BE.RHO}, sigma {BE.SIGMA}" if BE.CHANNEL == "ar1" else
            "Belgium 4G/LTE throughput traces (split by file; train / val / test)")
    lines = [f"# D38/D39 buffer / live-channel rate control ({C.CODEC}{', ' + TAG if TAG else ''})", "",
             f"Channel {chan}, latency cap {BE.D_CAP} s at the mean rate. Score = luma "
             f"dPSNR_B - 0.17 dB per 1 % over - {BE.LAM_STALL} dB per 1 % of duration stalled. 'vs vbv' / 'vs rule' "
             "= paired differences at the same lookahead, 95 % cluster bootstrap, seeds averaged.", "",
             "Tuned on val: " + "; ".join(f"L={L}: rule {t['rp']}, vbv psi {t['psi']} alpha {t['alpha']}"
                                         for L, t in bs["tune"].items()), ""]
    if b2.get("vbv2"):
        lines += [f"D39 stronger baselines (L=2, tuned on val): vbv2 {b2['vbv2']}; mpc gamma {b2['mpc']['gamma']} "
                  f"H {b2['mpc']['H']} channel model rho {b2['mpc']['rho']:.2f} sigma {b2['mpc']['sig']:.2f}.", ""]
    sets = [("test", "v1 test (n = 8)"), ("val", "v1 val (n = 8)"), ("test16", "test playlists (n = 16)")]
    if fresh:
        sets += [("fresh16", "fresh films, n = 16 (6:1:1 YUV PSNR)"), ("fresh32", "fresh films, n = 32 (6:1:1 YUV PSNR)")]
    for split, title in sets:
        F = {}
        for (b, L, sp), rows in list(bs["rows"].items()) + list(b2["rows"].items()):
            if sp == split:
                F[(b, L)] = frame([rows])
        for (m, L), rs in runs.items():
            if all(split in r for r in rs):
                F[(m, L)] = frame([r[split] for r in rs])
        fr = {}
        for k, rows in fresh.items():
            if k[2] == split:
                fr.setdefault((k[0], k[1]), []).append(rows)
        for k, v in fr.items():
            F[k] = frame(v)
        rows = []
        for (m, L), df in sorted(F.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            r = {"method": m, "L": L, "seeds": int(df.n_seeds.iloc[0]), "cases": len(df), "score (dB)": df.score.mean(),
                 "dPSNR_B": df.dpsnr.mean(), "use": f"{100 * df.use.mean():.1f}%",
                 ">1% over": f"{100 * df.over.mean():.0f}%", "stall %": df.stall_pct.mean(),
                 "streams with stall": f"{100 * df.stalled.mean():.0f}%"}
            for ref in ("mpc", "vbv2", "vbv", "rule"):
                R0 = F.get((ref, L))
                if R0 is not None and m not in (ref, "const") and not (ref == "mpc" and m in ("rule", "vbv", "vbv2")):
                    ks = [k for k in df.index if k in R0.index]
                    t = S.cboot(df.loc[ks].score.values - R0.loc[ks].score.values, df.loc[ks].group.values)
                    r[f"vs {ref}"] = f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"
            rows.append(r)
        if rows:
            lines += [f"## {title}", "", pd.DataFrame(rows).round(3).to_markdown(index=False), ""]
    rep = REPORTS + ("_quick" if quick else "")
    os.makedirs(rep, exist_ok=True)
    open(os.path.join(rep, "buffer_report.md"), "w").write("\n".join(lines))
    print("\n".join(lines))


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="ppo", choices=("ppo", "ppo_v2"))
    ap.add_argument("--look", type=int, default=2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--list", default="")
    ap.add_argument("--baselines", action="store_true")
    ap.add_argument("--baselines2", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--steps", type=int, default=0)
    a = ap.parse_args()
    if a.quick:
        CFG.update(ppo_steps=a.steps or 20000)
        OUT = C.results_dir("buffer_quick" + (f"_{TAG}" if TAG else ""))
    if a.baselines:
        return baselines(a.quick)
    if a.baselines2:
        return baselines2(a.quick)
    if a.fresh:
        return fresh_eval()
    if a.report:
        return report(a.quick)
    if a.list:
        line = open(a.list).read().splitlines()[int(os.environ["SLURM_ARRAY_TASK_ID"])]
        q = a.quick
        a = ap.parse_args(line.split())
        a.quick = q
    run(a)


if __name__ == "__main__":
    main()
