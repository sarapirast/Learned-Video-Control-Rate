"""Per-frame complexity features for the RL env: PLACEHOLDER.

P2's feature file is meant to replace this. Anything that provides
``compute_features`` with the same signature and return value can be dropped
in (see ``RateControlEnv(features_fn=...)``).

Placeholder definition, per frame i (luma only):
  temporal_i = mean |Y_i - Y_{i-1}|        (0 when there is no previous frame)
  spatial_i  = std(Y_i)
  complexity_i = 0.5 * min(temporal_i / 32, 1) + 0.5 * min(spatial_i / 64, 1)   in [0, 1]
  cut_i = temporal_i > CUT_THRESHOLD       (crude scene-cut flag)
"""
from __future__ import annotations

import numpy as np

CUT_THRESHOLD = 30.0   # mean abs luma difference (0..255) that counts as a cut


def compute_features(luma: np.ndarray, prev_luma: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """
    luma:      uint8 array [N, H, W], the frames of one GOP in display order.
    prev_luma: uint8 array [H, W], the frame before luma[0] in the clip, or None.

    Returns {"complexity": float32[N] in [0, 1], "cut": bool[N]}.
    cut[i] means frame i starts a new scene relative to frame i-1.
    """
    y = luma.astype(np.float32)
    n = y.shape[0]
    temporal = np.zeros(n, dtype=np.float32)
    if n > 1:
        temporal[1:] = np.abs(y[1:] - y[:-1]).mean(axis=(1, 2))
    if prev_luma is not None:
        temporal[0] = np.abs(y[0] - prev_luma.astype(np.float32)).mean()
    spatial = y.reshape(n, -1).std(axis=1)

    complexity = 0.5 * np.minimum(temporal / 32.0, 1.0) + 0.5 * np.minimum(spatial / 64.0, 1.0)
    cut = temporal > CUT_THRESHOLD
    if prev_luma is None:
        cut[0] = False
    return {"complexity": complexity.astype(np.float32), "cut": cut}
