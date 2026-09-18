# Copy to config.py and fill in real values. config.py is git-ignored.

# Admin login password (plaintext for local; hash before real deployment).
ADMIN_PASSWORD = "change-me"

# Secret used to sign links and sessions. Use a long random string.
SECRET_KEY = "change-me-to-a-long-random-string"

# Where completed results are emailed.
ADMIN_EMAIL = "admin@example.com"

# How many days a client link stays valid.
LINK_EXPIRY_DAYS = 7

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
