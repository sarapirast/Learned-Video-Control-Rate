"""D41: hindsight oracle for the live-channel task (D38/D39, rclib/bufenv.py). No encodes, CPU only.

For every evaluation case the oracle knows everything a real controller cannot: every GOP's constant-QP curve and the
whole future channel. It picks one constant QP per GOP to maximise the exact D38 score (luma dPSNR_B - 0.17 dB per 1 %
over - LAM_STALL dB per 1 % stalled). It is an upper bound on what any causal controller could score, used to say how
much of the gap between the vbv2 rule and the best possible plan RL closes.

Search (per case; not provably optimal, but never below any method it is seeded with):
  1. Lagrangian DP over the sender-buffer level (G bins of [0, CAP]): minimise sum MSE + lam x bits + mu x stall for a
     grid of (lam, mu); each DP policy is replayed exactly from F = 0 and scored with the exact score.
  2. Seeds: every constant QP and the QP sequences that vbv2, mpc and ppo_v2 (3 seeds) actually used on this case.
  3. Exact local search from the best few: single-GOP +-1 / +-2 moves and paired (+1 on one GOP, -1 on another) moves
     until no move improves the score.
Check: the exact scorer reproduces the stored score of every seeded method (else the run stops).

  RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 [RC_BUF_CHANNEL=trace] RC_V1=1 \
      python experiments/buffer_oracle.py --split test --shard 0 --nshards 4 [--limit 20] | --report
"""
import argparse
import glob
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import buffer_rl as BR, stream_rl as S  # noqa: E402
from rclib import bufenv as BE, clipenv as CE, config as C, metrics  # noqa: E402

G = 129                                  # buffer bins
LAMS = np.geomspace(1e-3, 30, 36)        # x n x mean MSE / B
MUS = np.concatenate([np.geomspace(0.3, 300, 7), [1e5]])   # x mean MSE (11.5 x mean MSE ~ the score's own price)
N_LOCAL = 4                              # local search from the best N_LOCAL starts
OUTO = os.path.join(BR.OUT, "oracle")
REPORTS = os.path.join(BR.REPORTS, "oracle")
METHODS = ("vbv2", "mpc", "ppo_v2")
log = S.log


def seeds_rows():
    """{method: [rows per seed]} for each split, from the stored D39 results."""
    b2 = pickle.load(open(os.path.join(BR.OUT, "baselines2.pkl"), "rb"))
    out = {m: {sp: [b2["rows"][(m, 2, sp)]] for sp in ("val", "test", "test16")} for m in ("vbv2", "mpc")}
    for p in sorted(glob.glob(os.path.join(BR.OUT, "*_L2_s*", "eval.pkl"))):    # ppo_v2 and any D42 learner
        r = pickle.load(open(p, "rb"))
        for sp, rows in r["res"].items():
            out.setdefault(r["args"]["method"], {}).setdefault(sp, []).append(rows)
    out.pop("ppo", None)     # D38 learner on the old vbv base, superseded
    return out


def key(r):
    return (tuple(r["stream"]), r["q0"], r["s"])


