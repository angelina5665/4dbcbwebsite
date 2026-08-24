"""Fetch, cross-check and atomically update the latest 4D result snapshot.

The script fails closed when a required provider is missing, priority-provider
sources disagree, dates are invalid/stale, or result shapes are incomplete.
Timestamp-only changes do not rewrite results.json.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import urllib.request
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".github" / "seo-prerender"))
import prerender_results as pre  # noqa: E402


SOURCE = "https://4d4d.co/"
MOON_SOURCE = "https://www.4dmoon.com/feedwest.json"
OUT = ROOT / "results.json"
APPROVAL_ID = "OWNER-REPUBLISH-2026-08-24"

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
MOON_PROVIDER_KEYS = {
    "magnum": "M",
    "damacai": "D",
    "damacai13d": "D6",
    "toto": "T",
}
CROSS_CHECKED_PROVIDER_KEYS = ("magnum", "damacai", "damacai13d", "toto", "totoextra")


def fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; 4dvip-results/2.0; +https://4dvip88.com/methodology.html)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def clean(value: str | None) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    value = value.replace("&nbsp;", " ").replace("&amp;", "&")
    return " ".join(value.split())


def cells(source: str, css: str) -> list[str]:
    return [clean(match) for match in re.findall(r'class="' + css + r'"[^>]*>(.*?)</td>', source, re.S)]


def section_after(source: str, heading: str) -> str:
    start = source.find(">" + heading + "</td>")
    if start < 0:
        return ""
    remainder = source[start:]
    next_heading = re.search(r'class="resultprizelable"[^>]*>(?!' + re.escape(heading) + r')', remainder[20:])
    return remainder[: next_heading.start() + 20] if next_heading else remainder


def parse_card(block: str) -> tuple[str | None, dict[str, Any] | None]:
    labels = re.findall(r'class="result\w+lable"[^>]*>\s*([^<>]+?)\s*</td>', block)
    name = next((clean(value) for value in labels if clean(value)), "")
    if name not in PROVIDER_KEYS:
        return None, None

    key = PROVIDER_KEYS[name]
    card: dict[str, Any] = {"name": name}
    match = re.search(r"Date:\s*(\d{2}-\d{2}-\d{4})\s*\((\w{3})\)", block)
    if match:
        card["drawDate"], card["drawDay"] = match.group(1), match.group(2)
    match = re.search(r"Draw No:\s*([^<\n]+?)\s*</td>", block)
    if match:
        card["drawNo"] = clean(match.group(1))

    tops = cells(block, "resulttop")
    if len(tops) >= 3:
        card["first"], card["second"], card["third"] = tops[:3]

    special = section_after(block, "Special 特別獎")
    consolation = section_after(block, "Consolation 安慰獎")
    if special:
        card["special"] = cells(special, "resultbottom")
    if consolation:
        card["consolation"] = cells(consolation, "resultbottom")

    if key == "sabah88" and len(tops) >= 6:
        card["threeD"] = {"first": tops[3], "second": tops[4], "third": tops[5]}

    if key == "damacai13d":
        zodiac = cells(block, "resultbottomtoto2")
        bonus = re.findall(r'id="d3jp\d"[^>]*>([^<]+)<', block)
        card["d3rows"] = [
            {
                "value": tops[index],
                "zodiac": zodiac[index] if index < len(zodiac) else "",
                "bonus": clean(bonus[index]) if index < len(bonus) else "",
            }
            for index in range(min(3, len(tops)))
        ]

    if key == "totoextra":
        for field in ("special", "consolation", "first", "second", "third"):
            card.pop(field, None)
        five_d = cells(section_after(block, "5D"), "resultbottom")
        six_d = cells(section_after(block, "6D"), "resultbottom")
        if len(five_d) >= 6:
            card["fiveD"] = five_d[:6]
        if len(six_d) >= 9:
            card["sixD"] = six_d[:9]
        card["lotto"] = []
        for title in ("Star Toto 6/50", "Power Toto 6/55", "Supreme Toto 6/58"):
            section = section_after(block, title)
            if not section:
                continue
            values = cells(section, "resultbottomtoto2")
            labels = cells(section, "resultbottomtotojp")
            amounts = cells(section, "resultbottomtotojpval")
            balls = [value for value in values if value and value != "+"]
            entry: dict[str, Any] = {"title": title, "balls": balls[:6]}
            if len(balls) > 6:
                entry["bonus"] = balls[6]
            entry["jackpots"] = [[labels[index], amounts[index]] for index in range(min(len(labels), len(amounts)))]
            card["lotto"].append(entry)
    return key, card


def parse(source: str) -> dict[str, Any]:
    providers: dict[str, Any] = {}
    for block in re.findall(r'<div class="outerbox">(.*?)</div>', source, re.S):
        key, card = parse_card(block)
        if key and card and key not in providers:
            providers[key] = card

    dates: list[str] = []
    for draw_date, draw_day in re.findall(r'/result/(\d{2}-\d{2}-\d{4})\.html">\1 \((\w{3})\)', source):
        entry = f"{draw_date} ({draw_day})"
        if entry not in dates:
            dates.append(entry)
    return {"recentDates": dates[:6], "providers": providers}


def build_grand_dragon(feed: dict[str, Any]) -> dict[str, Any]:
    source = feed.get("G")
    if not isinstance(source, dict) or not source.get("P1"):
        raise pre.ValidationError("Grand Dragon result is missing from the cross-check feed")
    card: dict[str, Any] = {
        "name": "Grand Dragon 4D",
        "first": str(source["P1"]),
        "second": str(source["P2"]),
        "third": str(source["P3"]),
    }
    match = re.match(r"\((\w{3})\)\s*(\d{2})-(\w{3})-(\d{4})", str(source.get("DD", "")))
    if not match:
        raise pre.ValidationError("Grand Dragon draw date is missing or invalid")
    months = {name: f"{number:02d}" for number, name in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
    card["drawDay"] = match.group(1)
    card["drawDate"] = f"{match.group(2)}-{months[match.group(3)]}-{match.group(4)}"
    card["special"] = [str(source.get(f"S{index}", "")) for index in range(1, 14)]
    card["consolation"] = [str(source.get(f"C{index}", "")) for index in range(1, 11)]
    return card


def normalise_number(value: Any) -> str:
    return "".join(re.findall(r"\d|\*", str(value)))


def normalise_draw_number(value: Any) -> str:
    return "".join(re.findall(r"\d", str(value)))


def normalise_amount(value: Any) -> str:
    return "".join(re.findall(r"\d|\.", str(value).replace(",", "")))


def moon_draw_metadata(source: dict[str, Any]) -> tuple[str, str]:
    match = re.fullmatch(r"\(([A-Z][a-z]{2})\)\s*(\d{2})-([A-Z][a-z]{2})-(\d{4})", str(source.get("DD", "")))
    if not match:
        raise pre.ValidationError("cross-check draw date is missing or invalid")
    months = {name: f"{number:02d}" for number, name in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
    return f"{match.group(2)}-{months[match.group(3)]}-{match.group(4)}", match.group(1)


def numeric_values(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return sorted(normalise_number(value) for value in values if re.search(r"\d", str(value)))


def cross_check(providers: dict[str, Any], moon: dict[str, Any]) -> None:
    for provider_key, moon_key in MOON_PROVIDER_KEYS.items():
        provider = providers.get(provider_key)
        source = moon.get(moon_key)
        if not isinstance(provider, dict) or not isinstance(source, dict):
            raise pre.ValidationError(f"cross-check data missing for {provider_key}")
        source_date, source_day = moon_draw_metadata(source)
        if provider.get("drawDate") != source_date or provider.get("drawDay") != source_day:
            raise pre.ValidationError(f"cross-source mismatch for {provider_key} draw date")
        if source.get("DN") and normalise_draw_number(provider.get("drawNo")) != normalise_draw_number(source.get("DN")):
            raise pre.ValidationError(f"cross-source mismatch for {provider_key} draw number")
        for field, source_field in (("first", "P1"), ("second", "P2"), ("third", "P3")):
            if normalise_number(provider.get(field)) != normalise_number(source.get(source_field)):
                raise pre.ValidationError(f"cross-source mismatch for {provider_key} {field}")
        source_special = [source.get(f"S{index}", "") for index in range(1, 14)]
        source_consolation = [source.get(f"C{index}", "") for index in range(1, 11)]
        if numeric_values(provider.get("special")) != numeric_values(source_special):
            raise pre.ValidationError(f"cross-source mismatch for {provider_key} special results")
        if numeric_values(provider.get("consolation")) != numeric_values(source_consolation):
            raise pre.ValidationError(f"cross-source mismatch for {provider_key} consolation results")

    totoextra = providers.get("totoextra")
    toto_source = moon.get("T")
    if not isinstance(totoextra, dict) or not isinstance(toto_source, dict):
        raise pre.ValidationError("cross-check data missing for totoextra")
    source_date, source_day = moon_draw_metadata(toto_source)
    if totoextra.get("drawDate") != source_date or totoextra.get("drawDay") != source_day:
        raise pre.ValidationError("cross-source mismatch for totoextra draw date")
    if normalise_draw_number(totoextra.get("drawNo")) != normalise_draw_number(toto_source.get("DN")):
        raise pre.ValidationError("cross-source mismatch for totoextra draw number")
    expected_five = [
        toto_source.get("P5D1", ""), toto_source.get("P5D4", ""),
        toto_source.get("P5D2", ""), toto_source.get("P5D5", ""),
        toto_source.get("P5D3", ""), toto_source.get("P5D6", ""),
    ]
    expected_six = [
        toto_source.get("P6D1", ""), toto_source.get("P6D2A", ""), toto_source.get("P6D2B", ""),
        toto_source.get("P6D3A", ""), toto_source.get("P6D3B", ""), toto_source.get("P6D4A", ""),
        toto_source.get("P6D4B", ""), toto_source.get("P6D5A", ""), toto_source.get("P6D5B", ""),
    ]
    if [normalise_number(value) for value in totoextra.get("fiveD", [])] != [normalise_number(value) for value in expected_five]:
        raise pre.ValidationError("cross-source mismatch for totoextra fiveD")
    if [normalise_number(value) for value in totoextra.get("sixD", [])] != [normalise_number(value) for value in expected_six]:
        raise pre.ValidationError("cross-source mismatch for totoextra sixD")
    lotto_sources = {
        "Star Toto 6/50": ([toto_source.get(f"P650{index}", "") for index in range(1, 7)], toto_source.get("P650EX"), [toto_source.get("P650JP1"), toto_source.get("P650JP2")]),
        "Power Toto 6/55": ([toto_source.get(f"P655{index}", "") for index in range(1, 7)], None, [toto_source.get("P655JP")]),
        "Supreme Toto 6/58": ([toto_source.get(f"P658{index}", "") for index in range(1, 7)], None, [toto_source.get("P658JP")]),
    }
    lotto_by_title = {entry.get("title"): entry for entry in totoextra.get("lotto", []) if isinstance(entry, dict)}
    for title, (balls, bonus, jackpots) in lotto_sources.items():
        entry = lotto_by_title.get(title)
        if not isinstance(entry, dict):
            raise pre.ValidationError(f"cross-source mismatch for totoextra {title}")
        if [normalise_number(value) for value in entry.get("balls", [])] != [normalise_number(value) for value in balls]:
            raise pre.ValidationError(f"cross-source mismatch for totoextra {title} balls")
        if normalise_number(entry.get("bonus")) != normalise_number(bonus):
            raise pre.ValidationError(f"cross-source mismatch for totoextra {title} bonus")
        observed_amounts = [normalise_amount(row[1]) for row in entry.get("jackpots", []) if isinstance(row, list) and len(row) == 2]
        if observed_amounts != [normalise_amount(value) for value in jackpots]:
            raise pre.ValidationError(f"cross-source mismatch for totoextra {title} jackpots")


def latest_provider_date(providers: dict[str, Any]) -> tuple[str, str]:
    dated = []
    for provider in providers.values():
        draw_date = provider.get("drawDate")
        draw_day = provider.get("drawDay")
        if draw_date and draw_day:
            dated.append((pre.parse_draw_date(draw_date), draw_date, draw_day))
    if not dated:
        raise pre.ValidationError("no provider draw dates were parsed")
    _, draw_date, draw_day = max(dated, key=lambda entry: entry[0])
    return draw_date, draw_day


def semantic_view(data: dict[str, Any]) -> dict[str, Any]:
    view = deepcopy(data)
    view.pop("updated", None)
    provenance = view.get("provenance")
    if isinstance(provenance, dict):
        provenance.pop("verifiedAt", None)
    return view


def atomic_json_write(path: Path, data: dict[str, Any]) -> None:
    payload = (json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    handle, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def main() -> int:
    now = datetime.now(pre.MYT)
    try:
        data = parse(fetch(SOURCE))
        moon = json.loads(fetch(MOON_SOURCE))
        if not isinstance(moon, dict):
            raise pre.ValidationError("cross-check feed is not a JSON object")
        data["providers"]["gd4d"] = build_grand_dragon(moon)
        cross_check(data["providers"], moon)
        data["drawDate"], data["drawDay"] = latest_provider_date(data["providers"])
        data["updated"] = now.strftime("%Y-%m-%d %H:%M MYT")
        data["provenance"] = {
            "approvalId": APPROVAL_ID,
            "verifiedAt": now.isoformat(timespec="seconds"),
            "providerSources": pre.EXPECTED_SOURCE_MAP,
            "crossChecks": {"4dmoon-feedwest": list(CROSS_CHECKED_PROVIDER_KEYS)},
        }
        pre.validate_results_shape(data, now=now)

        previous = pre.read_json(OUT) if OUT.exists() else None
        if previous is not None and semantic_view(previous) == semantic_view(data):
            print(f"No material result change for draw {data['drawDate']}; results.json unchanged")
            return 0
        atomic_json_write(OUT, data)
        print(f"Wrote {OUT.name} for draw {data['drawDate']} with {len(data['providers'])} providers")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, pre.ValidationError) as exc:
        print(f"Refusing to overwrite {OUT.name}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
