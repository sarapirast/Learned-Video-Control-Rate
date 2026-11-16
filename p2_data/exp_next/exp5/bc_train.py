"""Exp 5b: centred BC as a classifier over R2's 13 offsets. Pre-registration: exp_next/exp5/PREREG_BC.md (REVISION 2).

Data: results_v1/next/exp5/data_v2_<enc>_k<k>.npz (build.py --v2): obs with o[2], o[5..8] zeroed (asserted again
here), class target label2 = clip(plan QP - round(q_real + mean[t]), -6, 6), beta 0.1 weights w = exp(delta / 0.1)
clipped at the 99th percentile. Fitting clips only (the fold was excluded in build.py).
Model: offrl.mlp(obs_dim, 13) = Linear-256 ReLU Linear-256 ReLU Linear-13, i.e. R2's actor (SB3 MlpPolicy, pi 256-256
ReLU + action_net), so the weights load into PPO unchanged. Weighted cross-entropy via weight-proportional sampling.
Hold-out: 10% of the fitting clips (fixed split, seed 0), used to pick the checkpoint (lowest weighted CE) and for the
reported numbers. Columns 2, 5..8 of the first layer are set to 0 when saving (inputs always 0 in BC; R3 then starts
with zero weights on o[5..8], PREREG_BC REVISION 1).

  python exp_next/exp5/bc_train.py [--ks 0,5] [--seeds 0,1,2] [--steps 40000]
Out: results_v1/next/exp5/bc/bc_<enc>_k<k>_s<s>.pt ({"state_dict", "obs_dim", "meta"}), bc_train_<enc>.md
"""
import argparse
import os
import sys
import time
import zipfile

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, "/scratch1/aayushso/ee599/repo-pavneet")
from rclib import config as C, offrl  # noqa: E402

ENC = C.CODEC
EXP5 = "/scratch1/aayushso/ee599/results_v1/next/exp5"
OUT = f"{EXP5}/bc"
ZERO_COLS = [2, 5, 6, 7, 8]
NA, GOP = 13, 30


def npz_memmap(path, key):
    """Memory-map one array of an uncompressed .npz (same as shift_fit.npz_memmap; no pandas / sklearn needed)."""
    zf = zipfile.ZipFile(path)
    info = zf.getinfo(key + ".npy")
    assert info.compress_type == zipfile.ZIP_STORED
    with open(path, "rb") as f:
        f.seek(info.header_offset)
        h = f.read(30)
        n, m = int.from_bytes(h[26:28], "little"), int.from_bytes(h[28:30], "little")
        f.seek(info.header_offset + 30 + n + m)
        ver = np.lib.format.read_magic(f)
        rd = np.lib.format.read_array_header_1_0 if ver == (1, 0) else np.lib.format.read_array_header_2_0
        shape, fortran, dtype = rd(f)
        off = f.tell()
    return np.memmap(path, dtype=dtype, mode="r", offset=off, shape=shape, order="F" if fortran else "C")


def weights(delta, beta=0.1):
    w = np.exp(delta / beta)
    return np.minimum(w, np.percentile(w, 99))


