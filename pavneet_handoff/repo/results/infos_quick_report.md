# GOP information (x265)

GOPs per split: {'test': np.int64(8), 'train': np.int64(8), 'val': np.int64(8)}

STATIC vs constant QP (saving %, % over budget):

|               |   saving |   over |   n |
|:--------------|---------:|-------:|----:|
| ('test', 30)  |    3.084 |  0.5   |   8 |
| ('test', 38)  |    3.093 |  0.875 |   8 |
| ('train', 30) |   -1.799 |  0.25  |   8 |
| ('train', 38) |    0.136 |  0.375 |   8 |
| ('val', 30)   |    1.51  |  0.5   |   8 |
| ('val', 38)   |    0.442 |  0.75  |   8 |

Detected cuts per GOP by family:

| family    |   cuts |   fp_cv |
|:----------|-------:|--------:|
| film_long |  0.333 |   0.439 |
| splice    |  1.5   |   0.965 |
| ugc       |  0.2   |   0.472 |
| xiph_cif  |  0     |   0.263 |
