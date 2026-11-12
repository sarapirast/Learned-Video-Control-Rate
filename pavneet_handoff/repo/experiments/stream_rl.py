"""D34: stream-level rate control on dataset v1, scored in dB at the budget (rclib/streamenv.py). No encodes.

methods:  bc          imitate the hindsight per-GOP plan (offsets on the model QP)
          ppo         PPO from scratch, reward = score_db at the end of the stream
          bc_ppo      bc, then PPO fine-tuning
          bc_ppo_lag  bc_ppo with reward dPSNR_B - lam x %over, lam = 0.34 (2 x the metric's 0.17)
Baselines (--baselines, run once before any learner is looked at): equal split per GOP and the remaining-budget rule,
each with margin, rate-model slope and calibration prior weight tuned on val (grids MARGINS x QPDS x CWS), the best constant QP in hindsight and the hindsight per-GOP plan.

  RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 python experiments/stream_rl.py --baselines
  ... python experiments/stream_rl.py --method bc_ppo --look 2 --seed 0
  ... python experiments/stream_rl.py --list runs/stream.txt          # line $SLURM_ARRAY_TASK_ID of the list
  ... python experiments/stream_rl.py --report
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
from rclib import clipenv as CE, config as C, streamenv as SE  # noqa: E402

CFG = {"ppo_steps": 2_000_000, "n_envs": 16, "n_steps": 128, "batch": 256, "epochs": 5, "lr_scratch": 3e-4,
       "lr_ft": 1e-4, "ent": 0.01, "bc_eps": 20000, "bc_steps": 4000, "lam": 0.34}
MARGINS = (0.90, 0.92, 0.94, 0.96, 0.98, 1.00, 1.02, 1.04)
QPDS = (4.5, 5.0, 5.5, 6.0, 6.5)      # rule's rate-model slope, QP per doubling of bits
CWS = (0.5, 1.0, 3.0)                  # weight of the training prior in the rule's online calibration
LOOKS = (0, 2)
OUT = C.results_dir("stream")
REPORTS = os.environ.get("RC_REPORTS") or os.path.join(C.PROJECT, "results", "v1_stream", C.CODEC)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def load_infos():
    with open(os.path.join(C.WORK, "results_infos", "infos_slim.pkl"), "rb") as f:
        return pickle.load(f)


def split_ids(infos, s):
    return [g for g, x in infos.items() if x["gop"]["split"] == s and x["gop"]["family"] != "splice"]


def episodes(infos, split, n_mixed=100, n=SE.N_GOP):
    """Every window of n consecutive GOPs of one clip (stride 1; clustered by source group in the CIs) and n_mixed
    streams of n GOPs from n different clips (each its own cluster). Fixed per split."""
    by = {}
    for g in split_ids(infos, split):
        x = infos[g]["gop"]
        by.setdefault(x["clip"], []).append((x["start"], g))
    out = []
    for c, lst in sorted(by.items()):
        lst = [g for _, g in sorted(lst)]
        grp = infos[lst[0]]["gop"]["group"]
        out += [("clip", grp, tuple(lst[i:i + n])) for i in range(len(lst) - n + 1)]
    rng = np.random.default_rng({"train": 0, "val": 1, "test": 2}[split])
    clips = sorted(by)
    for j in range(n_mixed):
        cs = rng.choice(len(clips), n, replace=False)
        out.append(("mixed", f"mixed{j}", tuple(by[clips[i]][rng.integers(len(by[clips[i]]))][1] for i in cs)))
    return out


def cases(infos, split):
    return [(kind, grp, st, q0, s) for kind, grp, st in episodes(infos, split) for q0 in SE.LEVELS for s in SE.EVAL_S]


def evaluate(act, infos, split, look, c0, margin=1.0, mode="rule", rp=None):
    env = SE.StreamEnv(infos, split_ids(infos, split), look=look, c0=c0, margin=margin, mode=mode, rp=rp)
    rows = []
    for kind, grp, st, q0, s in cases(infos, split):
        env.force(st, q0, s)
        o, _ = env.reset()
        if act in ("hindsight", "const"):
            if act == "hindsight":
                plan = SE.hindsight(env.tabs, env.B)
            else:
                best = max(range(C.QP_MIN, C.QP_MAX + 1), key=lambda q: SE.stream_score(
                    env.tabs, sum(t["bits"][q] for t in env.tabs), CE.pooled([t["psnr"][q] for t in env.tabs]),
                    env.B)[2])
                plan = [best] * len(st)
            for q in plan:
                o, _, done, _, res = env.step(SE.ZERO, q=int(q))
        else:
            done = False
            while not done:
                o, _, done, _, res = env.step(act(o))
        rows.append({**res, "kind": kind, "group": grp})
    return rows


def train_c0(infos):
    return SE.StreamEnv(infos, split_ids(infos, "train")).c0


def baselines(infos):
    p = os.path.join(C.results_dir("stream"), "baselines.pkl")   # shared by --quick runs (baselines do not train)
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    c0 = train_c0(infos)
    B, tune = {}, {}
    zero = lambda o: SE.ZERO  # noqa: E731
    tr = split_ids(infos, "train")
    tabs = {g: CE.gop_table(infos[g]) for g in tr}
    c0q = {q: SE.prior_c0(tabs, tr, q) for q in QPDS}
    for mode in ("split", "rule"):
        for look in ((0,) if mode == "split" else LOOKS):
            val = {}
            for m in MARGINS:
                for q in QPDS:
                    for w in CWS:
                        rp = {"qpd": q, "cw": w, "c0": c0q[q]}
                        val[(m, q, w)] = np.mean([r["score"] for r in evaluate(zero, infos, "val", look, c0, m, mode, rp)])
            best = max(val, key=val.get)
            rp = {"qpd": best[1], "cw": best[2], "c0": c0q[best[1]]}
            tune[(mode, look)] = {"val": val, "best": best, "rp": rp}
            top = sorted(val.items(), key=lambda kv: -kv[1])[:5]
            log(f"{mode} L={look}: {len(val)} settings, val best " + "; ".join(
                f"m{k[0]:.2f} qpd{k[1]} cw{k[2]}: {v:+.3f}" for k, v in top))
            for s in ("val", "test"):
                B[(mode, look, s)] = evaluate(zero, infos, s, look, c0, best[0], mode, rp)
    for s in ("val", "test"):
        B[("const", -1, s)] = evaluate("const", infos, s, 0, c0)
        B[("hindsight", -1, s)] = evaluate("hindsight", infos, s, 0, c0)
        log(f"baselines {s} done")
    out = {"rows": B, "tune": tune, "c0": c0}
    pickle.dump(out, open(p, "wb"))
    return out


def bc_data(infos, c0, look, seed, n_eps):
    env = SE.StreamEnv(infos, split_ids(infos, "train"), look=look, c0=c0, seed=seed)
    X, Y = [], []
    for _ in range(n_eps):
        o, _ = env.reset()
        plan = SE.hindsight(env.tabs, env.B)
        for q in plan:
            a = int(np.clip(q - round(env.q_hat()), SE.ACTIONS[0], SE.ACTIONS[-1])) - SE.ACTIONS[0]
            X.append(o)
            Y.append(a)
            o, _, _, _, _ = env.step(a, q=int(q))
    return np.array(X), np.array(Y)


def train_bc(model, X, Y, steps, seed):
    torch.manual_seed(seed)
    pol = model.policy
    opt = torch.optim.Adam(pol.parameters(), 1e-3)
    Xt, Yt = torch.from_numpy(X).float(), torch.from_numpy(Y).long()
    for _ in range(steps):
        idx = torch.randint(len(Xt), (512,))
        _, logp, _ = pol.evaluate_actions(Xt[idx], Yt[idx])
        loss = -logp.mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        acc = (pol.get_distribution(Xt[:20000]).distribution.probs.argmax(1) == Yt[:20000]).float().mean()
    return float(acc)


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
    infos = load_infos()
    tr = split_ids(infos, "train")
    c0 = train_c0(infos)
    lam = CFG["lam"] if a.method.endswith("_lag") else 0.0
    venv = DummyVecEnv([(lambda i=i: SE.StreamEnv(infos, tr, look=a.look, c0=c0, seed=1000 * a.seed + i, lam=lam))
                        for i in range(CFG["n_envs"])])
    pk = {"net_arch": {"pi": [128, 128], "vf": [128, 128]}, "activation_fn": torch.nn.ReLU}
    scratch = a.method == "ppo"
    model = PPO("MlpPolicy", venv, learning_rate=CFG["lr_scratch"] if scratch else CFG["lr_ft"],
                n_steps=CFG["n_steps"], batch_size=CFG["batch"], n_epochs=CFG["epochs"], gamma=1.0, gae_lambda=0.95,
                ent_coef=CFG["ent"], policy_kwargs=pk, seed=a.seed, device="cpu", verbose=0)
    info = {"c0": c0, "lam": lam}
    if a.method.startswith("bc"):
        X, Y = bc_data(infos, c0, a.look, a.seed, CFG["bc_eps"])
        info["bc_acc"] = train_bc(model, X, Y, CFG["bc_steps"], a.seed)
        info["bc_label_hist"] = np.bincount(Y, minlength=len(SE.ACTIONS)).tolist()
        log(f"BC on {len(X)} steps: accuracy {info['bc_acc']:.3f}, labels {info['bc_label_hist']}")
    if a.method != "bc":
        curve = []

        class Track(BaseCallback):
            def _on_step(self):
                for inf, d in zip(self.locals["infos"], self.locals["dones"]):
                    if d and "score" in inf:
                        curve.append((self.num_timesteps, inf["score"], inf["over"], inf["use"]))
                if self.num_timesteps % 200_000 < CFG["n_envs"] and curve:
                    r = np.array(curve[-2000:])
                    log(f"  steps {self.num_timesteps}: score {r[:, 1].mean():+.3f} dB, over {100 * r[:, 2].mean():.1f}%,"
                        f" use {100 * r[:, 3].mean():.1f}%")
                return True
        model.learn(total_timesteps=CFG["ppo_steps"], callback=Track())
        np.save(os.path.join(out, "train_curve.npy"), np.array(curve, float))
    model.save(os.path.join(out, "model.zip"))
    pol = model.policy

    def act(o):
        return int(pol.predict(o, deterministic=True)[0])
    res = {s: evaluate(act, infos, s, a.look, c0) for s in ("val", "test")}
    for s, rows in res.items():
        log(f"{name} {s}: score {np.mean([r['score'] for r in rows]):+.3f} dB, dPSNR_B "
            f"{np.mean([r['dpsnr'] for r in rows]):+.3f}, use {100 * np.mean([r['use'] for r in rows]):.1f}%, "
            f"over {100 * np.mean([r['over'] for r in rows]):.1f}%")
    with open(os.path.join(out, "eval.pkl"), "wb") as f:
        pickle.dump({"args": vars(a), "cfg": CFG, "info": info, "res": res, "seconds": time.time() - t0}, f)


def cboot(d, groups, n=4000, seed=0):
    """Mean and 95 % cluster-bootstrap interval (clusters = source groups / mixed streams)."""
    u, inv = np.unique(groups, return_inverse=True)
    s, c = np.bincount(inv, d, len(u)), np.bincount(inv, minlength=len(u))
    w = np.random.default_rng(seed).multinomial(len(u), [1 / len(u)] * len(u), n)
    m = (w @ s) / (w @ c)
    return float(np.mean(d)), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def frame(seeds):
    df = [pd.DataFrame([{k: x[k] for k in ("kind", "group", "q0", "s", "score", "dpsnr", "use", "over_pct", "over")}
                        | {"key": (x["stream"], x["q0"], x["s"])} for x in rows]).set_index("key") for rows in seeds]
    m = df[0].copy()
    for c in ("score", "dpsnr", "use", "over_pct", "over"):
        m[c] = np.mean([d[c].astype(float).values for d in df], 0)
    m["n_seeds"] = len(df)
    return m


def report(split="test"):
    infos = load_infos()
    Bs = baselines(infos)
    R = {}
    names = {"split": "equal split per GOP (tuned m)", "rule": "remaining-budget rule (tuned m)",
             "const": "best constant QP (offline)", "hindsight": "hindsight per-GOP plan (offline)"}
    for k, rows in Bs["rows"].items():
        if k[2] == split:
            R[names[k[0]] + (f" L={k[1]}" if k[0] == "rule" else "")] = [rows]
    for p in sorted(glob.glob(os.path.join(OUT, "*", "eval.pkl"))):
        r = pickle.load(open(p, "rb"))
        R.setdefault(f"{r['args']['method']} L={r['args']['look']}", []).append(r["res"][split])
    F = {k: frame(v) for k, v in R.items()}
    hs = F[names["hindsight"]]
    rows = []
    for k, df in F.items():
        look = k.split("L=")[-1] if "L=" in k else "0"
        ref = F.get(f"{names['rule']} L={look}", F[f"{names['rule']} L=0"])
        r = {"method": k, "seeds": int(df.n_seeds.iloc[0]), "cases": len(df), "score (dB)": df.score.mean(),
             "dPSNR_B": df.dpsnr.mean(), "use": f"{100 * df.use.mean():.1f}%", ">1% over": f"{100 * df.over.mean():.0f}%",
             "mean over %": df.over_pct.mean(), "same-clip": df[df.kind == "clip"].score.mean(),
             "mixed": df[df.kind == "mixed"].score.mean(), "s=1": df[df.s == 1.0].score.mean()}
        if not k.startswith(names["rule"]):
            d = df.score.values - ref.loc[df.index].score.values
            t = cboot(d, df.group.values)
            r["vs rule (same L)"] = f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"
        gap = hs.score.mean() - ref.score.mean()
        r["share of ceiling gap"] = (df.score.mean() - ref.score.mean()) / gap if gap > 0 else np.nan
        rows.append(r)
    tune = "; ".join(f"{m} L={l}: margin {v['best'][0]}, QP/doubling {v['best'][1]}, prior weight {v['best'][2]}"
                     for (m, l), v in Bs["tune"].items())
    out = [f"# Stream-level rate control, dataset v1 ({C.CODEC}, {split})", "",
           f"Streams of {SE.N_GOP} IDR GOPs (every window of consecutive GOPs of a clip, plus 100 mixed streams) under one "
           f"budget = s x sum of the GOPs' v1 budgets at level q0, q0 in {SE.LEVELS}, s in {SE.EVAL_S}. Each step picks one "
           "GOP's constant QP (offset -6..+6 on the causal model QP); outcomes from the real constant-QP curves. Score = "
           "dPSNR_B - 0.17 dB per 1 % over (P2's metric) on the stream's pooled PSNR. 'vs rule' = paired difference to the "
           "tuned remaining-budget rule at the same lookahead, 95 % cluster bootstrap over source groups (mixed streams: "
           "each its own cluster), seeds averaged. 'share of ceiling gap' = (method - rule) / (hindsight - rule).", "",
           f"Margins tuned on val: {tune}.", "", pd.DataFrame(rows).round(3).to_markdown(index=False), ""]
    os.makedirs(REPORTS, exist_ok=True)
    p = os.path.join(REPORTS, f"stream_report_{split}.md")
    open(p, "w").write("\n".join(out))
    print("\n".join(out))
    print(f"wrote {p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="bc_ppo")
    ap.add_argument("--look", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--list", default="")
    ap.add_argument("--baselines", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    global OUT, REPORTS
    if a.quick:
        CFG.update(ppo_steps=20000, bc_eps=200, bc_steps=200)
        OUT = C.results_dir("stream_quick")
        REPORTS = REPORTS + "_quick"
    if a.baselines:
        baselines(load_infos())
        return
    if a.report:
        report("val")
        return report("test")
    if a.list:
        line = open(a.list).read().splitlines()[int(os.environ["SLURM_ARRAY_TASK_ID"])]
        a = ap.parse_args(line.split() + (["--quick"] if a.quick else []))
    run(a)


if __name__ == "__main__":
    main()
