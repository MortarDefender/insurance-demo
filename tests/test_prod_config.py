"""Tests for production config: env-var overlay, hashed admin password, and
hardened session cookies."""
import importlib
import os

import pytest

import app as app_module
from auth import check_password
from werkzeug.security import generate_password_hash


class _Bag:
    pass


def test_env_overrides_win_over_config(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "env-secret")
    monkeypatch.setenv("LINK_EXPIRY_DAYS", "21")
    monkeypatch.setenv("MAIL_MODE", "outbox")
    monkeypatch.setenv("SMTP_USE_TLS", "0")
    monkeypatch.setenv("ALLOWED_UPLOAD_EXTENSIONS", "pdf, png ,JPG")
    s = app_module._settings_from_config()
    assert s.SECRET_KEY == "env-secret"
    assert s.LINK_EXPIRY_DAYS == 21 and isinstance(s.LINK_EXPIRY_DAYS, int)
    assert s.MAIL_MODE == "outbox"
    assert s.SMTP_USE_TLS is False
    assert s.ALLOWED_UPLOAD_EXTENSIONS == ["pdf", "png", "jpg"]


def test_invalid_int_env_is_ignored(monkeypatch):
    monkeypatch.setenv("LINK_EXPIRY_DAYS", "not-a-number")
    monkeypatch.setenv("SECRET_KEY", "x")
    s = app_module._settings_from_config()
    # Falls back to config.py's value rather than crashing.
    assert isinstance(getattr(s, "LINK_EXPIRY_DAYS", 7), int)


def test_hashed_password_is_accepted_and_plaintext_ignored_when_hash_set():
    s = _Bag()
    s.ADMIN_PASSWORD_HASH = generate_password_hash("correct-horse")
    s.ADMIN_PASSWORD = "different-plaintext"
    assert check_password(s, "correct-horse") is True
    assert check_password(s, "different-plaintext") is False
    assert check_password(s, "") is False


def test_plaintext_password_still_works_without_hash():
    s = _Bag()
    s.ADMIN_PASSWORD = "local-dev-pw"
    assert check_password(s, "local-dev-pw") is True
    assert check_password(s, "wrong") is False


def test_no_password_configured_denies_everyone():
    s = _Bag()
    assert check_password(s, "anything") is False


def test_malformed_hash_fails_closed():
    s = _Bag()
    s.ADMIN_PASSWORD_HASH = "not-a-real-hash"
    assert check_password(s, "anything") is False


def test_cookies_hardened(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 16)
    monkeypatch.setenv("ADMIN_PASSWORD", "p")
    app = app_module.create_app()
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_secure_cookies_and_proxyfix_on_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("SECRET_KEY", "x" * 16)
    monkeypatch.setenv("ADMIN_PASSWORD", "p")
    app = app_module.create_app()
    assert app.config["SESSION_COOKIE_SECURE"] is True
    from werkzeug.middleware.proxy_fix import ProxyFix
    assert isinstance(app.wsgi_app, ProxyFix)
