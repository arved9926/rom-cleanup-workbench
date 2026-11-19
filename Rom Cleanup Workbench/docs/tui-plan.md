# Handover: Linux terminal version (`--tui`)

Status: **steps 1–6 of 14 done.** The terminal version shows the analyzed list; the cursor and a selection of several rows can be moved, `d`/`p` mark and keep files, and the three views can be chosen with `1`/`2`/`3` or by clicking. Next: step 7 (filter). Textual 8.2.8 is installed for the user.

## Decisions (agreed with the user)

- Library: **Textual** (`pip install textual`), already installed.
- Target: a modern terminal (xterm-256color). No 80 × 24 limit; colors, bold and italic allowed. Not a strict VT100.
- Mouse: **yes** (click selects a row, the wheel scrolls, views and buttons can be clicked).
- Start: the same program, `python3 rom_cleanup_workbench.py --tui [folder]`; automatic when there is no graphical display.
- Final test: on the user's Linux computer. During development: Textual's headless test mode (`App.run_test()`, Pilot) on Windows.
- Rules, configuration, translations and settings files stay shared with the Windows window. Nothing for Windows may change behavior.

## How to work

- One step at a time. A step is done when **all tests pass** (`python -m unittest` in `Rom Cleanup Workbench`) and it is **committed locally**. Upload to GitHub only when the user asks.
- After each step: tick it off below and write one line under "Log".
- Never delete files outside temporary test folders. Never run the program on a real game folder.
- Texts go into `translations.py` for all six languages (en, de, it, es, fr, ja).

## Steps

- [x] **1. Shared settings module.** Move `load_scope`, `save_scope`, `load_confirmed_saves`, `add_confirmed_saves`, `format_kb` and the settings path from `rom_cleanup_workbench_window.py` into a new `workbench_state.py`; the window imports them from there. Done when: all existing tests pass unchanged (only import paths in tests may change).
- [x] **2. `--tui` option and start.** `--tui` in `build_parser`; `main` starts `rom_cleanup_workbench_tui.run_tui(...)` with the same `analyze` and `ConfigFile`; without a display (`DISPLAY`/`WAYLAND_DISPLAY` missing on Linux) the terminal version starts automatically; a clear message if Textual is missing. A stub app that only shows the title. Done when: main tests cover the choice of front end.
- [x] **3. Read-only list.** App with title row (program and folder), help row, priority row, the game list (games, Keep/Marked sections, size, note), status row; background analysis with progress bar. Done when: a Pilot test shows the demo games and the status text.
- [x] **4. Moving the cursor.** Arrows, Shift+arrows for several rows, Tab/Shift+Tab per game, mouse click and wheel. Done when: Pilot tests for selection and Tab pass.
- [x] **5. D and P.** Mark and keep with `d`/`p`, brown "By hand" rows, status updates. Done when: tests match the window's D/P tests.
- [x] **6. Views.** Three views with `1`/`2`/`3` and clickable radio items with the red dot; the choice is saved like in the window. Done when: tests for every view and for saving pass.
- [ ] **7. Filter.** Filter field (`Ctrl+F` or `/`) with `*` and `?`; keys typed there never act on the list; Esc clears. Done when: filter tests pass.
- [ ] **8. Questions and messages.** A modal screen with Yes/No/OK in the program's language, No preselected, Esc answers No, list locked meanwhile. Done when: tests answer questions by pressing the buttons.
- [ ] **9. Proceed.** `Ctrl+L`/`x`: confirmation text from `Review.confirm_message`, progress bar while deleting, result message, deleted files leave the list, save files are confirmed. Done when: deletion tests on temporary folders pass.
- [ ] **10. Folder choice.** `Ctrl+O`/`o`: directory tree starting at `/` and the home folder, path field, Select/Cancel. Done when: tests choose a temporary folder.
- [ ] **11. Settings.** `Ctrl+E`/`e`: region priority (up, down, remove, add), language, low priority tags; writes through `ConfigFile`. Done when: tests match the window's settings tests.
- [ ] **12. Colors and fallbacks.** Same colors as the window, bold and italic; readable with 16 colors and on the Linux console; ASCII fallback for terminals without UTF-8; Japanese width. Done when: snapshot or text checks of the screen pass.
- [ ] **13. Linux check.** The user runs it on Linux (GNOME Terminal or similar, SSH, tmux); fix what turns up.
- [ ] **14. Documentation.** English only: README section and a chapter in the user guide (Word/PDF). The PowerPoint is never uploaded.

