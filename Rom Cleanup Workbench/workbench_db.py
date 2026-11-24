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

"""The collection: a roms folder with one folder per platform and a database of the scans.

The database is SQLite (part of Python) in the hidden folder .rom_cleanup_workbench of the roms
folder. It keeps the facts of each scan (files, sizes, ZIP contents, checksums), not the
decisions: the rules decide again from these facts in a moment, with the current settings.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rom_cleanup_workbench import FileFacts, ZipMember, _is_hidden

DATABASE_FOLDER = ".rom_cleanup_workbench"
DATABASE_NAME = "rom_cleanup_workbench.sqlite"
SCHEMA_VERSION = 1
_HIDDEN_ATTRIBUTE = 0x2  # FILE_ATTRIBUTE_HIDDEN

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_info (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS platforms (
    id INTEGER PRIMARY KEY,
    folder TEXT NOT NULL UNIQUE,
    last_scan TEXT,
    files INTEGER,
    games INTEGER,
    marked INTEGER,
    problematic INTEGER,
    summary_key TEXT,
    config_json TEXT
);
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    platform_id INTEGER NOT NULL REFERENCES platforms(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    size INTEGER,
    mtime_ns INTEGER,
    sha256 TEXT,
    zip_error_kind TEXT,
    zip_error_text TEXT NOT NULL DEFAULT '',
    UNIQUE (platform_id, name)
);
CREATE TABLE IF NOT EXISTS zip_members (
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    name TEXT NOT NULL,
    size INTEGER NOT NULL,
    sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS confirmed_saves (
    platform_id INTEGER NOT NULL REFERENCES platforms(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    size INTEGER NOT NULL,
    UNIQUE (platform_id, name)
);
CREATE TABLE IF NOT EXISTS manual_moves (
    platform_id INTEGER NOT NULL REFERENCES platforms(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    size INTEGER,
    mtime_ns INTEGER,
    decision TEXT NOT NULL,
    UNIQUE (platform_id, name)
);
CREATE INDEX IF NOT EXISTS zip_members_file ON zip_members (file_id);
"""


@dataclass
class PlatformRow:
    """What the database knows about a platform folder; None everywhere if it was never scanned."""

    folder: str
    last_scan: str | None = None
    files: int | None = None
    games: int | None = None
    marked: int | None = None
    problematic: int | None = None
    summary_key: str | None = None
    has_own_config: bool = False


def _hide(path: Path) -> None:
    """Hides the folder in the Windows Explorer as well; elsewhere the dot already hides it."""
    if os.name != "nt":
        return
    try:
        import ctypes

        attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attributes != -1 and not attributes & _HIDDEN_ATTRIBUTE:
            ctypes.windll.kernel32.SetFileAttributesW(str(path), attributes | _HIDDEN_ATTRIBUTE)
    except (OSError, AttributeError):
        pass  # Hiding is a courtesy; the database works without it.


