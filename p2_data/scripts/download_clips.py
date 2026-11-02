#!/usr/bin/env python3
"""Download the source material for data/clip_candidates.csv into data/raw/.

Fetches only what the clips use, where the format allows it:
  y4m       (Xiph)          HTTP range request for just the clip's frames -> <clip_id>.y4m
  y4m.xz    (BBB, ED, Sita) streamed and decompressed once per film; only the segments are kept
                            -> <clip_id>.y4m per segment (the full film never touches disk)
  PNG dirs  (Sintel, ToS)   only the segment's frames, checked against the published SHA256SUMS
                            -> <clip_id>/NNNNN.png
  other     (UGC .mkv, UVG .7z)  whole file, resumable -> <clip_id>.<ext>

Every output is written as .part and renamed when complete, so a rerun skips finished clips and
resumes or redoes the rest. data/raw/index.csv records, per clip, the file and the source frame
index of its first frame (decode skips start_frame - first_src_frame frames).

Bulk downloads belong on the transfer nodes (hpc-transfer1/2), not login or compute nodes:
  python3 scripts/download_clips.py --dry-run          # what would be fetched, and how much
  python3 scripts/download_clips.py                    # priority-1 clips
  python3 scripts/download_clips.py --priority 2       # priority 1 and 2
  python3 scripts/download_clips.py --only ed_s00,riverbed
"""
import argparse
import csv
import hashlib
import lzma
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = os.path.join(ROOT, 'data', 'clip_candidates.csv')
CHUNK = 8 << 20
RETRIES = 4
_print_lock = threading.Lock()


def log(*a):
    with _print_lock:
        print(time.strftime('%H:%M:%S'), *a, flush=True)


def urlopen(url, start=None, end=None, method='GET'):
    """urlopen with retries; start/end are an inclusive byte range."""
    headers = {'User-Agent': 'ee599-clip-fetch'}
    if start is not None:
        headers['Range'] = 'bytes=%d-%s' % (start, '' if end is None else end)
    for attempt in range(RETRIES):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=headers, method=method),
                                          timeout=120)
        except (urllib.error.URLError, OSError) as e:
            if attempt == RETRIES - 1 or getattr(e, 'code', 500) in (403, 404, 416):
                raise
            time.sleep(5 * 2 ** attempt)


def content_length(url):
    with urlopen(url, method='HEAD') as f:
        return int(f.headers['Content-Length'])


def copy_stream(src, dst, nbytes=None):
    done = 0
    while nbytes is None or done < nbytes:
        b = src.read(CHUNK if nbytes is None else min(CHUNK, nbytes - done))
        if not b:
            break
        dst.write(b)
        done += len(b)
    return done


# ---- y4m header handling ---------------------------------------------------------------------

def y4m_frame_bytes(header):
    """Payload bytes per frame from a y4m stream header line (without the newline)."""
    w = int(re.search(rb' W(\d+)', header).group(1))
    h = int(re.search(rb' H(\d+)', header).group(1))
    m = re.search(rb' C(\S+)', header)
    cs = m.group(1).decode() if m else '420jpeg'
    depth = 2 if re.search(r'p(9|1\d)', cs) else 1
    planes = {'420': 1.5, '422': 2.0, '444': 3.0, 'mon': 1.0}[cs[:3]]
    return int(w * h * planes) * depth


def y4m_header(url):
    with urlopen(url, 0, 4095) as f:
        head = f.read()
    hdr = head.split(b'\n', 1)[0]
    if not hdr.startswith(b'YUV4MPEG2 '):
        raise ValueError('not a y4m stream: %s' % url)
    return hdr


# ---- jobs ------------------------------------------------------------------------------------

def src_range(clip, limit):
    """[first, last) source frames a clip needs, before decimation."""
    dec = int(clip['decimate']) if clip['decimate'].isdigit() else 1
    first = int(clip['start_frame'])
    n = int(clip['n_frames']) * dec
    if limit:
        n = min(n, limit)
    return first, first + n


