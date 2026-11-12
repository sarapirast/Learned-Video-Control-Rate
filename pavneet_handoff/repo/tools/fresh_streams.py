"""D35: fresh long-stream test set from two films v1 never trains on (Elephants Dream, Tears of Steel; v1 train has
BBB and Sintel). Contiguous segments of SEG_GOPS consecutive 30-frame GOPs from our own 320x180 film clips
(/scratch1/pbanga/rcwork/clips), SEGS per film, evenly spaced between 2 % and 85 % of the film (skips titles and the
end credits). Every segment is its own bootstrap cluster ('group').

  stage manifest : write RC_WORK/manifest.json (+ clips symlink); then experiments/infos.py (RC_V1=1 RC_PRESET=medium
                   RC_BUDGETS=24,30,36,42) makes the curves, first passes and scene analysis
  stage prep     : budgets like v1's budgets.csv (segment mean of the constant-QP bits per GOP at each level) ->
                   results_infos/infos_slim.pkl, the file stream_rl / stream_fresh read

  RC_WORK=/scratch1/pbanga/rcwork_fresh/x265 python tools/fresh_streams.py --stage manifest|prep
"""
import argparse
import json
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import config as C, data  # noqa: E402

FILMS = {"film_elephants_dream_720p24": "ed", "film_tears_of_steel": "tos"}
SRC_CLIPS = "/scratch1/pbanga/rcwork/clips"
SEGS, SEG_GOPS = 6, 32
LEVELS = (24, 30, 36, 42)
SHARED_GOPS = "/scratch1/pbanga/rcwork_fresh/gops"


def manifest():
    os.makedirs(C.WORK, exist_ok=True)
    if not os.path.exists(C.CLIPS):
        os.symlink(SRC_CLIPS, C.CLIPS)
    if not os.path.exists(C.GOPS):     # GOP files are encoder-independent: one copy shared by x265 and x264
        os.makedirs(SHARED_GOPS, exist_ok=True)
        os.symlink(SHARED_GOPS, C.GOPS)
    gops = []
    for clip, short in FILMS.items():
        n = data.y4m_info(os.path.join(SRC_CLIPS, clip + ".y4m"))["frames"] // C.GOP
        lo, hi = int(0.02 * n), int(0.85 * n) - SEG_GOPS
        for j, s0 in enumerate(np.linspace(lo, hi, SEGS).astype(int)):
            for i in range(SEG_GOPS):
                start = int((s0 + i) * C.GOP)
                gops.append({"id": f"{clip}@{start}", "clip": f"{short}_seg{j}", "source": f"film:{short}",
                             "family": "film_fresh", "category": "film", "split": "test", "start": start,
                             "group": f"{short}_seg{j}", "file_clip": clip})
    # data.gop_path reads frames from CLIPS/<clip>.y4m: keep 'clip' = the segment name for streams, and build the GOP
    # files here so gop_path never needs the clip name
    for g in gops:
        p = os.path.join(C.GOPS, g["id"].replace("/", "_") + ".yuv")
        if not os.path.exists(p):
            os.makedirs(C.GOPS, exist_ok=True)
            fr = data.read_frames(os.path.join(SRC_CLIPS, g["file_clip"] + ".y4m"), g["start"], C.GOP)
            tmp = f"{p}.{os.getpid()}.part"
            fr.tofile(tmp)
            os.replace(tmp, p)
    json.dump({"gops": gops}, open(os.path.join(C.WORK, "manifest.json"), "w"))
    print(f"{len(gops)} GOPs in {len(gops) // SEG_GOPS} segments -> {C.WORK}")


def prep():
    d = os.path.join(C.WORK, "results_infos")
    inf = pickle.load(open(os.path.join(d, "infos.pkl"), "rb"))
    seg = {}
    for g, x in inf.items():
        seg.setdefault(x["gop"]["clip"], []).append(np.asarray(x["curve"]["bits"], float))
    mean = {c: np.mean(v, 0) for c, v in seg.items()}
    slim = {}
    for g, x in inf.items():
        m = mean[x["gop"]["clip"]]
        x = dict(x)
        x["budget"] = {q: float(m[C.QPS.index(q)]) for q in LEVELS}
        x["curve"] = {k: v for k, v in x["curve"].items() if k != "frame_bits"}
        x["gop"] = {**x["gop"], "label": "film"}
        slim[g] = x
    pickle.dump(slim, open(os.path.join(d, "infos_slim.pkl"), "wb"))
    r = [x["budget"][30] / x["curve"]["bits"][C.QPS.index(30)] for x in slim.values()]
    print(f"{len(slim)} GOPs; budget / own constant-QP 30 bits: median {np.median(r):.2f}, "
          f"10-90 % {np.percentile(r, 10):.2f}-{np.percentile(r, 90):.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("manifest", "prep"))
    {"manifest": manifest, "prep": prep}[ap.parse_args().stage]()
