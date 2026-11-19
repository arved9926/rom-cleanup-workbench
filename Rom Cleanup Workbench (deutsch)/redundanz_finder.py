"""Findet redundante Dateien in einem Verzeichnis und löscht sie auf Wunsch.

Dateinamen: <Spielname> (Region oder Zusatzinfo) (...).<Dateityp>
Pro Spielname bleibt die Datei mit der höchsten Regionen-Priorität erhalten,
alle anderen werden zum Löschen markiert. Details stehen in der README.md.
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

NO_REGION = "keine"
REVIEW_ALL = "alle"
REVIEW_PROBLEMS = "probleme"
# Die Werte der Radio Buttons im Fenster; ohne --review gilt dort der gespeicherte Stand.
_REVIEW_SCOPES = {REVIEW_ALL: "markiert", REVIEW_PROBLEMS: "problematisch"}
DEFAULT_CONFIG_PATH = Path(__file__).with_name("redundanz_config.json")
DEFAULT_CONFIG = {
    "region_priority": ["USA", "Europe", "Japan", NO_REGION],
    "region_aliases": {
        "USA": ["US"],
        "Europe": ["Europa", "EU"],
        "Japan": ["JP", "JPN"],
    },
    "delete_tags": ["Proto"],
    "low_priority_tags": ["Beta"],
    "part_tags": ["Disc", "Disk", "CD", "Side", "Seite", "Part", "Teil", "Track"],
}

_TAG_RE = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]")
_EXT_RE = re.compile(r"\.[A-Za-z0-9]+$")
_SEPARATOR_RE = re.compile(r"[-_]")
_AND_RE = re.compile(r"\b(?:und|and)\b")
_THE_RE = re.compile(r"^the\s+|(?:,\s*|\s+)the,?$")
# Im Spielnamen zählt nur die Form v1.1, damit "Spiel V2" ein eigener Titel bleibt.
_NAME_VERSION_RE = re.compile(r"[\s_-]+(v\d+(?:\.\d+)+)$", re.IGNORECASE)
_VERSION_TAG_RE = re.compile(
    r"(?:v|ver\.?|version|rev\.?|revision)\s*(\d+(?:\.\d+)*)|rev(?:ision)?\s+([a-z])",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)*")
_CHUNK_SIZE = 1024 * 1024
_NO_ROM_PREFIX = "gamelist"  # Metadaten von Frontends wie gamelist.xml: Kein ROM, also nie markiert.
_SAVE_FILE_RATIO = 4  # Eine markierte Datei unter 1/4 der größten Datei des Spiels bleibt erhalten.
_SAVE_FILE_NOTE = "Verdacht auf Status- oder Spielstanddatei"
# Beginnt nicht mit _SAVE_FILE_NOTE: Eine bestätigte Datei bleibt erhalten, ist aber kein Grund mehr hinzusehen.
_CONFIRMED_SAVE_FILE_NOTE = "Status- oder Spielstanddatei, beim Löschen bestätigt"
_HIDDEN_ATTRIBUTE = 0x2  # FILE_ATTRIBUTE_HIDDEN, derselbe Wert wie stat.FILE_ATTRIBUTE_HIDDEN.
_ZIP_DEFECT_ERRORS = (zipfile.BadZipFile, EOFError, zlib.error)
# Diese Fehler sagen nichts über das Archiv aus: Die Datei kann gesperrt sein oder
# ein Verfahren nutzen, das Python nicht kennt, wie Deflate64 bei großen Windows-ZIPs.
_ZIP_READ_ERRORS = (RuntimeError, NotImplementedError, OSError)


def normalize(text: str) -> str:
    """Vereinheitlicht Text für Vergleiche (MaME = MAME = mame)."""
    return " ".join(text.split()).casefold()


def game_key(game: str) -> str:
    """Vergleichsschlüssel: "&" = "und" = "and", "The X" = "X The" = "X, The" = "X" und
    "Pac-Man" = "Pac Man" = "Pac_Man" = "PacMan".

    "und" wird zu "&", damit "H & M" nach dem Entfernen der Leerzeichen nicht zu "Hund M" wird.
    """
    text = normalize(_SEPARATOR_RE.sub(" ", game.replace("&", " & ")))
    key = _AND_RE.sub("&", text)
    key = _THE_RE.sub("", key) or key
    # Namen nur aus Trennzeichen bleiben eigene Titel, statt als leerer Name zusammenzufallen.
    return key.replace(" ", "") or normalize(game)


def parse_filename(filename: str) -> tuple[str, list[str]]:
    """Zerlegt einen Dateinamen in Spielname und Klammerinhalte."""
    ext_match = _EXT_RE.search(filename)
    ext = ext_match.group() if ext_match else ""
    stem = filename[: -len(ext)] if ext else filename

    first_tag = _TAG_RE.search(stem)
    game = (stem[: first_tag.start()] if first_tag else stem).strip()
    # "Katz und Maus.abc (Japan).abc": Der Dateityp steht auch vor der Klammer.
    if ext and game.casefold().endswith(ext.casefold()):
        game = game[: -len(ext)].strip()

    tags = []
    name_version = _NAME_VERSION_RE.search(game)
    if name_version:
        tags.append(name_version.group(1))
        game = game[: name_version.start()].strip()

    for match in _TAG_RE.finditer(stem):
        content = match.group(1) if match.group(1) is not None else match.group(2)
        tags.extend(part.strip() for part in content.split(",") if part.strip())
    return game or stem.strip(), tags


def _matches_tag(tag: str, names: list[str]) -> bool:
    """Prüft auf gleiches Wort am Anfang: "Proto 2" passt zu "Proto", "Protocol" nicht."""
    tag = normalize(tag)
    for name in names:
        name = normalize(name)
        if tag.startswith(name) and not tag[len(name):len(name) + 1].isalpha():
            return True
    return False


def version_number(tags: list[str]) -> tuple[int, ...]:
    """Liefert die höchste Versionsnummer: v1.10 > v1.9 und v1.0 = v1; ohne Version ()."""
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
    """Sortierschlüssel: höhere Versionen zuerst, v1.1 auch vor v1."""
    return tuple(-part for part in version_number(tags)) + (1,)


@dataclass
class Config:
    region_priority: list[str]
    region_aliases: dict[str, list[str]]
    delete_tags: list[str]
    part_tags: list[str]
    low_priority_tags: list[str] = field(default_factory=list)
    _canonical: dict[str, str] = field(init=False, repr=False)

    def __post_init__(self):
        self._canonical = {
            normalize(alias): normalize(region)
            for region, aliases in self.region_aliases.items()
            for alias in aliases
        }
        self._ranks = {}
        for index, region in enumerate(self.region_priority):
            self._ranks.setdefault(self.canonical(region), index)

    @classmethod
    def load(cls, path: Path | None) -> "Config":
        """Lädt die Konfiguration; fehlende Einträge kommen aus den Standardwerten."""
        values = dict(DEFAULT_CONFIG)
        if path is not None:
            # utf-8-sig: Manche Windows-Editoren speichern mit BOM.
            with open(path, encoding="utf-8-sig") as handle:
                loaded = json.load(handle)
            if not isinstance(loaded, dict):
                raise ValueError("Die Datei muss ein JSON-Objekt enthalten")
            # Ein Tippfehler darf nicht still zu den Standardwerten führen.
            unknown = sorted(set(loaded) - set(DEFAULT_CONFIG))
            if unknown:
                raise ValueError("Unbekannte Einträge: " + ", ".join(unknown))
            for key, value in loaded.items():
                if not isinstance(value, type(DEFAULT_CONFIG[key])):
                    raise ValueError(f'Falscher Typ bei "{key}"')
            values.update(loaded)
        return cls(**{key: values[key] for key in DEFAULT_CONFIG})

    def canonical(self, tag: str) -> str:
        normalized = normalize(tag)
        return self._canonical.get(normalized, normalized)

    def is_region(self, tag: str) -> bool:
        return tag != normalize(NO_REGION) and tag in self._ranks

    def rank(self, tags: list[str]) -> int:
        """Kleiner ist besser; ohne bekannte Region zählt der Eintrag "keine".

        Dateien mit einer Zusatzinfo aus low_priority_tags stehen hinter allen
        anderen und werden untereinander weiter nach Region sortiert.
        """
        ranks = [self._ranks[tag] for tag in tags if self.is_region(tag)]
        if ranks:
            rank = min(ranks)
        else:
            rank = self._ranks.get(normalize(NO_REGION), len(self.region_priority))
        if any(_matches_tag(tag, self.low_priority_tags) for tag in tags):
            rank += len(self.region_priority) + 1
        return rank

    def low_priority_number(self, tags: list[str]) -> tuple[int, ...]:
        """Liefert die höchste Nummer nach einer Zusatzinfo aus low_priority_tags: Beta 2 > Beta 1 > Beta; sonst ()."""
        best: tuple[int, ...] = ()
        for tag in tags:
            text = normalize(tag)
            for name in self.low_priority_tags:
                if not _matches_tag(text, [name]):
                    continue
                match = _NUMBER_RE.fullmatch(text[len(normalize(name)):].strip())
                if match:
                    parts = [int(part) for part in match.group().split(".")]
                    while parts and parts[-1] == 0:
                        parts.pop()
                    best = max(best, tuple(parts))
        return best

    def delete_reason(self, tags: list[str]) -> str | None:
        for name in self.delete_tags:
            if any(_matches_tag(tag, [name]) for tag in tags):
                return name
        return None

    def version_key(self, tags: list[str]) -> frozenset[str]:
        """Dateien mit gleichem Schlüssel gehören zusammen (Disc 1 + 2, .cue + .bin)."""
        return frozenset(tag for tag in tags if not _matches_tag(tag, self.part_tags))


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
    zip_error: str | None = None
    zip_defective: bool = False
    notes: list[str] = field(default_factory=list)
    moved: bool = False  # Bei der Prüfung von Hand gegen die Entscheidung des Programms verschoben.
    _sha256: str | None = None
    _size: int | None = None

    def content_size(self) -> int | None:
        """Größe des Inhalts: Bei einem ZIP die entpackte Größe, damit das Packen nicht zählt.

        None bei einem ZIP, das sich nicht lesen ließ: Seine Archivgröße sagt nichts über den Inhalt.
        """
        if self.is_zip:
            return sum(member.size for member in self.members) if self.members is not None else None
        return self.size()

    def size(self) -> int | None:
        """Dateigröße in Bytes, einmal gelesen; None, wenn die Datei nicht lesbar ist."""
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
        """Prüft, ob der Inhalt der ZIP-Datei in diesem Eintrag vorkommt."""
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
    """Liest die ZIP-Inhalte und merkt sich Größe und Prüfsumme.

    Die Inhalte werden beim Lesen direkt gehasht. Das liefert dasselbe Ergebnis
    wie temporäres Entpacken, braucht aber keinen Plattenplatz und schließt
    schädliche Pfade im Archiv aus.
    """
    members = []
    try:
        with zipfile.ZipFile(entry.path) as archive:
            infos = archive.infolist()
            if any(info.flag_bits & 0x1 for info in infos):
                entry.zip_error = "ZIP verschlüsselt, Inhalt nicht geprüft"
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
        entry.zip_error = f"ZIP defekt: {str(error) or type(error).__name__}"
        entry.zip_defective = True
        return
    except _ZIP_READ_ERRORS as error:
        entry.zip_error = f"ZIP nicht lesbar, bitte selbst prüfen: {str(error) or type(error).__name__}"
        return
    entry.members = members


def _adopt_tags_from_zip(entry: Entry, config: Config) -> None:
    """Übernimmt Region und Version der ZIP-Inhalte, wenn der ZIP-Name sie nicht nennt."""
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
        entry.notes.append("Region aus ZIP-Inhalt: " + ", ".join(regions))
    if versions and not version_number(entry.tags):
        newest = max(versions, key=lambda tag: version_number([tag]))
        entry.tags.append(newest)
        entry.notes.append(f"Version aus ZIP-Inhalt: {newest}")


def _covering_entries(entry: Entry, others: list[Entry]) -> list[Entry]:
    """Liefert die Einträge, die den ganzen ZIP-Inhalt abdecken, sonst eine leere Liste."""
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


def _names(entries: list[Entry]) -> str:
    return ", ".join(entry.path.name for entry in entries)


def _sort_key(entry: Entry, config: Config):
    return (
        config.rank(entry.tags),
        _newest_first(entry.tags),
        # Wie bei einer Version: Die höhere Nummer gewinnt, eine Beta ohne Nummer verliert gegen Beta 1.
        tuple(-part for part in config.low_priority_number(entry.tags)) + (1,),
        len(config.version_key(entry.tags)),
        entry.is_zip,
        entry.path.name.casefold(),
    )


def find_problems(keep: list[Entry], marked: list[Entry]) -> list[str]:
    """Nennt die Gründe, aus denen ein Mensch auf diese Entscheidung schauen sollte."""
    entries = keep + marked
    notes = [note for entry in entries for note in entry.notes]
    problems = []
    if not keep:
        problems.append("Keine Datei bleibt erhalten")
    if any(note.startswith("WARNUNG") for note in notes):
        problems.append("Inhalt eines markierten ZIPs bleibt nicht erhalten")
    if any(entry.zip_defective for entry in entries):
        problems.append("ZIP defekt oder verschlüsselt")
    if any(entry.zip_error and not entry.zip_defective for entry in entries):
        problems.append("ZIP nicht lesbar")
    if any(note.startswith(_SAVE_FILE_NOTE) for note in notes):
        problems.append(_SAVE_FILE_NOTE)
    if any(note.startswith("Gleichstand") for note in notes):
        problems.append("Gleichstand bei der Priorität")
    if any(note.startswith("Inhalt weicht") for note in notes):
        problems.append("ZIPs mit anderem Inhalt")
    # Fällt ein Name erst durch den Vergleich zusammen, können es zwei Spiele sein ("Spiel 1-2", "Spiel 12").
    if len({normalize(entry.game) for entry in entries}) > 1:
        problems.append("Unterschiedliche Schreibweisen des Namens")
    # Gleicher Name, anderer Dateityp: Das kann dasselbe Spiel für ein anderes System sein.
    kept_types = set()
    for entry in keep:
        if entry.is_zip:
            kept_types.update(PurePosixPath(member.name).suffix.casefold() for member in entry.members or [])
        else:
            kept_types.add(entry.path.suffix.casefold())
    if keep and any(not entry.is_zip and entry.path.suffix.casefold() not in kept_types for entry in marked):
        problems.append("Anderer Dateityp als die behaltene Datei")
    return problems


def _suspected_save_files(entries: list[Entry], config: Config) -> list[Entry]:
    """Findet Dateien, die viel kleiner als eine andere Datei des Spiels sind: vielleicht ein Spielstand.

    Sie werden vor der Auswahl beiseitegelegt, damit sie weder gelöscht werden noch die echte ROM
    verdrängen, etwa eine normale 1941.state das ZIP 1941.zip. Eine kleine normale Datei neben einer
    großen normalen Datei ihrer eigenen Version, etwa eine .cue neben ihrer .bin, gehört zu dieser
    Version und steht nicht unter Verdacht; ein ZIP hat außerhalb keine solchen Begleiter. Dateien mit
    delete_tags oder einem defekten ZIP stehen nicht unter Verdacht: Diese Regeln gelten immer.
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
        own_version = config.version_key(entry.tags)
        if any(
            not other.is_zip
            and config.version_key(other.tags) == own_version
            and size * _SAVE_FILE_RATIO < other.content_size()
            for other in others
        ):
            continue
        entry.notes.append(f"{_SAVE_FILE_NOTE}: kleiner als 1/{_SAVE_FILE_RATIO} von {largest.path.name}")
        suspected.append(entry)
    return suspected


