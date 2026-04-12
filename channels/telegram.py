"""
Telegram notification channel for agent-notifications.

Usage:
    from channels.telegram import send
    send(config, "Your message here")

Config keys:
    telegram.chat_id    — Telegram chat ID to send to
    telegram.bot_token  — Bot token (or uses TELEGRAM_BOT_TOKEN env var)
"""

import json
import os
import urllib.request


def send(config: dict, message: str) -> bool:
    """Send a message to a Telegram chat. Returns True on success."""
    telegram_cfg = config.get("channels", {}).get("telegram", {})
    chat_id   = telegram_cfg.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID", "")
    bot_token = telegram_cfg.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN", "")

    if not chat_id or not bot_token:
        raise ValueError("telegram.chat_id and telegram.bot_token are required")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }).encode()

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
        return result.get("ok", False)