class Collection:
    """A roms folder and its database. Opening it creates the database if it is missing."""

    def __init__(self, root: Path):
        self.root = Path(root)
        folder = self.root / DATABASE_FOLDER
        folder.mkdir(exist_ok=True)
        _hide(folder)
        self.path = folder / DATABASE_NAME
        self._db = sqlite3.connect(self.path)
        self._db.execute("PRAGMA foreign_keys = ON")
        with self._db:
            self._db.executescript(_SCHEMA)
            if self._db.execute("SELECT COUNT(*) FROM schema_info").fetchone()[0] == 0:
                self._db.execute("INSERT INTO schema_info (version) VALUES (?)", (SCHEMA_VERSION,))
        version = self._db.execute("SELECT version FROM schema_info").fetchone()[0]
        if version > SCHEMA_VERSION:
            self.close()
            raise ValueError(f"database version {version} is newer than this program ({SCHEMA_VERSION})")

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "Collection":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # Platforms ------------------------------------------------------------------------------

    def platform_folders(self) -> list[Path]:
        """The subfolders that are platforms: not hidden, not the database, not gamelist..."""
        folders = []
        try:
            children = list(self.root.iterdir())
        except OSError:
            return []
        for child in children:
            if not child.is_dir() or child.name == DATABASE_FOLDER or _is_hidden(child):
                continue
            if child.name.casefold().startswith("gamelist"):
                continue
            folders.append(child)
        return sorted(folders, key=lambda path: path.name.casefold())

    def _platform_id(self, folder: str, create: bool = True) -> int | None:
        row = self._db.execute("SELECT id FROM platforms WHERE folder = ?", (folder,)).fetchone()
        if row:
            return row[0]
        if not create:
            return None
        with self._db:
            return self._db.execute("INSERT INTO platforms (folder) VALUES (?)", (folder,)).lastrowid

    def platform(self, folder: str) -> PlatformRow:
        row = self._db.execute(
            "SELECT folder, last_scan, files, games, marked, problematic, summary_key, config_json "
            "FROM platforms WHERE folder = ?", (folder,)).fetchone()
        if row is None:
            return PlatformRow(folder)
        return PlatformRow(*row[:7], has_own_config=row[7] is not None)

    # Facts of a scan --------------------------------------------------------------------------

    def save_facts(self, folder: str, facts: list[FileFacts], when: datetime | None = None) -> None:
        """Replaces the facts of the platform with those of a scan, in one transaction."""
        platform_id = self._platform_id(folder)
        moment = (when or datetime.now()).isoformat(timespec="seconds")
        with self._db:
            self._db.execute("DELETE FROM files WHERE platform_id = ?", (platform_id,))
            for item in facts:
                self._insert_file(platform_id, item)
            self._db.execute("UPDATE platforms SET last_scan = ?, files = ?, summary_key = NULL WHERE id = ?",
                             (moment, len(facts), platform_id))

    def _insert_file(self, platform_id: int, item: FileFacts) -> None:
        file_id = self._db.execute(
            "INSERT INTO files (platform_id, name, size, mtime_ns, sha256, zip_error_kind, zip_error_text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (platform_id, item.name, item.size, item.mtime_ns, item.sha256, item.zip_error_kind,
             item.zip_error_text)).lastrowid
        self._db.executemany(
            "INSERT INTO zip_members (file_id, position, name, size, sha256) VALUES (?, ?, ?, ?, ?)",
            [(file_id, position, member.name, member.size, member.sha256)
             for position, member in enumerate(item.members or [])])

    def load_facts(self, folder: str) -> list[FileFacts] | None:
        """The facts of the last scan, sorted by name; None if the platform was never scanned."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None or self.platform(folder).last_scan is None:
            return None
        members: dict[int, list[ZipMember]] = {}
        for file_id, name, size, sha in self._db.execute(
                "SELECT m.file_id, m.name, m.size, m.sha256 FROM zip_members m JOIN files f ON f.id = m.file_id "
                "WHERE f.platform_id = ? ORDER BY m.file_id, m.position", (platform_id,)):
            members.setdefault(file_id, []).append(ZipMember(name, size, sha))
        facts = []
        for file_id, name, size, mtime, sha, error_kind, error_text in self._db.execute(
                "SELECT id, name, size, mtime_ns, sha256, zip_error_kind, zip_error_text FROM files "
                "WHERE platform_id = ?", (platform_id,)):
            item = FileFacts(name, size, mtime, sha256=sha, zip_error_kind=error_kind, zip_error_text=error_text)
            if item.is_zip and not error_kind:
                item.members = members.get(file_id, [])
            facts.append(item)
        return sorted(facts, key=lambda item: item.name.casefold())

    def update_checksums(self, folder: str, checksums: dict[str, str]) -> None:
        """Keeps checksums of plain files that were computed while deciding."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None or not checksums:
            return
        with self._db:
            self._db.executemany("UPDATE files SET sha256 = ? WHERE platform_id = ? AND name = ? AND sha256 IS NULL",
                                 [(sha, platform_id, name) for name, sha in checksums.items()])

    def remove_files(self, folder: str, names: list[str]) -> None:
        """Deleted files leave the database, so that no new scan is needed."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None or not names:
            return
        with self._db:
            self._db.executemany("DELETE FROM files WHERE platform_id = ? AND name = ?",
                                 [(platform_id, name) for name in names])
            self._db.execute("UPDATE platforms SET files = (SELECT COUNT(*) FROM files WHERE platform_id = ?), "
                             "summary_key = NULL WHERE id = ?", (platform_id, platform_id))

    def rename_file(self, folder: str, old: str, new: str, mtime_ns: int | None = None) -> None:
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return
        with self._db:
            self._db.execute("UPDATE files SET name = ?, mtime_ns = COALESCE(?, mtime_ns) "
                             "WHERE platform_id = ? AND name = ?", (new, mtime_ns, platform_id, old))
            self._db.execute("UPDATE platforms SET summary_key = NULL WHERE id = ?", (platform_id,))

    # Summary for the overview ------------------------------------------------------------------

    def save_summary(self, folder: str, games: int, marked: int, problematic: int, key: str) -> None:
        """The numbers of the overview, with the settings (key) they were computed with."""
        platform_id = self._platform_id(folder)
        with self._db:
            self._db.execute("UPDATE platforms SET games = ?, marked = ?, problematic = ?, summary_key = ? "
                             "WHERE id = ?", (games, marked, problematic, key, platform_id))

    # A platform's own configuration -----------------------------------------------------------

    def own_config(self, folder: str) -> dict | None:
        row = self._db.execute("SELECT config_json FROM platforms WHERE folder = ?", (folder,)).fetchone()
        return json.loads(row[0]) if row and row[0] is not None else None

    def set_own_config(self, folder: str, values: dict | None) -> None:
        """Stores the platform's own configuration; None goes back to the default configuration."""
        platform_id = self._platform_id(folder)
        with self._db:
            self._db.execute("UPDATE platforms SET config_json = ?, summary_key = NULL WHERE id = ?",
                             (None if values is None else json.dumps(values, ensure_ascii=False), platform_id))
