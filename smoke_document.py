"""Live end-to-end test of the DOCUMENT flow against a running server."""
import json
import re
import os
import glob
import urllib.request
import urllib.parse
import http.cookiejar

BASE = os.environ.get("SMOKE_BASE", "http://127.0.0.1:9900")
cj = http.cookiejar.CookieJar()
admin = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def multipart(fields, files):
    boundary = "----smoke12345"
    lines = []
    for k, v in fields.items():
        lines.append(f"--{boundary}")
        lines.append(f'Content-Disposition: form-data; name="{k}"')
        lines.append("")
        lines.append(v)
    for k, (fname, data) in files.items():
        lines.append(f"--{boundary}")
        lines.append(
            f'Content-Disposition: form-data; name="{k}"; filename="{fname}"')
        lines.append("Content-Type: application/octet-stream")
        lines.append("")
        body_pre = ("\r\n".join(lines) + "\r\n").encode() + data + b"\r\n"
    tail = f"--{boundary}--\r\n".encode()
    body = body_pre + tail
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return body, headers


for f in glob.glob("outbox/*.eml"):
    os.remove(f)

# login
admin.open(BASE + "/login",
           data=urllib.parse.urlencode({"password": "admin123"}).encode())
print("login OK")

# upload a document template
body, headers = multipart({"display_name": "Beneficiary Form"},
                          {"file": ("beneficiary.pdf", b"%PDF-1.4 template")})
req = urllib.request.Request(BASE + "/admin/documents/new", data=body,
                             headers=headers)
admin.open(req)
html = admin.open(BASE + "/admin").read().decode()
# grab the document id from the document Share button
did = re.findall(r"openShare\('document','([a-f0-9]{32})'", html)[0]
print("uploaded document", did)

# share
r = admin.open(BASE + "/admin/share",
               data=urllib.parse.urlencode(
                   {"kind": "document", "template_id": did,
                    "first_name": "Mary", "last_name": "Smith"}).encode())
link = json.load(r)["link"]
token = link.split("/c/")[1]
print("share link:", link)

# guest (cookieless) downloads template
guest = urllib.request.build_opener()
dl = guest.open(f"{BASE}/c/{token}/download").read()
assert dl == b"%PDF-1.4 template", dl
print("guest downloaded template")

# guest uploads signed file
body, headers = multipart({}, {"file": ("signed.pdf", b"%PDF-1.4 SIGNED")})
req = urllib.request.Request(f"{BASE}/c/{token}", data=body, headers=headers)
thanks = guest.open(req).read().decode()
assert "Thank you" in thanks
print("guest uploaded signed file")

# verify email + attachment
import base64
emls = glob.glob("outbox/*.eml")
assert len(emls) == 1, emls
raw = open(emls[0], "rb").read()
assert b"Beneficiary Form - Mary Smith" in raw
assert base64.b64encode(b"%PDF-1.4 SIGNED").strip() in raw.replace(b"\n", b"")
print("email has correct subject + signed attachment")

# verify nothing about the client persisted
leaked = []
for f in glob.glob("templates_store/**/*", recursive=True):
    if os.path.isfile(f):
        t = open(f, encoding="utf-8", errors="ignore").read()
        if "Mary" in t or "Smith" in t or "SIGNED" in t:
            leaked.append(f)
assert not leaked, leaked
print("no client data persisted")
print("DOCUMENT FLOW LIVE TEST PASSED")
