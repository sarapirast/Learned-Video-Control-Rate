# Feature spec: DRAFT for P2 + P4 (Aayush, Sara)

Status: draft, 2026-11-02. Nothing here is final until Sara agrees. The **Questions** section at the end
lists what needs deciding.

## 1. Per-frame feature table

**File:** `data/v1/<res>/features/frames.parquet`, built by `scripts/build_features.py`.
- One row per frame, full GOPs only.
- Today: 28,200 rows = 940 GOPs x 30 frames, 94 clips.

| Column | Type | Meaning | Usable in the policy state? |
|---|---|---|---|
| `clip_id`, `split`, `group` | category | identity; `group` is the split unit | no |
| `gop`, `pos_in_gop`, `frame` | int32 | GOP index in the clip, frame index within the GOP (0 = IDR), frame index in the clip | `pos_in_gop` yes |
| `gop_label` | category | `stable` / `cut` / `gradual` from the **reviewed** labels | **no** (analysis only) |
| `fp_bits` | float32 | first-pass bits (pilot: ultrafast encode at QP 32) | yes. **Empty until the encoder is decided** |
| `si`, `ti` | float32 | ITU-T P.910 spatial / temporal information | yes (cheap complexity proxies) |
| `hist_delta`, `scdet_score` | float32 | raw cut-detector signals | yes |
| `y_mean` | float32 | mean luma | yes |
| `cut_flag` | int8 | **automatic** cut detector (deployable: no human review) | yes |
| `cut_label` | int8 | **reviewed** cut label (human + Claude review) | **no** (analysis only) |

**Policy flag vs analysis label.** These are deliberately two columns.
- **What the policy sees:** `cut_flag`, because that's all a live encoder would have.
- **What the results are split by:** `cut_label` and `gop_label`.
- **How they differ:** on natural clips, `cut_flag` finds 97% of reviewed cuts (138/142). But 22% of its
  alarms are false positives (flicker, fades, fast motion), with precision 78%. So the policy is trained
  and evaluated with a realistically noisy flag.

## 2. Lookahead summary (fixed size for every k)

**Why a fixed size:** the pilot's state grew from about 10 to about 70 numbers as k grew, which mixed
"more lookahead" with "harder learning problem". A fixed-size summary keeps the state the same size for
every k.

**Reference implementation:** `scripts/lookahead.py`, function `summary(complexity, cut_flags, t, k)`.
- **Causal:** normalisation uses frames 0..t only.
- **Window:** frames t+1..t+k, **clipped at the GOP end**, since the budget is per GOP.

| Feature | Definition |
|---|---|
| `la_len` | frames actually visible in the window (< k near the GOP end) |
| `la_mean` | mean complexity in the window / running mean over frames 0..t |
| `la_max` | max complexity in the window / the same running mean |
| `la_cut` | 1 if `cut_flag` fires anywhere in the window |
| `la_frames_to_cut` | frames ahead to the first flagged cut; k+1 if none |
| `frames_to_gop_end` | 29 - `pos_in_gop` for 30-frame GOPs |

**At k = 0** every window feature is 0 (and `la_frames_to_cut` = 1). Together with `la_len` = 0, that
tells the policy it has no lookahead.

**Proposed approach:** compute the summary on the fly from `frames.parquet` (in the env and in training),
not as one stored file per k. One table then serves every k on the grid, and P1 and P4 share one
definition.

## 3. Questions for Sara

1. **Complexity input:** `fp_bits` once it exists. Until the encoder is decided, should training
   prototypes use `si` (or `si * ti`) as a stand-in?
2. **Normalisation:** running mean over the current GOP so far (the proposal), or over the clip so far,
   which carries information across GOP boundaries?
3. **Window clipping at the GOP end:** agreed? The alternative is letting the window see into the next
   GOP, which doesn't affect this GOP's budget.
4. **k grid:** the pilot used 0, 1, 2, 5, 10, 29. Keep it?
5. **Extra state from P2:**
   - Should `si`/`ti` of the current frame enter the state?
   - Should `cut_flag` of the current frame enter it? Visible at k = 0, since the encoder sees the
     current frame.
6. **Budget features:** these depend on the budget definition (`docs/p2-plan.md`, policy sees only B).
   They're out of scope here.
