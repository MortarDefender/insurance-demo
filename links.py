"""Sign and verify per-client link tokens. No client data is stored;
identity lives only inside the signed token."""

from datetime import datetime, timezone

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
        # Per-client expiry, signed into the token so it cannot be tampered with.
        "expiry_days": int(expiry_days),
    }
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
