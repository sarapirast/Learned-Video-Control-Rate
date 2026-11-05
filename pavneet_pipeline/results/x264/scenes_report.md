# Scene analysis (x264)

Detector fitted on train splices: {'hist': 0.2, 'msad_ratio': 2.0, 'fp_ratio': 1.8, 'flash_back': 0.08} (train F1 0.941)

| detector | precision | recall | F1 (test splices) |
|---|---|---|---|
| cut | 0.948 | 0.968 | 0.958 |
| v_hist | 0.920 | 0.979 | 0.948 |
| v_msad | 0.517 | 0.989 | 0.679 |
| v_fp | 0.353 | 0.830 | 0.495 |

Natural GOPs: detected cuts per GOP / share of GOPs with a cut:

- film_long: 0.181 / 0.158
- film: 0.244 / 0.195
- ugc: 0.127 / 0.085
- xiph_hd: 0.054 / 0.054
- xiph_cif: 0.004 / 0.004

Hindsight teacher around cuts (mean QP offset on top of STATIC; negative = more bits):

| frame - cut | -3 | -2 | -1 | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|---|---|---|
| offset | +0.75 | +0.92 | +1.35 | -0.37 | +0.37 | +0.44 | +0.48 | +0.45 | +0.47 |

Search gain over STATIC: GOPs with a cut 22.92 (n=454), without 22.14 (n=1938)
