# Presentation script: 20 minutes, 5 speakers × about 4 minutes

Deck: https://claude.ai/artifact/LeTMK5swRpFufCUMfJpXXf (each slide's speaker notes hold the same text; download as PowerPoint from the deck's Share/Export menu).

| Speaker | Slides | Part | Spoken length |
|---|---|---|---|
| Atharva | 1–5 | Problem, research question, three levels, related work | ~4 min |
| Ahhana | 6–9 | Data, metric, leak-free setup, value of lookahead, scene cuts | ~4 min |
| Aayush | 10–13 | R3 (imitation + residual PPO), test and test2 results, how it wins | ~4 min |
| Sara | 14–17 | Stream level: rules A and B, RL vs each rule, PID-Lagrangian PPO | ~4 min |
| Pavneet | 18–22 | Live channel and leak fix, il_ppo results, limits, synthesis, conclusion | ~4 min |

# Atharva

## Slide 1: How much lookahead does learned video rate control need?

(about 20 seconds on this slide). Good morning everyone. We are Atharva, Ahhana, Aayush, Sara and Pavneet, and our project asks one question: when a video encoder decides how many bits each frame gets, how much does it help to look ahead at future frames, and when does reinforcement learning actually beat a well-tuned hand-designed controller? We will each take about four minutes. I will set up the problem, Ahhana will cover our setup and the value of lookahead, Aayush the per-frame RL result, Sara the stream level, and Pavneet the live-streaming setting and our conclusions.

## Slide 2: Every frame needs a quantization parameter

(about 1 minute). Every video encoder has to choose a quantization parameter, or QP, for every frame. A lower QP spends more bits and gives higher quality. The hard part is that frames are predicted from earlier frames, so bits spent early also improve the frames that follow, and the encoder has to fit the whole segment into a fixed bit budget. Production encoders use a lookahead buffer: a quick first pass over upcoming frames. But lookahead is not free. At 30 frames per second, every frame you look ahead adds 33 milliseconds of delay. How much of it to pay for is usually decided by experience, not measurement.

## Slide 3: ATHARVA · OUR RESEARCH QUESTION

(about 45 seconds). So our research question, fixed in the proposal, is this. Imagine an offline search that sees a whole group of pictures, a GOP, and tries hundreds of real encodes to find the best QP plan. That search is much better than any controller, but it cannot run live. How much of its gain can a single-pass policy recover, and how does that change with k, the number of future frames the policy is allowed to see? We go from k equals zero, strictly causal, up to the whole GOP. Second: where does reinforcement learning actually help, compared with a controller that a human tuned carefully?

## Slide 4: We study rate control at three levels

(about 1 minute). We study the question at three levels, and the rest of the talk follows them. Level one is the proposal’s setting: one GOP of 30 frames with a fixed budget, where the policy picks a QP per frame and we vary the lookahead from zero to 29 frames. Ahhana and Aayush cover this level. Level two zooms out: several GOPs share one budget, which is what on-demand encoding looks like, and the decision is how to split the budget across GOPs. Sara covers that. Level three adds a network: the bits have to leave through a time-varying channel and a sender buffer with a latency cap, so if you send too much, playback stalls. Pavneet covers that. Moving up, the horizon gets longer and the state harder to model, which is where RL helps most.

## Slide 5: What prior work does, and what we add

(about 1 minute 15 seconds). The closest prior work comes from Google’s VP9 encoder. Mao and colleagues learned rate control by imitating the plans of an offline search, and Mandhane and colleagues trained a MuZero agent with self-competition. Both work in a two-pass setting where the whole clip is known. The adaptive-streaming literature gave us the channel and buffer model and the MPC baseline for our live setting. We add three things. First, we control lookahead explicitly and measure what it is worth. Second, we separate what imitation of the search gives from what RL interaction adds on top. Third, we make sure no budget or initial QP leaks future information. With that, I will hand over to Ahhana, who will explain our setup and what lookahead is worth.

