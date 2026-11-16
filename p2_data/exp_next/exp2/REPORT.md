# Experiment 2: handoff (learner first, final4 for the last m frames) -- REPORT (2026-11-13)

Pre-registration `exp_next/exp2/PREREG.md`. Jobs: x264 14207330, x265 14207331 (resubmission; the first submission
14200366/7 lost its output to a missing parquet engine in the torch env, see the tracker). 33,600 val episodes
(5 m x k 0/5 x 3 seeds x 560 episodes x 2 encoders). Analysis `exp_next/exp2/report.py` ->
`results_v1/next/exp2/report.md`, `episodes.parquet`. Level-24-hole episodes excluded.

## Gate (m = 10, both encoders, k 0/5) -- FAIL on all three conditions

| Condition | Result | Required |
|---|---|---|
| hybrid - final4, point | -0.052 | >= 0 |
| 95% CI lower bound | -0.146 (CI [-0.146, +0.056]) | > -0.05 |
| mean \|spend error\| | 4.16% vs final4 2.55% | <= 3.05% |

Per encoder: x264 -0.109 [-0.224, -0.006], x265 +0.005 [-0.094, +0.122]. Per seed: -0.051 / -0.076 / -0.028.

## All m (descriptive)

| m | hybrid - final4 | hybrid - learner alone | mean \|spend err\| (final4 2.55%, learner 4.54%) | signed err x264 / x265 |
|---|---|---|---|---|
| 3 | -0.072 [-0.187, +0.041] | +0.022 * | 3.87% | -0.2% / -1.4% |
| 5 | -0.057 [-0.164, +0.053] | +0.037 * | 3.85% | -0.5% / -1.8% |
| 10 | -0.052 [-0.144, +0.050] | +0.042 * | 4.16% | -1.2% / -2.6% |
| 15 | -0.077 [-0.153, +0.009] | +0.017 | 4.95% | -2.2% / -3.6% |
| 20 | -0.117 [-0.197, -0.051] * | -0.023 | 5.76% | -3.1% / -4.4% |

## Reading

- Handing the last 3-10 frames to final4 helps the learner a little (+0.02 to +0.04 dB) but does not bring it to
  final4. On x265 at k0 the hybrid is slightly above final4 (+0.05 at m = 10, n.s.); on x264 it is below at every m.
- **A longer handoff makes landing worse, not better.** As m grows the hybrid increasingly under-spends (signed
  error -1% at m = 10 to -3..-4% at m = 20) and its tail widens (p90 |spend error| 13% -> 19-22%). final4's
  per-frame re-planning only lands well when it has also chosen the earlier frames: after the learner's frames
  its single-slope rate model, calibrated at the learner's QPs, over-predicts the remaining frames' bits. This is
  the rate-model limitation D3 (per-frame slope 3.7-8.2 QP per halving vs one fitted value), now seen directly.
- Large early overshoots by the learner (worst case +82-85%) cannot be repaired by any m.
- Conclusion: the learner's spend problem is not a "last frames" problem that final4 can patch; the residual
  design (final4 plans every frame, the learner adjusts) is the right structure, as in Exp 3 / Exp 4.

Line stopped (protocol: a failed gate is recorded and that line ends). The handoff hybrid does not go into the
final test run.
