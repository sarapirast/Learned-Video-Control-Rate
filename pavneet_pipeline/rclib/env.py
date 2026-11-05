"""Gym environment: one episode = one GOP under one budget; each step picks frame t's QP offset.

Observation = global/state features + current-frame features + a lookahead window of up to KMAX future frames.
Lookahead is strict: features of frames beyond the visible window are zeroed (with a 'visible' flag), and every
summary feature (window mean cost, scene share, distance to next cut) is computed over visible frames only.
Which future frames are visible is set by a lookahead *mode* (fixed k, scene-truncated, scene-extended, cut-triggered,
per-GOP k), see `visible_len`. Feature groups can be switched off (zeroed) for ablations.

Each step is one real prefix encode of frames 0..t (prefix property verified in tools/codec_check.py); the last step's
encode is decoded for PSNR. Reward is 0 until the end, then (score - STATIC score) / REWARD_SCALE, or a Lagrangian
variant (saving - lambda * overshoot).
"""
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from . import codec, config as C, data, metrics

KMAX = C.GOP - 1
F_FRAME = 11            # per-frame feature width (incl. 'visible' flag)
F_GLOBAL = 16
OBS_DIM = F_GLOBAL + F_FRAME * (1 + KMAX)
REWARD_SCALE = 10.0
# optional extra global features appended after OBS_DIM (D23):
#   fb   achieved PSNR (last, mean), bit-prediction error (last, mean), frames since the last cut, last-mean PSNR
#   sum  fb + a summary of the visible window (mean/max/min cost, any cut, where it is, cost after vs before it)
#        that replaces the raw lookahead slots (slot 0, the current frame, is kept)
EXTRA = {"": 0, "fb": 6, "sum": 13}
STATIC_OFF = np.array(C.static_offsets(), float)

# feature groups -> (global indices, per-frame indices). 'budget' state and position are never ablated.
GROUPS = {
    "history": ([5, 6, 7, 8], []),
    "fp": ([9, 13], [0]),
    "pixel": ([], [1, 2, 3, 4]),
    "scene": ([10, 11, 12], [5, 6, 7, 10]),
}


def frame_table(info, b=None):
    """Per-frame features of a whole GOP (row t = frame t), computed once per GOP from infos."""
    an, fp = info["an"], np.asarray(info["fp_bits"], float)
    # orig arm: always the QP-30 budget (his code); dec arm: the episode's own budget (no QP-30 info at b=38)
    nb = b if (C.ARM == "dec" and b is not None) else C.BUDGET_QPS[0]
    per_frame_budget = info["budget"][nb] / C.GOP
    T = np.zeros((C.GOP, F_FRAME), np.float32)
    T[:, 0] = np.log2(np.maximum(fp, 8) / per_frame_budget) / 4
    T[:, 1] = an["spatial"] / 20
    T[:, 2] = np.log1p(an["msad"]) / 3
    T[:, 3] = np.log1p(an["sad"]) / 3
    T[:, 4] = np.minimum(an["hist_d"], 2.0)
    T[:, 5] = an["cut"]
    T[:, 6] = an["flash"]
    T[:, 7] = an["fade"]
    T[0, 8] = 1.0
    T[:, 9] = STATIC_OFF / 6
    # column 10 (same scene as the current frame) is filled per step
    return T


# ---------------------------------------------------------------- lookahead modes

def visible_len(t, mode, k, cut):
    """Number of future frames (after t) whose features the controller may use at step t."""
    rest = C.GOP - 1 - t
    if mode == "fixed":
        return min(k, rest)
    nxt = [j for j in range(t + 1, C.GOP) if cut[j]]
    d = (nxt[0] - t) if nxt else None           # frames until the next cut (the cut frame itself is at t+d)
    if mode == "scene_trunc":                   # never look into the next scene
        return min(k, rest, (d - 1) if (d is not None and d <= k) else rest)
    if mode == "scene_ext":                     # always see up to and including the next cut frame (k = cap)
        return min(rest, d if d is not None else k)
    if mode == "cut_trig":                      # k frames only when a cut is within k frames, else none
        return min(k, rest) if (d is not None and d <= k) else 0
    raise ValueError(mode)


