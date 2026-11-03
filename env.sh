# EE599 RL-QP project environment.
# Usage (interactive or at the top of a SLURM script):
#   source <repo>/env.sh
#
# CARC modules provide the compiler, the x264 library and ffmpeg; Python
# (numpy, gymnasium) comes from a conda env. No python module is loaded, so
# the two Pythons never shadow each other.
#
# One-time env creation (package cache on scratch, not /home1):
#   module purge && module load conda/25.11.0
#   export CONDA_PKGS_DIRS=/scratch1/$USER/conda_pkgs
#   mamba create --prefix /scratch1/$USER/envs/ee599 -c conda-forge --file environment.lock.txt
# environment.lock.txt = P2's p2_data/environment.lock.txt + gymnasium.
# Use another env location by setting EE599_ENV before sourcing this file.

module purge
module load ver/2506 gcc/14.3.0 x264/20250608 ffmpeg/7.1.1 conda/25.11.0
eval "$(conda shell.bash hook)"
conda activate "${EE599_ENV:-/scratch1/$USER/envs/ee599}"
