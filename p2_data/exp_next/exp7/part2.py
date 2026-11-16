"""Exp 7 Part 2 (descriptive, val; exp_next/exp7/PREREG.md): zero-shot hierarchy on x264, the encoder whose selected
stream policy (bc_ppo, L = 2) beat the retuned rule on val.

Per val same-clip 8-GOP stream case and stream controller (bc_ppo seeds 0-2, Pavneet's stored models; the retuned
L = 2 rule, rule_8_<enc>_v2.pkl), two GOP-level systems are played:
- "+ constant QP": the stream controller's per-GOP QP, outcome from the GOP's constant-QP curve (= Part 1 exactly);
- "+ final4": at each GOP the controller picks its QP q as usual; the GOP budget B_g = the controller's OWN predicted
  spend at q (bc_ppo: clipenv first-pass model, slope 5.5, online calibration; rule: its own model with slope qpd and
  prior weight cw); final4 (1.0:6:1.0:2:3:4:1:1:1:0:3, k5) encodes the GOP at B_g with real encodes
  (scripts/controller_real.run_episode); history from the stream's own previous GOP as final4's chain() does (h = 3);
  the first GOP's base-QP estimate is budgets.csv base_qp_est_k5 interpolated in log budget across the 4 levels.
  The actual bits and PSNR feed back into the stream state (spent, calibration, observations).
Both scored at the stream level against the stream budget with Part 1's metric (SE.stream_score, pooled PSNR). The
per-GOP check |bits - B_g| / B_g is reported separately.

  RC_CODEC=x264 python exp_next/exp7/part2.py --check        (a) "+ constant QP" == Part 1 rows; (b) run_episode
                                                               reproduces stored final4 rows
  RC_CODEC=x264 python exp_next/exp7/part2.py [--shard i --nshards n] [--workers w] [--limit N]
Out: results_v1/next/exp7/part2_<enc>_<shard>of<n>.pkl
"""
import argparse
import importlib.util
import os
import pickle
import sys
import time
from multiprocessing import Pool

ENC = os.environ["RC_CODEC"]
SRC = "/scratch1/aayushso/ee599/exp_next/exp7/src_pavneet/pavneet_handoff"
os.environ["RC_WORK"] = f"{SRC}/artifacts/{ENC}/v1"
os.environ.setdefault("RC_V1", "1")
os.environ.setdefault("RC_BUDGETS", "24,30,36,42")
sys.path.insert(0, f"{SRC}/repo")
import numpy as np  # noqa: E402
from experiments import stream_rl as S  # noqa: E402
from rclib import clipenv as CE, config as C, streamenv as SE  # noqa: E402

ROOT = "/scratch1/aayushso/ee599"
OUT = f"{ROOT}/results_v1/next/exp7"
spec = importlib.util.spec_from_file_location("controller_real", f"{ROOT}/scripts/controller_real.py")
CR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CR)
K = 5
_G = {}
SPLIT = ["val"]       # set by --split before the pool starts (fork)


def _init():
    _G["infos"] = S.load_infos()
    _G["inp"] = pickle.load(open(f"{OUT}/part2_inputs_{ENC}{'' if SPLIT[0] == 'val' else '_' + SPLIT[0]}.pkl", "rb"))
    _G["c0"] = S.train_c0(_G["infos"])
    _G["rule"] = pickle.load(open(f"{OUT}/rule_8_{ENC}_v2.pkl", "rb"))[2]
    _G["pol"] = {}
    _G["tmp"] = os.environ.get("RC_TMP") or os.environ.get("TMPDIR", "/tmp")


def policy(seed):
    if seed not in _G["pol"]:
        from stable_baselines3 import PPO
        _G["pol"][seed] = PPO.load(f"{os.environ['RC_WORK']}/results_stream/bc_ppo_L2_s{seed}/model.zip", device="cpu").policy
    return _G["pol"][seed]


