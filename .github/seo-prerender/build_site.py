#!/usr/bin/env python3
"""Build crawlable Batch 2-3 result pages from a validated results snapshot."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import prerender_results as pre


TOOL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOL_DIR.parents[1]
BASE_URL = "https://4dvip88.com"
ARCHIVE_METADATA_PATH = TOOL_DIR / "archive-metadata.json"
ARCHIVE_METADATA_SCHEMA_VERSION = 1

PROVIDER_PAGES = (
    {
        "slug": "magnum-4d-results",
        "title": "Magnum 4D Results in Malaysia | 4DVIP88",
        "description": "Check the latest completed Magnum 4D result available to 4DVIP88, including draw date, draw number and prize numbers.",
        "h1": "Magnum 4D Results",
        "lead": "View the latest completed Magnum 4D draw available to this independent reference site, with its draw date and update time.",
        "keys": ("magnum",),
        "context": "Magnum 4D is sometimes written as Magnum4D in searches. Both spellings refer to the same result page; no separate spelling doorway is needed.",
        "coverage": "The card keeps the first, second and third prize numbers with the special and consolation groups for one Magnum draw. The provider draw number and draw date are shown separately from the time when 4DVIP88 last updated its copy.",
        "reading": "Match the draw date and draw number before comparing a number. Leading zeroes are significant, and a number listed under special or consolation is not the same category as a top-three result.",
        "verification": "The current pipeline compares the imported Magnum numbers, draw metadata and prize groups with a second aggregation feed. This reduces transcription risk but does not make 4DVIP88 an official Magnum source.",
        "related_href": "/west-malaysia-4d-results/",
        "related_label": "Compare the current West Malaysia provider results",
    },
    {
        "slug": "sports-toto-4d-results",
        "title": "Sports Toto 4D Results in Malaysia | 4DVIP88",
        "description": "Check the latest completed Sports Toto 4D, 5D, 6D and lotto results available to 4DVIP88, with draw and update dates.",
        "h1": "Sports Toto 4D Results",
        "lead": "Check the latest completed Sports Toto result data available for 4D, 5D, 6D and lotto draws.",
        "keys": ("toto", "totoextra"),
        "context": "Toto and SportsToto are common ways people refer to the same provider. The word sports is used here only as part of the Sports Toto name.",
        "coverage": "The 4D card shows the top-three, special and consolation groups. A separate card preserves the 5D, 6D and lotto fields from the same Sports Toto draw so that unlike result formats are not merged into one table.",
        "reading": "Check the product label as well as the draw number. A 4D number, a masked 6D combination and a lotto ball set describe different result formats and should not be compared as if they were interchangeable.",
        "verification": "The current pipeline compares Sports Toto draw metadata, 4D prize groups, 5D and 6D fields, lotto balls, bonus ball and jackpot fields with a second aggregation feed. Provider rules still control prize and claim information.",
        "related_href": "/west-malaysia-4d-results/",
        "related_label": "Compare the current West Malaysia provider results",
    },
    {
        "slug": "da-ma-cai-results",
        "title": "Da Ma Cai Results in Malaysia | 4DVIP88",
        "description": "Check the latest completed Da Ma Cai 4D and 1+3D results available to 4DVIP88, with draw date and update information.",
        "h1": "Da Ma Cai 4D Results",
        "lead": "View the latest completed Da Ma Cai 4D and 1+3D result data available to this reference site.",
        "keys": ("damacai", "damacai13d"),
        "context": "Da Ma Cai is also written as Damacai. This single page covers both natural spellings instead of creating duplicate pages.",
        "coverage": "The page keeps the Da Ma Cai 4D card and the 1+3D card separate. Each card retains its own labels while sharing the provider draw date and draw number, avoiding a misleading combination of four-digit and six-digit fields.",
        "reading": "Use the heading above each card before reading a number. Spaces inside 1+3D values are part of the displayed format; they do not turn that field into an ordinary four-digit result.",
        "verification": "The current pipeline compares Da Ma Cai draw metadata, top results, special numbers and consolation numbers with a second aggregation feed. The comparison is a data-quality check, not a claim of provider endorsement.",
        "related_href": "/west-malaysia-4d-results/",
        "related_label": "Compare the current West Malaysia provider results",
    },
    {
        "slug": "sabah-88-4d-results",
        "title": "Sabah 88 4D Results | 4DVIP88",
        "description": "Check the latest completed Sabah 88 4D result available to 4DVIP88, including draw date and prize numbers.",
        "h1": "Sabah 88 4D Results",
        "lead": "View the latest completed Sabah 88 4D result available to this independent reference site.",
        "keys": ("sabah88",),
        "context": "The result card records the provider draw date and draw number separately from the website update time.",
        "coverage": "The Sabah 88 card includes the 4D top-three, special and consolation groups and the available 3D top-three fields. These are presented under separate labels so the shorter 3D values are not mistaken for incomplete 4D numbers.",
        "reading": "Check the Sabah 88 draw number and date first, then read the 4D and 3D sections independently. The website update time shows when the imported file changed; it is not a provider confirmation time.",
        "verification": "This provider currently comes from one automated aggregation feed. Because no automated second feed is recorded for it, verify important numbers and the draw date with the relevant provider before relying on this reference page.",
        "related_href": "/east-malaysia-4d-results/",
        "related_label": "Compare the current East Malaysia provider results",
    },
    {
        "slug": "special-cash-sweep-results",
        "title": "Special Cash Sweep Results | 4DVIP88",
        "description": "Check the latest completed Special Cash Sweep 4D result available to 4DVIP88 for Sarawak result reference.",
        "h1": "Special Cash Sweep 4D Results",
        "lead": "View the latest completed Special Cash Sweep result available for Sarawak result reference.",
        "keys": ("cashsweep",),
        "context": "The upstream label may appear as Cashsweep; this page uses the clearer Special Cash Sweep provider name.",
        "coverage": "The Special Cash Sweep card presents one draw's first, second and third prizes followed by special and consolation groups. The displayed draw number belongs to that provider result and is not shared with the other Sarawak or Sabah cards.",
        "reading": "Use the provider name, draw date and draw number together when checking a result. Similar four-digit numbers can appear in different categories or draws, so the category heading is part of the factual result.",
        "verification": "This provider currently comes from one automated aggregation feed. 4DVIP88 does not treat the import timestamp as independent proof, so verify important numbers and the draw date with the relevant provider before relying on this reference page.",
        "related_href": "/east-malaysia-4d-results/",
        "related_label": "Compare the current East Malaysia provider results",
    },
    {
        "slug": "sandakan-stc-4d-results",
        "title": "Sandakan STC 4D Results | 4DVIP88",
        "description": "Check the latest completed Sandakan Turf Club or STC 4D result available to 4DVIP88, with draw date and numbers.",
        "h1": "Sandakan STC 4D Results",
        "lead": "View the latest completed Sandakan Turf Club (STC) 4D result available to this reference site.",
        "keys": ("sandakan",),
        "context": "Sandakan and STC are kept together on one useful provider page.",
        "coverage": "The Sandakan Turf Club card contains the top-three, special and consolation numbers for the displayed STC draw. One canonical page covers both the Sandakan and STC names so users do not have to choose between duplicate spelling pages.",
        "reading": "Confirm the draw date and STC draw number before reading the prize group. A page update can occur after a draw without changing its numbers, so freshness and the provider draw date are reported separately.",
        "verification": "This provider currently comes from one automated aggregation feed. Because no automated second feed is recorded for it, verify important numbers and the draw date with the relevant provider before relying on this reference page.",
        "related_href": "/east-malaysia-4d-results/",
        "related_label": "Compare the current East Malaysia provider results",
    },
)

REGION_PAGES = (
    {
        "slug": "west-malaysia-4d-results",
        "title": "West Malaysia 4D Results | 4DVIP88",
        "description": "Compare the latest completed Magnum, Sports Toto and Da Ma Cai 4D results for West Malaysia in one reference page.",
        "h1": "West Malaysia 4D Results",
        "lead": "Compare the latest completed result data available for Magnum 4D, Sports Toto and Da Ma Cai.",
        "keys": ("magnum", "toto", "damacai"),
        "scope": "This page groups three commonly searched West Malaysia result references without treating them as one combined draw. Magnum, Sports Toto and Da Ma Cai retain separate draw numbers, schedules and prize groups.",
        "reading": "Start with the provider heading, then compare the draw date and draw number. The cards can share a calendar date while still describing independent draws. If one provider has not published a newer result, its own date remains the deciding freshness signal.",
        "verification": "Magnum, Sports Toto and Da Ma Cai are in the current automated two-feed comparison set. Agreement between aggregation feeds reduces copying errors, but important numbers should still be checked with the relevant provider.",
        "links": (("Magnum 4D details", "/magnum-4d-results/"), ("Sports Toto details", "/sports-toto-4d-results/"), ("Da Ma Cai details", "/da-ma-cai-results/")),
    },
    {
        "slug": "east-malaysia-4d-results",
        "title": "East Malaysia 4D Results | 4DVIP88",
        "description": "Compare the latest completed Sabah 88, Sandakan STC and Special Cash Sweep results for Sabah and Sarawak.",
        "h1": "East Malaysia 4D Results",
        "lead": "Compare the latest completed result data available for Sabah 88, Sandakan STC and Special Cash Sweep.",
        "keys": ("sabah88", "sandakan", "cashsweep"),
        "scope": "This page groups regional result references for Sabah 88, Sandakan Turf Club and Special Cash Sweep. The grouping is navigational: it does not claim that the providers share a draw, schedule, territory rule or result number.",
        "reading": "Read each card independently and keep its provider draw number with the number being checked. Sabah 88 also carries a separately labelled 3D result, while the other cards on this page present their own 4D categories.",
        "verification": "These regional providers currently come from one automated aggregation feed. The import timestamp is not an independent confirmation, so users should verify important numbers and draw dates with the relevant provider.",
        "links": (("Sabah 88 details", "/sabah-88-4d-results/"), ("Sandakan STC details", "/sandakan-stc-4d-results/"), ("Special Cash Sweep details", "/special-cash-sweep-results/")),
    },
)


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def canonical(path: str) -> str:
    return BASE_URL + path


def atomic_write(path: Path, content: str) -> bool:
    encoded = content.encode("utf-8")
    if path.exists() and path.read_bytes() == encoded:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return True


def replace_marker(document: str, name: str, content: str) -> str:
    start = f"<!-- GENERATED_{name}_START -->"
    end = f"<!-- GENERATED_{name}_END -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if len(pattern.findall(document)) != 1:
        raise pre.ValidationError(f"index marker {name} is missing or duplicated")
    return pattern.sub(start + content + end, document)


def nav(current: str, language: str = "en-MY") -> str:
    if language == "ms-MY":
        items = (
            ("home", "/", "Utama"),
            ("magnum", "/magnum-4d-results/", "Magnum"),
            ("toto", "/sports-toto-4d-results/", "Sports Toto"),
            ("damacai", "/da-ma-cai-results/", "Da Ma Cai"),
            ("history", "/past-results/", "Keputusan lepas"),
            ("ms", "/ms/", "Bahasa Melayu"),
        )
    else:
        items = (
            ("home", "/", "Home"),
            ("magnum", "/magnum-4d-results/", "Magnum"),
            ("toto", "/sports-toto-4d-results/", "Sports Toto"),
            ("damacai", "/da-ma-cai-results/", "Da Ma Cai"),
            ("history", "/past-results/", "Past results"),
            ("ms", "/ms/", "Bahasa Melayu"),
        )
    links = []
    for key, href, label in items:
        current_attr = ' aria-current="page"' if key == current else ""
        lang_attr = ' lang="ms"' if key == "ms" else ""
        links.append(f'<a href="{href}"{current_attr}{lang_attr}>{esc(label)}</a>')
    return "".join(links)


def footer(language: str = "en-MY") -> str:
    if language == "ms-MY":
        return """
