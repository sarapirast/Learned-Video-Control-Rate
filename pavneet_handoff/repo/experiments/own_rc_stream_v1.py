"""D34 hole 4: the encoders' own stream rate control on the D34 v1 test streams, scored with P2's dB metric.

Same streams and budgets as experiments/stream_rl.py at s = 1 (the stream budget is exactly the sum of the GOPs'
budgets.csv budgets; 4 levels), so every case pairs with the stream RL results. Each stream is coded as ONE
240-frame encode (IDR every 30, closed GOPs, preset as v1: RC_PRESET=medium), told the budget as an average
bitrate; the encoder picks a QP per frame (an advantage over RL and the rule, which pick one per GOP).

configs (tools: plain = AQ and cutree/mb-tree off, as the curves; tree = cutree/mb-tree on; aq = encoder defaults)
  abr          single-pass ABR, plain
  abr_vbv      ABR + VBV, maxrate = the average rate, 1-second buffer (P2's ABR+VBV baseline), plain
  abr_tree     ABR + cutree/mb-tree, rc-lookahead 30
  abr_aq       ABR with the encoder's defaults (AQ + cutree), rc-lookahead 30
  2pass        two-pass ABR (non-causal: whole-stream first pass), plain
  2pass_aq     two-pass with the encoder's defaults (non-causal)
Score = dPSNR_B - 0.17 dB per 1 % over on the stream's pooled PSNR, as stream_rl.py.

stages
  check   4 test streams: constant QP 30 / 38 on the concatenated stream must reproduce the v1 per-GOP curves
  run     every case x config [sharded]; then --stage gather
  RC_V1=1 RC_PRESET=medium RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 python experiments/own_rc_stream_v1.py --report
"""
import glob
import os
import pickle
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import own_rc_stream as O, stream_rl as S  # noqa: E402
from rclib import clipenv as CE, codec, config as C, data, runner, streamenv as SE  # noqa: E402
from rclib.runner import log  # noqa: E402

VBV = ("vbv",)
CONFIGS = {"abr": ("abr", "plain", ()), "abr_vbv": ("abr", "plain", VBV), "abr_tree": ("abr", "tree", ()),
           "abr_aq": ("abr", "aq", ()), "2pass": ("2pass", "plain", ()), "2pass_aq": ("2pass", "aq", ())}


# v1's frozen settings (codec.py under RC_V1=1) turn psy off for the curves; give the plain and tree configs the same,
# so the only differences are rate control and cutree. The encoder-defaults configs (aq) keep psy on, as shipped.
assert C.V1, "run with RC_V1=1 (v1 encoder settings: psy off)"
PSY_OFF = {"x265": ["--psy-rd", "0", "--psy-rdoq", "0"], "x264": ["--no-psy"]}
O.TOOLS["tree"] = {k: [*v, *PSY_OFF[k]] for k, v in O.TOOLS["tree"].items()}
O.TOOLS["plain"] = codec.FORCED_ARGS


def cases(infos, quick=False):
    c = [x for x in S.cases(infos, "test") if x[4] == 1.0]
    return c[:8] + c[-8:] if quick else c


def _args(B, tk, extra):
    rc = O._rc_args(B)
    a = [*O.TOOLS[tk][C.CODEC], *rc, "--rc-lookahead", "30"]
    if "vbv" in extra:
        k = rc[1]
        a += ["--vbv-maxrate", k, "--vbv-bufsize", k]
    return a


def _case(item):
    kind, grp, stream, q0, s, sub = item
    tabs = [CE.gop_table(sub[g]) for g in stream]
    B = s * sum(SE.gop_budget(sub, g, q0) for g in stream)
    d = tempfile.mkdtemp(dir=codec._tmpdir())
    out = {}
    try:
        p, src = O._stream(sub, stream, d)
        for name, (mode, tk, extra) in CONFIGS.items():
            try:
                bits, psnr = O._encode(p, src, d, _args(B, tk, extra), mode == "2pass")
            except (RuntimeError, AssertionError) as e:
                out[name] = {"failed": True, "err": str(e)[-300:]}
                continue
            gb, gp = O._per_gop(bits, psnr)
            tot, mp = float(gb.sum()), float(CE.pooled(gp))
            dps, over, sc = SE.stream_score(tabs, tot, mp, B)
            out[name] = {"bits": tot, "psnr": mp, "use": tot / B, "dpsnr": dps, "over_pct": over,
                         "over": tot > 1.01 * B, "score": sc, "gop_bits": gb.tolist()}
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return (stream, q0, s), {"kind": kind, "group": grp, "B": B, **out}


def check(infos):
    eps = S.episodes(infos, "test")
    lines = []
    for kind, grp, st in eps[:2] + eps[-2:]:
        sub = {g: infos[g] for g in st}
        tabs = [CE.gop_table(sub[g]) for g in st]
        d = tempfile.mkdtemp(dir=codec._tmpdir())
        try:
            p, src = O._stream(sub, st, d)
            for q in (30, 38):
                gb, gp = O._per_gop(*O._encode(p, src, d, [*codec.FORCED_ARGS[C.CODEC], "--qp", str(q)]))
                rb = gb / np.array([t["bits"][q] for t in tabs]) - 1
                dp = gp - np.array([t["psnr"][q] for t in tabs])
                lines.append(f"{kind} QP{q}: per-GOP bits rel. diff max {np.abs(rb).max():.4f}, "
                             f"PSNR diff max {np.abs(dp).max():.4f} dB")
        finally:
            shutil.rmtree(d, ignore_errors=True)
    for x in lines:
        log(x)
    return lines


