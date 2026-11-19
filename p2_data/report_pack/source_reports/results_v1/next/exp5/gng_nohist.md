# Centred-BC go/no-go without own history (exp_next/exp5/gng_nohist.py)

4000 plans per (encoder, k), OOF by clip, beta 0.1 weights. Dropped obs slots [5, 6, 7, 8] (own history).

| enc | k | features | R^2 label: position | R^2 label: GBM | **R^2 centred label** |
|---|---|---|---|---|---|
| x264 | 0 | no own history | 0.035 | 0.549 | **0.533** |
| x264 | 5 | no own history | 0.072 | 0.459 | **0.417** |
| x264 | 5 | drop o[6] only | 0.072 | 0.504 | **0.465** |
| x265 | 0 | no own history | 0.046 | 0.568 | **0.547** |
| x265 | 5 | no own history | 0.068 | 0.459 | **0.420** |
| x265 | 5 | drop o[6] only | 0.068 | 0.501 | **0.465** |

Full observation (shift_fit.md, same plans): x264 k0 0.590, k5 0.517; x265 k0 0.597, k5 0.524.

**GO: train centred BC without own history in the observation** (rule: >= 0.10 at k5, both encoders, no own history)