class Case:
    def __init__(self, env):
        tabs = env.tabs
        self.q = np.arange(C.QP_MIN, C.QP_MAX + 1)
        self.n = len(tabs)
        self.Bt = np.array([t["bits"][self.q] for t in tabs], float)
        self.Pt = np.array([t["psnr"][self.q] for t in tabs], float)
        bad = ~np.isfinite(self.Bt) | ~np.isfinite(self.Pt)
        self.Bt[bad], self.Pt[bad] = 1e30, -100.0
        self.Mt = 10 ** (-self.Pt / 10)
        self.R = np.asarray(env.m, float) * env.mean_r
        self.cap, self.B = float(env.cap), float(env.B)
        self.curve = CE.stream_curve(tabs)
        self.r = np.arange(self.n)

    def score(self, idx):
        b = self.Bt[self.r, idx]
        F, st = 0.0, 0.0
        for i in range(self.n):
            F += b[i]
            F -= min(F, self.R[i])
            if F > self.cap:
                st += (F - self.cap) / self.R[i]
                F = self.cap
        sp = 100 * st / self.n
        psnr = float(CE.pooled(self.Pt[self.r, idx]))
        d = float(metrics.dpsnr_budget(psnr, self.curve, self.B))
        over = float(metrics.overshoot(float(b.sum()), self.B))
        return d - metrics.OVER_PENALTY_DB * over - BE.LAM_STALL * sp, sp

    def dp_plans(self):
        """One plan per (lam, mu): backward DP on the binned buffer level, then an exact forward replay from F = 0."""
        return np.unique(self.rollout(self.dp_policy(), 0, 0.0)[0], axis=0)

    def rollout(self, pol, i, F0):
        """Replay every DP policy exactly from GOP i with buffer F0: (plans (K, n - i), stall seconds (K,))."""
        n, cap = self.n, self.cap
        K = pol.shape[1]
        plans = np.empty((K, n - i), int)
        F, st = np.full(K, float(F0)), np.zeros(K)
        for j in range(i, n):
            g = np.rint(np.minimum(F, cap) / cap * (G - 1)).astype(int)
            a = pol[j][np.arange(K), g].astype(int)
            plans[:, j - i] = a
            F = np.maximum(F + self.Bt[j][a] - self.R[j], 0)
            st += np.maximum(F - cap, 0) / self.R[j]
            F = np.minimum(F, cap)
        return plans, st

    def score_many(self, plans, st):
        """Exact scores of full plans (K, n) given their total stall seconds (K,)."""
        bits = self.Bt[self.r, plans].sum(1)
        psnr = -10 * np.log10(self.Mt[self.r, plans].mean(1))
        return (metrics.dpsnr_budget(psnr, self.curve, self.B) - metrics.OVER_PENALTY_DB * metrics.overshoot(bits, self.B)
                - BE.LAM_STALL * 100 * st / self.n)

    def dp_policy(self):
        """Backward DP on the binned buffer level for every (lam, mu): pol[i][k, g] = QP index."""
        n, cap = self.n, self.cap
        Fg = np.linspace(0, cap, G)
        mm = float(np.median(self.Mt[:, (self.Mt.shape[1] // 3)]))
        lam = (LAMS * n * mm / self.B)[:, None]
        mu = (MUS * mm)[None, :]
        lam, mu = np.broadcast_arrays(lam, mu)
        lam, mu = lam.ravel()[:, None, None], mu.ravel()[:, None, None]      # (K, 1, 1)
        K = lam.shape[0]
        V = np.zeros((K, G))
        pol = np.empty((n, K, G), np.int16)
        for i in range(n - 1, -1, -1):
            Fn = Fg[:, None] + self.Bt[i][None, :]                           # (G, Q)
            Fn = np.maximum(Fn - self.R[i], 0)
            st = np.maximum(Fn - cap, 0) / self.R[i]
            gn = np.rint(np.minimum(Fn, cap) / cap * (G - 1)).astype(int)
            cost = self.Mt[i][None, None, :] + lam * self.Bt[i][None, None, :] + mu * st[None] + V[:, gn]  # (K, G, Q)
            pol[i] = np.argmin(cost, 2)
            V = np.take_along_axis(cost, pol[i][:, :, None].astype(int), 2)[:, :, 0]
        return pol

    def local(self, idx, s):
        idx = idx.copy()
        nq = len(self.q)
        improved = True
        while improved:
            improved = False
            moves = [(g, d) for g in range(self.n) for d in (-1, 1, -2, 2)]
            moves += [((g, h), 0) for g in range(self.n) for h in range(self.n) if g != h]
            for g, d in moves:
                t = idx.copy()
                if d:
                    t[g] += d
                else:
                    t[g[0]] += 1
                    t[g[1]] -= 1
                if t.min() < 0 or t.max() >= nq:
                    continue
                v = self.score(t)[0]
                if v > s + 1e-9:
                    idx, s, improved = t, v, True
        return idx, s


def solve(env, seeded):
    cs = Case(env)
    starts = {}
    for name, qps in seeded.items():
        idx = np.asarray(qps, int) - C.QP_MIN
        starts[name] = (idx, cs.score(idx)[0])
    for j in range(len(cs.q)):
        idx = np.full(cs.n, j)
        starts[f"const{j}"] = (idx, cs.score(idx)[0])
    for j, idx in enumerate(cs.dp_plans()):
        starts[f"dp{j}"] = (idx, cs.score(idx)[0])
    top = sorted(starts.items(), key=lambda kv: -kv[1][1])[:N_LOCAL]
    best_dp = max(v[1] for k, v in starts.items() if k.startswith("dp"))
    res = [cs.local(idx, s) for _, (idx, s) in top]
    idx, s = max(res, key=lambda x: x[1])
    sc, sp = cs.score(idx)
    bits = float(cs.Bt[cs.r, idx].sum())
    return {"score": sc, "stall_pct": sp, "stalled": sp > 0, "use": bits / cs.B,
            "qps": list(map(int, cs.q[idx])), "start": top[0][0], "dp_only": best_dp,
            "seed_scores": {k: v[1] for k, v in starts.items() if not k[:2] in ("dp", "co")}}


def shard(a):
    t0 = time.time()
    bs = BR.baselines()
    tu, c0 = bs["tune"][2], bs["c0"]
    b2 = pickle.load(open(os.path.join(BR.OUT, "baselines2.pkl"), "rb"))
    cases = BR.case_sets()[a.split]
    cases = cases[a.shard::a.nshards]
    if a.limit:
        cases = cases[:a.limit]
    env = BR.make_env(a.split, 2, c0, tu["rp"], "vbv2", n=BR.n_of(a.split), bp=b2["vbv2"])
    sr = seeds_rows()
    look = {m: [{key(r): r for r in rows} for rows in sr[m][a.split]] for m in METHODS}
    rows, worst = [], 0.0
    for c in cases:
        kind, grp, st, q0, s = c
        env.force(st, q0, s)
        env.reset()
        k = (tuple(st), q0, s)
        seeded, stored = {}, {}
        for m in METHODS:
            for j, d in enumerate(look[m]):
                seeded[f"{m}_{j}"], stored[f"{m}_{j}"] = d[k]["qps"], d[k]["score"]
        r = solve(env, seeded)
        for nm, v in stored.items():
            worst = max(worst, abs(r["seed_scores"][nm] - v))
        if worst > 1e-6:
            raise SystemExit(f"exact scorer mismatch {worst:.2e} on {k} ({nm})")
        rows.append({**r, "stream": st, "q0": q0, "s": s, "kind": kind, "group": grp})
    out = OUTO + ("_debug" if a.limit else "")
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, f"{a.split}_{a.shard}of{a.nshards}.pkl")
    pickle.dump(rows, open(p, "wb"))
    gain = np.mean([r["score"] - max(v for nm, v in r["seed_scores"].items()) for r in rows])
    log(f"oracle {a.split} shard {a.shard}/{a.nshards}: {len(rows)} cases, score {np.mean([r['score'] for r in rows]):+.3f}"
        f", stall {np.mean([r['stall_pct'] for r in rows]):.2f}%, +{gain:.3f} over the best seeded method, "
        f"scorer check max diff {worst:.1e}, {(time.time() - t0) / 60:.1f} min -> {p}")


def report(debug=False):
    src = OUTO + ("_debug" if debug else "")
    sr = seeds_rows()
    chan = (f"AR(1) rho {BE.RHO}, sigma {BE.SIGMA}" if BE.CHANNEL == "ar1" else "Belgium 4G/LTE throughput traces")
    lines = [f"# D41 hindsight oracle, live channel ({C.CODEC}{', ' + BR.TAG if BR.TAG else ''})", "",
             f"Channel {chan}, cap {BE.D_CAP} s, {BE.LAM_STALL} dB per 1 % stalled. The oracle knows every GOP's "
             "curve and the whole future channel (offline upper bound, not achievable live). 'gap closed' = "
             "(method - vbv2) / (oracle - vbv2); 95 % cluster bootstrap.", ""]
    for split, title in (("test", "v1 test (n = 8)"), ("test16", "test playlists (n = 16)"), ("val", "v1 val (n = 8)")):
        fs = sorted(glob.glob(os.path.join(src, f"{split}_*of*.pkl")))
        if not fs:
            continue
        orc = {key(r): r for f in fs for r in pickle.load(open(f, "rb"))}
        ks = list(orc)
        grp = np.array([orc[k]["group"] for k in ks])
        O = np.array([orc[k]["score"] for k in ks])
        M = {}
        for m in sr:
            per = [{key(r): r for r in rows} for rows in sr[m].get(split, [])]
            if per:
                M[m] = (np.mean([[d[k]["score"] for k in ks] for d in per], 0),
                        np.mean([[d[k]["stall_pct"] for k in ks] for d in per], 0), len(per))
        V = M["vbv2"][0]
        u, inv = np.unique(grp, return_inverse=True)
        w = np.random.default_rng(0).multinomial(len(u), [1 / len(u)] * len(u), 4000)

        def bmean(x):
            return (w @ np.bincount(inv, x, len(u))) / (w @ np.bincount(inv, minlength=len(u)))
        rows = [{"method": "oracle (hindsight)", "seeds": "-", "score (dB)": O.mean(),
                 "stall %": np.mean([orc[k]["stall_pct"] for k in ks]), "vs vbv2": "", "gap closed": "100%"}]
        go = bmean(O - V)
        for m, (sc, st, ns) in M.items():
            t = S.cboot(sc - V, grp)
            frac = bmean(sc - V) / go
            rows.append({"method": m, "seeds": ns, "score (dB)": sc.mean(), "stall %": st.mean(),
                         "cases > oracle": f"{100 * np.mean(sc > O + 1e-9):.1f}%",
                         "vs vbv2": f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]" if m != "vbv2" else "",
                         "gap closed": (f"{100 * (sc - V).mean() / (O - V).mean():.0f}% "
                                        f"[{100 * np.percentile(frac, 2.5):.0f}, {100 * np.percentile(frac, 97.5):.0f}]")
                         if m != "vbv2" else "0%"})
        t = S.cboot(O - V, grp)
        rows[0]["vs vbv2"] = f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"
        dp = np.mean([orc[k]["dp_only"] for k in ks])
        lines += [f"## {title} ({len(ks)} cases)", "", pd.DataFrame(rows).round(3).to_markdown(index=False), "",
                  f"Search check: best DP plan alone {dp:+.3f}; oracle beats the best seeded method on "
                  f"{100 * np.mean([orc[k]['score'] > max(orc[k]['seed_scores'].values()) + 1e-9 for k in ks]):.0f}% "
                  f"of cases; start of the winning local search: "
                  f"{pd.Series([orc[k]['start'].split('_')[0].rstrip('0123456789') for k in ks]).value_counts().to_dict()}.", ""]
    rep = REPORTS + ("_debug" if debug else "")
    os.makedirs(rep, exist_ok=True)
    open(os.path.join(rep, "oracle_report.md"), "w").write("\n".join(lines))
    print("\n".join(lines))


def main():
    assert C.V1, "set RC_V1=1"
    p = argparse.ArgumentParser()
    p.add_argument("--split", default="test")
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--nshards", type=int, default=1)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--report", action="store_true")
    p.add_argument("--debug", action="store_true", help="report on the --limit outputs")
    a = p.parse_args()
    if a.report:
        report(a.debug)
    else:
        shard(a)


if __name__ == "__main__":
    main()
