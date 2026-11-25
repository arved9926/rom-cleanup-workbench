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

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rom_cleanup_workbench import (
    Config, FileFacts, GroupResult, ZipMember, _is_hidden, decide, known_checksums, read_facts, rom_files, rom_files_with_stat,
    scan_facts,
)

# The state of a platform in the overview.
NOT_SCANNED = "not_scanned"
NO_GAMES = "no_games"  # set by hand: the folder holds no games; never scanned, never opened
CURRENT = "current"
CHANGED = "changed"

DATABASE_FOLDER = ".rom_cleanup_workbench"
DATABASE_NAME = "rom_cleanup_workbench.sqlite"
SCHEMA_VERSION = 4  # 2: platforms.no_games; 3: game_info, media, gamelist_files; 4: gamelist_files.source
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
    config_json TEXT,
    no_games INTEGER NOT NULL DEFAULT 0
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
-- What the gamelist.xml (and later the workbench) knows about a ROM; rom is relative to the platform folder.
CREATE TABLE IF NOT EXISTS game_info (
    platform_id INTEGER NOT NULL REFERENCES platforms(id) ON DELETE CASCADE,
    rom TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'game',
    name TEXT, sortname TEXT, description TEXT, rating REAL, release_date TEXT,
    developer TEXT, publisher TEXT, genre TEXT, players TEXT, region TEXT, lang TEXT,
    favorite INTEGER, hidden INTEGER, kidgame INTEGER, playcount INTEGER, playtime INTEGER, last_played TEXT,
    xml_id TEXT,
    extra_json TEXT,
    edited_json TEXT,
    created INTEGER NOT NULL DEFAULT 0,
    UNIQUE (platform_id, rom)
);
-- 1:n: the media of a ROM, one row per category (one file may serve several categories).
CREATE TABLE IF NOT EXISTS media (
    platform_id INTEGER NOT NULL REFERENCES platforms(id) ON DELETE CASCADE,
    rom TEXT,
    category TEXT NOT NULL,
    path TEXT NOT NULL,
    origin TEXT NOT NULL,
    size INTEGER,
    mtime_ns INTEGER,
    UNIQUE (platform_id, rom, category, path)
);
-- The gamelist.xml read last: to see whether it changed, and what its import reported.
CREATE TABLE IF NOT EXISTS gamelist_files (
    platform_id INTEGER NOT NULL UNIQUE REFERENCES platforms(id) ON DELETE CASCADE,
    size INTEGER,
    mtime_ns INTEGER,
    sha256 TEXT,
    imported_at TEXT,
    provider_json TEXT,
    entries INTEGER,
    problems_json TEXT,
    notes_json TEXT,
    source TEXT
);
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


