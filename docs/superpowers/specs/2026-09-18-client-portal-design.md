# Client Portal - Design Spec

Date: 2026-09-18
Status: Approved design, ready for implementation planning

## Purpose

A life insurance company needs a sustainable way to collect signed papers and
questionnaire answers from clients. Today this is done by phone (questionnaires)
and by emailing PDFs for signature. This app replaces that with a self-hosted
site that has an admin area and a guest area.

Core principle: **the site stores only templates. It stores no client data.**
Client identity lives only inside a per-client signed link. When a client finishes
a task, the result is emailed to the admin and any uploaded file is deleted.

Start local-first. Deploy to a real URL later.

## Users

- **Admin** (the insurance company): one operator, password-protected.
- **Guest** (the client): opens a unique link, no login, completes one task.

## Tech stack

- Python 3.14 in a project-local virtual environment (`.venv`).
- Flask 3.1.x (installed) for routing, sessions, templates.
- Jinja2 (bundled with Flask) for HTML pages.
- `itsdangerous` (bundled with Flask) for signed, expiring per-client links.
- Email: standard library `smtplib` + `email` (used only when switching to real
  email). For local development, a simulated outbox writes emails to disk.
- Storage: plain files on disk. No database.

Rationale: minimal moving parts, auditable, and the email layer can switch from
simulated outbox to real SMTP by changing one config, with no other code changes.

## Architecture

Three logical parts:

1. Admin area - create/manage templates, generate share links.
2. Signed link - carries client name + template reference, no server-side storage.
3. Guest area - client completes the task; result is emailed and discarded.

Plus a mailer module that abstracts "send" so outbox-now / SMTP-later is a config
switch.

### Data flow

```
Admin creates template  ->  stored on disk (templates_store/)
Admin clicks Share, enters first+last name
    ->  server builds a signed token {type, template_id, first, last, exp}
    ->  produces link /c/<token>
Client opens /c/<token>
    ->  server verifies + decodes token (no lookup, no storage)
    ->  questionnaire: render questions; document: download + upload signed file
Client submits
    ->  mailer.send(subject, body, attachments)
        subject = "<Template name> - <First> <Last>"
        body    = readable answers (questionnaire) or short note (document)
        attach  = uploaded signed file (document flow)
    ->  now: write .eml + attachments into outbox/
    ->  later: send via SMTP
    ->  uploaded file deleted; nothing about the client persists
```

## Feature detail

### Admin authentication

- Single shared password stored in git-ignored `config.py` (never in code, chat,
  or version control).
- A `/login` page posts the password; on success a session cookie is set.
- All admin routes require an active session; otherwise redirect to `/login`.
- `/logout` clears the session.
- Deployment hardening (later, out of scope for local version): store a password
  hash instead of plaintext, serve over HTTPS, set secure cookie flags.

### Templates

Two template types, both stored under `templates_store/`.

Questionnaire template:
- Created via an in-app builder (no external tools, no file import in v1).
- A questionnaire has a name and an ordered list of questions.
- Each question has: prompt text, type, and a required flag.
- Supported question types: `text`, `choice` (single-select with admin-defined
  options), `yesno`, `number`, `date`.
- Stored as a JSON file: `templates_store/questionnaires/<id>.json`.
- Admin can create, view, edit, and delete questionnaires.

Document template:
- Admin uploads a file (PDF or Word) to be signed by hand.
- Has a display name.
- Stored as the uploaded file under `templates_store/documents/<id>.<ext>` plus a
  small JSON sidecar with its display name and original filename.
- Admin can upload, view/download, and delete documents.

### Share links

- Each template row in the admin list has a Share button.
- Clicking opens a popup asking for the client's first and last name.
- On submit, the server creates a signed token encoding:
  `{ type: "questionnaire"|"document", template_id, first_name, last_name, exp }`
  where `exp` is now + configurable expiry days (default 7).
- The token is signed with `itsdangerous` using a secret key from `config.py`.
- The admin is shown the resulting link `/c/<token>` to copy and send to the client.
- No record of the client or the link is stored on the server.

### Guest experience

- Opening `/c/<token>`:
  - Verify signature and expiry. If invalid or expired, show a friendly error.
  - Greet the client by first name and explain what to do.
