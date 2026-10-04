import copy
import unittest
from unittest import mock

import scrape


def provider(name, draw_date, draw_day, first="0038"):
    return {
        "name": name,
        "drawDate": draw_date,
        "drawDay": draw_day,
        "first": first,
        "second": "1234",
        "third": "5678",
    }


class ScrapeSnapshotTests(unittest.TestCase):
    def snapshot(self):
        return {
            "drawDate": "26-08-2026",
            "drawDay": "Wed",
            "recentDates": [
                "26-08-2026 (Wed)",
                "23-08-2026 (Sun)",
                "22-08-2026 (Sat)",
                "19-08-2026 (Wed)",
                "16-08-2026 (Sun)",
                "15-08-2026 (Sat)",
            ],
            "providers": {
                "cashsweep": provider("Cashweep 4D", "26-08-2026", "Wed"),
                "gd4d": provider("Grand Dragon 4D", "27-08-2026", "Thu", first="0838"),
            },
        }

    def test_upstream_cash_sweep_aliases_normalize_to_canonical_name(self):
        for alias in (
            "Cashweep 4D",
            "Cashsweep 4D",
            "Cash Sweep 4D",
            "Special Cash Sweep 4D",
        ):
            with self.subTest(alias=alias):
                key, card = scrape.parse_card(
                    '<table><tr><td class="resultprizelable">%s</td></tr></table>' % alias
                )
                self.assertEqual("cashsweep", key)
                self.assertEqual("Special Cash Sweep 4D", card["name"])

    def test_latest_provider_sets_global_date_and_recent_dates(self):
        snapshot = self.snapshot()
        scrape.finalize_snapshot(snapshot)

        self.assertEqual("27-08-2026", snapshot["drawDate"])
        self.assertEqual("Thu", snapshot["drawDay"])
        self.assertEqual("27-08-2026 (Thu)", snapshot["recentDates"][0])
        self.assertEqual(6, len(snapshot["recentDates"]))
        self.assertEqual(len(snapshot["recentDates"]), len(set(snapshot["recentDates"])))
        self.assertEqual("Special Cash Sweep 4D", snapshot["providers"]["cashsweep"]["name"])
        self.assertEqual("0038", snapshot["providers"]["cashsweep"]["first"])
        self.assertEqual("0838", snapshot["providers"]["gd4d"]["first"])

    def test_missing_optional_newer_provider_keeps_primary_date(self):
        snapshot = self.snapshot()
        del snapshot["providers"]["gd4d"]
        scrape.finalize_snapshot(snapshot)

        self.assertEqual("26-08-2026", snapshot["drawDate"])
        self.assertEqual("Wed", snapshot["drawDay"])
        self.assertEqual("26-08-2026 (Wed)", snapshot["recentDates"][0])

    def test_equal_latest_dates_are_deterministic(self):
        snapshot = self.snapshot()
        snapshot["providers"]["gd4d"]["drawDate"] = "26-08-2026"
        snapshot["providers"]["gd4d"]["drawDay"] = "Wed"
        first = scrape.finalize_snapshot(copy.deepcopy(snapshot))
        second = scrape.finalize_snapshot(copy.deepcopy(snapshot))
        self.assertEqual(first, second)

    def test_invalid_provider_date_fails_closed(self):
        snapshot = self.snapshot()
        snapshot["providers"]["gd4d"]["drawDate"] = "31-02-2026"
        with self.assertRaisesRegex(ValueError, "invalid draw date"):
            scrape.finalize_snapshot(snapshot)

    def test_incorrect_provider_weekday_fails_closed(self):
        snapshot = self.snapshot()
        snapshot["providers"]["gd4d"]["drawDay"] = "Fri"
        with self.assertRaisesRegex(ValueError, "does not match"):
            scrape.finalize_snapshot(snapshot)

    def test_recent_date_newer_than_provider_data_fails_closed(self):
        snapshot = self.snapshot()
        snapshot["recentDates"].insert(0, "28-08-2026 (Fri)")
        with self.assertRaisesRegex(ValueError, "newer than the latest provider date"):
            scrape.finalize_snapshot(snapshot)

    def test_timestamp_only_change_is_not_a_result_change(self):
        baseline = self.snapshot()
        baseline["updated"] = "2026-08-26 19:15 MYT"
        candidate = copy.deepcopy(baseline)
        candidate["updated"] = "2026-08-26 19:20 MYT"
        self.assertFalse(scrape.snapshot_changed(candidate, baseline))

    def test_new_prize_is_a_result_change(self):
        baseline = self.snapshot()
        candidate = copy.deepcopy(baseline)
        candidate["providers"]["cashsweep"]["first"] = "9999"
        self.assertTrue(scrape.snapshot_changed(candidate, baseline))

    def test_missing_existing_provider_is_rejected(self):
        baseline = self.snapshot()
        candidate = copy.deepcopy(baseline)
        del candidate["providers"]["cashsweep"]
        with self.assertRaisesRegex(ValueError, "omits existing providers: cashsweep"):
            scrape.validate_against_baseline(candidate, baseline)

    def test_provider_date_regression_is_rejected(self):
        baseline = self.snapshot()
        candidate = copy.deepcopy(baseline)
        candidate["providers"]["gd4d"]["drawDate"] = "20-08-2026"
        candidate["providers"]["gd4d"]["drawDay"] = "Thu"
        with self.assertRaisesRegex(ValueError, "regresses"):
            scrape.validate_against_baseline(candidate, baseline)


