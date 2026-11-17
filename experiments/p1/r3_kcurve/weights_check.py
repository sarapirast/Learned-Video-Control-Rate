"""Compare the policy weights of my k5 R3 reruns with Aayush's stored models (bit-identical = training through the shim
reproduces R3 exactly). Needs torch: run with Aayush's rc env.
  python -I weights_check.py <out.txt> <seed> [<seed> ...]     e.g. weights_check.txt 3 ; weights_check_b2.txt 4 5
Read by score_kcurve.py (weights_check.txt) and score_all.py (weights_check_b2.txt).
"""
import io
import sys
import zipfile

import torch

MINE = ("/scratch1/ahhanagu/ee599/results/r3_kcurve/work/results_rl/"
        "res_k5_fixed_no-level_f4_lam0.17_st180k_r6_capbit_meanpooled_bcinit_wu20k_s{s}/model.zip")
STORED = ("/scratch1/aayushso/rcwork_v1/x264_resh/results_rl/"
          "res_k5_fixed_no-level_f4_lam0.17_st360k_r6_capbit_meanpooled_bcinit_wu20k_s{s}/model_180993.zip")


def weights(p):
    with zipfile.ZipFile(p) as z:
        return torch.load(io.BytesIO(z.read("policy.pth")), map_location="cpu", weights_only=False)


def main():
    out, lines = sys.argv[1], []
    for s in (int(x) for x in sys.argv[2:]):
        a, b = weights(MINE.format(s=s)), weights(STORED.format(s=s))
        m = max(float((a[n] - b[n]).abs().max()) for n in a)
        lines.append(f"k5 s{s} policy weights vs Aayush model_180993: max |diff| = {m:.3e} "
                     f"({'bit-identical' if m == 0 else 'different'}) over {len(a)} tensors")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