def save_file_key(path: Path) -> str:
    """Schlüssel, unter dem eine bestätigte Spielstanddatei gemerkt wird; dieselbe Datei bekommt immer denselben."""
    return os.path.normcase(os.path.abspath(path))


def _suspected_entries(results: list[GroupResult]) -> list[Entry]:
    return [
        entry
        for result in results
        for entry in result.keep
        if any(note.startswith(_SAVE_FILE_NOTE) for note in entry.notes)
    ]


def has_suspected_save_file(result: GroupResult) -> bool:
    """Solche Spiele bleiben in jeder Ansicht sichtbar, auch ohne markierte Datei."""
    return any(
        note.startswith(_SAVE_FILE_NOTE) for entry in result.keep + result.marked for note in entry.notes
    )


def analyze_group(entries: list[Entry], config: Config) -> GroupResult:
    """Entscheidet für alle Dateien eines Spiels: behalten oder löschen."""
    # Auch einzelne ZIPs werden gelesen, sonst bliebe ein Defekt unerkannt.
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
            entry.notes.append(f"Zusatzinfo: {reason}")
            marked.append(entry)
        elif entry.zip_defective:
            entry.notes.append(entry.zip_error)
            marked.append(entry)
        elif entry.zip_error:
            # Ein unlesbares ZIP darf weder eine gute Datei verdrängen noch still verschwinden.
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
                if config.rank(entry.tags) == config.rank(best.tags):
                    if version_number(entry.tags) < version_number(best.tags):
                        entry.notes.append("Ältere Version")
                    elif (
                        version_number(entry.tags) == version_number(best.tags)
                        and config.low_priority_number(entry.tags) < config.low_priority_number(best.tags)
                    ):
                        entry.notes.append("Ältere Beta")
                    else:
                        entry.notes.append("Gleichstand bei der Priorität")
                marked.append(entry)

    # Neben einer normalen Datei bleibt nie eine ZIP-Datei übrig, auch nicht bei anderem Inhalt.
    plain_files = [entry for entry in keep if not entry.is_zip]
    if plain_files:
        for entry in [e for e in keep if e.is_zip] + unreadable:
            entry.notes.append("Normale Datei bevorzugt")
            marked.append(entry)
        keep = plain_files
        unreadable = []

    # Mehrere ZIP-Dateien derselben Version sind nur bei gleichem Inhalt redundant.
    for entry in [e for e in keep if e.is_zip]:
        others = [other for other in keep if other is not entry]
        covering = _covering_entries(entry, others)
        if covering:
            entry.notes.append(f"Inhalt identisch mit {_names(covering)}")
            keep.remove(entry)
            marked.append(entry)
        elif any(sorted(other.tags) == sorted(entry.tags) for other in others):
            entry.notes.append("Inhalt weicht von gleichnamiger Datei ab, beide behalten")

    for entry in marked:
        if not entry.is_zip or entry.zip_error or not entry.members:
            continue
        if any(note.startswith("Inhalt identisch") for note in entry.notes):
            continue
        covering = _covering_entries(entry, keep)
        if covering:
            entry.notes.append(f"Inhalt identisch mit {_names(covering)}")
        else:
            entry.notes.append("WARNUNG: Inhalt kommt in den behaltenen Dateien nicht vor")

    keep.extend(unreadable)
    keep.extend(suspected)
    marked.sort(key=sort_key)
    title = (keep or marked)[0].game
    return GroupResult(title, keep, marked, find_problems(keep, marked))


