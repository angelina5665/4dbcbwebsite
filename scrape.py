"""
Fetch the latest 4D results and write them to results.json.

The website reads results.json, so this script is the only thing that needs to
know where the numbers come from. Layout, logos and banners live in index.html
and are never touched by this script.

Run it with:  python scrape.py
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

SOURCE = "https://4d4d.co/"
GD_SOURCE = "https://www.4dmoon.com/feedwest.json"
GD_DRAW_ARCHIVE = "https://tiok4d.com/results/grand-dragon-4d/{year}/{month}"
NINE_SOURCE = "https://4dgm.com/?view=home"
NINE_CROSSCHECK_SOURCE = "https://lotto09.com/"
HUAWEI_RESULTS_BASE = os.environ.get("HUAWEI_RESULTS_BASE", "https://api.huawei88.org").rstrip("/")
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
    "Cash Sweep 4D": "cashsweep",
    "Special Cash Sweep 4D": "cashsweep",
}

CANONICAL_PROVIDER_NAMES = {
    "cashsweep": "Special Cash Sweep 4D",
}

DRAW_DATE_FORMAT = "%d-%m-%Y"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; 4dvip-results/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "my4d-results/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


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

    key = PROVIDER_KEYS[name]
    card = {"name": CANONICAL_PROVIDER_NAMES.get(key, name)}

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


def validated_draw_date(value, day, label):
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}-\d{2}-\d{4}", value):
        raise ValueError("%s has invalid draw date %r" % (label, value))
    try:
        parsed = datetime.strptime(value, DRAW_DATE_FORMAT)
    except ValueError as error:
        raise ValueError("%s has invalid draw date %r" % (label, value)) from error
    expected_day = parsed.strftime("%a")
    if day != expected_day:
        raise ValueError("%s draw day %r does not match %r" % (label, day, expected_day))
    return parsed


def recent_dates_with_latest(values, latest_date, latest_day, limit=6):
    latest = validated_draw_date(latest_date, latest_day, "latest provider")
    dated_entries = {}
    candidates = list(values or []) + [latest_date + " (" + latest_day + ")"]

    for value in candidates:
        match = re.fullmatch(r"(\d{2}-\d{2}-\d{4}) \(([A-Z][a-z]{2})\)", str(value))
        if not match:
            raise ValueError("invalid recent date %r" % value)
        parsed = validated_draw_date(match.group(1), match.group(2), "recent date")
        if parsed > latest:
            raise ValueError("recent date %r is newer than the latest provider date" % value)
        dated_entries[parsed.date()] = match.group(1) + " (" + match.group(2) + ")"

    return [dated_entries[key] for key in sorted(dated_entries, reverse=True)[:limit]]


def finalize_snapshot(data):
    providers = data.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ValueError("snapshot has no providers")

    dated_providers = []
    for key, provider in providers.items():
        if not isinstance(provider, dict):
            raise ValueError("provider %r is invalid" % key)
        if key in CANONICAL_PROVIDER_NAMES:
            provider["name"] = CANONICAL_PROVIDER_NAMES[key]
        parsed = validated_draw_date(
            provider.get("drawDate"),
            provider.get("drawDay"),
            "provider %r" % key,
        )
        dated_providers.append((parsed, provider))

    _latest_date, latest_provider = max(dated_providers, key=lambda item: item[0])
    data["drawDate"] = latest_provider["drawDate"]
    data["drawDay"] = latest_provider["drawDay"]
    data["recentDates"] = recent_dates_with_latest(
        data.get("recentDates", []),
        data["drawDate"],
        data["drawDay"],
    )
    return data


def result_facts(data):
    """Return only draw facts; the fetch timestamp is not a result change."""
    return {key: value for key, value in data.items() if key != "updated"}


def snapshot_changed(candidate, baseline):
    return result_facts(candidate) != result_facts(baseline)


def validate_against_baseline(candidate, baseline):
    """Refuse incomplete or older upstream snapshots."""
    baseline_providers = baseline.get("providers") or {}
    candidate_providers = candidate.get("providers") or {}
    missing = sorted(set(baseline_providers) - set(candidate_providers))
    if missing:
        raise ValueError("candidate omits existing providers: %s" % ", ".join(missing))

    for key, previous in baseline_providers.items():
        current = candidate_providers[key]
        previous_date = validated_draw_date(
            previous.get("drawDate"), previous.get("drawDay"), "baseline provider %r" % key
        )
        current_date = validated_draw_date(
            current.get("drawDate"), current.get("drawDay"), "candidate provider %r" % key
        )
        if current_date < previous_date:
            raise ValueError(
                "candidate provider %r regresses from %s to %s"
                % (key, previous.get("drawDate"), current.get("drawDate"))
            )


def _grand_dragon_draw_no(html, card):
    """Return a corroborated Grand Dragon draw number from a month archive."""
    draw_date = datetime.strptime(card["drawDate"], DRAW_DATE_FORMAT).strftime("%Y-%m-%d")
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        date_match = re.search(r'<time[^>]+datetime=["\']([^"\']+)', row, re.I)
        numbers = [clean(value) for value in re.findall(r'class=["\'][^"\']*recent-number[^"\']*["\'][^>]*>(.*?)</td>', row, re.S | re.I)]
        cells_in_row = [clean(value) for value in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)]
        if not date_match or date_match.group(1) != draw_date or len(numbers) < 3 or len(cells_in_row) < 2:
            continue
        if numbers[:3] != [card["first"], card["second"], card["third"]]:
            raise ValueError("Grand Dragon draw-number source disagrees on top prizes")
        draw_no = cells_in_row[1]
        if re.fullmatch(r"\d{1,6}/\d{4}", draw_no) is None:
            raise ValueError("Grand Dragon draw-number source has an invalid draw number")
        return draw_no
    return None


def fetch_grand_dragon():
    """Grand Dragon 4D comes from 4dmoon.com's json feed (key "G")."""
    raw = json.loads(fetch(GD_SOURCE))
    g = raw.get("G")
    if not g or not g.get("P1"):
        return None
    card = {"name": "Grand Dragon 4D"}
    m = re.match(r"\((\w{3})\)\s*(\d{2})-(\w{3})-(\d{4})", g.get("DD", ""))
    if m:
        months = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
                  "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}
        card["drawDay"] = m.group(1)
        card["drawDate"] = "%s-%s-%s" % (m.group(2), months.get(m.group(3), "01"), m.group(4))
    card["first"], card["second"], card["third"] = g["P1"], g["P2"], g["P3"]
    sp = [g.get("S%d" % i, "") for i in range(1, 14)]
    # centre the last three, same as the source site shows them
    card["special"] = sp[:10] + [""] + sp[10:13] + [""]
    card["consolation"] = [g.get("C%d" % i, "") for i in range(1, 11)]
    if card.get("drawDate"):
        day, month, year = card["drawDate"].split("-")
        try:
            archive = fetch(GD_DRAW_ARCHIVE.format(year=year, month=month))
            draw_no = _grand_dragon_draw_no(archive, card)
            if draw_no:
                card["drawNo"] = draw_no
            else:
                print("Grand Dragon draw number unavailable for %s" % card["drawDate"], file=sys.stderr)
        except Exception as exc:
            # The draw number is supporting metadata. Never discard a complete
            # verified result card merely because the archive is unavailable.
            print("Grand Dragon draw-number lookup failed (%s)" % exc, file=sys.stderr)
    return card


