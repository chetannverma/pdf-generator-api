"""
generate_pdf.py — FINAL (verbatim HTML content, exact image sequence)
Two-column layout matching Design_Reference_File.pdf
Images placed exactly where they appear in the HTML source.
"""

import io, os, sys, argparse, numpy as np
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, KeepTogether
)
from reportlab.pdfgen import canvas as pdfcanvas

# ── Brand ─────────────────────────────────────────────────────────────────────
BLUE        = colors.HexColor("#1B71AC")
GREEN       = colors.HexColor("#2AB573")
LIGHT_GREEN = colors.HexColor("#E8F5EE")
LIGHT_BLUE  = colors.HexColor("#EAF4FB")
WHITE       = colors.white
DARK        = colors.HexColor("#222222")
GREY        = colors.HexColor("#555555")
LIGHT_GREY  = colors.HexColor("#F4F4F4")

HEADER_LOGO_FILE    = "LOGO-FULL-01.png"
WATERMARK_LOGO_FILE = "LOGO-CROP.png"

SUBJECT = "Economic and Social Issues"
CHAPTER = "Economic Growth and Development"
PHONE   = "+91 9999466225"
WEBSITE = "www.anujjindal.in"

PAGE_W, PAGE_H = A4
MARGIN_SIDE   = 1.1 * cm
MARGIN_TOP    = 2.6 * cm
MARGIN_BOTTOM = 1.5 * cm
COL_GAP       = 0.45 * cm
COL_W         = (PAGE_W - 2 * MARGIN_SIDE - COL_GAP) / 2
HEADER_H      = 1.75 * cm
FOOTER_H      = 0.85 * cm


# ── Image helpers ─────────────────────────────────────────────────────────────
def _load(img_dir: Path, fname: str) -> bytes | None:
    p = img_dir / fname
    return p.read_bytes() if p.exists() else None


def _prep_logo(data: bytes) -> ImageReader | None:
    """Strip black background from LOGO-FULL-01 (has black bg, blue text on white header)."""
    try:
        from PIL import Image as PIL
        img = PIL.open(io.BytesIO(data)).convert("RGBA")
        arr = np.array(img, dtype=np.uint8)
        R, G, B = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        black = (R < 50) & (G < 50) & (B < 50)
        arr[black, 3] = 0
        result = PIL.fromarray(arr, "RGBA")
        buf = io.BytesIO(); result.save(buf, "PNG"); buf.seek(0)
        return ImageReader(buf)
    except Exception as e:
        print(f"[WARN] logo: {e}", file=sys.stderr); return None


def _prep_watermark(data: bytes) -> ImageReader | None:
    """Resize to 550×550 and set 20% opacity."""
    try:
        from PIL import Image as PIL
        img = PIL.open(io.BytesIO(data)).convert("RGBA").resize((550, 550), PIL.LANCZOS)
        r, g, b, a = img.split()
        a = a.point(lambda x: int(x * 0.20))
        img.putalpha(a)
        buf = io.BytesIO(); img.save(buf, "PNG"); buf.seek(0)
        return ImageReader(buf)
    except Exception as e:
        print(f"[WARN] watermark: {e}", file=sys.stderr); return None


