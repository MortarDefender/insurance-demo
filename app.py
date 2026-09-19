import os
from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash)

from store import Store
from auth import check_password, login_required


def _settings_from_config():
    class S:
        pass
    s = S()

    # Baseline defaults so the app runs even with no config.py and no env vars
    # set (e.g. a fresh cloud host). config.py and env vars override these.
    _DEFAULTS = {
        "SECRET_KEY": "dev-insecure-change-me",
        "ADMIN_PASSWORD": "",
        "ADMIN_PASSWORD_HASH": "",
        "ADMIN_EMAIL": "admin@example.com",
        "LINK_EXPIRY_DAYS": 7,
        "PORT": 9900,
        "MAIL_MODE": "outbox",
        "SMTP_HOST": "",
        "SMTP_PORT": 587,
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
        "SMTP_USE_TLS": True,
        "SMTP_TIMEOUT": 15,
        "RESEND_API_KEY": "",
        "MAIL_FROM": "",
        "MAIL_TIMEOUT": 15,
        "MAX_UPLOAD_MB": 15,
        "ALLOWED_UPLOAD_EXTENSIONS": ["pdf", "doc", "docx"],
    }
    for key, val in _DEFAULTS.items():
        setattr(s, key, val)

    # Base defaults from config.py when present. On a fresh cloud host there may
    # be no config.py at all; that's fine, every value can come from the
    # environment instead.
    try:
        import config
        for key in dir(config):
            if key.isupper():
                setattr(s, key, getattr(config, key))
    except ModuleNotFoundError:
        pass

    _apply_env_overrides(s)

    base = os.path.dirname(os.path.abspath(__file__))
    # Storage dirs are configurable so a host with a persistent disk can point
    # them at the mounted volume via env vars.
    s.STORE_DIR = os.environ.get("STORE_DIR",
                                 os.path.join(base, "templates_store"))
    s.OUTBOX_DIR = os.environ.get("OUTBOX_DIR", os.path.join(base, "outbox"))
    s.UPLOADS_TMP_DIR = os.environ.get("UPLOADS_TMP_DIR",
                                       os.path.join(base, "uploads_tmp"))
    return s


def _env_bool(name, default):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _apply_env_overrides(s):
    """Overlay environment variables onto the settings object. Env wins over
    config.py so the same code runs locally (config.py) and on a host (env)."""
    str_keys = [
        "SECRET_KEY", "ADMIN_PASSWORD", "ADMIN_PASSWORD_HASH", "ADMIN_EMAIL",
        "MAIL_MODE", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD",
        "RESEND_API_KEY", "MAIL_FROM",
        "COMPANY_NAME", "COMPANY_TAGLINE", "CONTACT_EMAIL", "CONTACT_PHONE",
        "CONTACT_ADDRESS",
    ]
    for key in str_keys:
        if key in os.environ:
            setattr(s, key, os.environ[key])

    int_keys = ["LINK_EXPIRY_DAYS", "PORT", "SMTP_PORT", "MAX_UPLOAD_MB"]
    for key in int_keys:
        if key in os.environ:
            try:
                setattr(s, key, int(os.environ[key]))
            except ValueError:
                pass

    if "SMTP_USE_TLS" in os.environ:
        s.SMTP_USE_TLS = _env_bool("SMTP_USE_TLS", True)

    if "ALLOWED_UPLOAD_EXTENSIONS" in os.environ:
        s.ALLOWED_UPLOAD_EXTENSIONS = [
            e.strip().lower()
            for e in os.environ["ALLOWED_UPLOAD_EXTENSIONS"].split(",")
            if e.strip()]

    # Deployment behaviour flags.
    s.DEBUG = _env_bool("FLASK_DEBUG", False)
    # Secure cookies over HTTPS. Render terminates TLS at its proxy, so default
    # this on in production and off for local plain-HTTP dev.
    s.SESSION_COOKIE_SECURE = _env_bool(
        "SESSION_COOKIE_SECURE", not s.DEBUG and _on_https_host())


def _on_https_host():
    """Heuristic: Render and most PaaS set RENDER or provide a public URL."""
    return bool(os.environ.get("RENDER") or os.environ.get("PUBLIC_HTTPS"))


