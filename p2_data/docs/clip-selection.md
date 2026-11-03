# Clip selection (draft, 2026-10-29)

The candidate clip list for P2 week 1 task 2. It's generated, not hand-maintained:

```bash
python3 scripts/select_clips.py      # reads config/clip_sources.csv, writes data/clip_candidates.csv
```

To change the list, edit `config/clip_sources.csv` (curated sources) or the UGC settings at the top of
`scripts/select_clips.py`, then rerun. Same inputs and `--seed` give the same list. Anything marked
**proposal** needs team agreement.

## Result

142 clips from 103 independent groups, ~1,345 GOPs at 30 frames.

| Split | Clips | Groups | GOPs | Clips with natural or likely cuts |
|---|---|---|---|---|
| train | 87 | 66 | 817 | 14 clips from 3 groups (BBB, Sintel, 1 UGC) + spliced clips (to add) |
| val | 21 | 16 | 195 | 8 clips from 3 groups (Sita Sings the Blues, 2 UGC) |
| test | 34 | 19 | 333 | 20 clips from 6 groups (Tears of Steel, Elephants Dream, rush_field_cuts, 3 UGC) |

**Priority 1** (fetch first): 103 clips, 982 GOPs. **Priority 2** (if time allows): 39 clips, 363 GOPs:
LDV 720p, HDgreetings, video conferencing, Netflix, the 4K-only UVG clips, and the 4th UGC clip per
category.

**38 of these clips (15 priority 1) are flagged for high frame rate** and wait on a team decision; see
the frame-rate rule below.

The plan's requirements and where each stands:
- Split by clip, never by GOP: met, and stricter. The split unit is the group (film, shoot or uploader),
  so segments of one film, or two UVG clips from one shoot, never straddle splits.
- At least 10 val clips: 23.
- Natural cuts in test; spliced clips train only: test cuts come only from films and real UGC edits.
- At least 40 cut GOPs in test from at least 5 clips: 20 cut-source clips from 6 groups. The estimate is
  ~50 cut GOPs from Tears of Steel and Elephants Dream alone (160 GOPs; with shots of ~3-4 s, about 30%
  of 30-frame GOPs contain a cut). **Not yet measured**: the cut detector confirms it.

## Sources

| Source | Clips | Licence | Why |
|---|---|---|---|
| Blender films: Big Buck Bunny, Sintel (+ trailer), Tears of Steel, Elephants Dream | 29 | CC BY 3.0 (ED: CC BY 2.5) | Natural hard cuts; ToS is the only live-action film |
| Sita Sings the Blues (archive.org, via Xiph) | 6 | CC0 1.0 | Natural cuts, 2D animation, different look from the Blender films |
| YouTube UGC | 54 | CC BY 4.0, per-uploader attribution | Real-world variety: 12 categories, wide complexity range |
| Xiph derf HD: SVT, TU Munich LDV, NTIA/VQEG, HDgreetings, conferencing | 33 | Mixed, see below | Standard codec test scenes, single shots (except rush_field_cuts) |
| UVG | 16 | CC BY-NC 3.0 | High-quality 4K camera footage |
| Netflix El Fuente / Chimera (via Xiph) | 4 | CC BY-NC-ND 4.0 | Professional camera footage |

**How the UGC clips were picked:**
- Categories: 12 of 16. Left out: HDR (needs tone mapping), VR (equirectangular), VerticalVideo (mostly
  portrait), Lyrics (3 clips).
- Only 16:9 clips, at 360p/480p where possible. Everything gets downscaled to ~320x180, so bigger sources
  only cost download time.
- 3 clips per category (priority 1) plus 1 more (priority 2), spread evenly over the dataset's own
  temporal-complexity score.
- One clip per uploader, so uploader is the group.
- Frame rate checked with ffprobe (cached in `data/meta/ugc_probe.tsv`). Clips the rule rejects are
  skipped, and the next-nearest clip in the same category takes their place.
