# daily-bcp

`daily-bcp` is a terminal-first Daily Office reader for the ACNA 2019 Book of
Common Prayer lectionary. It gives you Morning Prayer or Evening Prayer
readings, KJV Bible text, collects, common prayers, devotions, a keyboard-driven
reader mode, persistent Markdown notes, and local readings history.

It is built for deliberate, text-first use: open the office, read linearly, and
keep reflections in plain files you control.

## What It Does

- Reads Morning Prayer and Evening Prayer from local lectionary CSV files
- Fetches public-domain KJV Bible text from `bible-api.com`
- Prints the office collect before the readings
- Looks up weekday collects with `bcp collects`
- Lists and prints common prayers with `bcp common`
- Lists and prints personal devotions with `bcp devotion`
- Lists and reads user-managed library YAML files with `bcp library`
- Opens a persistent Markdown notes file with `bcp notes`
- Shows local readings consistency history with `bcp history`
- Provides an optional vim-style reader with `--vim`
- Supports compact lesson formatting with `--compact`

Current lectionary coverage is May and June only.

## Requirements

- `python3`
- internet access for Bible text lookup
- an editor such as `vim`, `nvim`, `nano`, or another `$VISUAL`/`$EDITOR` for
  notes

The CLI has no Python package dependencies.

## Install

The package is not published to PyPI yet. For now, install from a clone:

```sh
pipx install git+https://github.com/dwhamilton/daily-bcp.git
```

After the first PyPI release is published, install with:

```sh
pipx install daily-bcp
```

For editable source-checkout use:

```sh
git clone https://github.com/dwhamilton/daily-bcp.git
cd daily-bcp
pipx install .
```

If you prefer a virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install .
```

Verify:

```sh
bcp collects sat
bcp readings morning --date 2026-05-05
```

When running directly from a clone without installing:

```sh
./bcp.sh
python3 -m bcp_cli
```

## Use

Show a short first-use prompt:

```sh
bcp
```

Read the current office. Before noon this defaults to Morning Prayer; at noon
or later this defaults to Evening Prayer:

```sh
bcp readings
```

Read today's Morning or Evening Prayer explicitly:

```sh
bcp readings morning
bcp readings evening
```

Read a specific date:

```sh
bcp readings --date 2026-05-05
bcp readings morning --date yesterday
bcp readings evening --date tomorrow
```

Render lessons as wrapped paragraphs with inline verse markers:

```sh
bcp readings morning --date 2026-05-05 --compact
```

Psalms remain verse-broken in compact mode.

## History

Show a calendar-style view of reading consistency for the current month:

```sh
bcp history
```

Show a specific month:

```sh
bcp history --month 2026-05
bcp history --month may
bcp history --month dec
```

Only successful `bcp readings` runs are tracked. The history date is the local
day you ran the command, not the lectionary date requested with `--date`.

## Collects, Prayers, And Devotions

Read the weekday collect:

```sh
bcp collects
bcp collects saturday
bcp collects sat
bcp collects all
```

List common prayers:

```sh
bcp common
```

Print a common prayer:

```sh
bcp common lords-prayer
bcp common apostles-creed
bcp common nicene-creed
bcp common confession
bcp common all
```

List personal devotions:

```sh
bcp devotion
```

Print a devotion:

```sh
bcp devotion peace
bcp devotion daily-growth
bcp devotion wesley
bcp devotion all
```

## Library

Store personal readings as YAML files in a `library/` folder beside your notes
file, or set `BCP_LIBRARY_DIR` to another folder.

On first use, `daily-bcp` creates the folder if needed and adds a bundled
`sample.yaml` file when that filename does not already exist.

List library items:

```sh
bcp library
```

Show only the library folder path:

```sh
bcp library --path
```

Read one item:

```sh
bcp library item1
bcp library item1 --vim
bcp library sample
```

The filename stem is the command key, so `item1.yaml` is read with
`bcp library item1`. Each file uses this shape:

```yaml
title: Item Title
readings:
  first:
    title: First Reading
    text: |
      Reading text here.

  second:
    title: Second Reading
    text: |
      Another reading here.
```

## Vim-Style Reader

Add `--vim` to read in a cleared, keyboard-driven terminal view:

```sh
bcp readings --vim
bcp readings morning --vim
bcp readings evening --date 2026-05-05 --vim
bcp readings morning --date 2026-05-05 --compact --vim
bcp collects all --vim
bcp common all --vim
bcp devotion all --vim
bcp library item1 --vim
```

Controls:

- `h` / `l`: previous / next section
- `j` / `k`: scroll one line
- Space / `b`: scroll one screen
- `gg` / `G`: top / bottom of the current section
- `m`: make/open notes in your editor
- `?`: help
- `q`: quit

## Notes

Open the notes file:

```sh
bcp notes
```

In `--vim` mode, press `m` to open the same notes file. When reading an office,
`daily-bcp` creates one dated section for that date and office, and pressing `m`
again does not duplicate it.

Library readings use a separate notes file at `<library folder>/notes.md`.

The editor is chosen in this order:

1. `$VISUAL`
2. `$EDITOR`
3. `vi`

The notes file is chosen in this order:

1. `BCP_NOTES`
2. `BCP_MEMO`
3. `${XDG_STATE_HOME:-$HOME/.local/state}/daily-bcp/notes.md`

Example:

```sh
export BCP_NOTES="$HOME/notes/bcp.md"
bcp notes
```

Notes are not removed when you uninstall the CLI.

## Configuration

Current configuration is environment-variable based:

- `BCP_NOTES`: path to the notes file
- `BCP_MEMO`: older alias for the notes file path
- `BCP_DATA_DIR`: directory containing bundled-style CSV/YAML data files
- `BCP_COLLECTS`: path to `collects.yaml`
- `BCP_CSV`: override the lectionary CSV for a run
- `BCP_HISTORY`: path to the readings history JSON file
- `BCP_LIBRARY_DIR`: path to the library readings folder

By default, history is stored at
`${XDG_STATE_HOME:-$HOME/.local/state}/daily-bcp/history.json`.

## Uninstall

If installed with `pipx`:

```sh
pipx uninstall daily-bcp
```

If installed in a virtual environment, remove that environment.

Your notes file is stored separately and is not removed by uninstalling.

## Current Limits

- May and June lectionary data only
- Bible text requires internet access
- KJV is currently the only Bible translation
- Minimal validation of custom data files

## BCP Text And Use

This project currently avoids reproducing the New Coverdale Psalter text by
fetching public-domain KJV Bible text instead. The local data files contain
lectionary references and short collect, prayer, and devotion texts.

This README is not legal advice. Before publishing, distributing broadly,
charging money, or bundling larger portions of BCP text, the licensing and
copyright position should be reviewed carefully.

## Development

Developer notes, project structure, data format details, and possible future
directions live in [docs/development.md](docs/development.md).
