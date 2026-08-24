from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock


TOOL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOL_DIR.parents[1]
SCRIPT = TOOL_DIR / "prerender_results.py"
FIXTURE = TOOL_DIR / "tests" / "fixtures" / "results.synthetic.json"
SYNTHETIC_OUTPUT = TOOL_DIR / "tests" / "generated" / "synthetic-results-preview.html"

sys.path.insert(0, str(TOOL_DIR))
import build_site  # noqa: E402
import package_candidate  # noqa: E402
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
    updated = pre.parse_updated(current_results()["updated"])
    reviewed = pre.parse_iso_datetime(current_policy()["accuracyReview"]["reviewedAt"])
    assert reviewed is not None
    return max(updated, reviewed.astimezone(pre.MYT)) + timedelta(minutes=2)


def policy_issues(policy: dict, results: dict, *, mode: str) -> list[str]:
    return pre.policy_blockers(policy, results, mode=mode, now=reviewed_now())


def build_plan(results: dict, policy: dict, *, mode: str) -> dict[Path, str]:
    return build_site.build(results, policy, mode=mode, now=reviewed_now())


def approved_policy(results: dict) -> dict:
    policy = current_policy()
    for source in policy["sources"]:
        source["publicationAllowed"] = True
    policy["releaseApproval"] = {
        "status": "approved",
        "approvalId": "OWNER-EXACT-SNAPSHOT-TEST",
        "approvedAt": (pre.parse_updated(results["updated"]) + timedelta(minutes=1)).isoformat(),
        "resultsSha256": pre.results_snapshot_digest(results),
        "evidence": "Synthetic unit-test approval for one exact snapshot.",
        "reason": "Exercise the positive publication-policy path in tests.",
    }
    return policy


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

    def test_recent_dates_must_start_with_global_draw_date(self) -> None:
        results = current_results()
        results["recentDates"] = results["recentDates"][1:]
        with self.assertRaisesRegex(pre.ValidationError, "does not match global drawDate"):
            pre.validate_results_shape(results, now=reviewed_now())


