"""Clips, GOP windows, train/val/test splits by source, spliced GOPs, and the raw per-GOP file cache.

A GOP record is a dict: id, clip, source, family, category, split, start (first frame in the clip), and for spliced GOPs
`parts` = [(clip, start, n), ...]. The GOP's pixels live in $RC_WORK/gops/<id>.yuv (30 raw frames, made on first use).
The manifest is deterministic (sorted names, hash-based splits, a fixed RNG seed), so x265 and x264 runs that build it
from the same clips get identical GOPs.
"""
import hashlib
import json
import os
import re

import numpy as np

from . import config as C

MANIFEST = os.path.join(C.WORK, "manifest.json")

# GOP windows per clip (evenly spaced, non-overlapping) by family (D12)
GOPS_PER_CLIP = {"xiph_cif": 8, "xiph_hd": 8, "ugc": 8, "film": 60, "film_long": 90}
N_SPLICED = {"train": 120, "val": 40, "test": 60}     # GOPs built from 2-3 clips of one split (real scene cuts)

# films are split whole (one film = one source); Sintel trailer goes with the Sintel film
FILM_SPLIT = {"big_buck_bunny_720p24": "train", "elephants_dream_720p24": "train", "tears_of_steel": "val",
              "sintel": "test", "sintel_trailer_2k_720p24": "test"}


# ---------------------------------------------------------------- y4m access

def y4m_info(path):
    with open(path, "rb") as f:
        hdr = f.readline()
        assert hdr.startswith(b"YUV4MPEG2"), path
        w = int(re.search(rb" W(\d+)", hdr).group(1))
        h = int(re.search(rb" H(\d+)", hdr).group(1))
        first = f.readline()
    assert (w, h) == (C.W, C.H), (path, w, h)
    frame_hdr = len(first)                          # b"FRAME\n" (no per-frame params in our files)
    size = os.path.getsize(path)
    n = (size - len(hdr)) // (frame_hdr + C.FRAME_BYTES)
    return {"header": len(hdr), "frame_hdr": frame_hdr, "frames": int(n)}


def read_frames(path, start, n, info=None):
    info = info or y4m_info(path)
    stride = info["frame_hdr"] + C.FRAME_BYTES
    out = np.empty((n, C.FRAME_BYTES), np.uint8)
    with open(path, "rb") as f:
        for i in range(n):
            f.seek(info["header"] + (start + i) * stride + info["frame_hdr"])
            out[i] = np.frombuffer(f.read(C.FRAME_BYTES), np.uint8)
    return out


# ---------------------------------------------------------------- clip registry

def classify(name):
    """name is the clip file stem, e.g. xiph_foreman_cif, film_sintel, ugc_Gaming_360P-0b98."""
    if name.startswith("film_"):
        film = name[5:]
        return {"family": "film_long" if film in ("sintel", "tears_of_steel", "big_buck_bunny_720p24",
                                                   "elephants_dream_720p24") else "film",
                "source": "film_" + ("sintel" if film.startswith("sintel") else film), "category": "Film"}
    if name.startswith("ugc_"):
        cat = name[4:].split("_360P")[0]
        return {"family": "ugc", "source": name, "category": cat}
    if name.startswith("xiph_"):
        hd = "720p" in name or "1080p" in name
        return {"family": "xiph_hd" if hd else "xiph_cif", "source": name, "category": "Xiph-HD" if hd else "Xiph-CIF"}
    raise ValueError(name)


def _hash01(s):
    return int(hashlib.sha1(s.encode()).hexdigest()[:8], 16) / 2 ** 32


def split_of(name, meta):
    if meta["family"].startswith("film"):
        return FILM_SPLIT[name[5:]]
    u = _hash01(meta["source"])
    return "train" if u < 0.6 else ("val" if u < 0.8 else "test")


