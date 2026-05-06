from __future__ import annotations

import os
import shlex
import subprocess
from datetime import datetime
from pathlib import Path


def default_memo_path() -> Path:
    notes = os.environ.get("BCP_NOTES")
    if notes:
        return Path(notes).expanduser()

    configured = os.environ.get("BCP_MEMO")
    if configured:
        return Path(configured).expanduser()

    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return base / "bcp-cli" / "notes.md"


def ensure_memo_section(
    memo_path: Path,
    date: datetime,
    office_title: str,
    office: str,
    psalms: list[str],
    first: str,
    second: str,
) -> None:
    marker = f"<!-- bcp-cli:{date:%Y-%m-%d}:{office} -->"
    memo_path.parent.mkdir(parents=True, exist_ok=True)
    if not memo_path.exists():
        memo_path.write_text("# BCP Notes\n", encoding="utf-8")

    existing = memo_path.read_text(encoding="utf-8")
    if marker in existing:
        return

    section = [
        "",
        marker,
        f"## {date:%Y-%m-%d} - {office_title}",
        "",
        f"Psalms: {', '.join(psalms) if psalms else 'None'}",
        f"First Lesson: {first}",
        f"Second Lesson: {second}",
        "",
        "Notes:",
        "",
    ]
    with memo_path.open("a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write("\n".join(section))


def ensure_memo_file(memo_path: Path) -> None:
    memo_path.parent.mkdir(parents=True, exist_ok=True)
    if not memo_path.exists():
        memo_path.write_text("# BCP Notes\n", encoding="utf-8")


def editor_command() -> list[str]:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    return shlex.split(editor)


def open_editor(path: Path) -> None:
    command = editor_command() + [str(path)]
    try:
        with open("/dev/tty", "r+b", buffering=0) as tty:
            subprocess.run(command, stdin=tty, stdout=tty, stderr=tty, check=False)
    except OSError:
        subprocess.run(command, check=False)


def open_notes() -> None:
    memo_path = default_memo_path()
    ensure_memo_file(memo_path)
    open_editor(memo_path)