- Plus one "likely cuts" clip in each of 6 edit-heavy categories: the highest chunk-complexity variation
  left. That's a weak proxy. The cut detector decides, and a clip that turns out to have no cuts just
  becomes a stable clip.

**Licence notes:**
- Everything here is fine for a non-commercial course project.
- Netflix (NoDerivatives) and NTIA/VQEG ("research purposes only"): don't publish the derived YUV. The
  repo holds only metadata and scripts anyway.
- The TU Munich LDV clips have no explicit licence; Xiph hosts them as "believed freely redistributable".
- UGC needs attribution per uploader. `data/meta/ugc_ATTRIBUTION.txt` has the lines; the README should
  carry them.

**Not used:**
- SD/CIF classics (foreman etc.): 4:3, 352x288 or smaller.
- Twitch gaming captures: UGC Gaming covers the genre.
- Netflix Open Content titles (Meridian, Sparks, Nocturne, Cosmos Laundromat): HDR/PQ masters only, so
  they'd need tone mapping. Cosmos Laundromat is the first to add if we want another cut source.
- The pilot's 21 clips: not on the list yet, because I don't have their identities (see open items).

## Frame-rate rule (decided 2026-10-29, updated 2026-11-02)

**Update 2026-11-02 (team decision):** the high-frame-rate sources are decimated by an integer factor
and then used like any other clip, keeping the splits they already had.
- **Factors:** 120 -> 30, 60/59.94 -> 30/29.97, 50 -> 25.
- **How:** `decode_clips.py` keeps source frames 0, N, 2N, ... (verified against independently extracted
  source frames) and writes the reduced rate in the y4m header.
- **Status:** these clips are now `fps_status = decimate`, not `flag-high-fps`.
- **Priority 1:** 15 clips: 5 SVT, 7 UVG (from the `.7z` archives, streamed through `7za`), and 3 UGC.
- **Short clips:** UVG's 120 fps clips give 150 frames (5 GOPs) each; ShakeNDry gives 75 (2 GOPs).
- **Superseded:** the "flagged, needing a decision" text below is kept for the record.

- **Accept only 23.976-30 fps sources.**
- **50/60 fps-family sources** (50, 59.94, 60, and their 100/120 multiples) are **flagged, not dropped**,
  pending a team decision. They're marked `fps_status = flag-high-fps` in `data/clip_candidates.csv`.
- **Any other rate is rejected.** That covers anything under 23.976 fps and odd rates like 45 fps.
- **Where it's enforced:** `fps_status()` in `scripts/select_clips.py`. A curated source that breaks the
  rule stops the script; a rejected UGC clip is replaced automatically.

**Applied on 2026-10-29.** These UGC clips were dropped and replaced from the same category:

| Dropped | Rate | Replacement |
|---|---|---|
| LyricVideo_360P-5e87 | 6 fps | LyricVideo_720P-2d24 (29.97) |
| CoverSong_360P-0a9d | 8.8 fps | CoverSong_360P-5a24 (29.97) |
| HowTo_360P-18e7 | 15 fps | HowTo_360P-127f (25) |
| Lecture_360P-27db | 15 fps | Lecture_360P-5594 (29.97) |
| Gaming_360P-2f99 | 45.3 fps (neither in range nor 50/60) | Gaming_360P-7acb (30) |

**Flagged, needing a decision** (38 clips; P1 = priority 1):

| Rate | Clips |
|---|---|
| 50 | SVT: crowd_run, park_joy, ducks_take_off, in_to_tree, old_town_cross (P1); LDV 720p: mobcal, parkrun, shields; UVG 50 fps set (8); UGC LyricVideo_720P-59ed (P1) |
| 59.94 / 60 | stockholm; conferencing (6); Netflix (4); UGC Gaming_360P-3eb6 (59.79), Sports_480P-0efe (P1) |
| 120 | UVG: Beauty, Bosphorus, YachtRide, HoneyBee, Jockey, ReadySetGo, ShakeNDry (P1), Lips |

