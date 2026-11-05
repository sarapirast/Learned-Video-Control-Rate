# Feature ablations at k = 5 (x265)

Groups: history (last bits/QP, bits vs first-pass estimate), fp (first-pass cost), pixel (spatial/temporal complexity, histogram change), scene (cut/flash/fade flags, same-scene flag, distance to cut, scene cost share). Budget state and position are always on.

| dropped groups             |   n |   score |    ci |   median |   saving |   over % |   seen |   seeds |   share of search gain | vs all         |
|:---------------------------|----:|--------:|------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|:---------------|
| (none: all features)       | 958 |   3.482 | 0.601 |    2.657 |    5.112 |   20.181 |    4.5 |       3 |                  0.709 | nan            |
| fp                         | 958 |  -0.971 | 0.817 |    0.872 |    3.071 |   30.724 |    4.5 |       3 |                  0.525 | -4.452 ± 0.565 |
| history                    | 958 |   1.92  | 0.719 |    2.218 |    4.575 |   21.747 |    4.5 |       3 |                  0.645 | -1.562 ± 0.406 |
| pixel                      | 958 |   1.811 | 0.887 |    2.399 |    4.482 |   20.042 |    4.5 |       3 |                  0.64  | -1.671 ± 0.660 |
| scene                      | 958 |   3.404 | 0.554 |    2.739 |    4.589 |   15.379 |    4.5 |       3 |                  0.706 | -0.077 ± 0.371 |
| fp,pixel,scene             | 958 |  -3.618 | 1.015 |    0.316 |    2.368 |   37.822 |    4.5 |       3 |                  0.416 | -7.100 ± 0.803 |
| history,fp,pixel           | 958 |  -4.384 | 1.061 |   -0.769 |    2.994 |   45.755 |    4.5 |       3 |                  0.384 | -7.866 ± 0.851 |
| history,fp,scene           | 958 |  -1.075 | 0.881 |    1.211 |    3.37  |   33.994 |    4.5 |       3 |                  0.521 | -4.556 ± 0.710 |
| history,pixel,scene        | 958 |   2.629 | 0.694 |    2.706 |    4.781 |   23.974 |    4.5 |       3 |                  0.674 | -0.852 ± 0.433 |
| history,fp,pixel,scene     | 958 |  -4.412 | 1.127 |   -0.105 |    2.346 |   50.626 |    4.5 |       3 |                  0.383 | -7.893 ± 0.908 |
| (all) + scene budget prior | 958 |   3.221 | 0.639 |    2.982 |    5.2   |   21.19  |    4.5 |       3 |                  0.698 | -0.260 ± 0.333 |
