# Changelog

## [Unreleased]

### Added
- `scripts/email_checker.py` — Gmail IMAP watcher, silent if nothing new
- `scripts/github_checker.py` — GitHub issues/PRs watcher with state file
- `scripts/rss_checker.py` — RSS/Atom feed watcher with state file
- `channels/telegram.py` — Telegram notification channel
- `channels/email_reply.py` — In-thread SMTP email reply channel
- `channels/slack.py` — Slack incoming webhook channel
- `channels/discord.py` — Discord webhook channel
- `examples/email_prompt.txt` — Agent prompt for email handling
- `examples/github_prompt.txt` — Agent prompt for GitHub activity
- `config.example.yaml` — Full configuration reference
- `HERMES_PATCH.md` — Scheduler patch for true zero-token silent runs
