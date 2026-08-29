import copy
import unittest

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


if __name__ == "__main__":
    unittest.main()
