from __future__ import annotations

import calendar
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .errors import usage_error


HistoryData = dict[str, Any]


def default_history_path() -> Path:
    configured = os.environ.get("BCP_HISTORY")
    if configured:
        return Path(configured).expanduser()

    state_home = os.environ.get("XDG_STATE_HOME")
    if state_home:
        base = Path(state_home).expanduser()
    else:
        base = Path.home() / ".local" / "state"
    return base / "daily-bcp" / "history.json"


def empty_history() -> HistoryData:
    return {"version": 1, "days": {}}


def load_history(path: Path | None = None) -> HistoryData:
    history_path = path or default_history_path()
    if not history_path.exists():
        return empty_history()

    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        usage_error(f"Could not read history file {history_path}: invalid JSON at line {error.lineno}.")

    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("days"), dict):
        usage_error(f"Could not read history file {history_path}: expected version 1 history data.")

    return data


def save_history(data: HistoryData, path: Path | None = None) -> None:
    history_path = path or default_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def record_reading(
    office: str,
    reading_date: date,
    *,
    completed_at: datetime | None = None,
    path: Path | None = None,
) -> None:
    record_usage(
        "readings",
        office=office,
        reading_date=reading_date,
        completed_at=completed_at,
        path=path,
    )


def record_usage(
    activity: str,
    *,
    office: str = "",
    reading_date: date | None = None,
    completed_at: datetime | None = None,
    path: Path | None = None,
) -> None:
    completed = completed_at or datetime.now().astimezone()
    day_key = completed.date().isoformat()
    timestamp = completed.isoformat(timespec="seconds")

    data = load_history(path)
    days = data.setdefault("days", {})
    if not isinstance(days, dict):
        usage_error("Could not read history data: expected days to be an object.")

    day = days.setdefault(
        day_key,
        {
            "activities": [],
            "offices": [],
            "reading_dates": [],
            "first_completed_at": timestamp,
            "last_completed_at": timestamp,
        },
    )
    if not isinstance(day, dict):
        usage_error(f"Could not read history data: expected {day_key} to be an object.")

    activities = _list_field(day, "activities", day_key)
    if activity not in activities:
        activities.append(activity)

    if office:
        offices = _list_field(day, "offices", day_key)
        if office not in offices:
            offices.append(office)

    if reading_date:
        reading_key = reading_date.isoformat()
        reading_dates = _list_field(day, "reading_dates", day_key)
        if reading_key not in reading_dates:
            reading_dates.append(reading_key)

    day.setdefault("first_completed_at", timestamp)
    day["last_completed_at"] = timestamp
    save_history(data, path)


def _list_field(day: dict[str, Any], field: str, day_key: str) -> list[str]:
    value = day.setdefault(field, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        usage_error(f"Could not read history data: expected {day_key}.{field} to be a list of strings.")
    return value


MONTH_ABBREVIATIONS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def parse_history_month(value: str, today: date | None = None) -> tuple[int, int]:
    normalized = value.lower()
    current_day = today or date.today()

    if normalized in MONTH_ABBREVIATIONS:
        month_number = MONTH_ABBREVIATIONS[normalized]
        year = current_day.year
        if month_number > current_day.month:
            year -= 1
        return year, month_number

    if not (
        len(value) == 7
        and value[4] == "-"
        and value[:4].isdigit()
        and value[5:].isdigit()
    ):
        usage_error(f"Invalid month: {value!r}. Expected YYYY-MM or a three-letter month abbreviation.")
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError:
        usage_error(f"Invalid month: {value!r}. Expected YYYY-MM or a three-letter month abbreviation.")
    return parsed.year, parsed.month


def format_history(
    *,
    month: str = "",
    verbose: bool = False,
    today: date | None = None,
    path: Path | None = None,
) -> str:
    data = load_history(path)
    days = data["days"]

    current_day = today or date.today()
    if month:
        year, month_number = parse_history_month(month, current_day)
    else:
        year, month_number = current_day.year, current_day.month

    if not days:
        return "No history yet. Run bcp daily to start tracking."

    lines = [
        f"{calendar.month_name[month_number]} {year}",
        "",
        "Mon Tue Wed Thu Fri Sat Sun",
    ]

    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    elapsed_days = 0
    used_days = 0
    selected_month = (year, month_number)
    current_month = (current_day.year, current_day.month)

    for week in cal.monthdatescalendar(year, month_number):
        cells: list[str] = []
        for day in week:
            if day.month != month_number:
                cells.append(" ")
                continue

            day_key = day.isoformat()
            is_future = selected_month == current_month and day > current_day
            if is_future:
                cells.append(" ")
            elif day_key in days:
                cells.append("*")
                elapsed_days += 1
                used_days += 1
            else:
                cells.append("-")
                elapsed_days += 1
        lines.append(" ".join(f"{cell:^3}" for cell in cells).rstrip())

    lines.extend(
        [
            "",
            _summary_line(used_days, elapsed_days, selected_month, current_month),
            f"Current streak: {_current_streak(days, current_day)} days.",
            f"Last use: {_last_use(days)}.",
        ]
    )
    if verbose:
        lines.extend(_verbose_lines(days, year, month_number))
    return "\n".join(lines)


def _verbose_lines(days: dict[str, Any], year: int, month_number: int) -> list[str]:
    details = ["", "Details"]
    matching_days = [
        key
        for key in sorted(days)
        if _is_iso_day(key) and date.fromisoformat(key).year == year and date.fromisoformat(key).month == month_number
    ]
    if not matching_days:
        details.append("No tracked days in this month.")
        return details

    for day_key in matching_days:
        day = days[day_key]
        if not isinstance(day, dict):
            details.append(f"{day_key}: invalid history entry")
            continue
        details.append(f"{day_key}:")
        details.append(f"  activities: {_format_list(day.get('activities'))}")
        details.append(f"  offices: {_format_list(day.get('offices'))}")
        details.append(f"  reading_dates: {_format_list(day.get('reading_dates'))}")
        details.append(f"  first_completed_at: {day.get('first_completed_at', 'unknown')}")
        details.append(f"  last_completed_at: {day.get('last_completed_at', 'unknown')}")
    return details


def _format_list(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "-"
    return ", ".join(str(item) for item in value)


def _summary_line(
    used_days: int,
    elapsed_days: int,
    selected_month: tuple[int, int],
    current_month: tuple[int, int],
) -> str:
    suffix = " so far this month" if selected_month == current_month else " this month"
    return f"Used {used_days} of {elapsed_days} days{suffix}."


def _current_streak(days: dict[str, Any], today: date) -> int:
    streak = 0
    cursor = today
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _last_use(days: dict[str, Any]) -> str:
    day_keys = [key for key in days if _is_iso_day(key)]
    if not day_keys:
        return "never"
    return max(day_keys)


def _is_iso_day(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
