"""D40: the D39 live-channel result with the real encoder in the loop (x265 / x264, v1 settings: RC_V1=1, medium).

Same cases, channels, buffer, stall penalty and luma dPSNR_B score as experiments/buffer_rl.py; the channel and
buffer stay simulated (trace-driven for RC_BUF_CHANNEL=trace), the video is really encoded and decoded.

methods (per case; every one is paired with the others on the same channel)
  vbv2 / ppo_v2       curve lookups (D39; ppo_v2 = seed 0), recomputed here for exact pairing
  rp_vbv2 / rp_ppo_v2 E1 replay: the same per-GOP QPs, each 1-s GOP really encoded at that constant QP (closed GOPs,
                      so equal to one stream encode; D34 check). Measured bits and decoded luma PSNR go through the
                      buffer. Subset of cases (checks that lookups = real encodes).
  enc_vbv             E2: the encoder's own ABR + VBV for the whole stream, channel-blind: average rate = f x channel
                      mean rate (f in E2_F, picked on val), maxrate = that rate, bufsize = D_CAP s of it (plain tools, psy off).
  enc_vbv2            E3: channel-aware encoder rate control. Each second the vbv2 rule (D39 tuned) sets a bit target
                      from the buffer and observed channel; the encoder codes that GOP with its own frame-level ABR+VBV
                      (maxrate = bufsize = target) and the measured bits / PSNR drive the buffer and the next target.
  enc_ppo_v2          E3 with ppo_v2 (seed 0) choosing the per-second target instead (its QP -> bits by the rate model).
  --model NAME        (D43) any later saved policy, e.g. il_ppo_rr: NAME (lookup), rp_NAME (E1 replay on every case),
                      enc_NAME (E3), in separate files {split}_{k}of{n}_NAME.pkl; the report pairs them with the rows
                      above by case. A policy with a privileged critic gets its unseen inputs as zeros (masked anyway).

  RC_V1=1 RC_PRESET=medium RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 \
      python experiments/buffer_real.py --split test --shard 0 --nshards 8      # then --report
"""
import argparse
import glob
import os
import pickle
import shutil
import sys
import tempfile
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import buffer_rl as BR, stream_rl as S  # noqa: E402
from rclib import bufenv as BE, clipenv as CE, codec, config as C, data, yrd  # noqa: E402

assert C.V1, "run with RC_V1=1 (v1 encoder settings, as the curves)"
log = S.log
STRIDE = {"test": 3, "test16": 3, "val": 6}   # every k-th case of the D39 sets
E2_F = (0.6, 0.7, 0.8, 0.9, 1.0)       # E2 target = f x channel mean rate; f picked on val (the rules were tuned too)
E2_X = (0.2, 0.3, 0.4, 0.5)            # --e2x: extension below the grid (trace tuning hit f = 0.6, the edge)
N_REPLAY = 8                           # E1 replay on the first N cases of each shard
OUTR = os.path.join(BR.OUT, "real")
REPORTS = os.path.join(BR.REPORTS, "real")
EXT = "hevc" if C.CODEC == "x265" else "264"


# --------------------------------------------------------------------------------------------- real encodes
def _luma(src, rec):
    ys = C.W * C.H
    d = src[:, :ys].astype(np.int32) - rec[:, :ys].astype(np.int32)
    return (d * d).mean(1)


def _enc(path, n, args, d, src):
    out = os.path.join(d, "out." + EXT)
    codec._run(codec._cmd(C.CODEC, path, n, out, [*args, *(["--repeat-headers"] if C.CODEC == "x265" else [])]))
    with open(out, "rb") as f:
        bits = codec.frame_bits(f.read(), C.CODEC)
    assert len(bits) == n, (len(bits), n)
    return bits.astype(float), _luma(src, codec.decode(out, n))


def _rate(T, n):
    """ABR args so that bits per frame = T / n exactly (integer kbps + rational fps), as own_rc_stream._rc_args."""
    k = max(1, round(T / n * 30 / 1000))
    return k, ["--bitrate", str(k), "--fps", f"{k * 1000 * n}/{max(1, int(round(T)))}"]


def gop_cqp(info, q, d):
    """One GOP at constant QP q (the curve's encode): bits, luma PSNR of the mean frame MSE."""
    p = data.gop_path(info["gop"])
    b, m = _enc(p, C.GOP, [*codec.FORCED_ARGS[C.CODEC], "--qp", str(int(q))], d, data.gop_frames(info["gop"]))
    return b.sum(), float(yrd.psnr(m.mean()))


