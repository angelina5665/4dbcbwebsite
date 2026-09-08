"""Regression gates for the explicitly retained September archive backfill."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / ".github/seo-prerender"
sys.path.insert(0, str(TOOL))
import build_site as site

EVIDENCE = TOOL / "retained-results"
DATES = ("2026-09-05", "2026-09-06")
KEYS = tuple(key for key in site.pre.REQUIRED_PROVIDERS if key != "gd4d")


class RetainedArchiveTests(unittest.TestCase):
    def data(self, date: str) -> dict:
        return json.loads((EVIDENCE / f"{date}.json").read_bytes())

    def page(self, date: str) -> str:
        return (REPO / f"results/{date}/index.html").read_text(encoding="utf-8")

    def test_retained_bytes_and_historical_shapes(self):
        manifest = json.loads((EVIDENCE / "manifest.json").read_text())
        self.assertEqual(set(manifest["archives"]), set(DATES))
        for date in DATES:
            with self.subTest(date=date):
                record = manifest["archives"][date]
                raw = (EVIDENCE / f"{date}.json").read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), record["sha256"])
                data = json.loads(raw)
                site.pre.validate_results_shape(data, now=site.pre.parse_updated(data["updated"]))
                self.assertEqual(record["publishedProviderKeys"], list(KEYS))
                self.assertIn("not independent", record["historicalSourceComparison"])
                self.assertEqual(set(data["providers"]), set(site.pre.REQUIRED_PROVIDERS))

    def test_only_supported_date_provider_cards_are_rendered(self):
        for date in DATES:
            with self.subTest(date=date):
                page, data = self.page(date), self.data(date)
                actual = re.findall(r'<article[^>]+data-provider="([^"]+)"', page)
                self.assertEqual(actual, list(KEYS))
                for key in KEYS:
                    expected = site.pre.render_cards(data, (key,))
                    self.assertIn(expected, page)
                    self.assertEqual(data["providers"][key]["drawDate"], "-".join(reversed(date.split("-"))))
                self.assertNotIn('data-provider="gd4d"', page)
                self.assertIn("Grand Dragon is omitted", page)
                self.assertNotIn("automated job regenerates only its newest completed draw", page)
                self.assertIn("not refreshed by the scheduled results updater", page)
                self.assertIn("<strong>Retained data imported:</strong>", page)

    def test_archive_crawlability_and_existing_template(self):
        current_template = (REPO / "results/2026-08-23/index.html").read_text(encoding="utf-8")
        for date in DATES:
            with self.subTest(date=date):
                page = self.page(date)
                self.assertEqual(len(re.findall(r"<h1(?:\s|>)", page)), 1)
                self.assertEqual(re.findall(r'<link rel="canonical" href="([^"]+)"', page), [f"https://4dvip88.com/results/{date}/"])
                self.assertNotIn('<meta name="robots" content="noindex', page)
                self.assertEqual(re.findall(r'<link rel="stylesheet"[^>]*>', page), re.findall(r'<link rel="stylesheet"[^>]*>', current_template))
                self.assertNotIn("<style", page)
                self.assertNotIn("style=", page)
                for tag in ("header", "footer"):
                    pattern = rf"<{tag}\b.*?</{tag}>"
                    self.assertEqual(re.search(pattern, page, re.S).group(), re.search(pattern, current_template, re.S).group())
                schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1))
                self.assertEqual(schema["@graph"][0]["url"], f"https://4dvip88.com/results/{date}/")
                self.assertEqual(schema["@graph"][1]["itemListElement"][-1]["item"], f"https://4dvip88.com/results/{date}/")

    def test_history_sitemap_and_metadata_agree(self):
        history = (REPO / "past-results/index.html").read_text(encoding="utf-8")
        metadata = json.loads((TOOL / "archive-metadata.json").read_text())["archives"]
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        root = ET.parse(REPO / "sitemap.xml").getroot()
        entries = {node.find("s:loc", ns).text: node.find("s:lastmod", ns).text for node in root}
        self.assertEqual(len(entries), len(list(root)))
        for date in DATES:
            self.assertEqual(history.count(f'href="/results/{date}/"'), 1)
            self.assertEqual(entries[f"https://4dvip88.com/results/{date}/"], metadata[date]["lastmod"])
        self.assertLess(history.index("2026-09-06"), history.index("2026-09-05"))

    def test_bad_provider_selection_is_rejected(self):
        data = self.data(DATES[0])
        for keys in (("magnum", "magnum"), ("invented",), ()):
            with self.subTest(keys=keys), self.assertRaises(site.pre.ValidationError):
                site.archive_page(data, DATES[0], provider_keys=keys)

    def test_empty_or_wrong_date_archives_are_rejected(self):
        with self.assertRaises(site.pre.ValidationError):
            site.archive_page(self.data(DATES[0]), "2026-09-07", provider_keys=KEYS)

    def test_incomplete_or_wrong_weekday_records_fail_shape_gate(self):
        original = self.data(DATES[0])
        for field in ("incomplete", "weekday"):
            data = copy.deepcopy(original)
            if field == "incomplete":
                data["providers"]["magnum"]["first"] = "----"
            else:
                data["providers"]["magnum"]["drawDay"] = "Mon"
            with self.subTest(field=field), self.assertRaises(site.pre.ValidationError):
                site.pre.validate_results_shape(data, now=site.pre.parse_updated(data["updated"]))

    def test_default_archive_selection_remains_compatible(self):
        data = self.data(DATES[0])
        default = site.archive_page(data, DATES[0])
        explicit = site.archive_page(data, DATES[0], provider_keys=site.pre.REQUIRED_PROVIDERS)
        self.assertEqual(default, explicit)
        self.assertEqual(default.count('data-provider="'), 10)


if __name__ == "__main__":
    unittest.main()