The options for flagged clips:
- (a) drop them;
- (b) keep them, decimating to 25/30 fps by dropping frames (the current `decimate` column). This
  changes motion statistics, so a 120 fps clip decimated by 4 has 4x the frame-to-frame motion it was
  shot with, though it's still smooth;
- (c) keep them, but only in train.

Dropping all of them would remove all of UVG and SVT. That leaves the camera-footage side of the set to
LDV, NTIA and UGC.

## Processing rules (proposal)

1. **Frame rate:** see the rule above.
2. **Length:** at most 300 output frames per clip (10 GOPs at GOP 30). Films contribute 6-8 segments each,
   evenly spaced between 5% and 90% of the running time to skip titles and credits.
3. **Aspect and colour:** see the decode rules below.
4. **Trims:** NTIA clips drop their first and last 2 s, as the readme says. LDV 720p clips drop their
   leading mid-grey frames (already set in `start`).

## Decode rules (decided 2026-10-29)

`scripts/decode_clips.py`, run as the array job `jobs/decode_v1.sbatch`, turns `data/raw/` into the
clips everyone uses.

- **Output:** `data/v1/<W>x<H>/clips/<clip_id>.y4m`, 8-bit yuv420p. The y4m header carries size and fps.
- **Resolution:** a parameter (`--res`, default 320x180 from the pilot). Each resolution gets its own
  directory, so a change is one rerun next to the old output.
- **Frame rate:**
  - Native, with no conversion. A clip outside 23.976-30 fps is skipped and listed in
    `data/v1/<res>/skipped.csv`.
  - Frames are taken exactly as stored: input timestamps are regenerated at the source's constant rate
    (`-r` as an input option, `-fps_mode passthrough`), so ffmpeg never duplicates or drops a frame.
- **Geometry:**
  - Centre-crop the largest 16:9 region with even size and offsets, then lanczos scale
    (`lanczos+accurate_rnd+full_chroma_int`) to W x H, then `setsar=1`.
  - Sintel (1920x818) and Tears of Steel (1920x800) are stored already cropped to scope, with no bars,
    so they lose ~24% of the width (e.g. 1422x800 from x=248). Padding with black bars was rejected:
    it puts static black in ~24% of every frame and makes those clips look cheaper to encode than real
    content.
  - 854x480 UGC loses 2 columns; exact 16:9 sources aren't cropped.
- **Colour, by source type:**
  - YUV sources (Xiph y4m, UGC mkv): values pass through with no matrix conversion, only crop and
    scale. The original tags are recorded per clip in the manifest: UGC is 13 BT.601, 3 BT.709,
    35 untagged; Xiph is untagged.
  - RGB sources (Sintel/ToS PNG): converted to YUV with BT.709.
  - All outputs are limited range (`out_range=tv`); no accepted source is tagged full range.
  - 4:2:2 sources (NTIA): chroma is resampled to 4:2:0 by the same scaler.
- **Bit depth:**
  - Sources above 8 bits are scaled at their own depth and rounded to 8 bits without dither, as the last
    step of the scaler.
  - Tested: with a resize, swscale doesn't dither in any mode (none, ed, bayer and auto give identical
    output). Without a resize its default would dither, so `sws_dither=none` is set explicitly.
  - No accepted source is above 8 bits at the moment; only the flagged Netflix clips are 10-bit.
- **Known effect:** lanczos rings at sharp edges, so a few pixels land outside 16-235. Measured 0.02%
  (ToS) and 0.24% (ED, mostly chroma) of pixels, against 0% in the ED source. Bicubic rings about 4x
  less. These values are kept as the scaler produces them, not clipped.
- **Checks per clip** (the task fails if any fails):
  - fps within the rule, and matching the candidate list;
  - raw frame count matches `data/raw/index.csv` where it has one;
  - output header is W x H 4:2:0 at the source fps;
  - output holds exactly `n_frames` frames (from `clip_candidates.csv`).