class Job:
    """One download: a list of clips that share a URL (only film segments share one)."""

    def __init__(self, kind, url, clips, out, limit):
        self.kind, self.url, self.clips, self.out, self.limit = kind, url, clips, out, limit

    def done_paths(self):
        if self.kind == 'png':
            return [os.path.join(self.out, c['clip_id'], '.complete') for c in self.clips]
        if self.kind in ('y4m', 'y4m.xz'):
            return [os.path.join(self.out, c['clip_id'] + '.y4m') for c in self.clips]
        return [os.path.join(self.out, self.clips[0]['clip_id'] + self.ext())]

    def ext(self):
        name = self.url.rsplit('/', 1)[-1]
        return '.y4m.xz' if name.endswith('.y4m.xz') else os.path.splitext(name)[1]

    def is_done(self):
        return all(os.path.exists(p) for p in self.done_paths())

    def index_rows(self):
        rows = []
        for c in self.clips:
            if self.kind in ('y4m', 'y4m.xz', 'png'):
                first, last = src_range(c, self.limit)
                path = c['clip_id'] + ('/' if self.kind == 'png' else '.y4m')
                kind = 'png_dir' if self.kind == 'png' else 'y4m'
            else:
                first, last = 0, ''
                path, kind = c['clip_id'] + self.ext(), self.ext().lstrip('.')
            rows.append(OrderedDict(clip_id=c['clip_id'], path=path, kind=kind,
                                    first_src_frame=first,
                                    n_src_frames='' if last == '' else last - first))
        return rows

    # -- size estimate for --dry-run
    def estimate(self):
        if self.kind == 'y4m':
            hdr = y4m_header(self.url)
            fb = y4m_frame_bytes(hdr) + 6
            return sum((b - a) * fb for a, b in (src_range(c, self.limit) for c in self.clips))
        if self.kind == 'png':
            return None
        return content_length(self.url)

    def run(self):
        getattr(self, 'run_' + self.kind.replace('.', '_'))()

    # -- Xiph y4m: byte range of the frames we keep
    def run_y4m(self):
        hdr = y4m_header(self.url)
        rec = y4m_frame_bytes(hdr) + 6  # 'FRAME\n' + payload
        total = content_length(self.url)
        for c in self.clips:
            first, last = src_range(c, self.limit)
            nframes = (total - len(hdr) - 1) // rec
            last = min(last, nframes)
            dst = os.path.join(self.out, c['clip_id'] + '.y4m')
            a = len(hdr) + 1 + first * rec
            b = len(hdr) + 1 + last * rec
            with urlopen(self.url, a, b - 1) as f, open(dst + '.part', 'wb') as g:
                if f.status != 206:
                    raise IOError('%s: server ignored the byte range (HTTP %d)' % (self.url, f.status))
                g.write(hdr + b'\n')
                got = copy_stream(f, g, b - a)
            if got != b - a:
                raise IOError('%s: short read %d of %d bytes' % (c['clip_id'], got, b - a))
            check_y4m(dst + '.part', rec, last - first)
            os.rename(dst + '.part', dst)

    # -- xz-compressed films: one streaming pass, keep only the segments
    def run_y4m_xz(self):
        ranges = sorted((src_range(c, self.limit) + (c['clip_id'],) for c in self.clips))
        stop = max(r[1] for r in ranges)
        dec = lzma.LZMADecompressor()
        buf = bytearray()
        hdr = rec = None
        frame = 0
        open_files = {}
        with urlopen(self.url) as f:
            while frame < stop:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                buf += dec.decompress(chunk)
                if hdr is None:
                    nl = buf.find(b'\n')
                    if nl < 0:
                        continue
                    hdr = bytes(buf[:nl])
                    rec = y4m_frame_bytes(hdr) + 6
                    del buf[:nl + 1]
                while len(buf) >= rec and frame < stop:
                    if buf[:6] != b'FRAME\n':
                        raise IOError('%s: bad frame marker at frame %d' % (self.url, frame))
                    for a, b, cid in ranges:
                        if a <= frame < b:
                            if cid not in open_files:
                                p = os.path.join(self.out, cid + '.y4m.part')
                                open_files[cid] = open(p, 'wb')
                                open_files[cid].write(hdr + b'\n')
                            open_files[cid].write(buf[:rec])
                        elif frame == b and cid in open_files:
                            self._finish_xz(open_files.pop(cid), cid, rec, b - a)
                    del buf[:rec]
                    frame += 1
        for a, b, cid in ranges:
            if cid in open_files:
                if frame < b:
                    raise IOError('%s: stream ended at frame %d, segment needs %d' % (cid, frame, b))
                self._finish_xz(open_files.pop(cid), cid, rec, b - a)

    def _finish_xz(self, fh, cid, rec, n):
        fh.close()
        p = os.path.join(self.out, cid + '.y4m')
        check_y4m(p + '.part', rec, n)
        os.rename(p + '.part', p)

    # -- PNG frame directories: only the segment's frames, sha256-checked
    def run_png(self):
        with urlopen(self.url + 'SHA256SUMS.txt') as f:
            sums = [l.split() for l in f.read().decode().splitlines() if l.strip()]
        sums = sorted((name, h) for h, name in sums if name.endswith('.png'))
        for c in self.clips:
            first, last = src_range(c, self.limit)
            d = os.path.join(self.out, c['clip_id'])
            os.makedirs(d, exist_ok=True)
            for k in range(first, min(last, len(sums))):
                name, want = sums[k]
                dst = os.path.join(d, '%05d.png' % (k - first))
                if os.path.exists(dst):
                    continue
                with urlopen(self.url + name) as f:
                    data = f.read()
                if hashlib.sha256(data).hexdigest() != want:
                    raise IOError('%s: sha256 mismatch for %s' % (c['clip_id'], name))
                with open(dst + '.part', 'wb') as g:
                    g.write(data)
                os.rename(dst + '.part', dst)
            with open(os.path.join(d, '.complete'), 'w') as g:
                g.write('%s frames %d..%d\n' % (self.url, first, last - 1))

    # -- anything else: whole file, resumable
    def run_whole(self):
        dst = self.done_paths()[0]
        total = content_length(self.url)
        have = os.path.getsize(dst + '.part') if os.path.exists(dst + '.part') else 0
        if have > total:
            have = 0
        if have < total:
            with urlopen(self.url, have if have else None) as f:
                resume = have and f.status == 206  # else the server sent the whole file again
                with open(dst + '.part', 'ab' if resume else 'wb') as g:
                    copy_stream(f, g)
        size = os.path.getsize(dst + '.part')
        if size != total:
            raise IOError('%s: got %d of %d bytes' % (dst, size, total))
        os.rename(dst + '.part', dst)


