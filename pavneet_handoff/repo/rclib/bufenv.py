"""D38: stream rate control through a live channel with a sender buffer (latency limit), scored in luma dB.

Same decision as D34 (each GOP's constant QP as an offset -6..+6 on a base QP; outcomes from the real constant-QP
curves, no encodes), same budgets (B = s x the v1 budgets of the stream's GOPs), but the bits leave through a channel:

* channel: GOP i (1 s) can send R_i = m_i x B / n bits; log m follows an AR(1) (RHO, SIGMA) and is normalised so the
  mean of m over the stream is 1, i.e. the channel carries exactly B. The controller sees R_i only after GOP i was sent.
* sender buffer: F += bits of GOP i, then the channel drains min(F, R_i). The latency limit is CAP = D_CAP x B / n bits
  (D_CAP seconds at the mean rate). If F > CAP after the drain the viewer stalls for (F - CAP) / R_i seconds while the
  excess drains (F = CAP).
* score = dPSNR_B (luma, pooled MSE; rclib/yrd.py) - 0.17 dB per 1 % over the total budget - LAM_STALL dB per 1 % of
  the stream's duration stalled. LAM_STALL is fixed here before any result: a stall costs more than overshoot.

Base QPs: 'rule' = the D34 remaining-budget rule (buffer-blind, tuned rate model); 'vbv' = the same rule, then raised so
that the rate model predicts F + bits - R_hat <= psi x CAP, with R_hat an EMA (alpha) of the observed channel rate
(x264/x265 ABR + VBV logic); psi and alpha tuned on val. Learners act on the vbv QP (offset 0 = vbv rule).
"""
import os
import pickle
import zlib

import numpy as np
from gymnasium import spaces

from . import clipenv as CE, config as C, metastream as MS, streamenv as SE, yrd

# setting (D38 default: AR(1) 0.8 / 0.3, cap 1 s, 0.5 dB per % stalled); the D39 sweep changes one at a time by env var
RHO = 0.8
SIGMA = float(os.environ.get("RC_BUF_SIGMA", 0.3))
D_CAP = float(os.environ.get("RC_BUF_CAP", 1.0))
LAM_STALL = float(os.environ.get("RC_BUF_LAM", 0.5))
CHANNEL = os.environ.get("RC_BUF_CHANNEL", "ar1")        # ar1 | trace (Belgium 4G/LTE logs, per-second throughput)
TRACES = os.environ.get("RC_BUF_TRACES", "/scratch1/pbanga/data/traces/belgium4g/throughput.pkl")
M_FLOOR = 0.05
N_BUF = 7
# Leak fix (TA feedback, 2026-11-17): RC_BUF_LADDER=1 -> the stream budget, and with it the channel's mean rate, no
# longer comes from the stream's own content. B = s x n x LADDER[q0], LADDER[q] = median over dataset-v1 TRAIN GOPs of
# the constant-QP bits per GOP at QP q: the same for every stream, like a fixed bitrate ladder. Before, B = s x the
# sum of the stream's own clip-level budgets, so the mean channel rate B / n told every controller the stream's cost.
LADDER = os.environ.get("RC_BUF_LADDER", "0") == "1"
_LAD = None


def ladder_bits(infos):
    """Per-GOP budget at every QP (index = QP): median over the TRAIN GOPs of `infos` (dataset v1 only)."""
    global _LAD
    if _LAD is None:
        tr = [g for g, x in infos.items() if x["gop"]["split"] == "train"]
        assert tr, "the ladder needs the dataset-v1 train GOPs"
        _LAD = np.nanmedian(np.array([CE.gop_table(infos[g])["bits"] for g in tr]), 0)
    return _LAD


def tag():
    """'' for the D38 default setting, else the changed settings (results go to results_buffer_<tag>)."""
    t = []
    if SIGMA != 0.3:
        t.append(f"sig{SIGMA:g}")
    if D_CAP != 1.0:
        t.append(f"cap{D_CAP:g}")
    if LAM_STALL != 0.5:
        t.append(f"lam{LAM_STALL:g}")
    if CHANNEL != "ar1":
        t.append(CHANNEL)
    if LADDER:
        t.append("ladder")
    return "_".join(t)


_TR = {}


def trace_split(split):
    """Traces split by file (deterministic hash): ~60 % train, 20 % val, 20 % test."""
    if not _TR:
        _TR.update(pickle.load(open(TRACES, "rb")))
    k = {"train": (0, 6), "val": (6, 8), "test": (8, 10)}[split]
    return [v for n, v in sorted(_TR.items()) if k[0] <= zlib.crc32(n.encode()) % 10 < k[1]]