- **Record:** `data/v1/<res>/meta/<clip_id>.json`, merged into `manifest.csv` by `--merge`. It holds the
  frames, fps, crop, filter chain, colour conversion, source tags, ffmpeg version and MD5.
- **Tested before the cluster run (2026-10-29):**
  - an output frame is byte-identical to the same source frame scaled independently;
  - `trim` starts on the right frame;
  - mean luma is preserved through YUV passthrough (134.48 in, 134.49 out);
  - the 1422x800 ToS crop is as calculated.
- **Not handled yet:** UVG `.7z` (all UVG clips are flagged), and the decimation of flagged clips.

## Downloading

`scripts/download_clips.py` fetches only what the clips use, into `data/raw/`:

| Source format | How it's fetched | Raw output |
|---|---|---|
| Xiph `.y4m` | HTTP range request for just the clip's frames | `<clip_id>.y4m` |
| `.y4m.xz` (BBB, ED, Sita) | streamed and decompressed once per film; only the segments are written | `<clip_id>.y4m` per segment |
| PNG dirs (Sintel, ToS) | only the segment's frames, each checked against the published SHA256SUMS | `<clip_id>/00000.png ...` |
| UGC `.mkv`, UVG `.7z` | whole file, resumable | `<clip_id>.mkv` / `.7z` |

- **Volume:**
  - Priority 1: 35.8 GB, plus ~4,200 PNGs (~11 GB).
  - Clips flagged for high frame rate are skipped by default. `--include-flagged` adds them (priority 1
    becomes 51.4 GB).
  - Priority 2 adds the Netflix ranges and the 4K UVG archives.
  - Output YUV at 320x180 is only ~4 GB.
- **Rerunning:** outputs are written as `.part` and renamed when complete, so a rerun skips finished
  clips and resumes or redoes the rest.
- **Index:** `data/raw/index.csv` records each clip's file and `first_src_frame`. Decode skips
  `start_frame - first_src_frame` frames, which is 0 except for UGC/UVG whole files.
- **Tested (2026-10-29):** a few frames of every format (y4m range, y4m.xz stream, PNG, mkv). The
  extracted frames are byte-identical (ffmpeg framemd5) to the same frames read directly from the source.

Run it on a transfer node: bulk downloads don't belong on login or compute nodes. It needs only Python
>= 3.6, no modules.

```bash
ssh hpc-transfer1.usc.edu
cd /scratch1/aayushso/ee599 && mkdir -p logs
python3 scripts/download_clips.py --dry-run                        # list and sizes, fetches nothing
nohup python3 scripts/download_clips.py > logs/download_p1.log 2>&1 &   # priority 1, ~30-60 min
tail -f logs/download_p1.log                                       # safe to log out; rerun to resume
```

Use `--priority 2` for everything, `--only a,b` for specific clips, and `--workers N` for parallelism
(default 4).

**Extracting the UVG `.7z` archives.** The archives are downloaded whole and extracted during decode
(a compute job), streamed straight into ffmpeg, so the raw `.yuv` never lands on disk. That matters for
the 4K ones: 600 frames are 7.5 GB raw.
- **Tool:** `module load gcc/13.3.0 p7zip/17.05` provides `7za`.
- **Module conflict:** p7zip needs gcc/13.3.0 but ffmpeg needs gcc/14.3.0, and Lmod allows only one
  compiler. So each side of the pipe loads its own modules in a subshell:

  ```bash
  (module purge; module load gcc/13.3.0 p7zip/17.05; 7za x -so data/raw/Beauty.7z "$YUV_NAME") |
  (module purge; module load ver/2506 gcc/14.3.0 ffmpeg/7.1.1;
   ffmpeg -f rawvideo -pix_fmt yuv420p -s 1920x1080 -r 120 -i - ...)
  ```

