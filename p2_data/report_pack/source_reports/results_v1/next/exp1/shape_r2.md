# Exp 1: predictability of the search's per-frame shape (exp_next/exp1/shape_r2.py)

shape_t = QP_t - mean P-frame QP; R^2 over all frames / P frames only. 'search' = the search shape; 'search - final4' = the search shape minus final4's realised shape at the same (GOP, level, k). Train: clip-grouped 5-fold out-of-fold; val: fit on all train. Model (i) = per-frame-index mean; (ii) = GBM on causal first-pass features at k.

## x264

Tied-best plans per train (GOP, level): median 2, mean 10.3, max 600, share with ties 0.55.

| k | target | train OOF (i) all / P | train OOF (ii) all / P | val (i) all / P | val (ii) all / P |
|---|---|---|---|---|---|
| 0 | search | 0.704 / 0.638 | 0.735 / 0.677 | 0.710 / 0.645 | 0.742 / 0.684 |
| 0 | search - final4 | 0.122 / 0.116 | 0.370 / 0.370 | 0.042 / 0.031 | 0.350 / 0.346 |
| 2 | search | 0.704 / 0.638 | 0.738 / 0.680 | 0.710 / 0.645 | 0.745 / 0.687 |
| 2 | search - final4 | 0.144 / 0.144 | 0.345 / 0.334 | 0.093 / 0.089 | 0.341 / 0.326 |
| 5 | search | 0.704 / 0.638 | 0.736 / 0.678 | 0.710 / 0.645 | 0.742 / 0.684 |
| 5 | search - final4 | 0.185 / 0.189 | 0.345 / 0.335 | 0.159 / 0.161 | 0.331 / 0.321 |

## x265

Tied-best plans per train (GOP, level): median 2, mean 9.2, max 600, share with ties 0.56.

| k | target | train OOF (i) all / P | train OOF (ii) all / P | val (i) all / P | val (ii) all / P |
|---|---|---|---|---|---|
| 0 | search | 0.697 / 0.631 | 0.724 / 0.665 | 0.709 / 0.644 | 0.741 / 0.683 |
| 0 | search - final4 | 0.107 / 0.099 | 0.335 / 0.333 | 0.081 / 0.072 | 0.394 / 0.393 |
| 2 | search | 0.697 / 0.631 | 0.725 / 0.665 | 0.709 / 0.644 | 0.741 / 0.683 |
| 2 | search - final4 | 0.125 / 0.122 | 0.309 / 0.297 | 0.129 / 0.128 | 0.403 / 0.388 |
| 5 | search | 0.697 / 0.631 | 0.725 / 0.665 | 0.709 / 0.644 | 0.741 / 0.682 |
| 5 | search - final4 | 0.154 / 0.155 | 0.268 / 0.250 | 0.182 / 0.188 | 0.375 / 0.363 |

## PRIMARY (stop rule 2): R^2 on val of (search shape - final4 shape) at k = 5, model (ii), all frames

x264: 0.331, x265: 0.375

Stop rule 2 (PREREG): < 0.1 -> expect Experiment 4 rung 3 to gain at most a few hundredths of a dB.

