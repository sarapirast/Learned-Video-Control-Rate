# Scene analysis (x265)

Detector fitted on train splices: {'hist': 0.2, 'msad_ratio': 2.0, 'fp_ratio': 1.8, 'flash_back': 0.08} (train F1 0.944)

| detector | precision | recall | F1 (test splices) |
|---|---|---|---|
| cut | 0.872 | 0.654 | 0.747 |
| v_hist | 0.625 | 0.673 | 0.648 |
| v_msad | 0.215 | 0.962 | 0.351 |
| v_fp | 0.077 | 0.673 | 0.139 |

Natural GOPs: detected cuts per GOP / share of GOPs with a cut:

- ugc: 0.124 / 0.102
- uvg: 0.000 / 0.000
- xiph_hd: 0.047 / 0.047
- film: 0.196 / 0.175
- archive_org: 0.083 / 0.067
