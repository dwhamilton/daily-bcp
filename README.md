# bcp-cli

`bcp-cli` is a terminal-first Daily Office reader for the ACNA 2019 Book of
Common Prayer lectionary. It gives you Morning Prayer or Evening Prayer
readings, KJV Bible text, collects, common prayers, devotions, a keyboard-driven
reader mode, and persistent Markdown notes.

It is built for deliberate, text-first use: open the office, read linearly, and
keep reflections in plain files you control.

## What It Does

- Reads Morning Prayer and Evening Prayer from local lectionary CSV files
- Fetches public-domain KJV Bible text from `bible-api.com`
- Prints the office collect before the readings
- Looks up weekday collects with `bcp collect`
- Lists and prints common prayers with `bcp common`
- Lists and prints personal devotions with `bcp devotion`
- Opens a persistent Markdown notes file with `bcp note`
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

There is not yet a published PyPI or Homebrew package. For now, install from a
clone.

```sh
git clone https://github.com/dwhamilton/bcp-cli.git
cd bcp-cli
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
bcp collect sat
bcp 2026-05-05 morning
```

When running directly from a clone without installing:

```sh
./bcp.sh
python3 -m bcp_cli
```

## Use

Read today's Evening Prayer:

```sh
bcp
```

Read today's Morning or Evening Prayer:

```sh
bcp morning
bcp evening
```

Read a specific date:

```sh
bcp 2026-05-05
bcp 2026-05-05 morning
bcp 2026-05-05 evening
```

Render lessons as wrapped paragraphs with inline verse markers:

```sh
bcp 2026-05-05 morning --compact
```

Psalms remain verse-broken in compact mode.

## Collects, Prayers, And Devotions

Read the weekday collect:

```sh
bcp collect
bcp collect saturday
bcp collect sat
bcp collect all
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

## Vim-Style Reader

Add `--vim` to read in a cleared, keyboard-driven terminal view:

```sh
bcp --vim
bcp --vim morning
bcp 2026-05-05 evening --vim
bcp 2026-05-05 morning --compact --vim
bcp collect all --vim
bcp common all --vim
bcp devotion all --vim
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
bcp note
bcp notes
```

In `--vim` mode, press `m` to open the same notes file. When reading an office,
`bcp-cli` creates one dated section for that date and office, and pressing `m`
again does not duplicate it.

The editor is chosen in this order:

1. `$VISUAL`
2. `$EDITOR`
3. `vi`

The notes file is chosen in this order:

1. `BCP_NOTES`
2. `BCP_MEMO`
3. `${XDG_STATE_HOME:-$HOME/.local/state}/bcp-cli/notes.md`

Example:

```sh
export BCP_NOTES="$HOME/notes/bcp.md"
bcp note
```

Notes are not removed when you uninstall the CLI.

## Configuration

Current configuration is environment-variable based:

- `BCP_NOTES`: path to the notes file
- `BCP_MEMO`: older alias for the notes file path
- `BCP_DATA_DIR`: directory containing bundled-style CSV/YAML data files
- `BCP_COLLECTS`: path to `collects.yaml`
- `BCP_CSV`: override the lectionary CSV for a run

## Uninstall

If installed with `pipx`:

```sh
pipx uninstall bcp-cli
```

If installed in a virtual environment, remove that environment.

Your notes file is stored separately and is not removed by uninstalling.

## Current Limits

- May and June lectionary data only
- Bible text requires internet access
- KJV is currently the only Bible translation
- No published package-manager install yet
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
