from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOL_DIR.parents[1]
SCRIPT = TOOL_DIR / "prerender_results.py"
FIXTURE = TOOL_DIR / "tests" / "fixtures" / "results.synthetic.json"
SYNTHETIC_OUTPUT = TOOL_DIR / "tests" / "generated" / "synthetic-results-preview.html"

sys.path.insert(0, str(TOOL_DIR))
import build_site  # noqa: E402
import prerender_results as pre  # noqa: E402

SCRAPE_SPEC = importlib.util.spec_from_file_location("scrape", REPO_ROOT / "scrape.py")
assert SCRAPE_SPEC and SCRAPE_SPEC.loader
scrape = importlib.util.module_from_spec(SCRAPE_SPEC)
SCRAPE_SPEC.loader.exec_module(scrape)


def current_results() -> dict:
    return json.loads((REPO_ROOT / "results.json").read_text(encoding="utf-8"))


def current_policy() -> dict:
    return json.loads((TOOL_DIR / "provenance-policy.json").read_text(encoding="utf-8"))


def reviewed_now() -> datetime:
    return pre.parse_updated(current_results()["updated"]) + timedelta(minutes=2)


def moon_from_results(results: dict) -> dict:
    moon = {}
    for provider_key, moon_key in scrape.MOON_PROVIDER_KEYS.items():
        provider = results["providers"][provider_key]
        draw_date = datetime.strptime(provider["drawDate"], "%d-%m-%Y")
        source = {
            "DD": f'({provider["drawDay"]}) {draw_date.strftime("%d-%b-%Y")}',
            "DN": "#" + provider.get("drawNo", "").replace("-", "/"),
            "P1": provider["first"],
            "P2": provider["second"],
            "P3": provider["third"],
        }
        for index, value in enumerate(scrape.numeric_values(provider.get("special", [])), 1):
            if index <= 13:
                source[f"S{index}"] = value
        for index, value in enumerate(scrape.numeric_values(provider.get("consolation", [])), 1):
            if index <= 10:
                source[f"C{index}"] = value
        moon[moon_key] = source
    totoextra = results["providers"]["totoextra"]
    toto_source = moon["T"]
    five_keys = ("P5D1", "P5D4", "P5D2", "P5D5", "P5D3", "P5D6")
    for key, value in zip(five_keys, totoextra["fiveD"]):
        toto_source[key] = value
    six_keys = ("P6D1", "P6D2A", "P6D2B", "P6D3A", "P6D3B", "P6D4A", "P6D4B", "P6D5A", "P6D5B")
    for key, value in zip(six_keys, totoextra["sixD"]):
        toto_source[key] = value
    lotto_keys = {
        "Star Toto 6/50": ("P650", "P650EX", ("P650JP1", "P650JP2")),
        "Power Toto 6/55": ("P655", None, ("P655JP",)),
        "Supreme Toto 6/58": ("P658", None, ("P658JP",)),
    }
    for lotto in totoextra["lotto"]:
        prefix, bonus_key, jackpot_keys = lotto_keys[lotto["title"]]
        for index, value in enumerate(lotto["balls"], 1):
            toto_source[f"{prefix}{index}"] = value
        if bonus_key:
            toto_source[bonus_key] = lotto["bonus"]
        for key, row in zip(jackpot_keys, lotto["jackpots"]):
            toto_source[key] = row[1]
    return moon


