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


def _order_cells(is_rtl_doc, prompt_cell, answer_cell):
    """Column order for one row. RTL reads question-right, answer-left, so the
    answer cell goes in the (left) first column and the prompt in the second."""
    if is_rtl_doc:
        return [answer_cell, prompt_cell]
    return [prompt_cell, answer_cell]


def _col_widths(is_rtl_doc):
    """Prompt column narrow, answer column wide; mirrored for RTL so the prompt
    still lands on the right edge of the page."""
    return [100 * mm, 60 * mm] if is_rtl_doc else [60 * mm, 100 * mm]


def _table_visual_order(columns, grid):
    """Return the left-to-right column index order for rendering. RTL content
    reverses it so the first logical column reads on the right."""
    rtl = _is_rtl(" ".join(columns)) or any(
        _is_rtl(" ".join(str(c) for c in row)) for row in grid)
    order = list(range(len(columns)))
    return order[::-1] if rtl else order


def _table_answer_flowable(answer, styles, font_ok):
    """Render a table-type answer ({'columns': [...], 'rows': [[...], ...]}) as a
    nested reportlab Table so it appears as a real grid inside the answer cell."""
    columns = answer.get("columns", [])
    grid = answer.get("rows", [])
    if not columns:
        return _cell("(no answer)", base_style=styles["QAnswer"],
                     font_ok=font_ok)

    # For RTL content, the first logical column reads on the right, so reverse
    # the visual column order (header and every row together).
    order = _table_visual_order(columns, grid)

    header = [_cell(columns[i], base_style=styles["QPrompt"], font_ok=font_ok)
              for i in order]
    data = [header]
    for row in grid:
        cells = []
        for i in order:
            val = row[i] if i < len(row) else ""
            cells.append(_cell(val or "-", base_style=styles["QAnswer"],
                               font_ok=font_ok))
        data.append(cells)

    # Distribute the answer column width (~100mm) across the table columns.
    total = 96 * mm
    col_w = max(18 * mm, total / max(1, len(columns)))
    inner = Table(data, colWidths=[col_w] * len(columns))
    inner.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f4f8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return inner


def build_questionnaire_pdf(*, title, first_name, last_name, answers,
                            password=""):
    """answers: list of (prompt, answer_string). Returns PDF bytes.

    If ``password`` is a non-empty string, the PDF is encrypted with it as the
    open (user) password using reportlab's 128-bit standard encryption. This is
    standard PDF password protection: readers such as Preview, Acrobat, and most
    mail clients will prompt for the password. Note that PDF standard encryption
    is only moderately strong; it protects casual access, not a determined
    attacker with the file.
    """
    font_ok = _ensure_font()
    buf = BytesIO()

    encrypt = None
    password = (password or "").strip()
    if password:
        from reportlab.lib import pdfencrypt
        encrypt = pdfencrypt.StandardEncryption(
            userPassword=password, ownerPassword=password,
            canPrint=1, canModify=0, canCopy=1, canAnnotate=0, strength=128)

    title_rtl = _is_rtl(title)
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title=title, author="Client Portal", encrypt=encrypt)

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

    is_rtl_doc = _is_rtl(title) or any(_is_rtl(p) for p, _ in answers)

    rows = []
    for prompt, answer in answers:
        prompt_cell = _cell(prompt, base_style=styles["QPrompt"],
                            font_ok=font_ok)
        if isinstance(answer, dict):
            answer_cell = _table_answer_flowable(answer, styles, font_ok)
        else:
            answer = answer if answer not in (None, "") else "(no answer)"
            answer_cell = _cell(answer, base_style=styles["QAnswer"],
                                font_ok=font_ok)
        rows.append(_order_cells(is_rtl_doc, prompt_cell, answer_cell))

    if rows:
        table = Table(rows, colWidths=_col_widths(is_rtl_doc))
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
