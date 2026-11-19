# GOP information (x265)

GOPs per split: {'test': np.int64(6), 'train': np.int64(8), 'val': np.int64(6)}

STATIC vs constant QP (saving %, % over budget):

|               |   saving |   over |   n |
|:--------------|---------:|-------:|----:|
| ('test', 30)  |    0.15  |  0     |   6 |
| ('test', 38)  |    0.962 |  0.5   |   6 |
| ('train', 30) |   -4.414 |  0.25  |   8 |
| ('train', 38) |   -7.133 |  0.625 |   8 |
| ('val', 30)   |    0.666 |  0.333 |   6 |
| ('val', 38)   |    3.747 |  0.667 |   6 |

Detected cuts per GOP by family:

| family      |   cuts |   fp_cv |
|:------------|-------:|--------:|
| archive_org |      0 |   0.995 |
| film        |      0 |   0.558 |
| splice      |      1 |   0.769 |
| ugc         |      0 |   0.275 |
| uvg         |      0 |   0.113 |
| xiph_hd     |      0 |   0.472 |
