"""Day-1 offline architecture test (P2 tracker item 36): flat MLP vs shared per-frame encoder, by BC imitation of the
hindsight search's best plans. No encodes.

Data = what bc@prev trains on (work dir rcwork_v1/<codec>_lfqp: the search's plans re-expressed as offsets around the
causal previous-GOP base, actions -10..+10). The val split's search results keep only the best plan's actions, not
its per-frame bits, so val observations cannot be rebuilt; instead a held-out quarter of the TRAIN clips (seeded,
natural clips only, no spliced ones) is the offline validation set ("hold"), the rest trains. Split by clip. Shortcut vs rl.py: keep the top LOG_TOP plans per GOP x budget (rl.py keeps 24 top + 24 random);
BC trains on the best plans only, so the targets are the same unless more than LOG_TOP plans tie for the best.
Nets (rclib/nets.py): mlp (2 x 256, as every run so far), set_mm, set_attn. Trained per k and on all k pooled ("anyk").
BC recipe = rl.py's (offrl.train_bc: Adam 3e-4, batch 512, best plans only), steps --steps (rl.py: 20000).
Metrics per val transition: |predicted offset - search offset| (QP), accuracy, NLL; aggregated per GOP x budget,
then compared with the per-k mlp, paired, 95% bootstrap over clips; split stable / cut (gops.csv label).

  RC_CODEC=x264 RC_ARM=lfq RC_ACT_RANGE=10 RC_WORK=/scratch1/aayushso/rcwork_v1/x264_lfqp RC_METRIC=dpsnr \
    python -I tools/arch_offline.py [--ks 0,2,5,10,29] [--archs mlp,set_mm,set_attn] [--seeds 0] [--steps 20000]
Out: /scratch1/aayushso/ee599/results_v1/arch/offline_<codec>[_tag].{md,csv}
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, offrl, runner, nets  # noqa: E402

LOG_TOP = 4
OUT = "/scratch1/aayushso/ee599/results_v1/arch"
GOPS_CSV = "/scratch1/aayushso/ee599/data/v1/320x180/gops.csv"
RNG = np.random.default_rng(0)


def build(infos, srch, ids, k):
    """Per-GOP arrays from the logged plans (best plans only are used downstream)."""
    parts, meta = [], []
    for i, g in enumerate(ids):
        if g not in srch:
            continue
        p = offrl.trajectories((infos[g], srch[g], k, "fixed", (), False, 7 * i, {"top": LOG_TOP, "random": 0}, ""))
        if p is None:
            continue
        parts.append(p)
        meta.append(g)
    return parts, meta


def val_tensors(parts, meta):
    O, A, G = [], [], []
    for p, g in zip(parts, meta):
        o, a, best = p[0], p[1], p[4]
        keep = best[:, 0]
        O.append(o[keep].reshape(-1, o.shape[-1]))
        A.append(a[keep].reshape(-1))
        G += [g] * int(keep.sum() * C.GOP)
    return torch.from_numpy(np.concatenate(O)), torch.from_numpy(np.concatenate(A)), np.array(G)


def evaluate(net, O, A):
    net.eval()
    with torch.no_grad():
        logits = torch.cat([net(O[i:i + 8192]) for i in range(0, len(O), 8192)])
    net.train()
    acts = np.asarray(C.ACTIONS, float)
    pred = logits.argmax(1).numpy()
    return {"mae": np.abs(acts[pred] - acts[A.numpy()]), "acc": (pred == A.numpy()).astype(float),
            "nll": F.cross_entropy(logits, A, reduction="none").numpy()}


def boot(d, clips, n=2000):
    d, clips = np.asarray(d, float), np.asarray(clips)
    u = np.unique(clips)
    idx = {c: np.flatnonzero(clips == c) for c in u}
    ms = [d[np.concatenate([idx[c] for c in RNG.choice(u, len(u))])].mean() for _ in range(n)]
    return d.mean(), np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ks", default="0,2,5,10,29")
    ap.add_argument("--archs", default="mlp,set_mm,set_attn")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--no-anyk", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--hold-frac", type=float, default=0.25)
    ap.add_argument("--hold-seed", type=int, default=0)
    a = ap.parse_args()
    torch.set_num_threads(int(os.environ.get("SLURM_CPUS_PER_TASK", 2)))
    assert C.LFQ_LEARN, "needs RC_ARM=lfq and RC_ACT_RANGE (the lfqp learner setup)"
    ks = [int(x) for x in a.ks.split(",")]
    archs, seeds = a.archs.split(","), [int(x) for x in a.seeds.split(",")]
    t0 = time.time()
    st = runner.Stages("infos", False)
    infos = {g: offrl.slim(x) for g, x in st.load("infos_learn").items()}
    srch_st = runner.Stages("search", False)
    all_tr = [g for g, x in infos.items() if x["gop"]["split"] == "train"]
    nat = sorted({infos[g]["gop"]["clip"] for g in all_tr if infos[g]["gop"]["family"] != "splice"})
    hold = set(np.random.default_rng(a.hold_seed).choice(nat, max(1, round(a.hold_frac * len(nat))), replace=False))
    tr_ids = [g for g in all_tr if infos[g]["gop"]["clip"] not in hold]
    va_ids = [g for g in all_tr if infos[g]["gop"]["clip"] in hold]
    print(f"hold-out: {len(hold)} of {len(nat)} natural train clips, {len(va_ids)} GOPs; train {len(tr_ids)} GOPs",
          flush=True)
    s_tr = srch_st.load("search_train")
    s_va = s_tr
    gops = pd.read_csv(GOPS_CSV)
    label = {f"{r.clip_id}@{r.start_frame}": r.label for r in gops.itertuples()}
    data = {}
    for k in ks:
        tp, _ = build(infos, s_tr, tr_ids, k)
        vp, vm = build(infos, s_va, va_ids, k)
        data[k] = (tp, val_tensors(vp, vm))
        print(f"k{k}: train {sum(len(p[0]) for p in tp)} plans, val {len(data[k][1][1])} transitions "
              f"({time.time() - t0:.0f}s)", flush=True)
    obs_dim, n_out = data[ks[0]][1][0].shape[1], len(C.ACTIONS)
    rows = []

    def run(arch, train_ks, seed, label_train):
        ds = offrl.Dataset([p for k in train_ks for p in data[k][0]])
        torch.manual_seed(seed)
        net = nets.make(arch, obs_dim, n_out)
        nparam = sum(p.numel() for p in net.parameters())
        t1 = time.time()
        net = offrl.train_bc(ds, a.steps, seed=seed, net=net)
        for k in ks if label_train == "anyk" else train_ks:
            O, A, G = data[k][1]
            m = evaluate(net, O, A)
            df = pd.DataFrame({"gid": G, **m}).groupby("gid").mean().reset_index()
            rows.append(df.assign(arch=arch, train=label_train, k=k, seed=seed, params=nparam))
        print(f"{arch} {label_train} s{seed}: {nparam} params, {time.time() - t1:.0f}s", flush=True)

    for seed in seeds:
        for arch in archs:
            for k in ks:
                run(arch, [k], seed, "per-k")
            if not a.no_anyk:
                run(arch, ks, seed, "anyk")
    R = pd.concat(rows, ignore_index=True)
    R["clip"] = R.gid.str.split("@").str[0]
    R["cls"] = R.gid.map(label)
    os.makedirs(OUT, exist_ok=True)
    name = f"{OUT}/offline_{C.CODEC}{'_' + a.tag if a.tag else ''}"
    R.to_csv(name + ".csv", index=False)

    # seeds averaged per GOP, then paired vs the per-k mlp
    M = R.groupby(["arch", "train", "k", "gid", "clip", "cls"], as_index=False)[["mae", "acc", "nll"]].mean()
    ref = M[(M.arch == "mlp") & (M.train == "per-k")].set_index(["k", "gid"])
    L = [f"# Day-1 offline architecture test, {C.CODEC} (tracker 36; repo-pavneet tools/arch_offline.py)", "",
         f"BC imitation of the search's best HELD-OUT plans (a quarter of the natural train clips, seed "
         f"{a.hold_seed}; the val split's search results lack per-frame bits) (lfqp data: offsets -10..+10 around the previous-GOP base). "
         f"Steps {a.steps}, seeds {a.seeds}, top {LOG_TOP} plans per GOP x budget. MAE = |offset - search offset| (QP), "
         "per GOP then averaged; diff = arch - mlp(per-k), paired by GOP, 95% bootstrap over clips (negative MAE diff "
         "= better). Gate 1: a set_* net beats mlp per-k on pooled MAE (CI < 0) on both encoders, not worse on cut GOPs.",
         ""]
    tab = []
    for (arch, tr), x in M.groupby(["arch", "train"], sort=False):
        r = {"arch": arch, "train": tr, "params": int(R[(R.arch == arch) & (R.train == tr)].params.iloc[0])}
        for k in ks:
            r[f"MAE k{k}"] = x[x.k == k].mae.mean()
        r["MAE pooled"] = x.mae.mean()
        r["acc pooled"] = x.acc.mean()
        r["NLL pooled"] = x.nll.mean()
        if not (arch == "mlp" and tr == "per-k"):
            b = ref.reindex(list(zip(x.k, x.gid)))
            r["MAE diff pooled"] = "{:+.3f} [{:+.3f}, {:+.3f}]".format(*boot(x.mae.to_numpy() - b.mae.to_numpy(),
                                                                              x["clip"]))
            for c in ("stable", "cut"):
                s = (x.cls == c).to_numpy()
                r[f"MAE diff {c}"] = "{:+.3f} [{:+.3f}, {:+.3f}]".format(
                    *boot(x.mae.to_numpy()[s] - b.mae.to_numpy()[s], x["clip"].to_numpy()[s]))
        tab.append(r)
    L += ["## Val imitation", "", pd.DataFrame(tab).round(3).to_markdown(index=False), ""]
    open(name + ".md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
