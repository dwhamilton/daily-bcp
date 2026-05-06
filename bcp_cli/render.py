from __future__ import annotations

import textwrap

from .bible_api import fetch_passage
from .errors import usage_error

WRAP_WIDTH = 78


def format_collect(title: str, text: str) -> str:
    heading = title or "A Collect"
    body = textwrap.fill(" ".join(text.split()), width=WRAP_WIDTH)
    return f"{heading}\n{'-' * len(heading)}\n{body}\n"


def format_prayer(title: str, text: str) -> str:
    heading = title or "A Prayer"
    body = text.strip()
    return f"{heading}\n{'-' * len(heading)}\n{body}\n"


def format_passage(label: str, ref: str, compact_mode: bool = False) -> str:
    data = fetch_passage(ref)
    verses = data.get("verses", [])
    if not verses:
        usage_error(f"No verses returned for {ref!r}.")

    lines = [label, ref, "-" * len(ref)]
    current_chapter = None
    paragraph_parts: list[str] = []
    for verse in verses:
        chapter = verse["chapter"]
        if chapter != current_chapter:
            if paragraph_parts:
                lines.append(textwrap.fill(" ".join(paragraph_parts), width=WRAP_WIDTH))
                paragraph_parts = []
            current_chapter = chapter
            lines.extend(["", f"{verse['book_name']} {chapter}"])
        text = " ".join(verse["text"].split())
        if compact_mode and label != "Psalm":
            paragraph_parts.append(f"[{verse['verse']}] {text}")
            continue
        wrapped = textwrap.fill(
            f"{verse['verse']}. {text}",
            width=WRAP_WIDTH,
            subsequent_indent="    ",
        )
        lines.append(wrapped)
    if paragraph_parts:
        lines.append(textwrap.fill(" ".join(paragraph_parts), width=WRAP_WIDTH))
    return "\n".join(lines) + "\n"

