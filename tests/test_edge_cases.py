"""Edge-case and failure-mode tests for the client portal."""
import io
import os
import glob
import time
import pytest
from app import create_app
from links import make_link_token


@pytest.fixture
def app_and_client(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    return app, app.test_client()


def test_expired_link_rejected_live(app_and_client, settings):
    """A token older than the expiry window shows the friendly error."""
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(name="HC", questions=[])
    # expiry_days is embedded at read time via settings; simulate expiry by
    # setting the app's expiry window to 0 days.
    settings.LINK_EXPIRY_DAYS = 0
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="A", last_name="B",
                            expiry_days=0)
    resp = c.get(f"/c/{token}")
    assert resp.status_code == 400
    assert b"invalid or has expired" in resp.data


def test_tampered_link_rejected_live(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(name="HC", questions=[])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="A", last_name="B",
                            expiry_days=7)
    resp = c.get(f"/c/{token}XYZ")
    assert resp.status_code == 400


def test_link_to_deleted_template_shows_error(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(name="HC", questions=[])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="A", last_name="B",
                            expiry_days=7)
    app.config["STORE"].delete_questionnaire(qid)
    resp = c.get(f"/c/{token}")
    assert resp.status_code == 404
    assert b"no longer available" in resp.data


def test_choice_question_round_trip(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="Prefs",
        questions=[{"prompt": "Plan?", "type": "choice",
                    "options": ["Bronze", "Silver", "Gold"],
                    "required": True}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Sam", last_name="Lee",
                            expiry_days=7)
    page = c.get(f"/c/{token}").data.decode()
    assert "Bronze" in page and "Silver" in page and "Gold" in page
    resp = c.post(f"/c/{token}", data={"answer_0": "Gold"},
                  follow_redirects=True)
    assert b"Thank you" in resp.data
    content = open(glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml"))[0],
                   encoding="utf-8").read()
    assert "Plan?" in content and "Gold" in content


def test_guest_document_rejects_bad_extension(app_and_client, settings):
    app, c = app_and_client
    did = app.config["STORE"].create_document(
        display_name="Form", original_filename="f.pdf",
        file_bytes=b"%PDF-1.4")
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id=did, first_name="A", last_name="B",
                            expiry_days=7)
    resp = c.post(f"/c/{token}", data={
        "file": (io.BytesIO(b"nope"), "malware.exe")},
        content_type="multipart/form-data", follow_redirects=True)
    assert b"not allowed" in resp.data
    assert glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml")) == []


def test_admin_rejects_bad_document_extension(app_and_client, settings):
    app, c = app_and_client
    c.post("/login", data={"password": "testpass"})
    resp = c.post("/admin/documents/new", data={
        "display_name": "X",
        "file": (io.BytesIO(b"nope"), "bad.exe")},
        content_type="multipart/form-data", follow_redirects=True)
    assert b"not allowed" in resp.data
    assert app.config["STORE"].list_documents() == []


def test_edit_questionnaire_changes_stored(app_and_client, settings):
    app, c = app_and_client
    c.post("/login", data={"password": "testpass"})
    qid = app.config["STORE"].create_questionnaire(name="Old", questions=[])
    c.post(f"/admin/questionnaires/{qid}/edit", data={
        "name": "Renamed",
        "q_prompt": ["New Q"], "q_type": ["text"],
        "q_required_flag": ["0"], "q_options": [""],
    }, follow_redirects=True)
    q = app.config["STORE"].get_questionnaire(qid)
    assert q["name"] == "Renamed"
    assert len(q["questions"]) == 1
    assert q["questions"][0]["prompt"] == "New Q"


def test_oversized_upload_rejected(app_and_client, settings):
    app, c = app_and_client
    c.post("/login", data={"password": "testpass"})
    big = b"x" * (settings.MAX_UPLOAD_MB * 1024 * 1024 + 1024)
    resp = c.post("/admin/documents/new", data={
        "display_name": "Big",
        "file": (io.BytesIO(big), "big.pdf")},
        content_type="multipart/form-data")
    assert resp.status_code == 413


