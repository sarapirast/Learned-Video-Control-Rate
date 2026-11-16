"""D36: meta-RL for stream-level rate control. Same decision, budgets, outcomes and score as D34 (rclib/streamenv.py);
what changes is what the policy can know and remember:

* Stream length is randomised in training (n uniform in N_RANGE) and observed (GOPs left, log2 n). v1 training clips
  have at most 10 GOPs, so 'clip' streams longer than a clip are playlists: consecutive GOPs of one clip, then the
  start of another random training clip, and so on (a channel / playlist). 'mixed' streams are unchanged (each GOP
  from a different clip). D34 trained at n = 8 only and saw the position as i / n.
* fb=True adds quality feedback, which D34 never observed: the last GOP's PSNR relative to the stream's pooled PSNR so
  far, the pooled PSNR so far, spend lead (spent / B - i / n), and the last GOP's bits relative to its equal share.
* A recurrent policy (sb3-contrib RecurrentPPO, LSTM) can keep its own history of (QP, bits, PSNR) and infer the
  content's rate-quality behaviour online (experiments/stream_meta.py); a feedforward policy only sees the current obs.

The extra features are appended after the D34 observation, so D34 indices keep their meaning.
"""
import numpy as np
from gymnasium import spaces

from . import clipenv as CE, streamenv as SE

N_RANGE = (4, 24)
N_EXTRA = 6
OBS_DIM = CE.OBS_DIM + N_EXTRA


class MetaStreamEnv(SE.StreamEnv):
    def __init__(self, infos, ids, look=0, seed=0, c0=None, n=SE.N_GOP, lam=0.0, fb=True, nrange=N_RANGE):
        super().__init__(infos, ids, look=look, seed=seed, c0=c0, n=n, lam=lam)
        self.fb, self.nrange, self.n_fixed = fb, nrange, n
        self.observation_space = spaces.Box(-10, 10, (OBS_DIM,), np.float32)
        self.names = sorted(self.clips)

    def _playlist(self, n):
        c = self.names[self.rng.integers(len(self.names))]
        lst = self.clips[c]
        out = list(lst[self.rng.integers(len(lst)):])
        while len(out) < n:
            out += self.clips[self.names[self.rng.integers(len(self.names))]]
        return tuple(out[:n])

    def reset(self, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        if self.forced:
            self.n = len(self.forced[0])
            return super().reset(options=options)
        n = int(self.rng.integers(self.nrange[0], self.nrange[1] + 1)) if self.nrange else self.n_fixed
        self.n = n
        if self.rng.random() < 0.5:
            stream = self._playlist(n)
        else:
            cs = self.rng.choice(len(self.names), n, replace=False)
            stream = tuple(self.clips[self.names[j]][self.rng.integers(len(self.clips[self.names[j]]))] for j in cs)
        q0 = int(self.rng.integers(SE.TRAIN_Q0[0], SE.TRAIN_Q0[1] + 1))
        s = float(self.rng.uniform(*SE.TRAIN_S))
        # same state as ClipEnv.reset; budget from clip means, as D34 training (q0 and s never observed)
        self.stream, self.q0, self.s = stream, q0, s
        self.tabs = [self.tables[g] for g in stream]
        self.B = s * sum(self.cm[self.infos[g]["gop"]["clip"]][q0] for g in stream)
        self.i, self.spent, self.qps, self.bits, self.psnrs, self.logr, self.acts = 0, 0.0, [], [], [], [], []
        return self._obs(), {}

    def _obs(self):
        base = super()._obs()
        e = np.zeros(N_EXTRA, np.float32)
        i, n = self.i, self.n
        e[0] = (n - i) / 16
        e[1] = np.log2(n) / 5
        if self.fb and self.psnrs:
            pp = float(CE.pooled(self.psnrs))
            e[2] = (self.psnrs[-1] - pp) / 3
            e[3] = (pp - 38) / 8
            e[4] = 5 * (self.spent / self.B - i / n)
            e[5] = np.log2(self.bits[-1] / (self.B / n))
        return np.clip(np.concatenate([base, e]), -10, 10)

    def step(self, a, q=None):
        o, r, done, trunc, info = super().step(a, q=q)
        if done:
            o = np.zeros(OBS_DIM, np.float32)
        return o, r, done, trunc, info
