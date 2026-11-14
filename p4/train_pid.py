"""PPO with a PID-Lagrangian over-budget penalty, stream-level (D34 env)."""
import os, sys, time, pickle, argparse, numpy as np, torch
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pavneet_handoff", "repo"))
from experiments import stream_rl as S
from rclib import streamenv as SE
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv

ap = argparse.ArgumentParser()
ap.add_argument("--look", type=int, default=2)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--target", type=float, default=0.05)    # max share of streams >1% over budget
ap.add_argument("--kp", type=float, default=2.0)
ap.add_argument("--ki", type=float, default=0.05)
ap.add_argument("--steps", type=int, default=2_000_000)
ap.add_argument("--bc", action="store_true")
a = ap.parse_args()

CFG, BASE = S.CFG, 0.17
name = f"{'bc_ppo_pid' if a.bc else 'ppo_pid'}_L{a.look}_s{a.seed}"
out = os.path.join(S.C.results_dir("stream"), name)
os.makedirs(out, exist_ok=True)
torch.set_num_threads(2)
t0 = time.time()

infos = S.load_infos()
tr = S.split_ids(infos, "train")
c0 = S.train_c0(infos)
venv = DummyVecEnv([(lambda i=i: SE.StreamEnv(infos, tr, look=a.look, c0=c0, seed=1000 * a.seed + i, lam=BASE))
                    for i in range(CFG["n_envs"])])
pk = {"net_arch": {"pi": [128, 128], "vf": [128, 128]}, "activation_fn": torch.nn.ReLU}
model = PPO("MlpPolicy", venv, learning_rate=CFG["lr_ft"] if a.bc else CFG["lr_scratch"], n_steps=CFG["n_steps"], batch_size=CFG["batch"],
            n_epochs=CFG["epochs"], gamma=1.0, gae_lambda=0.95, ent_coef=CFG["ent"], policy_kwargs=pk,
            seed=a.seed, device="cpu", verbose=0)
if a.bc:
    X, Y = S.bc_data(infos, c0, a.look, a.seed, CFG["bc_eps"])
    print("BC accuracy", S.train_bc(model, X, Y, CFG["bc_steps"], a.seed), flush=True)
curve, lams = [], []      # curve: (step, score, over, use) per finished stream; lams: (step, rate, lambda)

class PID(BaseCallback):
    I, lam = 0.0, BASE

    def _on_step(self):
        for inf, d in zip(self.locals["infos"], self.locals["dones"]):
            if d and "score" in inf:
                curve.append((self.num_timesteps, inf["score"], inf["over"], inf["use"]))
        return True

    def _on_rollout_end(self):
        if len(curve) < 200:
            return
        rate = np.mean([c[2] for c in curve[-1000:]])
        e = rate - a.target
        self.I = max(0, self.I + e)
        self.lam = BASE + max(0, a.kp * e + a.ki * self.I)
        self.training_env.set_attr("lam", self.lam)
        lams.append((self.num_timesteps, rate, self.lam))
        if len(lams)%100 == 0:
            r= np.array(curve[-2000:])
            print(f"steps {self.num_timesteps}: score {r[:, 1].mean():+.3f} dB, "
                  f"over {100 * rate:.1f}%, lambda {self.lam:.3f}", flush=True)

model.learn(total_timesteps=a.steps, callback=PID())
model.save(os.path.join(out, "model.zip"))
np.save(os.path.join(out, "lam_curve.npy"), np.array(lams))

pol = model.policy
act = lambda o: int(pol.predict(o, deterministic=True)[0])
res = {s: S.evaluate(act, infos, s, a.look, c0) for s in ("val", "test")}
for s, rows in res.items():
    print(name, s, f"score {np.mean([r['score'] for r in rows]):+.3f} dB, "
          f"over {100 * np.mean([r['over'] for r in rows]):.1f}%, use {100 * np.mean([r['use'] for r in rows]):.1f}%")
pickle.dump({"args": vars(a) | {"method": "ppo_pid"}, "cfg": CFG, "info": {"c0": c0, "lams": lams},
             "res": res, "seconds": time.time() - t0}, open(os.path.join(out, "eval.pkl"), "wb"))