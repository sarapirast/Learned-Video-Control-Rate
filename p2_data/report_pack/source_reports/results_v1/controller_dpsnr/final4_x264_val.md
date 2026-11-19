# Controller settings on dPSNR_B (x264, final4, val; scripts/controller_dpsnr.py)

140 GOPs (12 flat excluded), levels [np.int64(24), np.int64(30), np.int64(36), np.int64(42)], k [np.int64(0), np.int64(2), np.int64(5), np.int64(10), np.int64(29)]. score = dPSNR_B - 0.17 x %over (dB), pooled over k and levels; setting = margin:dI:i_cap:w0:dmax:fcap:init:pmin:a:b.

| setting                                     |    n |   score |   dpsnr_b |   use |   over_pct_eps |   mean_over |   score_old |     k0 |   k2 |    k5 |    k10 |    k29 |
|:--------------------------------------------|-----:|--------:|----------:|------:|---------------:|------------:|------------:|-------:|-----:|------:|-------:|-------:|
| 1.0:6.0:1.0:2.0:3.0:4.0:1.0:1.0:1.0:0.0:3.0 | 2800 |  -0.224 |    -0.026 | 0.998 |         53.821 |       1.164 |      -2.251 | -0.426 | -0.2 | -0.16 | -0.162 | -0.172 |