def gop_abr(info, T, d):
    """One GOP with the encoder's ABR + VBV at target T bits (maxrate = bufsize = the target rate)."""
    k, rc = _rate(T, C.GOP)
    a = [*codec.FORCED_ARGS[C.CODEC], *rc, "--vbv-maxrate", str(k), "--vbv-bufsize", str(k), "--rc-lookahead", "30"]
    b, m = _enc(data.gop_path(info["gop"]), C.GOP, a, d, data.gop_frames(info["gop"]))
    return b.sum(), float(yrd.psnr(m.mean()))


def stream_abr_vbv(infos, stream, B, d, f=1.0):
    """E2: whole stream, one encode, ABR at B / n per second (B = f x channel total), maxrate = that, bufsize =
    D_CAP s of the channel mean rate."""
    n = len(stream) * C.GOP
    src = np.concatenate([data.gop_frames(infos[g]["gop"]) for g in stream])
    p = os.path.join(d, "stream.yuv")
    src.tofile(p)
    k, rc = _rate(f * B, n)
    kb = max(1, round(k * BE.D_CAP / f))
    a = [*codec.FORCED_ARGS[C.CODEC], *rc, "--vbv-maxrate", str(k), "--vbv-bufsize", str(kb), "--rc-lookahead", "30"]
    b, m = _enc(p, n, a, d, src)
    return b.reshape(-1, C.GOP).sum(1), yrd.psnr(m.reshape(-1, C.GOP).mean(1))


# --------------------------------------------------------------------------------------------- env with real outcomes
def q_eff(t, bits):
    """Constant QP whose curve bits equal the measured bits (for the rule's rate-model calibration)."""
    q = np.arange(yrd.QLO, yrd.QHI + 1)
    lb = np.log(t["bits"][q])
    return int(np.clip(round(float(np.interp(-np.log(bits), -lb, q))), yrd.QLO, yrd.QHI))


def step_real(env, bits, psnr, q, a=CE.ZERO):
    """Advance the buffer env with a measured GOP outcome (the table entry is swapped for this one step)."""
    i = env.i
    t0 = env.tabs[i]
    t = dict(t0, bits=t0["bits"].copy(), psnr=t0["psnr"].copy())
    t["bits"][q], t["psnr"][q] = bits, psnr
    env.tabs[i] = t
    try:
        o, _, done, _, info = env.step(a, q=q)
    finally:
        env.tabs[i] = t0
    return o, done, (env.result() if done else None)


def model_bits(env, q):
    return float(env._calib() * env.tabs[env.i]["fp"] * 2.0 ** (-(q - CE.FP_QP) / env.rp["qpd"]))


def policy_q(env, o, act):
    """(action, QP) exactly as BufEnv.step would choose them (the action is kept: the observation shows it)."""
    a = CE.ZERO if act is None else act(o)
    return a, int(np.clip(round(env.q_hat()) + CE.ACTIONS[a], C.QP_MIN, C.QP_MAX))


def run_case(env, case, act, mode, infos, d):
    """mode: lookup | replay | abr (E3). Returns the env result dict (+ per-GOP real numbers)."""
    kind, grp, st, q0, s = case
    env.force(st, q0, s)
    o, _ = env.reset()
    if act is not None and hasattr(act, "reset"):
        act.reset()
    done, gb, gp, tg = False, [], [], []
    while not done:
        a, q = policy_q(env, o, act)
        info = infos[st[env.i]]
        if mode == "lookup":
            o, _, done, _, res = env.step(a, q=q)
            continue
        if mode == "replay":
            b, p = gop_cqp(info, q, d)
            qq = q
        else:
            T = model_bits(env, q)
            b, p = gop_abr(info, T, d)
            qq = q_eff(env.tabs[env.i], b)
            tg.append(T)
        gb.append(b)
        gp.append(p)
        o, done, res = step_real(env, b, p, qq, a)
    return {**res, "kind": kind, "group": grp, "gop_bits": gb, "gop_psnr": gp, "targets": tg}


def run_e2(env, case, infos, d, f=1.0):
    kind, grp, st, q0, s = case
    env.force(st, q0, s)
    env.reset()
    gb, gp = stream_abr_vbv(infos, st, env.B, d, f)
    done = False
    for b, p in zip(gb, gp):
        _, done, res = step_real(env, float(b), float(p), q_eff(env.tabs[env.i], b))
    assert done
    return {**res, "kind": kind, "group": grp, "gop_bits": list(gb), "gop_psnr": list(gp)}


# --------------------------------------------------------------------------------------------- driver
def cases_for(split):
    cs = BR.case_sets()[split]
    return cs[::STRIDE[split]]


