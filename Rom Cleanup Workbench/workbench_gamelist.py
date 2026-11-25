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

"""Reading a platform's gamelist.xml (EmulationStation and its offshoots: RetroPie, Batocera, ES-DE).

The gamelist.xml is only input: what it says about the games is checked and goes into the
collection's database. An entry whose ROM is not in the platform folder and a link to a file that
does not exist are not taken over; they are reported. Nothing in the folder is changed.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

GAMELIST_NAME = "gamelist.xml"

# gamelist tag -> column of the database. Every other tag is kept as it is (extra).
FIELDS = {
    "name": "name", "sortname": "sortname", "desc": "description", "rating": "rating",
    "releasedate": "release_date", "developer": "developer", "publisher": "publisher", "genre": "genre",
    "players": "players", "region": "region", "lang": "lang", "favorite": "favorite", "hidden": "hidden",
    "kidgame": "kidgame", "playcount": "playcount", "playtime": "playtime", "lastplayed": "last_played",
}
COLUMNS = tuple(FIELDS.values())
_BOOLS = {"favorite", "hidden", "kidgame"}
_INTS = {"playcount", "playtime"}

# Tags that link a medium; the tag is its category and stays as it is (wheel and logo are not merged).
MEDIA_TAGS = frozenset({
    "image", "thumbnail", "marquee", "video", "wheel", "logo", "boxart", "box", "screenshot", "cartridge",
    "mix", "fanart", "titleshot", "manual", "magazine", "map", "bezel", "boxback", "cover", "backcover",
    "titlescreen", "3dbox", "physicalmedia", "miximage",
})

# Problems: what was not taken over. Notes: taken over, but worth knowing.
XML_ERROR, NO_PATH, DUPLICATE, ROM_MISSING, ROM_NOT_IN_LIST, MEDIA_MISSING = (
    "xml_error", "no_path", "duplicate", "rom_missing", "rom_not_in_list", "media_missing")
MAPPED, WRONG_CASE, OUTSIDE = "mapped", "wrong_case", "outside"

_DRIVE = re.compile(r"^[A-Za-z]:/")
_DATE = re.compile(r"^(\d{4})(\d{2})(\d{2})(?:T|$)")


@dataclass
class Report:
    """A problem or note: its kind, the path or name it is about and, for broken XML, the line."""

    kind: str
    path: str = ""
    line: int | None = None

    def as_dict(self) -> dict:
        return {"kind": self.kind, "path": self.path, **({"line": self.line} if self.line else {})}


@dataclass
class Entry:
    """One <game> or <folder> that was taken over."""

    rom: str  # relative to the platform folder, with /
    kind: str = "game"
    values: dict = field(default_factory=dict)  # column -> value
    extra: list = field(default_factory=list)  # [tag, text, attributes] of every other tag, in order
    xml_id: str | None = None
    media: list = field(default_factory=list)  # (category, path relative to the platform folder or absolute)


@dataclass
class Gamelist:
    entries: list[Entry] = field(default_factory=list)
    provider: list | None = None  # [tag, text] of the <provider> block, in order
    problems: list[Report] = field(default_factory=list)
    notes: list[Report] = field(default_factory=list)
    unreadable: bool = False
    media_stamps: dict = field(default_factory=dict)  # stored media path -> (size, change time)


class Resolver:
    """Finds the files a gamelist links, also with another spelling of upper and lower case.

    Works from folder listings, which on Windows already hold type, size and change time, so that
    thousands of links on a network drive need no call per file.
    """

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self._listings: dict[Path, tuple[dict, dict]] = {}
        self._entries: dict[Path, os.DirEntry] = {}

    def _listing(self, folder: Path) -> tuple[dict, dict]:
        if folder not in self._listings:
            entries: dict[str, os.DirEntry] = {}
            try:
                with os.scandir(folder) as found:
                    for entry in found:
                        entries[entry.name] = entry
            except OSError:
                pass
            folded: dict[str, str] = {}
            for name in sorted(entries):
                folded.setdefault(name.casefold(), name)
            self._listings[folder] = (entries, folded)
        return self._listings[folder]

    def _walk(self, parts: list[str]) -> tuple[Path | None, bool]:
        """The path below the platform folder as it is spelled on disk, and whether the spelling was exact."""
        current, exact, entry = self.directory, True, None
        for part in parts:
            if part in ("", "."):
                continue
            if part == "..":
                return None, False
            entries, folded = self._listing(current)
            real = part if part in entries else folded.get(part.casefold())
            if real is None:
                return None, False
            exact = exact and real == part
            entry = entries[real]
            current = current / real
        if entry is not None:
            self._entries[current] = entry
        return current, exact

    def is_file(self, path: Path) -> bool:
        entry = self._entries.get(path)
        try:
            return entry.is_file() if entry is not None else Path(path).is_file()
        except OSError:
            return False

    def is_dir(self, path: Path) -> bool:
        entry = self._entries.get(path)
        try:
            return entry.is_dir() if entry is not None else Path(path).is_dir()
        except OSError:
            return False

    def stamp(self, path: Path) -> tuple:
        """(size, change time) of a found file; from the listing where it can be."""
        entry = self._entries.get(path)
        try:
            stat = entry.stat() if entry is not None else Path(path).stat()
        except OSError:
            return None, None
        return stat.st_size, stat.st_mtime_ns

    def resolve(self, text: str) -> tuple[Path | None, str]:
        """(file, status): status ok, mapped, wrong_case or outside; (None, "missing") if not found."""
        raw = (text or "").strip().replace("\\", "/")
        if not raw:
            return None, "missing"
        if raw.startswith("~/"):
            return self._outside(Path.home() / raw[2:])
        if raw.startswith("/") or _DRIVE.match(raw):
            inside = self._inside_parts(raw)
            if inside is not None:
                return self._here(inside, "ok")
            parts = raw.split("/")
            folded = [part.casefold() for part in parts]
            name = self.directory.name.casefold()
            if name in folded:  # a path of another machine: /home/pi/RetroPie/roms/nes/x.png
                index = len(folded) - 1 - folded[::-1].index(name)
                found, status = self._here(parts[index + 1:], MAPPED)
                if found is not None:
                    return found, status
            return self._outside(Path(raw))
        if raw.startswith("./"):
            raw = raw[2:]
        return self._here(raw.split("/"), "ok")

    def _here(self, parts: list[str], status: str) -> tuple[Path | None, str]:
        found, exact = self._walk(parts)
        if found is None or found == self.directory:
            return None, "missing"
        return found, status if exact else WRONG_CASE

    def _inside_parts(self, raw: str) -> list[str] | None:
        """The parts below the platform folder of an absolute path that points into it; None otherwise."""
        base = self.directory.as_posix().rstrip("/") + "/"
        if raw.casefold().startswith(base.casefold()):
            return raw[len(base):].split("/")
        return None

    @staticmethod
    def _outside(path: Path) -> tuple[Path | None, str]:
        return (path, OUTSIDE) if path.exists() else (None, "missing")

    def relative(self, path: Path) -> str:
        """The path as stored: relative to the platform folder with /, or absolute if outside."""
        try:
            return Path(path).relative_to(self.directory).as_posix()
        except ValueError:
            return str(path)


def _text(element) -> str:
    return (element.text or "").strip()


def _value(tag: str, text: str):
    """The column value of a known tag; None if it cannot be read (it is then kept as extra)."""
    if tag == "rating":
        try:
            return float(text)
        except ValueError:
            return None
    if tag == "releasedate":
        match = _DATE.match(text)
        return f"{match[1]}-{match[2]}-{match[3]}" if match else None
    if tag in _BOOLS:
        return {"true": 1, "1": 1, "yes": 1, "false": 0, "0": 0, "no": 0}.get(text.casefold())
    if tag in _INTS:
        try:
            return int(text)
        except ValueError:
            return None
    return text


def read_gamelist(path: Path, directory: Path, rom_names) -> Gamelist:
    """Reads and checks a gamelist.xml. rom_names: the ROM files of the platform folder (its list)."""
    directory = Path(directory)
    rom_names = set(rom_names)
    result = Gamelist()
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        result.unreadable = True
        result.problems.append(Report(XML_ERROR, Path(path).name, error.position[0]))
        return result
    except OSError:
        result.unreadable = True
        result.problems.append(Report(XML_ERROR, Path(path).name))
        return result
    resolver = Resolver(directory)
    entries: dict[str, Entry] = {}
    for element in root:
        if element.tag == "provider":
            result.provider = [[child.tag, _text(child)] for child in element]
            continue
        if element.tag not in ("game", "folder"):
            continue
        entry = _read_entry(element, directory, rom_names, resolver, result)
        if entry is None:
            continue
        if entry.rom in entries:
            result.problems.append(Report(DUPLICATE, entry.rom))
            del entries[entry.rom]  # the last one counts, in its place
        entries[entry.rom] = entry
    result.entries = list(entries.values())
    return result


def _read_entry(element, directory: Path, rom_names: set, resolver: Resolver, result: Gamelist) -> Entry | None:
    path_text = element.findtext("path")
    if not path_text or not path_text.strip():
        result.problems.append(Report(NO_PATH, element.findtext("name") or ""))
        return None
    found, status = resolver.resolve(path_text)
    shown = path_text.strip()
    if found is None:
        result.problems.append(Report(ROM_MISSING, shown))
        return None
    kind = element.tag
    if kind == "game":
        if found.parent != directory or not resolver.is_file(found) or found.name not in rom_names:
            result.problems.append(Report(ROM_NOT_IN_LIST, shown))
            return None
    elif not resolver.is_dir(found) or status == OUTSIDE:
        result.problems.append(Report(ROM_NOT_IN_LIST, shown))
        return None
    if status != "ok":
        result.notes.append(Report(status, shown))
    entry = Entry(resolver.relative(found), kind)
    for name, value in element.attrib.items():
        if name == "id":
            entry.xml_id = value
        else:
            entry.extra.append(["@" + name, value, {}])
    for child in element:
        tag, text = child.tag, _text(child)
        if tag == "path":
            continue
        if tag in MEDIA_TAGS and text and not len(child):
            medium, medium_status = resolver.resolve(text)
            if medium is None or not resolver.is_file(medium):
                result.problems.append(Report(MEDIA_MISSING, text))
                continue
            stored = resolver.relative(medium)
            result.media_stamps.setdefault(stored, resolver.stamp(medium))
            if medium_status != "ok":
                result.notes.append(Report(medium_status, text))
            entry.media.append((tag, stored))
            continue
        if tag in FIELDS and text and not len(child) and not child.attrib:
            value = _value(tag, text)
            if value is not None:
                entry.values[FIELDS[tag]] = value
                continue
        if text or len(child) or child.attrib:
            entry.extra.append([tag, text if not len(child) else ET.tostring(child, encoding="unicode"),
                                dict(child.attrib)])
    return entry


# Stage 2: media in the subfolders ----------------------------------------------------------------

# Categories a folder name or a name ending may name; the category is kept as it is written.
CATEGORIES = MEDIA_TAGS | {"snap", "title", "thumb"}
MEDIA_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp",
    ".mp4", ".mkv", ".avi", ".webm", ".mov", ".m4v", ".wmv", ".flv",
    ".pdf", ".cbz", ".cbr",
})
_SEPARATORS = "-._"
_SKIPPED_FOLDERS = {".rom_cleanup_workbench"}


def category_of(word: str) -> str | None:
    """The category a folder name or name ending stands for (plural as singular); None if none."""
    word = word.casefold()
    if word in CATEGORIES:
        return word
    for ending in ("es", "s"):
        if word.endswith(ending) and word[:-len(ending)] in CATEGORIES:
            return word[:-len(ending)]
    return None


@dataclass
class FoundMedia:
    assigned: list = field(default_factory=list)  # (rom, category, path, (size, change time))
    unassigned: list = field(default_factory=list)  # (category or "other", path, (size, change time))


def find_media(directory: Path, rom_names, known_paths=()) -> FoundMedia:
    """Media in the subfolders of a platform, assigned to a ROM only where the name says so clearly.

    Two ways of keeping them are recognised:
    1. a folder per category, the file named like the ROM: wheel/10yard.png, marquees/10yard.png;
    2. any folder, the ROM's name, a separator (- . _) and a category: 10yard-wheel.png, game.image.jpg.
    If several ROM names fit, the longest wins (sf2ce-image.png is sf2ce, not sf2). Files the
    gamelist.xml already links (known_paths) are left out; files directly in the platform folder too.
    """
    directory = Path(directory)
    known = set(known_paths)
    stems: dict[str, list[str]] = {}
    exact: dict[str, list[str]] = {}
    for name in rom_names:
        stem = Path(name).stem
        exact.setdefault(stem, []).append(name)
        stems.setdefault(stem.casefold(), []).append(name)
    result = FoundMedia()
    pending = [directory]
    while pending:
        folder = pending.pop()
        try:
            with os.scandir(folder) as found:
                entries = sorted(found, key=lambda entry: entry.name)
        except OSError:
            continue
        for entry in entries:
            if entry.name.startswith(".") or entry.name in _SKIPPED_FOLDERS:
                continue
            try:
                if entry.is_dir():
                    pending.append(Path(entry.path))
                    continue
                if folder == directory or not entry.is_file():
                    continue
                if Path(entry.name).suffix.casefold() not in MEDIA_EXTENSIONS:
                    continue
                stat = entry.stat()
            except OSError:
                continue
            path = Path(entry.path).relative_to(directory).as_posix()
            if path in known:
                continue
            stamp = (stat.st_size, stat.st_mtime_ns)
            stem = Path(entry.name).stem
            folder_category = category_of(folder.name)
            roms, category = None, None
            if folder_category is not None:  # 1. a folder per category
                roms = exact.get(stem) or stems.get(stem.casefold())
                category = folder_category
            if not roms:  # 2. name, separator, category
                roms, category = _by_ending(stem, stems)
            if roms:
                for rom in roms:
                    result.assigned.append((rom, category, path, stamp))
            else:
                result.unassigned.append((folder_category or _ending_category(stem) or "other", path, stamp))
    return result


def _by_ending(stem: str, stems: dict) -> tuple[list | None, str | None]:
    folded = stem.casefold()
    best = None
    for index, character in enumerate(folded):
        if character not in _SEPARATORS:
            continue
        roms = stems.get(folded[:index])
        category = category_of(folded[index + 1:])
        if roms and category and (best is None or index > best[0]):
            best = (index, roms, category)
    return (best[1], best[2]) if best else (None, None)


def _ending_category(stem: str) -> str | None:
    for index in range(len(stem) - 1, -1, -1):
        if stem[index] in _SEPARATORS:
            return category_of(stem[index + 1:])
    return None


# BIOS files and other files that are not games ----------------------------------------------------

# Well-known BIOS sets of arcade emulators (file name without extension).
BIOS_NAMES = frozenset({
    "neogeo", "pgm", "skns", "cpzn1", "cpzn2", "decocass", "isgsm", "nss", "stvbios", "hng64", "naomi",
    "naomi2", "awbios", "chihiro", "triforce", "playch10", "megaplay", "konamigx", "qsound",
})
_BRACKETS = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]|\{([^{}]*)\}")


def is_bios(name: str, extra_names=()) -> bool:
    """A BIOS file: BIOS in a bracket ([BIOS] Neo Geo (World).zip) or a known BIOS name."""
    stem = Path(name).stem
    if stem.casefold() in BIOS_NAMES or stem.casefold() in {item.casefold() for item in extra_names}:
        return True
    for match in _BRACKETS.finditer(stem):
        content = next(group for group in match.groups() if group is not None)
        if re.search(r"\bbios\b", content, re.IGNORECASE):
            return True
    return False


def title_of(name: str) -> str:
    """The name of an empty entry: the text before the first bracket; the file name if there is none."""
    stem = Path(name).stem
    title = _BRACKETS.split(stem, maxsplit=1)[0].strip() if _BRACKETS.search(stem) else stem
    return title or stem


# Stage 5: writing the gamelist.xml ----------------------------------------------------------------

SOFTWARE = "RCW"  # our short name in the <provider> block
WEB = "https://github.com/arved9926/rom-cleanup-workbench"
_TAGS = {column: tag for tag, column in FIELDS.items()}


def _xml_text(column: str, value) -> str | None:
    """A column's value as the gamelist writes it; None for a default, which is left out."""
    if value is None or value == "":
        return None
    if column in ("favorite", "hidden", "kidgame"):
        return "true" if value else None
    if column in ("playcount", "playtime"):
        return str(int(value)) if value else None
    if column == "rating":
        return f"{float(value):g}"
    if column == "release_date" and re.match(r"^\d{4}-\d{2}-\d{2}$", str(value)):
        return str(value).replace("-", "") + "T000000"
    return str(value)


