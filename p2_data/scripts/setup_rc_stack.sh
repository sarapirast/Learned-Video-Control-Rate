#!/bin/bash
# Build the stack needed to run Pavneet's pipeline (repo-pavneet/) on data v1.
#   x265 4.1 (static CLI)  -> /scratch1/aayushso/envs/codecs/bin/x265
#   x264: CARC module x264/20250608 (0.165.3222), not built
#   Python env             -> /scratch1/aayushso/envs/rc (py3.12, torch CPU, SB3, gymnasium, ffmpeg)
# Re-runnable: each part is skipped when its output already exists. Usage: bash scripts/setup_rc_stack.sh [codecs|env|all]
set -euo pipefail
WHAT=${1:-all}
PFX=/scratch1/aayushso/envs/codecs
ENV=/scratch1/aayushso/envs/rc
SRC=/scratch1/aayushso/src
export TMPDIR=/scratch1/aayushso/tmp CONDA_PKGS_DIRS=/scratch1/aayushso/conda_pkgs
mkdir -p "$SRC" "$TMPDIR" "$PFX"
J=$(nproc)

codecs() {
  module purge
  module load gcc/13.3.0 nasm 2>/dev/null || module load gcc/13.3.0
  if [[ ! -x $PFX/bin/x265 ]]; then
    [[ -d $SRC/x265 ]] || git clone -q https://bitbucket.org/multicoreware/x265_git.git "$SRC/x265"
    cd "$SRC/x265" && git checkout -q 4.1
    mkdir -p build/v1 && cd build/v1
    /usr/bin/cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX=$PFX -DENABLE_SHARED=OFF ../../source >cmake.log
    make -j"$J" >make.log 2>&1 && make install >/dev/null
  fi
  "$PFX/bin/x265" --version 2>&1 | grep -m1 -i 'version'
  # x264: not built; jobs use the CARC module x264/20250608 (0.165.3222, one commit from Pavneet's 3223)
}

env() {
  module purge
  module load conda/25.11.0
  if [[ ! -x $ENV/bin/python ]]; then
    mamba create -y -q -p "$ENV" -c conda-forge python=3.12 numpy scipy pandas scikit-learn matplotlib \
      gymnasium ffmpeg pip
    "$ENV/bin/pip" install -q --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
    "$ENV/bin/pip" install -q --no-cache-dir stable-baselines3 sb3-contrib
  fi
  "$ENV/bin/python" -c "import torch, stable_baselines3 as s, gymnasium as g, numpy as n; print('torch', torch.__version__, 'sb3', s.__version__, 'gym', g.__version__, 'numpy', n.__version__)"
}

case $WHAT in codecs) codecs ;; env) env ;; all) codecs; env ;; esac