def test_guest_cannot_reach_admin(app_and_client):
    app, c = app_and_client
    resp = c.get("/admin", follow_redirects=False)
    assert "/login" in resp.headers["Location"]


def test_download_only_for_document_kind(app_and_client, settings):
    """A questionnaire token cannot be used on the document download route."""
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(name="HC", questions=[])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="A", last_name="B",
                            expiry_days=7)
    resp = c.get(f"/c/{token}/download")
    assert resp.status_code == 400


def test_questionnaire_mailer_failure_shows_retry(app_and_client, settings,
                                                  monkeypatch):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="HC", questions=[{"prompt": "Q", "type": "text",
                               "required": False}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="A", last_name="B",
                            expiry_days=7)
    import mailer as m

    def boom(*a, **k):
        raise RuntimeError("smtp down")
    monkeypatch.setattr(m, "send", boom)
    resp = c.post(f"/c/{token}", data={"answer_0": "x"})
    assert resp.status_code == 503
    assert b"try again" in resp.data.lower()


def test_document_mailer_failure_shows_retry(app_and_client, settings,
                                             monkeypatch):
    app, c = app_and_client
    did = app.config["STORE"].create_document(
        display_name="Form", original_filename="f.pdf", file_bytes=b"%PDF")
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id=did, first_name="A", last_name="B",
                            expiry_days=7)
    import mailer as m

    def boom(*a, **k):
        raise RuntimeError("smtp down")
    monkeypatch.setattr(m, "send", boom)
    resp = c.post(f"/c/{token}", data={
        "file": (io.BytesIO(b"%PDF signed"), "signed.pdf")},
        content_type="multipart/form-data")
    assert resp.status_code == 503
    assert b"try again" in resp.data.lower()


def test_client_name_cannot_inject_email_headers(app_and_client, settings):
    """A crafted name with CRLF must not create extra email headers."""
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(
        name="HC", questions=[{"prompt": "Q", "type": "text",
                               "required": False}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid,
                            first_name="Evil\r\nBcc: attacker@x.com",
                            last_name="B", expiry_days=7)
    resp = c.post(f"/c/{token}", data={"answer_0": "x"})
    # Either it is safely sent (no injected header) or fails to 503, but never
    # produces a Bcc header line in the outbox.
    for f in glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml")):
        raw = open(f, "rb").read()
        assert b"\nBcc: attacker" not in raw


def _login(c):
    return c.post("/login", data={"password": "testpass"}, follow_redirects=True)


def test_share_uses_custom_expiry(app_and_client, settings):
    """A per-client expiry entered in the Share modal is honored on the link."""
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(name="HC", questions=[])
    _login(c)
    resp = c.post("/admin/share", data={
        "kind": "questionnaire", "template_id": qid,
        "first_name": "A", "last_name": "B", "expiry_days": "30",
    })
    assert resp.status_code == 200
    from links import read_link_token
    token = resp.get_json()["link"].rsplit("/c/", 1)[1]
    data = read_link_token(settings.SECRET_KEY, token, max_age_days=1)
    assert data["expiry_days"] == 30


def test_share_defaults_expiry_when_blank(app_and_client, settings):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(name="HC", questions=[])
    settings.LINK_EXPIRY_DAYS = 7
    _login(c)
    resp = c.post("/admin/share", data={
        "kind": "questionnaire", "template_id": qid,
        "first_name": "A", "last_name": "B", "expiry_days": "",
    })
    from links import read_link_token
    token = resp.get_json()["link"].rsplit("/c/", 1)[1]
    data = read_link_token(settings.SECRET_KEY, token, max_age_days=1)
    assert data["expiry_days"] == 7


@pytest.mark.parametrize("bad", ["0", "366", "-3", "abc", "3.5"])
def test_share_rejects_bad_expiry(app_and_client, bad):
    app, c = app_and_client
    qid = app.config["STORE"].create_questionnaire(name="HC", questions=[])
    _login(c)
    resp = c.post("/admin/share", data={
        "kind": "questionnaire", "template_id": qid,
        "first_name": "A", "last_name": "B", "expiry_days": bad,
    })
    assert resp.status_code == 400
    assert "expiry" in resp.get_json()["error"].lower()