class RateEnv(gym.Env):
    metadata = {}

    def __init__(self, infos, gop_ids=None, budgets=C.BUDGET_QPS, k=5, mode="fixed", drop=(), seed=0,
                 k_sampler=None, reward="relative", lam=0.0, prior=False, extra="", cut_weight=1.0):
        super().__init__()
        self.infos = infos
        self.ids = list(gop_ids or infos.keys())
        self.budgets = list(budgets)
        self.k, self.mode, self.k_sampler = k, mode, k_sampler
        self.reward_kind, self.lam = reward, lam
        self.prior = prior
        self.extra = extra
        self.dim = OBS_DIM + EXTRA[extra]
        self.rng = np.random.default_rng(seed)
        # training-time oversampling of GOPs with a scene cut (spliced or detected cut after frame 0)
        w = np.array([cut_weight if (infos[g]["gop"]["family"] == "splice" or infos[g]["an"]["cut"][1:].sum() > 0)
                      else 1.0 for g in self.ids])
        self.p_ids = w / w.sum()
        self.mask = np.ones(self.dim, np.float32)
        for g in drop:
            gi, fi = GROUPS[g]
            self.mask[gi] = 0
            for slot in range(1 + KMAX):
                for f in fi:
                    self.mask[F_GLOBAL + slot * F_FRAME + f] = 0
        self.observation_space = spaces.Box(-10, 10, (self.dim,), np.float32)
        self.action_space = spaces.Discrete(len(C.ACTIONS))
        self._tables = {}
        self.forced = None              # (gop_id, budget) for evaluation
        self.k_seen = []

    # -- episode control
    def set_lambda(self, lam):
        self.lam = float(lam)

    def force(self, gid, budget, k=None):
        self.forced = (gid, budget, k)

    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        if self.forced:
            self.gid, self.b, kk = self.forced
            self.k_ep = self.k if kk is None else kk
        else:
            self.gid = self.ids[self.rng.choice(len(self.ids), p=self.p_ids)]
            self.b = self.budgets[self.rng.integers(len(self.budgets))]
            self.k_ep = self.k_sampler(self.rng) if self.k_sampler else self.k
        self.info = self.infos[self.gid]
        key = (self.gid, self.b)
        if key not in self._tables:
            self._tables[key] = frame_table(self.info, self.b)
        self.T = self._tables[key]
        self.budget = self.info["budget"][self.b]
        self.cut = self.info["an"]["cut"]
        self.path = data.gop_path(self.info["gop"])
        self.t, self.qps, self.acts, self.bits, self.psnr = 0, [], [], [], []
        self.k_seen = []
        self.q_override, self.n_shield = None, 0     # set by policies.Shield (eval only, v1-data branch)
        return self._obs(), {}

    # -- observation
    def _obs(self):
        t, T = self.t, self.T
        o = np.zeros(self.dim, np.float32)
        spent = float(sum(self.bits))
        rest = C.GOP - t
        v = visible_len(t, self.mode, self.k_ep, self.cut)
        self.k_seen.append(v)
        win = slice(t, t + v + 1)
        fp = np.maximum(np.asarray(self.info["fp_bits"], float), 8)
        per_frame = self.budget / C.GOP
        o[0] = t / KMAX
        o[1] = rest / C.GOP
        o[2] = float(self.b != C.BUDGET_QPS[0])
        o[3] = spent / self.budget
        o[4] = np.log2(max(self.budget - spent, 1.0) / (rest * per_frame)) / 2
        if t > 0:
            o[5] = np.log2(max(self.bits[-1], 8) / per_frame) / 4
            o[6] = C.ACTIONS[self.acts[-1]] / 3
            o[7] = np.log2(max(self.bits[-1], 8) / fp[t - 1]) / 2
            o[8] = np.log2(max(spent, 8) / fp[:t].sum()) / 2
        o[9] = np.log2(self.budget / fp[0]) / 4
        # scene state, visible part only
        scene_start = max([j for j in range(t + 1) if self.cut[j]] or [0])
        o[10] = (t - scene_start) / C.GOP
        nxt = [j for j in range(t + 1, t + v + 1) if self.cut[j]]
        o[11] = ((nxt[0] - t) if nxt else (v + 1)) / C.GOP
        end = nxt[0] if nxt else t + v + 1
        o[12] = fp[t:end].sum() / fp[win].sum()
        o[13] = np.log2(fp[win].mean() / per_frame) / 4
        o[14] = v / KMAX
        o[15] = self._prior(t) if self.prior else 0.0
        # frames: slot 0 = current frame, slots 1..v = lookahead
        scene_now = self.info["an"]["scene"][t]
        for s in range(v + 1):
            j = t + s
            base = F_GLOBAL + s * F_FRAME
            o[base:base + F_FRAME] = T[j]
            o[base + 10] = float(self.info["an"]["scene"][j] == scene_now)
            # 'visible' flag is implicit: an all-zero slot is invisible; position column 9 is never zero except
            # STATIC offset 0, so add 0.01 to keep visible slots distinguishable
            o[base + 9] += 0.01
        if self.extra:
            self._extra(o, t, v, fp)
        return np.clip(o * self.mask, -10, 10)

    def _extra(self, o, t, v, fp):
        e = o[OBS_DIM:]
        if t > 0:
            ps = np.asarray(self.psnr[:t], float)
            q = np.asarray(self.qps[:t], float)
            err = np.log2(np.maximum(np.asarray(self.bits[:t], float), 8) / (fp[:t] * 2 ** (-(q - 30) / 6)))
            e[0], e[1], e[5] = ps[-1] / 50, ps.mean() / 50, (ps[-1] - ps.mean()) / 5
            e[2], e[3] = err[-1] / 2, err[1:].mean() / 2 if t > 1 else err[0] / 2
        last_cut = max([j for j in range(t + 1) if self.cut[j]] or [0])
        e[4] = (t - last_cut) / C.GOP
        if self.extra == "sum":
            c = self.T[t:t + v + 1, 0]
            e[6], e[7], e[8] = c.mean(), c.max(), c.min()
            nxt = [j for j in range(t + 1, t + v + 1) if self.cut[j]]
            e[9] = float(bool(nxt))
            e[10] = ((nxt[0] - t) / (v + 1)) if nxt else 1.0
            if nxt:
                e[11] = self.T[nxt[0]:t + v + 1, 0].mean() - self.T[t:nxt[0], 0].mean()
            e[12] = v / KMAX
            o[F_GLOBAL + F_FRAME:OBS_DIM] = 0          # raw lookahead slots replaced by the summary

    def _prior(self, t):
        """Scene budget prior: log2 ratio of the bits a per-scene cost-proportional plan gives frame t (using the
        visible window) to the uniform share. 0 when no lookahead is visible."""
        v = visible_len(t, self.mode, self.k_ep, self.cut)
        if v == 0:
            return 0.0
        fp = np.maximum(np.asarray(self.info["fp_bits"], float)[t:t + v + 1], 8)
        w = fp * 2 ** (-STATIC_OFF[t:t + v + 1] / 6)
        return float(np.log2(w[0] / w.mean()) / 2)

    # -- dynamics
    def step(self, a):
        a = int(a)
        t = self.t
        q = int(self.b + STATIC_OFF[t] + C.ACTIONS[a])
        if getattr(self, "q_override", None) is not None:      # budget shield forced a QP outside the action range
            q, self.q_override = int(self.q_override), None
        self.qps.append(q)
        self.acts.append(a)
        last = t == C.GOP - 1
        r = codec.encode(self.path, self.qps, measure=last or bool(self.extra))
        self.bits = [int(x) for x in r["bits"]]
        if self.extra:
            self.psnr = [float(x) for x in r["psnr"]]
        self.t += 1
        if not last:
            return self._obs(), 0.0, False, False, {}
        res = self.result(r)
        return np.zeros(self.dim, np.float32), res["reward"], True, False, res

    def result(self, r):
        curve, st = self.info["curve"], self.info["static"][self.b]
        sav = float(metrics.saving(r["total_bits"], r["mean_psnr"], curve))
        over = float(metrics.overshoot(r["total_bits"], self.budget))
        score = sav - metrics.OVER_PENALTY * over
        if self.reward_kind == "relative":
            rew = (score - st["score"]) / REWARD_SCALE
        elif self.reward_kind == "lagrangian":
            rew = (sav - st["saving"] - self.lam * over) / REWARD_SCALE
        else:
            raise ValueError(self.reward_kind)
        return {"gid": self.gid, "budget": self.b, "bits": r["total_bits"], "psnr": r["mean_psnr"], "saving": sav,
                "over_pct": over, "over": r["total_bits"] > self.budget, "score": score, "reward": rew,
                "static_score": st["score"], "qps": list(self.qps), "frame_bits": [int(x) for x in r["bits"]],
                "frames_seen": float(np.mean(self.k_seen)), "shield_fires": int(getattr(self, "n_shield", 0))}


