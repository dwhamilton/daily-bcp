from __future__ import annotations

from datetime import datetime

from .config import Options
from .data import load_collects
from .errors import usage_error
from .notes import default_memo_path
from .pager import vim_pager
from .render import format_collect, format_prayer


def show_pages(pages: list[tuple[str, str]], options: Options) -> None:
    if options.vim_mode:
        vim_pager(pages, default_memo_path(), options.office)
        return
    for _, body in pages:
        print(body)


def normalize_common_key(value: str) -> str:
    aliases = {
        "lord": "lords_prayer",
        "lords": "lords_prayer",
        "lord-prayer": "lords_prayer",
        "lords-prayer": "lords_prayer",
        "lords_prayer": "lords_prayer",
        "our-father": "lords_prayer",
        "our_father": "lords_prayer",
        "apostle": "apostles_creed",
        "apostles": "apostles_creed",
        "apostles-creed": "apostles_creed",
        "apostles_creed": "apostles_creed",
        "nicene": "nicene_creed",
        "nicene-creed": "nicene_creed",
        "nicene_creed": "nicene_creed",
        "agnus": "agnus_dei",
        "agnus-dei": "agnus_dei",
        "agnus_dei": "agnus_dei",
        "purity": "collect_for_purity",
        "collect-purity": "collect_for_purity",
        "collect-for-purity": "collect_for_purity",
        "collect_for_purity": "collect_for_purity",
        "night": "at_night",
        "at-night": "at_night",
        "at_night": "at_night",
        "present": "be_present",
        "be-present": "be_present",
        "be_present": "be_present",
        "sleep": "for_sleep",
        "for-sleep": "for_sleep",
        "for_sleep": "for_sleep",
        "confess": "confession",
        "confession": "confession",
    }
    return aliases.get(value, value.replace("-", "_"))


def print_common_prayers(options: Options) -> None:
    collects = load_collects(options.collects_path)
    common = collects.get("common_prayers", {})
    if not common:
        usage_error("No common prayers found.")

    if options.common_key == "all":
        pages = []
        for key, prayer in common.items():
            title = prayer.get("title", key)
            pages.append((title, format_prayer(title, prayer.get("text", ""))))
        show_pages(pages, options)
        return

    if options.common_key:
        key = normalize_common_key(options.common_key)
        prayer = common.get(key)
        if not prayer:
            available = ", ".join(sorted(common.keys()))
            usage_error(f"No common prayer found for {options.common_key!r}. Available: {available}")
        print(format_prayer(prayer.get("title", key), prayer.get("text", "")))
        return

    print("Common Prayers")
    print("--------------")
    for key, prayer in common.items():
        title = prayer.get("title", "")
        print(f"{key}: {title}")
    print()


def normalize_devotion_key(value: str) -> str:
    aliases = {
        "peace": "participation",
        "francis": "participation",
        "participation": "participation",
        "daily": "daily_growth",
        "growth": "daily_growth",
        "daily-growth": "daily_growth",
        "richard": "daily_growth",
        "seeking": "seeking_god",
        "seeking-god": "seeking_god",
        "anselm": "seeking_god",
        "seek": "grace_to_seek",
        "grace": "grace_to_seek",
        "grace-to-seek": "grace_to_seek",
        "benedict": "grace_to_seek",
        "submission": "submission",
        "will": "submission",
        "mercier": "submission",
        "satisfaction": "satisfaction",
        "christ": "satisfaction",
        "julian": "satisfaction",
        "covenant": "covenant_prayer",
        "wesley": "covenant_prayer",
        "heart": "virtuous",
        "virtuous": "virtuous",
        "aquinas": "virtuous",
        "union": "union",
        "anima": "union",
        "anima-christi": "union",
    }
    return aliases.get(value, value.replace("-", "_"))


def print_devotion(options: Options) -> None:
    collects = load_collects(options.collects_path)
    devotions = collects.get("devotions", {})
    if not devotions:
        usage_error("No devotions found.")

    if options.devotion_key == "all":
        pages = []
        for key, devotion in devotions.items():
            title = devotion.get("title", key)
            author = devotion.get("author", "")
            heading = f"{title} - {author}" if author else title
            pages.append((title, format_prayer(heading, devotion.get("text", ""))))
        show_pages(pages, options)
        return

    if options.devotion_key:
        key = normalize_devotion_key(options.devotion_key)
        devotion = devotions.get(key)
        if not devotion:
            available = ", ".join(sorted(devotions.keys()))
            usage_error(f"No devotion found for {options.devotion_key!r}. Available: {available}")
        title = devotion.get("title", key)
        author = devotion.get("author", "")
        heading = f"{title} - {author}" if author else title
        print(format_prayer(heading, devotion.get("text", "")))
        return

    print("Devotions")
    print("---------")
    for key, devotion in devotions.items():
        title = devotion.get("title", "")
        author = devotion.get("author", "")
        suffix = f" - {author}" if author else ""
        print(f"{key}: {title}{suffix}")
    print()


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


def print_daily_collect(date: datetime, options: Options) -> None:
    collects = load_collects(options.collects_path)
    if options.collect_day == "all":
        daily = collects.get("daily", {})
        order = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        pages = []
        for weekday in order:
            collect = daily.get(weekday)
            if not collect:
                continue
            title = collect.get("title", "")
            weekday_title = weekday.title()
            heading = f"{title} - {weekday_title}" if title else weekday_title
            pages.append((weekday_title, format_collect(heading, collect.get("text", ""))))
        if not pages:
            usage_error("No daily collects found.")
        show_pages(pages, options)
        return

    weekday = normalize_weekday(options.collect_day, date)
    daily_collect = collects.get("daily", {}).get(weekday)
    if not daily_collect:
        usage_error(f"No collect found for {weekday}.")

    title = daily_collect.get("title", "")
    weekday_title = weekday.title()
    heading = f"{title} - {weekday_title}" if title else weekday_title
    print(format_collect(heading, daily_collect.get("text", "")))

