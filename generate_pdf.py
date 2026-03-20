"""
generate_pdf.py  — FINAL VERSION
─────────────────────────────────
Converts Economic Growth & Development notes into a branded A4 PDF.

Brand colours : Blue #1B71AC  |  Green #2AB573
Header logo   : LOGO-FULL-01.png  (top-left of every page)
Watermark     : LOGO-CROP.png     (550x550 px resized, 20% opacity, centred every page)

All images are loaded from the SAME folder as this script (or --img-dir).
No internet required — logos are bundled with the repo.

Usage:
    python generate_pdf.py [--output myfile.pdf] [--img-dir /path/to/images]
"""

import io
import os
import sys
import argparse
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image
)
from reportlab.pdfgen import canvas as pdfcanvas

# ── Brand constants ───────────────────────────────────────────────────────────
BLUE        = colors.HexColor("#1B71AC")
GREEN       = colors.HexColor("#2AB573")
LIGHT_BLUE  = colors.HexColor("#E8F4FD")
LIGHT_GREEN = colors.HexColor("#E8F9F1")
WHITE       = colors.white
DARK_TEXT   = colors.HexColor("#1A1A2E")
GREY_TEXT   = colors.HexColor("#555555")
PAGE_BG     = colors.HexColor("#F9FAFB")

HEADER_LOGO_FILE    = "LOGO-FULL-01.png"
WATERMARK_LOGO_FILE = "LOGO-CROP.png"

SUBJECT  = "Economic and Social Issues"
CHAPTER  = "Economic Growth and Development"
PHONE    = "+91 9999466225"
WEBSITE  = "www.anujjindal.in"

PAGE_W, PAGE_H = A4
MARGIN_H = 1.5 * cm
MARGIN_V = 1.5 * cm
HEADER_H = 1.9 * cm


# ── Helpers ───────────────────────────────────────────────────────────────────
def _load_file(img_dir: Path, filename: str) -> bytes | None:
    p = img_dir / filename
    if p.exists():
        return p.read_bytes()
    print(f"[WARN] File not found: {p}", file=sys.stderr)
    return None


def _watermark_reader(data: bytes):
    """Resize to exactly 550x550 px and apply 20% opacity. Returns ImageReader."""
    try:
        from PIL import Image as PILImage
        wm = PILImage.open(io.BytesIO(data)).convert("RGBA")
        wm = wm.resize((550, 550), PILImage.LANCZOS)
        r, g, b, a = wm.split()
        a = a.point(lambda x: int(x * 0.20))
        wm.putalpha(a)
        buf = io.BytesIO()
        wm.save(buf, format="PNG")
        buf.seek(0)
        return pdfcanvas.ImageReader(buf)
    except Exception as e:
        print(f"[WARN] Watermark error: {e}", file=sys.stderr)
        return None


