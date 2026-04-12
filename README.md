# agent-notifications

Zero-token push notification system for AI agents. Poll any source on a schedule — only wake the agent when something actually needs attention.

Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent). Extensible to any channel or data source.

---

## How it works

```
every N minutes:
  run checker script (pure Python, no LLM)
    → nothing new? exit silently — agent never wakes up
    → something new? output structured data
      → agent wakes up, acts, delivers to configured channel
```

The key insight: the data-collection script runs cheap (no API calls, no LLM). The agent only spins up when there's actually something to do.

## Quick Start

### 1. Configure your source

Copy a checker script from `scripts/` and fill in your credentials:

```bash
cp scripts/email_checker.py scripts/my_email_checker.py
# Edit credentials and allowed senders
```

### 2. Create the cron job

```python
from hermes_tools import cronjob

cronjob(
    action="create",
    name="email-notifications",
    schedule="every 5m",
    script="my_email_checker.py",   # must live in ~/.hermes/scripts/
    prompt=open("examples/email_prompt.txt").read(),
    deliver="origin",               # or "local", or "telegram:CHAT_ID"
)
```

### 3. That's it

No new mail → script exits empty → agent never runs → zero tokens spent.
New mail from you → agent wakes, replies via SMTP.
External mail → agent wakes, pings you on Telegram.

---

## Config reference

All configuration lives in `config.yaml` (a single file per deployment):

```yaml
# config.yaml — copy and fill in your values

# --- Agent email account ---
email:
  address: valerieruntime@gmail.com
  password: "xxxx xxxx xxxx xxxx"   # Gmail app password (not account password)
  imap_host: imap.gmail.com
  smtp_host: smtp.gmail.com
  imap_port: 993
  smtp_port: 587

# --- Who is allowed to send commands ---
trusted_senders:
  - kuberhob@gmail.com
  - yokuber@gmail.com
  - kuber@polyth.ink

# --- Notification channels ---
channels:
  telegram:
    enabled: true
    chat_id: "6073534541"
  email_reply:
    enabled: true                   # reply in-thread to trusted senders
  slack:
    enabled: false
    webhook_url: ""
  discord:
    enabled: false
    webhook_url: ""

# --- Schedule ---
schedule: "every 5m"                # cron expression or human interval

# --- Noreply patterns to silently ignore ---
noreply_patterns:
  - noreply
  - no-reply
  - mailer-daemon
  - bounce
  - notifications.google
  - donotreply
```

---

## Channels

| Channel | File | Notes |
|---------|------|-------|
| Telegram | `channels/telegram.py` | Send message to a chat ID |
| Email reply | `channels/email_reply.py` | In-thread SMTP reply |
| Slack | `channels/slack.py` | Incoming webhook |
| Discord | `channels/discord.py` | Incoming webhook |

Each channel is a standalone Python module with a single `send(config, message)` function. Easy to add new ones.

---

## Checker scripts

| Script | What it monitors |
|--------|-----------------|
| `scripts/email_checker.py` | Gmail IMAP inbox for unseen emails |
| `scripts/github_checker.py` | GitHub repo for new issues/PRs |
| `scripts/rss_checker.py` | RSS/Atom feed for new entries |

Scripts follow one rule: **output nothing if there's nothing new**. This is what keeps the agent from waking up unnecessarily.

---

## Adding a new source

1. Create `scripts/my_checker.py` — outputs structured text only when there's something new, otherwise exits silently
2. Add a cron job pointing at your script
3. Write a prompt that tells the agent what to do with the output

See `scripts/email_checker.py` for the canonical pattern.

---

## Hermes scheduler patch (required for true zero-token runs)

By default, Hermes still wakes the agent even when a script produces no output (it just suppresses delivery). To truly skip the LLM:

Patch `cron/scheduler.py` in your Hermes installation — see `HERMES_PATCH.md` for the exact diff.

---

## License

MIT
