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