def shard(a):
    from stable_baselines3 import PPO
    od = OUTR + ("_debug" if a.limit else "")      # --limit runs (tests) never mix with the real shards
    os.makedirs(od, exist_ok=True)
    p = os.path.join(od, f"{a.split}_{a.shard}of{a.nshards}{'_e2x' if a.e2x else ''}.pkl")
    if os.path.exists(p):
        log(f"{p}: done")
        return
    t0 = time.time()
    infos, Y = BR.data()
    bs, b2 = BR.baselines(), BR.baselines2()
    tu, c0 = bs["tune"][2], bs["c0"]
    model = PPO.load(os.path.join(BR.OUT, "ppo_v2_L2_s0", "model.zip"), device="cpu")
    act = BR.Actor(model)
    cs = [c for j, c in enumerate(cases_for(a.split)) if j % a.nshards == a.shard]
    if a.limit:
        cs = cs[:a.limit]
    n = BR.n_of(a.split)

    def env(rl=False):
        """Exactly D39's environments: the vbv2 baseline was tuned and evaluated with make_env's default psi / alpha,
        ppo_v2 trained and evaluated with the D38-tuned psi / alpha (alpha also sets the volatility EMA)."""
        if rl:
            return BR.make_env(a.split, 2, c0, tu["rp"], "vbv2", tu["psi"], tu["alpha"], n=n, bp=b2["vbv2"])
        return BR.make_env(a.split, 2, c0, tu["rp"], "vbv2", n=n, bp=b2["vbv2"])
    fs = E2_X if a.e2x else E2_F
    R = {k: [] for k in ("vbv2", "ppo_v2", "rp_vbv2", "rp_ppo_v2", *(f"enc_vbv_f{f:g}" for f in fs), "enc_vbv2",
                         "enc_ppo_v2")}
    d = tempfile.mkdtemp(dir=codec._tmpdir())
    try:
        for j, c in enumerate(cs):
            for f in fs:
                R[f"enc_vbv_f{f:g}"].append(run_e2(env(), c, infos, d, f))
            if a.split == "val" or a.e2x:          # val: only E2's target fraction is tuned here
                continue
            R["vbv2"].append(run_case(env(), c, None, "lookup", infos, d))
            R["ppo_v2"].append(run_case(env(True), c, act, "lookup", infos, d))
            if j < a.replay:
                R["rp_vbv2"].append(run_case(env(), c, None, "replay", infos, d))
                R["rp_ppo_v2"].append(run_case(env(True), c, act, "replay", infos, d))
            R["enc_vbv2"].append(run_case(env(), c, None, "abr", infos, d))
            R["enc_ppo_v2"].append(run_case(env(True), c, act, "abr", infos, d))
            if j % 10 == 0:
                log(f"{a.split} shard {a.shard}: {j + 1}/{len(cs)} cases, {(time.time() - t0) / 60:.1f} min; " +
                    ", ".join(f"{k} {np.mean([r['score'] for r in v]):+.3f}" for k, v in R.items() if v))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    if a.split == "val" or a.e2x:
        pickle.dump({"rows": R, "seconds": time.time() - t0, "lookup_check": 0.0}, open(p, "wb"))
        return
    # sanity: the lookup vbv2 rows equal D39's stored rows for the same cases
    ref = {(tuple(r["stream"]), r["q0"], r["s"]): r["score"] for r in b2["rows"][("vbv2", 2, a.split)]}
    dif = [abs(r["score"] - ref[(tuple(r["stream"]), r["q0"], r["s"])]) for r in R["vbv2"]]
    e0 = pickle.load(open(os.path.join(BR.OUT, "ppo_v2_L2_s0", "eval.pkl"), "rb"))["res"][a.split]
    ref = {(tuple(r["stream"]), r["q0"], r["s"]): r["score"] for r in e0}
    dif += [abs(r["score"] - ref[(tuple(r["stream"]), r["q0"], r["s"])]) for r in R["ppo_v2"]]
    log(f"lookup vbv2 / ppo_v2 vs D39 rows: max |diff| {max(dif):.2e}")
    pickle.dump({"rows": R, "seconds": time.time() - t0, "lookup_check": max(dif)}, open(p, "wb"))
    log(f"{p}: {(time.time() - t0) / 60:.1f} min")


