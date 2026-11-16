"""Exp 7 Part 1d: pre-registered selection of ONE stream policy per encoder (exp_next/exp7/PREREG.md).

Population: val same-clip 8-GOP streams (504 cases). Comparator: the retuned L = 2 rule (rule_8_<enc>_v2.pkl).
Candidates (L = 2, seeds 0-2 averaged per case): ppo, bc_ppo (Pavneet's stored val rows, reproduced exactly in
step 1), ppo_pid, bc_ppo_pid (our retrain of Sara's code; val rows from rcwork_exp7). Pick the highest mean
(candidate - retuned rule); within 0.01 dB the simpler: ppo > bc_ppo > ppo_pid > bc_ppo_pid. Also reported: vs the
rule as reported, cluster-bootstrap CIs over source groups (stream_rl.cboot), over-budget share (> 1 % over) and p90
|spend error|, and the PID sanity check (over-budget share about half the rule's, as Sara described).

  RC_CODEC=<enc> python exp_next/exp7/select_policy.py
Out: results_v1/next/exp7/select_<enc>.md, select_<enc>.json
"""
import json
import os
import pickle
import sys

ENC = os.environ["RC_CODEC"]
SRC = "/scratch1/aayushso/ee599/exp_next/exp7/src_pavneet/pavneet_handoff"
os.environ["RC_WORK"] = f"{SRC}/artifacts/{ENC}/v1"
os.environ.setdefault("RC_V1", "1")
os.environ.setdefault("RC_BUDGETS", "24,30,36,42")
sys.path.insert(0, f"{SRC}/repo")
sys.path.insert(0, "/scratch1/aayushso/ee599/exp_next/exp7")
import numpy as np  # noqa: E402
from experiments import stream_rl as S  # noqa: E402
import rule_tune as RT  # noqa: E402

OUT = "/scratch1/aayushso/ee599/results_v1/next/exp7"
ORDER = ["ppo", "bc_ppo", "ppo_pid", "bc_ppo_pid"]
DIRS = {"ppo": f"{SRC}/artifacts/{ENC}/v1/results_stream", "bc_ppo": f"{SRC}/artifacts/{ENC}/v1/results_stream",
        "ppo_pid": f"/scratch1/aayushso/rcwork_exp7/{ENC}_v1/results_stream",
        "bc_ppo_pid": f"/scratch1/aayushso/rcwork_exp7/{ENC}_v1/results_stream"}


def key(r):
    return (tuple(r["ids"]) if "ids" in r else r.get("stream"), r.get("q0"), r.get("s"))


def stats(rows):
    sc = np.array([r["score"] for r in rows])
    use = np.array([r["use"] for r in rows])
    return {"score": sc.mean(), "over>1%": 100 * np.mean(100 * (use - 1) > 1), "p90 |err| %": 100 * np.quantile(np.abs(use - 1), 0.9),
            "signed err %": 100 * np.mean(use - 1)}