def create_app(settings=None):
    if settings is None:
        settings = _settings_from_config()

    app = Flask(__name__)
    app.secret_key = settings.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_UPLOAD_MB * 1024 * 1024
    app.config["SETTINGS"] = settings
    app.config["STORE"] = Store(settings.STORE_DIR)

    # Hardened session cookies. Secure is toggled by environment so local dev
    # over plain HTTP still works while production (HTTPS) gets Secure cookies.
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=getattr(settings, "SESSION_COOKIE_SECURE", False),
    )

    # Trust the platform's proxy headers (X-Forwarded-Proto/Host) so url_for
    # builds correct https:// external links behind Render's load balancer.
    if _on_https_host():
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    from i18n import strings as i18n_strings

    def _admin_lang():
        """Admin UI language from the session ('en' default, or 'he')."""
        return "he" if session.get("admin_lang") == "he" else "en"

    @app.context_processor
    def _inject_admin_i18n():
        # Make the admin language, direction, and string table available to
        # every template (guest pages override tr/dir with their own values).
        lang = _admin_lang()
        return {
            "admin_lang": lang,
            "admin_dir": "rtl" if lang == "he" else "ltr",
            "atr": i18n_strings(lang),
            "show_lang_toggle": bool(session.get("is_admin")),
        }

    @app.route("/admin/language/<lang>")
    def set_language(lang):
        # Toggle the admin UI language. Only en/he are supported.
        session["admin_lang"] = "he" if lang == "he" else "en"
        nxt = request.referrer or url_for("admin")
        return redirect(nxt)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            if check_password(settings, request.form.get("password", "")):
                session["is_admin"] = True
                return redirect(url_for("admin"))
            flash("Incorrect password")
        return render_template("login.html", show_lang_toggle=True)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    def home():
        company = {
            "name": getattr(settings, "COMPANY_NAME", "Meridian"),
            "tagline": getattr(settings, "COMPANY_TAGLINE",
                               "Insurance Services"),
            "email": getattr(settings, "CONTACT_EMAIL",
                             "hello@meridian.example"),
            "phone": getattr(settings, "CONTACT_PHONE", "+1 (555) 010-2400"),
            "address": getattr(settings, "CONTACT_ADDRESS",
                               "100 Market Street, Suite 500, "
                               "San Francisco, CA"),
        }
        # The public site follows the same language toggle as the admin.
        lang = _admin_lang()
        return render_template("home.html", company=company,
                               dir="rtl" if lang == "he" else "ltr",
                               show_lang_toggle=True)

    @app.route("/admin")
    @login_required
    def admin():
        store = app.config["STORE"]
        return render_template(
            "admin_list.html",
            questionnaires=store.list_questionnaires(),
            documents=store.list_documents(),
            settings=settings,
        )

    register_admin_routes(app)
    register_guest_routes(app)
    return app


