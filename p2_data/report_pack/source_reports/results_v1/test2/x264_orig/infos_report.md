# GOP information (x264)

GOPs per split: {'parity': np.int64(28), 'test2': np.int64(930)}

STATIC vs constant QP (saving %, % over budget):

|                |   saving |   over |   n |
|:---------------|---------:|-------:|----:|
| ('parity', 30) |   -0.163 |  0.429 |  28 |
| ('parity', 38) |   -0.557 |  0.714 |  28 |
| ('test2', 30)  |    0.722 |  0.529 | 930 |
| ('test2', 38)  |    2.109 |  0.758 | 930 |

Detected cuts per GOP by family:

| family   |   cuts |   fp_cv |
|:---------|-------:|--------:|
| film     |  0     |   0.49  |
| ugc      |  0.072 |   0.47  |
| xiph_hd  |  0     |   0.165 |
