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
