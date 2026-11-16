"""One RL run = one (method, k, lookahead mode, dropped feature groups, prior, seed). One SLURM job each.

methods:  bc | cql | iql                     offline only (from the training search logs)
          cql_ppo | bc_ppo                   offline init + PPO fine-tune (cql_ppo is the core recipe)
          ppo | a2c | dqn                    online from scratch, same number of env steps
          lagr                               cql_ppo with a Lagrangian reward (saving - lam * overshoot), fixed lam
          pid                                cql_ppo with a PID-controlled lam targeting a GOP over-budget rate
          anyk                               cql_ppo trained with a random k per episode (one net for every k/mode)
          mpc                                learned bits/PSNR model + receding-horizon CEM planning (rclib/mpc.py)
          mb                                 cql_ppo whose PPO runs only inside the learned model (rclib/mbenv.py, D26)
          mb_ppo                             mb, then PPO on real encodes (ft_steps)
          res                                residual on P2's causal controller (RC_ARM=res only; v1-data, P2 11-09):
                                             Lagrangian reward relative to the controller's own result, lam 4, the
                                             lagr PPO settings (lr_ft, ppo_steps); no offline data; the policy starts
                                             at P(offset 0) = res_p0 (action-logit bias), critic from scratch
Outputs in $RC_WORK/results_rl/<run>/: model, train curve, val/test episode results (eval.pkl).

  python experiments/rl.py --method cql_ppo --k 5 --seed 0
  python experiments/rl.py --method cql_ppo --k 5 --drop scene,pixel --seed 1
  python experiments/rl.py --method anyk --kmax 29 --seed 0      # then evaluate under many modes with --eval-modes
"""
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.environ.get("RC_ARM") == "lfq":
    # lfq learners (P2 2026-11-10, tracker 30d): offsets +-10 around the causal base (rclib/config.py LFQ_LEARN), infos
    # with the causal base / P2 first pass / no flat GOPs (tools/lfq_infos.py -> results_infos/infos_learn.pkl)
    os.environ.setdefault("RC_ACT_RANGE", "10")
from rclib import config as C, env as E, offrl, policies as P, runner  # noqa: E402
from rclib.runner import log  # noqa: E402

CFG = {"ppo_steps": 60000, "n_steps": 64, "batch": 128, "epochs": 5, "lr_ft": 1e-4, "lr_scratch": 3e-4,
       "ent": 0.01, "cql_steps": 50000, "bc_steps": 20000, "iql_steps": 50000, "distill_steps": 8000,
       "lagr_lam": 4.0, "lagr_lam_db": 0.34, "mpc_steps": 20000, "pid_target_over": 0.05, "pid": (2.0, 0.2, 0.0),
       "lr_dqn": 1e-4, "mpc_margins": (0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0),
       "res_p0": 0.7,
       "ft_steps": 40000, "gate_steps": 40000, "cut_weight": 4.0, "mb_steps": 1000000}
QUICK = {"mb_steps": 1792, "ft_steps": 896, "gate_steps": 896, "mpc_steps": 300, "ppo_steps": 1792, "cql_steps": 500, "bc_steps": 300, "iql_steps": 500, "distill_steps": 200}
EVAL_SPLITS = ("val", "test")


