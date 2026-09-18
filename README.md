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
- Each template has a **Share** button. Enter a client's first and last name,
  and optionally set how many days the link stays valid (defaults to
  `LINK_EXPIRY_DAYS`), to generate a unique link. A **Copy link** button copies
  it to the clipboard.
- The client's name and the link's expiry are encoded inside a **signed,
  expiring token** in the link. Nothing about the client is written to disk.
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
- `LINK_EXPIRY_DAYS` - default validity for new links (default 7). The admin can
  override this per client in the Share dialog (1 to 365 days).
- `PORT` - local dev server port (default 9900; 5000 is taken by macOS AirPlay).
- `MAIL_MODE` - `outbox` (local, writes to `outbox/`) or `smtp` (real email).
- `SMTP_*` - only used in `smtp` mode.
- `MAX_UPLOAD_MB`, `ALLOWED_UPLOAD_EXTENSIONS` - upload limits.

## Email

In `outbox` mode, "sent" emails are written as `.eml` files in `outbox/`. Open
them in any mail client to verify. To send real email later, set
`MAIL_MODE = "smtp"` and fill in the `SMTP_*` values. No code changes needed.

## Client ID (email subject + PDF password)

The Share dialog has an optional **ID** field (e.g. a policy or client number).
When set, it is carried inside the signed link token (never stored on the site)
and used for two things:

- It is prefixed to the email subject: `[ID] Template - First Last`.
- For questionnaires, it becomes the password that opens the emailed PDF
  (128-bit PDF standard encryption). The admin opens the PDF with the same ID.

If the ID is left blank, the subject has no prefix and the PDF is not encrypted.

Notes: the document-upload flow emails the client's own uploaded file, which is
not re-encrypted, so encryption applies to the generated questionnaire PDF only.
PDF standard encryption protects against casual access, not a determined
attacker; treat the ID as a shared secret and share it out of band.

## Languages (Hebrew / RTL)

The site handles Hebrew and other right-to-left languages automatically, with no
configuration. Direction is detected from the content itself:

- Client pages flip to a right-to-left layout when the questionnaire or document
  name is in Hebrew (English content stays left-to-right).
- Client-facing UI text (intro, buttons, step instructions, Yes/No options,
  thank-you and error pages) is shown in Hebrew for Hebrew content and English
  otherwise. Strings live in `i18n.py`; the admin area stays English.
- The emailed PDF embeds a bundled Hebrew font (`fonts/NotoSansHebrew-Regular.ttf`,
  SIL Open Font License) and reorders RTL text correctly. Mixed English/Hebrew
  content is handled per line.

Client answers, names, and question text are UTF-8 throughout, so Hebrew flows
through the email and PDF unchanged. Stored/emailed answer *values* stay
language-independent (a Yes/No question shows כן/לא but still records `Yes`/`No`).

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