# ── Page canvas (header / footer / watermark) ─────────────────────────────────
class _Canvas:
    def __init__(self, img_dir: Path):
        logo_data = _load(img_dir, HEADER_LOGO_FILE)
        wm_data   = _load(img_dir, WATERMARK_LOGO_FILE)
        self._logo = _prep_logo(logo_data) if logo_data else None
        self._wm   = _prep_watermark(wm_data) if wm_data else None
        self._date = date.today().strftime("%d %B %Y")

    def __call__(self, cv: pdfcanvas.Canvas, doc):
        cv.saveState()
        w, h = PAGE_W, PAGE_H

        # Watermark (behind all content)
        if self._wm:
            try:
                s = 7.5 * cm
                cv.drawImage(self._wm, (w - s) / 2, (h - s) / 2,
                             width=s, height=s,
                             preserveAspectRatio=True, mask="auto")
            except: pass

        # ── Header — white background bar ─────────────────────────────────────
        cv.setFillColor(WHITE)
        cv.rect(0, h - HEADER_H, w, HEADER_H, fill=1, stroke=0)
        # Blue bottom border line
        cv.setStrokeColor(BLUE); cv.setLineWidth(1.5)
        cv.line(0, h - HEADER_H, w, h - HEADER_H)

        # Logo top-left on white background
        if self._logo:
            try:
                lh = HEADER_H * 0.72
                lw = lh * 4.0
                cv.drawImage(self._logo,
                             MARGIN_SIDE,
                             h - HEADER_H + (HEADER_H - lh) / 2,
                             width=lw, height=lh,
                             preserveAspectRatio=True, mask="auto")
            except: pass

        # Right side: subject | chapter | date
        cv.setFont("Helvetica", 7.5)
        cv.setFillColor(GREY)
        cv.drawRightString(w - MARGIN_SIDE,
                           h - HEADER_H / 2 - 3,
                           f"{SUBJECT}  |  {CHAPTER}  |  {self._date}")

        # ── Footer ────────────────────────────────────────────────────────────
        cv.setFillColor(LIGHT_GREY)
        cv.rect(0, 0, w, FOOTER_H, fill=1, stroke=0)
        cv.setStrokeColor(colors.HexColor("#CCCCCC")); cv.setLineWidth(0.5)
        cv.line(0, FOOTER_H, w, FOOTER_H)

        cv.setFont("Helvetica", 8); cv.setFillColor(GREY)
        cv.drawString(MARGIN_SIDE, FOOTER_H / 2 - 3, PHONE)
        cv.drawCentredString(w / 2, FOOTER_H / 2 - 3, WEBSITE)

        # Green page-number box on right (matches reference exactly)
        pgw = 1.15 * cm
        cv.setFillColor(GREEN)
        cv.rect(w - pgw, 0, pgw, FOOTER_H, fill=1, stroke=0)
        cv.setFont("Helvetica-Bold", 9); cv.setFillColor(WHITE)
        cv.drawCentredString(w - pgw / 2, FOOTER_H / 2 - 3, str(doc.page))

        cv.restoreState()


# ── Styles ────────────────────────────────────────────────────────────────────
def ST():
    def s(n, **k): return ParagraphStyle(n, **k)
    return dict(
        sec  = s("sec",  fontName="Helvetica-Bold", fontSize=9.5, leading=13,
                 textColor=WHITE),
        h1   = s("h1",   fontName="Helvetica-Bold", fontSize=9, leading=13,
                 textColor=BLUE, spaceBefore=6, spaceAfter=2),
        h2   = s("h2",   fontName="Helvetica-Bold", fontSize=8.5, leading=12,
                 textColor=DARK, spaceBefore=4, spaceAfter=1),
        h3   = s("h3",   fontName="Helvetica-Bold", fontSize=8, leading=11.5,
                 textColor=DARK, spaceBefore=3, spaceAfter=1),
        body = s("body", fontName="Helvetica", fontSize=8.5, leading=12.5,
                 textColor=DARK, spaceAfter=2),
        bul  = s("bul",  fontName="Helvetica", fontSize=8.5, leading=12.5,
                 textColor=DARK, leftIndent=10, firstLineIndent=-8, spaceAfter=1.5),
        note = s("note", fontName="Helvetica-Oblique", fontSize=7.5, leading=11,
                 textColor=GREY, spaceAfter=2),
        ngh  = s("ngh",  fontName="Helvetica-Bold", fontSize=8.5, leading=12,
                 textColor=DARK, spaceAfter=1),
        ngb  = s("ngb",  fontName="Helvetica", fontSize=8, leading=12,
                 textColor=DARK, leftIndent=10, firstLineIndent=-8, spaceAfter=1.5),
        thdr = s("thdr", fontName="Helvetica-Bold", fontSize=7.5, leading=11,
                 textColor=WHITE, alignment=TA_CENTER),
        tcl  = s("tcl",  fontName="Helvetica", fontSize=7.5, leading=11,
                 textColor=DARK),
    )


# ── Flowable builders ─────────────────────────────────────────────────────────
def sec_bar(text, st):
    t = Table([[Paragraph(text.upper(), st["sec"])]],
              colWidths=[COL_W],
              style=TableStyle([
                  ("BACKGROUND",    (0,0),(-1,-1), GREEN),
                  ("TOPPADDING",    (0,0),(-1,-1), 5),
                  ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                  ("LEFTPADDING",   (0,0),(-1,-1), 8),
                  ("RIGHTPADDING",  (0,0),(-1,-1), 8),
              ]))
    return [Spacer(1, 5), t, Spacer(1, 4)]


def H1(text, st): return Paragraph(text, st["h1"])
def H2(text, st): return Paragraph(text, st["h2"])
def H3(text, st): return Paragraph(text, st["h3"])
def P(text, st):  return Paragraph(text, st["body"])
def B(text, st):  return Paragraph(f"• {text}", st["bul"])
def NOTE(text, st): return Paragraph(text, st["note"])
def DIV(): return HRFlowable(width="100%", thickness=0.4,
                              color=colors.HexColor("#DDDDDD"),
                              spaceAfter=3, spaceBefore=3)