def trace_channel(n, rng, split):
    tr = trace_split(split)
    t = tr[rng.integers(len(tr))]
    while len(t) < n:
        t = np.concatenate([t, t])
    i = rng.integers(len(t) - n + 1)
    m = np.maximum(t[i:i + n] / max(t[i:i + n].mean(), 1.0), 1e-9)
    m = np.maximum(m, M_FLOOR)
    return m / m.mean()
OBS_DIM = MS.OBS_DIM + N_BUF


def channel(n, rng):
    x = np.zeros(n)
    x[0] = rng.normal(0, SIGMA / np.sqrt(1 - RHO ** 2))
    for i in range(1, n):
        x[i] = RHO * x[i - 1] + rng.normal(0, SIGMA)
    m = np.exp(x)
    return m / m.mean()


def case_seed(stream, q0, s):
    return zlib.crc32(("|".join(stream) + f"|{q0}|{s:.3f}").encode())


class BufEnv(MS.MetaStreamEnv):
    def __init__(self, infos, ids, Y, look=0, seed=0, c0=None, n=SE.N_GOP, fb=True, nrange=MS.N_RANGE, rp=None,
                 base="vbv", psi=0.9, alpha=0.5, split="train", bp=None):
        super().__init__(infos, ids, look=look, seed=seed, c0=c0, n=n, fb=fb, nrange=nrange)
        if Y is not None:   # luma PSNR of the constant-QP encodes (pooled over frames); fresh films keep 6:1:1 YUV
            for g, t in self.tables.items():
                p = np.full(C.QP_MAX + 1, np.nan)
                p[yrd.QLO:yrd.QHI + 1] = Y[g]["cq_psnr"]
                t["psnr"] = p
        self.rp, self.base, self.psi, self.alpha, self.split = rp, base, psi, alpha, split
        self.bp = bp or {}     # vbv2 / mpc parameters
        self.observation_space = spaces.Box(-10, 10, (OBS_DIM,), np.float32)
        self.m = None

    def reset(self, seed=None, options=None):
        self.m, self.F, self.stalls, self.Rseen, self.Rhat, self.vol = None, 0.0, [], [], None, 0.0
        super().reset(seed=seed, options=options)
        rng = np.random.default_rng(case_seed(self.stream, self.q0, self.s)) if self.forced else self.rng
        self.m = channel(self.n, rng) if CHANNEL == "ar1" else trace_channel(self.n, rng, self.split)
        if LADDER:
            self.B = self.s * self.n * float(ladder_bits(self.infos)[int(self.q0)])
        self.mean_r = self.B / self.n
        self.cap = D_CAP * self.mean_r
        return self._obs(), {}

    # base QPs -------------------------------------------------------------------------------------------------------
    def _calib(self):
        qpd, cw, c0 = self.rp["qpd"], self.rp["cw"], self.rp["c0"]
        lr = [np.log(b / (t["fp"] * 2.0 ** (-(q - CE.FP_QP) / qpd))) for b, q, t in zip(self.bits, self.qps, self.tabs)]
        return float(np.exp((cw * np.log(c0) + sum(lr)) / (cw + len(lr))))

    def _q_for(self, bits):
        if bits <= 0:
            return float(C.QP_MAX)
        qpd, c = self.rp["qpd"], self._calib()
        return float(CE.FP_QP - qpd * np.log2(bits / (c * self.tabs[self.i]["fp"])))

    def _vbv2_q(self):
        """Buffer-tracking rule: target = cautious rate estimate + beta x (psi x CAP - F); the cautious estimate shrinks
        with the observed rate volatility (kappa); optional remaining-budget clamp (rmargin; None = off)."""
        b = self.bp
        rh = self.Rhat if self.Rhat is not None else self.mean_r
        T = rh * np.exp(-b["kappa"] * self.vol) + b["beta"] * (b["psi"] * self.cap - self.F)
        T = min(T, self.cap + rh - self.F)
        q = self._q_for(T)
        if b.get("rmargin") is not None:
            m0 = self.margin
            self.margin = b["rmargin"]
            q = max(q, self._rule_q())
            self.margin = m0
        return float(np.clip(q, C.QP_MIN, C.QP_MAX))

    def _mpc_q(self):
        """Model-predictive baseline that knows the channel model (AR(1) rho / sigma; for traces an AR(1) fitted on the
        training traces): for each offset -6..+6 on the vbv2 QP, hold that QP for H GOPs, simulate the buffer on K
        sampled channel paths with the calibrated rate model, and pick the offset maximising -gamma x QP - stall cost."""
        b = self.bp
        q0 = self._vbv2_q()
        H = min(b["H"], self.n - self.i)
        fps = np.array([t["fp"] for t in self.tabs])
        vis = min(self.n, self.i + 1 + self.look)
        seen = fps[:vis].mean()
        f = np.array([fps[j] if j < vis else seen for j in range(self.i, self.i + H)])
        c, qpd = self._calib(), self.rp["qpd"]
        rho, sig = b["rho"], b["sig"]
        x0 = np.log(self.Rseen[-1] / self.mean_r) if self.Rseen else 0.0
        rng = np.random.default_rng(1000 * self.i + 17)
        K = 64
        x = np.empty((K, H))
        prev = np.full(K, x0)
        for h in range(H):
            prev = rho * prev + rng.normal(0, sig, K)
            x[:, h] = prev
        R = np.exp(x) * self.mean_r
        best, bq = -np.inf, q0
        for d in range(-6, 7):
            q = float(np.clip(round(q0) + d, C.QP_MIN, C.QP_MAX))
            bits = c * f * 2.0 ** (-(q - CE.FP_QP) / qpd)
            F = np.full(K, self.F)
            st = np.zeros(K)
            for h in range(H):
                F = F + bits[h]
                F = F - np.minimum(F, R[:, h])
                over = np.maximum(F - self.cap, 0)
                st += over / R[:, h]
                F = np.minimum(F, self.cap)
            J = -b["gamma"] * q * H - LAM_STALL * 100 * st.mean() / self.n
            if J > best:
                best, bq = J, q
        return bq

    def base_q(self):
        if self.base == "vbv2":
            return self._vbv2_q()
        if self.base == "mpc":
            return self._mpc_q()
        q = self._rule_q()
        if self.base == "rule":
            return q
        rh = self.Rhat if self.Rhat is not None else self.mean_r
        allow = self.psi * self.cap + rh - self.F       # bits this GOP may add without exceeding psi x CAP
        if allow <= 0:
            return float(C.QP_MAX)
        qpd, c = self.rp["qpd"], self._calib()
        qv = CE.FP_QP - qpd * np.log2(allow / (c * self.tabs[self.i]["fp"]))
        return float(np.clip(max(q, qv), C.QP_MIN, C.QP_MAX))

    def q_hat(self):
        if self.m is None or self.rp is None:     # during the parent's reset, before the channel exists
            return super().q_hat()
        return self.base_q()

    # observation / step ---------------------------------------------------------------------------------------------
    def _obs(self):
        base = super()._obs()
        e = np.zeros(N_BUF, np.float32)
        if self.m is not None:
            e[0] = self.F / self.cap
            e[1] = np.log2(self.Rseen[-1] / self.mean_r) if self.Rseen else 0.0
            e[2] = np.log2(self.Rhat / self.mean_r) if self.Rhat else 0.0
            e[3] = 100 * sum(self.stalls) / self.n
            e[4] = float(self.stalls[-1] > 0) if self.stalls else 0.0
            if self.rp is not None and self.i < self.n:
                e[5] = (self._rule_q() - self.base_q()) / 6
            e[6] = D_CAP
        return np.clip(np.concatenate([base, e]), -10, 10)

    def step(self, a, q=None):
        i = self.i
        o, r, done, trunc, info = SE.StreamEnv.step(self, a, q=q)
        R = self.m[i] * self.mean_r
        self.F += self.bits[-1]
        self.F -= min(self.F, R)
        st = 0.0
        if self.F > self.cap:
            st, self.F = (self.F - self.cap) / R, self.cap
        self.stalls.append(st)
        self.Rseen.append(R)
        if self.Rseen[:-1]:
            dv = abs(np.log(R / self.Rseen[-2]))
            self.vol = dv if len(self.Rseen) == 2 else self.alpha * dv + (1 - self.alpha) * self.vol
        al = self.bp.get("alpha", self.alpha)
        self.Rhat = R if self.Rhat is None else al * R + (1 - al) * self.Rhat
        if done:
            info = self.result()
            r = info["score"]
            return np.zeros(OBS_DIM, np.float32), r, True, False, info
        return self._obs(), 0.0, False, False, {}

    def result(self):
        res = SE.StreamEnv.result(self)
        sp = 100 * sum(self.stalls) / self.n
        res.update(stall_pct=sp, stalled=sp > 0, score=res["score"] - LAM_STALL * sp, score_nostall=res["score"])
        return res
