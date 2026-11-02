#!/usr/bin/env python3
"""Build the per-frame feature table, data/v1/<res>/features/frames.parquet (DRAFT format, see
docs/feature-spec-draft.md).

One row per frame of every v1 clip, for full GOPs only. fp_bits (first-pass bits) is empty until the
encoder is decided; everything else is filled from existing outputs:
  manifest.csv, gops.csv, cuts/frames/<clip>.csv, cuts/cut_frames.csv, features/siti.csv

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
    df['fp_bits'] = np.nan                                         # filled once the encoder is decided
    cols = ['clip_id', 'split', 'group', 'gop', 'pos_in_gop', 'frame', 'gop_label',
            'fp_bits', 'si', 'ti', 'hist_delta', 'scdet_score', 'y_mean', 'cut_flag', 'cut_label']
    df = df[cols].sort_values(['clip_id', 'frame']).reset_index(drop=True)
    for c in ('gop', 'pos_in_gop', 'frame'):
        df[c] = df[c].astype('int32')
    for c in ('fp_bits', 'si', 'ti', 'hist_delta', 'scdet_score', 'y_mean'):
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
