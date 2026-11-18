"""test2 clip selection (exp_next/test2/PLAN.md section 3). Deterministic; no randomness, no results used.

Source: YouTube UGC only, the same catalogue, filters and helpers as scripts/select_clips.py (imported, not copied):
  - categories: the 12 v1 uses (HDR, VR, VerticalVideo left out); 16:9 only; 360P/480P (720P only if a category's
    pool is thin, as in v1); frame-rate rule (native 23.976-30 fps or integer decimation of 50/60 fps)
  - NOT eligible: any clip in data/clip_candidates.csv (all v1 candidates, priority 1 and 2), any uploader of a v1
    candidate, config/exclude_clips.csv, and any clip giving fewer than 300 output frames (10 GOPs)
  - per category: PER_CAT_STRAT clips spread evenly over temporal complexity (select_clips.quantile_pick) +
    PER_CAT_CUT clips with the highest chunk-complexity variation (likely natural cuts); one clip per uploader
  - split = test2 for every new clip
Parity clips (PLAN.md section 5): three v1 TEST clips are appended unchanged from data/clip_candidates.csv with
split = parity; they are re-run through the test2 path and must reproduce the stored v1 rows; never analysed.

Frame rates come from ffprobe over HTTP for clips not in a probe cache (v1's data/meta/ugc_probe.tsv is read, never
written; new probes go to data/t2/meta/ugc_probe.tsv), so ffmpeg must be loaded:
  module purge; module load ver/2506 gcc/14.3.0 ffmpeg/7.1.1
  /scratch1/aayushso/envs/ee599/bin/python -I exp_next/test2/select_t2.py            (dry run: prints the list)
  /scratch1/aayushso/envs/ee599/bin/python -I exp_next/test2/select_t2.py --write    (writes the files below)
Out: data/t2/clip_candidates.csv (download_clips.py / decode_clips.py --candidates), data/t2/selection.md
Refuses to overwrite an existing clip_candidates.csv that differs.
"""
import argparse
import csv
import importlib.util
import io
import os
import sys
from collections import Counter, defaultdict

ROOT = "/scratch1/aayushso/ee599"
T2 = f"{ROOT}/data/t2"
PER_CAT_STRAT, PER_CAT_CUT = 6, 2
N_FRAMES = 300
PARITY = ("ed_s05", "NewsClip_360P-1b1c", "park_joy")   # film with cuts; UGC with cuts; Xiph 50 fps decimated

spec = importlib.util.spec_from_file_location("select_clips", f"{ROOT}/scripts/select_clips.py")
SC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SC)


