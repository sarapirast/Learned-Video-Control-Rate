# P2 plan: data, features and baselines (Aayush)

Read this when working on P2 tasks. `CLAUDE.md` has the short version; this file has the full plan,
draft file formats, and the review of Pavneet's pilot. Anything marked **(draft)** still needs team agreement.

## What P2 owns

- **Clip set:** sourcing, licences, scaling, decoding to YUV, splits.
- **Scene-cut labels** for every GOP.
- **Per-frame complexity features**, and the fixed-size lookahead summaries the policy sees.
- **Budgets per GOP**, and a causal base-QP estimator.
- **Every non-learned baseline,** including the x264 `rc-lookahead` curve and the fixed "spend early"
  pattern.
- **The analysis split** into cut vs stable GOPs, and the adaptive-lookahead result.
- **The report's** data and baselines section.

## Week by week

The project runs 5 weeks from 2026-10-26. Each week ends with a team checkpoint.

### Week 1: data v0, then the full data set

Do the encoder-independent items first (clips, splits, cut labels, SI/TI). The encoder-dependent items
(first-pass bits, budgets, R-D curves, baselines) wait for the encoder decision.

**1. v0 (Wednesday).** Repackage the pilot's 21 clips into the agreed formats (below) so P1, P3 and P5 can
start:
   - clip manifest
   - YUV files
   - GOP table with cut labels
   - native constant-QP R-D curves (QP 18-50) per GOP

**2. Full clip set (Friday).**
   - Size: ~80-150 clips.
   - Sources:
     - variety: Xiph derf, UVG, YouTube UGC (CC BY)
     - natural scene cuts: Blender open movies (Sintel, Tears of Steel, Big Buck Bunny, Elephants Dream)
       and Netflix Open Content
   - Split by clip, never by GOP.
   - At least 10 validation clips (the pilot had 2).
   - Natural cuts only in the test set. Spliced clips stay in train and are flagged in the manifest.
   - The test set needs at least 40 cut GOPs, from at least 5 different clips.

**3. Cut labels.**
   - Run the pilot's luma-histogram detector (change > 0.35) and ffmpeg `scdet`, and review a sample of
     the frames where they disagree.
   - Use three GOP classes: `stable`, `cut` (hard cut inside the GOP), `gradual` (fade or dissolve).

**4. Features.**
   - First-pass bits per frame, using the pilot's definition (ultrafast encode at QP 32) so results stay
     comparable.
   - SI/TI per frame.
   - Agree the lookahead summary with Sara (P4); see below.

**5. Budgets** and the base-QP estimator (below).

**6. Baselines started:**
   - native constant QP
   - fixed pattern with hindsight shift (reference)
   - causal fixed pattern

**7. Data README:**
   - clip and GOP counts per split
   - cut, gradual and stable counts per split
   - complexity histograms
   - licences

**Checkpoint:** manifest, YUV files, GOP table, feature files, budget table, R-D curves and the base-QP
estimator all exist, and the README describes them.

### Week 2: baselines at scale

Run every baseline on all GOPs × budgets as CARC job arrays.

- **Native constant QP:** the best constant QP that fits the budget. This is also the search's starting
  point for P3.
- **ABR+VBV:** the encoder's own rate control, with VBV sized to the GOP budget. This is the causal,
  production-style baseline.
- **CRF and two-pass:** references only. They use the encoder's own lookahead, so they are not causal.
- **`rc-lookahead` over the k grid:** gives a non-learned lookahead curve to set against the learned one.
  Run it with mb-tree off; report the defaults separately.
- **Fixed pattern:** IDR at q-6, P-frames ramping q-3 to q+3.
  - Hindsight-shifted version: reference only.
  - Causal version: the shift comes from the base-QP estimator, or a budget shield forces max QP when the
    remaining budget can't cover the remaining frames.

**Out:** a baseline table and the heuristic lookahead curve, all in the results-row format.

### Week 3: where does the search's gain come from?

- Split the search's gain and each baseline's gain into cut, gradual and stable GOPs.
- Plot the search's QP trajectories around cuts.
- **Key measurement:** how much does the search change QP *before* a cut, compared with *at or after*
  it?
  - Changes before a cut can only be captured with lookahead.
  - Changes at or after a cut are reachable at k = 0, because the current frame's cut flag is visible.
- Write down the expected shape of each Week 4 curve before the sweep runs.

**Out:** the gain breakdown and written hypotheses.

### Week 4: split every curve; adaptive lookahead

- Split every share-of-gain vs k curve into cut and stable GOPs.
- **Adaptive lookahead gate (no new training):** a causal cut detector picks a policy per frame.
  - Pair it with sub-policies that work. The pilot's gate failed because its k=2 and k=29 sub-policies
    were weaker than k=1.
  - Also test the pilot's suggested hybrid: the fixed rule on stable stretches, the learned policy
    around cuts.
  - Choose any thresholds on validation only.

**Out:** the split curves and the gating script.

### Week 5: evaluation and write-up

