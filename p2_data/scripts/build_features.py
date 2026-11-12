#!/usr/bin/env python3
"""Build the per-frame feature table, data/v1/<res>/features/frames.parquet (DRAFT format, see
docs/feature-spec-draft.md).

One row per frame of every v1 clip, for full GOPs only, filled from existing outputs:
  manifest.csv, gops.csv, cuts/frames/<clip>.csv, cuts/cut_frames.csv, features/siti.csv,
  features/fp_bits.parquet and features/fp_stats.parquet (scripts/rd_native.py, scripts/fp_stats.py)

First pass (added 2026-11-09; ultrafast constant-QP encode per GOP on P1's frozen settings, slice bits only):
  fp_bits_<enc>_q30 / _q32   first-pass slice bits, enc = x264 | x265, first-pass QP 30 | 32 (the team has not
                             picked 30 vs 32; QP 32 tracks real bits slightly better, docs/rd-native-summary.md)
  fp_bits                    the default = fp_bits_x264_q32 (P1's encoder)
  fps_<enc>_<stat>           richer first-pass stats at QP 32: tex / mv / misc bits, intra / inter / skip blocks

Run in the project env:
  module purge && module load conda/25.11.0 && conda activate /scratch1/aayushso/envs/ee599
  python scripts/build_features.py [--res 320x180]
"""
import argparse
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOP = 30
HIST_T, SCDET_T, HIST_WEAK, SCDET_WEAK = 0.35, 10.0, 0.10, 2.0   # same as cut_labels.py


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--res', default='320x180')
    args = ap.parse_args()
    d = os.path.join(ROOT, 'data', 'v1', args.res)

    man = pd.read_csv(os.path.join(d, 'manifest.csv'))
    gops = pd.read_csv(os.path.join(d, 'gops.csv'))
    siti = pd.read_csv(os.path.join(d, 'features', 'siti.csv'))[['clip_id', 'frame', 'si', 'ti']]
    sig = pd.concat([pd.read_csv(os.path.join(d, 'cuts', 'frames', c + '.csv')).assign(clip_id=c)
                     for c in man.clip_id], ignore_index=True)
    final = pd.read_csv(os.path.join(d, 'cuts', 'cut_frames.csv'))
    final = final[final.final_cut == 1][['clip_id', 'frame']].assign(cut_label=1)

    df = sig.merge(siti, on=['clip_id', 'frame'], how='left')
    df['gop'] = df.frame // GOP
    df['pos_in_gop'] = df.frame % GOP
    df = df.merge(gops[['clip_id', 'gop', 'split', 'group', 'label']].rename(columns={'label': 'gop_label'}),
                  on=['clip_id', 'gop'], how='inner')             # full GOPs only
    df = df.merge(final, on=['clip_id', 'frame'], how='left')
    df['cut_label'] = df.cut_label.fillna(0).astype('int8')
    h, s = df.hist_delta, df.scdet_score
    # Deployable flag: the automatic rule only (no review), what a live encoder could compute.
    df['cut_flag'] = (((s > SCDET_T) & (h > HIST_WEAK)) | ((h > HIST_T) & (s > SCDET_WEAK))).astype('int8')
    # first pass: one column per encoder x first-pass QP, plus the richer stats at QP 32
    fpb = pd.read_parquet(os.path.join(d, 'features', 'fp_bits.parquet'))
    fpb['col'] = 'fp_bits_' + fpb.encoder + '_q' + fpb.fp_qp.astype(str)
    fpw = fpb.pivot_table(index=['clip_id', 'gop', 'frame'], columns='col', values='fp_slice_bits').reset_index()
    fps = pd.read_parquet(os.path.join(d, 'features', 'fp_stats.parquet')).query('fp_qp == 32')
    stats = ['tex', 'mv', 'misc', 'intra_blocks', 'inter_blocks', 'skip_blocks']
    fsw = fps.pivot_table(index=['clip_id', 'gop', 'frame'], columns='encoder', values=stats)
    fsw.columns = ['fps_%s_%s' % (e, st.replace('_blocks', '')) for st, e in fsw.columns]
    fpw = fpw.merge(fsw.reset_index(), on=['clip_id', 'gop', 'frame']).rename(columns={'frame': 'pos_in_gop'})
    n0 = len(df)
    df = df.merge(fpw, on=['clip_id', 'gop', 'pos_in_gop'], how='left', validate='one_to_one')
    assert len(df) == n0
    fp_cols = sorted(c for c in fpw.columns if c.startswith('fp_bits_')) + \
        sorted(c for c in fpw.columns if c.startswith('fps_'))
    missing = int(df[fp_cols].isna().any(axis=1).sum())
    assert missing == 0, '%d frames without first-pass data' % missing
    df['fp_bits'] = df['fp_bits_x264_q32']                         # default definition (see docstring)
    cols = ['clip_id', 'split', 'group', 'gop', 'pos_in_gop', 'frame', 'gop_label',
            'fp_bits', 'si', 'ti', 'hist_delta', 'scdet_score', 'y_mean', 'cut_flag', 'cut_label'] + fp_cols
    df = df[cols].sort_values(['clip_id', 'frame']).reset_index(drop=True)
    for c in ('gop', 'pos_in_gop', 'frame'):
        df[c] = df[c].astype('int32')
    for c in ('fp_bits', 'si', 'ti', 'hist_delta', 'scdet_score', 'y_mean'):
        df[c] = df[c].astype('float32')
    for c in fp_cols:
        df[c] = df[c].astype('float32')
    for c in ('clip_id', 'split', 'group', 'gop_label'):
        df[c] = df[c].astype('category')

    dst = os.path.join(d, 'features', 'frames.parquet')
    df.to_parquet(dst + '.part', index=False)
    os.replace(dst + '.part', dst)
    n_gops = df.groupby(['clip_id', 'gop']).ngroups
    print('wrote %s: %d rows, %d GOPs, %d clips' % (dst, len(df), n_gops, df.clip_id.nunique()))
    agree = (df.cut_flag == df.cut_label).mean()
    print('cut_flag (automatic) vs cut_label (reviewed): %.2f%% of frames agree; '
          'flags %d, labels %d' % (100 * agree, df.cut_flag.sum(), df.cut_label.sum()))


if __name__ == '__main__':
    main()
