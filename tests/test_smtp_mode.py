"""SMTP-mode integration test: the full guest submission path sends over a real
smtplib connection to an in-process capture server (stdlib only, no creds)."""
import base64
import socket
import threading

import pytest

from app import create_app
from links import make_link_token


class CaptureSMTP:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.data = b""
        self.rcpt_to = []
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def start(self):
        self.thread.start()

    def _serve(self):
        conn, _ = self.sock.accept()
        with conn:
            conn.sendall(b"220 capture ESMTP\r\n")
            in_data = False
            buf = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\r\n" in buf and not in_data:
                    line, buf = buf.split(b"\r\n", 1)
                    up = line.decode(errors="ignore").upper()
                    if up.startswith(("EHLO", "HELO")):
                        conn.sendall(b"250-capture\r\n250 OK\r\n")
                    elif up.startswith("MAIL FROM"):
                        conn.sendall(b"250 OK\r\n")
                    elif up.startswith("RCPT TO"):
                        self.rcpt_to.append(line.decode(errors="ignore"))
                        conn.sendall(b"250 OK\r\n")
                    elif up.startswith("DATA"):
                        conn.sendall(b"354 go\r\n")
                        in_data = True
                    elif up.startswith("QUIT"):
                        conn.sendall(b"221 Bye\r\n")
                        return
                    elif up.startswith("RSET"):
                        conn.sendall(b"250 OK\r\n")
                if in_data and b"\r\n.\r\n" in buf:
                    payload, buf = buf.split(b"\r\n.\r\n", 1)
                    self.data += payload
                    conn.sendall(b"250 queued\r\n")
                    in_data = False


def test_full_questionnaire_submit_over_smtp(settings):
    server = CaptureSMTP()
    server.start()
    settings.MAIL_MODE = "smtp"
    settings.SMTP_HOST = "127.0.0.1"
    settings.SMTP_PORT = server.port
    settings.SMTP_USERNAME = ""
    settings.SMTP_PASSWORD = ""
    settings.SMTP_USE_TLS = False

    app = create_app(settings)
    app.config.update(TESTING=True)
    c = app.test_client()

    qid = app.config["STORE"].create_questionnaire(
        name="Annual Review",
        questions=[{"prompt": "Do you smoke?", "type": "yesno",
                    "required": True}])
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id=qid, first_name="Jane", last_name="Doe",
                            expiry_days=7)
    resp = c.post(f"/c/{token}", data={"answer_0": "No"},
                  follow_redirects=True)
    assert resp.status_code == 200
    assert b"Thank you" in resp.data

    server.thread.join(timeout=2)
    assert any("admin@example.com" in r for r in server.rcpt_to), server.rcpt_to
    assert b"Subject: Annual Review - Jane Doe" in server.data
    assert b"Do you smoke?" in server.data and b"No" in server.data


def test_full_document_submit_over_smtp(settings):
    server = CaptureSMTP()
    server.start()
    settings.MAIL_MODE = "smtp"
    settings.SMTP_HOST = "127.0.0.1"
    settings.SMTP_PORT = server.port
    settings.SMTP_USERNAME = ""
    settings.SMTP_PASSWORD = ""
    settings.SMTP_USE_TLS = False

    app = create_app(settings)
    app.config.update(TESTING=True)
    c = app.test_client()

    import io
    did = app.config["STORE"].create_document(
        display_name="Beneficiary Form", original_filename="b.pdf",
        file_bytes=b"%PDF template")
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id=did, first_name="Mary", last_name="Smith",
                            expiry_days=7)
    resp = c.post(f"/c/{token}", data={
        "file": (io.BytesIO(b"%PDF-1.4 SIGNED"), "signed.pdf")},
        content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Thank you" in resp.data

    server.thread.join(timeout=2)
    assert b"Subject: Beneficiary Form - Mary Smith" in server.data
    assert base64.b64encode(b"%PDF-1.4 SIGNED").strip() in \
        server.data.replace(b"\n", b"")
