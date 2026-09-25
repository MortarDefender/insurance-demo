"""Tests for the admin-side additions: question notes, template preview pages,
the advisory ID-validation endpoint, and last-modified timestamps."""

import pytest
from app import create_app


@pytest.fixture
def logged_in(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    c = app.test_client()
    c.post("/login", data={"password": "testpass"})
    return c, app


def test_questionnaire_preview_renders_and_disables_submit(logged_in):
    c, app = logged_in
    qid = app.config["STORE"].create_questionnaire(
        name="Health",
        questions=[{"prompt": "Age", "type": "number", "required": True}])
    resp = c.get(f"/admin/questionnaires/{qid}/preview")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Age" in body
    # Preview submit button must be disabled so no email is ever sent.
    assert "disabled" in body


def test_document_preview_renders(logged_in):
    c, app = logged_in
    did = app.config["STORE"].create_document(
        display_name="Consent", original_filename="c.pdf",
        file_bytes=b"%PDF-1.4 x")
    resp = c.get(f"/admin/documents/{did}/preview")
    assert resp.status_code == 200
    assert b"Consent" in resp.data


def test_preview_requires_login(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    c = app.test_client()
    qid = app.config["STORE"].create_questionnaire(
        name="Health", questions=[])
    resp = c.get(f"/admin/questionnaires/{qid}/preview",
                 follow_redirects=False)
    assert resp.status_code in (301, 302)
    assert "/login" in resp.headers["Location"]


def test_validate_id_endpoint_states(logged_in):
    c, _ = logged_in
    assert c.get("/admin/validate-id?value=123456782").get_json()["state"] \
        == "valid"
    assert c.get("/admin/validate-id?value=123456789").get_json()["state"] \
        == "invalid"
    assert c.get("/admin/validate-id?value=").get_json()["state"] == "empty"


def test_validate_id_requires_login(settings):
    app = create_app(settings)
    app.config.update(TESTING=True)
    c = app.test_client()
    resp = c.get("/admin/validate-id?value=123456782",
                 follow_redirects=False)
    assert resp.status_code in (301, 302)


def test_list_includes_updated_at(logged_in):
    c, app = logged_in
    app.config["STORE"].create_questionnaire(name="Health", questions=[])
    q = app.config["STORE"].list_questionnaires()[0]
    assert isinstance(q.get("updated_at"), float)
    # And it renders in the admin table.
    body = c.get("/admin").get_data(as_text=True)
    assert "Last modified" in body


def test_admin_list_sorted_newest_first(logged_in):
    import os
    import time
    c, app = logged_in
    store = app.config["STORE"]
    id1 = store.create_questionnaire(name="First", questions=[])
    time.sleep(0.01)
    id2 = store.create_questionnaire(name="Second", questions=[])
    # Force distinct mtimes regardless of filesystem granularity.
    now = time.time()
    os.utime(store._q_path(id1), (now - 100, now - 100))
    os.utime(store._q_path(id2), (now, now))
    names = [q["name"] for q in store.list_questionnaires()]
    assert names.index("Second") < names.index("First")
