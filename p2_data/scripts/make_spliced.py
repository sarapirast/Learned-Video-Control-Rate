#!/usr/bin/env python3
"""Spliced clips for training: random pieces of v1 train clips joined by hard cuts.

Recipe (the pilot's, docs/Report.pdf / Dataset videos and sources.pdf): each spliced clip is 300 frames
of random 20-70-frame pieces, random seed fixed per clip. For v1:
  - pieces come only from train clips, so spliced clips are train only (plan: never in val/test)
  - one frame-rate class per spliced clip (~30 fps = 29.97/30, or 25 fps), so it has one rate
  - consecutive pieces come from different clips, so every boundary is a real cut
  - frames are copied byte-for-byte from the decoded clips: no re-encode, no re-scale
Labels are exact, not detected: every piece boundary is a cut, plus the source clip's own cuts and
gradual spans inside each piece. They go to spliced/cuts.csv and spliced/gradual.csv, which
cut_labels.py uses instead of the detectors for these clips.

Outputs (data/v1/<res>/): clips/spliced_NN.y4m, meta/spliced_NN.json (merged into manifest.csv by
decode_clips.py --merge), spliced/pieces.csv, spliced/cuts.csv, spliced/gradual.csv.

  python3 scripts/make_spliced.py [--res 320x180]
"""
import argparse
import csv
import hashlib
import json
import os
import random
import re
import time
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N_FRAMES = 300
PIECE_MIN, PIECE_MAX = 20, 70
# (clip number, frame-rate class). Classes: header rate and the source rates they accept.
PLAN = [(1, '30'), (2, '30'), (3, '30'), (4, '30'), (5, '25'), (6, '25')]
CLASSES = {'30': ('30000/1001', {'30000/1001', '30/1'}), '25': ('25/1', {'25/1'})}
SEED_BASE = 599000