# ── Page decorator ────────────────────────────────────────────────────────────
class _PageDecor:
    def __init__(self, img_dir: Path):
        # Header logo
        hdata = _load_file(img_dir, HEADER_LOGO_FILE)
        self._hlogo = None
        if hdata:
            try:
                self._hlogo = pdfcanvas.ImageReader(io.BytesIO(hdata))
            except Exception as e:
                print(f"[WARN] Header logo: {e}", file=sys.stderr)

        # Watermark — pre-processed once
        wmdata = _load_file(img_dir, WATERMARK_LOGO_FILE)
        self._wm = _watermark_reader(wmdata) if wmdata else None

        self._date = date.today().strftime("%d %B %Y")

    def __call__(self, cv: pdfcanvas.Canvas, doc):
        cv.saveState()
        w, h = PAGE_W, PAGE_H

        # Background
        cv.setFillColor(PAGE_BG)
        cv.rect(0, 0, w, h, fill=1, stroke=0)

        # Watermark (behind everything)
        if self._wm:
            try:
                wm_pt = 8 * cm
                cv.drawImage(self._wm,
                             (w - wm_pt) / 2, (h - wm_pt) / 2,
                             width=wm_pt, height=wm_pt,
                             preserveAspectRatio=True, mask="auto")
            except Exception as e:
                print(f"[WARN] WM draw: {e}", file=sys.stderr)

        # Header bar
        cv.setFillColor(BLUE)
        cv.rect(0, h - HEADER_H, w, HEADER_H, fill=1, stroke=0)
        # Green accent line
        cv.setFillColor(GREEN)
        cv.rect(0, h - HEADER_H - 3, w, 3, fill=1, stroke=0)

        # Logo top-left
        if self._hlogo:
            try:
                logo_h = HEADER_H * 0.70
                logo_w = logo_h * 4.2
                cv.drawImage(self._hlogo,
                             MARGIN_H,
                             h - HEADER_H + (HEADER_H - logo_h) / 2,
                             width=logo_w, height=logo_h,
                             preserveAspectRatio=True, mask="auto")
            except Exception as e:
                print(f"[WARN] Logo draw: {e}", file=sys.stderr)

        # Right-side text: subject / chapter / date
        from reportlab.platypus import Paragraph as P
        st = _build_styles()
        p = P(f"<b>{SUBJECT}</b><br/>{CHAPTER}<br/>{self._date}",
              st["header_subject"])
        p.wrapOn(cv, 10 * cm, HEADER_H)
        p.drawOn(cv, w - MARGIN_H - 10 * cm,
                 h - HEADER_H + (HEADER_H - p.height) / 2)

        # Footer bar
        fh = 0.9 * cm
        cv.setFillColor(BLUE)
        cv.rect(0, 0, w, fh, fill=1, stroke=0)
        cv.setFillColor(GREEN)
        cv.rect(0, fh, w, 2, fill=1, stroke=0)

        # Footer text: phone LEFT | website CENTRE | page RIGHT
        cv.setFont("Helvetica", 8)
        cv.setFillColor(WHITE)
        ty = fh / 2 - 3
        cv.drawString(MARGIN_H, ty, PHONE)
        cv.drawCentredString(w / 2, ty, WEBSITE)
        cv.drawRightString(w - MARGIN_H, ty, f"Page {doc.page}")

        cv.restoreState()


# ── Styles ────────────────────────────────────────────────────────────────────
def _build_styles() -> dict:
    def s(name, **kw):
        return ParagraphStyle(name=name, **kw)
    return {
        "body":    s("body", fontName="Helvetica", fontSize=9.5, leading=15,
                     textColor=DARK_TEXT, spaceAfter=4, alignment=TA_JUSTIFY),
        "body_bullet": s("body_bullet", fontName="Helvetica", fontSize=9.5,
                         leading=15, textColor=DARK_TEXT,
                         leftIndent=14, firstLineIndent=-10, spaceAfter=3),
        "h2":      s("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
                     textColor=WHITE, spaceAfter=3),
        "h3":      s("h3", fontName="Helvetica-Bold", fontSize=10.5, leading=14,
                     textColor=BLUE, spaceAfter=3, spaceBefore=5),
        "nugget_title": s("nugget_title", fontName="Helvetica-Bold", fontSize=10,
                          leading=14, textColor=GREEN, spaceAfter=2),
        "nugget_body":  s("nugget_body", fontName="Helvetica", fontSize=9,
                          leading=13, textColor=DARK_TEXT,
                          leftIndent=10, firstLineIndent=-8, spaceAfter=2),
        "cell":    s("cell", fontName="Helvetica", fontSize=9, leading=13,
                     textColor=DARK_TEXT),
        "cell_hdr":s("cell_hdr", fontName="Helvetica-Bold", fontSize=9.5,
                     leading=13, textColor=WHITE, alignment=TA_CENTER),
        "header_subject": s("header_subject", fontName="Helvetica-Bold",
                            fontSize=7.5, leading=11,
                            textColor=WHITE, alignment=TA_RIGHT),
    }


# ── Layout helpers ────────────────────────────────────────────────────────────
def _bar(title, styles):
    tbl = Table([[Paragraph(title, styles["h2"])]],
                colWidths=[PAGE_W - 2 * MARGIN_H],
                style=TableStyle([
                    ("BACKGROUND",    (0,0),(-1,-1), BLUE),
                    ("TOPPADDING",    (0,0),(-1,-1), 6),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                    ("LEFTPADDING",   (0,0),(-1,-1), 10),
                    ("RIGHTPADDING",  (0,0),(-1,-1), 10),
                ]))
    return [Spacer(1, 8), tbl, Spacer(1, 6)]


def _sub(title, styles):
    return [Paragraph(title, styles["h3"]), Spacer(1, 2)]


