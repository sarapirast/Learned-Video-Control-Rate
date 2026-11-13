# P4: Per-length retuning of the stream rule (leave-one-film-out)

**Owner:** Sara Pirasteh · **Branch:** `sara-p4`

## Question
Pavneet's D35 fresh-film results show RL beating the remaining-budget rule by more on 16/32-GOP
streams than on 8-GOP ones. But the rule was tuned only on 8-GOP v1 streams. Is the long-stream
gain real, or is the rule just mistuned at longer lengths?

## Method
- Streams of N = 16 or 32 consecutive GOPs from the Elephants Dream (ED) and Tears of Steel (ToS)
  segments in `pavneet_handoff/artifacts/<codec>/fresh` (6 segments per film).
- **Leave-one-film-out:** grid-search the rule on one film, evaluate on the other, then swap.
  The test film is never used for tuning.
- Grid: margin {0.98, 1.00, 1.02} × QP per doubling {4.5–8.0} × prior weight {0.1–200}
  (231 settings). Widened three times until the optimum was interior or the score was flat at the
  edge (neighbouring settings within 0.011 dB).
- Policies (PPO, BC→PPO; L = 0 and 2; 3 seeds averaged) are Pavneet's D34 models, unchanged.
- 95 % cluster bootstrap over film segments (`stream_rl.cboot`).

## Results: policy vs the retuned rule (dB, test film)

| | ahead | CI excludes 0 | N=32, L=2, ToS |
|---|---|---|---|
| PPO, x264 | 8/8 | 6/8 | +0.122 |
| PPO, x265 | 8/8 | 8/8 | +0.102 |
| BC→PPO, x264 | 7/8 | 2/8 | −0.045 |
| BC→PPO, x265 | 7/8 | 3/8 | −0.132 |

Full per-case output: `lofo_x264.txt`, `lofo_x265.txt`.

## Findings
1. **Plain PPO's long-stream gain is real.** It beats the retuned rule in 16/16 cases
   (+0.07 to +0.39 dB; 14/16 CIs exclude 0).
2. **Part of the reported gain came from the 8-GOP tuning.** On ToS at 32 GOPs, retuning cut PPO's
   lead by up to half (x265 L=0: +0.40 → +0.20 dB).
3. **The pre-registered BC→PPO mostly does not hold up** (5/16 significant), and it falls behind
   the rule in the same case on both codecs (32 GOPs, L=2, ToS). Hypothesis, not tested: the BC
   start anchors the policy to 8-GOP hindsight plans.
4. The rule's prior weight is not identifiable from 3 segments: the optimum is ≤ 0.5 when tuned on
   ED and ≥ 24 on ToS. Retuning improved the rule on the held-out film in only 10 of 16 cases.

## Caveats
- Only 2 films, 6 segments each, so the CIs are wide.
- `ed_s*` / `tos_s*` clips are in v1's **test** split, so these films are not "unseen" in the
  sense of being outside v1. The segments here are longer, and no policy was trained or tuned on
  them.

## How to run
From `p4/` (PowerShell):
    $env:RC_V1="1"; $env:RC_CODEC="x264"
    $env:RC_WORK="<repo>\pavneet_handoff\artifacts\x264\fresh"
    $env:RC_V1WORK="<repo>\pavneet_handoff\artifacts\x264\v1"
    python -u stream_rule_lofo.py | Tee-Object lofo_x264.txt
Takes about 5 min per codec on a laptop, no cluster needed.