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

"""Rom Cleanup Workbench: finds duplicate ROM files in a directory and deletes them on request.

File names: <game name> (region or extra info) (...).<file type>
For each game name the file with the highest region priority is kept, all
others are marked for deletion. Details are in README.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
import zlib
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath

from translations import DEFAULT_LANGUAGE, LANGUAGES, NO_REGION_WORDS, set_language, tr

NO_REGION = "none"
REVIEW_ALL = "all"
REVIEW_PROBLEMS = "problems"
# The radio button values in the window; without --review the saved choice applies there.
_REVIEW_SCOPES = {REVIEW_ALL: "marked", REVIEW_PROBLEMS: "problems"}
DEFAULT_CONFIG_PATH = Path(__file__).with_name("redundanz_config.json")
DEFAULT_CONFIG = {
    # Entries after "none", such as "Beta", push a file back (see Config.rank). Japan stays a
    # region there, because it has other spellings: Japanese files come after files without region.
    "region_priority": ["USA", "Europe", NO_REGION, "Japan", "Beta"],
    # U, E and J are the short forms of GoodTools names such as "Title (J) [o1].nes".
    "region_aliases": {
        "USA": ["US", "U"],
        "Europe": ["Europa", "EU", "E"],
        "Japan": ["JP", "JPN", "J"],
    },
    # Extra info that marks a file for deletion (rule 2); none by default, the settings can add some.
    "delete_tags": [],
    "part_tags": ["Disc", "Disk", "CD", "Side", "Seite", "Part", "Teil", "Track"],
    "language": DEFAULT_LANGUAGE,
    # The same game as a plain file and as a ZIP file: false keeps the plain file, true the ZIP.
    "prefer_zip": False,
}

_TAG_RE = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]")
_EXT_RE = re.compile(r"\.[A-Za-z0-9]+$")
_SEPARATOR_RE = re.compile(r"[-_]")
_AND_RE = re.compile(r"\b(?:und|and)\b")
# Apostrophes do not count: Sullivan's = Sullivan`s = Sullivan´s = Sullivan’s = Sullivans.
_APOSTROPHE_RE = re.compile("['`\u00b4\u2019]")
# Roman numerals I to IX as whole words count as numbers: "Final Fantasy VII" = "Final Fantasy 7".
# Not X: "Mega Man X" and "Mega Man 10" are two games.
_ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9"}
_ROMAN_RE = re.compile(r"\b(?:viii|vii|vi|iv|ix|v|iii|ii|i)\b")
_AMPERSANDS_RE = re.compile("&+")  # "&&" = "&"
_VERSUS_RE = re.compile(r"\b(?:versus|vs)\b\.?")
# A number in front of the name, such as the "057" of a numbered collection, is no part of it:
# "057 Robocop", "057 - Robocop", "057. Robocop" = "Robocop". Not in "4 in 1", which names the game.
_LEADING_NUMBER_RE = re.compile(r"^\d+\.?\s+(?!in\s*\d)(?=\S)")
_THE_RE = re.compile(r"^the\s+|(?:,\s*|\s+)the,?$")
# In the game name only the form v1.1 counts, so that "Title V2" stays a title of its own.
_NAME_VERSION_RE = re.compile(r"[\s_-]+(v\d+(?:\.\d+)+)$", re.IGNORECASE)
_VERSION_TAG_RE = re.compile(
    r"(?:v|ver\.?|version|rev\.?|revision)\s*(\d+(?:\.\d+)*)|rev(?:ision)?\s+([a-z])",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)*")
_CHUNK_SIZE = 1024 * 1024
_NO_ROM_PREFIX = "gamelist"  # Metadata of frontends such as gamelist.xml: No ROM, so never marked.
_SAVE_FILE_RATIO = 4  # A marked file below 1/4 of the largest file of the game is kept.
_HIDDEN_ATTRIBUTE = 0x2  # FILE_ATTRIBUTE_HIDDEN, the same value as stat.FILE_ATTRIBUTE_HIDDEN.
_ZIP_DEFECT_ERRORS = (zipfile.BadZipFile, EOFError, zlib.error)
# These errors say nothing about the archive: The file may be locked or use a
# method Python does not know, such as Deflate64 in large Windows ZIPs.
_ZIP_READ_ERRORS = (RuntimeError, NotImplementedError, OSError)


class Note(str):
    """A note as shown, in the current language; kind is the same in every language.

    The rules ask for the kind, never for the text, so that every language decides the same way.
    """

    kind: str

    def __new__(cls, kind: str, **values) -> "Note":
        note = super().__new__(cls, tr("note." + kind, **values))
        note.kind = kind
        note.values = values  # kept, so that a note can be stored and shown again
        return note


def _has_note(notes, *kinds: str) -> bool:
    return any(getattr(note, "kind", None) in kinds for note in notes)


def normalize(text: str) -> str:
    """Unifies text for comparisons (MaME = MAME = mame)."""
    return " ".join(text.split()).casefold()


def game_key(game: str) -> str:
    """Comparison key: "&" = "&&" = "und" = "and", "vs" = "vs." = "versus", "Sullivan's" = "Sullivans",
    "The X" = "X The" = "X, The" = "X", "057 X" = "X", "X VII" = "X 7" (I to IX) and
    "Pac-Man" = "Pac Man" = "Pac_Man" = "PacMan".

    "und" becomes "&" so that "H & M" does not turn into "Hund M" once the spaces are removed.
    """
    text = normalize(_SEPARATOR_RE.sub(" ", _AMPERSANDS_RE.sub(" & ", _APOSTROPHE_RE.sub("", game))))
    text = _LEADING_NUMBER_RE.sub("", text)
    # After the number in front: "I Robot" is a name, not the number 1 in front of "Robot".
    text = _ROMAN_RE.sub(lambda match: _ROMAN[match.group()], text)
    key = _VERSUS_RE.sub("vs", text)
    key = _AND_RE.sub("&", key)
    key = _THE_RE.sub("", key) or key
    # Names made only of separators stay titles of their own instead of collapsing into an empty name.
    return key.replace(" ", "") or normalize(game)


# The same number in the file name, with what separates it from the name: "073 ", "073 - ", "073_".
_FILE_NUMBER_RE = re.compile(r"^\d+\.?[\s_-]+")
# Files that name other files in their content: renaming those files would break them.
_INDEX_SUFFIXES = {".cue", ".gdi", ".m3u", ".mds", ".toc", ".ccd"}


def has_leading_number(game: str) -> bool:
    """True for "073 Batman": the number in front of the name that game_key ignores."""
    return bool(_LEADING_NUMBER_RE.match(normalize(_SEPARATOR_RE.sub(" ", game))))


def game_title(entry: "Entry") -> str:
    """The name shown for a game: without a number in front ("073 Batman" -> "Batman")."""
    if has_leading_number(entry.game):
        return _FILE_NUMBER_RE.sub("", entry.game, count=1)
    return entry.game


def parse_filename(filename: str) -> tuple[str, list[str]]:
    """Splits a file name into the game name and the bracket contents."""
    game, groups = parse_tag_groups(filename)
    return game, [tag for group in groups for tag in group]


def parse_tag_groups(filename: str) -> tuple[str, list[list[str]]]:
    """Like parse_filename, but keeps the parts of each bracket together.

    "(USA, Japan)" is one group with two parts, "(USA) (Beta)" two groups: the priority list
    counts the best entry within a group and the worst group (see Config.rank).
    A version in the game name ("Title v1.1") is a group of its own.
    """
    ext_match = _EXT_RE.search(filename)
    ext = ext_match.group() if ext_match else ""
    stem = filename[: -len(ext)] if ext else filename

    first_tag = _TAG_RE.search(stem)
    game = (stem[: first_tag.start()] if first_tag else stem).strip()
    # "Katz und Maus.abc (Japan).abc": The file type also appears before the bracket.
    if ext and game.casefold().endswith(ext.casefold()):
        game = game[: -len(ext)].strip()

    groups = []
    name_version = _NAME_VERSION_RE.search(game)
    if name_version:
        groups.append([name_version.group(1)])
        game = game[: name_version.start()].strip()

    for match in _TAG_RE.finditer(stem):
        content = match.group(1) if match.group(1) is not None else match.group(2)
        parts = [part.strip() for part in content.split(",") if part.strip()]
        if parts:
            groups.append(parts)
    return game or stem.strip(), groups


def _matches_tag(tag: str, names: list[str]) -> bool:
    """Checks for the same word at the start: "Proto 2" matches "Proto", "Protocol" does not."""
    tag = normalize(tag)
    for name in names:
        name = normalize(name)
        if tag.startswith(name) and not tag[len(name):len(name) + 1].isalpha():
            return True
    return False


def _contains_word(tag: str, name: str) -> bool:
    """The word anywhere in the bracket part: "Micks Hack" and "Hack 2" contain "Hack", "Hackers" does not."""
    tag, name = normalize(tag), normalize(name)
    if not name:
        return False
    start = tag.find(name)
    while start >= 0:
        end = start + len(name)
        if not tag[start - 1:start].isalpha() and not tag[end:end + 1].isalpha():
            return True
        start = tag.find(name, start + 1)
    return False


def version_number(tags: list[str]) -> tuple[int, ...]:
    """Returns the highest version number: v1.10 > v1.9 and v1.0 = v1; without a version ()."""
    best: tuple[int, ...] = ()
    for tag in tags:
        match = _VERSION_TAG_RE.fullmatch(normalize(tag))
        if not match:
            continue
        if match.group(1):
            parts = [int(part) for part in match.group(1).split(".")]
        else:
            parts = [ord(match.group(2)) - ord("a") + 1]
        while parts and parts[-1] == 0:
            parts.pop()
        best = max(best, tuple(parts))
    return best


def _newest_first(tags: list[str]) -> tuple[int, ...]:
    """Sort key: higher versions first, v1.1 also before v1."""
    return tuple(-part for part in version_number(tags)) + (1,)


def _plain_canonical(tag: str) -> str:
    """Without the aliases of a configuration: only the words for "none" of every language."""
    text = normalize(tag)
    return NO_REGION if text in {normalize(word) for word in NO_REGION_WORDS} else text


def with_old_low_priority(regions: list[str], low_priority: list[str], canonical=_plain_canonical) -> list[str]:
    """The priority list with the low priority tags of an old file appended as keywords.

    They go after "none", which is added if missing; tags already in the list stay where they are.
    """
    merged = list(regions)
    if low_priority and not any(canonical(entry) == NO_REGION for entry in merged):
        merged.append(NO_REGION)
    known = {canonical(entry) for entry in merged}
    for tag in low_priority:
        if canonical(tag) not in known:
            merged.append(tag)
            known.add(canonical(tag))
    return merged


# Entries of old files that are still read; the settings drop them when they save.
LEGACY_CONFIG_KEYS = {"low_priority_tags": list}


@dataclass
class Config:
    region_priority: list[str]
    region_aliases: dict[str, list[str]]
    delete_tags: list[str]
    part_tags: list[str]
    low_priority_tags: list[str] = field(default_factory=list)
    language: str = DEFAULT_LANGUAGE
    prefer_zip: bool = False
    _canonical: dict[str, str] = field(init=False, repr=False)

    def __post_init__(self):
        self._canonical = {
            normalize(alias): normalize(region)
            for region, aliases in self.region_aliases.items()
            for alias in aliases
        }
        # "keine", "aucune" and so on mean the same as "none" in region_priority.
        for word in NO_REGION_WORDS:
            self._canonical.setdefault(normalize(word), NO_REGION)
        # Old low priority tags become keywords at the end of the list, after "none".
        if self.low_priority_tags:
            self.region_priority = with_old_low_priority(self.region_priority, self.low_priority_tags,
                                                         self.canonical)
            self.low_priority_tags = []
        self._ranks = {}
        for index, region in enumerate(self.region_priority):
            self._ranks.setdefault(self.canonical(region), index)
        self._none_rank = self._ranks.get(NO_REGION, len(self.region_priority))
        # Regions with other spellings stay regions wherever they stand (for ZIP contents).
        self._aliased = {self.canonical(region) for region in self.region_aliases}

    @classmethod
    def load(cls, path: Path | None) -> "Config":
        """Loads the configuration; missing entries come from the defaults."""
        values = dict(DEFAULT_CONFIG)
        if path is not None:
            # utf-8-sig: Some Windows editors save with a BOM.
            with open(path, encoding="utf-8-sig") as handle:
                loaded = json.load(handle)
            if not isinstance(loaded, dict):
                raise ValueError(tr("config.not_object"))
            # A typo must not silently fall back to the defaults.
            unknown = sorted(set(loaded) - set(DEFAULT_CONFIG) - set(LEGACY_CONFIG_KEYS))
            if unknown:
                raise ValueError(tr("config.unknown_entries", names=", ".join(unknown)))
            for key, value in loaded.items():
                expected = LEGACY_CONFIG_KEYS.get(key) or type(DEFAULT_CONFIG[key])
                if not isinstance(value, expected):
                    raise ValueError(tr("config.wrong_type", key=key))
            values.update(loaded)
        if values["language"] not in LANGUAGES:
            raise ValueError(
                tr("config.unknown_language", language=values["language"], languages=", ".join(LANGUAGES))
            )
        # An old file's low priority tags become keywords after "none" (see __post_init__).
        return cls(**{key: values[key] for key in DEFAULT_CONFIG},
                   low_priority_tags=list(values.get("low_priority_tags", [])))

    def canonical(self, tag: str) -> str:
        normalized = normalize(tag)
        return self._canonical.get(normalized, normalized)

    def is_region(self, tag: str) -> bool:
        """A region of the list: an entry before "none", or one with other spellings anywhere.

        Keywords such as "Beta" after "none" are no regions: a ZIP does not lend them its name.
        """
        if tag == normalize(NO_REGION) or tag not in self._ranks:
            return False
        return self._ranks[tag] < self._none_rank or tag in self._aliased

    def _position(self, tag: str) -> int | None:
        """The place of a bracket part in the priority list; a keyword also matches "Beta 2"."""
        tag = self.canonical(tag)
        if tag == NO_REGION:
            return None
        if tag in self._ranks:
            return self._ranks[tag]
        positions = [index for index, entry in enumerate(self.region_priority)
                     if self.canonical(entry) != NO_REGION and _matches_tag(tag, [entry])]
        return min(positions) if positions else None

    def rank(self, tags: list[str], groups: list[list[str]] | None = None) -> tuple[int, int]:
        """Smaller is better: (the file's place, its best entry).

        Within one bracket the best entry counts ("(USA, Japan)" counts as USA), across
        brackets the worst ("(USA) (Beta)" counts as Beta): so an entry at the end of the list,
        such as Beta after "none", pushes a file back. Without any entry of the list, "none"
        applies. Among files in the same place, the best entry decides, but never better than
        "none": a Beta without region and a Beta from a region placed after "none" are equal.
        groups: the brackets; without them every tag counts as a bracket of its own.
        """
        groups = groups if groups is not None else [[tag] for tag in tags]
        bracket_places = []
        best = self._none_rank
        for group in groups:
            places = [place for place in map(self._position, group) if place is not None]
            if places:
                bracket_places.append(min(places))
                best = min(best, min(places))
        place = max(bracket_places) if bracket_places else self._none_rank
        return place, best

    def rank_label(self, index: int) -> str:
        """The entry of the priority list at this place, as written there; "none" past its end."""
        return self.region_priority[index] if index < len(self.region_priority) else NO_REGION

    def with_regions(self, regions: list[str]) -> list[str]:
        """--priority: these regions; without "none" in them, "none" and the keywords after it stay.

        So "--priority USA Europe Japan" still puts Betas last, as the configuration says.
        """
        if any(self.canonical(region) == NO_REGION for region in regions):
            return list(regions)
        keywords = self.region_priority[self._none_rank:] if self._none_rank < len(self.region_priority) else []
        given = {self.canonical(region) for region in regions}
        return list(regions) + [entry for entry in keywords if self.canonical(entry) not in given]

    def keyword_number(self, tags: list[str]) -> tuple[int, ...]:
        """Returns the highest number after an entry of the list: Beta 2 > Beta 1 > Beta; else ()."""
        best: tuple[int, ...] = ()
        for tag in tags:
            text = normalize(tag)
            for name in self.region_priority:
                if self.canonical(name) == NO_REGION or not _matches_tag(text, [name]):
                    continue
                match = _NUMBER_RE.fullmatch(text[len(normalize(name)):].strip())
                if match:
                    parts = [int(part) for part in match.group().split(".")]
                    while parts and parts[-1] == 0:
                        parts.pop()
                    best = max(best, tuple(parts))
        return best

    def delete_reason(self, tags: list[str]) -> str | None:
        """The first delete keyword found as a whole word anywhere in a bracket."""
        for name in self.delete_tags:
            if any(_contains_word(tag, name) for tag in tags):
                return name
        return None

    def version_key(self, tags: list[str]) -> frozenset[str]:
        """Files with the same key belong together (Disc 1 + 2, .cue + .bin)."""
        return frozenset(tag for tag in tags if not _matches_tag(tag, self.part_tags))


# The entries the settings may change; all others stay as they are.
EDITABLE_CONFIG_KEYS = ("language", "region_priority", "delete_tags", "prefer_zip")


def _format_json(value, indent: int = 0) -> str:
    """Like json.dumps with indent, but lists stay on one line, as in a hand-written file."""
    if isinstance(value, dict) and value:
        pad = " " * indent
        items = (f'{pad}  {json.dumps(key, ensure_ascii=False)}: {_format_json(item, indent + 2)}'
                 for key, item in value.items())
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    return json.dumps(value, ensure_ascii=False)


@dataclass
class ConfigFile:
    """The configuration file as the settings dialog reads and changes it."""

    path: Path

    def _load_raw(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            with open(self.path, encoding="utf-8-sig") as handle:
                raw = json.load(handle)
        except (OSError, ValueError) as error:
            raise ValueError(tr("config.unreadable", error=error)) from error
        if not isinstance(raw, dict):
            raise ValueError(tr("config.unreadable", error=tr("config.not_object")))
        return raw

    def read(self) -> dict:
        """The editable entries; missing ones come from the defaults.

        The low priority tags of an old file appear as keywords at the end of the priority
        list, as the analysis uses them; saving then writes them there.
        """
        raw = self._load_raw()
        values = {key: raw.get(key, DEFAULT_CONFIG[key]) for key in EDITABLE_CONFIG_KEYS}
        old = raw.get("low_priority_tags")
        if isinstance(old, list) and isinstance(values["region_priority"], list):
            values["region_priority"] = with_old_low_priority(values["region_priority"], old)
        return values

    def write(self, language: str, region_priority: list[str], delete_tags: list[str],
              prefer_zip: bool | None = None) -> None:
        """Checks the values and saves them; the file stays unchanged if anything is wrong.

        An old entry low_priority_tags is dropped: read() has put its tags into the priority list.
        prefer_zip None leaves that entry as it is.
        """
        regions = _clean_names(region_priority)
        if not regions:
            raise ValueError(tr("settings.no_regions"))
        tags = _clean_names(delete_tags)
        raw = self._load_raw()
        raw.pop("low_priority_tags", None)
        raw.update({"language": language, "region_priority": regions, "delete_tags": tags})
        if prefer_zip is not None:
            raw["prefer_zip"] = bool(prefer_zip)
        # The same checks as when loading, before anything is written.
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(_format_json(raw) + "\n", encoding="utf-8")
        try:
            Config.load(temporary)
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)


def _clean_names(names: list[str]) -> list[str]:
    """Drops empty entries and refuses the same name twice, regardless of case."""
    cleaned = []
    for name in (name.strip() for name in names):
        if not name:
            continue
        if any(normalize(name) == normalize(other) for other in cleaned):
            raise ValueError(tr("settings.duplicate", name=name))
        cleaned.append(name)
    return cleaned


@dataclass
class ZipMember:
    name: str
    size: int
    sha256: str


@dataclass
class Entry:
    path: Path
    game: str
    tags: list[str]
    members: list[ZipMember] | None = None
    zip_error: Note | None = None
    zip_defective: bool = False
    notes: list[str] = field(default_factory=list)
    moved: bool = False  # Moved by hand during the review, against the program's decision.
    # The tags bracket by bracket, for the priority list (Config.rank); None: each tag on its own.
    tag_groups: list[list[str]] | None = None
    _sha256: str | None = None
    _size: int | None = None
    zip_read: bool = False  # True once the ZIP contents (or its error) are known

    def content_size(self) -> int | None:
        """Size of the content: For a ZIP the unpacked size, so that packing counts for nothing.

        None for a ZIP that could not be read: Its archive size says nothing about the content.
        """
        if self.is_zip:
            return sum(member.size for member in self.members) if self.members is not None else None
        return self.size()

    def size(self) -> int | None:
        """File size in bytes, read once; None if the file cannot be read."""
        if self._size is None:
            try:
                self._size = self.path.stat().st_size
            except OSError:
                return None
        return self._size

    @property
    def is_zip(self) -> bool:
        return self.path.suffix.casefold() == ".zip"

    def sha256(self) -> str | None:
        if self._sha256 is None:
            digest = hashlib.sha256()
            try:
                with open(self.path, "rb") as handle:
                    while chunk := handle.read(_CHUNK_SIZE):
                        digest.update(chunk)
            except OSError:
                return None
            self._sha256 = digest.hexdigest()
        return self._sha256

    def contains(self, member: ZipMember) -> bool:
        """Checks whether the content of the ZIP member appears in this entry."""
        if self.is_zip:
            return any(other.sha256 == member.sha256 for other in self.members or [])
        try:
            if self.path.stat().st_size != member.size:
                return False
        except OSError:
            return False
        return self.sha256() == member.sha256


@dataclass
class GroupResult:
    title: str
    keep: list[Entry]
    marked: list[Entry]
    problems: list[str] = field(default_factory=list)


def read_zip(entry: Entry) -> None:
    """Reads the ZIP contents once and remembers their size and checksum."""
    if entry.zip_read:
        return
    entry.zip_read = True
    _read_zip(entry)


def _read_zip(entry: Entry) -> None:
    """Reads the ZIP contents and remembers their size and checksum.

    The contents are hashed directly while reading. This gives the same result
    as temporary extraction, but needs no disk space and rules out harmful
    paths in the archive.
    """
    members = []
    try:
        with zipfile.ZipFile(entry.path) as archive:
            infos = archive.infolist()
            if any(info.flag_bits & 0x1 for info in infos):
                entry.zip_error = Note("zip_encrypted")
                entry.zip_defective = True
                return
            for info in infos:
                if info.is_dir():
                    continue
                digest = hashlib.sha256()
                size = 0
                with archive.open(info) as handle:
                    while chunk := handle.read(_CHUNK_SIZE):
                        digest.update(chunk)
                        size += len(chunk)
                members.append(ZipMember(info.filename, size, digest.hexdigest()))
    except _ZIP_DEFECT_ERRORS as error:
        entry.zip_error = Note("zip_defective", error=str(error) or type(error).__name__)
        entry.zip_defective = True
        return
    except _ZIP_READ_ERRORS as error:
        entry.zip_error = Note("zip_unreadable", error=str(error) or type(error).__name__)
        return
    entry.members = members


def _adopt_tags_from_zip(entry: Entry, config: Config) -> None:
    """Takes over the region and version of the ZIP contents if the ZIP name does not state them."""
    regions = []
    versions = []
    for member in entry.members or []:
        game, tags = parse_filename(PurePosixPath(member.name).name)
        if game_key(game) != game_key(entry.game):
            continue
        for tag in map(config.canonical, tags):
            if config.is_region(tag) and tag not in regions:
                regions.append(tag)
            elif version_number([tag]):
                versions.append(tag)
    if regions and not any(config.is_region(tag) for tag in entry.tags):
        entry.tags.extend(regions)
        if entry.tag_groups is not None:
            entry.tag_groups.append(list(regions))  # like one bracket "(USA, Europe)"
        entry.notes.append(Note("region_from_zip", regions=", ".join(regions)))
    if versions and not version_number(entry.tags):
        newest = max(versions, key=lambda tag: version_number([tag]))
        entry.tags.append(newest)
        if entry.tag_groups is not None:
            entry.tag_groups.append([newest])
        entry.notes.append(Note("version_from_zip", version=newest))


def _covering_entries(entry: Entry, others: list[Entry]) -> list[Entry]:
    """Returns the entries that cover the whole ZIP content, otherwise an empty list."""
    if not entry.members:
        return []
    covering = []
    for member in entry.members:
        source = next((other for other in others if other.contains(member)), None)
        if source is None:
            return []
        if source not in covering:
            covering.append(source)
    return covering


def _plain_covered_by(entry: Entry, kept: list[Entry]) -> list[Entry] | None:
    """The kept files that hold the content of a plain file; None if it cannot be read.

    Sizes are compared first, so that a checksum is only computed when a kept file (or a file
    inside a kept ZIP) has the same size: large collections stay fast.
    """
    size = entry.size()
    if size is None:
        return None
    candidates = [
        other for other in kept
        if (other.is_zip and any(member.size == size for member in other.members or []))
        or (not other.is_zip and other.size() == size)
    ]
    if not candidates:
        return []
    digest = entry.sha256()
    if digest is None:
        return None
    content = ZipMember(entry.path.name, size, digest)
    return [other for other in candidates if other.contains(content)]


def _names(entries: list[Entry]) -> str:
    return ", ".join(entry.path.name for entry in entries)


def _rank(entry: Entry, config: Config) -> tuple[int, int]:
    return config.rank(entry.tags, entry.tag_groups)


def _sort_key(entry: Entry, config: Config):
    place, best = _rank(entry, config)
    return (
        place,
        best,
        _newest_first(entry.tags),
        # Like a version: The higher number wins, a Beta without a number loses to Beta 1.
        tuple(-part for part in config.keyword_number(entry.tags)) + (1,),
        # In a tie the name with a number in front wins ("073 Batman" before "Batman").
        not has_leading_number(entry.game),
        len(config.version_key(entry.tags)),
        entry.is_zip != config.prefer_zip,  # the preferred form first (prefer_zip)
        entry.path.name.casefold(),
    )


def find_problems(keep: list[Entry], marked: list[Entry]) -> list[str]:
    """Names the reasons why a person should look at this decision."""
    entries = keep + marked
    notes = [note for entry in entries for note in entry.notes]
    problems = []
    if not keep:
        problems.append(tr("problem.nothing_kept"))
    # Same version as a kept file, but other content: which dump is the right one?
    if _has_note(notes, "warning", "warning_plain"):
        problems.append(tr("problem.same_version_differs"))
    if any(entry.zip_defective for entry in entries):
        problems.append(tr("problem.zip_defective"))
    if any(entry.zip_error and not entry.zip_defective for entry in entries):
        problems.append(tr("problem.zip_unreadable"))
    if _has_note(notes, "save_suspected"):
        problems.append(tr("problem.save_file"))
    if _has_note(notes, "tie"):
        problems.append(tr("problem.tie"))
    if _has_note(notes, "differs"):
        problems.append(tr("problem.zip_differs"))
    # If names only match through the comparison, they may be two games ("Title 1-2", "Title 12").
    if len({normalize(entry.game) for entry in entries}) > 1:
        problems.append(tr("problem.spellings"))
    # Same name, different file type: This may be the same game for another system.
    kept_types = set()
    for entry in keep:
        if entry.is_zip:
            kept_types.update(PurePosixPath(member.name).suffix.casefold() for member in entry.members or [])
        else:
            kept_types.add(entry.path.suffix.casefold())
    if keep and any(not entry.is_zip and entry.path.suffix.casefold() not in kept_types for entry in marked):
        problems.append(tr("problem.file_type"))
    return problems


def _suspected_save_files(entries: list[Entry], config: Config) -> list[Entry]:
    """Finds files far smaller than another file of the game: maybe a status or save file.

    They are set aside before the selection, so that they neither get deleted nor push out
    the real ROM, for example a plain 1941.state the ZIP 1941.zip. A small plain file next to
    a large plain file of its own version, such as a .cue next to its .bin, is part of that
    version and is not suspected; a ZIP has no such companions outside. Neither is a file of the
    same type as the largest file (.nes next to .nes): it is a ROM. Files with delete_tags
    or a defective ZIP are not suspected: these rules always apply.
    """
    suspected = []
    for entry in entries:
        size = entry.content_size()
        if size is None or config.delete_reason(entry.tags) or entry.zip_defective:
            continue
        others = [other for other in entries if other is not entry and other.content_size() is not None]
        if not others:
            continue
        largest = max(others, key=lambda other: other.content_size())
        if size * _SAVE_FILE_RATIO >= largest.content_size():
            continue
        # The same file type as the largest file (.nes next to .nes): a ROM, not a save file.
        if entry.path.suffix.casefold() == largest.path.suffix.casefold():
            continue
        own_version = config.version_key(entry.tags)
        if any(
            not other.is_zip
            and config.version_key(other.tags) == own_version
            and size * _SAVE_FILE_RATIO < other.content_size()
            for other in others
        ):
            continue
        entry.notes.append(Note("save_suspected", ratio=_SAVE_FILE_RATIO, name=largest.path.name))
        suspected.append(entry)
    return suspected


def save_file_key(path: Path) -> str:
    """Key under which a confirmed save file is remembered; the same file always gets the same key."""
    return os.path.normcase(os.path.abspath(path))


def _suspected_entries(results: list[GroupResult]) -> list[Entry]:
    return [
        entry
        for result in results
        for entry in result.keep
        if _has_note(entry.notes, "save_suspected")
    ]


def has_suspected_save_file(result: GroupResult) -> bool:
    """Such games stay visible in every view, even without a marked file."""
    return any(_has_note(entry.notes, "save_suspected") for entry in result.keep + result.marked)


def analyze_group(entries: list[Entry], config: Config) -> GroupResult:
    """Decides for all files of a game: keep or delete."""
    # Single ZIPs are read too, otherwise a defect would go unnoticed.
    for entry in entries:
        if entry.is_zip:
            read_zip(entry)
            _adopt_tags_from_zip(entry, config)

    suspected = _suspected_save_files(entries, config)
    entries = [entry for entry in entries if not any(entry is other for other in suspected)]

    marked: list[Entry] = []
    candidates: list[Entry] = []
    unreadable: list[Entry] = []
    for entry in entries:
        reason = config.delete_reason(entry.tags)
        if reason:
            entry.notes.append(Note("extra_info", reason=reason))
            marked.append(entry)
        elif entry.zip_defective:
            entry.notes.append(entry.zip_error)
            marked.append(entry)
        elif entry.zip_error:
            # An unreadable ZIP must neither push out a good file nor silently disappear.
            entry.notes.append(entry.zip_error)
            unreadable.append(entry)
        else:
            candidates.append(entry)

    def sort_key(entry: Entry):
        return _sort_key(entry, config)

    keep: list[Entry] = []
    if candidates:
        best = min(candidates, key=sort_key)
        best_version = config.version_key(best.tags)
        for entry in sorted(candidates, key=sort_key):
            if config.version_key(entry.tags) == best_version:
                keep.append(entry)
            else:
                if _rank(entry, config) == _rank(best, config):
                    if version_number(entry.tags) < version_number(best.tags):
                        entry.notes.append(Note("older_version"))
                    elif (
                        version_number(entry.tags) == version_number(best.tags)
                        and config.keyword_number(entry.tags) < config.keyword_number(best.tags)
                    ):
                        entry.notes.append(Note("older_beta"))
                    else:
                        entry.notes.append(Note("tie"))
                else:
                    # Lost through the priority list: name its own entry and the one that won.
                    own, kept = _rank(entry, config), _rank(best, config)
                    index = 0 if own[0] != kept[0] else 1
                    entry.notes.append(Note("priority", own=config.rank_label(own[index]),
                                            kept=config.rank_label(kept[index])))
                marked.append(entry)

    # Same version, one name with a number in front ("073 Batman"), one without: the number wins.
    numbered = [entry for entry in keep if has_leading_number(entry.game)]
    if numbered and len(numbered) < len(keep):
        for entry in [e for e in keep if not has_leading_number(e.game)]:
            entry.notes.append(Note("number_preferred"))
            marked.append(entry)
        keep = numbered

    zip_files = [entry for entry in keep if entry.is_zip]
    plain_files = [entry for entry in keep if not entry.is_zip]
    replaced_plain: list[Entry] = []
    if config.prefer_zip:
        # Next to a readable ZIP file a plain file of the same version does not remain.
        # An unreadable ZIP pushes out nothing: it stays, and so does the plain file.
        if zip_files and plain_files:
            for entry in plain_files:
                entry.notes.append(Note("zip_preferred"))
                marked.append(entry)
                replaced_plain.append(entry)
            keep = zip_files
    elif plain_files:
        # Next to a plain file a ZIP file never remains, not even with different content.
        for entry in zip_files + unreadable:
            entry.notes.append(Note("plain_preferred"))
            marked.append(entry)
        keep = plain_files
        unreadable = []

    # Several ZIP files of the same version are only duplicates if their content is the same.
    for entry in [e for e in keep if e.is_zip]:
        others = [other for other in keep if other is not entry]
        covering = _covering_entries(entry, others)
        if covering:
            entry.notes.append(Note("identical", names=_names(covering)))
            keep.remove(entry)
            marked.append(entry)
        elif any(sorted(other.tags) == sorted(entry.tags) for other in others):
            entry.notes.append(Note("differs"))

    for entry in marked:
        if not entry.is_zip or entry.zip_error or not entry.members:
            continue
        # Marked by a delete keyword: deleted as requested, its content is meant to go.
        if _has_note(entry.notes, "extra_info"):
            continue
        if _has_note(entry.notes, "identical"):
            continue
        covering = _covering_entries(entry, keep)
        if covering:
            entry.notes.append(Note("identical", names=_names(covering)))
        elif _has_note(entry.notes, "priority", "older_version", "older_beta"):
            # Another region or an older version: other content is expected, no problem.
            entry.notes.append(Note("content_differs"))
        else:
            entry.notes.append(Note("warning"))

    # A plain file that gave way to a ZIP: is its content in a kept ZIP?
    for entry in replaced_plain:
        size, digest = entry.size(), entry.sha256()
        content = ZipMember(entry.path.name, size, digest) if size is not None and digest else None
        covering = [other for other in keep if content and other.contains(content)]
        if covering:
            entry.notes.append(Note("identical", names=_names(covering[:1])))
        else:
            entry.notes.append(Note("warning_plain"))

    # Every other marked plain file: is its content kept? Information only, no problem:
    # a regional version usually differs. Files marked by a delete keyword go as requested.
    for entry in marked:
        if entry.is_zip or entry in replaced_plain or _has_note(entry.notes, "extra_info"):
            continue
        covering = _plain_covered_by(entry, keep)
        if covering:
            entry.notes.append(Note("identical", names=_names(covering[:1])))
        elif covering is not None:
            entry.notes.append(Note("content_differs"))

    keep.extend(unreadable)
    keep.extend(suspected)
    marked.sort(key=sort_key)
    title = game_title((keep or marked)[0])
    return GroupResult(title, keep, marked, find_problems(keep, marked))


def _is_hidden(path: Path) -> bool:
    """Hidden are names starting with a dot and, on Windows, files with the attribute "hidden"."""
    if path.name.startswith("."):
        return True
    try:
        attributes = getattr(path.stat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & _HIDDEN_ATTRIBUTE)


def _is_rom_candidate(path: Path) -> bool:
    """Only these files are analyzed; all others are never shown and never deleted."""
    return path.is_file() and not path.name.casefold().startswith(_NO_ROM_PREFIX) and not _is_hidden(path)


@dataclass
class FileFacts:
    """What the scan learns about one file, independent of the configuration.

    Reading these is the slow part (ZIPs are unpacked and hashed); the database keeps them,
    so that the rules can decide again at once without reading the folder.
    """

    name: str
    size: int | None
    mtime_ns: int | None
    members: list[ZipMember] | None = None
    zip_error_kind: str | None = None  # zip_encrypted, zip_defective or zip_unreadable
    zip_error_text: str = ""
    sha256: str | None = None  # of a plain file, once known

    @property
    def is_zip(self) -> bool:
        return Path(self.name).suffix.casefold() == ".zip"


def rom_files(directory: Path) -> list[Path]:
    """The files of a folder the program looks at, sorted by name."""
    return sorted((p for p in directory.iterdir() if _is_rom_candidate(p)), key=lambda p: p.name.casefold())


def read_facts(path: Path) -> FileFacts:
    """Reads one file: size, change time and, for a ZIP, its contents."""
    try:
        stat = path.stat()
        size, mtime = stat.st_size, stat.st_mtime_ns
    except OSError:
        size, mtime = None, None
    facts = FileFacts(path.name, size, mtime)
    if facts.is_zip:
        entry = Entry(path, "", [])
        read_zip(entry)
        facts.members = entry.members
        if entry.zip_error is not None:
            facts.zip_error_kind = entry.zip_error.kind
            facts.zip_error_text = str(entry.zip_error.values.get("error", ""))
    return facts


def scan_facts(directory: Path, progress=None, files: list[Path] | None = None) -> list[FileFacts]:
    """Reads the facts of all files of the folder; progress(done, total) counts files."""
    files = rom_files(directory) if files is None else files
    if progress:
        progress(0, len(files))
    facts = []
    for done, path in enumerate(files, 1):
        facts.append(read_facts(path))
        if progress:
            progress(done, len(files))
    return facts


def _entry_from_facts(directory: Path, facts: FileFacts, config: Config) -> Entry:
    game, tag_groups = parse_tag_groups(facts.name)
    tag_groups = [[config.canonical(tag) for tag in group] for group in tag_groups]
    entry = Entry(directory / facts.name, game, [tag for group in tag_groups for tag in group],
                  tag_groups=tag_groups)
    entry._size = facts.size
    entry._sha256 = facts.sha256
    if facts.is_zip:
        entry.zip_read = True
        entry.members = None if facts.zip_error_kind else list(facts.members or [])
        if facts.zip_error_kind:
            entry.zip_error = Note(facts.zip_error_kind, error=facts.zip_error_text)
            entry.zip_defective = facts.zip_error_kind in ("zip_encrypted", "zip_defective")
    return entry


def decide(directory: Path, facts: list[FileFacts], config: Config) -> list[GroupResult]:
    """Applies the rules to the facts of a folder; reads no ZIP again."""
    groups: dict[str, list[Entry]] = {}
    for item in facts:
        entry = _entry_from_facts(directory, item, config)
        groups.setdefault(game_key(entry.game), []).append(entry)
    results = [analyze_group(entries, config) for entries in groups.values()]
    return sorted(results, key=lambda result: result.title.casefold())


def known_checksums(results: list[GroupResult]) -> dict[str, str]:
    """Checksums of plain files computed while deciding, by file name, to keep them with the facts."""
    return {
        entry.path.name: entry._sha256
        for result in results for entry in result.keep + result.marked
        if not entry.is_zip and entry._sha256
    }


def scan_directory(directory: Path, config: Config, progress=None) -> list[GroupResult]:
    """Analyzes the folder; progress(done, total) reports the state in files."""
    return decide(directory, scan_facts(directory, progress), config)


def _format_entry(entry: Entry) -> str:
    return entry.path.name + (f"  [{'; '.join(entry.notes)}]" if entry.notes else "")


def render_report(results: list[GroupResult], show_all: bool = False) -> str:
    """Creates the tree display."""
    blocks = []
    for result in results:
        if not result.marked and not show_all:
            continue
        lines = [tr("report.game", title=result.title)]
        lines.extend(f"+ {_format_entry(entry)}" for entry in result.keep)
        if result.marked:
            lines.append("  + " + tr("report.marked"))
            lines.extend(f"    - {_format_entry(entry)}" for entry in result.marked)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def marked_paths(results: list[GroupResult]) -> list[Path]:
    return [entry.path for result in results for entry in result.marked]


def rename_plan(results: list[GroupResult]) -> tuple[list[tuple[Entry, Path]], list[Entry]]:
    """Kept files with a number in front of the name and their new name without it.

    Returns (renames, skipped). Skipped are files of a game with a .cue, .gdi or .m3u file
    (it names the files in its content) and files whose name without number is taken by a file
    that stays, or by another file of the plan.
    """
    marked = {os.path.normcase(os.path.abspath(entry.path)) for result in results for entry in result.marked}
    renames, skipped, taken = [], [], set()
    for result in results:
        numbered = [entry for entry in result.keep if has_leading_number(entry.game)]
        if not numbered:
            continue
        if any(entry.path.suffix.casefold() in _INDEX_SUFFIXES for entry in result.keep):
            skipped.extend(numbered)
            continue
        for entry in numbered:
            target = entry.path.with_name(_FILE_NUMBER_RE.sub("", entry.path.name, count=1))
            key = os.path.normcase(os.path.abspath(target))
            if key in taken or (target.exists() and key not in marked):
                skipped.append(entry)
                continue
            taken.add(key)
            renames.append((entry, target))
    return renames, skipped


def _total_size(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        try:
            total += path.stat().st_size
        except OSError:
            pass
    return total


def matches_search(result: GroupResult, pattern: str) -> bool:
    """True if a file name of the game contains the pattern; an empty pattern matches everything.

    Only * and ? are wildcards: ROM names often contain square brackets such as [!], so
    they stay ordinary characters here, unlike in fnmatch. Case does not count.
    """
    pattern = pattern.strip()
    if not pattern:
        return True
    parts = (".*" if char == "*" else "." if char == "?" else re.escape(char) for char in pattern)
    regex = re.compile("".join(parts), re.IGNORECASE | re.DOTALL)
    return any(regex.search(entry.path.name) for entry in result.keep + result.marked)


@dataclass
class Review:
    """State of the review; the window only displays it and contains no rules itself."""

    results: list[GroupResult]
    config: Config
    source: str = ""
    # Set when the folder is a platform of a collection: deleting and renaming update its database.
    collection_root: Path | None = None
    directory: Path | None = None

    def priority_text(self) -> str:
        return tr(
            "review.priority",
            regions=" > ".join(self.config.region_priority),
            source=self.source or tr("review.defaults"),
        )

    def delete(self, progress=None) -> tuple[int, list[str]]:
        """Deletes the marked files, then removes the number in front of the kept names (rename_plan)."""
        renames, _skipped = rename_plan(self.results)
        to_delete = marked_paths(self.results)
        deleted, errors = delete_files(to_delete, progress)
        self._forget_deleted_files()
        self.renamed = 0
        done_renames = []
        for entry, target in renames:
            if target.exists():  # a marked file of that name could not be deleted
                errors.append(tr("error.rename_exists", name=entry.path.name, new=target.name))
                continue
            try:
                entry.path.rename(target)
            except OSError as error:
                errors.append(f"{entry.path.name}: {error}")
                continue
            done_renames.append((entry.path.name, target.name))
            entry.path = target
            entry.game = _FILE_NUMBER_RE.sub("", entry.game, count=1)
            self.renamed += 1
        for result in self.results:
            result.title = game_title((result.keep or result.marked)[0])
        if self.collection_root is not None and self.directory is not None:
            from workbench_db import record_changes  # only for a collection

            gone = [path.name for path in to_delete if not path.exists()]
            record_changes(self.collection_root, self.directory, gone, done_renames, self.results, self.config)
        return deleted, errors

    def done_message(self, deleted: int) -> str:
        """After Proceed: how many files were deleted and renamed."""
        text = tr("terminal.deleted", count=deleted)
        if getattr(self, "renamed", 0):
            text += "\n" + tr("terminal.renamed", count=self.renamed)
        return text

    def has_work(self) -> bool:
        """Something for Proceed: marked files or names to shorten."""
        return any(result.marked for result in self.results) or bool(rename_plan(self.results)[0])

    def _forget_deleted_files(self) -> None:
        """Brings the state up to date without reading the folder again.

        Files that could not be deleted stay marked. A kept file no longer counts as changed
        by hand: The deletion has carried out that decision.
        """
        remaining = []
        for result in self.results:
            result.marked = [entry for entry in result.marked if entry.path.exists()]
            for entry in result.keep:
                entry.moved = False
            if result.keep or result.marked:
                result.title = game_title((result.keep or result.marked)[0])
                result.problems = find_problems(result.keep, result.marked)
                remaining.append(result)
        self.results = remaining

    def save_file_keys(self) -> dict[str, int]:
        """The suspected status or save files that are not confirmed yet, with their size."""
        return {
            save_file_key(entry.path): entry.size()
            for entry in _suspected_entries(self.results)
            if entry.size() is not None
        }

    def confirmed_saves(self, settings_path: Path) -> dict[str, int]:
        """The confirmed status or save files: from the database of a collection, else the settings file."""
        from workbench_state import load_confirmed_saves

        confirmed = load_confirmed_saves(settings_path)
        if self.collection_root is None or self.directory is None:
            return confirmed
        from workbench_db import confirmed_saves_of

        return confirmed_saves_of(self.collection_root, self.directory, confirmed)

    def remember_save_files(self, settings_path: Path, files: dict[str, int]) -> None:
        """Keeps confirmed files where confirmed_saves reads them; may raise OSError."""
        if self.collection_root is None or self.directory is None:
            from workbench_state import add_confirmed_saves

            add_confirmed_saves(settings_path, files)
            return
        from workbench_db import add_confirmed_saves_to

        add_confirmed_saves_to(self.collection_root, self.directory, files)

    def confirm_save_files(self, confirmed: dict[str, int]) -> None:
        """Treats remembered files as legitimate, as long as their size has not changed.

        They stay kept, but no longer make their game visible or problematic.
        """
        for result in self.results:
            changed = False
            for entry in result.keep:
                if confirmed.get(save_file_key(entry.path)) != entry.size() or entry.size() is None:
                    continue
                notes = [note for note in entry.notes if not _has_note([note], "save_suspected")]
                if len(notes) != len(entry.notes):
                    entry.notes = notes + [Note("save_confirmed")]
                    changed = True
            if changed:
                result.problems = find_problems(result.keep, result.marked)

    def promote(self, result: GroupResult, entry: Entry) -> bool:
        """Keeps the file and sorts it in where the rules place it."""
        if entry not in result.marked:
            return False
        result.marked.remove(entry)
        key = _sort_key(entry, self.config)
        position = next(
            (index for index, other in enumerate(result.keep) if key < _sort_key(other, self.config)),
            len(result.keep),
        )
        result.keep.insert(position, entry)
        entry.moved = not entry.moved
        result.title = game_title((result.keep or result.marked)[0])  # the spelling of the first kept file
        self._record_move(entry, kept=True)
        return True

    def demote(self, result: GroupResult, entry: Entry) -> bool:
        """Marks the file for deletion and puts it at the end of the game."""
        if entry not in result.keep:
            return False
        result.keep.remove(entry)
        result.marked.append(entry)
        entry.moved = not entry.moved
        result.title = game_title((result.keep or result.marked)[0])
        self._record_move(entry, kept=False)
        return True

    def _record_move(self, entry: Entry, kept: bool) -> None:
        """In a collection, k and x are kept in the database until Proceed or a new scan."""
        if self.collection_root is not None and self.directory is not None:
            from workbench_db import record_move

            record_move(self.collection_root, self.directory, entry, kept)

    def is_visible(self, result: GroupResult, only_problems: bool, show_all: bool = False, pattern: str = "") -> bool:
        """Shows games with marked files, with show_all also the others.

        Games changed by hand stay visible unless the search excludes them.
        """
        if not matches_search(result, pattern):
            return False
        if self._moved_count([result]) > 0:
            return True
        relevant = bool(result.marked) or show_all or has_suspected_save_file(result)
        return relevant and (not only_problems or bool(result.problems))

    def nothing_to_do(self) -> bool:
        return (
            not marked_paths(self.results)
            and not self.moved_count()
            and not any(has_suspected_save_file(result) for result in self.results)
        )

    @staticmethod
    def _moved_count(results: list[GroupResult]) -> int:
        return sum(entry.moved for result in results for entry in result.keep + result.marked)

    def moved_count(self) -> int:
        return self._moved_count(self.results)

    def status(self, only_problems: bool, show_all: bool = False, pattern: str = "") -> str:
        visible = sum(self.is_visible(result, only_problems, show_all, pattern) for result in self.results)
        marked = len(marked_paths(self.results))
        problems = sum(
            bool(result.problems and (result.marked or show_all or has_suspected_save_file(result)))
            for result in self.results
        )
        return tr(
            "review.status", visible=visible, total=len(self.results), marked=marked,
            problems=problems, moved=self.moved_count(),
        )

    def confirm_message(self, only_problems: bool, show_all: bool = False, pattern: str = "") -> str:
        """Before deleting, names everything the window may not be showing right now."""
        paths = marked_paths(self.results)
        renames, skipped = rename_plan(self.results)
        example = f"{renames[0][0].path.name} \u2192 {renames[0][1].name}" if renames else ""
        if paths:
            lines = [
                tr("confirm.question", count=len(paths), size=f"{_total_size(paths) / 1024 / 1024:.1f}"),
                # "Recycle Bin" is the Windows name; other systems call it the trash.
                tr("confirm.no_recycle_bin" if os.name == "nt" else "confirm.no_trash"),
            ]
            if renames:
                lines.append(tr("confirm.rename", count=len(renames), example=example))
        else:
            lines = [tr("confirm.rename_only", count=len(renames), example=example)]
        if skipped:
            lines.append(tr("confirm.rename_skipped", count=len(skipped)))
        hidden = [result for result in self.results if not self.is_visible(result, only_problems, show_all, pattern)]
        hidden_count = len(marked_paths(hidden))
        if hidden_count:
            key = "confirm.hidden_filtered" if pattern.strip() else "confirm.hidden_unproblematic"
            lines.append(tr(key, count=hidden_count))
        if self.moved_count():
            lines.append(tr("confirm.moved", count=self.moved_count()))
        suspected = len(self.save_file_keys())
        if suspected:
            lines.append(tr("confirm.save_files", count=suspected))
        emptied = [result.title for result in self.results if result.marked and not result.keep]
        if emptied:
            shown = ", ".join(emptied[:5])
            if len(emptied) > 5:
                shown = tr("confirm.emptied_more", games=shown, count=len(emptied) - 5)
            lines.append(tr("confirm.emptied", count=len(emptied), games=shown))
        return "\n\n".join(lines)


def delete_files(paths: list[Path], progress=None) -> tuple[int, list[str]]:
    """Deletes the files; progress(done, total) reports the state after each file, failed ones included."""
    deleted = 0
    errors = []
    if progress:
        progress(0, len(paths))
    for done, path in enumerate(paths, 1):
        try:
            path.unlink()
            deleted += 1
        except OSError as error:
            errors.append(f"{path.name}: {error}")
        if progress:
            progress(done, len(paths))
    return deleted, errors


def build_parser() -> argparse.ArgumentParser:
    # The options stay in English: The language is only known once --config has been read.
    parser = argparse.ArgumentParser(
        prog="rom_cleanup_workbench.py",
        description="Rom Cleanup Workbench: finds duplicate ROM files in a directory.",
        epilog="Copyright (C) 2026 M. Kärcher. Free software under the GNU General Public License, "
               "version 3 or later (see LICENSE). Use at your own risk: there is no warranty. We recommend "
               "running the program on a copy of your own ROM collection.",
    )
    parser.add_argument("directory", type=Path, nargs="?", help="directory to check (otherwise chosen in the window)")
    parser.add_argument("--config", type=Path, help="JSON configuration (default: redundanz_config.json)")
    parser.add_argument(
        "--priority", nargs="+", metavar="REGION",
        help=f'regions, best first, e.g. USA Europe Japan {NO_REGION} ("{NO_REGION}" = no region)',
    )
    parser.add_argument(
        "--delete-tag", nargs="*", metavar="INFO",
        help="extra info that always leads to deletion, e.g. Proto Beta",
    )
    parser.add_argument("--all", action="store_true", help="with --report-only: also show games without marked files")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--report-only", action="store_true", help="without window: only print the report in the terminal")
    mode.add_argument("--yes", action="store_true", help="without window: delete marked files without asking")
    mode.add_argument("--scan-all", action="store_true",
                      help="without window: scan every platform folder of the roms folder into its database")
    mode.add_argument(
        "--review", choices=[REVIEW_ALL, REVIEW_PROBLEMS],
        help="open the window with all marked or only the problematic games",
    )
    parser.add_argument("--full", action="store_true", help="with --scan-all: read every file again")
    parser.add_argument(
        "--tui", action="store_true",
        help="use the terminal version instead of the window (automatic on Linux without a graphical display)",
    )
    parser.add_argument(
        "--ascii", action="store_true",
        help="terminal version with ASCII characters only, for terminals without UTF-8 "
             "(automatic on the Linux console); implies --tui",
    )
    return parser


def _use_terminal_version(args: argparse.Namespace) -> bool:
    """--tui or --ascii, or Linux without a graphical display, for example over SSH or on the console."""
    if args.tui or args.ascii:
        return True
    if not sys.platform.startswith("linux"):
        return False
    return not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _run_in_terminal(args: argparse.Namespace, parser: argparse.ArgumentParser, analyze) -> int:
    """Runs only with --report-only or --yes, for example for scripts."""
    if args.directory is None:
        parser.error(tr("terminal.need_directory"))
    try:
        review = analyze(args.directory)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))

    print(review.priority_text())
    print()
    report = render_report(review.results, args.all)
    if report:
        print(report)
        print()

    paths = marked_paths(review.results)
    if not review.has_work():
        print(tr("terminal.no_duplicates"))
        return 0
    print(tr("terminal.summary", games=len(review.results), files=len(paths)))
    if args.report_only:
        print(tr("terminal.nothing_deleted"))
        return 0

    deleted, errors = review.delete()
    print(review.done_message(deleted))
    for error in errors:
        print(tr("terminal.error", error=error), file=sys.stderr)
    return 1 if errors else 0


def _scan_all_in_terminal(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """--scan-all: every platform of the roms folder into its database; prints one line per platform."""
    from workbench_db import is_collection, scan_all

    if args.directory is None:
        parser.error("--scan-all needs the roms folder")
    if not args.directory.is_dir() or not is_collection(args.directory):
        print(tr("terminal.not_collection", directory=args.directory), file=sys.stderr)
        return 1
    finished = scan_all(args.directory, full=args.full)
    for platform, files, read in finished:
        print(tr("terminal.scan_platform", platform=platform, files=files, read=read))
    print(tr("terminal.scan_done", count=len(finished)))
    return 0


def _config_path(args: argparse.Namespace) -> Path | None:
    if args.config is not None:
        return args.config
    return DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else None


def _apply_language(args: argparse.Namespace) -> None:
    """Sets the language once at the start; a broken configuration is reported later by the analysis."""
    try:
        set_language(Config.load(_config_path(args)).language)
    except (OSError, ValueError, TypeError):
        set_language(DEFAULT_LANGUAGE)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)
    _apply_language(args)

    def load_config() -> Config:
        """The configuration as the analysis uses it, also for the numbers of the overview."""
        try:
            config = Config.load(_config_path(args))
        except (OSError, ValueError, TypeError) as error:
            raise ValueError(tr("config.unreadable", error=error)) from error
        if args.priority:
            config = replace(config, region_priority=config.with_regions(args.priority))
        if args.delete_tag is not None:
            config = replace(config, delete_tags=args.delete_tag)
        return config

    def analyze(directory: Path, progress=None, rescan: bool = False, full: bool = False) -> Review:
        """Reads the configuration again for every analysis and examines the folder.

        A platform of a collection is decided from its database; rescan (F5) reads it again.
        A changed language only takes effect at the next start, so that window and notes match.
        """
        if not directory.is_dir():
            raise ValueError(tr("error.directory_not_found", directory=directory))
        config_path = _config_path(args)
        try:
            config = Config.load(config_path)
        except (OSError, ValueError, TypeError) as error:
            raise ValueError(tr("config.unreadable", error=error)) from error
        if args.priority:
            config = replace(config, region_priority=config.with_regions(args.priority))
        if args.delete_tag is not None:
            config = replace(config, delete_tags=args.delete_tag)
        source = "--priority" if args.priority else str(config_path or "")
        from workbench_db import collection_root, open_platform

        root = collection_root(directory)
        if root is None:
            return Review(scan_directory(directory, config, progress), config, source)
        results = open_platform(root, directory, config, progress, rescan=rescan, full=full)
        return Review(results, config, source, collection_root=root, directory=directory)

    if args.scan_all:
        return _scan_all_in_terminal(args, parser)

    if args.report_only or args.yes:
        return _run_in_terminal(args, parser, analyze)

    # The settings change the file the analysis reads; without one they create redundanz_config.json.
    config_file = ConfigFile(_config_path(args) or DEFAULT_CONFIG_PATH)
    scope = _REVIEW_SCOPES.get(args.review)
    if _use_terminal_version(args):
        # Loaded only here: The window does not need Textual, the terminal version not tkinter.
        try:
            from rom_cleanup_workbench_tui import run_tui
        except ImportError as error:
            print(tr("terminal.no_textual", error=error), file=sys.stderr)
            print(tr("terminal.nothing_deleted"))
            return 1
        # None: the terminal version finds out itself whether it may draw more than ASCII.
        return run_tui(analyze, args.directory, scope, config_file, True if args.ascii else None,
                       config_loader=load_config)

    # Loaded only here: Without the window the program also runs without tkinter.
    try:
        from rom_cleanup_workbench_window import run_window

        return run_window(analyze, args.directory, scope, config_file, load_config)
    except (ImportError, RuntimeError) as error:
        print(tr("terminal.no_window", error=error), file=sys.stderr)
        print(tr("terminal.nothing_deleted"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
