"""Admin authentication helpers. Single shared password from config."""

import hmac
from functools import wraps
from flask import session, redirect, url_for


def check_password(settings, candidate):
    if not candidate:
        return False
    return hmac.compare_digest(str(candidate), str(settings.ADMIN_PASSWORD))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
