# Hindsight search (x264)

|               |   n |   static |   best |   gain |   saving |   over |
|:--------------|----:|---------:|-------:|-------:|---------:|-------:|
| ('train', 30) |   8 |  -20.174 | -4.694 | 15.48  |    3.237 |   0.25 |
| ('train', 38) |   8 |  -29.683 | -2.6   | 27.083 |    2.226 |   0.25 |

By family (all splits):

| family   |   n |   gain |    best |
|:---------|----:|-------:|--------:|
| film     |   2 | 43.643 | -32.865 |
| splice   |   4 | 40.011 | -17.471 |
| ugc      |   8 | 10.492 |   7.232 |
| xiph_hd  |   2 |  4.621 |   9.705 |

Convergence: mean best score after n encodes (both seeds, per seed budget):

10: -18.118 | 25: -12.585
