# GOP information (x265)

GOPs per split: {'test': np.int64(479), 'train': np.int64(1196), 'val': np.int64(386)}

STATIC vs constant QP (saving %, % over budget):

|               |   saving |   over |    n |
|:--------------|---------:|-------:|-----:|
| ('test', 30)  |    1.625 |  0.428 |  479 |
| ('test', 38)  |    1.614 |  0.628 |  479 |
| ('train', 30) |    1.992 |  0.396 | 1196 |
| ('train', 38) |    1.926 |  0.63  | 1196 |
| ('val', 30)   |    2.41  |  0.386 |  386 |
| ('val', 38)   |    2.38  |  0.65  |  386 |

Detected cuts per GOP by family:

| family    |   cuts |   fp_cv |
|:----------|-------:|--------:|
| film      |  0.244 |   0.477 |
| film_long |  0.183 |   0.45  |
| splice    |  1.559 |   1     |
| ugc       |  0.127 |   0.506 |
| xiph_cif  |  0.004 |   0.225 |
| xiph_hd   |  0.054 |   0.25  |
