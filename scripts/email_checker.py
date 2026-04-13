#!/usr/bin/env python3
"""
Email checker for agent-notifications.

Checks a Gmail inbox for unseen messages and outputs structured data
for the agent to act on. Outputs NOTHING if there's nothing new —
this is what prevents the agent from waking up unnecessarily.

Configuration:
  Set these environment variables or edit the CONFIG block below.

  EMAIL_ADDRESS       — agent's Gmail address
  EMAIL_PASSWORD      — Gmail app password (not account password)
                        Get one at: myaccount.google.com/apppasswords
  EMAIL_IMAP_HOST     — default: imap.gmail.com
  EMAIL_TRUSTED       — comma-separated trusted sender addresses
  EMAIL_NOREPLY       — comma-separated noreply patterns to silently skip
"""

import imaplib
import email as emaillib
from email.header import decode_header
from email.utils import parseaddr
import os
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Edit directly or set as environment variables.

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "your-agent@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")      # required — Gmail app password
IMAP_HOST     = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")

# Trusted senders: agent will reply to these in-thread
TRUSTED_SENDERS = set(
    addr.strip().lower()
    for addr in os.getenv("EMAIL_TRUSTED", "").split(",")
    if addr.strip()
)

# Patterns in sender address that indicate automated/noreply mail
NOREPLY_PATTERNS = [
    p.strip().lower()
    for p in os.getenv(
        "EMAIL_NOREPLY",
        "noreply,no-reply,mailer-daemon,bounce,donotreply,notifications.google"
    ).split(",")
    if p.strip()
]

# ── HELPERS ───────────────────────────────────────────────────────────────────

def decode_str(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for part, enc in parts:
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(part)
    return "".join(out)


def get_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except Exception:
            body = str(msg.get_payload())
    return body.strip()


def is_noreply(addr: str) -> bool:
    return any(p in addr for p in NOREPLY_PATTERNS)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if not EMAIL_PASSWORD:
        print("EMAIL_CHECK_ERROR: EMAIL_PASSWORD not set", file=sys.stderr)
        sys.exit(1)

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, "UNSEEN")
        ids = messages[0].split()

        if not ids:
            # Nothing new — exit silently, agent stays asleep
            mail.logout()
            return

        trusted_emails = []
        external_emails = []

        for uid in ids:
            status, data = mail.fetch(uid, "(RFC822)")
            msg = emaillib.message_from_bytes(data[0][1])

            sender_raw = msg["From"] or ""
            _, sender_addr = parseaddr(sender_raw)
            sender_addr = sender_addr.lower().strip()

            # Skip noreply/automated senders silently
            if is_noreply(sender_addr):
                mail.store(uid, "+FLAGS", "\\Seen")
                continue

            subject     = decode_str(msg["Subject"] or "(no subject)")
            body        = get_body(msg)[:1500]
            msg_id      = msg["Message-ID"] or ""
            in_reply_to = msg["In-Reply-To"] or ""

            info = {
                "uid":         uid.decode(),
                "from":        sender_raw,
                "from_addr":   sender_addr,
                "subject":     subject,
                "body":        body,
                "msg_id":      msg_id,
                "in_reply_to": in_reply_to,
            }

            if sender_addr in TRUSTED_SENDERS:
                trusted_emails.append(info)
            else:
                external_emails.append(info)

            # Mark seen so we don't re-process next run
            mail.store(uid, "+FLAGS", "\\Seen")

        mail.logout()

        if not trusted_emails and not external_emails:
            # Everything was noreply — still nothing to do
            return

        # ── Output for the agent ──────────────────────────────────────────────
        print("=== NEW EMAILS ===")

        if trusted_emails:
            print(f"\nTRUSTED: {len(trusted_emails)} email(s) — REPLY IN-THREAD")
            for e in trusted_emails:
                print("---")
                print(f"UID:        {e['uid']}")
                print(f"From:       {e['from']}")
                print(f"Subject:    {e['subject']}")
                print(f"MsgID:      {e['msg_id']}")
                print(f"InReplyTo:  {e['in_reply_to']}")
                print(f"Body:\n{e['body']}")

        if external_emails:
            print(f"\nEXTERNAL: {len(external_emails)} email(s) — NOTIFY OWNER")
            for e in external_emails:
                print("---")
                print(f"From:       {e['from']}")
                print(f"Subject:    {e['subject']}")
                print(f"Body:\n{e['body'][:400]}")

    except Exception as ex:
        print(f"EMAIL_CHECK_ERROR: {ex}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
