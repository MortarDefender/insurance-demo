"""Israeli national ID (Teudat Zehut) validation.

The check digit uses the standard Luhn-like algorithm defined by the Israeli
Population Registry: the 9-digit number (zero-padded on the right of shorter
inputs) is valid when the weighted digit sum is divisible by 10. Each digit is
multiplied by 1 or 2 alternately; products >= 10 are reduced by summing their
own digits (equivalently subtracting 9).

This is intentionally advisory only: callers use it to warn the admin, never to
block a submission. A human owner must still verify the identity by other means.
"""


def is_valid_israeli_id(value):
    """Return True if ``value`` is a structurally valid Israeli ID number.

    Accepts strings with surrounding whitespace and shorter numbers that are
    conventionally left-padded with zeros (the registry stores 9 digits).
    Non-numeric input, empty input, or the wrong length returns False.
    """
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    # Reject if there were non-digit, non-space characters in the original.
    stripped = str(value or "").strip()
    if not stripped or any(not ch.isdigit() for ch in stripped):
        return False
    if len(digits) == 0 or len(digits) > 9:
        return False
    # Left-pad to the canonical 9 digits.
    digits = digits.zfill(9)

    total = 0
    for i, ch in enumerate(digits):
        num = int(ch) * (1 if i % 2 == 0 else 2)
        if num > 9:
            num -= 9
        total += num
    return total % 10 == 0
