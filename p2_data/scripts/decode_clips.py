#!/usr/bin/env python3
"""Decode downloaded sources (data/raw/) into fixed-size 8-bit 4:2:0 y4m clips.

  data/v1/<W>x<H>/clips/<clip_id>.y4m   one clip
  data/v1/<W>x<H>/meta/<clip_id>.json   how it was made (merged into manifest.csv by --merge)

Rules (docs/clip-selection.md, "Decode rules"):
  - frame rate: native, no conversion; clips outside 23.976-30 fps are skipped
  - frames: exactly n_frames from clip_candidates.csv, never duplicated or dropped
  - geometry: centre-crop the largest even-sized 16:9 region, then lanczos scale to WxH
  - colour: YUV sources pass through (scaled only, no matrix change), RGB (PNG) sources are
    converted with BT.709, and everything ends up limited range; > 8-bit sources are rounded to
    8 bits without dithering

Steps:
  python3 scripts/decode_clips.py --make-tasks              # freeze the task list, print array size
  sbatch --array=0-<N-1>%20 jobs/decode_v1.sbatch           # one task per clip
  python3 scripts/decode_clips.py --merge                   # manifest.csv from the per-clip JSON

Needs ffmpeg/ffprobe: module load ver/2506 gcc/14.3.0 ffmpeg/7.1.1
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = os.path.join(ROOT, 'data', 'clip_candidates.csv')
RAW = os.path.join(ROOT, 'data', 'raw')
FPS_MIN, FPS_MAX = 23.976, 30.0   # same rule as select_clips.py
SCALE_FLAGS = 'lanczos+accurate_rnd+full_chroma_int'


def run(cmd):
    return subprocess.check_output(cmd, universal_newlines=True, stderr=subprocess.STDOUT)


def probe(path, kind):
    """Width, height, pix_fmt, exact frame rate and colour tags of a raw source."""
    args = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-of', 'json', '-show_entries',
            'stream=width,height,pix_fmt,r_frame_rate,color_range,color_space,color_primaries,color_transfer']
    if kind == 'png_dir':
        path = os.path.join(path, '00000.png')
    s = json.loads(run(args + [path]))['streams'][0]
    return s


def crop_16x9(w, h):
    """Largest centred 16:9 region with even size and offsets (keeps 4:2:0 chroma aligned)."""
    if w * 9 > h * 16:                          # too wide: trim the sides
        cw, ch = (h * 16 // 9) // 2 * 2, h // 2 * 2
    else:                                       # too tall: trim top and bottom
        cw, ch = w // 2 * 2, (w * 9 // 16) // 2 * 2
    return cw, ch, (w - cw) // 2 // 2 * 2, (h - ch) // 2 // 2 * 2


def ffmpeg_command(clip, raw, raw_dir, src, out_w, out_h, fps, skip, dst):
    w, h = src['width'], src['height']
    cw, ch, x, y = crop_16x9(w, h)
    rgb = src['pix_fmt'].startswith(('rgb', 'bgr', 'gbr', 'pal'))
    filters = []
    if skip:
        filters.append('trim=start_frame=%d' % skip)
    if (cw, ch) != (w, h):
        filters.append('crop=%d:%d:%d:%d' % (cw, ch, x, y))
    # sws_dither=none: with a resize, swscale rounds without dither anyway; without one (output size
    # == source size) its default would dither when reducing bit depth.
    scale = 'scale=%d:%d:flags=%s:out_range=tv:sws_dither=none' % (out_w, out_h, SCALE_FLAGS)
    if rgb:
        scale += ':out_color_matrix=bt709'
    # setsar=1: crops a pixel off exact 16:9 (e.g. 1422x800) and would otherwise leave a 6399:6400 SAR
    filters += [scale, 'format=yuv420p', 'setsar=1']
    chain = ','.join(filters)

    rate = '%d/%d' % (fps.numerator, fps.denominator)
    cmd = ['ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'error', '-y']
    if raw['kind'] == 'png_dir':
        cmd += ['-framerate', rate, '-start_number', '0', '-i', os.path.join(raw_dir, raw['path'], '%05d.png')]
    else:
        # -r as an input option: constant-rate timestamps for every stored frame, nothing re-timed
        cmd += ['-r', rate, '-i', os.path.join(raw_dir, raw['path'])]
    cmd += ['-vf', chain, '-fps_mode', 'passthrough', '-frames:v', str(clip['n_frames']),
            '-f', 'yuv4mpegpipe', dst]
    crop = None if (cw, ch) == (w, h) else '%dx%d+%d+%d' % (cw, ch, x, y)
    colour = ('RGB -> YUV BT.709, limited range' if rgb else
              'none (YUV passthrough); range normalised to limited')
    return cmd, chain, crop, colour


def check_y4m(path, w, h, n):
    """Header matches and the file holds exactly n frames."""
    with open(path, 'rb') as f:
        hdr = f.readline().decode()
    m = re.match(r'YUV4MPEG2 .*W(\d+) H(\d+) F(\d+):(\d+)', hdr)
    if not m or (int(m.group(1)), int(m.group(2))) != (w, h):
        raise RuntimeError('bad y4m header: %r' % hdr)
    if ' C' in hdr and not re.search(r' C420(jpeg|mpeg2|paldv)?( |$)', hdr):
        raise RuntimeError('output is not 8-bit 4:2:0: %r' % hdr)
    rec = w * h * 3 // 2 + 6
    body = os.path.getsize(path) - len(hdr.encode())
    if body % rec or body // rec != n:
        raise RuntimeError('%s holds %.2f frames, expected %d' % (path, body / rec, n))
    return Fraction(int(m.group(3)), int(m.group(4))), hdr.strip()


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def decode(clip_id, args):
    clip = next(c for c in csv.DictReader(open(args.candidates)) if c['clip_id'] == clip_id)
    clip['n_frames'] = int(clip['n_frames'])
    out_dir = os.path.join(args.out, 'clips')
    meta_dir = os.path.join(args.out, 'meta')
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(meta_dir, exist_ok=True)
    dst = os.path.join(out_dir, clip_id + '.y4m')
    meta_path = os.path.join(meta_dir, clip_id + '.json')
    if os.path.exists(dst) and os.path.exists(meta_path) and not args.force:
        print('%s: already decoded, skipping' % clip_id)
        return

    if clip['fps_status'] != 'ok':
        raise RuntimeError('%s is flagged (%s fps); not decoding until the team decides'
                           % (clip_id, clip['src_fps']))
    raw = {r['clip_id']: r for r in csv.DictReader(open(args.index))}.get(clip_id)
    if raw is None:
        raise RuntimeError('%s is not in %s (not downloaded yet?)' % (clip_id, args.index))
    if raw['kind'] == '7z':
        raise RuntimeError('%s: 7z (UVG) sources are not handled yet' % clip_id)
    # Range and PNG downloads hold exactly the clip's source frames.
    if raw['n_src_frames'] and int(raw['n_src_frames']) != clip['n_frames'] * int(clip['decimate']):
        raise RuntimeError('%s: raw has %s frames, clip needs %d' % (clip_id, raw['n_src_frames'],
                                                                      clip['n_frames']))

    src = probe(os.path.join(args.raw, raw['path']), raw['kind'])
    if raw['kind'] == 'png_dir':
        fps = Fraction(clip['src_fps']).limit_denominator(1001)
    else:
        fps = Fraction(src['r_frame_rate'])
    if not FPS_MIN - 0.01 <= float(fps) <= FPS_MAX + 0.01:
        raise RuntimeError('%s: source is %.3f fps, outside %g-%g' % (clip_id, fps, FPS_MIN, FPS_MAX))
    if abs(float(fps) - float(clip['src_fps'])) > 0.01 * float(fps):
        raise RuntimeError('%s: source is %.3f fps but the candidate list says %s'
                           % (clip_id, fps, clip['src_fps']))
    skip = int(clip['start_frame']) - int(raw['first_src_frame'])

    out_w, out_h = args.width, args.height
    cmd, chain, crop, colour = ffmpeg_command(clip, raw, args.raw, src, out_w, out_h, fps, skip,
                                               dst + '.part')
    t0 = time.time()
    subprocess.check_call(cmd)
    out_fps, header = check_y4m(dst + '.part', out_w, out_h, clip['n_frames'])
    if out_fps != fps:
        raise RuntimeError('%s: output header fps %s, source %s' % (clip_id, out_fps, fps))

    meta = dict(
        clip_id=clip_id, split=clip['split'], group=clip['group'], source=clip['source'],
        path=os.path.relpath(dst, args.out), width=out_w, height=out_h,
        fps='%d/%d' % (fps.numerator, fps.denominator), n_frames=clip['n_frames'],
        src_path=raw['path'], src_size='%dx%d' % (src['width'], src['height']),
        src_pix_fmt=src['pix_fmt'], src_start_frame=int(clip['start_frame']),
        src_color_range=src.get('color_range', 'unknown'),
        src_color_space=src.get('color_space', 'unknown'),
        src_color_primaries=src.get('color_primaries', 'unknown'),
        crop=crop or 'none', colour_conversion=colour,
        bit_depth='8-bit source' if not re.search(r'p(9|1\d)', src['pix_fmt'])
        else 'rounded to 8-bit, no dither',
        filter_chain=chain, y4m_header=header,
        ffmpeg=run(['ffmpeg', '-version']).splitlines()[0],
        md5=md5(dst + '.part'), decode_seconds=round(time.time() - t0, 1),
        decoded_at=time.strftime('%Y-%m-%d %H:%M:%S'))
    os.rename(dst + '.part', dst)
    with open(meta_path + '.part', 'w') as f:
        json.dump(meta, f, indent=1)
    os.rename(meta_path + '.part', meta_path)
    print('%s: %d frames %s @ %s fps, crop %s, %s (%.1fs)' % (
        clip_id, clip['n_frames'], '%dx%d' % (out_w, out_h), meta['fps'], meta['crop'],
        colour.split(';')[0], meta['decode_seconds']))


def make_tasks(args):
    """Freeze the list of decodable clips so array indices can't shift under a running job."""
    raw = {r['clip_id'] for r in csv.DictReader(open(args.index))} if os.path.exists(args.index) else set()
    tasks, skipped = [], []
    for c in csv.DictReader(open(args.candidates)):
        if c['fps_status'] != 'ok':
            skipped.append((c['clip_id'], 'flagged: %s fps (pending team decision)' % c['src_fps']))
        elif c['clip_id'] not in raw:
            skipped.append((c['clip_id'], 'not downloaded'))
        else:
            tasks.append(c['clip_id'])
    os.makedirs(args.out, exist_ok=True)
    with open(args.tasks, 'w') as f:
        f.writelines(t + '\n' for t in tasks)
    with open(os.path.join(args.out, 'skipped.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['clip_id', 'reason'])
        w.writerows(skipped)
    print('%d tasks -> %s' % (len(tasks), args.tasks))
    print('%d skipped -> %s' % (len(skipped), os.path.join(args.out, 'skipped.csv')))
    if tasks:
        print('submit: sbatch --array=0-%d%%20 jobs/decode_v1.sbatch' % (len(tasks) - 1))


def merge(args):
    meta_dir = os.path.join(args.out, 'meta')
    rows = [json.load(open(os.path.join(meta_dir, f)))
            for f in sorted(os.listdir(meta_dir)) if f.endswith('.json')]
    path = os.path.join(args.out, 'manifest.csv')
    with open(path + '.part', 'w', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    os.rename(path + '.part', path)
    print('%d clips -> %s' % (len(rows), path))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--res', default='320x180', help='output WxH (default: the pilot\'s 320x180)')
    ap.add_argument('--candidates', default=CANDIDATES)
    ap.add_argument('--index', default=os.path.join(RAW, 'index.csv'))
    ap.add_argument('--tasks', help='task list (default data/v1/<res>/tasks.txt)')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--make-tasks', action='store_true')
    g.add_argument('--task-index', type=int, help='decode line N (0-based) of the task list')
    g.add_argument('--clip', help='decode one clip by id')
    g.add_argument('--merge', action='store_true')
    ap.add_argument('--force', action='store_true', help='redo clips that are already decoded')
    ap.add_argument('--raw', default=RAW, help='raw download directory (testing)')
    ap.add_argument('--out', help='output directory (default data/v1/<res>; testing)')
    args = ap.parse_args()

    args.width, args.height = map(int, args.res.lower().split('x'))
    if args.width % 2 or args.height % 2 or args.width * 9 != args.height * 16:
        sys.exit('--res must be even and 16:9, e.g. 320x180')
    args.out = args.out or os.path.join(ROOT, 'data', 'v1', '%dx%d' % (args.width, args.height))
    args.tasks = args.tasks or os.path.join(args.out, 'tasks.txt')

    if args.make_tasks:
        make_tasks(args)
    elif args.merge:
        merge(args)
    else:
        clip_id = args.clip or open(args.tasks).read().split()[args.task_index]
        try:
            decode(clip_id, args)
        except (RuntimeError, subprocess.CalledProcessError) as e:
            out = getattr(e, 'output', None)
            sys.exit('FAILED %s: %s%s' % (clip_id, e, ('\n' + out) if out else ''))


if __name__ == '__main__':
    main()
