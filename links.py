"""Sign and verify per-client link tokens. No client data is stored;
identity lives only inside the signed token."""

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
    }
    return _serializer(secret_key).dumps(payload)


def read_link_token(secret_key, token, *, max_age_days):
    if int(max_age_days) <= 0:
        # A zero- or negative-day validity window means the link is not valid.
        raise LinkError("link expired")
    max_age_seconds = int(max_age_days) * 24 * 60 * 60
    try:
        return _serializer(secret_key).loads(token, max_age=max_age_seconds)
    except SignatureExpired as exc:
        raise LinkError("link expired") from exc
    except BadSignature as exc:
        raise LinkError("invalid link") from exc