def shard_model(a):
    """D43: lookup, E1 replay (every case) and E3 for a saved policy (results_buffer*/<model>_L2_s0/model.zip)."""
    from stable_baselines3 import PPO
    od = OUTR + ("_debug" if a.limit else "")
    os.makedirs(od, exist_ok=True)
    p = os.path.join(od, f"{a.split}_{a.shard}of{a.nshards}_{a.model}.pkl")
    if os.path.exists(p):
        log(f"{p}: done")
        return
    t0 = time.time()
    infos, Y = BR.data()
    bs, b2 = BR.baselines(), BR.baselines2()
    tu, c0 = bs["tune"][2], bs["c0"]
    md = os.path.join(BR.OUT, f"{a.model}_L2_s0")
    model = PPO.load(os.path.join(md, "model.zip"), device="cpu")
    dim = model.observation_space.shape[0]

    def act(o):
        o = np.concatenate([o, np.zeros(dim - len(o), np.float32)]) if len(o) < dim else o
        return int(model.predict(o, deterministic=True)[0])
    cs = [c for j, c in enumerate(cases_for(a.split)) if j % a.nshards == a.shard]
    if a.limit:
        cs = cs[:a.limit]
    n = BR.n_of(a.split)

    def env():
        return BR.make_env(a.split, 2, c0, tu["rp"], "vbv2", tu["psi"], tu["alpha"], n=n, bp=b2["vbv2"])
    M = a.model
    R = {M: [], f"rp_{M}": [], f"enc_{M}": []}
    d = tempfile.mkdtemp(dir=codec._tmpdir())
    try:
        for j, c in enumerate(cs):
            R[M].append(run_case(env(), c, act, "lookup", infos, d))
            R[f"rp_{M}"].append(run_case(env(), c, act, "replay", infos, d))
            R[f"enc_{M}"].append(run_case(env(), c, act, "abr", infos, d))
            if j % 10 == 0:
                log(f"{a.split} shard {a.shard} [{M}]: {j + 1}/{len(cs)} cases, {(time.time() - t0) / 60:.1f} min; " +
                    ", ".join(f"{k} {np.mean([r['score'] for r in v]):+.3f}" for k, v in R.items() if v))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    e0 = pickle.load(open(os.path.join(md, "eval.pkl"), "rb"))["res"][a.split]
    ref = {(tuple(r["stream"]), r["q0"], r["s"]): r["score"] for r in e0}
    dif = max(abs(r["score"] - ref[(tuple(r["stream"]), r["q0"], r["s"])]) for r in R[M])
    log(f"lookup {M} vs its eval.pkl rows: max |diff| {dif:.2e}")
    pickle.dump({"rows": R, "seconds": time.time() - t0, "lookup_check": dif}, open(p, "wb"))
    log(f"{p}: {(time.time() - t0) / 60:.1f} min")


