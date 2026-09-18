"""Render questionnaire answers to a PDF in memory. No file is written to disk;
the bytes are handed straight to the mailer as an attachment."""

from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle)
from reportlab.lib import colors


def _style_sheet():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="QPrompt", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=13, textColor=colors.HexColor("#1a1a2e")))
    styles.add(ParagraphStyle(
        name="QAnswer", parent=styles["Normal"], fontName="Helvetica",
        fontSize=11, leading=15))
    styles.add(ParagraphStyle(
        name="Muted", parent=styles["Normal"], fontName="Helvetica",
        fontSize=9, leading=12, textColor=colors.HexColor("#666666")))
    return styles


def _escape(text):
    """Reportlab paragraphs accept a mini-HTML markup, so escape the client's
    text to prevent broken layout or markup injection."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def build_questionnaire_pdf(*, title, first_name, last_name, answers):
    """answers: list of (prompt, answer_string). Returns PDF bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title=title, author="Client Portal")
    styles = _style_sheet()
    story = []

    story.append(Paragraph(_escape(title), styles["Title"]))
    story.append(Paragraph(
        f"Client: {_escape(first_name)} {_escape(last_name)}",
        styles["Heading2"]))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Submitted: {stamp}", styles["Muted"]))
    story.append(Spacer(1, 8 * mm))

    rows = []
    for prompt, answer in answers:
        answer = answer if answer not in (None, "") else "(no answer)"
        rows.append([
            Paragraph(_escape(prompt), styles["QPrompt"]),
            Paragraph(_escape(answer), styles["QAnswer"]),
        ])

    if rows:
        table = Table(rows, colWidths=[60 * mm, 100 * mm])
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