# Ahhana

## Slide 6: One dataset, real encoders, one metric

(about 1 minute). Thanks, Atharva. All our results use one dataset: 109 clips from Blender open movies, Xiph, UVG and YouTube user-generated content, cut into 1,042 GOPs of 30 frames. We split by source, so no film or uploader appears in both training and test. We later added a fresh test set of 93 clips, which Aayush will come back to. Everything is encoded with the real x264 and x265 encoders. Our metric is one number in decibels. We take the PSNR the episode reaches and subtract the PSNR that a constant QP would reach at exactly the same budget. Then we subtract 0.17 dB for every percent over budget, so overspending is never free. A score of zero means as good as the best constant QP chosen in hindsight.

## Slide 7: Only what is known at decision time

(about 1 minute). One lesson from our milestone feedback was about leaks. Early on, a GOP’s budget was computed from that GOP’s own encode, which quietly tells the controller how expensive the GOP is, and the starting QP that hits such a budget is an oracle. We removed both. In the on-demand settings, the budget is the clip’s average cost, which is what a two-pass encoder knows after its first pass. In the live setting there is no first pass, so the budget comes from a fixed bitrate ladder fitted on training clips only. The starting QP comes from a causal rate model, plus the previous GOP’s outcome, and scene-cut flags only look at frames the policy can see. And the headline uses one pre-registered test pass, with confidence intervals clustered by source.

## Slide 8: Lookahead pays off early, then stops

(about 1 minute). Here is the first answer to our question. This is our tuned causal controller on the test set, by lookahead, for both encoders. Zero, the dashed line, is the best constant QP in hindsight. Going from no lookahead to two frames is worth about 0.19 dB on x264 and 0.16 on x265. Going from two to five adds only a few hundredths, and beyond five frames there is nothing; the whole GOP is even slightly worse. So two to five frames, that is 67 to 167 milliseconds, buy all of lookahead’s value. The encoders’ own rate control is 1.2 to 1.7 dB below this controller at every k. The offline search is about 0.3 dB above zero, so no single-pass method reaches it, but the controller already captures about three quarters of the search’s gain over the encoder.

## Slide 9: Cut-triggered lookahead saves no delay

(about 1 minute). Our proposal reviewer asked us to look at scene cuts separately, so we did. Around a cut, the offline search changes QP in a characteristic way, and almost half of that change happens before the cut, so it needs lookahead. For the controller, lookahead is worth about twice as much on GOPs with a cut, plus 0.38 dB versus plus 0.18 on stable GOPs. That suggests an obvious idea: use short lookahead normally and request more only around cuts. Even if we knew the class in hindsight, that is slightly worse than fixed k equals five, because stable GOPs also gain from five frames. And once you count the detector, it gets worse: to know whether a cut lies in the next five frames, a causal detector has to read 4.5 frames ahead on average, 6.1 with flash rejection. That is as much delay as just using k equals five. Now Aayush will show where RL beats this controller.

# Aayush

## Slide 10: R3: three parts that only work together

(about 1 minute). Thanks, Ahhana. That controller turned out to be a very hard baseline. Every learner that had to set the QP on its own, behaviour cloning, CQL followed by PPO, Lagrangian PPO, stayed below it, mostly because they spend their capacity repairing the budget. What finally worked, which we call R3, has three parts. First, a strong base: the controller sets the QP, and the policy only adds an offset between minus six and plus six, with a hard cap on bits. Second, an imitation start: we clone the plans of the offline search, which tries about 600 real encodes per GOP. Third, PPO fine-tuning, with overshoot priced exactly as in the metric, 0.17 dB per percent. We also train only the critic for the first 20 thousand steps, so random early advantages do not destroy the cloned actor.

## Slide 11: Neither imitation nor RL alone beats the controller

