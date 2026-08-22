"""
Fetch the latest 4D results and write them to results.json.

The website reads results.json, so this script is the only thing that needs to
know where the numbers come from. Layout, logos and banners live in index.html
and are never touched by this script.

Run it with:  python scrape.py
"""

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

SOURCE = "https://4d4d.co/"
OUT = "results.json"

# 4d4d.co's name for each provider -> the key our website uses
PROVIDER_KEYS = {
    "Damacai 4D": "damacai",
    "Magnum 4D": "magnum",
    "Toto 4D": "toto",
    "SportsToto 5D, 6D, Lotto": "totoextra",
    "Da Ma Cai 1+3D": "damacai13d",
    "Singapore 4D": "singapore",
    "Sabah88 4D": "sabah88",
    "Sandakan 4D": "sandakan",
    "Cashweep 4D": "cashsweep",
    "Cashsweep 4D": "cashsweep",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; 4dvip-results/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def clean(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    return " ".join(s.split())


def cells(html, css):
    """All <td class="css"> values, in page order."""
    return [clean(m) for m in re.findall(r'class="' + css + r'"[^>]*>(.*?)</td>', html, re.S)]


def section_after(html, heading):
    """Everything after a prize heading, up to the next heading."""
    i = html.find(">" + heading + "</td>")
    if i < 0:
        return ""
    rest = html[i:]
    nxt = re.search(r'class="resultprizelable"[^>]*>(?!' + re.escape(heading) + r')', rest[20:])
    return rest[: nxt.start() + 20] if nxt else rest


def parse_card(block):
    label = re.findall(r'class="result\w+lable"[^>]*>\s*([^<>]+?)\s*</td>', block)
    name = next((clean(x) for x in label if clean(x)), "")
    if name not in PROVIDER_KEYS:
        return None, None

    card = {"name": name}

    m = re.search(r"Date:\s*(\d{2}-\d{2}-\d{4})\s*\((\w{3})\)", block)
    if m:
        card["drawDate"], card["drawDay"] = m.group(1), m.group(2)
    m = re.search(r"Draw No:\s*([^<\n]+?)\s*</td>", block)
    if m:
        card["drawNo"] = clean(m.group(1))

    tops = cells(block, "resulttop")
    if len(tops) >= 3:
        card["first"], card["second"], card["third"] = tops[0], tops[1], tops[2]

    sp = section_after(block, "Special 特別獎")
    if sp:
        card["special"] = cells(sp, "resultbottom")
    co = section_after(block, "Consolation 安慰獎")
    if co:
        card["consolation"] = cells(co, "resultbottom")

    key = PROVIDER_KEYS[name]

    if key == "sabah88" and len(tops) >= 6:
        # the 3D prizes follow the 4D prizes in the same card
        card["threeD"] = {"first": tops[3], "second": tops[4], "third": tops[5]}

    if key == "damacai13d":
        zod = cells(block, "resultbottomtoto2")
        bonus = re.findall(r'id="d3jp\d"[^>]*>([^<]+)<', block)
        rows = []
        for i in range(min(3, len(tops))):
            rows.append({
                "value": tops[i],
                "zodiac": zod[i] if i < len(zod) else "",
                "bonus": clean(bonus[i]) if i < len(bonus) else "",
            })
        card["d3rows"] = rows

    if key == "totoextra":
        card.pop("special", None)
        card.pop("consolation", None)
        card.pop("first", None)
        card.pop("second", None)
        card.pop("third", None)

        five = section_after(block, "5D")
        fv = cells(five, "resultbottom")
        if len(fv) >= 6:
            card["fiveD"] = fv[:6]

        six = section_after(block, "6D")
        sx = cells(six, "resultbottom")
        if len(sx) >= 9:
            card["sixD"] = sx[:9]

        card["lotto"] = []
        for title in ("Star Toto 6/50", "Power Toto 6/55", "Supreme Toto 6/58"):
            blk = section_after(block, title)
            if not blk:
                continue
            nums = cells(blk, "resultbottomtoto2")
            jpl = cells(blk, "resultbottomtotojp")
            jpv = cells(blk, "resultbottomtotojpval")
            balls = [n for n in nums if n and n != "+"]
            entry = {"title": title, "balls": balls[:6]}
            if len(balls) > 6:
                entry["bonus"] = balls[6]
            entry["jackpots"] = [[jpl[i], jpv[i]] for i in range(min(len(jpl), len(jpv)))]
            card["lotto"].append(entry)

    return key, card


def parse(html):
    providers = {}
    for block in re.findall(r'<div class="outerbox">(.*?)</div>', html, re.S):
        key, card = parse_card(block)
        if key and key not in providers:
            providers[key] = card

    dates = []
    for d, day in re.findall(r'/result/(\d{2}-\d{2}-\d{4})\.html">\1 \((\w{3})\)', html):
        entry = d + " (" + day + ")"
        if entry not in dates:
            dates.append(entry)
    if not dates:
        for d, day in re.findall(r'href="/result/(\d{2}-\d{2}-\d{4})\.html"[^>]*>\s*([\d-]+ \((\w{3})\))', html):
            pass

    latest = next((c for c in providers.values() if c.get("drawDate")), {})
    now = datetime.now(timezone(timedelta(hours=8)))

    return {
        "drawDate": latest.get("drawDate", ""),
        "drawDay": latest.get("drawDay", ""),
        "recentDates": dates[:6],
        "updated": now.strftime("%Y-%m-%d %H:%M") + " MYT",
        "providers": providers,
    }


def main():
    html = fetch(SOURCE)
    data = parse(html)

    if len(data["providers"]) < 5:
        print("Only found %d providers - refusing to overwrite results.json"
              % len(data["providers"]), file=sys.stderr)
        return 1

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print("Wrote %s for draw %s (%s) with %d providers"
          % (OUT, data["drawDate"], data["drawDay"], len(data["providers"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
