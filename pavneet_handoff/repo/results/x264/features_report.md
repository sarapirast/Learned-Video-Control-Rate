# Feature ablations at k = 5 (x264)

Groups: history (last bits/QP, bits vs first-pass estimate), fp (first-pass cost), pixel (spatial/temporal complexity, histogram change), scene (cut/flash/fade flags, same-scene flag, distance to cut, scene cost share). Budget state and position are always on.

| dropped groups             |   n |   score |    ci |   median |   saving |   over % |   seen |   seeds |   share of search gain | vs all         |
|:---------------------------|----:|--------:|------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|:---------------|
| (none: all features)       | 958 |   0.426 | 0.786 |    1.763 |    4.453 |   29.819 |    4.5 |       3 |                  0.632 | nan            |
| fp                         | 958 |  -1.075 | 0.843 |    0.868 |    3.675 |   33.368 |    4.5 |       3 |                  0.574 | -1.501 ± 0.716 |
| history                    | 958 |   1.565 | 0.791 |    2.824 |    4.735 |   21.051 |    4.5 |       3 |                  0.676 | +1.140 ± 0.458 |
| pixel                      | 958 |   3.152 | 0.609 |    3.113 |    4.831 |   20.842 |    4.5 |       3 |                  0.738 | +2.726 ± 0.519 |
| scene                      | 958 |   3.226 | 0.635 |    3.309 |    5.266 |   20.529 |    4.5 |       3 |                  0.74  | +2.800 ± 0.464 |
| fp,pixel,scene             | 958 |  -5.613 | 0.981 |   -1.859 |    1.149 |   44.12  |    4.5 |       3 |                  0.399 | -6.039 ± 0.835 |
| history,fp,pixel           | 958 |  -8.658 | 0.966 |   -7.845 |    1.871 |   73.417 |    4.5 |       3 |                  0.282 | -9.084 ± 0.760 |
| history,fp,scene           | 958 |  -2.8   | 1.026 |    0.705 |    3.015 |   36.604 |    4.5 |       3 |                  0.508 | -3.226 ± 0.785 |
| history,pixel,scene        | 958 |  -0.699 | 0.894 |    1.61  |    4.417 |   39.144 |    4.5 |       3 |                  0.589 | -1.124 ± 0.603 |
| history,fp,pixel,scene     | 958 |  -2.945 | 0.973 |    0.42  |    2.373 |   37.23  |    4.5 |       3 |                  0.502 | -3.370 ± 0.808 |
| (all) + scene budget prior | 958 |   3.022 | 0.615 |    3.1   |    5.206 |   21.677 |    4.5 |       3 |                  0.732 | +2.596 ± 0.445 |
