"""
Slack notification channel for agent-notifications.

Sends a message to a Slack channel via incoming webhook.

Usage:
    from channels.slack import send
    send(config, "Your message here")

Config keys:
    channels.slack.webhook_url — Slack incoming webhook URL
    channels.slack.username    — optional display name (default: "Agent")
    channels.slack.icon_emoji  — optional emoji (default: ":robot_face:")
"""

import json
import os
import urllib.request


def send(config: dict, message: str) -> bool:
    """Post a message to Slack via incoming webhook. Returns True on success."""
    slack_cfg   = config.get("channels", {}).get("slack", {})
    webhook_url = slack_cfg.get("webhook_url") or os.getenv("SLACK_WEBHOOK_URL", "")
    username    = slack_cfg.get("username", "Agent")
    icon_emoji  = slack_cfg.get("icon_emoji", ":robot_face:")

    if not webhook_url:
        raise ValueError("channels.slack.webhook_url is required")

    payload = json.dumps({
        "text": message,
        "username": username,
        "icon_emoji": icon_emoji,
    }).encode()

    req = urllib.request.Request(
        webhook_url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read() == b"ok"
