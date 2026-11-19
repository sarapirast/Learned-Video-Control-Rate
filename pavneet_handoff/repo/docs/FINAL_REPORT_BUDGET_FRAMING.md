# Final report: what each setting is allowed to know about the budget (D46)

Draft text for the Methods section, plus the caveats list.

## Methods: budget and information available at decision time

The budget tells a controller something about the content, so we fix, per setting, what a real encoder would know.

- **On-demand, per GOP and per stream (Sections X, Y).** The budget at level q0 is the clip's average
  constant-QP bits per GOP at q0, times the number of GOPs (times s in {0.85, 1, 1.18} for streams, never observed).
  This is the information a two-pass encoder has after its first pass: the clip's average cost at a target quality.
  No GOP's budget comes from its own encode, the controller sees only frame 0 and the visible frames, and q0 and s are
  never inputs.
- **Live stream (Section Z).** There is no first pass, so the clip's cost cannot be known. The budget and the mean
  channel rate come from a fixed bitrate ladder: at level q0, the median over training GOPs of constant-QP bits per
  GOP, the same for every stream. The budget then says nothing about the stream's content. An earlier version used
  the clip-level budget here too; that leaks the stream's cost through the mean channel rate, and its results are
  reported only as a comparison (Table Z-old).
- **Milestone setting (original dataset).** The budget was the GOP's own constant-QP bits and the base QP the one that
  met it, so the controller was told the GOP's cost. Those results are superseded and shown only for history.

## Caveats to list

- Live-stream test split read several times across D39-D45; the per-GOP v1 result read test once (pre-registered).
- Elephants Dream and Tears of Steel are v1 test clips and were used for tuning in P4.
- final4's test rows and the stream results existed before P2's test pass.
- R3 tested at k = 5 only; x264 ABR margin and live-stream vbv2 alpha / MPC H, gamma at grid edges (natural bounds).
- PSNR cap (100 dB per plane) applied in P2's numbers; live-stream curves not recomputed (3 GOPs affected, <= 0.01 dB).
- Live-stream score includes a stall penalty; its dB are not comparable with the per-GOP section.
- 320x180, 30-frame GOPs, one encoder setting per codec.