- Questionnaire flow:
  - Render questions in order with appropriate inputs per type.
  - Enforce required fields.
  - On submit, format answers into a readable body and email to admin.
  - Show a thank-you confirmation. No answers stored on server.
- Document flow:
  - Step-by-step instructions: (1) download the template, (2) sign it yourself in
    real life, (3) upload the signed file here.
  - Provide the download.
  - Provide an upload field for the signed file.
  - On submit, email the uploaded file as an attachment to admin, then delete the
    uploaded file from disk. Show a thank-you confirmation.

### Mailer

- Single module `mailer.py` exposing `send(subject, body, attachments)`.
- Mode selected by config:
  - `outbox` (default, local): write a `.eml` file and any attachments into
    `outbox/` so the admin can open and verify them.
  - `smtp` (later): send via `smtplib` using SMTP settings from `config.py`.
- Email subject is always `"<Template name> - <First> <Last>"`.
- Recipient is the admin email address from `config.py`.

### Configuration

`config.py` (git-ignored) holds:
- `ADMIN_PASSWORD` - admin login password.
- `SECRET_KEY` - used to sign links and sessions.
- `ADMIN_EMAIL` - where results are sent.
- `LINK_EXPIRY_DAYS` - default 7.
- `MAIL_MODE` - `outbox` or `smtp`.
- SMTP settings (host, port, username, password, TLS) - used only in `smtp` mode.

A `config.example.py` is committed as a template with placeholder values.

## Storage layout

```
p/
  app.py                 # Flask app + routes
  mailer.py              # outbox now, SMTP later
  config.py              # local secrets/settings (git-ignored)
  config.example.py      # committed template
  templates_store/
    questionnaires/      # <id>.json
    documents/           # <id>.<ext> + <id>.json sidecar
  outbox/                # simulated sent emails (git-ignored)
  uploads_tmp/           # transient upload area, cleared after send (git-ignored)
  templates/             # Jinja2 HTML: base, login, admin list, builder,
                         #   guest questionnaire, guest document, thank-you, error
  static/                # CSS
  docs/superpowers/specs/
  .venv/                 # virtual environment (git-ignored)
```

## Error handling

- Invalid/expired token: friendly guest error page, no internal details leaked.
- Missing required questionnaire fields: re-render with a clear message.
- Wrong/oversized upload: reject with a clear message; enforce a max upload size
  and an allowed extension list.
- Mailer failure: show the client a "please try again / contact us" message and do
  not delete the uploaded file until send succeeds.
- Admin routes without session: redirect to login.

## Security notes (local version)

- Admin password and secret key live only in git-ignored `config.py`.
- Guest links are unguessable and signed; tampering invalidates them; they expire.
- Links are reusable until expiry (no one-time enforcement) by design, to honor the
  no-storage principle. Known trade-off, documented.
- Uploaded signed documents are deleted immediately after successful email.
- This is a local-first build. Before real deployment a human owner must review:
  HTTPS, password hashing, secure cookies, upload scanning, and any legal/
  regulatory requirements for collecting signed insurance documents and personal
  data. This spec does not establish legal sufficiency of the signature or intake
  process; that must be independently verified by the responsible owner.

## Out of scope (v1)

- Legally binding in-browser e-signatures (client signs offline and uploads).
- Importing questionnaires from external files (planned future enhancement).
- Multiple admin accounts / roles.
- One-time-use links.
- Real SMTP sending is built but disabled by default (outbox mode for local).

## Success criteria

- Admin can log in with the configured password.
- Admin can create, edit, and delete a questionnaire with mixed question types.
- Admin can upload and delete a document template.
- Admin can generate a unique share link for a named client from any template.
- A client opening a questionnaire link can answer and submit; the admin receives
  an email (in `outbox/`) titled `"<Template> - <First> <Last>"` containing the
  Q&A.
- A client opening a document link can download, then upload a signed file; the
  admin receives an email (in `outbox/`) with the file attached, titled the same
  way; the uploaded file is then deleted.
- Expired or tampered links are rejected with a friendly message.
- Nothing about the client is persisted anywhere on the server.
- Switching to real email requires only editing `config.py` (mode + SMTP), no code
  changes.

---
Prepared with AI assistance; reviewed by the responsible owner.