def _is_hidden(path: Path) -> bool:
    """Versteckt sind Namen mit einem Punkt am Anfang und unter Windows Dateien mit dem Attribut "versteckt"."""
    if path.name.startswith("."):
        return True
    try:
        attributes = getattr(path.stat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & _HIDDEN_ATTRIBUTE)


def _is_rom_candidate(path: Path) -> bool:
    """Nur diese Dateien werden analysiert; alle anderen werden nie angezeigt und nie gelöscht."""
    return path.is_file() and not path.name.casefold().startswith(_NO_ROM_PREFIX) and not _is_hidden(path)


def scan_directory(directory: Path, config: Config, progress=None) -> list[GroupResult]:
    """Analysiert den Ordner; progress(fertig, gesamt) meldet den Stand in Dateien."""
    groups: dict[str, list[Entry]] = {}
    files = sorted((p for p in directory.iterdir() if _is_rom_candidate(p)), key=lambda p: p.name.casefold())
    for path in files:
        game, tags = parse_filename(path.name)
        entry = Entry(path, game, [config.canonical(tag) for tag in tags])
        entry.size()  # Hier im Hintergrund-Thread, damit das Anzeigen der Liste nicht auf die Dateien zugreift.
        groups.setdefault(game_key(game), []).append(entry)
    results = []
    done = 0
    if progress:
        progress(done, len(files))
    for entries in groups.values():
        results.append(analyze_group(entries, config))
        done += len(entries)
        if progress:
            progress(done, len(files))
    return sorted(results, key=lambda result: result.title.casefold())


