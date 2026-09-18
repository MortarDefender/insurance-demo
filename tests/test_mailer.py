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


class _FakeSMTP:
    """Records the sequence of smtplib calls for assertion."""
    instances = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.calls = []
        self.logged_in = None
        self.sent = 0
        self.quit_called = False
        _FakeSMTP.instances.append(self)

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, pw):
        self.logged_in = (user, pw)
        self.calls.append("login")

    def send_message(self, msg):
        self.sent += 1
        self.calls.append("send")

    def quit(self):
        self.quit_called = True


def test_smtp_tls_and_login_invoked(settings, monkeypatch):
    import smtplib
    import mailer as m
    _FakeSMTP.instances = []
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)

    settings.MAIL_MODE = "smtp"
    settings.SMTP_HOST = "smtp.example.com"
    settings.SMTP_PORT = 587
    settings.SMTP_USERNAME = "user@example.com"
    settings.SMTP_PASSWORD = "secret"
    settings.SMTP_USE_TLS = True

    m.send(settings, subject="S", body="B", attachments=[])

    assert len(_FakeSMTP.instances) == 1
    inst = _FakeSMTP.instances[0]
    assert inst.host == "smtp.example.com" and inst.port == 587
    # order matters: starttls before login before send, and quit at the end
    assert inst.calls == ["starttls", "login", "send"]
    assert inst.logged_in == ("user@example.com", "secret")
    assert inst.quit_called is True


def test_smtp_no_tls_no_auth_skips_those_steps(settings, monkeypatch):
    import smtplib
    import mailer as m
    _FakeSMTP.instances = []
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)

    settings.MAIL_MODE = "smtp"
    settings.SMTP_HOST = "localhost"
    settings.SMTP_PORT = 25
    settings.SMTP_USERNAME = ""
    settings.SMTP_PASSWORD = ""
    settings.SMTP_USE_TLS = False

    m.send(settings, subject="S", body="B", attachments=[])
    inst = _FakeSMTP.instances[0]
    assert inst.calls == ["send"]           # no starttls, no login
    assert inst.logged_in is None
    assert inst.quit_called is True


def test_smtp_quit_called_even_if_send_fails(settings, monkeypatch):
    import smtplib
    import mailer as m
    _FakeSMTP.instances = []

    class Failing(_FakeSMTP):
        def send_message(self, msg):
            raise RuntimeError("network dropped")

    monkeypatch.setattr(smtplib, "SMTP", Failing)
    settings.MAIL_MODE = "smtp"
    settings.SMTP_HOST = "h"; settings.SMTP_PORT = 25
    settings.SMTP_USERNAME = ""; settings.SMTP_PASSWORD = ""
    settings.SMTP_USE_TLS = False

    import pytest
    with pytest.raises(RuntimeError):
        m.send(settings, subject="S", body="B", attachments=[])
    # connection must still be closed
    assert _FakeSMTP.instances[0].quit_called is True
