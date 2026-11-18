"""D42: two attempts to close more of the vbv2 -> oracle gap (D41) on the live-channel task (rclib/bufenv.py).

Same decision, action space (offset -6..+6 on the vbv2 QP), score, base rule, network and evaluation cases as ppo_v2
(D39, experiments/buffer_rl.py); only the training changes.

* ppo_mix  (idea 2, channel randomisation): one policy for both channels. Each training episode draws its channel:
  half AR(1) with rho ~ U(0.5, 0.95), sigma ~ U(0.1, 0.6) (D39 tested 0.8 / 0.15-0.5), half a window of a training
  LTE trace. The base rule switches with the channel (each channel's own val-tuned vbv2, as ppo_v2). Evaluated on both
  channels' test cases with that channel's base rule, so the comparison with ppo_v2 is paired.
* ppo_mixh: ppo_mix plus the last H_HIST observed channel rates (log2 of rate / mean) in the observation; ppo_v2 sees
  only the last rate and a smoothed average.
* il / il_ppo (idea 1, imitation of the D41 oracle): DAgger on the channel ppo_v2 trained on (RC_BUF_CHANNEL). The
  teacher at a visited state (GOP i, buffer F, QPs so far) replays every D41 DP policy from that state with the true
  future channel and curves, keeps the best full plan by the exact score (and the teacher's previous plan if it is
  still feasible), and its next QP is the label (offset clipped to +-6). The student sees only the ppo_v2
  observation. Iteration k rolls out the teacher with probability 0.5^k, else the student. il = the DAgger policy;
  il_ppo = il after a critic warm-up and PPO fine-tuning (lower learning rate, fewer steps).

  RC_CODEC=x265 RC_WORK=/scratch1/pbanga/rcwork_v1/x265 RC_V1=1 [RC_BUF_CHANNEL=trace] \
      python experiments/buffer_rl2.py --method ppo_mix|ppo_mixh|il --seed 0 [--quick] | --report
"""
import argparse
import os
import pickle
import sys
import time

import numpy as np
import torch
from gymnasium import spaces

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import buffer_oracle as BO, buffer_rl as BR, stream_rl as S  # noqa: E402
from rclib import bufenv as BE, clipenv as CE, config as C  # noqa: E402

H_HIST = 8
WIDE_ACTS = tuple(range(-24, 7))   # --wide: offsets -24..+6 on the vbv2 QP (D41 oracle wants up to ~-16 below vbv2 on training streams)
WIDE = False                       # set from --wide in main()
RAND = {"rho": (0.5, 0.95), "sigma": (0.1, 0.6)}
IL = {"iters": 4, "eps": 1000, "epochs": 10, "bc_lr": 1e-3, "batch": 512, "v_eps": 1000, "v_epochs": 20,
      "ft_steps": 1_000_000, "ft_lr": 1e-4, "ft_ent": 0.003}
QUICK = {"iters": 2, "eps": 20, "epochs": 2, "v_eps": 10, "v_epochs": 2, "ft_steps": 4096}
# result folders per channel; the leak-fixed setting (RC_BUF_LADDER=1, D45) has its own (fixed 2026-11-17: the ladder
# tag was missing here, so D45's first il runs read the leaky-setting baselines and wrote over D42's il / il_ppo files;
# D42's files were restored from the 11-15 handoff copy)
DIRS = {"ar1": "buffer" + ("_ladder" if BE.LADDER else ""), "trace": "buffer_trace" + ("_ladder" if BE.LADDER else "")}
log = S.log


def tuned(ch):
    d = C.results_dir(DIRS[ch])
    bs = pickle.load(open(os.path.join(d, "baselines.pkl"), "rb"))
    b2 = pickle.load(open(os.path.join(d, "baselines2.pkl"), "rb"))
    return bs["tune"][2], bs["c0"], b2["vbv2"]