def _nine_lotto_card(html, source):
    """Parse one complete Nine Lotto 4D card from a supported public board."""
    if source == "4dgm":
        match = re.search(
            r'<div class="card result ninelotto-result">(.*?)<!-- END -->',
            html,
            re.S | re.I,
        )
        if not match:
            raise ValueError("4dgm has no Nine Lotto card")
        block = match.group(1)
        date_match = re.search(r"Date:\s*(\d{2})/(\d{2})/(\d{4})\s*\((\w{3})\)", block)
        draw_match = re.search(r"Draw No:\s*([^<]+)</div>", block)
        prizes = re.findall(r'class="col col-6 draw">\s*([0-9]{4})\s*</div>', block)
        special_block = re.search(r"Special Prize.*?</div>(.*?)Consolation", block, re.S | re.I)
        consolation_block = re.search(r"Consolation.*?</div>(.*?)<div class=\"row separator\">\s*<div class=\"col-12\">6D", block, re.S | re.I)

        def values(section):
            if not section:
                return []
            return [clean(value) for value in re.findall(r'class="[^"]*\bdraw\b[^"]*">(.*?)</div>', section.group(1), re.S)]

        special = values(special_block)
        consolation = [value for value in values(consolation_block) if value]
        if not date_match or not draw_match or len(prizes) < 3:
            raise ValueError("4dgm Nine Lotto card is incomplete")
        card = {
            "name": "Nine Lotto 4D",
            "drawDate": "%s-%s-%s" % (date_match.group(1), date_match.group(2), date_match.group(3)),
            "drawDay": date_match.group(4),
            "drawNo": clean(draw_match.group(1)),
            "first": prizes[0],
            "second": prizes[1],
            "third": prizes[2],
            "special": special,
            "consolation": consolation,
        }
    elif source == "lotto09":
        start = html.lower().find('alt="logo-nine lotto"')
        if start < 0:
            raise ValueError("lotto09 has no Nine Lotto card")
        end = html.lower().find('class="card outer-box', start + 1)
        block = html[start:end if end > start else len(html)]
        date_match = re.search(r'data-id="date">\s*(\d{2})-(\d{2})-(\d{4})\s*\((\w{3})\)', block)
        draw_match = re.search(r'data-id="draw_no">\s*([^<]+)', block)

        def field(name):
            match = re.search(r'data-id="' + re.escape(name) + r'">\s*([^<]*)', block)
            return clean(match.group(1)) if match else ""

        special = [field("special-%d" % index) for index in range(1, 16)]
        consolation = [field("consolation-%d" % index) for index in range(1, 11)]
        special = special[:max((index for index, value in enumerate(special, 1) if value), default=0)]
        if not date_match or not draw_match:
            raise ValueError("lotto09 Nine Lotto card is incomplete")
        card = {
            "name": "Nine Lotto 4D",
            "drawDate": "%s-%s-%s" % (date_match.group(1), date_match.group(2), date_match.group(3)),
            "drawDay": date_match.group(4),
            "drawNo": clean(draw_match.group(1)),
            "first": field("first_prize"),
            "second": field("second_prize"),
            "third": field("third_prize"),
            "special": special,
            "consolation": consolation,
        }
    else:
        raise ValueError("unsupported Nine Lotto source")

    if not all(re.fullmatch(r"\d{4}", card[key] or "") for key in ("first", "second", "third")):
        raise ValueError("Nine Lotto top prizes are incomplete")
    if len(card["consolation"]) != 10 or any(not re.fullmatch(r"\d{4}", value) for value in card["consolation"]):
        raise ValueError("Nine Lotto consolation list is incomplete")
    if len(card["special"]) < 10 or any(value and value != "----" and not re.fullmatch(r"\d{4}", value) for value in card["special"]):
        raise ValueError("Nine Lotto special list is incomplete")
    validated_draw_date(card["drawDate"], card["drawDay"], "Nine Lotto")
    return card


