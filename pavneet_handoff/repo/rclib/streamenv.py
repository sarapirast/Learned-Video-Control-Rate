"""Stream-level rate control on dataset v1, scored on quality at the budget (D34).

Same episode as D25 (rclib/clipenv.py): a stream of N_GOP IDR GOPs under ONE bit budget; each step picks the next GOP's
constant QP as an offset -6..+6 on the causal model QP; outcomes are read from the encoder's real constant-QP curves,
so no encodes run. What changes:

* Data: dataset v1 (Aayush's clips, splits and clip-level budgets). Splice clips are excluded.
* Budget: evaluation streams use the sum of each GOP's v1 budget (budgets.csv: clip mean of the constant-QP bits at
  level q0 in {24, 30, 36, 42}) times s in EVAL_S. Training draws q0 uniformly in TRAIN_Q0 and s in TRAIN_S, with the
  same clip-mean construction. Neither q0 nor s is observed: the policy sees only the budget and the first pass.
* Score: P2's dB metric, score = dPSNR_B - 0.17 dB per 1 % over, where dPSNR_B is the stream's pooled (MSE) PSNR minus
  the PSNR of the stream's constant-QP curve at exactly the budget. Unused budget is no longer free.
* Reward: score_db at the end of the stream (REWARD_SCALE 1: dB values are already O(1)); with lam > 0 the reward
  instead charges lam dB per 1 % over (Lagrangian variant; the reported score always uses 0.17).
* The model QP has a margin m (spend m x the remaining budget). m is a baseline hyper-parameter tuned on val; the
  learners always see m = 1.

Baselines (experiments/stream_rl.py): 'split' gives every GOP an equal share B/N with no carry-over (the per-GOP
setting all earlier work used), 'rule' is offset 0 on the remaining-budget model QP with m tuned on val, and the
hindsight per-GOP plan is the offline ceiling.
"""
import numpy as np

from . import clipenv as CE, config as C, metrics

N_GOP = CE.N_GOP
ACTIONS, ZERO, OBS_DIM = CE.ACTIONS, CE.ZERO, CE.OBS_DIM
LEVELS = (24, 30, 36, 42)
TRAIN_Q0 = CE.TRAIN_Q0   # (24, 44), drawn by ClipEnv.reset
TRAIN_S = CE.TRAIN_S
EVAL_S = (0.85, 1.0, 1.18)


def clip_means(infos, ids):
    """clip -> mean constant-QP bits per GOP at every QP (over the clip's GOPs in `ids`), indexed by QP."""
    by = {}
    for g in ids:
        by.setdefault(infos[g]["gop"]["clip"], []).append(CE.gop_table(infos[g])["bits"])
    return {c: np.nanmean(v, 0) for c, v in by.items()}


def prior_c0(tables, ids, qpd):
    """Median ratio of constant-QP bits to the first-pass model with c = 1 and slope qpd, over (training) GOPs."""
    r = [tables[g]["bits"][q] / (tables[g]["fp"] * 2.0 ** (-(q - CE.FP_QP) / qpd)) for g in ids for q in (26, 30, 34, 38, 42)]
    return float(np.nanmedian(r))


def gop_budget(infos, g, q0):
    return float(infos[g]["budget"][q0])


def stream_score(tabs, bits, psnr, B):
    curve = CE.stream_curve(tabs)
    d = float(metrics.dpsnr_budget(psnr, curve, B))
    over = float(metrics.overshoot(bits, B))
    return d, over, d - metrics.OVER_PENALTY_DB * over


