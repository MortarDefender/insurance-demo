# Deploying to Render

This app is prepared for a production deployment on [Render](https://render.com).
It runs under **gunicorn**, reads all secrets from **environment variables**,
supports a **hashed admin password**, and sets **secure cookies** behind HTTPS.

Local development is unchanged: `python app.py` still uses `config.py` and runs
on port 9900 with auto-reload.

---

## 1. One-time preparation

### Generate a hashed admin password
Never store the plaintext admin password on the server.

```bash
python gen_password_hash.py
# paste the printed value into ADMIN_PASSWORD_HASH below
```

### Rotate the Gmail app password (recommended)
If the current app password was ever in a file or chat, revoke it at
<https://myaccount.google.com/apppasswords> and generate a fresh one. You will
paste the new 16-character value into `SMTP_PASSWORD`.

---

## 2. Push the repo to GitHub
Render deploys from a Git repo. `config.py` is git-ignored and will **not** be
pushed, which is correct: production uses env vars instead.

```bash
git remote add origin <your-github-repo-url>   # if not already set
git push -u origin main
```

---

## 3. Create the service on Render

**Option A - Blueprint (uses `render.yaml`):**
1. Render dashboard -> **New +** -> **Blueprint**.
2. Select your repo. Render reads `render.yaml`.
3. Fill in every value marked `sync: false` (secrets) when prompted.
4. Click **Apply**.

**Option B - Manual web service:**
1. **New +** -> **Web Service** -> select repo.
2. Runtime: Python. Build: `pip install -r requirements.txt`.
   Start: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`.
3. Add the environment variables from the table below.

---

## 4. Environment variables

| Variable | Required | Example / notes |
|---|---|---|
| `SECRET_KEY` | yes | Long random string. On Blueprint, `generateValue` does this. |
| `ADMIN_PASSWORD_HASH` | yes | Output of `gen_password_hash.py`. |
| `ADMIN_EMAIL` | yes | Where completed results are emailed. |
| `MAIL_MODE` | yes | `resend` (recommended for cloud), `smtp`, or `outbox`. |
| `RESEND_API_KEY` | for resend | Free key from https://resend.com (`re_...`). |
| `MAIL_FROM` | for resend | Verified sender. Demo: `onboarding@resend.dev`. |
| `SMTP_HOST` | for smtp | `smtp.gmail.com` (SMTP is blocked on Render free). |
| `SMTP_PORT` | for smtp | `587` |
| `SMTP_USE_TLS` | for smtp | `1` |
| `SMTP_USERNAME` | for smtp | Full Gmail address. |
| `SMTP_PASSWORD` | for smtp | Gmail 16-char app password. |
| `LINK_EXPIRY_DAYS` | no | Default 7. |
| `FLASK_DEBUG` | no | Keep `0` in production. |
| `SESSION_COOKIE_SECURE` | no | `1` in production (auto-on when `RENDER` is set). |
| `STORE_DIR` / `OUTBOX_DIR` / `UPLOADS_TMP_DIR` | no | Point at a persistent disk (see below). |
| `COMPANY_NAME`, `COMPANY_TAGLINE`, `CONTACT_*` | no | Landing-page branding. |

Environment variables always win over `config.py`, so the same code runs both
locally and in the cloud.

### Email on Render (important)
Render's free tier **blocks outbound SMTP**, so Gmail/SMTP will hang and fail
there. Use **`MAIL_MODE=resend`** (the Resend HTTP API works over HTTPS):
1. Sign up free at <https://resend.com> and create an API key.
2. Set `RESEND_API_KEY` and `MAIL_FROM`. For a quick demo you can send from
   `onboarding@resend.dev`; for production, verify your own domain in Resend and
   use an address on it.
3. Free Resend tier is ~3,000 emails/month, plenty for a demo.

---

## 5. Persistent storage (important)

The admin's questionnaire/document **templates** are stored as files in
`STORE_DIR`. Without a persistent disk, that directory is wiped on every
restart or deploy, so templates disappear.

- **Paid Render plan:** the included `render.yaml` mounts a 1 GB disk at
  `/var/data` and points the storage dirs there. Templates persist.
- **Free Render plan:** persistent disks are **not** available. Remove the
  `disk:` block from `render.yaml`. Templates will reset on redeploy. For a
  durable free setup, template storage would need to move to a database
  (not yet implemented; ask if you want this).

Client answers and uploads are never stored on disk in either case; they are
emailed and discarded, by design.

---

## 6. Free plan behaviour
The free web service **sleeps after ~15 minutes** of inactivity. The first
request after sleeping takes ~30-60 seconds to wake (cold start). Subsequent
requests are fast. This is fine for demos and low-traffic use.

---

## 7. Post-deploy smoke test
1. Visit the Render URL: the landing page should load over HTTPS.
2. Go to `/login`, sign in with your admin password.
3. Create a questionnaire, generate a share link, open it in a private window,
   submit it, and confirm the email + PDF arrive.

---

## Security note (read before real client data)
This portal intakes health/insurance answers. Before collecting real people's
data, a security/compliance owner must review:
- the PDF password scheme (standard PDF encryption is weak; the ID also travels
  in the link URL),
- data retention and lawful basis for processing,
- Gmail deliverability/spam and whether a dedicated mailbox is warranted.

Prepared with AI assistance; reviewed by the responsible owner.
