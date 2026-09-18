import pytest
from app import create_app


@pytest.fixture
def client(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    return app.test_client()


def test_admin_redirects_to_login_when_logged_out(client):
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code in (301, 302)
    assert "/login" in resp.headers["Location"]


def test_login_with_wrong_password_shows_error(client):
    resp = client.post("/login", data={"password": "wrong"},
                       follow_redirects=True)
    assert b"Incorrect password" in resp.data


def test_login_success_then_admin_accessible(client):
    resp = client.post("/login", data={"password": "testpass"},
                       follow_redirects=True)
    assert resp.status_code == 200
    resp2 = client.get("/admin")
    assert resp2.status_code == 200
    assert b"Templates" in resp2.data


def test_logout_clears_session(client):
    client.post("/login", data={"password": "testpass"})
    client.get("/logout")
    resp = client.get("/admin", follow_redirects=False)
    assert "/login" in resp.headers["Location"]


@pytest.fixture
def logged_in_client(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    c = app.test_client()
    c.post("/login", data={"password": "testpass"})
    return c, app


def test_create_questionnaire(logged_in_client):
    c, app = logged_in_client
    resp = c.post("/admin/questionnaires/new", data={
        "name": "Health Check",
        "q_prompt": ["Do you smoke?", "Age"],
        "q_type": ["yesno", "number"],
        "q_required_flag": ["1", "1"],
        "q_options": ["", ""],
    }, follow_redirects=True)
    assert resp.status_code == 200
    items = app.config["STORE"].list_questionnaires()
    assert len(items) == 1
    assert items[0]["name"] == "Health Check"
    assert len(items[0]["questions"]) == 2


def test_delete_questionnaire(logged_in_client):
    c, app = logged_in_client
    qid = app.config["STORE"].create_questionnaire(name="X", questions=[])
    c.post(f"/admin/questionnaires/{qid}/delete", follow_redirects=True)
    assert app.config["STORE"].get_questionnaire(qid) is None


def test_upload_document(logged_in_client):
    import io
    c, app = logged_in_client
    data = {
        "display_name": "NDA",
        "file": (io.BytesIO(b"%PDF-1.4 fake"), "nda.pdf"),
    }
    resp = c.post("/admin/documents/new", data=data,
                  content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    docs = app.config["STORE"].list_documents()
    assert len(docs) == 1
    assert docs[0]["display_name"] == "NDA"


def test_share_link_generated(logged_in_client):
    c, app = logged_in_client
    qid = app.config["STORE"].create_questionnaire(name="HC", questions=[])
    resp = c.post("/admin/share", data={
        "kind": "questionnaire", "template_id": qid,
        "first_name": "Jane", "last_name": "Doe",
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert "/c/" in body["link"]


def test_share_link_requires_names(logged_in_client):
    c, app = logged_in_client
    qid = app.config["STORE"].create_questionnaire(name="HC", questions=[])
    resp = c.post("/admin/share", data={
        "kind": "questionnaire", "template_id": qid,
        "first_name": "", "last_name": "",
    })
    assert resp.status_code == 400