class PolicyAndRenderingTests(unittest.TestCase):
    def tearDown(self) -> None:
        SYNTHETIC_OUTPUT.unlink(missing_ok=True)

    def test_staging_passes_but_checked_in_policy_blocks_publication(self) -> None:
        policy = current_policy()
        results = current_results()
        self.assertEqual([], policy_issues(policy, results, mode="staging"))
        blockers = policy_issues(policy, results, mode="publication")
        self.assertTrue(any("not approved for live publication" in blocker for blocker in blockers))
        self.assertTrue(any("live release approval is not approved" in blocker for blocker in blockers))

    def test_publication_approval_is_bound_to_the_exact_snapshot(self) -> None:
        results = current_results()
        policy = approved_policy(results)
        self.assertEqual([], policy_issues(policy, results, mode="publication"))

        changed = copy.deepcopy(results)
        changed["recentDates"] = changed["recentDates"][:-1]
        blockers = policy_issues(policy, changed, mode="publication")
        self.assertTrue(any("resultsSha256 does not match" in blocker for blocker in blockers))

    def test_publication_digest_includes_both_snapshot_timestamps(self) -> None:
        results = current_results()
        policy = approved_policy(results)
        changed = copy.deepcopy(results)
        changed["updated"] = "2026-08-24 14:24 MYT"
        changed["provenance"]["verifiedAt"] = "2026-08-24T14:24:30+08:00"
        self.assertNotEqual(
            pre.results_snapshot_digest(results),
            pre.results_snapshot_digest(changed),
        )
        blockers = policy_issues(policy, changed, mode="publication")
        self.assertTrue(any("resultsSha256 does not match" in blocker for blocker in blockers))

    def test_release_approval_cannot_predate_the_result_snapshot(self) -> None:
        results = current_results()
        policy = approved_policy(results)
        policy["releaseApproval"]["approvedAt"] = (
            pre.parse_updated(results["updated"]) - timedelta(minutes=1)
        ).isoformat()
        blockers = policy_issues(policy, results, mode="publication")
        self.assertTrue(any("predates the result snapshot" in blocker for blocker in blockers))

    def test_snapshot_verification_ids_are_declared_and_unique(self) -> None:
        results = current_results()
        results["provenance"]["snapshotVerificationIds"].append("unknown-verification")
        blockers = policy_issues(current_policy(), results, mode="staging")
        self.assertTrue(any("unknown snapshot verification" in blocker for blocker in blockers))

        results = current_results()
        results["provenance"]["snapshotVerificationIds"].append(
            results["provenance"]["snapshotVerificationIds"][0]
        )
        blockers = policy_issues(current_policy(), results, mode="staging")
        self.assertTrue(any("contains duplicates" in blocker for blocker in blockers))

    def test_snapshot_verification_ids_and_policy_schema_are_restricted(self) -> None:
        policy = current_policy()
        policy["schemaVersion"] = 2
        policy["accuracyReview"]["snapshotVerifications"][""] = {}
        blockers = policy_issues(policy, current_results(), mode="staging")
        self.assertTrue(any("schemaVersion" in blocker for blocker in blockers))
        self.assertTrue(any("invalid snapshot verification ID" in blocker for blocker in blockers))

        results = current_results()
        results["provenance"]["snapshotVerificationIds"] = [""]
        blockers = policy_issues(current_policy(), results, mode="staging")
        self.assertTrue(any("not a valid ID list" in blocker for blocker in blockers))

    def test_snapshot_verification_digest_binds_exact_provider_object(self) -> None:
        results = current_results()
        results["providers"]["cashsweep"]["first"] = "0000"
        blockers = policy_issues(current_policy(), results, mode="staging")
        self.assertTrue(any("digest does not match cashsweep" in blocker for blocker in blockers))
        publication_blockers = policy_issues(current_policy(), results, mode="publication")
        self.assertTrue(any("cashsweep" in blocker and "lacks an independent" in blocker for blocker in publication_blockers))

    def test_snapshot_verification_binds_draw_date_and_number(self) -> None:
        policy = current_policy()
        verification = policy["accuracyReview"]["snapshotVerifications"][
            "draw-2026-08-23-provider-owned-2026-08-24"
        ]
        verification["providers"]["cashsweep"]["drawDate"] = "22-08-2026"
        verification["providers"]["sandakan"]["drawNo"] = "999-26"
        blockers = policy_issues(policy, current_results(), mode="staging")
        self.assertTrue(any("draw date does not match cashsweep" in blocker for blocker in blockers))
        self.assertTrue(any("draw number does not match sandakan" in blocker for blocker in blockers))

    def test_future_snapshot_verification_is_blocked(self) -> None:
        policy = current_policy()
        policy["accuracyReview"]["snapshotVerifications"][
            "draw-2026-08-23-provider-owned-2026-08-24"
        ]["checkedAt"] = "2099-01-01T00:00:00+08:00"
        blockers = policy_issues(policy, current_results(), mode="staging")
        self.assertTrue(any("checkedAt is in the future" in blocker for blocker in blockers))

    def test_malformed_evidence_fails_closed_without_exception(self) -> None:
        policy = current_policy()
        binding = policy["accuracyReview"]["snapshotVerifications"][
            "draw-2026-08-23-provider-owned-2026-08-24"
        ]["providers"]["cashsweep"]
        binding["evidenceSources"] = [["not", "an", "object"], {"url": ["not-hashable"]}]
        blockers = policy_issues(policy, current_results(), mode="publication")
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
        blockers = policy_issues(policy, current_results(), mode="publication")
        self.assertTrue(any("lacks required source roles" in blocker for blocker in blockers))
        self.assertTrue(any("lacks separate publishers" in blocker for blocker in blockers))
        self.assertTrue(any("cashsweep" in blocker and "lacks an independent" in blocker for blocker in blockers))

    def test_future_scrape_can_stage_without_reusing_manual_verification(self) -> None:
        results = current_results()
        results["provenance"].pop("snapshotVerificationIds")
        self.assertEqual([], policy_issues(current_policy(), results, mode="staging"))
        blockers = policy_issues(current_policy(), results, mode="publication")
        self.assertTrue(any("cashsweep" in blocker and "gd4d" in blocker for blocker in blockers))
        missing = next(
            blocker for blocker in blockers
            if blocker.startswith("live publication lacks an independent cross-check")
        )
        self.assertEqual(
            {"cashsweep", "gd4d", "sabah88", "sandakan", "singapore"},
            {value.strip() for value in missing.split(":", 1)[1].split(",")},
        )

    def test_raw_fragment_contains_priority_numbers_and_no_second_h1(self) -> None:
        fragment = pre.render_results_fragment(current_results())
        self.assertIn("6456", fragment)
        self.assertIn("1917", fragment)
        self.assertIn("4083", fragment)
        self.assertIn("<h2", fragment)
        self.assertNotIn("<h1", fragment)

    def test_build_plan_contains_required_pages_and_sitemap_urls(self) -> None:
        planned = build_plan(current_results(), current_policy(), mode="staging")
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
        planned = build_plan(current_results(), current_policy(), mode="staging")
        homepage = planned[REPO_ROOT / "index.html"]
        for number in ("6456", "1917", "4083"):
            self.assertIn(number, homepage)
        self.assertIn('fetch("results.json", { cache: "no-cache" })', homepage)
        self.assertIn("sameGeneratedSnapshot", homepage)
        show_error = homepage.split("function showError()", 1)[1].split("fetch(", 1)[0]
        self.assertIn("showing the last generated results", show_error)
        self.assertNotIn("innerHTML", show_error)

    def test_malay_page_uses_localized_dates_navigation_and_cautious_copy(self) -> None:
        planned = build_plan(current_results(), current_policy(), mode="staging")
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
        planned = build_plan(results, current_policy(), mode="staging")
        archive = planned[REPO_ROOT / "results" / "2026-08-23" / "index.html"]
        self.assertNotIn('data-provider="sabah88"', archive)
        self.assertIn('data-provider="magnum"', archive)

    def test_sitemap_uses_content_update_date_for_dynamic_pages(self) -> None:
        results = current_results()
        planned = build_plan(results, current_policy(), mode="staging")
        sitemap = planned[REPO_ROOT / "sitemap.xml"]
        updated_date = pre.parse_updated(results["updated"]).strftime("%Y-%m-%d")
        self.assertIn(f"<loc>https://4dvip88.com/</loc>\n    <lastmod>{updated_date}</lastmod>", sitemap)
        self.assertIn(f"<loc>https://4dvip88.com/results/2026-08-23/</loc>\n    <lastmod>{updated_date}</lastmod>", sitemap)

    def test_policy_requires_current_cross_check_provenance(self) -> None:
        results = current_results()
        results["provenance"].pop("crossChecks")
        self.assertTrue(any("crossChecks" in blocker for blocker in policy_issues(current_policy(), results, mode="staging")))
        results = current_results()
        results["provenance"]["verifiedAt"] = "2099-01-01T00:00:00+08:00"
        self.assertTrue(any("future" in blocker for blocker in policy_issues(current_policy(), results, mode="staging")))

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
            build_plan(current_results(), policy, mode="publication")

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

    def test_removing_dated_manual_verifications_is_not_a_factual_change(self) -> None:
        reviewed = current_results()
        next_scrape = copy.deepcopy(reviewed)
        next_scrape["provenance"].pop("snapshotVerificationIds")
        self.assertEqual(scrape.semantic_view(reviewed), scrape.semantic_view(next_scrape))
        self.assertEqual(pre.result_facts_digest(reviewed), pre.result_facts_digest(next_scrape))

    def test_new_candidate_provenance_never_carries_snapshot_verifications(self) -> None:
        provenance = scrape.candidate_provenance(
            reviewed_now(),
            {"4d4d-co": "primary", "4dmoon-feedwest": "cross-check"},
        )
        self.assertNotIn("snapshotVerificationIds", provenance)
        self.assertEqual(pre.EXPECTED_SOURCE_MAP, provenance["providerSources"])
        self.assertEqual(
            {"4d4d-co", "4dmoon-feedwest"},
            set(provenance["sourcePayloadSha256"]),
        )

    def test_recent_dates_include_newest_cross_feed_provider_date(self) -> None:
        values = ["23-08-2026 (Sun)", "22-08-2026 (Sat)"]
        self.assertEqual(
            ["24-08-2026 (Mon)", "23-08-2026 (Sun)", "22-08-2026 (Sat)"],
            scrape.recent_dates_with_latest(values, "24-08-2026", "Mon"),
        )

    def test_source_response_size_is_bounded(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.headers = {"Content-Length": str(scrape.MAX_SOURCE_BYTES + 1)}
        with mock.patch.object(scrape.urllib.request, "urlopen", return_value=response):
            with self.assertRaisesRegex(pre.ValidationError, "source response exceeds"):
                scrape.fetch("https://example.test/results")

        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.headers = {}
        response.read.return_value = b"x" * (scrape.MAX_SOURCE_BYTES + 1)
        with mock.patch.object(scrape.urllib.request, "urlopen", return_value=response):
            with self.assertRaisesRegex(pre.ValidationError, "source response exceeds"):
                scrape.fetch("https://example.test/results")

    def test_candidate_output_inside_repository_is_rejected(self) -> None:
        args = Namespace(
            baseline=REPO_ROOT / "results.json",
            output=REPO_ROOT / "candidate-results.json",
            status_output=REPO_ROOT / "candidate-status.json",
        )
        with self.assertRaisesRegex(pre.ValidationError, "outside the repository"):
            scrape.validate_candidate_paths(args)

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

    def test_candidate_cli_serializes_changed_status_without_touching_baseline(self) -> None:
        baseline_bytes = (REPO_ROOT / "results.json").read_bytes()
        candidate = current_results()
        candidate["providers"]["magnum"]["first"] = "0000"
        candidate["provenance"] = scrape.candidate_provenance(
            reviewed_now(),
            {"4d4d-co": "primary", "4dmoon-feedwest": "cross-check"},
        )
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            output = temporary_root / "results.json"
            status = temporary_root / "status.json"
            with mock.patch.object(scrape, "collect_candidate", return_value=candidate):
                return_code = scrape.run(
                    [
                        "--candidate",
                        "--baseline",
                        str(REPO_ROOT / "results.json"),
                        "--output",
                        str(output),
                        "--status-output",
                        str(status),
                    ]
                )
            self.assertEqual(0, return_code)
            serialized = json.loads(output.read_text(encoding="utf-8"))
            serialized_status = json.loads(status.read_text(encoding="utf-8"))
            self.assertEqual("0000", serialized["providers"]["magnum"]["first"])
            self.assertNotIn("snapshotVerificationIds", serialized["provenance"])
            self.assertTrue(serialized_status["changed"])
            self.assertEqual("candidate-ready", serialized_status["state"])
        self.assertEqual(baseline_bytes, (REPO_ROOT / "results.json").read_bytes())


class CandidateArtifactTests(unittest.TestCase):
    def changed_candidate(self) -> dict:
        candidate = current_results()
        for provider in candidate["providers"].values():
            provider["drawDate"] = "24-08-2026"
            provider["drawDay"] = "Mon"
        candidate["drawDate"] = "24-08-2026"
        candidate["drawDay"] = "Mon"
        candidate["recentDates"] = ["24-08-2026 (Mon)", *candidate["recentDates"]]
        candidate["updated"] = "2026-08-24 15:00 MYT"
        candidate["provenance"] = scrape.candidate_provenance(
            datetime(2026, 8, 24, 15, 0, tzinfo=pre.MYT),
            {"4d4d-co": "primary", "4dmoon-feedwest": "cross-check"},
        )
        return candidate

    def test_changed_candidate_packages_exact_bounded_review_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            candidate_path = temporary_root / "candidate.json"
            artifact_root = temporary_root / "artifact"
            scrape.atomic_json_write(candidate_path, self.changed_candidate())
            summary = package_candidate.package_candidate(
                candidate_path=candidate_path,
                baseline_path=REPO_ROOT / "results.json",
                policy_path=TOOL_DIR / "provenance-policy.json",
                output_root=artifact_root,
                base_commit="6ae25b05eef6efdeedc353fa81e823835a2b31a9",
                now=reviewed_now(),
            )
            files = {
                path.relative_to(artifact_root).as_posix()
                for path in artifact_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(20, summary["fileCount"])
            self.assertEqual(20, len(files))
            self.assertEqual(package_candidate.METADATA_PATHS, files - {name for name in files if name.startswith("preview/")})
            self.assertEqual(14, len([name for name in files if name.startswith("preview/")]))
            self.assertIn("preview/index.html", files)
            self.assertIn("preview/sitemap.xml", files)
            self.assertIn("preview/results/2026-08-24/index.html", files)
            self.assertIn("publicationApproved=false", (artifact_root / "READY").read_text(encoding="utf-8"))
            blockers = json.loads((artifact_root / "publication-blockers.json").read_text(encoding="utf-8"))
            self.assertEqual("blocked", blockers["status"])
            self.assertTrue(any("live release approval" in value for value in blockers["blockers"]))
            patch = (artifact_root / "changes.patch").read_text(encoding="utf-8")
            self.assertIn("--- a/results.json", patch)
            self.assertIn("+++ b/results.json", patch)

    def test_unchanged_candidate_is_not_packaged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            candidate_path = temporary_root / "candidate.json"
            candidate = current_results()
            candidate["updated"] = "2026-08-24 15:00 MYT"
            candidate["provenance"] = scrape.candidate_provenance(
                datetime(2026, 8, 24, 15, 0, tzinfo=pre.MYT),
                {"4d4d-co": "primary", "4dmoon-feedwest": "cross-check"},
            )
            scrape.atomic_json_write(candidate_path, candidate)
            with self.assertRaisesRegex(pre.ValidationError, "no factual result change"):
                package_candidate.package_candidate(
                    candidate_path=candidate_path,
                    baseline_path=REPO_ROOT / "results.json",
                    policy_path=TOOL_DIR / "provenance-policy.json",
                    output_root=temporary_root / "artifact",
                    base_commit="6ae25b05eef6efdeedc353fa81e823835a2b31a9",
                    now=reviewed_now(),
                )

    def test_candidate_with_old_snapshot_verifications_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            candidate = self.changed_candidate()
            candidate["provenance"]["snapshotVerificationIds"] = [
                "draw-2026-08-23-provider-owned-2026-08-24"
            ]
            candidate_path = temporary_root / "candidate.json"
            scrape.atomic_json_write(candidate_path, candidate)
            with self.assertRaisesRegex(pre.ValidationError, "snapshot-specific verification IDs"):
                package_candidate.package_candidate(
                    candidate_path=candidate_path,
                    baseline_path=REPO_ROOT / "results.json",
                    policy_path=TOOL_DIR / "provenance-policy.json",
                    output_root=temporary_root / "artifact",
                    base_commit="6ae25b05eef6efdeedc353fa81e823835a2b31a9",
                    now=reviewed_now(),
                )

    def test_candidate_cannot_regress_global_or_provider_draw_dates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            candidate = self.changed_candidate()
            for provider in candidate["providers"].values():
                provider["drawDate"] = "22-08-2026"
                provider["drawDay"] = "Sat"
            candidate["drawDate"] = "22-08-2026"
            candidate["drawDay"] = "Sat"
            candidate["recentDates"] = [
                "22-08-2026 (Sat)",
                "19-08-2026 (Wed)",
                "16-08-2026 (Sun)",
                "15-08-2026 (Sat)",
                "12-08-2026 (Wed)",
            ]
            candidate_path = temporary_root / "candidate.json"
            scrape.atomic_json_write(candidate_path, candidate)
            with self.assertRaisesRegex(pre.ValidationError, "global draw date regresses"):
                package_candidate.package_candidate(
                    candidate_path=candidate_path,
                    baseline_path=REPO_ROOT / "results.json",
                    policy_path=TOOL_DIR / "provenance-policy.json",
                    output_root=temporary_root / "artifact",
                    base_commit="6ae25b05eef6efdeedc353fa81e823835a2b31a9",
                    now=reviewed_now(),
                )

    def test_oversized_candidate_is_rejected_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            candidate_path = temporary_root / "candidate.json"
            candidate_path.write_bytes(b"x" * (package_candidate.MAX_FILE_BYTES + 1))
            with self.assertRaisesRegex(pre.ValidationError, "too large"):
                package_candidate.package_candidate(
                    candidate_path=candidate_path,
                    baseline_path=REPO_ROOT / "results.json",
                    policy_path=TOOL_DIR / "provenance-policy.json",
                    output_root=temporary_root / "artifact",
                    base_commit="6ae25b05eef6efdeedc353fa81e823835a2b31a9",
                    now=reviewed_now(),
                )

    def test_failed_final_validation_leaves_no_ready_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            candidate_path = temporary_root / "candidate.json"
            artifact_root = temporary_root / "artifact"
            scrape.atomic_json_write(candidate_path, self.changed_candidate())
            with mock.patch.object(
                package_candidate,
                "validate_artifact",
                side_effect=pre.ValidationError("forced final validation failure"),
            ):
                with self.assertRaisesRegex(pre.ValidationError, "forced final validation failure"):
                    package_candidate.package_candidate(
                        candidate_path=candidate_path,
                        baseline_path=REPO_ROOT / "results.json",
                        policy_path=TOOL_DIR / "provenance-policy.json",
                        output_root=artifact_root,
                        base_commit="6ae25b05eef6efdeedc353fa81e823835a2b31a9",
                        now=reviewed_now(),
                    )
            self.assertFalse(artifact_root.exists())
            self.assertFalse(any(temporary_root.glob("artifact.*.tmp")))

    def test_artifact_checksum_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            candidate_path = temporary_root / "candidate.json"
            artifact_root = temporary_root / "artifact"
            scrape.atomic_json_write(candidate_path, self.changed_candidate())
            package_candidate.package_candidate(
                candidate_path=candidate_path,
                baseline_path=REPO_ROOT / "results.json",
                policy_path=TOOL_DIR / "provenance-policy.json",
                output_root=artifact_root,
                base_commit="6ae25b05eef6efdeedc353fa81e823835a2b31a9",
                now=reviewed_now(),
            )
            (artifact_root / "manifest.json").write_text("tampered\n", encoding="utf-8")
            expected = {
                path.relative_to(artifact_root).as_posix()
                for path in artifact_root.rglob("*")
                if path.is_file()
            }
            with self.assertRaisesRegex(pre.ValidationError, "checksum mismatch"):
                package_candidate.validate_artifact(artifact_root, expected)

    def test_artifact_extra_file_and_size_limits_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact_root = Path(temporary)
            (artifact_root / "payload").write_bytes(b"12345")
            (artifact_root / "checksums.sha256").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(pre.ValidationError, "allowlist mismatch"):
                package_candidate.validate_artifact(artifact_root, {"checksums.sha256"})
            with mock.patch.object(package_candidate, "MAX_FILE_BYTES", 4):
                with self.assertRaisesRegex(pre.ValidationError, "exceeds 4 bytes"):
                    package_candidate.validate_artifact(
                        artifact_root,
                        {"payload", "checksums.sha256"},
                    )
            with mock.patch.object(package_candidate, "MAX_FILE_BYTES", 1024), mock.patch.object(
                package_candidate, "MAX_TOTAL_BYTES", 4
            ):
                with self.assertRaisesRegex(pre.ValidationError, "exceeds 4 total bytes"):
                    package_candidate.validate_artifact(
                        artifact_root,
                        {"payload", "checksums.sha256"},
                    )


class WorkflowSafetyTests(unittest.TestCase):
    def test_scheduled_workflow_is_staging_only_and_read_only(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "update-results.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("${RUNNER_TEMP}", workflow)
        self.assertIn("retention-days: 7", workflow)
        self.assertIn('cron: "5 16 * * *"', workflow)
        self.assertIn('[ "${SCHEDULE_EXPRESSION}" = "0 1 * * *" ]', workflow)
        self.assertIn("git diff --exit-code", workflow)
        self.assertIn('test "$(git rev-parse HEAD)" = "${GITHUB_SHA}"', workflow)
        self.assertRegex(workflow, r"actions/checkout@[0-9a-f]{40}")
        self.assertRegex(workflow, r"actions/setup-python@[0-9a-f]{40}")
        self.assertRegex(workflow, r"actions/upload-artifact@[0-9a-f]{40}")
        for forbidden in (
            "contents: write",
            "git add",
            "git commit",
            "git push",
            "git reset",
            "git restore",
            "git switch",
            "git tag",
            "--mode publication",
            "secrets.",
            "actions: write",
            "pages: write",
            "id-token: write",
            "deploy-pages",
            "upload-pages-artifact",
            "gh api",
        ):
            self.assertNotIn(forbidden, workflow)


if __name__ == "__main__":
    unittest.main()