# ---------------------------------------------------------------- offline trajectories

def plan_observations(info, budget, acts, bits, k=5, mode="fixed", drop=(), prior=False, extra="", fpsnr=None):
    """Observations a policy would have seen along a logged plan (exact, by the prefix property). Shape (30, dim)."""
    env = RateEnv({info["gop"]["id"]: info}, k=k, mode=mode, drop=drop, prior=prior, extra=extra)
    env.force(info["gop"]["id"], budget)
    obs = [env.reset()[0]]
    for t in range(C.GOP - 1):
        env.t = t + 1
        env.acts = list(acts[:t + 1])
        env.qps = [int(budget + STATIC_OFF[j] + C.ACTIONS[acts[j]]) for j in range(t + 1)]
        env.bits = [int(x) for x in bits[:t + 1]]
        if extra:
            env.psnr = [float(x) for x in fpsnr[:t + 1]]
        obs.append(env._obs())
    return np.stack(obs)


# ---------------------------------------------------------------- per-frame lookahead gate (D23)

class GateEnv(RateEnv):
    """Each step a gate (this env's agent, 2 actions) sees the k=0 observation and hands frame t to the k=0 policy
    (action 0) or to the k=K policy (action 1). Terminal reward = the GOP's reward - lam x share of frames given to
    the k=K policy / REWARD_SCALE (lam in score points for a whole GOP with lookahead)."""

    def __init__(self, infos, gate=None, **kw):
        kw = {**kw, "k": gate["k"]}
        super().__init__(infos, **kw)
        from . import policies as P
        self.subs = [P.make(gate["pol0"]), P.make(gate["polk"])]
        self.K, self.glam = gate["k"], gate["lam"]
        self.dim = OBS_DIM
        self.observation_space = spaces.Box(-10, 10, (OBS_DIM,), np.float32)
        self.action_space = spaces.Discrete(2)

    def reset(self, seed=None, options=None):
        self.used = []
        super().reset(seed, options)
        self.K_ep, self.k_seen = self.k_ep, []
        return self._gate_obs(), {}

    def _gate_obs(self):
        self.k_ep = 0
        o0 = self._obs()
        self.k_seen.pop()
        return o0

    def step(self, g):
        g = int(g)
        self.k_ep = self.K_ep if g else 0
        obs = self._obs()            # appends the frames actually seen to k_seen
        a = self.subs[g](self, obs)
        self.used.append(g)
        _, rew, done, trunc, res = super().step(a)
        if not done:
            self.k_seen.pop()        # the base step's own observation is not used
            return self._gate_obs(), 0.0, False, False, {}
        res["gate_share"] = float(np.mean(self.used))
        res["reward"] = rew - self.glam * res["gate_share"] / REWARD_SCALE
        return np.zeros(OBS_DIM, np.float32), res["reward"], True, False, res


def make_env(infos, gate=None, **kw):
    return GateEnv(infos, gate=gate, **kw) if gate else RateEnv(infos, **kw)
