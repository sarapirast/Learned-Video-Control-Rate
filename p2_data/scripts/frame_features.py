#!/usr/bin/env python3
"""Per-frame features for the decoded clips in data/v1/<res>/.

  --siti    SI and TI per frame (ITU-T P.910) -> features/siti/<clip_id>.csv, merged into features/siti.csv

SI/TI come from ffmpeg's siti filter, run on the decoded clips (what the encoder sees). The filter
expands limited-range luma to full range (x 255/219) and excludes the 1-pixel border, as P.910
specifies. On riverbed frames 0-1 it matches a plain-Python Sobel/difference implementation to
0.01 (docs/clip-selection.md). TI of frame 0 is 0 (no previous frame).

Needs ffmpeg: module load ver/2506 gcc/14.3.0 ffmpeg/7.1.1
"""
import argparse
import csv
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def siti(clip_id, args):
    path = os.path.join(args.data, 'clips', clip_id + '.y4m')
    out = subprocess.check_output(
        ['ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'error', '-i', path,
         '-vf', 'siti,metadata=print:file=-', '-f', 'null', '-'], universal_newlines=True)
    si = [float(v) for v in re.findall(r'lavfi\.siti\.si=([0-9.]+)', out)]
    ti = [float(v) for v in re.findall(r'lavfi\.siti\.ti=([0-9.]+)', out)]
    n = int(args.manifest[clip_id]['n_frames'])
    if len(si) != n or len(ti) != n:
        raise RuntimeError('%s: siti gave %d/%d values for %d frames' % (clip_id, len(si), len(ti), n))
    d = os.path.join(args.data, 'features', 'siti')
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, clip_id + '.csv')
    with open(dst + '.part', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['frame', 'si', 'ti'])
        w.writerows((i, '%.2f' % a, '%.2f' % b) for i, (a, b) in enumerate(zip(si, ti)))
    os.rename(dst + '.part', dst)
    return si, ti


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--res', default='320x180')
    ap.add_argument('--siti', action='store_true', required=True)
    ap.add_argument('--clip', help='one clip only (no merge)')
    args = ap.parse_args()
    args.data = os.path.join(ROOT, 'data', 'v1', args.res)
    args.manifest = {r['clip_id']: r for r in csv.DictReader(open(os.path.join(args.data, 'manifest.csv')))}
    ids = [args.clip] if args.clip else sorted(args.manifest)
    for c in ids:
        si, ti = siti(c, args)
        print('%-26s SI mean %6.2f  TI mean %6.2f' % (c, sum(si) / len(si), sum(ti[1:]) / max(1, len(ti) - 1)))
    if args.clip:
        return
    # Long-format merge: one row per (clip, frame), with split and group for convenience.
    dst = os.path.join(args.data, 'features', 'siti.csv')
    with open(dst + '.part', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['clip_id', 'split', 'group', 'frame', 'si', 'ti'])
        for c in ids:
            m = args.manifest[c]
            for r in csv.DictReader(open(os.path.join(args.data, 'features', 'siti', c + '.csv'))):
                w.writerow([c, m['split'], m['group'], r['frame'], r['si'], r['ti']])
    os.rename(dst + '.part', dst)
    print('merged -> %s' % dst)


if __name__ == '__main__':
    sys.exit(main())