def _format_entry(entry: Entry) -> str:
    return entry.path.name + (f"  [{'; '.join(entry.notes)}]" if entry.notes else "")


def render_report(results: list[GroupResult], show_all: bool = False) -> str:
    """Erzeugt die Baumdarstellung."""
    blocks = []
    for result in results:
        if not result.marked and not show_all:
            continue
        lines = [f"{result.title} (Spielname)"]
        lines.extend(f"+ {_format_entry(entry)}" for entry in result.keep)
        if result.marked:
            lines.append("  + Zum Löschen markiert")
            lines.extend(f"    - {_format_entry(entry)}" for entry in result.marked)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def marked_paths(results: list[GroupResult]) -> list[Path]:
    return [entry.path for result in results for entry in result.marked]


def _total_size(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        try:
            total += path.stat().st_size
        except OSError:
            pass
    return total


def matches_search(result: GroupResult, pattern: str) -> bool:
    """Wahr, wenn ein Dateiname des Spiels das Muster enthält; ein leeres Muster passt auf alles.

    Nur * und ? sind Platzhalter: ROM-Namen enthalten oft eckige Klammern wie [!], deshalb
    bleiben sie hier, anders als bei fnmatch, gewöhnliche Zeichen. Groß- und Kleinschreibung zählt nicht.
    """
    pattern = pattern.strip()
    if not pattern:
        return True
    parts = (".*" if char == "*" else "." if char == "?" else re.escape(char) for char in pattern)
    regex = re.compile("".join(parts), re.IGNORECASE | re.DOTALL)
    return any(regex.search(entry.path.name) for entry in result.keep + result.marked)


@dataclass
class Review:
    """Stand der Prüfung; das Fenster zeigt ihn nur an und enthält selbst keine Regeln."""

    results: list[GroupResult]
    config: Config
    source: str = "Standardwerte"

    def priority_text(self) -> str:
        return f"Priorität: {' > '.join(self.config.region_priority)}  (aus {self.source})"

    def delete(self, progress=None) -> tuple[int, list[str]]:
        deleted, errors = delete_files(marked_paths(self.results), progress)
        self._forget_deleted_files()
        return deleted, errors

    def _forget_deleted_files(self) -> None:
        """Bringt den Stand auf den neuesten Stand, ohne den Ordner neu zu lesen.

        Dateien, die sich nicht löschen ließen, bleiben markiert. Eine behaltene Datei gilt nicht
        mehr als von Hand geändert: Das Löschen hat diese Entscheidung umgesetzt.
        """
        remaining = []
        for result in self.results:
            result.marked = [entry for entry in result.marked if entry.path.exists()]
            for entry in result.keep:
                entry.moved = False
            if result.keep or result.marked:
                result.title = (result.keep or result.marked)[0].game
                result.problems = find_problems(result.keep, result.marked)
                remaining.append(result)
        self.results = remaining

    def save_file_keys(self) -> dict[str, int]:
        """Die vermuteten Status- oder Spielstanddateien, die noch nicht bestätigt sind, mit ihrer Größe."""
        return {
            save_file_key(entry.path): entry.size()
            for entry in _suspected_entries(self.results)
            if entry.size() is not None
        }

    def confirm_save_files(self, confirmed: dict[str, int]) -> None:
        """Behandelt gemerkte Dateien als legitim, solange sich ihre Größe nicht geändert hat.

        Sie bleiben erhalten, machen ihr Spiel aber nicht mehr sichtbar oder problematisch.
        """
        for result in self.results:
            changed = False
            for entry in result.keep:
                if confirmed.get(save_file_key(entry.path)) != entry.size() or entry.size() is None:
                    continue
                notes = [note for note in entry.notes if not note.startswith(_SAVE_FILE_NOTE)]
                if len(notes) != len(entry.notes):
                    entry.notes = notes + [_CONFIRMED_SAVE_FILE_NOTE]
                    changed = True
            if changed:
                result.problems = find_problems(result.keep, result.marked)

    def promote(self, result: GroupResult, entry: Entry) -> bool:
        """Behält die Datei und sortiert sie dort ein, wo die Regeln sie einordnen."""
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
        return True

    def demote(self, result: GroupResult, entry: Entry) -> bool:
        """Markiert die Datei zum Löschen und stellt sie ans Ende des Spiels."""
        if entry not in result.keep:
            return False
        result.keep.remove(entry)
        result.marked.append(entry)
        entry.moved = not entry.moved
        return True

    def is_visible(self, result: GroupResult, only_problems: bool, show_all: bool = False, pattern: str = "") -> bool:
        """Zeigt Spiele mit markierten Dateien, mit show_all auch die übrigen.

        Von Hand geänderte Spiele bleiben sichtbar, außer der Filter blendet sie aus.
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
        return (
            f"Angezeigt: {visible} von {len(self.results)} Spielen  |  "
            f"Zum Löschen: {marked} Datei(en)  |  "
            f"Problematisch: {problems}  |  "
            f"Von Hand geändert: {self.moved_count()}"
        )

    def confirm_message(self, only_problems: bool, show_all: bool = False, pattern: str = "") -> str:
        """Nennt vor dem Löschen alles, was im Fenster gerade nicht zu sehen sein kann."""
        paths = marked_paths(self.results)
        lines = [
            f"{len(paths)} Datei(en) ({_total_size(paths) / 1024 / 1024:.1f} MB) endgültig löschen?",
            "Gelöschte Dateien landen nicht im Papierkorb.",
        ]
        hidden = [result for result in self.results if not self.is_visible(result, only_problems, show_all, pattern)]
        hidden_count = len(marked_paths(hidden))
        if hidden_count:
            origin = "Spielen, die der Filter oder die Ansicht ausblendet" if pattern.strip() else "unproblematischen Spielen"
            lines.append(f"Davon nicht angezeigt: {hidden_count} Datei(en) aus {origin}.")
        if self.moved_count():
            lines.append(f"Von Hand geändert: {self.moved_count()} Datei(en).")
        suspected = len(self.save_file_keys())
        if suspected:
            lines.append(
                f"Als Status- oder Spielstanddatei behalten: {suspected} Datei(en). "
                "Sie gelten danach als legitim und werden nicht mehr angezeigt."
            )
        emptied = [result.title for result in self.results if result.marked and not result.keep]
        if emptied:
            shown = ", ".join(emptied[:5]) + (f" und {len(emptied) - 5} weitere" if len(emptied) > 5 else "")
            lines.append(f"Von {len(emptied)} Spiel(en) bleibt keine Datei übrig: {shown}.")
        return "\n\n".join(lines)


def delete_files(paths: list[Path], progress=None) -> tuple[int, list[str]]:
    """Löscht die Dateien; progress(fertig, gesamt) meldet den Stand nach jeder Datei, auch nach Fehlern."""
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
    parser = argparse.ArgumentParser(description="Findet redundante Dateien in einem Verzeichnis.")
    parser.add_argument("directory", type=Path, nargs="?", help="zu prüfendes Verzeichnis (sonst Auswahl im Fenster)")
    parser.add_argument("--config", type=Path, help="JSON-Konfiguration (Standard: redundanz_config.json)")
    parser.add_argument(
        "--priority", nargs="+", metavar="REGION",
        help=f'Regionen, beste zuerst, z. B. USA Europe Japan {NO_REGION} ("{NO_REGION}" = ohne Region)',
    )
    parser.add_argument(
        "--delete-tag", nargs="*", metavar="INFO",
        help="Zusatzinfos, die immer zum Löschen führen, z. B. Proto Beta",
    )
    parser.add_argument("--all", action="store_true", help="mit --report-only: auch Spiele ohne markierte Dateien zeigen")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--report-only", action="store_true", help="ohne Fenster: nur den Bericht im Terminal ausgeben")
    mode.add_argument("--yes", action="store_true", help="ohne Fenster: markierte Dateien ohne Rückfrage löschen")
    mode.add_argument(
        "--review", choices=[REVIEW_ALL, REVIEW_PROBLEMS],
        help="das Fenster mit allen markierten oder nur den problematischen Spielen öffnen",
    )
    return parser


def _run_in_terminal(args: argparse.Namespace, parser: argparse.ArgumentParser, analyze) -> int:
    """Läuft nur mit --report-only oder --yes, zum Beispiel für Skripte."""
    if args.directory is None:
        parser.error("--report-only und --yes brauchen ein Verzeichnis")
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
    if not paths:
        print("Keine redundanten Dateien gefunden.")
        return 0
    print(f"{len(review.results)} Spiele geprüft, {len(paths)} Datei(en) zum Löschen markiert.")
    if args.report_only:
        print("Es wurde nichts gelöscht.")
        return 0

    deleted, errors = review.delete()
    print(f"{deleted} Datei(en) gelöscht.")
    for error in errors:
        print(f"Fehler: {error}", file=sys.stderr)
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)

    def analyze(directory: Path, progress=None) -> Review:
        """Liest die Konfiguration bei jeder Analyse neu und untersucht den Ordner."""
        if not directory.is_dir():
            raise ValueError(f"Verzeichnis nicht gefunden: {directory}")
        config_path = args.config
        if config_path is None and DEFAULT_CONFIG_PATH.exists():
            config_path = DEFAULT_CONFIG_PATH
        try:
            config = Config.load(config_path)
        except (OSError, ValueError, TypeError) as error:
            raise ValueError(f"Konfiguration nicht lesbar: {error}") from error
        if args.priority:
            config = replace(config, region_priority=args.priority)
        if args.delete_tag is not None:
            config = replace(config, delete_tags=args.delete_tag)
        source = "--priority" if args.priority else config_path or "Standardwerte"
        return Review(scan_directory(directory, config, progress), config, str(source))

    if args.report_only or args.yes:
        return _run_in_terminal(args, parser, analyze)

    # Erst hier laden: Ohne Fenster läuft das Programm auch ohne tkinter.
    try:
        from redundanz_fenster import run_window

        return run_window(analyze, args.directory, _REVIEW_SCOPES.get(args.review))
    except (ImportError, RuntimeError) as error:
        print(f"Das Fenster lässt sich nicht öffnen: {error}", file=sys.stderr)
        print("Es wurde nichts gelöscht.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
