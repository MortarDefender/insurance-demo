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
        maintype, subtype = _guess_mime(filename)
        msg.add_attachment(data, maintype=maintype, subtype=subtype,
                           filename=filename)
    return msg


def _guess_mime(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mapping = {
        "pdf": ("application", "pdf"),
        "doc": ("application", "msword"),
        "docx": ("application",
                 "vnd.openxmlformats-officedocument.wordprocessingml.document"),
    }
    return mapping.get(ext, ("application", "octet-stream"))


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
    # A finite timeout is essential: without it a blocked/again SMTP port (e.g.
    # Render's free tier blocks outbound SMTP) hangs the request until the WSGI
    # worker is force-killed. With a timeout the connection fails fast and the
    # caller can show a friendly error instead of crashing.
    timeout = getattr(settings, "SMTP_TIMEOUT", 15)
    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT,
                          timeout=timeout)
    try:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