class Env2(BE.BufEnv):
    """BufEnv with optional channel randomisation (mix = {ch: (tune, vbv2 params)}) and rate history (hist)."""

    def __init__(self, *args, hist=False, mix=None, wide=False, **kw):
        self.hist, self.mix, self.wide = hist, mix, wide
        super().__init__(*args, **kw)
        if hist:
            self.observation_space = spaces.Box(-10, 10, (BE.OBS_DIM + H_HIST,), np.float32)
        if wide:
            self.action_space = spaces.Discrete(len(WIDE_ACTS))

    def set_base(self, tu, bp):
        self.rp, self.psi, self.alpha, self.bp, self.margin = tu["rp"], tu["psi"], tu["alpha"], bp, tu["rp"]["margin"]

    def reset(self, seed=None, options=None):
        draw = self.mix and not self.forced
        if draw:
            if seed is not None:
                self.rng = np.random.default_rng(seed)
            ch = "trace" if self.rng.random() < 0.5 else "ar1"
            self.set_base(*self.mix[ch])
        o, info = super().reset(seed=seed if not draw else None, options=options)
        if draw:
            if ch == "ar1":
                rho, sig = self.rng.uniform(*RAND["rho"]), self.rng.uniform(*RAND["sigma"])
                x = np.zeros(self.n)
                x[0] = self.rng.normal(0, sig / np.sqrt(1 - rho ** 2))
                for i in range(1, self.n):
                    x[i] = rho * x[i - 1] + self.rng.normal(0, sig)
                m = np.exp(x)
                self.m = m / m.mean()
            else:
                self.m = BE.trace_channel(self.n, self.rng, "train")
            o = self._obs()
        return o, info

    def _obs(self):
        o = super()._obs()
        if not getattr(self, "hist", False):
            return o
        h = np.zeros(H_HIST, np.float32)
        rs = getattr(self, "Rseen", None)
        if self.m is not None and rs:
            r = np.log2(np.array(rs[-H_HIST:]) / self.mean_r)[::-1]
            h[:len(r)] = r
        return np.clip(np.concatenate([o, h]), -10, 10)

    def step(self, a, q=None):
        if self.wide and q is None:    # wide offset -> QP; the stored action (shown in the obs) is clipped to +-6
            off = WIDE_ACTS[int(a)]
            q = int(np.clip(round(self.q_hat()) + off, C.QP_MIN, C.QP_MAX))
            a = int(np.clip(off, CE.ACTIONS[0], CE.ACTIONS[-1])) - CE.ACTIONS[0]
        o, r, done, trunc, info = super().step(a, q=q)
        if done and self.hist:
            o = np.zeros(BE.OBS_DIM + H_HIST, np.float32)
        return o, r, done, trunc, info


def make_env2(split, ch, hist=False, seed=0, mix=None, cls=None, **ekw):
    """Evaluation env (split in val / test / test16) or, split='train', a training env. cls / ekw: an Env2 subclass
    and its extra arguments (D43)."""
    cls = cls or Env2
    infos, Y = BR.data()
    tu, c0, bp = tuned(ch)
    sp = {"val": "val", "train": "train"}.get(split, "test")
    kw = dict(look=2, c0=c0, rp=tu["rp"], base="vbv2", psi=tu["psi"], alpha=tu["alpha"], split=sp, bp=bp)
    if split == "train":
        e = cls(infos, S.split_ids(infos, "train"), Y, seed=seed, hist=hist, mix=mix, wide=WIDE, **kw, **ekw)
    else:
        e = cls(infos, S.split_ids(infos, sp), Y, n=BR.n_of(split), nrange=None, hist=hist, wide=WIDE, **kw, **ekw)
    e.margin = tu["rp"]["margin"]
    return e


def evaluate_all(model, name, chans, hist, args, t0, quick, ekw=None, save=False):
    for ch in chans:
        BE.CHANNEL = ch        # read by BufEnv.reset
        res = {}
        for split, c in BR.case_sets().items():
            if quick:
                c = c[::60]
            res[split] = BR.evaluate(BR.Actor(model), c, make_env2(split, ch, hist, **(ekw or {})))
            log(f"{name} [{ch}] {split}: score {np.mean([r['score'] for r in res[split]]):+.3f}, "
                f"stall {np.mean([r['stall_pct'] for r in res[split]]):.2f}% ({len(c)} cases)")
        out = os.path.join(C.results_dir(DIRS[ch]), ("debug_rl2" if quick else ""), name)
        os.makedirs(out, exist_ok=True)
        pickle.dump({"args": {**args, "method": name.split("_L2_")[0], "look": 2}, "res": res, "seconds": time.time() - t0},
                    open(os.path.join(out, "eval.pkl"), "wb"))
        if save:
            model.save(os.path.join(out, "model.zip"))


