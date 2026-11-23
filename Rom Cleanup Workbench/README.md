# Rom Cleanup Workbench

**English** · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md)

**User guide with screenshots:** [PDF](<docs/Rom Cleanup Workbench - User Guide.pdf>) · [Word](<docs/Rom Cleanup Workbench - User Guide.docx>)

**Video:** [how the program works (YouTube)](https://youtu.be/D1yXZQXg-iM)

Finds duplicate ROM files in a directory by game name and deletes them on request.
Requires Python 3.10 or newer. The window needs no additional packages; the terminal version for Linux needs Textual (see [Terminal version (Linux)](#terminal-version-linux)).
The program speaks English, German, Italian, Spanish, French and Japanese (see [Language](#language)).

**Important:** Do not use this program on your original ROM files. Make a copy of your ROM repository and use the program to clean up only that copy.

## Installation

### Windows

1. **Install Python:** Download Python 3.10 or newer from [python.org/downloads](https://www.python.org/downloads/) and install it. If the installer offers "Add python.exe to PATH", tick that option. `tkinter` for the window comes with it. Then check in a new terminal:

   ```powershell
   python --version
   ```

2. **Download the program:** Without Git, the easiest way is a ZIP file. Either in the browser: on the [GitHub page](https://github.com/arved9926/rom-cleanup-workbench), choose the green button **Code** and then **Download ZIP**, right-click the file `rom-cleanup-workbench-main.zip` in Explorer, choose **Extract All...** and rename the extracted folder `rom-cleanup-workbench-main` to `rom-cleanup-workbench`. Or the same in PowerShell:

   ```powershell
   Invoke-WebRequest https://github.com/arved9926/rom-cleanup-workbench/archive/refs/heads/main.zip -OutFile rom-cleanup-workbench.zip
   Expand-Archive rom-cleanup-workbench.zip -DestinationPath .
   Rename-Item rom-cleanup-workbench-main rom-cleanup-workbench
   cd "rom-cleanup-workbench\Rom Cleanup Workbench"
   ```

   If you have Git installed, you can clone the repository instead:

   ```powershell
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   cd "rom-cleanup-workbench\Rom Cleanup Workbench"
   ```

   The program is in the folder `Rom Cleanup Workbench`. The window needs no further packages. Only if you want the terminal version on Windows, also install Textual:

   ```powershell
   python -m pip install textual==8.2.8
   ```

### Linux

1. **Install Python:** Python 3 is usually there already (`python3 --version`). Otherwise, on Debian or Ubuntu:

   ```bash
   sudo apt install python3 python3-venv wget unzip
   ```

   The package `python3-tk` is only needed if you want the window instead of the terminal version on Linux with a graphical display.

2. **Download the program:** Without Git, download it from GitHub as a ZIP file and unpack it:

   ```bash
   wget https://github.com/arved9926/rom-cleanup-workbench/archive/refs/heads/main.zip -O rom-cleanup-workbench.zip
   unzip rom-cleanup-workbench.zip
   mv rom-cleanup-workbench-main rom-cleanup-workbench
   ```

   If you have Git installed (`sudo apt install git`), you can clone the repository instead:

   ```bash
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   ```

3. **Install Textual in a virtual environment:**

   ```bash
   cd "rom-cleanup-workbench/Rom Cleanup Workbench"
   python3 -m venv ~/venvs/rom-cleanup-workbench
   ~/venvs/rom-cleanup-workbench/bin/pip install textual==8.2.8
   ```

## Usage

### Windows

Open a terminal (for example PowerShell) in the folder `Rom Cleanup Workbench` and start the program with the folder of your games:

```powershell
cd "rom-cleanup-workbench\Rom Cleanup Workbench"
python rom_cleanup_workbench.py "D:\Games"
```

Without a folder, the window asks for it. If you want the terminal version, add `--tui`.

### Linux

Change to the folder `Rom Cleanup Workbench` and start the program with the Python of the virtual environment and the folder of your games:

```bash
cd "rom-cleanup-workbench/Rom Cleanup Workbench"
~/venvs/rom-cleanup-workbench/bin/python rom_cleanup_workbench.py ~/roms
```

Without a graphical display, for example over SSH, the terminal version starts by itself. With a graphical display, the window opens (this needs `python3-tk`); with `--tui`, the terminal version starts anyway. More under [Terminal version (Linux)](#terminal-version-linux).

### What happens then

The program opens the analysis window and shows everything there; it prints nothing in the terminal and asks nothing there. Questions, messages and the folder choice also appear inside the window, in the language of the program, never as Windows popups; Enter chooses the preselected button and Esc answers No. Without a directory, the window asks for the folder. Files are only deleted after the confirmation in the window. **Deleted files do not go to the Recycle Bin.**

| Option | Effect |
| --- | --- |
| `--review all` | open the window with `All deletion marks` for this start |
| `--review problems` | open the window with `Problematic deletion marks` for this start |
| `--priority USA Europe Japan none` | set the priority for this run |
| `--delete-tag Hack Hacks Proto` | set the delete keywords for this run |
| `--config file.json` | use a different configuration |
| `--report-only` | without window: only print the report in the terminal |
| `--yes` | without window: delete marked files without asking |
| `--all` | with `--report-only`: also show games without marked files |
| `--tui` | use the terminal version instead of the window (automatic on Linux without a graphical display) |
| `--ascii` | terminal version with ASCII characters only (automatic on the Linux console); implies `--tui` |

The command line options and their help (`--help`) are always in English.

The tests run with `python -m unittest`.

## Analysis window

Since the ZIP files have to be unpacked to get the size, SHA-256 checksum and name of their contents, it can take a moment after choosing a directory until the results are shown.

The green row at the top says `Rom Cleanup Workbench` on the left and names the folder on the right; below it the window names the active priority with its source. The green second-to-last row shows the status, during the analysis for example `Analyzing: 120 of 2007 files`. A progress bar also appears in the middle during that time. The window also shows errors, for example in the configuration, and nothing can be deleted as long as the analysis fails. While deleting, the progress bar appears in the middle and the green row shows for example `Deleting: 120 of 500 files`; the window accepts no input until the deletion is finished. After deleting, it reports the result and removes the deleted files from the list without analyzing the folder again; files that could not be deleted stay marked. `F5` analyzes the folder again when you want that.

If nothing is marked in the whole folder and no file is suspected to be a status or save file, `Nothing to do.` blinks in the middle of the window.

The three radio buttons determine what the list shows:

- `Problematic deletion marks`: only games with a marked file that count as problematic (default on first start)
- `All deletion marks`: all games with a marked file
- `All ROM files`: all games. Their files can then also be marked with `x`, and problematic cases without a marked file, such as an unreadable ZIP, appear too.

The window remembers the most recently chosen view and the confirmed status or save files (rule 9) in `rom_cleanup_workbench_settings.json` next to the program.

| Key | Effect |
| --- | --- |
| Arrow keys | select a row, with Shift several (for example all discs of a game) |
| `Tab` / `Shift+Tab` | go to the next / previous game; the first file of the game is selected |
| `x` | mark the file for deletion; it moves to the end of its game |
| `k` | keep the file; it moves to the position the rules give it |
| `1` `2` `3` | the views `Problematic deletion marks`, `All deletion marks`, `All ROM files` |
| `Ctrl` + mouse wheel | enlarge or shrink the font (8 to 32 pt, applies until the window is closed) |
| `s` | same as the button `Settings...`: show or hide the settings for language, priority, delete keywords and ZIP or plain file (see [Settings](#settings)) |
| `/` | go to the filter field |
| `Enter` | same as the button `Proceed...`: delete after a confirmation, remove the number in front of the kept file names (rule 10) and confirm the suspected status or save files (rule 9) |
| `f` | choose another folder, inside the window in place of the list: open folders with the arrow, choose one at once with a double click, or type a path into `Path`, then `Select` or `Enter`; `Cancel` or `Esc` keep the current folder |
| `r` or `F5` | analyze again, also reads the configuration again |
| `c` or `F1` | show the credits |
| `q` or `Esc` | close without deleting anything; after changes by hand the program asks first |

Horizontal lines separate the games, and every second game has a dark gray background. The column `Size` shows the size of every file in KB, rounded up as in Windows Explorer (`1,234 KB`); `?` means the size could not be read. The size is read during the analysis. Kept files are shown in bold green under `Keep:`, files to be deleted in red under `Marked for deletion`. The window shows white text in Lucida Sans Typewriter 11 pt on a black background. If the font is not installed, Windows silently picks a substitute. Files moved by hand have a brown background and carry the note `By hand`; while the row is selected, it appears blue. The program's notes stay unchanged, even if they refer to a file you have moved.

`Problematic deletion marks` hides the unproblematic games. **Their marked files are still deleted when you delete**; the confirmation states their number. Games you have changed by hand always stay visible, unless the filter hides them.

### Filter

The filter field on the left of the bottom row narrows the current view to games with a file name that contains the pattern. A game stays complete if one of its files matches. The list updates shortly after typing; the file contents are not read.

- `*` stands for any number of characters, `?` for exactly one. All other characters, including `[` and `]`, count literally, and case does not count.
- The pattern may appear anywhere in the name: `Beta`, `*Beta*` and `Mario?2` all also find `Super Mario 2 (Beta).nes`. Accordingly, `S*` finds every name containing an `S`, not only names starting with it.
- `Enter`, `Tab` and the down arrow return to the list; `Esc` clears the filter and returns to the list.
- While the cursor is in the field, keys only write there: `x`, `k`, `Enter`, `f`, `r`, `F5` and `Esc` do not perform their list functions.
- The filter stays active after `F5`, after deleting and after choosing another folder. It is not saved.

**The filter only changes the display. Marked files hidden by the filter are still deleted when you delete**; the confirmation states their number.

### Settings

The button `Settings...` in the bottom row, or `s`, shows the most frequent changes to `redundanz_config.json` in the main window, in place of the file list. `Save` or `Cancel`, `Esc`, `Ctrl+E` or another click on `Settings...` bring the list back. Meanwhile the filter, the views, `Proceed...`, `Analyze again` and `Folder...` are locked, and `x`, `k` and `Enter` do nothing, so that nothing can change in the hidden list.

- **Language:** sets the language of the user interface. Choose one of the six languages. A new language applies from the next start of the program.
- **Priority:** sets which regional versions take precedence over others. The best region at the top; extra info such as `Beta` or `Proto` goes after `none`, so that such files come last (rule 6). Select an entry and move it with `Up` and `Down`, remove it with `Remove` or the `Delete` key, and add a new one with the field below the list and `Add` (or `Enter`).
- **Delete keywords:** set which versions of a game are always deleted. Separated by commas, for example `Hack, Hacks`. Files with them are marked for deletion (rule 2).
- **Same game as a plain file and as a ZIP file:** sets which of the two remains when both are of the same version. `Keep the plain file` (default) marks the ZIP file, `Keep the ZIP file` marks the plain files (see [ZIP files](#zip-files)).

`Save` writes the file and analyzes the folder again if the priority, the tags or the choice between plain file and ZIP file have changed; if you have changed marks by hand, the program asks first, because these changes are lost. All other entries of the file stay as they are. Wrong values, such as an empty region list or the same region twice, are reported, nothing is written, and the settings stay open. If the file cannot be read, the settings do not open, so that they cannot overwrite entries they do not know. With `--config`, the settings edit that file; with `--priority`, the priority given there still applies to this run.

A game counts as problematic if

- none of its files would be kept,
- the content of a marked ZIP does not appear anywhere else (`Game content deviates from the kept version`),
- a ZIP is defective, encrypted or unreadable,
- a file is kept as a suspected status or save file (rule 9),
- the rules only decided through a `Tie`,
- several ZIPs of the same version have different content,
- the file names spell the game differently (`Title 1-2` and `Title 12`),
- a marked file has a different file type than the kept ones (`.nes` and `.sfc`).

The window uses `tkinter`, which is part of the usual Python installation on Windows. If it is missing, the program reports this and deletes nothing.

## After the automatic cleanup

Even after the automatic cleanup, redundant game versions may remain. The easiest way to find them is the filter (key `/` and then the name of the game). Then you can mark the files that still need to be deleted.

## Terminal version (Linux)

The same program also runs in a text terminal, for example over SSH (PuTTY, MobaXterm), in `tmux` or on the Linux console. It shows the same list, applies the same rules, and shares `redundanz_config.json`, `rom_cleanup_workbench_settings.json` and `translations.py` with the window.

It starts by itself on Linux when there is no graphical display (neither `DISPLAY` nor `WAYLAND_DISPLAY` is set, as over SSH). `--tui` starts it everywhere else, also on Windows; use it where a graphical display exists but you want the terminal, for example in MobaXterm or under WSL.

It needs [Textual](https://textual.textualize.io/) (tested with 8.2.8). How to install it and start the program is described under [Installation](#installation) and [Usage](#usage).

Without Textual, the program says so and deletes nothing. The screen has the rows of the window from top to bottom: the green title row with the folder, a help row, the priority, the list, the filter field, the three views and the green status row. In the list, each game starts with its name in bold, followed by dashes up to the right edge; a note such as `Different spellings of the name` stands in that line. In a narrow terminal, such as PuTTY's 80 columns, long file names and notes wrap in their column instead of leaving the screen. `Nothing to do.` blinks with the terminal's own blinking; in PuTTY, blinking text may have to be switched on first. Questions and messages appear in a frame over the list, with buttons in the program's language; `No` is preselected.

The help row shows the keys as `key:action`, for example `x:delete  k:keep`. The window and the terminal version have the same keys.

| Key | Effect |
| --- | --- |
| Arrow keys | select a row, with Shift several |
| `Tab` / `Shift+Tab` | next / previous game; its first file is selected |
| `x` / `k` | mark the selected files for deletion / keep them |
| `1` `2` `3` | the views `Problematic deletion marks`, `All deletion marks`, `All ROM files` |
| `/` | go to the filter field (`Enter`, `Tab` or the down arrow return, `Esc` clears) |
| `Enter` | execute: delete after a confirmation (as `Proceed...`) |
| `f` | choose another folder: `Right` or `Space` opens a folder, `Left` closes it, `Enter` or a double click chooses; a path can also be typed |
| `s` | settings: `Shift+Up`/`Shift+Down` move a region, `Delete` removes it, `Ctrl+S` saves, `Esc` cancels |
| `r` or `F5` | analyze again |
| `c` or `F1` | show the credits (`c` too, because some terminals keep `F1` for their own help) |
| `q` or `Esc` | close without deleting anything; after changes by hand the program asks first |
| In a question | `Left`/`Right` choose a button, `Enter` presses it, `Esc` answers `No` |

The mouse works too: a click selects a row, the wheel scrolls, and the views and buttons can be clicked. Letters typed in a field stay in the field, also when typed fast or pasted: an `x` in the filter never marks a file.

**Colors and characters.** With 256 colors or more, the terminal version uses the colors of the window, but black behind every game (no stripes). Where the terminal only has 16 colors (`TERM=xterm`, `TERM=linux`), it switches to plain ANSI colors: blue selection, green title and status rows, green kept and red marked files, brown rows with black text changed by hand. On the Linux console, in terminals such as `vt100`, and when the locale names a charset other than UTF-8 (for example `en_US` or `de_DE.ISO-8859-1`), it draws only ASCII characters: views as `(*)`, frames from `+`, `-` and `|`. `--ascii` forces this. PuTTY reports itself as `xterm` (16 colors); for the window's colors, set *Connection → Data → Terminal-type string* to `xterm-256color`. File names and texts in other scripts, such as Japanese, still need a terminal and font that can show them.

Differences from the window: no font zoom, because the font belongs to the terminal (in PuTTY: *Window → Appearance*); and the games are not striped but start with a dashed line. With 16 colors, the green rows have black text, which stays readable on a light green. While deleting, the terminal version deletes in the background and shows the progress bar; all keys are locked until it is finished. The window and the terminal version keep their view and the confirmed save files in the same `rom_cleanup_workbench_settings.json`.

## Configuration: `redundanz_config.json`

The file is next to the program and is read again for every analysis. Language, priority, delete keywords and the choice between plain file and ZIP file are easiest to change in the window with `Settings...` (see [Settings](#settings)). In the file itself, it is enough to rearrange the order in `region_priority` and save the file:

```json
"region_priority": ["USA", "Europe", "none", "Japan", "Beta"],
"delete_tags": [],
"prefer_zip": false,
```

If the file contains an error, such as a misspelled entry, no analysis takes place and nothing is deleted. This is the file as shipped: the language is English, the priority USA, Europe, none, Japan, Beta, there are no delete keywords, and the plain file remains next to a ZIP file. Files without a region therefore come before Japanese ones. If the file or an entry is missing, the same defaults apply.

- `language`: the language of the window, the notes and the terminal output (see below).
- `region_priority`: regions and extra info, the best first. `none` stands for files without a known region; the words of the other languages (`keine`, `nessuna`, `ninguna`, `aucune`, `なし`) work as well. Extra info such as `Beta` after `none` puts such files last (rule 6); `Beta` also matches `Beta 2`.
- `region_aliases`: other spellings of a region, for example `Europa` for `Europe`. The short forms `U`, `E` and `J` of GoodTools names such as `Title (J) [o1].nes` are included.
- `delete_tags`: the delete keywords, extra info that always leads to deletion (rule 2). The list is empty by default. A delete keyword counts as a whole word anywhere inside a bracket: `Hack` matches `(Hack)`, `(Hack 2)`, `(Hack by Someone)` and `(Micks Hack)`, but not `(Hacks)` or `(Hackers)`, nor a word outside the brackets as in `Hack Attack (USA)`; if you want to delete hacks, enter both `Hack` and `Hacks`.
- `part_tags`: parts of a version, for example `Disc 1`.
- `prefer_zip`: `false` (default) keeps the plain file when a game exists as a plain file and as a ZIP file of the same version, `true` keeps the ZIP file.

Older files may still contain `low_priority_tags`, extra info with the lowest priority. The program reads its entries as if they stood at the end of `region_priority`, after `none`; the settings move them there when they save, and the entry disappears.

### Language

```json
"language": "de",
```

| Value | Language |
| --- | --- |
| `en` | English (default) |
| `de` | German |
| `it` | Italian |
| `es` | Spanish |
| `fr` | French |
| `ja` | Japanese |

The language applies to the window, the notes and the terminal output, and the program reads it at the start: after changing it, close the program and start it again. `F5` does not switch the language. An unknown value counts as an error in the configuration, as described above. The rules decide the same way in every language. The texts are in `translations.py`.

For Japanese, Windows shows the characters in a substitute font, because Lucida Sans Typewriter has no Japanese characters.

## Rules

The program ignores some files completely: they appear nowhere and are never deleted.

- Files whose name starts with `gamelist`, regardless of case. They are no ROM files.
- Hidden files: names starting with a dot, such as `.xxx` or `.DS_Store`, and files with the Windows attribute "hidden".

1. Files belong together if the text before the first bracket is the same. Case, spaces, hyphens and underscores do not count, so `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. This also means `Title 1-2` = `Title 12`. In addition, `und` = `and` = `&` = `&&`, `Sullivan's` = ``Sullivan`s`` = `Sullivan´s` = `Sullivans` (apostrophes do not count), the roman numerals `I` to `IX` as whole words = `1` to `9` (`Final Fantasy VII` = `Final Fantasy 7`; from `X` on they stay as they are, because `Mega Man X` and `Mega Man 10` are two games) as well as `The Title` = `Title The` = `Title, The` = `Title` count as equal. A `The` in the middle of the name does count. Likewise `vs` = `vs.` = `versus`. A number in front of the name, for example from a numbered collection, does not count: `057 Robocop vs Terminator` = `057 - Robocop vs Terminator` = `Robocop vs Terminator`. If the name is only the number (`1942`) or the number is attached to the word (`2Fast`), it stays part of the name; `4 in 1` and `3 in 1` stay different games. Because the names then only match through the comparison, the game counts as problematic (`Different spellings of the name`).
2. Files with a delete keyword (`delete_tags`, none by default, for example `Hack` and `Hacks`) are always marked, even if it is the only file of the game. `k` keeps such a file anyway.
3. Of the remaining files, the one with the best entry in `region_priority` is kept. Within one bracket the best entry counts: with `(USA, Japan)`, the better of the two. Across brackets the worst counts: `(USA) (Beta)` counts as `Beta` (rule 6).
4. All files of the same version are kept together, for example `(Disc 1)` and `(Disc 2)` or `.cue` and `.bin`. Everything else is marked. Exception: if only some of these files have a number in front of the name (`073 Batman (USA).sfc` and `Batman (USA).sfc`), those with the number are kept and the others are marked (`Name with number preferred`).
5. A region that is not in `region_priority` counts as `none`. This also applies to information such as `(Rev 1)`.
6. Extra info such as `Beta`, `Proto` or `Alpha` is written into `region_priority` after `none`. Files with it come after all others, even after files without a region, and in the order of the list: with `none, Beta, Proto`, a Beta comes before a Proto. They are only kept if there is no better file of the game. Among themselves, the region counts again, then the version from rule 7, then the number after the extra info: `Beta 2` wins over `Beta 1`, and `Beta 1` over `Beta` without a number. The numbers are compared numerically (`Beta 10` before `Beta 9`). The losing file gets the note `Older beta`.
7. With equal priority, the highest version number wins, compared numerically (`v1.10` before `v1.9`). Recognized in brackets are `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` and `Rev A`; in the game name only the form `Title v1.1`, also with `-` or `_` instead of a space. A file without a version loses to one with a version. The region counts before the version.
8. After that, the file with a number in front of the name wins (`073 Batman` before `Batman`), then the one with less extra information, then a file without ZIP (with `prefer_zip`: a ZIP file), then the alphabet. The report then shows `Tie`.
9. A file that is smaller than 1/4 of the largest file of the game is set aside before rules 3 to 8 and kept: it may be a status or save file. It therefore can neither be deleted nor push out the real ROM, for example `1941.state` the file `1941.zip`. The note column then says `Suspected status or save file`, and the game counts as problematic. Such a game appears in all three views, even if none of its files is marked. When you delete, the program confirms all suspected files that remain as legitimate: they stay where they are, are still never deleted, and no longer show up in `Problematic deletion marks` and `All deletion marks`, also after `F5` or a new start. The confirmation names their number. The program remembers them with path and size in `rom_cleanup_workbench_settings.json`; if the size changes, the file is suspected again. If nothing is marked, `Enter` offers to confirm them without deleting anything. ZIPs count with their unpacked size. This does not apply to a small plain file next to a large plain file of its own version, such as a `.cue` next to its `.bin`, nor to a file with the same extension as the largest file (a small `.nes` next to a large `.nes` is a ROM that rules 3 to 8 decide on), nor to files marked because of `delete_tags` or a defective ZIP. With `x` you can still mark the file by hand.
10. When you proceed, the program removes the number in front of the name of every kept file after deleting, together with the spaces, dots, hyphens or underscores after it: `073 Batman (USA).sfc` becomes `Batman (USA).sfc`, `057 - Robocop.md` becomes `Robocop.md`. The confirmation names their number and an example first; if nothing is marked, `Enter` only asks about renaming. The number stays if the game has a `.cue`, `.gdi`, `.m3u`, `.mds`, `.toc` or `.ccd` file (it names the file names in its content) or if the name without number is already taken; the confirmation names that number too. The content of ZIPs is not renamed. The title row of a game shows the name in the spelling of the first kept file (`Street Fighter II` or `Street Fighter 2`), always without number; if you move files with `k` or `x`, the title follows.

## ZIP files

Every ZIP file is read completely, even if it is the only file of a game. Its content is compared with the other files of the game using SHA-256.

- **Same content as a kept file:** The ZIP file is marked, and the report names the file with the same content.
- **If a ZIP and a plain file remain after the selection:** The ZIP is always marked, even with different content, if it is the only file containing a part such as `(Disc 1)` or if it is unreadable.
- **With `Keep the ZIP file` (`prefer_zip`):** It is the other way round: next to a readable ZIP file of the same version, the plain files are marked (`ZIP file preferred`). If the content of such a file does not appear in a kept ZIP, the report shows `Game content deviates from the kept ZIP file` and the game counts as problematic (`Content of a marked plain file is not kept`). An unreadable ZIP pushes out no plain file. The priority still comes first: a plain `(USA)` file wins over a `(Japan)` ZIP.
- **Several ZIPs of the same version with different content:** All are kept, and the report points this out.
- **Marked, but content does not appear in any kept file:** The report shows `Game content deviates from the kept version`. The file stays marked.
- **No region or version in the ZIP name:** The information is taken from the files in the ZIP, provided they have the same game name.
- **Defective or encrypted ZIP:** The file is always marked, even if it is the only file of the game. The content of an encrypted ZIP is not checked.
- **Locked ZIP or unknown method (for example Deflate64):** This says nothing about the condition of the file. Without a plain file of the game, it is kept and named in the report.

## Developing it further with Claude Code

The program is free software: you can clone the repository and develop it further with [Claude Code](https://claude.com/claude-code), without programming yourself. That is also how it was written.

1. Install Claude Code. It needs a Claude subscription or an account for the Claude API. On Windows in PowerShell:

   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```

   On Linux:

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

2. Clone the repository and start Claude Code in it:

   ```bash
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   cd rom-cleanup-workbench
   claude
   ```

3. Describe in your own words what should change, for example "Add an option that only shows ZIP files". Claude Code reads the code, suggests changes and asks before it changes files or runs commands. Then let it run the tests (`python -m unittest` in the folder `Rom Cleanup Workbench`) and try the change on a copy of your collection.

The plans of earlier changes are in `docs/`. If you pass on your changes, you must publish them under the GPL as well.

## License and disclaimer

Copyright (C) 2026 M. Kärcher

Rom Cleanup Workbench is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. The full text is in [LICENSE](<../LICENSE>).

**Use at your own risk.** The program deletes files, and there is no warranty of any kind; whoever uses it takes on all risks that come with it. We strongly recommend running it only on a copy of your own ROM collection.

## Credits

- Idea: M. Kärcher
- Programming: Claude Code
