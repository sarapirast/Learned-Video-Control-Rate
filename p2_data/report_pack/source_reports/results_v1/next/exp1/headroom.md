# Exp 1: allocation headroom and local slope (exp_next/exp1/decompose.py)

Val, flat GOPs excluded. A = quality for the bits (dB). 95% bootstrap over clips ('*' = CI excludes 0).

## x264

| k | n | search A - final4 A | search score - final4 score |
|---|---|---|---|
| 0 | 560 | +0.356 [+0.259, +0.467] * | +0.742 [+0.461, +1.115] * |
| 2 | 560 | +0.278 [+0.187, +0.402] * | +0.517 [+0.308, +0.795] * |
| 5 | 560 | +0.261 [+0.185, +0.360] * | +0.476 [+0.300, +0.707] * |
| 10 | 560 | +0.285 [+0.215, +0.367] * | +0.478 [+0.330, +0.681] * |
| 29 | 560 | +0.321 [+0.250, +0.396] * | +0.489 [+0.349, +0.635] * |

|   level |   slope dB per 1% |   optimal over rate (slope/0.17) |   final4 over rate |
|--------:|------------------:|---------------------------------:|-------------------:|
|      24 |             0.064 |                            0.374 |              0.449 |
|      30 |             0.051 |                            0.299 |              0.509 |
|      36 |             0.044 |                            0.261 |              0.547 |
|      42 |             0.043 |                            0.253 |              0.649 |

## x265

| k | n | search A - final4 A | search score - final4 score |
|---|---|---|---|
| 0 | 560 | +0.479 [+0.367, +0.609] * | +0.807 [+0.528, +1.150] * |
| 2 | 560 | +0.382 [+0.240, +0.548] * | +0.585 [+0.351, +0.873] * |
| 5 | 560 | +0.379 [+0.238, +0.535] * | +0.568 [+0.352, +0.834] * |
| 10 | 560 | +0.388 [+0.267, +0.518] * | +0.563 [+0.391, +0.775] * |
| 29 | 560 | +0.388 [+0.294, +0.491] * | +0.539 [+0.395, +0.705] * |

|   level |   slope dB per 1% |   optimal over rate (slope/0.17) |   final4 over rate |
|--------:|------------------:|---------------------------------:|-------------------:|
|      24 |             0.056 |                            0.331 |              0.429 |
|      30 |             0.048 |                            0.285 |              0.436 |
|      36 |             0.042 |                            0.249 |              0.52  |
|      42 |             0.036 |                            0.212 |              0.604 |

## PRIMARY: allocation headroom H, both encoders, k in {0, 5}, val

search A - final4 A = +0.369 [+0.269, +0.489] * (n 2240; bootstrap over clips, each clip carrying both encoders)

Stop rule 1 (PREREG): H < 0.05 dB -> frame-level RL has little left; shrink Experiments 4 and 5.

