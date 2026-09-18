# Client Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first Flask web app where an admin manages questionnaire and document templates and generates unique per-client links, and clients complete tasks whose results are emailed to the admin without any client data being stored.

**Architecture:** A single Flask app serves a password-protected admin area and a public guest area. Templates are stored as files on disk. Per-client identity is encoded inside a signed, expiring token (`itsdangerous`), so no client record is ever persisted. A mailer module writes emails to a local `outbox/` folder now and can switch to real SMTP by config later. Uploaded signed files are deleted immediately after a successful send.

**Tech Stack:** Python 3.14 (in `.venv`), Flask 3.1.x, Jinja2, itsdangerous, stdlib `smtplib`/`email`, pytest for tests.

Spec: `docs/superpowers/specs/2026-09-18-client-portal-design.md`

---

## File Structure

```
p/
  app.py                 # Flask app factory + all routes
  config.py              # local secrets/settings (git-ignored, created from example)
  config.example.py      # committed template of config.py
  auth.py                # login_required decorator + password check
  links.py               # sign/verify per-client tokens (itsdangerous)
  store.py               # read/write/delete templates on disk
  mailer.py              # send(): outbox mode now, smtp later
  templates_store/
    questionnaires/      # <id>.json
    documents/           # <id>.<ext> + <id>.json sidecar
  outbox/                # simulated sent emails (git-ignored)
  uploads_tmp/           # transient uploads, cleared after send (git-ignored)
  templates/             # Jinja2 HTML
    base.html
    login.html
    admin_list.html
    questionnaire_builder.html
    document_upload.html
    guest_questionnaire.html
    guest_document.html
    thank_you.html
    error.html
  static/
    style.css
  tests/
    conftest.py
    test_links.py
    test_store.py
    test_mailer.py
    test_auth.py
    test_admin_routes.py
    test_guest_routes.py
  requirements.txt
```

**Responsibilities:**
- `links.py`, `store.py`, `mailer.py`, `auth.py` are pure-ish modules, unit-tested in isolation.
- `app.py` wires them into routes, tested with Flask's test client.
- Config values are injected so tests never depend on the real `config.py`.

---

## Task 0: Project scaffolding and test harness

**Files:**
- Create: `requirements.txt`
- Create: `config.example.py`
- Create: `config.py` (git-ignored; created locally for running/tests)
- Create: `tests/conftest.py`
- Create: `pytest.ini`

- [ ] **Step 1: Install pytest into the venv**

Run:
```bash
cd /Users/tamir-sror/Documents/development/projects/p
. .venv/bin/activate
pip install pytest
```
Expected: pytest installs successfully.

- [ ] **Step 2: Write `requirements.txt`**

```
Flask>=3.1,<4
pytest>=8
```

- [ ] **Step 3: Write `config.example.py`**

```python
# Copy to config.py and fill in real values. config.py is git-ignored.

# Admin login password (plaintext for local; hash before real deployment).
ADMIN_PASSWORD = "change-me"

# Secret used to sign links and sessions. Use a long random string.
SECRET_KEY = "change-me-to-a-long-random-string"

# Where completed results are emailed.
ADMIN_EMAIL = "admin@example.com"

# How many days a client link stays valid.
LINK_EXPIRY_DAYS = 7

# "outbox" writes emails to ./outbox for local testing.
# "smtp" sends real email using the SMTP_* settings below.
MAIL_MODE = "outbox"

# Only used when MAIL_MODE == "smtp".
SMTP_HOST = ""
SMTP_PORT = 587
SMTP_USERNAME = ""
SMTP_PASSWORD = ""
SMTP_USE_TLS = True

# Upload limits for signed documents.
MAX_UPLOAD_MB = 15
ALLOWED_UPLOAD_EXTENSIONS = ["pdf", "doc", "docx"]
```

- [ ] **Step 4: Create a local `config.py` from the example**

Run:
```bash
cp config.example.py config.py
python - <<'PY'
import re, secrets, pathlib
p = pathlib.Path("config.py")
t = p.read_text()
t = t.replace('SECRET_KEY = "change-me-to-a-long-random-string"',
              f'SECRET_KEY = "{secrets.token_hex(32)}"')
t = t.replace('ADMIN_PASSWORD = "change-me"', 'ADMIN_PASSWORD = "admin123"')
p.write_text(t)
print("config.py written")
PY
```
Expected: `config.py written` (local password `admin123`, random secret). The admin can change these anytime.

- [ ] **Step 5: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
```

- [ ] **Step 6: Write `tests/conftest.py`**

This gives tests isolated temp directories and a test config, so no test touches real data.

```python
import importlib
import pytest


@pytest.fixture
def settings(tmp_path):
    """A plain settings object tests can pass into modules/app."""
    class S:
        ADMIN_PASSWORD = "testpass"
        SECRET_KEY = "test-secret-key"
        ADMIN_EMAIL = "admin@example.com"
        LINK_EXPIRY_DAYS = 7
        MAIL_MODE = "outbox"
        SMTP_HOST = ""
        SMTP_PORT = 587
        SMTP_USERNAME = ""
        SMTP_PASSWORD = ""
        SMTP_USE_TLS = True
        MAX_UPLOAD_MB = 15
        ALLOWED_UPLOAD_EXTENSIONS = ["pdf", "doc", "docx"]
        # directories (filled below)
        STORE_DIR = str(tmp_path / "templates_store")
        OUTBOX_DIR = str(tmp_path / "outbox")
        UPLOADS_TMP_DIR = str(tmp_path / "uploads_tmp")
    return S
```

- [ ] **Step 7: Run pytest to confirm the harness loads**

Run: `pytest -q`
Expected: `no tests ran` (exit 0) or collection succeeds with 0 tests. No errors.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt config.example.py pytest.ini tests/conftest.py
git commit -m "chore: scaffold project config and test harness"
```

---

## Task 1: Signed per-client links (`links.py`)

