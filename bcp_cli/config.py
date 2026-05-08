from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .errors import first_use_text, usage_error, usage_text
from .notes import default_library_dir


@dataclass(frozen=True)
class Options:
    date_arg: str
    office: str
    mode: str
    collect_day: str
    common_key: str
    devotion_key: str
    library_key: str
    library_path: bool
    vim_mode: bool
    compact_mode: bool
    history_month: str
    history_verbose: bool
    csv_path: Path
    collects_path: Path
    library_dir: Path


def default_data_dir() -> Path:
    configured = os.environ.get("BCP_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    package_data = Path(__file__).resolve().parent / "data"
    if package_data.exists():
        return package_data
    return Path(__file__).resolve().parent.parent


def parse_date(value: str, now: datetime | None = None) -> datetime:
    base = now or datetime.now()
    normalized = value.lower()
    if normalized == "today":
        return base
    if normalized == "yesterday":
        return base - timedelta(days=1)
    if normalized == "tomorrow":
        return base + timedelta(days=1)
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        usage_error(f"Invalid date: {value!r}. Expected today, yesterday, tomorrow, or YYYY-MM-DD.")


def default_office(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return "morning" if current.hour < 12 else "evening"


def normalize_office(value: str, program: str = "bcp") -> str:
    offices = {
        "am": "morning",
        "morning": "morning",
        "pm": "evening",
        "evening": "evening",
    }
    if value not in offices:
        usage_error(f"Unknown office: {value!r}. Expected am, pm, morning, or evening.", program)
    return offices[value]


def parse_options(argv: list[str] | None = None, now: datetime | None = None) -> Options:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    program = "bcp" if argv is not None else Path(sys.argv[0]).name or "bcp"
    if program == "__main__.py":
        program = "bcp"

    if not raw_args:
        print(first_use_text(program))
        raise SystemExit(0)

    if raw_args in (["--help"], ["-h"]):
        print(usage_text(program))
        raise SystemExit(0)

    date_arg = (now or datetime.now()).strftime("%Y-%m-%d")
    office = default_office(now)
    mode = ""
    collect_day = ""
    common_key = ""
    devotion_key = ""
    library_key = ""
    library_path = False
    vim_mode = False
    compact_mode = False
    history_month = ""
    history_verbose = False
    date_provided = False
    month_provided = False
    verbose_provided = False

    args: list[str] = []
    index = 0
    while index < len(raw_args):
        arg = raw_args[index]
        if arg in {"--vim", "--pages"}:
            vim_mode = True
        elif arg in {"--date", "-d"}:
            index += 1
            if index >= len(raw_args):
                usage_error(f"{arg} requires a date value.", program)
            date_arg = raw_args[index]
            date_provided = True
        elif arg == "--compact":
            compact_mode = True
        elif arg == "--verbose":
            history_verbose = True
            verbose_provided = True
        elif arg == "--month":
            index += 1
            if index >= len(raw_args):
                usage_error(f"{arg} requires a month value.", program)
            history_month = raw_args[index]
            month_provided = True
        elif arg == "--path":
            library_path = True
        elif arg.startswith("-"):
            usage_error(f"Unknown option: {arg}", program)
        else:
            args.append(arg)
        index += 1

    if not args:
        usage_error("Missing command.", program)

    command = args[0]
    command_args = args[1:]
    reading_commands = {"daily", "psalm", "first-lesson", "second-lesson", "readings"}
    if command in reading_commands:
        mode = "daily" if command == "readings" else command.replace("-", "_")
        if len(command_args) > 1:
            usage_error(f"{command} accepts at most one office: am, pm, morning, or evening.", program)
        if command_args:
            office = normalize_office(command_args[0], program)
        if command == "psalm" and compact_mode:
            usage_error("--compact is not supported for psalm.", program)
    elif command == "collect":
        mode = "office_collect"
        if compact_mode:
            usage_error("--compact is not supported for collect.", program)
        if len(command_args) > 1:
            usage_error("collect accepts at most one office: am, pm, morning, or evening.", program)
        if command_args:
            office = normalize_office(command_args[0], program)
    elif command == "collects":
        mode = "collects"
        if date_provided:
            usage_error("--date is only supported for daily, psalm, first-lesson, second-lesson, collect, and readings.", program)
        if compact_mode:
            usage_error("--compact is only supported for daily, first-lesson, second-lesson, and readings.", program)
        if len(command_args) > 1:
            usage_error("collects accepts at most one weekday or all.", program)
        collect_day = command_args[0] if command_args else ""
    elif command == "common":
        mode = "common"
        if date_provided:
            usage_error("--date is only supported for daily, psalm, first-lesson, second-lesson, collect, and readings.", program)
        if compact_mode:
            usage_error("--compact is only supported for daily, first-lesson, second-lesson, and readings.", program)
        if len(command_args) > 1:
            usage_error("common accepts at most one key or all.", program)
        common_key = command_args[0] if command_args else ""
    elif command == "devotion":
        mode = "devotion"
        if date_provided:
            usage_error("--date is only supported for daily, psalm, first-lesson, second-lesson, collect, and readings.", program)
        if compact_mode:
            usage_error("--compact is only supported for daily, first-lesson, second-lesson, and readings.", program)
        if len(command_args) > 1:
            usage_error("devotion accepts at most one key or all.", program)
        devotion_key = command_args[0] if command_args else ""
    elif command == "library":
        mode = "library"
        if date_provided:
            usage_error("--date is only supported for daily, psalm, first-lesson, second-lesson, collect, and readings.", program)
        if compact_mode:
            usage_error("--compact is only supported for daily, first-lesson, second-lesson, and readings.", program)
        if library_path and vim_mode:
            usage_error("--pages is not supported for library --path.", program)
        if library_path and command_args:
            usage_error("library --path does not accept an item key.", program)
        if len(command_args) > 1:
            usage_error("library accepts at most one item key.", program)
        library_key = command_args[0] if command_args else ""
    elif command == "notes":
        mode = "note"
        if date_provided:
            usage_error("--date is only supported for daily, psalm, first-lesson, second-lesson, collect, and readings.", program)
        if vim_mode:
            usage_error("--pages is not supported for notes.", program)
        if compact_mode:
            usage_error("--compact is only supported for daily, first-lesson, second-lesson, and readings.", program)
        if command_args:
            usage_error("notes does not accept additional arguments.", program)
    elif command == "history":
        mode = "history"
        if date_provided:
            usage_error("--date is only supported for daily, psalm, first-lesson, second-lesson, collect, and readings.", program)
        if vim_mode:
            usage_error("--pages is not supported for history.", program)
        if compact_mode:
            usage_error("--compact is only supported for daily, first-lesson, second-lesson, and readings.", program)
        if command_args:
            usage_error("history does not accept additional arguments.", program)
    elif looks_like_date(command):
        usage_error(f"Dates now use --date/-d. Try `{program} daily --date {command}`.", program)
    else:
        usage_error(f"Unknown command: {command!r}.", program)

    if month_provided and mode != "history":
        usage_error("--month is only supported for history.", program)
    if verbose_provided and mode != "history":
        usage_error("--verbose is only supported for history.", program)
    if library_path and mode != "library":
        usage_error("--path is only supported for library.", program)

    date = parse_date(date_arg, now)
    date_arg = date.strftime("%Y-%m-%d")
    month_slug = date.strftime("%B").lower()
    data_dir = default_data_dir()
    csv_path = Path(os.environ.get("BCP_CSV", data_dir / f"{month_slug}_{office}.csv"))
    collects_path = Path(os.environ.get("BCP_COLLECTS", data_dir / "collects.yaml"))
    library_dir = default_library_dir()

    return Options(
        date_arg=date_arg,
        office=office,
        mode=mode,
        collect_day=collect_day.lower(),
        common_key=common_key.lower(),
        devotion_key=devotion_key.lower(),
        library_key=library_key,
        library_path=library_path,
        vim_mode=vim_mode,
        compact_mode=compact_mode,
        history_month=history_month,
        history_verbose=history_verbose,
        csv_path=csv_path,
        collects_path=collects_path,
        library_dir=library_dir,
    )


def looks_like_date(value: str) -> bool:
    return value in {"today", "yesterday", "tomorrow"} or bool(
        len(value) == 10
        and value[4] == "-"
        and value[7] == "-"
        and value[:4].isdigit()
        and value[5:7].isdigit()
        and value[8:].isdigit()
    )
