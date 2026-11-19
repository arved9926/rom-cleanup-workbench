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