def make_env(ctrl):
    infos, c0 = _G["infos"], _G["c0"]
    ids = S.split_ids(infos, SPLIT[0])
    if ctrl == "rule":
        r = _G["rule"]
        return SE.StreamEnv(infos, ids, look=2, c0=c0, margin=r["best"][0], mode="rule", rp=r["rp"])
    return SE.StreamEnv(infos, ids, look=2, c0=c0)


def act(ctrl, seed, o):
    return SE.ZERO if ctrl == "rule" else int(policy(seed).predict(o, deterministic=True)[0])


def predicted_spend(env, ctrl, q):
    t = env.tabs[env.i]
    if ctrl == "rule":
        qpd, cw, c0 = env.rp["qpd"], env.rp["cw"], env.rp["c0"]
        lr = [np.log(b / (tt["fp"] * 2.0 ** (-(qq - CE.FP_QP) / qpd))) for b, qq, tt in zip(env.bits, env.qps, env.tabs)]
        c = float(np.exp((cw * np.log(c0) + sum(lr)) / (cw + len(lr))))
        return float(c * t["fp"] * 2.0 ** (-(q - CE.FP_QP) / qpd))
    return float(CE.fp_model(t["fp"], q, env.calib()))


def qhat_first(gin, B):
    lv = sorted(gin["levels"].values(), key=lambda v: v["B"])
    return float(np.interp(np.log(B), [np.log(v["B"]) for v in lv], [v["qest"] for v in lv]))


def play(case, ctrl, seed, final4):
    _, grp, st, q0, s = case
    env = make_env(ctrl)
    env.force(st, q0, s)
    o, _ = env.reset()
    inp, M, pm, setting = _G["inp"], _G["inp"]["M"], _G["inp"]["pm"], _G["inp"]["setting"]
    gops, prev = [], None
    while True:
        a = act(ctrl, seed, o)
        q = int(np.clip(round(env.q_hat()) + CE.ACTIONS[a], C.QP_MIN, C.QP_MAX))
        if not final4:
            o, _, done, _, res = env.step(a)
            gops.append({"q": q, "bits": env.bits[-1]})
            if done:
                return res, gops
            continue
        gin = inp["gops"][st[env.i]]
        fp = np.maximum(np.asarray(gin["gd"]["fp"], float), 8)
        Bg = predicted_spend(env, ctrl, q)
        if prev is None:
            qh, Mg = qhat_first(gin, Bg), M
        else:
            qh = float(CR.qhat_prev(pm, Bg, fp, K, prev[0], prev[1]))
            Mg = dict(M, c_i=M["c_i"] * prev[2], c_p=M["c_p"] * prev[2])
        row, bits = CR.run_episode(ENC, gin["gd"], Bg, -1, K, setting, Mg, gin["curve"], _G["tmp"], qh)
        b, p = float(row["bits"]), float(row["psnr_yuv"])
        prev = CR.history_features(fp, bits, row["qps"], Bg, M)
        t = env.tabs[env.i]
        env.logr.append(np.log(b / CE.fp_model(t["fp"], q, 1.0)))
        env.qps.append(q)
        env.acts.append(a)
        env.bits.append(b)
        env.psnrs.append(p)
        env.spent += b
        env.i += 1
        gops.append({"q": q, "B_g": Bg, "bits": b, "psnr": p, "qhat": qh, "f4_qps": row["qps"]})
        if env.i < env.n:
            o = env._obs()
            continue
        tot, mp = float(sum(env.bits)), float(CE.pooled(env.psnrs))
        d, over, sc = SE.stream_score(env.tabs, tot, mp, env.B)
        return {"stream": env.stream, "q0": q0, "s": s, "bits": tot, "budget": env.B, "use": tot / env.B, "psnr": mp,
                "dpsnr": d, "over_pct": over, "over": tot > 1.01 * env.B, "score": sc}, gops


