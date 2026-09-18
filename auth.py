"""Admin authentication helpers.

Two ways to configure the admin password:

- ``ADMIN_PASSWORD_HASH`` (preferred for production): a werkzeug password hash.
  Generate one with ``python gen_password_hash.py`` and store it as an
  environment variable / secret. The plaintext never lives on the server.
- ``ADMIN_PASSWORD`` (convenient for local dev): a plaintext password compared
  in constant time.

If both are set, the hash wins.
"""

import hmac
from functools import wraps

from flask import session, redirect, url_for
from werkzeug.security import check_password_hash


def check_password(settings, candidate):
    if not candidate:
        return False

    hashed = getattr(settings, "ADMIN_PASSWORD_HASH", None)
    if hashed:
        try:
            return check_password_hash(hashed, str(candidate))
        except Exception:
            # A malformed hash should fail closed, never crash the login.
            return False

    plain = getattr(settings, "ADMIN_PASSWORD", None)
    if plain:
        return hmac.compare_digest(str(candidate), str(plain))

    # No password configured at all: deny access rather than allow everyone.
    return False


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
