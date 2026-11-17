"""Check that a rebuilt BC dataset equals Aayush's as a set of rows (row order differs: his build used imap_unordered).
Row key = (gid, level, S, t) of the plan + a 64-bit fingerprint of the observation + every label column.
  python -I exp5_compare.py <mine dir> <tag: v1|v2> <k>
"""
import sys

import numpy as np
import pandas as pd

REF = "/scratch1/aayushso/ee599/results_v1/next/exp5"


def keys(d, tag, k):
    t = "_v2" if tag == "v2" else ""
    z = np.load(f"{d}/data{t}_x264_k{k}.npz")
    plans = pd.read_pickle(f"{d}/plans{t}_x264.pkl").set_index("pid")
    p = plans.reindex(z["pid"])
    w = np.random.default_rng(0).integers(1, 2**62, z["obs"].shape[1], dtype=np.uint64)
    obs = z["obs"].view(np.uint16)
    fp = np.concatenate([(obs[i:i + 100_000].astype(np.uint64) * w).sum(1)       # chunked: ~280 MB at a time
                         for i in range(0, len(obs), 100_000)])
    del obs
    cols = {"gid": p.gid.to_numpy(), "level": p.level.to_numpy(), "S": p.S.to_numpy(), "fp": fp}
    for c in z.files:
        if c not in ("obs", "pid"):
            a = z[c]
            if a.ndim == 1:
                cols[c] = a
            else:
                for j in range(a.shape[1]):
                    cols[f"{c}{j}"] = a[:, j]
    df = pd.DataFrame(cols)
    return df.sort_values(list(df.columns)).reset_index(drop=True)


def main():
    d, tag, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
    a, b = keys(d, tag, k), keys(REF, tag, k)
    same = a.shape == b.shape and list(a.columns) == list(b.columns) and a.equals(b)
    print(f"{tag} k{k}: mine {len(a)} rows, stored {len(b)} rows -> {'IDENTICAL as a set of rows' if same else 'DIFFERENT'}")
    if not same and a.shape == b.shape:
        print("differing columns:", [c for c in a.columns if not a[c].equals(b[c])])
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
