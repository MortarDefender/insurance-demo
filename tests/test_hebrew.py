"""Tests for Hebrew / RTL support across text direction, PDF, and web pages."""
import glob
import os
import pytest

from textdir import is_rtl, direction
from pdf_report import (build_questionnaire_pdf, _order_cells, _col_widths,
                        _table_visual_order)
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


def test_rtl_puts_prompt_on_the_right():
    # LTR: prompt-left (col 0), answer-right (col 1); narrow prompt column.
    assert _order_cells(False, "PROMPT", "ANSWER") == ["PROMPT", "ANSWER"]
    assert _col_widths(False)[0] < _col_widths(False)[1]
    # RTL: answer-left (col 0), prompt-right (col 1); prompt still on the wide
    # right side of the page.
    assert _order_cells(True, "PROMPT", "ANSWER") == ["ANSWER", "PROMPT"]
    assert _col_widths(True)[0] > _col_widths(True)[1]


def test_table_columns_reverse_for_rtl_pdf():
    # English/LTR keeps source column order.
    assert _table_visual_order(["Medication", "Dose"], []) == [0, 1]
    # Hebrew/RTL reverses so the first logical column (right) reads first.
    assert _table_visual_order(["תרופה", "מינון"], []) == [1, 0]
    # Direction can also come from the cell data, not just headers.
    assert _table_visual_order(["A", "B"], [["אקמול", "500"]]) == [1, 0]


@pytest.fixture
def app_and_client(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    return app, app.test_client()


def test_hebrew_questionnaire_page_renders_rtl(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="שאלון בריאות",
        questions=[{"prompt": "מה גילך?", "type": "number", "required": False},
                   {"prompt": "מעשן?", "type": "yesno", "required": False}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="ישראל",
                            last_name="ישראלי", expiry_days=7)
    html = c.get(f"/c/{token}").get_data(as_text=True)
    assert 'dir="rtl"' in html
    assert 'lang="he"' in html  # <html> reflects Hebrew content
    assert "מה גילך?" in html  # Hebrew prompt present, UTF-8 preserved
    # Yes/No options are shown in Hebrew, but posted values stay Yes/No so the
    # email/PDF logic is language-independent.
    assert "כן" in html and "לא" in html
    assert 'value="Yes"' in html and 'value="No"' in html
    # Guest UI chrome is localized (scope #2): intro + submit button.
    assert "אנא ענו" in html  # Hebrew intro text
    assert "שליחה" in html  # Hebrew Submit button
    assert "Submit" not in html and "Please answer" not in html


def test_english_questionnaire_page_stays_ltr(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Health Review",
        questions=[{"prompt": "Age", "type": "number", "required": False},
                   {"prompt": "Smoker?", "type": "yesno", "required": False}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane",
                            last_name="Doe", expiry_days=7)
    html = c.get(f"/c/{token}").get_data(as_text=True)
    assert 'dir="ltr"' in html
    assert 'lang="en"' in html
    assert 'dir="rtl"' not in html
    assert ">Yes<" in html and ">No<" in html  # English options unchanged
    assert "כן" not in html and "לא" not in html


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
    # The client saw Hebrew but the emailed answer value is language-independent.
    body = [p for p in msg.walk()
            if p.get_content_type() == "text/plain"][0]
    assert "A: 40" in body.get_payload(decode=True).decode("utf-8")


def test_hebrew_thank_you_is_localized(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="שאלון בריאות",
        questions=[{"prompt": "מה גילך?", "type": "number", "required": False}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="ישראל",
                            last_name="ישראלי", expiry_days=7)
    html = c.post(f"/c/{token}", data={"answer_0": "40"}).get_data(as_text=True)
    assert 'lang="he"' in html
    assert "תודה, ישראל!" in html  # localized + name interpolated
    assert "קיבלנו את תשובתכם" in html
    assert "Thank you" not in html


def test_english_thank_you_unchanged(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Health Review",
        questions=[{"prompt": "Age", "type": "number", "required": False}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane",
                            last_name="Doe", expiry_days=7)
    html = c.post(f"/c/{token}", data={"answer_0": "40"}).get_data(as_text=True)
    assert "Thank you, Jane!" in html
    assert 'lang="en"' in html


def test_hebrew_document_page_is_localized(app_and_client, settings):
    app, c = app_and_client
    did = app.config["STORE"].create_document(
        display_name="טופס הסכמה", original_filename="f.pdf",
        file_bytes=b"%PDF-1.4 x")
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id=did, first_name="ישראל",
                            last_name="ישראלי", expiry_days=7)
    html = c.get(f"/c/{token}").get_data(as_text=True)
    assert '<html lang="he" dir="rtl">' in html
    assert "הורדה" in html  # download button
    assert "שליחת המסמך החתום" in html  # submit button
    assert "אנא בצעו" in html  # steps intro
    assert "Download" not in html and "Send signed document" not in html


def test_invalid_link_error_page_renders_english_default(app_and_client):
    app, c = app_and_client
    html = c.get("/c/not-a-real-token").get_data(as_text=True)
    assert "This link is invalid" in html
    # Falls back to English/LTR when we cannot know the intended language.
    assert 'lang="en"' in html


def test_i18n_helper_maps_direction_and_falls_back():
    from i18n import strings, t, lang_for
    assert lang_for("rtl") == "he"
    assert lang_for("ltr") == "en"
    # direction values are accepted directly
    assert strings("rtl")["q_submit"] == "שליחה"
    assert strings("ltr")["q_submit"] == "Submit"
    # unknown language falls back to English
    assert strings("fr")["q_submit"] == "Submit"
    # format interpolation
    assert t("he", "thank_you_heading", name="דנה") == "תודה, דנה!"
    assert t("en", "thank_you_heading", name="Dana") == "Thank you, Dana!"
    # unknown key returns the key itself rather than raising
    assert t("en", "no_such_key") == "no_such_key"
