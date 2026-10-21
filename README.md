# for_reports

Daily integrations status: a Slack screenshot posted at 6 PM IST, plus the stakeholder email builder.

Both read the delivery-tracker Google Sheet. Nothing internal lives in this repo: the sheet ID,
Slack credentials, recipients and mail endpoint are all supplied as GitHub secrets or variables.

## Slack: daily post (automated)

`.github/workflows/slack-daily.yml` runs at 18:00 IST (cron `30 12 * * *`) and on manual dispatch.
It fetches the sheet CSV, builds the data, renders `Post-Contract Stage` and `Contract in Progress`
to a PNG with headless Chrome, and uploads it to the channel.

### One-time setup

1. Create a Slack app (api.slack.com/apps, From scratch) in the workspace.
2. Under OAuth & Permissions add bot scopes `chat:write` and `files:write`, then install to the workspace.
3. In the target channel run `/invite @<bot name>`.
4. In this repo go to Settings, Secrets and variables, Actions, and add:

| Name | Kind | Value |
|---|---|---|
| `SLACK_BOT_TOKEN` | **Secret** | the `xoxb-...` token |
| `SLACK_CHANNEL_ID` | Variable | the channel ID |
| `SHEET_ID` | Secret | the Google Sheet file ID (the sheet must allow link access) |
| `SHEET_GID` | Variable | the tab's gid |
| `SLACK_NOTIFY_USER_ID` | Secret | the bot's DM channel ID (`D...`) for run status DMs (optional) |

Use a Secret for the bot token. A Variable is stored in plain text and visible to anyone with repo access.
If this repo is public, make it private (Settings, Danger Zone): the Actions logs and the workflow are public otherwise.

5. Actions tab, "Daily Slack status", Run workflow, to test before waiting for 6 PM.

### What the sheet drives

| Sheet status | Where it shows |
|---|---|
| Awaiting live credentials, Certification pending, In QA, In dev, To be picked up | Post-Contract Stage |
| Contract in progress | Contract in Progress |
| Blocked | email only (Blocked on partner if the comment says so or the owner is the partner, else Waiting on Spyne) |
| Live with a go-live date in the last 30 days | email only (Went live, last 30 days) |

## Email (manual)

The email also carries the KPI tiles and live coverage, which come from the partner tracker (login-gated,
so it cannot be fetched unattended). Keep those in a local, git-ignored `tracker_snapshot.json`
(see `tracker_snapshot.example.json`) and refresh it by hand.

```bash
export REPORT_RECIPIENTS="a@x.com,b@x.com" MAIL_TEMPLATE="..." MAIL_API_URL="https://..."
curl -fsSL "https://docs.google.com/spreadsheets/d/$SHEET_ID/export?format=csv&gid=$SHEET_GID" -o sheet.csv
python scripts/generate_data.py --sheet sheet.csv --out data.json --snapshot tracker_snapshot.json
python scripts/email_report.py data.json payload.json   # guards abort on empty data or a tile/coverage mismatch
python scripts/send_email.py payload.json
```

## Local test of the Slack image

```bash
pip install -r requirements.txt
python scripts/generate_data.py --sheet sheet.csv --out data.json
python scripts/render_slack.py --data data.json --out slack_view.png
```
