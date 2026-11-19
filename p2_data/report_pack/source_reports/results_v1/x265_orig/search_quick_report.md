# Hindsight search (x265)

|               |   n |   static |   best |   gain |   saving |   over |
|:--------------|----:|---------:|-------:|-------:|---------:|-------:|
| ('train', 30) |   8 |  -19.221 | -5.849 | 13.372 |    2.517 |  0.25  |
| ('train', 38) |   8 |  -28.361 | -2.577 | 25.784 |    1.671 |  0.375 |

By family (all splits):

| family   |   n |   gain |    best |
|:---------|----:|-------:|--------:|
| film     |   2 | 44.106 | -31.604 |
| splice   |   4 | 39.79  | -15.413 |
| ugc      |   8 |  7.367 |   5.029 |
| xiph_hd  |   2 |  3.473 |   8.612 |

Convergence: mean best score after n encodes (both seeds, per seed budget):

10: -17.038 | 25: -11.827
