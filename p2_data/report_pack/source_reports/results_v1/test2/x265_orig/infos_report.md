# GOP information (x265)

GOPs per split: {'parity': np.int64(28), 'test2': np.int64(930)}

STATIC vs constant QP (saving %, % over budget):

|                |   saving |   over |   n |
|:---------------|---------:|-------:|----:|
| ('parity', 30) |    0.858 |  0.357 |  28 |
| ('parity', 38) |    1.163 |  0.5   |  28 |
| ('test2', 30)  |    1.691 |  0.448 | 930 |
| ('test2', 38)  |    1.361 |  0.671 | 930 |

Detected cuts per GOP by family:

| family   |   cuts |   fp_cv |
|:---------|-------:|--------:|
| film     |   0    |   0.496 |
| ugc      |   0.07 |   0.454 |
| xiph_hd  |   0    |   0.1   |