class LottoInProgressTests(unittest.TestCase):
    def toto(self, balls, draw_date="30-09-2026", draw_day="Wed"):
        return {
            "name": "SportsToto 5D, 6D, Lotto",
            "drawDate": draw_date,
            "drawDay": draw_day,
            "lotto": [
                {"title": "Star Toto 6/50", "balls": ["1", "2", "3", "4", "5", "6"]},
                {"title": "Power Toto 6/55", "balls": balls},
                {"title": "Supreme Toto 6/58", "balls": ["7", "8", "9", "10", "11", "12"]},
            ],
        }

    def test_half_drawn_lotto_keeps_previous_complete_card(self):
        previous = self.toto(["1", "27", "30", "37", "47", "52"])
        live = self.toto(["3", "14", "", "", "", ""], "03-10-2026", "Sat")
        previous_toto = {"name": "Toto 4D", "drawDate": "30-09-2026", "drawDay": "Wed", "first": "7161"}
        live_toto = {"name": "Toto 4D", "drawDate": "03-10-2026", "drawDay": "Sat", "first": "9728"}
        data = {"providers": {"totoextra": live, "toto": live_toto}}
        baseline = {"providers": {"totoextra": previous, "toto": previous_toto}}
        self.assertTrue(scrape.keep_complete_lotto(data, baseline))
        self.assertIs(data["providers"]["totoextra"], previous)
        self.assertIs(data["providers"]["toto"], previous_toto)

    def test_complete_lotto_is_published(self):
        previous = self.toto(["1", "27", "30", "37", "47", "52"])
        fresh = self.toto(["3", "14", "22", "31", "40", "55"], "03-10-2026", "Sat")
        data = {"providers": {"totoextra": fresh}}
        self.assertFalse(scrape.keep_complete_lotto(data, {"providers": {"totoextra": previous}}))
        self.assertIs(data["providers"]["totoextra"], fresh)

    def test_no_baseline_leaves_data_alone(self):
        live = self.toto(["3", "", "", "", "", ""])
        data = {"providers": {"totoextra": live}}
        self.assertFalse(scrape.keep_complete_lotto(data, None))


class NineLottoApiTests(unittest.TestCase):
    def api_result(self):
        return {
            "status": {"success": True},
            "draw_results": [{
                "type": "N",
                "label": "Nine Lotto",
                "4d": {
                    "first": "4807",
                    "second": "7563",
                    "third": "7125",
                    "special": ["2878", "6208", "9649", "3276", "5421", "9765", "9096", "1516", "3802", "1993"],
                    "consolation": ["8923", "1258", "5193", "0270", "6381", "6707", "8369", "2245", "2512", "1759"],
                },
            }],
        }

    def public_result(self):
        card = scrape._huawei_nine_lotto_card(self.api_result(), "2026-10-03")
        card["drawNo"] = "1508/2026"
        return card

    def test_huawei_result_maps_to_existing_card_shape(self):
        card = scrape._huawei_nine_lotto_card(self.api_result(), "2026-10-03")
        self.assertEqual("03-10-2026", card["drawDate"])
        self.assertEqual("Sat", card["drawDay"])
        self.assertEqual("4807", card["first"])
        self.assertEqual(10, len(card["special"]))
        self.assertEqual(10, len(card["consolation"]))

    def test_huawei_and_public_match_is_accepted_without_exposing_credentials(self):
        with mock.patch.dict("os.environ", {"HUAWEI_RESULTS_MID": "test-manager", "HUAWEI_RESULTS_PW": "hidden"}), \
             mock.patch.object(scrape, "fetch_huawei_nine_lotto", return_value=self.public_result()) as official, \
             mock.patch.object(scrape, "_public_nine_lotto", return_value=self.public_result()):
            card = scrape.fetch_nine_lotto()
        official.assert_called_once_with("test-manager", "hidden")
        self.assertEqual("1508/2026", card["drawNo"])

    def test_disagreement_fails_closed(self):
        official = self.public_result()
        official["first"] = "0000"
        with mock.patch.dict("os.environ", {"HUAWEI_RESULTS_MID": "test-manager", "HUAWEI_RESULTS_PW": "hidden"}), \
             mock.patch.object(scrape, "fetch_huawei_nine_lotto", return_value=official), \
             mock.patch.object(scrape, "_public_nine_lotto", return_value=self.public_result()):
            with self.assertRaisesRegex(ValueError, "disagree on first"):
                scrape.fetch_nine_lotto()


if __name__ == "__main__":
    unittest.main()
