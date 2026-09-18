"""Shared text-direction helpers so the web pages and the PDF agree on when
content is right-to-left (Hebrew, Arabic, etc.)."""

import re

# Hebrew, Arabic, Syriac, and Arabic presentation-form blocks.
_RTL_RE = re.compile(
    r"[\u0590-\u05FF\u0600-\u06FF\u0700-\u074F\uFB1D-\uFDFF\uFE70-\uFEFF]")


def is_rtl(text):
    """True if the text contains any strong RTL character."""
    return bool(_RTL_RE.search(str(text or "")))


def direction(*texts):
    """Return 'rtl' if any of the given strings is RTL, else 'ltr'."""
    return "rtl" if any(is_rtl(t) for t in texts if t) else "ltr"
