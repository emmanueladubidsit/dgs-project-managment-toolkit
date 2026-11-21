"""Render workspace content (a Markdown subset) to Word, PDF and PowerPoint for stakeholders.

Supported Markdown: #/##/### headings, paragraphs, "- " bullets (two-space indent = nested),
"- [ ]"/"- [x]" checklists, numbered lists, **bold**, _italic_/*italic*, `code` and "---" rules.
Everything is generated from stored data; nothing is invented here."""

import io
import re
from dataclasses import dataclass
from datetime import date, datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from pptx import Presentation
from pptx.dml.color import RGBColor as PptxRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches
from pptx.util import Pt as PPt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

BRAND = (0x2B, 0x4F, 0xBF)  # matches the app's primary colour
MUTED = (0x5F, 0x67, 0x78)

MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


# ---------------------------------------------------------------- parsing
@dataclass
class Block:
    kind: str  # h1 h2 h3 p bullet hr
    text: str = ""
    level: int = 0
    marker: str = ""  # "", "☐", "☑", "1." …


def parse(md: str) -> list[Block]:
    blocks: list[Block] = []
    para: list[str] = []

    def flush():
        if para:
            blocks.append(Block("p", " ".join(s.strip() for s in para)))
            para.clear()

    for raw in md.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        stripped = line.lstrip()
        indent = (len(line) - len(stripped)) // 2
        if not stripped:
            flush()
            continue
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            flush()
            blocks.append(Block("hr"))
            continue
        h = re.match(r"(#{1,3})\s+(.*)", stripped)
        if h:
            flush()
            blocks.append(Block(f"h{len(h.group(1))}", h.group(2).strip()))
            continue
        c = re.match(r"[-*]\s+\[( |x|X)\]\s+(.*)", stripped)
        if c:
            flush()
            blocks.append(
                Block("bullet", c.group(2), indent, "☑" if c.group(1).lower() == "x" else "☐")
            )
            continue
        b = re.match(r"[-*•]\s+(.*)", stripped)
        if b:
            flush()
            blocks.append(Block("bullet", b.group(1), indent))
            continue
        n = re.match(r"(\d+)[.)]\s+(.*)", stripped)
        if n:
            flush()
            blocks.append(Block("bullet", n.group(2), indent, f"{n.group(1)}."))
            continue
        para.append(stripped)
    flush()
    return blocks


INLINE = re.compile(
    r"(\*\*[^*]+\*\*|`[^`]+`|(?<![\w*])_[^_]+_(?![\w])|(?<![\w*])\*[^*]+\*(?![\w*]))"
)


def runs(text: str) -> list[tuple[str, bool, bool, bool]]:
    """Split inline Markdown into (text, bold, italic, code) runs."""
    out = []
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append((part[2:-2], True, False, False))
        elif part.startswith("`") and part.endswith("`"):
            out.append((part[1:-1], False, False, True))
        elif len(part) > 2 and part[0] in "_*" and part[-1] == part[0]:
            out.append((part[1:-1], False, True, False))
        else:
            out.append((part, False, False, False))
    return out


def plain(text: str) -> str:
    return "".join(r[0] for r in runs(text))


def _footer() -> str:
    return f"Generated from the DGS Engineering Workspace on {datetime.now():%d %B %Y at %H:%M}."


