from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .errors import usage_error


@dataclass(frozen=True)
class Options:
    date_arg: str
    office: str
    mode: str
    collect_day: str
    common_key: str
    devotion_key: str
    vim_mode: bool
    compact_mode: bool
    csv_path: Path
    collects_path: Path


def default_data_dir() -> Path:
    configured = os.environ.get("BCP_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    package_data = Path(__file__).resolve().parent / "data"
    if package_data.exists():
        return package_data
    return Path(__file__).resolve().parent.parent


def parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        usage_error(f"Invalid date: {value!r}. Expected YYYY-MM-DD.")


def parse_options(argv: list[str] | None = None) -> Options:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    program = Path(sys.argv[0]).name or "bcp"
    if program == "__main__.py":
        program = "bcp"

    date_arg = datetime.now().strftime("%Y-%m-%d")
    office = "evening"
    mode = "readings"
    collect_day = ""
    common_key = ""
    devotion_key = ""
    vim_mode = False
    compact_mode = False

    args = []
    for arg in raw_args:
        if arg == "--vim":
            vim_mode = True
        elif arg == "--compact":
            compact_mode = True
        else:
            args.append(arg)

    if len(args) > 2:
        usage_error("", program)

    if len(args) == 1:
        if args[0] == "collect":
            mode = "collect"
        elif args[0] == "common":
            mode = "common"
        elif args[0] == "devotion":
            mode = "devotion"
        elif args[0] in {"note", "notes"}:
            mode = "note"
        elif args[0] in {"morning", "evening"}:
            office = args[0]
        else:
            date_arg = args[0]
    elif len(args) == 2:
        if args[0] == "collect":
            mode = "collect"
            collect_day = args[1]
        elif args[0] == "common":
            mode = "common"
            common_key = args[1]
        elif args[0] == "devotion":
            mode = "devotion"
            devotion_key = args[1]
        else:
            date_arg = args[0]
            office = args[1]

    if mode == "note" and vim_mode:
        usage_error("--vim is not supported for note|notes.", program)

    if mode == "readings" and office not in {"morning", "evening"}:
        usage_error("", program)

    date = parse_date(date_arg)
    month_slug = date.strftime("%B").lower()
    data_dir = default_data_dir()
    csv_path = Path(os.environ.get("BCP_CSV", data_dir / f"{month_slug}_{office}.csv"))
    collects_path = Path(os.environ.get("BCP_COLLECTS", data_dir / "collects.yaml"))

    return Options(
        date_arg=date_arg,
        office=office,
        mode=mode,
        collect_day=collect_day.lower(),
        common_key=common_key.lower(),
        devotion_key=devotion_key.lower(),
        vim_mode=vim_mode,
        compact_mode=compact_mode,
        csv_path=csv_path,
        collects_path=collects_path,
    )

