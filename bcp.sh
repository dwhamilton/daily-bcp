#!/usr/bin/env bash

set -euo pipefail

date_arg="$(date +%F)"
office="evening"
mode="readings"
collect_day=""
vim_mode="false"

args=()
for arg in "$@"; do
  if [[ "$arg" == "--vim" ]]; then
    vim_mode="true"
  else
    args+=("$arg")
  fi
done

if [[ ${#args[@]} -gt 2 ]]; then
  printf 'Usage: %s [YYYY-MM-DD] [morning|evening]\n' "${0##*/}" >&2
  printf '       %s [morning|evening]\n' "${0##*/}" >&2
  printf '       %s [--vim] [YYYY-MM-DD] [morning|evening]\n' "${0##*/}" >&2
  printf '       %s collect [weekday]\n' "${0##*/}" >&2
  exit 1
fi

if [[ ${#args[@]} -eq 1 ]]; then
  if [[ "${args[0]}" == "collect" ]]; then
    mode="collect"
  elif [[ "${args[0]}" == "morning" || "${args[0]}" == "evening" ]]; then
    office="${args[0]}"
  else
    date_arg="${args[0]}"
  fi
elif [[ ${#args[@]} -eq 2 ]]; then
  if [[ "${args[0]}" == "collect" ]]; then
    mode="collect"
    collect_day="${args[1]}"
  else
    date_arg="${args[0]}"
    office="${args[1]}"
  fi
fi

if [[ "$mode" == "collect" && "$vim_mode" == "true" ]]; then
  printf 'Usage: %s collect [weekday]\n' "${0##*/}" >&2
  printf '%s\n' '--vim is only supported for morning and evening readings.' >&2
  exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$mode" == "readings" && "$office" != "morning" && "$office" != "evening" ]]; then
  printf 'Usage: %s [YYYY-MM-DD] [morning|evening]\n' "${0##*/}" >&2
  exit 1
fi

month_name="$(date -j -f '%Y-%m-%d' "$date_arg" '+%B' 2>/dev/null || date -d "$date_arg" '+%B' 2>/dev/null || true)"
month_slug="$(printf '%s' "$month_name" | tr '[:upper:]' '[:lower:]')"
csv_path="${BCP_CSV:-"$script_dir/${month_slug}_${office}.csv"}"
collects_path="${BCP_COLLECTS:-"$script_dir/collects.yaml"}"

python3 - "$date_arg" "$office" "$csv_path" "$collects_path" "$mode" "$collect_day" "$vim_mode" <<'PY'
from __future__ import annotations

import csv
import json
import os
import re
import shlex
import subprocess
import sys
import textwrap
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

DATE_ARG = sys.argv[1]
OFFICE = sys.argv[2]
CSV_PATH = Path(sys.argv[3])
COLLECTS_PATH = Path(sys.argv[4])
MODE = sys.argv[5]
COLLECT_DAY = sys.argv[6].lower()
VIM_MODE = sys.argv[7] == "true"
API_ROOT = "https://bible-api.com"
WRAP_WIDTH = 78

BOOKS = {
    "Deut": "Deuteronomy",
    "Eccl": "Ecclesiastes",
    "Ezek": "Ezekiel",
    "Josh": "Joshua",
    "Judg": "Judges",
    "Dan": "Daniel",
    "Matt": "Matthew",
    "Gal": "Galatians",
    "1 Pet": "1 Peter",
    "2 Pet": "2 Peter",
    "1 Thess": "1 Thessalonians",
    "2 Thess": "2 Thessalonians",
}

# Enough for the current local May lectionary. Add chapters here as more CSVs
# introduce "end" references.
CHAPTER_VERSE_COUNTS = {
    ("John", 1): 51,
    ("1 John", 2): 29,
    ("Luke", 2): 52,
    ("Luke", 3): 38,
    ("Luke", 4): 44,
    ("Luke", 5): 39,
    ("Luke", 7): 50,
    ("Luke", 8): 56,
    ("Luke", 9): 62,
    ("Luke", 10): 42,
    ("Luke", 11): 54,
    ("Luke", 13): 35,
    ("Luke", 15): 32,
    ("Luke", 17): 37,
    ("Luke", 19): 48,
    ("Luke", 21): 38,
    ("Luke", 22): 71,
    ("Luke", 24): 53,
    ("1 Thessalonians", 3): 13,
    ("1 Thessalonians", 5): 28,
    ("2 Peter", 3): 18,
    ("Acts", 1): 26,
    ("Acts", 2): 47,
    ("Acts", 5): 42,
    ("Acts", 8): 40,
    ("Acts", 9): 43,
    ("Acts", 10): 48,
    ("Acts", 11): 30,
    ("Acts", 14): 28,
    ("Acts", 16): 40,
    ("Acts", 17): 34,
    ("Acts", 19): 41,
    ("Acts", 20): 38,
    ("Acts", 23): 35,
}


def usage_error(message: str) -> None:
    raise SystemExit(
        f"{message}\n"
        "Usage: bcp.sh [YYYY-MM-DD] [morning|evening]\n"
        "       bcp.sh [morning|evening]\n"
        "       bcp.sh [--vim] [YYYY-MM-DD] [morning|evening]\n"
        "       bcp.sh collect [weekday]"
    )


def parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        usage_error(f"Invalid date: {value!r}. Expected YYYY-MM-DD.")


def normalize_book(ref: str) -> str:
    for short, full in sorted(BOOKS.items(), key=lambda item: len(item[0]), reverse=True):
        if ref == short or ref.startswith(f"{short} "):
            return full + ref[len(short):]
    return ref


def normalize_reference(ref: str) -> str:
    ref = ref.replace("†", "")
    ref = ref.replace("–", "-").replace("—", "-")
    ref = re.sub(r"\s+", " ", ref).strip()
    ref = normalize_book(ref)

    chapter_end = re.match(r"^(.+?)\s+(\d+):(\d+)-(\d+):end$", ref, flags=re.IGNORECASE)
    if chapter_end:
        book, first_chapter, first_verse, last_chapter_text = chapter_end.groups()
        last_chapter = int(last_chapter_text)
        last_verse = CHAPTER_VERSE_COUNTS.get((book, last_chapter))
        if not last_verse:
            usage_error(f"Cannot expand 'end' in {ref!r}; add its chapter length to bcp.sh.")
        return f"{book} {first_chapter}:{first_verse}-{last_chapter}:{last_verse}"

    chapter_verses = re.match(r"^(.+?)\s+(\d+)\s+([\d,\-]+)$", ref)
    if chapter_verses:
        book, chapter, verses = chapter_verses.groups()
        return f"{book} {chapter}:{verses}"

    no_end = re.match(r"^(.+?)\s+(\d+):(\d+)-end$", ref, flags=re.IGNORECASE)
    if no_end:
        book, chapter_text, first_verse = no_end.groups()
        chapter = int(chapter_text)
        last_verse = CHAPTER_VERSE_COUNTS.get((book, chapter))
        if not last_verse:
            usage_error(f"Cannot expand 'end' in {ref!r}; add its chapter length to bcp.sh.")
        return f"{book} {chapter}:{first_verse}-{last_verse}"

    return ref


def psalm_references(value: str) -> list[str]:
    refs = []
    for piece in value.split(","):
        piece = piece.strip()
        if piece:
            refs.append(f"Psalm {piece}")
    return refs


def find_readings(date: datetime) -> tuple[str, list[str], str, str]:
    if not CSV_PATH.exists():
        usage_error(f"Could not find CSV file: {CSV_PATH}")

    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required_fields = {
            "day",
            "observance",
            "sixty_day_psalter_ep",
            "first_lesson",
            "second_lesson",
        }
        if not reader.fieldnames or not required_fields.issubset(reader.fieldnames):
            expected = ", ".join(sorted(required_fields))
            found = ", ".join(reader.fieldnames or [])
            usage_error(
                f"{CSV_PATH.name} is not in the expected CSV format. "
                f"Expected fields: {expected}. Found: {found}"
            )

        for row in reader:
            if int(row["day"]) == date.day:
                observance = row["observance"].strip()
                psalms = psalm_references(row["sixty_day_psalter_ep"])
                first = normalize_reference(row["first_lesson"])
                second = normalize_reference(row["second_lesson"])
                return observance, psalms, first, second

    usage_error(f"No row found for {date:%B} {date.day}.")


def load_collects() -> dict[str, dict[str, dict[str, str]]]:
    if not COLLECTS_PATH.exists():
        return {}

    collects: dict[str, dict[str, dict[str, str]]] = {}
    section = ""
    key = ""
    field = ""

    for raw_line in COLLECTS_PATH.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue

        if not raw_line.startswith(" "):
            section = raw_line.rstrip(":")
            collects.setdefault(section, {})
            key = ""
            field = ""
            continue

        if raw_line.startswith("  ") and not raw_line.startswith("    "):
            stripped = raw_line.strip()
            if stripped.endswith(":"):
                key = stripped.rstrip(":")
                collects.setdefault(section, {}).setdefault(key, {})
                field = ""
                continue

        if raw_line.startswith("    ") and not raw_line.startswith("      "):
            stripped = raw_line.strip()

            name, _, value = stripped.partition(":")
            field = name
            value = value.strip()
            if value == "|":
                collects[section][key][field] = ""
            else:
                collects[section][key][field] = value.strip('"')
            continue

        if raw_line.startswith("      ") and field:
            text = collects[section][key].get(field, "")
            line = raw_line[6:]
            collects[section][key][field] = f"{text}\n{line}".strip("\n")

    return collects


def format_collect(title: str, text: str) -> str:
    heading = title or "A Collect"
    body = textwrap.fill(" ".join(text.split()), width=WRAP_WIDTH)
    return f"{heading}\n{'-' * len(heading)}\n{body}\n"


def print_collect(title: str, text: str) -> None:
    print(format_collect(title, text))


def normalize_weekday(value: str, date: datetime) -> str:
    if not value:
        return date.strftime("%A").lower()

    days = {
        "sun": "sunday",
        "sunday": "sunday",
        "mon": "monday",
        "monday": "monday",
        "tue": "tuesday",
        "tues": "tuesday",
        "tuesday": "tuesday",
        "wed": "wednesday",
        "wednesday": "wednesday",
        "thu": "thursday",
        "thur": "thursday",
        "thurs": "thursday",
        "thursday": "thursday",
        "fri": "friday",
        "friday": "friday",
        "sat": "saturday",
        "saturday": "saturday",
    }
    if value not in days:
        usage_error(f"Unknown weekday for collect: {value!r}.")
    return days[value]


def print_daily_collect(date: datetime) -> None:
    collects = load_collects()
    weekday = normalize_weekday(COLLECT_DAY, date)
    daily_collect = collects.get("daily", {}).get(weekday)
    if not daily_collect:
        usage_error(f"No collect found for {weekday}.")

    title = daily_collect.get("title", "")
    weekday_title = weekday.title()
    heading = f"{title} - {weekday_title}" if title else weekday_title
    print_collect(heading, daily_collect.get("text", ""))


def passage_url(ref: str) -> str:
    encoded = urllib.parse.quote(ref)
    query = urllib.parse.urlencode(
        {
            "translation": "kjv",
            "single_chapter_book_matching": "indifferent",
        }
    )
    return f"{API_ROOT}/{encoded}?{query}"


def fetch_passage(ref: str) -> dict:
    request = urllib.request.Request(
        passage_url(ref),
        headers={"User-Agent": "bcp-cli-prototype/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        usage_error(f"Could not fetch KJV text for {ref!r}: {exc}")


def format_passage(label: str, ref: str) -> str:
    data = fetch_passage(ref)
    verses = data.get("verses", [])
    if not verses:
        usage_error(f"No verses returned for {ref!r}.")

    lines = [label, ref, "-" * len(ref)]
    current_chapter = None
    for verse in verses:
        chapter = verse["chapter"]
        if chapter != current_chapter:
            current_chapter = chapter
            lines.extend(["", f"{verse['book_name']} {chapter}"])
        text = " ".join(verse["text"].split())
        wrapped = textwrap.fill(
            f"{verse['verse']}. {text}",
            width=WRAP_WIDTH,
            subsequent_indent="    ",
        )
        lines.append(wrapped)
    return "\n".join(lines) + "\n"


def print_passage(label: str, ref: str) -> None:
    print(format_passage(label, ref))


def default_memo_path() -> Path:
    configured = os.environ.get("BCP_MEMO")
    if configured:
        return Path(configured).expanduser()

    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return base / "bcp-cli" / "memo.md"


def ensure_memo_section(
    memo_path: Path,
    date: datetime,
    office_title: str,
    psalms: list[str],
    first: str,
    second: str,
) -> None:
    marker = f"<!-- bcp-cli:{date:%Y-%m-%d}:{OFFICE} -->"
    memo_path.parent.mkdir(parents=True, exist_ok=True)
    if not memo_path.exists():
        memo_path.write_text("# BCP Notes\n", encoding="utf-8")

    existing = memo_path.read_text(encoding="utf-8")
    if marker in existing:
        return

    section = [
        "",
        marker,
        f"## {date:%Y-%m-%d} - {office_title}",
        "",
        f"Psalms: {', '.join(psalms) if psalms else 'None'}",
        f"First Lesson: {first}",
        f"Second Lesson: {second}",
        "",
        "Notes:",
        "",
    ]
    with memo_path.open("a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write("\n".join(section))


def editor_command() -> list[str]:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    return shlex.split(editor)


def vim_pager(
    pages: list[tuple[str, str]],
    memo_path: Path,
    date: datetime,
    office_title: str,
    psalms: list[str],
    first: str,
    second: str,
) -> None:
    if not sys.stdout.isatty():
        usage_error("--vim requires an interactive terminal.")

    import curses

    tty = None
    try:
        tty = open("/dev/tty", "rb", buffering=0)
        os.dup2(tty.fileno(), sys.stdin.fileno())
    except OSError:
        usage_error("--vim could not read keyboard input from /dev/tty.")

    def draw_help(stdscr) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        lines = [
            "Help",
            "----",
            "h        previous section",
            "l        next section",
            "j        scroll down one line",
            "k        scroll up one line",
            "space    scroll down one screen",
            "b        scroll up one screen",
            "gg       jump to top",
            "G        jump to bottom",
            "m        open memo file in editor",
            "?        toggle this help",
            "q        quit",
        ]
        for row, line in enumerate(lines[:height]):
            stdscr.addnstr(row, 0, line, max(0, width - 1))
        stdscr.refresh()

    def draw(stdscr, page_index: int, offset: int, show_help: bool) -> None:
        if show_help:
            draw_help(stdscr)
            return

        stdscr.erase()
        height, width = stdscr.getmaxyx()
        title, body = pages[page_index]
        body_lines = body.splitlines()
        max_offset = max(0, len(body_lines) - max(1, height - 2))
        offset = min(offset, max_offset)

        header = f"{title} ({page_index + 1}/{len(pages)})"
        help_text = "h/l section  j/k scroll  m memo  ? help  q quit"
        stdscr.addnstr(0, 0, header, max(0, width - 1), curses.A_REVERSE)
        if width > len(help_text) + 2:
            stdscr.addnstr(0, max(0, width - len(help_text) - 1), help_text, len(help_text), curses.A_REVERSE)

        available = max(0, height - 2)
        for row, line in enumerate(body_lines[offset:offset + available], start=1):
            stdscr.addnstr(row, 0, line, max(0, width - 1))

        if max_offset:
            footer = f"line {offset + 1}-{min(len(body_lines), offset + available)} of {len(body_lines)}"
            stdscr.addnstr(height - 1, 0, footer, max(0, width - 1), curses.A_REVERSE)
        stdscr.refresh()

    def run(stdscr) -> None:
        curses.curs_set(0)
        page_index = 0
        offsets = [0 for _ in pages]
        show_help = False

        def open_memo(stdscr) -> None:
            ensure_memo_section(memo_path, date, office_title, psalms, first, second)
            command = editor_command() + [str(memo_path)]
            curses.def_prog_mode()
            curses.endwin()
            try:
                subprocess.run(command, check=False)
            finally:
                curses.reset_prog_mode()
                stdscr.clear()
                stdscr.refresh()

        while True:
            draw(stdscr, page_index, offsets[page_index], show_help)
            key = stdscr.getch()
            if key == ord("?"):
                show_help = not show_help
                continue
            if show_help:
                if key in (ord("q"), 27):
                    break
                show_help = False
                continue

            height, _ = stdscr.getmaxyx()
            page_len = len(pages[page_index][1].splitlines())
            max_offset = max(0, page_len - max(1, height - 2))
            page_step = max(1, height - 3)

            if key in (ord("q"), 27):
                break
            if key == ord("l") and page_index < len(pages) - 1:
                page_index += 1
            elif key == ord("h") and page_index > 0:
                page_index -= 1
            elif key == ord("g"):
                stdscr.timeout(500)
                second_key = stdscr.getch()
                stdscr.timeout(-1)
                if second_key == ord("g"):
                    offsets[page_index] = 0
            elif key == ord("G"):
                offsets[page_index] = max_offset
            elif key == ord("j"):
                offsets[page_index] = min(max_offset, offsets[page_index] + 1)
            elif key == ord("k"):
                offsets[page_index] = max(0, offsets[page_index] - 1)
            elif key in (ord(" "), curses.KEY_NPAGE):
                offsets[page_index] = min(max_offset, offsets[page_index] + page_step)
            elif key in (ord("b"), curses.KEY_PPAGE):
                offsets[page_index] = max(0, offsets[page_index] - page_step)
            elif key == ord("m"):
                open_memo(stdscr)

    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
    finally:
        if tty:
            tty.close()


def main() -> None:
    date = parse_date(DATE_ARG)
    if MODE == "collect":
        print_daily_collect(date)
        return

    observance, psalms, first, second = find_readings(date)
    collects = load_collects()

    office_title = "Morning Prayer" if OFFICE == "morning" else "Evening Prayer"
    title = f"{office_title} - {date:%B} {date.day}, {date.year}"
    if not VIM_MODE:
        print(title)
        if observance:
            print(observance)
        print("=" * len(title))
        print()

    pages: list[tuple[str, str]] = []

    office_collect = collects.get("office", {}).get(OFFICE)
    if office_collect:
        collect_page = format_collect(office_collect.get("title", ""), office_collect.get("text", ""))
        pages.append((f"{title} - Collect", collect_page))
        if not VIM_MODE:
            print(collect_page)

    for psalm in psalms:
        page = format_passage("Psalm", psalm)
        pages.append((f"{title} - {psalm}", page))
        if not VIM_MODE:
            print(page)

    first_page = format_passage("First Lesson", first)
    second_page = format_passage("Second Lesson", second)
    pages.append((f"{title} - First Lesson", first_page))
    pages.append((f"{title} - Second Lesson", second_page))

    if VIM_MODE:
        vim_pager(
            pages,
            default_memo_path(),
            date,
            office_title,
            psalms,
            first,
            second,
        )
    else:
        print(first_page)
        print(second_page)


if __name__ == "__main__":
    main()
PY
