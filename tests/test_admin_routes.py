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


def test_home_is_public_and_shows_landing(client):
    # The landing page must be reachable with no session/cookies.
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'id="about"' in body
    assert 'id="contact"' in body
    assert 'id="services"' in body
    # Links into the app are present.
    assert "/login" in body


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


def test_create_questionnaire_with_choice_saves_options(logged_in_client):
    c, app = logged_in_client
    # The builder JS rolls the individual choice inputs into a pipe-joined
    # q_options hidden field; the server splits it back into a list.
    resp = c.post("/admin/questionnaires/new", data={
        "name": "Plans",
        "q_prompt": ["Plan", "Date of birth"],
        "q_type": ["choice", "date"],
        "q_required_flag": ["1", "1"],
        "q_options": ["Basic|Premium|Gold", ""],
    }, follow_redirects=True)
    assert resp.status_code == 200
    q = [x for x in app.config["STORE"].list_questionnaires()
         if x["name"] == "Plans"][0]
    choice_q, date_q = q["questions"][0], q["questions"][1]
    assert choice_q["type"] == "choice"
    assert choice_q["options"] == ["Basic", "Premium", "Gold"]
    # Non-choice types carry no options key.
    assert date_q["type"] == "date"
    assert "options" not in date_q


def test_guest_renders_each_type_with_correct_input(logged_in_client, settings):
    from links import make_link_token
    c, app = logged_in_client
    qid = app.config["STORE"].create_questionnaire(name="Types", questions=[
        {"prompt": "DOB", "type": "date", "required": True},
        {"prompt": "Age", "type": "number", "required": True},
        {"prompt": "Plan", "type": "choice", "required": True,
         "options": ["Basic", "Premium"]},
        {"prompt": "Smoke?", "type": "yesno", "required": True},
        {"prompt": "Notes", "type": "text", "required": False},
    ])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane", last_name="Doe",
                            expiry_days=7)
    html = c.get(f"/c/{token}").get_data(as_text=True)
    assert '<input type="date" name="answer_0">' in html
    assert '<input type="number" name="answer_1">' in html
    assert '<select name="answer_2">' in html
    assert '<option value="Basic">Basic</option>' in html
    assert '<option value="Premium">Premium</option>' in html
    assert '<select name="answer_3">' in html   # yes/no
    assert '<textarea name="answer_4"' in html   # free text


def test_edit_page_shows_choice_options_prefilled(logged_in_client):
    c, app = logged_in_client
    qid = app.config["STORE"].create_questionnaire(name="P", questions=[
        {"prompt": "Plan", "type": "choice", "required": True,
         "options": ["Basic", "Premium"]}])
    html = c.get(f"/admin/questionnaires/{qid}/edit").get_data(as_text=True)
    assert 'value="Basic"' in html and 'value="Premium"' in html
    assert "Multiple choice" in html  # friendly type label


def test_choice_without_options_falls_back_to_text(logged_in_client):
    # Bypassing the client-side editor: a choice with no options must not
    # produce an empty, unanswerable dropdown.
    c, app = logged_in_client
    c.post("/admin/questionnaires/new", data={
        "name": "Bad", "q_prompt": ["Plan"], "q_type": ["choice"],
        "q_required_flag": ["1"], "q_options": [""]}, follow_redirects=True)
    q = [x for x in app.config["STORE"].list_questionnaires()
         if x["name"] == "Bad"][0]
    assert q["questions"][0]["type"] == "text"
    assert "options" not in q["questions"][0]


def test_unknown_type_falls_back_to_text(logged_in_client):
    c, app = logged_in_client
    c.post("/admin/questionnaires/new", data={
        "name": "Weird", "q_prompt": ["X"], "q_type": ["hacker"],
        "q_required_flag": ["0"], "q_options": [""]}, follow_redirects=True)
    q = [x for x in app.config["STORE"].list_questionnaires()
         if x["name"] == "Weird"][0]
    assert q["questions"][0]["type"] == "text"


