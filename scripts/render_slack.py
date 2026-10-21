#!/usr/bin/env python3
"""Render the Slack view (Post-Contract Stage + Contract in Progress) to a PNG.

Usage: python scripts/render_slack.py --data data.json --out slack_view.png
Needs Chrome/Chromium (CHROME_BIN, or found on PATH / default macOS location) and Pillow.
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slack_report  # noqa: E402
from PIL import Image, ImageChops  # noqa: E402

BG = (0xEF, 0xED, 0xF6)  # page background of the report
SCALE = 2


def find_chrome():
    env = os.environ.get("CHROME_BIN")
    if env:
        return env
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(mac):
        return mac
    sys.exit("ABORT: no Chrome/Chromium found (set CHROME_BIN)")


def slack_html(D):
    D = dict(D)
    D["TILES"] = [["X", 0, "#fff", "#fff", "#fff", "#fff"]]  # build_html needs one; stripped below
    D.setdefault("LIVE", [])
    D["CONTRACT_INPROGRESS"] = [[r[0], r[1], r[-1]] for r in D["CONTRACT_INPROGRESS"]]
    html = slack_report.build_html(D, datetime.datetime.now(slack_report.IST))

    html = re.sub(r'<tr><td class="tiles".*?</tr>\n', "", html, count=1, flags=re.S)
    cut = html.find("BLOCKED &mdash; WAITING ON SPYNE")
    if cut == -1:
        sys.exit("ABORT: could not find the cut point in the Slack view")
    cut = html.rfind('<tr><td class="section"', 0, cut)
    if cut == -1:
        sys.exit("ABORT: could not find the section start for the cut")
    return html[:cut] + "</table>\n</td></tr>\n</table>\n</td></tr>\n</table>\n</body>\n</html>\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    with open(a.data, encoding="utf-8") as f:
        D = json.load(f)
    if not D["POST_CONTRACT"] and not D["CONTRACT_INPROGRESS"]:
        sys.exit("ABORT: nothing in Post-Contract Stage or Contract in Progress; refusing to post an empty view")

    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "view.html")
        raw = os.path.join(tmp, "raw.png")
        with open(page, "w", encoding="utf-8") as f:
            f.write(slack_html(D))
        cmd = [find_chrome(), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
               f"--force-device-scale-factor={SCALE}", "--window-size=800,1600",
               f"--screenshot={raw}", f"file://{page}"]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)

        img = Image.open(raw).convert("RGB")
        bbox = ImageChops.difference(img, Image.new("RGB", img.size, BG)).getbbox()
        if not bbox:
            sys.exit("ABORT: screenshot is blank")
        bottom = min(img.height, bbox[3] + 24 * SCALE)
        if bbox[3] >= img.height - 2:
            sys.exit("ABORT: report is taller than the render window; raise --window-size height")
        img.crop((0, 0, img.width, bottom)).save(a.out)
    print(f"rendered {a.out}")


if __name__ == "__main__":
    main()
