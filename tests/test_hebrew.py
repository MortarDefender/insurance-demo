"""Tests for Hebrew / RTL support across text direction, PDF, and web pages."""
import glob
import os
import pytest

from textdir import is_rtl, direction
from pdf_report import build_questionnaire_pdf
from app import create_app
from links import make_link_token


HEB = "שלום"  # "hello"


def test_is_rtl_detects_hebrew_and_not_latin():
    assert is_rtl("שאלון בריאות") is True
    assert is_rtl("Health Review") is False
    assert is_rtl("") is False
    assert is_rtl(None) is False
    # mixed content counts as RTL because it contains a strong RTL char
    assert is_rtl("Age שנים") is True


def test_direction_any_rtl_wins():
    assert direction("Age", "שם", "Notes") == "rtl"
    assert direction("Age", "Name", "Notes") == "ltr"
    assert direction() == "ltr"


def _pdf_ok(data):
    return data[:5] == b"%PDF-" and b"%%EOF" in data[-2048:]


def test_hebrew_pdf_embeds_font_and_is_valid():
    data = build_questionnaire_pdf(
        title="שאלון בריאות", first_name="ישראל", last_name="ישראלי",
        answers=[("מה גילך?", "ארבעים"), ("מעשן?", "לא")])
    assert _pdf_ok(data)
    # The bundled Hebrew font must actually be embedded in the PDF.
    assert b"NotoSansHebrew" in data or b"NotoHeb" in data


def test_mixed_language_pdf_is_valid():
    data = build_questionnaire_pdf(
        title="Health / בריאות", first_name="John", last_name="Doe",
        answers=[("Age / גיל", "41"), ("Smoke?", "לא")])
    assert _pdf_ok(data)


def test_english_pdf_unaffected():
    data = build_questionnaire_pdf(
        title="Annual Health Review", first_name="Jane", last_name="Doe",
        answers=[("Age", "42")])
    assert _pdf_ok(data)


@pytest.fixture
def app_and_client(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    return app, app.test_client()


def test_hebrew_questionnaire_page_renders_rtl(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="שאלון בריאות",
        questions=[{"prompt": "מה גילך?", "type": "number", "required": False}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="ישראל",
                            last_name="ישראלי", expiry_days=7)
    html = c.get(f"/c/{token}").get_data(as_text=True)
    assert 'dir="rtl"' in html
    assert "מה גילך?" in html  # Hebrew prompt present, UTF-8 preserved


def test_english_questionnaire_page_stays_ltr(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Health Review",
        questions=[{"prompt": "Age", "type": "number", "required": False}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane",
                            last_name="Doe", expiry_days=7)
    html = c.get(f"/c/{token}").get_data(as_text=True)
    assert 'dir="ltr"' in html
    assert 'dir="rtl"' not in html


def test_hebrew_submission_emails_valid_hebrew_pdf(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="שאלון בריאות",
        questions=[{"prompt": "מה גילך?", "type": "number", "required": True}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="ישראל",
                            last_name="ישראלי", expiry_days=7)
    resp = c.post(f"/c/{token}", data={"answer_0": "40"})
    assert resp.status_code == 200
    eml = sorted(glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml")))[-1]
    import email
    msg = email.message_from_bytes(open(eml, "rb").read())
    pdfs = [p for p in msg.walk() if p.get_content_type() == "application/pdf"]
    assert len(pdfs) == 1
    assert _pdf_ok(pdfs[0].get_payload(decode=True))
