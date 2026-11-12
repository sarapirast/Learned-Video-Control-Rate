"""Build the EE599 milestone report (x265, preliminary) as a Word document."""
import sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT = sys.argv[1]
FONT = "Calibri"
INK = RGBColor(0x1F, 0x1F, 0x1F)
ACCENT = RGBColor(0x1F, 0x4E, 0x79)

d = Document()
sec = d.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for m in ("left_margin", "right_margin"):
    setattr(sec, m, Inches(0.9))
sec.top_margin = sec.bottom_margin = Inches(0.8)

st = d.styles["Normal"]
st.font.name, st.font.size, st.font.color.rgb = FONT, Pt(10), INK
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(4)
st.paragraph_format.line_spacing = 1.0
for name, size in (("Heading 1", 12.5), ("Heading 2", 11)):
    h = d.styles[name]
    h.font.name, h.font.size, h.font.bold, h.font.color.rgb = FONT, Pt(size), True, ACCENT
    h.element.rPr.rFonts.set(qn("w:asciiTheme"), "") if False else None
    rf = h.element.rPr.find(qn("w:rFonts"))
    for a in list(rf.attrib):
        del rf.attrib[a]
    rf.set(qn("w:ascii"), FONT); rf.set(qn("w:hAnsi"), FONT)
    h.paragraph_format.space_before = Pt(9 if name == "Heading 1" else 6)
    h.paragraph_format.space_after = Pt(3)
    h.paragraph_format.keep_with_next = True
for name in ("List Bullet",):
    s = d.styles[name]
    s.font.name, s.font.size = FONT, Pt(10)
    s.paragraph_format.space_after = Pt(2)


def runs(p, text):
    """**bold** segments inside text."""
    parts = text.split("**")
    for i, t in enumerate(parts):
        if t:
            r = p.add_run(t)
            r.bold = i % 2 == 1
    return p


def para(text, **kw):
    p = runs(d.add_paragraph(), text)
    if kw.get("italic"):
        for r in p.runs:
            r.italic = True
    if kw.get("size"):
        for r in p.runs:
            r.font.size = Pt(kw["size"])
    return p


def bullet(text):
    return runs(d.add_paragraph(style="List Bullet"), text)


def shade(cell, hex_):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hex_)
    tcPr.append(s)


def table(head, rows, widths, caption, bold_rows=()):
    cap = d.add_paragraph()
    r = cap.add_run(caption); r.bold = True; r.font.size = Pt(9.5)
    cap.paragraph_format.space_before = Pt(4); cap.paragraph_format.space_after = Pt(2)
    cap.paragraph_format.keep_with_next = True
    t = d.add_table(rows=1 + len(rows), cols=len(head))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for j, w in enumerate(widths):
        t.columns[j].width = Inches(w)
    for i, row in enumerate([head] + rows):
        for j, v in enumerate(row):
            c = t.cell(i, j)
            c.width = Inches(widths[j])
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            rr = p.add_run(v); rr.font.size = Pt(9.5)
            if i == 0:
                rr.bold = True; shade(c, "DCE6F0")
            elif i - 1 in bold_rows:
                rr.bold = True; shade(c, "F2F2F2")
    d.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


# ---- title ----
p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Learned Per-Frame QP Rate Control with Lookahead"); r.bold = True; r.font.size = Pt(16); r.font.color.rgb = ACCENT
p.paragraph_format.space_after = Pt(0)
p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("EE599 Milestone Report — preliminary results (x265)"); r.font.size = Pt(11.5)
p.paragraph_format.space_after = Pt(0)
p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("[Team members]  ·  November 3, 2026"); r.font.size = Pt(10); r.italic = True

para("**Status.** Interim report. The numbers are preliminary, from the first complete run of the pipeline on one "
     "encoder (x265); x264 and the full method comparison are left for the final report. A run with a wider range of "
     "bit budgets is in progress (Section 6).")

# ---- 1 ----
d.add_heading("1. Problem and setup", level=1)
para("A video encoder's rate controller chooses a quantiser (QP) for every frame so that a group of pictures (GOP) fits "
     "a bit budget at the highest possible quality. We train reinforcement-learning (RL) agents that make this choice "
     "frame by frame, and ask how much it helps for the agent to see the next **k** frames (lookahead), which RL recipe "
     "works best, and how close a learned controller gets to an exhaustive offline plan.")
bullet("**Episode:** one 30-frame GOP (one I frame + 29 P frames, no B-frames, adaptive quantisation and cutree off), "
       "encoded with x265 4.1 (fast preset). Every reward comes from a real encode: bits from the bitstream, PSNR from decoding the output.")
