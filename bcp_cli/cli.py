from __future__ import annotations

from .config import Options, parse_date, parse_options
from .data import find_readings, load_collects
from .notes import default_memo_path, open_notes
from .pager import vim_pager
from .prayers import print_common_prayers, print_daily_collect, print_devotion
from .render import format_collect, format_passage


def run(options: Options) -> None:
    date = parse_date(options.date_arg)
    if options.mode == "note":
        open_notes()
        return

    if options.mode == "common":
        print_common_prayers(options)
        return

    if options.mode == "devotion":
        print_devotion(options)
        return

    if options.mode == "collect":
        print_daily_collect(date, options)
        return

    observance, psalms, first, second = find_readings(date, options.csv_path)
    collects = load_collects(options.collects_path)

    office_title = "Morning Prayer" if options.office == "morning" else "Evening Prayer"
    title = f"{office_title} - {date:%B} {date.day}, {date.year}"
    if not options.vim_mode:
        print(title)
        if observance:
            print(observance)
        print("=" * len(title))
        print()

    pages: list[tuple[str, str]] = []

    office_collect = collects.get("office", {}).get(options.office)
    if office_collect:
        collect_page = format_collect(office_collect.get("title", ""), office_collect.get("text", ""))
        pages.append((f"{title} - Collect", collect_page))
        if not options.vim_mode:
            print(collect_page)

    for psalm in psalms:
        page = format_passage("Psalm", psalm, options.compact_mode)
        pages.append((f"{title} - {psalm}", page))
        if not options.vim_mode:
            print(page)

    first_page = format_passage("First Lesson", first, options.compact_mode)
    second_page = format_passage("Second Lesson", second, options.compact_mode)
    pages.append((f"{title} - First Lesson", first_page))
    pages.append((f"{title} - Second Lesson", second_page))

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
        print(first_page)
        print(second_page)


def main(argv: list[str] | None = None) -> None:
    run(parse_options(argv))