def nugget(title, items, st):
    rows = [Paragraph('✏  <font color="#2AB573"><b>Knowledge Nuggets</b></font>',
                      st["ngh"]),
            Paragraph(f"<b>{title}</b>", st["h3"])]
    for it in items:
        rows.append(Paragraph(f"• {it}", st["ngb"]))
    inner = Table([[r] for r in rows],
                  colWidths=[COL_W - 18],
                  style=TableStyle([
                      ("TOPPADDING",    (0,0),(-1,-1), 1.5),
                      ("BOTTOMPADDING", (0,0),(-1,-1), 1.5),
                      ("LEFTPADDING",   (0,0),(-1,-1), 0),
                      ("RIGHTPADDING",  (0,0),(-1,-1), 0),
                  ]))
    outer = Table([[inner]], colWidths=[COL_W],
                  style=TableStyle([
                      ("BOX",           (0,0),(-1,-1), 0.8, colors.HexColor("#BBBBBB")),
                      ("LINEABOVE",     (0,0),(-1, 0), 3,   GREEN),
                      ("BACKGROUND",    (0,0),(-1,-1), LIGHT_GREEN),
                      ("TOPPADDING",    (0,0),(-1,-1), 6),
                      ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                      ("LEFTPADDING",   (0,0),(-1,-1), 8),
                      ("RIGHTPADDING",  (0,0),(-1,-1), 8),
                  ]))
    return [Spacer(1, 4), outer, Spacer(1, 4)]


def img(img_dir, fname, h=4.5):
    """Embed image at exact position. Returns list of flowables."""
    p = img_dir / fname
    if p.exists():
        return [Image(str(p), width=COL_W, height=h * cm, kind="proportional"),
                Spacer(1, 4)]
    print(f"[WARN] image not found: {fname}", file=sys.stderr)
    return []


def comp_table(headers, rows, st):
    cw = COL_W / len(headers)
    data = [[Paragraph(h, st["thdr"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(c, st["tcl"]) for c in row])
    t = Table(data, colWidths=[cw] * len(headers), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_BLUE]),
        ("BOX",           (0,0),(-1,-1), 0.5, BLUE),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, colors.HexColor("#C5DCF0")),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 3),
        ("RIGHTPADDING",  (0,0),(-1,-1), 3),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))
    return [t, Spacer(1, 5)]


