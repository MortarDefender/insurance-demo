import os
from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash)

from store import Store
from auth import check_password, login_required


def _settings_from_config():
    import config

    class S:
        pass
    s = S()
    for key in dir(config):
        if key.isupper():
            setattr(s, key, getattr(config, key))
    base = os.path.dirname(os.path.abspath(__file__))
    s.STORE_DIR = os.path.join(base, "templates_store")
    s.OUTBOX_DIR = os.path.join(base, "outbox")
    s.UPLOADS_TMP_DIR = os.path.join(base, "uploads_tmp")
    return s


def create_app(settings=None):
    if settings is None:
        settings = _settings_from_config()

    app = Flask(__name__)
    app.secret_key = settings.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_UPLOAD_MB * 1024 * 1024
    app.config["SETTINGS"] = settings
    app.config["STORE"] = Store(settings.STORE_DIR)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            if check_password(settings, request.form.get("password", "")):
                session["is_admin"] = True
                return redirect(url_for("admin"))
            flash("Incorrect password")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    def home():
        return redirect(url_for("admin"))

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
        # Checkboxes don't submit when unchecked, so a hidden flag per row
        # carries the required state and keeps indexes aligned.
        req_flags = form.getlist("q_required_flag")
        questions = []
        for i, prompt in enumerate(prompts):
            prompt = prompt.strip()
            if not prompt:
                continue
            qtype = types[i] if i < len(types) else "text"
            opts_raw = options[i] if i < len(options) else ""
            opts = [o.strip() for o in opts_raw.split("|") if o.strip()]
            is_required = (req_flags[i] == "1") if i < len(req_flags) else False
            q = {"prompt": prompt, "type": qtype, "required": is_required}
            if qtype == "choice":
                q["options"] = opts
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
                                last_name=last,
                                expiry_days=expiry_days)
        link = url_for("guest", token=token, _external=True)
        return jsonify({"link": link})


def register_guest_routes(app):
    from flask import abort, Response
    from links import read_link_token, LinkError
    import mailer
    from textdir import direction

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
            return render_template("error.html", message=(
                "This link is invalid or has expired. "
                "Please ask for a new link.")), 400

        first, last = data["first_name"], data["last_name"]
        if data["kind"] == "questionnaire":
            q = store.get_questionnaire(data["template_id"])
            if q is None:
                return render_template(
                    "error.html",
                    message="This form is no longer available."), 404
            # Direction follows the questionnaire content (name + prompts).
            q_dir = direction(q["name"], *[qq.get("prompt", "")
                                           for qq in q["questions"]])
            greeting = "שלום" if q_dir == "rtl" else "Hello"
            if request.method == "POST":
                answers, missing = [], False
                for i, question in enumerate(q["questions"]):
                    val = request.form.get(f"answer_{i}", "").strip()
                    if question.get("required") and not val:
                        missing = True
                    answers.append((question["prompt"], val))
                if missing:
                    return render_template(
                        "guest_questionnaire.html", q=q, first=first,
                        dir=q_dir, greeting=greeting,
                        error="Please fill in all required fields.")
                body_lines = [f"Client: {first} {last}", ""]
                for prompt, val in answers:
                    body_lines.append(f"Q: {prompt}")
                    body_lines.append(f"A: {val or '(no answer)'}")
                    body_lines.append("")
                import pdf_report
                pdf_bytes = pdf_report.build_questionnaire_pdf(
                    title=q["name"], first_name=first, last_name=last,
                    answers=answers)
                safe_name = "".join(ch for ch in f"{q['name']} - {first} {last}"
                                    if ch.isalnum() or ch in " -_").strip()
                pdf_filename = f"{safe_name or 'questionnaire'}.pdf"
                try:
                    mailer.send(settings,
                                subject=f"{q['name']} - {first} {last}",
                                body="\n".join(body_lines),
                                attachments=[(pdf_filename, pdf_bytes)])
                except Exception:
                    return render_template(
                        "guest_questionnaire.html", q=q, first=first,
                        dir=q_dir, greeting=greeting,
                        error="Sorry, we could not send your response just now. "
                              "Please try again in a moment."), 503
                return render_template("thank_you.html", first=first)
            return render_template("guest_questionnaire.html", q=q,
                                   first=first, dir=q_dir, greeting=greeting,
                                   error=None)

        # document flow
        doc = store.get_document(data["template_id"])
        if doc is None:
            return render_template(
                "error.html",
                message="This document is no longer available."), 404
        d_dir = direction(doc["display_name"])
        greeting = "שלום" if d_dir == "rtl" else "Hello"
        if request.method == "POST":
            file = request.files.get("file")
            if not file or file.filename == "":
                return render_template(
                    "guest_document.html", doc=doc, first=first, token=token,
                    dir=d_dir, greeting=greeting,
                    error="Please choose your signed file.")
            ext = file.filename.rsplit(".", 1)[-1].lower() \
                if "." in file.filename else ""
            if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                return render_template(
                    "guest_document.html", doc=doc, first=first, token=token,
                    dir=d_dir, greeting=greeting,
                    error="That file type is not allowed.")
            file_bytes = file.read()
            try:
                mailer.send(settings,
                            subject=f"{doc['display_name']} - {first} {last}",
                            body=f"Signed document from {first} {last} attached.",
                            attachments=[(file.filename, file_bytes)])
            except Exception:
                return render_template(
                    "guest_document.html", doc=doc, first=first, token=token,
                    dir=d_dir, greeting=greeting,
                    error="Sorry, we could not send your file just now. "
                          "Please try again in a moment."), 503
            return render_template("thank_you.html", first=first)
        return render_template("guest_document.html", doc=doc, first=first,
                               token=token, dir=d_dir, greeting=greeting,
                               error=None)

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
    app = create_app()
    port = getattr(app.config["SETTINGS"], "PORT", 9900)
    app.run(debug=True, port=port)
