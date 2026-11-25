# Rom Cleanup Workbench

Finds duplicate ROM files in a folder by game name, shows the decision for every game and deletes the duplicates only after your confirmation. A window for Windows, a terminal version for Linux, a UI in English, German, Italian, Spanish, French and Japanese.

**Important:** Do not use this program on your original ROM files. Make a copy of your ROM repository and use the program to clean up only that copied repository.
**Important:** This is still an Alpha version of the program. Use it with caution ie. best in an isolated environment.

The documentation is the user guide (PDF): [English](<Rom Cleanup Workbench/docs/Rom Cleanup Workbench - User Guide.pdf>) · [Deutsch](<Rom Cleanup Workbench/docs/Rom Cleanup Workbench - Benutzerhandbuch.pdf>) · [Italiano](<Rom Cleanup Workbench/docs/Rom Cleanup Workbench - Guida utente.pdf>) · [Español](<Rom Cleanup Workbench/docs/Rom Cleanup Workbench - Guía del usuario.pdf>) · [Français](<Rom Cleanup Workbench/docs/Rom Cleanup Workbench - Guide utilisateur.pdf>) · [日本語](<Rom Cleanup Workbench/docs/Rom Cleanup Workbench - ユーザーガイド.pdf>)

## Quick start

Install Python 3.10 or newer, then download this repository (**Code → Download ZIP**, unpack it and rename the folder `rom-cleanup-workbench-main` to `rom-cleanup-workbench`) or clone it with Git.

On Windows, the window needs no further packages:

```powershell
cd "rom-cleanup-workbench\Rom Cleanup Workbench"
python rom_cleanup_workbench.py "D:\Games"
```

On Linux, the terminal version needs Textual in a virtual environment:

```bash
cd "rom-cleanup-workbench/Rom Cleanup Workbench"
python3 -m venv ~/venvs/rom-cleanup-workbench
~/venvs/rom-cleanup-workbench/bin/pip install textual==8.2.8
~/venvs/rom-cleanup-workbench/bin/python rom_cleanup_workbench.py ~/roms
```

The shipped settings: English, priority USA > Europe > none > Japan > Beta, no delete keywords. Change them in the program with `s`. The user guide explains the installation step by step, the keys and all rules.

**Deleted files do not go to the Recycle Bin.**

## License

Copyright (C) 2026 M. Kärcher. Free software under the GNU General Public License, version 3 or later; see [LICENSE](LICENSE). Use at your own risk: there is no warranty. We strongly recommend running the program only on a copy of your own ROM collection.

Programming: Claude Code. You can develop the program further with Claude Code yourself; the user guide shows how.