def list_clips():
    clips = []
    for fn in sorted(os.listdir(C.CLIPS)):
        if not fn.endswith(".y4m"):
            continue
        name = fn[:-4]
        meta = classify(name)
        info = y4m_info(os.path.join(C.CLIPS, fn))
        if info["frames"] < C.GOP:
            continue
        clips.append({"clip": name, **meta, "frames": info["frames"], "split": split_of(name, meta)})
    return clips


# ---------------------------------------------------------------- manifest

def build_manifest(seed=599):
    rng = np.random.default_rng(seed)
    clips = list_clips()
    gops = []
    for c in clips:
        avail = c["frames"] // C.GOP
        k = min(GOPS_PER_CLIP[c["family"]], avail)
        # evenly spaced windows over the whole clip (skip the first/last second of films: titles/credits)
        lo = 48 if c["family"].startswith("film") else 0
        hi = c["frames"] - C.GOP - (240 if c["family"].startswith("film") else 0)
        starts = np.unique(np.linspace(lo, max(lo, hi), k).astype(int))
        for s in starts:
            gops.append({"id": f"{c['clip']}@{s}", "clip": c["clip"], "source": c["source"], "family": c["family"],
                         "category": c["category"], "split": c["split"], "start": int(s)})
    # spliced GOPs: 2 or 3 segments from different sources of the same split -> hard scene cuts at known frames
    by_split = {}
    for c in clips:
        by_split.setdefault(c["split"], []).append(c)
    for split, n in N_SPLICED.items():
        pool = by_split.get(split, [])
        if len(pool) < 3:
            continue
        for i in range(n):
            m = int(rng.integers(2, 4))
            idx = rng.choice(len(pool), m, replace=False)
            cuts = np.sort(rng.choice(np.arange(4, C.GOP - 3), m - 1, replace=False))
            bounds = [0, *cuts.tolist(), C.GOP]
            parts = []
            for j, ci in enumerate(idx):
                c = pool[ci]
                ln = bounds[j + 1] - bounds[j]
                s = int(rng.integers(0, c["frames"] - ln))
                parts.append((c["clip"], s, ln))
            gops.append({"id": f"splice_{split}_{i:03d}", "clip": "splice", "source": f"splice_{split}",
                         "family": "splice", "category": "Splice", "split": split, "start": 0, "parts": parts,
                         "cuts": bounds[1:-1]})
    os.makedirs(C.WORK, exist_ok=True)
    with open(MANIFEST, "w") as f:
        json.dump({"clips": clips, "gops": gops}, f, indent=1)
    return gops


def load_manifest():
    with open(MANIFEST) as f:
        return json.load(f)


def gops(split=None, family=None):
    g = load_manifest()["gops"]
    if split:
        g = [x for x in g if x["split"] in (split if isinstance(split, (list, tuple)) else [split])]
    if family:
        g = [x for x in g if x["family"] == family]
    return g


def gop_path(g):
    """Path of the GOP's raw yuv file, creating it on first use (atomic rename: safe with many workers/jobs)."""
    gid = g["id"] if isinstance(g, dict) else g
    p = os.path.join(C.GOPS, gid.replace("/", "_") + ".yuv")
    if os.path.exists(p):
        return p
    assert isinstance(g, dict), "need the GOP record to build its file"
    os.makedirs(C.GOPS, exist_ok=True)
    if "parts" in g:
        fr = np.concatenate([read_frames(os.path.join(C.CLIPS, c + ".y4m"), s, n) for c, s, n in g["parts"]])
    else:
        fr = read_frames(os.path.join(C.CLIPS, g["clip"] + ".y4m"), g["start"], C.GOP)
    tmp = f"{p}.{os.getpid()}.part"
    fr.tofile(tmp)
    os.replace(tmp, p)
    return p


def gop_frames(g):
    return np.fromfile(gop_path(g), np.uint8).reshape(C.GOP, C.FRAME_BYTES)


def shard(items, n_shards, idx):
    """Deterministic contiguous shard of a list for job arrays."""
    return [x for i, x in enumerate(items) if i % n_shards == idx]
