"""D43: three follow-ups to D42 on the live-channel task (rclib/bufenv.py). Same decision, action space (offset -6..+6
on the vbv2 QP), score, base rule, network and evaluation cases as ppo_v2 (D39) and il_ppo (D42); only the training or
the policy's inputs change. Every run saves its model (model.zip next to eval.pkl).

* ppo_pc  (privileged critic, "asymmetric actor-critic"): ppo_v2, but the value network also sees what no controller
  can know at decision time: the true channel rate of the next K_PRIV GOPs, the mean channel over the rest of the
  stream, and the next K_PRIV GOPs' complexity (fp). The policy network sees exactly ppo_v2's observation (the
  privileged part is multiplied by zero before it; checked in the debug run). Only training uses the privileged
  numbers: a better value estimate gives lower-variance advantages, the policy stays deployable.
* il_pc: D42's il_ppo (DAgger on the D41 oracle, critic warm-up, PPO fine-tuning) with the same privileged critic.
  D42's student copied only 25-42 % of the hindsight teacher's labels; the privileged critic lets the fine-tuning
  stage judge actions with the information the teacher used.
* ppo_pred (throughput predictor, as Fugu / Puffer): a small supervised network, trained on the training channels
  before RL, predicts log2 of the next 4 GOPs' channel rate (and their minimum) from the last H_HIST observed rates;
  its 5 outputs are added to ppo_v2's observation. Prediction quality on val channels is logged (R^2 vs last value).
* il_rr: a re-run of D42's il_ppo (seed 0) that keeps the model, for the real-encoder check (buffer_real.py --model
  il_ppo_rr). D42 did not save its models. Named il_ppo_rr so the D42 numbers stay as reported.

  RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 RC_V1=1 [RC_BUF_CHANNEL=trace] \
      python experiments/buffer_rl3.py --method ppo_pc|il_pc|ppo_pred|il_rr --seed 0 [--quick] | --report
"""
import argparse
import os
import sys
import time

import numpy as np
import torch
from gymnasium import spaces
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.preprocessing import get_flattened_obs_dim
from stable_baselines3.common.torch_layers import FlattenExtractor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import buffer_oracle as BO, buffer_rl as BR, buffer_rl2 as R2, stream_rl as S  # noqa: E402
from rclib import bufenv as BE, metastream as MS  # noqa: E402

K_PRIV = 8
N_PRIV = 2 * K_PRIV + 1
H_HIST = 8
N_PRED = 5        # next 4 GOPs' log2 rate, and their minimum
log = S.log


# ------------------------------------------------------------------------------------------------ throughput predictor
def _windows(ms):
    """(X, Y) for every decision point of every channel m: X = last H_HIST seen log2 rates (newest first, 0-padded)
    + fraction of the history filled; Y = log2 m of the next 4 GOPs (repeating the last one past the end) + their min."""
    X, Y = [], []
    for m in ms:
        lm, n = np.log2(m), len(m)
        for i in range(n):
            h = np.zeros(H_HIST + 1)
            r = lm[max(0, i - H_HIST):i][::-1]
            h[:len(r)] = r
            h[H_HIST] = len(r) / H_HIST
            f = lm[i:min(n, i + 4)]
            f = np.concatenate([f, np.full(4 - len(f), f[-1])])
            X.append(h)
            Y.append(np.concatenate([f, [f.min()]]))
    return np.array(X), np.array(Y)


def _draw(ch, split, k, seed):
    rng = np.random.default_rng(seed)
    ns = rng.integers(MS.N_RANGE[0], MS.N_RANGE[1] + 1, k)
    if ch == "ar1":
        return [BE.channel(int(n), rng) for n in ns]
    return [BE.trace_channel(int(n), rng, split) for n in ns]


