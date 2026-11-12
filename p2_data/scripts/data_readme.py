#!/usr/bin/env python3
"""Generate the data README for data v1 (docs/data-v1-README.md) from the data files.

Every number in the README comes from these inputs, so rerun this whenever they change:
  data/v1/<res>/manifest.csv, gops.csv, features/siti.csv, cuts/cut_frames.csv
  data/clip_candidates.csv, data/v1/<res>/skipped.csv, config/cut_review_v1.csv,
  config/exclude_clips.csv, data/meta/ugc_ATTRIBUTION.txt
and, for the encoder-derived section (needs pandas + pyarrow, i.e. the project env):
  rd/rd_native.parquet, rd/rd_frames.parquet, rd/static_rd.parquet, features/fp_bits.parquet,
  features/fp_stats.parquet, features/frames.parquet, budgets.csv

  /scratch1/aayushso/envs/ee599/bin/python -I scripts/data_readme.py [--res 320x180]
"""
import argparse
import csv
import os
import re
import time
from collections import Counter, defaultdict
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLITS = ('train', 'val', 'test')


def rd(path):
    return list(csv.DictReader(open(path, encoding='utf-8')))


def table(header, rows):
    out = ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


def quantiles(v, qs=(0.1, 0.5, 0.9)):
    s = sorted(v)
    return [s[min(len(s) - 1, int(q * len(s)))] for q in qs]


def binned(values_by_split, edges):
    """Counts per bin per split; edges are the upper bounds, last bin is open-ended."""
    labels = ['< %g' % edges[0]] + ['%g-%g' % (a, b) for a, b in zip(edges, edges[1:])] + ['>= %g' % edges[-1]]
    rows = []
    for i, lab in enumerate(labels):
        lo = edges[i - 1] if i > 0 else float('-inf')
        hi = edges[i] if i < len(edges) else float('inf')
        rows.append([lab] + [sum(1 for v in values_by_split[s] if lo <= v < hi) for s in SPLITS])
    return rows


