#!/usr/bin/env python3
"""Build the send-template-email payload for the Integrations Status report.

HTMLdata is a complete HTML document: doctype, <head> with a real stylesheet,
and a <body>. Every element ALSO carries the equivalent inline style, because
Gmail deletes <style> blocks outright — the stylesheet gives the markup proper
structure and the responsive rules, the inline styles guarantee it renders.

Writes the payload for scripts/send_email.py.
"""
import json, datetime, os, sys
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# ------------------------------------------------- data + recipients from JSON
def load(path):
    with open(path) as f:
        return json.load(f)

STYLESHEET = """
    body, table, td { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    body { margin: 0; padding: 0; width: 100% !important;
           background-color: #EFEDF6;
           font-family: Arial, Helvetica, sans-serif; color: #0F1B33; }
    table { border-collapse: collapse; }

    .page       { background-color: #EFEDF6; }
    .page-pad   { padding: 20px 10px; }
    .card       { width: 720px; max-width: 100%; background-color: #FFFFFF;
                  border-radius: 12px; }

    .masthead        { background-color: #1B1442; padding: 24px 26px;
                       border-radius: 12px 12px 0 0; }
    .masthead-brand  { font-size: 20px; font-weight: bold; color: #FFFFFF; }
    .masthead-suffix { font-size: 20px; color: #B9AEE8; }
    .masthead-meta   { font-size: 12px; color: #9A8DD0; }

    .tiles      { padding: 20px 26px 0; }
    .tile       { padding: 10px 8px; }
    .tile-gap   { width: 1px; }
    .tile-label { font-size: 9px; letter-spacing: 1px; font-weight: bold; }
    .tile-value { font-size: 23px; font-weight: bold; }

    .section        { padding: 20px 26px 0; }
    .section-first  { padding: 24px 26px 0; }
    .section-last   { padding: 20px 26px 26px; }
    .section-title  { padding-left: 9px; font-size: 11px; letter-spacing: 1px;
                      color: #0F1B33; font-weight: bold; }
    .section-count  { font-size: 11px; color: #6B7086; }

    .grid       { margin-top: 10px; }
    .grid th,
    .col-head   { padding: 8px 12px; font-size: 9px; letter-spacing: 1px;
                  font-weight: bold; text-align: left; }
    .cell-partner { padding: 10px 12px; font-size: 13px; font-weight: bold;
                    color: #0F1B33; }
    .cell-text    { padding: 10px 12px; font-size: 12px; color: #3B4257; }
    .cell-date    { padding: 10px 12px; font-size: 12px; font-weight: bold;
                    color: #0F1B33; }
    .cell-unset   { padding: 10px 12px; font-size: 12px; color: #6B7086; }
    .cell-partners { padding: 10px 12px; font-size: 12px; color: #3B4257;
                     line-height: 1.7; }
    .rule       { border-bottom: 1px solid #F0EEF9; }
    .clear-note { padding: 11px 12px; font-size: 12px; color: #0A6B45; }

    @media only screen and (max-width: 600px) {
      .card      { width: 100% !important; border-radius: 0 !important; }
      .page-pad  { padding: 0 !important; }
      .masthead  { padding: 18px 16px !important; border-radius: 0 !important; }
      .tiles,
      .section,
      .section-first,
      .section-last { padding-left: 14px !important; padding-right: 14px !important; }
      .tile      { display: block !important; width: 100% !important; }
      .tile-gap  { display: none !important; }
      .col-head,
      .cell-partner, .cell-text, .cell-date,
      .cell-unset, .cell-partners { padding: 8px 8px !important;
                                    font-size: 11px !important; }
    }
"""

BB = "border-bottom:1px solid #F0EEF9"

def col_head(label, fg, border):
    return (f'<th class="col-head" align="left" style="padding:8px 12px;font-size:9px;'
            f'letter-spacing:1px;color:{fg};font-weight:bold;text-align:left;'
            f'border-bottom:1px solid {border}">{label}</th>')

def cell(kind, v, last):
    e = "" if last else ';' + BB
    if kind == 'p':
        return (f'<td class="cell-partner{"" if last else " rule"}" style="padding:10px 12px;'
                f'font-size:13px;font-weight:bold;color:#0F1B33{e}">{v}</td>')
    if kind == 't':
        return (f'<td class="cell-text{"" if last else " rule"}" style="padding:10px 12px;'
                f'font-size:12px;color:#3B4257{e}">{v}</td>')
    unset = v in ("not set", "—")
    cls = "cell-unset" if unset else "cell-date"
    col = "#6B7086" if unset else "#0F1B33"
    w   = "" if unset else "font-weight:bold;"
    return (f'<td class="{cls}{"" if last else " rule"}" style="padding:10px 12px;'
            f'font-size:12px;{w}color:{col}{e}">{v}</td>')