<footer class="site-footer"><div class="footer-inner">
  <nav class="footer-nav" aria-label="Navigasi kaki halaman">
    <a href="/">Utama</a><a href="/about.html">Tentang Kami</a><a href="/methodology.html">Sumber &amp; Kaedah</a>
    <a href="/privacy.html">Privasi</a><a href="/disclaimer.html">Penafian</a>
    <a href="/affiliate-disclosure.html">Pendedahan Afiliasi</a><a href="/sitemap.xml">Peta Laman</a>
  </nav>
  <p class="footer-note">4DVIP88 ialah laman maklumat bebas. Laman ini tidak menerima pertaruhan atau mewakili penyedia keputusan yang dinamakan pada halaman ini. Sahkan nombor penting dengan penyedia berkaitan.</p>
</div></footer>"""
    return """
<footer class="site-footer"><div class="footer-inner">
  <nav class="footer-nav" aria-label="Footer">
    <a href="/">Home</a><a href="/about.html">About</a><a href="/methodology.html">Sources &amp; Method</a>
    <a href="/privacy.html">Privacy</a><a href="/disclaimer.html">Disclaimer</a>
    <a href="/affiliate-disclosure.html">Affiliate Disclosure</a><a href="/sitemap.xml">Sitemap</a>
  </nav>
  <p class="footer-note">4DVIP88 is an independent information website. It does not accept wagers or represent the result providers named on these pages. Verify important numbers with the relevant provider.</p>