def _public_nine_lotto():
    """Require two independent public boards to agree on Nine Lotto."""
    primary = _nine_lotto_card(fetch(NINE_SOURCE), "4dgm")
    crosscheck = _nine_lotto_card(fetch(NINE_CROSSCHECK_SOURCE), "lotto09")
    # Publishers centre the 13-slot Special board differently, so compare its
    # ordered values while treating purely visual empty cells as layout only.
    primary_special = [value for value in primary["special"] if re.fullmatch(r"\d{4}", value or "")]
    crosscheck_special = [value for value in crosscheck["special"] if re.fullmatch(r"\d{4}", value or "")]
    comparable = ("drawDate", "drawDay", "drawNo", "first", "second", "third", "consolation")
    differences = [key for key in comparable if primary.get(key) != crosscheck.get(key)]
    if primary_special != crosscheck_special:
        differences.append("special")
    if differences:
        raise ValueError("Nine Lotto sources disagree on %s" % ", ".join(differences))
    primary["special"] = primary_special
    return primary


def _huawei_nine_lotto_card(payload, draw_date):
    status = payload.get("status") or {}
    if status.get("success") is not True:
        raise ValueError("Huawei result request was not successful")
    rows = payload.get("draw_results")
    if not isinstance(rows, list):
        raise ValueError("Huawei response has no draw_results list")
    result = next((row for row in rows if isinstance(row, dict) and row.get("type") == "N"), None)
    if not result:
        raise ValueError("Huawei response has no Nine Lotto result")
    four_d = result.get("4d")
    if not isinstance(four_d, dict):
        raise ValueError("Huawei Nine Lotto response has no 4D result")
    parsed_date = datetime.strptime(draw_date, "%Y-%m-%d")
    card = {
        "name": "Nine Lotto 4D",
        "drawDate": parsed_date.strftime(DRAW_DATE_FORMAT),
        "drawDay": parsed_date.strftime("%a"),
        "first": str(four_d.get("first") or "").strip(),
        "second": str(four_d.get("second") or "").strip(),
        "third": str(four_d.get("third") or "").strip(),
        "special": [str(value).strip() for value in (four_d.get("special") or []) if str(value).strip()],
        "consolation": [str(value).strip() for value in (four_d.get("consolation") or []) if str(value).strip()],
    }
    if not all(re.fullmatch(r"\d{4}", card[key]) for key in ("first", "second", "third")):
        raise ValueError("Huawei Nine Lotto top prizes are incomplete")
    if not (10 <= len(card["special"]) <= 13) or any(not re.fullmatch(r"\d{4}", value) for value in card["special"]):
        raise ValueError("Huawei Nine Lotto special prizes are incomplete")
    if len(card["consolation"]) != 10 or any(not re.fullmatch(r"\d{4}", value) for value in card["consolation"]):
        raise ValueError("Huawei Nine Lotto consolation prizes are incomplete")
    return card


