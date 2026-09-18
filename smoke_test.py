"""End-to-end smoke test against the running server (default port 9900)."""
import json
import re
import os
import glob
import urllib.request
import urllib.parse
import http.cookiejar

BASE = os.environ.get("SMOKE_BASE", "http://127.0.0.1:9900")
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def post(path, fields):
    data = urllib.parse.urlencode(fields, doseq=True).encode()
    return opener.open(BASE + path, data=data)


def get(path):
    return opener.open(BASE + path)


# clear outbox
for f in glob.glob("outbox/*.eml"):
    os.remove(f)

# 1. login
r = post("/login", {"password": "admin123"})
assert r.status == 200, r.status
print("login OK")

# 2. create questionnaire (mixed types)
post("/admin/questionnaires/new", [
    ("name", "Annual Health Review"),
    ("q_prompt", "Do you smoke?"), ("q_type", "yesno"),
    ("q_required_flag", "1"), ("q_options", ""),
    ("q_prompt", "Current age"), ("q_type", "number"),
    ("q_required_flag", "1"), ("q_options", ""),
])
html = get("/admin").read().decode()
qid = re.search(r"[a-f0-9]{32}", html).group(0)
print("created questionnaire", qid)

# 3. share link
r = post("/admin/share", {"kind": "questionnaire", "template_id": qid,
                          "first_name": "John", "last_name": "Client"})
link = json.load(r)["link"]
print("share link:", link)

# 4. guest opens + submits (new opener = no admin cookie, simulates client)
guest = urllib.request.build_opener()
token = link.split("/c/")[1]
page = guest.open(f"{BASE}/c/{token}").read().decode()
assert "Do you smoke?" in page and "John" in page
print("guest page renders")
gd = urllib.parse.urlencode({"answer_0": "No", "answer_1": "42"}).encode()
r = guest.open(f"{BASE}/c/{token}", data=gd)
thanks = r.read().decode()
assert "Thank you" in thanks
print("guest submitted")

# 5. verify outbox
emls = glob.glob("outbox/*.eml")
assert len(emls) == 1, emls
content = open(emls[0], encoding="utf-8").read()
assert "Annual Health Review - John Client" in content
assert "Do you smoke?" in content and "No" in content and "42" in content
print("email in outbox with correct subject + answers")
print("SMOKE TEST PASSED")
