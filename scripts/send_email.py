#!/usr/bin/env python3
"""POST a built payload to the internal mail API. Usage: python scripts/send_email.py [payload.json]
Environment: MAIL_API_URL (full send-template-email URL), MAIL_TEMPLATE (used when building the payload).
"""
import json, os, sys, urllib.request

url = os.environ.get("MAIL_API_URL", "").strip()
path = sys.argv[1] if len(sys.argv) > 1 else "payload.json"
if not url:
    sys.exit("ABORT: MAIL_API_URL is not set")
with open(path, "rb") as f:
    payload = f.read()
if not json.loads(payload).get("template"):
    sys.exit("ABORT: payload has no template (set MAIL_TEMPLATE before building)")
req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60) as resp:
    body = resp.read().decode().strip()
if resp.status != 200 or body != "OK":
    sys.exit(f"ABORT: mail API answered HTTP {resp.status} {body[:80]!r}")
print("email accepted by mail API")
