"""Write the RL run lists (one line of rl.py arguments per run) for each study. Same lists for both encoders.

  python tools/make_runs.py [--seeds 3] [--quick]   ->  runs/{core,methods,features,scenes}.txt
"""
import argparse
import itertools
import os

KS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 29)
METHODS = ("bc", "cql", "iql", "bc_ppo", "ppo", "a2c", "dqn", "lagr", "pid", "mpc")
GROUPS = ("history", "fp", "pixel", "scene")
ANYK_EVAL = ",".join([f"fixed:{k}" for k in (0, 1, 2, 3, 5, 7, 10, 15, 20, 29)] +
                     ["scene_trunc:5", "scene_trunc:10", "scene_trunc:29", "scene_ext:29", "cut_trig:5", "cut_trig:10"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    q = " --quick" if a.quick else ""
    S = range(a.seeds)
    runs = {
        "core": [f"--method cql_ppo --k {k} --seed {s}{q}" for k in KS for s in S],
        "methods": [f"--method {m} --k {k} --seed {s}{q}" for m in METHODS for k in (0, 5, 10) for s in S],
        "features": [f"--method cql_ppo --k 5 --drop {','.join(d)} --seed {s}{q}"
                     for n in (1, 3, 4) for d in itertools.combinations(GROUPS, n) for s in S]
                    + [f"--method cql_ppo --k 5 --prior --seed {s}{q}" for s in S],
        "scenes": [f"--method cql_ppo --k {k} --mode {m} --seed {s}{q}"
                   for m in ("scene_trunc", "scene_ext", "cut_trig") for k in (5, 10, 29) for s in S]
                  + [f"--method anyk --kmax 29 --eval-modes {ANYK_EVAL} --seed {s}{q}" for s in S]
                  + [f"--method cql_ppo --k 5 --train-family cut --tag cutspec --seed {s}{q}" for s in S],
    }
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs")
    os.makedirs(d, exist_ok=True)
    for name, lines in runs.items():
        p = os.path.join(d, f"{name}{'_quick' if a.quick else ''}.txt")
        open(p, "w").write("\n".join(lines) + "\n")
        print(f"{p}: {len(lines)} runs")


if __name__ == "__main__":
    main()
