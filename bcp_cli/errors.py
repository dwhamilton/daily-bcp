from __future__ import annotations


def usage_text(program: str = "bcp") -> str:
    return (
        f"Usage: {program} readings [morning|evening] [-d|--date today|yesterday|tomorrow|YYYY-MM-DD] [--compact] [--vim]\n"
        f"       {program} collects [weekday|all] [--vim]\n"
        f"       {program} common [key|all] [--vim]\n"
        f"       {program} devotion [key|all] [--vim]\n"
        f"       {program} notes\n"
        f"       {program} history [--month YYYY-MM|mon]\n"
    )


def usage_error(message: str, program: str = "bcp") -> None:
    raise SystemExit(f"{message}\n{usage_text(program)}")


def runtime_error(message: str) -> None:
    raise SystemExit(message)


def first_use_text(program: str = "bcp") -> str:
    return (
        "daily-bcp reads Daily Office readings, collects, common prayers, and devotions.\n\n"
        "Try:\n"
        f"  {program} readings\n"
        f"  {program} readings morning\n"
        f"  {program} readings --date tomorrow\n"
        f"  {program} collects sat\n"
        f"  {program} history\n\n"
        f"Run `{program} --help` for all options."
    )