def _link(path: str) -> str:
    return path if Path(path).is_absolute() else "./" + path


def build_gamelist(entries: list[dict], provider: list | None, system: str) -> str:
    """The text of a gamelist.xml: every game and folder of entries (workbench_db.game_info values).

    The <provider> block names RCW and our GitHub page; its other lines stay. Known fields, media
    by category (a file serving two categories is written twice), the id and every further field
    as they were read. Values that are the default are left out, as EmulationStation does.
    """
    root = ET.Element("gameList")
    lines = [list(item) for item in (provider or [])]
    tags = [tag for tag, _text in lines]
    for tag, text in (("system", system), ("software", SOFTWARE), ("web", WEB)):
        if tag in tags:
            if tag != "system":
                lines[tags.index(tag)][1] = text
        else:
            lines.append([tag, text])
    order = {"system": 0, "software": 1, "web": 2}
    block = ET.SubElement(root, "provider")
    for tag, text in sorted(lines, key=lambda line: order.get(line[0], 3)):
        ET.SubElement(block, tag).text = text
    for entry in sorted(entries, key=lambda item: (item["kind"] != "folder", item["rom"].casefold())):
        if entry["kind"] not in ("game", "folder"):
            continue
        element = ET.SubElement(root, entry["kind"])
        if entry.get("xml_id"):
            element.set("id", str(entry["xml_id"]))
        extra = entry.get("extra") or []
        for tag, text, _attributes in extra:
            if tag.startswith("@"):
                element.set(tag[1:], text)
        ET.SubElement(element, "path").text = _link(entry["rom"])
        for column in COLUMNS:
            text = _xml_text(column, entry.get(column))
            if text is not None:
                ET.SubElement(element, _TAGS[column]).text = text
        for category in sorted(entry.get("media") or {}):
            for path in entry["media"][category]:
                ET.SubElement(element, category).text = _link(path)
        for tag, text, attributes in extra:
            if tag.startswith("@"):
                continue
            if text.startswith("<" + tag):
                try:
                    element.append(ET.fromstring(text))
                    continue
                except ET.ParseError:
                    pass
            child = ET.SubElement(element, tag, attributes or {})
            child.text = text
    ET.indent(root, "  ")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


BACKUP_RE = re.compile(r"^gamelist\.xml\.\d{4}-\d{2}-\d{2}_\d{6}\.bak$")
BACKUPS_KEPT = 3