bullet("**Action:** a QP offset of −3…+3 per frame around a fixed QP pattern (STATIC: I frame −6, P1–9 −3, P10–29 +3).")
bullet("**Budget:** the bits x265's own constant-QP mode spends on the same GOP at QP 30 or QP 38.")
bullet("**Score:** % bits saved at equal PSNR against the encoder's constant-QP rate–quality curve, minus 2 points for "
       "every 1 % over budget. We always report the share of GOPs more than 1 % over budget next to it.")
bullet("**Ceiling:** a hindsight search (300 real encodes × 2 seeds per GOP and budget). It is not a usable "
       "controller; it is the target, and its logged plans are the training data for offline RL.")

# ---- 2 ----
d.add_heading("2. Dataset: what these results use, and the new dataset", level=1)
para("All results in this report are on dataset **v0** below. Every video is downscaled to 320×180 and cut into "
     "30-frame GOPs, split by source so no video is in two splits. Test numbers are over 479 GOPs × 2 budgets = 958 "
     "cases, 3 seeds; all choices were made on validation. We are now moving to dataset **v1**.")
table(["", "v0 (this report)", "v1 (new)"],
      [["Clips / frames", "187 / 171,667", "109 / 31,342 (≤ 450 frames per clip)"],
       ["GOPs (train / val / test)", "2,061 (1,196 / 386 / 479)", "1,042 (625 / 152 / 265)"],
       ["YouTube UGC", "961 GOPs (47 %)", "420 GOPs (40 %)"],
       ["Films", "401 GOPs from 5 films (4 long)", "280 GOPs, 28 Blender clips"],
       ["Test sequences", "Xiph CIF + HD: 479 GOPs", "Xiph LDV/NTIA/SVT, UVG: 222 GOPs"],
       ["Other", "—", "archive.org: 60 GOPs"],
       ["Spliced GOPs (known cuts)", "220", "60"],
       ["Scene-cut labels", "automatic detector (F1 0.96 on splices)", "two detectors + human review; every GOP labelled stable / cut / gradual (870 / 157 / 15)"]],
      [1.75, 2.15, 2.8], "Table 1. Dataset v0 (used here) and v1 (next). Both at 320×180.")
para("**The change from v0 to v1:** v1 has about half the GOPs but is more balanced. In v0 four long films supply "
     "17 % of all GOPs and the Xiph CIF clips are low-motion with almost no cuts. v1 caps clip length, adds new sources (UVG, Xiph "
     "LDV/NTIA/SVT, archive.org, many more Blender clips) and has human-checked scene cuts and gradual transitions on "
     "natural content, not only on spliced GOPs. v1 is not complete yet: 39 planned clips (e.g. JVET conferencing, "
     "Netflix, more UVG and UGC) are still to be downloaded.")

# ---- 3 ----
d.add_heading("3. Preliminary results (x265, test set)", level=1)
table(["Method", "Lookahead k", "Score", "Saving (%)", ">1 % over budget"],
      [["Constant QP (reference)", "—", "0.00", "0.00", "0 %"],
       ["STATIC pattern", "—", "−13.70", "1.62", "50 %"],
       ["x265 own 2-pass rate control", "full", "−18.75", "−11.15", "41 %"],
       ["Hand-made lookahead rule", "5", "−2.51", "0.05", "19 %"],
       ["Behaviour cloning (BC)", "5", "3.77", "4.58", "9 %"],
       ["Offline RL only (CQL)", "5", "−1.77", "3.25", "26 %"],
       ["CQL → PPO fine-tuning (proposed core)", "5", "3.48", "5.11", "15 %"],
       ["Lagrangian PPO (budget as constraint)", "5", "4.95", "5.22", "2 %"],
       ["Hindsight search (ceiling)", "29", "10.53", "10.61", "1 %"]],
      [2.65, 0.95, 0.8, 0.95, 1.35], "Table 2. Selected methods (partial; the full comparison has 12 learners).", bold_rows=(7,))
table(["Lookahead k", "0", "1", "3", "5", "10", "29 (full GOP)"],
      [["Score", "0.74", "2.30", "4.10", "3.48", "3.18", "2.37"],
       ["Saving (%)", "3.97", "4.29", "5.34", "5.11", "5.18", "4.48"],
       ["Share of search saving", "37 %", "40 %", "50 %", "48 %", "49 %", "42 %"],
       [">1 % over budget", "22 %", "13 %", "11 %", "15 %", "16 %", "13 %"]],
      [1.75, 0.65, 0.65, 0.65, 0.65, 0.65, 1.2], "Table 3. Lookahead curve of CQL → PPO (partial; 14 values of k were trained).")
para("**What we see so far.**")
bullet("Every learned controller with a few frames of lookahead beats the hand-made rules and x265's own rate control on "
       "this metric. The best learned methods save about 5 % bits at equal PSNR, **about half of the hindsight ceiling (10.6 %)**.")
bullet("Lookahead helps, but only the first few frames matter: the score rises from 0.7 (k = 0) to 4.1 (k = 3), and "
       "beyond that the curve is noisy (scores between 1.5 and 4.5) with no clear upward trend. Seeing the whole GOP (k = 29) scores lower than seeing 3 frames.")
