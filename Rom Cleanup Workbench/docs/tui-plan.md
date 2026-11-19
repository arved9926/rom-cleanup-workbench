# Handover: Linux terminal version (`--tui`)

Status: **step 1 of 14 done.** The terminal version itself does not exist yet. Textual 8.2.8 is installed for the user.

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
- [ ] **2. `--tui` option and start.** `--tui` in `build_parser`; `main` starts `rom_cleanup_workbench_tui.run_tui(...)` with the same `analyze` and `ConfigFile`; without a display (`DISPLAY`/`WAYLAND_DISPLAY` missing on Linux) the terminal version starts automatically; a clear message if Textual is missing. A stub app that only shows the title. Done when: main tests cover the choice of front end.
- [ ] **3. Read-only list.** App with title row (program and folder), help row, priority row, the game list (games, Keep/Marked sections, size, note), status row; background analysis with progress bar. Done when: a Pilot test shows the demo games and the status text.
- [ ] **4. Moving the cursor.** Arrows, Shift+arrows for several rows, Tab/Shift+Tab per game, mouse click and wheel. Done when: Pilot tests for selection and Tab pass.
- [ ] **5. D and P.** Mark and keep with `d`/`p`, brown "By hand" rows, status updates. Done when: tests match the window's D/P tests.
- [ ] **6. Views.** Three views with `1`/`2`/`3` and clickable radio items with the red dot; the choice is saved like in the window. Done when: tests for every view and for saving pass.
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
