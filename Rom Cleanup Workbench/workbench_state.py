# Rom Cleanup Workbench
# Copyright (C) 2026 M. Kärcher
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.

"""Parts shared by the window and the terminal version: the settings file, the views, sizes and folders.

Nothing here draws anything; both front ends show the same state in their own way.
"""

from __future__ import annotations

import json
import os
import string
from pathlib import Path

from translations import tr

# A file of its own, so that the front ends do not rewrite the hand-maintained redundanz_config.json.
SETTINGS_PATH = Path(__file__).with_name("rom_cleanup_workbench_settings.json")
_SCOPE_KEY = "scope"
_CONFIRMED_KEY = "confirmed_save_files"
_COLLECTION_KEY = "last_collection"
_HIDE_EMPTY_KEY = "hide_empty_folders"
_SORT_KEY = "overview_sort"
SCOPE_PROBLEMS = "problems"
SCOPE_MARKED = "marked"
SCOPE_ALL_FILES = "all"
DEFAULT_SCOPE = SCOPE_PROBLEMS
# The value is saved and stays the same in every language; the label is a text key.
SCOPES = (
    (SCOPE_PROBLEMS, "window.scope.problems"),
    (SCOPE_MARKED, "window.scope.marked"),
    (SCOPE_ALL_FILES, "window.scope.all"),
)


def scope_flags(scope: str, pattern: str = "") -> tuple[bool, bool, str]:
    """Translates a view into the values only_problems, show_all and pattern of the Review object."""
    return scope == SCOPE_PROBLEMS, scope == SCOPE_ALL_FILES, pattern


def format_kb(size: int | None) -> str:
    """Like Windows Explorer: Kilobytes rounded up, with the language's thousands separator."""
    if size is None:
        return "?"
    number = f"{-(-size // 1024):,}".replace(",", tr("number.thousands"))
    return f"{number} {tr('unit.kb')}"


def _load_settings(path: Path) -> dict:
    """A missing or broken file means: The defaults apply."""
    try:
        with open(path, encoding="utf-8-sig") as handle:
            settings = json.load(handle)
    except (OSError, ValueError):
        return {}
    return settings if isinstance(settings, dict) else {}


def _save_settings(path: Path, **values) -> None:
    """Changes only the given entries, so that the view and the confirmed files do not overwrite each other."""
    settings = _load_settings(path)
    settings.update(values)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)
        handle.write("\n")


def load_scope(path: Path) -> str:
    scope = _load_settings(path).get(_SCOPE_KEY)
    return scope if scope in (value for value, _label in SCOPES) else DEFAULT_SCOPE


def save_scope(path: Path, scope: str) -> None:
    _save_settings(path, **{_SCOPE_KEY: scope})


def load_last_collection(path: Path) -> Path | None:
    """The folder opened last (a roms folder or any other); None if there is none or it is gone."""
    value = _load_settings(path).get(_COLLECTION_KEY)
    folder = Path(value) if isinstance(value, str) and value else None
    return folder if folder is not None and folder.is_dir() else None


def save_last_collection(path: Path, folder: Path) -> None:
    _save_settings(path, **{_COLLECTION_KEY: str(folder)})


SORT_COLUMNS = ("platform", "files", "games", "marked", "problematic")


def load_overview_sort(path: Path) -> tuple[str, bool]:
    """The overview's order: (column, descending); by platform name, ascending, if none is stored."""
    value = _load_settings(path).get(_SORT_KEY)
    if isinstance(value, dict) and value.get("column") in SORT_COLUMNS:
        return value["column"], value.get("descending") is True
    return "platform", False


def save_overview_sort(path: Path, column: str, descending: bool) -> None:
    _save_settings(path, **{_SORT_KEY: {"column": column, "descending": bool(descending)}})


def load_hide_empty(path: Path) -> bool:
    """Whether the overview hides folders without a game file."""
    return _load_settings(path).get(_HIDE_EMPTY_KEY) is True


def save_hide_empty(path: Path, hide: bool) -> None:
    _save_settings(path, **{_HIDE_EMPTY_KEY: bool(hide)})


def load_confirmed_saves(path: Path) -> dict[str, int]:
    """Status or save files confirmed when deleting: file key to size in bytes."""
    confirmed = _load_settings(path).get(_CONFIRMED_KEY)
    if not isinstance(confirmed, dict):
        return {}
    return {key: size for key, size in confirmed.items() if isinstance(size, int) and not isinstance(size, bool)}


def add_confirmed_saves(path: Path, files: dict[str, int]) -> None:
    _save_settings(path, **{_CONFIRMED_KEY: {**load_confirmed_saves(path), **files}})


def drives() -> list[Path]:
    """The drives of the computer, for example C:\\ and D:\\; on other systems only /."""
    if os.name != "nt":
        return [Path("/")]
    if hasattr(os, "listdrives"):  # Python 3.12 and newer
        try:
            return [Path(drive) for drive in os.listdrives()]
        except OSError:
            pass
    return [Path(f"{letter}:\\") for letter in string.ascii_uppercase if Path(f"{letter}:\\").exists()]


def subfolders(folder: Path) -> list[Path]:
    """The visible subfolders, sorted like Windows Explorer; an unreadable folder has none."""
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return []
    folders = []
    for entry in entries:
        try:
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            attributes = getattr(entry.stat(), "st_file_attributes", 0)
        except OSError:
            continue
        if attributes & 0x6:  # FILE_ATTRIBUTE_HIDDEN or FILE_ATTRIBUTE_SYSTEM (Windows only)
            continue
        folders.append(Path(entry.path))
    return sorted(folders, key=lambda path: path.name.casefold())