def hindsight(tabs, B):
    """Offline per-GOP plan maximising score_db, with every GOP's curve known: candidates are every constant QP and a
    Lagrangian sweep (each GOP minimises MSE + lam x bits), then greedy single-GOP +-1 moves while the score improves."""
    q = np.arange(C.QP_MIN, C.QP_MAX + 1)
    n = len(tabs)
    Bt = np.array([t["bits"][q] for t in tabs])
    Pt = np.array([t["psnr"][q] for t in tabs])
    Mt = 10 ** (-Pt / 10)
    r = np.arange(n)

    def sc(idx):
        return stream_score(tabs, Bt[r, idx].sum(), CE.pooled(Pt[r, idx]), B)[2]
    cands = [np.full(n, i) for i in range(len(q))]
    for lam in np.geomspace(1e-4, 1e2, 400) * n * Mt.mean() / max(B, 1):
        cands.append(np.argmin(Mt + lam * Bt, 1))
    best = max(cands, key=sc)
    bs = sc(best)
    improved = True
    while improved:
        improved = False
        for g in range(n):
            for d in (-1, 1):
                if 0 <= best[g] + d < len(q):
                    t = best.copy()
                    t[g] += d
                    s = sc(t)
                    if s > bs + 1e-9:
                        best, bs, improved = t, s, True
    return q[best]


class StreamEnv(CE.ClipEnv):
    def __init__(self, infos, ids, look=0, seed=0, c0=None, n=N_GOP, lam=0.0, margin=1.0, mode="rule", rp=None):
        super().__init__(infos, ids, look=look, seed=seed, c0=c0, n=n)
        self.infos, self.lam, self.margin, self.mode = infos, lam, margin, mode
        self.rp = rp   # baseline rule parameters {qpd, cw, c0}: its own rate-model slope, prior weight and prior; None = D25
        self.cm = clip_means(infos, self.ids)

    def reset(self, seed=None, options=None):
        o, i = super().reset(seed=seed, options=options)
        if self.forced:
            self.B = self.s * sum(gop_budget(self.infos, g, self.q0) for g in self.stream)
        else:
            self.B = self.s * sum(self.cm[self.infos[g]["gop"]["clip"]][self.q0] for g in self.stream)
        return self._obs(), i

    def _rule_q(self):
        """Baseline rule with tuned rate model: bits = c x fp x 2^(-(q - 30) / qpd), c = geometric mean of the prior c0
        (weight cw) and the ratios of the GOPs already coded."""
        qpd, cw, c0 = self.rp["qpd"], self.rp["cw"], self.rp["c0"]
        lr = [np.log(b / (t["fp"] * 2.0 ** (-(q - CE.FP_QP) / qpd))) for b, q, t in zip(self.bits, self.qps, self.tabs)]
        c = float(np.exp((cw * np.log(c0) + sum(lr)) / (cw + len(lr))))
        i, n = self.i, self.n
        fps = np.array([t["fp"] for t in self.tabs])
        if self.mode == "split":
            R, rem = self.margin * self.B / n, fps[i]
        else:
            vis = min(n, i + 1 + self.look)
            R, rem = self.margin * self.B - self.spent, fps[i:vis].sum() + (n - vis) * fps[:vis].mean()
        if R <= 0:
            return float(C.QP_MAX)
        return float(np.clip(CE.FP_QP - qpd * np.log2(R / (c * rem)), C.QP_MIN, C.QP_MAX))

    def q_hat(self):
        if self.rp is not None:
            return self._rule_q()
        if self.mode == "split":   # equal share per GOP, no carry-over: QP whose model spend is B / N for this GOP
            t = self.tabs[self.i]
            share = self.margin * self.B / self.n
            return float(np.clip(CE.FP_QP - CE.QP_PER_DOUBLING * np.log2(share / (self.calib() * t["fp"])),
                                 C.QP_MIN, C.QP_MAX))
        B0 = self.B
        self.B = self.margin * B0   # plan against m x the budget: remaining = m x B - spent
        try:
            return super().q_hat()
        finally:
            self.B = B0

    def step(self, a, q=None):
        o, r, done, trunc, info = super().step(a, q=q)
        if done:
            r = info["score"] if self.lam <= 0 else info["dpsnr"] - self.lam * info["over_pct"]
        return o, r, done, trunc, info

    def result(self):
        tot, mp = float(sum(self.bits)), float(CE.pooled(self.psnrs))
        d, over, s = stream_score(self.tabs, tot, mp, self.B)
        return {"stream": self.stream, "q0": self.q0, "s": self.s, "bits": tot, "budget": self.B, "use": tot / self.B,
                "psnr": mp, "dpsnr": d, "over_pct": over, "over": tot > 1.01 * self.B, "score": s,
                "qps": list(self.qps)}
