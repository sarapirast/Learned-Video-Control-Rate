"""Build the EE599 project milestone report (3-4 pages, Word). Partial results only; usage: python3 milestone2_docx.py OUT FIG"""
import sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT, FIG = sys.argv[1], sys.argv[2]
FONT = "Calibri"
INK = RGBColor(0x1F, 0x1F, 0x1F)
ACCENT = RGBColor(0x1F, 0x4E, 0x79)

d = Document()
sec = d.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.left_margin = sec.right_margin = Inches(0.9)
sec.top_margin = sec.bottom_margin = Inches(0.8)
st = d.styles["Normal"]
st.font.name, st.font.size, st.font.color.rgb = FONT, Pt(10.5), INK
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(4)
st.paragraph_format.line_spacing = 1.0
for name, size in (("Heading 1", 12.5), ("Heading 2", 11)):
    h = d.styles[name]
    h.font.name, h.font.size, h.font.bold, h.font.color.rgb = FONT, Pt(size), True, ACCENT
    rf = h.element.rPr.find(qn("w:rFonts"))
    for a in list(rf.attrib):
        del rf.attrib[a]
    rf.set(qn("w:ascii"), FONT); rf.set(qn("w:hAnsi"), FONT)
    h.paragraph_format.space_before = Pt(9 if name == "Heading 1" else 5)
    h.paragraph_format.space_after = Pt(3)
    h.paragraph_format.keep_with_next = True
s = d.styles["List Bullet"]
s.font.name, s.font.size = FONT, Pt(10.5)
s.paragraph_format.space_after = Pt(2)


def runs(p, text):
    for i, t in enumerate(text.split("**")):
        if t:
            p.add_run(t).bold = i % 2 == 1
    return p


def para(text):
    return runs(d.add_paragraph(), text)


def bullet(text):
    return runs(d.add_paragraph(style="List Bullet"), text)


def shade(cell, hex_):
    s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hex_)
    cell._tc.get_or_add_tcPr().append(s)


def caption(text):
    p = d.add_paragraph()
    r = p.add_run(text); r.bold = True; r.font.size = Pt(9.5)
    p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True


