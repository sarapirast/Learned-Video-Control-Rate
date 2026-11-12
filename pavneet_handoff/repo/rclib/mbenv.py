"""Model-based pre-training env (D26): RateEnv with the encoder replaced by the learned per-frame bits/PSNR model of
rclib/mpc.py (trained on the training search logs). Same observations, actions and terminal reward as RateEnv, so a
policy moves between the two unchanged; steps cost one small MLP call instead of a prefix encode.

The model is used only for differences from the GOP's real STATIC encode (in infos): frame t's bits = real STATIC bits
of frame t x 2^(model log2 bits under the policy's QPs - model log2 bits under STATIC's QPs), mean PSNR = real STATIC
PSNR + (model mean PSNR under the policy - under STATIC). Scoring the model's raw PSNR against the real constant-QP
curve was unusable: a fraction of a dB of model error becomes tens of % of 'saving' after extrapolation.

The model's bit error (~15 %) is not hidden from the policy as a fixed bias: each episode draws a GOP-level bit bias
(log-normal, sd NOISE_GOP) and each frame its own noise (NOISE_FRAME), so the policy is trained to be robust to the
model being wrong rather than to exploit it (the failure of the MPC planner, D20/D24).

Guards (v2, after v1 runs found PSNR deltas the real curve extrapolates to -inf and trained into NaN): the GOP's mean
PSNR change vs STATIC is clipped to +-DPSNR_MAX dB (+-3 QP offsets move real GOPs by well under that), and the score
the reward is built from is clipped to +-SCORE_MAX.
"""
import numpy as np
import torch

from . import config as C, env as E, mpc

DPSNR_MAX, SCORE_MAX = 2.0, 100.0
NOISE_GOP, NOISE_FRAME = 0.10, 0.05     # sd of log2 bit multipliers (the model itself adds ~13 score points MAE, D26)


class ModelEnv(E.RateEnv):
    def __init__(self, infos, model_path=None, **kw):
        super().__init__(infos, **kw)
        torch.set_num_threads(1)
        self.m = torch.load(model_path, weights_only=False)
        self.m.eval()

    def reset(self, seed=None, options=None):
        o = super().reset(seed, options)
        self.bias = self.rng.normal(0, NOISE_GOP)
        self.fp = np.maximum(np.asarray(self.info["fp_bits"], float), 8)
        self.level = C.budget_level(self.b)
        st = self.info["static"][self.b]
        self.st_bits, self.st_psnr = np.maximum(np.asarray(st["bits"], float), 8), float(st["mean_psnr"])
        q_st = self.b + E.STATIC_OFF
        x = mpc.frame_inputs(self.T, q_st, self.level)
        with torch.no_grad():
            out = (self.m(torch.from_numpy(x)) * self.m.sd + self.m.mu).numpy()
        self.m_st_lb, self.m_st_psnr = out[:, 0], out[:, 1]
        self.dpsnr = []
        return o

    def step(self, a):
        a = int(a)
        t = self.t
        q = int(self.b + E.STATIC_OFF[t] + C.ACTIONS[a])
        self.qps.append(q)
        self.acts.append(a)
        x = mpc.frame_inputs(self.T[:t + 1], np.asarray(self.qps, float), self.level)[-1:]
        with torch.no_grad():
            out = (self.m(torch.from_numpy(x)) * self.m.sd + self.m.mu).numpy()[0]
        dlb = out[0] - self.m_st_lb[t] + self.bias + self.rng.normal(0, NOISE_FRAME)
        self.bits.append(int(self.st_bits[t] * 2 ** dlb))
        self.dpsnr.append(float(out[1] - self.m_st_psnr[t]))
        self.psnr.append(self.st_psnr + self.dpsnr[-1])
        self.t += 1
        if t < C.GOP - 1:
            return self._obs(), 0.0, False, False, {}
        r = {"bits": np.array(self.bits), "total_bits": float(sum(self.bits)), "mean_psnr": self.st_psnr + float(np.clip(np.mean(self.dpsnr), -DPSNR_MAX, DPSNR_MAX)),
             "psnr": np.array(self.psnr)}
        res = self.result(r)
        if not (np.isfinite(res["score"]) and abs(res["score"]) <= SCORE_MAX):
            sc = float(np.clip(np.nan_to_num(res["score"], nan=-SCORE_MAX), -SCORE_MAX, SCORE_MAX))
            res["reward"] += (sc - res["score"]) / E.REWARD_SCALE if np.isfinite(res["score"]) else 0.0
            if not np.isfinite(res["reward"]):
                res["reward"] = (sc - res["static_score"]) / E.REWARD_SCALE
            res["score"] = sc
        return np.zeros(self.dim, np.float32), res["reward"], True, False, res
