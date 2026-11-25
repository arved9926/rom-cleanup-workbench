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

"""What the game view (i) and the gamelist report (g) show, the same in the window and the terminal.

Both are a list of blocks; each user interface draws them in its own way:
("heading", text), ("field", label, value), ("line", text), ("note", text).
"""
from __future__ import annotations

from translations import tr

# The fields of the game view in their order: column -> translation key of the label.
FIELD_LABELS = [
    ("name", "game.field.name"), ("sortname", "game.field.sortname"), ("description", "game.field.description"),
    ("rating", "game.field.rating"), ("release_date", "game.field.release_date"),
    ("developer", "game.field.developer"), ("publisher", "game.field.publisher"), ("genre", "game.field.genre"),
    ("players", "game.field.players"), ("region", "game.field.region"), ("lang", "game.field.lang"),
    ("favorite", "game.field.favorite"), ("hidden", "game.field.hidden"), ("kidgame", "game.field.kidgame"),
    ("playcount", "game.field.playcount"), ("playtime", "game.field.playtime"),
    ("last_played", "game.field.last_played"), ("xml_id", "game.field.xml_id"),
]
_FLAGS = {"favorite", "hidden", "kidgame"}


def shows_info(info: dict | None) -> bool:
    """A ROM whose information is worth a name in the list: from the gamelist, or an empty entry with media."""
    return bool(info) and info.get("kind") == "game" and (not info.get("created") or bool(info.get("media")))


def list_title(info: dict | None, ascii: bool = False) -> str:
    """The name column of the list: the name, with a star for a favorite; "no game" for a BIOS file."""
    if not info:
        return ""
    if info.get("kind") == "no_game":
        return tr("game.no_game_short")
    if not shows_info(info):
        return ""
    star = ("* " if ascii else "★ ") if info.get("favorite") else ""
    return star + (info.get("name") or "")


def _value(column: str, value) -> str | None:
    if value is None or value == "":
        return None
    if column in _FLAGS:
        return tr("game.yes") if value else None
    if column == "rating":
        return f"{value * 5:g} / 5  ({value:g})"
    if column == "playtime":
        hours, rest = divmod(int(value), 3600)
        return f"{hours}:{rest // 60:02d} h"
    if column == "last_played" and len(str(value)) >= 15 and str(value)[8] == "T":
        text = str(value)
        return f"{text[:4]}-{text[4:6]}-{text[6:8]} {text[9:11]}:{text[11:13]}"
    return str(value)


def game_blocks(result, entry, info_by_rom: dict, size_text) -> tuple[str, str, list]:
    """(title, file name, blocks) of the game view for a file of the list.

    result: the game (its files to keep and to delete); entry: the highlighted file;
    info_by_rom: what the database knows (workbench_db.game_info); size_text(entry): its size as shown.
    """
    name = entry.path.name
    info = info_by_rom.get(name)
    title = (info or {}).get("name") or result.title
    blocks: list = [("heading", tr("game.section.files"))]
    for sign, key, entries in (("+", "game.keep", result.keep), ("-", "game.marked", result.marked)):
        for item in entries:
            mark = "  ◀" if item is entry else ""
            blocks.append(("line", f"{sign} {item.path.name}   {size_text(item)}   {tr(key)}{mark}"))
    blocks.append(("heading", tr("game.section.info")))
    if info is None:
        blocks.append(("note", tr("game.no_info")))
    elif info.get("kind") == "no_game":
        blocks.append(("note", tr("game.no_game")))
    else:
        if info.get("created"):
            blocks.append(("note", tr("game.empty_entry")))
        for column, label in FIELD_LABELS:
            value = _value(column, info.get(column))
            if value is not None and not (info.get("created") and column == "name"):
                blocks.append(("field", tr(label), value))
    extra = (info or {}).get("extra") or []
    if extra:
        blocks.append(("heading", tr("game.section.extra")))
        for tag, text, _attributes in extra:
            blocks.append(("field", tag, " ".join(str(text).split())))
    blocks.append(("heading", tr("game.section.media")))
    media = (info or {}).get("media") or {}
    if not media:
        blocks.append(("note", tr("game.no_media")))
    for category in sorted(media):
        for path in media[category]:
            blocks.append(("field", category, path))
    return title, name, blocks


def report_blocks(report: dict) -> list:
    """The blocks of the gamelist report (workbench_db.gamelist_report)."""
    blocks: list = []
    sections = [
        ("report.problems", [f"{tr('problem.' + item['kind'])}: {item.get('path', '')}"
                             + (f" ({tr('report.line', line=item['line'])})" if item.get("line") else "")
                             for item in report["problems"]]),
        ("report.notes", [f"{tr('problem.' + item['kind'])}: {item.get('path', '')}" for item in report["notes"]]),
        ("report.without_info", report["without_info"]),
        ("report.unassigned", [f"{category}: {path}" for category, path in report["unassigned"]]),
        ("report.no_games", report["no_games"]),
    ]
    if not report["has_gamelist"]:
        blocks.append(("note", tr("report.no_gamelist")))
    for key, lines in sections:
        blocks.append(("heading", f"{tr(key)} ({len(lines)})"))
        if not lines:
            blocks.append(("note", tr("report.none")))
        blocks.extend(("line", line) for line in lines)
    return blocks