</div></footer>"""


def page_schema(title: str, description: str, path: str, language: str, crumbs: list[tuple[str, str]]) -> str:
    graph: list[dict[str, Any]] = [
        {
            "@type": "WebPage",
            "@id": canonical(path) + "#webpage",
            "url": canonical(path),
            "name": title,
            "description": description,
            "inLanguage": language,
            "isPartOf": {"@id": BASE_URL + "/#website"},
        }
    ]
    if crumbs:
        graph.append(
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": position, "name": name, "item": canonical(href)}
                    for position, (name, href) in enumerate(crumbs, 1)
                ],
            }
        )
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))


def page_document(
    *,
    title: str,
    description: str,
    path: str,
    h1: str,
    lead: str,
    body: str,
    current: str,
    language: str = "en-MY",
    hreflang: bool = False,
    crumbs: list[tuple[str, str]] | None = None,
) -> str:
    crumbs = crumbs or [("Home", "/"), (h1, path)]
    breadcrumb_html = " &rsaquo; ".join(
        f'<a href="{esc(href)}">{esc(name)}</a>' if index < len(crumbs) - 1 else esc(name)
        for index, (name, href) in enumerate(crumbs)
    )
    alternates = ""
    if hreflang:
        alternates = (
            '<link rel="alternate" hreflang="en-MY" href="https://4dvip88.com/">'
            '<link rel="alternate" hreflang="ms-MY" href="https://4dvip88.com/ms/">'
            '<link rel="alternate" hreflang="x-default" href="https://4dvip88.com/">'
        )
    schema = page_schema(title, description, path, language, crumbs)
    breadcrumb_label = "Jejak halaman" if language == "ms-MY" else "Breadcrumb"
    document = f"""<!doctype html>
