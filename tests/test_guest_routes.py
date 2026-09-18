import io
import os
import glob
import pytest
from app import create_app
from links import make_link_token


@pytest.fixture
def app_and_client(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    return app, app.test_client()


def _q_token(settings, qid):
    return make_link_token(settings.SECRET_KEY, kind="questionnaire",
                           template_id=qid, first_name="Jane", last_name="Doe",
                           expiry_days=7)


def test_invalid_token_shows_error(app_and_client):
    app, c = app_and_client
    resp = c.get("/c/not-a-real-token")
    assert resp.status_code == 400
    assert b"link" in resp.data.lower()


def test_questionnaire_renders(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="HC", questions=[{"prompt": "Do you smoke?", "type": "yesno",
                               "required": True}])
    token = _q_token(settings, qid)
    resp = c.get(f"/c/{token}")
    assert resp.status_code == 200
    assert b"Do you smoke?" in resp.data
    assert b"Jane" in resp.data


def test_questionnaire_submit_emails_admin(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="HC", questions=[{"prompt": "Do you smoke?", "type": "yesno",
                               "required": True}])
    token = _q_token(settings, qid)
    resp = c.post(f"/c/{token}", data={"answer_0": "No"},
                  follow_redirects=True)
    assert resp.status_code == 200
    assert b"Thank you" in resp.data
    emls = glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml"))
    assert len(emls) == 1
    content = open(emls[0], encoding="utf-8").read()
    assert "HC - Jane Doe" in content
    assert "Do you smoke?" in content
    assert "No" in content


def test_questionnaire_required_field_blocks(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="HC", questions=[{"prompt": "Age", "type": "number",
                               "required": True}])
    token = _q_token(settings, qid)
    resp = c.post(f"/c/{token}", data={"answer_0": ""}, follow_redirects=True)
    assert b"required" in resp.data.lower()
    assert glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml")) == []


def test_document_flow_download_and_upload(app_and_client, settings):
    app, c = app_and_client
    did = app.config["STORE"].create_document(
        display_name="NDA", original_filename="nda.pdf",
        file_bytes=b"%PDF-1.4 fake")
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id=did, first_name="Jane", last_name="Doe",
                            expiry_days=7)
    # page renders with download link
    resp = c.get(f"/c/{token}")
    assert resp.status_code == 200
    assert b"Download" in resp.data
    # download works
    dl = c.get(f"/c/{token}/download")
    assert dl.status_code == 200
    assert dl.data == b"%PDF-1.4 fake"
    # upload signed file
    up = c.post(f"/c/{token}", data={
        "file": (io.BytesIO(b"%PDF-1.4 signed"), "signed.pdf")},
        content_type="multipart/form-data", follow_redirects=True)
    assert up.status_code == 200
    assert b"Thank you" in up.data
    emls = glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml"))
    assert len(emls) == 1
    raw = open(emls[0], "rb").read()
    import base64
    assert base64.b64encode(b"%PDF-1.4 signed").strip() in \
        raw.replace(b"\n", b"")
    # no leftover temp files
    if os.path.exists(settings.UPLOADS_TMP_DIR):
        assert os.listdir(settings.UPLOADS_TMP_DIR) == []
