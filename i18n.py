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
