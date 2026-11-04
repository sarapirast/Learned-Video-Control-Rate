"""Write Pavneet's pipeline manifest ($RC_WORK/manifest.json) from data v1, and link the v1 clips into $RC_WORK/clips.

Uses the v1 split, all 1042 v1 GOPs (contiguous 30-frame GOPs, not his 8 windows per clip), and v1's reviewed cut
frames as `cuts` on every GOP. v1 spliced clips are train only (family "splice"); there are no val/test splices.
Extra fields kept for our own breakdowns: label (stable/cut/gradual, reviewed), v1_gop, group.

  python scripts/v1_rc_manifest.py /scratch1/aayushso/rcwork_v1/x265
Stdlib only. Refuses to overwrite an existing manifest.json that differs (delete it first to rebuild).
"""
import csv
import json
import os
import sys

V1 = "/scratch1/aayushso/ee599/data/v1/320x180"


def family(m):
    src = m["source"]
    if src == "youtube-ugc":
        return "ugc"
    if src == "spliced":
        return "splice"
    if src == "blender":
        return "film"
    if src.startswith("xiph"):
        return "xiph_cif" if m["src_size"] in ("352x288", "352x240") else "xiph_hd"
    return src.replace(".", "_").replace("-", "_")          # uvg, archive_org


def main(work):
    man = {m["clip_id"]: m for m in csv.DictReader(open(os.path.join(V1, "manifest.csv")))}
    rows = list(csv.DictReader(open(os.path.join(V1, "gops.csv"))))
    clips, gops = [], []
    for cid, m in sorted(man.items()):
        fam = family(m)
        cat = cid.split("_")[0] if fam == "ugc" else ("Splice" if fam == "splice" else fam)
        clips.append({"clip": cid, "family": fam, "source": m["group"], "category": cat,
                      "frames": int(m["n_frames"]), "split": m["split"]})
    fam_of = {c["clip"]: c for c in clips}
    for r in rows:
        c = fam_of[r["clip_id"]]
        assert r["split"] == c["split"] and int(r["n_frames"]) == 30, r
        start = int(r["start_frame"])
        cuts = sorted(int(x) for x in r["cut_frames"].split()) if r["cut_frames"].strip() else []
        assert all(0 < x < 30 for x in cuts), r
        gops.append({"id": f"{r['clip_id']}@{start}", "clip": r["clip_id"], "source": c["source"],
                     "family": c["family"], "category": c["category"], "split": r["split"], "start": start,
                     "cuts": cuts, "label": r["label"], "v1_gop": int(r["gop"]), "group": r["group"]})
    assert not any(g["family"] == "splice" and g["split"] != "train" for g in gops)
    out = {"clips": clips, "gops": gops}
    os.makedirs(os.path.join(work, "clips"), exist_ok=True)
    p = os.path.join(work, "manifest.json")
    txt = json.dumps(out, indent=1)
    if os.path.exists(p) and open(p).read() != txt:
        sys.exit(f"{p} exists and differs; delete it first to rebuild")
    open(p, "w").write(txt)
    for c in clips:
        dst = os.path.join(work, "clips", c["clip"] + ".y4m")
        if not os.path.lexists(dst):
            os.symlink(os.path.join(V1, "clips", c["clip"] + ".y4m"), dst)
    by = {}
    for g in gops:
        k = (g["split"], g["label"])
        by[k] = by.get(k, 0) + 1
    print(f"{p}: {len(clips)} clips, {len(gops)} GOPs;", dict(sorted(by.items())))
    print("families:", {f: sum(g['family'] == f for g in gops) for f in sorted({g['family'] for g in gops})})


if __name__ == "__main__":
    main(sys.argv[1])