def main():
    infos = S.load_infos()
    c0 = S.train_c0(infos)
    tr = S.split_ids(infos, "train")
    tabs = {g: RT.CE.gop_table(infos[g]) for g in tr}
    cases = [c for c in S.cases(infos, "val") if c[0] == "clip"]
    RT.init(infos, cases, S.split_ids(infos, "val"), c0, tabs, tr)
    tuned = pickle.load(open(f"{OUT}/rule_8_{ENC}_v2.pkl", "rb"))[2]
    rule = RT.run_cases(2, tuned["best"][0], tuned["rp"], 8)
    rep = tuned["as_reported"]
    rule_rep = RT.run_cases(2, rep["best"][0], rep["rp"], 8)
    grp = np.array([r["group"] for r in rule])
    rs, rr = np.array([r["score"] for r in rule]), np.array([r["score"] for r in rule_rep])
    L = [f"# Exp 7 Part 1 selection, {ENC} (exp_next/exp7/select_policy.py)", "",
         f"Val same-clip 8-GOP streams ({len(cases)} cases, {len(set(grp))} source groups), L = 2, seeds averaged per "
         f"case. Retuned rule {tuned['best']} (val score {rs.mean():+.4f}); rule as reported {rep['best']} "
         f"({rr.mean():+.4f}). The retuned rule was tuned on these same streams (in-sample).", "",
         "| candidate | val score | - retuned rule | - rule as reported | > 1 % over | p90 abs err % | signed err % | seeds |",
         "|---|---|---|---|---|---|---|---|"]
    res = {}
    for m in ORDER:
        seeds = []
        for s in (0, 1, 2):
            p = f"{DIRS[m]}/{m}_L2_s{s}/eval.pkl"
            if not os.path.exists(p):
                continue
            v = [r for r in pickle.load(open(p, "rb"))["res"]["val"] if r["kind"] == "clip"]
            assert len(v) == len(rule) and all(a["group"] == b["group"] for a, b in zip(v, rule))
            seeds.append(v)
        if len(seeds) < 3:
            L.append(f"| {m} | missing ({len(seeds)} seeds) | | | | | | |")
            continue
        sc = np.mean([[r["score"] for r in v] for v in seeds], axis=0)
        d, d_rep = sc - rs, sc - rr
        ci, ci_rep = S.cboot(d, grp), S.cboot(d_rep, grp)
        st = stats([r for v in seeds for r in v])
        res[m] = {"score": float(sc.mean()), "vs_rule": float(d.mean()), "ci": [ci[1], ci[2]], "ci_reported": [ci_rep[1], ci_rep[2]],
                  "vs_rule_reported": float(d_rep.mean()), **{k: float(v) for k, v in st.items()}}
        L.append(f"| {m} | {sc.mean():+.4f} | {d.mean():+.4f} [{ci[1]:+.3f}, {ci[2]:+.3f}] | {d_rep.mean():+.4f} [{ci_rep[1]:+.3f}, {ci_rep[2]:+.3f}] | {st['over>1%']:.1f}% | "
                 f"{st['p90 |err| %']:.2f} | {st['signed err %']:+.2f} | {' '.join(f'{np.mean([r['score'] for r in v]):+.3f}' for v in seeds)} |")
    for lab, rows in (("retuned rule", rule), ("rule as reported", rule_rep)):
        st = stats(rows)
        L.append(f"| {lab} | {st['score']:+.4f} | | | {st['over>1%']:.1f}% | {st['p90 |err| %']:.2f} | {st['signed err %']:+.2f} | |")
    best = max(res[m]["vs_rule"] for m in res)
    cand = [m for m in ORDER if m in res and res[m]["vs_rule"] >= best - 0.01]
    sel = cand[0]
    beats = res[sel]["vs_rule"] > 0
    pid_rule_over = stats(rule_rep)["over>1%"]
    L += ["", f"Within 0.01 dB of the best: {', '.join(cand)} -> **selected ({ENC}): {sel}**; selected - retuned rule "
              f"{res[sel]['vs_rule']:+.4f} -> Part 2 {'ALLOWED (beats the retuned rule on val)' if beats else 'SKIPPED (does not beat the retuned rule on val)'}",
          "", "PID sanity check (Sara: about half the rule's overspends): " + "; ".join(
              f"{m} > 1 % over {res[m]['over>1%']:.1f}% vs rule as reported {pid_rule_over:.1f}% / retuned "
              f"{stats(rule)['over>1%']:.1f}%" for m in ("ppo_pid", "bc_ppo_pid") if m in res), ""]
    json.dump({"selected": sel, "part2": bool(beats), "candidates": res, "rule": {"retuned": tuned["best"],
               "as_reported": rep["best"]}}, open(f"{OUT}/select_{ENC}.json", "w"), indent=1, default=str)
    open(f"{OUT}/select_{ENC}.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
