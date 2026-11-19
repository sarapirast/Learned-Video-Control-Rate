# Controller settings on dPSNR_B (x264, final3, test; scripts/controller_dpsnr.py)

252 GOPs (13 flat excluded), levels [np.int64(24), np.int64(30), np.int64(36), np.int64(42)], k [np.int64(0), np.int64(2), np.int64(5), np.int64(10), np.int64(29)]. score = dPSNR_B - 0.17 x %over (dB), pooled over k and levels; setting = margin:dI:i_cap:w0:dmax:fcap:init:pmin:a:b.

| setting                                 |    n |   score |   dpsnr_b |   use |   over_pct_eps |   mean_over |   score_old |     k0 |     k2 |     k5 |    k10 |    k29 |
|:----------------------------------------|-----:|--------:|----------:|------:|---------------:|------------:|------------:|-------:|-------:|-------:|-------:|-------:|
| 1.0:9.0:1.0:2.0:3.0:4.0:0.0:1.0:1.0:0.0 | 5040 |   -0.22 |    -0.065 | 0.994 |          53.77 |        0.91 |      -3.095 | -0.486 | -0.237 | -0.117 | -0.107 | -0.152 |