**Files:**
- Create: `links.py`
- Test: `tests/test_links.py`

- [ ] **Step 1: Write the failing test**

```python
import time
import pytest
from links import make_link_token, read_link_token, LinkError


def test_round_trip_returns_payload(settings):
    token = make_link_token(
        settings.SECRET_KEY,
        kind="questionnaire",
        template_id="abc",
        first_name="Jane",
        last_name="Doe",
        expiry_days=7,
    )
    data = read_link_token(settings.SECRET_KEY, token, max_age_days=7)
    assert data["kind"] == "questionnaire"
    assert data["template_id"] == "abc"
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"


def test_tampered_token_rejected(settings):
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id="x", first_name="A", last_name="B",
                            expiry_days=7)
    with pytest.raises(LinkError):
        read_link_token(settings.SECRET_KEY, token + "junk", max_age_days=7)


def test_wrong_key_rejected(settings):
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id="x", first_name="A", last_name="B",
                            expiry_days=7)
    with pytest.raises(LinkError):
        read_link_token("other-key", token, max_age_days=7)


def test_expired_token_rejected(settings):
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id="x", first_name="A", last_name="B",
                            expiry_days=7)
    with pytest.raises(LinkError):
        read_link_token(settings.SECRET_KEY, token, max_age_days=0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_links.py -q`
Expected: FAIL (ModuleNotFoundError: No module named 'links').

- [ ] **Step 3: Write minimal implementation**

```python
"""Sign and verify per-client link tokens. No client data is stored;
identity lives only inside the signed token."""

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


class LinkError(Exception):
    """Raised when a token is missing, tampered with, or expired."""


_SALT = "client-link"


def _serializer(secret_key):
    return URLSafeTimedSerializer(secret_key, salt=_SALT)


def make_link_token(secret_key, *, kind, template_id, first_name, last_name,
                    expiry_days):
    if kind not in ("questionnaire", "document"):
        raise ValueError("kind must be 'questionnaire' or 'document'")
    payload = {
        "kind": kind,
        "template_id": template_id,
        "first_name": first_name,
        "last_name": last_name,
    }
    return _serializer(secret_key).dumps(payload)


def read_link_token(secret_key, token, *, max_age_days):
    max_age_seconds = int(max_age_days) * 24 * 60 * 60
    try:
        return _serializer(secret_key).loads(token, max_age=max_age_seconds)
    except SignatureExpired as exc:
        raise LinkError("link expired") from exc
    except BadSignature as exc:
        raise LinkError("invalid link") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_links.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add links.py tests/test_links.py
git commit -m "feat: signed expiring per-client link tokens"
```

---

## Task 2: Template storage (`store.py`)

**Files:**
- Create: `store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
import io
import pytest
from store import Store


@pytest.fixture
def store(settings):
    return Store(settings.STORE_DIR)


def test_create_and_get_questionnaire(store):
    qid = store.create_questionnaire(
        name="Health Check",
        questions=[
            {"prompt": "Do you smoke?", "type": "yesno", "required": True},
            {"prompt": "Age", "type": "number", "required": True},
        ],
    )
    q = store.get_questionnaire(qid)
    assert q["name"] == "Health Check"
    assert q["id"] == qid
    assert len(q["questions"]) == 2
    assert q["questions"][0]["type"] == "yesno"


def test_list_questionnaires(store):
    store.create_questionnaire(name="A", questions=[])
    store.create_questionnaire(name="B", questions=[])
    items = store.list_questionnaires()
    names = sorted(i["name"] for i in items)
    assert names == ["A", "B"]


def test_update_questionnaire(store):
    qid = store.create_questionnaire(name="Old", questions=[])
    store.update_questionnaire(qid, name="New",
                               questions=[{"prompt": "Q", "type": "text",
                                           "required": False}])
    q = store.get_questionnaire(qid)
    assert q["name"] == "New"
    assert len(q["questions"]) == 1


def test_delete_questionnaire(store):
    qid = store.create_questionnaire(name="Bye", questions=[])
    store.delete_questionnaire(qid)
    assert store.get_questionnaire(qid) is None


def test_create_and_get_document(store):
    did = store.create_document(display_name="NDA",
                                original_filename="nda.pdf",
                                file_bytes=b"%PDF-1.4 fake")
    doc = store.get_document(did)
    assert doc["display_name"] == "NDA"
    assert doc["original_filename"] == "nda.pdf"
    assert doc["ext"] == "pdf"
    data = store.read_document_bytes(did)
    assert data == b"%PDF-1.4 fake"


def test_list_and_delete_document(store):
    did = store.create_document(display_name="Doc",
                                original_filename="d.docx",
                                file_bytes=b"zip")
    assert len(store.list_documents()) == 1
    store.delete_document(did)
    assert store.get_document(did) is None
    assert store.list_documents() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store.py -q`
Expected: FAIL (No module named 'store').

- [ ] **Step 3: Write minimal implementation**