bullet("Staying within budget, more than saving, is what separates the methods. Lagrangian PPO saves about as much as CQL → PPO "
       "but is over budget on 2 % of GOPs instead of 15 %, and has the best score of any controller in Table 2.")
bullet("Most of the gain is on GOPs with a scene cut (CQL → PPO k = 5 saves 7.6 % there vs 4.8 % on stable GOPs).")

# ---- 4 ----
d.add_heading("4. What we think is wrong or limited", level=1)
bullet("**The lookahead curve should not go down.** More information should never hurt an ideal policy, so the lower "
       "scores at large k points to learning, not information. Longer windows add inputs without adding training data, and the "
       "differences between neighbouring k are about the size of the 3-seed noise (paired 95 % intervals of ±0.3–0.5 points). "
       "We do not yet know if the plateau is real or an artefact of training budget and seed count.")
bullet("**A penalty is not a constraint.** The proposed core recipe (CQL → PPO with a penalty of 2 points per % over) "
       "still overshoots on 15 % of GOPs. Offline RL alone (CQL) overshoots on 26 %, so online fine-tuning is needed "
       "to learn the budget at all. Treating the budget as a constraint "
       "(Lagrangian or PID multiplier) fixes this.")
bullet("**Two budgets are too few.** With budgets at only QP 30 and QP 38, the policy's budget input takes two values, "
       "so it may have learned two separate behaviours instead of one that scales with the budget. We cannot say yet "
       "whether the ranking of methods holds at higher or lower rates.")
bullet("**The x265 comparison is not fair to x265, and the setting is small.** x265's 2-pass lands within 1–2 % of "
       "the target, but its defaults are tuned for subjective quality, not PSNR, and 30 frames give single-pass ABR no "
       "time to converge. 320×180, 30-frame GOPs and no B-frames keep an encode at ~0.3 s, which makes the search "
       "possible but is far from production settings.")
bullet("**A learned encoder model was not accurate enough.** Pre-training the agent in a learned model of the encoder "
       "taught it to spend fewer bits but not where to spend them (saving 1.3 %): the model's ~15 % bit error "
       "is larger than the difference between a good and a bad allocation.")

# ---- 5 ----
d.add_heading("5. Changes to the initial proposal", level=1)
bullet("**Main method:** we propose to make constrained RL (Lagrangian / PID-Lagrangian PPO) the main method, instead of "
       "the penalty-based CQL → PPO named in the proposal. CQL → PPO stays as the method for the lookahead curve, so "
       "that curve stays comparable across k.")
bullet("**Budgets:** from 2 budget levels (QP 30, 38) to 5 (QP 26, 30, 34, 38, 42), covering roughly a 9× range of bit rates.")
bullet("**Metrics:** the over-budget share becomes a headline metric next to the score, not a footnote.")
bullet("**Model-based RL:** dropped from the main plan after the negative result above. It stays in the report as a "
       "documented negative result.")
bullet("**Data:** move from v0 to dataset v1 (Section 2). x264 runs through the same pipeline and will be in the final report.")

# ---- 6 ----
d.add_heading("6. What we are doing next", level=1)
para("**Expansion now in progress.** The results above use two budgets. We are re-running the core study on the same "
     "2,061 GOPs with **five budget QPs (26, 30, 34, 38, 42)**, to see whether a wider range of rates improves the "
     "learned policies and whether the conclusions above still hold. Only what is new is computed: STATIC encodes and "
     "the hindsight search at QP 26, 34 and 42 (QP 30 and 38 are reused). Then we retrain CQL → PPO at all 14 lookahead "
     "values, plus BC, Lagrangian and PID-Lagrangian PPO at k = 0, 5, 10, 3 seeds each (69 RL runs per encoder). "
     "The new encodes are finished and most of the search is done; RL training follows.")
para("It answers whether each method's score and over-budget share hold at all five budgets (or one end, e.g. QP 42, "
     "breaks it), whether the lookahead plateau at k ≈ 3 is the same at every budget, and whether the gap to the "
     "ceiling shrinks when the policy sees a continuous range of budgets.")
para("**Dataset v1.** Next we run the same pipeline on v1, to see whether a more balanced set with human-labelled cuts "
     "improves the learned policies, especially on GOPs with cuts and gradual transitions, where v0's labels were only "
     "automatic. Because v1 is smaller, we will compare methods within each dataset rather than mix the two.")
para("**After that:** more seeds at the key values of k, to settle whether the lookahead curve really flattens after k = 3; "
     "the x264 vs x265 comparison; and, if time allows, a check at a higher resolution (e.g. 640×360) on a subset of the clips. "
     "The final report will include x264, all 12 learners and the per-budget results.")

d.save(OUT)
print("wrote", OUT)
