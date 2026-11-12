"""Dataset v1 smoke test (D31), on the --quick subset: is the port right before any large run?
Prints budget/own spend, whether forced QPs are obeyed, the controller's score at k = 0, 5 against Aayush's numbers,
encode time, and how many logged search plans fit the residual action range."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rclib import codec, config as C, controller, data, env as E, offrl, policies as P, runner


def main():
    assert C.V1
    infos = runner.Stages("infos", True).load("infos")
    r = [x["budget"][b] / x["budget_own"][b] for x in infos.values() for b in C.BUDGET_QPS]
    print(f"budget/own spend: median {np.median(r):.2f}, 10-90% {np.percentile(r,10):.2f}-{np.percentile(r,90):.2f} (Aayush, all GOPs: 1.02, 0.66-2.1)")
    print("rate model", controller.model())
    g = next(x for x in infos.values() if x["gop"]["split"] == "test")
    p = data.gop_path(g["gop"]); t0 = time.time()
    for q in (24, 30, 36):
        codec.encode(p, [q] * 30, measure=False)
    print(f"forced-QP encode, preset {codec.PRESET}: {(time.time()-t0)/3:.2f} s per 30 frames")
    a, b = codec.encode(p, list(range(22, 37)) * 2, measure=False), codec.encode(p, list(range(22, 37)), measure=False)
    print("prefix property:", bool((a["bits"][:15] == b["bits"]).all()))
    q = codec.encode(p, [40] * 30, measure=False)["total_bits"], codec.encode(p, [26] * 30, measure=False)["total_bits"]
    print(f"QP is obeyed: bits at QP 40 / QP 26 = {q[0]/q[1]:.3f}")
    slim = {k: offrl.slim(x) for k, x in infos.items()}
    ip = P.save_infos_for_workers(slim, os.path.join(C.results_dir("infos_quick"), "infos_slim.pkl"))
    test = sorted(k for k, x in infos.items() if x["gop"]["split"] == "test")
    for k in (0, 5):
        rows = P.evaluate({"kind": "static"}, ip, test, desc=f"controller k={k}", k=k, mode="fixed")
        print(f"controller k={k}: n {len(rows)} score {np.mean([x['score'] for x in rows]):.2f} saving {np.mean([x['saving'] for x in rows]):.2f} "
              f"over>1% {100*np.mean([x['over_pct']>1 for x in rows]):.1f}% by level " +
              " ".join(f"{b}:{np.mean([x['score'] for x in rows if x['budget']==b]):.2f}" for b in C.BUDGET_QPS))
    print("(Aayush, all test GOPs: x264 k0 -3.94 k5 -0.94; x265 k0 -4.45 k5 -0.20)")
    st = runner.Stages("search", True)
    if st.done("search_train"):
        sr = st.load("search_train")
        for k in (0, 5):
            kept = tot = 0; dev = []
            for gid, e in sr.items():
                for b, ent in e.items():
                    for lg in ent["logs"]:
                        for pl in lg[::10]:
                            _, acts = E.plan_observations(infos[gid], b, pl["acts"], pl["bits"], k=k)
                            tot += 1; kept += int(acts.min() >= 0 and acts.max() < len(C.ACTIONS)); dev.append(np.abs(acts - 3))
            d = np.concatenate(dev)
            print(f"k={k}: plans inside +-3 of the controller: {kept}/{tot} ({100*kept/max(tot,1):.0f}%); frames inside: {100*np.mean(d<=3):.0f}%; median |offset| {np.median(d):.0f}")
        print("controller plan k=29 (search start):", {b: round(float(np.mean([infos[g]['static'][b]['score'] for g in sr])), 2) for b in C.BUDGET_QPS})
        print("search best (quick):", {b: round(float(np.mean([e[b]['best_score'] for e in sr.values()])), 2) for b in C.BUDGET_QPS})


if __name__ == "__main__":
    main()
