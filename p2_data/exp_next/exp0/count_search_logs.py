"""Exp 0 item 1: what the lfq search logs hold, and encode counts per (GOP, level), per encoder and split.
  python -I exp_next/exp0/count_search_logs.py
"""
import glob
import pickle

import numpy as np
import pandas as pd

RC = "/scratch1/aayushso/rcwork_v1"
flat = pd.read_csv("/scratch1/aayushso/ee599/data/v1/320x180/rd/flat_gops.csv")
flat = set(flat.loc[flat.flat, "gid"])
for enc in ("x264", "x265"):
    for split in ("train", "val", "test"):
        d = pickle.load(open(f"{RC}/{enc}_lfq/results_search/search_{split}.pkl", "rb"))
        n_g = len(d)
        n_flat = sum(g in flat for g in d)
        per, has_log, perframe = [], 0, 0
        for g, lv in d.items():
            if g in flat:
                continue
            for b, e in lv.items():
                if "logs" in e:
                    has_log += 1
                    n = sum(len(x) for x in e["logs"])
                    per.append(n)
                    L = e["logs"][0][0]
                    perframe += int(np.shape(L.get("bits", ())) == (30,) and np.shape(L.get("fpsnr", ())) == (30,))
                else:
                    per.append(0)
        per = np.array(per)
        print(f"{enc} {split}: GOPs {n_g} (flat {n_flat}); (GOP, level) non-flat {len(per)}; with logs {has_log}; "
              f"per-frame bits+psnr in logs {perframe}; encodes per (GOP, level) min/median/max "
              f"{per.min()}/{int(np.median(per))}/{per.max()}; total logged encodes {per.sum()}")