def table(head, rows, widths, cap, bold_rows=(), size=9.5):
    caption(cap)
    t = d.add_table(rows=1 + len(rows), cols=len(head))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    for i, row in enumerate([head] + rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.width = Inches(widths[j])
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(v); r.font.size = Pt(size)
            if i == 0:
                r.bold = True; shade(c, "DCE6F0")
            elif i - 1 in bold_rows:
                r.bold = True; shade(c, "F2F2F2")
    d.add_paragraph().paragraph_format.space_after = Pt(0)


# ---------------------------------------------------------------- title
for text, size, kw in (("Learned Video Rate Control Under a Bit Budget: How Much Lookahead Does RL Need?", 15, {"bold": True}),
                       ("EE599 Project Milestone Report", 11.5, {}),
                       ("Aayush Soni, Ahhana Gupta, Atharva Kulkarni, Pavneet Singh Banga, Sara Pirasteh  ·  November 4, 2026",
                        10, {"italic": True})):
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(1)
    r = p.add_run(text); r.font.size = Pt(size); r.bold = kw.get("bold", False); r.italic = kw.get("italic", False)
    if kw.get("bold"):
        r.font.color.rgb = ACCENT

# ---------------------------------------------------------------- 1
d.add_heading("1. Problem statement", level=1)
para("A video encoder must decide how many bits each frame gets, so that a group of pictures (GOP) fits a hard bit "
     "budget while looking as good as possible. It does this by choosing a quantiser (QP) per frame: a lower QP spends "
     "more bits for a sharper frame. We treat this as a reinforcement-learning (RL) problem. The **state** is the budget "
     "left, the recent QPs and bits, and the complexity of the current frame and of the next **k** frames (the "
     "lookahead). The **action** is the next frame's QP. The **reward** is picture quality, and the **constraint** is that "
     "the GOP's total bits must not exceed the budget, which is only known once the GOP is coded.")
para("**Research question.** An offline search that sees the whole GOP and tries many plans can beat the encoder's "
     "standard rate control, but it needs hundreds of trial encodes and cannot run inside a live encoder. How much of "
     "that search's gain can a policy capture in a single encode, and how does this change with the number of future "
     "frames it may see (from k = 0, strictly causal, to the full GOP)? Following the proposal feedback, we frame the "
     "contribution as this controlled **lookahead–quality trade-off under a fixed GOP budget**.")

# ---------------------------------------------------------------- 2
d.add_heading("2. Introduction and related work", level=1)
para("Rate control is a sequential decision problem with delayed, constrained feedback: overspending early forces "
     "crushed quality later, and a frame's cost depends on how well its reference frames were coded, so the problem is "
     "neither myopic nor easy to model. Lookahead is the main lever a live encoder has, but every frame of lookahead adds "
     "delay. Knowing what each frame of delay buys is useful to encoder designers.")
para("Two closely related works learn rate control from an offline search. Mao et al. (neural rate control via "
     "imitation learning) train a controller to imitate per-video search plans and report that imitation alone often "
     "misses the bit-rate target, which they fix with auxiliary bit losses, target relabelling and inference-time "
     "feedback. MuZero rate control (Mandhane et al.) plans with a learned model of the encoder and a self-competition "
     "reward. Both use libvpx (VP9), whole videos and BD-rate, so their numbers are not comparable to ours, and we did "
     "not reproduce them. We use them for discussion: our question, how the gain depends on lookahead under a fixed "
     "per-GOP budget, is complementary, and the imitation-versus-RL comparison suggested in the feedback is built into "
     "our study.")

# ---------------------------------------------------------------- 3
d.add_heading("3. What we did", level=1)
d.add_heading("3.1 Setup", level=2)
bullet("**Encoders and episode.** Real x265 4.1 and x264 encodes (fast preset). One episode is a 30-frame GOP (an I frame "
       "and 29 P frames, no B-frames, adaptive quantisation and cutree off so QPs are obeyed exactly). Every reward "
       "comes from a real encode: bits are counted from the bitstream and PSNR from decoding it.")
bullet("**Action.** A per-frame QP offset in −3…+3 around a fixed spend-early pattern (STATIC: I frame −6, P1–9 −3, "
       "P10–29 +3) on a base QP.")
bullet("**Budget and score.** The budget is the bits the encoder's own constant-QP mode spends on the same GOP at QP 30 or "
       "38. The score is the % of bits saved at equal PSNR against the encoder's constant-QP curve, minus 2 points per "
       "1 % over budget. We always report the share of GOPs more than 1 % over budget next to it.")
bullet("**Data.** 2,061 GOPs at 320×180 from YouTube UGC, open films and Xiph test sequences, split by source "
       "(1,196 train / 386 val / 479 test), plus GOPs spliced from two sources to create known scene cuts. A second, "
       "more balanced dataset with human-checked scene labels (v1, 1,042 GOPs) is being prepared.")
bullet("**Ceiling.** A hindsight search per GOP and budget (300 real encodes × 2 seeds). It is the yardstick, and its "
       "logged plans (about 1.4 M encodes) are the training data for imitation and offline RL.")
d.add_heading("3.2 Algorithms", level=2)
bullet("**Imitation:** behaviour cloning (BC) of the search's best plans.")
bullet("**Offline RL** on the search logs: CQL and IQL (discrete, γ = 1).")
bullet("**Online RL from scratch** in the real encoder: PPO, A2C and DQN, 60 k real encodes each.")
bullet("**Offline start + online fine-tuning:** CQL → PPO and BC → PPO (the imitation-then-RL comparison suggested in "
       "the feedback). CQL → PPO is the learner we sweep over the lookahead k = 0…29.")
bullet("**Budget-constrained RL:** a fixed overshoot penalty (the default reward), a Lagrangian (dual-ascent) constraint "
       "and a PID-controlled Lagrangian, all on PPO from the offline start.")
bullet("**Model-based:** a learned per-frame bits/PSNR model with receding-horizon CEM planning (MPC), and PPO "
       "pre-trained inside the learned model before real fine-tuning.")
bullet("**Baselines:** constant QP, the STATIC pattern, the encoders' own ABR / two-pass / ABR+VBV rate control, a causal "
       "feedback rule and a hand-made lookahead rule that allocates the budget by first-pass cost over the visible window.")
para("Everything runs as SLURM job arrays on the CARC cluster (sharded encodes, one job per learner × k × seed, 3 seeds); "
     "all choices are made on the validation split and the numbers below are on the held-out test split.")

# ---------------------------------------------------------------- 4
d.add_heading("4. Preliminary results", level=1)
para("Results so far use the two budgets (QP 30 and 38) and 479 test GOPs × 2 budgets = 958 cases per encoder, seeds "
     "averaged. Table 1 shows a subset of the learners; the full comparison will be in the final report.")
table(["Method", "x265, k = 0", "x265, k = 5", "x264, k = 0", "x264, k = 5"],
      [["Constant QP (reference)", "0.00 / 0 %", "", "0.00 / 0 %", ""],
       ["STATIC pattern", "−13.70 / 50 %", "", "−15.95 / 56 %", ""],
       ["Encoder's own two-pass", "−18.75 / 41 %", "", "−3.44 / 5 %", ""],
       ["Behaviour cloning", "1.68 / 17 %", "3.77 / 9 %", "0.21 / 19 %", "2.65 / 21 %"],
       ["CQL (offline RL)", "−3.42 / 29 %", "−1.77 / 26 %", "−4.07 / 29 %", "−1.23 / 25 %"],
       ["PPO from scratch", "0.41 / 10 %", "0.32 / 14 %", "−0.74 / 15 %", "0.15 / 14 %"],
       ["CQL → PPO", "0.74 / 22 %", "3.48 / 15 %", "−1.17 / 25 %", "0.43 / 24 %"],
       ["Lagrangian PPO", "4.36 / 1 %", "4.95 / 2 %", "3.90 / 2 %", "4.07 / 6 %"],
       ["MPC (learned model)", "−1.78 / 6 %", "−0.43 / 7 %", "−3.58 / 10 %", "−2.46 / 10 %"],
       ["Hindsight search (ceiling)", "10.53 / 1 %", "", "9.95 / 1 %", ""]],
      [2.05, 1.15, 1.15, 1.15, 1.15],
      "Table 1. Score / share of test cases > 1 % over budget (2 budgets, 3 seeds). Single entries do not depend on k.",
      bold_rows=(7,))
bullet("**The search finds about 10 % savings** at equal PSNR on both encoders, and it is still improving at 300 "
       "encodes, so this is a lower bound on what is attainable.")
bullet("**Imitation gives a useful start; budget-constrained RL is the best single-pass controller so far.** The "
       "Lagrangian learner beats BC by +2.7 points on x265 at k = 0 and is within budget on almost every GOP. It "
       "captures roughly 40–50 % of the search's gain.")
bullet("**Lookahead (Fig. 1):** going from k = 0 to k = 2–3 is clearly worth it on x265 (+3.4 points for CQL → PPO); "
       "beyond that the curve is noisy across seeds. x264 is noisier still.")
d.add_picture(FIG, width=Inches(6.3))
d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
caption("Figure 1. Score of CQL → PPO against lookahead k (test, 2 budgets, mean of 3 seeds).")

d.add_heading("4.1 What did not work", level=2)
bullet("**Online RL from scratch** (PPO, A2C, DQN) stays within ±1.5 points of constant QP with 60 k real encodes. "
       "This is partly a compute result: the offline learners start from about 1.4 M search encodes.")
bullet("**Pure offline RL** (CQL, IQL) is worse than plain imitation: it stays close to logged plans that are mostly near "
       "STATIC, and overshoots on 10–29 % of cases.")
bullet("**Model-based RL.** MPC exploits its model's errors, and pre-training inside the learned model fails because "
       "the model's ≈ 15 % bit error is larger than the effect of a good allocation.")
bullet("**RL fine-tuning on top of imitation adds little quality.** With clip-level confidence intervals, CQL → PPO − BC "
       "at k = 5 is −0.28 [−0.94, +0.22] on x265, not significant. RL's measurable contribution so far is "
       "budget reliability, not quality.")
bullet("**More lookahead is not always better.** At k = 29 the policy scores 1.7 points below k = 3 (clip-level CI "
       "excludes 0). Long windows make learning harder at our data size.")
bullet("**The encoders' own rate control** scores below constant QP in our setting, but that comparison is not fair to "
       "the encoder (Section 5), so we do not claim to beat it yet.")

# ---------------------------------------------------------------- 5
d.add_heading("5. Holes we found in the problem formulation", level=1)
para("A review of the setup found that some of the information the learners get is not available to a real encoder:")
bullet("**Oracle base QP.** Every learner is told the base QP, i.e. the constant QP that exactly meets this GOP's budget. "
       "Finding that QP is the hardest part of real rate control, and the encoder gets only a bitrate.")
bullet("**Budget leak.** Because the budget is defined as the GOP's own constant-QP cost, the budget features (budget "
       "relative to first-pass cost) reveal the GOP's true cost even at k = 0. So the k = 0 results are likely "
       "optimistic, and the lookahead curve may be compressed.")
bullet("**Scene flags look ahead.** The flash and fade detectors use up to 4 later frames. Recomputed causally, 2.4 % of "
       "frames get different flags at k = 0.")
bullet("**Statistics and data.** Our confidence intervals were over cases, not clips (the 479 test GOPs come from only 38 "
       "source clips plus 60 splices). 60 of the 90 test GOPs with a cut are artificial splices. Re-analysed at clip "
       "level, most headline differences still hold, but some small ones do not (e.g. k = 2 → 3).")
bullet("**Weak baselines.** The fixed STATIC pattern is poorly fitted (−13.7 on x265), and the encoders' own rate control "
       "is penalised by our oracle-based budget, by 30-frame episodes that are too short for ABR to converge, and by a "
       "PSNR score while its defaults target subjective quality.")

# ---------------------------------------------------------------- 6
d.add_heading("6. Pivot", level=1)
bullet("**A causal setting.** The budget becomes a scaled constant-QP cost with the scale hidden from the controller, "
       "the base QP comes from a GOP-level first-pass rate model fitted on training data (as an encoder's lookahead would "
       "provide), and scene flags are computed only from visible frames. A first attempt that re-estimated the base QP "
       "every frame failed (its first-frame QP was within ±2 of the right value in only 25 % of cases at k = 0), so we "
       "moved to the GOP-level model, which we are now testing.")
bullet("**A fair head-to-head with the encoder's own rate control**, where nobody gets an oracle QP: streams of several "
       "GOPs under one bitrate, with the encoder given the same lookahead as the learner. Our check shows that the joined "
       "stream reproduces the per-GOP encodes bit-exactly on x265.")
bullet("**A stronger non-RL baseline**: imitation plus a simple closed-loop budget correction (in the spirit of Mao et "
       "al.'s inference-time feedback). It tests whether RL is really needed for the budget.")
bullet("**Reframing.** The study's claims are about the lookahead–quality trade-off and about budget handling. The main "
       "learner moves from the penalty-based CQL → PPO to constrained RL.")

# ---------------------------------------------------------------- 7
d.add_heading("7. What is missing and future plan", level=1)
para("**Not done yet from the proposal:** RecurrentPPO (memory-based learner), the safety shield for the budget, the "
     "privileged-teacher actor-critic, VMAF as a second quality metric, and the encoder's CRF mode as a baseline.")
table(["Planned run / analysis", "Purpose"],
      [["Causal rerun of the core learners (CQL → PPO at k = 0, 1, 2, 3, 5; BC, Lagrangian, PID at k = 0, 5; 3 seeds; both encoders)",
        "Lookahead curve and method ranking without the oracle QP and the leak"],
       ["Encoder's own ABR / two-pass on the same causal budgets and on multi-GOP streams",
        "Fair head-to-head with real rate control"],
       ["BC + feedback control (tuned on validation)", "Is RL needed, or is imitation plus feedback enough?"],
       ["Wider range of budgets (QP 26 to 42)", "Do the conclusions hold from high to low bit rates?"],
       ["Budget shared across several GOPs", "Allocation across GOPs, closer to real streaming"],
       ["Stable vs scene-cut GOPs; extra lookahead only around cuts", "When future information is valuable (feedback suggestions)"],
       ["Dataset v1 with human-checked scene labels", "Natural cuts instead of splices; more balanced content"],
       ["VMAF, CRF baseline, RecurrentPPO, safety shield", "Remaining proposal items"]],
      [3.8, 2.85], "Table 2. Runs and analyses planned for the final report.")
para("The final report will give results for both encoders with clip-level intervals, the lookahead curve in the "
     "causal setting, and a clear statement of what RL adds over imitation, including negative results.")

d.save(OUT)
print("wrote", OUT)
