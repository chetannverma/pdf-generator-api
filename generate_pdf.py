"""
generate_pdf.py  — FINAL v2 (matches Design Reference exactly)
──────────────────────────────────────────────────────────────
Reference design:
  • Header  : white box top-left with logo | right = Subject | Chapter | Date
  • Layout  : TWO-COLUMN newspaper style
  • Section : Full-width green bar "ECONOMIC GROWTH AND DEVELOPMENT"
  • Items   : Bold blue numbered heading, body text, bullet points
  • Nuggets : Bordered box with pencil icon header
  • Footer  : phone left | website centre | page-number green box right
  • Watermark: LOGO-CROP.png centred, 20% opacity, 550×550 px
  • Font    : Helvetica throughout (matches reference)
"""

import io
import os
import sys
import argparse
import numpy as np
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, KeepTogether, PageBreak,
    NextPageTemplate
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.utils import ImageReader

# ── Brand ─────────────────────────────────────────────────────────────────────
BLUE        = colors.HexColor("#1B71AC")
GREEN       = colors.HexColor("#2AB573")
LIGHT_GREEN = colors.HexColor("#E8F5EE")
LIGHT_BLUE  = colors.HexColor("#EAF4FB")
WHITE       = colors.white
DARK        = colors.HexColor("#1A1A2E")
GREY        = colors.HexColor("#555555")
LIGHT_GREY  = colors.HexColor("#F2F2F2")
PAGE_BG     = colors.HexColor("#FFFFFF")

HEADER_LOGO_FILE    = "LOGO-FULL-01.png"
WATERMARK_LOGO_FILE = "LOGO-CROP.png"

SUBJECT = "Economic and Social Issues"
CHAPTER = "Economic Growth and Development"
PHONE   = "+91 9999466225"
WEBSITE = "www.anujjindal.in"

PAGE_W, PAGE_H = A4   # 595 × 842 pt
MARGIN_TOP    = 2.8 * cm   # space for header
MARGIN_BOTTOM = 1.6 * cm   # space for footer
MARGIN_SIDE   = 1.2 * cm
COL_GAP       = 0.4 * cm
COL_W         = (PAGE_W - 2 * MARGIN_SIDE - COL_GAP) / 2   # ~8.6 cm each

HEADER_H = 1.8 * cm
FOOTER_H = 0.85 * cm


# ── Logo pre-processor ─────────────────────────────────────────────────────────
def _process_header_logo(data: bytes) -> ImageReader | None:
    """
    LOGO-FULL-01.png has a BLACK background with BLUE text (#1B71AC).
    The header uses a WHITE background, so we need the logo as-is with
    black background removed (made transparent).
    Green mark → keep. Blue text → keep as blue (shows on white bg).
    Black bg → transparent.
    """
    try:
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(data)).convert("RGBA")
        arr = np.array(img, dtype=np.float32)
        R, G, B, A = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]

        out = arr.copy()
        # Black/near-black pixels → transparent
        is_black = (R < 50) & (G < 50) & (B < 50)
        out[is_black, 3] = 0  # alpha = 0 → transparent

        result = PILImage.fromarray(out.astype(np.uint8), "RGBA")
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)
    except Exception as e:
        print(f"[WARN] Header logo processing error: {e}", file=sys.stderr)
        return None


def _process_watermark(data: bytes) -> ImageReader | None:
    """Resize to 550×550 px and apply 20% opacity."""
    try:
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(data)).convert("RGBA")
        img = img.resize((550, 550), PILImage.LANCZOS)
        r, g, b, a = img.split()
        a = a.point(lambda x: int(x * 0.20))
        img.putalpha(a)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)
    except Exception as e:
        print(f"[WARN] Watermark processing error: {e}", file=sys.stderr)
        return None


def _load_file(img_dir: Path, filename: str) -> bytes | None:
    p = img_dir / filename
    if p.exists():
        return p.read_bytes()
    print(f"[WARN] Not found: {p}", file=sys.stderr)
    return None


