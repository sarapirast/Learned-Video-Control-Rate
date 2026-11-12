#!/bin/bash
# Download all public test video and convert each source to a 320x180 yuv420p y4m in $RC_WORK/clips.
# Sources: Xiph derf (CIF, 720p, 1080p), Blender films (BBB, Elephants Dream, Sintel trailer + full film,
# Tears of Steel), YouTube UGC 360P (up to UGC_PER_CAT clips per category).
# Resumable: a clip whose final .y4m exists is skipped. Small raw sources are kept in $RC_WORK/src; big ones are
# streamed straight into the downscaler and never stored at full size.
# usage: RC_WORK=/scratch1/pbanga/rcwork bash tools/fetch_data.sh [xiph|films|ugc|all]
set -uo pipefail
: "${RC_WORK:?set RC_WORK}"
WHAT=${1:-all}
UGC_PER_CAT=${UGC_PER_CAT:-10}
PAR=${FETCH_PAR:-4}
SRC=$RC_WORK/src; CLIPS=$RC_WORK/clips; LOG=$RC_WORK/fetch.log
mkdir -p "$SRC" "$CLIPS"
XIPH=https://media.xiph.org/video/derf/y4m

# centre-crop to 16:9, scale to 320x180, 8-bit 4:2:0, keep every source frame (no fps change)
VF="crop='min(iw,ih*16/9)':'min(ih,iw*9/16)',scale=320:180:flags=lanczos,format=yuv420p"

log() { echo "$(date +%T) $*" | tee -a "$LOG"; }

# convert <input (file or url or -)> <clip name> [extra ffmpeg input args]
convert() {
  local in=$1 name=$2; shift 2
  local out=$CLIPS/$name.y4m
  [[ -s $out ]] && return 0
  if ffmpeg -nostdin -loglevel error -y "$@" -i "$in" -an -sn -vf "$VF" -strict -1 -f yuv4mpegpipe "$out.part"; then
    mv "$out.part" "$out"; log "OK   $name $(( $(stat -c %s "$out") / 86400 )) frames"
  else
    rm -f "$out.part"; log "FAIL $name"; return 1
  fi
}

# fetch_keep <url> <file in $SRC>: download and keep (small sources)
fetch_keep() {
  local url=$1 f=$SRC/$2
  [[ -s $f ]] && return 0
  curl -sSfL --retry 3 -o "$f.part" "$url" && mv "$f.part" "$f" || { rm -f "$f.part"; log "FAIL download $url"; return 1; }
}

xiph_one() {
  local f=$1 name=${1%.y4m}
  fetch_keep "$XIPH/$f" "$f" && convert "$SRC/$f" "xiph_$name"
}
export -f xiph_one fetch_keep convert log
export SRC CLIPS LOG XIPH VF

do_xiph() {
  log "== xiph"
  # CIF 4:2:0 at full rate (the *_15fps variants and 4:2:2 versions are duplicates)
  local cif="akiyo bowing bridge_close bridge_far bus city coastguard container crew deadline flower football foreman
    hall_monitor harbour highway husky ice mad900 mobile mother_daughter news pamphlet paris sign_irene silent soccer
    stefan students tempete waterfall"
  local hd="720p50_mobcal_ter 720p50_parkrun_ter 720p50_shields_ter 720p5994_stockholm_ter ducks_take_off_420_720p50
    in_to_tree_420_720p50 old_town_cross_420_720p50 park_joy_420_720p50 vidyo1_720p_60fps vidyo3_720p_60fps
    vidyo4_720p_60fps"
  # 1080p sources are 1-4 GB each: stream them, don't keep
  local fhd="aspen_1080p blue_sky_1080p25 controlled_burn_1080p crowd_run_1080p50 dinner_1080p30 factory_1080p30
    life_1080p30 pedestrian_area_1080p25 red_kayak_1080p riverbed_1080p25 rush_field_cuts_1080p rush_hour_1080p25
    snow_mnt_1080p speed_bag_1080p station2_1080p25 sunflower_1080p25 touchdown_pass_1080p tractor_1080p25
    west_wind_easy_1080p"
  { printf '%s_cif.y4m\n' $cif; printf '%s.y4m\n' $hd; } | xargs -P "$PAR" -I{} bash -c 'xiph_one {}'
  for n in $fhd; do echo "$n"; done | xargs -P "$PAR" -I{} bash -c 'convert "$XIPH/{}.y4m" "xiph_{}"'
}

do_films() {
  log "== films"
  # Xiph's y4m.xz masters: stream through xz into the downscaler
  local n
  for n in big_buck_bunny_720p24 elephants_dream_720p24 sintel_trailer_2k_720p24; do
    [[ -s $CLIPS/film_$n.y4m ]] && continue
    curl -sSfL --retry 3 "$XIPH/$n.y4m.xz" | xz -dc | convert - "film_$n" -f yuv4mpegpipe
  done
  # Blender's distributed encodes (no y4m master available)
  convert https://download.blender.org/demo/movies/ToS/tears_of_steel_720p.mov film_tears_of_steel
  convert https://download.blender.org/durian/movies/Sintel.2010.1080p.mkv film_sintel   # 720p is only offered zipped
}

ugc_one() {
  local obj=$1 name; name=$(basename "$obj" .mkv)
  [[ -s $CLIPS/ugc_$name.y4m ]] && return 0
  fetch_keep "https://storage.googleapis.com/ugc-dataset/$obj" "$name.mkv" && convert "$SRC/$name.mkv" "ugc_$name" \
    && rm -f "$SRC/$name.mkv"   # raw UGC is ~200 MB per clip; the 320x180 copy is what's used
}
export -f ugc_one

do_ugc() {
  log "== ugc (<= $UGC_PER_CAT per category)"
  local cats="Animation CoverSong Gaming HowTo Lecture LiveMusic LyricVideo MusicVideo NewsClip Sports TelevisionClip
    VerticalVideo Vlog"
  local c
  for c in $cats; do
    # deterministic choice: first UGC_PER_CAT objects in name order
    curl -sSf "https://storage.googleapis.com/storage/v1/b/ugc-dataset/o?prefix=original_videos/$c/360P/&fields=items(name)&maxResults=1000" \
      | python -c "import sys,json; [print(i['name']) for i in sorted(json.load(sys.stdin).get('items',[]), key=lambda i:i['name'])[:$UGC_PER_CAT]]"
  done | xargs -P "$PAR" -I{} bash -c 'ugc_one {}'
}

case $WHAT in
  xiph1) xiph_one "$2" ;;   # test one Xiph file, e.g. akiyo_cif.y4m
  xiph) do_xiph ;; films) do_films ;; ugc) do_ugc ;;
  all) do_xiph; do_films; do_ugc ;;
  *) echo "unknown: $WHAT"; exit 1 ;;
esac
log "== done ($WHAT): $(ls "$CLIPS"/*.y4m 2>/dev/null | wc -l) clips, $(stat -c %s "$CLIPS"/*.y4m 2>/dev/null | awk "{s+=\$1} END {printf \"%.1f\", s/1e9}") GB"
