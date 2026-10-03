"""
Watchman: checks the whole results chain and exits non-zero if anything is wrong.

Checks, in plain words:
  1. The live feed source (4dmoon) is answering and carries a recent draw.
  2. Our relay (Cloudflare worker) is answering and matches the source.
  3. MY4D still exposes the migration, crawlability, theme and CTA signals.
  4. MY4D's saved provider results do not lag the relay.
  5. Every old-domain origin preserves a representative path in one 301 hop.

Run by GitHub Actions on a schedule; on failure the workflow opens an issue,
which emails the owner automatically.
"""

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

RELAY = "https://livefeed.angelina-bcb88.workers.dev/"
SOURCE = "https://www.4dmoon.com/feedwest.json"
SITE = "https://my4d.co/"
OLD_ORIGINS = [
    "http://4dvip88.com",
    "http://www.4dvip88.com",
    "https://4dvip88.com",
    "https://www.4dvip88.com",
]
REDIRECT_PATH = "/dictionary.html?health=1"

problems = []


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (health-check)"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def direct_status(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (health-check)"})
    opener = urllib.request.build_opener(NoRedirect)
    try:
        response = opener.open(req, timeout=timeout)
        return response.status, response.headers.get("Location", "")
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("Location", "")


def parse_dd(dd):
    m = re.search(r"(\d{2})-(\w{3})-(\d{4})", dd or "")
    if not m:
        return None
    months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    return datetime(int(m.group(3)), months.get(m.group(2), 1), int(m.group(1)),
                    tzinfo=timezone(timedelta(hours=8)))


def parse_site_date(value):
    try:
        return datetime.strptime(value or "", "%d-%m-%Y").replace(
            tzinfo=timezone(timedelta(hours=8))
        )
    except ValueError:
        return None


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

relay_west = {}
try:
    relay = json.loads(fetch(RELAY))
    relay_west = relay.get("west") or {}
    rel_p1 = relay_west.get("M", {}).get("P1")
    if not rel_p1:
        problems.append("Relay worker returns no Magnum numbers")
    elif src_p1 and str(rel_p1) != str(src_p1):
        problems.append("Relay is stale: relay Magnum=%s but source Magnum=%s" % (rel_p1, src_p1))
except Exception as e:
    problems.append("Relay worker unreachable: %s" % e)

# 3: the canonical site still carries every critical raw-HTML signal
try:
    html = fetch(SITE + "?health=1")
    required = {
        "live-feed code": "livefeed.angelina-bcb88.workers.dev",
        "raw prerendered result cards": "outerbox",
        "MY4D canonical": '<link rel="canonical" href="https://my4d.co/">',
        "English/Malay hreflang": 'hreflang="ms-MY" href="https://my4d.co/ms/"',
        "theme stylesheet": '/assets/theme.css?v=20261003r1',
        "theme script": '/assets/theme.js?v=20261003r1',
        "dictionary CTA": "data-dictionary-cta",
        "sponsor disclosure": "dictionary-cta-note",
    }
    for label, marker in required.items():
        if marker not in html:
            problems.append("%s lost its %s (page was overwritten?)" % (SITE, label))
    if re.search(r'<link rel="canonical" href="https?://(?:www\.)?4dvip88\.com/', html):
        problems.append("%s canonical reverted to the previous domain" % SITE)
    if html.count('class="ts-slide"') != 5:
        problems.append("%s no longer has exactly five banner slides" % SITE)
except Exception as e:
    problems.append("%s unreachable: %s" % (SITE, e))

# 4: published provider results must not trail the relay
try:
    rj = json.loads(fetch(SITE + "results.json?health=1"))
    provider_map = {
        "M": "magnum",
        "D": "damacai",
        "T": "toto",
        "G": "gd4d",
    }
    site_providers = rj.get("providers") or {}
    for feed_key, site_key in provider_map.items():
        feed_provider = relay_west.get(feed_key) or {}
        site_provider = site_providers.get(site_key) or {}
        feed_date = parse_dd(feed_provider.get("DD"))
        site_date = parse_site_date(site_provider.get("drawDate"))
        feed_first = str(feed_provider.get("P1") or "").strip()
        site_first = str(site_provider.get("first") or "").strip()
        if feed_date and site_date and feed_date.date() > site_date.date():
            problems.append(
                "MY4D %s result is behind relay: site=%s relay=%s"
                % (site_key, site_provider.get("drawDate"), feed_provider.get("DD"))
            )
        elif feed_date and site_date and feed_date.date() == site_date.date() \
                and feed_first and site_first and feed_first != site_first:
            problems.append(
                "MY4D %s first prize differs from relay for %s: site=%s relay=%s"
                % (site_key, site_provider.get("drawDate"), site_first, feed_first)
            )
except Exception as e:
    problems.append("results.json unreadable: %s" % e)

# 5: the migration redirect must be direct and preserve the full path/query
expected = SITE.rstrip("/") + REDIRECT_PATH
for origin in OLD_ORIGINS:
    try:
        status, location = direct_status(origin + REDIRECT_PATH)
        if status != 301:
            problems.append("%s returned %s instead of a direct 301" % (origin + REDIRECT_PATH, status))
        elif location != expected:
            problems.append("%s redirects to %s instead of %s" % (origin + REDIRECT_PATH, location, expected))
    except Exception as e:
        problems.append("%s redirect check failed: %s" % (origin + REDIRECT_PATH, e))

if problems:
    print("PROBLEMS FOUND:")
    for p in problems:
        print(" -", p)
    sys.exit(1)

print("All healthy: source, relay, published MY4D results, crawl signals and migration redirects. Checked",
      now.strftime("%d-%m-%Y %H:%M MYT"))
