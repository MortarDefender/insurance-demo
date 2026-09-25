"""Guest-facing UI strings in English and Hebrew.

Only the client-facing pages (questionnaire, document, thank-you, error) are
translated. The admin area stays English. The active language is chosen from the
direction of the template content (see textdir.direction): Hebrew content -> he,
otherwise en. Answers and stored values are never translated, so the emailed
PDF/text stay language-independent.
"""

_STRINGS = {
    "en": {
        "lang": "en",
        # questionnaire
        "q_intro": ("Please answer the questions below and press submit. "
                    "Your answers are sent directly to us and are not stored "
                    "on this site."),
        "q_submit": "Submit",
        "q_required": "Please fill in all required fields.",
        "select_placeholder": "-- select --",
        "yes": "Yes",
        "no": "No",
        # document
        "d_intro": "Please follow these steps:",
        "d_step_download": "Download the document below.",
        "d_step_sign": "Sign it yourself (print & sign, or sign digitally).",
        "d_step_upload": ("Upload your signed copy here. It is emailed to us "
                          "and not stored on this site."),
        "d_download": "Download",
        "d_upload_label": "Upload your signed file (pdf, doc, docx)",
        "d_submit": "Send signed document",
        "d_choose_file": "Please choose your signed file.",
        "d_bad_type": "That file type is not allowed.",
        # shared
        "greeting": "Hello",
        "sent_securely": "Sent securely",
        "not_stored": "Not stored on this site",
        "sending": "Sending your response, please wait...",
        "send_failed": ("Sorry, we could not send your response just now. "
                        "Please try again in a moment."),
        "thank_you_title": "Thank you",
        "thank_you_heading": "Thank you, {name}!",
        "thank_you_body": "We have received your response. You can close this "
                          "page.",
        "link_invalid": ("This link is invalid or has expired. "
                         "Please ask for a new link."),
        "form_unavailable": "This form is no longer available.",
        "doc_unavailable": "This document is no longer available.",
        "error_title": "Link problem",
        "error_heading": "Sorry",
        # --- admin UI ---
        "a_admin": "Admin",
        "a_logout": "Log out",
        "a_back": "Back to templates",
        "a_administration": "Administration",
        "a_templates": "Templates",
        "a_templates_intro": ("Create questionnaires and documents, then "
                              "generate a secure, per-client link to share."),
        "a_questionnaires": "Questionnaires",
        "a_documents": "Documents",
        "a_name": "Name",
        "a_questions": "Questions",
        "a_file": "File",
        "a_actions": "Actions",
        "a_no_questionnaires": ("No questionnaires yet. Create your first one "
                                "above."),
        "a_no_documents": "No documents yet. Upload your first one above.",
        "a_new_questionnaire": "New questionnaire",
        "a_upload_document": "Upload document",
        "a_share": "Share",
        "a_edit": "Edit",
        "a_preview_template": "Preview",
        "a_last_modified": "Last modified",
        "a_never": "-",
        "a_delete": "Delete",
        "a_delete_q_confirm": "Delete this questionnaire?",
        "a_delete_d_confirm": "Delete this document?",
        # login
        "a_signin": "Sign in",
        "a_signin_intro": ("Enter your admin password to manage templates and "
                           "links."),
        "a_password": "Password",
        "a_login": "Log in",
        # share dialog
        "a_share_intro": ("Enter the client's details to generate a unique, "
                          "secure link."),
        "a_first_name": "First name",
        "a_last_name": "Last name",
        "a_id_optional": "ID number (optional)",
        "a_id_hint": ("Added to the email subject and used as the password to "
                      "open the emailed PDF."),
        "a_id_valid": "Valid Israeli ID number.",
        "a_id_invalid": ("This is not a valid Israeli ID number. You can still "
                         "continue."),
        "a_expiry": "Link expires in (days)",
        "a_generate": "Generate link",
        "a_close": "Close",
        "a_copy": "Copy link",
        "a_copied": "Copied to clipboard",
        "a_copy_failed": "Copy failed, select and copy manually",
        # builder
        "a_builder": "Questionnaire builder",
        "a_new_q_title": "New questionnaire",
        "a_edit_q_title": "Edit questionnaire",
        "a_builder_intro": ("Add questions of any type. Mark the ones clients "
                            "must answer."),
        "a_q_name": "Questionnaire name",
        "a_prompt": "Question",
        "a_type": "Type",
        "a_notes": "Notes",
        "a_notes_hint": "Optional guidance shown to the client under the question.",
        "a_required": "Required",
        "a_remove": "Remove",
        "a_add_question": "+ Add question",
        "a_save": "Save questionnaire",
        "a_cancel": "Cancel",
        "a_choices_intro": "Answer choices the client can pick from:",
        "a_add_choice": "+ Add choice",
        "a_cols_intro": "Column headers the client fills in:",
        "a_add_column": "+ Add column",
        "a_num_rows": "Number of rows",
        "a_preview": "Preview",
        "a_cols_top": "Column headers (top row):",
        "a_rows_left": "Row labels (left column):",
        "a_add_row": "+ Add row",
        # document upload
        "a_upload_title": "Upload document template",
        "a_upload_intro": ("Clients will download this file, sign it, and "
                           "upload their signed copy back to you."),
        "a_display_name": "Display name",
        "a_file_types": "File (pdf, doc, docx)",
        "a_upload": "Upload",
        # question type labels
        "t_text": "Short text",
        "t_number": "Number",
        "t_date": "Date",
        "t_yesno": "Yes / No",
        "t_choice": "Multiple choice",
        "t_table": "Table",
        "t_matrix": "Matrix (rows + columns)",
        # --- public landing page ---
        "h_about": "About",
        "h_services": "Services",
        "h_contact": "Contact",
        "h_admin": "Admin",
        "h_hero_eyebrow": "Life & Health Insurance",
        "h_hero_title": "Protection that puts your family first.",
        "h_hero_lead": ("{name} helps you choose the right cover with clear "
                        "advice, fair pricing, and a claims process built "
                        "around real people, not paperwork."),
        "h_cta_advisor": "Talk to an advisor",
        "h_cta_cover": "Explore cover",
        "h_trust_licensed": "Licensed & regulated",
        "h_trust_independent": "Independent advice",
        "h_trust_claims": "Fast, human claims",
        "h_stat_years": "years protecting families",
        "h_stat_claims": "claims paid on first review",
        "h_stat_response": "typical advisor response",
        "h_about_eyebrow": "About us",
        "h_about_title": "A steady partner for life's big decisions",
        "h_about_p1": ("{name} {tagline} is an independent insurance practice. "
                       "We are not tied to a single insurer, so our only job is "
                       "to find the cover that genuinely fits your circumstances "
                       "and budget."),
        "h_about_p2": ("From your first quote to a claim years down the line, "
                       "you work with advisors who know your policy and answer "
                       "the phone. We keep the process simple, transparent, and "
                       "private."),
        "h_services_eyebrow": "What we offer",
        "h_services_title": "Cover for every stage",
        "h_svc_life": "Life insurance",
        "h_svc_life_desc": ("Term and whole-of-life policies that keep your "
                            "family secure if the unexpected happens."),
        "h_svc_health": "Health & critical illness",
        "h_svc_health_desc": ("Cover that helps with treatment costs and income "
                              "if you become seriously ill."),
        "h_svc_income": "Income protection",
        "h_svc_income_desc": ("A monthly benefit that replaces part of your "
                              "income when you cannot work."),
        "h_why_eyebrow": "Why {name}",
        "h_why_title": "Advice you can trust",
        "h_why_independent": "Independent",
        "h_why_independent_desc": ("We compare the whole market and recommend "
                                   "what is right for you, not for us."),
        "h_why_transparent": "Transparent",
        "h_why_transparent_desc": ("Clear pricing and plain-language policies. "
                                   "No hidden clauses or surprise exclusions."),
        "h_why_private": "Private",
        "h_why_private_desc": ("Your information is handled with care and shared "
                               "only with the insurer providing your cover."),
        "h_contact_eyebrow": "Contact",
        "h_contact_title": "Speak with an advisor",
        "h_email": "Email",
        "h_phone": "Phone",
        "h_office": "Office",
        "h_callback_title": "Request a call back",
        "h_callback_desc": ("Send us a note and an advisor will get in touch. "
                            "This opens your email app; no data is stored on "
                            "this site."),
        "h_email_us": "Email us now",
        "h_footer_tag": "Licensed insurance advisers.",
        "h_footer_demo": ("This site is a demo portal. Cover and figures shown "
                          "are illustrative."),
    },
    "he": {
        "lang": "he",
        "q_intro": ("אנא ענו על השאלות שלהלן ולחצו על שליחה. "
                    "התשובות נשלחות אלינו ישירות ואינן נשמרות באתר זה."),
        "q_submit": "שליחה",
        "q_required": "אנא מלאו את כל שדות החובה.",
        "select_placeholder": "-- בחר --",
        "yes": "כן",
        "no": "לא",
        "d_intro": "אנא בצעו את השלבים הבאים:",
        "d_step_download": "הורידו את המסמך שלהלן.",
        "d_step_sign": "חתמו עליו בעצמכם (הדפסה וחתימה, או חתימה דיגיטלית).",
        "d_step_upload": ("העלו כאן את העותק החתום. הוא נשלח אלינו במייל "
                          "ואינו נשמר באתר זה."),
        "d_download": "הורדה",
        "d_upload_label": "העלו את הקובץ החתום (pdf, doc, docx)",
        "d_submit": "שליחת המסמך החתום",
        "d_choose_file": "אנא בחרו את הקובץ החתום.",
        "d_bad_type": "סוג קובץ זה אינו נתמך.",
        "greeting": "שלום",
        "sent_securely": "נשלח באופן מאובטח",
        "not_stored": "לא נשמר באתר זה",
        "sending": "שולח את תשובתכם, אנא המתינו...",
        "send_failed": ("מצטערים, לא הצלחנו לשלוח את תשובתכם כרגע. "
                        "אנא נסו שוב בעוד רגע."),
        "thank_you_title": "תודה",
        "thank_you_heading": "תודה, {name}!",
        "thank_you_body": "קיבלנו את תשובתכם. ניתן לסגור דף זה.",
        "link_invalid": "קישור זה אינו תקין או שפג תוקפו. אנא בקשו קישור חדש.",
        "form_unavailable": "טופס זה אינו זמין עוד.",
        "doc_unavailable": "מסמך זה אינו זמין עוד.",
        "error_title": "בעיה בקישור",
        "error_heading": "מצטערים",
        # --- admin UI ---
        "a_admin": "ניהול",
        "a_logout": "התנתקות",
        "a_back": "חזרה לתבניות",
        "a_administration": "ניהול",
        "a_templates": "תבניות",
        "a_templates_intro": ("צרו שאלונים ומסמכים, ואז הפיקו קישור מאובטח "
                              "וייחודי לכל לקוח לשיתוף."),
        "a_questionnaires": "שאלונים",
        "a_documents": "מסמכים",
        "a_name": "שם",
        "a_questions": "שאלות",
        "a_file": "קובץ",
        "a_actions": "פעולות",
        "a_no_questionnaires": "אין שאלונים עדיין. צרו את הראשון למעלה.",
        "a_no_documents": "אין מסמכים עדיין. העלו את הראשון למעלה.",
        "a_new_questionnaire": "שאלון חדש",
        "a_upload_document": "העלאת מסמך",
        "a_share": "שיתוף",
        "a_edit": "עריכה",
        "a_preview_template": "תצוגה מקדימה",
        "a_last_modified": "עודכן לאחרונה",
        "a_never": "-",
        "a_delete": "מחיקה",
        "a_delete_q_confirm": "למחוק שאלון זה?",
        "a_delete_d_confirm": "למחוק מסמך זה?",
        # login
        "a_signin": "כניסה",
        "a_signin_intro": "הזינו את סיסמת המנהל לניהול התבניות והקישורים.",
        "a_password": "סיסמה",
        "a_login": "כניסה",
        # share dialog
        "a_share_intro": "הזינו את פרטי הלקוח כדי להפיק קישור מאובטח וייחודי.",
        "a_first_name": "שם פרטי",
        "a_last_name": "שם משפחה",
        "a_id_optional": "תעודת זהות (רשות)",
        "a_id_hint": ("נוסף לנושא המייל ומשמש כסיסמה לפתיחת ה-PDF שנשלח "
                      "במייל."),
        "a_id_valid": "מספר תעודת זהות תקין.",
        "a_id_invalid": "מספר תעודת הזהות אינו תקין. ניתן להמשיך בכל זאת.",
        "a_expiry": "הקישור תקף למשך (ימים)",
        "a_generate": "הפקת קישור",
        "a_close": "סגירה",
        "a_copy": "העתקת קישור",
        "a_copied": "הועתק ללוח",
        "a_copy_failed": "ההעתקה נכשלה, סמנו והעתיקו ידנית",
        # builder
        "a_builder": "בונה השאלונים",
        "a_new_q_title": "שאלון חדש",
        "a_edit_q_title": "עריכת שאלון",
        "a_builder_intro": "הוסיפו שאלות מכל סוג. סמנו אילו הן חובה למילוי.",
        "a_q_name": "שם השאלון",
        "a_prompt": "שאלה",
        "a_type": "סוג",
        "a_notes": "הערות",
        "a_notes_hint": "הנחיה לא חובה שתוצג ללקוח מתחת לשאלה.",
        "a_required": "חובה",
        "a_remove": "הסרה",
        "a_add_question": "+ הוספת שאלה",
        "a_save": "שמירת השאלון",
        "a_cancel": "ביטול",
        "a_choices_intro": "אפשרויות מענה שהלקוח יכול לבחור מהן:",
        "a_add_choice": "+ הוספת אפשרות",
        "a_cols_intro": "כותרות העמודות שהלקוח ממלא:",
        "a_add_column": "+ הוספת עמודה",
        "a_num_rows": "מספר שורות",
        "a_preview": "תצוגה מקדימה",
        "a_cols_top": "כותרות עמודות (שורה עליונה):",
        "a_rows_left": "תוויות שורות (עמודה ימנית):",
        "a_add_row": "+ הוספת שורה",
        # document upload
        "a_upload_title": "העלאת תבנית מסמך",
        "a_upload_intro": ("הלקוחות יורידו את הקובץ, יחתמו עליו, ויעלו את "
                           "העותק החתום בחזרה אליכם."),
        "a_display_name": "שם לתצוגה",
        "a_file_types": "קובץ (pdf, doc, docx)",
        "a_upload": "העלאה",
        # question type labels
        "t_text": "טקסט קצר",
        "t_number": "מספר",
        "t_date": "תאריך",
        "t_yesno": "כן / לא",
        "t_choice": "בחירה מרובה",
        "t_table": "טבלה",
        "t_matrix": "מטריצה (שורות + עמודות)",
        # --- public landing page ---
        "h_about": "אודות",
        "h_services": "שירותים",
        "h_contact": "צור קשר",
        "h_admin": "ניהול",
        "h_hero_eyebrow": "ביטוח חיים ובריאות",
        "h_hero_title": "הגנה ששמה את המשפחה שלכם במקום הראשון.",
        "h_hero_lead": ("{name} עוזרת לכם לבחור את הכיסוי הנכון עם ייעוץ ברור, "
                        "תמחור הוגן ותהליך תביעות שנבנה סביב אנשים אמיתיים, "
                        "לא ניירת."),
        "h_cta_advisor": "שיחה עם יועץ",
        "h_cta_cover": "גילוי הכיסויים",
        "h_trust_licensed": "מורשה ומפוקח",
        "h_trust_independent": "ייעוץ עצמאי",
        "h_trust_claims": "תביעות מהירות ואנושיות",
        "h_stat_years": "שנות הגנה על משפחות",
        "h_stat_claims": "תביעות ששולמו בבדיקה ראשונה",
        "h_stat_response": "זמן מענה טיפוסי של יועץ",
        "h_about_eyebrow": "אודותינו",
        "h_about_title": "שותף יציב להחלטות הגדולות בחיים",
        "h_about_p1": ("{name} {tagline} היא סוכנות ביטוח עצמאית. איננו קשורים "
                       "למבטח יחיד, ולכן תפקידנו היחיד הוא למצוא את הכיסוי "
                       "שמתאים באמת לנסיבות ולתקציב שלכם."),
        "h_about_p2": ("מהצעת המחיר הראשונה ועד תביעה שנים קדימה, אתם עובדים "
                       "עם יועצים שמכירים את הפוליסה שלכם ועונים לטלפון. אנו "
                       "שומרים על תהליך פשוט, שקוף ופרטי."),
        "h_services_eyebrow": "מה אנחנו מציעים",
        "h_services_title": "כיסוי לכל שלב",
        "h_svc_life": "ביטוח חיים",
        "h_svc_life_desc": ("פוליסות לתקופה ולכל החיים ששומרות על ביטחון "
                            "המשפחה אם קורה הבלתי צפוי."),
        "h_svc_health": "בריאות ומחלות קשות",
        "h_svc_health_desc": ("כיסוי שמסייע בעלויות טיפול ובהכנסה אם חליתם "
                              "במחלה קשה."),
        "h_svc_income": "אובדן כושר עבודה",
        "h_svc_income_desc": ("קצבה חודשית שמחליפה חלק מההכנסה שלכם כשאינכם "
                              "יכולים לעבוד."),
        "h_why_eyebrow": "למה {name}",
        "h_why_title": "ייעוץ שאפשר לסמוך עליו",
        "h_why_independent": "עצמאי",
        "h_why_independent_desc": ("אנו משווים את כל השוק וממליצים על מה "
                                   "שנכון לכם, לא לנו."),
        "h_why_transparent": "שקוף",
        "h_why_transparent_desc": ("תמחור ברור ופוליסות בשפה פשוטה. ללא "
                                   "סעיפים נסתרים או חריגים מפתיעים."),
        "h_why_private": "פרטי",
        "h_why_private_desc": ("המידע שלכם מטופל בזהירות ומשותף רק עם המבטח "
                               "שמספק את הכיסוי שלכם."),
        "h_contact_eyebrow": "צור קשר",
        "h_contact_title": "דברו עם יועץ",
        "h_email": "אימייל",
        "h_phone": "טלפון",
        "h_office": "משרד",
        "h_callback_title": "בקשת שיחה חוזרת",
        "h_callback_desc": ("שלחו לנו הודעה ויועץ יחזור אליכם. פעולה זו פותחת "
                            "את אפליקציית המייל; לא נשמר מידע באתר זה."),
        "h_email_us": "שלחו לנו מייל",
        "h_footer_tag": "יועצי ביטוח מורשים.",
        "h_footer_demo": ("אתר זה הוא פורטל הדגמה. הכיסויים והנתונים המוצגים "
                          "הם להמחשה בלבד."),
    },
}


def lang_for(direction):
    """Map a text direction ('rtl'/'ltr') to a language code ('he'/'en')."""
    return "he" if direction == "rtl" else "en"


def strings(lang_or_dir):
    """Return the string table for a language ('he'/'en') or direction
    ('rtl'/'ltr'). Unknown values fall back to English."""
    if lang_or_dir in ("rtl", "ltr"):
        lang_or_dir = lang_for(lang_or_dir)
    return _STRINGS.get(lang_or_dir, _STRINGS["en"])


def t(lang_or_dir, key, **fmt):
    """Translate a single key. Extra kwargs are used for str.format."""
    table = strings(lang_or_dir)
    value = table.get(key, _STRINGS["en"].get(key, key))
    return value.format(**fmt) if fmt else value
