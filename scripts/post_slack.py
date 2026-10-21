#!/usr/bin/env python3
"""Upload an image to a Slack channel with the bot token (Slack's external-upload flow).

Usage: python scripts/post_slack.py --image slack_view.png [--comment "text"]
Environment: SLACK_BOT_TOKEN (xoxb-...), SLACK_CHANNEL_ID
The bot needs the files:write and chat:write scopes and must be a member of the channel.
Prints nothing but success/failure: the token never reaches the logs.
"""
import argparse, datetime, json, os, sys, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

API = "https://slack.com/api/"


def call(method, token, *, form=None, body=None):
    if form is not None:
        data, ctype = urllib.parse.urlencode(form).encode(), "application/x-www-form-urlencoded"
    else:
        data, ctype = json.dumps(body).encode(), "application/json; charset=utf-8"
    req = urllib.request.Request(API + method, data=data, headers={
        "Authorization": f"Bearer {token}", "Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.load(resp)
    if not out.get("ok"):
        sys.exit(f"ABORT: Slack {method} failed: {out.get('error', 'unknown error')}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--comment")
    a = ap.parse_args()

    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    channel = os.environ.get("SLACK_CHANNEL_ID", "").strip()
    if not token or not channel:
        sys.exit("ABORT: SLACK_BOT_TOKEN and SLACK_CHANNEL_ID must be set")

    with open(a.image, "rb") as f:
        png = f.read()
    today = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    comment = a.comment or f"Integrations status, {today.strftime('%-d %b %Y')}"
    name = f"integrations-status-{today.strftime('%Y-%m-%d')}.png"

    slot = call("files.getUploadURLExternal", token, form={"filename": name, "length": len(png)})
    up = urllib.request.Request(slot["upload_url"], data=png, method="POST",
                                headers={"Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(up, timeout=120) as resp:
        if resp.status != 200:
            sys.exit(f"ABORT: image upload returned HTTP {resp.status}")
    call("files.completeUploadExternal", token, body={
        "files": [{"id": slot["file_id"], "title": name}],
        "channel_id": channel, "initial_comment": comment})
    print("posted to Slack")


if __name__ == "__main__":
    main()