def register_admin_routes(app):
    from flask import jsonify
    from links import make_link_token

    settings = app.config["SETTINGS"]
    store = app.config["STORE"]

    def _parse_questions(form):
        prompts = form.getlist("q_prompt")
        types = form.getlist("q_type")
        options = form.getlist("q_options")
        # Fixed row count for table questions (one entry per question row).
        table_rows = form.getlist("q_rows")
        # Row labels for matrix questions (pipe-joined, one entry per question).
        row_labels = form.getlist("q_rowlabels")
        # Checkboxes don't submit when unchecked, so a hidden flag per row
        # carries the required state and keeps indexes aligned.
        req_flags = form.getlist("q_required_flag")
        questions = []
        for i, prompt in enumerate(prompts):
            prompt = prompt.strip()
            if not prompt:
                continue
            qtype = types[i] if i < len(types) else "text"
            valid_types = ("text", "number", "date", "yesno", "choice",
                           "table", "matrix")
            if qtype not in valid_types:
                qtype = "text"
            opts_raw = options[i] if i < len(options) else ""
            opts = [o.strip() for o in opts_raw.split("|") if o.strip()]
            is_required = (req_flags[i] == "1") if i < len(req_flags) else False
            q = {"prompt": prompt, "type": qtype, "required": is_required}
            if qtype == "choice":
                # A choice needs real options. If none were provided (e.g. the
                # client-side editor was bypassed), fall back to free text so the
                # client is never shown an empty, unanswerable dropdown.
                if len(opts) >= 1:
                    q["options"] = opts
                else:
                    q["type"] = "text"
            elif qtype == "table":
                # A table needs column headers (reusing q_options) and a fixed
                # row count. Fall back to free text if the columns are missing.
                if len(opts) >= 1:
                    q["columns"] = opts
                    try:
                        n = int(table_rows[i]) if i < len(table_rows) else 1
                    except (ValueError, TypeError):
                        n = 1
                    q["rows"] = max(1, min(n, 50))  # clamp to a sane range
                else:
                    q["type"] = "text"
            elif qtype == "matrix":
                # A matrix has both column headers (q_options) and row labels
                # (q_rowlabels); the client fills only the inner cells. Needs at
                # least one of each, else fall back to free text.
                labels_raw = row_labels[i] if i < len(row_labels) else ""
                labels = [x.strip() for x in labels_raw.split("|") if x.strip()]
                if len(opts) >= 1 and len(labels) >= 1:
                    q["columns"] = opts
                    q["row_labels"] = labels
                else:
                    q["type"] = "text"
            questions.append(q)
        return questions

    @app.route("/admin/questionnaires/new", methods=["GET", "POST"])
    @login_required
    def questionnaire_new():
        if request.method == "POST":
            name = request.form.get("name", "").strip() or "Untitled"
            questions = _parse_questions(request.form)
            store.create_questionnaire(name=name, questions=questions)
            flash("Questionnaire saved")
            return redirect(url_for("admin"))
        return render_template("questionnaire_builder.html", questionnaire=None)

    @app.route("/admin/questionnaires/<qid>/edit", methods=["GET", "POST"])
    @login_required
    def questionnaire_edit(qid):
        q = store.get_questionnaire(qid)
        if q is None:
            flash("Not found")
            return redirect(url_for("admin"))
        if request.method == "POST":
            name = request.form.get("name", "").strip() or "Untitled"
            questions = _parse_questions(request.form)
            store.update_questionnaire(qid, name=name, questions=questions)
            flash("Questionnaire updated")
            return redirect(url_for("admin"))
        return render_template("questionnaire_builder.html", questionnaire=q)

    @app.route("/admin/questionnaires/<qid>/delete", methods=["POST"])
    @login_required
    def questionnaire_delete(qid):
        store.delete_questionnaire(qid)
        flash("Questionnaire deleted")
        return redirect(url_for("admin"))

    @app.route("/admin/documents/new", methods=["GET", "POST"])
    @login_required
    def document_new():
        if request.method == "POST":
            display_name = request.form.get("display_name", "").strip() \
                or "Untitled"
            file = request.files.get("file")
            if not file or file.filename == "":
                flash("Please choose a file")
                return redirect(url_for("document_new"))
            ext = file.filename.rsplit(".", 1)[-1].lower() \
                if "." in file.filename else ""
            if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                flash("File type not allowed")
                return redirect(url_for("document_new"))
            store.create_document(display_name=display_name,
                                  original_filename=file.filename,
                                  file_bytes=file.read())
            flash("Document uploaded")
            return redirect(url_for("admin"))
        return render_template("document_upload.html")

    @app.route("/admin/documents/<did>/delete", methods=["POST"])
    @login_required
    def document_delete(did):
        store.delete_document(did)
        flash("Document deleted")
        return redirect(url_for("admin"))

    @app.route("/admin/share", methods=["POST"])
    @login_required
    def admin_share():
        kind = request.form.get("kind", "")
        template_id = request.form.get("template_id", "")
        first = request.form.get("first_name", "").strip()
        last = request.form.get("last_name", "").strip()
        client_id = request.form.get("client_id", "").strip()
        if kind not in ("questionnaire", "document") or not template_id:
            return jsonify({"error": "bad request"}), 400
        if not first or not last:
            return jsonify({"error": "first and last name required"}), 400
        # Per-client link expiry. Defaults to the global setting; clamped to a
        # sane range so a typo can't create a 100-year or already-dead link.
        default_days = settings.LINK_EXPIRY_DAYS
        raw_days = request.form.get("expiry_days", "").strip()
        if raw_days == "":
            expiry_days = default_days
        else:
            try:
                expiry_days = int(raw_days)
            except ValueError:
                return jsonify({"error": "expiry days must be a whole number"}), 400
            if expiry_days < 1 or expiry_days > 365:
                return jsonify({"error": "expiry days must be between 1 and 365"}), 400
        token = make_link_token(settings.SECRET_KEY, kind=kind,
                                template_id=template_id, first_name=first,
                                last_name=last, client_id=client_id,
                                expiry_days=expiry_days,
                                lang=("he" if session.get("admin_lang") == "he"
                                      else "en"))
        link = url_for("guest", token=token, _external=True)
        return jsonify({"link": link})


