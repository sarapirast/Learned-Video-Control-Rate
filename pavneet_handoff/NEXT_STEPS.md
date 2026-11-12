# Open items and next steps (as of 2026-11-12)

## Pending, waiting on the user

- **Message to Aayush (not yet sent; the user sends it, not Claude).** Points it covers: which parallel task Pavneet
  picked (stream-level allocation; his START_HERE note asks to be told first), the D34/D35 results (lead with RL vs
  the encoders' rate control, then the tuned-rule result stated plainly, including H6 failing on x265), a request for
  permission to use his `final3` code for direction A below, and whether anyone else is working on stream
  allocation. His note also asks for review notes in a file in Pavneet's own folder.
- **Git:** nothing committed since 20c3862 (all of D31–D35, reports, docs are uncommitted). Commit/push only with
  explicit approval.
- **Cleanup awaiting confirmation:** delete `/scratch1/pbanga/rcwork_wide_test` (old test dir);
  `/scratch1/pbanga/rcwork_v1/old_stream_debug` holds the superseded margin-only baselines (keep or delete?).
- **Final report** not yet updated with D34/D35. `repo/docs/RL_BENEFIT_SUMMARY.md` has a ready-to-use summary.
  Respect the reporting rules in README §2.

## Directions for an RL win over the controller (best first)

**A. Hierarchical: RL allocates per-GOP budgets, final3 spends them inside each GOP. (Recommended.)**
final3 must be given a per-GOP budget; in a real stream something has to choose it. Compare final3 + RL budgets vs
final3 + equal split vs final3 + tuned rule on the same streams. D34 shows RL beats the rule at this choice, so odds
are good, and it is cheap (curve/per-frame lookups, no new encodes). Claim: "RL + final3 beats final3 alone".
Needs: Aayush's final3 code and permission (do not copy from `/scratch1/aayushso` without it). Implementation sketch:
replace `CE.gop_table` lookups in `streamenv.StreamEnv.step` with "run final3 on this GOP with budget b_g" using v1
per-frame rd data; action = budget share for the next GOP (e.g. log-ratio −1..+1 around remaining/expected).

**B. Real-world constraints final3 doesn't model.** VBV buffer with a time-varying channel rate, or a latency limit
(live streaming). final3's "spend the remaining budget" has no notion of buffer underflow; RL can learn the trade-off
from the reward. Most real-world relevant; needs a buffer/channel simulator (medium effort).

**C. Real encodes with reference dependencies.** The only way to beat final3 at its own per-GOP job: RL could learn to
give extra bits to heavily referenced frames, which the simulator rules out. Expensive (encode per step).

**D. Perceptual metric (VMAF).** Constant QP is no longer near-optimal under VMAF; final3 is built for PSNR. Needs
VMAF for all constant-QP encodes (medium effort) and changes the agreed metric.

## Smaller follow-ups that would strengthen D34/D35

- Retune the rule and retrain policies per stream length (N = 16/32) so the L=0 long-stream comparison is fair.
- More fresh films / segments (12 segments from 2 films is thin); e.g. other Blender or Xiph long sources not in v1.
- Report the bitrate-equivalent gain on the fresh set (`tools/stream_analysis.py` logic).
- VMAF on the D35a encodes as a secondary metric.

## Things that are easy to get wrong

- Always run v1/fresh encodes with `RC_V1=1 RC_PRESET=medium` (psy off). Without it, stream encodes are 7–19 % off the
  v1 curves.
- The debug partition was fully drained on 11-11; use an interactive `main` allocation for quick tests.
- BeeGFS writes can stall for minutes (a file showed 0 bytes for ~20 min, then completed); verify before rerunning.
- `stream_rl.py` reads `results_infos/infos_slim.pkl` and `results_stream/` under `RC_WORK`; `stream_fresh.py` reads
  policies from `RC_V1WORK`.
- Keep v1 results out of original-dataset reports and vice versa.
