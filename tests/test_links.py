import time
import pytest
from links import make_link_token, read_link_token, LinkError


def test_round_trip_returns_payload(settings):
    token = make_link_token(
        settings.SECRET_KEY,
        kind="questionnaire",
        template_id="abc",
        first_name="Jane",
        last_name="Doe",
        expiry_days=7,
    )
    data = read_link_token(settings.SECRET_KEY, token, max_age_days=7)
    assert data["kind"] == "questionnaire"
    assert data["template_id"] == "abc"
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"


def test_tampered_token_rejected(settings):
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id="x", first_name="A", last_name="B",
                            expiry_days=7)
    with pytest.raises(LinkError):
        read_link_token(settings.SECRET_KEY, token + "junk", max_age_days=7)


def test_wrong_key_rejected(settings):
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id="x", first_name="A", last_name="B",
                            expiry_days=7)
    with pytest.raises(LinkError):
        read_link_token("other-key", token, max_age_days=7)


def test_expired_token_rejected(settings):
    # Expiry now lives inside the signed token: a zero-day link is dead on arrival.
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id="x", first_name="A", last_name="B",
                            expiry_days=0)
    with pytest.raises(LinkError):
        read_link_token(settings.SECRET_KEY, token, max_age_days=7)


def test_per_client_expiry_is_signed_into_token(settings):
    # The token carries its own expiry; the caller's max_age_days is only a
    # fallback for older tokens and must not override a valid embedded value.
    token = make_link_token(settings.SECRET_KEY, kind="questionnaire",
                            template_id="x", first_name="A", last_name="B",
                            expiry_days=30)
    data = read_link_token(settings.SECRET_KEY, token, max_age_days=1)
    assert data["expiry_days"] == 30


def test_fallback_expiry_used_for_legacy_token(settings):
    # Simulate an older token minted before per-client expiry existed.
    from links import _serializer
    legacy = _serializer(settings.SECRET_KEY).dumps({
        "kind": "document", "template_id": "x",
        "first_name": "A", "last_name": "B",
    })
    # No embedded expiry -> caller's max_age_days governs.
    data = read_link_token(settings.SECRET_KEY, legacy, max_age_days=7)
    assert data["template_id"] == "x"
    with pytest.raises(LinkError):
        read_link_token(settings.SECRET_KEY, legacy, max_age_days=0)