def section(title, count, bar, bg, fg, border, headers, rows, kinds, cls="section"):
    pad = {"section": "20px 26px 0", "section-first": "24px 26px 0",
           "section-last": "20px 26px 26px"}[cls]
    head = ''.join(col_head(x, fg, border) for x in headers)
    body = ''.join('<tr>' + ''.join(cell(k, v, i == len(rows) - 1)
                                    for k, v in zip(kinds, r)) + '</tr>'
                   for i, r in enumerate(rows))
    return (f'<tr><td class="{cls}" style="padding:{pad}">'
            f'<table class="section-head" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td class="section-title" style="border-left:3px solid {bar};padding-left:9px;'
            f'font-size:11px;letter-spacing:1px;color:#0F1B33;font-weight:bold">{title}</td>'
            f'<td class="section-count" align="right" style="font-size:11px;color:#6B7086">{count}</td>'
            f'</tr></table>'
            f'<table class="grid" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin-top:10px;border:1px solid {border}">'
            f'<thead><tr bgcolor="{bg}" style="background-color:{bg}">{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></td></tr>')

def build_html(D, now):
    date_line = now.strftime("%-d %B %Y")
    time_line = now.strftime("%I:%M %p IST").lstrip("0")

    n_tiles = len(D['TILES'])
    tile_pct = round(100 / n_tiles, 2)
    tiles = ''
    for i, (label, val, bg, bar, fg, num) in enumerate(D['TILES']):
        if i:
            tiles += '<td class="tile-gap" width="1"></td>'
        tiles += (f'<td class="tile" width="{tile_pct}%" bgcolor="{bg}" style="background-color:{bg};'
                  f'border-top:3px solid {bar};padding:10px 8px;width:{tile_pct}%">'
                  f'<span class="tile-label" style="font-size:9px;letter-spacing:1px;color:{fg};'
                  f'font-weight:bold">{label}</span><br>'
                  f'<span class="tile-value" style="font-size:23px;font-weight:bold;color:{num}">'
                  f'{val}</span></td>')

    rows = ''
    for i, (name, n, partners) in enumerate(D['LIVE']):
        last = i == len(D['LIVE']) - 1
        e = "" if last else ';' + BB
        rows += (f'<tr><td class="cell-partner{"" if last else " rule"}" width="140" valign="top" '
                 f'style="padding:10px 12px;font-size:13px;font-weight:bold;color:#0F1B33{e}">{name}</td>'
                 f'<td class="cell-partner{"" if last else " rule"}" width="40" align="right" valign="top" '
                 f'style="padding:10px 12px;font-size:13px;font-weight:bold;color:#0F1B33{e}">{n}</td>'
                 f'<td class="cell-partners{"" if last else " rule"}" '
                 f'style="padding:10px 12px;font-size:12px;color:#3B4257;line-height:1.7{e}">'
                 f'{partners.replace(" · ", " &nbsp;&middot;&nbsp; ")}</td></tr>')

    parts = [
      '<!DOCTYPE html>',
      '<html lang="en">',
      '<head>',
      '<meta charset="utf-8">',
      '<meta name="viewport" content="width=device-width,initial-scale=1">',
      '<meta name="x-apple-disable-message-reformatting">',
      '<title>Integrations Delivery Status</title>',
      f'<style type="text/css">{STYLESHEET}  </style>',
      '</head>',
      '<body class="page" bgcolor="#EFEDF6" style="margin:0;padding:0;'
      'background-color:#EFEDF6;font-family:Arial,Helvetica,sans-serif;color:#0F1B33">',
      '<table class="page" width="100%" cellpadding="0" cellspacing="0" border="0" '
      'bgcolor="#EFEDF6" style="background-color:#EFEDF6;border-collapse:collapse">',
      '<tr><td class="page-pad" align="center" style="padding:20px 10px">',
      '<table class="card" width="720" cellpadding="0" cellspacing="0" border="0" '
      'bgcolor="#FFFFFF" style="width:720px;max-width:100%;background-color:#FFFFFF;'
      'border-radius:12px;border-collapse:collapse">',
      '<tr><td class="masthead" bgcolor="#1B1442" style="background-color:#1B1442;'
      'padding:24px 26px;border-radius:12px 12px 0 0">'
      '<span class="masthead-brand" style="font-size:20px;font-weight:bold;color:#FFFFFF">'
      'Integrations</span>'
      '<span class="masthead-suffix" style="font-size:20px;color:#B9AEE8">&nbsp; Delivery Status</span>'
      f'<br><span class="masthead-meta" style="font-size:12px;color:#9A8DD0">'
      f'{date_line} &nbsp;&middot;&nbsp; {time_line}</span></td></tr>',
      f'<tr><td class="tiles" style="padding:20px 26px 0">'
      f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>{tiles}</tr>'
      f'</table></td></tr>',
    ]

    if D['POST_CONTRACT']:
        parts.append(section(
            "POST-CONTRACT STAGE", f"{len(D['POST_CONTRACT'])} integration" +
            ("" if len(D['POST_CONTRACT']) == 1 else "s"),
            "#0EA5A5", "#EEFBFB", "#0B7A7A", "#C7ECEC",
            ["PARTNER", "SYSTEM", "EXPECTED LIVE", "ARR BLOCKED"], D['POST_CONTRACT'], 'ptdt',
            cls="section-first"))
    else:
        parts.append('<tr><td class="section-first" style="padding:24px 26px 0">'
                     '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                     '<td class="section-title" style="border-left:3px solid #0A9D63;'
                     'padding-left:9px;font-size:11px;letter-spacing:1px;color:#0F1B33;'
                     'font-weight:bold">POST-CONTRACT STAGE</td>'
                     '<td class="section-count" align="right" style="font-size:11px;'
                     'color:#6B7086">none</td></tr></table>'
                     '<table class="grid" width="100%" cellpadding="0" cellspacing="0" border="0" '
                     'style="margin-top:10px;border:1px solid #CDEBDC">'
                     '<tr bgcolor="#F1FAF5" style="background-color:#F1FAF5">'
                     '<td class="clear-note" style="padding:11px 12px;font-size:12px;'
                     'color:#0A6B45">Nothing in post-contract stage right now.</td></tr>'
                     '</table></td></tr>')

    if D['CONTRACT_INPROGRESS']:
        parts.append(section(
            "CONTRACT IN PROGRESS", f"{len(D['CONTRACT_INPROGRESS'])} integration" +
            ("" if len(D['CONTRACT_INPROGRESS']) == 1 else "s"),
            "#C2410C", "#FFF4ED", "#9A3412", "#FBDCC4",
            ["PARTNER", "SYSTEM", "ARR BLOCKED"],
            D['CONTRACT_INPROGRESS'], 'ptt'))
    else:
        parts.append('<tr><td class="section" style="padding:20px 26px 0">'
                     '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                     '<td class="section-title" style="border-left:3px solid #0A9D63;'
                     'padding-left:9px;font-size:11px;letter-spacing:1px;color:#0F1B33;'
                     'font-weight:bold">CONTRACT IN PROGRESS</td>'
                     '<td class="section-count" align="right" style="font-size:11px;'
                     'color:#6B7086">none</td></tr></table>'
                     '<table class="grid" width="100%" cellpadding="0" cellspacing="0" border="0" '
                     'style="margin-top:10px;border:1px solid #CDEBDC">'
                     '<tr bgcolor="#F1FAF5" style="background-color:#F1FAF5">'
                     '<td class="clear-note" style="padding:11px 12px;font-size:12px;'
                     'color:#0A6B45">No contracts in progress right now.</td></tr>'
                     '</table></td></tr>')

    if D['SPYNE_BLOCKED']:
        parts.append(section("BLOCKED &mdash; WAITING ON SPYNE",
                             f"{len(D['SPYNE_BLOCKED'])} integrations", "#E0392E", "#FEF2F1",
                             "#B3261E", "#F7DAD7",
                             ["PARTNER", "SYSTEM", "OWNER", "EXPECTED LIVE", "ARR BLOCKED"],
                             D['SPYNE_BLOCKED'], 'pttdt'))
    else:
        parts.append('<tr><td class="section" style="padding:20px 26px 0">'
                     '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                     '<td class="section-title" style="border-left:3px solid #0A9D63;'
                     'padding-left:9px;font-size:11px;letter-spacing:1px;color:#0F1B33;'
                     'font-weight:bold">BLOCKED &mdash; WAITING ON SPYNE</td>'
                     '<td class="section-count" align="right" style="font-size:11px;'
                     'color:#6B7086">none</td></tr></table>'
                     '<table class="grid" width="100%" cellpadding="0" cellspacing="0" border="0" '
                     'style="margin-top:10px;border:1px solid #CDEBDC">'
                     '<tr bgcolor="#F1FAF5" style="background-color:#F1FAF5">'
                     '<td class="clear-note" style="padding:11px 12px;font-size:12px;'
                     'color:#0A6B45">Nothing is blocked on our side.</td></tr>'
                     '</table></td></tr>')

    parts.append(section("BLOCKED ON PARTNER", f"{len(D['PARTNER_BLOCKED'])} integrations",
                         "#E0392E", "#FEF2F1", "#B3261E", "#F7DAD7",
                         ["PARTNER", "SYSTEM", "EXPECTED LIVE", "ARR BLOCKED"],
                         D['PARTNER_BLOCKED'], 'ptdt'))

    # Rolling 30-day window: sheet rows with Status=Live and a Go Live Date
    # within the last 30 days of the send date. Once a row ages past 30 days
    # it drops out of this table on its own - it stays counted in Live
    # coverage the whole time, since that section is status-based, not
    # date-based.
    parts.append(section("WENT LIVE \u2014 LAST 30 DAYS", f"{len(D['RECENT_LIVE'])} integrations",
                         "#0A9D63", "#F1FAF5", "#0A6B45", "#CDEBDC",
                         ["PARTNER", "SYSTEM", "GO LIVE DATE"], D['RECENT_LIVE'], 'ptd'))

    total_live = sum(n for _, n, _ in D['LIVE'])
    parts.append('<tr><td class="section-last" style="padding:20px 26px 26px">'
                 '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                 '<td class="section-title" style="border-left:3px solid #522EBF;'
                 'padding-left:9px;font-size:11px;letter-spacing:1px;color:#0F1B33;'
                 'font-weight:bold">LIVE COVERAGE BY SYSTEM TYPE</td>'
                 f'<td class="section-count" align="right" style="font-size:11px;color:#6B7086">'
                 f'{total_live} integrations</td></tr></table>'
                 '<table class="grid" width="100%" cellpadding="0" cellspacing="0" border="0" '
                 'style="margin-top:10px;border:1px solid #E8E5F4">'
                 '<thead><tr bgcolor="#F6F4FF" style="background-color:#F6F4FF">'
                 + col_head("SYSTEM TYPE", "#4A3F7A", "#E8E5F4")
                 + '<th class="col-head" align="right" style="padding:8px 12px;font-size:9px;'
                   'letter-spacing:1px;color:#4A3F7A;font-weight:bold;text-align:right;'
                   'border-bottom:1px solid #E8E5F4">LIVE</th>'
                 + col_head("PARTNERS", "#4A3F7A", "#E8E5F4")
                 + f'</tr></thead><tbody>{rows}</tbody></table></td></tr>')

    parts += ['</table>', '</td></tr>', '</table>', '</body>', '</html>']
    return '\n'.join(parts)


