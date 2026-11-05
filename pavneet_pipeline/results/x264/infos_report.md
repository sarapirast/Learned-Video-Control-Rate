# GOP information (x264)

GOPs per split: {'test': np.int64(479), 'train': np.int64(1196), 'val': np.int64(386)}

STATIC vs constant QP (saving %, % over budget):

|               |   saving |   over |    n |
|:--------------|---------:|-------:|-----:|
| ('test', 30)  |    0.903 |  0.503 |  479 |
| ('test', 38)  |    1.661 |  0.693 |  479 |
| ('train', 30) |    1.156 |  0.485 | 1196 |
| ('train', 38) |    2.156 |  0.718 | 1196 |
| ('val', 30)   |    1.077 |  0.466 |  386 |
| ('val', 38)   |    2.457 |  0.712 |  386 |

Detected cuts per GOP by family:

| family    |   cuts |   fp_cv |
|:----------|-------:|--------:|
| film      |  0.244 |   0.491 |
| film_long |  0.181 |   0.457 |
| splice    |  1.559 |   1.056 |
| ugc       |  0.127 |   0.542 |
| xiph_cif  |  0.004 |   0.221 |
| xiph_hd   |  0.054 |   0.239 |
