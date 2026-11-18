# P1 experiments (x264, val only)

Experiments by P1 (Ahhana) on top of the shim backend (`RC_BACKEND=shim`, see `P1_README.md` at the repo root): the
team's rclib environment with P1's x264 shim instead of the x264 command line, identical results and ~13× faster.
Test was never used. Each folder has its own README (question, runs, how to rerun, checks, results).

**Paths:** the scripts use absolute paths: my scratch (`/scratch1/ahhanagu/ee599/`, all outputs, outside git), this
repo clone, and Aayush's read-only inputs and Python envs (`/scratch1/aayushso/`: data, infos, search plans, stored
runs, `envs/rc` for encodes/training, `envs/ee599` for scoring). They are a record of what ran; to rerun elsewhere,
change the paths at the top of each script (for 03/04: `env.sh`). Data, logs, models and result files are not in git.

## Experiments
**[01 · Shim vs CLI check](01_shim_vs_cli_check/).** final4 and R3 on 10 val GOPs × 4 budget levels with both
backends: per-frame QPs, bits, PSNR and score identical on 40/40 episodes; 12–13× faster (R3 training ~33 → ~4 min).

**[02 · Baseline reproduction](02_baseline_reproduction/).** final4 at k 0/2/5/10/29 and R3 k5 (seeds 3–5) re-run
on all of val; R3 reproduced exactly, final4's bits exactly. Found that final4's stored PSNR was not capped at 100 dB
per plane while the learners' was; Aayush adopted one cap (val x264 R3 − final4 +0.077, cut/gradual +0.069).

**[03 · R3 across lookahead](03_r3_lookahead/).** R3 and its BC start at k 0, 2, 5, 10, 29 (3 seeds at k0/k5/k29).
R3 beats final4 by +0.07 to +0.10 dB at every k; the BC start goes from far below final4 (k0) to above it (k ≥ 10),
so PPO matters most for live encoding. k5 retrains are bit-identical to Aayush's models. Provisional scores.

**[04 · R2c control](04_r2c_control/).** R3 without the BC start at k0 and k29 (seeds 3–5), for the BC-start effect.
Runs complete, not scored yet; the k5 reproduction check against Aayush's stored R2c failed (likely a code-version
difference on 11-14, see the folder README).

## Lessons learned
- **Train BC networks one after the other, not in parallel.** `bc_train.py` uses as many torch threads as the job has
  cores; two at once oversubscribe them and run ~20× slower (job 14304096 timed out).
- **`env.sh` strict-mode fix.** Job scripts use `set -euo pipefail`, but `/etc/profile` (`lang.sh`: `LC_ALL` unbound)
  and Lmod are not safe under `set -u`: switch it off while they load (the first prep job died after 2 s, empty log).
- **Set `RC_METRIC=dpsnr`.** Without it rclib's `res` arm scores with the old % saving metric (bits/actions unchanged).
- **Git: fetch from the login node if a compute node is slow.** The first fetch on a compute node timed out (the remote
  holds large result pickles); later fetches took seconds.
- **Merge `main` into a shared branch; don't rebase it.** Rebasing would flatten the p1 merge and need a force-push.
- **Fit on held-out data does not predict closed-loop quality for BC** (k0 fits best and drifts worst; k29 the reverse).
- **One scoring convention everywhere:** rescore every method with the same function, curves and PSNR cap before
  comparing; a mixed convention moved the team's x264 cut/gradual number from +0.016 to +0.069.