class Probe(SC.UgcProbe):
    """UgcProbe with v1's cache read-only and new probes written to the test2 cache."""

    def __init__(self):
        os.makedirs(f"{T2}/meta", exist_ok=True)
        super().__init__(f"{T2}/meta/ugc_probe.tsv")
        v1 = os.path.join(SC.META, "ugc_probe.tsv")
        for line in open(v1):
            name, fps, dur = line.rstrip("\n").split("\t")
            self.cache.setdefault(name, (float(fps), float(dur)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    v1 = list(csv.DictReader(open(SC.OUT)))
    v1_clips = {r["clip_id"] for r in v1} | {r["source_id"] for r in v1}
    v1_up = {r["group"][4:] for r in v1 if r["source"] == "youtube-ugc"}
    excluded = {r["clip_id"] for r in csv.DictReader(open(SC.EXCLUDE))} if os.path.exists(SC.EXCLUDE) else set()
    probe = Probe()

    def frames_out(c):
        fps, dur = probe(c)
        dec = max(1, int(round(fps / 30)))
        return int(round(dur * fps)) // dec

    def eligible(c):
        return (c["name"] not in v1_clips and c["author"] not in v1_up and c["name"] not in excluded
                and SC.fps_status(probe(c)[0]) != "reject" and frames_out(c) >= N_FRAMES)

    by_cat = defaultdict(list)
    for c in SC.load_ugc():
        by_cat[c["cat"]].append(c)
    used = set(v1_up)              # quantile_pick skips these uploaders and adds its picks
    picks = []
    for cat in SC.UGC_CATEGORIES:
        pool = [c for c in by_cat[cat] if c["res"] != "720P"]
        if sum(1 for c in pool if c["name"] not in v1_clips and c["author"] not in v1_up) < 2 * (PER_CAT_STRAT + PER_CAT_CUT):
            pool = by_cat[cat]
        strat = SC.quantile_pick(pool, PER_CAT_STRAT, used, eligible)
        cut = []
        for c in sorted(pool, key=lambda c: (-c["cv"], c["name"])):    # highest chunk variation, any resolution
            if len(cut) == PER_CAT_CUT:
                break
            if c not in strat and c["author"] not in used and eligible(c):
                cut.append(c)
                used.add(c["author"])
        picks += [(c, "complexity-stratified") for c in strat] + [(c, "likely cuts (highest chunk variation)") for c in cut]
        if len(strat) + len(cut) < PER_CAT_STRAT + PER_CAT_CUT:
            print(f"WARNING {cat}: only {len(strat) + len(cut)} eligible picks", file=sys.stderr)

    rows = []
    for c, why in picks:
        fps, dur = probe(c)
        src = dict(source_id=c["name"], source="youtube-ugc", group="ugc:" + c["author"], priority="1",
                   split="test2", cuts="likely" if why.startswith("likely") else "unknown", url=c["url"],
                   licence=c["licence"] + " (attribute uploader; see data/meta/ugc_ATTRIBUTION.txt)",
                   src_res="%dx%d" % (c["w"], c["h"]), fps="%.3f" % fps, src_frames=str(int(round(dur * fps))),
                   start="", max_frames=str(N_FRAMES), segments="1",
                   notes="%s; %s; SC=%.2f TC=%.2f CV=%.1f; %.2f GB" % (why, c["cat"], c["sc"], c["tc"], c["cv"],
                                                                       c["size"] / 1e9))
        (r,) = SC.expand(src, 30)
        assert r["n_frames"] == N_FRAMES and r["fps_status"] != "reject", r
        r["_size"] = c["size"]
        rows.append(r)
    par = {r["clip_id"]: r for r in v1 if r["clip_id"] in PARITY}
    assert set(par) == set(PARITY), set(PARITY) - set(par)
    rows += [dict(par[p], split="parity", _size=0) for p in PARITY]

    # checks
    new = [r for r in rows if r["split"] == "test2"]
    assert len({r["clip_id"] for r in rows}) == len(rows)
    assert len({r["group"] for r in new}) == len(new), "one clip per uploader"
    assert not ({r["clip_id"] for r in new} & v1_clips) and not ({r["group"][4:] for r in new} & v1_up)

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=SC.FIELDS)
    w.writeheader()
    w.writerows({k: r[k] for k in SC.FIELDS} for r in rows)

    cats = Counter(r["notes"].split("; ")[1] for r in new)
    res = Counter(r["src_res"] for r in new)
    gb = sum(r["_size"] for r in new) / 1e9
    L = ["# test2 clip selection (exp_next/test2/select_t2.py)", "",
         f"{len(new)} new clips (split test2), {sum(r['est_gops'] for r in new)} GOPs, {len(new)} uploaders "
         f"(none in v1); download {gb:.1f} GB; + {len(PARITY)} parity clips from v1 test ({', '.join(PARITY)}; "
         "raw files already in data/raw).", "",
         "| category | clips | of which likely-cut picks |", "|---|---|---|"]
    for cat in SC.UGC_CATEGORIES:
        lk = sum(1 for r in new if r["notes"].split("; ")[1] == cat and r["cuts"] == "likely")
        L.append(f"| {cat} | {cats[cat]} | {lk} |")
    L += ["", "Source sizes: " + ", ".join(f"{k} x{v}" for k, v in sorted(res.items())),
          "Frame rates: " + ", ".join(f"{k} x{v}" for k, v in sorted(Counter(
              f"{r['src_fps']}{'/' + str(r['decimate']) if int(r['decimate']) > 1 else ''}" for r in new).items())), "",
          "| clip | category | uploader | src | fps | why | TC | CV | GB |", "|---|---|---|---|---|---|---|---|---|"]
    for r in new:
        n = r["notes"].split("; ")
        tc, cv = n[2].split()[1][3:], n[2].split()[2][3:]
        L.append(f"| {r['clip_id']} | {n[1]} | {r['group'][4:]} | {r['src_res']} | {r['src_fps']} | "
                 f"{'cut' if r['cuts'] == 'likely' else 'strat'} | {tc} | {cv} | {r['_size'] / 1e9:.2f} |")
    text = "\n".join(L) + "\n"
    print(text)
    if a.write:
        out = f"{T2}/clip_candidates.csv"
        if os.path.exists(out) and open(out).read() != buf.getvalue():
            sys.exit(f"{out} exists and differs; move it away first")
        open(out, "w").write(buf.getvalue())
        open(f"{T2}/selection.md", "w").write(text)
        print("wrote", out, f"{T2}/selection.md")


if __name__ == "__main__":
    main()
