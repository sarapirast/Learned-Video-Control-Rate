# Video for the live-stream experiments

The raw video is attached to the GitHub Release **`pavneet-live-stream-video`** of this repo (not in git history, so
cloning stays small). Only video whose licence allows redistribution is re-hosted; the rest is rebuilt from the
official sources with the dataset's own scripts (`../../p2_data/scripts/`).

## Release files

| Archive | Contents | Licence |
|---|---|---|
| `v1_clips_blender_sita.tar.xz` | 34 v1 clips: Big Buck Bunny, Sintel, Elephants Dream, Tears of Steel segments (`bbb_s*`, `sintel_s*`, `ed_s*`, `tos_s*`) and Sita Sings the Blues (`sita_s*`) | CC BY 3.0 / CC BY 2.5 / CC0 |
| `v1_clips_youtube_ugc.tar.xz` | 42 v1 clips from the YouTube UGC dataset (`<Category>_<res>P-<id>`) | CC BY 4.0 (per-clip credits: `data/v1/ugc_ATTRIBUTION_used.txt`) |
| `v1_clips_uvg.tar.xz` | 7 v1 clips from the UVG dataset (Beauty, Bosphorus, YachtRide, HoneyBee, Jockey, ReadySetGo, ShakeNDry) | CC BY-NC 3.0, non-commercial; cite Mercat et al., MMSys 2020 |
| `fresh_test_films_gops_320x180.tar.xz` | The fresh-film test set exactly as tested (D35 / D39): 384 GOPs = 12 segments × 32 GOPs from Elephants Dream and Tears of Steel | CC BY 2.5 / CC BY 3.0 |
| `SHA256SUMS` | Checksums of the archives | |

Format: v1 clips are 320×180 4:2:0 8-bit `.y4m`, 300 frames (dataset v1, `data/v1/manifest.csv` has each clip's
source, crop, filter chain, frame rate and MD5). Fresh-film GOPs are raw 320×180 4:2:0 `.yuv`, 30 frames each, named
`<film>@<first frame>.yuv` (frame index in our 320×180 film decode; segments evenly spaced between 2 % and 85 % of
each film, `../repo/tools/fresh_streams.py`). The fresh GOPs are the same for x265 and x264.

## Not re-hosted (rebuild from the sources)

26 of the 109 v1 clips are not redistributable here:

- 8 Xiph/NTIA clips (aspen, controlled_burn, red_kayak, rush_field_cuts, snow_mnt, speed_bag, touchdown_pass,
  west_wind_easy): "research use only".
- 5 Xiph/SVT clips (crowd_run, park_joy, ducks_take_off, in_to_tree, old_town_cross): SVT research-use terms.
- 7 Xiph/TU Munich LDV clips (blue_sky, pedestrian_area, riverbed, rush_hour, station2, sunflower, tractor): no
  stated licence.
- 6 spliced clips (`spliced_01`–`06`): each contains pieces of the clips above (`data/v1/spliced_pieces.csv`).

By split: train 20 of 66 clips, val 3 of 16 (aspen, blue_sky, snow_mnt), test 3 of 27 (park_joy, rush_field_cuts,
sunflower). Everything that uses curve lookups (all training and every result except the real-encoder check) needs no
video at all; only the real-encoder check (D40 / D43) and recomputing curves do.

To rebuild them, with Aayush's dataset scripts in `../../p2_data/` (sources and URLs: `../../p2_data/config/clip_sources.csv`;
the full candidate list: `data/v1/clip_candidates.csv`, which those scripts expect at `data/clip_candidates.csv`):

```bash
cd ../../p2_data
python3 scripts/download_clips.py --priority 2 --only aspen,blue_sky,controlled_burn,crowd_run,ducks_take_off,in_to_tree,old_town_cross,park_joy,pedestrian_area,red_kayak,riverbed,rush_field_cuts,rush_hour,snow_mnt,speed_bag,station2,sunflower,touchdown_pass,tractor,west_wind_easy
python3 scripts/decode_clips.py --make-tasks   # then run the decode tasks (jobs/decode_v1.sbatch), then:
python3 scripts/decode_clips.py --merge
python3 scripts/make_spliced.py --res 320x180  # spliced_01-06 (byte copies of decoded v1 frames, fixed seeds)
```

Check each rebuilt clip against the MD5 in `data/v1/manifest.csv`. (We have not re-run this rebuild ourselves; the
scripts are the ones that produced dataset v1.)

## Using the video with the code

Put all 109 `.y4m` clips in `$RC_WORK/clips/` (one work dir per encoder, as in `README.md`); the code cuts each
30-frame GOP into `$RC_WORK/gops/` on first use. For the fresh films, unpack the GOPs into `$RC_FRESHWORK/gops/`.

## Credits

- Big Buck Bunny, Sintel, Tears of Steel © Blender Foundation (CC BY 3.0); Elephants Dream © Blender Foundation /
  Netherlands Media Art Institute (CC BY 2.5); Sita Sings the Blues by Nina Paley (CC0). Sources: media.xiph.org.
- YouTube UGC: Y. Wang, S. Inguva, B. Adsumilli, "YouTube UGC Dataset for Video Compression Research", MMSP 2019;
  each clip is an audio-removed excerpt licensed CC BY 4.0 by its uploader (`data/v1/ugc_ATTRIBUTION_used.txt`).
- UVG: A. Mercat, M. Viitanen, J. Vanne, "UVG Dataset: 50/120fps 4K Sequences for Video Codec Analysis and
  Development", ACM MMSys 2020 (CC BY-NC 3.0).
- Dataset v1 (selection, cuts, 320×180 decode, budgets): Aayush Soni.
