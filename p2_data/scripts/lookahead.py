"""Fixed-size lookahead summary for the policy state (DRAFT; to be agreed with P4).

Reference implementation, so the env (P1), training (P4) and the analysis all compute the summary the
same way. It works on one GOP's per-frame values, oldest first, and is causal: at frame t it uses frames
0..t of the GOP for normalisation and t+1..t+k for the window. The window never crosses the GOP end, because
the budget is per GOP.

    from lookahead import summary
    s = summary(complexity, cut_flags, t, k)   # dict of 6 floats, same size for every k
"""


def summary(complexity, cut_flags, t, k):
    """Lookahead features for frame t of a GOP.

    complexity: per-frame complexity of the GOP (first-pass bits once available; any positive proxy until then)
    cut_flags:  per-frame 0/1 automatic cut-detector flags for the GOP (deployable, NOT the reviewed labels)
    t:          current frame index in the GOP (0-based)
    k:          lookahead length in frames (0 = strictly causal)
    """
    n = len(complexity)
    if not 0 <= t < n or k < 0:
        raise ValueError('need 0 <= t < %d and k >= 0, got t=%d k=%d' % (n, t, k))
    past = complexity[:t + 1]
    norm = sum(past) / len(past) or 1.0                # running mean over frames 0..t (causal)
    win = list(range(t + 1, min(n, t + 1 + k)))        # clipped at the GOP end
    vals = [complexity[i] / norm for i in win]
    cut_pos = [i - t for i in win if cut_flags[i]]
    return {
        'la_len': float(len(win)),                     # frames actually visible (< k near the GOP end)
        'la_mean': sum(vals) / len(vals) if vals else 0.0,
        'la_max': max(vals) if vals else 0.0,
        'la_cut': 1.0 if cut_pos else 0.0,
        'la_frames_to_cut': float(cut_pos[0]) if cut_pos else float(k + 1),
        'frames_to_gop_end': float(n - 1 - t),
    }


if __name__ == '__main__':
    # Tiny self-check: a cut 3 frames ahead is seen with k >= 3 and not with k = 2.
    c = [10, 10, 10, 10, 40, 40, 10]
    f = [0, 0, 0, 0, 1, 0, 0]
    assert summary(c, f, 1, 2)['la_cut'] == 0.0
    s = summary(c, f, 1, 3)
    assert s['la_cut'] == 1.0 and s['la_frames_to_cut'] == 3.0 and s['la_max'] == 4.0, s
    assert summary(c, f, 1, 0) == {'la_len': 0.0, 'la_mean': 0.0, 'la_max': 0.0, 'la_cut': 0.0,
                                   'la_frames_to_cut': 1.0, 'frames_to_gop_end': 5.0}
    assert summary(c, f, 6, 5)['la_len'] == 0.0        # last frame: nothing ahead in the GOP
    print('lookahead self-check ok')
