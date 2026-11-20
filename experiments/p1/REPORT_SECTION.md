# P1: encoder infrastructure and the lookahead study (imitation start and RL across k)

Author: Ahhana (P1). Status: DRAFT for the final report, 2026-11-19. Written in the style of Aayush's
`p2_data/report_pack/RESULTS.md`: every number cites the file it comes from (paths relative to
`/scratch1/ahhanagu/ee599/` unless they start with `/` or name a repo file). "The controller" = P2's frozen causal
controller (final4 in file names). A LaTeX version for the IEEE draft is in `report_section.tex`.

Contents
1. Infrastructure
2. Lookahead study: setup
3. Results (x264 val, x265 val, figure, test2)
4. Interpretation, and what not to claim
5. Limitations
6. Provenance

---

## 1. Infrastructure

**x264 per-frame shim and Gym environment.** A ctypes shim around libx264 (the CARC module build 165, P1's frozen
settings) encodes one frame at a time at a forced QP and returns slice bits, header bits and the reconstructed frame.
A Gymnasium environment wraps it (one GOP per episode, per-frame QP action, lookahead features). Against the x264
command line the shim is **byte-identical in 25/25 cases** (5 GOPs, including a synthetic pattern and a scene cut, each
at constant QP 26 / 11 / 51, random QPs and the budget-shield case): bitstream, per-frame slice bits and decoded frames
(`P1_README.md`, "Parity results").

**Fast backend for the team pipeline (`RC_BACKEND=shim`).** The team's RL environment (Pavneet's rclib) re-encoded
the whole GOP prefix with the x264 command line at every step. With the shim behind the same interface (one open encoder
per episode, only the newest frame encoded; bits counted with rclib's own parser, PSNR with rclib's own formula), the
results are identical and evaluation is about 13 times faster:

| Check (x264, 10 val GOPs x 4 budget levels = 40 episodes) | the controller | R3 (k5, seed 3) |
|---|---|---|
| per-frame QPs, bits, PSNR and score, shim vs command line | 40/40 identical | 40/40 identical |
| episodes per second, command line / shim (one core) | 0.39 / 5.15 (13.2x) | 0.38 / 4.67 (12.2x) |

