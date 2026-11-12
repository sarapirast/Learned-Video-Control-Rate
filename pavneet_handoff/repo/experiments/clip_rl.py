"""Phase K (#2): multi-GOP rate control under one shared budget (rclib/clipenv.py, D25). No encodes.

methods:  bc       imitate the hindsight per-GOP QP plan (offsets on the model QP), causal observations
          ppo      PPO from scratch
          bc_ppo   bc, then PPO fine-tuning
Baselines (in --report): the hand rule (offset 0 = model QP with online calibration), the best single constant QP
in hindsight, and the hindsight per-GOP plan (the 'search' of this setting).

  python experiments/clip_rl.py --method bc_ppo --look 2 --seed 0
  python experiments/clip_rl.py --list runs/clip.txt          # line $SLURM_ARRAY_TASK_ID of the list
  python experiments/clip_rl.py --report
"""
import argparse
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import clipenv as CE, config as C  # noqa: E402
from experiments.breakdown import boot, fmt_ci  # noqa: E402

CFG = {"ppo_steps": 2_000_000, "n_envs": 16, "n_steps": 128, "batch": 256, "epochs": 5, "lr_scratch": 3e-4,
       "lr_ft": 1e-4, "ent": 0.01, "bc_eps": 20000, "bc_steps": 4000}
OUT = C.results_dir("clip")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def load_infos():
    with open(os.path.join(C.WORK, "results_infos", "infos_slim.pkl"), "rb") as f:
        return pickle.load(f)


def split_ids(infos, s):
    return [g for g, x in infos.items() if x["gop"]["split"] == s]


def eval_cases(infos, split):
    return [(kind, st, q0, s) for kind, st in CE.episodes(infos, split) for q0 in CE.EVAL_Q0 for s in CE.EVAL_S]


def evaluate(act, infos, split, look, c0):
    env = CE.ClipEnv(infos, split_ids(infos, split), look=look, c0=c0)
    rows = []
    for kind, st, q0, s in eval_cases(infos, split):
        env.force(st, q0, s)
        if act in ("hindsight", "const"):
            env.reset()
            plan, const = CE.hindsight(env.tabs, env.B)
            _, _, res = env.rollout_qps(plan if act == "hindsight" else [const] * len(st))
        else:
            o, _ = env.reset()
            done = False
            while not done:
                o, _, done, _, res = env.step(act(o))
        rows.append({**res, "kind": kind})
    return rows


def bc_data(infos, c0, look, seed, n_eps):
    env = CE.ClipEnv(infos, split_ids(infos, "train"), look=look, c0=c0, seed=seed)
    X, Y = [], []
    for _ in range(n_eps):
        env.reset()
        plan, _ = CE.hindsight(env.tabs, env.B)
        o, a, _ = env.rollout_qps(plan)
        X.append(o)
        Y.append(a)
    return np.concatenate(X), np.concatenate(Y)


def train_bc(model, X, Y, steps, seed):
    """Cross-entropy on the hindsight plan's offsets, directly into the PPO actor."""
    torch.manual_seed(seed)
    pol = model.policy
    opt = torch.optim.Adam(pol.parameters(), 1e-3)
    Xt, Yt = torch.from_numpy(X).float(), torch.from_numpy(Y).long()
    for i in range(steps):
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
    c0 = CE.ClipEnv(infos, tr).c0
    venv = DummyVecEnv([(lambda i=i: CE.ClipEnv(infos, tr, look=a.look, c0=c0, seed=1000 * a.seed + i))
                        for i in range(CFG["n_envs"])])
    pk = {"net_arch": {"pi": [128, 128], "vf": [128, 128]}, "activation_fn": torch.nn.ReLU}
    scratch = a.method == "ppo"
    model = PPO("MlpPolicy", venv, learning_rate=CFG["lr_scratch"] if scratch else CFG["lr_ft"],
                n_steps=CFG["n_steps"], batch_size=CFG["batch"], n_epochs=CFG["epochs"], gamma=1.0, gae_lambda=0.95,
                ent_coef=CFG["ent"], policy_kwargs=pk, seed=a.seed, device="cpu", verbose=0)
    info = {"c0": c0}
    if a.method in ("bc", "bc_ppo"):
        X, Y = bc_data(infos, c0, a.look, a.seed, CFG["bc_eps"])
        info["bc_acc"] = train_bc(model, X, Y, CFG["bc_steps"], a.seed)
        info["bc_label_hist"] = np.bincount(Y, minlength=len(CE.ACTIONS)).tolist()
        log(f"BC on {len(X)} steps: accuracy {info['bc_acc']:.3f}, labels {info['bc_label_hist']}")
    if a.method in ("ppo", "bc_ppo"):
        curve = []
        from stable_baselines3.common.callbacks import BaseCallback

        class Track(BaseCallback):
            def _on_step(self):
                for inf, d in zip(self.locals["infos"], self.locals["dones"]):
                    if d and "score" in inf:
                        curve.append((self.num_timesteps, inf["score"], inf["over"]))
                if self.num_timesteps % 200_000 < CFG["n_envs"] and curve:
                    r = curve[-2000:]
                    log(f"  steps {self.num_timesteps}: score {np.mean([c[1] for c in r]):.2f} "
                        f"over {100 * np.mean([c[2] for c in r]):.1f}%")
                return True
        model.learn(total_timesteps=CFG["ppo_steps"], callback=Track())
        np.save(os.path.join(out, "train_curve.npy"), np.array(curve, float))
    model.save(os.path.join(out, "model.zip"))
    pol = model.policy

    def act(o):
        return int(pol.predict(o, deterministic=True)[0])
    res = {s: evaluate(act, infos, s, a.look, c0) for s in ("val", "test")}
    for s, rows in res.items():
        log(f"{name} {s}: score {np.mean([r['score'] for r in rows]):.2f} saving "
            f"{np.mean([r['saving'] for r in rows]):.2f} over {100 * np.mean([r['over'] for r in rows]):.1f}%")
    with open(os.path.join(out, "eval.pkl"), "wb") as f:
        pickle.dump({"args": vars(a), "cfg": CFG, "info": info, "res": res, "seconds": time.time() - t0}, f)


