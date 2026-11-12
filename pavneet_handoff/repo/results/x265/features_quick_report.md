# Feature ablations at k = 5 (x265)

Groups: history (last bits/QP, bits vs first-pass estimate), fp (first-pass cost), pixel (spatial/temporal complexity, histogram change), scene (cut/flash/fade flags, same-scene flag, distance to cut, scene cost share). Budget state and position are always on.

| dropped groups             |   n |   score |    ci |   median |   saving |   over % |   seen |   seeds |   share of search gain | vs all         |
|:---------------------------|----:|--------:|------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|:---------------|
| (none: all features)       |  16 |  -8.223 | 9.171 |   -5.115 |    3.563 |    62.5  |    4.5 |       1 |                  0.153 | nan            |
| scene                      |  16 |  -9.184 | 9.534 |   -7.244 |    3.207 |    68.75 |    4.5 |       1 |                  0.093 | -0.961 ± 0.998 |
| (all) + scene budget prior |  16 |  -8.144 | 8.965 |   -4.983 |    3.547 |    62.5  |    4.5 |       1 |                  0.158 | +0.079 ± 0.333 |