def test_create_table_question_saves_columns_and_rows(logged_in_client):
    c, app = logged_in_client
    c.post("/admin/questionnaires/new", data={
        "name": "Meds",
        "q_prompt": ["List medications"],
        "q_type": ["table"],
        "q_required_flag": ["1"],
        "q_options": ["Medication|Dose|Frequency"],
        "q_rows": ["3"],
    }, follow_redirects=True)
    q = [x for x in app.config["STORE"].list_questionnaires()
         if x["name"] == "Meds"][0]
    tq = q["questions"][0]
    assert tq["type"] == "table"
    assert tq["columns"] == ["Medication", "Dose", "Frequency"]
    assert tq["rows"] == 3


def test_table_row_count_is_clamped(logged_in_client):
    c, app = logged_in_client
    c.post("/admin/questionnaires/new", data={
        "name": "Big", "q_prompt": ["T"], "q_type": ["table"],
        "q_required_flag": ["0"], "q_options": ["A|B"], "q_rows": ["999"],
    }, follow_redirects=True)
    q = [x for x in app.config["STORE"].list_questionnaires()
         if x["name"] == "Big"][0]
    assert q["questions"][0]["rows"] == 50  # clamped to max


def test_table_without_columns_falls_back_to_text(logged_in_client):
    c, app = logged_in_client
    c.post("/admin/questionnaires/new", data={
        "name": "Empty", "q_prompt": ["T"], "q_type": ["table"],
        "q_required_flag": ["0"], "q_options": [""], "q_rows": ["3"],
    }, follow_redirects=True)
    q = [x for x in app.config["STORE"].list_questionnaires()
         if x["name"] == "Empty"][0]
    assert q["questions"][0]["type"] == "text"
    assert "columns" not in q["questions"][0]


def test_guest_renders_table_grid(logged_in_client, settings):
    from links import make_link_token
    c, app = logged_in_client
    qid = app.config["STORE"].create_questionnaire(name="Grid", questions=[
        {"prompt": "Meds", "type": "table", "required": True,
         "columns": ["Medication", "Dose"], "rows": 2}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane", last_name="Doe",
                            expiry_days=7)
    html = c.get(f"/c/{token}").get_data(as_text=True)
    assert "Medication" in html and "Dose" in html
    # 2 rows x 2 columns = 4 cell inputs.
    assert html.count('name="answer_0_r') == 4


def test_table_required_needs_all_cells(logged_in_client, settings):
    from links import make_link_token
    c, app = logged_in_client
    qid = app.config["STORE"].create_questionnaire(name="Grid2", questions=[
        {"prompt": "Meds", "type": "table", "required": True,
         "columns": ["Medication", "Dose"], "rows": 2}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane", last_name="Doe",
                            expiry_days=7)
    # Only one cell filled -> blocked.
    partial = c.post(f"/c/{token}", data={"answer_0_r0_c0": "Aspirin"})
    assert "required" in partial.get_data(as_text=True).lower()
    # All four cells filled -> accepted.
    full = c.post(f"/c/{token}", data={
        "answer_0_r0_c0": "Aspirin", "answer_0_r0_c1": "100mg",
        "answer_0_r1_c0": "Metformin", "answer_0_r1_c1": "500mg"})
    assert full.status_code == 200


def test_table_answer_in_email_and_pdf(logged_in_client, settings):
    import email
    import glob
    import os
    from io import BytesIO
    from pypdf import PdfReader
    from links import make_link_token
    c, app = logged_in_client
    qid = app.config["STORE"].create_questionnaire(name="Grid3", questions=[
        {"prompt": "Meds", "type": "table", "required": True,
         "columns": ["Medication", "Dose"], "rows": 1}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane", last_name="Doe",
                            expiry_days=7)
    c.post(f"/c/{token}", data={"answer_0_r0_c0": "Aspirin",
                                "answer_0_r0_c1": "100mg"})
    eml = sorted(glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml")))[-1]
    msg = email.message_from_bytes(open(eml, "rb").read())
    body = [p for p in msg.walk()
            if p.get_content_type() == "text/plain"][0]
    text = body.get_payload(decode=True).decode("utf-8")
    assert "Medication | Dose" in text
    assert "Aspirin | 100mg" in text
    pdf = [p for p in msg.walk()
           if p.get_content_type() == "application/pdf"][0]
    assert PdfReader(BytesIO(pdf.get_payload(decode=True))).pages


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