# ── Story — images placed at EXACT positions from HTML ───────────────────────
def build_story(st, img_dir):
    s = []
    add = s.append
    ext = s.extend

    # ═══════════════════════════════════════════════════════════════════
    # SECTION BAR
    # ═══════════════════════════════════════════════════════════════════
    ext(sec_bar("Economic Growth and Development", st))

    # ═══════════════════════════════════════════════════════════════════
    # 1.0 Economic Growth
    # ═══════════════════════════════════════════════════════════════════
    add(H1("1.0 Economic Growth", st))
    add(H2("1.1 Meaning and Importance", st))
    add(B("It is an increase in the level of output of goods and services that is sustained over a long period of time, measured in terms of value added.", st))
    add(B("Economic growth rate = (Change in GDP)/(Last Year's GDP) x 100", st))
    add(B("In economics, economic growth theory typically refers to growth of potential output i.e. production at full employment.", st))
    add(B("Process of economic growth is essentially a dynamic concept and refers to a continuous expansion in level of output.", st))

    # ── IMAGE: Untitled.png — appears here in HTML (after "dynamic concept" bullet) ──
    ext(img(img_dir, "Untitled.png", 5.5))

    add(B("Economic Growth in Commodity Market - In the commodity markets, economic growth leads to not only increased output but also to newer and, many times, better products.", st))
    add(B("Economic Growth in Factor Market - In the factor markets, economic growth brings improvements in skills of workforce and/or more efficient and/or safer types of machinery.", st))
    add(B("Economic Growth begets Structural Shift - The process of economic growth may also lead to structural shifts in an economy.", st))
    add(B("We can also say that the source of income generation in an economy shifts from one to another. This means that the economy moves away from being largely rural and agriculture-based economy to urban and industry-dominated economy.", st))

    add(H2("1.2 Importance of Economic Growth", st))
    add(B("Poverty alleviation", st))
    add(B("Wider availability for human choices and economic activities", st))
    add(B("Resolves social issues", st))
    add(B("Improves standard of living", st))
    add(B("Better technology", st))

    add(H2("1.3 Factors Affecting Economic Growth", st))
    add(B("Capital Formation (Investment) - More capital investment in an economy transforms into more production. More production means more economic growth. Hence, increasing investment in an economy also increases the growth of an economy.", st))
    add(B("Capital-Output Ratio - The term 'capital-output ratio' refers to the number of units of capital that are required in order to produce one unit of output. A lower capital-output ratio typically indicates higher efficiency in producing output with less capital.", st))
    add(B("A lower capital-output ratio can suggest higher efficiency in utilizing capital for production, which can positively impact economic growth by increasing productivity.", st))
    add(B("A lower ratio might indicate that less capital is required to generate a given level of output, potentially freeing up capital for further investment in other sectors or new technologies, which could spur growth.", st))
    add(B("Sometimes, a lower capital-output ratio might result from technological advancement or innovation that allows for more output with the same or less capital. This can contribute to sustained economic growth by fostering innovation and progress.", st))
    add(B("There should be an optimal balance between capital and output for sustainable growth. Extremely low capital-output ratios might suggest underinvestment, while extremely high ratios might indicate inefficient use of resources.", st))
    add(B("Occupational Structure - Another factor which determines economic growth process is the occupational structure of the working population. The efficient utilization of labor will further boost the overall level of productivity of the economy.", st))
    add(B("Technological Progress - Technology makes it possible to produce more from the same quantity of resources (or factors of production). This boosts the potential level of output of the economy.", st))

    add(H2("1.4 Limitations of Economic Growth", st))
    add(B("Inequality of income - The unequal distribution of income is the first limitation of economic growth. There is evidence to suggest that, at least in the initial stages of development, economic growth tends to worsen the distribution of income.", st))
    add(B("Pollution (and other negative externalities) - The drive for increased output tends to put more and more pressure on the environment and the result is increased pollution and environmental degradation.", st))
    add(B("Loss of non-renewable resources - The more we want to produce, the more resources we need to do that. This leads to the loss of non-renewable resources.", st))
    add(DIV())

    # ═══════════════════════════════════════════════════════════════════
    # 2.0 Economic Development
    # ═══════════════════════════════════════════════════════════════════
    add(H1("2.0 Economic Development", st))
    add(H2("2.1 Meaning and Importance", st))
    add(B("Economic development refers to a sustained, long-term increase in the economic well-being, standard of living, and overall prosperity of a country or region. It is a broader concept and includes Economic Growth as well because without economic growth, economic development cannot happen.", st))
    add(B("It involves various aspects beyond mere growth in GDP or income and encompasses improvements in the quality of life, reduction of poverty, inequality, and unemployment, as well as advancements in technology, infrastructure, education, healthcare, and social institutions.", st))
    add(B("Importance -", st))
    add(B("Improved Quality of Life", st))
    add(B("Poverty Reduction", st))
    add(B("Enhanced Human Capital", st))
    add(B("Increased Employment", st))
    add(B("Stimulated Innovation and Technological Advancement", st))
    add(B("Infrastructure Development", st))
    add(B("Social Stability and Equity", st))
    add(B("Environmental Sustainability", st))
    add(B("Institutional and Political Stability", st))

    add(H2("2.2 Evolution of Economic Development", st))
    add(B("Till 1960s, economic development was often used as a synonym of economic growth.", st))
    add(B("Overtime, two different approaches of measuring Economic Development evolved, which are:", st))
    add(B("Traditional Approach -", st))
    add(B("It opined that economic growth gets converted into economic development", st))
    add(B("It believed in sustained annual increase in GDP at the rate of 5 to 7 percent or more", st))
    add(B("Structural transformation of an agrarian economy into an industrial economy", st))
    add(B("Modern Approach -", st))
    add(B("It is not limited to measuring economic development vis-a-vis economic growth. It measures economic development on a broader level.", st))

    add(H2("2.3 Traditional and Modern Approaches", st))
    add(B("Traditional Approach - The traditional approach to economic development primarily focused on achieving growth in a nation's Gross Domestic Product (GDP) as the primary indicator of progress.", st))
    add(B("This approach, prevalent until the mid-20th century, emphasized industrialization, capital accumulation, and increasing output as the means to promote development.", st))
    add(B("It is assumed that the benefit of changes in GDP would trickle down to people in one form or another. This is known as the 'trickle-down effect'.", st))
    add(B("Key features of the traditional approach to economic development include:", st))

    # ── IMAGE: Untitled_1.png — appears here in HTML (after "Key features..." bullet) ──
    ext(img(img_dir, "Untitled_1.png", 5.5))

    add(B("Modern Approach - The modern approach to economic development encompasses a more comprehensive and multidimensional perspective, recognizing that economic growth alone does not guarantee overall development. This approach emphasizes a broader set of goals and strategies to achieve sustainable and inclusive development.", st))
    add(B("Some of the key aspects of the modern approach:", st))

    # ── IMAGE: Screenshot_2023-12-11_114429.png — appears here in HTML (after "modern approach" bullet) ──
    ext(img(img_dir, "Screenshot_2023-12-11_114429.png", 5.5))

    add(DIV())

    # ═══════════════════════════════════════════════════════════════════
    # 3.0 Economic Growth v/s Economic Development
    # ═══════════════════════════════════════════════════════════════════
    add(H1("3.0 Economic Growth v/s Economic Development", st))
    ext(comp_table(
        ["Basis of Distinction", "Economic Growth", "Economic Development"],
        [
            ["Meaning",
             "It is an increase in the level of output of goods and services that is sustained over a long period of time.",
             "Economic development can be referred as the quantitative and qualitative changes in the economy."],
            ["Parameters",
             "Economic growth is measured in terms of rise in GDP or market productivity.",
             "Economic development focuses on the spectrum of spheres ranging from health, education, employment, safety, environmental sustainability, social exclusion, gender empowerment, infrastructure, and other activities."],
            ["Nature",
             "It takes into account quantitative changes only.",
             "It takes into account both quantitative and qualitative aspects of improvement."],
            ["Scope",
             "The scope of economic growth is narrow.",
             "The scope of economic development is broad."],
            ["Measurement",
             "To measure the economic growth, GDP, GNP, etc. are considered.",
             "To measure the economic development HDI, Gender inequality index, gender development Index etc. are considered."],
        ], st))
    add(DIV())

    # ═══════════════════════════════════════════════════════════════════
    # 4.0 Economic Development and Structural Changes
    # ═══════════════════════════════════════════════════════════════════
    add(H1("4.0 Economic Development and Structural Changes", st))
    add(B("Econometricians have attempted to measure structural changes in economies as development proceeds.", st))
    add(B("Much of the pioneering work in this field was done by Prof. Simon Kuznets on the basis of historical data.", st))
    add(B("Hollis Chenery extended and refined the study of structural changes in an economy by using current data.", st))
    add(NOTE("📌 List of Important Structural Changes Begotten by Economic Development", st))

    # ── IMAGE: Untitled_2.png — appears here in HTML (after Hollis Chenery bullet) ──
    ext(img(img_dir, "Untitled_2.png", 5.5))

    add(DIV())

    # ═══════════════════════════════════════════════════════════════════
    # 5.0 Indices to Measure Economic Development
    # ═══════════════════════════════════════════════════════════════════
    add(H1("5.0 Indices to Measure Economic Development", st))
    add(H2("5.1 Human Development Report and Its Components", st))

    # ── IMAGE: Untitled_3.png — appears here in HTML (right after 5.1 heading) ──
    ext(img(img_dir, "Untitled_3.png", 5.5))

    # 5.1.1 HDI
    add(H3("5.1.1 Human Development Index (HDI)", st))
    add(B("Origin - 1990", st))
    add(B("Released by - United Nations Development Program", st))
    add(B("Purpose - to emphasize that people and their capabilities should be the ultimate criteria for assessing the development of a country, not economic growth alone", st))
    add(B("Components of HDI -", st))

    # ── IMAGE: Untitled_4.png — appears here in HTML (after "Components of HDI") ──
    ext(img(img_dir, "Untitled_4.png", 5.5))

    add(B("Coverage - 191 countries [subject to change]", st))
    add(B("Index value - The index value of HDI varies between 0 (the lowest human development) to 1 (highest human development).", st))

    # 5.1.2 IHDI
    add(H3("5.1.2 Inequality-adjusted Human Development Index (IHDI)", st))
    add(B("Origin - 2010", st))
    add(B("Released by - United Nations Development Program", st))
    add(B("Purpose - The Inequality-adjusted Human Development Index (IHDI) is a distinct and separate index that is related to the Human Development Index (HDI) but incorporates a correction factor for inequality within a country.", st))
    add(B("While they are related and share similarities, the IHDI and HDI serve different purposes in evaluating human development.", st))
    add(B("The HDI provides for the overall achievements of a country in health, education, and standard of living while the IHDI provides a more comprehensive assessment of human development by considering not only the average achievements but also the distribution of these achievements among the population.", st))
    add(B("Components of IHDI -", st))

    # ── IMAGE: Untitled_5.png — appears here in HTML (after "Components of IHDI") ──
    ext(img(img_dir, "Untitled_5.png", 5.5))

    add(B("Coverage - The number of countries assessed in the Inequality-adjusted Human Development Index (IHDI) is generally the same as those assessed in the Human Development Index (HDI).", st))
    add(B("However, the adjustment for inequality requires additional data, and in some cases, there might be missing or insufficient data to calculate the IHDI for all countries.", st))
    add(B("While the intention is to cover the same set of countries in both the HDI and IHDI, limitations in available data may result in differences in the final number of countries for which both indices can be accurately calculated and reported.", st))

    # 5.1.3 GDI
    add(H3("5.1.3 Gender Development Index (GDI)", st))
    add(B("Origin - 1990", st))
    add(B("Released by - United Nations Development Program", st))
    add(B("Purpose - To measure the achievements of a nation across health, education, and standard of living dimensions and its accessibility to males and females.", st))
    add(B("Health - measured by female and male life expectancy at birth;", st))
    add(B("Education - measured by female and male expected years of schooling for children and female and male mean years of schooling for adults ages 25 years and older;", st))
    add(B("Command over Economic Resources - measured by female and male estimated earned income", st))
    add(B("Components -", st))

    # ── IMAGE: Screenshot_2023-12-11_153014.png — appears here in HTML (after "Components -") ──
    ext(img(img_dir, "Screenshot_2023-12-11_153014.png", 5.5))

    add(NOTE("Note: Pay attention to male and female categories in each dimension.", st))
    add(B("Coverage - Typically, the number of countries assessed in the GDI is the same as or very similar to the number of countries assessed in the HDI because both indices are part of the same report and use the same dataset provided by the UNDP.", st))
    add(B("However, variations might occur due to data availability and quality issues, which can affect the calculation and inclusion of certain countries in either index.", st))

    # 5.1.4 GII
    add(H3("5.1.4 Gender Inequality Index (GII)", st))
    add(B("Origin - 1990", st))
    add(B("Released by - United Nations Development Report", st))
    add(B("Purpose - GII reflects gender-based disadvantage in three dimensions— reproductive health, empowerment and the labor market.", st))
    add(B("It shows the loss in potential human development due to inequality between female and male achievements in these dimensions.", st))
    add(B("It ranges from 0, where women and men fare equally, to 1, where one gender fares as poorly as possible in all measured dimensions. Hence, a lower value means a better performance of a country.", st))
    add(B("Components -", st))

    # ── IMAGE: Untitled_6.png — appears here in HTML (after "Components -") ──
    ext(img(img_dir, "Untitled_6.png", 5.5))

    add(B("Structure of the index -", st))
    add(B("Female Gender Index - It is made up of female reproductive health index, female empowerment index, and female labor market index.", st))
    add(B("Male Gender Index - It is made up of male empowerment index (male population with secondary education and male seats in parliament) and male labor market index (male labor force participation rate).", st))
    add(B("Coverage - Typically, the number of countries assessed in the GII is the same as or very similar to the number of countries assessed in the HDI because both indices are part of the same report and use the same dataset provided by the UNDP.", st))
    add(B("However, variations might occur due to data availability and quality issues, which can affect the calculation and inclusion of certain countries in either index.", st))

    # 5.1.5 GSNI
    add(H3("5.1.5 Gender Social Norms Index", st))
    add(B("Origin - 2019", st))
    add(B("Released by - United Nation Development Program", st))
    add(B("Purpose - The Gender Social Norms Index (GSNI) quantifies biases against women, capturing people's attitudes on women's roles along four key dimensions: political, educational, economic and physical integrity.", st))
    add(B("Without tackling biased gender social norms, we will not achieve gender equality or the Sustainable Development Goals. Biased gender social norms—the undervaluation of women's capabilities and rights in society—constrain women's choices and opportunities by regulating behavior and setting the boundaries of what women are expected to do and be.", st))
    add(B("Biased gender social norms are a major impediment to achieving gender equality and empowering all women and girls", st))
    add(B("Components -", st))

    # ── IMAGE: Untitled_7.png — appears here in HTML (after "Components -") ──
    ext(img(img_dir, "Untitled_7.png", 5.5))

    add(B("Coverage - 91 countries [subject to change]", st))

    # 5.1.6 MPI
    add(H3("5.1.6 Multidimensional Poverty Index", st))
    add(B("Origin - 2010", st))
    add(B("Released by - Oxford Poverty and Human Development Initiative (OPHI) and UN Development Program (UNDP)", st))
    add(B("Publication - Annual in Human Development Report", st))
    add(B("Purpose - The MPI is a high resolution lens on poverty. Knowing not just who is poor but how they are poor is essential for effective human development program and policies. It is useful because -", st))
    add(B("It shows all the deprivations", st))
    add(B("Identify the poorest people", st))
    add(B("Show which deprivation combinations are most common", st))
    add(B("Reflect the results of effective policy interventions quickly", st))
    add(B("Components -", st))

    # ── IMAGE: Untitled_8.png — appears here in HTML (after "Components -") ──
    ext(img(img_dir, "Untitled_8.png", 5.5))

    add(B("Structure of the index -", st))

    # ── IMAGE: Untitled_9.png — appears here in HTML (after "Structure of the index") ──
    ext(img(img_dir, "Untitled_9.png", 5.5))

    add(B("Coverage - Nearly 100 countries [subject to change]", st))

    # 5.2 Other Indices
    add(H2("5.2 Other Indices to Measure Economic Development", st))

    add(H3("5.2.1 Genuine Progress Indicator (GPI)", st))
    add(B("Meaning - The Genuine Progress Indicator (GPI) is an alternative metric to Gross Domestic Product (GDP) that attempts to measure economic progress, well-being, and sustainability.", st))
    add(B("It was developed as a response to the limitations of GDP as a sole measure of a country's economic performance.", st))
    add(B("GDP vs GPI - GDP measures the total monetary value of all finished goods and services produced within a country's borders in a specific time period.", st))
    add(B("However, it does not consider factors such as income distribution, environmental degradation, household work, volunteer work, and social factors, among others.", st))
    add(B("The Genuine Progress Indicator seeks to address these limitations by considering a broader range of economic, social, and environmental factors in its calculation.", st))
    add(B("Released by - There isn't a single central authority or organization responsible for releasing the GPI for all countries.", st))
    add(B("The GPI was conceptualized and developed by researchers to provide a more comprehensive measure of societal progress that goes beyond the limitations of GDP.", st))
    add(B("Several independent research institutions, non-governmental organizations (NGOs), and academic entities have been involved in calculating and publishing GPI values for specific regions, countries, or localities.", st))

    add(H3("5.2.2 World Happiness Index (WHI)", st))
    add(B("Origin - 2012", st))
    add(B("Released by - UN Sustainable Development Solutions Network", st))
    add(B("Purpose - Success of countries should be judged by the happiness of their people. Countries have also come to a consensus on how to quantifiably measure happiness.", st))
    add(B("Components -", st))

    # ── IMAGE: Untitled_10.png — appears here in HTML (after "Components -" for WHI) ──
    ext(img(img_dir, "Untitled_10.png", 6.5))

    add(H3("5.2.3 OECD Better Life Index", st))
    add(B("Purpose - The OECD Better Life Index is designed to provide a broader perspective on what constitutes a good life beyond economic indicators like Gross Domestic Product (GDP).", st))
    add(B("Components -", st))

    # ── IMAGE: Untitled_11.png — appears here in HTML (after "Components -" for OECD) ──
    ext(img(img_dir, "Untitled_11.png", 7.5))

    add(B("Ranking - The Better Life Index doesn't provide a single ranking but rather allows users to create their own personalized index by giving different weights to these 11 dimensions.", st))
    add(B("Individuals can use the Better Life Index tool available on the OECD website to customize and weigh these topics according to their personal preferences and values.", st))
    add(B("They can then compare countries' performances based on these preferences, allowing users to see how different countries fare in areas that matter most to them.", st))

    add(H3("5.2.4 The Physical Quality of Life Index (PQLI)", st))
    add(B("Origin - The Physical Quality of Life Index (PQLI) was a composite measure developed by the economist Morris David Morris in the 1970s as an attempt to assess the overall quality of life in different countries.", st))
    add(B("Components -", st))
    add(B("Basic Literacy Rate: The percentage of adults in a country who could read and write.", st))
    add(B("Life Expectancy at Age 1: The average number of years a newborn could expect to live if the prevailing mortality patterns remained the same throughout its life.", st))
    add(B("Infant Mortality Rate: The number of deaths of infants under one year old per 1,000 live births.", st))
    add(B("Score Range - The PQLI scores ranged from 0 to 100, with higher scores indicating a better overall quality of life.", st))
    add(DIV())

    # ═══════════════════════════════════════════════════════════════════
    # 6.0 Developed vs Developing Economies
    # ═══════════════════════════════════════════════════════════════════
    add(H1("6.0 Developed vs Developing Economies", st))
    add(H2("6.1 Introduction", st))
    add(B("World Bank's World Development Report categorizes economies in three categories on the basis of income, which are high income, middle income and low income economies.", st))
    add(B("Usually, high income countries are known as developed/advanced economies while low income countries are known as underdeveloped economies.", st))
    add(B("Developed or advanced economies are also characterized by high standard of living, universal and quality education, better health care facilities and high life expectancy.", st))
    add(B("Further, the underdeveloped economies showing high potential of growth in terms of their natural, physical and human resources are often referred to as developing economies.", st))
    add(B("Economists also use the terms, first world, second world and third world for the developed, socialist, industrialist countries and underdeveloped economies respectively.", st))

    add(H2("6.2 Classification of Countries on the Basis of Per Capita Income", st))
    add(H3("6.2.1 Income-based Classification", st))
    add(B("World Bank has classified economies into four categories for the current 2024 fiscal year -", st))
    ext(comp_table(
        ["Category", "GNI Per Capita Income (in US $)"],
        [
            ["Low income",          "$1,135 or less in 2022"],
            ["Low middle income",   "$1,136 and $4,465"],
            ["Upper middle income", "$4,466 and $13,845"],
            ["High income",         "$13,846 or more"],
        ], st))
    add(NOTE("Note: The above-mentioned classification is subject to change. You can check the updated classification on World Bank's website - https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups", st))

    add(H3("6.2.2 Development-based Classification", st))
    add(B("Developed country - An industrialized country (or post-industrial country), more developed country or More Economically Developed Country (MEDC) is a sovereign state that has a developed economy and advanced technological infrastructure relative to other less industrialized nations. Example - USA", st))
    add(B("Developing country - A relatively less industrialized nation which is based on primary activities but is thriving for new industrial development such as services (India) or mass production. Example - China and India", st))
    add(B("Least Developed Countries - Least Developed Countries (LDCs) are low-income countries confronting severe structural impediments to sustainable development. They are highly vulnerable to economic and environmental shocks and have low levels of human assets. Examples - Somalia, Sudan, etc.", st))

    add(H2("6.3 Common Characteristics of Developing Countries", st))
    add(B("Low GNP Per Capita", st))
    add(B("Scarcity of Capital", st))
    add(B("Rapid population growth and high dependency burden", st))
    add(B("Low Levels of Productivity", st))
    add(B("Technological Backwardness", st))
    add(B("High Levels of Unemployment", st))
    add(B("Low Human Wellbeing", st))
    add(B("Wide Income Inequality", st))
    add(B("High Poverty", st))
    add(B("Agrarian Economy", st))
    add(B("Low Participation in Foreign Trade", st))
    add(DIV())

    # ═══════════════════════════════════════════════════════════════════
    # 7.0 Composite Development Index
    # ═══════════════════════════════════════════════════════════════════
    add(H1("7.0 Composite Development Index", st))
    add(B("The Raghuram Rajan Committee submitted its report on a new Underdevelopment Index called Composite Development Index in 2013.", st))
    add(B("The committee suggested this index to determine underdevelopment of states.", st))
    add(B("The index had 10 sub-component carrying equal weightage -", st))

    # ── IMAGE: Untitled_12.png — appears here in HTML (at the very end) ──
    ext(img(img_dir, "Untitled_12.png", 9.0))

    return s


