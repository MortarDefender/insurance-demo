"""Render questionnaire answers to a PDF in memory. No file is written to disk;
the bytes are handed straight to the mailer as an attachment.

Supports mixed English/Hebrew (and other RTL) content. A bundled Noto Sans
Hebrew font provides the Hebrew glyphs, and the bidi algorithm reorders RTL text
so it displays correctly in a left-to-right PDF renderer."""

import os
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle)
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from bidi.algorithm import get_display

from textdir import is_rtl as _is_rtl


_FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_HEBREW_FONT = "NotoHeb"
_FONT_REGISTERED = False


def _ensure_font():
    """Register the bundled Hebrew-capable font once. Falls back silently to
    Helvetica if the font file is missing (Latin text still renders)."""
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return True
    path = os.path.join(_FONTS_DIR, "NotoSansHebrew-Regular.ttf")
    if not os.path.exists(path):
        return False
    pdfmetrics.registerFont(TTFont(_HEBREW_FONT, path))
    _FONT_REGISTERED = True
    return True


def _shape(text):
    """Apply the bidi algorithm so RTL runs display in visual order. Safe for
    pure-Latin text (returned unchanged in practice)."""
    return get_display(str(text))


def _escape(text):
    """Escape reportlab's mini-HTML markup to prevent broken layout or markup
    injection from client-provided text."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _cell(text, *, base_style, font_ok):
    """Build a Paragraph whose direction and font match the text content."""
    text = str(text)
    rtl = _is_rtl(text)
    style = ParagraphStyle(
        name=base_style.name + ("_rtl" if rtl else "_ltr"),
        parent=base_style,
        alignment=TA_RIGHT if rtl else TA_LEFT,
        wordWrap="RTL" if rtl else base_style.wordWrap,
    )
    # Use the Hebrew font for any RTL text; keep the base font for Latin so the
    # design stays consistent for English forms.
    if rtl and font_ok:
        style.fontName = _HEBREW_FONT
    return Paragraph(_escape(_shape(text)), style)


def build_questionnaire_pdf(*, title, first_name, last_name, answers):
    """answers: list of (prompt, answer_string). Returns PDF bytes."""
    font_ok = _ensure_font()
    buf = BytesIO()

    title_rtl = _is_rtl(title)
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title=title, author="Client Portal")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="QPrompt", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=14, textColor=colors.HexColor("#1a1a2e")))
    styles.add(ParagraphStyle(
        name="QAnswer", parent=styles["Normal"], fontName="Helvetica",
        fontSize=11, leading=16))
    styles.add(ParagraphStyle(
        name="Muted", parent=styles["Normal"], fontName="Helvetica",
        fontSize=9, leading=12, textColor=colors.HexColor("#666666")))

    story = []
    story.append(_cell(title, base_style=styles["Title"], font_ok=font_ok))
    name = f"{first_name} {last_name}".strip()
    # Prefix label in the same direction as the client's name for readability.
    client_line = (f"{name} :לקוח" if _is_rtl(name) else f"Client: {name}")
    story.append(_cell(client_line, base_style=styles["Heading2"],
                       font_ok=font_ok))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Submitted: {stamp}", styles["Muted"]))
    story.append(Spacer(1, 8 * mm))

    rows = []
    for prompt, answer in answers:
        answer = answer if answer not in (None, "") else "(no answer)"
        rows.append([
            _cell(prompt, base_style=styles["QPrompt"], font_ok=font_ok),
            _cell(answer, base_style=styles["QAnswer"], font_ok=font_ok),
        ])

    if rows:
        # If the questionnaire is RTL, put the prompt column on the right.
        col_prompt, col_answer = 60 * mm, 100 * mm
        table = Table(rows, colWidths=[col_prompt, col_answer])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("This questionnaire has no questions.",
                               styles["Muted"]))

    doc.build(story)
    return buf.getvalue()
