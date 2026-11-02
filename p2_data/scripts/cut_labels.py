#!/usr/bin/env python3
"""Scene-cut labels for the decoded clips in data/v1/<res>/.

  --signals   per-frame signals for every clip (or --clip ID) -> cuts/frames/<clip_id>.csv
              hist_delta   luma-histogram change from the previous frame (pilot-style detector)
              scdet_score  ffmpeg scdet score (0-100)
              y_mean, black_frac  mean luma and share of near-black pixels (for fades)
  --label     applies the rules below -> cuts/cut_frames.csv, cuts/gradual.csv, gops.csv,
              cuts/disagreements.csv, and prints a summary per split
  --review    contact sheets (previous | current frame) for disagreements -> cuts/review/*.png

Rules (docs/clip-selection.md, "Cut labels"):
  hist cut     hist_delta > HIST_T (pilot threshold 0.35; histogram definition is our
               re-implementation until the pilot code is available)
  scdet cut    scdet_score > SCDET_T (ffmpeg default 10)
  final cut    see FINAL_RULE
  gradual      fade: a >= FADE_MIN-frame luma ramp into or out of black frames
               dissolve candidate: histogram change over a DISSOLVE_W-frame window > HIST_T while
               no single frame is a cut
  review       verdicts in config/cut_review_v1.csv override the rule for the frames they list:
               cut / no_cut / unsure (counted as no cut) / gradual (a 3-frame gradual span)
  GOP label    'cut' if a final cut falls inside it (not on its first frame), else 'gradual' if a
               gradual span overlaps it, else 'stable'

Needs ffmpeg: module load ver/2506 gcc/14.3.0 ffmpeg/7.1.1
"""
import argparse
import csv
import os
import re
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW = os.path.join(ROOT, 'config', 'cut_review_v1.csv')
HIST_BINS = 64
HIST_T = 0.35
SCDET_T = 10.0
# 'evidence' (chosen after reviewing disagreements, docs/clip-selection.md): one detector fires and
# the other shows at least weak evidence. Histogram-only hits with scdet <= 2 were mostly dark or
# flat content; scdet-only hits with hist <= 0.1 were mostly motion.
FINAL_RULE = 'evidence'      # 'evidence' | 'both' | 'hist' | 'scdet' | 'either'
HIST_WEAK = 0.10
SCDET_WEAK = 2.0
BLACK_Y = 32                 # a pixel is near-black at Y <= 32 (limited range: black is 16)
BLACK_FRAC = 0.98            # a frame is black if >= 98% of its pixels are near-black
FADE_MIN = 4                 # frames of monotone luma change into or out of black
DISSOLVE_W = 8               # window for the dissolve test
GOP = 30


def y4m_frames(path):
    """Yield (Y plane bytes, width, height) for each frame of an 8-bit 4:2:0 y4m."""
    with open(path, 'rb') as f:
        hdr = f.readline().decode()
        w, h = (int(x) for x in re.search(r' W(\d+) H(\d+)', hdr).groups())
        ysize, rec = w * h, w * h * 3 // 2
        while True:
            marker = f.readline()
            if not marker:
                return
            if not marker.startswith(b'FRAME'):
                raise IOError('%s: bad frame marker %r' % (path, marker[:10]))
            data = f.read(rec)
            if len(data) != rec:
                raise IOError('%s: truncated frame' % path)
            yield data[:ysize], w, h


def tv_distance(a, b):
    """Total-variation distance between two normalised histograms (0 = same, 1 = disjoint)."""
    return 0.5 * sum(abs(x - y) for x, y in zip(a, b))


