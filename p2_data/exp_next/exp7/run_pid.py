"""Exp 7: retrain Sara's PID-Lag PPO with her train_pid.py unchanged via pid_launch.py (test eval skipped; commit 1860557, copy in exp_next/exp7/src_sara),
on train, her defaults (target 5 %, Kp 2, Ki 0.05, 2M steps): ppo_pid and bc_ppo_pid at L = 2, seeds 0-2, run in
parallel. Work dir = our copy of Pavneet's artifacts (/scratch1/aayushso/rcwork_exp7/<enc>_v1); logs to
results_v1/next/exp7/pid_logs/. Pre-registration: exp_next/exp7/PREREG.md Part 1c.

  RC_CODEC=<enc> python exp_next/exp7/run_pid.py [--steps N] [--work DIR]
"""
import argparse
import os
import subprocess
import sys

E7 = "/scratch1/aayushso/ee599/exp_next/exp7"
ap = argparse.ArgumentParser()
ap.add_argument("--steps", type=int, default=0, help="smoke only; 0 = her default (2M)")
ap.add_argument("--work", default=None)
ap.add_argument("--seeds", default="0,1,2")
a = ap.parse_args()
enc = os.environ["RC_CODEC"]
env = dict(os.environ, RC_WORK=a.work or f"/scratch1/aayushso/rcwork_exp7/{enc}_v1", RC_V1="1",
           RC_BUDGETS="24,30,36,42", PYTHONPATH=f"{E7}/src_pavneet/pavneet_handoff/repo")
logs = f"/scratch1/aayushso/ee599/results_v1/next/exp7/pid_logs{'_smoke' if a.steps else ''}"
os.makedirs(logs, exist_ok=True)
procs = []
for bc in (False, True):
    for s in [int(x) for x in a.seeds.split(",")]:
        args = [sys.executable, "-W", "ignore", f"{E7}/pid_launch.py", "--look", "2", "--seed", str(s)] + \
               (["--bc"] if bc else []) + (["--steps", str(a.steps)] if a.steps else [])
        f = open(f"{logs}/{'bcpid' if bc else 'pid'}_{enc}_L2_s{s}.txt", "w")
        procs.append((args, subprocess.Popen(args, cwd=f"{E7}/src_sara/p4", env=env, stdout=f, stderr=subprocess.STDOUT)))
rc = [p.wait() for _, p in procs]
for (args, _), r in zip(procs, rc):
    print(r, " ".join(args[4:]))
sys.exit(max(rc))
