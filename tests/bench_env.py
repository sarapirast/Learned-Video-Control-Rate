"""Env throughput benchmark: one env process pinned to one core, real clips.

    source env.sh && make
    python3 tests/bench_env.py [--episodes 60] [--data /path/to/data/v1/320x180]

Samples real 30-frame GOPs from P2's gops.csv (fixed seed; the same GOPs for
every config) and runs four configs: {random actions, constant dqp=0} x
{k=0, k=30}. Reports episodes/s, CPU time per episode, a per-step breakdown
(encode / MSE+PSNR / observation / other), the reset breakdown (GOP load from
disk + complexity features / encoder open), and RAM per env.
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")   # before numpy is imported

import argparse  # noqa: E402
import csv  # noqa: E402
import platform  # noqa: E402
import resource  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import x264env.encoder as encmod  # noqa: E402
from x264env.env import GOP_LEN, RateControlEnv  # noqa: E402

DEFAULT_DATA = "/scratch1/aayushso/ee599/data/v1/320x180"
T = defaultdict(float)   # accumulated seconds per timer
N = defaultdict(int)     # call counts


def timed(name, fn):
    def wrapper(*a, **kw):
        t0 = time.perf_counter()
        try:
            return fn(*a, **kw)
        finally:
            T[name] += time.perf_counter() - t0
            N[name] += 1
    return wrapper


def rss_mib(field="VmRSS") -> float:
    for line in open("/proc/self/status"):
        if line.startswith(field + ":"):
            return int(line.split()[1]) / 1024
    return float("nan")


def instrument(env: RateControlEnv) -> None:
    env._luma_mse_psnr = timed("psnr", env._luma_mse_psnr)
    env._obs = timed("obs", env._obs)
    env._load_gop = timed("reset_load_gop", env._load_gop)


def cpu_info() -> str:
    for line in open("/proc/cpuinfo"):
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=DEFAULT_DATA, help="data/v1/320x180 dir (gops.csv, clips/)")
    ap.add_argument("--episodes", type=int, default=60, help="episodes per config")
    ap.add_argument("--budget", type=int, default=172800,
                    help="slice-bit budget per GOP (default 0.1 bit/pixel)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    # one core, explicitly
    cpu = sorted(os.sched_getaffinity(0))[0]
    os.sched_setaffinity(0, {cpu})
    rss_imports = rss_mib()

    data = Path(args.data)
    rows = [r for r in csv.DictReader(open(data / "gops.csv")) if int(r["n_frames"]) == GOP_LEN]
    rng = np.random.default_rng(args.seed)
    pick = [rows[i] for i in rng.choice(len(rows), args.episodes, replace=False)]
    gops = [(str(data / "clips" / f"{r['clip_id']}.y4m"), int(r["gop"])) for r in pick]

    print(f"node {platform.node()}, CPU {cpu_info()}, pinned to core {cpu}, "
          f"SLURM job {os.environ.get('SLURM_JOB_ID', '-')} "
          f"({os.environ.get('SLURM_CPUS_ON_NODE', '?')} cores allocated), "
          f"load avg {os.getloadavg()[0]:.1f}/{os.cpu_count()}")
    print(f"{len(gops)} real GOPs from {len(set(c for c, _ in gops))} clips "
          f"(GOP index {min(g for _, g in gops)}..{max(g for _, g in gops)}), "
          f"{args.episodes} episodes per config, budget {args.budget} slice bits\n")

    # instrument the encoder class (every Encoder instance)
    encmod.Encoder.encode = timed("encode", encmod.Encoder.encode)
    encmod.Encoder.__init__ = timed("reset_encoder_open", encmod.Encoder.__init__)

    # warm-up: read every GOP once so the timed runs see the page cache, not cold BeeGFS
    t0 = time.perf_counter()
    warm = RateControlEnv(budget=args.budget)
    for clip, g in gops:
        warm._load_gop(clip, g)
    cold_load = (time.perf_counter() - t0) / len(gops)
    warm.close()
    del warm

    configs = [("random", 0), ("random", 30), ("dqp=0", 0), ("dqp=0", 30)]
    results = []
    for policy, k in configs:
        T.clear(); N.clear()
        env = RateControlEnv(budget=args.budget, k=k, base_qp=31)
        instrument(env)
        prng = np.random.default_rng(args.seed)
        qps, fired = [], 0
        w0, c0 = time.perf_counter(), time.process_time()
        for clip, g in gops:
            r0 = time.perf_counter()
            env.reset(options={"clip": clip, "gop": g, "k": k})
            T["reset"] += time.perf_counter() - r0
            for _ in range(GOP_LEN):
                a = int(prng.integers(9)) if policy == "random" else 4
                s0 = time.perf_counter()
                _, _, _, _, info = env.step(a)
                T["step"] += time.perf_counter() - s0
                qps.append(info["qp"]); fired += info["shield_fired"]
        wall, cpu_s = time.perf_counter() - w0, time.process_time() - c0
        env.close()
        n_steps = args.episodes * GOP_LEN
        # _obs runs once per step and once per reset; count only the step share here
        obs_step = T["obs"] * n_steps / (n_steps + args.episodes)
        res = dict(policy=policy, k=k, eps=args.episodes / wall, cpu_ep=cpu_s / args.episodes * 1e3,
                   wall=wall, util=cpu_s / wall,
                   enc=T["encode"] / n_steps * 1e3, psnr=T["psnr"] / n_steps * 1e3,
                   obs=obs_step / n_steps * 1e3,
                   other=(T["step"] - T["encode"] - T["psnr"] - obs_step) / n_steps * 1e3,
                   step=T["step"] / n_steps * 1e3, reset=T["reset"] / args.episodes * 1e3,
                   load=T["reset_load_gop"] / args.episodes * 1e3,
                   open=T["reset_encoder_open"] / args.episodes * 1e3,
                   eps_no_load=args.episodes / (wall - T["reset_load_gop"]),
                   mean_qp=float(np.mean(qps)), fired=fired / n_steps)
        results.append(res)
        print(f"[{policy:6s} k={k:2d}] {res['eps']:5.1f} episodes/s  "
              f"({res['cpu_ep']:.0f} ms CPU/episode, CPU/wall {res['util']:.2f}, mean QP {res['mean_qp']:.1f}, "
              f"shield {res['fired']:.0%} of steps)")

    print("\nper step (ms):        encode  MSE+PSNR    obs   other |  step   | per episode (ms): reset = load GOP + enc open + rest")
    for r in results:
        rest = r["reset"] - r["load"] - r["open"]
        print(f"  {r['policy']:6s} k={r['k']:2d}        {r['enc']:6.2f}  {r['psnr']:8.3f}  {r['obs']:5.3f}  {r['other']:6.3f} | {r['step']:6.2f}  "
              f"|   {r['reset']:6.1f} = {r['load']:6.1f} + {r['open']:5.2f} + {rest:5.2f}")
    print(f"\nGOP load from disk, first (cold) read: {cold_load * 1e3:.1f} ms per GOP")
    print("episodes/s if GOP frames were already in RAM (excludes load GOP): "
          + ", ".join(f"{r['policy']} k={r['k']}: {r['eps_no_load']:.1f}" for r in results))

    # RAM: RSS after imports, after 1 env, after 4 envs (each reset + one episode)
    envs = []
    rss = [rss_mib()]
    for i in range(4):
        e = RateControlEnv(budget=args.budget, k=30)
        clip, g = gops[i]
        e.reset(options={"clip": clip, "gop": g})
        for _ in range(GOP_LEN - 1):   # stay mid-episode so the encoder is still open
            e.step(4)
        envs.append(e)
        rss.append(rss_mib())
    per_env = (rss[4] - rss[1]) / 3
    print(f"\nRAM: RSS after imports {rss_imports:.0f} MiB; with 1 env {rss[1]:.0f} MiB; with 4 envs "
          f"{rss[4]:.0f} MiB -> about {per_env:.1f} MiB per extra env (open encoder, cached GOP, "
          f"episode buffers); peak RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} MiB")
    for e in envs:
        e.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
