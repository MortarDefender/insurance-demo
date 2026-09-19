"""Send results to the admin.

Three modes, selected by settings.MAIL_MODE:
  - "outbox": write .eml files to disk (local testing, no network).
  - "smtp":   send via SMTP (e.g. Gmail). Works locally, but many PaaS free
              tiers (Render) block outbound SMTP ports.
  - "resend": send via the Resend HTTP API over HTTPS (port 443). Works on hosts
              that block SMTP. Needs RESEND_API_KEY and MAIL_FROM.
Switching is a config change only.
"""

import base64
import json
import os
import smtplib
import time
import urllib.error
import urllib.request
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
    mode = getattr(settings, "MAIL_MODE", "outbox")
    if mode == "resend":
        _send_resend(settings, subject=subject, body=body,
                     attachments=attachments)
    elif mode == "smtp":
        _send_smtp(settings, _build_message(settings, subject, body,
                                            attachments))
    else:
        _send_outbox(settings, _build_message(settings, subject, body,
                                              attachments))


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


# Overridable for tests: does the actual HTTP POST and returns the status code.
def _http_post_json(url, headers, payload, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def _send_resend(settings, *, subject, body, attachments):
    """Send via the Resend HTTP API (https://resend.com). Uses HTTPS (443), so
    it works on hosts that block SMTP. Requires RESEND_API_KEY and MAIL_FROM."""
    api_key = getattr(settings, "RESEND_API_KEY", "")
    mail_from = getattr(settings, "MAIL_FROM", "") or settings.ADMIN_EMAIL
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set")

    payload = {
        "from": mail_from,
        "to": [settings.ADMIN_EMAIL],
        "subject": subject,
        "text": body,
        "attachments": [
            {"filename": filename,
             "content": base64.b64encode(data).decode("ascii")}
            for filename, data in attachments
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Resend is fronted by Cloudflare, which blocks the default
        # "Python-urllib" agent (403, code 1010). Send a normal UA.
        "User-Agent": "client-portal/1.0",
        "Accept": "application/json",
    }
    timeout = getattr(settings, "MAIL_TIMEOUT", 15)
    try:
        status, raw = _http_post_json("https://api.resend.com/emails",
                                      headers, payload, timeout)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"Resend API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Resend request failed: {exc.reason}") from exc
    if status >= 300:
        raise RuntimeError(f"Resend API returned status {status}")
