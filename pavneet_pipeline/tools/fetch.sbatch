#!/bin/bash
#SBATCH --account=rashidin_1753
#SBATCH --partition=main
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --job-name=rc_fetch
#SBATCH --output=/scratch1/pbanga/rcwork/logs/%x-%j.out
# usage: sbatch tools/fetch.sbatch [xiph|films|ugc|all]
set -uo pipefail
source /scratch1/pbanga/ee599/tools/job_env.sh
export FETCH_PAR=12
cd /scratch1/pbanga/ee599
bash tools/fetch_data.sh "${1:-all}"