Source: `experiments/p1/01_shim_vs_cli_check/README.md` (rows: `shimcheck/rows_*.pkl`). On the **full validation set**
the shim results are identical too: the controller at k = 0, 2, 5, 10, 29 (2,800 episodes: bits, PSNR and scores, with
the team's capped PSNR applied) and R3 at k5 (3 x 560 episodes: QPs, bits and scores)
(`experiments/p1/02_baseline_reproduction/README.md`, "Checks"). The shim is x264 only; **x265 runs use the command
line**. Training one R3 model (180k steps) went from ~33 min to ~4 min. Retraining Aayush's R3 recipe through the
shim gives **bit-identical models**: k5 seeds 3, 4, 5, all 12 weight tensors equal, and identical QPs and scores on
560/560 val episodes each (`results/r3_kcurve/weights_check.txt`, `weights_check_b2.txt`, `summary_all.md`).

**PSNR convention.** The stored controller rows and constant-QP curves did not cap each plane's PSNR at 100 dB while the
learners' rows did; after I reported it, the team adopted one convention, every plane capped at 100 dB everywhere
(curves included), which moved the val x264 R3 - controller from +0.068 to +0.077 and its cut/gradual slice from +0.016 to
+0.069 (`experiments/p1/02_baseline_reproduction/README.md`; `p2_data/docs/team-update-2026-11-16.txt` section 7). All
numbers below use it.

---

## 2. Lookahead study: setup

**Question.** Inside one GOP, how does lookahead k change (a) the imitation start alone, (b) R3 = that start fine-tuned
with PPO as a residual on the controller, and (c) the same PPO from the standard start?

**Methods** (all residual on the controller, Aayush's R3 recipe: lambda 0.17, controller-state features, budget level
masked, per-frame mean shift, bit cap, 20k critic-only warm-up, 180k PPO steps):
- **BC alone** = the imitation start: a classifier over 13 QP offsets trained on the hindsight-search plans. Measured as
  each R3 run's 20k checkpoint (the actor is frozen during the warm-up, so this is exactly the BC network).
- **R3** = BC start + PPO (the run's final 180k model).
- **R2c** = the same PPO from the standard start (no BC), Aayush's matched control.

**Lookahead** k in {0, 2, 5, 10, 29} frames (29 = the whole GOP).

**BC start at each k.** For each k, a BC network trained with the same data pipeline and fold protocol as Aayush's k5 BC:
the same 101,900 search plans over 56 fitting clips, 0 train-select fold clips, the same 5 hold-out clips, 40,000 steps,
batch 1,024, lr 3e-4; the per-frame mean shift fitted at each k the same way. Every data build also rebuilt k5 and had
to equal Aayush's k5 shift and k5 dataset exactly (it did: x264 3,057,000 rows, x265 3,058,500 rows)
(`experiments/p1/03_r3_lookahead/README.md`, "Checks that passed"; job logs in `results/r3_kcurve/logs/`).

**Seeds** 3, 4, 5, averaged per episode, except: x264 k2 and k10 (seed 3 only) and R2c at x264 k5 (seed 0 only); these
are marked "(1 seed)". R2c was run on x264 only.

**Evaluation.** Validation only (140 GOPs x 4 budget levels; level-24 "hole" episodes excluded: n = 548 x264, 550
x265); score = dPSNR_B - 0.17 dB per 1 % over budget, one PSNR cap everywhere; every method paired with the controller
at the same k on (GOP, level); 95 % clip bootstrap ("*" = CI excludes 0).

---

## 3. Results

### 3.1 x264, validation

| k | seeds R3 / R2c | controller score | BC - controller | R3 - controller | R3 - BC | R2c - controller | R3 - R2c |
|---|---|---|---|---|---|---|---|
| 0 | 3-5 / 3-5 | -0.358 | -0.533 [-0.734, -0.348] * | +0.069 [+0.005, +0.138] * | +0.602 [+0.440, +0.775] * | -0.064 [-0.114, -0.015] * | +0.133 [+0.086, +0.187] * |
| 2 | 3 (1 seed) / - | -0.148 | -0.234 [-0.308, -0.165] * | +0.072 [+0.020, +0.128] * | +0.306 [+0.225, +0.408] * | - | - |
| 5 | 3-5 / 0 (1 seed) | -0.115 | -0.155 [-0.314, -0.050] * | +0.077 [+0.020, +0.143] * | +0.231 [+0.131, +0.374] * | -0.018 [-0.087, +0.050] | +0.095 [+0.043, +0.147] * |
| 10 | 3 (1 seed) / - | -0.119 | +0.058 [+0.015, +0.099] * | +0.102 [+0.040, +0.168] * | +0.044 [+0.007, +0.085] * | - | - |
| 29 | 3-5 / 3-5 | -0.142 | +0.057 [+0.009, +0.103] * | +0.097 [+0.039, +0.154] * | +0.041 [-0.001, +0.084] | -0.044 [-0.064, -0.021] * | +0.141 [+0.090, +0.187] * |

Source: `results/r3_kcurve/summary_final.md` (`experiments/p1/03_r3_lookahead/score_final_capped.py`; rows
`rows_final.parquet`). At k2, Aayush's own 3-seed R3 runs give R3 - controller **+0.035, not significant**
(`p2_data/report_pack/RESULTS.md` section 10; `results_v1/next/fw/report_fw_val.md`); the +0.072 above is one seed.
The R3 - controller split by GOP class (stable vs cut/gradual) is in the same file; the cut/gradual slice (86 episodes)
is not significant at any k.

### 3.2 x265, validation (k0 and k29 mine; k2 and k5 Aayush's runs)

| k | runs | controller score | BC - controller | R3 - controller | R3 - BC |
|---|---|---|---|---|---|
| 0 | mine, seeds 3-5 | -0.470 | -0.395 [-0.606, -0.187] * | +0.127 [+0.006, +0.259] * | +0.522 [+0.377, +0.678] * |
| 2 | **Aayush's**, seeds 3-5 | -0.262 | -0.155 [-0.256, -0.053] * | +0.152 [+0.060, +0.260] * | +0.307 [+0.247, +0.375] * |
| 5 | **Aayush's**, seeds 3-5 | -0.254 | -0.003 [-0.099, +0.086] | +0.209 [+0.093, +0.346] * | +0.212 [+0.140, +0.296] * |
| 29 | mine, seeds 3-5 | -0.237 | +0.132 [+0.053, +0.215] * | +0.104 [+0.020, +0.202] * | -0.028 [-0.071, +0.008] |

Source: `results/r3_kcurve/summary_final_x265.md` (`score_final_capped.py --enc x265`). The k2 and k5 rows are
Aayush's existing x265 runs (R3 seeds 3-5 and his BC-alone evaluations), rescored with the same scorer; they reproduce
his `report_fw_val.md` numbers exactly. The controller rows are his stored x265 rows with the capped PSNR
(`results_v1/final/cap_fix_x265.pkl`). No R2c and no k10 on x265. The x265 setup was checked before training: the k5
shift and dataset equal his exactly, and his stored x265 k5 model evaluated through my x265 setup reproduces his stored
val rows 560/560 (`results/r3_kcurve/logs/r3k_x265_reeval-14378980.out`).

### 3.3 Figure

`results/r3_kcurve/fig_val_kcurve_bc_r3_r2c.png` (every plotted number in `fig_val_kcurve_bc_r3_r2c.csv`; script
`experiments/p1/03_r3_lookahead/make_kcurve_figure.py`). Top row x264, bottom row x265. Left: mean score vs k for the
controller, BC alone, R3, R2c and R2c's start (controller + shift + cap), with the best constant QP in hindsight as a
reference line (as in the report pack's figure 2). Right: paired differences with 95 % CIs. Hollow = one seed. Slide
versions (left panel only): `fig_val_kcurve_scores.png`, `fig_val_kcurve_scores_x265.png`.

### 3.4 test2 (fresh held-out clips)

| test2 | R3 - controller | status |
|---|---|---|
| x264, k0 (my models, seeds 3-5) | +0.097 [+0.051, +0.149] * (n 3,326, 88 clips) | Aayush's pre-registered secondary 10 |
| x264, k29 (my models, seeds 3-5) | +0.032 [+0.005, +0.061] * (n 3,326, 88 clips) | Aayush's pre-registered secondary 10 |
| x265, k0 (my models, seeds 3-5) | +0.166 [+0.109, +0.228] * (n 3,320, 88 clips) | **post-hoc, not pre-registered** |
| x265, k29 (my models, seeds 3-5) | +0.098 [+0.050, +0.145] * (n 3,320, 88 clips) | **post-hoc, not pre-registered** |

Source: `results_v1/test2/report_test2.md` (Aayush; secondary 10). My own re-run of this evaluation reproduces his
stored test2 rows exactly (10,320/10,320 per model) and both point estimates
(`results/test2_posthoc/summary_x264.md`, `experiments/p1/05_test2_posthoc/`). The x265 rows were evaluated once, after
all val results above were final, as a post-hoc check agreed with Aayush (not pre-registered); the val parity gate of
each model passed first (1,680/1,680 rows). BC alone on test2 is each run's own 20k checkpoint (its BC start):

| x265 test2, post-hoc, not pre-registered (n 3,320, 88 clips) | k0 | k29 |
|---|---|---|
| R3 - controller | +0.166 [+0.109, +0.228] * | +0.098 [+0.050, +0.145] * |
| BC start - controller | -0.340 [-0.431, -0.242] * | +0.140 [+0.087, +0.193] * |
| R3 - BC start | +0.506 [+0.420, +0.587] * | -0.042 [-0.067, -0.014] * |

Source: `results/test2_posthoc/summary_x265.md` (`experiments/p1/05_test2_posthoc/score_test2_p1.py --enc x265`, which
scores exactly as Aayush's test2 report; rows `r3k{0,29}[bc]_test2_x265.pkl`).

---

## 4. Interpretation (wording to keep)

- **R3 beats the controller at every lookahead on validation**, on both encoders (all CIs above 0), **except x264
  k2, which is not significant with 3 seeds** (Aayush's runs, +0.035; my single seed gives +0.072).
- **How much PPO adds over its BC start shrinks with k, to nothing measurable at k29** on both encoders (R3 - BC: x264
  +0.60 at k0 to +0.04 at k29, CI includes 0; x265 +0.52 to -0.03, CI includes 0). **At k29, BC alone already beats
  the controller** (x264 +0.057 \*, x265 +0.132 \*). In words: at small k PPO mostly repairs an imitation start that
  drifts in closed loop; at large k the imitation start is already good.
- **On x264, the BC start is worth about +0.10 to +0.14 dB at every k tested** (R3 - R2c +0.133, +0.095, +0.141 at
  k0, k5, k29, all significant), and **PPO from the standard start never beats the controller** (R2c - controller
  -0.064 \*, -0.018, -0.044 \*). So R3's gain needs both the imitation start and PPO.
- Absolute quality levels off around k5-k10 (x264 R3 score -0.289, -0.076, -0.038, -0.017, -0.044).
- **On test2 (fresh clips) R3 also beats the controller at k0 and k29**: x264 +0.097 \* / +0.032 \* (Aayush's
  pre-registered secondary), x265 +0.166 \* / +0.098 \* (**post-hoc, not pre-registered**). On x265 test2 at k29 the
  BC start alone already beats the controller (+0.140 \*) and R3 ends slightly below its own BC start (-0.042 \*): at
  full lookahead the PPO fine-tuning does not help and can cost a little.

**Do not claim:** that R3 uses lookahead better than the controller; that R3's edge over the controller grows or
shrinks with k, on either encoder (the CIs overlap at every k; on x264 the test2 ordering k0 > k29 is the reverse of
the val ordering; on x265 the k0 and k29 CIs overlap on both val and test2, so the order there is descriptive only); that
RL handles scene cuts better (cut/gradual slices are small and mostly not significant).

---

## 5. Limitations

- Validation only, except test2 for the k0 / k29 models: x264 (Aayush's pre-registered secondary) and x265 (post-hoc).
- The x265 test2 result is **post-hoc, not pre-registered** (models final before it was run; agreed with Aayush).
- R2c only on x264; R2c at k5 is one seed (seed 0).
- One seed at x264 k2 and k10; no k10 and no R2c on x265; the x265 k2 / k5 points are Aayush's runs.
- Aayush's 11-14 morning runs (k5 seeds 0-2) cannot be retrained bit-for-bit with today's code (his training code
  changed that day; evaluation did not); all results here use code that reproduces his seed 3-5 models exactly
  (`experiments/p1/04_r2c_control/README.md`).
- The R3 recipe (lambda 0.17, 180k checkpoint) was chosen on validation before this study, so the validation numbers
  are not fully held out, most of all at k5; test2 is the clean check.
- One resolution (320x180), 30-frame IPPP GOPs, one encoder setting per codec, PSNR only.

---

## 6. Provenance

| What | Code (branch `p1-fast-backend`) | Results (outside git) |
|---|---|---|
| shim, Gym env, parity | `encoder_shim.c`, `x264env/`, `tests/test_parity.py`, `P1_README.md` | - |
| fast backend | `x264env/rclib_backend.py`, `pavneet_pipeline/rclib/codec.py` (hook), `experiments/p1/01_shim_vs_cli_check/` | `shimcheck/` |
| PSNR cap, baselines | `experiments/p1/02_baseline_reproduction/` | `results/baselines_val/` |
| lookahead study, figure | `experiments/p1/03_r3_lookahead/` (jobs, `score_final_capped.py`, `make_kcurve_figure.py`) | `results/r3_kcurve/` |
| R2c control | `experiments/p1/04_r2c_control/` | `results/r3_kcurve/work/results_rl/*wu20k*` (no `bcinit`) |
| test2 | `experiments/p1/05_test2_posthoc/` | `results/test2_posthoc/` |