def _b(text, styles):
    return Paragraph(f"•  {text}", styles["body_bullet"])


def _nugget(title, items, styles):
    content = [Paragraph(f"📌  {title}", styles["nugget_title"])]
    for item in items:
        content.append(Paragraph(f"•  {item}", styles["nugget_body"]))
    inner = Table([[c] for c in content],
                  colWidths=[PAGE_W - 2 * MARGIN_H - 24],
                  style=TableStyle([("TOPPADDING",(0,0),(-1,-1),2),
                                    ("BOTTOMPADDING",(0,0),(-1,-1),2),
                                    ("LEFTPADDING",(0,0),(-1,-1),4),
                                    ("RIGHTPADDING",(0,0),(-1,-1),4)]))
    outer = Table([[inner]], colWidths=[PAGE_W - 2 * MARGIN_H],
                  style=TableStyle([
                      ("BACKGROUND",(0,0),(-1,-1), LIGHT_GREEN),
                      ("BOX",(0,0),(-1,-1), 1.5, GREEN),
                      ("LEFTPADDING",(0,0),(-1,-1),10),
                      ("RIGHTPADDING",(0,0),(-1,-1),10),
                      ("TOPPADDING",(0,0),(-1,-1),8),
                      ("BOTTOMPADDING",(0,0),(-1,-1),8),
                  ]))
    return [Spacer(1, 6), outer, Spacer(1, 6)]


