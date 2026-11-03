"""Env smoke test: gymnasium env_checker, then a few episodes with per-frame output.

    source env.sh && make
    python3 tests/test_env.py /path/to/clip.y4m [--budget 45000] [--k 5]

Episodes: constant dqp=0, random actions, and random actions under a tight
budget (budget/2) to exercise the shield.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from gymnasium.utils.env_checker import check_env

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from x264env.env import OBS_FIELDS, RateControlEnv  # noqa: E402


def run_episode(env, name, policy, options, rng):
    obs, _ = env.reset(options=options)
    assert env.observation_space.contains(obs), "reset obs outside observation_space"
    print(f"\n=== {name}: budget {options['budget']} slice bits, k={options['k']}, "
          f"base_qp={options['base_qp']}, dqp_mode={env.dqp_mode}")
    print(f"{'t':>3} {'type':>4} {'dqp':>4} {'qp':>3} {'slice':>7} {'header':>6} "
          f"{'PSNR-Y':>7} {'left':>7} shield")
    t, done, ret, fired = 0, False, 0.0, 0
    while not done:
        a = policy(rng)
        obs, r, done, trunc, info = env.step(a)
        assert env.observation_space.contains(obs), f"obs outside space at t={t}: {obs}"
        assert not trunc
        ret += r
        fired += info["shield_fired"]
        print(f"{t:3d} {info['frame_type']:>4} {a - 4:+4d} {info['qp']:3d} {info['slice_bits']:7d} "
              f"{info['header_bits']:6d} {info['psnr']:7.2f} {info['budget_left']:7d} "
              f"{'FIRED' if info['shield_fired'] else ''}")
        t += 1
    print(f"total slice bits {info['total_slice_bits']} vs budget {options['budget']} "
          f"-> overshoot {info['overshoot']:+.1%}; mean PSNR-Y {ret / t:.2f} dB; "
          f"shield fired on {fired}/{t} frames")
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--budget", type=int, default=45000)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--base-qp", type=int, default=31)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    env = RateControlEnv(clip=args.clip, budget=args.budget, k=args.k, base_qp=args.base_qp)
    check_env(env, skip_render_check=True)
    print("gymnasium env_checker: passed")
    print("obs fields:", ", ".join(OBS_FIELDS))

    opts = dict(clip=args.clip, gop=0, budget=args.budget, k=args.k, base_qp=args.base_qp)
    rng = np.random.default_rng(args.seed)
    run_episode(env, "constant dqp=0", lambda r: 4, opts, rng)
    run_episode(env, f"random actions (seed {args.seed})", lambda r: int(r.integers(9)), opts, rng)
    tight = {**opts, "budget": args.budget // 2}
    run_episode(env, "random actions, tight budget", lambda r: int(r.integers(9)), tight, rng)

    # k=0: lookahead must be all zeros with mask 0
    obs, _ = env.reset(options={**opts, "k": 0})
    assert not obs[11:].any(), obs[11:]
    # dqp_mode="base": qp = base_qp + dqp every frame (shield off to isolate it)
    benv = RateControlEnv(clip=args.clip, budget=10**9, base_qp=31, dqp_mode="base", shield=False)
    benv.reset()
    qps = [benv.step(a)[4]["qp"] for a in [8, 8, 0, 4, 2]]
    assert qps == [35, 35, 27, 31, 29], qps
    # clipping to [11, 51] in "prev" mode
    cenv = RateControlEnv(clip=args.clip, budget=10**9, base_qp=49, shield=False)
    cenv.reset()
    qps = [cenv.step(8)[4]["qp"] for _ in range(3)]
    assert qps == [51, 51, 51], qps
    print("\nk=0 mask, dqp_mode='base', QP clipping: ok")
    env.close(); benv.close(); cenv.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