def baselines(infos):
    p = os.path.join(OUT, "baselines.pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    c0 = CE.ClipEnv(infos, split_ids(infos, "train")).c0
    B = {}
    for s in ("val", "test"):
        B[("rule", 0, s)] = evaluate(lambda o: CE.ZERO, infos, s, 0, c0)
        B[("rule", 2, s)] = evaluate(lambda o: CE.ZERO, infos, s, 2, c0)
        B[("const", -1, s)] = evaluate("const", infos, s, 0, c0)
        B[("hindsight", -1, s)] = evaluate("hindsight", infos, s, 0, c0)
        log(f"baselines {s} done")
    pickle.dump(B, open(p, "wb"))
    return B


def report():
    infos = load_infos()
    B = baselines(infos)
    import glob
    R = {}
    for k, rows in B.items():
        if k[2] == "test":
            R[("hindsight plan (offline)" if k[0] == "hindsight" else "best constant QP (offline)" if k[0] == "const"
               else f"rule (model QP) L={k[1]}")] = rows
    for p in sorted(glob.glob(os.path.join(OUT, "*", "eval.pkl"))):
        r = pickle.load(open(p, "rb"))
        R.setdefault(f"{r['args']['method']} L={r['args']['look']}", []).append(r["res"]["test"])

    def frame(rows_or_seeds):
        seeds = rows_or_seeds if isinstance(rows_or_seeds[0], list) else [rows_or_seeds]
        df = [pd.DataFrame([{k: x[k] for k in ("kind", "q0", "s", "score", "saving", "over_pct", "over")}
                            | {"key": (x["stream"], x["q0"], x["s"])} for x in rows]).set_index("key") for rows in seeds]
        m = df[0].copy()
        for c in ("score", "saving", "over_pct", "over"):
            m[c] = np.mean([d[c].astype(float).values for d in df], 0)
        m["n_seeds"] = len(df)
        return m
    F = {k: frame(v) for k, v in R.items()}
    ref, hs = F["rule (model QP) L=0"], F["hindsight plan (offline)"]
    rows = []
    for k, df in F.items():
        r = {"method": k, "seeds": int(df.n_seeds.iloc[0]), "cases": len(df), "score": df.score.mean(),
             "saving": df.saving.mean(), ">1% over": f"{100 * df.over.mean():.0f}%",
             "mean over %": df.over_pct.mean(),
             "share of hindsight gain": (df.score.mean() - ref.score.mean()) / (hs.score.mean() - ref.score.mean()),
             "score, same-clip": df[df.kind == "clip"].score.mean(), "score, mixed": df[df.kind == "mixed"].score.mean()}
        if k != "rule (model QP) L=0":
            r["score vs rule L=0"] = fmt_ci(boot(df.score.values - ref.loc[df.index].score.values))
        bk = f"bc L={k.split('L=')[-1]}"
        if k.startswith(("ppo", "bc_ppo")) and bk in F:
            r["score vs bc (same L)"] = fmt_ci(boot(df.score.values - F[bk].loc[df.index].score.values))
        rows.append(r)
    out = [f"# Multi-GOP rate control ({C.CODEC}, test)", "",
           f"Streams of {CE.N_GOP} IDR GOPs (same-clip time-ordered runs, and mixed streams from different clips) "
           f"under one budget = s x bits at constant QP q0, q0 in {CE.EVAL_Q0}, s in {CE.EVAL_S}. Each step picks a "
           "GOP's constant QP as an offset -6..+6 on the causal model QP. Score = % saving at equal pooled (MSE) PSNR vs the stream's "
           "constant-QP curve - 2 x % over budget. 'share of hindsight gain' = (method - rule L=0) / "
           "(hindsight plan - rule L=0). Differences: 95 % bootstrap over cases (seeds averaged).", "",
           pd.DataFrame(rows).round(2).to_markdown(index=False), ""]
    p = os.path.join(C.REPORTS, "clip_report.md")
    open(p, "w").write("\n".join(out))
    print("\n".join(out))
    print(f"wrote {p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="bc_ppo")
    ap.add_argument("--look", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--list", default="")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    global OUT
    if a.quick:
        CFG.update(ppo_steps=20000, bc_eps=200, bc_steps=200)
        OUT = C.results_dir("clip_quick")
    if a.report:
        return report()
    if a.list:
        line = open(a.list).read().splitlines()[int(os.environ["SLURM_ARRAY_TASK_ID"])]
        a = ap.parse_args(line.split() + (["--quick"] if a.quick else []))
    run(a)


if __name__ == "__main__":
    main()
