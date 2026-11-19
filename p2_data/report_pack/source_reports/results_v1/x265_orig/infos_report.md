# GOP information (x265)

GOPs per split: {'test': np.int64(265), 'train': np.int64(625), 'val': np.int64(152)}

STATIC vs constant QP (saving %, % over budget):

|               |   saving |   over |   n |
|:--------------|---------:|-------:|----:|
| ('test', 30)  |    2.153 |  0.234 | 265 |
| ('test', 38)  |    1.583 |  0.528 | 265 |
| ('train', 30) |    2.196 |  0.403 | 625 |
| ('train', 38) |    1.33  |  0.653 | 625 |
| ('val', 30)   |    1.965 |  0.316 | 152 |
| ('val', 38)   |    0.472 |  0.586 | 152 |

Detected cuts per GOP by family:

| family      |   cuts |   fp_cv |
|:------------|-------:|--------:|
| archive_org |  0.083 |   0.451 |
| film        |  0.196 |   0.39  |
| splice      |  0.617 |   0.791 |
| ugc         |  0.124 |   0.493 |
| uvg         |  0     |   0.2   |
| xiph_hd     |  0.047 |   0.205 |
