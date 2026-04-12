#!/usr/bin/env python3
"""
RSS/Atom feed checker for agent-notifications.

Monitors one or more RSS/Atom feeds for new entries since the last run.
Uses a state file to track seen entry IDs/links.
Outputs nothing if nothing is new.

Configuration (environment variables):
  RSS_FEEDS      — comma-separated feed URLs
  RSS_STATE_FILE — path to state file (default: ~/.hermes/scripts/.rss_checker_state)
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────

RSS_FEEDS = [
    url.strip()
    for url in os.getenv("RSS_FEEDS", "").split(",")
    if url.strip()
]

STATE_FILE = Path(os.getenv(
    "RSS_STATE_FILE",
    Path.home() / ".hermes/scripts/.rss_checker_state"
))

# ── HELPERS ───────────────────────────────────────────────────────────────────

def load_state() -> set:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_state(seen: set):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Keep only last 500 to prevent unbounded growth
    entries = list(seen)[-500:]
    STATE_FILE.write_text(json.dumps(entries))


def fetch_feed(url: str) -> list[dict]:
    """Fetch and parse an RSS or Atom feed, return list of entries."""
    req = urllib.request.Request(url, headers={"User-Agent": "agent-notifications/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read()

    root = ET.fromstring(content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = []

    # Atom feed
    for entry in root.findall("atom:entry", ns):
        uid   = (entry.findtext("atom:id", namespaces=ns) or "").strip()
        title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
        link_el = entry.find("atom:link", ns)
        link  = (link_el.get("href", "") if link_el is not None else "").strip()
        summary = (entry.findtext("atom:summary", namespaces=ns) or
                   entry.findtext("atom:content", namespaces=ns) or "").strip()
        entries.append({"id": uid or link, "title": title, "link": link, "summary": summary[:400]})

    # RSS feed
    for item in root.findall(".//item"):
        uid   = (item.findtext("guid") or item.findtext("link") or "").strip()
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        desc  = (item.findtext("description") or "").strip()
        entries.append({"id": uid or link, "title": title, "link": link, "summary": desc[:400]})

    return entries


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if not RSS_FEEDS:
        print("RSS_CHECK_ERROR: RSS_FEEDS not set", file=sys.stderr)
        sys.exit(1)

    seen = load_state()
    new_entries = []

    for feed_url in RSS_FEEDS:
        try:
            entries = fetch_feed(feed_url)
            for entry in entries:
                if entry["id"] and entry["id"] not in seen:
                    entry["feed"] = feed_url
                    new_entries.append(entry)
        except Exception as ex:
            print(f"RSS_CHECK_WARNING: failed to fetch {feed_url}: {ex}", file=sys.stderr)

    if not new_entries:
        # Nothing new — exit silently, agent stays asleep
        return

    # Mark all new as seen
    for entry in new_entries:
        seen.add(entry["id"])
    save_state(seen)

    # ── Output for the agent ──────────────────────────────────────────────────
    print(f"=== NEW RSS ENTRIES: {len(new_entries)} ===")
    for e in new_entries:
        print("---")
        print(f"Feed:    {e['feed']}")
        print(f"Title:   {e['title']}")
        print(f"Link:    {e['link']}")
        if e["summary"]:
            print(f"Summary: {e['summary']}")


if __name__ == "__main__":
    main()
