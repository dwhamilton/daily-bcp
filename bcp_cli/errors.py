from __future__ import annotations


def usage_text(program: str = "bcp") -> str:
    return (
        f"Usage: {program} [YYYY-MM-DD] [morning|evening]\n"
        f"       {program} [morning|evening]\n"
        f"       {program} [--vim] [--compact] [YYYY-MM-DD] [morning|evening]\n"
        f"       {program} [--vim] collect [weekday|all]\n"
        f"       {program} [--vim] common [key|all]\n"
        f"       {program} [--vim] devotion [key|all]\n"
        f"       {program} note|notes"
    )


def usage_error(message: str, program: str = "bcp") -> None:
    raise SystemExit(f"{message}\n{usage_text(program)}")

