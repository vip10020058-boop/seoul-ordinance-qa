import unittest

from fetch_ordinances import select_ordinance_version


class SelectOrdinanceVersionTests(unittest.TestCase):
    def test_selects_latest_version_not_after_cutoff(self):
        hits = [
            {"mst": "old", "effective": "20250714"},
            {"mst": "cutoff", "effective": "20261001"},
            {"mst": "future", "effective": "20261201"},
        ]
        selected = select_ordinance_version(hits, "20261001")
        self.assertEqual(selected["mst"], "cutoff")

    def test_selects_latest_earlier_version_when_no_cutoff_day_version(self):
        hits = [
            {"mst": "older", "effective": "20250101"},
            {"mst": "latest_eligible", "effective": "20260713"},
            {"mst": "future", "effective": "20261101"},
        ]
        selected = select_ordinance_version(hits, "20261001")
        self.assertEqual(selected["mst"], "latest_eligible")

    def test_rejects_when_every_version_is_after_cutoff(self):
        hits = [
            {"mst": "future_1", "effective": "20261002"},
            {"mst": "future_2", "effective": "20261101"},
        ]
        with self.assertRaises(ValueError):
            select_ordinance_version(hits, "20261001")

    def test_ignores_entries_without_effective_date(self):
        hits = [
            {"mst": "missing_date", "effective": ""},
            {"mst": "eligible", "effective": "20260930"},
        ]
        selected = select_ordinance_version(hits, "20261001")
        self.assertEqual(selected["mst"], "eligible")


if __name__ == "__main__":
    unittest.main()
