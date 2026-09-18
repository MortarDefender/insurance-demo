#!/usr/bin/env python3
"""Generate a werkzeug password hash for the admin login.

Usage:
    python gen_password_hash.py                # prompts (hidden input)
    python gen_password_hash.py "my password"  # from an argument

Copy the printed hash into the ADMIN_PASSWORD_HASH environment variable (or
config.py). The plaintext is never stored anywhere.
"""
import getpass
import sys

from werkzeug.security import generate_password_hash


def main():
    if len(sys.argv) > 1:
        pw = sys.argv[1]
    else:
        pw = getpass.getpass("New admin password: ")
        again = getpass.getpass("Confirm password: ")
        if pw != again:
            print("Passwords do not match.", file=sys.stderr)
            sys.exit(1)
    if not pw:
        print("Empty password refused.", file=sys.stderr)
        sys.exit(1)
    # pbkdf2:sha256 is a solid, dependency-free default in werkzeug.
    print(generate_password_hash(pw, method="pbkdf2:sha256"))


if __name__ == "__main__":
    main()