- Adaptive-lookahead figure: quality against average delay (frames of lookahead used).
- Write the data and baselines section of the report.

## Day 1-2 agreements that involve P2 (draft formats)

All tables are CSV or Parquet in `data/` and are produced by scripts.

| File | Key | Columns |
|---|---|---|
| `manifest.csv` | `clip_id` | source, url, licence, split, width, height, fps, n_frames, spliced, notes |
| `gops.csv` | `clip_id, gop` | start_frame, n_frames, label (stable/cut/gradual), cut_frames |
| `features.parquet` | `clip_id, frame` | gop, fp_bits, si, ti, hist_delta, scdet_score, cut_flag |
| `rd_native.parquet` | `clip_id, gop, qp` | bits, psnr_mean_frames, mse_mean, psnr_from_mse |
| `budgets.csv` | `clip_id, gop, level` | budget_bits, how_set, base_qp_est |
| results rows (shared with all) | `run_id` | method, arm, k, seed, clip, gop, budget, bits, psnr, vmaf, overshoot, shield_fires |

`rd_native` stores both PSNR conventions, because the team hasn't picked one yet.

## Lookahead summary features (draft, agree with Sara / P4)

The pilot's policy got worse as k grew, because its inputs grew from about 10 numbers to about 70.
Fixed-size summaries remove that confound. For frame t and window t+1..t+k:

- **Mean and max first-pass bits** in the window, divided by the running mean of first-pass bits over
  frames 0..t. This is causal normalisation.
- **Frames until the next cut** in the window. Use k+1 if there is none.
- **Cut in window:** 0 or 1.
- **Window length:** k itself. At k = 0 the summaries are zero and this flag tells the policy so.

## Budget definition (draft P2 proposal)

**The problem with the pilot's definition.** The pilot sets the budget B to native constant-QP spend at q,
and puts q in the state. Finding q needs the whole GOP encoded, which makes q hindsight.

**Proposal:**
- **What the policy sees:** only B, as bits per frame per pixel.
- **Budget levels:** 3-4 per GOP, taken from native or CRF encodes. Record how each one was set in
  `how_set`.
- **Base QP:** comes from a causal estimator fitted on train only. A simple model to start:
  `q_hat = a + b*log(B/T/pixels) + c*log(fp_bits of frame 0)`.
  Report its MAE in QP on validation.

## Pilot review (Pavneet, `docs/Report.pdf`, 2026-10-26)

**Setup.**
- Encoder: x265, AQ and cutree off.
- Video: 320x180, 30-frame P-only GOPs.
- Clips: 12 train (5 spliced), 2 val, 7 test.
- Test set: 140 cases = 70 GOPs × 2 budgets, 32 of them with cuts.

**Numbers (bits saved vs native at equal PSNR).**

| Method | All GOPs | Cut GOPs | Stable GOPs | Note |
|---|---|---|---|---|
| Hindsight search | 7.65% | 15.0% | 5.5% | upper reference |
| Fixed rule, hindsight shift | 3.47% | 5.3% | 2.9% | 0% over budget |
| CQL+PPO, k=0 (chosen on validation) | 3.05% | 5.9% | 2.2% | 1% over budget |
| BC | 1.65% | | | |

**What it found:**
- The learned policy is tied with the fixed rule overall.
- It wins on cut GOPs by +1.2 to +3.5 points and loses about 1 point on stable GOPs.
- Learning from every plan the search tried (offline RL) roughly doubles BC.

**Issues P2 should account for:**
1. **Possible leak through the base plan.** Does the residual policy correct the *shifted* pattern? If
   so, the k=0 policy isn't causal.
2. **q in the state is hindsight.** This is fixed by the budget proposal above.
3. **The headline configuration was picked on test.** Validation had only 2 clips, so it couldn't choose.
   More validation clips is a P2 fix.
4. **Confidence intervals resample cases, not clips,** so they are too narrow. Grouping by clip only
   works with enough clips per split.
5. **Test-set cuts:** unclear whether they are natural or spliced. Record it in the manifest.
6. **The search is weak:** 2 × 300 encodes of hill-climbing. P3 owns this, but it needs P2's
   best-feasible constant QP as its start.

## Cut list (if a week slips)

Drop these in order:
1. the `rc-lookahead` defaults run (keep mb-tree off)
2. the `gradual` class (merge it into `cut`)
3. growing the clip set past ~80

Keep no matter what:
- validation of at least 10 clips
- natural cuts in the test set
- the cut/stable split
- the causal fixed-pattern baseline

## Dependencies

| Person | P2 needs from them | They need from P2 |
|---|---|---|
| Ahhana (P1) | Encoder decision and frozen settings | Clips, YUV, features |
| Atharva/Pavneet (P3) | Pilot code: cut detector, first-pass, fixed pattern; the leak answers | GOPs, budgets, best feasible constant QP |
| Atharva/Pavneet (P5) | Shared directory, results format | R-D curves, cut labels |
| Sara (P4) | Agreement on the lookahead summary | The feature spec |