def run_name(a):
    parts = [a.method, f"k{a.k}" if a.method != "anyk" else f"kmax{a.kmax}", a.mode]
    if a.drop:
        parts.append("no-" + "-".join(sorted(a.drop.split(","))))
    if a.prior:
        parts.append("prior")
    if a.extra:
        parts.append(a.extra)
    if a.method == "gate":
        parts.append(f"lam{a.gate_lam:g}")
    if a.shape:
        parts.append(f"shape{a.shape:g}")
    if getattr(a, "lam", None) is not None:
        parts.append(f"lam{a.lam:g}")
    if a.gae_lambda != 0.95:
        parts.append(f"gae{a.gae_lambda:g}")
    if getattr(a, "ppo_steps", 0):
        parts.append(f"st{a.ppo_steps // 1000}k")
    if getattr(a, "arch", "mlp") != "mlp" or getattr(a, "train_ks", ""):
        parts.append({"mlp": "mlp", "set_mm": "mm", "set_attn": "attn"}[a.arch] + ("-kall" if a.train_ks else ""))
    if getattr(a, "train_levels", ""):
        parts.append("lv" + "-".join(a.train_levels.split(",")))
    if C.RES and len(C.ACTIONS) != 7:    # residual range from RC_RES_RANGE (P2 next-exp R2); -3..+3 = unchanged
        parts.append(f"r{max(C.ACTIONS)}")
    if C.RES and getattr(C, "RES_RECAP", ""):          # P2 Exp 4 R3 (11-14); names of earlier runs unchanged
        parts.append(f"cap{C.RES_RECAP}")
    if getattr(a, "res_mean", ""):
        parts.append(f"mean{a.res_mean}")
    if getattr(a, "init_bc", ""):
        parts.append("bcinit")
    if getattr(a, "warmup", 0):
        parts.append(f"wu{a.warmup // 1000}k")
    if a.tag:
        parts.append(a.tag)
    parts.append(f"s{a.seed}")
    return "_".join(parts)


def cli(ap):
    ap.add_argument("--method", default="cql_ppo")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--kmax", type=int, default=29)
    ap.add_argument("--mode", default="fixed")
    ap.add_argument("--drop", default="")
    ap.add_argument("--prior", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--shape", type=float, default=0.0,
                    help="potential-based shaping on predicted overshoot during PPO training (v1-data, P2); 0 = off")
    ap.add_argument("--gae-lambda", type=float, default=0.95,
                    help="PPO GAE lambda (v1-data, P2); 0.95 = the original setting, run name unchanged")
    ap.add_argument("--train-family", default="", help="restrict training GOPs, e.g. 'cut' for the cut specialist")
    ap.add_argument("--ppo-steps", type=int, default=0,
                    help="override cfg ppo_steps (60000) for the PPO phase, e.g. 180000 (P2 tracker 37: under-training test)")
    ap.add_argument("--arch", default="mlp", choices=("mlp", "set_mm", "set_attn"),
                    help="BC network: mlp (2 x 256, default) or a shared per-frame encoder (rclib/nets.py; tracker 36)")
    ap.add_argument("--train-ks", default="",
                    help="BC only: train ONE net on these k pooled (e.g. 0,2,5,10,29) and evaluate it at each (tracker 36)")
    ap.add_argument("--train-levels", default="",
                    help="restrict TRAINING episodes to these budget levels, e.g. 36,42 (targeted residual, P2 tracker "
                         "35); evaluation still covers every level")
    ap.add_argument("--extra", default="", help="extra observation features: fb | sum (D23)")
    ap.add_argument("--lam", type=float, default=None,
                    help="Lagrangian lam override (dB per 1%% over under dpsnr; P2 11-10: 0.17 = the metric's penalty)")
    ap.add_argument("--gate-lam", type=float, default=1.0, help="gate: score points charged for a GOP fully at k")
    ap.add_argument("--eval-modes", default="", help="anyk: comma list of mode:k to evaluate, e.g. fixed:0,scene_ext:29")
    ap.add_argument("--eval-splits", default="val,test",
                    help="splits evaluated after training (P2 next-exp 11-13: 'val' keeps test untouched until the "
                         "final run); run name unchanged")
    ap.add_argument("--save-at", default="",
                    help="online methods: also save the policy at these PPO timesteps (comma list, e.g. 60000) as "
                         "model_<N>.zip and evaluate each on --eval-splits into <run>/eval_ckpt (P2 next-exp Exp 3); "
                         "the final model and <run>/eval are unchanged")
    ap.add_argument("--res-mean", default="", choices=("", "pooled"),
                    help="res arm (P2 Exp 4 R3, 11-14): add the pooled smooth Exp 5a shift for this encoder and k "
                         "(results_v1/next/exp5/shifts_smooth.json) to final4's real QP before rounding, every episode")
    ap.add_argument("--init-bc", default="",
                    help="res arm (Exp 4 R3): load this Exp 5b BC classifier (path; {enc} {k} {seed} filled in) into "
                         "the PPO actor (policy_net + action_net); BC has R2's actor shape")
    ap.add_argument("--warmup", type=int, default=0,
                    help="(Exp 4 R3) the first N PPO timesteps update only the critic (actor frozen); counted in the total")


