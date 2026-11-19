# Exp 5a: final4 + fixed shift, fold (exp_next/exp5/shift_report.py)

Score in dB, real encodes, deterministic. Level-24-hole episodes excluded unless stated. Pre-registration: exp_next/exp5/PREREG_SHIFT.md. The shift is a schedule distilled from the search by weighted averaging, not RL.

Caveat: final4's rate model was fitted on all train clips including the fold.

## x264

| variant       |   n |   score |      A |    E-P |   mean |err| % |   signed err % |   % over |   p90 |err| % |   minus_final4 |
|:--------------|----:|--------:|-------:|-------:|---------------:|---------------:|---------:|--------------:|---------------:|
| perlevel:none | 582 |  -0.2   |  0.04  | -0.24  |          2.928 |         -1.329 |   54.983 |         5.304 |          0.036 |
| perlevel:bit  | 582 |  -0.205 |  0.016 | -0.221 |          2.844 |         -1.595 |   53.608 |         4.556 |          0.032 |
| pooled:full   | 582 |  -0.227 |  0.039 | -0.266 |          3.146 |         -1.462 |   55.67  |         6.467 |          0.009 |
| perqbin:bit   | 582 |  -0.228 |  0.005 | -0.233 |          2.807 |         -1.412 |   55.67  |         5.214 |          0.008 |
| pooled:bit    | 582 |  -0.239 | -0.003 | -0.235 |          2.655 |         -1.024 |   56.701 |         4.66  |         -0.003 |
| pooled:none   | 582 |  -0.25  |  0.02  | -0.27  |          2.861 |         -0.679 |   56.529 |         5.241 |         -0.014 |

final4 on the same episodes: score -0.236, A 0.016, E-P -0.252, mean |err| % 2.769, signed err % -0.929, % over 49.141, p90 |err| % 4.514

Within 0.005 dB of the best selectable arm: perlevel:bit, perlevel:none. **Selected (x264): perlevel:bit** (shift:cap rule; pooled:full is a reference arm, not selectable)

Selected variant by k (minus final4, fold clip bootstrap): k0 +0.001 [-0.037, +0.031]; k5 +0.062 [+0.018, +0.112] *

## x265

| variant       |   n |   score |      A |    E-P |   mean |err| % |   signed err % |   % over |   p90 |err| % |   minus_final4 |
|:--------------|----:|--------:|-------:|-------:|---------------:|---------------:|---------:|--------------:|---------------:|
| perlevel:none | 584 |  -0.247 |  0.004 | -0.252 |          3.066 |         -1.262 |   61.644 |         5.647 |          0.105 |
| perlevel:bit  | 584 |  -0.25  | -0.012 | -0.238 |          3.01  |         -1.465 |   59.932 |         5.835 |          0.103 |
| perqbin:bit   | 584 |  -0.27  | -0.014 | -0.256 |          3.132 |         -1.46  |   58.733 |         7.002 |          0.082 |
| pooled:full   | 584 |  -0.284 | -0.02  | -0.263 |          3.15  |         -1.463 |   59.075 |         6.241 |          0.069 |
| pooled:none   | 584 |  -0.307 | -0.032 | -0.275 |          3.016 |         -0.859 |   59.932 |         6.086 |          0.046 |
| pooled:bit    | 584 |  -0.316 | -0.056 | -0.26  |          2.942 |         -1.029 |   59.247 |         5.996 |          0.037 |

final4 on the same episodes: score -0.353, A -0.092, E-P -0.260, mean |err| % 2.923, signed err % -0.913, % over 53.596, p90 |err| % 4.656

Within 0.005 dB of the best selectable arm: perlevel:bit, perlevel:none. **Selected (x265): perlevel:bit** (shift:cap rule; pooled:full is a reference arm, not selectable)

Selected variant by k (minus final4, fold clip bootstrap): k0 +0.089 [+0.042, +0.155] *; k5 +0.116 [+0.040, +0.209] *

## Selection under REVISION 2 (superseded by REVISION 3 below)

{"x264": "perlevel:bit", "x265": "perlevel:bit"}

## REVISION 3: per-qbin:bit (causal) vs perlevel:bit

Rule per encoder: per-qbin:bit >= perlevel:bit - 0.01 dB (mean of shift - final4, pooled over k 0/5 and levels, hole excluded) -> per-qbin:bit goes to val; otherwise no shift arm goes to val.

- x264: per-qbin:bit +0.008 vs perlevel:bit +0.032 (kept 25% of the gain; per-qbin - perlevel -0.024 [-0.052, -0.004] *); bin = level on 77% of episodes -> **FAILS: the gain depends on budget-level hindsight; no val run**
  - per-qbin:bit by k (minus final4): k0 -0.034 [-0.111, +0.016]; k5 +0.050 [+0.010, +0.095] *
  - per-qbin:bit spend vs final4: A 0.005 vs 0.016, E-P -0.233 vs -0.252, mean |err| % 2.807 vs 2.769, p90 |err| % 5.214 vs 4.514, signed err % -1.412 vs -0.929, % over 55.670 vs 49.141
- x265: per-qbin:bit +0.082 vs perlevel:bit +0.103 (kept 80% of the gain; per-qbin - perlevel -0.020 [-0.040, +0.001]); bin = level on 76% of episodes -> **FAILS: the gain depends on budget-level hindsight; no val run**
  - per-qbin:bit by k (minus final4): k0 +0.032 [-0.002, +0.072]; k5 +0.132 [+0.046, +0.251] *
  - per-qbin:bit spend vs final4: A -0.014 vs -0.092, E-P -0.256 vs -0.260, mean |err| % 3.132 vs 2.923, p90 |err| % 7.002 vs 4.656, signed err % -1.460 vs -0.913, % over 58.733 vs 53.596

## Selection (REVISION 3; null = no val run)

{"x264": null, "x265": null}