def binned(counts, n):
    """256-level counts -> normalised HIST_BINS-bin histogram."""
    h = [0] * HIST_BINS
    for level, c in counts.items():
        h[level * HIST_BINS // 256] += c
    return [c / n for c in h]


def scdet_scores(path, n_frames):
    out = subprocess.check_output(
        ['ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'error', '-i', path,
         '-vf', 'scdet=threshold=%g,metadata=print:key=lavfi.scd.score:file=-' % SCDET_T,
         '-f', 'null', '-'], universal_newlines=True)
    scores = [float(v) for v in re.findall(r'lavfi\.scd\.score=([0-9.]+)', out)]
    if len(scores) != n_frames:
        raise RuntimeError('%s: scdet gave %d scores for %d frames' % (path, len(scores), n_frames))
    return scores


def signals(clip_id, args):
    path = os.path.join(args.data, 'clips', clip_id + '.y4m')
    rows, prev = [], None
    for i, (y, w, h) in enumerate(y4m_frames(path)):
        counts = Counter(y)                     # C-speed count of the 256 luma levels
        n = w * h
        hist = binned(counts, n)
        rows.append(dict(frame=i, hist_delta=0.0 if prev is None else tv_distance(prev, hist),
                         y_mean=sum(l * c for l, c in counts.items()) / n,
                         black_frac=sum(c for l, c in counts.items() if l <= BLACK_Y) / n))
        prev = hist
    for r, s in zip(rows, scdet_scores(path, len(rows))):
        r['scdet_score'] = s
    out_dir = os.path.join(args.data, 'cuts', 'frames')
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, clip_id + '.csv')
    with open(dst + '.part', 'w', newline='') as f:
        wr = csv.DictWriter(f, ['frame', 'hist_delta', 'scdet_score', 'y_mean', 'black_frac'])
        wr.writeheader()
        for r in rows:
            wr.writerow({k: ('%.5f' % v if isinstance(v, float) else v) for k, v in r.items()})
    os.rename(dst + '.part', dst)
    print('%s: %d frames, %d hist cuts, %d scdet cuts' % (
        clip_id, len(rows), sum(r['hist_delta'] > HIST_T for r in rows),
        sum(r['scdet_score'] > SCDET_T for r in rows)))


def load_frames(args, clip_id):
    rows = list(csv.DictReader(open(os.path.join(args.data, 'cuts', 'frames', clip_id + '.csv'))))
    for r in rows:
        r['frame'] = int(r['frame'])
        for k in ('hist_delta', 'scdet_score', 'y_mean', 'black_frac'):
            r[k] = float(r[k])
    return rows


def is_final(r):
    h, s = r['hist_delta'], r['scdet_score']
    if FINAL_RULE == 'evidence':
        return (s > SCDET_T and h > HIST_WEAK) or (h > HIST_T and s > SCDET_WEAK)
    hist, scdet = h > HIST_T, s > SCDET_T
    return {'both': hist and scdet, 'hist': hist, 'scdet': scdet, 'either': hist or scdet}[FINAL_RULE]


def gradual_spans(rows, cuts):
    """(start, end, kind) spans of fades and dissolve candidates, end inclusive."""
    spans = []
    black = [r['black_frac'] >= BLACK_FRAC for r in rows]
    y = [r['y_mean'] for r in rows]
    n = len(rows)
    # Fades: a monotone luma ramp of >= FADE_MIN frames ending at a black frame (fade out) or
    # starting from one (fade in). Hard cuts to or from black are not fades.
    for t in range(n):
        if not black[t]:
            continue
        if t > 0 and not black[t - 1]:              # entering black at t: look back for a ramp
            s = t - 1
            while s > 0 and y[s - 1] > y[s] + 0.5 and s - 1 not in cuts:
                s -= 1
            if t - s >= FADE_MIN and t not in cuts:
                spans.append((s, t, 'fade_out'))
        if t + 1 < n and not black[t + 1]:          # leaving black after t: look ahead for a ramp
            e = t + 1
            while e + 1 < n and y[e + 1] > y[e] + 0.5 and e + 1 not in cuts:
                e += 1
            if e - t >= FADE_MIN and t + 1 not in cuts:
                spans.append((t, e, 'fade_in'))
    return spans


