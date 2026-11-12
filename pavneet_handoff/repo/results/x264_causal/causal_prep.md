# Causal setting checks (x264, budgets (26, 30, 34, 38, 42))

Rate model (train): {'w0': [-1.1926069440567428, -0.0972533898296801, -0.09872645345053213, -0.053679160617544006, 0.28690803730116166], 'w1': [-0.25439042653811783, -0.02114816730424706, -0.0046835433945634775, 0.00696376780707211, 0.05507596296203527], 'n_fit': 5980, 'resid_log2_std': 0.3410944307588453, 'resid_log2_iqr': 0.4038614878258009}

- train: GOP model base QP - b at s = 1: mean +0.42, |error| <= 1 for 37%, <= 2 for 67%, range -7.8..+11.1
- test: GOP model base QP - b at s = 1: mean +0.32, |error| <= 1 for 36%, <= 2 for 66%, range -8.0..+12.2
- causal flags with all frames visible equal the stored flags on 479/479 test GOPs
- at k = 0, frame t's stored flags differ from what the detector knows at t on 346/14370 test frames (2.4%)
- k=0: logged plans that stay inside -3..3 on the causal base QP: 4400/9600 (46%, 40 train GOPs)
- k=5: logged plans that stay inside -3..3 on the causal base QP: 4400/9600 (46%, 40 train GOPs)
