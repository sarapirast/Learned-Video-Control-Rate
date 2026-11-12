"""Collect every number the 3-page report uses into report3/data.json (test set, seeds averaged per case)."""
import json, os, sys
import numpy as np
sys.path.insert(0, "/scratch1/pbanga/ee599")
RUNS = {"x265_2": ("x265", "/scratch1/pbanga/rcwork", "30,38"), "x264_2": ("x264", "/scratch1/pbanga/rcwork_x264", "30,38"),
        "x265_5": ("x265", "/scratch1/pbanga/rcwork_wide", "26,30,34,38,42"), "x264_5": ("x264", "/scratch1/pbanga/rcwork_x264_wide", "26,30,34,38,42")}
key = sys.argv[1]
codec, work, bud = RUNS[key]
os.environ.update(RC_CODEC=codec, RC_WORK=work, RC_BUDGETS=bud)
from experiments.breakdown import boot, collect, per_case  # noqa
infos, test, items = collect(work)
D = per_case(infos, items)
out = {"labels": sorted(D)}
for m, df in D.items():
    out[m] = {"all": [float(df.score.mean()), float(df.saving.mean()), float(100 * df.over1.mean())],
              "b": {int(b): [float(g.score.mean()), float(g.saving.mean()), float(100 * g.over1.mean())]
                    for b, g in df.groupby(level="b")}}
def diff(a, b_):
    x, y = D[a].score, D[b_].score.reindex(D[a].index)
    return [float(v) for v in boot((x - y).values)]
pairs = {}
for a, b_ in (("lagr fixed:0", "bc fixed:0"), ("lagr fixed:5", "bc fixed:5"), ("cql_ppo fixed:5", "cql_ppo fixed:0"),
              ("hindsight search", "cql_ppo fixed:5")):
    if a in D and b_ in D:
        pairs[f"{a} - {b_}"] = diff(a, b_)
out["pairs"] = pairs
json.dump(out, open(f"/scratch1/pbanga/ee599/paper/report3/data_{key}.json", "w"), indent=1)
print(key, len(D), "methods")
