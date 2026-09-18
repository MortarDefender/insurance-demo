# Client Portal (local version)

A small self-hosted site for a life insurance company. An admin manages
questionnaire and document templates and generates a unique link per client.
Clients complete a questionnaire or upload a signed document, and the result is
emailed to the admin. The site stores only templates; no client data is kept.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.example.py config.py   # then edit config.py
python app.py
```

Open http://127.0.0.1:9900 and log in at `/login`.
(The bundled local `config.py` uses password `admin123` by default. Change it.)
(Port 9900 is the default because macOS AirPlay Receiver occupies 5000. Set `PORT` in `config.py` to change it.)

## How it works

- **Admin** logs in, then creates questionnaires (in-app builder, mixed question
  types) or uploads document templates (PDF/Word).
- Each template has a **Share** button. Enter a client's first and last name to
  generate a unique link.
- The client's name is encoded inside a **signed, expiring token** in the link.
  Nothing about the client is written to disk.
- **Clients** open the link (no login):
  - Questionnaire: answer and submit. Answers are emailed to the admin.
  - Document: download, sign it themselves offline, upload the signed file. The
    file is emailed to the admin and never stored.
- Every email is titled `"<Template name> - <First> <Last>"`.

## Configuration

Edit `config.py` (never commit it):

- `ADMIN_PASSWORD` - admin login password.
- `SECRET_KEY` - long random string; signs links and sessions.
- `ADMIN_EMAIL` - where results are emailed.
- `LINK_EXPIRY_DAYS` - how long a client link is valid (default 7).
- `PORT` - local dev server port (default 9900; 5000 is taken by macOS AirPlay).
- `MAIL_MODE` - `outbox` (local, writes to `outbox/`) or `smtp` (real email).
- `SMTP_*` - only used in `smtp` mode.
- `MAX_UPLOAD_MB`, `ALLOWED_UPLOAD_EXTENSIONS` - upload limits.

## Email

In `outbox` mode, "sent" emails are written as `.eml` files in `outbox/`. Open
them in any mail client to verify. To send real email later, set
`MAIL_MODE = "smtp"` and fill in the `SMTP_*` values. No code changes needed.

## Tests

```bash
pytest -q
```

There is also an end-to-end `smoke_test.py` that runs against a live server:

```bash
python app.py        # in one terminal
python smoke_test.py # in another
```

## Notes / before real deployment (human review required)

- Passwords and secrets live only in the git-ignored `config.py`.
- Client links are signed and expire; they are reusable until expiry.
- Uploaded signed documents are emailed and never written to disk.
- Before deploying to a real URL, a responsible owner must review: HTTPS,
  password hashing, secure cookies, upload scanning, and the legal sufficiency
  of the signed-document intake process.

Prepared with AI assistance; reviewed by the responsible owner.
