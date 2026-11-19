# Exp 5a: final4 + fixed shift, val (exp_next/exp5/shift_report.py)

Score in dB, real encodes, deterministic. Level-24-hole episodes excluded unless stated. Pre-registration: exp_next/exp5/PREREG_SHIFT.md. The shift is a schedule distilled from the search by weighted averaging, not RL.

**REVISION 4 (POST-HOC): per-qbin:bit at k5 only, chosen on the fold after its REVISION 3 result.**

Variants: {"x264": "perqbin:bit", "x265": "perqbin:bit"}

## PRIMARY (REVISION 4): (final4 + shift) - final4 per encoder, k5

- **x264: -0.025 [-0.081, +0.034] (n 548) -> DOES NOT HELP** (CI above 0)
  - by k: k5 -0.025 [-0.082, +0.033]
  - cut/gradual vs stable: cut/gradual -0.032 [-0.139, +0.136] (n 86); stable -0.023 [-0.088, +0.038] (n 462)
  - by level (budget, reported only): L24 -0.007; L30 -0.036; L36 -0.090; L42 +0.037
- **x265: +0.153 [+0.044, +0.283] * (n 550) -> HELPS** (CI above 0)
  - by k: k5 +0.153 [+0.040, +0.280] *
  - cut/gradual vs stable: cut/gradual +0.080 [-0.079, +0.462] (n 87); stable +0.167 [+0.061, +0.289] * (n 463)
  - by level (budget, reported only): L24 +0.008; L30 +0.033; L36 +0.083; L42 +0.478
- pooled over encoders (reported): +0.064 [-0.007, +0.146]

## Decomposition (A = quality for the bits, E-P = landing)

| enc   | k           | method         |   score |      A |    E-P |   mean |err| % |   signed err % |   % over |   p90 |err| % |
|:------|:------------|:---------------|--------:|-------:|-------:|---------------:|---------------:|---------:|--------------:|
| x264  | 5           | final4 + shift |  -0.138 |  0.06  | -0.198 |          2.203 |         -0.078 |   61.861 |         6.263 |
| x264  | 5           | final4         |  -0.113 |  0.072 | -0.185 |          1.84  |          0.413 |   55.657 |         3.687 |
| x265  | 5           | final4 + shift |  -0.103 |  0.051 | -0.154 |          1.781 |         -0.433 |   58.727 |         4.646 |
| x265  | 5           | final4         |  -0.256 | -0.085 | -0.171 |          1.627 |          0.344 |   50.364 |         3.448 |
| x264  | cut/gradual | final4 + shift |  -0.093 |  0.128 | -0.222 |          1.945 |          0.804 |   62.791 |         6.143 |
| x264  | cut/gradual | final4         |  -0.062 |  0.19  | -0.251 |          2.128 |          0.811 |   58.14  |         5.846 |
| x264  | stable      | final4 + shift |  -0.146 |  0.047 | -0.194 |          2.251 |         -0.243 |   61.688 |         6.2   |
| x264  | stable      | final4         |  -0.123 |  0.05  | -0.173 |          1.786 |          0.339 |   55.195 |         3.398 |
| x265  | cut/gradual | final4 + shift |  -0.041 |  0.126 | -0.167 |          1.467 |          0.562 |   66.667 |         4.96  |
| x265  | cut/gradual | final4         |  -0.121 |  0.094 | -0.216 |          1.835 |          0.556 |   54.023 |         6.007 |
| x265  | stable      | final4 + shift |  -0.114 |  0.037 | -0.151 |          1.84  |         -0.62  |   57.235 |         4.604 |
| x265  | stable      | final4         |  -0.281 | -0.118 | -0.162 |          1.588 |          0.304 |   49.676 |         2.91  |

## Level-effect check (signed spend error +1 pp or % over +10 pts vs final4)

none

With the hole included: x264 -0.015 [-0.075, +0.045]; x265 +0.156 [+0.040, +0.274] *

