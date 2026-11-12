"""Build the EE599 milestone report (3 pages + 1 page of references and appendix, Word).
usage: python3 tools/milestone3_docx.py OUT.docx FIG.png
Sources of the numbers: results/{x265,x264}/{breakdown,reanalysis,own_rc_stream}_report.md."""
import sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT, FIG = sys.argv[1], sys.argv[2]
FONT, BODY = "Calibri", 10
INK, ACCENT = RGBColor(0x1F, 0x1F, 0x1F), RGBColor(0x1F, 0x4E, 0x79)

d = Document()
sec = d.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.left_margin = sec.right_margin = Inches(0.7)
sec.top_margin = sec.bottom_margin = Inches(0.6)
st = d.styles["Normal"]
st.font.name, st.font.size, st.font.color.rgb = FONT, Pt(BODY), INK
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(3)
st.paragraph_format.line_spacing = 1.0
for name, size, before in (("Heading 1", 12, 7), ("Heading 2", 10.5, 4)):
    h = d.styles[name]
    h.font.name, h.font.size, h.font.bold, h.font.color.rgb = FONT, Pt(size), True, ACCENT
    rf = h.element.rPr.find(qn("w:rFonts"))
    for a in list(rf.attrib):
        del rf.attrib[a]
    rf.set(qn("w:ascii"), FONT); rf.set(qn("w:hAnsi"), FONT)
    h.paragraph_format.space_before, h.paragraph_format.space_after = Pt(before), Pt(2)
    h.paragraph_format.keep_with_next = True
b = d.styles["List Bullet"]
b.font.name, b.font.size = FONT, Pt(BODY)
b.paragraph_format.space_after = Pt(1.5)


def runs(p, text, size=None):
    for i, t in enumerate(text.split("**")):
        if t:
            r = p.add_run(t); r.bold = i % 2 == 1
            if size:
                r.font.size = Pt(size)
    return p


def para(text):
    p = runs(d.add_paragraph(), text)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def bullet(text):
    return runs(d.add_paragraph(style="List Bullet"), text)


def shade(cell, hex_):
    s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hex_)
    cell._tc.get_or_add_tcPr().append(s)


def caption(text, keep=True):
    p = d.add_paragraph()
    r = p.add_run(text); r.bold = True; r.font.size = Pt(9)
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(3), Pt(1.5)
    p.paragraph_format.keep_with_next = keep


