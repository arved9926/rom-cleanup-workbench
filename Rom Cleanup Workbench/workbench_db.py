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
CURRENT = "current"
CHANGED = "changed"

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

    def file_stamps(self, folder: str) -> dict[str, tuple[int | None, int | None]]:
        """Name -> (size, change time) of the files of the last scan."""
        platform_id = self._platform_id(folder, create=False)
        if platform_id is None:
            return {}
        return {name: (size, mtime) for name, size, mtime in self._db.execute(
            "SELECT name, size, mtime_ns FROM files WHERE platform_id = ?", (platform_id,))}

    def state(self, directory: Path, stamps: dict | None = None) -> str:
        """not_scanned, current or changed: compares names, sizes and change times only (fast)."""
        directory = Path(directory)
        if self.platform(directory.name).last_scan is None:
            return NOT_SCANNED
        if stamps is None:
            stamps = _stamps(directory)
        return CURRENT if stamps == self.file_stamps(directory.name) else CHANGED

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


# A platform of a collection ---------------------------------------------------------------------

def collection_root(directory: Path) -> Path | None:
    """The roms folder whose database knows this platform folder; None for a folder on its own."""
    parent = Path(directory).parent
    return parent if (parent / DATABASE_FOLDER / DATABASE_NAME).is_file() else None


def config_key(config: Config) -> str:
    """Fingerprint of the settings that decide, so that the overview knows when to count again."""
    values = {
        "region_priority": config.region_priority, "region_aliases": config.region_aliases,
        "delete_tags": config.delete_tags, "part_tags": config.part_tags, "prefer_zip": config.prefer_zip,
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
    return read


def open_platform(root: Path, directory: Path, config: Config, progress=None,
                  rescan: bool = False, full: bool = False) -> list[GroupResult]:
    """Decides a platform from the database; scans it first if it was never scanned or rescan is set.

    A rescan is quick (only new and changed files) unless full is set.
    """
    name = Path(directory).name
    with Collection(root) as collection:
        facts = None if rescan else collection.load_facts(name)
        if facts is None:
            scan_platform(collection, directory, progress, full=full)
            facts = collection.load_facts(name)
        results = decide(directory, facts, config)
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
                   results: list[GroupResult], config: Config) -> None:
    """After Proceed: deleted and renamed files go into the database, and the overview numbers."""
    name = Path(directory).name
    with Collection(root) as collection:
        collection.clear_moves(name)  # Proceed has carried out the changes by hand
        collection.remove_files(name, deleted)
        for old, new in renamed:
            try:
                mtime = (Path(directory) / new).stat().st_mtime_ns
            except OSError:
                mtime = None
            collection.rename_file(name, old, new, mtime)
        collection.save_summary(name, *summary_of(results), key=config_key(config))


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


def overview(root: Path, config: Config) -> list[OverviewRow]:
    """The platforms of a collection; numbers computed with other settings are computed again (no scan)."""
    with Collection(root) as collection:
        return [_overview_row(collection, directory, config) for directory in collection.platform_folders()]


def _overview_row(collection: "Collection", directory: Path, config: Config) -> OverviewRow:
    """One platform's row; numbers computed with other settings are computed again (no scan)."""
    name = directory.name
    stamps = _stamps(directory)
    state = collection.state(directory, stamps)
    row = collection.platform(name)
    effective = with_own_settings(config, collection.own_config(name))
    key = config_key(effective)
    if state != NOT_SCANNED and row.summary_key != key:
        results = decide(directory, collection.load_facts(name), effective)
        collection.update_checksums(name, known_checksums(results))
        collection.save_summary(name, *summary_of(results), key=key)
        row = collection.platform(name)
    return OverviewRow(name, state, row.files, row.games, row.marked, row.problematic,
                       row.last_scan, row.has_own_config, has_game_files(stamps))


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
        folders = collection.platform_folders()
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

OWN_KEYS = ("region_priority", "delete_tags", "prefer_zip")


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
                      region_priority: list[str], delete_tags: list[str], prefer_zip: bool) -> None:
    """Saves the settings: into the default file, or as the platform's own (the language always into the file)."""
    from rom_cleanup_workbench import Config, _clean_names
    from translations import tr

    if root is None or platform is None or not own:
        config_file.write(language, region_priority, delete_tags, prefer_zip)
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
    config_file.write(language, current["region_priority"], current["delete_tags"], current["prefer_zip"])
    with Collection(root) as collection:
        collection.set_own_config(platform, {"region_priority": regions, "delete_tags": tags,
                                             "prefer_zip": bool(prefer_zip)})


def settings_location(config_file, root: Path | None, own: bool) -> str:
    """Where the settings are saved: the configuration file, or a platform's own in the database."""
    from translations import tr

    if own and root is not None:
        return tr("settings.saved_in_db", folder=Path(root) / DATABASE_FOLDER, file=Path(config_file.path).name)
    return tr("settings.file", path=config_file.path)
