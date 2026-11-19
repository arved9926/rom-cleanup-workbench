# Rom Cleanup Workbench

**User guide with screenshots:** [PDF](<docs/Rom Cleanup Workbench - User Guide.pdf>) · [Word](<docs/Rom Cleanup Workbench - User Guide.docx>)

Finds duplicate ROM files in a directory by game name and deletes them on request.
Requires Python 3.10 or newer, but no additional packages.
The program speaks English, German, Italian, Spanish, French and Japanese (see [Language](#language)).

## Usage

```bash
python rom_cleanup_workbench.py "D:\Games"
```

The program opens the analysis window and shows everything there; it prints nothing in the terminal and asks nothing there. Questions and messages also appear inside the window, in the language of the program, never as Windows popups; Enter chooses the preselected button and Esc answers No. Without a directory, the window asks for the folder. Files are only deleted after the confirmation in the window. **Deleted files do not go to the Recycle Bin.**

| Option | Effect |
| --- | --- |
| `--review all` | open the window with `All deletion marks` for this start |
| `--review problems` | open the window with `Problematic deletion marks` for this start |
| `--priority USA Europe Japan none` | set the priority for this run |
| `--delete-tag Proto Beta` | set the extra info for this run |
| `--config file.json` | use a different configuration |
| `--report-only` | without window: only print the report in the terminal |
| `--yes` | without window: delete marked files without asking |
| `--all` | with `--report-only`: also show games without marked files |

The command line options and their help (`--help`) are always in English.

In VS Code: open the folder `Rom Cleanup Workbench`, start with F5 and enter the directory.
The tests run through the test view or with `python -m unittest`.

## Analysis window

The green row at the top says `Rom Cleanup Workbench` on the left and names the folder on the right; below it the window names the active priority with its source. The green second-to-last row shows the status, during the analysis for example `Analyzing: 120 of 2007 files`. A progress bar also appears in the middle during that time. The window also shows errors, for example in the configuration, and nothing can be deleted as long as the analysis fails. While deleting, the progress bar appears in the middle and the green row shows for example `Deleting: 120 of 500 files`; the window accepts no input until the deletion is finished. After deleting, it reports the result and removes the deleted files from the list without analyzing the folder again; files that could not be deleted stay marked. `F5` analyzes the folder again when you want that.

If nothing is marked in the whole folder and no file is suspected to be a status or save file, `Nothing to do.` blinks in the middle of the window.

The three radio buttons determine what the list shows:

- `Problematic deletion marks`: only games with a marked file that count as problematic (default on first start)
- `All deletion marks`: all games with a marked file
- `All ROM files`: all games. Their files can then also be marked with `D`, and problematic cases without a marked file, such as an unreadable ZIP, appear too.

The window remembers the most recently chosen view and the confirmed status or save files (rule 9) in `rom_cleanup_workbench_settings.json` next to the program.

| Key | Effect |
| --- | --- |
| Arrow keys | select a row, with Shift several (for example all discs of a game) |
| `Tab` / `Shift+Tab` | go to the next / previous game; the first file of the game is selected |
| `D` (Demote) | mark the file for deletion; it moves to the end of its game |
| `P` (Promote) | keep the file; it moves to the position the rules give it |
| `Ctrl` + mouse wheel | enlarge or shrink the font (8 to 32 pt, applies until the window is closed) |
| `Ctrl+E` | same as the button `Settings...`: show or hide the settings for language, region priority and low priority tags (see [Settings](#settings)) |
| `Ctrl+F` | go to the filter field |
| `Ctrl+L` | same as the button `Proceed...`: delete after a confirmation and confirm the suspected status or save files (rule 9) |
| `Ctrl+O` | choose another folder |
| `F5` | analyze again, also reads the configuration again |
| `Esc` | close without deleting anything |

Horizontal lines separate the games, and every second game has a dark gray background. The column `Size` shows the size of every file in KB, rounded up as in Windows Explorer (`1,234 KB`); `?` means the size could not be read. The size is read during the analysis. Kept files are shown in bold under `Keep:`, files to be deleted in normal weight under `Marked for deletion`. The window shows white text in Lucida Sans Typewriter 11 pt on a black background. If the font is not installed, Windows silently picks a substitute. Files moved by hand have a brown background and carry the note `By hand`; while the row is selected, it appears blue. The program's notes stay unchanged, even if they refer to a file you have moved.

`Problematic deletion marks` hides the unproblematic games. **Their marked files are still deleted when you delete**; the confirmation states their number. Games you have changed by hand always stay visible, unless the filter hides them.

### Filter

The filter field on the left of the bottom row narrows the current view to games with a file name that contains the pattern. A game stays complete if one of its files matches. The list updates shortly after typing; the file contents are not read.

- `*` stands for any number of characters, `?` for exactly one. All other characters, including `[` and `]`, count literally, and case does not count.
- The pattern may appear anywhere in the name: `Beta`, `*Beta*` and `Mario?2` all also find `Super Mario 2 (Beta).nes`. Accordingly, `S*` finds every name containing an `S`, not only names starting with it.
- `Enter`, `Tab` and the down arrow return to the list; `Esc` clears the filter and returns to the list.
- While the cursor is in the field, keys only write there: `D`, `P`, `Ctrl+L`, `Ctrl+O`, `F5` and `Esc` do not perform their list functions.
- The filter stays active after `F5`, after deleting and after choosing another folder. It is not saved.

**The filter only changes the display. Marked files hidden by the filter are still deleted when you delete**; the confirmation states their number.

### Settings

The button `Settings...` in the bottom row, or `Ctrl+E`, shows the most frequent changes to `redundanz_config.json` in the main window, in place of the file list. `Save` or `Cancel`, `Esc`, a second `Ctrl+E` or another click on `Settings...` bring the list back. Meanwhile the filter, the views, `Proceed...`, `Analyze again` and `Folder...` are locked, and `D`, `P` and `Ctrl+L` do nothing, so that nothing can change in the hidden list.

- **Language:** choose from the six languages. A new language applies from the next start of the program.
- **Region priority:** the best region at the top. Select a region and move it with `Up` and `Down`, remove it with `Remove` or the `Delete` key, and add a new one with the field below the list and `Add` (or `Enter`).
- **Low priority tags:** separated by commas, for example `Beta, Proto`.

`Save` writes the file and analyzes the folder again if the priority or the tags have changed; if you have changed marks by hand, the program asks first, because these changes are lost. All other entries of the file stay as they are. Wrong values, such as an empty region list or the same region twice, are reported, nothing is written, and the settings stay open. If the file cannot be read, the settings do not open, so that they cannot overwrite entries they do not know. With `--config`, the settings edit that file; with `--priority`, the priority given there still applies to this run.

A game counts as problematic if

- none of its files would be kept,
- the content of a marked ZIP does not appear anywhere else (`WARNING`),
- a ZIP is defective, encrypted or unreadable,
- a file is kept as a suspected status or save file (rule 9),
- the rules only decided through a `Tie`,
- several ZIPs of the same version have different content,
- the file names spell the game differently (`Title 1-2` and `Title 12`),
- a marked file has a different file type than the kept ones (`.nes` and `.sfc`).

The window uses `tkinter`, which is part of the usual Python installation on Windows. If it is missing, the program reports this and deletes nothing.

## Configuration: `redundanz_config.json`

The file is next to the program and is read again for every analysis. Language, region priority and low priority tags are easiest to change in the window with `Settings...` (see [Settings](#settings)). In the file itself, it is enough to rearrange the order in `region_priority` and save the file:

```json
"region_priority": ["Germany", "Europe", "USA", "none", "Japan"],
```

If the file contains an error, such as a misspelled entry, no analysis takes place and nothing is deleted. If the file or an entry is missing, the program's defaults apply; the priority there is USA, Europe, Japan, none, and the language is English.

- `language`: the language of the window, the notes and the terminal output (see below).
- `region_priority`: regions, the best first. `none` stands for files without a known region; the words of the other languages (`keine`, `nessuna`, `ninguna`, `aucune`, `なし`) work as well.
- `region_aliases`: other spellings of a region, for example `Europa` for `Europe`.
- `delete_tags`: extra info that always leads to deletion. `Proto` also matches `Proto 2`.
- `low_priority_tags`: extra info with the lowest priority. `Beta` also matches `Beta 2`.
- `part_tags`: parts of a version, for example `Disc 1`.

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

1. Files belong together if the text before the first bracket is the same. Case, spaces, hyphens and underscores do not count, so `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. This also means `Title 1-2` = `Title 12`. In addition, `und` = `and` = `&` as well as `The Title` = `Title The` = `Title, The` = `Title` count as equal. A `The` in the middle of the name does count.
2. Files with extra info from `delete_tags` are always marked, even if it is the only file of the game.
3. Of the remaining files, the one with the best region is kept. With `(USA, Japan)`, the better of the two counts.
4. All files of the same version are kept together, for example `(Disc 1)` and `(Disc 2)` or `.cue` and `.bin`. Everything else is marked.
5. A region that is not in `region_priority` counts as `none`. This also applies to information such as `(Rev 1)`.
6. Files with extra info from `low_priority_tags` come after all others, even after files without a region. They are only kept if there is no other file of the game. Among themselves, the region counts again, then the version from rule 7, then the number after the extra info: `Beta 2` wins over `Beta 1`, and `Beta 1` over `Beta` without a number. The numbers are compared numerically (`Beta 10` before `Beta 9`). The losing file gets the note `Older beta`.
7. With equal priority, the highest version number wins, compared numerically (`v1.10` before `v1.9`). Recognized in brackets are `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` and `Rev A`; in the game name only the form `Title v1.1`, also with `-` or `_` instead of a space. A file without a version loses to one with a version. The region counts before the version.
8. After that, the file with less extra information wins, then a file without ZIP, then the alphabet. The report then shows `Tie`.
9. A file that is smaller than 1/4 of the largest file of the game is set aside before rules 3 to 8 and kept: it may be a status or save file. It therefore can neither be deleted nor push out the real ROM, for example `1941.state` the file `1941.zip`. The note column then says `Suspected status or save file`, and the game counts as problematic. Such a game appears in all three views, even if none of its files is marked. When you delete, the program confirms all suspected files that remain as legitimate: they stay where they are, are still never deleted, and no longer show up in `Problematic deletion marks` and `All deletion marks`, also after `F5` or a new start. The confirmation names their number. The program remembers them with path and size in `rom_cleanup_workbench_settings.json`; if the size changes, the file is suspected again. If nothing is marked, `Ctrl+L` offers to confirm them without deleting anything. ZIPs count with their unpacked size. This does not apply to a small plain file next to a large plain file of its own version, such as a `.cue` next to its `.bin`, nor to files marked because of `delete_tags` or a defective ZIP. With `D` you can still mark the file by hand.

## ZIP files

Every ZIP file is read completely, even if it is the only file of a game. Its content is compared with the other files of the game using SHA-256.

- **Same content as a kept file:** The ZIP file is marked, and the report names the file with the same content.
- **If a ZIP and a plain file remain after the selection:** The ZIP is always marked, even with different content, if it is the only file containing a part such as `(Disc 1)` or if it is unreadable.
- **Several ZIPs of the same version with different content:** All are kept, and the report points this out.
- **Marked, but content does not appear in any kept file:** The report shows `WARNING`. The file stays marked.
- **No region or version in the ZIP name:** The information is taken from the files in the ZIP, provided they have the same game name.
- **Defective or encrypted ZIP:** The file is always marked, even if it is the only file of the game. The content of an encrypted ZIP is not checked.
- **Locked ZIP or unknown method (for example Deflate64):** This says nothing about the condition of the file. Without a plain file of the game, it is kept and named in the report.
