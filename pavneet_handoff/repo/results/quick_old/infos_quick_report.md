# GOP information (x265)

GOPs per split: {'test': np.int64(6), 'train': np.int64(8)}

STATIC vs constant QP (saving %, % over budget):

|               |   saving |   over |   n |
|:--------------|---------:|-------:|----:|
| ('test', 30)  |  -20.664 |  1     |   6 |
| ('test', 38)  |   -0.004 |  0.833 |   6 |
| ('train', 30) |    2.943 |  0     |   8 |
| ('train', 38) |    0.646 |  0.625 |   8 |

Detected cuts per GOP by family:

| family   |   cuts |   fp_cv |
|:---------|-------:|--------:|
| splice   |      2 |   0.788 |
| xiph_cif |      0 |   0.176 |