class ResultValidationTests(unittest.TestCase):
    def test_current_snapshot_passes_shape_validation(self) -> None:
        pre.validate_results_shape(current_results(), now=reviewed_now())

    def test_missing_provider_fails_closed(self) -> None:
        results = current_results()
        results["providers"].pop("magnum")
        with self.assertRaisesRegex(pre.ValidationError, "provider set mismatch"):
            pre.validate_results_shape(results, now=reviewed_now())

    def test_invalid_number_fails_closed(self) -> None:
        results = current_results()
        results["providers"]["magnum"]["first"] = "winner"
        with self.assertRaisesRegex(pre.ValidationError, "invalid first"):
            pre.validate_results_shape(results, now=reviewed_now())

    def test_three_digit_4d_number_fails_closed(self) -> None:
        results = current_results()
        results["providers"]["sabah88"]["first"] = "123"
        with self.assertRaisesRegex(pre.ValidationError, "invalid first"):
            pre.validate_results_shape(results, now=reviewed_now())

    def test_malformed_special_values_fail_closed(self) -> None:
        results = current_results()
        results["providers"]["magnum"]["special"] = ["12x4"] * 10
        with self.assertRaisesRegex(pre.ValidationError, "malformed special"):
            pre.validate_results_shape(results, now=reviewed_now())

    def test_empty_toto_lotto_objects_fail_closed(self) -> None:
        results = current_results()
        results["providers"]["totoextra"]["lotto"] = [{}, {}, {}]
        with self.assertRaisesRegex(pre.ValidationError, "lotto titles"):
            pre.validate_results_shape(results, now=reviewed_now())

    def test_future_draw_fails_closed(self) -> None:
        results = current_results()
        for provider in results["providers"].values():
            provider["drawDate"] = "25-08-2026"
            provider["drawDay"] = "Tue"
        results["drawDate"] = "25-08-2026"
        results["drawDay"] = "Tue"
        with self.assertRaisesRegex(pre.ValidationError, "future draw date"):
            pre.validate_results_shape(results, now=reviewed_now())

    def test_incorrect_weekday_fails_closed(self) -> None:
        results = current_results()
        results["providers"]["magnum"]["drawDay"] = "Mon"
        with self.assertRaisesRegex(pre.ValidationError, "does not match"):
            pre.validate_results_shape(results, now=reviewed_now())

    def test_related_provider_date_mismatch_fails(self) -> None:
        results = current_results()
        results["providers"]["totoextra"]["drawDate"] = "22-08-2026"
        results["providers"]["totoextra"]["drawDay"] = "Sat"
        with self.assertRaisesRegex(pre.ValidationError, "extended result dates"):
            pre.validate_results_shape(results, now=reviewed_now())

    def test_stale_provider_fails(self) -> None:
        results = current_results()
        with self.assertRaisesRegex(pre.ValidationError, "more than 7 days old"):
            pre.validate_results_shape(results, now=datetime(2026, 9, 20, 12, 0, tzinfo=pre.MYT))


