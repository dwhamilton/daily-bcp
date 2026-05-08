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
from bcp_cli.data import (
    bundled_library_dir,
    find_readings,
    list_library_items,
    load_collects,
    load_library_item,
    seed_library_samples,
)
from bcp_cli.history import format_history, load_history, record_reading, record_usage
from bcp_cli.notes import editor_command, ensure_library_memo_section, ensure_memo_section
from bcp_cli.pager import wrap_body_lines
from bcp_cli.references import normalize_reference


class CliTests(unittest.TestCase):
    def test_parse_readings_date_and_office(self) -> None:
        options = parse_options(["readings", "morning", "--date", "2026-05-05"])

        self.assertEqual(options.date_arg, "2026-05-05")
        self.assertEqual(options.office, "morning")
        self.assertEqual(options.mode, "daily")
        self.assertEqual(options.csv_path.name, "may_morning.csv")

    def test_parse_daily_commands_and_office_aliases(self) -> None:
        cases = [
            (["daily"], "daily", "morning"),
            (["daily", "am"], "daily", "morning"),
            (["daily", "pm"], "daily", "evening"),
            (["psalm", "morning"], "psalm", "morning"),
            (["first-lesson", "evening"], "first_lesson", "evening"),
            (["second-lesson", "pm"], "second_lesson", "evening"),
            (["collect", "am"], "office_collect", "morning"),
            (["collect", "pm"], "office_collect", "evening"),
        ]
        for args, mode, office in cases:
            with self.subTest(args=args):
                options = parse_options(args, now=datetime(2026, 5, 5, 9, 0))
                self.assertEqual(options.mode, mode)
                self.assertEqual(options.office, office)

    def test_pages_is_preferred_vim_alias(self) -> None:
        options = parse_options(["daily", "--pages"])

        self.assertTrue(options.vim_mode)

    def test_wrap_body_lines_wraps_long_reader_paragraphs(self) -> None:
        wrapped = wrap_body_lines("Alpha beta gamma delta\n\nEpsilon", 12)

        self.assertEqual(wrapped, ["Alpha beta", "gamma delta", "", "Epsilon"])
        self.assertTrue(all(len(line) <= 12 for line in wrapped))

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

        self.assertEqual(options.mode, "collects")
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

    def test_parse_history_verbose(self) -> None:
        options = parse_options(["history", "--verbose"])

        self.assertEqual(options.mode, "history")
        self.assertTrue(options.history_verbose)

    def test_parse_history_month_abbreviation(self) -> None:
        options = parse_options(["history", "--month", "may"])

        self.assertEqual(options.mode, "history")
        self.assertEqual(options.history_month, "may")

    def test_parse_library_list_command(self) -> None:
        options = parse_options(["library"])

        self.assertEqual(options.mode, "library")
        self.assertEqual(options.library_key, "")

    def test_parse_library_item_vim_command(self) -> None:
        options = parse_options(["library", "item1", "--vim"])

        self.assertEqual(options.mode, "library")
        self.assertEqual(options.library_key, "item1")
        self.assertTrue(options.vim_mode)

    def test_parse_library_path_command(self) -> None:
        options = parse_options(["library", "--path"])

        self.assertEqual(options.mode, "library")
        self.assertTrue(options.library_path)

    def test_no_args_prints_first_use(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                parse_options([])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("bcp daily", output.getvalue())
        self.assertIn("bcp psalm pm", output.getvalue())
        self.assertIn("bcp history --verbose", output.getvalue())

    def test_positional_date_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            parse_options(["2026-05-05", "morning"])

    def test_date_is_readings_only(self) -> None:
        with self.assertRaises(SystemExit):
            parse_options(["collects", "--date", "tomorrow"])

    def test_month_is_history_only(self) -> None:
        with self.assertRaises(SystemExit):
            parse_options(["readings", "--month", "2026-05"])

    def test_verbose_is_history_only(self) -> None:
        with self.assertRaises(SystemExit):
            parse_options(["readings", "--verbose"])

    def test_library_rejects_readings_options(self) -> None:
        for args in [
            ["library", "--date", "tomorrow"],
            ["library", "--compact"],
            ["library", "--month", "2026-05"],
        ]:
            with self.subTest(args=args):
                with self.assertRaises(SystemExit):
                    parse_options(args)

    def test_library_path_rejects_item_and_vim(self) -> None:
        for args in [
            ["library", "item1", "--path"],
            ["library", "--path", "--vim"],
            ["readings", "--path"],
        ]:
            with self.subTest(args=args):
                with self.assertRaises(SystemExit):
                    parse_options(args)

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

    def test_load_library_item(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "item1.yaml"
            path.write_text(
                """title: Item Title
readings:
  first:
    title: First Reading
    text: |
      Reading text here.

  second:
    title: Second Reading
    text: |
      Another reading here.
""",
                encoding="utf-8",
            )

            item = load_library_item(path)

        self.assertEqual(item.key, "item1")
        self.assertEqual(item.title, "Item Title")
        self.assertEqual([reading.key for reading in item.readings], ["first", "second"])
        self.assertEqual(item.readings[0].title, "First Reading")
        self.assertEqual(item.readings[1].text, "Another reading here.")

    def test_load_library_item_rejects_missing_fields_and_malformed_yaml(self) -> None:
        cases = {
            "missing_title.yaml": """readings:
  first:
    title: First Reading
    text: |
      Text.
""",
            "missing_readings.yaml": "title: Item Title\n",
            "missing_text.yaml": """title: Item Title
readings:
  first:
    title: First Reading
""",
            "malformed.yaml": """title Item Title
readings:
  first:
    title: First Reading
    text: |
      Text.
""",
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, content in cases.items():
                path = Path(directory) / name
                path.write_text(content, encoding="utf-8")
                with self.subTest(name=name):
                    with self.assertRaises(SystemExit):
                        load_library_item(path)

    def test_list_library_items_rejects_empty_folder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch("bcp_cli.data.bundled_library_dir", return_value=Path(directory) / "missing"):
                with self.assertRaises(SystemExit) as raised:
                    list_library_items(Path(directory))

        self.assertIn("No library items found", str(raised.exception))

    def test_list_library_items_shows_stems_and_titles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "item1.yaml"
            path.write_text(
                """title: Item Title
readings:
  first:
    title: First Reading
    text: |
      Text.
""",
                encoding="utf-8",
            )

            items = list_library_items(Path(directory))

        self.assertTrue(any(item.key == "item1" and item.title == "Item Title" for item in items))

    def test_list_library_items_reports_invalid_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "broken.yaml").write_text("title Broken\n", encoding="utf-8")

            items = list_library_items(Path(directory))

        broken = next(item for item in items if item.key == "broken")
        self.assertEqual(broken.title, "")
        self.assertIn("broken.yaml:1: malformed YAML line.", broken.error)

    def test_bundled_library_sample_loads(self) -> None:
        item = load_library_item(bundled_library_dir() / "sample.yaml")

        self.assertEqual(item.key, "sample")
        self.assertEqual(item.title, "Sample Devotional Readings")
        self.assertEqual(item.readings[0].title, "Augustine, Confessions, Book I.1")

    def test_list_library_items_seeds_bundled_sample(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            library_dir = Path(directory)

            items = list_library_items(library_dir)

            sample_path = library_dir / "sample.yaml"
            seeded = sample_path.read_text(encoding="utf-8")

        self.assertTrue(any(item.key == "sample" and item.title == "Sample Devotional Readings" for item in items))
        self.assertIn("Augustine, Confessions, Book I.1", seeded)

    def test_seed_library_samples_does_not_overwrite_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            library_dir = Path(directory)
            sample_path = library_dir / "sample.yaml"
            sample_path.write_text("title: Custom\n", encoding="utf-8")

            seed_library_samples(library_dir)

            content = sample_path.read_text(encoding="utf-8")

        self.assertEqual(content, "title: Custom\n")

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
            self.assertEqual(data["days"]["2026-05-07"]["activities"], ["readings"])
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
            self.assertEqual(data["days"]["2026-05-07"]["activities"], ["readings"])
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

    def test_repeated_usage_updates_same_day_activities(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            record_usage("collects", completed_at=datetime(2026, 5, 7, 9, 0), path=path)
            record_usage("collects", completed_at=datetime(2026, 5, 7, 10, 0), path=path)
            record_usage("common", completed_at=datetime(2026, 5, 7, 11, 0), path=path)

            data = load_history(path)
            self.assertEqual(data["days"]["2026-05-07"]["activities"], ["collects", "common"])
            self.assertNotEqual(
                data["days"]["2026-05-07"]["first_completed_at"],
                data["days"]["2026-05-07"]["last_completed_at"],
            )

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

    def test_reading_part_commands_render_only_requested_content(self) -> None:
        commands = [
            (parse_options(["psalm", "am", "--date", "2026-05-05"]), ["Psalm: Psalm 9"], ["First Lesson", "Second Lesson"]),
            (
                parse_options(["first-lesson", "am", "--date", "2026-05-05"]),
                ["First Lesson: Deuteronomy 6"],
                ["Psalm:", "Second Lesson"],
            ),
            (
                parse_options(["second-lesson", "am", "--date", "2026-05-05"]),
                ["Second Lesson: Luke 4"],
                ["Psalm:", "First Lesson"],
            ),
        ]

        for options, included, excluded in commands:
            with self.subTest(mode=options.mode):
                with patch("bcp_cli.cli.find_readings", return_value=("", ["Psalm 9"], "Deuteronomy 6", "Luke 4")):
                    with patch("bcp_cli.cli.load_collects", return_value={}):
                        with patch("bcp_cli.cli.format_passage", side_effect=lambda title, ref, compact: f"{title}: {ref}"):
                            with patch("bcp_cli.cli.record_reading") as record:
                                output = StringIO()
                                with redirect_stdout(output):
                                    run(options)

                for text in included:
                    self.assertIn(text, output.getvalue())
                for text in excluded:
                    self.assertNotIn(text, output.getvalue())
                record.assert_called_once()

    def test_collect_am_uses_morning_office_collect(self) -> None:
        options = parse_options(["collect", "am", "--date", "2026-05-06"])
        collects = {
            "office": {"morning": {"title": "Morning", "text": "Morning text."}},
            "daily": {"wednesday": {"title": "Wednesday", "text": "Evening text."}},
        }

        with patch("bcp_cli.cli.load_collects", return_value=collects):
            with patch("bcp_cli.cli.record_usage"):
                output = StringIO()
                with redirect_stdout(output):
                    run(options)

        self.assertIn("Morning", output.getvalue())
        self.assertIn("Morning text.", output.getvalue())
        self.assertNotIn("Evening text.", output.getvalue())

    def test_collect_pm_uses_weekday_evening_collect(self) -> None:
        options = parse_options(["collect", "pm", "--date", "2026-05-06"])
        collects = {
            "office": {"morning": {"title": "Morning", "text": "Morning text."}},
            "daily": {"wednesday": {"title": "Wednesday", "text": "Evening text."}},
        }

        with patch("bcp_cli.cli.load_collects", return_value=collects):
            with patch("bcp_cli.cli.record_usage"):
                output = StringIO()
                with redirect_stdout(output):
                    run(options)

        self.assertIn("Wednesday", output.getvalue())
        self.assertIn("Evening text.", output.getvalue())
        self.assertNotIn("Morning text.", output.getvalue())

    def test_collects_without_day_prints_all_daily_collects(self) -> None:
        options = parse_options(["collects"])

        with patch("bcp_cli.cli.record_usage"):
            output = StringIO()
            with redirect_stdout(output):
                run(options)

        self.assertIn("A Collect for Resurrection Hope - Sunday", output.getvalue())
        self.assertIn("A Collect for the Eve of Worship - Saturday", output.getvalue())

    def test_successful_content_commands_record_usage(self) -> None:
        commands = [
            (parse_options(["collects"]), "collects"),
            (parse_options(["common", "lords-prayer"]), "common"),
            (parse_options(["common", "all"]), "common"),
            (parse_options(["devotion", "daily-growth"]), "devotion"),
            (parse_options(["devotion", "all"]), "devotion"),
        ]

        with patch("bcp_cli.cli.print_daily_collect"):
            with patch("bcp_cli.cli.print_common_prayers"):
                with patch("bcp_cli.cli.print_devotion"):
                    with patch("bcp_cli.cli.record_usage") as record:
                        for options, activity in commands:
                            with self.subTest(activity=activity, args=options.mode):
                                with redirect_stdout(StringIO()):
                                    run(options)

        self.assertEqual([call.args[0] for call in record.call_args_list], [activity for _, activity in commands])

    def test_successful_library_item_records_usage(self) -> None:
        options = parse_options(["library", "item1"])

        with patch("bcp_cli.cli.print_library", return_value=True):
            with patch("bcp_cli.cli.record_usage") as record:
                with redirect_stdout(StringIO()):
                    run(options)

        record.assert_called_once_with("library")

    def test_utility_commands_do_not_record_usage(self) -> None:
        commands = [
            parse_options(["common"]),
            parse_options(["devotion"]),
            parse_options(["library"]),
            parse_options(["library", "--path"]),
            parse_options(["notes"]),
            parse_options(["history"]),
        ]

        with patch("bcp_cli.cli.print_common_prayers"):
            with patch("bcp_cli.cli.print_devotion"):
                with patch("bcp_cli.cli.print_library", return_value=False):
                    with patch("bcp_cli.cli.open_notes"):
                        with patch("bcp_cli.cli.format_history", return_value="history"):
                            with patch("bcp_cli.cli.record_usage") as record:
                                for options in commands:
                                    with redirect_stdout(StringIO()):
                                        run(options)

        record.assert_not_called()

    def test_library_list_run_prints_items(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "item1.yaml").write_text(
                """title: Item Title
readings:
  first:
    title: First Reading
    text: |
      Text.
""",
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"BCP_LIBRARY_DIR": directory}):
                options = parse_options(["library"])

            output = StringIO()
            with redirect_stdout(output):
                run(options)

        rendered = output.getvalue()
        self.assertIn(f"Library: {directory}\n\n", rendered)
        self.assertIn("sample: Sample Devotional Readings\n", rendered)
        self.assertIn("item1: Item Title\n", rendered)

    def test_library_list_run_prints_invalid_file_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "broken.yaml").write_text("title Broken\n", encoding="utf-8")
            with patch.dict("os.environ", {"BCP_LIBRARY_DIR": directory}):
                options = parse_options(["library"])

            output = StringIO()
            with redirect_stdout(output):
                run(options)

        rendered = output.getvalue()
        self.assertIn("broken: [invalid: broken.yaml:1: malformed YAML line.]", rendered)

    def test_library_path_run_prints_only_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", {"BCP_LIBRARY_DIR": directory}):
                options = parse_options(["library", "--path"])

            output = StringIO()
            with redirect_stdout(output):
                run(options)

        self.assertEqual(output.getvalue(), f"{directory}\n")

    def test_library_item_run_prints_readings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "item1.yaml").write_text(
                """title: Item Title
readings:
  first:
    title: First Reading
    text: |
      Reading text here.
  second:
    title: Second Reading
    text: |
      Another reading here.
""",
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"BCP_LIBRARY_DIR": directory}):
                options = parse_options(["library", "item1"])

            output = StringIO()
            with patch("bcp_cli.cli.record_usage"):
                with redirect_stdout(output):
                    run(options)

        rendered = output.getvalue()
        self.assertIn("Item Title\n==========", rendered)
        self.assertIn("First Reading\n-------------", rendered)
        self.assertIn("Reading text here.", rendered)
        self.assertIn("Second Reading\n--------------", rendered)

    def test_library_vim_uses_library_notes_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "item1.yaml").write_text(
                """title: Item Title
readings:
  first:
    title: First Reading
    text: |
      Text.
""",
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"BCP_LIBRARY_DIR": directory}):
                options = parse_options(["library", "item1", "--vim"], now=datetime(2026, 5, 7, 9, 0))

            with patch("bcp_cli.cli.vim_pager") as pager:
                with patch("bcp_cli.cli.record_usage"):
                    run(options)

            pager.assert_called_once()
            self.assertEqual(pager.call_args.args[1], Path(directory) / "notes.md")
            pager.call_args.kwargs["prepare_notes"]()
            notes = Path(directory, "notes.md").read_text(encoding="utf-8")

        self.assertIn("## 2026-05-07 - Item Title", notes)
        self.assertIn("<!-- daily-bcp-library:2026-05-07:item1 -->", notes)

    def test_library_note_section_creation_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.md"
            reading_date = datetime(2026, 5, 7, 9, 0)

            ensure_library_memo_section(path, reading_date, "item1", "Item Title")
            ensure_library_memo_section(path, reading_date, "item1", "Item Title")

            notes = path.read_text(encoding="utf-8")

        self.assertEqual(notes.count("## 2026-05-07 - Item Title"), 1)

    def test_daily_note_section_still_writes_to_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.md"

            ensure_memo_section(
                path,
                datetime(2026, 5, 7, 9, 0),
                "Morning Prayer",
                "morning",
                ["Psalm 9"],
                "Deuteronomy 6",
                "Luke 4",
            )

            notes = path.read_text(encoding="utf-8")

        self.assertIn("## 2026-05-07 - Morning Prayer", notes)

    def test_editor_command_respects_visual(self) -> None:
        with patch.dict("os.environ", {"VISUAL": "code --wait", "EDITOR": "vim"}, clear=True):
            self.assertEqual(editor_command(), ["code", "--wait"])

    def test_editor_command_respects_editor(self) -> None:
        with patch.dict("os.environ", {"EDITOR": "vim"}, clear=True):
            self.assertEqual(editor_command(), ["vim"])

    def test_editor_command_defaults_to_nano(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("bcp_cli.notes.shutil.which", return_value="/usr/bin/nano"):
                self.assertEqual(editor_command(), ["nano"])

    def test_editor_command_requires_configuration_without_nano(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("bcp_cli.notes.shutil.which", return_value=None):
                with self.assertRaises(RuntimeError):
                    editor_command()

    def test_format_history_with_no_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = format_history(path=Path(directory) / "history.json")

        self.assertEqual(output, "No history yet. Run bcp daily to start tracking.")

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
        self.assertIn("Last use: 2026-05-05.", output)

    def test_format_history_verbose_includes_day_details(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "days": {
                            "2026-05-05": {
                                "activities": ["readings", "collects"],
                                "offices": ["morning"],
                                "reading_dates": ["2026-05-05"],
                                "first_completed_at": "2026-05-05T09:00:00",
                                "last_completed_at": "2026-05-05T10:00:00",
                            },
                            "2026-06-01": {
                                "activities": ["common"],
                                "first_completed_at": "2026-06-01T09:00:00",
                                "last_completed_at": "2026-06-01T09:00:00",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            output = format_history(month="2026-05", verbose=True, today=date(2026, 6, 2), path=path)

        self.assertIn("Details", output)
        self.assertIn("2026-05-05:", output)
        self.assertIn("activities: readings, collects", output)
        self.assertIn("offices: morning", output)
        self.assertIn("reading_dates: 2026-05-05", output)
        self.assertIn("first_completed_at: 2026-05-05T09:00:00", output)
        self.assertNotIn("2026-06-01:", output)

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
        self.assertIn("Last use: 2026-06-01.", output)

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