def k_sampler_anyk(kmax):
    return lambda rng: int(rng.integers(0, kmax + 1))


def main():
    a = runner.args(cli)
    assert (a.method == "res") == C.RES, "method res <-> RC_ARM=res"
    assert not ((a.train_ks or a.arch != "mlp") and a.method != "bc"), "--arch / --train-ks: BC only (tracker 36)"
    cfg = {**CFG, **(QUICK if a.quick else {})}
    if a.ppo_steps:
        cfg["ppo_steps"] = a.ppo_steps
    drop = tuple(x for x in a.drop.split(",") if x)
    name = run_name(a)
    out = os.path.join(C.results_dir("rl" + ("_quick" if a.quick else "")), name)
    os.makedirs(out, exist_ok=True)
    if os.path.exists(os.path.join(out, "eval.pkl")):
        log(f"{name}: done")
        return
    torch.set_num_threads(2)
    infos_st = runner.Stages("infos", a.quick)
    iname = "infos_learn" if C.LFQ_LEARN else "infos"
    infos = {g: offrl.slim(x) for g, x in infos_st.load(iname).items()}
    ipath = P.save_infos_for_workers(infos, os.path.join(infos_st.dir, f"{iname}_slim.pkl"))
    train_ids = [g for g, x in infos.items() if x["gop"]["split"] == "train"]
    if a.train_family == "cut":
        train_ids = [g for g in train_ids if infos[g]["an"]["cut"].sum() > 0]
    k_train = a.kmax if a.method == "anyk" else a.k
    envkw = {"k": k_train, "mode": a.mode, "drop": drop, "prior": a.prior, "extra": a.extra}
    if a.res_mean:
        assert C.RES and a.method == "res" and a.mode == "fixed"
        import json
        sm = json.load(open("/scratch1/aayushso/ee599/results_v1/next/exp5/shifts_smooth.json"))
        envkw["res_mean"] = sm[f"{C.CODEC}|{k_train}|{a.res_mean}"]
        log(f"res_mean ({a.res_mean}): {np.round(envkw['res_mean'], 2).tolist()}")
    rl_dir = os.path.dirname(out)

    def prereq(k, seed):           # a finished k-step CQL->PPO policy (gate sub-policies, fine-tuning, ensemble)
        p = os.path.join(rl_dir, f"cql_ppo_k{k}_fixed_s{seed}", "model.zip")
        assert os.path.exists(p), f"missing prerequisite {p}"
        return p
    if a.method == "gate":
        envkw["gate"] = {"k": a.k, "lam": a.gate_lam, "pol0": {"kind": "sb3", "path": prereq(0, a.seed)},
                         "polk": {"kind": "sb3", "path": prereq(a.k, a.seed)}}
    if a.method in ("lagr_ft", "pid_ft"):
        a.init = prereq(a.k, a.seed)
    if a.method == "mb":            # the per-frame model is k-independent; reuse the one the k=5 MPC run trained
        a.model = os.path.join(rl_dir, f"mpc_k5_fixed_s{a.seed}", "mpc_model.pt")
        assert os.path.exists(a.model), f"missing prerequisite {a.model}"
    if a.method == "mb_ppo":
        a.init = os.path.join(rl_dir, f"mb_k{a.k}_{a.mode}_s{a.seed}", "model.zip")
        assert os.path.exists(a.init), f"missing prerequisite {a.init}"
    t0 = time.time()

    # ---- offline data (search logs of the training GOPs)
    need_data = a.method in ("bc", "cql", "iql", "cql_ppo", "bc_ppo", "lagr", "pid", "anyk", "cql_a2c", "cql_dqn", "mb")
    ds = None
    if need_data:
        srch = runner.Stages("search", a.quick).load("search_train")
        ks_data = [int(x) for x in a.train_ks.split(",")] if a.train_ks else [k_train]
        items = [(infos[g], srch[g], kd, a.mode, drop, a.prior, 7 * a.seed + i, offrl.LOG_CAP, a.extra)
                 for kd in ks_data for i, g in enumerate(train_ids) if g in srch]
        worker = offrl.trajectories_best if (a.method == "bc" and a.train_ks) else offrl.trajectories
        ds = offrl.Dataset(runner.pmap(worker, items, desc="dataset"))
        log(f"dataset: {ds.n} transitions from {len(items)} GOPs ({time.time() - t0:.0f}s)")

    spec = None
    if a.method == "bc":
        net0 = None
        if a.arch != "mlp":
            from rclib import nets
            torch.manual_seed(a.seed)
            net0 = nets.make(a.arch, ds.obs.shape[1], len(C.ACTIONS))
        net = offrl.train_bc(ds, cfg["bc_steps"], seed=a.seed, net=net0)
        spec = _save_torch(net, out)
    elif a.method == "cql":
        net = offrl.train_cql(ds, cfg["cql_steps"], seed=a.seed)
        spec = _save_torch(net, out)
    elif a.method == "iql":
        pi, _ = offrl.train_iql(ds, cfg["iql_steps"], seed=a.seed)
        spec = _save_torch(pi, out)
    elif a.method == "ensemble":         # the three seeds of one CQL->PPO setting, no training
        spec = {"kind": "ensemble", "paths": [prereq(a.k, s) for s in (0, 1, 2)]}
    elif a.method == "mpc":
        from rclib import mpc
        srch = runner.Stages("search", a.quick).load("search_train")
        model, fit = mpc.train_model(infos, {g: srch[g] for g in train_ids if g in srch}, cfg["mpc_steps"], a.seed)
        log(f"MPC model: {fit}")
        p = os.path.join(out, "mpc_model.pt")
        torch.save(model, p)
        spec = {"kind": "mpc", "path": p, "fit": fit}
    else:
        spec = train_online(a, cfg, infos, train_ids, ds, envkw, out)
    log(f"trained {name} in {time.time() - t0:.0f}s")

    # ---- evaluation (val for selection, test for the report)
    res = {}
    splits = tuple(x for x in a.eval_splits.split(",") if x)
    assert set(splits) <= set(EVAL_SPLITS), splits
    eval_ids = {s: [g for g, x in infos.items() if x["gop"]["split"] == s] for s in splits}
    modes = [(a.mode, a.k)]
    sweep = {}
    if a.method == "mpc":       # budget margin chosen on val; the sweep is kept
        for mg in (cfg["mpc_margins"][-2:] if a.quick else cfg["mpc_margins"]):
            rows = P.evaluate({**spec, "margin": mg}, ipath, eval_ids["val"], desc=f"val margin {mg}",
                              **{**envkw, "k_sampler": None})
            sweep[mg] = rows
            log(f"{name} margin {mg} val: {summarize(rows)}")
        spec["margin"] = max(sweep, key=lambda mg: summarize(sweep[mg])["score"])
        log(f"chosen margin {spec['margin']}")
    if a.train_ks:
        modes = [("fixed", int(x)) for x in a.train_ks.split(",")]
    if a.method == "anyk":
        modes = [tuple(m.split(":")) for m in a.eval_modes.split(",") if m] or [("fixed", k) for k in (0, 2, 5, 10, 29)]
        modes = [(m, int(k)) for m, k in modes]
    for m, k in modes:
        for s, ids in eval_ids.items():
            res[(m, k, s)] = P.evaluate(spec, ipath, ids, desc=f"eval {m}:{k} {s}",
                                        **{**envkw, "k": k, "mode": m, "k_sampler": None})
            sm = summarize(res[(m, k, s)])
            log(f"{name} {m}:{k} {s}: score {sm['score']:.2f} saving {sm['saving']:.2f} over {sm['over_pct']:.1f}% "
                f"use {sm['use']:.3f} "
                f"seen {sm['seen']:.1f}")
    runner.Stages("rl", a.quick).save(f"{name}/eval", {"args": vars(a), "cfg": cfg, "spec": spec, "res": res,
                                                       "margin_sweep": sweep, "seconds": time.time() - t0})
    # intermediate checkpoints (--save-at): same evaluation, stored separately so the final eval is unchanged
    ck = {}
    for n_at, path in (spec or {}).get("ckpts", {}).items():
        for m, k in modes:
            for s, ids in eval_ids.items():
                ck[(n_at, m, k, s)] = P.evaluate({**spec, "path": path}, ipath, ids, desc=f"eval ckpt {n_at} {m}:{k} {s}",
                                                 **{**envkw, "k": k, "mode": m, "k_sampler": None})
                sm = summarize(ck[(n_at, m, k, s)])
                log(f"{name} ckpt {n_at} {m}:{k} {s}: score {sm['score']:.3f} over {sm['over_pct']:.1f}% "
                    f"use {sm['use']:.3f}")
    if ck:
        runner.Stages("rl", a.quick).save(f"{name}/eval_ckpt", {"args": vars(a), "res": ck})


