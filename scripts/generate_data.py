#!/usr/bin/env python3
"""Turn the delivery-tracker sheet (CSV export) into the data file the report builders read.

Usage:
  python scripts/generate_data.py --sheet sheet.csv --out data.json [--snapshot tracker_snapshot.json]

Environment:
  REPORT_RECIPIENTS  comma-separated To: list (email only)

The snapshot carries what the sheet cannot: Total / Live counts and the live-coverage
breakdown from the partner tracker. The Slack view does not need it.
Output is deliberately quiet (counts only): this repo's Actions logs may be public.
"""
import argparse, csv, datetime, json, os, re, sys
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

SYSTEM_LABEL = {"crm": "Sales CRM", "payment partner": "Payments"}

POST_CONTRACT_STATUSES = {
    "awaiting live credentials", "certification pending", "in qa", "in dev", "to be picked up"}

TILE_STYLE = {
    "TOTAL": ["#F7F7FA", "#6B7086", "#4C5262", "#2A2F3D"],
    "LIVE": ["#F1FAF5", "#0A9D63", "#0A6B45", "#08472F"],
    "IN DEV": ["#FFF8EC", "#F5A623", "#8A6A12", "#6B5210"],
    "TO BE PICKED": ["#F4F4F8", "#6B7086", "#4B5165", "#2E313D"],
    "IN QA": ["#F1F6FE", "#2563EB", "#1D4ED8", "#16307F"],
    "CERT PENDING": ["#F6F3FF", "#522EBF", "#522EBF", "#3A1F8C"],
    "BLOCKED": ["#FEF2F1", "#E0392E", "#B3261E", "#8C1C16"],
}


def parse_date(text, today):
    """'Oct 5' / 'Sept 9' -> date, year inferred around today. None if blank/unparseable."""
    m = re.match(r"^\s*([A-Za-z]{3})[A-Za-z]*\.?\s+(\d{1,2})\s*$", text or "")
    if not m or m.group(1).lower() not in MONTHS:
        return None
    month, day = MONTHS[m.group(1).lower()], int(m.group(2))
    try:
        d = datetime.date(today.year, month, day)
    except ValueError:
        return None
    if (d - today).days > 180:
        d = d.replace(year=today.year - 1)
    elif (today - d).days > 180:
        d = d.replace(year=today.year + 1)
    return d


def fmt_date(text, today):
    d = parse_date(text, today)
    return f"{d.strftime('%b')} {d.day}" if d else "not set"


def clean_arr(text):
    t = (text or "").strip()
    return t if t and t not in ("-", "—") else "—"


def label_system(text):
    t = (text or "").strip()
    return SYSTEM_LABEL.get(t.lower(), t)


def first_line(text, limit=110):
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return line if len(line) <= limit else line[: limit - 1].rstrip() + "…"


def blocked_on_partner(row):
    """Heuristic: blocked on the partner if the comment says so, or the owner is the partner itself."""
    comment = (row.get("Comments") or "").lower()
    owner = (row.get("Owner") or "").strip().lower()
    partner = (row.get("Partner Name") or "").strip().lower()
    return "blocked on partner" in comment or (owner and owner in partner) or (partner and partner in owner)


def build(rows, today):
    D = {k: [] for k in (
        "AWAITING_CREDS", "CERT", "INQA", "INDEV", "TOBEPICKED", "CONTRACT_INPROGRESS",
        "SPYNE_BLOCKED", "PARTNER_BLOCKED", "RECENT_LIVE", "POST_CONTRACT")}
    recent = []
    for r in rows:
        name = (r.get("Partner Name") or "").strip()
        if not name:
            continue
        status = (r.get("Status") or "").strip().lower()
        system = label_system(r.get("System Type"))
        owner = (r.get("Owner") or "").strip() or "—"
        expected = fmt_date(r.get("Go Live Date"), today)
        arr = clean_arr(r.get("ARR Blocked"))
        dev_end = fmt_date(r.get("Dev End Date"), today)

        if status == "awaiting live credentials":
            D["AWAITING_CREDS"].append([name, system, expected, arr])
        elif status == "certification pending":
            D["CERT"].append([name, system, expected, arr])
        elif status == "in qa":
            D["INQA"].append([name, system, owner, dev_end, expected, arr])
        elif status == "in dev":
            D["INDEV"].append([name, system, owner, dev_end, expected, arr])
        elif status == "to be picked up":
            D["TOBEPICKED"].append(
                [name, system, owner, dev_end, expected, first_line(r.get("Comments")), arr])
        elif status == "contract in progress":
            D["CONTRACT_INPROGRESS"].append([name, system, expected, arr])
        elif status == "blocked":
            if blocked_on_partner(r):
                D["PARTNER_BLOCKED"].append([name, system, expected, arr])
            else:
                D["SPYNE_BLOCKED"].append([name, system, owner, expected, arr])
        elif status == "live":
            d = parse_date(r.get("Go Live Date"), today)
            if d and 0 <= (today - d).days <= 30:
                recent.append((d, [name, system, f"{d.strftime('%b')} {d.day}"]))

        if status in POST_CONTRACT_STATUSES:
            D["POST_CONTRACT"].append([name, system, expected, arr])

    D["RECENT_LIVE"] = [row for _, row in sorted(recent, key=lambda x: x[0], reverse=True)]
    return D


def tiles(D, snapshot):
    counts = {
        "TOTAL": snapshot.get("total", 0),
        "LIVE": snapshot.get("live", 0),
        "IN DEV": len(D["INDEV"]),
        "TO BE PICKED": len(D["TOBEPICKED"]),
        "IN QA": len(D["INQA"]),
        "CERT PENDING": len(D["CERT"]) + len(D["AWAITING_CREDS"]),
        "BLOCKED": len(D["SPYNE_BLOCKED"]) + len(D["PARTNER_BLOCKED"]),
    }
    return [[label, counts[label], *TILE_STYLE[label]] for label in TILE_STYLE]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--snapshot")
    a = ap.parse_args()

    with open(a.sheet, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        if "Partner Name" not in header or "Status" not in header:
            sys.exit("ABORT: sheet export has no Partner Name / Status columns "
                     "(login page or wrong tab?)")
        rows = list(reader)
    if not rows:
        sys.exit("ABORT: sheet export has no rows")

    today = datetime.datetime.now(IST).date()
    D = build(rows, today)

    snapshot = {}
    if a.snapshot:
        with open(a.snapshot, encoding="utf-8") as f:
            snapshot = json.load(f)
    D["LIVE"] = snapshot.get("live_coverage", [])
    D["TILES"] = tiles(D, snapshot)
    recipients = [x.strip() for x in os.environ.get("REPORT_RECIPIENTS", "").split(",") if x.strip()]
    D["TO"], D["CC"], D["BCC"] = recipients, [], []

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1)

    print("data written:",
          f"post-contract={len(D['POST_CONTRACT'])}",
          f"contract-in-progress={len(D['CONTRACT_INPROGRESS'])}",
          f"blocked={len(D['SPYNE_BLOCKED']) + len(D['PARTNER_BLOCKED'])}",
          f"recent-live={len(D['RECENT_LIVE'])}")


if __name__ == "__main__":
    main()