<html lang="{esc(language)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{esc(canonical(path))}">
  {alternates}
  <link rel="stylesheet" href="/assets/site.css?v=20260824-b23">
  <script type="application/ld+json">{schema}</script>
</head>
<body>
<header class="site-header"><div class="header-inner"><a class="site-brand" href="/">4DVIP88</a><nav class="primary-nav" aria-label="{'Navigasi utama' if language == 'ms-MY' else 'Primary'}">{nav(current, language)}</nav></div></header>
<main class="page-shell">
  <section class="page-hero">
    <nav class="breadcrumbs" aria-label="{breadcrumb_label}">{breadcrumb_html}</nav>
    <h1>{esc(h1)}</h1>
    <p class="lead">{esc(lead)}</p>
  </section>
  {body}
</main>
{footer(language)}
</body>
</html>
"""
    return "\n".join(line.rstrip() for line in document.splitlines()) + "\n"


def result_status(results: dict[str, Any], keys: Iterable[str]) -> str:
    shown = [results["providers"][key] for key in keys]
    latest = max(shown, key=lambda provider: datetime.strptime(provider["drawDate"], "%d-%m-%Y"))
    return (
        '<div class="status-box">'
        f'<p><strong>Most recent provider draw shown:</strong> {esc(latest["drawDate"])} ({esc(latest["drawDay"])})</p>'
        f'<p><strong>Data file updated:</strong> {esc(results["updated"])}</p>'
        '<p>Use this as a reference and verify important results with the relevant provider.</p>'
        '</div>'
    )


def result_grid(results: dict[str, Any], keys: Iterable[str], heading: str) -> str:
    keys = tuple(keys)
    return (
        '<section class="content-card">'
        f'<h2>{esc(heading)}</h2>{result_status(results, keys)}'
        f'<div class="results-grid">{pre.render_cards(results, keys)}</div>'
        '</section>'
    )


def provider_page(results: dict[str, Any], config: dict[str, Any]) -> str:
    body = result_grid(results, config["keys"], "Latest completed result")
    body += (
        '<section class="content-card"><h2>What this result page covers</h2>'
        f'<p>{esc(config["context"])}</p>'
        f'<p>{esc(config["coverage"])}</p>'
        '<h2>How to read and verify the result</h2>'
        f'<p>{esc(config["reading"])}</p>'
        f'<p>{esc(config["verification"])}</p>'
        '<p>The imported update time records when the data file changed. It does not by itself establish official status, finality or endorsement.</p>'
        f'<p><a href="{esc(config["related_href"])}">{esc(config["related_label"])}</a></p>'
        '<p><a href="/methodology.html">Read the source, freshness and correction methodology.</a></p></section>'
    )
    current = "magnum" if config["slug"].startswith("magnum") else "toto" if config["slug"].startswith("sports") else "damacai" if config["slug"].startswith("da-ma") else ""
    return page_document(
        title=config["title"], description=config["description"], path=f'/{config["slug"]}/',
        h1=config["h1"], lead=config["lead"], body=body, current=current,
    )


def region_page(results: dict[str, Any], config: dict[str, Any]) -> str:
    body = result_grid(results, config["keys"], "Provider comparison")
    body += (
        '<section class="content-card"><h2>What this regional page covers</h2>'
        f'<p>{esc(config["scope"])}</p>'
        '<h2>How to compare the results</h2>'
        f'<p>{esc(config["reading"])}</p>'
        f'<p>{esc(config["verification"])}</p>'
        '<ul class="page-links">'
        + "".join(f'<li><a href="{esc(href)}">{esc(label)}</a></li>' for label, href in config["links"])
        + '</ul></section>'
    )
    return page_document(
        title=config["title"], description=config["description"], path=f'/{config["slug"]}/',
        h1=config["h1"], lead=config["lead"], body=body, current="",
    )


def archive_page(results: dict[str, Any], iso_date: str) -> str:
    display_date = datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d %B %Y")
    path = f"/results/{iso_date}/"
    draw_date = datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    matching_providers = tuple(
        key for key in pre.REQUIRED_PROVIDERS if results["providers"][key].get("drawDate") == draw_date
    )
    if not matching_providers:
        raise pre.ValidationError(f"archive {iso_date} has no provider results with that draw date")
    body = result_grid(results, matching_providers, f"Recorded provider results for {display_date}")
    body += (
        '<section class="content-card"><h2>Archive scope</h2>'
        '<p>This dated page includes only provider records whose own draw date matches the date in this URL. Providers with a different schedule or draw date are not relabelled to fit the archive.</p>'
        '<p>Older result archives are retained as files. If an older draw needs a correction, verified retained source data and a dated manual rebuild are required; the current automated job regenerates only its newest completed draw.</p>'
        '<p><a href="/past-results/">Browse available past results.</a></p></section>'
    )
    return page_document(
        title=f"Malaysia 4D Results for {display_date} | 4DVIP88",
        description=f"Recorded Malaysia 4D results for {display_date}, including provider draw dates, numbers and source-status guidance.",
        path=path, h1=f"Malaysia 4D Results: {display_date}",
        lead="An archive containing only provider results recorded with this draw date.",
        body=body, current="history",
        crumbs=[("Home", "/"), ("Past results", "/past-results/"), (display_date, path)],
    )


def archive_dates(planned: dict[Path, str], current_iso: str) -> list[str]:
    dates = {current_iso}
    archive_root = REPO_ROOT / "results"
    if archive_root.exists():
        for child in archive_root.iterdir():
            if child.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", child.name) and (child / "index.html").exists():
                dates.add(child.name)
    for path in planned:
        match = re.search(r"results[\\/](\d{4}-\d{2}-\d{2})[\\/]index\.html$", str(path))
        if match:
            dates.add(match.group(1))
    return sorted(dates, reverse=True)


def archive_lastmods(
    metadata: dict[str, Any],
    dates: list[str],
    *,
    current_iso: str,
    content_modified_iso: str,
    mode: str,
    now: datetime | None = None,
) -> dict[str, str]:
    """Validate deterministic sitemap dates for every retained archive."""
    if metadata.get("schemaVersion") != ARCHIVE_METADATA_SCHEMA_VERSION:
        raise pre.ValidationError(
            f"archive metadata schemaVersion must be {ARCHIVE_METADATA_SCHEMA_VERSION}"
        )
    records = metadata.get("archives")
    if not isinstance(records, dict) or not records:
        raise pre.ValidationError("archive metadata records are missing")

    expected_dates = set(dates)
    recorded_dates = set(records)
    extra_dates = sorted(recorded_dates - expected_dates)
    missing_dates = sorted(expected_dates - recorded_dates)
    allowed_missing = {current_iso} if mode == "staging" else set()
    if extra_dates:
        raise pre.ValidationError(
            "archive metadata contains unretained dates: " + ", ".join(extra_dates)
        )
    if set(missing_dates) - allowed_missing:
        raise pre.ValidationError(
            "archive metadata is missing retained dates: " + ", ".join(missing_dates)
        )

    reference_now = now or datetime.now(pre.MYT)
    if reference_now.tzinfo is None or reference_now.utcoffset() is None:
        reference_now = reference_now.replace(tzinfo=pre.MYT)
    validated: dict[str, str] = {}
    for archive_date in sorted(recorded_dates):
        try:
            parsed_archive_date = datetime.strptime(archive_date, "%Y-%m-%d")
        except ValueError as exc:
            raise pre.ValidationError(
                f"archive metadata contains invalid date {archive_date!r}"
            ) from exc
        record = records[archive_date]
        if not isinstance(record, dict) or set(record) != {"lastmod"}:
            raise pre.ValidationError(
                f"archive metadata record for {archive_date} must contain only lastmod"
            )
        lastmod = record.get("lastmod")
        if not isinstance(lastmod, str):
            raise pre.ValidationError(f"archive metadata lastmod for {archive_date} is invalid")
        try:
            parsed_lastmod = datetime.strptime(lastmod, "%Y-%m-%d")
        except ValueError as exc:
            raise pre.ValidationError(
                f"archive metadata lastmod for {archive_date} is invalid"
            ) from exc
        if parsed_lastmod.date() < parsed_archive_date.date():
            raise pre.ValidationError(
                f"archive metadata lastmod for {archive_date} predates the archive"
            )
        if parsed_lastmod.date() > reference_now.astimezone(pre.MYT).date():
            raise pre.ValidationError(
                f"archive metadata lastmod for {archive_date} is in the future"
            )
        validated[archive_date] = lastmod

    if mode == "staging":
        validated[current_iso] = max(
            validated.get(current_iso, content_modified_iso),
            content_modified_iso,
        )
    elif validated.get(current_iso, "") < content_modified_iso:
        raise pre.ValidationError(
            f"archive metadata lastmod for current archive {current_iso} "
            f"predates the snapshot update {content_modified_iso}"
        )
    return validated


def past_results_page(dates: list[str]) -> str:
    links = "".join(
        f'<li><a href="/results/{date}/">Malaysia 4D results for {datetime.strptime(date, "%Y-%m-%d").strftime("%d %B %Y")}</a></li>'
        for date in dates
    )
    body = (
        '<section class="content-card"><h2>Available completed draw archives</h2>'
        f'<ul class="archive-list">{links}</ul>'
        '<p>The archive includes only completed result records retained by this website; 4DVIP88 does not invent earlier records from dates alone.</p>'
        '<h2>What a dated archive contains</h2>'
        '<p>Each archive URL represents one completed draw date and includes only provider records carrying that same date. Providers can follow different schedules, so an older provider record is not relabelled to make a date page look more complete.</p>'
        '<p>The page preserves the provider name, its draw date, available draw number and the result categories stored in the verified result record. The date in the URL describes the draw; the separate update timestamp records when the retained website file changed.</p>'
        '<h2>How to use the history carefully</h2>'
        '<ol><li>Open the required completed date.</li><li>Find the named provider and confirm its draw number.</li><li>Keep each number with its top, special or consolation label.</li><li>Verify important historical information with the relevant provider.</li></ol>'
        '<p>An older correction requires retained source evidence and a dated manual rebuild of the same archive URL. The site does not create empty future dates, spelling variants or mass provider-and-date doorway combinations.</p>'
        '<p><a href="/methodology.html">Read the source, retention and correction methodology.</a></p></section>'
    )
    return page_document(
        title="Malaysia 4D Past Results and History | 4DVIP88",
        description="Browse retained Malaysia 4D past results by genuine completed draw date, with provider details and source guidance.",
        path="/past-results/", h1="Malaysia 4D Past Results",
        lead="Browse completed result archives retained by this website.",
        body=body, current="history",
    )


def prize_guide_page() -> str:
    body = """
