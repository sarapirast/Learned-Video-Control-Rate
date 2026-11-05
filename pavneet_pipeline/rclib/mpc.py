"""Model-based control: a learned per-frame model of bits and PSNR, and receding-horizon planning (CEM) over the
visible lookahead window.

Model: MLP(frame features, frame QP, QP change vs previous frame, budget level) -> (log2(bits / first-pass bits),
PSNR). Trained on the training search logs (real encodes). Online, a running correction (median actual/predicted bits
over past frames) calibrates the bit predictions to the GOP being encoded.

Plan at step t: offsets for each visible frame t..t+v individually and one shared offset for all invisible frames
(their features are assumed equal to the mean of the visible P frames). Objective: mean predicted PSNR of the GOP
minus a budget penalty — maximising PSNR at fixed bits is the same as maximising the saving; the constant-QP curve is
never used (it is not available to a causal controller). Execute the first action, re-plan next frame.
"""
import numpy as np
import torch
import torch.nn as nn

from . import config as C, env as E

FEATS = 9 + 4
STATIC_OFF = np.array(C.static_offsets(), float)


def frame_inputs(T, qps, budget_level):
    """T: (n, F_FRAME) frame table rows; qps: (..., n) absolute QPs. Returns (..., n, FEATS)."""
    qps = np.asarray(qps, float)
    prev = np.concatenate([qps[..., :1], qps[..., :-1]], -1)
    base = np.broadcast_to(T[:, :9], qps.shape + (9,))
    extra = np.stack([qps / 51.0, (qps - prev) / 6.0, np.full(qps.shape, budget_level),
                      np.broadcast_to(T[:, 8], qps.shape)], -1)
    return np.concatenate([base, extra], -1).astype(np.float32)


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(FEATS, 128), nn.ReLU(), nn.Linear(128, 128), nn.ReLU(), nn.Linear(128, 2))

    def forward(self, x):
        return self.net(x)


def build_rows(infos, search_train, rng, plans_per=24):
    X, Y = [], []
    for g, r in search_train.items():
        T = E.frame_table(infos[g])
        fp = np.maximum(np.asarray(infos[g]["fp_bits"], float), 8)
        for b, x in r.items():
            logs = [e for lg in x["logs"] for e in lg if "fpsnr" in e]
            if not logs:
                continue
            for i in rng.choice(len(logs), min(plans_per, len(logs)), replace=False):
                e = logs[i]
                q = b + STATIC_OFF + np.array([C.ACTIONS[a] for a in e["acts"]])
                X.append(frame_inputs(T, q, float(b != C.BUDGET_QPS[0])))
                Y.append(np.stack([np.log2(np.maximum(e["bits"], 8) / fp), np.asarray(e["fpsnr"], float)], -1))
    return np.concatenate(X), np.concatenate(Y).astype(np.float32)


def train_model(infos, search_train, steps=20000, seed=0):
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    X, Y = build_rows(infos, search_train, rng)
    X, Y = torch.from_numpy(X), torch.from_numpy(Y)
    mu, sd = Y.mean(0), Y.std(0) + 1e-6
    m = Model()
    opt = torch.optim.Adam(m.parameters(), 1e-3)
    for i in range(steps):
        idx = torch.randint(len(X), (2048,))
        loss = (((m(X[idx]) - (Y[idx] - mu) / sd)) ** 2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    m.mu, m.sd = mu, sd
    with torch.no_grad():
        idx = torch.randint(len(X), (20000,))
        err = (m(X[idx]) * sd + mu - Y[idx]).abs().mean(0)
    return m, {"mae_log2bits": float(err[0]), "mae_psnr": float(err[1]), "rows": len(X)}


class MPC:
    def __init__(self, spec):
        self.m = torch.load(spec["path"], weights_only=False)
        self.m.eval()
        self.samples, self.iters, self.pen = spec.get("samples", 96), spec.get("iters", 4), spec.get("penalty", 2.0)
        # plan against margin * budget: the model's ~15 % bit error plus CEM picking plans it underestimates (D20)
        self.margin = spec.get("margin", 1.0)
        self.rng = np.random.default_rng(0)

    def _predict(self, T, q, level, fp):
        with torch.no_grad():
            out = self.m(torch.from_numpy(frame_inputs(T, q, level))) * self.m.sd + self.m.mu
        out = out.numpy()
        return fp * 2 ** out[..., 0], out[..., 1]

    def __call__(self, env, obs):
        t = env.t
        T = env.T
        fp = np.maximum(np.asarray(env.info["fp_bits"], float), 8)
        v = E.visible_len(t, env.mode, env.k_ep, env.cut)
        level = float(env.b != C.BUDGET_QPS[0])
        # features of invisible frames: mean of visible P frames (or the current frame at t = 0 with k = 0)
        Tf, fpf = T.copy(), fp.copy()
        vis = np.arange(t, t + v + 1)
        pv = vis[vis > 0] if (vis > 0).any() else vis
        for j in range(t + v + 1, C.GOP):
            Tf[j] = T[pv].mean(0)
            Tf[j, 5:8] = 0
            Tf[j, 9] = STATIC_OFF[j] / 6
            fpf[j] = fp[pv].mean() if t > 0 or v > 0 else fp[0] / 4
        past_q = np.array(env.qps, float)
        # calibration on the frames already encoded
        corr = 1.0
        if t > 0:
            pb, _ = self._predict(Tf[:t], past_q[None], level, fpf[:t])
            corr = float(np.median(np.asarray(env.bits) / pb[0]))
        nvar = v + 1 + (1 if t + v + 1 < C.GOP else 0)
        mu, sd = np.zeros(nvar), np.full(nvar, 1.5)
        A0, A1 = C.ACTIONS[0], C.ACTIONS[-1]
        best = None
        for it in range(self.iters):
            S = np.clip(np.round(self.rng.normal(mu, sd, (self.samples, nvar))), A0, A1)
            S[0] = np.clip(np.round(mu), A0, A1)
            offs = np.zeros((self.samples, C.GOP - t))
            offs[:, :v + 1] = S[:, :v + 1]
            if nvar > v + 1:
                offs[:, v + 1:] = S[:, -1:]
            q = env.b + STATIC_OFF[t:] + offs
            qfull = np.concatenate([np.broadcast_to(past_q, (self.samples, t)), q], 1)
            bits, psnr = self._predict(Tf, qfull, level, fpf)
            tot = np.asarray(env.bits).sum() + corr * bits[:, t:].sum(1)
            over = np.maximum(0, tot / (self.margin * env.budget) - 1) * 100
            obj = psnr.mean(1) * 10 - self.pen * over          # ~10 % bits per 1 dB at these rates (BD-rate slope)
            elite = S[np.argsort(-obj)[:max(4, self.samples // 8)]]
            mu, sd = elite.mean(0), elite.std(0) + 0.3
            if best is None or obj.max() > best[0]:
                best = (obj.max(), S[np.argmax(obj)])
        return int(best[1][0]) - A0
