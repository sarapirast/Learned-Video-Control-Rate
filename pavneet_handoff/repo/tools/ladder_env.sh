# D44: sourced by the ladder job scripts after job_env.sh. Needs RC_CODEC; LADDER_DIR (default rcwork_ladder) picks the
# work-dir root, so a debug test can use its own. Links the original dataset's clips/GOPs/scene fit (read only).
export RC_LADDER=1 RC_BUDGETS=30,34,38,42 RC_UNDER_PENALTY=1 RC_UNDER_TOL=3
LADDER_DIR=${LADDER_DIR:-/scratch1/pbanga/rcwork_ladder}
export RC_WORK=$LADDER_DIR/$RC_CODEC RC_REPORTS=/scratch1/pbanga/ee599/results/${RC_CODEC}_ladder
[[ $LADDER_DIR != /scratch1/pbanga/rcwork_ladder ]] && export RC_REPORTS=$LADDER_DIR/reports/$RC_CODEC
LADDER_SRC=/scratch1/pbanga/rcwork_wide; [[ $RC_CODEC == x264 ]] && LADDER_SRC=/scratch1/pbanga/rcwork_x264_wide
export LADDER_SRC
mkdir -p "$RC_WORK/logs" "$RC_REPORTS"
for f in clips gops manifest.json results_scenes; do
  [ -e "$RC_WORK/$f" ] || ln -s "$(readlink -f $LADDER_SRC/$f)" "$RC_WORK/$f"
done
