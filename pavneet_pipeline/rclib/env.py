"""Gym environment: one episode = one GOP under one budget; each step picks frame t's QP offset.

Observation = global/state features + current-frame features + a lookahead window of up to KMAX future frames.
Lookahead is strict: features of frames beyond the visible window are zeroed (with a 'visible' flag), and every
summary feature (window mean cost, scene share, distance to next cut) is computed over visible frames only.
Which future frames are visible is set by a lookahead *mode* (fixed k, scene-truncated, scene-extended, cut-triggered,
per-GOP k), see `visible_len`. Feature groups can be switched off (zeroed) for ablations.

Each step is one real prefix encode of frames 0..t (prefix property verified in tools/codec_check.py); the last step's
encode is decoded for PSNR. Reward is 0 until the end, then (score - STATIC score) / REWARD_SCALE, or a Lagrangian
variant (saving - lambda * overshoot).

Residual arm (RC_ARM=res, v1-data branch, P2 2026-11-09): frame t's QP = P2's causal controller QP (rclib/controller.py,
fed the real bits and QPs of frames < t and the first pass of frames t..t+k) + the action's offset, clipped to
QP_LO..QP_HI. The controller QP for the current frame is observation slot 15 ((q - 30) / 10; 'prior' must be off).
The baseline subtracted in the reward is the controller's own result on that GOP x level x k (info["ctrl"]).

lfq learners (RC_ARM=lfq with RC_ACT_RANGE set, config.LFQ_LEARN; P2 2026-11-10): frame t's QP =
round(base + RAMP[t] + offset) clipped to QP_LO..QP_HI, base = the CAUSAL base-QP estimate for (level, k)
(info["base"], P2 budgets.csv base_qp_est_k<k>), shown in observation slot 15 ((base - 30) / 10; 'prior' must be off).
Under METRIC=dpsnr (rclib/metrics.py) the scores and rewards are in dB: 'relative' = score - base score,
'lagrangian' = dPSNR_B - base dPSNR_B - lam x %over with lam in dB per 1% (rl.py: 0.34 = 2x the metric's 0.17);
the base is the hindsight search's start plan (info["static"], tools/lfq_infos.py; reward offset only).
"""
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from . import codec, config as C, data, metrics
if C.RES:
    from . import controller as CTRL

KMAX = C.GOP - 1
F_FRAME = 11            # per-frame feature width (incl. 'visible' flag)
F_GLOBAL = 16
OBS_DIM = F_GLOBAL + F_FRAME * (1 + KMAX)
# score points (% of bits) / 10; under METRIC=dpsnr the score is in dB, which is ~10-20x smaller, so no scaling
REWARD_SCALE = 1.0 if metrics.METRIC == "dpsnr" else 10.0
# optional extra global features appended after OBS_DIM (D23):
#   fb   achieved PSNR (last, mean), bit-prediction error (last, mean), frames since the last cut, last-mean PSNR
#   sum  fb + a summary of the visible window (mean/max/min cost, any cut, where it is, cost after vs before it)
#        that replaces the raw lookahead slots (slot 0, the current frame, is kept)
#   f4   (res arm only; P2 next-exp R2, 11-13) final4's state before frame t: planned QP, level, log2 of the plan's
#        predicted spend over the remaining budget, log2 of calibrated c_P over its prior, frames left
EXTRA = {"": 0, "fb": 6, "sum": 13, "f4": 5}
STATIC_OFF = np.array(C.static_offsets(), float)

# feature groups -> (global indices, per-frame indices). 'budget' state and position are never ablated.
GROUPS = {
    "history": ([5, 6, 7, 8], []),
    "fp": ([9, 13], [0]),
    "pixel": ([], [1, 2, 3, 4]),
    "scene": ([10, 11, 12], [5, 6, 7, 10]),
    # P2 11-13: o[2] = (budget level != lowest level) is clip-level hindsight under v1's clip-mean budgets; eval-only
    # ablation (exp_next/o2) and zeroed for BC / R3. Never part of a default.
    "level": ([2], []),
}


def frame_qp(base, t, a):
    """QP of frame t at offset index a around `base` (orig/dec/lf/res-free arms: base = the budget key, as before)."""
    if C.LFQ_LEARN:
        return int(np.clip(round(base + STATIC_OFF[t] + C.ACTIONS[a]), C.QP_LO, C.QP_HI))
    return int(base + STATIC_OFF[t] + C.ACTIONS[a])


