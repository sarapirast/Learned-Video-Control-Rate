# GOP information (x264)

GOPs per split: {'test': np.int64(265), 'train': np.int64(625), 'val': np.int64(152)}

STATIC vs constant QP (saving %, % over budget):

|               |   saving |   over |   n |
|:--------------|---------:|-------:|----:|
| ('test', 30)  |    0.805 |  0.37  | 265 |
| ('test', 38)  |    1.484 |  0.668 | 265 |
| ('train', 30) |    1.307 |  0.483 | 625 |
| ('train', 38) |    1.375 |  0.728 | 625 |
| ('val', 30)   |    0.798 |  0.382 | 152 |
| ('val', 38)   |    1.546 |  0.684 | 152 |

Detected cuts per GOP by family:

| family      |   cuts |   fp_cv |
|:------------|-------:|--------:|
| archive_org |  0.1   |   0.427 |
| film        |  0.121 |   0.381 |
| splice      |  0.533 |   0.896 |
| ugc         |  0.081 |   0.546 |
| uvg         |  0     |   0.22  |
| xiph_hd     |  0.021 |   0.212 |
