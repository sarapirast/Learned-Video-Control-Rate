# Leak-fixed live stream: 3-seed learners vs the encoder's own ABR+VBV, and the validation selection check

Score = luma dPSNR_B - 0.17 dB per % over - 0.5 dB per % stalled. Paired on identical cases; 95 % cluster bootstrap over source groups (mixed streams own cluster); * = CI excludes 0. Learner rows: seeds averaged per case (curve lookups, = real encodes, D47). Encoder: whole-stream ABR+VBV, 1 s buffer, target f x channel mean, f tuned on val.

## x265, AR(1) (encoder f = 0.9)

| comparison | test n=8 | test playlists n=16 |
|---|---|---|
| il_ppo (3 seeds) - encoder ABR+VBV | -0.510 [-1.743, +0.108] (n=724) | +1.250 [-0.363, +2.183] (n=600) |
| ppo_v2 (3 seeds) - encoder ABR+VBV | -0.731 [-1.990, -0.092]* (n=724) | +1.137 [-0.513, +2.124] (n=600) |

Validation (selection check): il_ppo - ppo_v2 +0.158 [+0.115, +0.210]* (n=1704); il_ppo - vbv2 +0.387 [+0.265, +0.537]* (n=1704); ppo_v2 - vbv2 +0.230 [+0.132, +0.349]* (n=1704)

## x265, LTE (encoder f = 0.3)

| comparison | test n=8 | test playlists n=16 |
|---|---|---|
| il_ppo (3 seeds) - encoder ABR+VBV | +0.964 [-0.859, +2.251] (n=724) | -- |
| ppo_v2 (3 seeds) - encoder ABR+VBV | +0.788 [-1.100, +2.133] (n=724) | -- |

Validation (selection check): il_ppo - ppo_v2 +0.124 [+0.009, +0.264]* (n=1704); il_ppo - vbv2 +0.444 [+0.285, +0.635]* (n=1704); ppo_v2 - vbv2 +0.320 [+0.187, +0.467]* (n=1704)

## x264, AR(1) (encoder f = 0.9)

| comparison | test n=8 | test playlists n=16 |
|---|---|---|
| il_ppo (3 seeds) - encoder ABR+VBV | -1.669 [-3.362, -0.749]* (n=724) | +0.097 [-2.251, +1.429] (n=600) |
| ppo_v2 (3 seeds) - encoder ABR+VBV | -1.846 [-3.576, -0.916]* (n=724) | +0.007 [-2.295, +1.342] (n=600) |

Validation (selection check): il_ppo - ppo_v2 +0.169 [+0.136, +0.210]* (n=1704); il_ppo - vbv2 +0.507 [+0.419, +0.615]* (n=1704); ppo_v2 - vbv2 +0.338 [+0.265, +0.426]* (n=1704)

## x264, LTE (encoder f = 0.4)

| comparison | test n=8 | test playlists n=16 |
|---|---|---|
| il_ppo (3 seeds) - encoder ABR+VBV | -0.516 [-2.967, +1.249] (n=724) | -- |
| ppo_v2 (3 seeds) - encoder ABR+VBV | -0.635 [-2.998, +1.074] (n=724) | -- |

Validation (selection check): il_ppo - ppo_v2 +0.153 [+0.002, +0.347]* (n=1704); il_ppo - vbv2 +0.572 [+0.418, +0.732]* (n=1704); ppo_v2 - vbv2 +0.419 [+0.184, +0.614]* (n=1704)

