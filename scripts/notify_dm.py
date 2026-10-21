#!/usr/bin/env python3
"""Send a short status DM from the bot. Usage: python scripts/notify_dm.py ok|fail
Environment: SLACK_BOT_TOKEN, SLACK_NOTIFY_USER_ID (the bot DM channel ID, D..., or a user ID).
The text carries no report data, only a link to the run.
"""
import json, os, sys, urllib.request

kind = sys.argv[1] if len(sys.argv) > 1 else "ok"
token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
target = os.environ.get("SLACK_NOTIFY_USER_ID", "").strip()
if not token or not target:
    sys.exit("skipped: SLACK_BOT_TOKEN or SLACK_NOTIFY_USER_ID not set")

run = "{}/{}/actions/runs/{}".format(
    os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
    os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_RUN_ID", ""))
text = (f":white_check_mark: Daily integrations report posted to the channel. <{run}|Run details>"
        if kind == "ok" else
        f":x: The 6 PM integrations report failed and was not posted. <{run}|Open the run> to see the error.")

req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps({"channel": target, "text": text}).encode(),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})
with urllib.request.urlopen(req, timeout=60) as resp:
    out = json.load(resp)
if not out.get("ok"):
    sys.exit(f"DM failed: {out.get('error', 'unknown error')}")
print("DM sent")
