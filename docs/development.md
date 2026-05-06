# Development Notes

This document explains the current shape of `bcp-cli`, the tradeoffs behind it,
and the likely direction for future work. The README is intentionally focused on
users.

## Project Shape

`bcp-cli` is a small Python CLI package with bundled data files and a thin shell
wrapper for source-checkout use.

```text
bcp.sh
pyproject.toml
bcp_cli/
  __main__.py
  bible_api.py
  cli.py
  config.py
  data.py
  errors.py
  notes.py
  pager.py
  prayers.py
  references.py
  render.py
  data/
    collects.yaml
    may_morning.csv
    may_evening.csv
    june_morning.csv
    june_evening.csv
tests/
  test_cli.py
```

The package has no runtime dependencies outside the Python standard library.

## Module Responsibilities

- `bcp_cli/cli.py`: command dispatch and Daily Office assembly
- `bcp_cli/config.py`: argument parsing, date parsing, data path resolution
- `bcp_cli/data.py`: CSV reading and the current lightweight YAML reader
- `bcp_cli/references.py`: lectionary reference normalization
- `bcp_cli/bible_api.py`: KJV text lookup through `bible-api.com`
- `bcp_cli/render.py`: collect, prayer, and passage formatting
- `bcp_cli/prayers.py`: collect, common prayer, and devotion commands
- `bcp_cli/notes.py`: notes path selection, note-section creation, editor launch
- `bcp_cli/pager.py`: vim-style curses reader
- `bcp_cli/errors.py`: usage text and command-line errors

`bcp.sh` should stay small. It exists so a user can run `./bcp.sh` from a clone
without installing the package. Application logic belongs in Python modules.

## Packaging

`pyproject.toml` defines a normal console script:

```toml
[project.scripts]
bcp = "bcp_cli.cli:main"
```

Bundled CSV and YAML files are included as package data:

```toml
[tool.setuptools.package-data]
bcp_cli = ["data/*.csv", "data/*.yaml"]
```

The intended install path is eventually:

```sh
pipx install bcp-cli
```

Until the package is published, install from a clone:

```sh
pipx install .
```

## Data Files

Monthly office CSV files live under `bcp_cli/data/` and use this schema:

```csv
day,observance,sixty_day_psalter_ep,first_lesson,second_lesson
```

The file naming convention is:

```text
<month>_<office>.csv
```

Examples:

```text
may_morning.csv
may_evening.csv
june_morning.csv
june_evening.csv
```

`collects.yaml` contains:

- office collects for Morning and Evening Prayer
- weekday collects used by `bcp collect`
- common prayers used by `bcp common`
- personal devotions used by `bcp devotion`

The current YAML reader in `data.py` is intentionally narrow. It supports the
specific file shape currently used by `collects.yaml`; it is not a general YAML
parser.

## Configuration

Configuration is environment-variable based:

- `BCP_NOTES`: path to the notes file
- `BCP_MEMO`: older alias for the notes file path
- `BCP_DATA_DIR`: directory containing bundled-style CSV/YAML data files
- `BCP_COLLECTS`: path to `collects.yaml`
- `BCP_CSV`: override the lectionary CSV for a run

A future config file would likely live at:

```text
${XDG_CONFIG_HOME:-$HOME/.config}/bcp-cli/config.yaml
```

Possible values:

```yaml
memo_file: /home/user/notes/bcp.md
data_dir: /home/user/.local/share/bcp-cli
bible_translation: kjv
```

## Architectural Tradeoffs

The original implementation was a Bash script with embedded Python. That was
useful while the command shape was fluid, but it made testing, importing, and
packaging harder. The current package structure keeps the same behavior while
making the code easier to test and evolve.

The project still favors a small standard-library implementation. That keeps
installation simple, but it has consequences:

- The custom YAML reader should either remain tightly scoped or be replaced
  with a real parser if the data format becomes more complex.
- The curses reader is portable enough for Unix-like terminals, but richer TUI
  behavior may eventually justify `prompt_toolkit` or `Textual`.
- Bible text lookup is network-only. Caching or offline text will require a
  data-source decision.
- Reference normalization still has hard-coded chapter-end data for readings
  that use `end`.

## Testing

Run the current tests with:

```sh
python3 -m unittest discover -s tests
```

The current suite covers:

- argument parsing
- command option selection
- reference normalization
- collect loading
- lectionary CSV lookup

Good next tests would cover:

- error messages for invalid dates, offices, and weekdays
- compact passage rendering with mocked Bible API responses
- note-section idempotency
- CSV validation across all bundled data files
- behavior when data files are missing

## Current Limitations

- May and June lectionary coverage only
- KJV only
- network-only Bible text lookup
- no offline Bible cache
- no published PyPI or Homebrew package
- minimal validation for bundled data files
- no full config file support

## Roadmap

Near-term:

- add remaining monthly CSVs
- validate all bundled CSV files in tests
- improve reference parsing and reduce hard-coded chapter-end data
- add tests around notes and rendering
- add a simple release checklist

Medium-term:

- publish to PyPI for `pipx install bcp-cli`
- cache fetched Bible text for faster repeat/offline use
- add a config file
- support user-provided data directories more formally
- improve terminal reader behavior and error recovery

Later:

- add Homebrew formula
- consider a richer TUI with `prompt_toolkit` or `Textual`
- support additional Bible text sources
- support local/offline public-domain Bible text
- revisit command shape, possibly adding commands such as:

```sh
bcp today
bcp read morning
bcp read 2026-05-05 evening
```

## Copyright And Source Text

This project currently avoids reproducing the New Coverdale Psalter text by
fetching public-domain KJV Bible text instead. The bundled data files contain
lectionary references and short collect, prayer, and devotion texts.

Before publishing broadly, charging money, or bundling larger portions of BCP
text, the licensing and copyright position should be reviewed carefully. In
particular, contributors should avoid adding copyrighted source text unless its
use is clearly permitted for this project.

