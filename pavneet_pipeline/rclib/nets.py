"""Policy networks with a shared per-frame encoder over the lookahead window (P2 tracker item 36, 2026-11-11).

The env observation (rclib/env.py) is [16 global | 30 frame slots x 11 features]; slot 0 = the current frame, slot j =
frame t+j, slots beyond the visible window are all zero. The flat MLP (offrl.mlp) gives every (slot, feature) its own
weights. FrameSetNet instead applies ONE small network phi to every visible slot, with the slot's position given as
inputs (relative j/29 and absolute (t+j)/29), pools the visible future slots, and feeds [global, phi(frame t), pooled]
to a small head:
  pool = "mm"   : mean and max over the visible future slots (zeros when k = 0)
  pool = "attn" : one attention read-out over slots 1..29, queried by [global, phi(frame t)], masked to visible slots
Weight sharing means a cut / an expensive frame is recognised the same way at every distance, and the same net can be
trained on all k (k only changes how many slots are visible). Extra observation features (env EXTRA, after the 346
standard ones) are appended to the global part.
"""
import torch
import torch.nn as nn

F_GLOBAL, F_FRAME, SLOTS = 16, 11, 30


class FrameSetNet(nn.Module):
    def __init__(self, obs_dim, n_out, d=32, head=(128, 128), pool="mm"):
        super().__init__()
        assert pool in ("mm", "attn"), pool
        self.pool, self.d = pool, d
        self.n_extra = obs_dim - (F_GLOBAL + F_FRAME * SLOTS)
        assert self.n_extra >= 0, obs_dim
        g = F_GLOBAL + self.n_extra
        self.phi = nn.Sequential(nn.Linear(F_FRAME + 2, d), nn.ReLU(), nn.Linear(d, d), nn.ReLU())
        if pool == "attn":
            self.q = nn.Linear(g + d, d)
            self.k = nn.Linear(d, d)
            self.v = nn.Linear(d, d)
        pooled = 2 * d if pool == "mm" else d
        layers, i = [], g + d + pooled
        for w in head:
            layers += [nn.Linear(i, w), nn.ReLU()]
            i = w
        layers.append(nn.Linear(i, n_out))
        self.head = nn.Sequential(*layers)
        self.register_buffer("rel", torch.arange(SLOTS, dtype=torch.float32) / (SLOTS - 1))

    def forward(self, x):
        n = x.shape[0]
        fr = x[:, F_GLOBAL:F_GLOBAL + F_FRAME * SLOTS].reshape(n, SLOTS, F_FRAME)
        gl = torch.cat([x[:, :F_GLOBAL], x[:, F_GLOBAL + F_FRAME * SLOTS:]], 1)
        vis = fr.abs().sum(-1) > 0                       # invisible slots are all zero (env: visible slots never are)
        vis[:, 0] = True
        rel = self.rel.expand(n, SLOTS)
        absp = gl[:, :1] + rel                           # global[0] = t / 29
        e = self.phi(torch.cat([fr, rel.unsqueeze(-1), absp.unsqueeze(-1)], -1))   # (n, 30, d)
        e = e * vis.unsqueeze(-1)
        e0, ef, vf = e[:, 0], e[:, 1:], vis[:, 1:]
        cnt = vf.sum(1, keepdim=True)
        if self.pool == "mm":
            mean = ef.sum(1) / cnt.clamp(min=1)
            mx = ef.masked_fill(~vf.unsqueeze(-1), -1e9).max(1).values
            mx = torch.where(cnt > 0, mx, torch.zeros_like(mx))
            pooled = torch.cat([mean, mx], 1)
        else:
            q = self.q(torch.cat([gl, e0], 1))                               # (n, d)
            s = (self.k(ef) * q.unsqueeze(1)).sum(-1) / self.d ** 0.5       # (n, 29)
            s = s.masked_fill(~vf, -1e9)
            w = torch.softmax(s, 1) * (cnt > 0)
            pooled = (w.unsqueeze(-1) * self.v(ef)).sum(1)
        return self.head(torch.cat([gl, e0, pooled], 1))


def make(arch, obs_dim, n_out):
    """'mlp' = the pipeline's 2 x 256 MLP (offrl.mlp); 'set_mm' / 'set_attn' = FrameSetNet."""
    if arch == "mlp":
        from . import offrl
        return offrl.mlp(obs_dim, n_out)
    return FrameSetNet(obs_dim, n_out, pool={"set_mm": "mm", "set_attn": "attn"}[arch])