def stats(net, X, y, w, mean_t, t):
    """Weighted CE, weighted accuracy, and R^2 of the expected offset for the class target (vs its per-frame mean)."""
    with torch.no_grad():
        out = []
        for i in range(0, len(X), 65536):
            out.append(net(torch.from_numpy(np.asarray(X[i:i + 65536], np.float32))))
        lg = torch.cat(out)
        ce = F.cross_entropy(lg, torch.from_numpy(y + 6).long(), reduction="none").numpy()
        p = torch.softmax(lg, 1).numpy()
    ev = p @ np.arange(-6, 7)
    acc = (p.argmax(1) - 6 == y)
    sse = np.sum(w * (y - ev) ** 2)
    sst = np.sum(w * (y - mean_t[t]) ** 2)
    return {"ce": float(np.average(ce, weights=w)), "acc": float(np.average(acc, weights=w)),
            "r2_centred": float(1 - sse / sst), "argmax0": float(np.average(p.argmax(1) == 6, weights=w))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ks", default="0,5")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--steps", type=int, default=40000)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--every", type=int, default=2000)
    ap.add_argument("--limit-rows", type=int, default=0, help="smoke: first N rows only")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--data", default=EXP5, help="smoke: directory with data_v2 / plans_v2")
    ap.add_argument("--tag", default="", help="report name suffix (e.g. final_s345), so earlier reports are kept")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    torch.set_num_threads(int(os.environ.get("SLURM_CPUS_PER_TASK", 2)))
    L = [f"# Exp 5b BC classifier, {ENC} (exp_next/exp5/bc_train.py)", "",
         f"Target label2 (13 classes), beta 0.1 weights, hold-out 10% of fitting clips, {a.steps} steps x batch "
         f"{a.batch}, lr {a.lr}; checkpoint = lowest hold-out weighted CE (every {a.every}). R^2 = expected offset vs "
         "the per-frame weighted mean of the target (the centred-label R^2; go/no-go threshold 0.10 at k5).", "",
         "| k | seed | best step | hold-out CE | CE of per-frame prior | acc | R^2 centred | P(argmax = 0) | minutes |",
         "|---|---|---|---|---|---|---|---|---|"]
    for k in [int(x) for x in a.ks.split(",")]:
        p = f"{a.data}/data_v2_{ENC}_k{k}.npz"
        z = np.load(p)
        n = a.limit_rows or len(z["label2"])
        y = z["label2"][:n].astype(int)
        t = z["t"][:n].astype(int)
        w = weights(z["delta"][:n].astype(float))
        X = npz_memmap(p, "obs")[:n]
        Xr = np.asarray(X)                                            # float16 in RAM (~2 GB)
        nz = np.count_nonzero(Xr[:, ZERO_COLS], axis=0)
        assert not nz.any(), f"o[2] / o[5..8] not zero in the saved obs: {dict(zip(ZERO_COLS, nz))}"
        import pandas as pd                                           # plans: gid -> clip for the hold-out split
        plans = pd.read_pickle(f"{a.data}/plans_v2_{ENC}.pkl").set_index("pid")
        gid = plans.gid.reindex(z["pid"][:n:GOP]).to_numpy()
        clip = np.array([g.split("@")[0] for g in gid])
        if len(np.unique(clip)) < 10:                                 # smoke data only: split by GOP
            clip = gid
        uc = np.unique(clip)
        hold = set(np.random.default_rng(0).choice(uc, max(1, len(uc) // 10), replace=False))
        hmask = np.repeat(np.array([c in hold for c in clip]), GOP)[:n]
        tr, te = np.flatnonzero(~hmask), np.flatnonzero(hmask)
        mean_t = np.array([np.average(y[tr][t[tr] == j], weights=w[tr][t[tr] == j]) for j in range(GOP)])
        prior = np.array([np.bincount(y[tr][t[tr] == j] + 6, weights=w[tr][t[tr] == j], minlength=NA) for j in range(GOP)])
        prior = (prior + 1e-3) / (prior + 1e-3).sum(1, keepdims=True)
        ce_prior = float(np.average(-np.log(prior[t[te], y[te] + 6]), weights=w[te]))
        Xte, yte, wte, tte = Xr[te], y[te], w[te], t[te]
        cdf = np.cumsum(w[tr])
        cdf /= cdf[-1]
        for s in [int(x) for x in a.seeds.split(",")]:
            t0 = time.time()
            torch.manual_seed(s)
            rng = np.random.default_rng(1000 + s)
            net = offrl.mlp(Xr.shape[1], NA)
            opt = torch.optim.Adam(net.parameters(), a.lr)
            best = (np.inf, 0, None, None)
            for step in range(1, a.steps + 1):
                idx = tr[np.minimum(np.searchsorted(cdf, rng.random(a.batch)), len(tr) - 1)]
                xb = torch.from_numpy(Xr[idx].astype(np.float32))
                yb = torch.from_numpy(y[idx] + 6).long()
                loss = F.cross_entropy(net(xb), yb)
                opt.zero_grad()
                loss.backward()
                opt.step()
                if step % a.every == 0 or step == a.steps:
                    st = stats(net, Xte, yte, wte, mean_t, tte)
                    if st["ce"] < best[0]:
                        best = (st["ce"], step, {kk: v.clone() for kk, v in net.state_dict().items()}, st)
                    print(f"{ENC} k{k} s{s} step {step}: hold-out CE {st['ce']:.4f} acc {st['acc']:.3f} "
                          f"R2c {st['r2_centred']:.3f}", flush=True)
            sd = best[2]
            sd["0.weight"][:, ZERO_COLS] = 0.0                     # inputs always 0 in BC; R3 starts with 0 weights
            dest = f"{a.out}/bc_{ENC}_k{k}_s{s}.pt"
            assert not os.path.exists(dest), f"{dest} exists; never overwrite"
            torch.save({"state_dict": sd, "obs_dim": int(Xr.shape[1]), "zero_cols": ZERO_COLS,
                        "meta": {"enc": ENC, "k": k, "seed": s, "best_step": best[1], "holdout": sorted(hold),
                                 "steps": a.steps, "batch": a.batch, "lr": a.lr, **best[3]}}, dest)
            st = best[3]
            L.append(f"| {k} | {s} | {best[1]} | {st['ce']:.4f} | {ce_prior:.4f} | {st['acc']:.3f} | "
                     f"{st['r2_centred']:.3f} | {st['argmax0']:.3f} | {(time.time() - t0) / 60:.1f} |")
            print(L[-1], flush=True)
    L += ["", "Hold-out clips are fitting clips (train minus the fold); the fold and val were never in the data.", ""]
    rep = f"{a.out}/bc_train_{ENC}{'_' + a.tag if a.tag else ''}.md"
    assert not os.path.exists(rep), f"{rep} exists; never overwrite"
    open(rep, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
