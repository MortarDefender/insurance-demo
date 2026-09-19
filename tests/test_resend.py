"""Tests for the Resend HTTP email mode (MAIL_MODE=resend)."""
import base64
import json

import pytest

import mailer


class _Bag:
    MAIL_MODE = "resend"
    ADMIN_EMAIL = "admin@example.com"
    RESEND_API_KEY = "re_test_key"
    MAIL_FROM = "sender@example.com"
    MAIL_TIMEOUT = 5


def test_resend_posts_expected_payload(monkeypatch):
    captured = {}

    def fake_post(url, headers, payload, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        captured["timeout"] = timeout
        return 200, b'{"id": "abc"}'

    monkeypatch.setattr(mailer, "_http_post_json", fake_post)
    mailer.send(_Bag(), subject="Health - Jane Doe", body="Q: Age\nA: 41",
                attachments=[("report.pdf", b"%PDF-1.4 data")])

    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["Authorization"] == "Bearer re_test_key"
    p = captured["payload"]
    assert p["from"] == "sender@example.com"
    assert p["to"] == ["admin@example.com"]
    assert p["subject"] == "Health - Jane Doe"
    assert "Age" in p["text"]
    # Attachment is base64-encoded.
    assert p["attachments"][0]["filename"] == "report.pdf"
    decoded = base64.b64decode(p["attachments"][0]["content"])
    assert decoded == b"%PDF-1.4 data"


def test_resend_missing_key_raises(monkeypatch):
    bag = _Bag()
    bag.RESEND_API_KEY = ""
    with pytest.raises(RuntimeError, match="RESEND_API_KEY"):
        mailer.send(bag, subject="x", body="y", attachments=[])


def test_resend_error_status_raises(monkeypatch):
    monkeypatch.setattr(mailer, "_http_post_json",
                        lambda *a, **k: (422, b'{"error":"bad"}'))
    with pytest.raises(RuntimeError, match="status 422"):
        mailer.send(_Bag(), subject="x", body="y", attachments=[])


def test_resend_falls_back_to_admin_email_when_no_from(monkeypatch):
    captured = {}
    monkeypatch.setattr(mailer, "_http_post_json",
                        lambda url, headers, payload, timeout:
                        (captured.update(payload=payload), (200, b"{}"))[1])
    bag = _Bag()
    bag.MAIL_FROM = ""
    mailer.send(bag, subject="x", body="y", attachments=[])
    assert captured["payload"]["from"] == "admin@example.com"