def ppo_model(venv, seed, lr, ent):
    from stable_baselines3 import PPO
    pk = {"net_arch": {"pi": [128, 128], "vf": [128, 128]}, "activation_fn": torch.nn.ReLU}
    return PPO("MlpPolicy", venv, learning_rate=lr, n_steps=BR.CFG["n_steps"], batch_size=BR.CFG["batch"],
               n_epochs=BR.CFG["epochs"], gamma=1.0, gae_lambda=0.95, ent_coef=ent, policy_kwargs=pk, seed=seed,
               device="cpu", verbose=0)


def tracker(t0, curve):
    from stable_baselines3.common.callbacks import BaseCallback

    class Track(BaseCallback):
        def _on_step(self):
            for inf, d in zip(self.locals["infos"], self.locals["dones"]):
                if d and "score" in inf:
                    curve.append((self.num_timesteps, inf["score"], inf["stall_pct"], inf["over"], inf["use"]))
            if self.num_timesteps % 200_000 < BR.CFG["n_envs"] and curve:
                r = np.array(curve[-2000:])
                log(f"  steps {self.num_timesteps}: score {r[:, 1].mean():+.3f} dB, stall {r[:, 2].mean():.2f}% "
                    f"({(time.time() - t0) / 60:.0f} min)")
            return True
    return Track()


def run_mix(a):
    from stable_baselines3.common.vec_env import DummyVecEnv
    hist = a.method == "ppo_mixh"
    name, t0 = f"{a.method}_L2_s{a.seed}", time.time()
    if a.method == "ppo_wide":     # ppo_v2 with offsets -15..+6: one channel (RC_BUF_CHANNEL), as ppo_v2
        mix, ch, chans = None, BE.CHANNEL, (BE.CHANNEL,)
    else:
        mix, ch, chans = {c: (tuned(c)[0], tuned(c)[2]) for c in DIRS}, "ar1", ("ar1", "trace")
    venv = DummyVecEnv([(lambda i=i: make_env2("train", ch, hist, 1000 * a.seed + i, mix))
                        for i in range(BR.CFG["n_envs"])])
    model = ppo_model(venv, a.seed, BR.CFG["lr"], BR.CFG["ent"])
    curve = []
    model.learn(total_timesteps=4096 if a.quick else BR.CFG["ppo_steps"], callback=tracker(t0, curve))
    evaluate_all(model, name, chans, hist, vars(a), t0, a.quick)
    log(f"{name}: {(time.time() - t0) / 60:.1f} min")


class Teacher:
    """D41 oracle from any state of the current episode (true future channel and curves)."""

    def __init__(self, env):
        self.cs = BO.Case(env)
        self.pol = self.cs.dp_policy()
        self.prev = None

    def qp(self, env):
        cs, i = self.cs, env.i
        pre = np.asarray(env.qps, int) - C.QP_MIN
        plans, st = cs.rollout(self.pol, i, env.F)
        full = np.hstack([np.tile(pre, (len(plans), 1)), plans])
        st = st + sum(env.stalls)
        if self.prev is not None and np.array_equal(self.prev[:i], pre):
            p2, s2 = self.prev[None], np.array([self.prev_st])
            full, st = np.vstack([full, p2]), np.concatenate([st, s2])
        sc = cs.score_many(full, st)
        k = int(np.argmax(sc))
        self.prev, self.prev_st = full[k], st[k]
        return int(cs.q[full[k][i]]), float(sc[k])

    def action(self, env):
        q, s = self.qp(env)
        acts = WIDE_ACTS if WIDE else CE.ACTIONS
        return int(np.clip(q - round(env.q_hat()), acts[0], acts[-1])) - acts[0], s


