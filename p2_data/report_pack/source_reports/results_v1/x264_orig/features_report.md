# Feature ablations at k = 5 (x264)

Groups: history (last bits/QP, bits vs first-pass estimate), fp (first-pass cost), pixel (spatial/temporal complexity, histogram change), scene (cut/flash/fade flags, same-scene flag, distance to cut, scene cost share). Budget state and position are always on.

| dropped groups       |   n |   score |    ci |   median |   saving |   over % |   seen |   seeds |   share of search gain |
|:---------------------|----:|--------:|------:|---------:|---------:|---------:|-------:|--------:|-----------------------:|
| (none: all features) | 530 |    3.75 | 0.618 |    3.315 |    4.667 |   13.836 |    4.5 |       3 |                  0.696 |
