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

    def test_checked_in_pages_are_synchronized(self) -> None:
        check = self.run_generator(REPO, "--check")
        self.assertEqual(check.returncode, 0, check.stderr or check.stdout)
        results = json.loads((REPO / "results.json").read_text(encoding="utf-8"))
        lastmod = results["updated"][:10]
        sitemap = (REPO / "sitemap.xml").read_text(encoding="utf-8")
        for relative_path in supporting.TARGET_PATHS:
            html = (REPO / relative_path).read_text(encoding="utf-8")
            self.assertIn(results["updated"], html)
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

    def assert_provider_facts(self, html: str, provider: dict) -> None:
        for field in ("drawDate", "drawDay", "drawNo", "first", "second", "third"):
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
        temporary, target = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        page = target / "magnum-4d-results" / "index.html"
        page.write_text(page.read_text(encoding="utf-8").replace("Magnum 4D Results in Malaysia", "Changed shell title", 1), encoding="utf-8")
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
        del results["providers"]["damacai"]
        results_path.write_text(json.dumps(results), encoding="utf-8")
        guarded = [target / path for path in (*supporting.TARGET_PATHS, "sitemap.xml")]
        before = [digest(path) for path in guarded]
        run = self.run_generator(target)
        self.assertEqual(run.returncode, 2)
        self.assertIn("missing target providers", run.stderr)
        self.assertEqual(before, [digest(path) for path in guarded])

    def test_missing_unrelated_optional_provider_does_not_block_target_pages(self) -> None:
        temporary, target = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        results_path = target / "results.json"
        results = json.loads(results_path.read_text(encoding="utf-8"))
        del results["providers"]["gd4d"]
        results_path.write_text(json.dumps(results), encoding="utf-8")
        run = self.run_generator(target)
        self.assertEqual(run.returncode, 0, run.stderr or run.stdout)


if __name__ == "__main__":
    unittest.main()