# ---------------------------------------------------------------- Word
def to_docx(title: str, md: str, subtitle: str | None = None) -> bytes:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        doc.styles[name].font.color.rgb = RGBColor(*BRAND)
    doc.add_heading(title, level=0)
    if subtitle:
        p = doc.add_paragraph(subtitle)
        p.runs[0].font.color.rgb = RGBColor(*MUTED)
    blocks = parse(md)
    if blocks and blocks[0].kind == "h1" and plain(blocks[0].text).strip() == title.strip():
        blocks = blocks[1:]  # avoid repeating the title
    for b in blocks:
        if b.kind in ("h1", "h2", "h3"):
            doc.add_heading(plain(b.text), level=int(b.kind[1]))
        elif b.kind == "hr":
            doc.add_paragraph("")
        else:
            if b.kind == "bullet":
                style_name = "List Number" if b.marker.endswith(".") else "List Bullet"
                if b.level:
                    style_name += " 2"
                p = doc.add_paragraph(style=style_name)
                if b.marker in ("☐", "☑"):
                    p.add_run(b.marker + " ")
            else:
                p = doc.add_paragraph()
            for text, bold, italic, code in runs(b.text):
                r = p.add_run(text)
                r.bold, r.italic = bold, italic
                if code:
                    r.font.name = "Consolas"
    foot = doc.sections[0].footer.paragraphs[0]
    foot.text = _footer()
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    foot.runs[0].font.size = Pt(8)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- PDF
_PDF_SAFE = {
    "→": "->",
    "←": "<-",
    "✓": "Yes",
    "✅": "Yes",
    "☐": "[ ]",
    "☑": "[x]",
    "≥": ">=",
    "≤": "<=",
    "↳": ">",
    "…": "...",
    " ": " ",
    " ": " ",
}


def _pdf_text(text: str) -> str:
    """Escape for ReportLab mini-HTML and keep within the built-in (WinAnsi) font."""
    for k, v in _PDF_SAFE.items():
        text = text.replace(k, v)
    text = text.encode("cp1252", "replace").decode("cp1252").replace("?", "?")
    out = []
    for t, bold, italic, code in runs(text):
        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if code:
            t = f'<font face="Courier">{t}</font>'
        if bold:
            t = f"<b>{t}</b>"
        if italic:
            t = f"<i>{t}</i>"
        out.append(t)
    return "".join(out)


def to_pdf(title: str, md: str, subtitle: str | None = None) -> bytes:
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    brand = colors.Color(*(c / 255 for c in BRAND))
    s_title = ParagraphStyle(
        "t", parent=styles["Title"], textColor=brand, alignment=TA_LEFT, fontSize=20
    )
    s = {
        "h1": ParagraphStyle("h1", parent=styles["Heading1"], textColor=brand, fontSize=16),
        "h2": ParagraphStyle(
            "h2", parent=styles["Heading2"], textColor=brand, fontSize=13, spaceBefore=10
        ),
        "h3": ParagraphStyle("h3", parent=styles["Heading3"], fontSize=11),
        "p": ParagraphStyle("p", parent=styles["BodyText"], fontSize=10, leading=14),
        "muted": ParagraphStyle("m", parent=styles["BodyText"], fontSize=9, textColor=colors.grey),
    }

    def on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.grey)
        canvas.drawString(18 * mm, 10 * mm, _footer())
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    story = [Paragraph(_pdf_text(title), s_title)]
    if subtitle:
        story.append(Paragraph(_pdf_text(subtitle), s["muted"]))
    story.append(Spacer(1, 6))
    blocks = parse(md)
    if blocks and blocks[0].kind == "h1" and plain(blocks[0].text).strip() == title.strip():
        blocks = blocks[1:]
    pending: list[ListItem] = []

    def flush_list():
        if pending:
            story.append(
                ListFlowable(
                    list(pending), bulletType="bullet", start="•", leftIndent=12, bulletFontSize=8
                )
            )
            pending.clear()

    for b in blocks:
        if b.kind == "bullet":
            prefix = f"{b.marker} " if b.marker else ""
            pending.append(
                ListItem(
                    Paragraph(_pdf_text(prefix + b.text), s["p"]), leftIndent=12 + b.level * 12
                )
            )
            continue
        flush_list()
        if b.kind == "hr":
            story.append(
                HRFlowable(width="100%", color=colors.lightgrey, spaceBefore=6, spaceAfter=6)
            )
        else:
            story.append(Paragraph(_pdf_text(b.text), s[b.kind]))
    flush_list()
    SimpleDocTemplate(
        buf,
        pagesize=A4,
        title=title,
        author="DGS Engineering Workspace",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    ).build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


