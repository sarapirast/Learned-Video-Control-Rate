# Message to Aayush (draft, Pavneet sends it)

Hi Aayush,

Your START_HERE note asked me to tell you first which task I'm taking, so: I'm working on **stream-level budget allocation**, meaning how a total budget is split across many GOPs. I'm not working on the per-GOP controller. Is anyone else on stream allocation?

**What we found (dataset v1, your dPSNR_B − 0.17 × %over metric, curve lookups, cluster-bootstrap CIs):**
- **RL vs the encoders' own rate control:** on real 240-frame stream encodes, PPO picking per-GOP QPs beats x265 ABR+VBV by +0.44 dB [+0.35, +0.54] and x264 ABR+VBV by +0.17 [+0.09, +0.26]. The encoders lose mostly through overshoot. Non-causal two-pass ties RL on x265 and beats it on x264.
- **RL vs a val-tuned remaining-budget rule:** +0.14 to +0.21 dB on v1 test. On fresh long films (Elephants Dream, Tears of Steel) it is +0.05 to +0.16 dB, growing with stream length. To be plain about it: my pre-registered primary test on fresh 8-GOP streams failed on x265 and passed on x264. The tuned rule itself also beats ABR+VBV on x265.
- **Memory and quality feedback don't help:** a recurrent (LSTM) policy with PSNR feedback did not help (ablations ≈ 0). Training on variable stream lengths did help on long streams.
- **None of this beats final3 inside a GOP.** I'm not claiming that. Your result stands.

**A metric note you may want to know:** our D34–D36 numbers use 6:1:1 YUV PSNR. On v1 the chroma MSE is 0, so U/V PSNR is pinned at 100 dB. Our dB values are therefore about 3/4 of luma dB. They are internally consistent, but not directly comparable to luma numbers. New work uses luma PSNR of the pooled MSE.

**Two requests:**
1. **May I use your final3 as a black box inside my stream experiments?** The idea is RL choosing each GOP's budget and final3 spending it, compared with final3 plus an equal split and final3 plus the tuned rule.
   - I tried our old D31 port of your controller with final3's settings. It scores about −1.6 dB per GOP against your −0.24 at k=2, because it lacks init/a/b and estimates unseen frames differently.
   - So I won't run this on the port. That would be the weak-baseline problem again.
   - If you're OK with it, could you point me to the function or commit to call? I'd only read and import it, and I won't copy or modify anything under /scratch1/aayushso.
2. **Reading your v1 per-frame table:** I'm reading `data/v1/320x180/rd/rd_frames.parquet` (read-only) for luma MSE per frame. Is that OK, and is it the final version?

**Also running now:** a live-channel variant. The channel rate varies, and a sender buffer has a 1-second latency cap, so stalls are penalised. RL acts on top of a VBV-style rule tuned on val. It uses curve lookups only and small jobs on the shared account (2 CPU / 8 GB, at most 6 at a time).

Thanks,
Pavneet