def run_il(a, ekw=None, mdl=None, pre=None, ft=None, save=False, eval_il=True):
    """D42 DAgger -> critic warm-up -> PPO. D43 reuses it: ekw = env extras (privileged obs), mdl = model builder,
    pre / ft = output names of the DAgger / fine-tuned policies, save = keep model.zip, eval_il = evaluate the
    DAgger policy too."""
    from stable_baselines3.common.vec_env import DummyVecEnv
    ekw, mdl = ekw or {}, mdl or ppo_model
    cfg = dict(IL, **(QUICK if a.quick else {}))
    ch, t0 = BE.CHANNEL, time.time()
    rng = np.random.default_rng(a.seed)
    env = make_env2("train", ch, seed=777 + a.seed, **ekw)
    venv = DummyVecEnv([(lambda i=i: make_env2("train", ch, seed=1000 * a.seed + i, **ekw))
                        for i in range(BR.CFG["n_envs"])])
    model = mdl(venv, a.seed, cfg["ft_lr"], cfg["ft_ent"])
    pol = model.policy
    opt = torch.optim.Adam(pol.parameters(), lr=cfg["bc_lr"])
    O, A = [], []
    for it in range(cfg["iters"]):
        beta = 0.5 ** it
        tsc, fin = [], []
        for _ in range(cfg["eps"]):
            o, _ = env.reset()
            te, done = Teacher(env), False
            while not done:
                at, s = te.action(env)
                O.append(o)
                A.append(at)
                act = at if rng.random() < beta else int(model.predict(o, deterministic=True)[0])
                o, _, done, _, res = env.step(act)
            tsc.append(s)
            fin.append(res["score"])
        X, Yt = torch.tensor(np.array(O), dtype=torch.float32), torch.tensor(np.array(A))
        for _ in range(cfg["epochs"]):
            perm = torch.randperm(len(X))
            for j in range(0, len(X), cfg["batch"]):
                b = perm[j:j + cfg["batch"]]
                _, lp, _ = pol.evaluate_actions(X[b], Yt[b])
                loss = -lp.mean()
                opt.zero_grad()
                loss.backward()
                opt.step()
        with torch.no_grad():
            acc = float((pol.get_distribution(X).distribution.probs.argmax(1) == Yt).float().mean())
        log(f"  DAgger iter {it} (beta {beta:.3f}): {len(X)} labels, teacher plan {np.mean(tsc):+.3f} dB, "
            f"episodes {np.mean(fin):+.3f} dB, train acc {acc:.2f}, NLL {loss.item():.3f} "
            f"({(time.time() - t0) / 60:.0f} min)")
    pre = pre or ("il_w" if WIDE else "il")
    ft = ft or f"{pre}_ppo"
    if eval_il:
        evaluate_all(model, f"{pre}_L2_s{a.seed}", (ch,), False, vars(a), t0, a.quick, ekw, save)
    # critic warm-up on the student's own returns (reward = final score, gamma 1), value parameters only
    Ov, Rv = [], []
    for _ in range(cfg["v_eps"]):
        o, _ = env.reset()
        done, obs = False, []
        while not done:
            obs.append(o)
            o, _, done, _, res = env.step(int(model.predict(o, deterministic=False)[0]))
        Ov += obs
        Rv += [res["score"]] * len(obs)
    X, Rt = torch.tensor(np.array(Ov), dtype=torch.float32), torch.tensor(np.array(Rv), dtype=torch.float32)
    vp = list(pol.mlp_extractor.value_net.parameters()) + list(pol.value_net.parameters())
    vopt = torch.optim.Adam(vp, lr=1e-3)
    for _ in range(cfg["v_epochs"]):
        perm = torch.randperm(len(X))
        for j in range(0, len(X), cfg["batch"]):
            b = perm[j:j + cfg["batch"]]
            vl = ((pol.predict_values(X[b]).squeeze(1) - Rt[b]) ** 2).mean()
            vopt.zero_grad()
            vl.backward()
            vopt.step()
    log(f"  critic warm-up: {len(X)} states, value MSE {vl.item():.3f}")
    curve = []
    model.learn(total_timesteps=cfg["ft_steps"], callback=tracker(t0, curve))
    evaluate_all(model, f"{ft}_L2_s{a.seed}", (ch,), False, vars(a), t0, a.quick, ekw, save)
    log(f"il seed {a.seed} [{ch}]: {(time.time() - t0) / 60:.1f} min")


def main():
    assert C.V1, "set RC_V1=1"
    p = argparse.ArgumentParser()
    p.add_argument("--method", default="ppo_mix", choices=("ppo_mix", "ppo_mixh", "ppo_wide", "il"))
    p.add_argument("--wide", action="store_true", help="offsets -24..+6 (WIDE_ACTS): il -> il_w, il_w_ppo; implied by ppo_wide")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--quick", action="store_true", help="tiny run for the debug partition (outputs under debug_rl2)")
    p.add_argument("--report", action="store_true", help="D39 buffer report and D41 oracle report for RC_BUF_CHANNEL")
    a = p.parse_args()
    global WIDE
    WIDE = a.wide or a.method == "ppo_wide"
    torch.set_num_threads(2)
    if a.report:
        BR.report()
        BO.report()
    elif a.method == "il":
        run_il(a)
    else:
        run_mix(a)


if __name__ == "__main__":
    main()