- **Tested:** on a synthetic 1080p 120 fps archive (LZMA2, like UVG's), the streamed frames, decimated
  by 4, are byte-identical to a direct read.
- **File names inside the archives:** unknown so far. Their headers are compressed, so they can't be
  read with range requests. Decode should run `7za l -slt` first and require exactly one `.yuv` inside.

**Split assignment** is by a hash of each group's name (~70/15/15). Adding or removing clips never moves
another group to a different split. The earlier position-based assignment did, so the 2026-10-29 rerun
also reshuffled some UGC splits once. Nothing had been downloaded or used yet.

## Cut labels (2026-10-29)

`scripts/cut_labels.py` runs on the decoded v1 clips: `--signals` (~0.6 s per clip), `--label`, `--review`.

**Signals per frame:**
- Luma-histogram change: 64 bins, total-variation distance to the previous frame, 0 to 1.
  - It's our re-implementation of the pilot's detector, so the bin count and distance still need
    checking against Pavneet's code.
  - The 0.35 threshold is the pilot's.
- `ffmpeg scdet` score, 0-100 (threshold 10, ffmpeg's default).
- Mean luma and the share of near-black pixels (Y <= 32), for fades.

**Results on the 88 clips:** 196 histogram cuts and 219 scdet cuts, but only 86 frames where both fire,
and 243 where they disagree.

**Review of disagreements:** 24 cases by eye, as previous | current | next frame:

| Type | Frames | Real cuts in sample | False positives were |
|---|---|---|---|
| Histogram only, scdet <= 2 | 83 | 1/6 | dark scenes, static slides, flat objects, motion blur |
| Histogram only, scdet 2-10 | 27 | 3/6 (+1 whip pan) | exposure flash, flat sky |
| scdet only, hist <= 0.1 | 61 | 1/6 | camera/game motion, jitter |
| scdet only, hist 0.1-0.35 | 72 | 6/6 | none in this sample |

**Provisional rule (`FINAL_RULE = 'evidence'`):**
- A cut if (scdet > 10 and hist > 0.10) or (hist > 0.35 and scdet > 2).
- Result: 185 cuts. Test has 51 cut GOPs from 18 clips / 7 groups, which meets the >= 40 / >= 5 target.
  Train has 56, val 27.
- ToS (23) and ED (15) supply 38 of the 51 test cut GOPs.
- Requiring both detectors would give only 21 test cut GOPs.

**Check on a random sample of 12 final cuts:** 8 real.
- All 7 frames where both detectors fired are real.
- 4 of the 5 frames added by the weak-evidence branch were false: flicker, fast camera turn, motion blur,
  static sky.
- So that branch is about 50/50, and its real and false cases have the same score ranges. No threshold
  separates them.

**Gradual:**
- Fades: 6 spans found, 5 real.
- The sixth is a motion-graphics title sliding in from black.
- Dissolve detection exists (`--dissolves`) but is untested.

**Visual review of all 99 uncertain frames.** These are the frames the rule calls cuts where only one
detector fired.
- **Two independent reviews, then settling:**
  - Claude and Aayush each reviewed all 99 frames from previous | current | next strips. Aayush's review
    was blind: random order, no detector scores, no Claude verdicts.
  - Agreement: 79/99 exact (80%), Cohen's kappa 0.64. On cut vs not-cut, which is what decides GOP
    labels: 88/99 (89%).
  - The 20 disagreements were re-viewed with 7-frame or 30-frame context and settled: 12 Claude's way,
    7 Aayush's, 1 neither. Typical causes:
    - stepped zooms in limited animation vs real reframing cuts;
    - teleports vs fast turns in game footage;
    - light build-ups that turn out to be fades to white;
    - whip transitions.
  - **Final verdicts:** 61 cut, 32 no cut, 6 gradual.
  - All are stored in `config/cut_review_v1.csv` with `claude_verdict`, `human_verdict`, `resolution`
    and a note. The human review files are in `data/v1/320x180/cuts/review/blind99/`.
- **First-pass verdicts (Claude):** 60 cut, 34 no cut, 2 gradual, 3 unsure. They're kept as
  `claude_verdict`.
- **What the 34 no-cuts are:** almost all flicker, VFX or fast motion within one shot. Examples:
  background light flicker in ED (7), hologram flicker in ToS (5), fast game-camera motion (8), static
  sky (3), and Sita's collage animation on a fixed starfield (4).
- **`aspen`** (listed as a single shot in the config) has real cuts.
- **How `--label` applies them:** each verdict overrides the rule for its frame. `unsure` counts as no
  cut; `gradual` adds a 3-frame gradual span.
- **Round 2 (Claude, 2026-10-29), from 5-frame strips:**
  - **All 144 frames the rule rejected.**
    - 4 missed cuts: a crowd cut in rush_field_cuts with near-identical colours, two game location jumps,
      and a strobe-edit reframing.
    - 1 unsure (game viewpoint jump).
    - 48 gradual: Sita fade to black (24), HowTo fade through white (10), music-video dissolves (9),
      ED fade-out (3), Sita dissolve (2).
    - 91 no cut: game-camera motion, static shots, exposure drift, flicker.
    - So the rule's rejections were mostly fades, not missed cuts. The ~1 in 6 estimate from the first
      sample was too high.
  - **16 random frames where both detectors fire.**
    - 14 cut, including one strobe edit.
    - 1 false: a Sintel character runs across the camera within one shot.
    - 1 unsure: a strobe frame.
    - Together with the first sample, 21 of 23 confirmed. The other 66 both-detector frames are taken
      as cuts without review.
  - These 160 verdicts have `resolution = claude only (...)`.
  - **Aayush's blind check** of 15 of them (`cuts/review/blind_round2/`): 10 agreed, 5 settled.
    - 2 went Aayush's way: a cut from black, a fast game turn.
    - 1 was agreement in substance: the cut Aayush marked is the already-labelled neighbouring frame.
    - 1 stays gradual: mid fade to black, luma 120 -> 16 over 25 frames.
    - 1 became unsure: game flick vs edit.
  - Aayush's question about black frames in MusicVideo_480P-7955 was checked: they're in the source
    YouTube file (a strobe effect), identical frame for frame in the raw mkv and our decode. They're not a
    pipeline artifact.
**Current labels (after round 2):**
- 141 final cuts.
- GOPs:

  | Split | Stable | Cut | Gradual |
  |---|---|---|---|
  | train | 424 | 49 | 5 |
  | val | 123 | 21 | 3 |
  | test | 201 | 49 | 5 |

- Test cut GOPs come from 18 clips / 7 groups.

**Dropped clip:**
- `Animation_360P-4b4c` (Webdriver Torso) is a synthetic test pattern: coloured rectangles replaced every
  30 frames, which matches the GOP length. Dropped 2026-10-29 via `config/exclude_clips.csv`.
- The selector replaced it with `Animation_480P-52af`: hand-drawn pencil animation, 29.97 fps, train.
  No other clip or split changed.
- Its verdicts stay in `config/cut_review_v1.csv` for the record. They're ignored because the clip is no
  longer decoded.

- Test cut GOPs come from 18 clips / 7 groups, which meets the >= 40 / >= 5 target. ToS supplies 23 of
  them and ED 12, so confidence intervals must resample by group.

**Labels:**
- A GOP is `cut` if a final cut falls inside it, not on its first frame. 15 GOPs have a cut exactly on
  their first frame; they're recorded (`cut_at_gop_start`) but not labelled `cut`.
- Outputs: `gops.csv`, `cuts/cut_frames.csv` (with a `review` column), `cuts/disagreements.csv`,
  `cuts/gradual.csv`.

## Dissolve detection (tested 2026-11-02; left off)

**The test:** `cut_labels.py --dissolves` flags an 8-frame window when the histogram change across it
exceeds 0.35 with no single-frame cut inside.
- **Result:** 60 candidate spans in 30 natural clips. 8 overlap a known gradual span.
- **Visual check of 16 of the other 52:**
  - 2 real dissolves;
  - 1 missed hard cut;
  - 1 unclear;
  - 12 false alarms: fast motion, game camera, stage-light colour changes, projector auto-exposure,
    collage animation.
- **Precision is roughly 1 in 6, so the detector stays off.** Gradual labels come from the fade rule and
  the visual reviews.

**The three spots it surfaced** were checked frame by frame and added to `config/cut_review_v1.csv`:
- `red_kayak` f148 is a hard cut both detectors narrowly missed (hist 0.338, scdet 8.5).
- `controlled_burn` f252-261 is a cross-dissolve.
- `ed_s00` f4-6 is cables sweeping past the camera, so not a dissolve.

Two train GOPs changed label. So the NTIA clips aren't all single shots: `aspen`, `red_kayak` and
`controlled_burn` contain edits.

## Spliced clips (2026-11-02)

`scripts/make_spliced.py` builds 6 train-only clips, `spliced_01`..`spliced_06`, following the pilot's
recipe.
- **Pieces:** each clip is 300 frames of random 20-70-frame pieces, with a fixed seed per clip.
- **Sources:** pieces come only from **train** clips. Consecutive pieces come from different clips, and
  one frame-rate class is used per clip:
  - 4 clips at ~30 fps, from 22 train clips at 29.97/30;
  - 2 clips at 25 fps, from 10 train clips.
  - The 24 fps class was skipped: it's almost all BBB/Sintel, which already have natural cuts.
- **No re-encoding:** frames are copied byte for byte from the decoded clips. All 42 pieces were
  verified identical to their source frames.
- **Exact labels:**
  - Every piece boundary is a cut (36), plus source cuts inside pieces (1) and source gradual spans.
  - `cut_labels.py` uses `spliced/cuts.csv` and `spliced/gradual.csv` for these clips instead of the
    detectors.
- **Each spliced clip is its own group** (`spliced:<id>`), all in train.
- **Effect:** +60 train GOPs (34 cut, 25 stable, 1 gradual). Train cut GOPs go from 49 to 83, and
  val/test are unchanged.
- **Detector check:** the automatic cut rule catches all 36 known boundaries (both detectors fire on 30).
  This is an upper bound on recall, since splices join unrelated clips and are easier than natural cuts.
- **To change the number or mix:** edit `PLAN` in the script and rerun it. Then rerun, in order:
  1. `decode_clips.py --merge`
  2. `cut_labels.py --signals --clip spliced_NN` for each spliced clip
  3. `cut_labels.py --label`
  4. `frame_features.py --siti`
  5. `data_readme.py`

## Frame features

**SI/TI (2026-10-29):** `scripts/frame_features.py --siti`.
- **Method:** ITU-T P.910, computed by ffmpeg's `siti` filter on the decoded 320x180 clips (what the
  encoder sees).
  - The filter expands limited-range luma to full range (x 255/219) and skips the 1-pixel border.
  - Checked against a plain-Python Sobel/difference implementation on riverbed frames 0-1: they match to
    0.01 (SI 80.85 vs 80.86, TI 26.90 vs 26.89).
  - TI of frame 0 is 0, since there's no previous frame.
- **Outputs:** `data/v1/320x180/features/siti/<clip_id>.csv`, merged into `features/siti.csv` (26,417
  rows, one per decoded frame).
- **Ranges** (clip means):
  - SI 32 (ED, dark) to 266 (checkerboard game).
  - TI 0.1 (a near-static lyric video) to 51 (a music video with fast cuts).

## Open items

- **Pilot clips:** get the 21 clip IDs and the 5 spliced clips from Pavneet. I'd propose keeping the
  pilot's test clips in test, for comparability, as long as that doesn't break a group.
- **Spliced clips:** make more of them, only from train groups.
- **Cut detection:** run it on everything, then update `cuts` and the test cut-GOP count.
- **Confidence intervals:** for P5, resample by `group`, not by clip. The test cut GOPs mostly come from
  two films.
- **Team decisions:** resolution, GOP length, the crop rule, and what to do with the 38 flagged
  high-frame-rate clips.
