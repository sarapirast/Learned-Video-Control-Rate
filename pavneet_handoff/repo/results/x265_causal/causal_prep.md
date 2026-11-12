# Causal setting checks (x265, budgets (26, 30, 34, 38, 42))

Rate model (train): {'w0': [-0.552375467587711, -0.06055520726362326, -0.043239390462174294, -0.10377480290046219, 0.0259925056679651], 'w1': [-0.27343558534617557, -0.02192276398166524, -0.0066121061648919816, 0.013642274826053088, 0.042683599768561356], 'n_fit': 5980, 'resid_log2_std': 0.27178292596308473, 'resid_log2_iqr': 0.3029633283174933}

- train: GOP model base QP - b at s = 1: mean +0.28, |error| <= 1 for 49%, <= 2 for 78%, range -18.1..+12.2
- test: GOP model base QP - b at s = 1: mean +0.27, |error| <= 1 for 48%, <= 2 for 75%, range -13.0..+8.9
- causal flags with all frames visible equal the stored flags on 479/479 test GOPs
- at k = 0, frame t's stored flags differ from what the detector knows at t on 346/14370 test frames (2.4%)
- k=0: logged plans that stay inside -3..3 on the causal base QP: 5194/9600 (54%, 40 train GOPs)
- k=5: logged plans that stay inside -3..3 on the causal base QP: 5194/9600 (54%, 40 train GOPs)