<section class="content-card">
  <h2>What the common result labels mean</h2>
  <p>A result table identifies numbers by category; it does not by itself determine what a ticket is worth. Read the provider, product, draw date and draw number before comparing any number.</p>
  <table class="guide-table">
    <caption>Common labels used on the result pages</caption>
    <thead><tr><th scope="col">Label</th><th scope="col">What this site displays</th><th scope="col">What to check</th></tr></thead>
    <tbody>
      <tr><th scope="row">First, second and third prize</th><td>The three top result-number positions for the named draw.</td><td>Match the exact number, including any leading zero, and keep it with its displayed position.</td></tr>
      <tr><th scope="row">Special</th><td>A separate group of published result numbers.</td><td>Do not treat a special number as a top-three result.</td></tr>
      <tr><th scope="row">Consolation</th><td>Another separately labelled group of result numbers.</td><td>Keep the category label when recording or comparing the result.</td></tr>
      <tr><th scope="row">3D, 5D, 6D or lotto</th><td>Product-specific formats shown only when present in the retained source data.</td><td>Use that product's own labels and rules; these fields are not ordinary 4D categories.</td></tr>
    </tbody>
  </table>
  <h2>Why fixed prize amounts are not listed here</h2>
  <p>Prize value, eligibility and claim rules can depend on the provider, product, ticket type, stake, draw and current terms. Those rules can change independently of the result number. 4DVIP88 therefore does not infer a payout from a number, promise that a ticket wins, or present an imported jackpot figure as claim advice.</p>
  <p>For a monetary value or claim decision, use the relevant provider's current rules and the information printed on the ticket. The result pages are an independent factual reference, not a substitute for provider confirmation.</p>
  <h2>A careful checking sequence</h2>
  <ol>
    <li>Choose the provider and product named on the ticket or record.</li>
    <li>Match the provider draw date and draw number.</li>
    <li>Compare every digit exactly and preserve leading zeroes.</li>
    <li>Keep the number with its first, second, third, special or consolation label.</li>
    <li>Verify prize value, eligibility and claim details with the relevant provider.</li>
  </ol>
  <h2>Choose a provider result</h2>
  <ul class="page-links"><li><a href="/magnum-4d-results/">Magnum 4D results</a></li><li><a href="/sports-toto-4d-results/">Sports Toto results</a></li><li><a href="/da-ma-cai-results/">Da Ma Cai results</a></li></ul>
  <p><a href="/methodology.html">Read how source, freshness and correction checks are handled.</a></p>
