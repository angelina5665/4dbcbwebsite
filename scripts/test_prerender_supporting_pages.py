from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
GENERATOR = REPO / "scripts" / "prerender_supporting_pages.py"
sys.path.insert(0, str(REPO / "scripts"))
import prerender_supporting_pages as supporting  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SupportingPageTests(unittest.TestCase):
    def run_generator(self, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(GENERATOR), "--repo", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def make_fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory(prefix="4dvip88-supporting-")
        target = Path(temporary.name)
        for name in ("results.json", "sitemap.xml"):
            shutil.copy2(REPO / name, target / name)
        for relative_path in supporting.TARGET_PATHS:
            destination = target / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / relative_path, destination)
        return temporary, target

    def test_target_inventory_is_exact(self) -> None:
        self.assertEqual(
            supporting.TARGET_PATHS,
            (
                "magnum-4d-results/index.html",
                "sports-toto-4d-results/index.html",
                "da-ma-cai-results/index.html",
                "sabah-88-4d-results/index.html",
                "special-cash-sweep-results/index.html",
                "sandakan-stc-4d-results/index.html",
                "west-malaysia-4d-results/index.html",
                "east-malaysia-4d-results/index.html",
                "ms/index.html",
            ),
        )

    def test_checked_in_pages_are_synchronized(self) -> None:
        check = self.run_generator(REPO, "--check")
        self.assertEqual(check.returncode, 0, check.stderr or check.stdout)
        results = json.loads((REPO / "results.json").read_text(encoding="utf-8"))
        lastmod = results["updated"][:10]
        sitemap = (REPO / "sitemap.xml").read_text(encoding="utf-8")
        for relative_path in supporting.TARGET_PATHS:
            html = (REPO / relative_path).read_text(encoding="utf-8")
            expected_updated = (
                supporting.site.malay_updated(results["updated"])
                if relative_path == supporting.MALAY_PATH
                else results["updated"]
            )
            self.assertIn(expected_updated, html)
            self.assertEqual(html.count("<h1"), 1)
            route = "/" + relative_path.removesuffix("index.html")
            self.assertRegex(
                sitemap,
                rf"<loc>https://4dvip88\.com{route}</loc>\s*<lastmod>{lastmod}</lastmod>",
            )
        for slug, config in supporting.PROVIDER_CONFIGS.items():
            html = (REPO / slug / "index.html").read_text(encoding="utf-8")
            self.assertEqual(re.findall(r'data-provider="([^"]+)"', html), list(config["keys"]))
            for key in config["keys"]:
                provider = results["providers"][key]
                self.assert_provider_facts(html, provider)

        for slug, config in supporting.REGION_CONFIGS.items():
            html = (REPO / slug / "index.html").read_text(encoding="utf-8")
            self.assertEqual(re.findall(r'data-provider="([^"]+)"', html), list(config["keys"]))
            for key in config["keys"]:
                self.assert_provider_facts(html, results["providers"][key])

        malay = (REPO / supporting.MALAY_PATH).read_text(encoding="utf-8")
        for key in supporting.site.MALAY_PROVIDER_KEYS:
            self.assert_provider_numbers(malay, results["providers"][key])

    def assert_provider_facts(self, html: str, provider: dict) -> None:
        for field in ("drawDate", "drawDay", "drawNo", "first", "second", "third"):
            if provider.get(field):
                self.assertIn(provider[field], html)
        for field in ("special", "consolation"):
            for value in provider.get(field, []):
                if any(character.isdigit() for character in value):
                    self.assertIn(value, html)

    def assert_provider_numbers(self, html: str, provider: dict) -> None:
        for field in ("first", "second", "third"):
            if provider.get(field):
                self.assertIn(provider[field], html)
        for field in ("special", "consolation"):
            for value in provider.get(field, []):
                if any(character.isdigit() for character in value):
                    self.assertIn(value, html)

    def test_generation_is_idempotent_and_preserves_page_shells(self) -> None:
        temporary, target = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        results_path = target / "results.json"
        results = json.loads(results_path.read_text(encoding="utf-8"))
        results["providers"]["magnum"]["first"] = "0001"
        results_path.write_text(json.dumps(results), encoding="utf-8")
        before = {
            relative_path: supporting.mask_result_region(
                (target / relative_path).read_text(encoding="utf-8"), relative_path
            )
            for relative_path in supporting.TARGET_PATHS
        }

        first = self.run_generator(target)
        self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
        for relative_path in supporting.TARGET_PATHS:
            current = (target / relative_path).read_text(encoding="utf-8")
            self.assertEqual(before[relative_path], supporting.mask_result_region(current, relative_path))
        first_hashes = {path: digest(target / path) for path in (*supporting.TARGET_PATHS, "sitemap.xml")}

        second = self.run_generator(target)
        self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
        second_hashes = {path: digest(target / path) for path in (*supporting.TARGET_PATHS, "sitemap.xml")}
        self.assertEqual(first_hashes, second_hashes)

    def test_non_result_html_drift_blocks_all_writes(self) -> None:
        cases = (
            ("magnum-4d-results/index.html", "Magnum 4D Results in Malaysia"),
            ("west-malaysia-4d-results/index.html", "West Malaysia 4D Results"),
            ("ms/index.html", "Keputusan 4D Malaysia"),
        )
        for relative_path, original in cases:
            with self.subTest(relative_path=relative_path):
                temporary, target = self.make_fixture()
                self.addCleanup(temporary.cleanup)
                page = target / relative_path
                page.write_text(
                    page.read_text(encoding="utf-8").replace(original, "Changed shell title", 1),
                    encoding="utf-8",
                )
                guarded = [target / path for path in (*supporting.TARGET_PATHS, "sitemap.xml")]
                before = [digest(path) for path in guarded]
                run = self.run_generator(target)
                self.assertEqual(run.returncode, 2)
                self.assertIn("non-result HTML drift", run.stderr)
                self.assertEqual(before, [digest(path) for path in guarded])

    def test_incomplete_provider_set_blocks_all_writes(self) -> None:
        temporary, target = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        results_path = target / "results.json"
        results = json.loads(results_path.read_text(encoding="utf-8"))
        del results["providers"]["totoextra"]
        results_path.write_text(json.dumps(results), encoding="utf-8")
        guarded = [target / path for path in (*supporting.TARGET_PATHS, "sitemap.xml")]
        before = [digest(path) for path in guarded]
        run = self.run_generator(target)
        self.assertEqual(run.returncode, 2)
        self.assertIn("provider set mismatch", run.stderr)
        self.assertEqual(before, [digest(path) for path in guarded])

    def test_sitemap_updates_only_target_lastmods(self) -> None:
        temporary, target = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        sitemap_path = target / "sitemap.xml"
        sitemap = sitemap_path.read_text(encoding="utf-8")
        sitemap_path.write_text(re.sub(r"<lastmod>[^<]+</lastmod>", "<lastmod>2000-01-01</lastmod>", sitemap), encoding="utf-8")

        run = self.run_generator(target)
        self.assertEqual(run.returncode, 0, run.stderr or run.stdout)

        updated = sitemap_path.read_text(encoding="utf-8")
        expected_lastmod = json.loads((target / "results.json").read_text(encoding="utf-8"))["updated"][:10]
        target_routes = {"/" + path.removesuffix("index.html") for path in supporting.TARGET_PATHS}
        entries = re.findall(r"<loc>https://4dvip88\.com([^<]*)</loc>\s*<lastmod>([^<]+)</lastmod>", updated)
        self.assertEqual(len(entries), 19)
        for route, lastmod in entries:
            self.assertEqual(lastmod, expected_lastmod if route in target_routes else "2000-01-01")

    def test_workflow_allowlist_covers_exact_generated_files(self) -> None:
        workflow = (REPO / ".github" / "workflows" / "update-results.yml").read_text(encoding="utf-8")
        generated_match = re.search(r"generated=\(([^)]+)\)", workflow)
        expected_match = re.search(r"expected='([^']+)'", workflow)
        self.assertIsNotNone(generated_match)
        self.assertIsNotNone(expected_match)

        generated = generated_match.group(1).split()
        expected_generated = ["results.json", "index.html", "sitemap.xml", *supporting.TARGET_PATHS]
        self.assertEqual(generated, expected_generated)
        allowlist = re.compile(expected_match.group(1))
        for relative_path in expected_generated:
            self.assertIsNotNone(allowlist.fullmatch(relative_path), relative_path)
        for unexpected in ("about.html", "assets/site.css", "results/2026-08-31/index.html"):
            self.assertIsNone(allowlist.fullmatch(unexpected), unexpected)


if __name__ == "__main__":
    unittest.main()
