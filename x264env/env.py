"""Gymnasium env: per-frame QP control for one 30-frame GOP under a slice-bit budget.

    env = RateControlEnv(clip="clip.y4m", budget=45000)
    obs, info = env.reset(options={"clip": "clip.y4m", "gop": 0, "budget": 45000,
                                   "k": 5, "base_qp": 31})
    obs, reward, terminated, truncated, info = env.step(action)

reset() takes clip/gop/budget/k/base_qp through ``options`` (gymnasium's
signature); anything not given falls back to the constructor's defaults.

Episode: frames [gop*30, gop*30+30) of the clip. Frame 0 is the IDR. A fresh
encoder is opened every episode, and the GOP's frames are cached in RAM.

Action: Discrete(9) -> dqp = action - 4, in {-4..+4}.
  dqp_mode="prev": qp_t = qp_{t-1} + dqp    (qp_{-1} = base_qp)
  dqp_mode="base": qp_t = base_qp + dqp
  Then clipped to the encoder's honoured range [11, 51].
Reward: PSNR-Y (dB) of the frame just encoded, capped at 100.
Budget: slice bits only (header bits are reported but not counted).
Shield: before encoding frame t, if the budget left is below a conservative
  estimate of what the remaining frames cost even at QP 51, frame t is forced
  to QP 51 and info["shield_fired"] = True.

Observation (float32[16], see OBS_FIELDS), all normalised:
  budget left / budget (clipped to [-1, 1]), frames left / 30,
  last 3 QPs ((qp - 11) / 40), last 3 slice bits (/ budget, clipped to [0, 1]),
  complexity of the last 3 encoded frames,
  lookahead over frames t..t+k-1 (starting with the frame about to be
  encoded, within the GOP): mean and max complexity, frames to next cut / k
  (1 if none), cut present, and a mask flag (0 with all-zero lookahead when k=0).
History slots before the first frame hold qp=base_qp, bits=0, complexity=0.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Callable

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .complexity import compute_features
from .encoder import Encoder, read_y4m

GOP_LEN = 30
QP_MIN, QP_MAX = 11, 51
N_ACTIONS = 9
PSNR_CAP = 100.0

# Conservative slice-bit cost of one frame at QP 51, measured as the maximum on
# the 320x180 testsrc clip (IDR: 6464, P: 456..800), rounded up. Re-measure on
# real clips and pass shield_bits_i / shield_bits_p to the constructor.
SHIELD_BITS_I = 6500
SHIELD_BITS_P = 800

OBS_FIELDS = (
    "budget_left_frac", "frames_left_frac",
    "qp_tm1", "qp_tm2", "qp_tm3",
    "bits_tm1", "bits_tm2", "bits_tm3",
    "cplx_tm1", "cplx_tm2", "cplx_tm3",
    "la_mean_cplx", "la_max_cplx", "la_frames_to_cut", "la_cut_present", "la_mask",
)


def _qp_norm(qp: int) -> float:
    return (qp - QP_MIN) / (QP_MAX - QP_MIN)


class RateControlEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, clip: str | None = None, gop: int = 0, budget: int = 45000,
                 k: int = 5, base_qp: int = 31, dqp_mode: str = "prev",
                 shield: bool = True, shield_bits_i: int = SHIELD_BITS_I,
                 shield_bits_p: int = SHIELD_BITS_P,
                 features_fn: Callable[..., dict[str, np.ndarray]] = compute_features):
        if dqp_mode not in ("prev", "base"):
            raise ValueError('dqp_mode must be "prev" or "base"')
        self.defaults = dict(clip=clip, gop=gop, budget=budget, k=k, base_qp=base_qp)
        self.dqp_mode = dqp_mode
        self.shield = shield
        self.shield_bits_i, self.shield_bits_p = shield_bits_i, shield_bits_p
        self.features_fn = features_fn

        self.action_space = spaces.Discrete(N_ACTIONS)
        low = np.zeros(len(OBS_FIELDS), dtype=np.float32)
        low[0] = -1.0
        self.observation_space = spaces.Box(low, np.ones(len(OBS_FIELDS), dtype=np.float32),
                                            dtype=np.float32)
        self._cache_key = None
        self._enc: Encoder | None = None

    # ----- data -----------------------------------------------------------
    def _load_gop(self, clip: str, gop: int) -> None:
        key = (str(Path(clip).resolve()), gop)
        if key == self._cache_key:
            return
        w, h, fn, fd, frames = read_y4m(clip)
        first = gop * GOP_LEN
        prev, gop_frames = None, []
        for i, f in enumerate(frames):
            if i == first - 1:
                prev = f
            elif first <= i < first + GOP_LEN:
                gop_frames.append(f)
            elif i >= first + GOP_LEN:
                break
        if len(gop_frames) < GOP_LEN:
            raise ValueError(f"{clip}: GOP {gop} needs frames {first}..{first + GOP_LEN - 1}, "
                             f"only {len(gop_frames)} available")
        ys = w * h
        luma = np.stack([np.frombuffer(f, np.uint8, ys).reshape(h, w) for f in gop_frames])
        prev_luma = None if prev is None else np.frombuffer(prev, np.uint8, ys).reshape(h, w)
        feats = self.features_fn(luma, prev_luma)
        self._w, self._h, self._fps = w, h, (fn, fd)
        self._frames = gop_frames            # raw I420 bytes, cached in RAM
        self._luma = luma
        self._cplx = np.asarray(feats["complexity"], dtype=np.float32)
        self._cut = np.asarray(feats["cut"], dtype=bool)
        self._cache_key = key

    # ----- gym API ----------------------------------------------------------
    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        cfg = {**self.defaults, **(options or {})}
        if cfg["clip"] is None:
            raise ValueError("no clip: pass options={'clip': ...} or RateControlEnv(clip=...)")
        if cfg["budget"] <= 0 or cfg["k"] < 0:
            raise ValueError("budget must be > 0 and k >= 0")
        if not QP_MIN <= cfg["base_qp"] <= QP_MAX:
            raise ValueError(f"base_qp must be in [{QP_MIN}, {QP_MAX}]")
        self._load_gop(cfg["clip"], int(cfg["gop"]))

        self.budget, self.k, self.base_qp = int(cfg["budget"]), int(cfg["k"]), int(cfg["base_qp"])
        self.close()
        self._enc = Encoder(self._w, self._h, *self._fps)
        if self._enc.qp_range != (QP_MIN, QP_MAX):
            raise RuntimeError(f"encoder QP range {self._enc.qp_range} != ({QP_MIN}, {QP_MAX})")

        self.t = 0
        self.slice_bits_used = 0
        self.prev_qp = self.base_qp
        self._hist_qp = deque([self.base_qp] * 3, maxlen=3)   # most recent first
        self._hist_bits = deque([0] * 3, maxlen=3)
        self._hist_cplx = deque([0.0] * 3, maxlen=3)
        return self._obs(), {"clip": cfg["clip"], "gop": int(cfg["gop"]), "budget": self.budget,
                             "k": self.k, "base_qp": self.base_qp, "dqp_mode": self.dqp_mode}

    def step(self, action):
        if self._enc is None or self.t >= GOP_LEN:
            raise RuntimeError("call reset() before step()")
        if not self.action_space.contains(action):
            raise ValueError(f"invalid action {action!r}")
        dqp = int(action) - N_ACTIONS // 2
        ref = self.prev_qp if self.dqp_mode == "prev" else self.base_qp
        qp = int(np.clip(ref + dqp, QP_MIN, QP_MAX))

        shield_fired = False
        if self.shield:
            left = self.budget - self.slice_bits_used
            n_left = GOP_LEN - self.t
            floor_cost = self.shield_bits_p * n_left
            if self.t == 0:
                floor_cost += self.shield_bits_i - self.shield_bits_p
            if left < floor_cost:
                qp, shield_fired = QP_MAX, True

        src = self._frames[self.t]
        out = self._enc.encode(src, qp)
        assert out is not None and out.pts == self.t, "encoder returned a delayed frame"

        ys = self._w * self._h
        ref_y = self._luma[self.t].astype(np.float32)
        rec_y = np.frombuffer(out.recon, np.uint8, ys).reshape(self._h, self._w).astype(np.float32)
        mse = float(np.mean((ref_y - rec_y) ** 2))
        psnr = PSNR_CAP if mse == 0 else min(PSNR_CAP, 10 * np.log10(255.0 ** 2 / mse))

        self.slice_bits_used += out.slice_bits
        self._hist_qp.appendleft(qp)
        self._hist_bits.appendleft(out.slice_bits)
        self._hist_cplx.appendleft(float(self._cplx[self.t]))
        self.prev_qp = qp
        self.t += 1
        terminated = self.t == GOP_LEN

        info = {"bits": out.bits, "slice_bits": out.slice_bits, "header_bits": out.header_bits,
                "mse": mse, "psnr": float(psnr), "qp": qp, "shield_fired": shield_fired,
                "frame_type": out.frame_type, "budget_left": self.budget - self.slice_bits_used}
        if terminated:
            info["total_slice_bits"] = self.slice_bits_used
            info["overshoot"] = (self.slice_bits_used - self.budget) / self.budget
            self.close()
        return self._obs(), float(psnr), terminated, False, info

    def close(self):
        if self._enc is not None:
            self._enc.close()
            self._enc = None

    # ----- observation ------------------------------------------------------
    def _obs(self) -> np.ndarray:
        o = np.zeros(len(OBS_FIELDS), dtype=np.float32)
        o[0] = np.clip((self.budget - self.slice_bits_used) / self.budget, -1.0, 1.0)
        o[1] = (GOP_LEN - self.t) / GOP_LEN
        o[2:5] = [_qp_norm(q) for q in self._hist_qp]
        o[5:8] = np.clip(np.array(self._hist_bits, dtype=np.float32) / self.budget, 0.0, 1.0)
        o[8:11] = list(self._hist_cplx)
        if self.k > 0:
            win = slice(self.t, min(self.t + self.k, GOP_LEN))
            c, cut = self._cplx[win], self._cut[win]
            if c.size:
                o[11], o[12] = float(c.mean()), float(c.max())
                hits = np.flatnonzero(cut)
                o[13] = hits[0] / self.k if hits.size else 1.0
                o[14] = float(hits.size > 0)
            o[15] = 1.0
        return o