def y4m_index(path):
    """(header line, payload bytes per frame, frame count) of an 8-bit 4:2:0 y4m."""
    with open(path, 'rb') as f:
        hdr = f.readline()
    w, h = (int(x) for x in re.search(rb' W(\d+) H(\d+)', hdr).groups())
    rec = w * h * 3 // 2 + 6
    n = (os.path.getsize(path) - len(hdr)) // rec
    return hdr, rec, n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--res', default='320x180')
    args = ap.parse_args()
    data = os.path.join(ROOT, 'data', 'v1', args.res)
    man = [m for m in csv.DictReader(open(os.path.join(data, 'manifest.csv'))) if m['source'] != 'spliced']
    srcs = {k: [m for m in man if m['split'] == 'train' and m['fps'] in rates]
            for k, (_, rates) in CLASSES.items()}
    cuts = {}
    for r in csv.DictReader(open(os.path.join(data, 'cuts', 'cut_frames.csv'))):
        if r['final_cut'] == '1':
            cuts.setdefault(r['clip_id'], set()).add(int(r['frame']))
    grads = {}
    for r in csv.DictReader(open(os.path.join(data, 'cuts', 'gradual.csv'))):
        grads.setdefault(r['clip_id'], []).append((int(r['start']), int(r['end'])))
    template = json.load(open(os.path.join(data, 'meta', man[0]['clip_id'] + '.json')))

    sdir = os.path.join(data, 'spliced')
    os.makedirs(sdir, exist_ok=True)
    pieces_rows, cut_rows, grad_rows = [], [], []
    for num, cls in PLAN:
        clip_id = 'spliced_%02d' % num
        rng = random.Random(SEED_BASE + num)
        pool = sorted(srcs[cls], key=lambda m: m['clip_id'])
        out_hdr_rate = CLASSES[cls][0]
        pieces, pos, prev = [], 0, None
        while pos < N_FRAMES:
            m = rng.choice([x for x in pool if x['clip_id'] != prev])
            n = min(rng.randint(PIECE_MIN, PIECE_MAX), N_FRAMES - pos)
            total = int(m['n_frames'])
            start = rng.randint(0, total - n)
            pieces.append((m, start, n, pos))
            pos += n
            prev = m['clip_id']
        # Write frames byte-for-byte from the decoded sources.
        dst = os.path.join(data, 'clips', clip_id + '.y4m')
        first_hdr = None
        with open(dst + '.part', 'wb') as out:
            for k, (m, start, n, opos) in enumerate(pieces):
                path = os.path.join(data, 'clips', m['clip_id'] + '.y4m')
                hdr, rec, total = y4m_index(path)
                if first_hdr is None:
                    w, h = re.search(rb' W(\d+) H(\d+)', hdr).groups()
                    first_hdr = b'YUV4MPEG2 W%s H%s F%s Ip A1:1 C420jpeg XCOLORRANGE=LIMITED\n' % (
                        w, h, out_hdr_rate.replace('/', ':').encode())
                    out.write(first_hdr)
                with open(path, 'rb') as f:
                    f.seek(len(hdr) + start * rec)
                    data_bytes = f.read(n * rec)
                assert len(data_bytes) == n * rec and data_bytes[:6] == b'FRAME\n', (clip_id, m['clip_id'])
                out.write(data_bytes)
                pieces_rows.append(dict(clip_id=clip_id, piece=k, src_clip=m['clip_id'], src_group=m['group'],
                                        src_start=start, n_frames=n, out_start=opos))
                if opos > 0:
                    cut_rows.append(dict(clip_id=clip_id, frame=opos, kind='boundary', src_clip=m['clip_id']))
                for f in sorted(cuts.get(m['clip_id'], ())):
                    if start < f < start + n:            # source cut strictly inside the piece
                        cut_rows.append(dict(clip_id=clip_id, frame=opos + f - start, kind='source_cut',
                                             src_clip=m['clip_id']))
                for a, b in grads.get(m['clip_id'], ()):
                    a2, b2 = max(a, start), min(b, start + n - 1)
                    if a2 <= b2:
                        grad_rows.append(dict(clip_id=clip_id, start=opos + a2 - start, end=opos + b2 - start,
                                              kind='source_gradual', src_clip=m['clip_id']))
        size = os.path.getsize(dst + '.part')
        rec = y4m_index(os.path.join(data, 'clips', pieces[0][0]['clip_id'] + '.y4m'))[1]
        assert size == len(first_hdr) + N_FRAMES * rec, (clip_id, size)
        h = hashlib.md5()
        with open(dst + '.part', 'rb') as f:
            for b in iter(lambda: f.read(8 << 20), b''):
                h.update(b)
        os.rename(dst + '.part', dst)
        meta = {k: '' for k in template}
        meta.update(clip_id=clip_id, split='train', group='spliced:%s' % clip_id, source='spliced',
                    path='clips/%s.y4m' % clip_id, width=template['width'], height=template['height'],
                    fps=out_hdr_rate, n_frames=N_FRAMES,
                    src_path='%d pieces from %d train clips (see spliced/pieces.csv)' % (
                        len(pieces), len({p[0]['clip_id'] for p in pieces})),
                    src_size='mixed', src_pix_fmt='yuv420p', src_start_frame=0, crop='none',
                    colour_conversion='none (byte copy of decoded v1 frames)', bit_depth='8-bit source',
                    filter_chain='byte concatenation, seed %d' % (SEED_BASE + num),
                    y4m_header=first_hdr.decode().strip(), md5=h.hexdigest(),
                    decoded_at=time.strftime('%Y-%m-%d %H:%M:%S'))
        with open(os.path.join(data, 'meta', clip_id + '.json'), 'w') as f:
            json.dump(meta, f, indent=1)
        print('%s: %d pieces from %d clips, %d cuts (%d boundaries), %s fps' % (
            clip_id, len(pieces), len({p[0]['clip_id'] for p in pieces}),
            sum(1 for c in cut_rows if c['clip_id'] == clip_id),
            sum(1 for c in cut_rows if c['clip_id'] == clip_id and c['kind'] == 'boundary'), out_hdr_rate))

    for name, rows, fields in (('pieces.csv', pieces_rows, None), ('cuts.csv', cut_rows, None),
                               ('gradual.csv', grad_rows, ['clip_id', 'start', 'end', 'kind', 'src_clip'])):
        with open(os.path.join(sdir, name), 'w', newline='') as f:
            wr = csv.DictWriter(f, fields or list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
    print('tables -> %s' % sdir)


if __name__ == '__main__':
    main()
