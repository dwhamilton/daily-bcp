from __future__ import annotations

from datetime import datetime

from .config import Options, parse_date, parse_options
from .data import (
    find_readings,
    library_item_path,
    list_library_items,
    load_collects,
    load_library_item,
    seed_library_samples,
)
from .errors import usage_error
from .history import format_history, record_reading, record_usage
from .notes import default_memo_path, ensure_library_memo_section, open_notes
from .pager import vim_pager
from .prayers import print_common_prayers, print_daily_collect, print_devotion, show_pages
from .render import format_collect, format_passage


def run(options: Options) -> None:
    date = parse_date(options.date_arg)
    if options.mode == "note":
        open_notes()
        return

    if options.mode == "common":
        print_common_prayers(options)
        if options.common_key:
            record_usage("common")
        return

    if options.mode == "devotion":
        print_devotion(options)
        if options.devotion_key:
            record_usage("devotion")
        return

    if options.mode == "collects":
        print_daily_collect(date, options)
        record_usage("collects")
        return

    if options.mode == "office_collect":
        print_office_collect(date, options)
        record_usage("collects")
        return

    if options.mode == "history":
        print(format_history(month=options.history_month, verbose=options.history_verbose))
        return

    if options.mode == "library":
        if print_library(options, date):
            record_usage("library")
        return

    if options.mode in {"daily", "psalm", "first_lesson", "second_lesson"}:
        print_reading_content(date, options)


def print_library(options: Options, date: datetime) -> bool:
    if options.library_path:
        print(options.library_dir)
        return False

    if not options.library_key:
        print(f"Library: {options.library_dir}")
        print()
        for item in list_library_items(options.library_dir):
            if item.error:
                print(f"{item.key}: [invalid: {item.error}]")
            elif item.title:
                print(f"{item.key}: {item.title}")
            else:
                print(item.key)
        return False

    seed_library_samples(options.library_dir)
    item = load_library_item(library_item_path(options.library_dir, options.library_key))
    pages = [
        (
            f"{item.title} - {reading.title}",
            f"{reading.title}\n{'-' * len(reading.title)}\n\n{reading.text}",
        )
        for reading in item.readings
    ]

    if options.vim_mode:
        memo_path = options.library_dir / "notes.md"
        vim_pager(
            pages,
            memo_path,
            "library",
            prepare_notes=lambda: ensure_library_memo_section(memo_path, date, item.key, item.title),
        )
        return True

    print(item.title)
    print("=" * len(item.title))
    print()
    for index, reading in enumerate(item.readings):
        if index:
            print()
        print(reading.title)
        print("-" * len(reading.title))
        print()
        print(reading.text)
    return True


def print_office_collect(date: datetime, options: Options) -> None:
    collects = load_collects(options.collects_path)
    if options.office == "morning":
        collect = collects.get("office", {}).get("morning")
        if not collect:
            usage_error("No morning collect found.")
        page = format_collect(collect.get("title", ""), collect.get("text", ""))
        show_pages([("Morning Collect", page)], options)
        return

    weekday = date.strftime("%A").lower()
    collect = collects.get("daily", {}).get(weekday)
    if not collect:
        usage_error(f"No evening collect found for {weekday}.")
    title = collect.get("title", "")
    weekday_title = weekday.title()
    heading = f"{title} - {weekday_title}" if title else weekday_title
    page = format_collect(heading, collect.get("text", ""))
    show_pages([(weekday_title, page)], options)


def print_reading_content(date: datetime, options: Options) -> None:
    observance, psalms, first, second = find_readings(date, options.csv_path)
    collects = load_collects(options.collects_path)

    office_title = "Morning Prayer" if options.office == "morning" else "Evening Prayer"
    title = f"{office_title} - {date:%B} {date.day}, {date.year}"

    pages: list[tuple[str, str]] = []

    if options.mode == "daily":
        office_collect = collects.get("office", {}).get(options.office)
        if office_collect:
            collect_page = format_collect(office_collect.get("title", ""), office_collect.get("text", ""))
            pages.append((f"{title} - Collect", collect_page))

    if options.mode in {"daily", "psalm"}:
        for psalm in psalms:
            page = format_passage("Psalm", psalm, options.compact_mode)
            pages.append((f"{title} - {psalm}", page))

    if options.mode in {"daily", "first_lesson"}:
        first_page = format_passage("First Lesson", first, options.compact_mode)
        pages.append((f"{title} - First Lesson", first_page))

    if options.mode in {"daily", "second_lesson"}:
        second_page = format_passage("Second Lesson", second, options.compact_mode)
        pages.append((f"{title} - Second Lesson", second_page))

    record_reading(options.office, date.date())

    if options.vim_mode:
        vim_pager(
            pages,
            default_memo_path(),
            options.office,
            date,
            office_title,
            psalms,
            first,
            second,
        )
    else:
        if options.mode == "daily":
            print(title)
            if observance:
                print(observance)
            print("=" * len(title))
            print()
        for _, page in pages:
            print(page)


def main(argv: list[str] | None = None) -> None:
    run(parse_options(argv))