def report(st, infos):
    enc = st.load("run")
    keys = sorted(enc)
    base = pickle.load(open(os.path.join(C.WORK, "results_stream", "baselines.pkl"), "rb"))
    M = {}
    names = {"rule": "rule (tuned), L={}", "hindsight": "hindsight per-GOP plan", "const": "best constant QP (offline)",
             "split": "equal split per GOP"}
    for (k, look, split), rows in base["rows"].items():
        if split == "test":
            M[names[k].format(look)] = S.frame([rows])
    for m in ("bc_ppo", "ppo", "bc_ppo_lag"):
        for L in (0, 2):
            seeds = [pickle.load(open(p, "rb"))["res"]["test"]
                     for p in sorted(glob.glob(os.path.join(C.WORK, "results_stream", f"{m}_L{L}_s*", "eval.pkl")))]
            if seeds:
                M[f"RL {m}, L={L}"] = S.frame(seeds)
    for name in CONFIGS:
        rows = {k: v[name] for k, v in enc.items() if not v[name].get("failed")}
        df = pd.DataFrame([{**rows[k], "kind": enc[k]["kind"], "group": enc[k]["group"]} for k in rows],
                          index=pd.Index(list(rows), tupleize_cols=False))
        M[f"{C.CODEC} {name}"] = df
    failed = {n: sum(bool(enc[k][n].get("failed")) for k in keys) for n in CONFIGS}
    rows = []
    for m, df in M.items():
        df = df.loc[[k for k in keys if k in df.index]]
        rows.append({"method": m, "cases": len(df), "score (dB)": df.score.mean(), "dPSNR_B": df.dpsnr.mean(),
                     "use": f"{100 * df.use.mean():.1f}%", ">1% over": f"{100 * df.over.astype(float).mean():.0f}%",
                     "mean over %": df.over_pct.mean(), "same-clip": df[df.kind == "clip"].score.mean(),
                     "mixed": df[df.kind == "mixed"].score.mean()})
    E = C.CODEC
    pairs = [("RL bc_ppo, L=2", f"{E} abr_tree", "causal RL vs causal encoder ABR (+cutree)"),
             ("RL ppo, L=2", f"{E} abr_tree", "causal RL vs causal encoder ABR (+cutree)"),
             ("RL bc_ppo, L=2", f"{E} abr_vbv", "causal RL vs ABR+VBV"),
             ("RL bc_ppo, L=0", f"{E} abr", "causal, no lookahead each"),
             ("rule (tuned), L=2", f"{E} abr_tree", "non-learned vs encoder"),
             ("RL bc_ppo, L=2", f"{E} 2pass", "causal RL vs non-causal two-pass"),
             ("hindsight per-GOP plan", f"{E} 2pass", "both non-causal")]
    prs = []
    for a, b, note in pairs:
        if a not in M or b not in M:
            continue
        ks = [k for k in keys if k in M[a].index and k in M[b].index]
        d = M[a].loc[ks].score.values - M[b].loc[ks].score.values
        t = S.cboot(d, M[a].loc[ks].group.values)
        ov = 100 * (M[a].loc[ks].over.astype(float).values - M[b].loc[ks].over.astype(float).values)
        prs.append({"A": a, "B": b, "comparison": note, "cases": len(ks),
                    "score A-B (dB)": f"{t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]", ">1% over A-B (pts)": f"{ov.mean():+.1f}"})
    out = [f"# Stream RL vs the encoder's own rate control ({E}, v1 test streams, dB metric)", "",
           f"{len(keys)} cases = {len(set(k[0] for k in keys))} streams of {SE.N_GOP} GOPs x 4 budget levels at s = 1 "
           "(budget = sum of the GOPs' budgets.csv budgets). The encoder codes each stream as one encode told the budget as "
           "an average bitrate and picks a QP per frame; RL and the rule pick one QP per GOP (curve lookups). Score = "
           "dPSNR_B - 0.17 dB per 1 % over on the stream's pooled PSNR. CIs: cluster bootstrap over source groups (mixed "
           f"streams: each its own cluster). Failed encodes (left out): {failed}.", "",
           pd.DataFrame(rows).round(3).to_markdown(index=False), "", "## Paired differences", "",
           pd.DataFrame(prs).to_markdown(index=False), ""]
    if st.done("check"):
        out += ["## Check (stream encode vs v1 per-GOP curves)", ""] + [f"- {x}" for x in st.load("check")] + [""]
    os.makedirs(S.REPORTS, exist_ok=True)
    p = os.path.join(S.REPORTS, "own_rc_stream_v1_report.md")
    open(p, "w").write("\n".join(out))
    print("\n".join(out))
    print(f"wrote {p}")


def main():
    a = runner.args()
    st = runner.Stages("own_rc_stream_v1", a.quick)
    infos = S.load_infos()
    if a.report:
        return report(st, infos)
    s = a.stage
    if s in (None, "check"):
        st.run("check", lambda: check(infos))
    if s in (None, "run"):
        mine = data.shard(cases(infos, a.quick), a.nshards, a.shard)
        items = [(k, g, stv, q0, sv, {x: infos[x] for x in stv}) for k, g, stv, q0, sv in mine]
        st.run("run", lambda: dict(runner.pmap(_case, items, desc="own_rc_stream_v1")), a.shard, a.nshards)
    if s == "gather" or (s is None and a.nshards == 1):
        st.gather("run", a.nshards)
        report(st, infos)


if __name__ == "__main__":
    main()
