"""Page-count proxy for a .docx when Word/LibreOffice are unavailable: re-typesets its body with XeLaTeX and Carlito
(Calibri's metrics), Word's single-line height (1.22 x size), the same margins and spacing, and no hyphenation.
usage: python3 tools/docx_pagecheck.py in.docx outdir"""
import os, re, subprocess, sys
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
d = Document(src); s = d.sections[0]
IN = 914400
def esc(t):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_"), ("$", r"\$"), ("{", r"\{"), ("}", r"\}"), ("~", r"\~{}")):
        t = t.replace(a, b)
    return t
def size(r, p):
    if r.font.size: return r.font.size.pt
    st = p.style
    while st is not None:
        if st.font.size: return st.font.size.pt
        st = st.base_style
    return 10
def rtext(p):
    o = []
    for r in p.runs:
        t = esc(r.text).replace("\t", r"\hspace{0.5em}")
        if not t: continue
        b = r.bold or (p.style.font.bold is True); i = r.italic
        o.append(("\\textbf{%s}" if b else "%s") % (("\\textit{%s}" if i else "%s") % t))
    return "".join(o)
L = [r"\documentclass{article}", r"\usepackage{fontspec,graphicx,array,setspace}",
     r"\usepackage[paperwidth=%.3fin,paperheight=%.3fin,left=%.3fin,right=%.3fin,top=%.3fin,bottom=%.3fin]{geometry}" % (
        s.page_width/IN, s.page_height/IN, s.left_margin/IN, s.right_margin/IN, s.top_margin/IN, s.bottom_margin/IN),
     r"\setmainfont{Carlito-Regular.ttf}[Path=/apps/generic/texlive/2024/texmf-dist/fonts/truetype/google/carlito/,BoldFont=Carlito-Bold.ttf,ItalicFont=Carlito-Italic.ttf,BoldItalicFont=Carlito-BoldItalic.ttf]",
     r"\pagestyle{empty}\setlength{\parindent}{0pt}\setlength{\parskip}{0pt}\hyphenpenalty=10000\exhyphenpenalty=10000\emergencystretch=3em\tolerance=2000\raggedbottom",
     r"\setlength{\tabcolsep}{0.075in}\renewcommand{\arraystretch}{1}\begin{document}"]
imgs = {r.rId: r.target_part.blob for r in d.part.rels.values() if "image" in r.reltype}
for n, blob in enumerate(imgs.values()):
    open(os.path.join(out, f"img{n}.png"), "wb").write(blob)
nimg = 0
for el in d.element.body.iterchildren():
    if el.tag.endswith("}p"):
        p = Paragraph(el, d); pf = p.paragraph_format; ps = p.style.paragraph_format
        if "w:br" in el.xml and 'w:type="page"' in el.xml:
            L.append(r"\clearpage"); continue
        if el.xpath(".//w:drawing"):
            ext = el.xpath(".//wp:extent")[0]; w = int(ext.get("cx"))/IN
            L.append(r"\begin{center}\includegraphics[width=%.3fin]{img%d.png}\end{center}\vspace{-1.2em}" % (w, nimg)); nimg += 1; continue
        runs = [r for r in p.runs if r.text]
        sz = size(runs[0], p) if runs else 10
        before = pf.space_before.pt if pf.space_before is not None else (ps.space_before.pt if ps.space_before is not None else 0)
        after = pf.space_after.pt if pf.space_after is not None else (ps.space_after.pt if ps.space_after is not None else 3)
        if not runs:
            ls = pf.line_spacing
            L.append(r"\vspace{%.1fpt}" % (ls.pt if hasattr(ls, "pt") else 12)); continue
        ind = (pf.left_indent or 0)/IN if pf.left_indent else 0
        if p.style.name == "List Bullet":
            ind = 0.25; t = r"\hspace{-0.25in}\makebox[0.25in][l]{•}" + rtext(p)
        elif ind:
            t = r"\hspace{-%.2fin}" % ind + rtext(p)
        else:
            t = rtext(p)
        al = r"\centering" if p.alignment is not None and int(p.alignment) == 1 else ("" if p.alignment is not None and int(p.alignment) == 3 else r"\raggedright")
        L.append(r"\vspace{%.1fpt}{\fontsize{%.1f}{%.2f}\selectfont\leftskip=%.2fin %s %s\par}\vspace{%.1fpt}" % (before, sz, sz*1.22, ind, al, t, after))
    elif el.tag.endswith("}tbl"):
        t = Table(el, d); w = [c.width/IN for c in t.rows[0].cells]
        sz = size(t.cell(0, 0).paragraphs[0].runs[0], t.cell(0, 0).paragraphs[0])
        L.append(r"{\fontsize{%.1f}{%.2f}\selectfont\begin{center}\vspace{-1em}\begin{tabular}{|%s|}\hline" % (sz, sz*1.22, "|".join(r">{\raggedright\arraybackslash}p{%.3fin}" % (x-0.15) for x in w)))
        for r in t.rows:
            L.append(" & ".join(esc(c.text) for c in r.cells) + r"\\\hline")
        L.append(r"\end{tabular}\vspace{-1em}\end{center}}")
L.append(r"\end{document}")
open(os.path.join(out, "proxy.tex"), "w").write("\n".join(L))
env = dict(os.environ, PATH="/apps/generic/texlive/2024/bin/x86_64-linux:" + os.environ["PATH"], TEXMFVAR="/scratch1/pbanga/tmp/texmf-var")
r = subprocess.run(["xelatex", "-interaction=nonstopmode", "proxy.tex"], cwd=out, env=env, capture_output=True, text=True)
print(re.findall(r"Output written.*|^! .*", r.stdout, re.M)[:6])