def offsets_for(qps, base):
    """lfq learners: offset indices that reproduce `qps` around `base`, or None if a frame needs an offset outside
    +-RC_ACT_RANGE (or a clipped QP would differ)."""
    acts = []
    for t, q in enumerate(qps):
        o = int(q) - int(round(base + STATIC_OFF[t]))
        if o < C.ACTIONS[0] or o > C.ACTIONS[-1]:
            return None
        a = C.ACTIONS.index(o)
        if frame_qp(base, t, a) != int(q):
            return None
        acts.append(a)
    return np.array(acts, np.int64)


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
                 k_sampler=None, reward="relative", lam=0.0, prior=False, extra="", cut_weight=1.0, shape=0.0,
                 o2_table=None, res_mean=None):
        super().__init__()
        # P2 11-14 (Exp 4 R3): a fixed real-valued per-frame shift added to final4's real QP before its rounding
        # (as Exp 5a's res_float), set at every reset; None = unchanged
        self.res_mean = None if res_mean is None else np.asarray(res_mean, float)
        # P2 11-13 (exp_next/o2, eval only): {(gid, level, k): value} replaces o[2] per episode (causal stand-in from
        # final4's frame-0 planning QP); None = unchanged
        self.o2_table, self.o2_value = o2_table, None
        self.shape = float(shape)       # potential-based shaping weight (v1-data branch, P2 2026-11-09); 0 = off
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
        if C.RES:
            assert not prior, "res arm: observation slot 15 holds the controller QP"
            self.ctrl_model = CTRL.load_model(C.CODEC, C.CTRL_MODEL)
        assert not (prior and C.LFQ_LEARN), "lfq learners: observation slot 15 holds the causal base QP"
        assert extra != "f4" or C.RES, "extra f4 needs the res arm"
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
        self.base = float(self.info["base"][(self.b, self.k_ep)]) if C.LFQ_LEARN else self.b
        if C.RES:   # history controllers (tracker 31): the qhat / rate-prior scale the controller used on this GOP
            r = self.info.get("ctrl_r", {}).get((self.b, self.k_ep), 1.0)
            self.ctrl_M = self.ctrl_model if r == 1.0 else dict(self.ctrl_model, c_i=self.ctrl_model["c_i"] * r,
                                                                c_p=self.ctrl_model["c_p"] * r)
            self.ctrl_qhat = self.info.get("ctrl_qhat", self.info.get("base", {})).get((self.b, self.k_ep))
        self.cut = self.info["an"]["cut"]
        self.path = data.gop_path(self.info["gop"])
        self.t, self.qps, self.acts, self.bits, self.psnr = 0, [], [], [], []
        self.k_seen, self.ctrl_qps = [], []
        self.o2_value = None if self.o2_table is None else float(self.o2_table[(self.gid, self.b, self.k_ep)])
        if self.res_mean is not None:
            self.res_float = self.res_mean
        self.n_dmax = self.n_fcap = self.n_range = 0
        self.q_override, self.n_shield = None, 0     # set by policies.Shield (eval only, v1-data branch)
        if self.shape:
            self.phi0, self.phi_prev, self.shaping_sum = self._phi_raw(), 0.0, 0.0
        return self._obs(), {}

    # -- potential-based reward shaping (v1-data branch, P2 2026-11-09)
    # Phi(s_t) = -pen x predicted overshoot % / REWARD_SCALE, pen = lam (lagrangian) or the score's 2 per 1% (relative).
    # Prediction: bits spent so far + the remaining frames at the default plan (offset 0), taken from the real encode
    # of the default plan (info["static"][b]["bits"], so Phi(s_0) is exact), scaled by a calibration = actual / predicted
    # bits of the frames already coded, where a frame coded at offset a is predicted as its default-plan bits x
    # 2^(-a / s) (s = 6.8 I / 5.0 P QP per halving, the train-fitted slopes of the budget shield), shrunk toward 1 with
    # weight t / (t + 3). Infos without a default-plan encode (lf arm) fall back to the constant-QP per-frame table.
    # The reward uses this hindsight data, never the observation. Phi is measured relative to the episode's start and
    # Phi(terminal) = 0, so the shaping terms of an episode sum to exactly 0: the return, and the optimal policy, are
    # unchanged; only the per-step credit assignment changes (Ng et al. 1999).
    SLOPE_I, SLOPE_P = 6.8, 5.0

    def _default_bits(self):
        st = self.info.get("static", {}).get(self.b)
        if st is not None and "bits" in st:
            return np.asarray(st["bits"], float)
        fb = self.info["curve"]["frame_bits"]
        out = []
        for j in range(C.GOP):
            q = int(self.b + STATIC_OFF[j])
            qc = int(np.clip(q, C.QPS[0], C.QPS[-1]))
            out.append(float(fb[C.QPS.index(qc), j]) * 2.0 ** (-(q - qc) / 6.0))
        return np.asarray(out)

    def _phi_raw(self):
        if getattr(self, "_db_key", None) != (self.gid, self.b):
            self._db, self._db_key = self._default_bits(), (self.gid, self.b)
        db = self._db
        t = len(self.bits)
        spent = float(sum(self.bits))
        if t:
            pred_done = sum(db[j] * 2.0 ** (-C.ACTIONS[self.acts[j]] / (self.SLOPE_I if j == 0 else self.SLOPE_P))
                            for j in range(t))
            cal = float(np.exp(t / (t + 3.0) * np.log(max(spent, 8.0) / max(pred_done, 8.0))))
        else:
            cal = 1.0
        over = 100.0 * max(0.0, (spent + cal * float(db[t:].sum())) / self.budget - 1.0)
        pen = self.lam if self.reward_kind == "lagrangian" else (
            metrics.OVER_PENALTY_DB if metrics.METRIC == "dpsnr" else metrics.OVER_PENALTY)
        return -pen * over / REWARD_SCALE

    def _shaping(self, last):
        phi = 0.0 if last else self._phi_raw() - self.phi0
        f = self.shape * (phi - self.phi_prev)
        self.phi_prev = phi
        self.shaping_sum += f
        return f

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
        o[2] = float(self.b != C.BUDGET_QPS[0]) if self.o2_value is None else self.o2_value
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
        if C.LFQ_LEARN:     # the causal base QP the offsets are relative to
            o[15] = (self.base - 30) / 10
        if C.RES:       # the controller's causal QP for frame t (same inputs it gets when run on its own)
            self.ctrl_diag = {}
            self.q_ctrl = CTRL.decide(t, self.bits, self.qps, fp, self.budget, self.k_ep, self.ctrl_M,
                                      *C.CTRL_SETTING, qhat=self.ctrl_qhat, diag=self.ctrl_diag)
            o[15] = (self.q_ctrl - 30) / 10
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
        if self.extra == "f4":
            d = self.ctrl_diag
            e[0] = (self.q_ctrl - 30) / 10
            e[1] = (d["level"] - 30) / 10
            e[2] = np.log2(max(d["plan_ratio"], 1e-3)) / 2
            e[3] = np.log2(max(d["c_p"], 1e-6) / self.ctrl_M["c_p"]) / 2
            e[4] = (C.GOP - t) / C.GOP
            return
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
        if C.RES:
            self.ctrl_qps.append(int(self.q_ctrl))
            q = int(np.clip(self.q_ctrl + C.ACTIONS[a], C.QP_LO, C.QP_HI))
            if getattr(self, "res_float", None) is not None:   # Exp 5a: real-valued offset before final4's rounding
                q = int(np.clip(round(self.ctrl_diag["q_real"] + float(self.res_float[t])) + C.ACTIONS[a],
                                C.QP_LO, C.QP_HI))
            if C.RES_RECAP and t > 0:     # decide()'s own limits again, in its order (cut boost b is 0 in the env)
                d = self.ctrl_diag
                if d["rem"] <= 0:
                    q = C.QP_HI
                else:
                    q = max(q, int(d["q_fcap_min"]))
                    if C.RES_RECAP == "full":
                        if C.CTRL_SETTING[4] < 51:
                            q = int(np.clip(q, d["ref"] - C.CTRL_SETTING[4], d["ref"] + C.CTRL_SETTING[4]))
                        q = max(q, self.qps[0] + C.CTRL_SETTING[7])
                    q = int(np.clip(q, C.QP_LO, C.QP_HI))
        else:
            q = frame_qp(self.base, t, a)
        if getattr(self, "q_override", None) is not None:      # budget shield forced a QP outside the action range
            q, self.q_override = int(self.q_override), None
        self.qps.append(q)
        self.acts.append(a)
        last = t == C.GOP - 1
        if C.RES:   # how often the offset takes the QP past final4's own limits (caps are not re-applied)
            d = self.ctrl_diag
            dmax = C.CTRL_SETTING[4]
            ref = d.get("ref")      # None at frame 0 (no step limit or fcap there)
            self.n_dmax += int(ref is not None and abs(q - ref) > dmax and abs(q - ref) > abs(self.q_ctrl - ref))
            self.n_fcap += int(ref is not None and q < d["q_fcap_min"] and q < self.q_ctrl)
            self.n_range += int(self.q_ctrl + C.ACTIONS[a] != q)
        r = codec.encode(self.path, self.qps, measure=last or self.extra in ("fb", "sum"))
        self.bits = [int(x) for x in r["bits"]]
        if self.extra in ("fb", "sum"):
            self.psnr = [float(x) for x in r["psnr"]]
        self.t += 1
        f = self._shaping(last) if self.shape else 0.0
        if not last:
            return self._obs(), f, False, False, {}
        res = self.result(r)
        if self.shape:
            res["shaping_sum"] = self.shaping_sum      # must be ~0 (telescoping check)
        return np.zeros(self.dim, np.float32), res["reward"] + f, True, False, res

    def result(self, r):
        curve = self.info["curve"]
        st = self.info["ctrl"][(self.b, self.k_ep)] if C.RES else self.info["static"].get(self.b)
        if st is None:          # lfq smoke builds without a search start for this split (tools/lfq_infos.py)
            st = {"score": np.nan, "dpsnr": np.nan, "saving": np.nan}
        sav = float(metrics.saving(r["total_bits"], r["mean_psnr"], curve))
        over = float(metrics.overshoot(r["total_bits"], self.budget))
        dq = float(metrics.dpsnr_budget(r["mean_psnr"], curve, self.budget))
        score = float(metrics.score(r["total_bits"], r["mean_psnr"], curve, self.budget))
        # Lagrangian: the metric's quality term (saving, or dPSNR_B) minus lam x %over, relative to the base plan
        qual, qual_b = (dq, st.get("dpsnr")) if metrics.METRIC == "dpsnr" else (sav, st.get("saving"))
        if self.reward_kind == "relative":
            rew = (score - st["score"]) / REWARD_SCALE
        elif self.reward_kind == "lagrangian":
            rew = (qual - qual_b - self.lam * over) / REWARD_SCALE
        else:
            raise ValueError(self.reward_kind)
        return {"gid": self.gid, "budget": self.b, "bits": r["total_bits"], "psnr": r["mean_psnr"], "saving": sav,
                "over_pct": over, "over": r["total_bits"] > self.budget, "score": score, "reward": rew,
                "dpsnr_b": dq, "score_old": sav - metrics.OVER_PENALTY * over, "use": r["total_bits"] / self.budget,
                **({"base_q": self.base} if C.LFQ_LEARN else {}),
                "static_score": st["score"], "qps": list(self.qps), "frame_bits": [int(x) for x in r["bits"]],
                "frames_seen": float(np.mean(self.k_seen)), "shield_fires": int(getattr(self, "n_shield", 0)),
                **({"ctrl_qps": list(self.ctrl_qps), "k": self.k_ep, "n_beyond_dmax": self.n_dmax,
                    "n_beyond_fcap": self.n_fcap, "n_clip_range": self.n_range} if C.RES else {})}


# ---------------------------------------------------------------- offline trajectories

def plan_observations(info, budget, acts, bits, k=5, mode="fixed", drop=(), prior=False, extra="", fpsnr=None):
    """Observations a policy would have seen along a logged plan (exact, by the prefix property). Shape (30, dim)."""
    env = RateEnv({info["gop"]["id"]: info}, k=k, mode=mode, drop=drop, prior=prior, extra=extra)
    env.force(info["gop"]["id"], budget)
    obs = [env.reset()[0]]
    for t in range(C.GOP - 1):
        env.t = t + 1
        env.acts = list(acts[:t + 1])
        env.qps = [frame_qp(env.base, j, acts[j]) for j in range(t + 1)]
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
