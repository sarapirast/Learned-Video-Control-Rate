#!/usr/bin/env python3
"""Build the candidate clip list, data/clip_candidates.csv.

Inputs:
  config/clip_sources.csv   hand-curated sources (films, Xiph, UVG, Netflix), one row per source
  YouTube UGC metadata      fetched into data/meta/ on first run (features, attribution, object list)

What it does:
  - expands each source into clips: films become evenly spaced segments; high frame rates are
    decimated to <= 30 fps (120 -> 30, 60 -> 30, 50 -> 25)
  - samples YouTube UGC per category, stratified by temporal complexity, one clip per uploader,
    plus a shortlist of likely natural-cut clips (highest chunk-complexity variation)
  - applies the frame-rate rule (see fps_status) to every source
  - assigns splits by group (never by clip or GOP), so clips that share a film or shoot stay together

Deterministic: same inputs and --seed give the same output. UGC frame rates are probed with ffprobe
over HTTP and cached in data/meta/ugc_probe.tsv, so ffprobe is needed only for uncached clips:
  module load ver/2506 gcc/14.3.0 ffmpeg/7.1.1

  python3 scripts/select_clips.py [--seed 599] [--gop 30]
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, 'config', 'clip_sources.csv')
# Clips the team decided to leave out, with the reason; the selector picks a replacement as usual.
EXCLUDE = os.path.join(ROOT, 'config', 'exclude_clips.csv')
META = os.path.join(ROOT, 'data', 'meta')
OUT = os.path.join(ROOT, 'data', 'clip_candidates.csv')

UGC_BASE = 'https://storage.googleapis.com/ugc-dataset'
UGC_API = 'https://storage.googleapis.com/storage/v1/b/ugc-dataset/o'
# Left out: HDR (needs tone mapping), VR (equirectangular), VerticalVideo (mostly portrait),
# Lyrics (3 clips).
UGC_CATEGORIES = ['Animation', 'CoverSong', 'Gaming', 'HowTo', 'Lecture', 'LiveMusic',
                  'LyricVideo', 'MusicVideo', 'NewsClip', 'Sports', 'TelevisionClip', 'Vlog']
# Categories where edits are common. Their likely-cut picks get these splits, in this order.
UGC_CUT_SPLITS = [('MusicVideo', 'test'), ('TelevisionClip', 'val'), ('NewsClip', 'test'),
                  ('LyricVideo', 'val'), ('LiveMusic', 'test'), ('Gaming', 'train')]
UGC_P1_PER_CATEGORY = 3
UGC_P2_PER_CATEGORY = 1
# Small resolutions first: everything is downscaled to ~320x180 anyway.
UGC_RES = ['360P', '480P', '720P']

# Frame-rate rule (team decision 2026-10-29): accept 23.976-30 fps sources. 50/60 fps-family sources
# (and their 100/120 multiples) are kept but flagged for a decision; any other rate is rejected.
FPS_MIN, FPS_MAX = 23.976, 30.0
HIGH_FPS = [50, 59.94, 60, 100, 119.88, 120]

FIELDS = ['clip_id', 'source_id', 'source', 'group', 'priority', 'split', 'cuts', 'spliced',
          'url', 'licence', 'src_res', 'src_fps', 'fps_status', 'decimate', 'out_fps',
          'start_frame', 'n_frames', 'est_gops', 'notes']


def fps_status(fps):
    if FPS_MIN - 0.01 <= fps <= FPS_MAX + 0.01:
        return 'ok'
    if any(abs(fps - h) <= 0.005 * h for h in HIGH_FPS):
        return 'flag-high-fps'
    return 'reject'


class UgcProbe:
    """Frame rate and duration of UGC clips, from ffprobe, cached in a TSV."""

    def __init__(self, path):
        self.path, self.cache = path, {}
        if os.path.exists(path):
            for line in open(path):
                name, fps, dur = line.rstrip('\n').split('\t')
                self.cache[name] = (float(fps), float(dur))

    def __call__(self, c):
        if c['name'] not in self.cache:
            try:
                out = subprocess.check_output(
                    ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                     'stream=r_frame_rate:format=duration', '-of', 'csv=p=0', c['url']],
                    universal_newlines=True, timeout=120)
            except FileNotFoundError:
                sys.exit('ffprobe not found; run: module load ver/2506 gcc/14.3.0 ffmpeg/7.1.1')
            rate, dur = out.split()[:2]
            num, den = rate.split('/')
            self.cache[c['name']] = (int(num) / int(den), float(dur))
            with open(self.path, 'a') as f:
                f.write('%s\t%.6f\t%.6f\n' % ((c['name'],) + self.cache[c['name']]))
        return self.cache[c['name']]


def fetch(url, path):
    if not os.path.exists(path):
        print('fetching', url, file=sys.stderr)
        with urllib.request.urlopen(url, timeout=120) as f, open(path + '.part', 'wb') as g:
            g.write(f.read())
        os.rename(path + '.part', path)
    return path


def ugc_objects(path):
    """name -> size for every .mkv under original_videos/ (cached as TSV)."""
    if not os.path.exists(path):
        rows, token = [], ''
        while True:
            q = '?prefix=original_videos/&fields=nextPageToken,items(name,size)&maxResults=1000'
            with urllib.request.urlopen(UGC_API + q + ('&pageToken=' + token if token else ''),
                                        timeout=120) as f:
                d = json.loads(f.read().decode())
            rows += [(o['name'], o['size']) for o in d.get('items', [])]
            token = d.get('nextPageToken', '')
            if not token:
                break
        with open(path + '.part', 'w') as g:
            g.writelines('%s\t%s\n' % r for r in rows)
        os.rename(path + '.part', path)
    objs = {}
    for line in open(path):
        name, size = line.rstrip('\n').split('\t')
        if name.endswith('.mkv'):
            objs[os.path.basename(name)[:-4]] = (name, int(size))
    return objs


def load_ugc():
    os.makedirs(META, exist_ok=True)
    feats = fetch(UGC_BASE + '/original_videos/dataset_selection_features.csv',
                  os.path.join(META, 'ugc_dataset_selection_features.csv'))
    attrib = fetch(UGC_BASE + '/ATTRIBUTION', os.path.join(META, 'ugc_ATTRIBUTION.txt'))
    objs = ugc_objects(os.path.join(META, 'ugc_objects.tsv'))

    authors = {}
    pat = re.compile(r"^(\S+) is an audio-removed excerpt from '.*' by '(.*)' licensed under (.+?)\s*$")
    for line in open(attrib, encoding='utf-8'):
        m = pat.match(line)
        if m:
            authors[m.group(1)] = (m.group(2), m.group(3))

    clips = []
    for r in csv.DictReader(open(feats)):
        name = r['FILENAME']
        cat, res = re.match(r'^([A-Za-z]+)_(\d+P)-', name).groups()
        w, h = int(r['WIDTH']), int(r['HEIGHT'])
        if cat not in UGC_CATEGORIES or res not in UGC_RES or not 1.7 < w / h < 1.8:
            continue
        if name not in objs or name not in authors:
            continue
        clips.append(dict(name=name, cat=cat, res=res, w=w, h=h,
                          sc=float(r['SPATIAL_COMPLEXITY']), tc=float(r['TEMPORAL_COMPLEXITY']),
                          cv=float(r['CHUNK_COMPLEXITY_VARIATION']),
                          author=authors[name][0], licence=authors[name][1],
                          url=UGC_BASE + '/' + objs[name][0], size=objs[name][1]))
    return clips


def quantile_pick(pool, n, used_authors, eligible):
    """n clips spread evenly over temporal complexity, skipping uploaders already used and clips
    that fail eligible(c)."""
    pool = sorted(pool, key=lambda c: (c['tc'], c['sc'], c['name']))
    picks = []
    for j in range(n):
        target = (j + 0.5) / n * len(pool)
        # nearest eligible clip to the target position
        for c in sorted(pool, key=lambda c: (abs(pool.index(c) + 0.5 - target), c['name'])):
            if c['author'] not in used_authors and c not in picks and eligible(c):
                picks.append(c)
                used_authors.add(c['author'])
                break
    return picks


def ugc_rows():
    clips = load_ugc()
    probe = UgcProbe(os.path.join(META, 'ugc_probe.tsv'))
    excluded = {r['clip_id'] for r in csv.DictReader(open(EXCLUDE))} if os.path.exists(EXCLUDE) else set()
    # Eligibility is checked only for clips the picker reaches, so only those get probed.
    eligible = lambda c: c['name'] not in excluded and fps_status(probe(c)[0]) != 'reject'
    by_cat = defaultdict(list)
    for c in clips:
        by_cat[c['cat']].append(c)
    used, rows = set(), []

    def row(c, priority, split, cuts, why):
        fps, dur = probe(c)
        return dict(source_id=c['name'], source='youtube-ugc', group='ugc:' + c['author'],
                    priority=priority, split=split, cuts=cuts, url=c['url'],
                    licence=c['licence'] + ' (attribute uploader; see data/meta/ugc_ATTRIBUTION.txt)',
                    src_res='%dx%d' % (c['w'], c['h']), fps='%.3f' % fps,
                    src_frames=str(int(round(dur * fps))), start='',
                    max_frames='300', segments='1',
                    notes='%s; %s; SC=%.2f TC=%.2f CV=%.1f; %.2f GB' % (
                        why, c['cat'], c['sc'], c['tc'], c['cv'], c['size'] / 1e9))

    for cat in UGC_CATEGORIES:
        # Prefer the smaller resolutions; fall back to 720P only if the pool is thin.
        pool = [c for c in by_cat[cat] if c['res'] != '720P']
        if len(pool) < 2 * (UGC_P1_PER_CATEGORY + UGC_P2_PER_CATEGORY):
            pool = by_cat[cat]
        p1 = quantile_pick(pool, UGC_P1_PER_CATEGORY, used, eligible)
        p2 = quantile_pick([c for c in pool if c not in p1], UGC_P2_PER_CATEGORY, used, eligible)
        rows += [row(c, '1', 'auto', 'unknown', 'complexity-stratified') for c in p1]
        rows += [row(c, '2', 'auto', 'unknown', 'complexity-stratified') for c in p2]

    for cat, split in UGC_CUT_SPLITS:
        pool = sorted((c for c in by_cat[cat] if c['author'] not in used),
                      key=lambda c: (c['res'] == '720P', -c['cv'], c['name']))
        pick = next((c for c in pool if eligible(c)), None)
        if pick:
            used.add(pick['author'])
            rows.append(row(pick, '1', split, 'likely', 'likely cuts (highest chunk variation)'))
    return rows


def expand(src, gop):
    """One source row -> list of clip rows."""
    fps = float(src['fps'])
    status = fps_status(fps)
    if status == 'reject':
        sys.exit('%s: %g fps breaks the frame-rate rule (%g-%g fps); fix config/clip_sources.csv'
                 % (src['source_id'], fps, FPS_MIN, FPS_MAX))
    # Decimation applies only if the team keeps the flagged high-frame-rate sources.
    decimate = max(1, int(round(fps / 30)))
    max_out = int(src['max_frames'])
    start = int(src['start'] or 0)
    segments = int(src['segments'] or 1)
    base = {k: src[k] for k in ('source_id', 'source', 'group', 'priority', 'split', 'cuts',
                                'url', 'licence', 'src_res', 'notes')}
    base.update(spliced=0, src_fps=src['fps'], fps_status=status, decimate=decimate,
                out_fps=round(fps / decimate, 3))

    total = int(src['src_frames'])
    if segments == 1:
        n = min(max_out, (total - start) // decimate)
        return [dict(base, clip_id=src['source_id'], start_frame=start, n_frames=n,
                     est_gops=n // gop)]

    # Films: evenly spaced segments between 5% and 90% of the running time
    # (skips opening titles and end credits).
    span = max_out * decimate
    lo, hi = int(0.05 * total), int(0.90 * total) - span
    clips = []
    for k in range(segments):
        s = lo + int(round(k * (hi - lo) / (segments - 1)))
        clips.append(dict(base, clip_id='%s_s%02d' % (src['source_id'], k), start_frame=s,
                          n_frames=max_out, est_gops=max_out // gop))
    return clips


def assign_splits(rows, seed):
    """Fill split='auto' by group, ~70/15/15 train/val/test. Each group's split depends only on a
    hash of its own name, so adding or removing other clips never moves it."""
    split_of = {r['group']: r['split'] for r in rows if r['split'] != 'auto'}
    for r in rows:
        g = r['group']
        if g not in split_of:
            f = int(hashlib.sha1(('%s:%s' % (seed, g)).encode()).hexdigest()[:8], 16) / 2.0 ** 32
            split_of[g] = 'train' if f < 0.70 else ('val' if f < 0.85 else 'test')
        r['split'] = split_of[g]


def summary(rows):
    print('%-6s %6s %6s %6s   %s' % ('split', 'clips', 'groups', 'gops', 'clips with natural/likely cuts'))
    for s in ('train', 'val', 'test'):
        rs = [r for r in rows if r['split'] == s]
        cut = [r for r in rs if r['cuts'] in ('natural', 'likely')]
        print('%-6s %6d %6d %6d   %d clips from %d groups' % (
            s, len(rs), len({r['group'] for r in rs}), sum(r['est_gops'] for r in rs),
            len(cut), len({r['group'] for r in cut})))
    print()
    for p in ('1', '2'):
        rs = [r for r in rows if r['priority'] == p]
        print('priority %s: %d clips, %d GOPs (%s)' % (
            p, len(rs), sum(r['est_gops'] for r in rs),
            ', '.join('%s %d' % kv for kv in sorted(Counter(r['split'] for r in rs).items()))))
    print()
    print('by source:', ', '.join('%s %d' % kv for kv in sorted(Counter(r['source'] for r in rows).items())))
    flagged = [r for r in rows if r['fps_status'] != 'ok']
    print('\nflagged high frame rate (team decision): %d clips (%d priority 1)' % (
        len(flagged), sum(r['priority'] == '1' for r in flagged)))
    for fps, rs in sorted(groupby_fps(flagged).items(), key=lambda kv: float(kv[0])):
        print('  %7s fps: %s' % (fps, ', '.join(r['clip_id'] for r in rs)))


def groupby_fps(rows):
    out = defaultdict(list)
    for r in rows:
        out[r['src_fps']].append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seed', type=int, default=599)
    ap.add_argument('--gop', type=int, default=30, help='GOP length used for est_gops only')
    args = ap.parse_args()

    sources = list(csv.DictReader(open(SOURCES)))
    rows = []
    for src in sources + ugc_rows():
        rows += expand(src, args.gop)
    ids = Counter(r['clip_id'] for r in rows)
    dup = [i for i, n in ids.items() if n > 1]
    if dup:
        sys.exit('duplicate clip ids: %s' % dup)
    assign_splits(rows, args.seed)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + '.part', 'w', newline='') as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    os.rename(OUT + '.part', OUT)
    print('wrote %s (%d clips)\n' % (OUT, len(rows)))
    summary(rows)


if __name__ == '__main__':
    main()