(about 1 minute). Our proposal reviewer asked a sharp question: does RL interaction add anything beyond simply imitating the search? The answer is yes, but only together with the imitation start. Behaviour cloning alone loses badly at small lookahead, more than half a dB below the controller at k equals zero. That is classic covariate shift: once the cloned policy drifts, it reaches states the search never showed it, and it misses the budget. PPO from the standard initialisation never beats the controller at any lookahead. But PPO started from the cloned actor beats the same PPO from the standard start by about 0.1 dB at every k, and all those differences are significant. So at small k, PPO mostly repairs the drift of a poor imitation start; at large k the start is already good and PPO polishes it.

## Slide 12: R3 beats the controller on two test sets

(about 1 minute). Here is the headline. In one pre-registered pass on the test set, R3 beats the controller by 0.067 dB on x264 and 0.163 dB on x265, both significant. Because all our models were developed on the first dataset, the team then built test2: 93 brand-new YouTube clips, from uploaders not in our data, pre-registered before any score existed, and used only for evaluation. R3 replicates there: plus 0.044 on x264 and plus 0.187 on x265, with every seed positive, and it beats imitation alone by about 0.2 dB. The figure shows test2 by lookahead. The open diamonds are R3 models Ahhana trained at k equals zero and 29 for x264: they beat the controller too, by the most at k equals zero, where the controller is weakest.

## Slide 13: It goes over budget half as often

(about 1 minute). How does R3 win? Mainly by landing the budget better. The controller goes over budget on more than half of the episodes; R3 on only 20 to 25 percent, on both test sets. Under our metric, going over costs two to three times more than going under. So the best strategy is to land slightly under, and that is exactly what PPO learned, about 1.5 percent under on average. It also spends the bits slightly better. We are careful about what we do not claim: the gain on scene-cut GOPs is not significant on x264, and R3 does not use lookahead better than the controller does. It is a better budget keeper with a learned correction on top of a strong rule. Sara will now take us to the stream level.

# Sara

## Slide 14: Splitting one budget across a stream

(about 1 minute). Thanks, Aayush. At the second level we zoom out from frames to GOPs. A stream of eight GOPs shares one budget, as in on-demand encoding. At each step the controller chooses the next GOP’s QP as an offset on a causal model. The baseline is a remaining-budget rule: it spends what is left in proportion to the predicted cost of what is coming, with a safety margin and a prior weight. Our learners are behaviour cloning followed by PPO, and PID-Lagrangian PPO, which targets an over-budget rate directly. We test on two kinds of streams: single-clip streams, where all GOPs come from one video, and mixed streams, where the content changes from GOP to GOP.

## Slide 15: Each rule is good at different streams

(about 1 minute). We found that how you tune this rule matters a lot, so we report two tunings, both on validation. Rule A is tuned on single-clip streams, our pre-registered population. It learns to ignore the prior and trust the stream’s own coded GOPs, and it plans to spend the whole budget. Rule B is tuned on all streams. It blends a prior worth three to six GOPs and keeps a two percent margin. Rule A is a bit better on single-clip streams, because inside one video the first GOPs predict the rest. On mixed streams the same choice misleads it: it overspends on a third of the x264 streams and scores 0.26 to 0.38 dB lower. And if we use a content-blind ladder budget instead of the clip-level one, its single-clip edge mostly disappears, so part of that edge came from the budget fitting the clip.

## Slide 16: RL beats each rule where that rule is weak

(about 1 minute). So how does RL compare? Against rule A on single-clip streams, our pre-registered primary comparison, RL does not win: minus 0.05 on x264 and plus 0.07 on x265, neither significant. We report that as a negative result. But rule A pays for its single-clip tuning on mixed streams, where RL beats it by about 0.6 dB. Against rule B, the rule tuned for all streams, RL is ahead on single-clip streams too, significantly on x265, and by 0.22 to 0.33 dB on mixed streams. The key point is that no single setting of the rule wins on both kinds of stream: one tuning is good inside a clip, the other across content changes. RL learns to handle both, so it beats each rule exactly where that rule is weak.