# ── Page canvas (header / footer / watermark) ─────────────────────────────────
class _PageCanvas:
    def __init__(self, img_dir: Path):
        hdata = _load_file(img_dir, HEADER_LOGO_FILE)
        self._logo   = _process_header_logo(hdata) if hdata else None
        wmdata = _load_file(img_dir, WATERMARK_LOGO_FILE)
        self._wm     = _process_watermark(wmdata) if wmdata else None
        self._date   = date.today().strftime("%d %B %Y")

    def draw(self, cv: pdfcanvas.Canvas, doc):
        cv.saveState()
        w, h = PAGE_W, PAGE_H

        # ── Watermark behind everything ───────────────────────────────────────
        if self._wm:
            try:
                wm_pt = 8 * cm
                cv.drawImage(self._wm,
                             (w - wm_pt) / 2, (h - wm_pt) / 2,
                             width=wm_pt, height=wm_pt,
                             preserveAspectRatio=True, mask="auto")
            except Exception as e:
                print(f"[WARN] WM draw: {e}", file=sys.stderr)

        # ── Header ────────────────────────────────────────────────────────────
        # White background bar
        cv.setFillColor(WHITE)
        cv.rect(0, h - HEADER_H, w, HEADER_H, fill=1, stroke=0)

        # Bottom border line of header (thin blue)
        cv.setStrokeColor(BLUE)
        cv.setLineWidth(1.5)
        cv.line(0, h - HEADER_H, w, h - HEADER_H)

        # Logo box — white rounded rect top-left
        logo_box_w = 5.2 * cm
        logo_box_h = HEADER_H - 4
        logo_box_x = MARGIN_SIDE
        logo_box_y = h - HEADER_H + 2

        # Draw logo inside the box
        if self._logo:
            try:
                logo_h = logo_box_h * 0.78
                logo_w = logo_h * 3.8
                lx = logo_box_x + (logo_box_w - logo_w) / 2
                ly = logo_box_y + (logo_box_h - logo_h) / 2
                cv.drawImage(self._logo, lx, ly,
                             width=logo_w, height=logo_h,
                             preserveAspectRatio=True, mask="auto")
            except Exception as e:
                print(f"[WARN] Logo draw: {e}", file=sys.stderr)

        # Right side: Subject | Chapter | Date
        cv.setFont("Helvetica", 7.5)
        cv.setFillColor(GREY)
        right_text = f"{SUBJECT}  |  {CHAPTER}  |  {self._date}"
        cv.drawRightString(w - MARGIN_SIDE,
                           h - HEADER_H/2 - 3, right_text)

        # ── Footer ────────────────────────────────────────────────────────────
        # Light grey background
        cv.setFillColor(LIGHT_GREY)
        cv.rect(0, 0, w, FOOTER_H, fill=1, stroke=0)

        # Top border line of footer
        cv.setStrokeColor(colors.HexColor("#CCCCCC"))
        cv.setLineWidth(0.5)
        cv.line(0, FOOTER_H, w, FOOTER_H)

        # Phone left
        cv.setFont("Helvetica", 8)
        cv.setFillColor(GREY)
        cv.drawString(MARGIN_SIDE, FOOTER_H / 2 - 3, PHONE)

        # Website centre
        cv.drawCentredString(w / 2, FOOTER_H / 2 - 3, WEBSITE)

        # Page number — green box on right (matches reference exactly)
        pg_box_w = 1.2 * cm
        pg_box_h = FOOTER_H
        cv.setFillColor(GREEN)
        cv.rect(w - pg_box_w, 0, pg_box_w, pg_box_h, fill=1, stroke=0)
        cv.setFont("Helvetica-Bold", 9)
        cv.setFillColor(WHITE)
        cv.drawCentredString(w - pg_box_w / 2, FOOTER_H / 2 - 3,
                             str(doc.page))

        cv.restoreState()