def tr_error(key: str, **values) -> str:
    from translations import tr

    return tr(key, **values)


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
        if version < 2:  # an older database gets the new column; nothing else changes
            with self._db:
                self._db.execute("ALTER TABLE platforms ADD COLUMN no_games INTEGER NOT NULL DEFAULT 0")
                self._db.execute("UPDATE schema_info SET version = 2")
        if version < 3:  # the new tables were created above
            with self._db:
                self._db.execute("UPDATE schema_info SET version = 3")
        if version < 4:  # where the gamelist.xml was read; a table created above has it already
            columns = {row[1] for row in self._db.execute("PRAGMA table_info(gamelist_files)")}
            with self._db:
                if "source" not in columns:
                    self._db.execute("ALTER TABLE gamelist_files ADD COLUMN source TEXT")
                self._db.execute("UPDATE schema_info SET version = 4")

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

    def forget_missing(self) -> list[str]:
        """The folder is what counts: drops every platform whose folder is gone, with its files, its
        changes by hand, its confirmed saves, its own settings and its "no games" mark. Nothing is
        dropped while the roms folder itself cannot be reached (a share that is offline, say)."""
        if not self.root.is_dir():
            return []
        gone = [folder for (folder,) in self._db.execute("SELECT folder FROM platforms")
                if not (self.root / folder).is_dir()]
        if gone:
            with self._db:  # files, zip members, saves and changes by hand go with it (ON DELETE CASCADE)
                self._db.executemany("DELETE FROM platforms WHERE folder = ?", [(folder,) for folder in gone])
        return gone

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

    def file_stamps(self, folder: str) -> dict[str, tuple[int | None, int | None]]:
        """Name -> (size, change time) of the files of the last scan."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return {}
        return {name: (size, mtime) for name, size, mtime in self._db.execute(
            "SELECT name, size, mtime_ns FROM files WHERE platform_id = ?", (platform_id,))}

    def state(self, directory: Path, stamps: dict | None = None) -> str:
        """no_games, not_scanned, current or changed: compares names, sizes and change times only (fast)."""
        directory = Path(directory)
        if self.is_no_games(directory.name):
            return NO_GAMES
        if self.platform(directory.name).last_scan is None:
            return NOT_SCANNED
        if stamps is None:
            stamps = _stamps(directory)
        if stamps != self.file_stamps(directory.name):
            return CHANGED
        return CHANGED if gamelist_changed(self, directory) else CURRENT

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
            # Deleted is deleted: what was known about the game goes as well.
            for table in ("game_info", "media"):
                self._db.executemany(f"DELETE FROM {table} WHERE platform_id = ? AND rom = ?",
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
            for table in ("game_info", "media"):
                self._db.execute(f"UPDATE {table} SET rom = ? WHERE platform_id = ? AND rom = ?",
                                 (new, platform_id, old))
            self._db.execute("UPDATE platforms SET summary_key = NULL WHERE id = ?", (platform_id,))

    # Confirmed status or save files ------------------------------------------------------------

    def confirmed(self, folder: str) -> dict[str, int]:
        """File name -> size of the status or save files confirmed when deleting."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return {}
        return dict(self._db.execute("SELECT name, size FROM confirmed_saves WHERE platform_id = ?", (platform_id,)))

    def add_confirmed(self, folder: str, files: dict[str, int]) -> None:
        platform_id = self._platform_id(folder)
        with self._db:
            self._db.executemany("INSERT OR REPLACE INTO confirmed_saves (platform_id, name, size) VALUES (?, ?, ?)",
                                 [(platform_id, name, size) for name, size in files.items()])

    # Changes by hand (k and x) -----------------------------------------------------------------

    def save_move(self, folder: str, name: str, size: int | None, mtime_ns: int | None, decision: str | None) -> None:
        """Remembers k ("keep") or x ("delete") for a file; None forgets it (the file is back where the rules put it)."""
        platform_id = self._platform_id(folder)
        with self._db:
            self._db.execute("DELETE FROM manual_moves WHERE platform_id = ? AND name = ?", (platform_id, name))
            if decision is not None:
                self._db.execute("INSERT INTO manual_moves (platform_id, name, size, mtime_ns, decision) "
                                 "VALUES (?, ?, ?, ?, ?)", (platform_id, name, size, mtime_ns, decision))

    def moves(self, folder: str) -> dict[str, tuple[int | None, int | None, str]]:
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return {}
        return {name: (size, mtime, decision) for name, size, mtime, decision in self._db.execute(
            "SELECT name, size, mtime_ns, decision FROM manual_moves WHERE platform_id = ?", (platform_id,))}

    def clear_moves(self, folder: str) -> None:
        platform_id = self._platform_id(folder, create=False)
        if platform_id is not None:
            with self._db:
                self._db.execute("DELETE FROM manual_moves WHERE platform_id = ?", (platform_id,))

    # What the gamelist.xml says ----------------------------------------------------------------

    def gamelist_record(self, folder: str) -> dict | None:
        """The gamelist.xml read last: stamp, number of entries, problems and notes; None if none."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return None
        row = self._db.execute("SELECT size, mtime_ns, sha256, imported_at, provider_json, entries, problems_json, "
                               "notes_json, source FROM gamelist_files WHERE platform_id = ?", (platform_id,)).fetchone()
        if row is None:
            return None
        return {"size": row[0], "mtime_ns": row[1], "sha256": row[2], "imported_at": row[3],
                "provider": json.loads(row[4]) if row[4] else None, "entries": row[5],
                "problems": json.loads(row[6] or "[]"), "notes": json.loads(row[7] or "[]"), "source": row[8]}

    def set_gamelist_source(self, folder: str, source: str | None) -> None:
        """Where the gamelist.xml was read or written: None for the platform folder, else its full path."""
        platform_id = self._platform_id(folder)
        with self._db:
            self._db.execute("UPDATE gamelist_files SET source = ? WHERE platform_id = ?", (source, platform_id))

    def save_gamelist(self, folder: str, gamelist, stamp: tuple, sha256: str | None, media_stamps: dict,
                      when: datetime | None = None) -> None:
        """Takes over a checked gamelist: new values replace the old ones, except fields edited by hand.
        Entries the gamelist no longer has stay: the gamelist.xml is input, not the master."""
        from workbench_gamelist import COLUMNS

        platform_id = self._platform_id(folder)
        moment = (when or datetime.now()).isoformat(timespec="seconds")
        with self._db:
            if not gamelist.unreadable:
                edited = {rom: set(json.loads(value or "[]")) for rom, value in self._db.execute(
                    "SELECT rom, edited_json FROM game_info WHERE platform_id = ?", (platform_id,))}
                for entry in gamelist.entries:
                    keep = edited.get(entry.rom, set())
                    values = {column: entry.values.get(column) for column in COLUMNS if column not in keep}
                    values.update(xml_id=entry.xml_id, created=0,
                                  extra_json=json.dumps(entry.extra, ensure_ascii=False) if entry.extra else None)
                    if "kind" not in keep:  # "no game" set by hand (n) stays
                        values["kind"] = entry.kind
                    names = ", ".join(values)
                    marks = ", ".join("?" * len(values))
                    updates = ", ".join(f"{name} = excluded.{name}" for name in values)
                    self._db.execute(f"INSERT INTO game_info (platform_id, rom, {names}) VALUES (?, ?, {marks}) "
                                     f"ON CONFLICT (platform_id, rom) DO UPDATE SET {updates}",
                                     (platform_id, entry.rom, *values.values()))
                    for category, path in entry.media:
                        size, mtime = media_stamps.get(path, (None, None))
                        self._db.execute("INSERT INTO media (platform_id, rom, category, path, origin, size, mtime_ns) "
                                         "VALUES (?, ?, ?, ?, 'gamelist', ?, ?) ON CONFLICT DO UPDATE SET "
                                         "size = excluded.size, mtime_ns = excluded.mtime_ns",
                                         (platform_id, entry.rom, category, path, size, mtime))
            entries = None if gamelist.unreadable else len(gamelist.entries)
            self._db.execute(
                "INSERT INTO gamelist_files (platform_id, size, mtime_ns, sha256, imported_at, provider_json, "
                "entries, problems_json, notes_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (platform_id) DO UPDATE SET size = excluded.size, mtime_ns = excluded.mtime_ns, "
                "sha256 = excluded.sha256, imported_at = excluded.imported_at, "
                "provider_json = COALESCE(excluded.provider_json, provider_json), "
                "entries = excluded.entries, problems_json = excluded.problems_json, "
                "notes_json = excluded.notes_json",
                (platform_id, stamp[0], stamp[1], sha256, moment,
                 json.dumps(gamelist.provider, ensure_ascii=False) if gamelist.provider else None, entries,
                 json.dumps([item.as_dict() for item in gamelist.problems], ensure_ascii=False),
                 json.dumps([item.as_dict() for item in gamelist.notes], ensure_ascii=False)))

    def mark_gamelist_written(self, folder: str, stamp: tuple, sha256: str, entries: int, provider: list) -> None:
        """The gamelist.xml was written from the database: it counts as read, without problems."""
        platform_id = self._platform_id(folder)
        moment = datetime.now().isoformat(timespec="seconds")
        with self._db:
            self._db.execute(
                "INSERT INTO gamelist_files (platform_id, size, mtime_ns, sha256, imported_at, provider_json, entries, "
                "problems_json, notes_json) VALUES (?, ?, ?, ?, ?, ?, ?, '[]', '[]') ON CONFLICT (platform_id) DO UPDATE "
                "SET size = excluded.size, mtime_ns = excluded.mtime_ns, sha256 = excluded.sha256, "
                "imported_at = excluded.imported_at, provider_json = excluded.provider_json, entries = excluded.entries, "
                "problems_json = '[]', notes_json = '[]'",
                (platform_id, stamp[0], stamp[1], sha256, moment, json.dumps(provider, ensure_ascii=False), entries))

    def touch_gamelist(self, folder: str, stamp: tuple) -> None:
        """The gamelist.xml has a new change time but the same content: only the stamp is new."""
        platform_id = self._platform_id(folder)
        with self._db:
            self._db.execute("UPDATE gamelist_files SET size = ?, mtime_ns = ? WHERE platform_id = ?",
                             (stamp[0], stamp[1], platform_id))

    def forget_missing_info(self, folder: str, directory: Path, rom_names) -> None:
        """The folder is what counts: information on ROMs that are gone, and media whose file is gone, go."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return
        directory = Path(directory)
        rom_names = set(rom_names)
        rows = self._db.execute("SELECT rom, kind FROM game_info WHERE platform_id = ?", (platform_id,)).fetchall()
        gone = [rom for rom, kind in rows
                if ((not (directory / rom).is_dir()) if kind == "folder" else rom not in rom_names)]
        known = {rom for rom, _kind in rows} - set(gone)
        media = self._db.execute("SELECT rom, category, path FROM media WHERE platform_id = ?",
                                 (platform_id,)).fetchall()
        listings: dict[Path, set] = {}

        def present(path: str) -> bool:  # one listing per folder, not a call per file (network drives)
            if Path(path).is_absolute():
                return Path(path).is_file()
            parent, _, file_name = path.rpartition("/")
            folder = directory / parent if parent else directory
            if folder not in listings:
                try:
                    with os.scandir(folder) as entries:
                        listings[folder] = {entry.name for entry in entries if entry.is_file()}
                except OSError:
                    listings[folder] = set()
            return file_name in listings[folder]

        lost = [(rom, category, path) for rom, category, path in media
                if (rom is not None and rom not in known) or not present(path)]
        if not gone and not lost:
            return
        with self._db:
            self._db.executemany("DELETE FROM game_info WHERE platform_id = ? AND rom = ?",
                                 [(platform_id, rom) for rom in gone])
            self._db.executemany("DELETE FROM media WHERE platform_id = ? AND rom IS ? AND category = ? "
                                 "AND path = ?", [(platform_id, *item) for item in lost])

    def info_count(self, folder: str) -> int:
        """ROMs of the list with information: from the gamelist.xml, or an empty entry with media found."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return 0
        return self._db.execute(
            "SELECT COUNT(*) FROM game_info g WHERE g.platform_id = ? AND g.kind = 'game' AND (g.created = 0 OR "
            "EXISTS (SELECT 1 FROM media m WHERE m.platform_id = g.platform_id AND m.rom = g.rom))",
            (platform_id,)).fetchone()[0]

    def ensure_entries(self, folder: str, rom_names) -> set[str]:
        """Every ROM of the list gets a row: an empty entry for a game, "no game" for a BIOS file.
        Returns the ROMs that are no game."""
        from workbench_gamelist import is_bios, title_of

        platform_id = self._platform_id(folder)
        rows = dict(self._db.execute("SELECT rom, kind FROM game_info WHERE platform_id = ?", (platform_id,)))
        new = []
        for rom in rom_names:
            if rom in rows:
                continue
            kind = "no_game" if is_bios(rom) else "game"
            rows[rom] = kind
            new.append((platform_id, rom, kind, None if kind == "no_game" else title_of(rom)))
        if new:
            with self._db:
                self._db.executemany("INSERT INTO game_info (platform_id, rom, kind, name, created) "
                                     "VALUES (?, ?, ?, ?, 1)", new)
        return {rom for rom, kind in rows.items() if kind == "no_game"}

    def set_no_game(self, folder: str, rom: str, no_game: bool) -> None:
        """n in the list: the file is no game (a BIOS file, say), or is one again. Kept against later imports."""
        from workbench_gamelist import title_of

        platform_id = self._platform_id(folder)
        row = self._db.execute("SELECT edited_json, created, name FROM game_info WHERE platform_id = ? AND rom = ?",
                               (platform_id, rom)).fetchone()
        with self._db:
            if row is None:
                self._db.execute("INSERT INTO game_info (platform_id, rom, kind, name, created) VALUES (?, ?, ?, ?, 1)",
                                 (platform_id, rom, "game", title_of(rom)))
                row = (None, 1, title_of(rom))
            edited = set(json.loads(row[0] or "[]"))
            if no_game:
                edited.add("kind")
                self._db.execute("DELETE FROM media WHERE platform_id = ? AND rom = ? AND origin = 'found'",
                                 (platform_id, rom))
            else:
                edited.discard("kind")
            name = row[2] if row[2] or not row[1] else title_of(rom)
            self._db.execute("UPDATE game_info SET kind = ?, edited_json = ?, name = ? WHERE platform_id = ? AND rom = ?",
                             ("no_game" if no_game else "game", json.dumps(sorted(edited)) if edited else None, name,
                              platform_id, rom))

    def media_only_of(self, folder: str, roms) -> list[str]:
        """The media files (inside the platform folder) that belong to these ROMs and to no other one."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None or not roms:
            return []
        gone = set(roms)
        rows = self._db.execute("SELECT rom, path FROM media WHERE platform_id = ? AND rom IS NOT NULL",
                                (platform_id,)).fetchall()
        used_elsewhere = {path for rom, path in rows if rom not in gone}
        return sorted({path for rom, path in rows
                       if rom in gone and path not in used_elsewhere and not Path(path).is_absolute()})

    def rename_media(self, folder: str, directory: Path, old: str, new: str) -> tuple[int, list[str]]:
        """Renames the media named after a ROM with it: "001 Game-image.png" with "001 Game.nes".
        A medium another ROM uses too, or whose new name is taken, stays. Returns (renamed, errors)."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return 0, []
        old_stem, new_stem = Path(old).stem, Path(new).stem
        rows = self._db.execute("SELECT rom, path FROM media WHERE platform_id = ?", (platform_id,)).fetchall()
        mine = sorted({path for rom, path in rows if rom == old})
        others = {path for rom, path in rows if rom != old}
        count, errors = 0, []
        for path in mine:
            medium = Path(path)
            name = medium.name
            rest = name[len(old_stem):]
            if (medium.is_absolute() or path in others or not name.casefold().startswith(old_stem.casefold())
                    or not rest or rest[0] not in "-._"):
                continue
            target = medium.parent / (new_stem + rest)
            if (directory / target).exists():
                errors.append(tr_error("error.rename_exists", name=name, new=target.name))
                continue
            try:
                (directory / medium).rename(directory / target)
            except OSError as error:
                errors.append(f"{path}: {error}")
                continue
            with self._db:
                self._db.execute("UPDATE media SET path = ? WHERE platform_id = ? AND path = ?",
                                 (target.as_posix(), platform_id, path))
            count += 1
        return count, errors

    def save_edits(self, folder: str, rom: str, values: dict) -> list[str]:
        """Fields changed by hand: stored and kept against later imports of the gamelist.xml.
        An empty entry becomes a real one. Returns the columns that changed."""
        from workbench_gamelist import title_of

        platform_id = self._platform_id(folder)
        row = self._db.execute("SELECT edited_json FROM game_info WHERE platform_id = ? AND rom = ?",
                               (platform_id, rom)).fetchone()
        with self._db:
            if row is None:
                self._db.execute("INSERT INTO game_info (platform_id, rom, kind, name, created) VALUES (?, ?, 'game', ?, 1)",
                                 (platform_id, rom, title_of(rom)))
                row = (None,)
            current = self._db.execute(f"SELECT {', '.join(values)} FROM game_info WHERE platform_id = ? AND rom = ?",
                                       (platform_id, rom)).fetchone()
            changed = [column for column, old in zip(values, current) if values[column] != old
                       and not (values[column] in (0, None) and old in (0, None))]
            if not changed:
                return []
            edited = set(json.loads(row[0] or "[]")) | set(changed)
            assignments = ", ".join(f"{column} = ?" for column in changed)
            self._db.execute(f"UPDATE game_info SET {assignments}, edited_json = ?, created = 0 "
                             "WHERE platform_id = ? AND rom = ?",
                             (*(values[column] for column in changed), json.dumps(sorted(edited)), platform_id, rom))
        return changed

    def gamelist_media_paths(self, folder: str) -> set[str]:
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return set()
        return {path for (path,) in self._db.execute(
            "SELECT path FROM media WHERE platform_id = ? AND origin = 'gamelist'", (platform_id,))}

    def save_found_media(self, folder: str, found) -> None:
        """The media found in the subfolders replace those found before; the gamelist's links stay."""
        platform_id = self._platform_id(folder)
        with self._db:
            self._db.execute("DELETE FROM media WHERE platform_id = ? AND origin = 'found'", (platform_id,))
            self._db.executemany(
                "INSERT OR IGNORE INTO media (platform_id, rom, category, path, origin, size, mtime_ns) "
                "VALUES (?, ?, ?, ?, 'found', ?, ?)",
                [(platform_id, rom, category, path, *stamp) for rom, category, path, stamp in found.assigned]
                + [(platform_id, None, category, path, *stamp) for category, path, stamp in found.unassigned])

    def media_counts(self, folder: str) -> tuple[int, int]:
        """(media files assigned to a ROM, media files without one)."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return 0, 0
        assigned = self._db.execute("SELECT COUNT(DISTINCT path) FROM media WHERE platform_id = ? AND rom IS NOT NULL",
                                    (platform_id,)).fetchone()[0]
        unassigned = self._db.execute("SELECT COUNT(*) FROM media WHERE platform_id = ? AND rom IS NULL",
                                      (platform_id,)).fetchone()[0]
        return assigned, unassigned

    def game_info(self, folder: str) -> dict[str, dict]:
        """rom -> its information: the columns, extra, xml_id, created and media by category."""
        from workbench_gamelist import COLUMNS

        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return {}
        info = {}
        for row in self._db.execute(f"SELECT rom, kind, {', '.join(COLUMNS)}, xml_id, extra_json, created, "
                                    "edited_json FROM game_info WHERE platform_id = ?", (platform_id,)):
            values = dict(zip(COLUMNS, row[2:2 + len(COLUMNS)]))
            values.update(rom=row[0], kind=row[1], xml_id=row[-4], extra=json.loads(row[-3] or "[]"),
                          created=bool(row[-2]), edited=set(json.loads(row[-1] or "[]")) - {"kind"}, media={})
            info[row[0]] = values
        for rom, category, path in self._db.execute("SELECT rom, category, path FROM media WHERE platform_id = ? "
                                                    "ORDER BY category, path", (platform_id,)):
            if rom in info:
                info[rom]["media"].setdefault(category, []).append(path)
        return info

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

    def is_no_games(self, folder: str) -> bool:
        row = self._db.execute("SELECT no_games FROM platforms WHERE folder = ?", (folder,)).fetchone()
        return bool(row and row[0])

    def set_no_games(self, folder: str, no_games: bool) -> None:
        """Marks a folder as holding no games; what the database knew about it is dropped."""
        platform_id = self._platform_id(folder)
        with self._db:
            if no_games:
                for table in ("files", "manual_moves", "confirmed_saves", "game_info", "media",
                              "gamelist_files"):
                    self._db.execute(f"DELETE FROM {table} WHERE platform_id = ?", (platform_id,))
                self._db.execute("UPDATE platforms SET last_scan = NULL, files = NULL, games = NULL, marked = NULL, "
                                 "problematic = NULL, summary_key = NULL WHERE id = ?", (platform_id,))
            self._db.execute("UPDATE platforms SET no_games = ? WHERE id = ?", (int(no_games), platform_id))

    def set_own_config(self, folder: str, values: dict | None) -> None:
        """Stores the platform's own configuration; None goes back to the default configuration."""
        platform_id = self._platform_id(folder)
        with self._db:
            self._db.execute("UPDATE platforms SET config_json = ?, summary_key = NULL WHERE id = ?",
                             (None if values is None else json.dumps(values, ensure_ascii=False), platform_id))


