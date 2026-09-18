"""Verify mailer's SMTP mode against a tiny in-process capture server.

Uses a raw-socket SMTP server (stdlib only) because Python 3.12+ removed the
smtpd module. This exercises the real smtplib send path that the app will use
in production when MAIL_MODE == "smtp".
"""
import socket
import threading
import base64

import mailer


class CaptureSMTP:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.data = b""
        self.mail_from = None
        self.rcpt_to = []
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def start(self):
        self.thread.start()

    def _serve(self):
        conn, _ = self.sock.accept()
        with conn:
            conn.sendall(b"220 capture ESMTP\r\n")
            in_data = False
            buf = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\r\n" in buf and not in_data:
                    line, buf = buf.split(b"\r\n", 1)
                    cmd = line.decode(errors="ignore")
                    up = cmd.upper()
                    if up.startswith("EHLO") or up.startswith("HELO"):
                        conn.sendall(b"250-capture\r\n250 OK\r\n")
                    elif up.startswith("MAIL FROM"):
                        self.mail_from = cmd
                        conn.sendall(b"250 OK\r\n")
                    elif up.startswith("RCPT TO"):
                        self.rcpt_to.append(cmd)
                        conn.sendall(b"250 OK\r\n")
                    elif up.startswith("DATA"):
                        conn.sendall(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                        in_data = True
                    elif up.startswith("QUIT"):
                        conn.sendall(b"221 Bye\r\n")
                        return
                    elif up.startswith("RSET"):
                        conn.sendall(b"250 OK\r\n")
                if in_data:
                    if b"\r\n.\r\n" in buf:
                        payload, buf = buf.split(b"\r\n.\r\n", 1)
                        self.data += payload
                        conn.sendall(b"250 OK queued\r\n")
                        in_data = False


class Settings:
    ADMIN_EMAIL = "admin@example.com"
    MAIL_MODE = "smtp"
    SMTP_HOST = "127.0.0.1"
    SMTP_PORT = 0          # filled in below
    SMTP_USERNAME = ""      # no auth for the capture server
    SMTP_PASSWORD = ""
    SMTP_USE_TLS = False    # capture server speaks plain SMTP


def main():
    server = CaptureSMTP()
    server.start()
    s = Settings()
    s.SMTP_PORT = server.port

    mailer.send(s,
                subject="Annual Health Review - Jane Doe",
                body="Q: Do you smoke?\nA: No\n",
                attachments=[("signed.pdf", b"%PDF-1.4 SIGNED-CONTENT")])

    # give the server thread a moment to flush
    server.thread.join(timeout=2)

    assert server.mail_from and "admin@example.com" in server.mail_from, \
        server.mail_from
    assert any("admin@example.com" in r for r in server.rcpt_to), server.rcpt_to
    assert b"Subject: Annual Health Review - Jane Doe" in server.data
    assert b"Do you smoke?" in server.data
    assert base64.b64encode(b"%PDF-1.4 SIGNED-CONTENT").strip() in \
        server.data.replace(b"\n", b""), "attachment not found in DATA"
    print("MAIL FROM:", server.mail_from.strip())
    print("RCPT TO:", [r.strip() for r in server.rcpt_to])
    print("subject + body + attachment all present in transmitted DATA")
    print("SMTP MODE LIVE TEST PASSED")


if __name__ == "__main__":
    main()
