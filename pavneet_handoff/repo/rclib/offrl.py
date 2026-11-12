"""Offline learning from the hindsight search's logged plans: datasets, BC, CQL, IQL (all discrete, gamma = 1).

A logged plan (30 actions + the real per-frame bits of its encode) is replayed into the exact observations a policy
would have seen (`env.plan_observations`); its return is the terminal relative reward (score - STATIC score) / 10.
"""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from . import config as C, env as E

NA = len(C.ACTIONS)
LOG_CAP = {"top": 24, "random": 24}      # plans kept per (GOP, budget) from the ~600 logged (D15)


def slim(info):
    """The parts of an infos entry the env needs (keeps subprocess pickles small)."""
    return {"gop": info["gop"], "fp_bits": info["fp_bits"], "an": info["an"], "budget": info["budget"],
            "curve": {"bits": info["curve"]["bits"], "psnr": info["curve"]["psnr"]},
            "static": {b: {k: v for k, v in s.items() if k != "psnr"} for b, s in info["static"].items()},
            **({"qfit": info["qfit"]} if "qfit" in info else {})}


def select_plans(entry, rng, cap=LOG_CAP):
    logs = [e for lg in entry["logs"] for e in lg]
    logs.sort(key=lambda e: -e["score"])
    top = logs[:cap["top"]]
    rest = logs[cap["top"]:]
    if rest and cap["random"]:
        idx = rng.choice(len(rest), min(cap["random"], len(rest)), replace=False)
        top += [rest[i] for i in idx]
    return top


def trajectories(args):
    """Worker: (info, search entry per budget, k, mode, drop, prior, seed) -> arrays for one GOP."""
    info, sr, k, mode, drop, prior, seed, cap, *rest = args
    extra = rest[0] if rest else ""
    rng = np.random.default_rng(seed)
    O, A, R, D, best = [], [], [], [], []
    for b, entry in sr.items():
        plans = select_plans(entry, rng, cap)
        replay = []
        for p in plans:
            obs = E.plan_observations(info, b, p["acts"], p["bits"], k=k, mode=mode, drop=drop, prior=prior,
                                      extra=extra, fpsnr=p.get("fpsnr"))
            if C.CAUSAL:   # D30: the plan's QPs as offsets on the causal base QP; plans that leave -3..3 are dropped
                obs, acts = obs
                if C.V1:      # D31: residual targets outside the action range are clipped to it
                    acts = np.clip(acts, 0, NA - 1)
                elif acts.min() < 0 or acts.max() >= NA:
                    continue
                p = {**p, "acts": acts}
            replay.append((p, obs))
        if not replay:
            continue
        smax = max(p["score"] for p, _ in replay)
        for p, obs in replay:
            r = np.zeros(C.GOP, np.float32)
            r[-1] = (p["score"] - (0.0 if C.V1 else entry["static_score"])) / E.REWARD_SCALE
            d = np.zeros(C.GOP, np.float32)
            d[-1] = 1
            O.append(obs.astype(np.float32))
            A.append(p["acts"].astype(np.int64))
            R.append(r)
            D.append(d)
            best.append(np.full(C.GOP, p["score"] >= smax - 1e-9))
    if not O:
        dim = E.OBS_DIM + E.EXTRA[extra]
        return (np.zeros((0, C.GOP, dim), np.float32), np.zeros((0, C.GOP), np.int64), np.zeros((0, C.GOP), np.float32),
                np.zeros((0, C.GOP), np.float32), np.zeros((0, C.GOP), bool))
    return np.stack(O), np.stack(A), np.stack(R), np.stack(D), np.stack(best)


class Dataset:
    """Transitions flattened over (plan, t); next obs = obs[t+1] within the plan."""

    def __init__(self, parts):
        O = np.concatenate([p[0] for p in parts])        # (P, 30, D)
        A = np.concatenate([p[1] for p in parts])
        R = np.concatenate([p[2] for p in parts])
        Dn = np.concatenate([p[3] for p in parts])
        B = np.concatenate([p[4] for p in parts])
        P = len(O)
        self.obs = torch.from_numpy(O.reshape(P * C.GOP, -1))
        nxt = np.concatenate([O[:, 1:], np.zeros_like(O[:, :1])], 1)
        self.next = torch.from_numpy(nxt.reshape(P * C.GOP, -1))
        self.act = torch.from_numpy(A.reshape(-1))
        self.rew = torch.from_numpy(R.reshape(-1))
        self.done = torch.from_numpy(Dn.reshape(-1))
        self.best = torch.from_numpy(B.reshape(-1))
        # Monte-Carlo return (terminal reward only, gamma 1) for IQL/AWR diagnostics
        self.ret = torch.from_numpy(np.repeat(R[:, -1:], C.GOP, 1).reshape(-1))
        self.n = len(self.act)

    def batch(self, n, gen, best_only=False):
        if best_only:
            idx = torch.nonzero(self.best).squeeze(1)
            i = idx[torch.randint(len(idx), (n,), generator=gen)]
        else:
            i = torch.randint(self.n, (n,), generator=gen)
        return self.obs[i], self.act[i], self.rew[i], self.next[i], self.done[i]