if __name__ == "__main__":
    data_path = sys.argv[1] if len(sys.argv) > 1 else "report_data.json"
    out       = sys.argv[2] if len(sys.argv) > 2 else "payload.json"
    D = load(data_path)

    # ---- guards: never broadcast a half-built report
    if not D.get("LIVE") or not D.get("TILES"):
        sys.exit("ABORT: report data is empty - refusing to build a payload")
    live_sum = sum(n for _, n, _ in D['LIVE'])
    live_tile = next((v for l, v, *_ in D['TILES'] if l == "LIVE"), None)
    if live_tile != live_sum:
        sys.exit(f"ABORT: LIVE tile ({live_tile}) != sum of coverage rows ({live_sum})")
    if not D.get("TO"):
        sys.exit("ABORT: no recipients")

    now = datetime.datetime.now(IST)
    payload = {
        "to": D['TO'], "cc": D.get("CC", []), "bcc": D.get("BCC", []),
        "subject": f"Integrations Status \u2014 {now.strftime('%-d %b %Y')}",
        "template": os.environ.get("MAIL_TEMPLATE", ""),
        "templateData": {"HTMLdata": build_html(D, now)},
    }
    with open(out, "w") as f:
        json.dump(payload, f, ensure_ascii=False)
    html = payload["templateData"]["HTMLdata"]
    print(f"wrote {out}")
    print(f"  to       : {len(D['TO'])} addresses")
    print(f"  subject  : {payload['subject']}")
    print(f"  HTMLdata : {len(html):,} chars - full document")
    print(f"  live      : tile {live_tile} == coverage sum {live_sum}  OK")
    print(f"  payload  : {len(json.dumps(payload)):,} bytes")