def item(args):
    case, ctrl, seed = args
    r_cqp, g_cqp = play(case, ctrl, seed, False)
    r_f4, g_f4 = play(case, ctrl, seed, True)
    return {"case": case, "ctrl": ctrl, "seed": seed, "cqp": r_cqp, "f4": r_f4, "gops_f4": g_f4, "gops_cqp": g_cqp}


def check():
    _init()
    infos = _G["infos"]
    cases = [c for c in S.cases(infos, "val") if c[0] == "clip"]
    sel = pickle.load(open(f"{OUT}/rule_8_{ENC}_v2.pkl", "rb"))[2]
    import rule_tune as RT  # noqa: E402
    tr = S.split_ids(infos, "train")
    RT.init(infos, cases, S.split_ids(infos, "val"), _G["c0"], {g: CE.gop_table(infos[g]) for g in tr}, tr)
    rule_rows = RT.run_cases(2, sel["best"][0], sel["rp"], 8)
    ev = pickle.load(open(f"{os.environ['RC_WORK']}/results_stream/bc_ppo_L2_s0/eval.pkl", "rb"))["res"]["val"]
    ev = [r for r in ev if r["kind"] == "clip"]
    ok = tot = 0
    for i in range(0, len(cases), 7):
        for ctrl, ref in (("rule", rule_rows[i]), ("bc_ppo", ev[i])):
            r, _ = play(cases[i], ctrl, 0, False)
            ok += abs(r["score"] - ref["score"]) < 1e-9
            tot += 1
    print(f"(a) '+ constant QP' reproduces Part 1 rows: {ok}/{tot}")
    n_ok = 0
    for r in _G["inp"]["final4_rows"][:3]:
        gid = f"{r['clip_id']}@{30 * r['gop']}"
        gin = _G["inp"]["gops"][gid]
        row, _ = CR.run_episode(ENC, gin["gd"], float(r["budget_bits"]), int(r["level_q0"]), K, _G["inp"]["setting"],
                                _G["inp"]["M"], gin["curve"], _G["tmp"], gin["levels"][int(r["level_q0"])]["qest"])
        same = int(row["bits"]) == int(r["bits"]) and list(row["qps"]) == list(r["qps"])
        n_ok += same
        print(gid, r["level_q0"], "bits", int(row["bits"]), int(r["bits"]), "OK" if same else "MISMATCH")
    print(f"(b) run_episode reproduces stored final4 rows (k5, first GOP of clip): {n_ok}/3")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--shard", type=int, default=int(os.environ.get("SLURM_ARRAY_TASK_ID", 0)))
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--workers", type=int, default=max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", 2)) - 1))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--split", default="val", choices=("val", "test"))   # test: approved final pass only
    a = ap.parse_args()
    SPLIT[0] = a.split
    sys.path.insert(0, f"{ROOT}/exp_next/exp7")
    if a.check:
        return check()
    infos = S.load_infos()
    cases = [c for c in S.cases(infos, a.split) if c[0] == "clip"]
    items = [(c, "rule", 0) for c in cases] + [(c, "bc_ppo", s) for s in (0, 1, 2) for c in cases]
    items = items[a.shard::a.nshards]
    if a.limit:
        items = items[:a.limit]
    dest = f"{OUT}/part2_{ENC}{'' if a.split == 'val' else '_' + a.split}_{a.shard}of{a.nshards}{'_limit' if a.limit else ''}.pkl"
    assert not os.path.exists(dest), f"{dest} exists; never overwrite"
    t0 = time.time()
    with Pool(a.workers, initializer=_init) as p:
        rows = list(p.imap_unordered(item, items, chunksize=1))
    pickle.dump(rows, open(dest + ".part", "wb"))
    os.replace(dest + ".part", dest)
    print(f"{ENC} part 2 shard {a.shard}/{a.nshards}: {len(rows)} stream episodes, {time.time() - t0:.0f}s -> {dest}")


if __name__ == "__main__":
    main()