def table(head, rows, widths, cap, bold_rows=(), size=8.5, left_cols=(0,)):
    caption(cap)
    t = d.add_table(rows=1 + len(rows), cols=len(head))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    for i, row in enumerate([head] + rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.width = Inches(widths[j])
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j in left_cols else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(v); r.font.size = Pt(size)
            if i == 0:
                r.bold = True; shade(c, "DCE6F0")
            elif i - 1 in bold_rows:
                r.bold = True; shade(c, "F2F2F2")
    sp = d.add_paragraph(); sp.paragraph_format.space_after = Pt(0)
    sp.paragraph_format.line_spacing = Pt(5)


# ---------------------------------------------------------------- title
for text, size, kw in (("Learned Video Rate Control Under a Bit Budget: How Much Lookahead Does RL Need?", 13.5, {"bold": True}),
                       ("EE599 Milestone Report, November 5, 2026  ·  Aayush Soni, Ahhana Gupta, Atharva Kulkarni, Pavneet Singh Banga, Sara Pirasteh", 9.5, {"italic": True})):
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(0)
    r = p.add_run(text); r.font.size = Pt(size); r.bold = kw.get("bold", False); r.italic = kw.get("italic", False)
    if kw.get("bold"):
        r.font.color.rgb = ACCENT

# ---------------------------------------------------------------- 1
d.add_heading("1. Introduction", level=1)
d.add_heading("1.1 Problem statement", level=2)
para("Every video encoder must decide how many bits each frame receives, so that a segment of video fits a bit budget "
     "while looking as good as possible. It does this by choosing a quantisation parameter (QP) for each frame: a lower "
     "QP spends more bits and gives a sharper frame. Overspending early forces poor quality later, and a frame's cost depends on how well "
     "the frames it references were coded, so a choice made now changes the price of every later frame. Knowing the future would help, but each frame of lookahead adds delay.")
para("We study this as a reinforcement learning (RL) problem on one group of pictures (GOP) at a time. An offline search "
     "that tries hundreds of plans on the whole GOP beats standard rate control, but cannot run in a live encoder. **Our research question is how much of that search's gain a policy can capture in a single encode, and how "
     "this changes with the number of future frames k it may see**, from k = 0 (strictly causal) to the whole GOP. "
     "Following the proposal feedback, our contribution is this controlled trade-off between lookahead and quality "
     "under a fixed budget, not a new learned rate controller.")
d.add_heading("1.2 Related work", level=2)
para("**Classical rate control.** Ramchandran et al. [1] posed bit allocation across dependent frames as an operational "
     "rate-distortion problem, which is the optimisation our hindsight search approximates. Practical encoders use models: "
     "the R-λ model of Li et al. [2] is the basis of the HEVC reference software, x264's macroblock-tree [3] "
     "propagates the importance of each block backwards through a lookahead window, and x265 builds its rate control on "
     "the same kind of pre-analysis [4]. Wei et al. [5] survey the field.")
para("**Learned rate control.** Mao et al. [6] search for good QP sequences per video and train a policy to imitate them; "
     "they find plain imitation is not enough to meet the bit-rate target and add auxiliary losses and inference-time corrections. Mandhane et al. [7] instead apply MuZero with a self-competition reward to handle "
     "the constraint. Both work on whole videos in libvpx (VP9) at very large scale, so we discuss them as "
     "context rather than as comparison points. Closer to our setting, Ho et al. allocate bits per frame within a GOP in x265, "
     "using a dual-critic actor-critic [8] and then action-constrained RL with Frank-Wolfe policy optimisation [9]. "
     "Zhou et al. [10] apply deep RL to QP selection in HEVC. None of this work isolates how the "
     "benefit depends on lookahead length under one fixed budget, which is our focus.")

# ---------------------------------------------------------------- 2
d.add_heading("2. Methodology", level=1)
para("**Formulation.** One episode is one 30-frame GOP (an I frame followed by 29 P frames), coded by a real x265 or x264 "
     "encoder, so every bit count and PSNR value comes from an actual encode. The **state** holds the budget remaining, "
     "recent QPs and bits, and first-pass cost and complexity features of the current frame and the next k frames. The **action** is a QP offset between −3 and +3, applied on top of a base QP and a fixed spend-early "
     "pattern we call STATIC (I frame −6, P frames 1–9 −3, P frames 10–29 +3). The **score** is the percentage of bits "
     "saved at equal PSNR against the encoder's own constant-QP curve, minus 2 points per 1% over budget. A score of 0 "
     "matches constant QP, and we report the share of cases more than 1% over budget alongside it.")
para("**Hindsight search (the reference).** For each GOP and budget, a search tries 300 real encodes with each of 2 seeds "
     "and keeps the best plan. Its score is our ceiling, and its roughly 1.4 million logged encodes train imitation and offline RL.")
para("**Algorithms** (3 seeds each):")
bullet("**Imitation:** behaviour cloning (BC) of the search's best plans.")
bullet("**Offline RL** on the search logs, with no further encoding: CQL [14] (lowers the value of actions absent from the "
       "data) and IQL [15] (learns values from logged actions only).")
bullet("**Online RL from scratch:** PPO [16], A2C [17] and DQN [18], each with 60,000 real encodes.")
bullet("**Offline start with online fine-tuning:** BC→PPO and CQL→PPO, which tests whether extra encoder "
       "interaction improves on imitation. CQL→PPO is the learner we sweep over k.")
bullet("**Budget-constrained RL [11, 12]:** PPO from the offline start, with a fixed overshoot penalty, a Lagrangian multiplier (a "
       "learned penalty weight that rises while the budget is violated), or a PID-controlled multiplier [13] (which also "
       "reacts to the size and trend of the violation, to reduce oscillation).")
bullet("**Model-based control:** a learned model of per-frame bits and PSNR, used for model-predictive control (MPC), which re-plans at every frame.")
para("**Baselines.** We compare against six baselines: constant QP, the STATIC pattern, the encoder's one-pass ABR and two-pass "
     "modes, and hand-written feedback and lookahead rules. Table A1 in the appendix explains each one and why we include it. **Head-to-head with the encoder.** Thirty frames is too short for ABR to settle, so for a fair "
     "comparison we built test streams of 8 GOPs under one bit budget, where every method receives only that budget and no oracle QP. In this setting the learned policy "
     "picks one QP per GOP and sees L further GOPs ahead, while the encoder controls every frame. Both encoders cap their lookahead at 30 frames, so the windows match at L = 0 but not at L = 2.")

# ---------------------------------------------------------------- 3
d.add_heading("3. Results", level=1)
d.add_heading("3.1 Setup", level=2)
para("**Dataset.** Our dataset has 2,061 GOPs at 320×180 from YouTube UGC, open films and Xiph sequences (1,196 train, 386 "
     "validation, 479 test), with some GOPs spliced from two sources to create known scene cuts. "
     "Budgets are the bits constant QP spends on the same GOP at QP 30 and 38, giving 958 test cases per encoder. "
     "All numbers below are on the test split. Intervals are 95% bootstrap intervals "
     "resampled by source clip unless stated otherwise; seeds are averaged first, so they do not include variation between "
     "training seeds, which Fig. 1 shows separately.")
d.add_heading("3.2 Obtained results", level=2)
table(["Method", "x265, k = 0", "x265, k = 5", "x264, k = 0", "x264, k = 5"],
      [["STATIC pattern (no adaptation)", "−13.70 / 50%", "", "−15.95 / 56%", ""],
       ["Feedback rule", "−12.54 / 63%", "", "−15.14 / 85%", ""],
       ["Lookahead rule", "−6.00 / 27%", "−2.51 / 19%", "−5.39 / 25%", "−1.95 / 16%"],
       ["Behaviour cloning", "1.68 / 17%", "3.77 / 9%", "0.21 / 19%", "2.65 / 21%"],
       ["CQL", "−3.42 / 29%", "−1.77 / 26%", "−4.07 / 29%", "−1.23 / 25%"],
       ["IQL", "2.04 / 10%", "−0.63 / 23%", "−2.48 / 25%", "0.35 / 18%"],
       ["PPO from scratch", "0.41 / 10%", "0.32 / 14%", "−0.74 / 15%", "0.15 / 14%"],
       ["A2C from scratch", "0.53 / 3%", "−0.47 / 8%", "1.04 / 1%", "−0.04 / 7%"],
       ["DQN from scratch", "0.27 / 8%", "−1.41 / 11%", "0.53 / 3%", "−0.23 / 6%"],
       ["CQL→PPO", "0.74 / 22%", "3.48 / 15%", "−1.17 / 25%", "0.43 / 24%"],
       ["BC→PPO", "2.80 / 10%", "3.17 / 14%", "2.46 / 8%", "3.60 / 10%"],
       ["Lagrangian PPO", "4.36 / 1%", "4.95 / 2%", "3.90 / 2%", "4.07 / 6%"],
       ["PID-Lagrangian PPO", "4.46 / 4%", "4.48 / 4%", "3.83 / 4%", "4.53 / 6%"],
       ["Hindsight search (ceiling)", "10.53 / 1%", "", "9.95 / 1%", ""]],
      [2.1, 1.15, 1.15, 1.15, 1.15],
      "Table 1. Score / share of cases more than 1% over budget (mean of 3 seeds). Constant QP = 0.",
      bold_rows=(11,), size=8)
para("**Budget-constrained RL is the best single-pass controller (Table 1).** On this budget, which leaks each GOP's cost "
     "(Section 3.3), the Lagrangian learner reaches 39–47% of the search's score while staying within budget on nearly every GOP. It beats imitation at k = 0 by +2.68 [+1.89, +3.44] "
     "on x265 and +3.68 [+2.68, +4.62] on x264, also on natural GOPs alone. The STATIC pattern alone saves 1.6 (x265) and 1.3 (x264) points but overshoots on over half of the cases, "
     "so about a third of the Lagrangian learner's saving comes from the pattern, and RL's main addition is holding the budget.")
d.add_picture(FIG, width=Inches(6.6))
d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
d.paragraphs[-1].paragraph_format.space_after = Pt(0)
d.paragraphs[-1].paragraph_format.keep_with_next = True
caption("Figure 1. Share of the search's score captured against lookahead k. Points: mean of 3 seeds. Bars: range across seeds.", keep=False)
para("**Lookahead buys real compression mainly at scene cuts (Fig. 1).** We measured lookahead across several learners rather "
     "than one: a fine sweep of 14 values for CQL→PPO, and k = 0, 5 and 10 for the others. Lagrangian PPO turned out to be the "
     "best learner, so its full sweep is planned. Single seeds sometimes collapse, so individual points should not be "
     "over-read; beyond k = 1–3 there is no consistent further gain. For CQL→PPO, k = 0 → 5 "
     "gains +2.74 [+1.79, +3.64] on x265. Splitting by GOP type, as the feedback suggested, shows where this comes from. Saving "
     "rises by +3.2 (x265) and +3.8 (x264) on natural cuts, which are only about 30 GOPs, and by +4.8 and +5.7 on splices, with "
     "every seed positive. On stable GOPs it rises by only +0.2 to +0.6, so the score gain there is mostly a smaller overshoot "
     "penalty. Lagrangian PPO's curve looks flat, but that is uninformative: its budget already reveals the GOP's total cost "
     "at k = 0, which is itself future information, so this curve needs a rerun on leak-free budgets.")
table(["CQL→PPO, 958 cases per encoder", "x265 score", "frames seen", "> 1% over", "x264 score", "frames seen", "> 1% over"],
      [["No lookahead (k = 0)", "0.74", "0", "22%", "−1.17", "0", "25%"],
       ["Lookahead only near a cut (up to 5 frames)", "3.32", "0.2", "10%", "1.67", "0.2", "16%"],
       ["Fixed lookahead (k = 5)", "3.48", "4.5", "15%", "0.43", "4.5", "24%"]],
      [2.7, 0.7, 0.6, 0.65, 0.7, 0.6, 0.65],
      "Table 2. Dynamic lookahead. Frames seen = mean future frames visible per decision, excluding the scene detector's own scan.")
para("**Requesting lookahead only near cuts keeps most of the gain (Table 2).** The proposal feedback suggested requesting extra "
     "lookahead only around difficult scenes, so we trained a policy that sees no future frames unless a scene cut is flagged within the next 5. "
     "It sees 0.2 frames per decision on average instead of 4.5, yet beats k = 0 by +2.58 [+1.80, +3.23] on x265 and +2.84 [+1.98, +3.97] "
     "on x264, and +2.39 and +2.21 on natural GOPs alone. On x265 it nearly matches fixed k = 5. On x264 it scores higher than k = 5, but one of its three seeds "
     "falls below k = 0, so we do not read that as a win. The frame count excludes the detector, which must itself scan ahead to raise the flag, "
     "so the real saving in encoding delay is still to be measured.")
table(["Multi-GOP streams, 912 cases per encoder", "x265 score", "saving", "> 1% over", "x264 score", "saving", "> 1% over"],
      [["RL (BC→PPO), L = 0", "1.65", "1.70", "1%", "0.11", "0.47", "2%"],
       ["RL (BC→PPO), L = 2", "3.23", "3.28", "1%", "1.86", "2.06", "1%"],
       ["Encoder: one-pass ABR with cutree/mb-tree", "−21.65", "−0.73", "34%", "−13.42", "−0.61", "45%"],
       ["Encoder: plain two-pass", "−2.30", "−0.38", "30%", "0.57", "1.94", "22%"],
       ["Encoder: two-pass with default AQ", "3.83", "7.03", "45%", "3.18", "4.49", "22%"],
       ["Hindsight per-GOP plan (ceiling)", "12.54", "12.54", "0%", "12.45", "12.46", "0%"]],
      [2.7, 0.7, 0.6, 0.65, 0.7, 0.6, 0.65],
      "Table 3. Head-to-head under one stream budget, with no oracle QP for any method. Best constant QP in hindsight = 0.")
para("**Against the encoder, RL wins on reliability but not yet on compression (Table 3).** RL beats one-pass ABR by +23.3 "
     "points on x265 and +13.5 on x264, although most of this comes from the overshoot penalty: the difference in saving "
     "alone is +2.4 [+1.3, +3.7] and +1.1 (not significant). Against plain two-pass, which sees the whole stream, RL with L = 2 leads by +5.5 on x265 "
     "and +1.3 on x264, where the two tie on saving. The encoder's two-pass with default settings still has the highest score, but it uses adaptive "
     "quantisation (AQ), which our forced-QP encodes switch off, and it exceeds the budget far more often.")
d.add_heading("3.3 Discussion", level=2)
para("**What did not work.** Online RL from scratch stays within about 2 points of constant QP, partly because it gets "
     "60,000 encodes against 1.4 million for the offline methods. Pure offline RL is worse than imitation. MPC "
     "stays below constant QP (−1.78 and −3.58 at k = 0), because its model's bit error of about 15% exceeds the effect of a good allocation. "
     "PPO fine-tuning adds little quality over imitation: CQL→PPO minus BC at k = 5 is −0.28 [−0.94, +0.22] on x265 and "
     "significantly negative on x264 (−2.22), so RL's clearest contribution so far is budget reliability.")
para("**Holes we found in our own setup.** (1) Learners are given the base QP that "
     "exactly meets the budget, which a real encoder does not know. (2) The budget is derived from the GOP's "
     "own cost, so it reveals that cost even at k = 0. (3) Some "
     "scene flags used up to 4 later frames. (4) Our early intervals treated cases as independent, although the test GOPs "
     "come from only 38 clips and 60 splices, and some small effects do not survive clip-level testing. "
     "(5) Two-thirds of the test GOPs with cuts are artificial splices. Budgets that do not reveal a GOP's cost, a causal "
     "base QP and causal scene flags (Section 4) address (1)–(3), and clip-level intervals address (4).")

# ---------------------------------------------------------------- 4
d.add_heading("4. Plan until the final report", level=1)
para("**Remaining work.** The main final results will use budgets that do not reveal a GOP's cost, a causal base QP, causal "
     "scene flags and the team's frozen encoder settings. What remains is:")
bullet("**Rerun the core learners:** BC, CQL→PPO, Lagrangian and PID-Lagrangian PPO on both encoders, including a "
       "full Lagrangian lookahead sweep with more seeds, reported as share of search gain and split by stable and natural-cut GOPs.")
bullet("**Test RL against a learning-free online controller** on identical budgets, to see whether learning adds anything beyond "
       "feedback control, and test dense reward shaping for the budget [19].")
bullet("**Complete the proposal:** VMAF as a second quality metric, the CRF baseline, and RecurrentPPO.")
bullet("**Close the gap to the encoder:** run Lagrangian PPO on the streams, and study why default two-pass leads on saving, including encodes with AQ enabled.")
para("**Further analyses.** The final report will also cover the causal rerun of "
     "the learners with a hidden budget scale, a wider range of five budgets (QP 26 to 42), imitation combined with closed-loop "
     "feedback as a non-RL test of whether RL is needed, the delay cost of dynamic lookahead, "
     "multi-seed policy ensembles, and how results change with the number of training clips. "
     "All conclusions will carry clip-level intervals and seed ranges.")

# ---------------------------------------------------------------- refs + appendix (page 4)
p = d.add_paragraph(); p.paragraph_format.space_after = Pt(0)
p.add_run().add_break(WD_BREAK.PAGE)
d.add_heading("References", level=1)
REFS = [
    "K. Ramchandran, A. Ortega, M. Vetterli. Bit allocation for dependent quantization with applications to multiresolution and MPEG video coders. IEEE Trans. Image Processing 3(5):533–545, 1994.",
    "B. Li, H. Li, L. Li, J. Zhang. λ domain rate control algorithm for High Efficiency Video Coding. IEEE Trans. Image Processing 23(9):3841–3854, 2014.",
    "J. Garrett-Glaser. A novel macroblock-tree algorithm for high-performance optimization of dependent video coding in H.264/AVC. Unpublished manuscript, x264 project, 2009.",
    "H. Liu. Revisiting pre-analysis information based rate control in x265. arXiv:2109.12294, 2021.",
    "X. Wei, M. Zhou, H. Wang, H. Yang, L. Chen, S. Kwong. Recent advances in rate control: from optimisation to implementation and beyond. arXiv:2205.10815, 2022.",
    "H. Mao, C. Gu, M. Wang, A. Chen, N. Lazic, N. Levine, et al. Neural rate control for video encoding using imitation learning. arXiv:2012.05339, 2020.",
    "A. Mandhane, A. Zhernov, M. Rauh, C. Gu, M. Wang, F. Xue, W. Shang, et al. MuZero with self-competition for rate control in VP9 video compression. arXiv:2202.06626, 2022.",
    "Y.-H. Ho, G.-L. Jin, Y. Liang, W.-H. Peng, X. Li. A dual-critic reinforcement learning framework for frame-level bit allocation in HEVC/H.265. arXiv:2104.01735, 2021.",
    "Y.-H. Ho, Y. Liang, C.-H. Kao, W.-H. Peng. Action-constrained reinforcement learning for frame-level bit allocation in HEVC/H.265 through Frank-Wolfe policy optimization. arXiv:2203.05127, 2022.",
    "M. Zhou, X. Wei, S. Kwong, W. Jia, B. Fang. Rate control method based on deep reinforcement learning for dynamic video sequences in HEVC. IEEE Trans. Multimedia 23:1106–1121, 2021.",
    "J. Achiam, D. Held, A. Tamar, P. Abbeel. Constrained policy optimization. ICML, 2017.",
    "C. Tessler, D. J. Mankowitz, S. Mannor. Reward constrained policy optimization. ICLR, 2019.",
    "A. Stooke, J. Achiam, P. Abbeel. Responsive safety in reinforcement learning by PID Lagrangian methods. ICML, PMLR 119:9133–9143, 2020.",
    "A. Kumar, A. Zhou, G. Tucker, S. Levine. Conservative Q-learning for offline reinforcement learning. NeurIPS, 2020.",
    "I. Kostrikov, A. Nair, S. Levine. Offline reinforcement learning with implicit Q-learning. ICLR, 2022.",
    "J. Schulman, F. Wolski, P. Dhariwal, A. Radford, O. Klimov. Proximal policy optimization algorithms. arXiv:1707.06347, 2017.",
    "V. Mnih, A. P. Badia, M. Mirza, A. Graves, et al. Asynchronous methods for deep reinforcement learning. ICML, 2016.",
    "V. Mnih, K. Kavukcuoglu, D. Silver, et al. Human-level control through deep reinforcement learning. Nature 518:529–533, 2015.",
    "A. Y. Ng, D. Harada, S. Russell. Policy invariance under reward transformations: theory and application to reward shaping. ICML, 1999.",
]
for i, r in enumerate(REFS, 1):
    p = d.add_paragraph()
    p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Inches(0.28), Inches(-0.28)
    p.paragraph_format.space_after = Pt(1)
    x = p.add_run(f"[{i}]\t{r}"); x.font.size = Pt(8.5)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(0.28))

