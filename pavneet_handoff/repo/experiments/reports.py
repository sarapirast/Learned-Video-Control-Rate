"""Write every report for the current encoder ($RC_CODEC / $RC_WORK). A report whose inputs are missing is skipped
with a note, so this can run after partial failures."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [["infos.py", "--report"], ["search.py", "--report"], ["scenes.py", "--report"], ["baselines.py", "--report"],
         ["analysis.py"]]

if __name__ == "__main__":
    extra = sys.argv[1:]
    for s in STEPS:
        r = subprocess.run([sys.executable, "-W", "ignore", os.path.join(HERE, s[0]), *s[1:], *extra])
        print(f"== {' '.join(s)}: {'ok' if r.returncode == 0 else f'FAILED rc={r.returncode}'}", flush=True)