def check_y4m(path, rec, n):
    """Size and frame-marker check for a y4m written by this script."""
    with open(path, 'rb') as f:
        hdr = f.readline()
        body = os.path.getsize(path) - len(hdr)
        if body != n * rec:
            raise IOError('%s: %d bytes of frames, expected %d' % (path, body, n * rec))
        for i in (0, n // 2, n - 1):
            f.seek(len(hdr) + i * rec)
            if f.read(6) != b'FRAME\n':
                raise IOError('%s: bad frame marker at frame %d' % (path, i))


def make_jobs(clips, out, limit):
    by_url = OrderedDict()
    for c in clips:
        by_url.setdefault(c['url'], []).append(c)
    jobs = []
    for url, cs in by_url.items():
        if url.endswith('/'):
            kind = 'png'
        elif url.endswith('.y4m.xz'):
            kind = 'y4m.xz'
        elif url.endswith('.y4m'):
            kind = 'y4m'
        else:
            kind = 'whole'
        if kind == 'whole' and len(cs) > 1:
            sys.exit('several clips share %s; give them one clip row' % url)
        jobs.append(Job(kind, url, cs, out, limit))
    return jobs


def write_index(out, jobs):
    path = os.path.join(out, 'index.csv')
    rows = OrderedDict()
    if os.path.exists(path):
        for r in csv.DictReader(open(path)):
            rows[r['clip_id']] = r
    for j in jobs:
        if j.is_done():
            for r in j.index_rows():
                rows[r['clip_id']] = r
    with open(path + '.part', 'w', newline='') as f:
        w = csv.DictWriter(f, ['clip_id', 'path', 'kind', 'first_src_frame', 'n_src_frames'])
        w.writeheader()
        w.writerows(rows.values())
    os.rename(path + '.part', path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--candidates', default=CANDIDATES)
    ap.add_argument('--out', default=os.path.join(ROOT, 'data', 'raw'))
    ap.add_argument('--priority', type=int, default=1, help='include clips with priority <= this')
    ap.add_argument('--only', help='comma-separated clip_ids')
    ap.add_argument('--include-flagged', action='store_true',
                    help='also fetch clips flagged for high frame rate (pending a team decision)')
    ap.add_argument('--workers', type=int, default=4, help='parallel downloads (be gentle: shared node)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--test-frames', type=int, default=0,
                    help='testing only: fetch at most N source frames per range/PNG clip')
    args = ap.parse_args()

    clips = list(csv.DictReader(open(args.candidates)))
    if args.only:
        want = set(args.only.split(','))
        missing = want - {c['clip_id'] for c in clips}
        if missing:
            sys.exit('unknown clip_id: %s' % ', '.join(sorted(missing)))
        clips = [c for c in clips if c['clip_id'] in want]
    else:
        clips = [c for c in clips if int(c['priority']) <= args.priority]
        if not args.include_flagged:
            flagged = [c for c in clips if c['fps_status'] != 'ok']
            clips = [c for c in clips if c['fps_status'] == 'ok']
            if flagged:
                log('skipping %d clips flagged for high frame rate (--include-flagged to fetch them)'
                    % len(flagged))
    os.makedirs(args.out, exist_ok=True)
    jobs = make_jobs(clips, args.out, args.test_frames)
    todo = [j for j in jobs if not j.is_done()]
    log('%d clips, %d downloads, %d already complete' % (len(clips), len(jobs), len(jobs) - len(todo)))

    if args.dry_run:
        total = 0
        for j in todo:
            est = j.estimate()
            total += est or 0
            n = sum(src_range(c, args.test_frames)[1] - src_range(c, args.test_frames)[0] for c in j.clips)
            print('%-8s %-28s %s  %s' % (j.kind, j.clips[0]['clip_id'] + (' +%d' % (len(j.clips) - 1) if len(j.clips) > 1 else ''),
                                         '%8.2f GB' % (est / 1e9) if est else '%5d PNGs' % n, j.url))
        print('total (excluding PNG dirs): %.1f GB' % (total / 1e9))
        return

    failed = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {}
        for j in todo:
            log('start', j.kind, ','.join(c['clip_id'] for c in j.clips)[:60])
            futs[ex.submit(j.run)] = j
        for fut in as_completed(futs):
            j = futs[fut]
            name = ','.join(c['clip_id'] for c in j.clips)[:60]
            try:
                fut.result()
                log('done ', name)
            except Exception as e:
                failed.append(name)
                log('FAIL ', name, '-', e)
    write_index(args.out, jobs)
    log('%d failed%s' % (len(failed), (': ' + '; '.join(failed)) if failed else ''))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