d.add_heading("Appendix A: Baselines", level=1)
table(["Baseline", "What it means", "Why we include it"],
      [["Constant QP", "The same QP on every frame", "The simplest option; the zero point of the score"],
       ["STATIC pattern", "Fixed QP offsets by frame position, ignoring content", "Tests spending early without looking at the video"],
       ["Encoder one-pass ABR", "Adjusts QP during encoding to reach an average bitrate", "The real-world option for a live encoder"],
       ["Encoder two-pass", "Analyses the whole video first, then encodes to the target", "The real-world option when delay does not matter"],
       ["Hand-written feedback rule", "Raises QP when spending runs ahead of an expected curve (gain tuned on validation, offsets limited to ±3)", "Can a simple rule hold the budget without learning?"],
       ["Hand-written lookahead rule", "Divides the remaining budget over visible frames by first-pass cost", "Can a simple rule use lookahead as well as RL?"]],
      [1.6, 2.9, 2.4], "Table A1. The baselines used in this report.", size=8.5, left_cols=(0, 1, 2))
d.add_heading("Appendix B: Division of work", level=1)
para("The work was shared evenly: each member owned one project stream and a set of algorithms, and all contributed to analysis and writing.")
table(["Member", "Project stream", "Algorithms and experiments"],
      [["Aayush Soni", "Dataset, scene-cut labels, features, leak-free budgets and the causal base-QP estimate",
        "Learning-free online controller, baseline table, budget safety layer, MPC"],
       ["Ahhana Gupta", "Encoder wrapper, Gym environment, frozen encoder settings and forced-QP checks",
        "Online RL from scratch with A2C and DQN, environment validation"],
       ["Atharva Kulkarni", "Hindsight search, wider budget range, evaluation and report integration",
        "Behaviour cloning, CQL and IQL on the search logs"],
       ["Pavneet Singh Banga", "Experiment pipeline on the CARC cluster, encoder head-to-head and clip-level re-analysis",
        "BC→PPO, CQL→PPO, lookahead sweep, causal rerun"],
       ["Sara Pirasteh", "RL training setup, lookahead feature design and budget handling",
        "PPO from scratch, Lagrangian PPO, PID-Lagrangian PPO"]],
      [1.35, 2.75, 2.8], "Table A2. Division of work.", size=8.5, left_cols=(0, 1, 2))

d.save(OUT)
print("wrote", OUT)
