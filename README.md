# bcp-cli

Terminal-first Daily Office reader with vim-style navigation, KJV readings,
collects, and persistent Markdown notes.

`bcp-cli` is an opinionated command-line tool for reading the Daily Office from
the ACNA 2019 Book of Common Prayer lectionary. It is designed for users who
prefer deliberate, text-first workflows and want to pair structured reading with
durable reflection.

This is currently a prototype shell script with embedded Python. The long-term
shape is likely a small installable Python CLI.

## Features

- Daily Office readings from local ACNA 2019 lectionary CSV files
- Morning Prayer and Evening Prayer support
- public-domain KJV Bible text fetched from `bible-api.com`
- office collects before the readings
- weekday collect lookup as a separate command
- optional vim-style terminal reader
- persistent Markdown memo support from vim-style mode
- local-first design with no accounts or sync

## Philosophy

This tool is not optimized for speed or frictionless consumption. It is
optimized for:

- attention
- clarity
- deliberate engagement
- durable notes

It assumes:

- you are willing to read linearly
- you prefer keyboard-driven interaction
- you want reflections saved as plain text
- you value local files over accounts, dashboards, and sync layers

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

After install:

```sh
bcp
bcp morning
bcp evening
bcp 2026-05-05 morning
bcp 2026-06-24 evening
```

With no arguments:

```sh
bcp
```

is equivalent to today's Evening Prayer.

When developing from a clone, use `./bcp.sh` in place of `bcp`.

## Installation

There is no package-manager install yet. For now, install the script and data
files locally.

### Option 1: Agent-Assisted Install

If you use Codex, Claude Code, Cursor, or another terminal coding agent, you can
give it bounded install instructions instead of doing the manual steps yourself.

```text
Please install bcp-cli from this GitHub repository:

https://github.com/dwhamilton/bcp-cli.git

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

### Option 2: Manual Install

Clone the repo and install the script and data files:

```sh
git clone https://github.com/dwhamilton/bcp-cli.git
cd bcp-cli
mkdir -p "$HOME/.local/share/bcp-cli" "$HOME/.local/bin"
cp bcp.sh collects.yaml *_morning.csv *_evening.csv "$HOME/.local/share/bcp-cli/"
chmod +x "$HOME/.local/share/bcp-cli/bcp.sh"
ln -sf "$HOME/.local/share/bcp-cli/bcp.sh" "$HOME/.local/bin/bcp"
```

Make sure `~/.local/bin` is on your `PATH`.

Verify:

```sh
bcp collect sat
bcp 2026-05-05 morning
```

### Uninstall

```sh
rm -f "$HOME/.local/bin/bcp"
rm -rf "$HOME/.local/share/bcp-cli"
```

Memo files are stored separately and are not removed by the uninstall commands.
By default they live under:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/bcp-cli/
```

## Commands

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

Read the weekday collect:

```sh
bcp collect
bcp collect saturday
bcp collect sat
```

Short weekday names are supported, such as `sun`, `mon`, `tue`, `wed`, `thu`,
`fri`, and `sat`.

## Vim-Style Reader

Add `--vim` to Morning or Evening Prayer:

```sh
bcp --vim
bcp --vim morning
bcp 2026-05-05 evening --vim
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

In `--vim` mode, press `m` to open one persistent Markdown memo file.

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
bcp --vim
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
- weekday collects used by `bcp collect`

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

## Design Principles

- text-first
- local-first
- keyboard-driven
- durable Markdown outputs
- explicit, inspectable data files
- opinionated workflows over broad configuration

## Current Limitations

- partial lectionary coverage: May and June only
- Bash/Python hybrid implementation
- no offline Bible text cache
- minimal validation of CSV inputs
- no package-manager installation
- no config file yet

## Future CLI Shape

The current command surface is intentionally small. Future versions may grow
toward commands like:

```sh
bcp today
bcp read morning
bcp read 2026-05-05 evening
bcp note
bcp collect sat
```

These commands do not exist yet; they are listed here to make the direction
explicit without misrepresenting the current tool.

## Roadmap

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

## License

No license file has been added yet. MIT is a likely fit for the code.

The ACNA 2019 Book of Common Prayer text is not included in full. Users are
responsible for ensuring appropriate use of source materials.

## Why This Exists

Most tools optimize for doing more.

This tool is designed to help you pay attention to less, more deliberately.

## Development Notes

This repository is intentionally small while the workflow is still being
discovered. The shell script is a practical wrapper, but most of the real logic
is already Python. When the feature set stabilizes, the cleanest next step is to
turn that Python into a proper package and leave the shell script behind.
