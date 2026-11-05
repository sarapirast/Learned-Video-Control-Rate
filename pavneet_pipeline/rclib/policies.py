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
            ratio = 2 ** (-(env.b - 30) / self.sens)
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


class Shield:
    """Budget shield around any policy (evaluation only; Aayush, v1-data branch, 2026-11-04).

    Before frame t it predicts the GOP's total bits if frame t gets the policy's QP and every later frame j gets
    b + STATIC[j] + `fut_off` (3 = lenient 'max', 0 = strict 'neutral'). Bit model: bits_j(q) = c x fp_j x
    2^(-(q-30)/s), with slopes s fitted on the TRAIN search logs (I and P frames separately). c is calibrated online:
    frame 0 from its own bits; P frames by shrinking the P frames coded so far towards the train prior with `w0`
    pseudo-frames. Strictly causal at the policy's lookahead: frames beyond the visible window use the mean first-pass
    cost of P frames 1..t+v (or fp_0 / ip_ratio before any P frame is known). It fires when the prediction exceeds
    budget x margin x (1 + tol x frames_left / 29): early predictions need a stronger signal; the last frame is held
    to margin x budget. When it fires, frame t's QP is raised to the smallest QP (up to 51) that fits."""

    def __init__(self, base, margin=1.0, future="max", prior=(0.6, 0.6), ip_ratio=5.5, qmax=51,
                 slopes=(6.0, 6.0), w0=3.0, tol=0.0):
        self.base, self.margin, self.qmax = base, float(margin), int(qmax)
        self.fut_off = {"max": C.ACTIONS[-1], "neutral": 0}[future]
        self.prior_i, self.prior_p = map(float, prior)
        self.ip_ratio = float(ip_ratio)
        self.s_i, self.s_p = map(float, slopes)
        self.w0, self.tol = float(w0), float(tol)

    def __call__(self, env, obs):
        a = int(self.base(env, obs))
        t, S = env.t, E.STATIC_OFF
        q0 = int(env.b + S[t] + C.ACTIONS[a])
        fp = np.maximum(np.asarray(env.info["fp_bits"], float), 8)
        v = E.visible_len(t, env.mode, env.k_ep, env.cut)
        known_p = fp[1:t + v + 1]
        fh = fp.copy()
        fh[t + v + 1:] = known_p.mean() if len(known_p) else fp[0] / self.ip_ratio
        bits = np.asarray(env.bits, float)
        qp = np.asarray(env.qps, float)
        c_i = bits[0] / (fp[0] * 2 ** (-(qp[0] - 30) / self.s_i)) if t >= 1 else self.prior_i
        if t >= 2:
            pp = fp[1:t] * 2 ** (-(qp[1:t] - 30) / self.s_p)
            m = pp.mean()
            c_p = (bits[1:t].sum() + self.w0 * self.prior_p * m) / (pp.sum() + self.w0 * m)
        else:
            c_p = self.prior_p

        def cost(j, q):
            return c_i * fh[0] * 2 ** (-(q - 30) / self.s_i) if j == 0 else c_p * fh[j] * 2 ** (-(q - 30) / self.s_p)
        rest = sum(cost(j, min(self.qmax, env.b + S[j] + self.fut_off)) for j in range(t + 1, C.GOP))
        limit = self.margin * env.budget * (1 + self.tol * (C.GOP - 1 - t) / (C.GOP - 1))
        spent = bits.sum()
        q = q0
        while q < self.qmax and spent + cost(t, q) + rest > limit:
            q += 1
        if q == q0:
            return a
        env.n_shield += 1
        off = int(q - env.b - S[t])
        if off <= C.ACTIONS[-1]:
            return C.ACTIONS.index(off)
        env.q_override = q
        return len(C.ACTIONS) - 1


def make(spec):
    k = spec["kind"]
    if k == "shield":
        return Shield(make(spec["base"]), spec.get("margin", 1.0), spec.get("future", "max"),
                      spec.get("prior", (0.6, 0.6)), spec.get("ip_ratio", 5.5), slopes=spec.get("slopes", (6.0, 6.0)),
                      w0=spec.get("w0", 3.0), tol=spec.get("tol", 0.0))
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
