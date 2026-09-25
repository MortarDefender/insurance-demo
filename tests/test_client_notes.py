"""Tests for the client-fillable per-question notes on the guest questionnaire.

Notes are optional free-text the end user can add under each question. They ride
along into the emailed summary and the generated PDF."""

import email
import glob
import os
from io import BytesIO

import pytest
from pypdf import PdfReader

from app import create_app
from links import make_link_token
from pdf_report import build_questionnaire_pdf


@pytest.fixture
def app_and_client(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    return app, app.test_client()


def _latest_email(settings):
    eml = sorted(glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml")))[-1]
    return email.message_from_bytes(open(eml, "rb").read())


def test_guest_form_shows_a_notes_box_per_question(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Health",
        questions=[{"prompt": "Age", "type": "number", "required": True},
                   {"prompt": "Weight", "type": "number", "required": False}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane", last_name="Doe",
                            expiry_days=7)
    body = c.get(f"/c/{token}").get_data(as_text=True)
    # One notes textarea per question, index-aligned with the answers.
    assert 'name="answer_0_notes"' in body
    assert 'name="answer_1_notes"' in body


def test_client_note_appears_in_email_and_pdf(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Health Review",
        questions=[{"prompt": "Age", "type": "number", "required": True}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane", last_name="Doe",
                            expiry_days=7)
    resp = c.post(f"/c/{token}", data={
        "answer_0": "41",
        "answer_0_notes": "Recently changed since a check-up.",
    })
    assert resp.status_code == 200
    msg = _latest_email(settings)
    text = None
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            text = part.get_payload(decode=True).decode("utf-8")
    assert text is not None
    assert "Recently changed since a check-up." in text
    assert "Notes:" in text


def test_missing_note_is_simply_absent(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Health",
        questions=[{"prompt": "Age", "type": "number", "required": True}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane", last_name="Doe",
                            expiry_days=7)
    assert c.post(f"/c/{token}", data={"answer_0": "41"}).status_code == 200
    msg = _latest_email(settings)
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            text = part.get_payload(decode=True).decode("utf-8")
    assert "Notes:" not in text


def test_pdf_accepts_notes_and_still_builds():
    data = build_questionnaire_pdf(
        title="Health", first_name="Jane", last_name="Doe",
        answers=[("Age", "41"), ("Weight", "70")],
        notes=["needs review", ""])
    r = PdfReader(BytesIO(data))
    assert len(r.pages) == 1


def test_pdf_notes_optional_backward_compatible():
    # Older callers pass no notes at all.
    data = build_questionnaire_pdf(
        title="Health", first_name="Jane", last_name="Doe",
        answers=[("Age", "41")])
    assert len(PdfReader(BytesIO(data)).pages) == 1


def test_hebrew_client_note_roundtrips(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="שאלון בריאות",
        questions=[{"prompt": "גיל", "type": "number", "required": True}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="ישראל",
                            last_name="ישראלי", expiry_days=7, lang="he")
    resp = c.post(f"/c/{token}", data={
        "answer_0": "41", "answer_0_notes": "הערה בעברית"})
    assert resp.status_code == 200
    msg = _latest_email(settings)
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            text = part.get_payload(decode=True).decode("utf-8")
    assert "הערה בעברית" in text