def dissolve_candidates(rows, hists, cuts):
    spans = []
    for t in range(DISSOLVE_W, len(rows)):
        if any(f in cuts for f in range(t - DISSOLVE_W + 1, t + 1)):
            continue
        if tv_distance(hists[t - DISSOLVE_W], hists[t]) > HIST_T:
            if spans and spans[-1][1] >= t - DISSOLVE_W:
                spans[-1] = (spans[-1][0], t, 'dissolve?')
            else:
                spans.append((t - DISSOLVE_W, t, 'dissolve?'))
    return spans


def clip_hists(args, clip_id):
    path = os.path.join(args.data, 'clips', clip_id + '.y4m')
    return [binned(Counter(y), w * h) for y, w, h in y4m_frames(path)]


def label(args):
    manifest = {r['clip_id']: r for r in csv.DictReader(open(os.path.join(args.data, 'manifest.csv')))}
    review = {}
    if os.path.exists(REVIEW):
        review = {(r['clip_id'], int(r['frame'])): r['verdict'] for r in csv.DictReader(open(REVIEW))}
    # Spliced clips (make_spliced.py) have exact labels: piece boundaries plus the source labels.
    known_cuts, known_grad = {}, {}
    sdir = os.path.join(args.data, 'spliced')
    if os.path.exists(os.path.join(sdir, 'cuts.csv')):
        for r in csv.DictReader(open(os.path.join(sdir, 'cuts.csv'))):
            known_cuts.setdefault(r['clip_id'], {})[int(r['frame'])] = r['kind']
        for r in csv.DictReader(open(os.path.join(sdir, 'gradual.csv'))):
            known_grad.setdefault(r['clip_id'], []).append((int(r['start']), int(r['end']), r['kind']))
    cut_rows, disagree, gradual, gops = [], [], [], []
    for clip_id in sorted(manifest):
        m = manifest[clip_id]
        rows = load_frames(args, clip_id)
        cuts, reviewed_gradual = set(), []
        if m['source'] == 'spliced':
            known = known_cuts.get(clip_id, {})
            for r in rows:
                if r['frame'] in known:
                    cuts.add(r['frame'])
                    cut_rows.append(dict(clip_id=clip_id, split=m['split'], frame=r['frame'],
                                         hist_delta='%.3f' % r['hist_delta'], scdet_score='%.1f' % r['scdet_score'],
                                         hist_cut=int(r['hist_delta'] > HIST_T), scdet_cut=int(r['scdet_score'] > SCDET_T),
                                         final_cut=1, review='spliced:' + known[r['frame']]))
            rows_for_spans = []
            spans = list(known_grad.get(clip_id, []))
        else:
            rows_for_spans = rows
        for r in rows_for_spans:
            h, s = r['hist_delta'] > HIST_T, r['scdet_score'] > SCDET_T
            verdict = review.get((clip_id, r['frame']), '')
            if h or s or verdict:
                final = verdict == 'cut' if verdict else is_final(r)
                rec = dict(clip_id=clip_id, split=m['split'], frame=r['frame'],
                           hist_delta='%.3f' % r['hist_delta'], scdet_score='%.1f' % r['scdet_score'],
                           hist_cut=int(h), scdet_cut=int(s), final_cut=int(final), review=verdict)
                cut_rows.append(rec)
                if h != s:
                    disagree.append(rec)
                if final:
                    cuts.add(r['frame'])
                if verdict == 'gradual':
                    reviewed_gradual.append((r['frame'] - 1, r['frame'] + 1, 'reviewed'))
        if m['source'] != 'spliced':
            spans = gradual_spans(rows, cuts) + reviewed_gradual
        if args.dissolves and m['source'] != 'spliced':
            spans += dissolve_candidates(rows, clip_hists(args, clip_id), cuts)
        for s, e, kind in spans:
            gradual.append(dict(clip_id=clip_id, split=m['split'], start=s, end=e, kind=kind))
        n = len(rows)
        for g in range(n // GOP):                    # full GOPs only
            a, b = g * GOP, (g + 1) * GOP
            inside = sorted(f for f in cuts if a < f < b)
            grad = [sp for sp in spans if sp[0] < b and sp[1] >= a]
            gops.append(dict(clip_id=clip_id, gop=g, split=m['split'], group=m['group'],
                             start_frame=a, n_frames=GOP,
                             label='cut' if inside else ('gradual' if grad else 'stable'),
                             cut_frames=' '.join(str(f - a) for f in inside),
                             cut_at_gop_start=int(a in cuts)))
    cdir = os.path.join(args.data, 'cuts')
    write_csv(os.path.join(cdir, 'cut_frames.csv'), cut_rows)
    write_csv(os.path.join(cdir, 'disagreements.csv'), disagree)
    write_csv(os.path.join(cdir, 'gradual.csv'), gradual,
              ['clip_id', 'split', 'start', 'end', 'kind'])
    write_csv(os.path.join(args.data, 'gops.csv'), gops)
    summary(gops, cut_rows, disagree, gradual)


def write_csv(path, rows, fields=None):
    with open(path + '.part', 'w', newline='') as f:
        w = csv.DictWriter(f, fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    os.rename(path + '.part', path)


def summary(gops, cut_rows, disagree, gradual):
    print('rule: final cut = %s; hist > %.2f (%d bins), scdet > %g; review overrides: %s' % (
        FINAL_RULE, HIST_T, HIST_BINS, SCDET_T,
        dict(Counter(r['review'] for r in cut_rows if r['review']))))
    print('frames: %d hist cuts, %d scdet cuts, %d both, %d disagree; %d final cuts; %d gradual spans'
          % (sum(int(r['hist_cut']) for r in cut_rows), sum(int(r['scdet_cut']) for r in cut_rows),
             sum(int(r['hist_cut']) and int(r['scdet_cut']) for r in cut_rows), len(disagree),
             sum(int(r['final_cut']) for r in cut_rows), len(gradual)))
    print('%-6s %5s %7s %7s %7s   %s' % ('split', 'gops', 'stable', 'cut', 'gradual', 'cut GOPs from clips/groups'))
    for s in ('train', 'val', 'test'):
        g = [x for x in gops if x['split'] == s]
        c = Counter(x['label'] for x in g)
        cg = [x for x in g if x['label'] == 'cut']
        print('%-6s %5d %7d %7d %7d   %d clips / %d groups' % (
            s, len(g), c['stable'], c['cut'], c['gradual'],
            len({x['clip_id'] for x in cg}), len({x['group'] for x in cg})))


def review(args):
    """previous | current frame side by side for each disagreement (and gradual span ends)."""
    rows = list(csv.DictReader(open(os.path.join(args.data, 'cuts', 'disagreements.csv'))))
    if args.limit:
        rows = rows[:args.limit]
    out = os.path.join(args.data, 'cuts', 'review')
    os.makedirs(out, exist_ok=True)
    for r in rows:
        f = int(r['frame'])
        dst = os.path.join(out, '%s_f%03d_%s.png' % (r['clip_id'], f, 'hist' if r['hist_cut'] == '1' else 'scdet'))
        subprocess.check_call(
            ['ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'error', '-y',
             '-i', os.path.join(args.data, 'clips', r['clip_id'] + '.y4m'),
             '-vf', 'select=between(n\\,%d\\,%d),tile=2x1' % (f - 1, f), '-frames:v', '1', dst])
    print('%d sheets -> %s' % (len(rows), out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--res', default='320x180')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--signals', action='store_true')
    g.add_argument('--label', action='store_true')
    g.add_argument('--review', action='store_true')
    ap.add_argument('--clip', help='--signals for one clip only')
    ap.add_argument('--dissolves', action='store_true', help='--label: also flag dissolve candidates')
    ap.add_argument('--limit', type=int, default=0, help='--review: at most N sheets')
    args = ap.parse_args()
    args.data = os.path.join(ROOT, 'data', 'v1', args.res)
    if args.signals:
        ids = [args.clip] if args.clip else sorted(
            r['clip_id'] for r in csv.DictReader(open(os.path.join(args.data, 'manifest.csv'))))
        for c in ids:
            signals(c, args)
    elif args.label:
        label(args)
    else:
        review(args)


if __name__ == '__main__':
    main()