</section>"""
    return page_document(
        title="Malaysia 4D Prize Guide | Result Labels Explained | 4DVIP88",
        description="Understand common Malaysia 4D prize and result-table labels without unsupported payout or winning claims.",
        path="/4d-prize-guide/", h1="Malaysia 4D Prize Guide",
        lead="A factual guide to common labels used in 4D result tables.",
        body=body, current="",
    )


def malay_card(key: str, provider: dict[str, Any]) -> str:
    name = pre.DISPLAY_NAMES.get(key, provider.get("name", key))
    draw_date = malay_draw_date(provider.get("drawDate"), provider.get("drawDay"))
    provider_link = pre.PROVIDER_LINKS.get(key)
    heading = esc(name) if not provider_link else f'<a href="{esc(provider_link)}">{esc(name)}</a>'
    special = "".join(f"<li>{esc(value)}</li>" for value in pre.meaningful_numbers(provider.get("special")))
    consolation = "".join(f"<li>{esc(value)}</li>" for value in pre.meaningful_numbers(provider.get("consolation")))
    three_d = ""
    if key == "sabah88":
        values = provider.get("threeD", {})
        three_d = f"""
  <table class="top-prizes"><caption class="sr-only">Hadiah utama 3D Sabah 88</caption><thead><tr><th scope="col">Hadiah pertama 3D</th><th scope="col">Hadiah kedua 3D</th><th scope="col">Hadiah ketiga 3D</th></tr></thead>
  <tbody><tr><td>{esc(values.get("first"))}</td><td>{esc(values.get("second"))}</td><td>{esc(values.get("third"))}</td></tr></tbody></table>"""
    return f"""<article class="result-card">
  <div class="provider-heading"><h3 class="provider-title">{heading}</h3></div>
  <p class="result-meta">Tarikh cabutan: {esc(draw_date)}</p>
  <table class="top-prizes"><caption class="sr-only">Hadiah utama untuk {esc(name)}</caption><thead><tr><th scope="col">Hadiah pertama</th><th scope="col">Hadiah kedua</th><th scope="col">Hadiah ketiga</th></tr></thead>
  <tbody><tr><td>{esc(provider.get("first"))}</td><td>{esc(provider.get("second"))}</td><td>{esc(provider.get("third"))}</td></tr></tbody></table>
  <div class="number-group"><strong>Hadiah khas</strong><ul class="number-list">{special}</ul></div>
  <div class="number-group"><strong>Hadiah saguhati</strong><ul class="number-list">{consolation}</ul></div>
  {three_d}
