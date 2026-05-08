from __future__ import annotations


def usage_text(program: str = "bcp") -> str:
    return (
        f"Usage: {program} daily [am|pm] [-d|--date today|yesterday|tomorrow|YYYY-MM-DD] [--compact] [--pages]\n"
        f"       {program} psalm [am|pm] [-d|--date today|yesterday|tomorrow|YYYY-MM-DD] [--pages]\n"
        f"       {program} first-lesson [am|pm] [-d|--date today|yesterday|tomorrow|YYYY-MM-DD] [--compact] [--pages]\n"
        f"       {program} second-lesson [am|pm] [-d|--date today|yesterday|tomorrow|YYYY-MM-DD] [--compact] [--pages]\n"
        f"       {program} collect [am|pm] [-d|--date today|yesterday|tomorrow|YYYY-MM-DD] [--pages]\n"
        f"       {program} collects [weekday|all] [--pages]\n"
        f"       {program} common [key|all] [--pages]\n"
        f"       {program} devotion [key|all] [--pages]\n"
        f"       {program} library [item] [--pages]\n"
        f"       {program} library --path\n"
        f"       {program} notes\n"
        f"       {program} history [--month YYYY-MM|mon] [--verbose]\n"
        f"\nCompatibility aliases: readings for daily, --vim for --pages, morning for am, evening for pm.\n"
    )


def usage_error(message: str, program: str = "bcp") -> None:
    raise SystemExit(f"{message}\n{usage_text(program)}")


def runtime_error(message: str) -> None:
    raise SystemExit(message)


def first_use_text(program: str = "bcp") -> str:
    return (
        "daily-bcp reads Daily Office readings, collects, common prayers, and devotions.\n\n"
        "Try:\n"
        f"  {program} daily\n"
        f"  {program} daily am\n"
        f"  {program} psalm pm\n"
        f"  {program} collect\n"
        f"  {program} history\n"
        f"  {program} history --verbose\n\n"
        f"Run `{program} --help` for all options."
    )