def report():
    chan = f"AR(1) rho {BE.RHO}, sigma {BE.SIGMA}" if BE.CHANNEL == "ar1" else "Belgium 4G/LTE traces (test files)"
    lines = [f"# D40 live channel with the real encoder in the loop ({C.CODEC}{', ' + BR.TAG if BR.TAG else ''})", "",
             f"Channel {chan}, cap {BE.D_CAP} s, stall weight {BE.LAM_STALL} dB per %. Score = luma dPSNR_B - 0.17 x "
             "%over - stall weight x %stalled. Real encodes: v1 encoder settings (medium, psy/AQ/cutree off), "
             "decoded luma PSNR. Paired differences, 95 % cluster bootstrap. ppo_v2 = seed 0.", "",
             "- vbv2 / ppo_v2: curve lookups (D39). rp_*: same QPs really encoded (E1, subset).",
             "- enc_vbv: encoder ABR+VBV for the whole stream at f x the channel's mean rate (f tuned on val), 1 s buffer "
             "(E2, channel-blind).",
             "- enc_vbv2 / enc_ppo_v2: per-second bit target from vbv2 / ppo_v2, coded by the encoder's own ABR+VBV "
             "(E3, channel-aware).", ""]
    fbest, vf = 1.0, sorted(glob.glob(os.path.join(OUTR, "val_*of*.pkl")))
    if vf:
        V = {}
        for f in vf:
            for k, v in pickle.load(open(f, "rb"))["rows"].items():
                V.setdefault(k, []).extend(r["score"] for r in v)
        vm = {f: np.mean(V[f"enc_vbv_f{f:g}"]) for f in sorted(E2_X + E2_F) if f"enc_vbv_f{f:g}" in V}
        fbest = max(vm, key=vm.get)
        lines += ["E2 target fraction tuned on val (" + ", ".join(f"f {f:g}: {v:+.3f}" for f, v in vm.items()) +
                  f"): f = {fbest:g}. enc_vbv_f1 = untuned (target = channel mean).", ""]
    pairs = [("rp_vbv2", "vbv2"), ("rp_ppo_v2", "ppo_v2"), ("ppo_v2", "vbv2"), ("ppo_v2", "enc_vbv"),
             ("ppo_v2", "enc_vbv_hindsight"), ("ppo_v2", "enc_vbv2"), ("enc_vbv2", "enc_vbv"), ("enc_ppo_v2", "enc_vbv2"), ("enc_ppo_v2", "enc_vbv"),
             ("enc_ppo_v2", "ppo_v2"), ("enc_vbv2", "vbv2")]
    extra = sorted({os.path.basename(f).split("_", 2)[2][:-4] for f in glob.glob(os.path.join(OUTR, "test*_*of*_*.pkl"))
                    if not f.endswith("_e2x.pkl")})      # D43 --model rows
    for M in extra:
        pairs += [(f"rp_{M}", M), (M, "vbv2"), (M, "ppo_v2"), (M, "enc_vbv"), (M, "enc_vbv_hindsight"),
                  (f"enc_{M}", "enc_vbv2"), (f"rp_{M}", "rp_ppo_v2")]
    for split, title in (("test", "v1 test (n = 8, every 3rd case)"), ("test16", "test playlists (n = 16, every 3rd)")):
        fs = sorted(glob.glob(os.path.join(OUTR, f"{split}_*of*.pkl")))
        if not fs:
            continue
        R, chk = {}, []
        for f in fs:
            x = pickle.load(open(f, "rb"))
            chk.append(x["lookup_check"])
            for k, v in x["rows"].items():
                R.setdefault(k, []).extend(v)
        F = {k: pd.DataFrame([{"kind": r["kind"], "group": r["group"], "score": r["score"], "dpsnr": r["dpsnr"],
                               "use": r["use"], "over": r["over"], "stall_pct": r["stall_pct"], "stalled": r["stalled"],
                               "key": (tuple(r["stream"]), r["q0"], r["s"])} for r in v]).set_index("key")
             for k, v in R.items() if v}
        F["enc_vbv"] = F[f"enc_vbv_f{fbest:g}"]
        ef = {k: v.score.mean() for k, v in F.items() if k.startswith("enc_vbv_f")}
        F["enc_vbv_hindsight"] = F[max(ef, key=ef.get)]     # E2's best f on test itself: an upper bound for E2
        lines_f = "E2 on this test set by f: " + ", ".join(f"{k[9:]} {v:+.3f}" for k, v in sorted(ef.items(),
                                                           key=lambda kv: float(kv[0][9:])))
        F = {k: v for k, v in F.items() if not k.startswith("enc_vbv_f") or k == "enc_vbv_f1"}
        rows = [{"method": k, "cases": len(df), "score (dB)": df.score.mean(), "dPSNR_B": df.dpsnr.mean(),
                 "use": f"{100 * df.use.mean():.1f}%", ">1% over": f"{100 * df.over.mean():.0f}%",
                 "stall %": df.stall_pct.mean(), "streams with stall": f"{100 * df.stalled.mean():.0f}%"}
                for k, df in F.items()]
        diffs = []
        for a_, b_ in pairs:
            if a_ in F and b_ in F:
                ks = [k for k in F[a_].index if k in F[b_].index]
                t = S.cboot(F[a_].loc[ks].score.values - F[b_].loc[ks].score.values, F[a_].loc[ks].group.values)
                diffs.append({"comparison": f"{a_} - {b_}", "cases": len(ks),
                              "score diff (dB)": f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"})
        lines += [f"## {title}", "", lines_f + f" (hindsight = {max(ef, key=ef.get)[8:]}).", "",
                  f"Lookup vbv2 / ppo_v2 = D39 rows (max |diff| {max(chk):.1e}).", "",
                  pd.DataFrame(rows).round(3).to_markdown(index=False), "",
                  pd.DataFrame(diffs).to_markdown(index=False), ""]
    os.makedirs(REPORTS, exist_ok=True)
    open(os.path.join(REPORTS, "real_report.md"), "w").write("\n".join(lines))
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=tuple(STRIDE))
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--replay", type=int, default=N_REPLAY)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--e2x", action="store_true", help="E2 only, at the extra fractions E2_X (separate files)")
    ap.add_argument("--model", default=None, help="D43: a saved policy name (e.g. il_ppo_rr); test / test16 only")
    a = ap.parse_args()
    if a.report:
        return report()
    if a.model:
        return shard_model(a)
    shard(a)


if __name__ == "__main__":
    main()