class Predictor:
    def __init__(self, ch, k=4000, seed=0):
        from sklearn.neural_network import MLPRegressor
        t0 = time.time()
        X, Y = _windows(_draw(ch, "train", k, seed))
        self.net = MLPRegressor(hidden_layer_sizes=(64, 64), max_iter=300, early_stopping=True, random_state=seed).fit(X, Y)
        Xv, Yv = _windows(_draw(ch, "val", max(200, k // 4), seed + 1))
        P = self.net.predict(Xv)
        last = np.repeat(Xv[:, :1], N_PRED, 1)       # naive: the last seen rate (0 = channel mean before any)
        r2 = 1 - ((P - Yv) ** 2).sum(0) / ((Yv - Yv.mean(0)) ** 2).sum(0)
        r2n = 1 - ((last - Yv) ** 2).sum(0) / ((Yv - Yv.mean(0)) ** 2).sum(0)
        log(f"  predictor [{ch}]: {len(X)} train / {len(Xv)} val points, {(time.time() - t0):.0f} s; val R^2 "
            f"next1..4,min = {np.round(r2, 3).tolist()} (last value: {np.round(r2n, 3).tolist()})")
        self.r2, self.r2_last = r2, r2n

    def __call__(self, rseen, mean_r):
        h = np.zeros(H_HIST + 1)
        if rseen:
            r = np.log2(np.array(rseen[-H_HIST:]) / mean_r)[::-1]
            h[:len(r)] = r
            h[H_HIST] = len(r) / H_HIST
        return self.net.predict(h[None])[0]


# ------------------------------------------------------------------------------------------------ environment
class Env3(R2.Env2):
    """Env2 (no history, no mix) + optional predictor outputs (actor-visible) + optional privileged block (last)."""

    def __init__(self, *args, priv=False, pred=None, **kw):
        self.priv, self.pred = priv, pred
        super().__init__(*args, **kw)
        self.dim = BE.OBS_DIM + (N_PRED if pred is not None else 0) + (N_PRIV if priv else 0)
        self.observation_space = spaces.Box(-10, 10, (self.dim,), np.float32)

    def _obs(self):
        o = super()._obs()
        if getattr(self, "pred", None) is None and not getattr(self, "priv", False):
            return o
        ext = []
        ready = self.m is not None and getattr(self, "Rseen", None) is not None
        if self.pred is not None:
            ext.append(self.pred(self.Rseen, self.mean_r) if ready else np.zeros(N_PRED))
        if self.priv:
            p = np.zeros(N_PRIV)
            if ready and self.i < self.n:
                i, n = self.i, self.n
                fp = np.array([t["fp"] for t in self.tabs])
                for k in range(K_PRIV):
                    if i + k < n:
                        p[k] = np.log2(self.m[i + k])
                        p[K_PRIV + k] = np.log2(fp[i + k] / fp.mean())
                p[2 * K_PRIV] = np.log2(self.m[i:].mean())
            ext.append(p)
        return np.clip(np.concatenate([o, *ext]).astype(np.float32), -10, 10)

    def step(self, a, q=None):
        o, r, done, trunc, info = super().step(a, q=q)
        if done:
            o = np.zeros(self.dim, np.float32)
        return o, r, done, trunc, info


def n_actor(pred):
    return BE.OBS_DIM + (N_PRED if pred else 0)


# ------------------------------------------------------------------------------------------------ privileged critic
class MaskExtractor(FlattenExtractor):
    """Flatten, then zero every input past the first n_act (the policy network never sees them)."""

    def __init__(self, space, n_act):
        super().__init__(space)
        m = torch.zeros(get_flattened_obs_dim(space))
        m[:n_act] = 1
        self.register_buffer("mask", m)

    def forward(self, x):
        return super().forward(x) * self.mask


class PCPolicy(ActorCriticPolicy):
    """Separate actor / critic inputs: the critic sees the whole observation, the actor its first n_act entries."""

    def __init__(self, *a, n_act, **kw):
        kw["share_features_extractor"] = False
        super().__init__(*a, **kw)
        self.pi_features_extractor = MaskExtractor(self.observation_space, n_act)
        self.features_extractor = self.pi_features_extractor


def pc_model(venv, seed, lr, ent, n_act=BE.OBS_DIM):
    from stable_baselines3 import PPO
    pk = {"net_arch": {"pi": [128, 128], "vf": [128, 128]}, "activation_fn": torch.nn.ReLU, "n_act": n_act}
    return PPO(PCPolicy, venv, learning_rate=lr, n_steps=BR.CFG["n_steps"], batch_size=BR.CFG["batch"],
               n_epochs=BR.CFG["epochs"], gamma=1.0, gae_lambda=0.95, ent_coef=ent, policy_kwargs=pk, seed=seed,
               device="cpu", verbose=0)


def mask_check(model, env, k=200):
    """The policy's action probabilities must not change when the privileged block is overwritten."""
    pol, O = model.policy, []
    o, _ = env.reset()
    for _ in range(k):
        O.append(o)
        o, _, done, _, _ = env.step(env.action_space.sample())
        if done:
            o, _ = env.reset()
    X = torch.tensor(np.array(O))
    X2 = X.clone()
    X2[:, -N_PRIV:] = torch.randn(len(X), N_PRIV) * 3
    with torch.no_grad():
        d = (pol.get_distribution(X).distribution.probs - pol.get_distribution(X2).distribution.probs).abs().max()
        dv = (pol.predict_values(X) - pol.predict_values(X2)).abs().max()
    log(f"  mask check: max |policy prob change| {float(d):.1e} (must be 0), max |value change| {float(dv):.2f} (> 0)")
    assert float(d) == 0.0


# ------------------------------------------------------------------------------------------------ runs
def run_ppo(a, ekw, mdl, name):
    from stable_baselines3.common.vec_env import DummyVecEnv
    ch, t0 = BE.CHANNEL, time.time()
    venv = DummyVecEnv([(lambda i=i: R2.make_env2("train", ch, seed=1000 * a.seed + i, **ekw))
                        for i in range(BR.CFG["n_envs"])])
    model = mdl(venv, a.seed, BR.CFG["lr"], BR.CFG["ent"])
    if ekw.get("priv"):
        mask_check(model, R2.make_env2("train", ch, seed=99, **ekw))
    curve = []
    model.learn(total_timesteps=4096 if a.quick else BR.CFG["ppo_steps"], callback=R2.tracker(t0, curve))
    if ekw.get("priv"):
        mask_check(model, R2.make_env2("train", ch, seed=98, **ekw))
    R2.evaluate_all(model, f"{name}_L2_s{a.seed}", (ch,), False, vars(a), t0, a.quick, ekw, save=True)
    log(f"{name} seed {a.seed} [{ch}]: {(time.time() - t0) / 60:.1f} min")


def main():
    assert BR.C.V1, "set RC_V1=1"
    p = argparse.ArgumentParser()
    p.add_argument("--method", default="ppo_pc", choices=("ppo_pc", "il_pc", "ppo_pred", "il_rr"))
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--quick", action="store_true", help="tiny run for the debug partition (outputs under debug_rl2)")
    p.add_argument("--report", action="store_true", help="D39 buffer report and D41 oracle report for RC_BUF_CHANNEL")
    a = p.parse_args()
    torch.set_num_threads(2)
    if a.report:
        BR.report()
        BO.report()
        return
    if a.method == "ppo_pc":
        run_ppo(a, {"cls": Env3, "priv": True}, pc_model, "ppo_pc")
    elif a.method == "ppo_pred":
        pr = Predictor(BE.CHANNEL, k=300 if a.quick else 4000, seed=a.seed)
        run_ppo(a, {"cls": Env3, "pred": pr}, R2.ppo_model, "ppo_pred")
    elif a.method == "il_pc":
        t0 = time.time()
        R2.run_il(a, ekw={"cls": Env3, "priv": True}, mdl=pc_model, pre="il_pcbc", ft="il_pc", save=True,
                  eval_il=False)
        log(f"il_pc total {(time.time() - t0) / 60:.1f} min")
    else:
        R2.run_il(a, pre="il_rr", ft="il_ppo_rr", save=True, eval_il=False)


if __name__ == "__main__":
    main()