def encoder_section(data, w):
    """Encoder-derived files (P1's frozen settings, both encoders). Needs pandas; skipped with a note otherwise."""
    w('## Encoder-derived data (P1 frozen settings, x264 and x265)\n')
    try:
        import numpy as np
        import pandas as pd
    except ImportError:
        w('(Not generated: run this script with the project env to fill this section.)\n')
        return
    p = lambda *a: os.path.join(data, *a)  # noqa: E731
    rdn = pd.read_parquet(p('rd', 'rd_native.parquet'))
    rdf = pd.read_parquet(p('rd', 'rd_frames.parquet'), columns=['encoder', 'kind'])
    st = pd.read_parquet(p('rd', 'static_rd.parquet'))
    fpb = pd.read_parquet(p('features', 'fp_bits.parquet'))
    fps = pd.read_parquet(p('features', 'fp_stats.parquet'), columns=['encoder'])
    frm = pd.read_parquet(p('features', 'frames.parquet'))
    bud = pd.read_csv(p('budgets.csv'))
    w('Settings: `docs/Ahhana_update.txt` (x264 module 20250608, preset medium, IPPP, keyint 30, AQ / mb-tree / '
      'psy off, 1 thread; x265 4.1 with the same choices). Bits are **slice (picture) bits**; stream headers are '
      'stored separately. Scripts: `scripts/rd_native.py`, `scripts/fp_stats.py`, `scripts/static_rd.py`, '
      '`scripts/budgets_v1.py`, `scripts/build_features.py`.\n')
    w(table(['file', 'rows', 'contents'], [
        ['`rd/rd_native.parquet`', len(rdn), 'per GOP x encoder x QP %d-%d: constant-QP slice/header bits, I-frame '
         'bits, PSNR (Y and 6:1:1 YUV, mean of frames and from mean MSE)' % (rdn.qp.min(), rdn.qp.max())],
        ['`rd/rd_frames.parquet`', len(rdf), 'per frame of those encodes (kind cqp) and of the first passes (kind fp): '
         'slice/header bits, MSE per plane'],
        ['`rd/static_rd.parquet`', len(st), "the pilot's STATIC pattern (I q-6, P1-9 q-3, P10-29 q+3) at every base q "
         '%d-%d, per GOP x encoder' % (st.base_q.min(), st.base_q.max())],
        ['`features/fp_bits.parquet`', len(fpb), 'first-pass slice bits per frame (ultrafast, QP %s)' %
         ' and '.join(str(q) for q in sorted(fpb.fp_qp.unique()))],
        ['`features/fp_stats.parquet`', len(fps), 'richer first-pass stats per frame (tex / mv / misc bits, intra / '
         'inter / skip blocks)'],
        ['`features/frames.parquet`', len(frm), 'per-frame feature table; first-pass columns merged 2026-11-09 '
         '(`fp_bits` = x264 at QP 32; all variants as `fp_bits_<enc>_q<qp>`, stats as `fps_<enc>_<stat>`)'],
        ['`budgets.csv`', len(bud), 'budgets per GOP x encoder x level, hindsight q_fit, causal base-QP estimates'],
    ]) + '\n')
    rows = []
    for enc, d in rdn.groupby('encoder'):
        d = d.sort_values(['clip_id', 'gop', 'qp'])
        steps = (d.groupby(['clip_id', 'gop']).slice_bits.diff() > 0).sum()
        med = d.groupby('qp').slice_bits.median()
        rows.append([enc, d.groupby(['clip_id', 'gop']).ngroups] + ['%.0f' % (med[q] / 1000) for q in (24, 30, 36, 42)]
                    + ['%d of %d' % (steps, len(d) - d.groupby(['clip_id', 'gop']).ngroups)])
    w('Constant-QP curves: median GOP slice bits (kbit) and QP steps where bits went UP with QP (should be 0):\n')
    w(table(['encoder', 'GOPs', 'QP 24', 'QP 30', 'QP 36', 'QP 42', 'non-monotonic steps'], rows) + '\n')
    rows = []
    for (enc, lv), d in bud.groupby(['encoder', 'level_q0']):
        r = d.budget_over_own_cqp
        rows.append([enc, lv, '%.0f' % (d.budget_bits.median() / 1000), '%.2f' % r.quantile(.1), '%.2f' % r.median(),
                     '%.2f' % r.quantile(.9), '%.1f%%' % (100 * d.q_fit_flag.notna().mean())])
    w('Budgets (`budgets.csv`): clip-level, the clip\'s mean constant-QP slice bits per GOP at level q0; never the '
      'GOP\'s own spend. Ratio = budget / the GOP\'s own constant-QP spend at q0. Flagged = the hindsight q_fit falls '
      'outside the curve (QP 18-50) and is clipped:\n')
    w(table(['encoder', 'level q0', 'median budget (kbit)', 'ratio p10', 'ratio median', 'ratio p90', 'flagged'],
            rows) + '\n')
    rows = []
    for (enc, q), d in fpb.groupby(['encoder', 'fp_qp']):
        g = d.groupby(['clip_id', 'gop']).fp_slice_bits.sum().rename('fp')
        c = rdn[(rdn.encoder == enc) & (rdn.qp == q)].set_index(['clip_id', 'gop']).slice_bits
        j = pd.concat([g, c], axis=1, join='inner')
        rows.append([enc, q, '%.3f' % np.corrcoef(np.log(j.fp), np.log(j.slice_bits))[0, 1],
                     '%.2f' % (j.fp / j.slice_bits).median()])
    w('First pass vs the real encode at the same constant QP, per GOP:\n')
    w(table(['encoder', 'first-pass QP', 'log-log correlation', 'median first-pass / real bits'], rows) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--res', default='320x180')
    args = ap.parse_args()
    data = os.path.join(ROOT, 'data', 'v1', args.res)

    man = rd(os.path.join(data, 'manifest.csv'))
    gops = rd(os.path.join(data, 'gops.csv'))
    siti = rd(os.path.join(data, 'features', 'siti.csv'))
    cand = {r['clip_id']: r for r in rd(os.path.join(ROOT, 'data', 'clip_candidates.csv'))}
    skipped = rd(os.path.join(data, 'skipped.csv'))
    review = rd(os.path.join(ROOT, 'config', 'cut_review_v1.csv'))
    excluded = rd(os.path.join(ROOT, 'config', 'exclude_clips.csv'))
    cuts = rd(os.path.join(data, 'cuts', 'cut_frames.csv'))
    ids = {m['clip_id'] for m in man}
    L = []
    w = L.append

    w('# Data v1 (%s)\n' % args.res)
    w('**Status: frozen 2026-11-03.** Do not change the clips, splits or labels; changes go into a new version.\n')
    w('Generated by `scripts/data_readme.py` on %s. Every number below comes from the data files; '
      'rerun the script after any change. Rules and the evidence behind them: `docs/clip-selection.md`.\n'
      % time.strftime('%Y-%m-%d'))

    # ---- overview
    frames = sum(int(m['n_frames']) for m in man)
    w('## Overview\n')
    w('- %d clips, %d frames, %d full 30-frame GOPs (partial GOPs at clip ends are not used).' % (
        len(man), frames, len(gops)))
    w('- Format: `clips/<clip_id>.y4m`, 8-bit 4:2:0, %s, native frame rate, limited range.' % args.res)
    w('- Splits are by **group** (a film, a shoot or a YouTube uploader), never by clip or GOP. '
      'Resample by `group` for confidence intervals.')
    w('- Files: `manifest.csv` (one row per clip: source, crop, colour handling, fps, MD5), '
      '`gops.csv` (one row per GOP: label, cut frames), `features/siti.csv` (per frame), '
      '`cuts/` (cut signals and frames).\n')

    rows = []
    for s in SPLITS:
        ms = [m for m in man if m['split'] == s]
        rows.append([s, len(ms), len({m['group'] for m in ms}), sum(int(m['n_frames']) for m in ms),
                     sum(1 for g in gops if g['split'] == s)])
    rows.append(['**total**', len(man), len({m['group'] for m in man}), frames, len(gops)])
    w(table(['split', 'clips', 'groups', 'frames', 'GOPs'], rows) + '\n')

    # ---- sources
    w('## Sources\n')
    src = defaultdict(Counter)
    for m in man:
        src[m['source']][m['split']] += 1
    w(table(['source', 'train', 'val', 'test', 'total'],
            [[k] + [src[k][s] for s in SPLITS] + [sum(src[k].values())] for k in sorted(src)]) + '\n')
    fps = Counter('%.3f' % float(Fraction(m['fps'])) for m in man)
    w('Frame rates (clips): ' + ', '.join('%s fps: %d' % kv for kv in sorted(fps.items())) + '.\n')
    conv = Counter(m['colour_conversion'] for m in man)
    w('Colour handling (clips): ' + '; '.join('%s: %d' % kv for kv in sorted(conv.items())) + '.\n')

    # ---- cut labels
    w('## Scene-cut labels\n')
    lab = defaultdict(Counter)
    for g in gops:
        lab[g['split']][g['label']] += 1
    rows = []
    for s in SPLITS:
        cg = [g for g in gops if g['split'] == s and g['label'] == 'cut']
        rows.append([s, lab[s]['stable'], lab[s]['cut'], lab[s]['gradual'],
                     len({g['clip_id'] for g in cg}), len({g['group'] for g in cg})])
    w(table(['split', 'stable', 'cut', 'gradual', 'clips with cut GOPs', 'groups with cut GOPs'], rows) + '\n')
    test_cut = Counter(g['group'] for g in gops if g['split'] == 'test' and g['label'] == 'cut')
    w('Test cut GOPs by group: ' + ', '.join('%s %d' % kv for kv in test_cut.most_common()) + '.\n')
    n_final = sum(1 for c in cuts if c['final_cut'] == '1')
    at_start = sum(1 for g in gops if g['cut_at_gop_start'] == '1')
    w('- %d cut frames in total. A GOP is `cut` if a cut falls inside it (not on its first frame); '
      '%d GOPs have a cut exactly on their first frame and are not labelled `cut`.' % (n_final, at_start))
    rv = [r for r in review if r['clip_id'] in ids]
    both = [r for r in rv if r['human_verdict']]
    agree = sum(1 for r in both if r['human_verdict'] == r['claude_verdict'])
    cut_agree = sum(1 for r in both if (r['human_verdict'] == 'cut') == (r['claude_verdict'] == 'cut'))
    w('- Detectors: luma-histogram change (64 bins, > 0.35) and ffmpeg `scdet` (> 10). Every frame where '
      'only one fired, or where the rule rejected a detection, was reviewed by eye: %d review verdicts '
      'for clips in v1 (%s).' % (len(rv), ', '.join('%s %d' % kv for kv in sorted(Counter(r['verdict'] for r in rv).items()))))
    if both:
        w('- %d of those were reviewed independently by a second (human) reviewer: %d/%d exact agreement, '
          '%d/%d on cut vs not-cut. Disagreements were settled with wider context.\n' % (
              len(both), agree, len(both), cut_agree, len(both)))

    # ---- complexity
    w('## Complexity (SI/TI, ITU-T P.910)\n')
    w('Per-frame SI and TI from ffmpeg `siti` on the decoded clips (full-range scaled, border excluded). '
      'GOP values are means over the GOP\'s 30 frames (TI over frames 1-29 of the GOP).\n')
    fr = defaultdict(dict)
    for r in siti:
        fr[r['clip_id']][int(r['frame'])] = (float(r['si']), float(r['ti']))
    gsi, gti = defaultdict(list), defaultdict(list)
    for g in gops:
        a = int(g['start_frame'])
        vals = [fr[g['clip_id']][f] for f in range(a, a + 30)]
        gsi[g['split']].append(sum(v[0] for v in vals) / 30)
        gti[g['split']].append(sum(v[1] for v in vals[1:]) / 29)
    rows = []
    for s in SPLITS:
        rows.append([s] + ['%.1f' % x for x in quantiles(gsi[s])] + ['%.1f' % x for x in quantiles(gti[s])])
    w(table(['split', 'SI p10', 'SI median', 'SI p90', 'TI p10', 'TI median', 'TI p90'], rows) + '\n')
    w('GOP-mean SI, number of GOPs per bin:\n')
    w(table(['SI', 'train', 'val', 'test'], binned(gsi, [40, 60, 80, 100, 120, 150])) + '\n')
    w('GOP-mean TI, number of GOPs per bin:\n')
    w(table(['TI', 'train', 'val', 'test'], binned(gti, [2, 5, 10, 20, 30])) + '\n')

    encoder_section(data, w)

    # ---- licences
    w('## Licences and attribution\n')
    lic = Counter('spliced from v1 train clips (their licences apply)' if m['source'] == 'spliced'
                  else cand[m['clip_id']]['licence'].split(' (')[0] for m in man)
    w(table(['licence', 'clips'], sorted(lic.items(), key=lambda kv: -kv[1])) + '\n')
    w('- NTIA/VQEG clips are for research only; Netflix clips (not in v1 yet) are NoDerivatives. '
      'Don\'t publish derived YUV of either.')
    w('- Films: Big Buck Bunny, Sintel, Tears of Steel (c) Blender Foundation, CC BY 3.0; Elephants Dream '
      '(c) Blender Foundation / Netherlands Media Art Institute, CC BY 2.5; Sita Sings the Blues by Nina Paley, CC0.')
    att = {}
    path = os.path.join(ROOT, 'data', 'meta', 'ugc_ATTRIBUTION.txt')
    for line in open(path, encoding='utf-8'):
        m = re.match(r'^(\S+) is (.*)$', line.strip())
        if m:
            att[m.group(1)] = m.group(2)
    ugc = sorted(m['clip_id'] for m in man if m['source'] == 'youtube-ugc')
    w('- YouTube UGC clips (CC BY 4.0), attribution as published with the dataset:\n')
    for c in ugc:
        w('  - `%s` is %s' % (c, att.get(c, '(attribution missing)')))
    w('')

    # ---- not in v1
    w('## Not in v1\n')
    why = Counter(r['reason'].split(':')[0] for r in skipped)
    w('- %d candidates are not decoded: %s. See `skipped.csv`.' % (
        len(skipped), ', '.join('%s %d' % kv for kv in sorted(why.items()))))
    for e in excluded:
        w('- Excluded by decision: `%s`: %s (%s).' % (e['clip_id'], e['reason'], e['decided']))
    w('')

    w('## Known caveats\n')
    w('- The histogram cut detector re-implements the pilot\'s (threshold 0.35); its bin count still needs '
      'checking against the pilot code.')
    w('- Dissolve detection is untested; dissolves found so far came from the visual reviews.')
    w('- Lanczos scaling rings at sharp edges: 0.02-0.24% of pixels fall outside 16-235 (left unclipped).')
    w('- Test cut GOPs are concentrated in two films; see the group breakdown above.')

    dst = os.path.join(ROOT, 'docs', 'data-v1-README.md')
    with open(dst + '.part', 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    os.rename(dst + '.part', dst)
    print('wrote %s (%d lines)' % (dst, len(L)))


if __name__ == '__main__':
    main()
