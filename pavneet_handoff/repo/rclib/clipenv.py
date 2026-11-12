"""Multi-GOP rate control (D25): one episode = a stream of N_GOP independent IDR GOPs under one shared bit budget.

This is the setting where the per-GOP hindsight search does not scale (8 GOPs x 33 QPs each) and per-GOP imitation has
no teacher for moving bits between GOPs. Each step picks the next GOP's QP; the GOP is coded at that constant QP and
its bits and PSNR are read from the encoder's own constant-QP curve (real encodes made by infos.py), so no encodes run
and an episode costs microseconds. Frame-level QP inside the GOP is not controlled here.

Budget = s x (bits of every GOP of the stream at one constant QP q0), with s random, so the QP that meets the budget is
unknown to the controller, which is only told the budget (like a bitrate target). The causal 'model QP' q_hat is the
QP that a first-pass rate model, bits = c x first-pass bits x 2^(-(q - 30) / 6) with c calibrated online on the GOPs
already coded, predicts will spend the remaining budget over the remaining GOPs (GOPs beyond the lookahead are assumed
to cost the mean of those seen). Action = offset -6..+6 on round(q_hat); offset 0 everywhere is the hand rule.

Score = % bits saved at equal mean PSNR vs the stream's constant-QP curve (summed GOP bits, mean GOP PSNR at each QP)
- 2 x % over budget; reward = score / 10 at the end of the stream.
"""
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from . import config as C, metrics

N_GOP = 8
LMAX = 4                     # GOPs of lookahead the observation has room for
ACTIONS = tuple(range(-6, 7))   # per-GOP offsets on the model QP (the hindsight plan moves GOPs well beyond +-3)
ZERO = ACTIONS.index(0)
OBS_DIM = 15 + 2 * LMAX
REWARD_SCALE = 10.0
FP_QP = 30                   # first-pass QP of fp_bits (codec.first_pass)
TRAIN_Q0 = (24, 44)          # training budgets: q0 uniform in this range, s uniform in TRAIN_S
TRAIN_S = (0.8, 1.25)
EVAL_Q0 = C.BUDGET_QPS
EVAL_S = (0.85, 1.0, 1.18)


def gop_table(info):
    an = info["an"]
    fp = np.maximum(np.asarray(info["fp_bits"], float), 8)
    q = np.asarray(info["curve"].get("qps", C.QPS), int)
    bits = np.full(C.QP_MAX + 1, np.nan)
    psnr = np.full(C.QP_MAX + 1, np.nan)
    bits[q], psnr[q] = info["curve"]["bits"], info["curve"]["psnr"]
    return {"fp": fp.sum(), "bits": bits, "psnr": psnr,
            "feat": np.array([min(an["cut"][1:].sum(), 3) / 3, float(an["fade"].sum() > 0), an["spatial"].mean() / 20,
                              np.log1p(an["msad"].mean()) / 3, np.log2(fp[0] / fp[1:].mean()) / 4], np.float32)}


QP_PER_DOUBLING = 5.5       # fitted on training GOPs, QP 24-44 (5.46 x265, 5.52 x264)


def fp_model(fp, q, c):
    return c * fp * 2.0 ** (-(q - FP_QP) / QP_PER_DOUBLING)


def calib_prior(tables, ids):
    """Median ratio of the GOP's constant-QP bits to the first-pass model with c = 1, over training GOPs."""
    r = [tables[g]["bits"][q] / fp_model(tables[g]["fp"], q, 1.0) for g in ids for q in (26, 30, 34, 38, 42)]
    return float(np.median(r))


def pooled(psnrs, axis=None):
    """PSNR of the mean MSE of GOPs given their PSNRs (equal frame counts)."""
    return -10 * np.log10(np.mean(10 ** (-np.asarray(psnrs, float) / 10), axis=axis))


def stream_curve(tabs):
    q = np.arange(C.QP_MIN, C.QP_MAX + 1)
    return {"bits": np.sum([t["bits"][q] for t in tabs], 0), "psnr": pooled([t["psnr"][q] for t in tabs], 0)}


