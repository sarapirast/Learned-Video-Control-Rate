# GOP information (x264)

GOPs per split: {'test': np.int64(6), 'train': np.int64(8), 'val': np.int64(6)}

STATIC vs constant QP (saving %, % over budget):

|               |   saving |   over |   n |
|:--------------|---------:|-------:|----:|
| ('test', 30)  |    0.455 |  0.167 |   6 |
| ('test', 38)  |    1.176 |  0.5   |   6 |
| ('train', 30) |   -3.316 |  0.375 |   8 |
| ('train', 38) |   -6.143 |  0.625 |   8 |
| ('val', 30)   |   -0.513 |  0.333 |   6 |
| ('val', 38)   |    3.139 |  1     |   6 |

Detected cuts per GOP by family:

| family      |   cuts |   fp_cv |
|:------------|-------:|--------:|
| archive_org |      0 |   0.965 |
| film        |      0 |   0.568 |
| splice      |      1 |   0.802 |
| ugc         |      0 |   0.228 |
| uvg         |      0 |   0.116 |
| xiph_hd     |      0 |   0.531 |
