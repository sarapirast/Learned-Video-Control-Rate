"""Fair head-to-head (D29): the encoders' own rate control on the multi-GOP streams of the D25 setting (clipenv.py).

Same test streams, budgets and score as experiments/clip_rl.py, so every case pairs with the RL controllers' results.
Neither side gets an oracle base QP: the RL controller is told the stream's bit budget and derives its QP from a
first-pass rate model calibrated online; the encoder is told the same budget as an average bitrate. The encoder
codes the 8 GOPs as one 240-frame stream (IDR every 30 frames, closed GOPs, no scene-cut keyframes, the same tools
as the constant-QP curves), so its rate control carries state across GOPs as the RL controller's does.

Information matched per config:
  RL L=0 sees the current GOP's first pass (30 frames)        <->  ABR + cutree, --rc-lookahead 30
  RL L=2 sees 2 more GOPs (90 frames)                         <->  ABR + cutree, --rc-lookahead 90
  (ABR without cutree/mb-tree ignores --rc-lookahead: the debug check gave identical bitstreams at 30 and 90)
  hindsight plan knows every GOP's real RD curve (non-causal) <->  two-pass ABR (whole-stream first pass)
Remaining differences (stated in the report): the encoder picks a QP per frame, the RL controller one per GOP
(favours the encoder); x264 ABR without mb-tree makes little use of its lookahead.
The bitrate is passed as integer kbps with the frame rate set so that kbps / fps equals budget / 240 frames exactly.

stages
  check   4 test streams: constant QP 30 / 38 on the concatenated stream must reproduce the per-GOP curve bits and
          PSNR (stream encode == 8 independent GOP encodes); and whether lookahead 30 vs 90 changes the ABR output
  run     every test case x every config [sharded]; then --stage gather
  python experiments/own_rc_stream.py --report
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
from rclib import clipenv as CE, codec, config as C, data, metrics, runner  # noqa: E402
from rclib.runner import log  # noqa: E402

CONFIGS = {   # name: (mode, tools, rc-lookahead frames); tools: plain = AQ and cutree/mb-tree off (as the curves),
              # tree = cutree/mb-tree on, AQ off (the only plain-PSNR way ABR uses its lookahead), aq = encoder defaults
    "abr": ("abr", "plain", 30),          # ABR without cutree ignores rc-lookahead (check stage: 30 and 90 identical)
    "abr_tree_la30": ("abr", "tree", 30),
    "abr_tree_la90": ("abr", "tree", 90),
    "2pass": ("2pass", "plain", 30),
    "abr_aq_la30": ("abr", "aq", 30),
    "2pass_aq": ("2pass", "aq", 30),
}
TOOLS = {"plain": codec.FORCED_ARGS, "aq": codec.OWN_AQ_ARGS,
         "tree": {"x265": ["--aq-mode", "0", "--cutree"], "x264": ["--aq-mode", "0", "--mbtree"]}}
N = CE.N_GOP * C.GOP


def load_infos():
    with open(os.path.join(C.WORK, "results_infos", "infos_slim.pkl"), "rb") as f:
        return pickle.load(f)


def cases(infos, quick=False):
    eps = CE.episodes(infos, "test")
    if quick:
        eps = eps[:2] + eps[-2:]
    return [(kind, st, q0, s) for kind, st in eps for q0 in CE.EVAL_Q0 for s in CE.EVAL_S]


def _stream(sub, stream, d):
    src = np.concatenate([data.gop_frames(sub[g]["gop"]) for g in stream])
    p = os.path.join(d, "stream.yuv")
    src.tofile(p)
    return p, src


def _encode(p, src, d, extra, two_pass=False):
    out = os.path.join(d, "out." + ("hevc" if C.CODEC == "x265" else "264"))
    base = [*extra, *(["--repeat-headers"] if C.CODEC == "x265" else [])]   # x264 repeats SPS/PPS at IDR by default
    if two_pass:
        stats = os.path.join(d, "stats.log")
        for k in (1, 2):
            codec._run(codec._cmd(C.CODEC, p, N, out, [*base, "--pass", str(k), "--stats", stats]))
    else:
        codec._run(codec._cmd(C.CODEC, p, N, out, base))
    with open(out, "rb") as f:
        bits = codec.frame_bits(f.read(), C.CODEC)
    assert len(bits) == N, (len(bits), N)
    psnr, _ = codec._psnr(src, codec.decode(out, N))
    return bits, psnr


def _per_gop(bits, psnr):
    return bits.reshape(CE.N_GOP, C.GOP).sum(1), psnr.reshape(CE.N_GOP, C.GOP).mean(1)


def _rc_args(B):
    """Integer kbps plus a rational frame rate so that bits per frame = B / N exactly."""
    k = max(1, round(B / N * 30 / 1000))
    return ["--bitrate", str(k), "--fps", f"{k * 1000 * N}/{max(1, int(round(B)))}"]


def _case(item):
    kind, stream, q0, s, sub = item
    tabs = [CE.gop_table(sub[g]) for g in stream]
    B = s * sum(t["bits"][q0] for t in tabs)
    curve = CE.stream_curve(tabs)
    d = tempfile.mkdtemp(dir=codec._tmpdir())
    out = {}
    try:
        p, src = _stream(sub, stream, d)
        for name, (mode, tk, la) in CONFIGS.items():
            tools = TOOLS[tk][C.CODEC]
            try:
                bits, psnr = _encode(p, src, d, [*tools, *_rc_args(B), "--rc-lookahead", str(la)], mode == "2pass")
            except (RuntimeError, AssertionError) as e:
                out[name] = {"failed": True, "err": str(e)[-300:]}
                continue
            gb, gp = _per_gop(bits, psnr)
            tot, mp = float(gb.sum()), float(CE.pooled(gp))
            sav, over = float(metrics.saving(tot, mp, curve)), float(metrics.overshoot(tot, B))
            out[name] = {"bits": tot, "psnr": mp, "saving": sav, "over_pct": over, "over": tot > 1.01 * B,
                         "score": sav - metrics.OVER_PENALTY * over, "gop_bits": gb.tolist()}
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return (stream, q0, s), {"kind": kind, "B": B, **out}


def check(infos):
    eps = CE.episodes(infos, "test")
    lines = []
    for kind, st in eps[:2] + eps[-2:]:
        sub = {g: infos[g] for g in st}
        tabs = [CE.gop_table(sub[g]) for g in st]
        d = tempfile.mkdtemp(dir=codec._tmpdir())
        try:
            p, src = _stream(sub, st, d)
            for q in (30, 38):
                gb, gp = _per_gop(*_encode(p, src, d, [*codec.FORCED_ARGS[C.CODEC], "--qp", str(q)]))
                rb = gb / np.array([t["bits"][q] for t in tabs]) - 1
                dp = gp - np.array([t["psnr"][q] for t in tabs])
                lines.append(f"{kind} QP{q}: per-GOP bits rel. diff max {np.abs(rb).max():.4f}, "
                             f"PSNR diff max {np.abs(dp).max():.4f} dB")
            B = sum(t["bits"][38] for t in tabs)
            for tk in ("plain", "tree"):
                r = {la: _encode(p, src, d, [*TOOLS[tk][C.CODEC], *_rc_args(B), "--rc-lookahead", str(la)])[0]
                     for la in (30, 90)}
                lines.append(f"{kind} ABR ({tk}) at QP38 budget: bits/budget la30 {r[30].sum() / B:.3f}, la90 "
                             f"{r[90].sum() / B:.3f}, identical={bool(np.array_equal(r[30], r[90]))}")
        finally:
            shutil.rmtree(d, ignore_errors=True)
    for x in lines:
        log(x)
    return lines


# ---------------------------------------------------------------- report

def _cluster(key, kind, sub_infos):
    """Bootstrap cluster: the source clip for same-clip streams, the stream itself for mixed streams."""
    return sub_infos[key[0][0]]["gop"]["clip"] if kind == "clip" else "|".join(key[0])


def cboot(d, groups, n=4000, seed=0):
    d = np.asarray(d, float)
    u, inv = np.unique(groups, return_inverse=True)
    sums, cnt = np.bincount(inv, d), np.bincount(inv)
    idx = np.random.default_rng(seed).integers(len(u), size=(n, len(u)))
    m = sums[idx].sum(1) / cnt[idx].sum(1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    return f"{d.mean():+.2f} [{lo:+.2f}, {hi:+.2f}]"


def report(st, infos):
    enc = st.load("run")
    clip_dir = C.results_dir("clip")
    B = pickle.load(open(os.path.join(clip_dir, "baselines.pkl"), "rb"))
    M = {}   # method -> {key: row}
    names = {"rule": "our rule (model QP), L={}", "const": "best constant QP (hindsight)",
             "hindsight": "hindsight per-GOP plan"}
    for (k, look, split), rows in B.items():
        if split == "test":
            M[names[k].format(look)] = {(r["stream"], r["q0"], r["s"]): r for r in rows}
    seeds = {}
    for p in sorted(glob.glob(os.path.join(clip_dir, "*", "eval.pkl"))):
        r = pickle.load(open(p, "rb"))
        seeds.setdefault(f"RL {r['args']['method']}, L={r['args']['look']}", []).append(r["res"]["test"])
    for m, runs in seeds.items():
        keyed = [{(x["stream"], x["q0"], x["s"]): x for x in rows} for rows in runs]
        M[m] = {k: {c: float(np.mean([kr[k][c] for kr in keyed])) for c in ("score", "saving", "over_pct", "over")}
                | {"kind": keyed[0][k]["kind"]} for k in keyed[0]}
    for name in CONFIGS:
        M[f"{C.CODEC} {name}"] = {k: v[name] | {"kind": v["kind"]} for k, v in enc.items()
                                  if not v[name].get("failed")}
    keys = sorted(enc)
    kind = {k: enc[k]["kind"] for k in keys}
    grp = np.array([_cluster(k, kind[k], infos) for k in keys])
    failed = {n: sum(bool(enc[k][n].get("failed")) for k in keys) for n in CONFIGS}

    rows = []
    for m, R in M.items():
        ks = [k for k in keys if k in R]
        df = pd.DataFrame([R[k] for k in ks])
        rows.append({"method": m, "cases": len(ks), "score": df.score.mean(), "saving": df.saving.mean(),
                     ">1% over": f"{100 * df.over.astype(float).mean():.0f}%", "mean % over": df.over_pct.mean(),
                     "score same-clip": df[df.kind == "clip"].score.mean(),
                     "score mixed": df[df.kind == "mixed"].score.mean()})
    E = C.CODEC
    pairs = [("RL bc_ppo, L=0", f"{E} abr", "causal; encoder ABR (uses no lookahead)"),
             ("RL bc_ppo, L=0", f"{E} abr_tree_la30", "causal, 30-frame lookahead each"),
             ("RL bc_ppo, L=2", f"{E} abr_tree_la90", "causal, 90-frame lookahead each"),
             ("RL ppo, L=2", f"{E} abr_tree_la90", "causal, 90-frame lookahead each"),
             ("our rule (model QP), L=0", f"{E} abr_tree_la30", "non-learned vs encoder, same information"),
             ("RL bc_ppo, L=0", f"{E} abr_aq_la30", "encoder with its default AQ/cutree"),
             ("RL bc_ppo, L=2", f"{E} 2pass", "causal RL vs non-causal encoder"),
             ("hindsight per-GOP plan", f"{E} 2pass", "both non-causal")]
    prs = []
    for a, b, note in pairs:
        if a not in M or b not in M:
            continue
        ks = [k for k in keys if k in M[a] and k in M[b]]
        g = np.array([_cluster(k, kind[k], infos) for k in ks])
        prs.append({"A": a, "B": b, "comparison": note, "cases": len(ks),
                    "score A-B": cboot([M[a][k]["score"] - M[b][k]["score"] for k in ks], g),
                    "saving A-B": cboot([M[a][k]["saving"] - M[b][k]["saving"] for k in ks], g),
                    ">1% over A-B (pts)": cboot([100 * (float(M[a][k]["over"]) - float(M[b][k]["over"])) for k in ks], g)})
    out = [f"# Fair head-to-head: learned vs the encoder's own rate control ({E}, multi-GOP test streams)", "",
           f"{len(keys)} cases = {len(set(k[0] for k in keys))} streams of {CE.N_GOP} GOPs x budgets "
           f"(q0 {CE.EVAL_Q0} x s {CE.EVAL_S}). No method gets an oracle QP: each is given the stream's bit budget. "
           "The encoder codes the stream as one 240-frame encode (IDR every 30; plain = AQ/cutree off, tree = cutree on, aq = encoder defaults), "
           "picking a QP per frame; the RL controllers and our rule pick one QP per GOP. "
           "Score = % bits saved at equal pooled PSNR vs the stream's constant-QP curve - 2 x % over budget.", "",
           f"Failed encodes (left out): {failed}. 95 % CIs: bootstrap over {len(set(grp))} clusters (source clip for "
           "same-clip streams, the stream for mixed streams).", "",
           pd.DataFrame(rows).round(2).to_markdown(index=False), "", "## Paired differences", "",
           pd.DataFrame(prs).to_markdown(index=False), ""]
    if st.done("check"):
        out += ["## Check (stream encode vs per-GOP curves)", ""] + [f"- {x}" for x in st.load("check")] + [""]
    p = os.path.join(C.REPORTS, "own_rc_stream_report.md")
    open(p, "w").write("\n".join(out))
    print("\n".join(out))
    print(f"wrote {p}")


def main():
    a = runner.args()
    st = runner.Stages("own_rc_stream", a.quick)
    infos = load_infos()
    if a.report:
        return report(st, infos)
    s = a.stage
    if s in (None, "check"):
        st.run("check", lambda: check(infos))
    if s in (None, "run"):
        mine = data.shard(cases(infos, a.quick), a.nshards, a.shard)
        items = [(k, stv, q0, sv, {g: infos[g] for g in stv}) for k, stv, q0, sv in mine]
        st.run("run", lambda: dict(runner.pmap(_case, items, desc="own_rc_stream")), a.shard, a.nshards)
    if s == "gather" or (s is None and a.nshards == 1):
        st.gather("run", a.nshards)
        report(st, infos)


if __name__ == "__main__":
    main()
