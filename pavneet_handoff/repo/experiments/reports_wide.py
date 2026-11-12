"""Reports of the wide-budget study (D28) for $RC_CODEC / $RC_WORK, written to $RC_REPORTS: the standard reports
(reports.py), the breakdown and constraint analyses, and the per-budget report. A failing step is noted and skipped."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [["reports.py"], ["breakdown.py"], ["constraint.py"], ["budgets.py"]]

if __name__ == "__main__":
    assert os.environ.get("RC_REPORTS"), "set RC_REPORTS so the two-budget reports are not overwritten"
    for s in STEPS:
        r = subprocess.run([sys.executable, "-W", "ignore", os.path.join(HERE, s[0]), *s[1:]])
        print(f"== {' '.join(s)}: {'ok' if r.returncode == 0 else f'FAILED rc={r.returncode}'}", flush=True)
