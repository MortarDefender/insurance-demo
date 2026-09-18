"""Sign and verify per-client link tokens. No client data is stored;
identity lives only inside the signed token."""

from datetime import datetime, timezone

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


class LinkError(Exception):
    """Raised when a token is missing, tampered with, or expired."""


_SALT = "client-link"


def _clean_id(client_id):
    """Normalize the optional client ID. Strips surrounding whitespace and
    removes control characters (notably CR/LF) so it is safe to place in an
    email header and to use as a PDF password."""
    text = (client_id or "").strip()
    return "".join(ch for ch in text if ch == " " or ord(ch) >= 0x20)


def _serializer(secret_key):
    return URLSafeTimedSerializer(secret_key, salt=_SALT)


def make_link_token(secret_key, *, kind, template_id, first_name, last_name,
                    expiry_days, client_id="", lang=""):
    if kind not in ("questionnaire", "document"):
        raise ValueError("kind must be 'questionnaire' or 'document'")
    payload = {
        "kind": kind,
        "template_id": template_id,
        "first_name": first_name,
        "last_name": last_name,
        # Optional client/reference ID. Used in the email subject and as the
        # password that encrypts the generated PDF. Stored only inside the
        # signed token, never on disk. Control chars are stripped so it is safe
        # in an email header.
        "client_id": _clean_id(client_id),
        # Per-client expiry, signed into the token so it cannot be tampered with.
        "expiry_days": int(expiry_days),
    }
    # Optional forced language for the client page ('en'/'he'). When absent the
    # guest page falls back to detecting direction from the content.
    if lang in ("en", "he"):
        payload["lang"] = lang
    return _serializer(secret_key).dumps(payload)


def read_link_token(secret_key, token, *, max_age_days):
    # max_age_days is a fallback for older tokens that predate per-link expiry.
    try:
        payload, issued_at = _serializer(secret_key).loads(
            token, return_timestamp=True)
    except SignatureExpired as exc:
        raise LinkError("link expired") from exc
    except BadSignature as exc:
        raise LinkError("invalid link") from exc

    # Prefer the expiry embedded in the signed token; fall back to the caller's.
    expiry_days = int(payload.get("expiry_days", max_age_days))
    if expiry_days <= 0:
        # A zero- or negative-day validity window means the link is not valid.
        raise LinkError("link expired")

    age_seconds = (datetime.now(timezone.utc) - issued_at).total_seconds()
    if age_seconds > expiry_days * 24 * 60 * 60:
        raise LinkError("link expired")
    return payload
