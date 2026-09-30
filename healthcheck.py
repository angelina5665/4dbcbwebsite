"""
Watchman: checks the whole results chain and exits non-zero if anything is wrong.

Checks, in plain words:
  1. The live feed source (4dmoon) is answering and carries a recent draw.
  2. Our relay (Cloudflare worker) is answering and matches the source.
  3. Both websites still contain the live-boost code that reads the relay.
  4. The robot's saved copy (results.json) is not absurdly old.

Run by GitHub Actions on a schedule; on failure the workflow opens an issue,
which emails the owner automatically.
"""

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

RELAY = "https://livefeed.angelina-bcb88.workers.dev/"
SOURCE = "https://www.4dmoon.com/feedwest.json"
SITES = ["https://4dvip88.com/", "https://4dresult1.com/"]

problems = []


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (health-check)"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def parse_dd(dd):
    m = re.search(r"(\d{2})-(\w{3})-(\d{4})", dd or "")
    if not m:
        return None
    months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    return datetime(int(m.group(3)), months.get(m.group(2), 1), int(m.group(1)),
                    tzinfo=timezone(timedelta(hours=8)))


now = datetime.now(timezone(timedelta(hours=8)))

# 1 + 2: source and relay agree and are recent
try:
    src = json.loads(fetch(SOURCE))
    src_p1 = src.get("M", {}).get("P1")
    src_dd = parse_dd(src.get("M", {}).get("DD"))
    if not src_p1:
        problems.append("Source feed (4dmoon) has no Magnum numbers")
    elif src_dd and (now - src_dd).days > 5:
        problems.append("Source feed looks frozen: newest draw is %s" % src.get("M", {}).get("DD"))
except Exception as e:
    problems.append("Source feed (4dmoon) unreachable: %s" % e)
    src_p1 = None

try:
    relay = json.loads(fetch(RELAY))
    rel_p1 = (relay.get("west") or {}).get("M", {}).get("P1")
    if not rel_p1:
        problems.append("Relay worker returns no Magnum numbers")
    elif src_p1 and str(rel_p1) != str(src_p1):
        problems.append("Relay is stale: relay Magnum=%s but source Magnum=%s" % (rel_p1, src_p1))
except Exception as e:
    problems.append("Relay worker unreachable: %s" % e)

# 3: both sites still carry the live-boost code
for site in SITES:
    try:
        html = fetch(site + "?health=1")
        if "livefeed.angelina-bcb88.workers.dev" not in html:
            problems.append("%s lost the live-feed code (page was overwritten?)" % site)
        if "outerbox" not in html:
            problems.append("%s page structure looks broken" % site)
    except Exception as e:
        problems.append("%s unreachable: %s" % (site, e))

# 4: robot baseline not absurdly old
try:
    rj = json.loads(fetch(SITES[0] + "results.json?health=1"))
    m = re.search(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})", rj.get("updated", ""))
    if m:
        upd = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                       int(m.group(4)), int(m.group(5)), tzinfo=timezone(timedelta(hours=8)))
        age_h = (now - upd).total_seconds() / 3600
        if age_h > 18:
            problems.append("Robot baseline is %.0f hours old (scheduler skipping runs)" % age_h)
except Exception as e:
    problems.append("results.json unreadable: %s" % e)

if problems:
    print("PROBLEMS FOUND:")
    for p in problems:
        print(" -", p)
    sys.exit(1)

print("All healthy: source, relay, both sites, baseline. Checked", now.strftime("%d-%m-%Y %H:%M MYT"))