# ---------------------------------------------------------------- PowerPoint
MAX_BULLETS = 7
FONT = "Calibri"


def to_pptx(title: str, md: str, subtitle: str | None = None) -> bytes:
    """Title slide, then one slide per ## section (long sections continue on extra slides)."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    brand, muted = PptxRGB(*BRAND), PptxRGB(*MUTED)

    def accent(slide):
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.12))
        bar.fill.solid()
        bar.fill.fore_color.rgb = brand
        bar.line.fill.background()

    width = prs.slide_width - Inches(1.4)

    def place(shape, top, height):
        shape.left, shape.top, shape.width, shape.height = Inches(0.7), top, width, height

    def style(shape, size, color, bold=False):
        for para in shape.text_frame.paragraphs:
            for r in para.runs:
                r.font.name, r.font.size, r.font.color.rgb, r.font.bold = (
                    FONT,
                    PPt(size),
                    color,
                    bold,
                )

    s0 = prs.slides.add_slide(prs.slide_layouts[0])
    accent(s0)
    s0.shapes.title.text = title
    place(s0.shapes.title, Inches(2.3), Inches(1.6))
    style(s0.shapes.title, 40, brand, bold=True)
    s0.placeholders[1].text = subtitle or f"{date.today():%d %B %Y}"
    place(s0.placeholders[1], Inches(4.0), Inches(1.0))
    style(s0.placeholders[1], 20, muted)

    sections: list[tuple[str, list[Block]]] = []
    for b in parse(md):
        if b.kind == "h1":
            continue
        if b.kind == "h2" or not sections:
            sections.append((plain(b.text) if b.kind == "h2" else "Summary", []))
            if b.kind == "h2":
                continue
        if b.kind in ("p", "bullet", "h3"):
            sections[-1][1].append(b)

    for heading, items in sections:
        items = items or [Block("p", "None recorded.")]
        chunks = [items[i : i + MAX_BULLETS] for i in range(0, len(items), MAX_BULLETS)]
        for n, chunk in enumerate(chunks):
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            accent(slide)
            slide.shapes.title.text = heading + (f" (continued {n + 1}/{len(chunks)})" if n else "")
            place(slide.shapes.title, Inches(0.4), Inches(1.0))
            style(slide.shapes.title, 30, brand, bold=True)
            slide.shapes.title.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
            body = slide.placeholders[1]
            place(body, Inches(1.6), Inches(5.4))
            tf = body.text_frame
            tf.clear()
            for i, b in enumerate(chunk):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.level = min(b.level, 2) if b.kind == "bullet" else 0
                text = (f"{b.marker} " if b.marker else "") + b.text
                text = text if len(text) <= 220 else text[:217] + "…"
                for t, bold, italic, _code in runs(text):
                    r = p.add_run()
                    r.text = t
                    r.font.bold = bold or b.kind == "h3"
                    r.font.italic = italic
                    r.font.size = PPt(18 if p.level == 0 else 15)
                    r.font.name = FONT
    last = prs.slides.add_slide(prs.slide_layouts[5])
    accent(last)
    last.shapes.title.text = "Generated from workspace data"
    place(last.shapes.title, Inches(0.4), Inches(1.0))
    style(last.shapes.title, 30, brand, bold=True)
    box = last.shapes.add_textbox(Inches(0.7), Inches(2), Inches(11.5), Inches(1))
    box.text_frame.text = _footer() + " Figures reflect what was recorded at that time."
    box.text_frame.paragraphs[0].runs[0].font.color.rgb = muted
    box.text_frame.paragraphs[0].runs[0].font.name = FONT
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def render(fmt: str, title: str, md: str, subtitle: str | None = None) -> bytes:
    return {"docx": to_docx, "pdf": to_pdf, "pptx": to_pptx}[fmt](title, md, subtitle)


def filename(title: str, fmt: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()[:80] or "export"
    return f"{slug}.{fmt}"
