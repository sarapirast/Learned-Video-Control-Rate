"""test2 cut-label review, same protocol as v1 (docs/clip-selection.md "Cut labels"; Aayush 11-17: option 1).

Round 1 (two independent reviewers): every frame of a NEW test2 clip that the rule calls a cut although only one
detector fired (final_cut = 1, hist_cut != scdet_cut). Claude reviews from strips with scores; Aayush reviews BLIND:
random case order, no detector scores, no Claude verdicts (prev | current | next frame, as v1 blind99).
Round 2 (Claude only, as v1): every frame the rule REJECTED where one detector fired (missed cuts, fades), from 5-frame
strips, plus 16 random frames where both detectors fire (precision spot check).
Parity clips are not reviewed (their v1 verdicts in config/cut_review_v1.csv apply).
Verdicts: cut | no_cut | gradual | unsure (unsure counts as no cut; gradual adds a 3-frame gradual span).

  python -I exp_next/test2/cut_review.py --make        (after cut_labels.py --label; needs ffmpeg)
     -> data/t2/320x180/cuts/review/round1/{caseNNN.png, review.csv}      for Aayush (blind)
        data/t2/320x180/cuts/review/round1_claude/{<clip>_f<frame>.png, claude.csv}   strips + scores (Claude)
        data/t2/320x180/cuts/review/round2_claude/{<clip>_f<frame>.png, claude.csv}
  python -I exp_next/test2/cut_review.py --merge       (after both reviews + settle.csv if any disagreements)
     -> config/cut_review_t2.csv (v1 columns); then rerun cut_labels.py --label with P2_DATA=data/t2/320x180
"""
import argparse
import csv
import os
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = "/scratch1/aayushso/ee599"
T2 = os.environ.get("P2_DATA") or f"{ROOT}/data/t2/320x180"
RV = f"{T2}/cuts/review"
OUTCSV = f"{ROOT}/config/cut_review_t2.csv"
VERDICTS = {"cut", "no_cut", "gradual", "unsure"}


def strip(clip, frame, n_before, n_after, dst, w=480, h=270):
    a, b = max(0, frame - n_before), frame + n_after
    n = b - a + 1
    subprocess.check_call(
        ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", f"{T2}/clips/{clip}.y4m",
         "-vf", f"select=between(n\\,{a}\\,{b}),scale={w}:{h}:flags=lanczos,tile={n}x1:padding=6:color=white",
         "-frames:v", "1", dst])


def make():
    d = pd.read_csv(f"{T2}/cuts/disagreements.csv")
    cf = pd.read_csv(f"{T2}/cuts/cut_frames.csv")
    d, cf = d[d.split == "test2"], cf[cf.split == "test2"]
    r1 = d[(d.final_cut == 1) & (d.hist_cut != d.scdet_cut)].sort_values(["clip_id", "frame"]).reset_index(drop=True)
    r2 = d[d.final_cut == 0].sort_values(["clip_id", "frame"]).reset_index(drop=True)
    both = cf[(cf.hist_cut == 1) & (cf.scdet_cut == 1)]
    both = both.sample(min(16, len(both)), random_state=599).sort_values(["clip_id", "frame"])
    for sub in ("round1", "round1_claude", "round2_claude"):
        if os.path.exists(f"{RV}/{sub}"):
            sys.exit(f"{RV}/{sub} exists; move it away first")
        os.makedirs(f"{RV}/{sub}")
    # round 1, blind copy for Aayush: random order, no scores
    order = np.random.default_rng(599).permutation(len(r1))
    rows = []
    for i, j in enumerate(order, 1):
        r = r1.iloc[j]
        f = f"case{i:03d}.png"
        strip(r.clip_id, int(r.frame), 1, 1, f"{RV}/round1/{f}")
        rows.append({"case": i, "file": f, "clip_id": r.clip_id, "frame": int(r.frame), "your_verdict": "",
                     "comment": ""})
    pd.DataFrame(rows).to_csv(f"{RV}/round1/review.csv", index=False)
    # Claude's copies, with scores
    for sub, df, nb, na, kind in (("round1_claude", r1, 1, 1, "single-detector accepted"),
                                  ("round2_claude", r2, 2, 2, "rejected"),
                                  ("round2_claude", both, 2, 2, "both detectors")):
        out = []
        for r in df.itertuples():
            f = f"{r.clip_id}_f{int(r.frame):03d}.png"
            strip(r.clip_id, int(r.frame), nb, na, f"{RV}/{sub}/{f}")
            out.append({"clip_id": r.clip_id, "frame": int(r.frame), "kind": kind, "hist_delta": r.hist_delta,
                        "scdet_score": r.scdet_score, "hist_cut": r.hist_cut, "scdet_cut": r.scdet_cut,
                        "final_cut": r.final_cut, "file": f, "claude_verdict": "", "note": ""})
        p = f"{RV}/{sub}/claude.csv"
        pd.DataFrame(out).to_csv(p, mode="a", header=not os.path.exists(p), index=False)
    print(f"round 1: {len(r1)} frames (blind sheets for Aayush in {RV}/round1); round 2 (Claude): {len(r2)} rejected "
          f"+ {len(both)} both-detector frames")