# ── Styles ────────────────────────────────────────────────────────────────────
def _styles() -> dict:
    def s(name, **kw):
        return ParagraphStyle(name=name, **kw)

    return {
        # Section heading bar text
        "section_bar": s("section_bar",
            fontName="Helvetica-Bold", fontSize=10, leading=14,
            textColor=WHITE, spaceAfter=0),

        # Numbered item title (bold blue)
        "item_title": s("item_title",
            fontName="Helvetica-Bold", fontSize=9, leading=13,
            textColor=BLUE, spaceAfter=2, spaceBefore=6),

        # Sub-heading under item
        "sub_head": s("sub_head",
            fontName="Helvetica-Bold", fontSize=8.5, leading=12,
            textColor=DARK, spaceAfter=1, spaceBefore=3),

        # Body text
        "body": s("body",
            fontName="Helvetica", fontSize=8.5, leading=12.5,
            textColor=DARK, spaceAfter=2, alignment=TA_LEFT),

        # Bullet point
        "bullet": s("bullet",
            fontName="Helvetica", fontSize=8.5, leading=12.5,
            textColor=DARK, leftIndent=10, firstLineIndent=-8,
            spaceAfter=1.5),

        # Source line
        "source": s("source",
            fontName="Helvetica-Oblique", fontSize=7.5, leading=11,
            textColor=GREY, spaceAfter=4, spaceBefore=2),

        # Knowledge nugget title
        "nugget_head": s("nugget_head",
            fontName="Helvetica-Bold", fontSize=8.5, leading=12,
            textColor=DARK, spaceAfter=1),

        # Knowledge nugget body
        "nugget_body": s("nugget_body",
            fontName="Helvetica", fontSize=8, leading=12,
            textColor=DARK, leftIndent=10, firstLineIndent=-8,
            spaceAfter=1.5),

        # About sub-section inside nugget
        "nugget_sub": s("nugget_sub",
            fontName="Helvetica", fontSize=8, leading=11,
            textColor=DARK, spaceAfter=1),
    }


# ── Flowable helpers ──────────────────────────────────────────────────────────
def _section_bar(title: str, st: dict) -> list:
    """Full-width green section header bar — matches reference."""
    tbl = Table(
        [[Paragraph(title.upper(), st["section_bar"])]],
        colWidths=[COL_W],
        style=TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), GREEN),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ])
    )
    return [Spacer(1, 4), tbl, Spacer(1, 3)]


def _item_heading(num: str, title: str, st: dict) -> Paragraph:
    return Paragraph(f"<b>{num}. {title}</b>", st["item_title"])


def _sub(title: str, st: dict) -> Paragraph:
    return Paragraph(f"<b>{title}</b>", st["sub_head"])


def _body(text: str, st: dict) -> Paragraph:
    return Paragraph(text, st["body"])


def _bullet(text: str, st: dict) -> Paragraph:
    return Paragraph(f"• {text}", st["bullet"])


def _source(text: str, st: dict) -> Paragraph:
    return Paragraph(f"<i>Source: {text}</i>", st["source"])


def _nugget(heading: str, sub_title: str, items: list, st: dict) -> list:
    """
    Knowledge Nuggets box — matches reference exactly:
    Green top border, pencil icon + 'Knowledge Nuggets' header,
    bold sub-title, bullet points.
    """
    content = []
    # Header row: pencil icon text + "Knowledge Nuggets"
    content.append(
        Paragraph(f'✏  <font color="#2AB573"><b>Knowledge Nuggets</b></font>',
                  st["nugget_head"])
    )
    content.append(Paragraph(f"<b>{sub_title}</b>", st["sub_head"]))
    for item in items:
        content.append(Paragraph(f"• {item}", st["nugget_body"]))

    inner = Table(
        [[c] for c in content],
        colWidths=[COL_W - 16],
        style=TableStyle([
            ("TOPPADDING",    (0,0),(-1,-1), 1.5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 1.5),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ])
    )
    outer = Table(
        [[inner]],
        colWidths=[COL_W],
        style=TableStyle([
            ("BOX",           (0,0),(-1,-1), 1,   colors.HexColor("#BBBBBB")),
            ("LINEABOVE",     (0,0),(-1, 0), 3,   GREEN),
            ("BACKGROUND",    (0,0),(-1,-1), LIGHT_GREEN),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ])
    )
    return [Spacer(1, 4), outer, Spacer(1, 4)]


def _divider() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.4,
                      color=colors.HexColor("#DDDDDD"), spaceAfter=3)


def _img(img_dir: Path, fname: str, h: float = 4.5) -> list:
    p = img_dir / fname
    if p.exists():
        return [Image(str(p), width=COL_W, height=h*cm,
                      kind="proportional"), Spacer(1, 4)]
    return []


