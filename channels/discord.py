"""
Discord notification channel for agent-notifications.

Sends a message to a Discord channel via incoming webhook.

Usage:
    from channels.discord import send
    send(config, "Your message here")

Config keys:
    channels.discord.webhook_url — Discord webhook URL
    channels.discord.username    — optional display name (default: "Agent")
    channels.discord.avatar_url  — optional avatar URL
"""

import json
import os
import urllib.request


def send(config: dict, message: str) -> bool:
    """Post a message to Discord via webhook. Returns True on success."""
    discord_cfg = config.get("channels", {}).get("discord", {})
    webhook_url = discord_cfg.get("webhook_url") or os.getenv("DISCORD_WEBHOOK_URL", "")
    username    = discord_cfg.get("username", "Agent")
    avatar_url  = discord_cfg.get("avatar_url", "")

    if not webhook_url:
        raise ValueError("channels.discord.webhook_url is required")

    payload: dict = {"content": message, "username": username}
    if avatar_url:
        payload["avatar_url"] = avatar_url

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        # Discord returns 204 No Content on success
        return resp.status in (200, 204)
