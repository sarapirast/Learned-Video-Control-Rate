"""Run Sara's train_pid.py byte-for-byte unchanged, except that stream_rl.evaluate returns no rows for the test split
(val only before the single approved test pass; the test rows come from the final eval-only script).
  python pid_launch.py <train_pid.py args>      (cwd = exp_next/exp7/src_sara/p4, PYTHONPATH = Pavneet's repo copy)
"""
import runpy
import sys

from experiments import stream_rl as S

_eval = S.evaluate


def evaluate(act, infos, split, *a, **k):
    return [] if split == "test" else _eval(act, infos, split, *a, **k)


S.evaluate = evaluate
sys.argv = ["train_pid.py"] + sys.argv[1:]
runpy.run_path("train_pid.py", run_name="__main__")
