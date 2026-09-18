"""Tests for the admin language toggle and language-carrying share links."""
import pytest

from app import create_app
from links import read_link_token


@pytest.fixture
def logged_in(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    c = app.test_client()
    c.post("/login", data={"password": "testpass"})
    return c, app


def test_admin_defaults_to_english(logged_in):
    c, app = logged_in
    html = c.get("/admin").get_data(as_text=True)
    assert '<html lang="en" dir="ltr">' in html
    assert "Templates" in html
    assert "lang-toggle" in html  # toggle visible when logged in


def test_toggle_switches_admin_to_hebrew_rtl(logged_in):
    c, app = logged_in
    c.get("/admin/language/he")
    html = c.get("/admin").get_data(as_text=True)
    assert '<html lang="he" dir="rtl">' in html
    assert "תבניות" in html   # "Templates"
    assert "שיתוף" in html    # "Share"


def test_invalid_language_falls_back_to_english(logged_in):
    c, app = logged_in
    c.get("/admin/language/fr")
    html = c.get("/admin").get_data(as_text=True)
    assert '<html lang="en" dir="ltr">' in html


def test_share_while_hebrew_embeds_lang_and_forces_guest(logged_in, settings):
    c, app = logged_in
    qid = app.config["STORE"].create_questionnaire(
        name="Health Review",  # deliberately English content
        questions=[{"prompt": "Age", "type": "number", "required": True}])
    c.get("/admin/language/he")
    resp = c.post("/admin/share", data={
        "kind": "questionnaire", "template_id": qid,
        "first_name": "Jane", "last_name": "Doe", "expiry_days": "7"})
    token = resp.get_json()["link"].rsplit("/c/", 1)[-1]
    data = read_link_token(settings.SECRET_KEY, token, max_age_days=7)
    assert data["lang"] == "he"
    # Guest page is Hebrew/RTL despite English content, because the link forces it.
    html = c.get(f"/c/{token}").get_data(as_text=True)
    assert '<html lang="he" dir="rtl">' in html
    assert "שליחה" in html   # Hebrew submit button


def test_share_while_english_embeds_en_and_guest_ltr(logged_in, settings):
    c, app = logged_in
    qid = app.config["STORE"].create_questionnaire(
        name="Health Review",
        questions=[{"prompt": "Age", "type": "number", "required": True}])
    # default is English
    resp = c.post("/admin/share", data={
        "kind": "questionnaire", "template_id": qid,
        "first_name": "Jane", "last_name": "Doe", "expiry_days": "7"})
    token = resp.get_json()["link"].rsplit("/c/", 1)[-1]
    data = read_link_token(settings.SECRET_KEY, token, max_age_days=7)
    assert data["lang"] == "en"
    html = c.get(f"/c/{token}").get_data(as_text=True)
    assert '<html lang="en" dir="ltr">' in html


def test_legacy_link_without_lang_uses_content_detection(logged_in, settings):
    from links import make_link_token
    c, app = logged_in
    # A Hebrew-content questionnaire, link minted without a forced language.
    qid = app.config["STORE"].create_questionnaire(
        name="שאלון בריאות",
        questions=[{"prompt": "מה גילך?", "type": "number", "required": True}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="ישראל",
                            last_name="ישראלי", expiry_days=7)  # no lang
    html = c.get(f"/c/{token}").get_data(as_text=True)
    # Falls back to detecting direction from the Hebrew content.
    assert '<html lang="he" dir="rtl">' in html
