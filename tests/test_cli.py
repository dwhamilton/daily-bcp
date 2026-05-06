from __future__ import annotations

import unittest
import csv
import json
import ssl
import tempfile
import urllib.error
from contextlib import redirect_stdout
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from bcp_cli.cli import run
from bcp_cli.bible_api import fetch_passage
from bcp_cli.config import default_data_dir, parse_options
from bcp_cli.data import find_readings, load_collects
from bcp_cli.history import format_history, load_history, record_reading
from bcp_cli.references import normalize_reference


class CliTests(unittest.TestCase):
    def test_parse_readings_date_and_office(self) -> None:
        options = parse_options(["readings", "morning", "--date", "2026-05-05"])

        self.assertEqual(options.date_arg, "2026-05-05")
        self.assertEqual(options.office, "morning")
        self.assertEqual(options.mode, "readings")
        self.assertEqual(options.csv_path.name, "may_morning.csv")

    def test_readings_default_office_uses_current_time(self) -> None:
        morning = parse_options(["readings"], now=datetime(2026, 5, 5, 9, 0))
        evening = parse_options(["readings"], now=datetime(2026, 5, 5, 12, 0))

        self.assertEqual(morning.office, "morning")
        self.assertEqual(evening.office, "evening")

    def test_parse_relative_date(self) -> None:
        options = parse_options(
            ["readings", "-d", "tomorrow"],
            now=datetime(2026, 5, 5, 9, 0),
        )

        self.assertEqual(options.date_arg, "2026-05-06")
        self.assertEqual(options.csv_path.name, "may_morning.csv")

    def test_parse_collects_command(self) -> None:
        options = parse_options(["--vim", "collects", "sat"])

        self.assertEqual(options.mode, "collect")
        self.assertEqual(options.collect_day, "sat")
        self.assertTrue(options.vim_mode)

    def test_parse_history_command(self) -> None:
        options = parse_options(["history"])

        self.assertEqual(options.mode, "history")
        self.assertEqual(options.history_month, "")

    def test_parse_history_month(self) -> None:
        options = parse_options(["history", "--month", "2026-05"])

        self.assertEqual(options.mode, "history")
        self.assertEqual(options.history_month, "2026-05")

    def test_parse_history_month_abbreviation(self) -> None:
        options = parse_options(["history", "--month", "may"])

        self.assertEqual(options.mode, "history")
        self.assertEqual(options.history_month, "may")

    def test_no_args_prints_first_use(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                parse_options([])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("bcp readings", output.getvalue())

    def test_positional_date_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            parse_options(["2026-05-05", "morning"])

    def test_date_is_readings_only(self) -> None:
        with self.assertRaises(SystemExit):
            parse_options(["collects", "--date", "tomorrow"])

    def test_month_is_history_only(self) -> None:
        with self.assertRaises(SystemExit):
            parse_options(["readings", "--month", "2026-05"])

    def test_option_without_command_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            parse_options(["--vim"])

    def test_normalize_reference(self) -> None:
        self.assertEqual(normalize_reference("Deut 6"), "Deuteronomy 6")
        self.assertEqual(normalize_reference("Luke 4:31-end"), "Luke 4:31-44")
        self.assertEqual(normalize_reference("1 Pet 4:7-end"), "1 Peter 4:7-19")
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

    def test_bible_fetch_ssl_error_has_certificate_hint_without_usage(self) -> None:
        ssl_error = ssl.SSLCertVerificationError("unable to get local issuer certificate")

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError(ssl_error)):
            with self.assertRaises(SystemExit) as raised:
                fetch_passage("Psalm 9")

        message = str(raised.exception)
        self.assertIn("Could not fetch KJV text for 'Psalm 9'", message)
        self.assertIn("HTTPS certificate verification failed", message)
        self.assertIn("Install Certificates.command", message)
        self.assertNotIn("Usage: bcp readings", message)

    def test_bible_fetch_network_error_does_not_print_usage(self) -> None:
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timed out")):
            with self.assertRaises(SystemExit) as raised:
                fetch_passage("Psalm 9")

        message = str(raised.exception)
        self.assertIn("Could not fetch KJV text for 'Psalm 9'", message)
        self.assertNotIn("Usage: bcp readings", message)

    def test_all_bundled_lesson_references_normalize(self) -> None:
        for path in sorted(default_data_dir().glob("*.csv")):
            with self.subTest(path=path.name):
                with path.open(newline="", encoding="utf-8") as handle:
                    for row in csv.DictReader(handle):
                        normalize_reference(row["first_lesson"])
                        normalize_reference(row["second_lesson"])

    def test_record_reading_creates_day_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            record_reading(
                "morning",
                date(2026, 5, 5),
                completed_at=datetime(2026, 5, 7, 9, 0),
                path=path,
            )

            data = load_history(path)
            self.assertEqual(list(data["days"]), ["2026-05-07"])
            self.assertEqual(data["days"]["2026-05-07"]["offices"], ["morning"])
            self.assertEqual(data["days"]["2026-05-07"]["reading_dates"], ["2026-05-05"])

    def test_repeated_reading_updates_same_day_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            record_reading(
                "morning",
                date(2026, 5, 5),
                completed_at=datetime(2026, 5, 7, 9, 0),
                path=path,
            )
            record_reading(
                "evening",
                date(2026, 5, 5),
                completed_at=datetime(2026, 5, 7, 18, 0),
                path=path,
            )

            data = load_history(path)
            self.assertEqual(list(data["days"]), ["2026-05-07"])
            self.assertEqual(data["days"]["2026-05-07"]["offices"], ["morning", "evening"])
            self.assertEqual(data["days"]["2026-05-07"]["reading_dates"], ["2026-05-05"])
            self.assertNotEqual(
                data["days"]["2026-05-07"]["first_completed_at"],
                data["days"]["2026-05-07"]["last_completed_at"],
            )

    def test_requested_lectionary_date_does_not_control_history_day(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            record_reading(
                "morning",
                date(2026, 5, 5),
                completed_at=datetime(2026, 5, 7, 9, 0),
                path=path,
            )

            data = load_history(path)
            self.assertIn("2026-05-07", data["days"])
            self.assertNotIn("2026-05-05", data["days"])

    def test_successful_readings_run_records_usage(self) -> None:
        options = parse_options(["readings", "morning", "--date", "2026-05-05"])

        with patch("bcp_cli.cli.find_readings", return_value=("", ["Psalm 9"], "Deuteronomy 6", "Luke 4")):
            with patch("bcp_cli.cli.load_collects", return_value={}):
                with patch("bcp_cli.cli.format_passage", side_effect=lambda title, ref, compact: f"{title}: {ref}"):
                    with patch("bcp_cli.cli.record_reading") as record:
                        with redirect_stdout(StringIO()):
                            run(options)

        record.assert_called_once()
        self.assertEqual(record.call_args.args[0], "morning")
        self.assertEqual(record.call_args.args[1], date(2026, 5, 5))

    def test_non_readings_commands_do_not_record_usage(self) -> None:
        commands = [
            parse_options(["collects"]),
            parse_options(["common"]),
            parse_options(["devotion"]),
            parse_options(["notes"]),
            parse_options(["history"]),
        ]

        with patch("bcp_cli.cli.print_daily_collect"):
            with patch("bcp_cli.cli.print_common_prayers"):
                with patch("bcp_cli.cli.print_devotion"):
                    with patch("bcp_cli.cli.open_notes"):
                        with patch("bcp_cli.cli.format_history", return_value="history"):
                            with patch("bcp_cli.cli.record_reading") as record:
                                for options in commands:
                                    with redirect_stdout(StringIO()):
                                        run(options)

        record.assert_not_called()

    def test_format_history_with_no_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = format_history(path=Path(directory) / "history.json")

        self.assertEqual(output, "No readings history yet. Run bcp readings to start tracking.")

    def test_format_history_current_month(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "days": {
                            "2026-05-01": {},
                            "2026-05-02": {},
                            "2026-05-04": {},
                            "2026-05-05": {},
                        },
                    }
                ),
                encoding="utf-8",
            )

            output = format_history(today=date(2026, 5, 7), path=path)

        self.assertIn("May 2026", output)
        self.assertIn("Mon Tue Wed Thu Fri Sat Sun", output)
        self.assertIn("                 *   *   -", output)
        self.assertIn(" *   *   -   -", output)
        self.assertIn("Used 4 of 7 days so far this month.", output)
        self.assertIn("Current streak: 0 days.", output)
        self.assertIn("Last reading: 2026-05-05.", output)

    def test_format_history_selected_month(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "days": {
                            "2026-05-31": {},
                            "2026-06-01": {},
                        },
                    }
                ),
                encoding="utf-8",
            )

            output = format_history(month="2026-05", today=date(2026, 6, 2), path=path)

        self.assertIn("May 2026", output)
        self.assertIn("Used 1 of 31 days this month.", output)
        self.assertIn("Last reading: 2026-06-01.", output)

    def test_format_history_selected_month_abbreviation_current_year(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "days": {
                            "2026-04-30": {},
                            "2026-05-01": {},
                        },
                    }
                ),
                encoding="utf-8",
            )

            may_output = format_history(month="may", today=date(2026, 5, 6), path=path)
            apr_output = format_history(month="apr", today=date(2026, 5, 6), path=path)

        self.assertIn("May 2026", may_output)
        self.assertIn("Used 1 of 6 days so far this month.", may_output)
        self.assertIn("April 2026", apr_output)
        self.assertIn("Used 1 of 30 days this month.", apr_output)

    def test_format_history_selected_month_abbreviation_previous_year(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "days": {
                            "2025-12-25": {},
                            "2026-12-25": {},
                        },
                    }
                ),
                encoding="utf-8",
            )

            output = format_history(month="dec", today=date(2026, 5, 6), path=path)

        self.assertIn("December 2025", output)
        self.assertIn("Used 1 of 31 days this month.", output)

    def test_format_history_month_abbreviations_are_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "days": {
                            "2026-05-01": {},
                        },
                    }
                ),
                encoding="utf-8",
            )

            output = format_history(month="MAY", today=date(2026, 5, 6), path=path)

        self.assertIn("May 2026", output)

    def test_format_history_rejects_invalid_month(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(json.dumps({"version": 1, "days": {"2026-05-01": {}}}), encoding="utf-8")

            for month in ["2026-13", "2026-5", "sept", "foo"]:
                with self.subTest(month=month):
                    with self.assertRaises(SystemExit) as raised:
                        format_history(month=month, today=date(2026, 5, 6), path=path)

                    self.assertIn("Invalid month", str(raised.exception))
                    self.assertIn("Expected YYYY-MM or a three-letter month abbreviation", str(raised.exception))

    def test_format_history_rejects_invalid_month_without_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit) as raised:
                format_history(month="foo", today=date(2026, 5, 6), path=Path(directory) / "history.json")

        self.assertIn("Invalid month", str(raised.exception))

    def test_corrupt_history_json_produces_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text("{not json", encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                load_history(path)

        self.assertIn("invalid JSON", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