def fetch_huawei_nine_lotto(mid, password):
    credentials = {"mid": mid, "pw": password}
    schedule = post_json(
        HUAWEI_RESULTS_BASE + "/api/bet_server_get_draw_dates/en",
        credentials,
    )
    status = schedule.get("status") or {}
    if status.get("success") is not True:
        raise ValueError("Huawei draw-date request was not successful")
    now = datetime.now(timezone(timedelta(hours=8)))
    candidates = []
    for day in schedule.get("draw_results") or []:
        if not isinstance(day, dict) or not isinstance(day.get("result_date"), str):
            continue
        try:
            result_date = datetime.strptime(day["result_date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        types = day.get("types") or []
        if result_date <= now.date() and any(isinstance(item, dict) and item.get("type") == "N" for item in types):
            candidates.append(day["result_date"])
    if not candidates:
        raise ValueError("Huawei has no completed Nine Lotto draw date")
    draw_date = max(candidates)
    payload = post_json(
        HUAWEI_RESULTS_BASE + "/api/bet_server_get_results/en",
        {"draw_date": draw_date, **credentials},
    )
    return _huawei_nine_lotto_card(payload, draw_date)


def fetch_nine_lotto():
    """Use Huawei as primary when configured and public boards as an accuracy gate."""
    public = _public_nine_lotto()
    mid = os.environ.get("HUAWEI_RESULTS_MID", "").strip()
    password = os.environ.get("HUAWEI_RESULTS_PW", "")
    if not mid or not password:
        print("Huawei result credentials are not configured - using the dual-public-source gate", file=sys.stderr)
        return public

    official = fetch_huawei_nine_lotto(mid, password)
    comparable = ("drawDate", "first", "second", "third", "special", "consolation")
    differences = [key for key in comparable if official.get(key) != public.get(key)]
    if differences:
        raise ValueError("Huawei and public Nine Lotto results disagree on %s" % ", ".join(differences))
    official["drawNo"] = public["drawNo"]
    return official


def lotto_in_progress(provider):
    """True while the Toto lotto games are still being drawn (some balls not out yet)."""
    for entry in (provider or {}).get("lotto") or []:
        balls = entry.get("balls") or []
        if len(balls) != 6 or any(not str(ball).isdigit() for ball in balls):
            return True
    return False


def keep_complete_lotto(data, baseline):
    """During the live draw, keep the last complete Toto cards instead of
    publishing half-drawn balls, so the rest of the results can still be saved."""
    providers = data.get("providers", {})
    previous_all = (baseline or {}).get("providers") or {}
    current = providers.get("totoextra")
    previous = previous_all.get("totoextra")
    if current and previous and lotto_in_progress(current) and not lotto_in_progress(previous):
        # Toto 4D and the Toto lotto card must carry the same draw date, so hold both back together
        providers["totoextra"] = previous
        if previous_all.get("toto"):
            providers["toto"] = previous_all["toto"]
        return True
    return False


def main():
    html = fetch(SOURCE)
    data = parse(html)

    try:
        with open(OUT, "r", encoding="utf-8") as f:
            baseline = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        baseline = None

    try:
        gd = fetch_grand_dragon()
        if gd:
            data["providers"]["gd4d"] = gd
    except Exception as e:
        print("Grand Dragon fetch failed (%s) - keeping the rest" % e, file=sys.stderr)

    try:
        data["providers"]["nine"] = fetch_nine_lotto()
    except Exception as e:
        previous_nine = ((baseline or {}).get("providers") or {}).get("nine")
        if previous_nine:
            data["providers"]["nine"] = previous_nine
            print("Nine Lotto fetch/cross-check failed (%s) - keeping the last verified card" % e, file=sys.stderr)
        else:
            print("Nine Lotto fetch/cross-check failed (%s) - no card will be added" % e, file=sys.stderr)

    if len(data["providers"]) < 5:
        print("Only found %d providers - refusing to overwrite results.json"
              % len(data["providers"]), file=sys.stderr)
        return 1

    try:
        finalize_snapshot(data)
    except ValueError as error:
        print("Invalid result snapshot (%s) - refusing to overwrite results.json"
              % error, file=sys.stderr)
        return 1

    if baseline is not None:
        if keep_complete_lotto(data, baseline):
            print("Toto lotto still being drawn - keeping the last complete lotto card for now")
        try:
            validate_against_baseline(data, baseline)
        except ValueError as error:
            print("Unsafe result snapshot (%s) - refusing to overwrite results.json"
                  % error, file=sys.stderr)
            return 1
        if not snapshot_changed(data, baseline):
            print("No factual result change - keeping the existing snapshot and timestamp")
            return 0

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print("Wrote %s for draw %s (%s) with %d providers"
          % (OUT, data["drawDate"], data["drawDay"], len(data["providers"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
