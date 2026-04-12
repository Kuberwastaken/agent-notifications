#!/usr/bin/env python3
"""
GitHub checker for agent-notifications.

Monitors a GitHub repo for new issues and PRs opened since the last run.
Uses a state file to track what's already been seen.
Outputs nothing if nothing is new.

Configuration (environment variables):
  GITHUB_TOKEN     — personal access token (read:repo scope)
  GITHUB_REPO      — e.g. "Kuberwastaken/claurst"
  GH_STATE_FILE    — path to state file (default: ~/.hermes/scripts/.gh_checker_state)
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "")    # e.g. "owner/repo"
STATE_FILE   = Path(os.getenv(
    "GH_STATE_FILE",
    Path.home() / ".hermes/scripts/.gh_checker_state"
))

# ── HELPERS ───────────────────────────────────────────────────────────────────

def gh_get(path: str) -> list | dict:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_issue_id": 0, "last_pr_id": 0}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("GH_CHECK_ERROR: GITHUB_TOKEN and GITHUB_REPO must be set", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    new_issues = []
    new_prs    = []

    try:
        # Check new issues
        issues = gh_get("issues?state=open&sort=created&direction=desc&per_page=20&filter=all")
        for item in issues:
            if "pull_request" in item:
                continue  # PRs show up in issues endpoint too
            if item["number"] > state["last_issue_id"]:
                new_issues.append(item)

        # Check new PRs
        prs = gh_get("pulls?state=open&sort=created&direction=desc&per_page=20")
        for item in prs:
            if item["number"] > state["last_pr_id"]:
                new_prs.append(item)

    except urllib.error.HTTPError as e:
        print(f"GH_CHECK_ERROR: HTTP {e.code} — {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as ex:
        print(f"GH_CHECK_ERROR: {ex}", file=sys.stderr)
        sys.exit(1)

    if not new_issues and not new_prs:
        # Nothing new — exit silently, agent stays asleep
        return

    # Update state to highest seen IDs
    all_issue_ids = [i["number"] for i in new_issues]
    all_pr_ids    = [p["number"] for p in new_prs]
    if all_issue_ids:
        state["last_issue_id"] = max(max(all_issue_ids), state["last_issue_id"])
    if all_pr_ids:
        state["last_pr_id"] = max(max(all_pr_ids), state["last_pr_id"])
    save_state(state)

    # ── Output for the agent ──────────────────────────────────────────────────
    print(f"=== NEW GITHUB ACTIVITY: {GITHUB_REPO} ===")

    if new_issues:
        print(f"\nNEW ISSUES: {len(new_issues)}")
        for i in new_issues:
            labels = ", ".join(l["name"] for l in i.get("labels", []))
            print("---")
            print(f"#{i['number']}: {i['title']}")
            print(f"By:     {i['user']['login']}")
            print(f"Labels: {labels or 'none'}")
            print(f"URL:    {i['html_url']}")
            if i.get("body"):
                print(f"Body:\n{i['body'][:500]}")

    if new_prs:
        print(f"\nNEW PRs: {len(new_prs)}")
        for p in new_prs:
            labels = ", ".join(l["name"] for l in p.get("labels", []))
            print("---")
            print(f"#{p['number']}: {p['title']}")
            print(f"By:     {p['user']['login']}")
            print(f"Branch: {p['head']['ref']} → {p['base']['ref']}")
            print(f"Labels: {labels or 'none'}")
            print(f"URL:    {p['html_url']}")
            if p.get("body"):
                print(f"Body:\n{p['body'][:500]}")


if __name__ == "__main__":
    main()
