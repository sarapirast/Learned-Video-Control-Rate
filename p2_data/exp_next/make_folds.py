"""Brief Part B item 4: create (once) and freeze the train-select fold -> exp_next/folds.json.
Rule (written before use): 8 TRAIN clips, each from a single-clip source group (so no source group is split between
the fold and the rest of train, like the train/val/test split), excluding spliced clips and clips whose GOPs are
all flat; stratified: 3 clips with at least one natural cut GOP, 5 without. Drawn with numpy default_rng(20261113)
from the sorted candidate lists. Refuses to overwrite an existing folds.json.
  python -I exp_next/make_folds.py
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
OUT = f"{ROOT}/exp_next/folds.json"
assert not os.path.exists(OUT), "folds.json exists: the fold is frozen"
g = pd.read_csv(f"{ROOT}/data/v1/320x180/gops.csv")
fl = pd.read_csv(f"{ROOT}/data/v1/320x180/rd/flat_gops.csv")[["gid", "flat"]]
g["gid"] = g.clip_id + "@" + g.start_frame.astype(str)
g = g.merge(fl, on="gid")
t = g[g.split == "train"]
size = t.groupby("group").clip_id.nunique()
c = t.groupby(["clip_id", "group"]).agg(cut=("label", lambda s: int((s == "cut").sum())),
                                        n=("gop", "size"), flat=("flat", "sum")).reset_index()
c = c[c.group.map(size).eq(1) & ~c.group.str.startswith("spliced") & (c.flat < c.n)]
cut = sorted(c.loc[c.cut > 0, "clip_id"])
nocut = sorted(c.loc[c.cut == 0, "clip_id"])
rng = np.random.default_rng(20261113)
pick = sorted(rng.choice(cut, 3, replace=False).tolist()) + sorted(rng.choice(nocut, 5, replace=False).tolist())
sel = c.set_index("clip_id").loc[pick]
out = {"train_select_clips": pick, "groups": sel.group.tolist(),
       "gops": int(t.clip_id.isin(pick).sum()), "cut_gops": int(sel.cut.sum()),
       "rule": __doc__.strip().splitlines()[1:5], "created": "2026-11-13", "seed": 20261113}
json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=True)
print(json.dumps(out, indent=1, ensure_ascii=True))