def summarize(rows):
    return {"score": float(np.mean([r["score"] for r in rows])), "saving": float(np.mean([r["saving"] for r in rows])),
            "use": float(np.mean([r.get("use", np.nan) for r in rows])),
            "over_pct": 100 * float(np.mean([r["over"] for r in rows])),
            "seen": float(np.mean([r["frames_seen"] for r in rows]))}


def _save_torch(net, out):
    p = os.path.join(out, "policy.pt")
    torch.save(net, p)
    return {"kind": "torch", "path": p}


def load_bc_actor(model, path):
    """Copy an Exp 5b BC classifier (offrl.mlp: Linear-ReLU-Linear-ReLU-Linear) into the SB3 PPO actor: layers 0 / 2 ->
    mlp_extractor.policy_net 0 / 2, layer 4 -> action_net. Deterministic actions then equal BC's argmax exactly."""
    ck = torch.load(path, weights_only=False)
    sd = ck["state_dict"]
    pn, an = model.policy.mlp_extractor.policy_net, model.policy.action_net
    assert pn[0].weight.shape == sd["0.weight"].shape and an.weight.shape == sd["4.weight"].shape, (pn, an)
    with torch.no_grad():
        pn[0].weight.copy_(sd["0.weight"]); pn[0].bias.copy_(sd["0.bias"])      # noqa: E702
        pn[2].weight.copy_(sd["2.weight"]); pn[2].bias.copy_(sd["2.bias"])      # noqa: E702
        an.weight.copy_(sd["4.weight"]); an.bias.copy_(sd["4.bias"])            # noqa: E702
    log(f"actor initialised from BC {path} (best step {ck['meta']['best_step']}, zero input cols {ck['zero_cols']})")


