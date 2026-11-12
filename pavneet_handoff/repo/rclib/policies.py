"""Every controller as `act(env, obs) -> action index`, and a parallel evaluator over (GOP, budget) pairs.

Policy specs are plain dicts so they can be sent to worker processes:
  {"kind": "static"}
  {"kind": "rule", "gain": g}                               causal feedback on a fixed spend curve (no lookahead)
  {"kind": "la_rule", "gain": g, "sens": s}                 lookahead rule: allocate the remaining budget over the
                                                            visible window by first-pass cost (works at any k / mode)
  {"kind": "scene_rule", "gain": g, "sens": s, "cut_boost": c}   la_rule + extra bits on detected cut frames
  {"kind": "sb3", "path": zip, "algo": "ppo"|"a2c"|"dqn"}
  {"kind": "torch", "path": pt}                             argmax of a saved torch MLP (BC / CQL / IQL)
  {"kind": "mpc", "path": model.pt, "horizon": h}           see mpc.py
  {"kind": "fb", "base": spec, "gain": g, "margin": m, "curve": c}   any policy + budget feedback (D30, the
                                                            'imitation + inference-time feedback control' baseline)
"""
import os
import pickle

import numpy as np
import torch

from . import config as C, env as E, runner

ZERO = C.ACTIONS.index(0)
STATIC_OFF = np.array(C.static_offsets(), float)
# average cumulative share of the GOP's STATIC bits spent before frame t (fitted on train by baselines.py; this
# default is the 6-dB-per-QP model of STATIC with equal frame costs and a 4x I frame)
_w = 2 ** (-STATIC_OFF / 6) * np.r_[4.0, np.ones(C.GOP - 1)]
SPEND_CURVE = np.r_[0.0, np.cumsum(_w)[:-1]] / _w.sum()


def _clip_act(delta):
    return int(np.clip(round(delta), C.ACTIONS[0], C.ACTIONS[-1])) - C.ACTIONS[0]


class Static:
    def __call__(self, env, obs):
        return ZERO


class Rule:
    """No lookahead: compare bits spent so far with the expected share of the budget; raise QP when ahead."""

    def __init__(self, gain=3.0, curve=None):
        self.gain, self.curve = gain, np.asarray(curve if curve is not None else SPEND_CURVE)

    def __call__(self, env, obs):
        t = env.t
        if t == 0:
            return ZERO
        e = np.log2(max(sum(env.bits), 1) / max(env.budget * self.curve[t], 1))
        return _clip_act(self.gain * e)


class LookaheadRule:
    """Plan frame t's bits as its share of the remaining budget over the rest of the GOP, then pick the offset whose
    predicted bits hit that target. Frame weights are first-pass cost x 2^(-STATIC offset/sens); frames outside the
    visible window are assumed to cost the mean of the visible P frames (their STATIC offsets are known: position is
    not lookahead). Predicted bits = first-pass cost x a running actual/first-pass ratio (median over past P frames).
    """

    def __init__(self, gain=1.0, sens=5.0, cut_boost=0.0):
        self.gain, self.sens, self.cut_boost = gain, sens, cut_boost

    def __call__(self, env, obs):
        t = env.t
        fp = np.maximum(np.asarray(env.info["fp_bits"], float), 8)
        stat = 2 ** (-STATIC_OFF / self.sens)
        v = E.visible_len(t, env.mode, env.k_ep, env.cut)
        vis = np.arange(t, t + v + 1)
        p_vis = vis[vis > 0]
        est_fp = fp[p_vis].mean() if len(p_vis) else None
        w = np.empty(C.GOP - t)
        for i, j in enumerate(range(t, C.GOP)):
            if j <= t + v:
                w[i] = fp[j] * stat[j] * (2 ** self.cut_boost if (self.cut_boost and env.cut[j]) else 1.0)
            else:
                w[i] = (est_fp if est_fp is not None else np.nan) * stat[j]
        if np.isnan(w).any():                 # k = 0 at the I frame: no P-frame cost visible yet
            share = SPEND_CURVE[1]
        else:
            share = w[0] / w.sum()
        target = max(env.budget - sum(env.bits), env.budget * 0.002) * share
        if t >= 2:
            past = np.arange(1, t)
            acts = np.array([C.ACTIONS[a] for a in env.acts])[past]
            ratio = np.median(np.asarray(env.bits)[past] / fp[past] * 2 ** ((STATIC_OFF[past] + acts) / self.sens))
        elif t == 1:
            ratio = env.bits[0] / fp[0] * 2 ** ((STATIC_OFF[0] + C.ACTIONS[env.acts[0]]) / self.sens)
        else:
            ratio = 2 ** (-(env.qbase - 30) / self.sens)
        pred0 = fp[t] * ratio * stat[t]
        return _clip_act(self.gain * self.sens * np.log2(pred0 / max(target, 1.0)))