</article>"""


def malay_draw_date(value: Any, day: Any) -> str:
    months = ("Januari", "Februari", "Mac", "April", "Mei", "Jun", "Julai", "Ogos", "September", "Oktober", "November", "Disember")
    days = {"Mon": "Isnin", "Tue": "Selasa", "Wed": "Rabu", "Thu": "Khamis", "Fri": "Jumaat", "Sat": "Sabtu", "Sun": "Ahad"}
    parsed = datetime.strptime(str(value), "%d-%m-%Y")
    return f"{parsed.day} {months[parsed.month - 1]} {parsed.year} ({days.get(str(day), str(day))})"


def malay_updated(value: Any) -> str:
    months = ("Januari", "Februari", "Mac", "April", "Mei", "Jun", "Julai", "Ogos", "September", "Oktober", "November", "Disember")
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2}) MYT", str(value))
    if not match:
        return str(value)
    year, month, day, clock = match.groups()
    return f"{int(day)} {months[int(month) - 1]} {year}, {clock} MYT"


def malay_page(results: dict[str, Any]) -> str:
    cards = "".join(
        malay_card(key, results["providers"][key])
        for key in ("toto", "magnum", "damacai", "gd4d", "sabah88", "sandakan", "cashsweep")
    )
    draw_date = malay_draw_date(results["drawDate"], results["drawDay"])
    updated = malay_updated(results["updated"])
    body = f"""
<section class="content-card">
  <h2>Keputusan 4D mengikut penyedia</h2>
  <p>Jika anda mencari keputusan 4D hari ini, semak tarikh cabutan yang dipaparkan terlebih dahulu. Halaman ini memaparkan keputusan yang tersedia di 4DVIP88, bukan keputusan masa nyata atau jaminan bahawa setiap penyedia mempunyai cabutan pada hari yang sama.</p>
  <p>Keputusan Sports Toto, Magnum 4D, Da Ma Cai, Grand Dragon, Sabah 88, Sandakan STC dan Special Cash Sweep dipaparkan mengikut penyedia dan tarikh cabutan masing-masing.</p>
  <div class="status-box"><p><strong>Tarikh keputusan terkini yang dipaparkan:</strong> {esc(draw_date)}</p><p><strong>Masa kemas kini data:</strong> {esc(updated)}</p></div>
  <div class="results-grid">{cards}</div>
  <h2>Cara membaca keputusan</h2>
  <p>Pastikan nama penyedia dan tarikh cabutan sepadan sebelum membandingkan nombor. Hadiah pertama, kedua, ketiga, khas dan saguhati ialah kategori yang berbeza. Sifar di hadapan nombor perlu dikekalkan.</p>
  <h2>Tarikh dan masa kemas kini</h2>
  <p>Halaman ini memaparkan tarikh cabutan dan masa data dikemas kini. Rujuk kedua-dua maklumat tersebut untuk menilai sama ada keputusan yang dipaparkan masih terkini.</p>
  <h2>Sumber dan pengesahan</h2>
  <p>4DVIP88 ialah laman maklumat bebas dan tidak mewakili penyedia keputusan yang dinamakan pada halaman ini. Keputusan bagi beberapa penyedia utama disemak silang menggunakan dua suapan data agregat, manakala keputusan bagi penyedia lain diperoleh daripada satu suapan automatik. Untuk pengesahan, bandingkan nombor dan tarikh cabutan dengan keputusan yang diterbitkan oleh penyedia berkaitan.</p>
  <p><a href="/methodology.html">Baca kaedah sumber, kesegaran data dan pembetulan.</a></p>
  <p class="language-switch"><a href="/" hreflang="en-MY">Lihat halaman ini dalam bahasa Inggeris</a></p>