# A platform of a collection ---------------------------------------------------------------------

def collection_root(directory: Path) -> Path | None:
    """The roms folder whose database knows this platform folder; None for a folder on its own."""
    parent = Path(directory).parent
    return parent if (parent / DATABASE_FOLDER / DATABASE_NAME).is_file() else None


# Raised whenever the rules decide differently, so that the overview counts again (no scan needed).
# 2: save files stay only next to a kept file of their name (2026-11-24).
# 3: a delete keyword leaves "(Japan, USA)" alone when USA is in the priority list (2026-11-24).
# 4: {} counts as a bracket like () and [] (2026-11-24).
RULES_VERSION = 4


def config_key(config: Config) -> str:
    """Fingerprint of the settings that decide, so that the overview knows when to count again."""
    values = {
        "rules": RULES_VERSION,
        "region_priority": config.region_priority, "region_aliases": config.region_aliases,
        "delete_tags": config.delete_tags, "part_tags": config.part_tags, "prefer_zip": config.prefer_zip,
        "prefer_played": config.prefer_played,
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def summary_of(results: list[GroupResult]) -> tuple[int, int, int]:
    """Games, marked files and problematic games, as the overview shows them."""
    return (len(results), sum(len(result.marked) for result in results),
            sum(1 for result in results if result.problems))


def _stamps(directory: Path) -> dict[str, tuple[int | None, int | None]]:
    try:
        return {path.name: (stat.st_size, stat.st_mtime_ns) for path, stat in rom_files_with_stat(directory)}
    except OSError:  # a folder that cannot be read counts as changed
        return {}


def quick_scan_facts(directory: Path, old: list[FileFacts], progress=None) -> tuple[list[FileFacts], int]:
    """Reads only new and changed files; unchanged ones (name, size, change time) keep their facts.

    Returns the facts and how many files were read. progress(done, total) counts all files.
    """
    known = {item.name: item for item in old}
    files = rom_files(directory)
    if progress:
        progress(0, len(files))
    facts, read = [], 0
    for done, path in enumerate(files, 1):
        try:
            stat = path.stat()
            stamp = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            stamp = (None, None)
        item = known.get(path.name)
        if item is not None and (item.size, item.mtime_ns) == stamp and stamp != (None, None):
            facts.append(item)
        else:
            facts.append(read_facts(path))
            read += 1
        if progress:
            progress(done, len(files))
    return facts, read


def scan_platform(collection: "Collection", directory: Path, progress=None, full: bool = False) -> int:
    """Scans a platform and stores the facts: quickly (only changes) or fully. Returns the files read."""
    name = Path(directory).name
    old = None if full else collection.load_facts(name)
    if old is None:
        facts = scan_facts(directory, progress)
        read = len(facts)
    else:
        facts, read = quick_scan_facts(directory, old, progress)
    collection.save_facts(name, facts)
    collection.clear_moves(name)  # a new scan starts from the rules again
    names = [item.name for item in facts]
    import_gamelist(collection, directory, names, force=full)
    update_media(collection, directory, names)
    return read


def update_media(collection: "Collection", directory: Path, rom_names) -> None:
    """Every ROM gets its row (an empty entry, or "no game" for a BIOS file), then the subfolders are
    searched for media the gamelist.xml does not link."""
    from workbench_gamelist import find_media

    name = Path(directory).name
    no_games = collection.ensure_entries(name, rom_names)
    games = [rom for rom in rom_names if rom not in no_games]
    known = collection.gamelist_media_paths(name)
    found = find_media(directory, games, known)
    from workbench_gamelist import media_places

    for place in media_places(directory):  # ES-DE's downloaded_media, RetroPie's downloaded_images ...
        more = find_media(directory, games, known, root=place)
        found.assigned += more.assigned
        found.unassigned += more.unassigned
    collection.save_found_media(name, found)


def _gamelist_stamp(directory: Path) -> tuple | None:
    from workbench_gamelist import find_gamelist

    path = find_gamelist(directory)
    try:
        stat = path.stat() if path is not None else None
    except OSError:
        return None
    return None if stat is None else (stat.st_size, stat.st_mtime_ns)


def _source_of(directory: Path, path: Path) -> str | None:
    """None for the platform folder's own gamelist.xml, else the full path (ES-DE, RetroPie)."""
    return None if Path(path).parent == Path(directory) else str(path)


def gamelist_changed(collection: "Collection", directory: Path) -> bool:
    """A gamelist.xml that is new or changed since it was read; a deleted one changes nothing."""
    stamp = _gamelist_stamp(directory)
    if stamp is None:
        return False
    record = collection.gamelist_record(Path(directory).name)
    return record is None or (record["size"], record["mtime_ns"]) != stamp


def import_gamelist(collection: "Collection", directory: Path, rom_names, force: bool = False) -> bool:
    """Reads the platform's gamelist.xml if it changed (or force) and takes over what checks out.
    Afterwards information on ROMs and media that are gone is dropped. Returns whether it was read."""
    from workbench_gamelist import find_gamelist, read_gamelist

    directory = Path(directory)
    name = directory.name
    read = False
    stamp = _gamelist_stamp(directory)
    if stamp is not None and (force or gamelist_changed(collection, directory)):
        path = find_gamelist(directory)  # the platform folder's own, else ES-DE's or RetroPie's
        try:
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            sha = None
        record = collection.gamelist_record(name)
        if not force and sha is not None and record is not None and record["sha256"] == sha:
            collection.touch_gamelist(name, stamp)
        else:
            gamelist = read_gamelist(path, directory, rom_names)
            collection.save_gamelist(name, gamelist, stamp, sha, gamelist.media_stamps)
            collection.set_gamelist_source(name, _source_of(directory, path))
            read = True
    collection.forget_missing_info(name, directory, rom_names)
    return read


def gamelist_summary(directory: Path | None) -> str:
    """For the platform line: what the last gamelist.xml brought; empty without one."""
    from translations import tr

    if directory is None:
        return ""
    directory = Path(directory)
    root = collection_root(directory)
    if root is None:
        return ""
    with Collection(root) as collection:
        record = collection.gamelist_record(directory.name)
        assigned, unassigned = collection.media_counts(directory.name)
    parts = []
    if record is not None and record["entries"] is None:
        line = next((item.get("line") for item in record["problems"] if item.get("kind") == "xml_error"), None)
        parts.append(tr("gamelist.unreadable", line=line or "?"))
    elif record is not None:
        parts.append(tr("gamelist.summary", entries=record["entries"], problems=len(record["problems"]),
                        notes=len(record["notes"])))
    if record is not None and record.get("source"):
        parts[-1] += "  " + tr("gamelist.from", path=record["source"])
    if assigned or unassigned:
        parts.append(tr("media.summary", assigned=assigned, unassigned=unassigned))
    return "    ".join(parts)


def open_platform(root: Path, directory: Path, config: Config, progress=None,
                  rescan: bool = False, full: bool = False) -> list[GroupResult]:
    """Decides a platform from the database; scans it first if it was never scanned or rescan is set.

    A rescan is quick (only new and changed files) unless full is set. A folder marked "no games"
    is neither scanned nor opened (ValueError).
    """
    name = Path(directory).name
    with Collection(root) as collection:
        if collection.is_no_games(name):
            from translations import tr

            raise ValueError(tr("overview.no_games_locked", platform=name))
    with Collection(root) as collection:
        facts = None if rescan else collection.load_facts(name)
        if facts is None:
            scan_platform(collection, directory, progress, full=full)
            facts = collection.load_facts(name)
        results = decide(directory, facts, config)
        apply_played(results, collection.game_info(name), config.prefer_played)
        collection.update_checksums(name, known_checksums(results))
        collection.save_summary(name, *summary_of(results), key=config_key(config))
        _apply_moves(collection, name, facts, results, config)
    return results


def _apply_moves(collection: "Collection", name: str, facts: list[FileFacts], results: list[GroupResult],
                 config: Config) -> None:
    """Applies the remembered k and x; a move of a file that changed since is forgotten."""
    from rom_cleanup_workbench import Review

    moves = collection.moves(name)
    if not moves:
        return
    stamps = {item.name: (item.size, item.mtime_ns) for item in facts}
    review = Review(results, config)
    for result in results:
        for entry in list(result.keep + result.marked):
            move = moves.pop(entry.path.name, None)
            if move is None:
                continue
            size, mtime, decision = move
            if stamps.get(entry.path.name) != (size, mtime):
                collection.save_move(name, entry.path.name, None, None, None)
            elif decision == "keep" and entry in result.marked:
                review.promote(result, entry)
            elif decision == "delete" and entry in result.keep:
                review.demote(result, entry)
    for gone in moves:  # files that are no longer there
        collection.save_move(name, gone, None, None, None)


def record_move(root: Path, directory: Path, entry, kept: bool) -> None:
    """After k or x: remembers the file's new place, or forgets it if it is back where the rules put it."""
    try:
        stat = entry.path.stat()
        size, mtime = stat.st_size, stat.st_mtime_ns
    except OSError:
        size, mtime = None, None
    decision = ("keep" if kept else "delete") if entry.moved else None
    with Collection(root) as collection:
        collection.save_move(Path(directory).name, entry.path.name, size, mtime, decision)


def record_changes(root: Path, directory: Path, deleted: list[str], renamed: list[tuple[str, str]],
                   results: list[GroupResult], config: Config) -> tuple[int, int, list[str]]:
    """After Proceed: deleted and renamed files go into the database, and the overview numbers.

    The media of deleted ROMs are deleted as well, unless a remaining ROM uses them too; media named
    after a renamed ROM are renamed with it. Returns (media deleted, media renamed, errors).
    """
    name = Path(directory).name
    directory = Path(directory)
    errors: list[str] = []
    removed = renamed_media = 0
    with Collection(root) as collection:
        for path in collection.media_only_of(name, deleted):
            try:
                (directory / path).unlink()
                removed += 1
            except FileNotFoundError:
                pass
            except OSError as error:
                errors.append(f"{path}: {error}")
        collection.clear_moves(name)  # Proceed has carried out the changes by hand
        collection.remove_files(name, deleted)
        for old, new in renamed:
            try:
                mtime = (directory / new).stat().st_mtime_ns
            except OSError:
                mtime = None
            count, problems = collection.rename_media(name, directory, old, new)
            renamed_media += count
            errors.extend(problems)
            collection.rename_file(name, old, new, mtime)
        collection.save_summary(name, *summary_of(results), key=config_key(config))
    return removed, renamed_media, errors


def media_to_delete(root: Path, directory: Path, names: list[str]) -> list[str]:
    """For the question before deleting: the media that go with these ROMs."""
    with Collection(root) as collection:
        return collection.media_only_of(Path(directory).name, names)


def is_played(info: dict | None) -> bool:
    """A favorite, or a game with play time or a play count (gamelist.xml)."""
    return bool(info) and info.get("kind") == "game" and bool(
        info.get("favorite") or (info.get("playtime") or 0) > 0 or (info.get("playcount") or 0) > 0)


def apply_played(results: list[GroupResult], info: dict[str, dict], prefer: bool) -> None:
    """The setting "favorites and played games" after the rules have decided.

    Always: a file to delete that is a favorite or was played gets a note. With prefer: within a
    game, the favorite (else the file played longest, else most often) is kept; if the rules kept
    a single other file, that one gives way. Save files follow the kept file of their name.
    """
    from rom_cleanup_workbench import Note, _has_note, find_problems, save_file_stem

    for result in results:
        if prefer:
            candidates = [entry for entry in result.keep + result.marked
                          if is_played(info.get(entry.path.name)) and save_file_stem(entry.path) is None]
            if candidates:
                best = max(candidates, key=lambda entry: (bool(info[entry.path.name].get("favorite")),
                                                          info[entry.path.name].get("playtime") or 0,
                                                          info[entry.path.name].get("playcount") or 0))
                if best in result.marked:
                    result.marked.remove(best)
                    roms = [entry for entry in result.keep if save_file_stem(entry.path) is None]
                    if len(roms) == 1:
                        gone = roms[0]
                        result.keep.remove(gone)
                        gone.notes.append(Note("replaced_by_played", name=best.path.name))
                        result.marked.insert(0, gone)
                        for save in [entry for entry in result.keep if save_file_stem(entry.path) is not None
                                     and save_file_stem(entry.path).casefold() == gone.path.stem.casefold()]:
                            result.keep.remove(save)
                            save.notes.append(Note("save_orphan", name=save_file_stem(save.path)))
                            result.marked.append(save)
                    best.notes.append(Note("kept_played"))
                    result.keep.insert(0, best)
                    for save in [entry for entry in result.marked if _has_note(entry.notes, "save_orphan")
                                 and (save_file_stem(entry.path) or "").casefold() == best.path.stem.casefold()]:
                        result.marked.remove(save)
                        save.notes[:] = [note for note in save.notes if getattr(note, "kind", None) != "save_orphan"]
                        result.keep.append(save)
                    result.problems = find_problems(result.keep, result.marked)
        for entry in result.marked:
            if is_played(info.get(entry.path.name)) and not _has_note(entry.notes, "played_marked"):
                entry.notes.append(Note("played_marked"))


# The overview ----------------------------------------------------------------------------------

# Files a roms folder may hold besides its platform folders: notes, pictures, documents.
SIDE_FILE_EXTENSIONS = frozenset({
    ".txt", ".nfo", ".diz", ".md", ".pdf", ".rtf", ".doc", ".docx", ".htm", ".html", ".url", ".log",
    ".ini", ".xml", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
})


def is_collection(folder: Path) -> bool:
    """A roms folder: it has a database, or it holds no ROM files itself (side files such as
    info.txt do not count) but platform folders."""
    folder = Path(folder)
    if (folder / DATABASE_FOLDER / DATABASE_NAME).is_file():
        return True
    try:
        if any(path.suffix.casefold() not in SIDE_FILE_EXTENSIONS for path in rom_files(folder)):
            return False
    except OSError:
        return False
    return any(child.is_dir() and not _is_hidden(child) for child in folder.iterdir())


@dataclass
class OverviewRow:
    """One line of the overview: a platform folder and what the database knows about it."""

    folder: str
    state: str
    files: int | None = None
    games: int | None = None
    marked: int | None = None
    problematic: int | None = None
    last_scan: str | None = None
    has_own_config: bool = False
    has_games: bool = True  # False: not a single game file in the folder (side files do not count)
    info: int | None = None  # ROMs of the list with information from the gamelist.xml
    gamelist_problems: int | None = None  # what the last gamelist.xml import did not take over; None: none read


def overview(root: Path, config: Config) -> list[OverviewRow]:
    """The platforms of a collection; numbers computed with other settings are computed again (no scan).
    What the database knows about folders that are gone is dropped first."""
    with Collection(root) as collection:
        collection.forget_missing()
        return [_overview_row(collection, directory, config) for directory in collection.platform_folders()]


def _overview_row(collection: "Collection", directory: Path, config: Config) -> OverviewRow:
    """One platform's row; numbers computed with other settings are computed again (no scan)."""
    name = directory.name
    if collection.is_no_games(name):
        return OverviewRow(name, NO_GAMES, has_own_config=collection.own_config(name) is not None, has_games=False)
    stamps = _stamps(directory)
    state = collection.state(directory, stamps)
    row = collection.platform(name)
    effective = with_own_settings(config, collection.own_config(name))
    key = config_key(effective)
    if state != NOT_SCANNED and row.summary_key != key:
        results = decide(directory, collection.load_facts(name), effective)
        apply_played(results, collection.game_info(name), effective.prefer_played)
        collection.update_checksums(name, known_checksums(results))
        collection.save_summary(name, *summary_of(results), key=key)
        row = collection.platform(name)
    record = collection.gamelist_record(name)
    return OverviewRow(name, state, row.files, row.games, row.marked, row.problematic,
                       row.last_scan, row.has_own_config, has_game_files(stamps),
                       None if state == NOT_SCANNED else collection.info_count(name),
                       None if record is None else len(record["problems"]))


def has_game_files(names) -> bool:
    """At least one file that is no side file such as info.txt, a picture or a PDF."""
    return any(Path(name).suffix.casefold() not in SIDE_FILE_EXTENSIONS for name in names)


class ScanCancelled(Exception):
    """Raised by a progress callback to stop a batch scan; finished platforms stay saved."""


def scan_all(root: Path, full: bool = False, progress=None, config: Config | None = None,
             finished_row=None) -> list[tuple[str, int, int]]:
    """Scans every platform folder one after the other and saves each at once.

    progress(platform, number, count, done, total) reports the state; it may raise ScanCancelled.
    With a configuration, finished_row(OverviewRow) gets each platform's numbers as soon as it is done.
    Returns (platform, files, files read) for every finished platform. Never deletes anything.
    """
    finished = []
    with Collection(root) as collection:
        folders = [directory for directory in collection.platform_folders()
                   if not collection.is_no_games(directory.name)]
        for number, directory in enumerate(folders, 1):
            def report(done, total, directory=directory, number=number):
                if progress:
                    progress(directory.name, number, len(folders), done, total)

            read = scan_platform(collection, directory, report, full=full)
            finished.append((directory.name, collection.platform(directory.name).files or 0, read))
            if config is not None:
                row = _overview_row(collection, directory, config)
                if finished_row is not None:
                    finished_row(row)
    return finished


def confirmed_saves_of(root: Path, directory: Path, from_settings: dict[str, int]) -> dict[str, int]:
    """The confirmed files of a platform, keyed as save_file_key does.

    Files confirmed before the collection existed (in the settings file) are taken over once.
    """
    from rom_cleanup_workbench import save_file_key

    directory = Path(directory)
    own = os.path.normcase(os.path.abspath(directory))
    older = {Path(key).name: size for key, size in from_settings.items()
             if os.path.normcase(os.path.dirname(key)) == own}
    with Collection(root) as collection:
        known = collection.confirmed(directory.name)
        new = {name: size for name, size in older.items() if name not in known}
        if new:
            collection.add_confirmed(directory.name, new)
            known.update(new)
    return {save_file_key(directory / name): size for name, size in known.items()}


def add_confirmed_saves_to(root: Path, directory: Path, files: dict[str, int]) -> None:
    """Remembers confirmed files (keyed as save_file_key does) in the platform's database."""
    with Collection(root) as collection:
        collection.add_confirmed(Path(directory).name, {Path(key).name: size for key, size in files.items()})


# A platform's own settings --------------------------------------------------------------------

OWN_KEYS = ("region_priority", "delete_tags", "prefer_zip", "prefer_played")


def with_own_settings(config: Config, own: dict | None) -> Config:
    """The default configuration with the platform's own priority, delete keywords and ZIP choice."""
    if not own:
        return config
    from dataclasses import replace

    return replace(config, **{key: own[key] for key in OWN_KEYS if key in own})


def platform_config(root: Path, directory: Path, config: Config) -> Config:
    with Collection(root) as collection:
        return with_own_settings(config, collection.own_config(Path(directory).name))


def settings_for(config_file, root: Path | None, platform: str | None, own: bool | None = None) -> tuple[dict, bool]:
    """The values the settings show: the default file, or a platform's own values.

    own None: as stored; True/False: show those values (a new own configuration starts from the default).
    Returns (values, own).
    """
    values = config_file.read()
    if root is None or platform is None:
        return values, False
    with Collection(root) as collection:
        stored = collection.own_config(platform)
    if own is None:
        own = stored is not None
    if own and stored:
        values = dict(values, **{key: stored[key] for key in OWN_KEYS if key in stored})
    return values, bool(own)


def save_settings_for(config_file, root: Path | None, platform: str | None, own: bool, language: str,
                      region_priority: list[str], delete_tags: list[str], prefer_zip: bool,
                      prefer_played: bool | None = None) -> None:
    """Saves the settings: into the default file, or as the platform's own (the language always into the file)."""
    from rom_cleanup_workbench import Config, _clean_names
    from translations import tr

    if root is None or platform is None or not own:
        config_file.write(language, region_priority, delete_tags, prefer_zip, prefer_played)
        if root is not None and platform is not None:
            with Collection(root) as collection:
                collection.set_own_config(platform, None)
        return
    regions = _clean_names(region_priority)
    if not regions:
        raise ValueError(tr("settings.no_regions"))
    tags = _clean_names(delete_tags)
    Config(regions, {}, tags, [], prefer_zip=bool(prefer_zip))  # the same checks as for the file
    current = config_file.read()
    config_file.write(language, current["region_priority"], current["delete_tags"], current["prefer_zip"],
                      current["prefer_played"])
    if prefer_played is None:
        prefer_played = current["prefer_played"]
    with Collection(root) as collection:
        collection.set_own_config(platform, {"region_priority": regions, "delete_tags": tags,
                                             "prefer_zip": bool(prefer_zip),
                                             "prefer_played": bool(prefer_played)})


def settings_location(config_file, root: Path | None, own: bool) -> str:
    """Where the settings are saved: the configuration file, or a platform's own in the database."""
    from translations import tr

    if own and root is not None:
        return tr("settings.saved_in_db", file=Path(config_file.path).name)
    return tr("settings.file", path=config_file.path)


def platform_label(directory: Path | None) -> str:
    """The open platform's name for "Platform: ...", with * if it has its own settings (as in the overview)."""
    if directory is None:
        return ""
    directory = Path(directory)
    root = collection_root(directory)
    if root is None:
        return directory.name
    with Collection(root) as collection:
        own = collection.own_config(directory.name) is not None
    return directory.name + (" *" if own else "")


def sort_rows(rows: list, column: str, descending: bool) -> list:
    """The overview's rows in the chosen order; rows without numbers (never scanned) always come last."""
    if column == "platform":
        return sorted(rows, key=lambda row: row.folder.casefold(), reverse=descending)
    known = [row for row in rows if getattr(row, column) is not None]
    unknown = [row for row in rows if getattr(row, column) is None]
    known.sort(key=lambda row: (getattr(row, column), row.folder.casefold()), reverse=descending)
    return known + sorted(unknown, key=lambda row: row.folder.casefold())


def toggle_no_games(root: Path, folder: str, config: Config) -> OverviewRow:
    """Key n in the overview: switches "no games" for a folder; returns its new row."""
    with Collection(root) as collection:
        collection.set_no_games(folder, not collection.is_no_games(folder))
        return _overview_row(collection, Path(root) / folder, config)


# Stage 3: the game view, "no game" by hand and the report ------------------------------------------

def load_game_info(directory: Path | None) -> dict[str, dict]:
    """rom -> what the database knows about it; empty for a folder on its own."""
    if directory is None:
        return {}
    directory = Path(directory)
    root = collection_root(directory)
    if root is None:
        return {}
    with Collection(root) as collection:
        return collection.game_info(directory.name)


def toggle_no_game(directory: Path, roms: list[str]) -> bool | None:
    """n: the files become "no game", or games again if all of them already are. Returns the new
    state; None if the folder is no platform of a collection or no file is given."""
    directory = Path(directory)
    root = collection_root(directory)
    if root is None or not roms:
        return None
    with Collection(root) as collection:
        info = collection.game_info(directory.name)
        no_game = not all(info.get(rom, {}).get("kind") == "no_game" for rom in roms)
        for rom in roms:
            collection.set_no_game(directory.name, rom, no_game)
    return no_game


def gamelist_report(directory: Path | None) -> dict | None:
    """For g: what the last gamelist.xml did not take over, its notes, ROMs without information,
    media without a ROM and the files that are no game; None for a folder on its own."""
    if directory is None:
        return None
    directory = Path(directory)
    root = collection_root(directory)
    if root is None:
        return None
    with Collection(root) as collection:
        record = collection.gamelist_record(directory.name)
        info = collection.game_info(directory.name)
        platform_id = collection._platform_id(directory.name, create=False)
        unassigned = [] if platform_id is None else collection._db.execute(
            "SELECT category, path FROM media WHERE platform_id = ? AND rom IS NULL ORDER BY path",
            (platform_id,)).fetchall()
    from workbench_view import shows_info

    return {
        "source": (record or {}).get("source"),
        "has_gamelist": record is not None,
        "problems": record["problems"] if record else [],
        "notes": record["notes"] if record else [],
        "without_info": sorted((rom for rom, item in info.items() if item["kind"] == "game" and not shows_info(item)),
                               key=str.casefold),
        "unassigned": [tuple(row) for row in unassigned],
        "no_games": sorted((rom for rom, item in info.items() if item["kind"] == "no_game"), key=str.casefold),
    }


# Stage 5: writing the gamelist.xml ------------------------------------------------------------------

def writable_entries(directory: Path) -> int:
    """How many games and folders a written gamelist.xml would hold (BIOS files and no games not)."""
    return sum(1 for item in load_game_info(directory).values() if item["kind"] in ("game", "folder"))


def write_gamelist(directory: Path, when: datetime | None = None) -> tuple[int, str | None]:
    """Writes the platform's gamelist.xml from the database; only when the user asks for it.

    The file there is first copied to gamelist.xml.<date_time>.bak (the last three copies stay).
    The new file is written under another name and then put in place, so that a break never leaves
    half a gamelist.xml. Afterwards it counts as read. Returns (entries written, backup name or None).
    """
    import shutil

    from workbench_gamelist import BACKUP_RE, BACKUPS_KEPT, GAMELIST_NAME, build_gamelist

    directory = Path(directory)
    root = collection_root(directory)
    if root is None:
        from translations import tr

        raise ValueError(tr("game.only_collection"))
    name = directory.name
    with Collection(root) as collection:
        entries = [item for item in collection.game_info(name).values() if item["kind"] in ("game", "folder")]
        if not entries:
            return 0, None
        record = collection.gamelist_record(name)
        provider = (record or {}).get("provider")
        text = build_gamelist(entries, provider, name)
        # Where it was read (ES-DE or RetroPie keep it outside), else in the platform folder.
        path = Path(record["source"]) if record and record.get("source") else directory / GAMELIST_NAME
        place = path.parent
        backup = None
        if path.exists():
            backup = f"{GAMELIST_NAME}.{(when or datetime.now()).strftime('%Y-%m-%d_%H%M%S')}.bak"
            shutil.copy2(path, place / backup)
        temporary = place / (GAMELIST_NAME + ".tmp")
        temporary.write_bytes(text.encode("utf-8"))
        os.replace(temporary, path)
        backups = sorted(item for item in os.listdir(place) if BACKUP_RE.match(item))
        for old in backups[:-BACKUPS_KEPT]:
            try:
                (place / old).unlink()
            except OSError:
                pass
        stat = path.stat()
        from workbench_gamelist import SOFTWARE, WEB

        lines = [list(item) for item in (provider or [])]
        tags = [tag for tag, _text in lines]
        for tag, value in (("system", name), ("software", SOFTWARE), ("web", WEB)):
            if tag in tags:
                if tag != "system":
                    lines[tags.index(tag)][1] = value
            else:
                lines.append([tag, value])
        collection.mark_gamelist_written(name, (stat.st_size, stat.st_mtime_ns),
                                         hashlib.sha256(text.encode("utf-8")).hexdigest(), len(entries), lines)
        collection.set_gamelist_source(name, _source_of(directory, path))
    return len(entries), backup


def platform_row(root: Path, folder: str, config: Config) -> OverviewRow:
    """One platform's overview row, as it is now."""
    with Collection(root) as collection:
        return _overview_row(collection, Path(root) / folder, config)


def write_all_gamelists(root: Path) -> list[tuple[str, int, str | None]]:
    """--write-gamelists: every platform with information; (platform, entries, backup) for each written."""
    written = []
    with Collection(root) as collection:
        folders = [directory for directory in collection.platform_folders() if not collection.is_no_games(directory.name)]
    for directory in folders:
        count, backup = write_gamelist(directory)
        if count:
            written.append((directory.name, count, backup))
    return written


# Stage 6: editing the game information ------------------------------------------------------------

def edit_game(directory: Path, rom: str, form: dict) -> list[str]:
    """Saves a filled-in edit form for a ROM; ValueError if a value is wrong. Returns the changed columns."""
    from workbench_view import parse_form

    directory = Path(directory)
    root = collection_root(directory)
    if root is None:
        from translations import tr

        raise ValueError(tr("game.only_collection"))
    values = parse_form(form)
    with Collection(root) as collection:
        return collection.save_edits(directory.name, rom, values)


def gamelist_path(directory: Path) -> Path:
    """Where the platform's gamelist.xml is read and written: the place recorded, the one found, or
    the platform folder."""
    from workbench_gamelist import GAMELIST_NAME, find_gamelist

    directory = Path(directory)
    root = collection_root(directory)
    if root is not None:
        with Collection(root) as collection:
            record = collection.gamelist_record(directory.name)
        if record and record.get("source"):
            return Path(record["source"])
    return find_gamelist(directory) or directory / GAMELIST_NAME

