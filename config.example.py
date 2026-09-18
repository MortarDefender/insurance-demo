# Copy to config.py and fill in real values. config.py is git-ignored.
#
# For LOCAL development you can set values here. For a PRODUCTION deploy
# (e.g. Render) prefer environment variables; they override anything here.
# See DEPLOY.md.

# Admin login password.
#   Local dev: set ADMIN_PASSWORD (plaintext) below.
#   Production: instead set the ADMIN_PASSWORD_HASH env var to the output of
#   `python gen_password_hash.py`, and leave the plaintext unset. If both are
#   present, the hash wins.
ADMIN_PASSWORD = "change-me"
# ADMIN_PASSWORD_HASH = "pbkdf2:sha256:...."  # optional; overrides the above

# Secret used to sign links and sessions. Use a long random string.
SECRET_KEY = "change-me-to-a-long-random-string"

# Where completed results are emailed.
ADMIN_EMAIL = "admin@example.com"

# How many days a client link stays valid.
LINK_EXPIRY_DAYS = 7

# Local dev server port. 5000 is taken by macOS AirPlay Receiver, so default 9900.
PORT = 9900

# "outbox" writes emails to ./outbox for local testing.
# "smtp" sends real email using the SMTP_* settings below.
MAIL_MODE = "outbox"

# Only used when MAIL_MODE == "smtp".
SMTP_HOST = ""
SMTP_PORT = 587
SMTP_USERNAME = ""
SMTP_PASSWORD = ""
SMTP_USE_TLS = True

# Upload limits for signed documents.
MAX_UPLOAD_MB = 15
ALLOWED_UPLOAD_EXTENSIONS = ["pdf", "doc", "docx"]

# Public landing page (home page). All optional; sensible defaults apply.
COMPANY_NAME = "Meridian"
COMPANY_TAGLINE = "Insurance Services"
CONTACT_EMAIL = "hello@meridian.example"
CONTACT_PHONE = "+1 (555) 010-2400"
CONTACT_ADDRESS = "100 Market Street, Suite 500, San Francisco, CA"