# ── Content ───────────────────────────────────────────────────────────────────
def _build_content(st: dict, img_dir: Path) -> list:
    s = []
    add  = s.append
    ext  = s.extend

    # ═══════════════════════════════════════════════════════════
    # SECTION BAR
    # ═══════════════════════════════════════════════════════════
    ext(_section_bar("Economic Growth and Development", st))

    # ───────────────────────────────────────────────────────────
    # 1. ECONOMIC GROWTH
    # ───────────────────────────────────────────────────────────
    add(_item_heading("1", "Economic Growth — Meaning and Importance", st))
    add(_body(
        "It is an increase in the level of output of goods and services that "
        "is sustained over a long period of time, measured in terms of value added.", st))
    add(_body(
        "<b>Economic growth rate</b> = (Change in GDP) / (Last Year's GDP) × 100", st))

    for pt in [
        "Refers to growth of <b>potential output</b> i.e. production at full employment.",
        "A <b>dynamic concept</b> — continuous expansion in level of output.",
        "<b>Commodity Market:</b> leads to increased output and newer, better products.",
        "<b>Factor Market:</b> improves workforce skills and produces more efficient machinery.",
        "<b>Structural Shift:</b> moves economy from rural/agricultural to urban/industrial.",
    ]:
        add(_bullet(pt, st))

    ext(_img(img_dir, "Untitled.png", 5))

    add(_sub("1.2  Importance of Economic Growth", st))
    for pt in ["Poverty alleviation",
               "Wider availability for human choices and economic activities",
               "Resolves social issues", "Improves standard of living",
               "Better technology"]:
        add(_bullet(pt, st))

    add(_sub("1.3  Factors Affecting Economic Growth", st))
    for title, desc in [
        ("Capital Formation (Investment)",
         "More capital investment → more production → higher growth."),
        ("Capital-Output Ratio",
         "Units of capital per unit of output. Lower ratio = higher efficiency."),
        ("Occupational Structure",
         "Efficient labour utilisation boosts overall productivity."),
        ("Technological Progress",
         "Enables more output from the same resources."),
    ]:
        add(_bullet(f"<b>{title}</b> — {desc}", st))

    add(_sub("1.4  Limitations of Economic Growth", st))
    for pt in [
        "<b>Inequality of Income</b> — early-stage growth worsens income distribution.",
        "<b>Pollution &amp; Negative Externalities</b> — increased output pressures the environment.",
        "<b>Loss of Non-Renewable Resources</b> — more production depletes finite resources.",
    ]:
        add(_bullet(pt, st))

    add(Spacer(1, 4))
    add(_divider())

    # ───────────────────────────────────────────────────────────
    # 2. ECONOMIC DEVELOPMENT
    # ───────────────────────────────────────────────────────────
    add(_item_heading("2", "Economic Development — Meaning and Importance", st))
    add(_body(
        "A sustained, long-term increase in economic well-being, standard of living, and "
        "overall prosperity. A <b>broader concept</b> that includes economic growth.", st))
    add(_body(
        "Encompasses improvements beyond GDP: quality of life, poverty and inequality "
        "reduction, technology, infrastructure, education, and healthcare.", st))

    add(_sub("Importance", st))
    for pt in ["Improved Quality of Life", "Poverty Reduction", "Enhanced Human Capital",
               "Increased Employment", "Stimulated Innovation",
               "Infrastructure Development", "Social Stability and Equity",
               "Environmental Sustainability", "Institutional and Political Stability"]:
        add(_bullet(pt, st))

    add(_sub("2.2  Evolution of Economic Development", st))
    add(_body("Till 1960s, used as a synonym of economic growth. Two approaches emerged:", st))
    add(_bullet("<b>Traditional Approach</b> — focused on GDP growth of 5–7% p.a.; "
                "structural shift from agrarian to industrial; trickle-down effect.", st))
    add(_bullet("<b>Modern Approach</b> — broader, multidimensional beyond GDP growth.", st))

    ext(_img(img_dir, "Untitled_1.png", 5))
    ext(_img(img_dir, "Untitled_2.png", 5))

    add(_divider())

    # ───────────────────────────────────────────────────────────
    # 3. GROWTH vs DEVELOPMENT
    # ───────────────────────────────────────────────────────────
    add(_item_heading("3", "Economic Growth vs Economic Development", st))

    cw = COL_W / 3
    tbl_data = [
        [Paragraph("<b>Basis</b>",       ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=7.5, textColor=WHITE)),
         Paragraph("<b>Growth</b>",      ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=7.5, textColor=WHITE)),
         Paragraph("<b>Development</b>", ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=7.5, textColor=WHITE))],
        [Paragraph("Meaning",     ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5)),
         Paragraph("Increase in output sustained over time.", ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5)),
         Paragraph("Quantitative AND qualitative changes.", ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5))],
        [Paragraph("Nature",      ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5)),
         Paragraph("Quantitative only.", ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5)),
         Paragraph("Both quantitative and qualitative.", ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5))],
        [Paragraph("Scope",       ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5)),
         Paragraph("Narrow.", ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5)),
         Paragraph("Broad.", ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5))],
        [Paragraph("Measurement", ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5)),
         Paragraph("GDP, GNP.", ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5)),
         Paragraph("HDI, GII, GDI.", ParagraphStyle("tc", fontName="Helvetica", fontSize=7.5))],
    ]
    comp_tbl = Table(tbl_data, colWidths=[cw]*3,
        style=TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), BLUE),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_BLUE]),
            ("BOX",           (0,0),(-1,-1), 0.5, BLUE),
            ("INNERGRID",     (0,0),(-1,-1), 0.3, colors.HexColor("#C5DCF0")),
            ("TOPPADDING",    (0,0),(-1,-1), 3),
            ("BOTTOMPADDING", (0,0),(-1,-1), 3),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("RIGHTPADDING",  (0,0),(-1,-1), 4),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ]))
    add(comp_tbl)
    add(Spacer(1, 5))
    add(_divider())

    # ───────────────────────────────────────────────────────────
    # 4. STRUCTURAL CHANGES
    # ───────────────────────────────────────────────────────────
    add(_item_heading("4", "Economic Development and Structural Changes", st))
    add(_body(
        "Pioneering work by <b>Prof. Simon Kuznets</b> (historical data). "
        "<b>Hollis Chenery</b> extended it using current data.", st))
    ext(_img(img_dir, "Untitled_3.png", 5))
    ext(_img(img_dir, "Untitled_4.png", 5))
    add(_divider())

    # ───────────────────────────────────────────────────────────
    # 5. INDICES
    # ───────────────────────────────────────────────────────────
    add(_item_heading("5", "Indices to Measure Economic Development", st))
    ext(_img(img_dir, "Untitled_5.png", 5.5))

    # 5.1 HDI
    add(_sub("5.1.1  Human Development Index (HDI)", st))
    for k, v in [
        ("Origin", "1990  |  Released by: UNDP"),
        ("Purpose", "People and capabilities — not just economic growth."),
        ("Coverage", "191 countries  |  Range: 0 to 1"),
    ]:
        add(_bullet(f"<b>{k}:</b>  {v}", st))
    ext(_img(img_dir, "Untitled_6.png", 5.5))

    # Nugget: HDI
    ext(_nugget("HDI", "Components of HDI",
        ["Long and healthy life — Life expectancy at birth",
         "Knowledge — Expected & mean years of schooling",
         "Standard of living — GNI per capita (PPP $)"], st))

    # 5.1.2 IHDI
    add(_sub("5.1.2  Inequality-adjusted HDI (IHDI)", st))
    ext(_img(img_dir, "Untitled_7.png", 4.5))
    for pt in [
        "<b>Origin:</b> 2010  |  Released by: UNDP",
        "Adds a <b>correction factor for inequality</b> within a country.",
        "HDI = averages; IHDI = distribution of achievements.",
    ]:
        add(_bullet(pt, st))

    # 5.1.3 GDI
    add(_sub("5.1.3  Gender Development Index (GDI)", st))
    ext(_img(img_dir, "Screenshot_2023-12-11_153014.png", 4.5))
    add(_bullet("<b>Origin:</b> 1990  |  Released by: UNDP", st))
    add(_bullet(
        "<b>Purpose:</b> Measure health, education, and standard of living "
        "separately for men and women.", st))

    # 5.1.4 GII
    add(_sub("5.1.4  Gender Inequality Index (GII)", st))
    ext(_img(img_dir, "Untitled_8.png", 4.5))
    for pt in [
        "<b>Origin:</b> 1990  |  Released by: UNDP",
        "Reflects gender disadvantage across reproductive health, empowerment, labour market.",
        "Range: 0 (equality) to 1 (max inequality) — lower = better.",
    ]:
        add(_bullet(pt, st))

    # Nugget: GII
    ext(_nugget("GII", "Components of GII",
        ["Health: Maternal mortality ratio, Adolescent birth rate",
         "Empowerment: Parliamentary seats, Secondary education",
         "Labour Market: Labour force participation rate"], st))

    # 5.1.5 GSNI
    add(_sub("5.1.5  Gender Social Norms Index (GSNI)", st))
    ext(_img(img_dir, "Untitled_9.png", 4.5))
    for pt in [
        "<b>Origin:</b> 2019  |  Released by: UNDP",
        "Quantifies biases against women across 4 dimensions.",
        "Coverage: 91 countries (subject to change).",
    ]:
        add(_bullet(pt, st))

    # 5.1.6 MPI
    add(_sub("5.1.6  Multidimensional Poverty Index (MPI)", st))
    ext(_img(img_dir, "Untitled_10.png", 4.5))
    ext(_img(img_dir, "Untitled_11.png", 6))
    for pt in [
        "<b>Origin:</b> 2010  |  Released by: OPHI and UNDP",
        "Shows <i>how</i> people are poor — all deprivations identified.",
        "Coverage: ~100 countries (subject to change).",
    ]:
        add(_bullet(pt, st))

    # Nugget: MPI
    ext(_nugget("MPI", "Dimensions of MPI",
        ["Health (1/3): Nutrition, Child mortality",
         "Education (1/3): Years of schooling, School attendance",
         "Living Standards (1/3): Cooking fuel, Sanitation, "
         "Drinking water, Electricity, Housing, Assets"], st))

    # 5.2 Other indices
    add(_sub("5.2  Other Indices", st))

    add(_sub("5.2.2  World Happiness Index (WHI)", st))
    ext(_img(img_dir, "Untitled_12.png", 7))
    for pt in [
        "<b>Origin:</b> 2012  |  Released by: UN SDSN",
        "7 components: Social Support, Life Expectancy, Freedom, "
        "Generosity, GDP per capita, Corruption, Dystopia.",
    ]:
        add(_bullet(pt, st))

    add(_sub("5.2.3  OECD Better Life Index", st))
    ext(_img(img_dir, "Screenshot_2023-12-11_114429.png", 7))
    for pt in [
        "11 dimensions — no single ranking; users set own weights.",
        "Dimensions: Housing, Income, Jobs, Community, Education, "
        "Environment, Governance, Health, Life Satisfaction, Safety, Work-Life Balance.",
    ]:
        add(_bullet(pt, st))

    for title, desc in [
        ("5.2.1  Genuine Progress Indicator (GPI)",
         "Alternative to GDP; accounts for income distribution, "
         "environmental degradation, household/volunteer work."),
        ("5.2.4  Physical Quality of Life Index (PQLI)",
         "Morris David Morris, 1970s. Components: Basic Literacy Rate, "
         "Life Expectancy at Age 1, Infant Mortality Rate. Scores 0–100."),
    ]:
        add(_sub(title, st))
        add(_body(desc, st))

    add(_divider())

    # ───────────────────────────────────────────────────────────
    # 6. DEVELOPED vs DEVELOPING
    # ───────────────────────────────────────────────────────────
    add(_item_heading("6", "Developed vs Developing Economies", st))
    add(_body(
        "World Bank categorises economies into <b>high income</b>, <b>middle income</b>, "
        "and <b>low income</b>.", st))

    add(_sub("6.2.1  World Bank Income Classification (2024)", st))
    cw2 = COL_W / 2
    wb_data = [
        [Paragraph("<b>Category</b>", ParagraphStyle("th2", fontName="Helvetica-Bold", fontSize=7.5, textColor=WHITE)),
         Paragraph("<b>GNI Per Capita (US$)</b>", ParagraphStyle("th2", fontName="Helvetica-Bold", fontSize=7.5, textColor=WHITE))],
        [Paragraph("Low income",           ParagraphStyle("tc2", fontName="Helvetica", fontSize=7.5)),
         Paragraph("$1,135 or less",       ParagraphStyle("tc2", fontName="Helvetica", fontSize=7.5))],
        [Paragraph("Lower middle income",  ParagraphStyle("tc2", fontName="Helvetica", fontSize=7.5)),
         Paragraph("$1,136 – $4,465",      ParagraphStyle("tc2", fontName="Helvetica", fontSize=7.5))],
        [Paragraph("Upper middle income",  ParagraphStyle("tc2", fontName="Helvetica", fontSize=7.5)),
         Paragraph("$4,466 – $13,845",     ParagraphStyle("tc2", fontName="Helvetica", fontSize=7.5))],
        [Paragraph("High income",          ParagraphStyle("tc2", fontName="Helvetica", fontSize=7.5)),
         Paragraph("$13,846 or more",      ParagraphStyle("tc2", fontName="Helvetica", fontSize=7.5))],
    ]
    wb_tbl = Table(wb_data, colWidths=[cw2]*2,
        style=TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), BLUE),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_BLUE]),
            ("BOX",           (0,0),(-1,-1), 0.5, BLUE),
            ("INNERGRID",     (0,0),(-1,-1), 0.3, colors.HexColor("#C5DCF0")),
            ("TOPPADDING",    (0,0),(-1,-1), 3),
            ("BOTTOMPADDING", (0,0),(-1,-1), 3),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ]))
    add(wb_tbl)
    add(Spacer(1, 4))

    add(_sub("6.2.2  Development-based Classification", st))
    for pt in [
        "<b>Developed (MEDC)</b> — advanced economy, strong tech infrastructure. E.g. USA.",
        "<b>Developing</b> — less industrialised, moving toward services/production. E.g. India.",
        "<b>Least Developed (LDCs)</b> — severe structural impediments. E.g. Somalia, Sudan.",
    ]:
        add(_bullet(pt, st))

    add(_sub("6.3  Common Characteristics of Developing Countries", st))
    for c in ["Low GNP Per Capita", "Scarcity of Capital",
              "Rapid population growth", "Low Productivity",
              "Technological Backwardness", "High Unemployment",
              "Low Human Wellbeing", "Wide Income Inequality",
              "High Poverty", "Agrarian Economy",
              "Low Participation in Foreign Trade"]:
        add(_bullet(c, st))

    add(_divider())

    # ───────────────────────────────────────────────────────────
    # 7. COMPOSITE DEVELOPMENT INDEX
    # ───────────────────────────────────────────────────────────
    add(_item_heading("7", "Composite Development Index", st))
    add(_body(
        "The <b>Raghuram Rajan Committee (2013)</b> proposed a <b>Composite Development "
        "Index</b> to determine underdevelopment of Indian states with "
        "<b>10 equal-weight sub-components</b>.", st))

    for i, sc in enumerate([
        "Monthly per-capita consumption expenditure", "Education", "Health",
        "Household amenities", "Poverty rate", "Female literacy",
        "Percentage of SC/ST population", "Urbanisation rate",
        "Financial inclusion", "Connectivity",
    ], 1):
        add(_bullet(f"<b>{i}.</b>  {sc}", st))

    # Final nugget
    ext(_nugget("Reminders", "Key Points to Remember",
        ["Economic Growth ⊂ Economic Development.",
         "HDI = Health + Education + Standard of Living.",
         "Lower GII = better gender equality.",
         "PQLI = first composite alternative to GDP.",
         "Raghuram Rajan Committee (2013) → Composite Development Index."], st))

    return s


