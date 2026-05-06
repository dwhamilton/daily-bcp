from __future__ import annotations

import unittest
from datetime import datetime

from bcp_cli.config import default_data_dir, parse_options
from bcp_cli.data import find_readings, load_collects
from bcp_cli.references import normalize_reference


class CliTests(unittest.TestCase):
    def test_parse_date_and_office(self) -> None:
        options = parse_options(["2026-05-05", "morning"])

        self.assertEqual(options.date_arg, "2026-05-05")
        self.assertEqual(options.office, "morning")
        self.assertEqual(options.mode, "readings")
        self.assertEqual(options.csv_path.name, "may_morning.csv")

    def test_parse_collect_command(self) -> None:
        options = parse_options(["--vim", "collect", "sat"])

        self.assertEqual(options.mode, "collect")
        self.assertEqual(options.collect_day, "sat")
        self.assertTrue(options.vim_mode)

    def test_normalize_reference(self) -> None:
        self.assertEqual(normalize_reference("Deut 6"), "Deuteronomy 6")
        self.assertEqual(normalize_reference("Luke 4:31-end"), "Luke 4:31-44")
        self.assertEqual(normalize_reference("1 Pet 2:11–3:7"), "1 Peter 2:11-3:7")

    def test_load_collects(self) -> None:
        collects = load_collects(default_data_dir() / "collects.yaml")

        self.assertIn("office", collects)
        self.assertIn("daily", collects)
        self.assertEqual(collects["common_prayers"]["lords_prayer"]["title"], "The Lord's Prayer")

    def test_find_readings(self) -> None:
        observance, psalms, first, second = find_readings(
            datetime.strptime("2026-05-05", "%Y-%m-%d"),
            default_data_dir() / "may_morning.csv",
        )

        self.assertEqual(observance, "")
        self.assertEqual(psalms, ["Psalm 9"])
        self.assertEqual(first, "Deuteronomy 6")
        self.assertEqual(second, "Luke 4:31-44")


if __name__ == "__main__":
    unittest.main()
