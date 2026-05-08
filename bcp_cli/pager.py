from __future__ import annotations

import os
import sys
import textwrap
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .errors import usage_error
from .notes import ensure_memo_file, ensure_memo_section, open_editor


def wrap_body_lines(body: str, width: int) -> list[str]:
    line_width = max(1, width)
    wrapped: list[str] = []
    for line in body.splitlines():
        if not line:
            wrapped.append("")
            continue
        wrapped.extend(
            textwrap.wrap(
                line,
                width=line_width,
                replace_whitespace=False,
            )
        )
    return wrapped


def vim_pager(
    pages: list[tuple[str, str]],
    memo_path: Path,
    office: str,
    date: datetime | None = None,
    office_title: str = "",
    psalms: list[str] | None = None,
    first: str = "",
    second: str = "",
    prepare_notes: Callable[[], None] | None = None,
) -> None:
    if not sys.stdout.isatty():
        usage_error("--pages requires an interactive terminal.")

    import curses

    tty = None
    try:
        tty = open("/dev/tty", "rb", buffering=0)
        os.dup2(tty.fileno(), sys.stdin.fileno())
    except OSError:
        usage_error("--pages could not read keyboard input from /dev/tty.")

    def draw_help(stdscr) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        lines = [
            "Help",
            "----",
            "h        previous section",
            "l        next section",
            "j        scroll down one line",
            "k        scroll up one line",
            "space    scroll down one screen",
            "b        scroll up one screen",
            "gg       jump to top",
            "G        jump to bottom",
            "m        make/open notes in editor",
            "?        toggle this help",
            "q        quit",
        ]
        for row, line in enumerate(lines[:height]):
            stdscr.addnstr(row, 0, line, max(0, width - 1))
        stdscr.refresh()

    def draw(stdscr, page_index: int, offset: int, show_help: bool) -> None:
        if show_help:
            draw_help(stdscr)
            return

        stdscr.erase()
        height, width = stdscr.getmaxyx()
        title, body = pages[page_index]
        body_lines = wrap_body_lines(body, max(1, width - 1))
        max_offset = max(0, len(body_lines) - max(1, height - 2))
        offset = min(offset, max_offset)

        header = f"{title} ({page_index + 1}/{len(pages)})"
        help_text = "h/l section  j/k scroll  m note  ? help  q quit"
        if width > 0:
            stdscr.addnstr(0, 0, " " * max(0, width - 1), max(0, width - 1), curses.A_REVERSE)
            if width > len(help_text) + 2:
                header_width = max(0, width - len(help_text) - 3)
                stdscr.addnstr(0, 0, header, header_width, curses.A_REVERSE)
                stdscr.addnstr(0, max(0, width - len(help_text) - 1), help_text, len(help_text), curses.A_REVERSE)
            else:
                stdscr.addnstr(0, 0, header, max(0, width - 1), curses.A_REVERSE)

        available = max(0, height - 2)
        for row, line in enumerate(body_lines[offset:offset + available], start=1):
            stdscr.addnstr(row, 0, line, max(0, width - 1))

        if max_offset:
            footer = f"line {offset + 1}-{min(len(body_lines), offset + available)} of {len(body_lines)}"
            stdscr.addnstr(height - 1, 0, footer, max(0, width - 1), curses.A_REVERSE)
        stdscr.refresh()

    def run(stdscr) -> None:
        curses.curs_set(0)
        page_index = 0
        offsets = [0 for _ in pages]
        show_help = False

        def open_memo(stdscr) -> None:
            if prepare_notes:
                prepare_notes()
            elif date and office_title and psalms is not None:
                ensure_memo_section(memo_path, date, office_title, office, psalms, first, second)
            else:
                ensure_memo_file(memo_path)
            curses.def_prog_mode()
            curses.endwin()
            try:
                open_editor(memo_path)
            finally:
                curses.reset_prog_mode()
                stdscr.clear()
                stdscr.refresh()

        while True:
            draw(stdscr, page_index, offsets[page_index], show_help)
            key = stdscr.getch()
            if key == ord("?"):
                show_help = not show_help
                continue
            if show_help:
                if key in (ord("q"), 27):
                    break
                show_help = False
                continue

            height, width = stdscr.getmaxyx()
            page_len = len(wrap_body_lines(pages[page_index][1], max(1, width - 1)))
            max_offset = max(0, page_len - max(1, height - 2))
            page_step = max(1, height - 3)

            if key in (ord("q"), 27):
                break
            if key == ord("l") and page_index < len(pages) - 1:
                page_index += 1
            elif key == ord("h") and page_index > 0:
                page_index -= 1
            elif key == ord("g"):
                stdscr.timeout(500)
                second_key = stdscr.getch()
                stdscr.timeout(-1)
                if second_key == ord("g"):
                    offsets[page_index] = 0
            elif key == ord("G"):
                offsets[page_index] = max_offset
            elif key == ord("j"):
                offsets[page_index] = min(max_offset, offsets[page_index] + 1)
            elif key == ord("k"):
                offsets[page_index] = max(0, offsets[page_index] - 1)
            elif key in (ord(" "), curses.KEY_NPAGE):
                offsets[page_index] = min(max_offset, offsets[page_index] + page_step)
            elif key in (ord("b"), curses.KEY_PPAGE):
                offsets[page_index] = max(0, offsets[page_index] - page_step)
            elif key == ord("m"):
                open_memo(stdscr)

    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
    finally:
        if tty:
            tty.close()
