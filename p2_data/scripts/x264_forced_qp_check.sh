#!/bin/bash
# Forced-QP check: does x264 encode the per-frame QPs asked for in a qpfile? Prints requested vs actual QP per frame.
set -e
G=/scratch1/aayushso/rcwork_v1/x264_orig/gops/Animation_360P-3e40@0.yuv
D=/scratch1/aayushso/tmp/qpcheck
# requested: I at 28; P frames sweep offsets around base 34, plus extremes 11 and 51
REQ=(28 31 37 40 25 11 51 45 34 28 40 22 46 34 30 38 34 34 26 42 34 34 34 20 48 34 34 34 34 34)
: > $D/qp.txt; for i in "${!REQ[@]}"; do t=P; [[ $i == 0 ]] && t=I; echo "$i $t ${REQ[$i]}" >> $D/qp.txt; done
COMMON="--demuxer raw --input-res 320x180 --input-csp i420 --fps 30 --keyint 30 --min-keyint 30 --no-scenecut --bframes 0 --threads 1 --frames 30 --verbose"
run() { name=$1; shift; x264 $COMMON "$@" --qpfile $D/qp.txt -o $D/$name.264 $G 2>&1 | grep -E "frame= *[0-9]+ QP=" | sed -E 's/.*frame= *([0-9]+) QP=([0-9.]+).*/\2/' > $D/$name.qp; }
run pavneet_crf --preset fast --aq-mode 0 --no-mbtree --crf 28
run pavneet_qp  --preset fast --aq-mode 0 --no-mbtree --qp 28
run ahhana      --preset medium --aq-mode 0 --no-mbtree --no-psy --qp 31 --ipratio 10 --pbratio 10
run medium_crf  --preset medium --aq-mode 0 --no-mbtree --no-psy --crf 28
printf "%3s %4s %12s %11s %7s %11s\n" frame req pavneet_crf pavneet_qp ahhana medium_crf
paste <(seq 0 29) <(printf '%s\n' "${REQ[@]}") $D/pavneet_crf.qp $D/pavneet_qp.qp $D/ahhana.qp $D/medium_crf.qp | awk '{printf "%3d %4d %12s %11s %7s %11s\n",$1,$2,$3,$4,$5,$6; for(c=3;c<=6;c++) if ($c+0!=$2) bad[c]++} END{printf "mismatches: pavneet_crf=%d pavneet_qp=%d ahhana=%d medium_crf=%d (of 30)\n", bad[3]+0, bad[4]+0, bad[5]+0, bad[6]+0}'
