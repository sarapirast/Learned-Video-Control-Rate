# Hindsight search (x265)

|               |   n |   static |    best |   gain |   saving |   over |
|:--------------|----:|---------:|--------:|-------:|---------:|-------:|
| ('test', 30)  |   6 |  -61.058 | -16.394 | 44.664 |  -13.486 |  0.333 |
| ('test', 38)  |   6 |  -12.078 |   4.58  | 16.658 |    4.743 |  0.167 |
| ('train', 30) |   8 |    2.943 |   6.589 |  3.646 |    6.589 |  0     |
| ('train', 38) |   8 |   -4.628 |   5.013 |  9.641 |    5.045 |  0.125 |

By family (all splits):

| family   |   n |   gain |   best |
|:---------|----:|-------:|-------:|
| splice   |   4 |  7.059 |  5.68  |
| xiph_cif |  24 | 18.583 | -0.033 |

Convergence: mean best score after n encodes (both seeds, per seed budget):

10: -9.355 | 25: -6.019