def mlp(i, o, h=(256, 256)):
    layers, d = [], i
    for w in h:
        layers += [nn.Linear(d, w), nn.ReLU()]
        d = w
    layers.append(nn.Linear(d, o))
    return nn.Sequential(*layers)


def train_bc(ds, steps=20000, lr=3e-4, seed=0, best_only=True):
    torch.manual_seed(seed)
    gen = torch.Generator().manual_seed(seed)
    net = mlp(ds.obs.shape[1], NA)
    opt = torch.optim.Adam(net.parameters(), lr)
    for i in range(steps):
        o, a, *_ = ds.batch(512, gen, best_only)
        loss = F.cross_entropy(net(o), a)
        opt.zero_grad()
        loss.backward()
        opt.step()
    return net


def train_cql(ds, steps=50000, lr=3e-4, alpha=1.0, tau=0.005, seed=0):
    """Discrete CQL(H) with a double-Q target; gamma = 1 (finite 30-step episodes)."""
    torch.manual_seed(seed)
    gen = torch.Generator().manual_seed(seed)
    q = mlp(ds.obs.shape[1], NA)
    qt = mlp(ds.obs.shape[1], NA)
    qt.load_state_dict(q.state_dict())
    opt = torch.optim.Adam(q.parameters(), lr)
    for i in range(steps):
        o, a, r, o2, d = ds.batch(1024, gen)
        with torch.no_grad():
            a2 = q(o2).argmax(1, keepdim=True)
            y = r + (1 - d) * qt(o2).gather(1, a2).squeeze(1)
        qa = q(o)
        qsa = qa.gather(1, a[:, None]).squeeze(1)
        loss = F.smooth_l1_loss(qsa, y) + alpha * (torch.logsumexp(qa, 1) - qsa).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        with torch.no_grad():
            for p, pt in zip(q.parameters(), qt.parameters()):
                pt.mul_(1 - tau).add_(tau * p)
    return q


def train_iql(ds, steps=50000, lr=3e-4, expectile=0.8, beta=3.0, tau=0.005, seed=0):
    """Discrete IQL: expectile V, Q by TD on V(s'), policy by advantage-weighted regression."""
    torch.manual_seed(seed)
    gen = torch.Generator().manual_seed(seed)
    D = ds.obs.shape[1]
    q, qt, v, pi = mlp(D, NA), mlp(D, NA), mlp(D, 1), mlp(D, NA)
    qt.load_state_dict(q.state_dict())
    oq, ov, op = (torch.optim.Adam(m.parameters(), lr) for m in (q, v, pi))
    for i in range(steps):
        o, a, r, o2, d = ds.batch(1024, gen)
        with torch.no_grad():
            qsa_t = qt(o).gather(1, a[:, None]).squeeze(1)
        vs = v(o).squeeze(1)
        u = qsa_t - vs
        lv = (torch.abs(expectile - (u < 0).float()) * u ** 2).mean()
        ov.zero_grad()
        lv.backward()
        ov.step()
        with torch.no_grad():
            y = r + (1 - d) * v(o2).squeeze(1)
        lq = F.mse_loss(q(o).gather(1, a[:, None]).squeeze(1), y)
        oq.zero_grad()
        lq.backward()
        oq.step()
        with torch.no_grad():
            w = torch.clamp(torch.exp(beta * (qsa_t - v(o).squeeze(1))), max=100.0)
        lp = (w * F.cross_entropy(pi(o), a, reduction="none")).mean()
        op.zero_grad()
        lp.backward()
        op.step()
        with torch.no_grad():
            for p_, pt in zip(q.parameters(), qt.parameters()):
                pt.mul_(1 - tau).add_(tau * p_)
    return pi, q


def distill_into_ppo(model, ds, teacher, temp=0.3, steps=8000, lr=3e-4, seed=0, value_from_q=True):
    """Initialise an SB3 PPO/A2C actor-critic from an offline teacher network (Q-values or logits).

    Actor: cross-entropy to softmax(teacher/temp). Critic: E_pi[Q] when the teacher is a Q-function.
    """
    torch.manual_seed(seed)
    gen = torch.Generator().manual_seed(seed)
    pol = model.policy
    opt = torch.optim.Adam(pol.parameters(), lr)
    for i in range(steps):
        o, *_ = ds.batch(1024, gen)
        with torch.no_grad():
            tq = teacher(o)
            target = F.softmax(tq / temp, 1)
        feats = pol.extract_features(o)
        lat_pi, lat_vf = pol.mlp_extractor(feats)
        logits = pol.action_net(lat_pi)
        loss = -(target * F.log_softmax(logits, 1)).sum(1).mean()
        if value_from_q:
            vt = (target * tq).sum(1)
            loss = loss + 0.5 * F.mse_loss(pol.value_net(lat_vf).squeeze(1), vt)
        opt.zero_grad()
        loss.backward()
        opt.step()
    return model