def episodes(infos, split, seed=0, n_mixed=100, n=N_GOP):
    """Fixed evaluation streams: every non-overlapping run of n time-ordered GOPs of one source clip ('clip'), and
    n_mixed streams of n GOPs from different clips ('mixed')."""
    by = {}
    for g, x in infos.items():
        if x["gop"]["split"] == split and x["gop"]["family"] != "splice":
            by.setdefault(x["gop"]["clip"], []).append((x["gop"]["start"], g))
    out = []
    for c, lst in sorted(by.items()):
        lst = [g for _, g in sorted(lst)]
        out += [("clip", tuple(lst[i:i + n])) for i in range(0, len(lst) - n + 1, n)]
    rng = np.random.default_rng(seed)
    clips = sorted(by)
    for _ in range(n_mixed):
        cs = rng.choice(len(clips), n, replace=False)
        out.append(("mixed", tuple(by[clips[i]][rng.integers(len(by[clips[i]]))][1] for i in cs)))
    return out


def hindsight(tabs, B):
    """Offline optimum with full knowledge of every GOP's constant-QP curve: per-GOP QPs maximising the score, by a
    Lagrangian sweep (each GOP minimises MSE + lam x bits) plus every single constant QP, then a greedy pass that
    lowers one GOP's QP at a time while the budget allows. Returns (per-GOP QPs, best constant QP)."""
    q = np.arange(C.QP_MIN, C.QP_MAX + 1)
    Bt = np.array([t["bits"][q] for t in tabs])
    Pt = np.array([t["psnr"][q] for t in tabs])
    Mt = 10 ** (-Pt / 10)
    curve = stream_curve(tabs)

    def sc(idx):
        b, p = Bt[np.arange(len(tabs)), idx].sum(), pooled(Pt[np.arange(len(tabs)), idx])
        return float(metrics.score(b, p, curve, B))
    cands = [np.full(len(tabs), i) for i in range(len(q))]
    const = max(cands, key=sc)
    m0 = Mt.mean()
    for lam in np.geomspace(1e-4, 1e2, 400) * len(tabs) * m0 / max(B, 1):
        cands.append(np.argmin(Mt + lam * Bt, 1))
    best = max(cands, key=sc)
    improved = True
    while improved:
        improved = False
        for g in np.argsort(Bt[np.arange(len(tabs)), best]):
            if best[g] > 0:
                t = best.copy()
                t[g] -= 1
                if sc(t) > sc(best):
                    best, improved = t, True
    return q[best], int(q[const[0]])


