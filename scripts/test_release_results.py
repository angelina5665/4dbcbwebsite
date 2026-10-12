import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
from datetime import datetime

from results_http import fresh_request

spec = importlib.util.spec_from_file_location("release_results", Path(__file__).with_name("release_results.py"))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class FreshRequestsTests(unittest.TestCase):
    def test_public_get_is_unique_and_keeps_existing_query(self):
        first = fresh_request("https://4dgm.com/?view=home#card", "test")
        second = fresh_request("https://4dgm.com/?view=home#card", "test")
        self.assertNotEqual(first.full_url, second.full_url)
        self.assertIn("view=home&", first.full_url)
        self.assertTrue(first.full_url.endswith("#card"))
        self.assertEqual("no-cache, no-store, max-age=0", first.get_header("Cache-control"))

    def test_existing_nonce_is_replaced_not_accumulated(self):
        request = fresh_request("https://my4d.co/results.json?_my4d_check=old&health=1", "test")
        self.assertEqual(1, request.full_url.count("_my4d_check="))
        self.assertNotIn("=old", request.full_url)
        self.assertIn("health=1", request.full_url)


class ReleaseTests(unittest.TestCase):
    def test_live_verification_waits_for_json_and_raw_cards(self):
        import json
        snapshot = {"updated": "2026-10-11 19:15 MYT", "drawDate": "11-10-2026"}
        html = 'data-results-updated="' + snapshot["updated"] + '"' + ''.join('id="card-' + key + '"' for key in release.REQUIRED)
        with mock.patch.object(release, "read_public", side_effect=[json.dumps(snapshot), "old homepage", json.dumps(snapshot), html]), mock.patch.object(release.time, "sleep") as sleep:
            release.verify_live(snapshot)
            sleep.assert_called_once_with(15)

    def test_failed_live_verification_never_claims_success(self):
        with mock.patch.object(release, "read_public", side_effect=OSError("offline")), mock.patch.object(release.time, "monotonic", side_effect=[0, 241]):
            with self.assertRaisesRegex(RuntimeError, "deployment was not verified"):
                release.verify_live({})

    def test_real_complete_snapshot_passes(self):
        import json
        data = json.loads((release.ROOT / "results.json").read_text(encoding="utf-8"))
        release.require_complete(data, data)

    def test_missing_prizes_fail_before_publication(self):
        import copy
        import json
        baseline = json.loads((release.ROOT / "results.json").read_text(encoding="utf-8"))
        for key, field in [("magnum", "first"), ("nine", "consolation"), ("totoextra", "sixD")]:
            data = copy.deepcopy(baseline)
            data["providers"][key][field] = [] if isinstance(baseline["providers"][key][field], list) else "----"
            with self.subTest(key=key, field=field), self.assertRaisesRegex(RuntimeError, "Incomplete"):
                release.require_complete(data, baseline)

    def test_partial_lotto_balls_fail_before_publication(self):
        import copy
        import json
        baseline = json.loads((release.ROOT / "results.json").read_text(encoding="utf-8"))
        data = copy.deepcopy(baseline)
        data["providers"]["totoextra"]["lotto"][0]["balls"] = ["1", "2"]
        with self.assertRaisesRegex(RuntimeError, "Incomplete Toto"):
            release.require_complete(data, baseline)

    def test_daily_window_includes_special_days_and_is_bounded(self):
        for hour, minute, expected in [(18, 44, False), (18, 45, True), (19, 30, True), (22, 59, True), (23, 0, False)]:
            self.assertEqual(expected, release.in_window(datetime(2026, 10, 27, hour, minute, tzinfo=release.MYT)))

    def test_dirty_checkout_blocks_recovery(self):
        with mock.patch.object(release, "git", return_value=" M unrelated.txt"):
            with self.assertRaisesRegex(RuntimeError, "Dirty checkout"):
                release.assert_clean()

    def test_publish_rejects_unrelated_files_without_staging(self):
        with mock.patch.object(release, "git", side_effect=["index.html\nunrelated.txt", "", ""]) as git:
            with self.assertRaisesRegex(RuntimeError, "Unexpected files"):
                release.publish()
            self.assertEqual(3, git.call_count)

    def test_current_global_date_is_not_enough_when_nine_lags(self):
        import json
        now = datetime(2026, 10, 11, 19, 30, tzinfo=release.MYT)
        data = {"drawDate": "11-10-2026", "providers": {key: {"drawDate": "11-10-2026"} for key in release.REQUIRED}}
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(release, "ROOT", Path(directory)):
            path = Path(directory) / "results.json"
            path.write_text(json.dumps(data))
            self.assertTrue(release.all_current(now))
            data["providers"]["nine"]["drawDate"] = "10-10-2026"
            path.write_text(json.dumps(data))
            self.assertFalse(release.all_current(now))

    def test_no_change_does_not_test_or_publish(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(release, "ROOT", Path(directory)):
            (Path(directory) / "results.json").write_text("original")
            with mock.patch.object(release, "assert_clean"), mock.patch.object(release, "backup"), mock.patch.object(release, "run"), mock.patch.object(release, "validate") as validate, mock.patch.object(release, "publish") as publish:
                self.assertFalse(release.cycle(False))
                validate.assert_not_called()
                publish.assert_not_called()

    def test_validation_failure_restores_last_verified_result_and_never_pushes(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(release, "ROOT", Path(directory)):
            root = Path(directory)
            saved = root / "backup"
            saved.mkdir()
            (saved / "results.json").write_text("verified")
            (root / "results.json").write_text("verified")
            def scrape(*args):
                (root / "results.json").write_text("candidate")
            with mock.patch.object(release, "assert_clean"), mock.patch.object(release, "git"), mock.patch.object(release, "backup", return_value=saved), mock.patch.object(release, "run", side_effect=scrape), mock.patch.object(release, "validate", side_effect=RuntimeError("failed tests")), mock.patch.object(release, "publish") as publish:
                with self.assertRaisesRegex(RuntimeError, "failed tests"):
                    release.cycle(True)
                self.assertEqual("verified", (root / "results.json").read_text())
                publish.assert_not_called()

    def test_changed_results_validate_before_publish(self):
        order = []
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(release, "ROOT", Path(directory)):
            root = Path(directory)
            (root / "results.json").write_text("verified")
            def scrape(*args):
                order.append("scrape")
                (root / "results.json").write_text("candidate")
            with mock.patch.object(release, "assert_clean"), mock.patch.object(release, "git"), mock.patch.object(release, "backup"), mock.patch.object(release, "run", side_effect=scrape), mock.patch.object(release, "validate", side_effect=lambda: order.append("validate")), mock.patch.object(release, "publish", side_effect=lambda: order.append("publish")):
                self.assertTrue(release.cycle(True))
                self.assertEqual(["scrape", "validate", "publish"], order)

    def test_outside_window_does_not_sleep(self):
        with mock.patch.object(release.sys, "argv", ["release_results.py", "--publish"]), mock.patch.dict(release.os.environ, {"GITHUB_ACTIONS": "true"}), mock.patch.object(release, "cycle") as cycle, mock.patch.object(release, "now_myt", return_value=datetime(2026, 10, 11, 9, 0, tzinfo=release.MYT)), mock.patch.object(release.time, "sleep") as sleep:
            self.assertEqual(0, release.main())
            cycle.assert_called_once_with(True)
            sleep.assert_not_called()

    def test_polls_when_nine_lags_then_stops_when_current(self):
        with mock.patch.object(release.sys, "argv", ["release_results.py", "--publish"]), mock.patch.dict(release.os.environ, {"GITHUB_ACTIONS": "true"}), mock.patch.object(release, "cycle") as cycle, mock.patch.object(release, "now_myt", return_value=datetime(2026, 10, 11, 19, 0, tzinfo=release.MYT)), mock.patch.object(release, "all_current", side_effect=[False, True]), mock.patch.object(release.time, "sleep") as sleep:
            release.main()
            self.assertEqual(2, cycle.call_count)
            sleep.assert_called_once_with(60)

    def test_poll_loop_respects_twenty_minute_cap(self):
        with mock.patch.object(release.sys, "argv", ["release_results.py", "--publish"]), mock.patch.dict(release.os.environ, {"GITHUB_ACTIONS": "true"}), mock.patch.object(release, "cycle") as cycle, mock.patch.object(release, "now_myt", return_value=datetime(2026, 10, 11, 19, 0, tzinfo=release.MYT)), mock.patch.object(release, "all_current", return_value=False), mock.patch.object(release.time, "monotonic", side_effect=[0, 1201]), mock.patch.object(release.time, "sleep") as sleep:
            release.main()
            cycle.assert_called_once()
            sleep.assert_not_called()


class GitPortabilityTests(unittest.TestCase):
    # Regression: 11 Oct 2026 the robot failed every run with "Unsupported SSL backend 'openssl'"
    # because the Windows-only http.sslBackend switch was passed to Linux git.
    def test_linux_git_gets_no_windows_ssl_switch(self):
        with mock.patch.object(release.os, "name", "posix"), mock.patch.object(release, "run") as run:
            release.git("fetch", "origin", "main")
        self.assertEqual(("git", "fetch", "origin", "main"), run.call_args.args)
