# Results and interpretation (as of 2026-11-12)

All numbers are copied from the report files named in each section (paths relative to `repo/`). Scores are in dB
(Aayush's metric, see README §5) unless a section says "points" (the old saving-based score). Brackets are 95 %
cluster-bootstrap CIs. "vs rule" = paired difference to the val-tuned remaining-budget rule at the same lookahead L.

---

## 1. D34: stream-level budget allocation on dataset v1 (`results/v1_stream/<codec>/stream_report_test.md`)

2172 test cases per codec (streams × 4 levels × 3 budget scales); learners averaged over 3 seeds.

| Method | x265 score | x265 vs rule | x265 >1 % over | x264 score | x264 vs rule | x264 >1 % over |
|---|---|---|---|---|---|---|
| equal split per GOP | −1.059 | −0.433 [−0.535, −0.361] | 20 % | −1.195 | −0.485 [−0.608, −0.385] | 16 % |
| tuned rule L=0 | −0.627 | — | 12 % | −0.710 | — | 13 % |
| tuned rule L=2 | −0.423 | — | 12 % | −0.517 | — | 13 % |
| best constant QP (offline) | −0.214 | | 17 % | −0.213 | | 17 % |
| hindsight per-GOP plan (offline) | +0.218 | +0.845 (vs L=0 rule) | 0 % | +0.214 | +0.925 | 0 % |
| bc L=2 | −0.632 | −0.209 [−0.315, −0.065] | 36 % | −0.877 | −0.359 [−0.526, −0.177] | 34 % |
| ppo L=0 | −0.454 | +0.172 [+0.094, +0.283] | 14 % | −0.561 | +0.149 [+0.087, +0.228] | 16 % |
| ppo L=2 | −0.222 | +0.201 [+0.159, +0.265] | 12 % | −0.378 | +0.140 [+0.106, +0.177] | 15 % |
| **bc_ppo L=2 (primary)** | **−0.210** | **+0.213 [+0.152, +0.301]** | 10 % | **−0.382** | **+0.136 [+0.087, +0.201]** | 12 % |
| bc_ppo_lag L=2 | −0.217 | +0.206 [+0.142, +0.300] | 5 % | −0.400 | +0.117 [+0.070, +0.176] | 7 % |

Pre-registered hypotheses: H1 (hindsight − rule ≥ 0.3 dB, room exists) pass; H2 (bc_ppo L=2 > rule, CI > 0) pass;
H3 (gain larger on mixed streams) pass; H4 (overshoot within 5 pts of rule) pass; H5 (rule > equal split) pass.

Follow-up (`stream_variation_test.md`):
- Most of the gain is on **mixed streams** (+0.32 / +0.20 dB) vs same-clip streams (+0.08 / +0.06). Same-clip L=0
  gain ≈ 0; same-clip L=2 gain +0.08–0.11 dB (x265), +0.06–0.11 (x264; significant only for ppo).
- At equal stream variation, mixed streams still gain more: part of the mixed-stream advantage is the rule's online
  calibration being misled by unrelated clips, not variation alone.
- Bitrate equivalent (bits the rule needs to match RL's PSNR, L=2): x265 +4.2–5.1 %, x264 +1.5–3.1 %; same-clip only
  x265 +1.0–2.4 %, x264 +0.3–1.9 %.

Caution: on x265 the **offline best constant QP** (−0.214) equals bc_ppo L=2 (−0.210); on x264 it is better (−0.213
vs −0.382). It is not causal (it knows the right QP in advance), but it shows how much of the causal deficit is just
"finding the right QP level".

## 2. D35a: RL vs the encoders' own rate control (`results/v1_stream/<codec>/own_rc_stream_v1_report.md`)

724 cases (181 test streams × 4 levels, s = 1). Each stream is one real 240-frame encode; the encoder may change QP
every frame, RL only every GOP. Check: constant-QP stream encode reproduces the v1 curves exactly.

| Config | x265 score | x265 >1 % over | x265 mean over | x264 score | x264 >1 % over | x264 mean over |
|---|---|---|---|---|---|---|
| RL bc_ppo L=2 | −0.205 | 10 % | 0.36 % | −0.377 | 12 % | 0.47 % |
| tuned rule L=2 | −0.419 | 11 % | 0.52 % | −0.511 | 12 % | 0.64 % |
| abr | −2.417 | 61 % | 14.5 % | −1.243 | 59 % | 6.2 % |
| abr_vbv (Aayush's baseline) | −0.646 | 27 % | 0.9 % | −0.550 | 56 % | 1.9 % |
| abr_tree (cutree) | −2.743 | 34 % | 12.8 % | −0.949 | 40 % | 4.1 % |
| abr_aq (encoder defaults) | −3.036 | 40 % | 14.4 % | −1.175 | 38 % | 3.3 % |
| 2pass (non-causal) | −0.215 | 35 % | 1.4 % | −0.106 | 12 % | 0.3 % |
| 2pass_aq (non-causal) | −0.269 | 36 % | 1.7 % | −0.130 | 15 % | 0.4 % |

Paired: bc_ppo L=2 vs abr_vbv **+0.441 [+0.350, +0.541]** (x265), **+0.173 [+0.094, +0.256]** (x264); vs abr_tree
+2.54 / +0.57; vs two-pass +0.010 [−0.041, +0.055] (x265 tie) / −0.271 [−0.367, −0.191] (x264, two-pass ahead).
H9 pass.

Interpretation: the encoders lose mainly through **overshoot**; single-pass ABR is not built to hit a hard total.
Note the tuned (non-learned) rule also beats ABR+VBV on x265 (−0.419 vs −0.646) and roughly ties it on x264; the
RL-specific claim is "RL > tuned rule > encoder ABR", not only "RL > encoder".

## 3. D35b: fresh long films (`results/fresh_stream/<codec>/fresh_stream_report.md`)

Elephants Dream + Tears of Steel (never in v1), 12 segments of 32 GOPs; policies and rule from D34 unchanged.

L=2, vs rule (dB):

| Method | x265 N=8 | x265 N=16 | x265 N=32 | x264 N=8 | x264 N=16 | x264 N=32 |
|---|---|---|---|---|---|---|
| ppo | +0.051 [−0.012, +0.121] | **+0.118** [+0.058, +0.185] | **+0.161** [+0.092, +0.241] | **+0.071** [+0.025, +0.122] | **+0.093** [+0.044, +0.146] | **+0.151** [+0.084, +0.238] |
| bc_ppo (primary) | +0.032 [−0.040, +0.110] | +0.065 [−0.007, +0.137] | +0.008 [−0.102, +0.101] | **+0.065** [+0.016, +0.119] | +0.058 [−0.006, +0.122] | +0.037 [−0.062, +0.141] |
| bc_ppo_lag | +0.035 | +0.067 | +0.044 | **+0.060** | +0.053 | +0.040 |
| bc | −0.456 | −0.556 | −1.016 | −0.423 | −0.546 | −1.004 |
| hindsight (offline) | +0.574 | +0.746 | +0.981 | +0.644 | +0.761 | +0.952 |

L=0: ppo / bc_ppo +0.20 to +0.40 at N = 16/32, but the rule (tuned at N=8) degrades from −0.50 to −0.81 on long
streams, so these are not claimed.

Hypotheses: **H6** (bc_ppo L=2 > rule at N=8) **split** — fails x265, passes x264. **H7** (gain doesn't shrink with
N) pass. **H8** (overshoot within 5 pts of rule) pass; bc_ppo_lag 1–5 %.

## 4. What it all means

1. **RL clearly beats the encoders' own causal rate control** (ABR, ABR+VBV, cutree, defaults) on both encoders,
   because it controls overshoot far better while using the budget. Only non-causal two-pass matches or beats it.
2. **RL beats a carefully tuned hand rule at stream-level allocation**, but the size depends on the data:
   +0.14–0.21 dB on v1 (inflated by spliced mixed streams), +0.05–0.16 dB (~1–3 % bitrate) on real continuous film,
   most reliable for plain PPO on longer streams.
3. **The gain comes from reward-driven RL, not imitation**: BC of the hindsight plan is always worse than the rule;
   PPO (from scratch or after BC) is what crosses above it.
4. **Within one GOP, Aayush's final3 is not beaten** by any learner (his result). The RL benefit is at the
   stream budget-allocation level, which final3 does not decide (it is handed a per-GOP budget).

What "dB" means: PSNR in dB at the same budget relative to "constant QP spending exactly the budget", after a
0.17 dB per 1 % overshoot charge. Example x265 N=8 fresh: rule dPSNR_B −0.22 / score −0.26; PPO −0.16 / −0.21.

## 5. Why final3 is hard to beat (analysis from reading Aayush's `controller_v1.py`, read-only)

- final3: per-frame rate model bits = c × first-pass bits × 2^(−(q−30)/s) (separate I/P), c recalibrated after every
  frame, then solve for the constant P-frame QP that spends margin × remaining budget over the rest of the GOP;
  limit QP change per frame (dmax); setting `1.0:9:1:2:3:4:0:1:1:0` (margin:dI:i_cap:w0:dmax:fcap:init:pmin:a:b).
- Under MSE/PSNR with a fixed budget, constant QP is near-optimal; final3 is an online solver for exactly that, so
  only rate-model error remains, and feedback shrinks it.
- His simulator reads each frame's bits from constant-QP encodes, so a P frame's cost does **not** depend on its
  reference frame's QP (his docstring says so). The one known way to beat constant QP (spending more on heavily
  referenced frames, what cutree/mb-tree do) is therefore invisible; RL has nothing to discover.
- Headroom is small: per-GOP hindsight search +0.30 dB vs final3 ≈ −0.24 dB at k=2 (x264); his residual RL on
  final3 was slightly worse at every k.
- Real world: deployed live/low-delay rate control is single-pass ABR/CBR+VBV, which is **weaker** on this metric
  (Aayush: x264 ABR+VBV −1.6 dB per GOP vs final3 −0.24; ours: RL beats ABR+VBV at stream level). VOD uses two-pass /
  per-shot encoding that sees the future, which is **stronger** than final3. final3 is strong because it lives in an
  idealised simulator with exact budgets and a fitted model.

## 6. Caveats (state these with the results)

- Fresh set: 12 segments from 2 films (segments of one film are not independent).
- Rule and policies tuned/trained at N=8 only.
- Per-GOP constant QP from curves: no frame-level control inside a GOP on either side (except the encoder configs).
- H6, the pre-registered primary on fresh films, failed on x265.
- PSNR only; no perceptual metric.
- v1 gains partly from spliced mixed streams that real video rarely contains.

## 7. Earlier phases (old saving-based score, "points"; details in `repo/paper/full_report/full_report.pdf`)

- Original setting (oracle base QP, 2 budgets): hindsight search ~10 pts; best learner Lagrangian/PID-PPO from an
  offline start (x265 4.36/4.95 at k=0/5, x264 3.90/4.07); lookahead helps to k≈1–3 and at cuts.
- Causal rerun (D30): lookahead gain nearly vanishes (+0.40 x265, +0.11 x264, k 0→5); Lagrangian beats BC
  by +6.1 / +10.8 at k=0.
- Learning curve (D32): more clips buy budget reliability, not compression.
- v1 Stage 1 (D31): CQL→PPO and Lagrangian beat Aayush's *original* controller by +2.0 to +3.7 pts — later shown
  unfair by the unused-budget issue (D33) and his retuned final3.
- D33 rerun with an under-budget penalty: spend rose to 94–98 %, PSNR +0.37–0.51 dB vs controller, but overshoot rose
  to 10–19 %; superseded by the dB metric.
- None of the original-setting wins survive as "beats a fair, tuned controller"; that is why D34 exists.