class PolicyAndRenderingTests(unittest.TestCase):
    def tearDown(self) -> None:
        SYNTHETIC_OUTPUT.unlink(missing_ok=True)

    def test_staging_and_approved_publication_policy_pass(self) -> None:
        policy = current_policy()
        results = current_results()
        self.assertEqual([], pre.policy_blockers(policy, results, mode="staging"))
        self.assertEqual([], pre.policy_blockers(policy, results, mode="publication"))

    def test_snapshot_verification_ids_are_declared_and_unique(self) -> None:
        results = current_results()
        results["provenance"]["snapshotVerificationIds"].append("unknown-verification")
        blockers = pre.policy_blockers(current_policy(), results, mode="staging")
        self.assertTrue(any("unknown snapshot verification" in blocker for blocker in blockers))

        results = current_results()
        results["provenance"]["snapshotVerificationIds"].append(
            results["provenance"]["snapshotVerificationIds"][0]
        )
        blockers = pre.policy_blockers(current_policy(), results, mode="staging")
        self.assertTrue(any("contains duplicates" in blocker for blocker in blockers))

    def test_snapshot_verification_ids_and_policy_schema_are_restricted(self) -> None:
        policy = current_policy()
        policy["schemaVersion"] = 2
        policy["accuracyReview"]["snapshotVerifications"][""] = {}
        blockers = pre.policy_blockers(policy, current_results(), mode="staging")
        self.assertTrue(any("schemaVersion" in blocker for blocker in blockers))
        self.assertTrue(any("invalid snapshot verification ID" in blocker for blocker in blockers))

        results = current_results()
        results["provenance"]["snapshotVerificationIds"] = [""]
        blockers = pre.policy_blockers(current_policy(), results, mode="staging")
        self.assertTrue(any("not a valid ID list" in blocker for blocker in blockers))

    def test_snapshot_verification_digest_binds_exact_provider_object(self) -> None:
        results = current_results()
        results["providers"]["cashsweep"]["first"] = "0000"
        blockers = pre.policy_blockers(current_policy(), results, mode="staging")
        self.assertTrue(any("digest does not match cashsweep" in blocker for blocker in blockers))
        publication_blockers = pre.policy_blockers(current_policy(), results, mode="publication")
        self.assertTrue(any("cashsweep" in blocker and "lacks an independent" in blocker for blocker in publication_blockers))

    def test_snapshot_verification_binds_draw_date_and_number(self) -> None:
        policy = current_policy()
        verification = policy["accuracyReview"]["snapshotVerifications"][
            "draw-2026-08-23-provider-owned-2026-08-24"
        ]
        verification["providers"]["cashsweep"]["drawDate"] = "22-08-2026"
        verification["providers"]["sandakan"]["drawNo"] = "999-26"
        blockers = pre.policy_blockers(policy, current_results(), mode="staging")
        self.assertTrue(any("draw date does not match cashsweep" in blocker for blocker in blockers))
        self.assertTrue(any("draw number does not match sandakan" in blocker for blocker in blockers))

    def test_future_snapshot_verification_is_blocked(self) -> None:
        policy = current_policy()
        policy["accuracyReview"]["snapshotVerifications"][
            "draw-2026-08-23-provider-owned-2026-08-24"
        ]["checkedAt"] = "2099-01-01T00:00:00+08:00"
        blockers = pre.policy_blockers(policy, current_results(), mode="staging")
        self.assertTrue(any("checkedAt is in the future" in blocker for blocker in blockers))

    def test_malformed_evidence_fails_closed_without_exception(self) -> None:
        policy = current_policy()
        binding = policy["accuracyReview"]["snapshotVerifications"][
            "draw-2026-08-23-provider-owned-2026-08-24"
        ]["providers"]["cashsweep"]
        binding["evidenceSources"] = [["not", "an", "object"], {"url": ["not-hashable"]}]
        blockers = pre.policy_blockers(policy, current_results(), mode="publication")
        self.assertTrue(any("malformed evidence" in blocker for blocker in blockers))
        self.assertTrue(any("cashsweep" in blocker and "lacks an independent" in blocker for blocker in blockers))

    def test_same_publisher_aliases_do_not_count_as_independent(self) -> None:
        policy = current_policy()
        binding = policy["accuracyReview"]["snapshotVerifications"][
            "draw-2026-08-23-provider-owned-2026-08-24"
        ]["providers"]["cashsweep"]
        binding["evidenceSources"] = [
            {
                "url": "https://www.cashsweep.my/api/results/draw/number/5334",
                "publisherId": "special-cash-sweep",
                "role": "provider-owned",
            },
            {
                "url": "https://cashsweep.my/results",
                "publisherId": "special-cash-sweep",
                "role": "provider-owned",
            },
        ]
        blockers = pre.policy_blockers(policy, current_results(), mode="publication")
        self.assertTrue(any("lacks required source roles" in blocker for blocker in blockers))
        self.assertTrue(any("lacks separate publishers" in blocker for blocker in blockers))
        self.assertTrue(any("cashsweep" in blocker and "lacks an independent" in blocker for blocker in blockers))

    def test_future_scrape_can_stage_without_reusing_manual_verification(self) -> None:
        results = current_results()
        results["provenance"].pop("snapshotVerificationIds")
        self.assertEqual([], pre.policy_blockers(current_policy(), results, mode="staging"))
        blockers = pre.policy_blockers(current_policy(), results, mode="publication")
        self.assertTrue(any("cashsweep" in blocker and "gd4d" in blocker for blocker in blockers))

    def test_raw_fragment_contains_priority_numbers_and_no_second_h1(self) -> None:
        fragment = pre.render_results_fragment(current_results())
        self.assertIn("6456", fragment)
        self.assertIn("1917", fragment)
        self.assertIn("4083", fragment)
        self.assertIn("<h2", fragment)
        self.assertNotIn("<h1", fragment)

    def test_build_plan_contains_required_pages_and_sitemap_urls(self) -> None:
        planned = build_site.build(current_results(), current_policy(), mode="staging")
        relative = {str(path.relative_to(REPO_ROOT)).replace("\\", "/") for path in planned}
        self.assertIn("magnum-4d-results/index.html", relative)
        self.assertIn("sports-toto-4d-results/index.html", relative)
        self.assertIn("da-ma-cai-results/index.html", relative)
        self.assertIn("ms/index.html", relative)
        self.assertIn("results/2026-08-23/index.html", relative)
        sitemap = planned[REPO_ROOT / "sitemap.xml"]
        self.assertIn("https://4dvip88.com/magnum-4d-results/", sitemap)
        self.assertNotIn("example.com", sitemap)

    def test_homepage_progressive_enhancement_keeps_raw_results_on_json_failure(self) -> None:
        planned = build_site.build(current_results(), current_policy(), mode="staging")
        homepage = planned[REPO_ROOT / "index.html"]
        for number in ("6456", "1917", "4083"):
            self.assertIn(number, homepage)
        self.assertIn('fetch("results.json", { cache: "no-cache" })', homepage)
        self.assertIn("sameGeneratedSnapshot", homepage)
        show_error = homepage.split("function showError()", 1)[1].split("fetch(", 1)[0]
        self.assertIn("showing the last generated results", show_error)
        self.assertNotIn("innerHTML", show_error)

    def test_malay_page_uses_localized_dates_navigation_and_cautious_copy(self) -> None:
        planned = build_site.build(current_results(), current_policy(), mode="staging")
        malay = planned[REPO_ROOT / "ms" / "index.html"]
        self.assertIn("Keputusan 4D Terkini di Malaysia", malay)
        self.assertIn(build_site.malay_draw_date(current_results()["drawDate"], current_results()["drawDay"]), malay)
        self.assertIn(build_site.malay_updated(current_results()["updated"]), malay)
        self.assertIn('aria-label="Navigasi utama"', malay)
        self.assertIn('aria-label="Navigasi kaki halaman"', malay)
        self.assertIn("Jika anda mencari keputusan 4D hari ini", malay)
        self.assertIn("Hadiah saguhati", malay)
        self.assertIn("Sabah 88 4D", malay)
        self.assertNotIn("(Sun)", malay)

    def test_static_page_styles_provide_44px_link_targets(self) -> None:
        styles = (REPO_ROOT / "assets" / "site.css").read_text(encoding="utf-8")
        self.assertIn(".breadcrumbs a,.provider-title a,.content-card p>a", styles)
        self.assertIn("min-height:44px", styles)

    def test_archive_includes_only_providers_with_the_route_draw_date(self) -> None:
        results = current_results()
        results["providers"]["sabah88"]["drawDate"] = "22-08-2026"
        results["providers"]["sabah88"]["drawDay"] = "Sat"
        results["provenance"].pop("snapshotVerificationIds")
        planned = build_site.build(results, current_policy(), mode="staging")
        archive = planned[REPO_ROOT / "results" / "2026-08-23" / "index.html"]
        self.assertNotIn('data-provider="sabah88"', archive)
        self.assertIn('data-provider="magnum"', archive)

    def test_sitemap_uses_content_update_date_for_dynamic_pages(self) -> None:
        results = current_results()
        planned = build_site.build(results, current_policy(), mode="staging")
        sitemap = planned[REPO_ROOT / "sitemap.xml"]
        updated_date = pre.parse_updated(results["updated"]).strftime("%Y-%m-%d")
        self.assertIn(f"<loc>https://4dvip88.com/</loc>\n    <lastmod>{updated_date}</lastmod>", sitemap)
        self.assertIn(f"<loc>https://4dvip88.com/results/2026-08-23/</loc>\n    <lastmod>{updated_date}</lastmod>", sitemap)

    def test_policy_requires_current_cross_check_provenance(self) -> None:
        results = current_results()
        results["provenance"].pop("crossChecks")
        self.assertTrue(any("crossChecks" in blocker for blocker in pre.policy_blockers(current_policy(), results, mode="staging")))
        results = current_results()
        results["provenance"]["verifiedAt"] = "2099-01-01T00:00:00+08:00"
        self.assertTrue(any("future" in blocker for blocker in pre.policy_blockers(current_policy(), results, mode="staging")))

    def test_publication_build_fails_without_release_approval(self) -> None:
        policy = current_policy()
        policy["releaseApproval"] = {
            "status": "staging-only",
            "approvalId": None,
            "approvedAt": None,
            "evidence": None,
        }
        for source in policy["sources"]:
            source["publicationAllowed"] = False
        with self.assertRaisesRegex(pre.ValidationError, "PUBLICATION_BLOCKED"):
            build_site.build(current_results(), policy, mode="publication")

    def test_synthetic_preview_is_noindex_and_watermarked(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--mode",
                "synthetic",
                "--results",
                str(FIXTURE),
                "--output",
                str(SYNTHETIC_OUTPUT),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        preview = SYNTHETIC_OUTPUT.read_text(encoding="utf-8")
        self.assertIn(pre.SYNTHETIC_WATERMARK, preview)
        self.assertIn("noindex,nofollow,noarchive", preview)
        self.assertIn("TEST-1", preview)


class ScraperSafetyTests(unittest.TestCase):
    def test_timestamp_only_change_is_semantically_equal(self) -> None:
        original = current_results()
        changed = copy.deepcopy(original)
        changed["updated"] = "2099-01-01 00:00 MYT"
        changed["provenance"]["verifiedAt"] = "2099-01-01T00:00:00+08:00"
        self.assertEqual(scrape.semantic_view(original), scrape.semantic_view(changed))

    def test_removing_dated_manual_verifications_is_a_material_change(self) -> None:
        reviewed = current_results()
        next_scrape = copy.deepcopy(reviewed)
        next_scrape["provenance"].pop("snapshotVerificationIds")
        self.assertNotEqual(scrape.semantic_view(reviewed), scrape.semantic_view(next_scrape))

    def test_cross_source_mismatch_fails(self) -> None:
        results = current_results()
        moon = moon_from_results(results)
        moon["M"]["P1"] = "0000"
        with self.assertRaisesRegex(pre.ValidationError, "cross-source mismatch"):
            scrape.cross_check(results["providers"], moon)

    def test_cross_source_match_passes(self) -> None:
        results = current_results()
        scrape.cross_check(results["providers"], moon_from_results(results))

    def test_cross_source_draw_date_mismatch_fails(self) -> None:
        results = current_results()
        moon = moon_from_results(results)
        moon["M"]["DD"] = "(Sat) 22-Aug-2026"
        with self.assertRaisesRegex(pre.ValidationError, "draw date"):
            scrape.cross_check(results["providers"], moon)

    def test_cross_source_draw_number_mismatch_fails(self) -> None:
        results = current_results()
        moon = moon_from_results(results)
        moon["M"]["DN"] = "#999/26"
        with self.assertRaisesRegex(pre.ValidationError, "draw number"):
            scrape.cross_check(results["providers"], moon)

    def test_cross_source_toto_extended_mismatch_fails(self) -> None:
        results = current_results()
        moon = moon_from_results(results)
        moon["T"]["P5D1"] = "00000"
        with self.assertRaisesRegex(pre.ValidationError, "totoextra fiveD"):
            scrape.cross_check(results["providers"], moon)

    def test_atomic_json_write_leaves_valid_complete_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "results.json"
            scrape.atomic_json_write(target, {"complete": True, "value": "1234"})
            self.assertEqual({"complete": True, "value": "1234"}, json.loads(target.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
