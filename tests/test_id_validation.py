"""Tests for the advisory Israeli ID (Teudat Zehut) validation. This is only a
warning aid for the admin; it never blocks link generation or submission."""

from id_validation import is_valid_israeli_id


def test_known_valid_ids():
    # Structurally valid numbers (checksum passes). These are algorithmically
    # valid, not real people's identities.
    for value in ["000000018", "123456782", "030000004"]:
        assert is_valid_israeli_id(value), value


def test_known_invalid_ids():
    for value in ["123456789", "000000019", "111111111"]:
        assert not is_valid_israeli_id(value), value


def test_short_ids_are_left_padded():
    # 5-digit "3018" style inputs are conventionally padded to 9 digits.
    assert is_valid_israeli_id("18") is True  # -> 000000018


def test_whitespace_is_trimmed():
    assert is_valid_israeli_id("  123456782  ") is True


def test_non_numeric_is_invalid():
    for value in ["", "   ", "abc", "12-34", "1234567x", None]:
        assert is_valid_israeli_id(value) is False


def test_too_long_is_invalid():
    assert is_valid_israeli_id("1234567890") is False
