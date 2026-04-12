# agent-notifications

Zero-token push notification system for AI agents. Poll any source on a schedule — only wake the agent when something actually needs attention.

Works with **Hermes Agent**, **OpenClaw**, and any other agent framework that supports scheduled tasks or cron.

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

---

## Quick Start

### 1. Configure your source

Copy a checker script from `scripts/` and fill in your credentials:

```bash
cp scripts/email_checker.py scripts/my_email_checker.py
# Edit credentials and allowed senders
```

### 2. Set up the cron job

#### Hermes Agent

```python
cronjob(
    action="create",
    name="email-notifications",
    schedule="every 5m",
    script="my_email_checker.py",   # must live in ~/.hermes/scripts/
    prompt=open("examples/email_prompt.txt").read(),
    deliver="origin",
)
```

For true zero-token silent runs (skip LLM entirely when nothing is new), apply the scheduler patch — see `HERMES_PATCH.md`.

#### OpenClaw

Add to your OpenClaw config:

```yaml
# openclaw.config.yaml
jobs:
  - name: email-notifications
    schedule: "*/5 * * * *"
    script: /path/to/scripts/my_email_checker.py
    prompt_file: /path/to/examples/email_prompt.txt
    deliver: telegram
    silent_if_empty: true   # skip agent run if script has no output
```

Or via CLI:

```bash
openclaw job create \
  --name email-notifications \
  --schedule "*/5 * * * *" \
  --script scripts/my_email_checker.py \
  --prompt examples/email_prompt.txt \
  --silent-if-empty
```

#### Any other framework / raw cron

The checker scripts are pure Python stdlib — run them from anywhere:

```bash
# In system crontab (crontab -e), every 5 mins:
*/5 * * * * OUTPUT=$(python3 /path/to/scripts/email_checker.py) && [ -n "$OUTPUT" ] && your-agent-cli send "$OUTPUT"
```

The `[ -n "$OUTPUT" ]` check means the agent only gets invoked when the script actually produced output.

### 3. That's it

No new mail → script exits empty → agent never runs → zero tokens spent.
New mail from you → agent wakes, replies via SMTP.
External mail → agent wakes, pings you on your notification channel.

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

## Checker scripts

| Script | What it monitors |
|--------|-----------------|
| `scripts/email_checker.py` | Gmail IMAP inbox for unseen emails |
| `scripts/github_checker.py` | GitHub repo for new issues/PRs |
| `scripts/rss_checker.py` | RSS/Atom feed for new entries |

All scripts follow one rule: **output nothing if there's nothing new**. This is what keeps the agent from waking up unnecessarily.

### Writing your own

A checker script is any executable that:
- Outputs nothing (or exits non-zero) when there's nothing to act on
- Outputs structured text when there is something

```python
#!/usr/bin/env python3
import sys

new_stuff = check_for_new_things()

if not new_stuff:
    sys.exit(0)   # silent — agent stays asleep

print("=== NEW STUFF ===")
for item in new_stuff:
    print(item)
```

---

## Channels

| Channel | File | Notes |
|---------|------|-------|
| Telegram | `channels/telegram.py` | Send message to a chat ID |
| Email reply | `channels/email_reply.py` | In-thread SMTP reply |
| Slack | `channels/slack.py` | Incoming webhook |
| Discord | `channels/discord.py` | Incoming webhook |

Each channel is a standalone Python module with a single `send(config, message)` function — easy to add new ones.

---

## Agent framework notes

### Hermes Agent

- Checker script goes in `~/.hermes/scripts/`
- Schedule via `cronjob` tool or `hermes cron create`
- For true zero-token runs (no LLM invocation on empty output), see `HERMES_PATCH.md`
- Delivery targets: `"origin"` (back to you), `"local"` (save to disk), `"telegram:CHAT_ID"`

### OpenClaw

- Script can live anywhere, reference by absolute path in job config
- `silent_if_empty: true` in job config achieves the same zero-token behavior natively
- Delivery handled by OpenClaw's built-in channel system — the `channels/` modules here are optional extras if you need custom delivery logic

### n8n / Make / Zapier

- Use "Run Script" node → IF node → agent node
- IF condition: script output is not empty
- No patching needed — the flow control is visual

### Raw cron + any CLI agent

```bash
*/5 * * * * OUTPUT=$(python3 /path/to/checker.py) && [ -n "$OUTPUT" ] && echo "$OUTPUT" | your-agent send
```

---

## License

MIT