```python
"""File-backed storage for templates. This is the only persistent data in the
app. No client data is ever stored here."""

import json
import os
import uuid


class Store:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.q_dir = os.path.join(base_dir, "questionnaires")
        self.d_dir = os.path.join(base_dir, "documents")
        os.makedirs(self.q_dir, exist_ok=True)
        os.makedirs(self.d_dir, exist_ok=True)

    # ---- questionnaires ----
    def _q_path(self, qid):
        return os.path.join(self.q_dir, f"{qid}.json")

    def create_questionnaire(self, *, name, questions):
        qid = uuid.uuid4().hex
        data = {"id": qid, "name": name, "questions": questions}
        with open(self._q_path(qid), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return qid

    def get_questionnaire(self, qid):
        path = self._q_path(qid)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def list_questionnaires(self):
        items = []
        for name in os.listdir(self.q_dir):
            if name.endswith(".json"):
                with open(os.path.join(self.q_dir, name), encoding="utf-8") as f:
                    items.append(json.load(f))
        return items

    def update_questionnaire(self, qid, *, name, questions):
        if self.get_questionnaire(qid) is None:
            raise KeyError(qid)
        data = {"id": qid, "name": name, "questions": questions}
        with open(self._q_path(qid), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def delete_questionnaire(self, qid):
        path = self._q_path(qid)
        if os.path.exists(path):
            os.remove(path)

    # ---- documents ----
    def _d_json(self, did):
        return os.path.join(self.d_dir, f"{did}.json")

    def _d_file(self, did, ext):
        return os.path.join(self.d_dir, f"{did}.{ext}")

    def create_document(self, *, display_name, original_filename, file_bytes):
        did = uuid.uuid4().hex
        ext = original_filename.rsplit(".", 1)[-1].lower() if "." in \
            original_filename else "bin"
        with open(self._d_file(did, ext), "wb") as f:
            f.write(file_bytes)
        meta = {"id": did, "display_name": display_name,
                "original_filename": original_filename, "ext": ext}
        with open(self._d_json(did), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return did

    def get_document(self, did):
        path = self._d_json(did)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def read_document_bytes(self, did):
        meta = self.get_document(did)
        if meta is None:
            return None
        with open(self._d_file(did, meta["ext"]), "rb") as f:
            return f.read()

    def list_documents(self):
        items = []
        for name in os.listdir(self.d_dir):
            if name.endswith(".json"):
                with open(os.path.join(self.d_dir, name), encoding="utf-8") as f:
                    items.append(json.load(f))
        return items

    def delete_document(self, did):
        meta = self.get_document(did)
        if meta is None:
            return
        for path in (self._d_json(did), self._d_file(did, meta["ext"])):
            if os.path.exists(path):
                os.remove(path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add store.py tests/test_store.py
git commit -m "feat: file-backed template storage"
```

---

## Task 3: Mailer (`mailer.py`)

**Files:**
- Create: `mailer.py`
- Test: `tests/test_mailer.py`

- [ ] **Step 1: Write the failing test**

```python
import os
import glob
import pytest
from mailer import send


def test_outbox_writes_eml(settings):
    send(settings, subject="Health Check - Jane Doe",
         body="Q: Do you smoke?\nA: No\n", attachments=[])
    files = glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml"))
    assert len(files) == 1
    content = open(files[0], encoding="utf-8").read()
    assert "Health Check - Jane Doe" in content
    assert "admin@example.com" in content
    assert "Do you smoke?" in content


def test_outbox_writes_attachment(settings):
    send(settings, subject="NDA - Jane Doe", body="Signed doc attached.",
         attachments=[("signed.pdf", b"%PDF-1.4 fake")])
    emls = glob.glob(os.path.join(settings.OUTBOX_DIR, "*.eml"))
    assert len(emls) == 1
    raw = open(emls[0], "rb").read()
    # base64 of the attachment content should be present in the MIME body
    import base64
    assert base64.b64encode(b"%PDF-1.4 fake").strip() in raw.replace(b"\n", b"")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mailer.py -q`
Expected: FAIL (No module named 'mailer').

- [ ] **Step 3: Write minimal implementation**

```python
"""Send results to the admin. Outbox mode (local) writes .eml files to disk;
smtp mode sends real email. Switching is a config change only."""

import os
import smtplib
import time
import uuid
from email.message import EmailMessage


def _build_message(settings, subject, body, attachments):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.ADMIN_EMAIL
    msg["To"] = settings.ADMIN_EMAIL
    msg.set_content(body)
    for filename, data in attachments:
        maintype, subtype = "application", "octet-stream"
        msg.add_attachment(data, maintype=maintype, subtype=subtype,
                           filename=filename)
    return msg


def send(settings, *, subject, body, attachments):
    """attachments: list of (filename, bytes)."""
    msg = _build_message(settings, subject, body, attachments)
    mode = getattr(settings, "MAIL_MODE", "outbox")
    if mode == "smtp":
        _send_smtp(settings, msg)
    else:
        _send_outbox(settings, msg)


def _send_outbox(settings, msg):
    os.makedirs(settings.OUTBOX_DIR, exist_ok=True)
    name = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.eml"
    with open(os.path.join(settings.OUTBOX_DIR, name), "wb") as f:
        f.write(bytes(msg))


def _send_smtp(settings, msg):
    if settings.SMTP_USE_TLS:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
    else:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
    try:
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
    finally:
        server.quit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mailer.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add mailer.py tests/test_mailer.py
git commit -m "feat: mailer with outbox and smtp modes"
```

---

## Task 4: Auth helpers (`auth.py`)

**Files:**
- Create: `auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write the failing test**

```python
from auth import check_password


def test_correct_password(settings):
    assert check_password(settings, "testpass") is True


def test_wrong_password(settings):
    assert check_password(settings, "nope") is False


def test_empty_password(settings):
    assert check_password(settings, "") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py -q`
Expected: FAIL (No module named 'auth').

- [ ] **Step 3: Write minimal implementation**

```python
"""Admin authentication helpers. Single shared password from config."""

import hmac
from functools import wraps
from flask import session, redirect, url_for


def check_password(settings, candidate):
    if not candidate:
        return False
    return hmac.compare_digest(str(candidate), str(settings.ADMIN_PASSWORD))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: admin auth helpers"