# ── Document builder ──────────────────────────────────────────────────────────
def generate(output_path: str = "Economic_Growth_and_Development.pdf",
             img_dir: str | None = None) -> str:
    if img_dir is None:
        img_dir = Path(__file__).parent
    img_dir = Path(img_dir)
    print(f"[INFO] img_dir  = {img_dir}")
    print(f"[INFO] output   = {output_path}")

    page_canvas = _PageCanvas(img_dir)
    st = _styles()
    content = _build_content(st, img_dir)

    # ── Two-column page layout ────────────────────────────────────────────────
    left_frame = Frame(
        MARGIN_SIDE, MARGIN_BOTTOM,
        COL_W, PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0,
        id="left"
    )
    right_frame = Frame(
        MARGIN_SIDE + COL_W + COL_GAP, MARGIN_BOTTOM,
        COL_W, PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0,
        id="right"
    )

    two_col_template = PageTemplate(
        id="TwoCol",
        frames=[left_frame, right_frame],
        onPage=page_canvas.draw,
    )

    doc = BaseDocTemplate(
        output_path,
        pagesize=A4,
        pageTemplates=[two_col_template],
        title=f"{SUBJECT} – {CHAPTER}",
        author="Anuj Jindal",
        subject=CHAPTER,
    )

    doc.build(content)
    kb = Path(output_path).stat().st_size // 1024
    print(f"[INFO] Done ✓  {kb} KB → {output_path}")
    return output_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output",  default="Economic_Growth_and_Development.pdf")
    ap.add_argument("--img-dir", default=None)
    args = ap.parse_args()
    generate(args.output, args.img_dir)
