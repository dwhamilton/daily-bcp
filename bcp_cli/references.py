from __future__ import annotations

import re

from .errors import usage_error

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
            usage_error(f"Cannot expand 'end' in {ref!r}; add its chapter length to bcp_cli/references.py.")
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
            usage_error(f"Cannot expand 'end' in {ref!r}; add its chapter length to bcp_cli/references.py.")
        return f"{book} {chapter}:{first_verse}-{last_verse}"

    return ref