def train_online(a, cfg, infos, train_ids, ds, envkw, out):
    from stable_baselines3 import A2C, DQN, PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import SubprocVecEnv

    reward = "lagrangian" if a.method in ("lagr", "pid", "lagr_ft", "pid_ft", "res") else "relative"
    from rclib import metrics
    lam_cfg = cfg["lagr_lam_db"] if metrics.METRIC == "dpsnr" else cfg["lagr_lam"]   # dB or score points per 1% over
    if a.lam is not None:
        lam_cfg = a.lam
    lam0 = lam_cfg if a.method in ("lagr", "lagr_ft", "res") else 0.0
    ft = a.method in ("lagr_ft", "pid_ft", "mb_ppo")
    cw = cfg["cut_weight"] if a.method in ("lagr_ft", "pid_ft") else 1.0
    k_sampler = k_sampler_anyk(a.kmax) if a.method == "anyk" else None
    train_infos = {g: infos[g] for g in train_ids}

    def mk(i):
        def f():
            if a.method == "mb":
                from rclib import mbenv
                return mbenv.ModelEnv(train_infos, model_path=a.model, seed=1000 * a.seed + i, reward=reward,
                                      lam=lam0, cut_weight=cw, **envkw)
            if a.train_levels:
                lv = tuple(int(x) for x in a.train_levels.split(","))
                assert set(lv) <= set(C.BUDGET_QPS), (lv, C.BUDGET_QPS)
                return E.make_env(train_infos, seed=1000 * a.seed + i, reward=reward, lam=lam0, k_sampler=k_sampler,
                                  cut_weight=cw, shape=a.shape, budgets=lv, **envkw)
            return E.make_env(train_infos, seed=1000 * a.seed + i, reward=reward, lam=lam0, k_sampler=k_sampler,
                              cut_weight=cw, shape=a.shape, **envkw)
        return f

    venv = SubprocVecEnv([mk(i) for i in range(C.N_ENVS)], start_method="forkserver")
    pk = {"net_arch": {"pi": [256, 256], "vf": [256, 256]}, "activation_fn": torch.nn.ReLU}
    common = {"gamma": 1.0, "seed": a.seed, "device": "cpu", "verbose": 0}
    steps = (cfg["ft_steps"] if ft else cfg["gate_steps"] if a.method == "gate" else cfg["mb_steps"] if a.method == "mb"
             else cfg["ppo_steps"])
    if ft:                               # continue a finished policy: under the budget constraint (D23) or on real encodes (D26)
        model = PPO.load(a.init, env=venv, device="cpu", custom_objects={"learning_rate": cfg["lr_ft"]})
        log(f"continuing {a.init}")
    elif a.method == "cql_dqn":          # DQN whose Q-network starts as the offline CQL Q-function (D23)
        model = DQN("MlpPolicy", venv, learning_rate=cfg["lr_dqn"], buffer_size=200000, learning_starts=2000,
                    batch_size=256, train_freq=1, gradient_steps=C.N_ENVS, target_update_interval=2000,
                    exploration_fraction=0.5, exploration_initial_eps=0.1, exploration_final_eps=0.02,
                    policy_kwargs={"net_arch": [256, 256]}, **common)
        q = offrl.train_cql(ds, cfg["cql_steps"], seed=a.seed)
        torch.save(q, os.path.join(out, "teacher.pt"))
        model.q_net.q_net.load_state_dict(q.state_dict())
        model.q_net_target.q_net.load_state_dict(q.state_dict())
        log("Q-network initialised from CQL")
    elif a.method == "dqn":
        # one gradient step per collected transition (train_freq counts vec-env steps of N_ENVS transitions) (D21)
        model = DQN("MlpPolicy", venv, learning_rate=cfg["lr_dqn"], buffer_size=200000, learning_starts=2000,
                    batch_size=256, train_freq=1, gradient_steps=C.N_ENVS, target_update_interval=2000,
                    exploration_fraction=0.5,
                    policy_kwargs={"net_arch": [256, 256]}, **common)
    elif a.method in ("a2c", "cql_a2c"):
        warm = a.method == "cql_a2c"
        model = A2C("MlpPolicy", venv, learning_rate=cfg["lr_ft"] if warm else cfg["lr_scratch"],
                    n_steps=cfg["n_steps"] // 8, ent_coef=cfg["ent"], policy_kwargs=pk, **common)
        if warm:
            teacher = offrl.train_cql(ds, cfg["cql_steps"], seed=a.seed)
            torch.save(teacher, os.path.join(out, "teacher.pt"))
            offrl.distill_into_ppo(model, ds, teacher, temp=0.3, steps=cfg["distill_steps"], seed=a.seed,
                                   value_from_q=True)
            log("actor initialised from offline teacher")
    else:
        scratch = a.method in ("ppo", "gate", "res")
        model = PPO("MlpPolicy", venv, learning_rate=cfg["lr_scratch"] if scratch and a.method != "res" else cfg["lr_ft"],
                    n_steps=cfg["n_steps"], batch_size=cfg["batch"], n_epochs=cfg["epochs"], gae_lambda=a.gae_lambda,
                    ent_coef=cfg["ent"], clip_range=0.2, policy_kwargs=pk, **common)
        if a.method == "res":           # same learning rate as lagr's PPO phase; start near "follow the controller"
            n, i0 = len(C.ACTIONS), C.ACTIONS.index(0)
            with torch.no_grad():
                bias = model.policy.action_net.bias
                bias.zero_()
                bias[i0] = float(np.log(cfg["res_p0"] / (1 - cfg["res_p0"]) * (n - 1)))
            log(f"res: P(offset 0) starts at {cfg['res_p0']}, lr {cfg['lr_ft']}")
            if a.init_bc:
                load_bc_actor(model, a.init_bc.format(enc=C.CODEC, k=a.k, seed=a.seed))
        if not scratch:
            if a.method == "bc_ppo":
                teacher, temp, vq = offrl.train_bc(ds, cfg["bc_steps"], seed=a.seed), 1.0, False
            else:
                teacher, temp, vq = offrl.train_cql(ds, cfg["cql_steps"], seed=a.seed), 0.3, True
            torch.save(teacher, os.path.join(out, "teacher.pt"))
            offrl.distill_into_ppo(model, ds, teacher, temp=temp, steps=cfg["distill_steps"], seed=a.seed,
                                   value_from_q=vq)
            log("actor initialised from offline teacher")

    curve = []
    save_at = sorted(int(x) for x in a.save_at.split(",") if x)
    ckpts = {}

    class Track(BaseCallback):
        def __init__(self):
            super().__init__()
            self.lam, self.integ, self.prev = lam0, 0.0, 0.0
            self.buf = []

        def _on_step(self):
            for n_at in save_at:
                if self.num_timesteps >= n_at and n_at not in ckpts:
                    ckpts[n_at] = os.path.join(out, f"model_{n_at}.zip")
                    self.model.save(ckpts[n_at])
                    log(f"  saved checkpoint at {self.num_timesteps} steps -> {ckpts[n_at]}")
            for inf, d in zip(self.locals["infos"], self.locals["dones"]):
                if d and "score" in inf:
                    self.buf.append(inf)
                    curve.append((self.num_timesteps, inf["score"], inf["over"], inf["saving"], self.lam))
            return True

        def _on_rollout_end(self):
            if a.method in ("pid", "pid_ft") and self.buf:
                kp, ki, kd = cfg["pid"]
                err = float(np.mean([b["over"] for b in self.buf])) - cfg["pid_target_over"]
                self.integ = max(0.0, self.integ + err)
                self.lam = max(0.0, kp * err + ki * self.integ + kd * (err - self.prev))
                self.prev = err
                self.training_env.env_method("set_lambda", self.lam)
            if self.buf and len(curve) % 50 < len(self.buf):
                rec = curve[-200:]
                log(f"  steps {self.num_timesteps}: score {np.mean([c[1] for c in rec]):.2f} "
                    f"over {100 * np.mean([c[2] for c in rec]):.1f}% lam {self.lam:.2f}")
            self.buf = []

    cb = Track()
    if a.warmup:
        actor = list(model.policy.mlp_extractor.policy_net.parameters()) + list(model.policy.action_net.parameters())
        for q in actor:
            q.requires_grad_(False)
        model.learn(total_timesteps=a.warmup, callback=cb)
        for q in actor:
            q.requires_grad_(True)
        log(f"warm-up: first {a.warmup} timesteps critic only; actor unfrozen")
        model.learn(total_timesteps=steps - a.warmup, callback=cb, reset_num_timesteps=False)
    else:
        model.learn(total_timesteps=steps, callback=cb)
    venv.close()
    p = os.path.join(out, "model.zip")
    model.save(p)
    np.save(os.path.join(out, "train_curve.npy"), np.array(curve, float))
    out_spec = {"kind": "sb3", "path": p,
                "algo": {"dqn": "dqn", "cql_dqn": "dqn", "a2c": "a2c", "cql_a2c": "a2c"}.get(a.method, "ppo")}
    if ckpts:
        out_spec["ckpts"] = dict(ckpts)
    return out_spec


if __name__ == "__main__":
    main()
