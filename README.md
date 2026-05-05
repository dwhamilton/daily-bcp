# bcp-cli

A terminal-first prototype for reading the ACNA 2019 Daily Office lectionary.

`bcp-cli` reads local lectionary CSV files, finds the Morning or Evening Prayer
readings for a given date, fetches public-domain KJV Bible text from
`bible-api.com`, and prints the office in a terminal-friendly format. With no
arguments, it defaults to today's Evening Prayer.

This is currently a prototype shell script with embedded Python. The long-term
shape is likely a small installable Python CLI.

## Current State

Implemented:

- Morning Prayer and Evening Prayer readings
- May and June lectionary data
- public-domain KJV Bible text lookup through `bible-api.com`
- office collects before the readings
- weekday collect lookup as a separate command
- a `--vim` terminal reader mode
- memo support from `--vim` mode

Not yet implemented:

- full-year lectionary data
- offline Bible text
- packaged `pipx`, Homebrew, or npm install
- config file support
- robust test suite

## BCP Text and Use

My working understanding is that this tool is aimed at personal devotional use
and non-commercial experimentation.

The ACNA 2019 Book of Common Prayer copyright page says that, with the exception
of the New Coverdale Psalter, the content of the Book of Common Prayer (2019) is
not under copyright, and that not-for-profit reproduction by churches and
non-profit organizations is permitted. It also says the New Coverdale Psalter is
copyright 2019 by the Anglican Church in North America, but that this is not
intended to discourage use and duplication by churches for worship. For-profit
publication requests are directed to Anglican House Media.

Source: https://bcp2019.anglicanchurch.net/wp-content/uploads/2019/08/02-Copyright-Page.pdf

This project currently avoids reproducing the New Coverdale Psalter text by
fetching public-domain KJV Bible text instead. The local CSV files contain
lectionary references and short collect texts. This README is not legal advice.
Before publishing, distributing broadly, charging money, or bundling larger
portions of BCP text, the licensing/copyright position should be reviewed more
carefully.

## Requirements

- `bash`
- `python3`
- internet access for Bible text lookup
- an editor such as `vim`, `nvim`, `nano`, or another `$VISUAL`/`$EDITOR` for
  memo support

The script has no Python package dependencies.

## Quick Start

From the repo:

```sh
./bcp.sh
./bcp.sh morning
./bcp.sh evening
./bcp.sh 2026-05-05 morning
./bcp.sh 2026-06-24 evening
```

With no arguments:

```sh
./bcp.sh
```

is equivalent to today's Evening Prayer.

## Current Local Install

The simplest install today is to put this repo somewhere stable and symlink the
script into a directory on your `PATH`.

Example:

```sh
mkdir -p "$HOME/.local/bin"
ln -sf "$PWD/bcp.sh" "$HOME/.local/bin/bcp"
```

Then run:

```sh
bcp
bcp morning
bcp 2026-05-05 evening
```

Keep the CSV files and `collects.yaml` next to `bcp.sh`; the script currently
expects to find its data beside the script. A future install script should move
data into a standard location such as:

```text
~/.local/share/bcp-cli/
```

and teach the CLI to read from that installed data directory.

## Agent-Assisted Install

If you use Codex, Claude Code, or another terminal coding agent, you can give it
bounded install instructions instead of doing the manual steps yourself.

```text
Please install bcp-cli from this GitHub repository:

git@github.com:dwhamilton/bcp-cli.git

Goal:
Install bcp-cli so I can run it as `bcp` from my terminal.

Please do the following:
1. Clone the repository into a normal source directory such as ~/src/bcp-cli,
   unless it already exists.
2. Inspect the repository before changing anything.
3. Confirm that it contains:
   - bcp.sh
   - collects.yaml
   - *_morning.csv and *_evening.csv files
4. Create ~/.local/share/bcp-cli if it does not exist.
5. Copy bcp.sh, collects.yaml, and all *_morning.csv / *_evening.csv files into
   ~/.local/share/bcp-cli.
6. Make ~/.local/share/bcp-cli/bcp.sh executable.
7. Create ~/.local/bin if it does not exist.
8. Symlink ~/.local/share/bcp-cli/bcp.sh to ~/.local/bin/bcp.
9. If ~/.local/bin is not on my PATH, tell me the exact shell config line to
   add, but do not edit my shell config unless I explicitly approve.
10. Run these verification commands:
   - ~/.local/bin/bcp collect sat
   - ~/.local/bin/bcp 2026-05-05 morning
11. Report what changed and whether the install worked.

Do not delete or overwrite unrelated files. If a target file already exists, ask
before replacing it unless it is already part of this bcp-cli install.
```

