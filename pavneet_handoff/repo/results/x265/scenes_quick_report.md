# Scene analysis (x265)

Detector fitted on train splices: {'hist': 0.15, 'msad_ratio': 2.0, 'fp_ratio': 1.8, 'flash_back': 0.08} (train F1 1.000)

| detector | precision | recall | F1 (test splices) |
|---|---|---|---|
| cut | 1.000 | 1.000 | 1.000 |
| v_hist | 1.000 | 1.000 | 1.000 |
| v_msad | 1.000 | 1.000 | 1.000 |
| v_fp | 0.667 | 0.667 | 0.667 |

Natural GOPs: detected cuts per GOP / share of GOPs with a cut:

- film_long: 0.500 / 0.500
- ugc: 0.300 / 0.100
- xiph_cif: 0.000 / 0.000

Hindsight teacher around cuts (mean QP offset on top of STATIC; negative = more bits):

| frame - cut | -3 | -2 | -1 | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|---|---|---|
| offset | -0.25 | -0.06 | -0.25 | -0.12 | +0.12 | -0.25 | +0.00 | +0.50 | +0.50 |

Search gain over STATIC: GOPs with a cut 13.49 (n=8), without 10.41 (n=8)