## Slide 17: PID-Lagrangian PPO sets its own price

(about 1 minute). Operators also care how often a stream goes over budget, so we trained PID-Lagrangian PPO, a constrained RL method where a PID controller adjusts the Lagrange multiplier on the over-budget constraint. It found an overshoot price of 0.36 to 0.48 by itself, close to the 0.34 we had picked by hand. At the same over-budget rate as the rule, it beats rule B by about 0.21 to 0.26 dB on x264 and 0.24 to 0.27 on x265, all significant, and RL’s edge grows as the reliability requirement tightens. Finally, lookahead over two future GOPs is worth about a quarter of a dB in PSNR at this level, for the rule and RL alike, and RL’s edge over the rule is already present without it. Pavneet will now add the network.

# Pavneet

## Slide 18: Bits must also cross a varying network

(about 50 seconds). Thanks, Sara. At the third level, the bits also have to leave through a network. Each one-second GOP drains at a rate that varies over time, from a model or from real LTE traces. The sender buffer holds at most one second of video, and anything above that stalls playback, which costs 0.5 dB per percent of time stalled. Our feedback pointed out a leak here: the channel’s mean rate is tied to the budget, so if the budget comes from the stream’s own clips, the channel tells every controller how expensive the stream is. We replaced it with one fixed bitrate ladder, fitted on training clips and the same for every stream, and reran every live-stream experiment with it.

## Slide 19: Oracle imitation + PPO beats tuned buffer rules

(about 1 minute). Here the picture changes. Our best learner, which we call il_ppo, first imitates a hindsight oracle, a dynamic program that knows the future channel and content, using DAgger, and then fine-tunes with PPO. It beats our best hand-designed buffer rule, vbv2, tuned on a wide grid, in all four settings: by 0.66 and 0.45 dB on the AR(1) channel and 0.34 and 0.25 dB on real LTE traces, all significant. It also stalls less, for example 1.5 percent of the time versus 2.4 on x265. Imitation of the oracle alone fails badly, because the oracle’s choices depend on a future the student cannot see. Rescored with VMAF at 1080p, il_ppo still wins by 1.1 to 2.8 points in every setting.

## Slide 20: What the live result does not show

(about 50 seconds). We also checked the limits. Re-encoding the chosen QPs with the real encoder gives exactly the same scores. The fairest baseline is the encoder’s own whole-stream rate control with a VBV buffer and a target we tuned on validation. Against that, RL does not win: it ties in most settings, and the encoder wins on x264 with the AR(1) channel. The encoder picks a QP per frame, while our policies pick one per GOP, so combining the two is the obvious next step. The hindsight oracle is far ahead, and il_ppo closes only 12 to 34 percent of that gap. And one honest note on VMAF: at the stream level, lookahead helps PSNR but actually lowers the rule’s VMAF.

## Slide 21: Where RL helps, and where a rule is enough

(about 40 seconds). Putting the three levels together, here is where RL helps. It helps as a residual on a strong base, when it starts from imitation so that PPO corrects drift instead of searching from scratch, when the decision has a long horizon and a state that is hard to model by hand, like a buffer, a channel or changing content, and when a reliability target has to be met. A tuned rule is enough when the structure is simple, like a single clip on demand, and learners that must set the QP on their own, or that only imitate a teacher who sees the future, never beat it.

## Slide 22: The answers

(about 30 seconds). So, to answer our question. Inside a GOP, two to five frames of lookahead, 67 to 167 milliseconds, capture all of its value. Imitation plus RL fine-tuning beats a well-tuned controller by 0.04 to 0.19 dB on two independent test sets. And RL’s largest gains come where hand-designed rules have the least structure to exploit: the live channel, where oracle imitation plus PPO beats tuned buffer rules by a quarter to two thirds of a dB with fewer stalls. Thank you, and we are happy to take questions.