# ── Document builder ──────────────────────────────────────────────────────────
def generate(output_path="Economic_Growth_and_Development.pdf", img_dir=None):
    if img_dir is None:
        img_dir = Path(__file__).parent
    img_dir = Path(img_dir)
    print(f"[INFO] img_dir = {img_dir}")
    print(f"[INFO] output  = {output_path}")

    canvas_cb = _Canvas(img_dir)
    st        = ST()
    story     = build_story(st, img_dir)

    left  = Frame(MARGIN_SIDE,
                  MARGIN_BOTTOM,
                  COL_W,
                  PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
                  leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0, id="left")

    right = Frame(MARGIN_SIDE + COL_W + COL_GAP,
                  MARGIN_BOTTOM,
                  COL_W,
                  PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
                  leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0, id="right")

    doc = BaseDocTemplate(
        output_path,
        pagesize=A4,
        pageTemplates=[PageTemplate(id="2col",
                                    frames=[left, right],
                                    onPage=canvas_cb)],
        title=f"{SUBJECT} – {CHAPTER}",
        author="Anuj Jindal",
        subject=CHAPTER,
    )
    doc.build(story)
    kb = Path(output_path).stat().st_size // 1024
    print(f"[INFO] Done ✓  {kb} KB")
    return output_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output",  default="Economic_Growth_and_Development.pdf")
    ap.add_argument("--img-dir", default=None)
    args = ap.parse_args()
    generate(args.output, args.img_dir)