Review any commands the agent asks to run before approving them. This section is
a convenience wrapper around the manual install steps, not a substitute for
understanding what is being installed.

## Commands

Read today's Evening Prayer:

```sh
./bcp.sh
```

Read today's Morning or Evening Prayer:

```sh
./bcp.sh morning
./bcp.sh evening
```

Read a specific date:

```sh
./bcp.sh 2026-05-05
./bcp.sh 2026-05-05 morning
./bcp.sh 2026-05-05 evening
```

Read the weekday collect:

```sh
./bcp.sh collect
./bcp.sh collect saturday
./bcp.sh collect sat
```

Short weekday names are supported, such as `sun`, `mon`, `tue`, `wed`, `thu`,
`fri`, and `sat`.

## Vim-Style Reader

Add `--vim` to Morning or Evening Prayer:

```sh
./bcp.sh --vim
./bcp.sh --vim morning
./bcp.sh 2026-05-05 evening --vim
```

Each element appears on its own cleared terminal page:

- office collect
- each psalm
- first lesson
- second lesson

Controls:

- `h` / `l`: previous / next section
- `j` / `k`: scroll one line
- Space / `b`: scroll one screen
- `gg` / `G`: top / bottom of the current section
- `m`: open memo file in your editor
- `?`: help
- `q`: quit

## Memos

In `--vim` mode, press `m` to open a persistent memo file.

The editor is chosen in this order:

1. `$VISUAL`
2. `$EDITOR`
3. `vi`

The memo file is chosen in this order:

1. `BCP_MEMO`
2. `${XDG_STATE_HOME:-$HOME/.local/state}/bcp-cli/memo.md`

Example:

```sh
export BCP_MEMO="$HOME/notes/bcp.md"
./bcp.sh --vim
```

When a memo is opened, the CLI ensures there is one section for the current date
and office. Pressing `m` repeatedly does not duplicate the section.

Example section:

```md
<!-- bcp-cli:2026-05-05:evening -->
## 2026-05-05 - Evening Prayer

Psalms: Psalm 10
First Lesson: Job 33
Second Lesson: 1 Peter 2:11-3:7

Notes:
```

## Data Files

Current lectionary files:

- `may_morning.csv`
- `may_evening.csv`
- `june_morning.csv`
- `june_evening.csv`

Monthly office CSV files use this schema:

```csv
day,observance,sixty_day_psalter_ep,first_lesson,second_lesson
```

The file naming convention is:

```text
<month>_<office>.csv
```

Examples:

```text
july_morning.csv
july_evening.csv
```

`collects.yaml` contains:

- office collects for Morning and Evening Prayer
- weekday collects used by `./bcp.sh collect`

## Configuration

Current configuration is environment-variable based:

- `BCP_MEMO`: path to the memo file
- `BCP_COLLECTS`: path to `collects.yaml`
- `BCP_CSV`: override the lectionary CSV for a run

Likely future config file:

```text
${XDG_CONFIG_HOME:-$HOME/.config}/bcp-cli/config.yaml
```

Possible config values:

```yaml
memo_file: /home/user/notes/bcp.md
data_dir: /home/user/.local/share/bcp-cli
bible_translation: kjv
```

## Future Development

Near-term:

- add remaining monthly CSVs
- add `BCP_DATA_DIR`
- add an `install.sh`
- add validation for all CSV files
- improve reference parsing and reduce hard-coded chapter-end data

Medium-term:

- split the embedded Python into modules
- package as a Python CLI
- support `pipx install`
- cache fetched Bible text for faster repeat/offline use
- add tests around reference normalization and CSV loading

Later:

- publish to PyPI
- add Homebrew formula
- consider a richer TUI with `prompt_toolkit` or `Textual`
- support additional Bible text sources
- support local/offline public-domain Bible text

## Development Notes

This repository is intentionally small while the workflow is still being
discovered. The shell script is a practical wrapper, but most of the real logic
is already Python. When the feature set stabilizes, the cleanest next step is to
turn that Python into a proper package and leave the shell script behind.
