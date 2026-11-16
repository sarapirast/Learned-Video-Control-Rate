"""One-off: set each eval.pkl's method label from its folder name (train_pid.py used to save 'ppo_pid' for all)."""
import os, sys, glob, pickle
for p in glob.glob(os.path.join(sys.argv[1], "results_stream", "*pid*", "eval.pkl")):
    r = pickle.load(open(p, "rb"))
    new = os.path.basename(os.path.dirname(p)).rsplit("_L", 1)[0]
    if r["args"]["method"] != new:
        print(p, ":", r["args"]["method"], "->", new)
        r["args"]["method"] = new
        pickle.dump(r, open(p, "wb"))