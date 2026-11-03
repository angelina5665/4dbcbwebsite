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


class GrandDragonDrawNumberTests(unittest.TestCase):
    def card(self):
        return {
            "drawDate": "05-10-2026",
            "first": "5726",
            "second": "5746",
            "third": "4080",
        }

    def archive_row(self, draw_no="3582/2026", first="5726"):
        return '''
        <table><tbody><tr>
          <td><time datetime="2026-10-05">5 Oct 2026</time></td>
          <td>%s</td>
          <td class="recent-number">%s</td>
          <td class="recent-number">5746</td>
          <td class="recent-number">4080</td>
          <td>Published</td>
        </tr></tbody></table>
        ''' % (draw_no, first)

    def test_draw_number_requires_matching_date_and_top_prizes(self):
        self.assertEqual("3582/2026", scrape._grand_dragon_draw_no(self.archive_row(), self.card()))

    def test_disagreement_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "disagrees on top prizes"):
            scrape._grand_dragon_draw_no(self.archive_row(first="0000"), self.card())

    def test_invalid_draw_number_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "invalid draw number"):
            scrape._grand_dragon_draw_no(self.archive_row(draw_no="unknown"), self.card())

    def test_missing_matching_date_returns_none(self):
        html = self.archive_row().replace("2026-10-05", "2026-10-04")
        self.assertIsNone(scrape._grand_dragon_draw_no(html, self.card()))

    def test_accessible_archive_format_is_supported(self):
        html = '''<table><tr>
          <th><time datetime="2026-10-05">05-10-2026</time></th>
          <td><a class="ssr-w1">5726</a></td>
          <td><a class="ssr-w1">5746</a></td>
          <td><a class="ssr-w1">4080</a></td>
          <td class="ssr-dn">#261005</td><td>—</td>
        </tr></table>'''
        self.assertEqual("#261005", scrape._grand_dragon_draw_no(html, self.card()))


class DaMaCai13DBonusTests(unittest.TestCase):
    def card(self):
        return {
            "drawDate": "01-11-2026", "drawDay": "Sun", "drawNo": "6154-26",
            "first": "464 863", "second": "740 700", "third": "925 201",
            "special": ["233 624", "014 209", "457 907", "153 821", "658 827",
                        "355 526", "550 283", "866 100", "862 680", "130 155"],
            "consolation": ["658 120", "004 549", "042 482", "614 869", "653 951",
                            "498 779", "816 948", "383 657", "760 776", "382 185"],
            "d3rows": [
                {"value": "464 863", "zodiac": "ROOSTER", "bonus": ""},
                {"value": "740 700", "zodiac": "MONKEY", "bonus": ""},
                {"value": "925 201", "zodiac": "DOG", "bonus": ""},
            ],
        }

    def moon(self):
        values = {
            "DD": "(Sun) 01-Nov-2026", "DN": "#6154/26",
            "P1": "464863", "P2": "740700", "P3": "925201",
            "PB1": "ROOSTER", "PB2": "MONKEY", "PB3": "DOG",
            "JP1": "RM 848,333.30", "JP2": "RM 1,241,762.10", "JP3": "RM 2,163,339",
        }
        for index, value in enumerate(("233624", "014209", "457907", "153821", "658827",
                                       "355526", "550283", "866100", "862680", "130155"), 1):
            values["S%d" % index] = value
        for index, value in enumerate(("658120", "004549", "042482", "614869", "653951",
                                       "498779", "816948", "383657", "760776", "382185"), 1):
            values["C%d" % index] = value
        return {"D6": values}

    def test_missing_primary_bonus_is_filled_after_full_agreement(self):
        card = self.card()
        scrape.enrich_damacai13d_from_moon(card, self.moon())
        self.assertEqual(
            ["RM 848,333.30", "RM 1,241,762.10", "RM 2,163,339.00"],
            [row["bonus"] for row in card["d3rows"]],
        )

    def test_shared_result_disagreement_fails_closed(self):
        moon = self.moon()
        moon["D6"]["P1"] = "000000"
        with self.assertRaisesRegex(ValueError, "disagrees on first"):
            scrape.enrich_damacai13d_from_moon(self.card(), moon)

    def test_invalid_bonus_amount_fails_closed(self):
        moon = self.moon()
        moon["D6"]["JP2"] = "pending"
        with self.assertRaisesRegex(ValueError, "invalid amount"):
            scrape.enrich_damacai13d_from_moon(self.card(), moon)

    def test_bad_secondary_feed_holds_only_the_damacai_pair(self):
        data = {"providers": {
            "damacai": {"drawDate": "04-11-2026", "first": "9999"},
            "damacai13d": self.card(),
            "magnum": {"drawDate": "04-11-2026", "first": "1234"},
        }}
        previous = {"providers": {
            "damacai": {"drawDate": "01-11-2026", "first": "4863"},
            "damacai13d": self.card(),
        }}
        bad = self.moon()
        bad["D6"]["P1"] = "000000"
        self.assertTrue(scrape.enrich_or_hold_damacai_pair(data, previous, bad))
        self.assertEqual("4863", data["providers"]["damacai"]["first"])
        self.assertEqual("1234", data["providers"]["magnum"]["first"])


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

    def test_three_source_consensus_overrides_one_stale_board(self):
        stale = self.public_result()
        current = copy.deepcopy(stale)
        current.update({"drawDate": "03-11-2026", "drawDay": "Tue", "drawNo": "1539/2026", "first": "8079"})
        parsed = {"4dgm": stale, "lotto09": current, "lotto4dlive": current, "starbucks4d": current}
        with mock.patch.object(scrape, "fetch", side_effect=lambda url: url), \
             mock.patch.object(scrape, "_nine_lotto_card", side_effect=lambda html, source: copy.deepcopy(parsed[source])):
            card = scrape._public_nine_lotto()
        self.assertEqual("03-11-2026", card["drawDate"])
        self.assertEqual("8079", card["first"])

    def test_two_source_fallback_is_not_enough(self):
        stale = self.public_result()
        current = copy.deepcopy(stale)
        current.update({"drawDate": "03-11-2026", "drawDay": "Tue", "drawNo": "1539/2026", "first": "8079"})
        parsed = {"4dgm": stale, "lotto09": current, "lotto4dlive": current}
        def fake_fetch(url):
            if url == scrape.NINE_FALLBACK_SOURCES["starbucks4d"]:
                raise OSError("unavailable")
            return url
        with mock.patch.object(scrape, "fetch", side_effect=fake_fetch), \
             mock.patch.object(scrape, "_nine_lotto_card", side_effect=lambda html, source: copy.deepcopy(parsed[source])):
            with self.assertRaisesRegex(ValueError, "sources disagree"):
                scrape._public_nine_lotto()


if __name__ == "__main__":
    unittest.main()