## Log

- 2026-11-19: Concept agreed, Textual installed, this note written. Next: step 1.
- 2026-11-19: Step 1 done. `workbench_state.py` now holds the settings file (view, confirmed save files), `format_kb`, the view names (`SCOPES`, `scope_flags`) and the folder helpers `drives`/`subfolders` for step 10. The window imports them under its old names, so its code and all 290 tests are unchanged. Next: step 2.
- 2026-11-19: Step 2 done. `--tui` and `_use_terminal_version` (Linux without `DISPLAY`/`WAYLAND_DISPLAY`) in `rom_cleanup_workbench.py`; `main` passes `analyze`, folder, view and `ConfigFile` to `rom_cleanup_workbench_tui.run_tui`. Missing Textual prints `terminal.no_textual` and deletes nothing. `rom_cleanup_workbench_tui.py` has `WorkbenchApp` with the green title row and `q`/Esc to quit. Tests: `MainTests` (front-end choice; `DISPLAY` is set in `setUp` so the window tests stay valid on a headless Linux machine) and `TerminalVersionTests` (Pilot). Note: import Textual before patching `sys.platform` in tests. 297 tests pass. Next: step 3.
- 2026-11-19: Step 3 done. `WorkbenchApp` shows help (`tui.help`), priority, a `DataTable` (File/Size/Note; game, Keep/Marked rows, empty row between games; row keys `g{n}`, `g{n}f{m}` in `app.files`), "Nothing to do.", a progress bar and the green status row. Analysis runs in a thread worker; `_analysis` counter ignores replaced results. Dynamic texts are Rich `Text`/`markup=False`, so `[!]` in names stays literal. Screenshot check: `NO_COLOR=1` is set in this shell, unset it to see colors. 304 tests pass. Next: step 4.
- 2026-11-19: Step 4 done. `GameTable` (a `DataTable`) keeps a set `selected` of row keys and paints it like the cursor row (`datatable--selected`, via `_get_row_style`); Up/Down/Shift skip the empty `s{n}` rows (`action_move_cursor`), Tab/Shift+Tab (`action_move_game`, priority bindings) jump to the first file of the neighboring game and scroll the whole game into view; after the analysis the first file is selected. A click or the table's own keys (Page Up, Home) select only the new row; a click on an empty row selects nothing; the wheel scrolls as in Textual. Ctrl/Shift+click are not supported yet. `app.selected_keys()` gives the rows for D/P. 310 tests pass. Next: step 5.
- 2026-11-19: Step 5 done. `d`/`D` and `p`/`P` call `Review.demote`/`promote` on the selected file rows (game and heading rows do nothing); `_fill_table` redraws the list from `_visible` with stable row keys per file (`_file_keys`), so the selection, cursor and scroll position survive, and a vanished Keep heading moves the cursor to the last moved file. Moved files get "By hand: keep/delete" in the note and the brown background `#5c4400` (`datatable--moved`); the status row follows. The step-4 highlight handler was replaced: `GameTable` overrides `_on_click` and the page/home/end actions to select only the cursor row, which is simpler than telling the app's own moves apart. Like the window, games do not leave the view after D/P. 316 tests pass. Next: step 6.
- 2026-11-19: Step 6 done. A horizontal `RadioSet` (`#views`, buttons `view-problems`/`view-marked`/`view-all`, red dot `#e5383b` on gray) above the status row; `1`/`2`/`3` set the button, `on_radio_set_changed` calls `set_scope`, which redraws and saves with `save_scope`. The `RadioSet` cannot take the focus, so the keys keep acting on the list after a click. Row keys now follow the game's place in `review.results` (`_game_numbers`, `_file_keys` set in `show_review`), so the selection survives a view change; if none of it is shown any more, the first file is selected. A failed save shows "Choice not saved: <error>" in the status row for now; step 8 should turn it into a message like the window's. 322 tests pass. Next: step 7.
