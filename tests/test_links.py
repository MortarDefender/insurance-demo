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
    token = make_link_token(settings.SECRET_KEY, kind="document",
                            template_id="x", first_name="A", last_name="B",
                            expiry_days=7)
    with pytest.raises(LinkError):
        read_link_token(settings.SECRET_KEY, token, max_age_days=0)