def merge():
    c1 = pd.read_csv(f"{RV}/round1_claude/claude.csv")
    h1 = pd.read_csv(f"{RV}/round1/review.csv")
    c2 = pd.read_csv(f"{RV}/round2_claude/claude.csv")
    for name, s in (("claude round 1", c1.claude_verdict), ("Aayush round 1", h1.your_verdict),
                    ("claude round 2", c2.claude_verdict)):
        bad = set(s.fillna("")) - VERDICTS
        assert not bad, f"{name}: missing or unknown verdicts {bad}"
    m = c1.merge(h1[["clip_id", "frame", "your_verdict", "comment"]], on=["clip_id", "frame"])
    assert len(m) == len(c1) == len(h1)
    st = {}
    if os.path.exists(f"{RV}/settle.csv"):
        st = {(r.clip_id, int(r.frame)): (r.verdict, r.note) for r in pd.read_csv(f"{RV}/settle.csv").itertuples()}
    cut = lambda v: v == "cut"
    rows, open_ = [], []
    for r in m.itertuples():
        if r.claude_verdict == r.your_verdict:
            v, res, note = r.claude_verdict, "agreed (Claude and Aayush blind)", r.note
        elif (r.clip_id, int(r.frame)) in st:
            v, note = st[(r.clip_id, int(r.frame))]
            res = f"settled (Claude {r.claude_verdict} / human {r.your_verdict})"
        else:
            open_.append((r.clip_id, int(r.frame), r.claude_verdict, r.your_verdict))
            continue
        rows.append({"clip_id": r.clip_id, "frame": int(r.frame), "verdict": v, "claude_verdict": r.claude_verdict,
                     "human_verdict": r.your_verdict, "resolution": res, "note": note if isinstance(note, str) else "",
                     "hist_delta": r.hist_delta, "scdet_score": r.scdet_score})
    if open_:
        pd.DataFrame(open_, columns=["clip_id", "frame", "claude_verdict", "human_verdict"]).to_csv(
            f"{RV}/to_settle.csv", index=False)
        sys.exit(f"{len(open_)} disagreements to settle -> {RV}/to_settle.csv (write settle.csv: clip_id,frame,verdict,note)")
    for r in c2.itertuples():
        rows.append({"clip_id": r.clip_id, "frame": int(r.frame), "verdict": r.claude_verdict,
                     "claude_verdict": r.claude_verdict, "human_verdict": "", "resolution": f"claude only ({r.kind})",
                     "note": r.note if isinstance(r.note, str) else "", "hist_delta": r.hist_delta,
                     "scdet_score": r.scdet_score})
    out = pd.DataFrame(rows)
    assert not out.duplicated(["clip_id", "frame"]).any()
    a = (m.claude_verdict == m.your_verdict).mean()
    b = (m.claude_verdict.map(cut) == m.your_verdict.map(cut)).mean()
    out.to_csv(OUTCSV, index=False)
    print(f"-> {OUTCSV}: {len(out)} verdicts {out.verdict.value_counts().to_dict()}; round 1 agreement {a:.0%} exact, "
          f"{b:.0%} on cut vs not-cut")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--make", action="store_true")
    g.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    make() if a.make else merge()
