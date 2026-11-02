#!/bin/bash
# Decode data/raw/ into data/v1/<RES>/clips/<clip_id>.y4m, one array task per clip.
# Submit from the project root (the directory holding scripts/ and data/); logs go to logs/ there.
#
#   python3 scripts/decode_clips.py --make-tasks           # freezes data/v1/320x180/tasks.txt, prints N
#   sbatch --array=0-<N-1>%20 jobs/decode_v1.sbatch
#   python3 scripts/decode_clips.py --merge                # data/v1/320x180/manifest.csv
#
# Other resolution: sbatch --export=ALL,RES=640x360 ... (after --make-tasks --res 640x360).
# Other task list (e.g. a test): sbatch --export=ALL,TASKS=/path/to/list ...
#SBATCH --job-name=decode_v1
#SBATCH --partition=main
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:20:00
#SBATCH --output=logs/%x-%A_%a.out

set -euo pipefail
module purge
module load ver/2506 gcc/14.3.0 ffmpeg/7.1.1

RES=${RES:-320x180}
cd "$SLURM_SUBMIT_DIR"
[ -f scripts/decode_clips.py ] || { echo "submit from the project root (holds scripts/ and data/)"; exit 1; }
TASKS=${TASKS:-data/v1/$RES/tasks.txt}
echo "$(date '+%F %T') host=$(hostname) task=$SLURM_ARRAY_TASK_ID res=$RES tasks=$TASKS"
python3 -I scripts/decode_clips.py --res "$RES" --tasks "$TASKS" --task-index "$SLURM_ARRAY_TASK_ID"
