"""Tests for the client ID feature: it rides inside the signed link token, is
prefixed to the email subject, and encrypts the generated questionnaire PDF."""
import email
import glob
import os
from io import BytesIO

import pytest
from pypdf import PdfReader

from app import create_app
from links import make_link_token, read_link_token, _serializer
from pdf_report import build_questionnaire_pdf


def test_token_carries_client_id_roundtrip():
    sk = "secret-key-1234"
    tok = make_link_token(sk, kind="questionnaire", template_id="t1",
                          first_name="Jane", last_name="Doe",
                          client_id="A-1234", expiry_days=7)
    data = read_link_token(sk, tok, max_age_days=7)
    assert data["client_id"] == "A-1234"


def test_token_client_id_is_optional_and_stripped():
    sk = "secret-key-1234"
    tok = make_link_token(sk, kind="questionnaire", template_id="t1",
                          first_name="Jane", last_name="Doe",
                          client_id="  P-9  ", expiry_days=7)
    assert read_link_token(sk, tok, max_age_days=7)["client_id"] == "P-9"
    # Omitting client_id defaults to an empty string.
    tok2 = make_link_token(sk, kind="questionnaire", template_id="t1",
                           first_name="Jane", last_name="Doe", expiry_days=7)
    assert read_link_token(sk, tok2, max_age_days=7)["client_id"] == ""


def test_legacy_token_without_client_id_still_reads():
    sk = "secret-key-1234"
    legacy = _serializer(sk).dumps({
        "kind": "questionnaire", "template_id": "t1",
        "first_name": "Jane", "last_name": "Doe", "expiry_days": 7})
    data = read_link_token(sk, legacy, max_age_days=7)
    assert data.get("client_id") is None  # key simply absent on old tokens


def test_pdf_encrypts_with_password_and_opens():
    data = build_questionnaire_pdf(
        title="Health", first_name="Jane", last_name="Doe",
        answers=[("Age", "41")], password="A-1234")
    r = PdfReader(BytesIO(data))
    assert r.is_encrypted
    assert r.decrypt("A-1234")  # non-zero result means success
    assert len(r.pages) == 1


def test_pdf_wrong_password_fails_to_decrypt():
    data = build_questionnaire_pdf(
        title="Health", first_name="Jane", last_name="Doe",
        answers=[("Age", "41")], password="A-1234")
    r = PdfReader(BytesIO(data))
    assert r.decrypt("wrong") == 0  # 0 == failure in pypdf


def test_pdf_without_password_is_not_encrypted():
    data = build_questionnaire_pdf(
        title="Health", first_name="Jane", last_name="Doe",
        answers=[("Age", "41")], password="")
    assert PdfReader(BytesIO(data)).is_encrypted is False


@pytest.fixture
def app_and_client(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    return app, app.test_client()


def _latest_email(settings):
    eml = sorted(glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml")))[-1]
    return email.message_from_bytes(open(eml, "rb").read())


def test_questionnaire_email_subject_has_id_and_pdf_is_encrypted(
        app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Health Review",
        questions=[{"prompt": "Age", "type": "number", "required": True}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane", last_name="Doe",
                            client_id="POL-99", expiry_days=7)
    assert c.post(f"/c/{token}", data={"answer_0": "41"}).status_code == 200
    msg = _latest_email(settings)
    assert msg["Subject"] == "[POL-99] Health Review - Jane Doe"
    pdf = [p for p in msg.walk()
           if p.get_content_type() == "application/pdf"][0]
    r = PdfReader(BytesIO(pdf.get_payload(decode=True)))
    assert r.is_encrypted and r.decrypt("POL-99")


def test_questionnaire_without_id_keeps_plain_subject_and_pdf(
        app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Health Review",
        questions=[{"prompt": "Age", "type": "number", "required": True}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane", last_name="Doe",
                            expiry_days=7)
    assert c.post(f"/c/{token}", data={"answer_0": "41"}).status_code == 200
    msg = _latest_email(settings)
    assert msg["Subject"] == "Health Review - Jane Doe"
    pdf = [p for p in msg.walk()
           if p.get_content_type() == "application/pdf"][0]
    assert PdfReader(BytesIO(pdf.get_payload(decode=True))).is_encrypted is False


def test_document_email_subject_has_id(app_and_client, settings):
    app, c = app_and_client
    did = app.config["STORE"].create_document(
        display_name="Consent Form", original_filename="c.pdf",
        file_bytes=b"%PDF-1.4 x")
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id=did, first_name="Jane", last_name="Doe",
                            client_id="POL-99", expiry_days=7)
    data = {"file": (BytesIO(b"%PDF-1.4 signed"), "signed.pdf")}
    resp = c.post(f"/c/{token}", data=data,
                  content_type="multipart/form-data")
    assert resp.status_code == 200
    msg = _latest_email(settings)
    assert msg["Subject"] == "[POL-99] Consent Form - Jane Doe"


def test_admin_share_accepts_client_id(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Health Review",
        questions=[{"prompt": "Age", "type": "number", "required": True}])
    with c.session_transaction() as sess:
        sess["is_admin"] = True
    resp = c.post("/admin/share", data={
        "kind": "questionnaire", "template_id": qid,
        "first_name": "Jane", "last_name": "Doe",
        "client_id": "A-77", "expiry_days": "7"})
    assert resp.status_code == 200
    link = resp.get_json()["link"]
    token = link.rsplit("/c/", 1)[-1]
    assert read_link_token(settings.SECRET_KEY, token,
                           max_age_days=7)["client_id"] == "A-77"