</section>"""
    return page_document(
        title="Keputusan 4D Malaysia | 4DVIP88",
        description="Semak keputusan 4D Malaysia terkini untuk Sports Toto, Magnum 4D, Da Ma Cai dan penyedia lain, bersama tarikh cabutan dan masa kemas kini.",
        path="/ms/", h1="Keputusan 4D Malaysia",
        lead="Semak keputusan 4D bagi penyedia utama di Malaysia, bersama tarikh cabutan dan masa kemas kini.",
        body=body, current="ms", language="ms-MY", hreflang=True,
        crumbs=[("Utama", "/"), ("Keputusan 4D", "/ms/")],
    )


def sitemap_document(paths: list[tuple[str, str]]) -> str:
    rows = []
    for path, lastmod in paths:
        rows.append(f"  <url>\n    <loc>{esc(canonical(path))}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"


def build(
    results: dict[str, Any],
    policy: dict[str, Any],
    *,
    mode: str,
    now: datetime | None = None,
) -> dict[Path, str]:
    pre.validate_results_shape(results, now=now)
    blockers = pre.policy_blockers(policy, results, mode=mode, now=now)
    if blockers:
        raise pre.ValidationError(mode.upper() + "_BLOCKED: " + "; ".join(blockers))

    current_iso = datetime.strptime(results["drawDate"], "%d-%m-%Y").strftime("%Y-%m-%d")
    content_modified_iso = pre.parse_updated(results["updated"]).strftime("%Y-%m-%d")
    planned: dict[Path, str] = {}

    index_path = REPO_ROOT / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index = replace_marker(
        index,
        "UPDATED",
        f'<span data-generated-draw="{esc(results["drawDate"])}" data-generated-updated="{esc(results["updated"])}">'
        f'Draw {esc(results["drawDate"])} ({esc(results["drawDay"])}) · updated {esc(results["updated"])}</span>',
    )
    index = replace_marker(index, "RESULTS", "\n" + pre.render_results_fragment(results))
    planned[index_path] = index

    for config in PROVIDER_PAGES:
        planned[REPO_ROOT / config["slug"] / "index.html"] = provider_page(results, config)
    for config in REGION_PAGES:
        planned[REPO_ROOT / config["slug"] / "index.html"] = region_page(results, config)

    archive_path = REPO_ROOT / "results" / current_iso / "index.html"
    planned[archive_path] = archive_page(results, current_iso)
    dates = archive_dates(planned, current_iso)
    metadata = pre.read_json(ARCHIVE_METADATA_PATH)
    archive_lastmod = archive_lastmods(
        metadata,
        dates,
        current_iso=current_iso,
        content_modified_iso=content_modified_iso,
        mode=mode,
        now=now,
    )
    planned[REPO_ROOT / "past-results" / "index.html"] = past_results_page(dates)
    planned[REPO_ROOT / "4d-prize-guide" / "index.html"] = prize_guide_page()
    planned[REPO_ROOT / "ms" / "index.html"] = malay_page(results)

    static_paths = [
        ("/", content_modified_iso),
        ("/privacy.html", "2026-08-25"),
        ("/disclaimer.html", "2026-08-24"),
        ("/about.html", "2026-08-24"),
        ("/methodology.html", "2026-08-24"),
        ("/affiliate-disclosure.html", "2026-08-24"),
    ]
    generated_paths = [(f'/{config["slug"]}/', content_modified_iso) for config in PROVIDER_PAGES + REGION_PAGES]
    generated_paths.extend([("/past-results/", content_modified_iso), ("/4d-prize-guide/", "2026-08-24"), ("/ms/", content_modified_iso)])
    archive_paths = [
        (f"/results/{date}/", archive_lastmod[date])
        for date in dates
    ]
    planned[REPO_ROOT / "sitemap.xml"] = sitemap_document(static_paths + generated_paths + archive_paths)
    return planned


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("staging", "publication"), required=True)
    parser.add_argument("--results", type=Path, default=REPO_ROOT / "results.json")
    parser.add_argument("--policy", type=Path, default=TOOL_DIR / "provenance-policy.json")
    parser.add_argument("--check", action="store_true", help="fail if generated files differ; do not write")
    return parser.parse_args(argv)


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        results = pre.read_json(args.results.resolve())
        policy = pre.read_json(args.policy.resolve())
        planned = build(results, policy, mode=args.mode)
        changed = [path for path, content in planned.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
        if args.check:
            if changed:
                print("OUT_OF_DATE: " + ", ".join(str(path.relative_to(REPO_ROOT)) for path in changed), file=sys.stderr)
                return 1
            print(f"CHECKED {len(planned)} generated files")
            return 0
        written = [path for path, content in planned.items() if atomic_write(path, content)]
        print(f"BUILT {len(planned)} files; changed {len(written)}")
        for path in written:
            print(path.relative_to(REPO_ROOT))
        return 0
    except (OSError, pre.ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
