"""Tests for the questionnaire-to-PDF rendering and its delivery."""
import io
import glob
import os
import pytest

from pdf_report import build_questionnaire_pdf
from app import create_app
from links import make_link_token


def _is_pdf(data):
    return data[:5] == b"%PDF-" and b"%%EOF" in data[-1024:]


def test_build_pdf_returns_valid_pdf_bytes():
    data = build_questionnaire_pdf(
        title="Annual Health Review", first_name="Jane", last_name="Doe",
        answers=[("Age", "42"), ("Smoker?", "No"), ("Notes", "")])
    assert _is_pdf(data)
    assert len(data) > 800  # non-trivial document


def test_build_pdf_escapes_markup_and_empty_answers():
    # Angle brackets and ampersands must not break the PDF or inject markup.
    data = build_questionnaire_pdf(
        title="Form <b>", first_name="A<i>", last_name="B&C",
        answers=[("<script>", "<b>bold</b>"), ("Blank", "")])
    assert _is_pdf(data)


def test_build_pdf_handles_no_questions():
    data = build_questionnaire_pdf(
        title="Empty", first_name="A", last_name="B", answers=[])
    assert _is_pdf(data)


@pytest.fixture
def app_and_client(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    return app, app.test_client()


def test_questionnaire_submit_emails_pdf_attachment(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Annual Health Review",
        questions=[{"prompt": "Age", "type": "number", "required": True}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane",
                            last_name="Doe", expiry_days=7)
    resp = c.post(f"/c/{token}", data={"answer_0": "42"})
    assert resp.status_code == 200

    eml = sorted(glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml")))[-1]
    raw = open(eml, "rb").read()
    # The email must declare a PDF attachment...
    assert b"application/pdf" in raw
    assert b'filename="Annual Health Review - Jane Doe.pdf"' in raw
    # ...and the decoded attachment must be a real PDF carrying the answer.
    import email
    msg = email.message_from_bytes(raw)
    parts = [p for p in msg.walk()
             if p.get_content_type() == "application/pdf"]
    assert len(parts) == 1
    pdf = parts[0].get_payload(decode=True)
    assert _is_pdf(pdf)