class TorchArgmax:
    def __init__(self, path):
        self.net = torch.load(path, weights_only=False)
        self.net.eval()

    def __call__(self, env, obs):
        with torch.no_grad():
            return int(self.net(torch.as_tensor(obs[None])).argmax(1))


class SB3:
    def __init__(self, path, algo="ppo"):
        from stable_baselines3 import A2C, DQN, PPO
        cls = {"ppo": PPO, "a2c": A2C, "dqn": DQN}[algo]
        self.model = cls.load(path, device="cpu")

    def __call__(self, env, obs):
        a, _ = self.model.predict(obs, deterministic=True)
        return int(a)


class Ensemble:
    """Several SB3 policies (e.g. seeds) as one: argmax of the mean action probabilities."""

    def __init__(self, paths, algo="ppo"):
        self.members = [SB3(p, algo).model.policy for p in paths]

    def __call__(self, env, obs):
        with torch.no_grad():
            o = torch.as_tensor(obs[None])
            p = sum(m.get_distribution(o).distribution.probs for m in self.members)
        return int(p.argmax(1))


class Feedback:
    """A base policy (e.g. BC) plus a closed-loop budget correction added to its action (gain x e, clipped to -3..3).
    mode 'cum': e = log2(bits spent so far / expected share of the margin-reduced budget);
    mode 'rem': e = -log2(budget left / expected remaining share), which reacts most strongly near the end of the GOP,
    where a cumulative error turns into overshoot. Not learned: mode, gain and margin are tuned on val.
    The expected share is the training-set STATIC spend curve (baselines.py spend_curve), the same as the causal rule."""

    def __init__(self, base, gain=2.0, margin=0.0, curve=None, mode="cum"):
        self.base = make(base)
        self.gain, self.margin, self.mode = gain, margin, mode
        self.curve = np.asarray(curve if curve is not None else SPEND_CURVE)

    def __call__(self, env, obs):
        a = self.base(env, obs)
        t = env.t
        if t == 0:
            return a
        B = env.budget * (1 - self.margin)
        if self.mode == "rem":
            e = -np.log2(max(B - sum(env.bits), 1.0) / max(B * (1 - self.curve[t]), 1.0))
        else:
            e = np.log2(max(sum(env.bits), 1) / max(B * self.curve[t], 1))
        return _clip_act(C.ACTIONS[a] + self.gain * e)


def make(spec):
    k = spec["kind"]
    if k == "static":
        return Static()
    if k == "rule":
        return Rule(spec.get("gain", 3.0), spec.get("curve"))
    if k in ("la_rule", "scene_rule"):
        return LookaheadRule(spec.get("gain", 1.0), spec.get("sens", 5.0), spec.get("cut_boost", 0.0))
    if k == "torch":
        return TorchArgmax(spec["path"])
    if k == "sb3":
        return SB3(spec["path"], spec.get("algo", "ppo"))
    if k == "ensemble":
        return Ensemble(spec["paths"], spec.get("algo", "ppo"))
    if k == "fb":
        return Feedback(spec["base"], spec.get("gain", 2.0), spec.get("margin", 0.0), spec.get("curve"),
                        spec.get("mode", "cum"))
    if k == "mpc":
        from . import mpc
        return mpc.MPC(spec)
    raise ValueError(k)


# ---------------------------------------------------------------- evaluation

_cache = {}


def _infos(path):
    if path not in _cache:
        with open(path, "rb") as f:
            _cache[path] = pickle.load(f)
    return _cache[path]


def _episode(item):
    spec, infos_path, gid, b, envkw = item
    infos = _infos(infos_path)
    key = repr(sorted((k, v) for k, v in spec.items() if k != "curve"))
    if key not in _cache:
        _cache[key] = make(spec)
    pol = _cache[key]
    env = E.make_env({gid: infos[gid]}, **envkw)
    env.force(gid, b)
    obs, _ = env.reset()
    done = False
    while not done:
        obs, r, done, _, res = env.step(pol(env, obs))
    return res


def evaluate(spec, infos_path, gids, budgets=C.BUDGET_QPS, workers=None, desc="eval", **envkw):
    items = [(spec, infos_path, g, b, envkw) for g in gids for b in budgets]
    return runner.pmap(_episode, items, workers, desc=desc)


def evaluate_per_gop_k(spec, infos_path, choice, desc="eval", workers=None, **envkw):
    """choice: {(gid, budget): k} — a per-GOP lookahead chosen by a gate."""
    items = [(spec, infos_path, g, b, {**envkw, "k": k}) for (g, b), k in choice.items()]
    return runner.pmap(_episode, items, workers, desc=desc)


def save_infos_for_workers(infos, path):
    if not os.path.exists(path):
        tmp = f"{path}.{os.getpid()}.part"
        with open(tmp, "wb") as f:
            pickle.dump(infos, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, path)
    return path
