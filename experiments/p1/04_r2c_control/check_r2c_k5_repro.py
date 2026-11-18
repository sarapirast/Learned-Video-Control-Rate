"""check_r2c_k5_repro.py: does my R2c k5 seed-0 run (shim backend, P1 job scripts) reproduce Aayush's stored R2c run
(CLI backend, his jobs)? Compares the final policy weights and, per val episode, the QPs and the score rl.py stored.
A check of the pipeline only: no comparison with final4, no re-scoring.
Inputs: my run folder and Aayush's (read-only), both res_k5_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_wu20k_s0.
Output: prints the result and writes it to /scratch1/ahhanagu/ee599/results/r3_kcurve/r2c_k5_repro_check.txt
Run (needs torch: Aayush's rc env): python -I check_r2c_k5_repro.py
"""
import io
import pickle
import zipfile

import torch

NAME = "res_k5_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_wu20k_s0"
MINE = f"/scratch1/ahhanagu/ee599/results/r3_kcurve/work/results_rl/{NAME}"
STORED = f"/scratch1/aayushso/rcwork_v1/x264_resh/results_rl/{NAME}"
OUT = "/scratch1/ahhanagu/ee599/results/r3_kcurve/r2c_k5_repro_check.txt"


def weights(p):
    with zipfile.ZipFile(p) as z:          # SB3 model.zip: the policy's state dict is policy.pth
        return torch.load(io.BytesIO(z.read("policy.pth")), map_location="cpu", weights_only=False)


def rows(d):                               # rl.py's final-model val evaluation, keyed by episode
    return {(r["gid"], r["budget"]): r for r in pickle.load(open(f"{d}/eval.pkl", "rb"))["res"][("fixed", 5, "val")]}


def main():
    a, b = weights(f"{MINE}/model.zip"), weights(f"{STORED}/model.zip")
    m = max(float((a[n] - b[n]).abs().max()) for n in a)
    ra, rb = rows(MINE), rows(STORED)
    q = sum(list(ra[x]["qps"]) == list(rb[x]["qps"]) for x in rb)
    s = sum(abs(ra[x]["score"] - rb[x]["score"]) < 1e-9 for x in rb)
    lines = [f"R2c k5 s0 policy weights vs Aayush's: max |diff| = {m:.3e} ({'bit-identical' if m == 0 else 'different'})"
             f" over {len(a)} tensors",
             f"R2c k5 s0 val episodes: identical QPs {q}/{len(rb)}, identical stored score {s}/{len(rb)}"]
    open(OUT, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