def _tbl(headers, rows, styles):
    cw = (PAGE_W - 2 * MARGIN_H) / len(headers)
    data = [[Paragraph(h, styles["cell_hdr"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(c, styles["cell"]) for c in row])
    t = Table(data, colWidths=[cw]*len(headers), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, LIGHT_BLUE]),
        ("BOX",(0,0),(-1,-1),0.8, BLUE),
        ("INNERGRID",(0,0),(-1,-1),0.4, colors.HexColor("#C5DCF0")),
        ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("RIGHTPADDING",(0,0),(-1,-1),6),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    return [Spacer(1,6), t, Spacer(1,8)]


def _img(img_dir, fname, h=5.5):
    p = img_dir / fname
    if p.exists():
        return [Image(str(p), width=PAGE_W-2*MARGIN_H-10,
                      height=h*cm, kind="proportional"), Spacer(1,6)]
    return []


# ── Story ─────────────────────────────────────────────────────────────────────
def _build_story(styles, img_dir):
    s = []
    add = s.append
    ext = s.extend

    # 1.0 Economic Growth
    ext(_bar("1.0  Economic Growth", styles))
    ext(_sub("1.1  Meaning and Importance", styles))
    add(Paragraph("Economic growth is a sustained increase in the output of goods and "
                  "services over a long period, measured in terms of value added.", styles["body"]))
    add(Paragraph("<b>Economic growth rate</b> = (Change in GDP) ÷ (Last Year's GDP) × 100",
                  styles["body"]))
    for pt in [
        "Refers to growth of <b>potential output</b> — production at full employment.",
        "A <b>dynamic concept</b> — a continuous expansion in the level of output.",
        "<b>Commodity Market:</b> leads to increased output and newer, better products.",
        "<b>Factor Market:</b> improves workforce skills and produces more efficient machinery.",
        "<b>Structural Shift:</b> moves an economy from rural/agricultural to urban/industrial.",
    ]:
        add(_b(pt, styles))
    ext(_img(img_dir, "Untitled.png", 7))

    ext(_sub("1.2  Importance of Economic Growth", styles))
    for pt in ["Poverty alleviation",
               "Wider availability for human choices and economic activities",
               "Resolves social issues", "Improves standard of living", "Better technology"]:
        add(_b(pt, styles))
    add(Spacer(1,4))

    ext(_sub("1.3  Factors Affecting Economic Growth", styles))
    for title, desc in [
        ("<b>Capital Formation</b>", "More investment → more production → higher growth."),
        ("<b>Capital-Output Ratio</b>",
         "Units of capital per unit of output. A lower ratio means higher efficiency, "
         "potentially freeing capital for further investment and innovation."),
        ("<b>Occupational Structure</b>",
         "Efficient labour utilisation boosts overall productivity."),
        ("<b>Technological Progress</b>",
         "Enables more output from the same resources, boosting potential output."),
    ]:
        add(Paragraph(f"{title} — {desc}", styles["body"]))
    add(Spacer(1,4))

    ext(_sub("1.4  Limitations of Economic Growth", styles))
    for pt in [
        "<b>Inequality of Income</b> — early-stage growth can worsen income distribution.",
        "<b>Pollution &amp; Negative Externalities</b> — increased output pressures the environment.",
        "<b>Loss of Non-Renewable Resources</b> — more production depletes finite resources.",
    ]:
        add(_b(pt, styles))

    # 2.0 Economic Development
    ext(_bar("2.0  Economic Development", styles))
    ext(_sub("2.1  Meaning and Importance", styles))
    add(Paragraph(
        "A sustained, long-term increase in economic well-being and overall prosperity. "
        "A <b>broader concept</b> that includes economic growth — without growth, "
        "development cannot happen. Encompasses improvements beyond GDP: quality of life, "
        "poverty and inequality reduction, technology, infrastructure, education, and healthcare.",
        styles["body"]))
    ext(_nugget("Importance of Economic Development", [
        "Improved Quality of Life", "Poverty Reduction", "Enhanced Human Capital",
        "Increased Employment", "Stimulated Innovation and Technological Advancement",
        "Infrastructure Development", "Social Stability and Equity",
        "Environmental Sustainability", "Institutional and Political Stability",
    ], styles))

    ext(_sub("2.2  Evolution of Economic Development", styles))
    add(Paragraph(
        "Till the 1960s used as a synonym of economic growth. Two approaches emerged:",
        styles["body"]))
    for pt in [
        "<b>Traditional Approach</b> — focused on GDP growth of 5–7% p.a.; structural "
        "transformation from agrarian to industrial; assumed trickle-down effect.",
        "<b>Modern Approach</b> — broader, multidimensional development beyond GDP.",
    ]:
        add(_b(pt, styles))
    add(Spacer(1,4))

    ext(_sub("2.3  Traditional and Modern Approaches", styles))
    ext(_img(img_dir, "Untitled_1.png", 6))
    ext(_img(img_dir, "Untitled_2.png", 6))

    # 3.0 Growth vs Development
    ext(_bar("3.0  Economic Growth vs Economic Development", styles))
    ext(_tbl(
        ["Basis", "Economic Growth", "Economic Development"],
        [
            ["Meaning", "Sustained increase in output.",
             "Quantitative AND qualitative changes in the economy."],
            ["Parameters", "Rise in GDP or market productivity.",
             "Health, education, employment, gender, environment, etc."],
            ["Nature", "Quantitative only.", "Both quantitative and qualitative."],
            ["Scope", "Narrow.", "Broad."],
            ["Measurement", "GDP, GNP, etc.", "HDI, GII, GDI, etc."],
        ], styles))

    # 4.0 Structural Changes
    ext(_bar("4.0  Economic Development and Structural Changes", styles))
    add(Paragraph(
        "Pioneering work by <b>Prof. Simon Kuznets</b> (historical data); "
        "<b>Hollis Chenery</b> extended it using current data.", styles["body"]))
    ext(_img(img_dir, "Untitled_3.png", 6))
    ext(_img(img_dir, "Untitled_4.png", 6))

    # 5.0 Indices
    ext(_bar("5.0  Indices to Measure Economic Development", styles))
    ext(_sub("5.1  Human Development Report & Its Components", styles))
    ext(_img(img_dir, "Untitled_5.png", 6))

    ext(_sub("5.1.1  Human Development Index (HDI)", styles))
    for k, v in [
        ("Origin", "1990"),
        ("Released by", "United Nations Development Programme (UNDP)"),
        ("Purpose", "People and their capabilities — not economic growth alone — "
                    "should be the ultimate criteria for assessing development."),
        ("Coverage", "191 countries (subject to change)"),
        ("Range", "0 (lowest) to 1 (highest human development)"),
    ]:
        add(Paragraph(f"<b>{k}:</b>  {v}", styles["body"]))
    ext(_img(img_dir, "Untitled_6.png", 6))

    ext(_sub("5.1.2  Inequality-adjusted HDI (IHDI)", styles))
    ext(_img(img_dir, "Untitled_7.png", 5))
    for pt in [
        "<b>Origin:</b> 2010  |  <b>Released by:</b> UNDP",
        "Adds a <b>correction factor for inequality</b> within a country.",
        "HDI measures averages; IHDI measures the <i>distribution</i> of achievements.",
    ]:
        add(_b(pt, styles))
    add(Spacer(1,4))

    ext(_sub("5.1.3  Gender Development Index (GDI)", styles))
    ext(_img(img_dir, "Screenshot_2023-12-11_153014.png", 5.5))
    for k, v in [
        ("Origin", "1990  |  Released by: UNDP"),
        ("Purpose", "Measure health, education, and standard of living separately for men and women."),
    ]:
        add(Paragraph(f"<b>{k}:</b>  {v}", styles["body"]))
    add(Spacer(1,4))

    ext(_sub("5.1.4  Gender Inequality Index (GII)", styles))
    ext(_img(img_dir, "Untitled_8.png", 5.5))
    for pt in [
        "<b>Origin:</b> 1990  |  <b>Released by:</b> UNDP",
        "Reflects gender disadvantage across <b>reproductive health</b>, "
        "<b>empowerment</b>, and <b>labour market</b>.",
        "Ranges 0 (equality) to 1 (maximum inequality) — lower = better.",
    ]:
        add(_b(pt, styles))
    add(Spacer(1,4))

    ext(_sub("5.1.5  Gender Social Norms Index (GSNI)", styles))
    ext(_img(img_dir, "Untitled_9.png", 5.5))
    for pt in [
        "<b>Origin:</b> 2019  |  <b>Released by:</b> UNDP",
        "Quantifies biases against women across four dimensions: political, "
        "educational, economic, and physical integrity.",
        "Coverage: 91 countries (subject to change).",
    ]:
        add(_b(pt, styles))
    add(Spacer(1,4))

    ext(_sub("5.1.6  Multidimensional Poverty Index (MPI)", styles))
    ext(_img(img_dir, "Untitled_10.png", 5))
    ext(_img(img_dir, "Untitled_11.png", 7))
    for pt in [
        "<b>Origin:</b> 2010  |  <b>Released by:</b> OPHI and UNDP",
        "Published annually in the Human Development Report.",
        "Shows <i>how</i> people are poor — all deprivations, identifies the poorest.",
        "Coverage: ~100 countries (subject to change).",
    ]:
        add(_b(pt, styles))
    add(Spacer(1,4))

    ext(_sub("5.2  Other Indices to Measure Economic Development", styles))
    ext(_sub("5.2.2  World Happiness Index (WHI)", styles))
    ext(_img(img_dir, "Untitled_12.png", 9))
    for pt in [
        "<b>Origin:</b> 2012  |  <b>Released by:</b> UN Sustainable Development Solutions Network",
        "Judges country success by the happiness of its people.",
        "7 components: Social Support, Healthy Life Expectancy, Freedom to make Life Choices, "
        "Generosity, GDP per capita, Perception of Corruption, Dystopia.",
    ]:
        add(_b(pt, styles))
    add(Spacer(1,4))

    ext(_sub("5.2.3  OECD Better Life Index", styles))
    ext(_img(img_dir, "Screenshot_2023-12-11_114429.png", 9))
    for pt in [
        "Broader perspective beyond GDP across 11 dimensions.",
        "No single ranking — users customise weights on the OECD website.",
        "11 dimensions: Housing, Income, Jobs, Community, Education, Environment, "
        "Governance, Health, Life Satisfaction, Safety, Work-Life Balance.",
    ]:
        add(_b(pt, styles))
    add(Spacer(1,4))

    for title, desc in [
        ("5.2.1  Genuine Progress Indicator (GPI)",
         "Alternative to GDP; accounts for income distribution, environmental degradation, "
         "household and volunteer work. Calculated by independent research institutions."),
        ("5.2.4  Physical Quality of Life Index (PQLI)",
         "Developed by Morris David Morris in the 1970s. Components: Basic Literacy Rate, "
         "Life Expectancy at Age 1, Infant Mortality Rate. Scores 0–100 (higher = better)."),
    ]:
        add(Paragraph(f"<b>{title}:</b>  {desc}", styles["body"]))
        add(Spacer(1,3))

    # 6.0 Developed vs Developing
    ext(_bar("6.0  Developed vs Developing Economies", styles))
    ext(_sub("6.1  Introduction", styles))
    add(Paragraph(
        "World Bank categorises economies into <b>high income</b>, <b>middle income</b>, "
        "and <b>low income</b>. High income = developed; low income = underdeveloped. "
        "Developing economies show high growth potential.", styles["body"]))

    ext(_sub("6.2.1  Income-based Classification (World Bank 2024)", styles))
    ext(_tbl(
        ["Category", "GNI Per Capita (US $)"],
        [
            ["Low income", "$1,135 or less"],
            ["Lower middle income", "$1,136 – $4,465"],
            ["Upper middle income", "$4,466 – $13,845"],
            ["High income", "$13,846 or more"],
        ], styles))

    ext(_sub("6.2.2  Development-based Classification", styles))
    for pt in [
        "<b>Developed (MEDC)</b> — advanced economy with strong tech infrastructure. E.g. USA.",
        "<b>Developing</b> — less industrialised, moving toward services/production. E.g. India, China.",
        "<b>Least Developed (LDCs)</b> — severe structural impediments. E.g. Somalia, Sudan.",
    ]:
        add(_b(pt, styles))
    add(Spacer(1,4))

    ext(_sub("6.3  Common Characteristics of Developing Countries", styles))
    for c in ["Low GNP Per Capita", "Scarcity of Capital",
              "Rapid population growth and high dependency burden",
              "Low Levels of Productivity", "Technological Backwardness",
              "High Levels of Unemployment", "Low Human Wellbeing",
              "Wide Income Inequality", "High Poverty",
              "Agrarian Economy", "Low Participation in Foreign Trade"]:
        add(_b(c, styles))

    # 7.0 Composite Development Index
    ext(_bar("7.0  Composite Development Index", styles))
    add(Paragraph(
        "The <b>Raghuram Rajan Committee (2013)</b> proposed a <b>Composite Development "
        "Index</b> to determine underdevelopment of Indian states with "
        "<b>10 equal-weight sub-components</b>:", styles["body"]))
    for i, sc in enumerate([
        "Monthly per-capita consumption expenditure", "Education", "Health",
        "Household amenities", "Poverty rate", "Female literacy",
        "Percentage of SC/ST population", "Urbanisation rate",
        "Financial inclusion", "Connectivity",
    ], 1):
        add(Paragraph(f"  {i}.  {sc}", styles["body_bullet"]))

    ext(_nugget("Key Reminders", [
        "Economic Growth is a subset of Economic Development.",
        "HDI = Health + Education + Standard of Living.",
        "A lower GII value indicates better gender equality.",
        "PQLI was the first composite alternative to GDP.",
        "Raghuram Rajan Committee (2013) → Composite Development Index for Indian states.",
    ], styles))

    add(Spacer(1,12))
    add(HRFlowable(width="100%", thickness=1.5, color=GREEN))
    add(Spacer(1,4))
    add(Paragraph(
        f"<i>Subject: {SUBJECT}  |  Chapter: {CHAPTER}</i>",
        ParagraphStyle("end_note", fontName="Helvetica-Oblique",
                       fontSize=8, textColor=GREY_TEXT, alignment=TA_CENTER)))
    return s


# ── Entry-point ───────────────────────────────────────────────────────────────
def generate(output_path: str = "Economic_Growth_and_Development.pdf",
             img_dir: str | None = None) -> str:
    if img_dir is None:
        img_dir = Path(__file__).parent
    img_dir = Path(img_dir)
    print(f"[INFO] img_dir  = {img_dir}")
    print(f"[INFO] output   = {output_path}")

    styles = _build_styles()
    decor  = _PageDecor(img_dir)
    story  = _build_story(styles, img_dir)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN_H, rightMargin=MARGIN_H,
        topMargin=MARGIN_V + 2.1 * cm,
        bottomMargin=MARGIN_V + 1.0 * cm,
        title=f"{SUBJECT} – {CHAPTER}",
        author="Anuj Jindal", subject=CHAPTER,
    )
    doc.build(story, onFirstPage=decor, onLaterPages=decor)
    kb = Path(output_path).stat().st_size // 1024
    print(f"[INFO] Done ✓  {kb} KB")
    return output_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output",  default="Economic_Growth_and_Development.pdf")
    ap.add_argument("--img-dir", default=None)
    args = ap.parse_args()
    generate(args.output, args.img_dir)
