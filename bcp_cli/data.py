from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .errors import usage_error
from .references import normalize_reference


def psalm_references(value: str) -> list[str]:
    refs = []
    for piece in value.split(","):
        piece = piece.strip()
        if piece:
            refs.append(f"Psalm {piece}")
    return refs


def find_readings(date: datetime, csv_path: Path) -> tuple[str, list[str], str, str]:
    if not csv_path.exists():
        usage_error(f"Could not find CSV file: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8") as handle:
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
                f"{csv_path.name} is not in the expected CSV format. "
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


def load_collects(collects_path: Path) -> dict[str, dict[str, dict[str, str]]]:
    if not collects_path.exists():
        return {}

    collects: dict[str, dict[str, dict[str, str]]] = {}
    section = ""
    key = ""
    field = ""

    for raw_line in collects_path.read_text(encoding="utf-8").splitlines():
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