```

---

## Task 5: App factory + login/logout routes

**Files:**
- Create: `app.py`
- Create: `templates/base.html`
- Create: `templates/login.html`
- Create: `static/style.css`
- Test: `tests/test_admin_routes.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_routes.py -q`
Expected: FAIL (No module named 'app').

- [ ] **Step 3: Write `templates/base.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Client Portal{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
  <div class="container">
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="flash">{% for m in messages %}<p>{{ m }}</p>{% endfor %}</div>
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </div>
</body>
</html>
```

- [ ] **Step 4: Write `templates/login.html`**

```html
{% extends "base.html" %}
{% block title %}Admin Login{% endblock %}
{% block content %}
<h1>Admin Login</h1>
<form method="post" action="{{ url_for('login') }}">
  <label>Password
    <input type="password" name="password" autofocus required>
  </label>
  <button type="submit">Log in</button>
</form>
{% endblock %}
```

- [ ] **Step 5: Write `static/style.css`**

```css
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0;
  background: #f5f7fa; color: #1c2530; }
.container { max-width: 820px; margin: 0 auto; padding: 32px 20px; }
h1 { font-size: 1.6rem; }
.flash { background: #fff3cd; border: 1px solid #ffe08a; padding: 10px 14px;
  border-radius: 8px; margin-bottom: 16px; }
label { display: block; margin: 12px 0; font-weight: 600; }
input, select, textarea { width: 100%; padding: 10px; border: 1px solid #cbd5e0;
  border-radius: 8px; font-size: 1rem; margin-top: 4px; }
button, .btn { background: #2b6cb0; color: #fff; border: 0; padding: 10px 16px;
  border-radius: 8px; font-size: 1rem; cursor: pointer; text-decoration: none;
  display: inline-block; }
button.secondary, .btn.secondary { background: #718096; }
button.danger { background: #c53030; }
table { width: 100%; border-collapse: collapse; margin: 16px 0; background: #fff; }
th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }
.card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 20px; margin: 16px 0; }
.section-title { margin-top: 28px; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: none; align-items: center; justify-content: center; }
.modal-backdrop.open { display: flex; }
.modal { background: #fff; border-radius: 12px; padding: 24px; width: 380px; }
.link-box { word-break: break-all; background: #edf2f7; padding: 10px;
  border-radius: 8px; margin-top: 10px; font-size: .9rem; }
.q-row { border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;
  margin-bottom: 10px; }
.help { color: #4a5568; font-size: .95rem; }
.steps { padding-left: 20px; }
.steps li { margin: 8px 0; }
```

- [ ] **Step 6: Write `app.py` (factory + login/logout + empty admin stub)**

```python
import os
from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash)

from store import Store
from auth import check_password, login_required


def _settings_from_config():
    import config

    class S:
        pass
    s = S()
    for key in dir(config):
        if key.isupper():
            setattr(s, key, getattr(config, key))
    base = os.path.dirname(os.path.abspath(__file__))
    s.STORE_DIR = os.path.join(base, "templates_store")
    s.OUTBOX_DIR = os.path.join(base, "outbox")
    s.UPLOADS_TMP_DIR = os.path.join(base, "uploads_tmp")
    return s


def create_app(settings=None):
    if settings is None:
        settings = _settings_from_config()

    app = Flask(__name__)
    app.secret_key = settings.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_UPLOAD_MB * 1024 * 1024
    app.config["SETTINGS"] = settings
    app.config["STORE"] = Store(settings.STORE_DIR)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            if check_password(settings, request.form.get("password", "")):
                session["is_admin"] = True
                return redirect(url_for("admin"))
            flash("Incorrect password")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    def home():
        return redirect(url_for("admin"))

    @app.route("/admin")
    @login_required
    def admin():
        store = app.config["STORE"]
        return render_template(
            "admin_list.html",
            questionnaires=store.list_questionnaires(),
            documents=store.list_documents(),
        )

    register_admin_routes(app)
    register_guest_routes(app)
    return app


def register_admin_routes(app):
    pass  # filled in Task 6


def register_guest_routes(app):
    pass  # filled in Task 7


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
```

- [ ] **Step 7: Write a minimal `templates/admin_list.html` so `/admin` renders**

```html
{% extends "base.html" %}
{% block title %}Admin - Templates{% endblock %}
{% block content %}
<h1>Templates</h1>
<p><a href="{{ url_for('logout') }}">Log out</a></p>
{% endblock %}
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_admin_routes.py -q`
Expected: PASS (4 passed).

- [ ] **Step 9: Commit**

```bash
git add app.py templates/base.html templates/login.html templates/admin_list.html static/style.css tests/test_admin_routes.py
git commit -m "feat: app factory with admin login/logout"
```

---

## Task 6: Admin template management + share links

**Files:**
- Modify: `app.py` (fill `register_admin_routes`)
- Modify: `templates/admin_list.html` (full version)
- Create: `templates/questionnaire_builder.html`
- Create: `templates/document_upload.html`
- Test: extend `tests/test_admin_routes.py`

- [ ] **Step 1: Write the failing tests (append to `tests/test_admin_routes.py`)**

```python
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
        "q_required": ["on", "on"],
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_admin_routes.py -q`
Expected: FAIL (routes 404 / not found).

- [ ] **Step 3: Implement `register_admin_routes` in `app.py`**

Replace the `register_admin_routes` stub with:

```python
def register_admin_routes(app):
    from flask import jsonify
    from links import make_link_token

    settings = app.config["SETTINGS"]
    store = app.config["STORE"]

    def _parse_questions(form):
        prompts = form.getlist("q_prompt")
        types = form.getlist("q_type")
        required = form.getlist("q_required")  # checkboxes: only "on" present
        options = form.getlist("q_options")
        # Checkboxes don't submit when unchecked, so align by index using a
        # hidden required flag per row instead:
        req_flags = form.getlist("q_required_flag")
        questions = []
        for i, prompt in enumerate(prompts):
            prompt = prompt.strip()
            if not prompt:
                continue
            qtype = types[i] if i < len(types) else "text"
            opts_raw = options[i] if i < len(options) else ""
            opts = [o.strip() for o in opts_raw.split("|") if o.strip()]
            is_required = (req_flags[i] == "1") if i < len(req_flags) else False
            q = {"prompt": prompt, "type": qtype, "required": is_required}
            if qtype == "choice":
                q["options"] = opts
            questions.append(q)
        return questions

    @app.route("/admin/questionnaires/new", methods=["GET", "POST"])
    @login_required
    def questionnaire_new():
        if request.method == "POST":
            name = request.form.get("name", "").strip() or "Untitled"
            questions = _parse_questions(request.form)
            store.create_questionnaire(name=name, questions=questions)
            flash("Questionnaire saved")
            return redirect(url_for("admin"))
        return render_template("questionnaire_builder.html",
                               questionnaire=None)

    @app.route("/admin/questionnaires/<qid>/edit", methods=["GET", "POST"])
    @login_required
    def questionnaire_edit(qid):
        q = store.get_questionnaire(qid)
        if q is None:
            flash("Not found")
            return redirect(url_for("admin"))
        if request.method == "POST":
            name = request.form.get("name", "").strip() or "Untitled"
            questions = _parse_questions(request.form)
            store.update_questionnaire(qid, name=name, questions=questions)
            flash("Questionnaire updated")
            return redirect(url_for("admin"))
        return render_template("questionnaire_builder.html", questionnaire=q)

    @app.route("/admin/questionnaires/<qid>/delete", methods=["POST"])
    @login_required
    def questionnaire_delete(qid):
        store.delete_questionnaire(qid)
        flash("Questionnaire deleted")
        return redirect(url_for("admin"))

    @app.route("/admin/documents/new", methods=["GET", "POST"])
    @login_required
    def document_new():
        if request.method == "POST":
            display_name = request.form.get("display_name", "").strip() \
                or "Untitled"
            file = request.files.get("file")
            if not file or file.filename == "":
                flash("Please choose a file")
                return redirect(url_for("document_new"))
            ext = file.filename.rsplit(".", 1)[-1].lower() \
                if "." in file.filename else ""
            if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                flash("File type not allowed")
                return redirect(url_for("document_new"))
            store.create_document(display_name=display_name,
                                  original_filename=file.filename,
                                  file_bytes=file.read())
            flash("Document uploaded")
            return redirect(url_for("admin"))
        return render_template("document_upload.html")

    @app.route("/admin/documents/<did>/delete", methods=["POST"])
    @login_required
    def document_delete(did):
        store.delete_document(did)
        flash("Document deleted")
        return redirect(url_for("admin"))

    @app.route("/admin/share", methods=["POST"])
    @login_required
    def admin_share():
        kind = request.form.get("kind", "")
        template_id = request.form.get("template_id", "")
        first = request.form.get("first_name", "").strip()
        last = request.form.get("last_name", "").strip()
        if kind not in ("questionnaire", "document") or not template_id:
            return jsonify({"error": "bad request"}), 400
        if not first or not last:
            return jsonify({"error": "first and last name required"}), 400
        token = make_link_token(settings.SECRET_KEY, kind=kind,
                                template_id=template_id, first_name=first,
                                last_name=last,
                                expiry_days=settings.LINK_EXPIRY_DAYS)
        link = url_for("guest", token=token, _external=True)
        return jsonify({"link": link})
```

- [ ] **Step 4: Write full `templates/admin_list.html`**

```html
{% extends "base.html" %}
{% block title %}Admin - Templates{% endblock %}
{% block content %}
<div style="display:flex;justify-content:space-between;align-items:center">
  <h1>Templates</h1>
  <a href="{{ url_for('logout') }}">Log out</a>
</div>

<h2 class="section-title">Questionnaires</h2>
<a class="btn" href="{{ url_for('questionnaire_new') }}">+ New questionnaire</a>
<table>
  <thead><tr><th>Name</th><th>Questions</th><th>Actions</th></tr></thead>
  <tbody>
  {% for q in questionnaires %}
    <tr>
      <td>{{ q.name }}</td>
      <td>{{ q.questions|length }}</td>
      <td>
        <button class="btn"
          onclick="openShare('questionnaire','{{ q.id }}','{{ q.name }}')">
          Share</button>
        <a class="btn secondary"
           href="{{ url_for('questionnaire_edit', qid=q.id) }}">Edit</a>
        <form method="post" style="display:inline"
              action="{{ url_for('questionnaire_delete', qid=q.id) }}">
          <button class="danger" onclick="return confirm('Delete?')">
            Delete</button>
        </form>
      </td>
    </tr>
  {% else %}
    <tr><td colspan="3" class="help">No questionnaires yet.</td></tr>
  {% endfor %}
  </tbody>
</table>

<h2 class="section-title">Documents</h2>
<a class="btn" href="{{ url_for('document_new') }}">+ Upload document</a>
<table>
  <thead><tr><th>Name</th><th>File</th><th>Actions</th></tr></thead>
  <tbody>
  {% for d in documents %}
    <tr>
      <td>{{ d.display_name }}</td>
      <td>{{ d.original_filename }}</td>
      <td>
        <button class="btn"
          onclick="openShare('document','{{ d.id }}','{{ d.display_name }}')">
          Share</button>
        <form method="post" style="display:inline"
              action="{{ url_for('document_delete', did=d.id) }}">
          <button class="danger" onclick="return confirm('Delete?')">
            Delete</button>
        </form>
      </td>
    </tr>
  {% else %}
    <tr><td colspan="3" class="help">No documents yet.</td></tr>
  {% endfor %}
  </tbody>
</table>

<div class="modal-backdrop" id="shareModal">
  <div class="modal">
    <h3 id="shareTitle">Share</h3>
    <p class="help">Enter the client's name to generate a unique link.</p>
    <label>First name <input type="text" id="firstName"></label>
    <label>Last name <input type="text" id="lastName"></label>
    <input type="hidden" id="shareKind">
    <input type="hidden" id="shareTemplateId">
    <div style="margin-top:12px">
      <button class="btn" onclick="generateLink()">Generate link</button>
      <button class="btn secondary" onclick="closeShare()">Close</button>
    </div>
    <div id="linkResult" class="link-box" style="display:none"></div>
  </div>
</div>

<script>
function openShare(kind, id, name) {
  document.getElementById('shareKind').value = kind;
  document.getElementById('shareTemplateId').value = id;
  document.getElementById('shareTitle').textContent = 'Share: ' + name;
  document.getElementById('firstName').value = '';
  document.getElementById('lastName').value = '';
  document.getElementById('linkResult').style.display = 'none';
  document.getElementById('shareModal').classList.add('open');
}
function closeShare() {
  document.getElementById('shareModal').classList.remove('open');
}
async function generateLink() {
  const body = new FormData();
  body.append('kind', document.getElementById('shareKind').value);
  body.append('template_id', document.getElementById('shareTemplateId').value);
  body.append('first_name', document.getElementById('firstName').value);
  body.append('last_name', document.getElementById('lastName').value);
  const resp = await fetch('{{ url_for("admin_share") }}',
    {method: 'POST', body});
  const box = document.getElementById('linkResult');
  box.style.display = 'block';
  if (resp.ok) {
    const data = await resp.json();
    box.textContent = data.link;
  } else {
    box.textContent = 'Please enter both first and last name.';
  }
}
</script>
{% endblock %}
```

- [ ] **Step 5: Write `templates/questionnaire_builder.html`**

```html
{% extends "base.html" %}
{% block title %}Questionnaire builder{% endblock %}
{% block content %}
<h1>{{ "Edit" if questionnaire else "New" }} questionnaire</h1>
<form method="post">
  <label>Name
    <input type="text" name="name"
           value="{{ questionnaire.name if questionnaire else '' }}" required>
  </label>

  <h3>Questions</h3>
  <div id="questions">
    {% if questionnaire %}
      {% for q in questionnaire.questions %}
      <div class="q-row">
        <label>Prompt
          <input type="text" name="q_prompt" value="{{ q.prompt }}"></label>
        <label>Type
          <select name="q_type" onchange="toggleOptions(this)">
            {% for t in ["text","choice","yesno","number","date"] %}
            <option value="{{ t }}" {{ "selected" if q.type==t }}>{{ t }}</option>
            {% endfor %}
          </select>
        </label>
        <label>Options (for choice, separate with | )
          <input type="text" name="q_options"
            value="{{ q.options|join('|') if q.options else '' }}"></label>
        <label>Required
          <input type="checkbox" onchange="syncReq(this)"
                 {{ "checked" if q.required }}>
          <input type="hidden" name="q_required_flag"
                 value="{{ '1' if q.required else '0' }}"></label>
        <button type="button" class="danger"
                onclick="this.closest('.q-row').remove()">Remove</button>
      </div>
      {% endfor %}
    {% endif %}
  </div>

  <button type="button" class="btn secondary" onclick="addQuestion()">
    + Add question</button>
  <div style="margin-top:16px">
    <button type="submit" class="btn">Save</button>
    <a class="btn secondary" href="{{ url_for('admin') }}">Cancel</a>
  </div>
</form>

<template id="qTemplate">
  <div class="q-row">
    <label>Prompt <input type="text" name="q_prompt"></label>
    <label>Type
      <select name="q_type" onchange="toggleOptions(this)">
        <option value="text">text</option>
        <option value="choice">choice</option>
        <option value="yesno">yesno</option>
        <option value="number">number</option>
        <option value="date">date</option>
      </select>
    </label>
    <label>Options (for choice, separate with | )
      <input type="text" name="q_options"></label>
    <label>Required
      <input type="checkbox" onchange="syncReq(this)">
      <input type="hidden" name="q_required_flag" value="0"></label>
    <button type="button" class="danger"
            onclick="this.closest('.q-row').remove()">Remove</button>
  </div>
</template>

<script>
function addQuestion() {
  const tpl = document.getElementById('qTemplate');
  document.getElementById('questions')
    .appendChild(tpl.content.cloneNode(true));
}
function syncReq(cb) {
  cb.parentElement.querySelector('input[type=hidden]').value =
    cb.checked ? '1' : '0';
}
function toggleOptions(sel) { /* options field always visible for simplicity */ }
</script>
{% endblock %}
```

- [ ] **Step 6: Write `templates/document_upload.html`**

```html
{% extends "base.html" %}
{% block title %}Upload document{% endblock %}
{% block content %}
<h1>Upload document template</h1>
<form method="post" enctype="multipart/form-data">
  <label>Display name
    <input type="text" name="display_name" required></label>
  <label>File (pdf, doc, docx)
    <input type="file" name="file" accept=".pdf,.doc,.docx" required></label>
  <div style="margin-top:16px">
    <button type="submit" class="btn">Upload</button>
    <a class="btn secondary" href="{{ url_for('admin') }}">Cancel</a>
  </div>
</form>
{% endblock %}
```

- [ ] **Step 7: Update `test_create_questionnaire` to send `q_required_flag`**

In `tests/test_admin_routes.py`, replace the `test_create_questionnaire` body's `data` dict with the flag-based fields:

```python
    resp = c.post("/admin/questionnaires/new", data={
        "name": "Health Check",
        "q_prompt": ["Do you smoke?", "Age"],
        "q_type": ["yesno", "number"],
        "q_required_flag": ["1", "1"],
        "q_options": ["", ""],
    }, follow_redirects=True)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_admin_routes.py -q`
Expected: PASS (all admin route tests pass).

- [ ] **Step 9: Commit**

```bash
git add app.py templates/admin_list.html templates/questionnaire_builder.html templates/document_upload.html tests/test_admin_routes.py
git commit -m "feat: admin template management and share links"
```

---

## Task 7: Guest routes (questionnaire + document flows)

**Files:**
- Modify: `app.py` (fill `register_guest_routes`)
- Create: `templates/guest_questionnaire.html`
- Create: `templates/guest_document.html`
- Create: `templates/thank_you.html`
- Create: `templates/error.html`
- Test: `tests/test_guest_routes.py`

- [ ] **Step 1: Write the failing tests**

```python
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
    assert os.listdir(settings.UPLOADS_TMP_DIR) == [] \
        if os.path.exists(settings.UPLOADS_TMP_DIR) else True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_guest_routes.py -q`
Expected: FAIL (guest routes not implemented).

- [ ] **Step 3: Implement `register_guest_routes` in `app.py`**

Replace the `register_guest_routes` stub with:

```python
def register_guest_routes(app):
    from flask import abort, send_file, Response
    import io
    from links import read_link_token, LinkError
    import mailer

    settings = app.config["SETTINGS"]
    store = app.config["STORE"]

    def _load(token):
        try:
            data = read_link_token(settings.SECRET_KEY, token,
                                   max_age_days=settings.LINK_EXPIRY_DAYS)
        except LinkError as exc:
            return None, str(exc)
        return data, None

    @app.route("/c/<token>", methods=["GET", "POST"])
    def guest(token):
        data, err = _load(token)
        if data is None:
            return render_template("error.html", message=(
                "This link is invalid or has expired. "
                "Please ask for a new link.")), 400

        first, last = data["first_name"], data["last_name"]
        if data["kind"] == "questionnaire":
            q = store.get_questionnaire(data["template_id"])
            if q is None:
                return render_template("error.html",
                                       message="This form is no longer available."), 404
            if request.method == "POST":
                answers, missing = [], False
                for i, question in enumerate(q["questions"]):
                    val = request.form.get(f"answer_{i}", "").strip()
                    if question.get("required") and not val:
                        missing = True
                    answers.append((question["prompt"], val))
                if missing:
                    return render_template("guest_questionnaire.html",
                                           q=q, first=first,
                                           error="Please fill in all required fields.")
                body_lines = [f"Client: {first} {last}", ""]
                for prompt, val in answers:
                    body_lines.append(f"Q: {prompt}")
                    body_lines.append(f"A: {val or '(no answer)'}")
                    body_lines.append("")
                mailer.send(settings,
                            subject=f"{q['name']} - {first} {last}",
                            body="\n".join(body_lines), attachments=[])
                return render_template("thank_you.html", first=first)
            return render_template("guest_questionnaire.html", q=q,
                                   first=first, error=None)

        # document flow
        doc = store.get_document(data["template_id"])
        if doc is None:
            return render_template("error.html",
                                   message="This document is no longer available."), 404
        if request.method == "POST":
            file = request.files.get("file")
            if not file or file.filename == "":
                return render_template("guest_document.html", doc=doc,
                                       first=first, token=token,
                                       error="Please choose your signed file.")
            ext = file.filename.rsplit(".", 1)[-1].lower() \
                if "." in file.filename else ""
            if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                return render_template("guest_document.html", doc=doc,
                                       first=first, token=token,
                                       error="That file type is not allowed.")
            file_bytes = file.read()
            mailer.send(settings,
                        subject=f"{doc['display_name']} - {first} {last}",
                        body=f"Signed document from {first} {last} attached.",
                        attachments=[(file.filename, file_bytes)])
            return render_template("thank_you.html", first=first)
        return render_template("guest_document.html", doc=doc, first=first,
                               token=token, error=None)

    @app.route("/c/<token>/download")
    def guest_download(token):
        data, err = _load(token)
        if data is None or data["kind"] != "document":
            abort(400)
        doc = store.get_document(data["template_id"])
        if doc is None:
            abort(404)
        content = store.read_document_bytes(data["template_id"])
        return Response(
            content,
            headers={
                "Content-Disposition":
                    f'attachment; filename="{doc["original_filename"]}"',
                "Content-Type": "application/octet-stream",
            },
        )
```

Note: the document flow reads the upload into memory and passes it straight to
the mailer, so no temp file is written to disk (satisfies "store nothing" and the
test's no-leftover-files check).

- [ ] **Step 4: Write `templates/guest_questionnaire.html`**

```html
{% extends "base.html" %}
{% block title %}{{ q.name }}{% endblock %}
{% block content %}
<h1>Hello {{ first }}</h1>
<p class="help">Please answer the questions below and press submit. Your answers
  are sent directly to us and are not stored on this site.</p>
{% if error %}<div class="flash">{{ error }}</div>{% endif %}
<form method="post">
  {% for question in q.questions %}
  <div class="card">
    <label>{{ loop.index }}. {{ question.prompt }}
      {% if question.required %}<span style="color:#c53030">*</span>{% endif %}
    </label>
    {% set nm = "answer_" ~ loop.index0 %}
    {% if question.type == "text" %}
      <textarea name="{{ nm }}" rows="3"></textarea>
    {% elif question.type == "number" %}
      <input type="number" name="{{ nm }}">
    {% elif question.type == "date" %}
      <input type="date" name="{{ nm }}">
    {% elif question.type == "yesno" %}
      <select name="{{ nm }}">
        <option value="">-- select --</option>
        <option value="Yes">Yes</option>
        <option value="No">No</option>
      </select>
    {% elif question.type == "choice" %}
      <select name="{{ nm }}">
        <option value="">-- select --</option>
        {% for opt in question.options %}
        <option value="{{ opt }}">{{ opt }}</option>
        {% endfor %}
      </select>
    {% else %}
      <input type="text" name="{{ nm }}">
    {% endif %}
  </div>
  {% endfor %}
  <button type="submit" class="btn">Submit</button>
</form>
{% endblock %}
```

- [ ] **Step 5: Write `templates/guest_document.html`**

```html
{% extends "base.html" %}
{% block title %}{{ doc.display_name }}{% endblock %}
{% block content %}
<h1>Hello {{ first }}</h1>
<p class="help">Please follow these steps:</p>
<ol class="steps">
  <li>Download the document below.</li>
  <li>Sign it yourself (print &amp; sign, or sign digitally).</li>
  <li>Upload your signed copy here. It is emailed to us and not stored on this
    site.</li>
</ol>

<div class="card">
  <a class="btn" href="{{ url_for('guest_download', token=token) }}">
    Download: {{ doc.display_name }}</a>
</div>

{% if error %}<div class="flash">{{ error }}</div>{% endif %}
<form method="post" enctype="multipart/form-data" class="card">
  <label>Upload your signed file (pdf, doc, docx)
    <input type="file" name="file" accept=".pdf,.doc,.docx" required></label>
  <button type="submit" class="btn">Send signed document</button>
</form>
{% endblock %}
```

- [ ] **Step 6: Write `templates/thank_you.html`**

```html
{% extends "base.html" %}
{% block title %}Thank you{% endblock %}
{% block content %}
<div class="card">
  <h1>Thank you, {{ first }}!</h1>
  <p class="help">We have received your response. You can close this page.</p>
</div>
{% endblock %}
```

- [ ] **Step 7: Write `templates/error.html`**

```html
{% extends "base.html" %}
{% block title %}Link problem{% endblock %}
{% block content %}
<div class="card">
  <h1>Sorry</h1>
  <p class="help">{{ message }}</p>
</div>
{% endblock %}
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_guest_routes.py -q`
Expected: PASS (all guest route tests pass).

- [ ] **Step 9: Commit**

```bash
git add app.py templates/guest_questionnaire.html templates/guest_document.html templates/thank_you.html templates/error.html tests/test_guest_routes.py
git commit -m "feat: guest questionnaire and document flows"
```

---

## Task 8: Full test run, manual smoke test, and README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Run the entire test suite**

Run: `pytest -q`
Expected: All tests pass (links, store, mailer, auth, admin routes, guest routes).

- [ ] **Step 2: Start the app for a manual smoke test**

Run:
```bash
. .venv/bin/activate
python app.py
```
Expected: Flask serves on http://127.0.0.1:5000

- [ ] **Step 3: Manual smoke checklist (do in a browser)**

  - Visit `/admin` -> redirected to `/login`.
  - Log in with the password from `config.py` (`admin123` by default).
  - Create a questionnaire with a couple of mixed-type questions. Save.
  - Click Share, enter a first/last name, generate a link. Copy it.
  - Open the link in a private window. Answer and submit. See thank-you.
  - Check `outbox/` for a new `.eml` titled `<Name> - First Last` with the Q&A.
  - Upload a document template. Share it, open the link, download, then upload any
    small pdf. See thank-you.
  - Check `outbox/` for a new `.eml` with the file attached.
  - Confirm nothing about the client appears anywhere except the `.eml` in outbox.

- [ ] **Step 4: Write `README.md`**

```markdown
# Client Portal (local version)

A small self-hosted site for a life insurance company. An admin manages
questionnaire and document templates and generates a unique link per client.
Clients complete a questionnaire or upload a signed document, and the result is
emailed to the admin. The site stores only templates; no client data is kept.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.example.py config.py   # then edit config.py
python app.py
```

Open http://127.0.0.1:5000 and log in at `/login`.

## Configuration

Edit `config.py` (never commit it):

- `ADMIN_PASSWORD` - admin login password.
- `SECRET_KEY` - long random string; signs links and sessions.
- `ADMIN_EMAIL` - where results are emailed.
- `LINK_EXPIRY_DAYS` - how long a client link is valid (default 7).
- `MAIL_MODE` - `outbox` (local, writes to `outbox/`) or `smtp` (real email).
- `SMTP_*` - only used in `smtp` mode.

## Email

In `outbox` mode, "sent" emails are written as `.eml` files in `outbox/`. Open
them in any mail client to verify. To send real email later, set
`MAIL_MODE = "smtp"` and fill in the `SMTP_*` values. No code changes needed.

## Tests

```bash
pytest -q
```

## Notes / before real deployment (human review required)

- Passwords and secrets live only in the git-ignored `config.py`.
- Client links are signed and expire; they are reusable until expiry.
- Uploaded signed documents are emailed and never written to disk.
- Before deploying to a real URL, a responsible owner must review: HTTPS,
  password hashing, secure cookies, upload scanning, and the legal sufficiency
  of the signed-document intake process.

Prepared with AI assistance; reviewed by the responsible owner.
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add README and finalize local version"
```

---

## Self-Review

**Spec coverage:**
- Admin password login -> Task 4, Task 5. Covered.
- Questionnaire templates with mixed types + required -> Task 2, Task 6, Task 7. Covered.
- Document templates upload/download -> Task 2, Task 6, Task 7. Covered.
- Share button popup -> Task 6 (modal + `/admin/share`). Covered.
- Unique signed expiring links from name+type -> Task 1, Task 6. Covered.
- Guest questionnaire answer -> email -> Task 7. Covered.
- Guest document download + upload signed -> email -> Task 7. Covered.
- Email titled `<Template> - <First> <Last>` -> Task 7. Covered.
- Store no client data (uploads not persisted, name only in token) -> Task 7 (in-memory upload), Task 1. Covered.
- Outbox now, SMTP later by config -> Task 3. Covered.
- Files-on-disk storage -> Task 2. Covered.
- Expiry days configurable -> Task 0 config, Task 1, Task 7. Covered.

**Placeholder scan:** No TBDs. `toggleOptions` is intentionally a no-op (documented inline) to keep the options field always visible; not a placeholder for required behavior.

**Type consistency:** `Store` method names consistent across Tasks 2/6/7. `make_link_token`/`read_link_token` signatures consistent across Tasks 1/6/7. `mailer.send(settings, subject=, body=, attachments=)` consistent across Tasks 3/7. Question dict shape `{prompt, type, required, options?}` consistent across Tasks 2/6/7. Form field names (`q_prompt`, `q_type`, `q_required_flag`, `q_options`, `answer_<i>`) consistent between builder template, parser, and tests.

One correction applied inline: the required-checkbox problem (unchecked checkboxes don't submit, breaking index alignment) is solved with a hidden `q_required_flag` per row, and the Task 6 test was updated to send `q_required_flag` accordingly.