class ClipEnv(gym.Env):
    metadata = {}

    def __init__(self, infos, ids, look=0, seed=0, c0=None, n=N_GOP):
        super().__init__()
        self.tables = {g: gop_table(infos[g]) for g in ids}
        by = {}
        for g in ids:
            x = infos[g]["gop"]
            if x["family"] != "splice":
                by.setdefault(x["clip"], []).append((x["start"], g))
        self.clips = {c: [g for _, g in sorted(v)] for c, v in by.items()}
        self.long = [c for c, v in self.clips.items() if len(v) >= n]
        self.ids = [g for v in self.clips.values() for g in v]
        self.look, self.n = look, n
        self.c0 = c0 if c0 is not None else calib_prior(self.tables, self.ids)
        self.rng = np.random.default_rng(seed)
        self.observation_space = spaces.Box(-10, 10, (OBS_DIM,), np.float32)
        self.action_space = spaces.Discrete(len(ACTIONS))
        self.forced = None

    def force(self, stream, q0, s):
        self.forced = (tuple(stream), q0, s)

    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        if self.forced:
            self.stream, q0, s = self.forced
        else:
            if self.rng.random() < 0.5:
                c = self.long[self.rng.integers(len(self.long))]
                i = self.rng.integers(len(self.clips[c]) - self.n + 1)
                self.stream = tuple(self.clips[c][i:i + self.n])
            else:
                cs = self.rng.choice(len(self.clips), self.n, replace=False)
                names = list(self.clips)
                self.stream = tuple(self.clips[names[j]][self.rng.integers(len(self.clips[names[j]]))] for j in cs)
            q0 = int(self.rng.integers(TRAIN_Q0[0], TRAIN_Q0[1] + 1))
            s = float(self.rng.uniform(*TRAIN_S))
        self.tabs = [self.tables[g] for g in self.stream]
        self.q0, self.s = q0, s
        self.B = s * sum(t["bits"][q0] for t in self.tabs)
        self.i, self.spent, self.qps, self.bits, self.psnrs, self.logr, self.acts = 0, 0.0, [], [], [], [], []
        return self._obs(), {}

    def calib(self):
        return float(np.exp((np.log(self.c0) + sum(self.logr)) / (1 + len(self.logr))))

    def q_hat(self):
        i, n = self.i, self.n
        fps = np.array([t["fp"] for t in self.tabs])
        vis = min(n, i + 1 + self.look)
        seen = fps[:vis].mean()
        rem = fps[i:vis].sum() + (n - vis) * seen
        R = self.B - self.spent
        if R <= 0:
            return float(C.QP_MAX)
        return float(np.clip(FP_QP - QP_PER_DOUBLING * np.log2(R / (self.calib() * rem)), C.QP_MIN, C.QP_MAX))

    def _obs(self):
        o = np.zeros(OBS_DIM, np.float32)
        i, n = self.i, self.n
        qh = self.q_hat()
        fps = np.array([t["fp"] for t in self.tabs])
        vis = min(n, i + 1 + self.look)
        seen = fps[:vis].mean()
        o[0] = i / n
        o[1] = self.spent / self.B
        o[2] = (qh - 34) / 8
        o[3] = qh - round(qh)
        o[4] = np.log2(self.calib() / self.c0)
        o[5] = self.logr[-1] / np.log(2) if self.logr else 0.0
        o[6] = ACTIONS[self.acts[-1]] / 6 if self.acts else 0.0
        o[7] = np.log2(max(self.B - self.spent, 1) / (n - i) / (self.B / n))
        o[8] = np.log2(fps[i] / seen)
        o[9:14] = self.tabs[i]["feat"]
        o[14] = self.look / LMAX
        for j in range(1, LMAX + 1):
            if j <= self.look and i + j < n:
                o[15 + 2 * (j - 1)] = np.log2(fps[i + j] / seen)
                o[16 + 2 * (j - 1)] = 1.0
        return np.clip(o, -10, 10)

    def step(self, a, q=None):
        a = int(a)
        if q is None:
            q = int(np.clip(round(self.q_hat()) + ACTIONS[a], C.QP_MIN, C.QP_MAX))
        t = self.tabs[self.i]
        b, p = float(t["bits"][q]), float(t["psnr"][q])
        self.logr.append(np.log(b / fp_model(t["fp"], q, 1.0)))
        self.qps.append(q)
        self.acts.append(a)
        self.bits.append(b)
        self.psnrs.append(p)
        self.spent += b
        self.i += 1
        if self.i < self.n:
            return self._obs(), 0.0, False, False, {}
        res = self.result()
        return np.zeros(OBS_DIM, np.float32), res["score"] / REWARD_SCALE, True, False, res

    def result(self):
        curve = stream_curve(self.tabs)
        tot, mp = float(sum(self.bits)), float(pooled(self.psnrs))
        sav = float(metrics.saving(tot, mp, curve))
        over = float(metrics.overshoot(tot, self.B))
        return {"stream": self.stream, "q0": self.q0, "s": self.s, "bits": tot, "psnr": mp, "saving": sav,
                "over_pct": over, "over": tot > 1.01 * self.B, "score": sav - metrics.OVER_PENALTY * over,
                "qps": list(self.qps)}

    def rollout_qps(self, qps):
        """Play a fixed QP plan (hindsight oracle); returns observations, the offsets they imply, and the result."""
        obs, acts = [], []
        o, _ = self.reset()
        for q in qps:
            a = int(np.clip(q - round(self.q_hat()), ACTIONS[0], ACTIONS[-1])) - ACTIONS[0]
            obs.append(o)
            acts.append(a)
            o, _, done, _, res = self.step(a, q=int(q))
        return np.array(obs), np.array(acts), res
