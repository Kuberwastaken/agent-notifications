"""
Email reply channel for agent-notifications.

Sends an in-thread SMTP reply to an email, preserving threading headers.

Usage:
    from channels.email_reply import send
    send(config, original_msg_id, original_subject, to_addr, body)

Config keys:
    email.address   — sender address
    email.password  — Gmail app password
    email.smtp_host — default: smtp.gmail.com
    email.smtp_port — default: 587
"""

import os
import smtplib
from email.mime.text import MIMEText


def send(
    config: dict,
    original_msg_id: str,
    original_subject: str,
    to_addr: str,
    body: str,
) -> bool:
    """Send an in-thread SMTP reply. Returns True on success."""
    email_cfg = config.get("email", {})
    address   = email_cfg.get("address") or os.getenv("EMAIL_ADDRESS", "")
    password  = email_cfg.get("password") or os.getenv("EMAIL_PASSWORD", "")
    smtp_host = email_cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = email_cfg.get("smtp_port", 587)

    if not address or not password:
        raise ValueError("email.address and email.password are required")

    subject = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"]    = subject
    msg["From"]       = address
    msg["To"]         = to_addr
    msg["In-Reply-To"] = original_msg_id
    msg["References"]  = original_msg_id

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(address, password)
        server.send_message(msg)

    return True