def register_guest_routes(app):
    from flask import abort, Response
    from links import read_link_token, LinkError
    import mailer
    from textdir import direction
    from i18n import strings as i18n_strings

    settings = app.config["SETTINGS"]
    store = app.config["STORE"]

    def _load(token):
        try:
            data = read_link_token(settings.SECRET_KEY, token,
                                   max_age_days=settings.LINK_EXPIRY_DAYS)
        except LinkError as exc:
            return None, str(exc)
        return data, None

    @app.route("/c/<token>", methods=["GET", "POST"])
    def guest(token):
        data, err = _load(token)
        if data is None:
            tr = i18n_strings("en")
            return render_template("error.html", message=tr["link_invalid"],
                                   dir="ltr", tr=tr), 400

        first, last = data["first_name"], data["last_name"]
        client_id = (data.get("client_id") or "").strip()
        # A link may force a language (set by the admin at share time). Otherwise
        # fall back to detecting direction from the content.
        forced_lang = data.get("lang")
        # Optional ID prefix for the email subject, e.g. "[A-1234] ...".
        subject_prefix = f"[{client_id}] " if client_id else ""
        if data["kind"] == "questionnaire":
            q = store.get_questionnaire(data["template_id"])
            if forced_lang in ("en", "he"):
                q_dir = "rtl" if forced_lang == "he" else "ltr"
            else:
                # Direction follows the questionnaire content (name + prompts).
                q_dir = direction(q["name"], *[qq.get("prompt", "")
                                               for qq in q["questions"]]) \
                    if q else "ltr"
            tr = i18n_strings(q_dir)
            if q is None:
                return render_template(
                    "error.html", message=tr["form_unavailable"],
                    dir=q_dir, tr=tr), 404
            greeting = tr["greeting"]
            if request.method == "POST":
                answers, missing = [], False
                for i, question in enumerate(q["questions"]):
                    if question.get("type") == "table":
                        cols = question.get("columns", [])
                        nrows = int(question.get("rows", 1))
                        grid = []
                        all_filled = True
                        for r in range(nrows):
                            row_vals = []
                            for c in range(len(cols)):
                                cell = request.form.get(
                                    f"answer_{i}_r{r}_c{c}", "").strip()
                                if not cell:
                                    all_filled = False
                                row_vals.append(cell)
                            grid.append(row_vals)
                        # Required means the whole table must be filled.
                        if question.get("required") and not all_filled:
                            missing = True
                        answers.append((question["prompt"],
                                        {"columns": cols, "rows": grid}))
                    elif question.get("type") == "matrix":
                        cols = question.get("columns", [])
                        labels = question.get("row_labels", [])
                        grid = []
                        all_filled = True
                        for r in range(len(labels)):
                            row_vals = []
                            for c in range(len(cols)):
                                cell = request.form.get(
                                    f"answer_{i}_r{r}_c{c}", "").strip()
                                if not cell:
                                    all_filled = False
                                row_vals.append(cell)
                            grid.append(row_vals)
                        if question.get("required") and not all_filled:
                            missing = True
                        answers.append((question["prompt"],
                                        {"columns": cols, "row_labels": labels,
                                         "rows": grid}))
                    else:
                        val = request.form.get(f"answer_{i}", "").strip()
                        if question.get("required") and not val:
                            missing = True
                        answers.append((question["prompt"], val))
                if missing:
                    return render_template(
                        "guest_questionnaire.html", q=q, first=first,
                        dir=q_dir, greeting=greeting, tr=tr,
                        error=tr["q_required"])
                body_lines = [f"Client: {first} {last}", ""]
                for prompt, val in answers:
                    body_lines.append(f"Q: {prompt}")
                    if isinstance(val, dict):
                        cols = val.get("columns", [])
                        labels = val.get("row_labels")
                        if labels:
                            # Matrix: header row has a leading blank corner,
                            # each data row is prefixed with its label.
                            body_lines.append("   " + " | ".join([""] + cols))
                            for lbl, row in zip(labels, val.get("rows", [])):
                                cells = [c or "-" for c in row]
                                body_lines.append("   " + " | ".join([lbl] + cells))
                        else:
                            # Plain table: columns only.
                            body_lines.append("   " + " | ".join(cols))
                            for row in val.get("rows", []):
                                cells = [c or "-" for c in row]
                                body_lines.append("   " + " | ".join(cells))
                    else:
                        body_lines.append(f"A: {val or '(no answer)'}")
                    body_lines.append("")
                import pdf_report
                pdf_bytes = pdf_report.build_questionnaire_pdf(
                    title=q["name"], first_name=first, last_name=last,
                    answers=answers, password=client_id)
                safe_name = "".join(ch for ch in f"{q['name']} - {first} {last}"
                                    if ch.isalnum() or ch in " -_").strip()
                pdf_filename = f"{safe_name or 'questionnaire'}.pdf"
                try:
                    mailer.send(settings,
                                subject=f"{subject_prefix}{q['name']} - "
                                        f"{first} {last}",
                                body="\n".join(body_lines),
                                attachments=[(pdf_filename, pdf_bytes)])
                except Exception:
                    app.logger.exception("Failed to send questionnaire email")
                    return render_template(
                        "guest_questionnaire.html", q=q, first=first,
                        dir=q_dir, greeting=greeting, tr=tr,
                        error=tr["send_failed"]), 503
                return render_template("thank_you.html", first=first,
                                       dir=q_dir, tr=tr)
            return render_template("guest_questionnaire.html", q=q,
                                   first=first, dir=q_dir, greeting=greeting,
                                   tr=tr, error=None)

        # document flow
        doc = store.get_document(data["template_id"])
        if forced_lang in ("en", "he"):
            d_dir = "rtl" if forced_lang == "he" else "ltr"
        else:
            d_dir = direction(doc["display_name"]) if doc else "ltr"
        tr = i18n_strings(d_dir)
        if doc is None:
            return render_template(
                "error.html", message=tr["doc_unavailable"],
                dir=d_dir, tr=tr), 404
        greeting = tr["greeting"]
        if request.method == "POST":
            file = request.files.get("file")
            if not file or file.filename == "":
                return render_template(
                    "guest_document.html", doc=doc, first=first, token=token,
                    dir=d_dir, greeting=greeting, tr=tr,
                    error=tr["d_choose_file"])
            ext = file.filename.rsplit(".", 1)[-1].lower() \
                if "." in file.filename else ""
            if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                return render_template(
                    "guest_document.html", doc=doc, first=first, token=token,
                    dir=d_dir, greeting=greeting, tr=tr,
                    error=tr["d_bad_type"])
            file_bytes = file.read()
            try:
                mailer.send(settings,
                            subject=f"{subject_prefix}{doc['display_name']} - "
                                    f"{first} {last}",
                            body=f"Signed document from {first} {last} attached.",
                            attachments=[(file.filename, file_bytes)])
            except Exception:
                app.logger.exception("Failed to send signed-document email")
                return render_template(
                    "guest_document.html", doc=doc, first=first, token=token,
                    dir=d_dir, greeting=greeting, tr=tr,
                    error=tr["send_failed"]), 503
            return render_template("thank_you.html", first=first,
                                   dir=d_dir, tr=tr)
        return render_template("guest_document.html", doc=doc, first=first,
                               token=token, dir=d_dir, greeting=greeting,
                               tr=tr, error=None)

    @app.route("/c/<token>/download")
    def guest_download(token):
        data, err = _load(token)
        if data is None or data["kind"] != "document":
            abort(400)
        doc = store.get_document(data["template_id"])
        if doc is None:
            abort(404)
        content = store.read_document_bytes(data["template_id"])
        return Response(
            content,
            headers={
                "Content-Disposition":
                    f'attachment; filename="{doc["original_filename"]}"',
                "Content-Type": "application/octet-stream",
            },
        )


if __name__ == "__main__":
    # Local development entry point only. In production the app is served by
    # gunicorn via wsgi.py (debug always off). Running `python app.py` locally
    # defaults to debug/auto-reload unless FLASK_DEBUG=0 is set.
    app = create_app()
    settings = app.config["SETTINGS"]
    port = getattr(settings, "PORT", 9900)
    local_debug = _env_bool("FLASK_DEBUG", True)
    app.run(debug=local_debug, port=port)
