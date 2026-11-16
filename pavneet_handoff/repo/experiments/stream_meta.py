"""D36: meta-RL for stream-level rate control (rclib/metastream.py). No encodes; same budgets, score and test cases as
D34 (v1) and D35 (fresh films), so every result pairs case by case with the D34 rule and policies.

methods (all PPO from scratch on reward = score_db at the end of the stream, stream length n ~ U{4..24} in training):
  ppo_fb    feedforward PPO, observation + length + quality feedback
  rppo      recurrent PPO (LSTM), observation + length, no quality feedback
  rppo_fb   recurrent PPO (LSTM), observation + length + quality feedback      (primary)
Evaluation: v1 val / test (n = 8, D34 cases) and the fresh films at n = 8 / 16 / 32 (D35 cases).

  RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 RC_FRESHWORK=/scratch1/pbanga/rcwork_fresh/x265 \
      python experiments/stream_meta.py --method rppo_fb --look 2 --seed 0
  ... --list runs/stream_meta.txt     (line $SLURM_ARRAY_TASK_ID)
  ... --report
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
from rclib import config as C, metastream as M, streamenv as SE  # noqa: E402

CFG = {"ppo_steps": 2_000_000, "n_envs": 16, "n_steps": 128, "batch": 256, "epochs": 5, "lr": 3e-4, "ent": 0.01,
       "lstm": 64}
FRESH = os.environ.get("RC_FRESHWORK", f"/scratch1/pbanga/rcwork_fresh/{C.CODEC}")
OUT = C.results_dir("stream_meta")
REPORTS = os.path.join(C.PROJECT, "results", "v1_stream_meta", C.CODEC)
METHODS = ("ppo_fb", "rppo", "rppo_fb")
NS = (8, 16, 32)
log = S.log


def fresh_cases(infos, n):
    """D35 fresh-film cases (same as experiments/stream_fresh.cases): windows of n GOPs, stride n / 2, per segment."""
    by = {}
    for g, x in infos.items():
        by.setdefault(x["gop"]["clip"], []).append((x["gop"]["start"], g))
    out = []
    for c, lst in sorted(by.items()):
        lst = [g for _, g in sorted(lst)]
        for i in range(0, len(lst) - n + 1, max(1, n // 2)):
            out += [("clip", c, tuple(lst[i:i + n]), q0, s) for q0 in SE.LEVELS for s in SE.EVAL_S]
    return out


def load_fresh():
    return pickle.load(open(os.path.join(FRESH, "results_infos", "infos_slim.pkl"), "rb"))


class Actor:
    """Deterministic policy wrapper; keeps the LSTM state across one stream and resets it at the start of the next."""

    def __init__(self, model, recurrent):
        self.m, self.rec = model, recurrent
        self.reset()

    def reset(self):
        self.state, self.start = None, np.ones((1,), bool)

    def __call__(self, o):
        if not self.rec:
            return int(self.m.predict(o, deterministic=True)[0])
        a, self.state = self.m.predict(o[None], state=self.state, episode_start=self.start, deterministic=True)
        self.start = np.zeros((1,), bool)
        return int(a[0])


def evaluate(actor, env, cases):
    rows = []
    for kind, grp, st, q0, s in cases:
        env.force(st, q0, s)
        o, _ = env.reset()
        actor.reset()
        done = False
        while not done:
            o, _, done, _, res = env.step(actor(o))
        rows.append({**res, "kind": kind, "group": grp})
    return rows


def evaluate_all(actor, look, fb, c0, quick=False):
    infos = S.load_infos()
    out = {}
    for sp in ("val", "test"):
        cs = S.cases(infos, sp)
        env = M.MetaStreamEnv(infos, S.split_ids(infos, sp), look=look, c0=c0, fb=fb)
        out[sp] = evaluate(actor, env, cs[:200] if quick else cs)
    fr = load_fresh()
    for n in NS:
        cs = fresh_cases(fr, n)
        env = M.MetaStreamEnv(fr, list(fr), look=look, c0=c0, fb=fb, n=n)
        out[f"fresh{n}"] = evaluate(actor, env, cs[:60] if quick else cs)
    return out


def run(a):
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import DummyVecEnv
    from sb3_contrib import RecurrentPPO
    name = f"{a.method}_L{a.look}_s{a.seed}"
    out = os.path.join(OUT, name)
    os.makedirs(out, exist_ok=True)
    if os.path.exists(os.path.join(out, "eval.pkl")):
        log(f"{name}: done")
        return
    torch.set_num_threads(2)
    t0 = time.time()
    infos = S.load_infos()
    tr = S.split_ids(infos, "train")
    c0 = pickle.load(open(os.path.join(C.results_dir("stream"), "baselines.pkl"), "rb"))["c0"]
    fb, rec = a.method.endswith("_fb"), a.method.startswith("rppo")
    venv = DummyVecEnv([(lambda i=i: M.MetaStreamEnv(infos, tr, look=a.look, c0=c0, seed=1000 * a.seed + i, fb=fb))
                        for i in range(CFG["n_envs"])])
    common = dict(learning_rate=CFG["lr"], n_steps=CFG["n_steps"], batch_size=CFG["batch"], n_epochs=CFG["epochs"],
                  gamma=1.0, gae_lambda=0.95, ent_coef=CFG["ent"], seed=a.seed, device="cpu", verbose=0)
    if rec:
        pk = {"net_arch": {"pi": [128], "vf": [128]}, "activation_fn": torch.nn.ReLU, "lstm_hidden_size": CFG["lstm"]}
        model = RecurrentPPO("MlpLstmPolicy", venv, policy_kwargs=pk, **common)
    else:
        pk = {"net_arch": {"pi": [128, 128], "vf": [128, 128]}, "activation_fn": torch.nn.ReLU}
        model = PPO("MlpPolicy", venv, policy_kwargs=pk, **common)
    curve = []

    class Track(BaseCallback):
        def _on_step(self):
            for inf, d in zip(self.locals["infos"], self.locals["dones"]):
                if d and "score" in inf:
                    curve.append((self.num_timesteps, inf["score"], inf["over"], inf["use"], len(inf["qps"])))
            if self.num_timesteps % 200_000 < CFG["n_envs"] and curve:
                r = np.array(curve[-2000:])
                log(f"  steps {self.num_timesteps}: score {r[:, 1].mean():+.3f} dB, over {100 * r[:, 2].mean():.1f}%,"
                    f" use {100 * r[:, 3].mean():.1f}%, mean n {r[:, 4].mean():.1f} ({(time.time() - t0) / 60:.0f} min)")
            return True
    model.learn(total_timesteps=CFG["ppo_steps"], callback=Track())
    np.save(os.path.join(out, "train_curve.npy"), np.array(curve, float))
    model.save(os.path.join(out, "model.zip"))
    res = evaluate_all(Actor(model, rec), a.look, fb, c0, a.quick)
    for s, rows in res.items():
        log(f"{name} {s}: score {np.mean([r['score'] for r in rows]):+.3f} dB, over "
            f"{100 * np.mean([r['over'] for r in rows]):.1f}%, use {100 * np.mean([r['use'] for r in rows]):.1f}%")
    with open(os.path.join(out, "eval.pkl"), "wb") as f:
        pickle.dump({"args": vars(a), "cfg": CFG, "c0": c0, "res": res, "seconds": time.time() - t0}, f)
    log(f"{name}: {(time.time() - t0) / 60:.1f} min")


def report():
    base = pickle.load(open(os.path.join(C.results_dir("stream"), "baselines.pkl"), "rb"))["rows"]
    d34 = {}
    for m in ("ppo", "bc_ppo"):
        for L in (0, 2):
            for p in sorted(glob.glob(os.path.join(C.results_dir("stream"), f"{m}_L{L}_s*", "eval.pkl"))):
                d34.setdefault((m, L), []).append(pickle.load(open(p, "rb"))["res"])
    fresh = {n: pickle.load(open(os.path.join(FRESH, "results_stream_fresh", f"n{n}.pkl"), "rb")) for n in NS
             if os.path.exists(os.path.join(FRESH, "results_stream_fresh", f"n{n}.pkl"))}
    meta = {}
    for p in sorted(glob.glob(os.path.join(OUT, "*", "eval.pkl"))):
        r = pickle.load(open(p, "rb"))
        meta.setdefault((r["args"]["method"], r["args"]["look"]), []).append(r["res"])
    lines = [f"# D36 meta-RL for stream rate control ({C.CODEC})", "",
             "PPO from scratch with stream length randomised in training (n in 4..24, playlists of v1 train clips); "
             "ppo_fb = feedforward + quality feedback, rppo = LSTM without feedback, rppo_fb = LSTM + feedback. "
             "Score = dPSNR_B - 0.17 dB per 1 % over. 'vs rule' and 'vs D34 ppo' = paired differences at the same "
             "lookahead, 95 % cluster bootstrap (v1: source groups, mixed streams each their own; fresh: 12 film "
             "segments), seeds averaged.", ""]
    sets = [("test", "v1 test (n = 8)"), ("val", "v1 val (n = 8)")] + [(f"fresh{n}", f"fresh films, n = {n}") for n in NS]
    for key, title in sets:
        F = {}
        for L in (0, 2):
            if key in ("val", "test"):
                F[("rule", L)] = S.frame([base[("rule", L, key)]])
                for (m, LL), runs in d34.items():
                    if LL == L:
                        F[(f"D34 {m}", L)] = S.frame([r[key] for r in runs])
            else:
                n = int(key[5:])
                if n in fresh:
                    F[("rule", L)] = S.frame([fresh[n][("rule", L, 0)]])
                    for m in ("ppo", "bc_ppo"):
                        rs = [v for k, v in fresh[n].items() if k[0] == m and k[1] == L]
                        if rs:
                            F[(f"D34 {m}", L)] = S.frame(rs)
            for (m, LL), runs in meta.items():
                if LL == L and all(key in r for r in runs):
                    F[(m, L)] = S.frame([r[key] for r in runs])
        rows = []
        for (m, L), df in sorted(F.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            r = {"method": m, "L": L, "seeds": int(df.n_seeds.iloc[0]), "cases": len(df), "score (dB)": df.score.mean(),
                 "dPSNR_B": df.dpsnr.mean(), "use": f"{100 * df.use.mean():.1f}%",
                 ">1% over": f"{100 * df.over.mean():.0f}%"}
            for refname in ("rule", "D34 ppo"):
                ref = F.get((refname, L))
                if ref is not None and m != refname and m != "rule":
                    ks = [k for k in df.index if k in ref.index]
                    t = S.cboot(df.loc[ks].score.values - ref.loc[ks].score.values, df.loc[ks].group.values)
                    r[f"vs {refname}"] = f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"
            rows.append(r)
        if rows:
            lines += [f"## {title}", "", pd.DataFrame(rows).round(3).to_markdown(index=False), ""]
    os.makedirs(REPORTS, exist_ok=True)
    p = os.path.join(REPORTS, "meta_report.md")
    open(p, "w").write("\n".join(lines))
    print("\n".join(lines))
    print("wrote", p)


def main():
    global OUT, REPORTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="rppo_fb", choices=METHODS)
    ap.add_argument("--look", type=int, default=2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--list", default="")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--steps", type=int, default=0)
    a = ap.parse_args()
    if a.quick:
        CFG.update(ppo_steps=a.steps or 20000)
        OUT = C.results_dir("stream_meta_quick")
        REPORTS = REPORTS + "_quick"
    if a.report:
        return report()
    if a.list:
        line = open(a.list).read().splitlines()[int(os.environ["SLURM_ARRAY_TASK_ID"])]
        q = a.quick
        a = ap.parse_args(line.split())
        a.quick = q
    run(a)


if __name__ == "__main__":
    main()
