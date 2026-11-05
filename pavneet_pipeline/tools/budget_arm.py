"""Derive the decoupled-budget arm ("dec") from a finished original-arm infos.pkl (data-v1 branch, no encodes).

budget_dec[g][b] = round(budget_orig[g][b] * s), s ~ U(0.8, 1.25) drawn deterministically from sha1(gop id, b), so
both encoders and every rerun get the same factors. The constant QP that meets the budget is then no longer b
(about +-2 QP away) and the budget carries the GOP's cost only up to that factor. STATIC's score/over are recomputed
against the new budget; everything else (curves, first pass, features, cut flags, STATIC encodes) is copied unchanged.

  python tools/budget_arm.py <orig RC_WORK> <dec RC_WORK>
Run after experiments/scenes.py --stage apply in the orig work dir. Links clips/, gops/ and manifest.json.
"""
import hashlib
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import metrics  # noqa: E402

LO, HI = 0.8, 1.25


def factor(gid, b):
    u = int(hashlib.sha1(f"{gid}|{b}".encode()).hexdigest()[:8], 16) / 2 ** 32
    return LO + (HI - LO) * u


def main(src, dst):
    os.makedirs(os.path.join(dst, "results_infos"), exist_ok=True)
    for name in ("clips", "gops", "manifest.json"):
        if not os.path.lexists(os.path.join(dst, name)):
            os.symlink(os.path.join(src, name), os.path.join(dst, name))
    out = os.path.join(dst, "results_infos", "infos.pkl")
    if os.path.exists(out):
        sys.exit(f"{out} exists; delete it to rebuild")
    with open(os.path.join(src, "results_infos", "infos.pkl"), "rb") as f:
        infos = pickle.load(f)
    for gid, x in infos.items():
        x["budget_orig"] = dict(x["budget"])
        x["budget_factor"] = {b: factor(gid, b) for b in x["budget"]}
        x["budget"] = {b: int(round(v * x["budget_factor"][b])) for b, v in x["budget_orig"].items()}
        for b, s in x["static"].items():
            s["score"] = float(metrics.score(s["total_bits"], s["mean_psnr"], x["curve"], x["budget"][b]))
            s["over"] = bool(s["total_bits"] > x["budget"][b])
    with open(out, "wb") as f:
        pickle.dump(infos, f)
    fs = [v for x in infos.values() for v in x["budget_factor"].values()]
    print(f"{out}: {len(infos)} GOPs, factor mean {sum(fs) / len(fs):.3f} min {min(fs):.3f} max {max(fs):.3f}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
