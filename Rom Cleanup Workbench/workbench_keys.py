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

"""The keys of the program, for the short line above the list and the key overview (F1 or ?).

The window and the terminal version show the same keys; only a few differ (the font size exists
only in the window, o only in the terminal version).
"""
from __future__ import annotations

from translations import tr

LIST = "list"
OVERVIEW = "overview"
GAME = "game"  # the game view (Enter) and the gamelist report (g)

ALL_KEYS = "F1 / ?"


def short_keys(context: str) -> list[tuple[str, str]]:
    """The few keys of the short line: (key, what it does)."""
    if context == OVERVIEW:
        keys = [("Enter", "keys.short.open"), ("r", "keys.short.scan"), ("a", "keys.short.scan_all")]
    else:
        keys = [("x", "keys.short.delete"), ("k", "keys.short.keep"), ("Enter", "keys.short.game_info"),
                ("F12", "keys.run_cleanup")]
    return [(key, tr(text)) for key, text in keys] + [(ALL_KEYS, tr("keys.short.all"))]


def key_sections(context: str, window: bool, collection: bool, ascii: bool = False) -> list[tuple[str, list]]:
    """The key overview: [(section title, [(key, what it does), ...]), ...].

    window: the window (font size with the mouse wheel) or the terminal version (o for the overview);
    collection: a platform of a collection is open, so q and Esc go back to the overview first.
    """
    up_down = "Up Down" if ascii else "↑ ↓"
    esc = tr("keys.esc")
    zoom = [(tr("keys.zoom_key"), "keys.font_size")] if window else []
    if context == GAME:
        sections = [
            ("keys.section.game", [("e", "keys.edit_game_here"), ("Enter", "keys.close_game_view"),
                                   ("g", "keys.close_report"), (f"q  {esc}", "keys.back_to_list"),
                                   *zoom, ("F1  ?", "keys.this_overview")]),
        ]
        return [(tr(title), [(key, tr(text)) for key, text in rows]) for title, rows in sections]
    if context == OVERVIEW:
        sections = [
            ("keys.section.platforms", [(up_down, "keys.select_platform"), ("Enter", "keys.open_platform"),
                                        ("r  F5", "keys.scan"), ("a", "keys.scan_all")]),
            ("keys.section.switches", [("d", "keys.deep_scan"), ("h", "keys.hide_empty"), ("n", "keys.no_games")]),
            ("keys.section.game", [("w", "keys.write_gamelist")]),
            ("keys.section.program", [("f", "keys.other_roms_folder"), *zoom, ("c", "keys.credits"),
                                      (f"q  {esc}", "keys.close"), ("F1  ?", "keys.this_overview")]),
        ]
    else:
        back = [("o", "keys.to_overview")] if collection and not window else []
        sections = [
            ("keys.section.decide", [("x", "keys.delete_file"), ("k", "keys.keep_file"),
                                     ("F12", "keys.run_cleanup")]),
            ("keys.section.navigate", [(up_down, "keys.select_row"), (f"Shift+{up_down}", "keys.select_several"),
                                       ("Tab", "keys.next_game"), ("Shift+Tab", "keys.previous_game"),
                                       ("/", "keys.filter")]),
            ("keys.section.view", [("1", "window.scope.problems"), ("2", "window.scope.marked"),
                                   ("3", "window.scope.all"), *zoom]),
            *([("keys.section.game", [("Enter", "keys.game_view_window" if window else "keys.game_view"),
                                      ("e", "keys.edit_game"), ("n", "keys.no_game"), ("g", "keys.report"),
                                      ("w", "keys.write_gamelist")])] if collection else []),
            ("keys.section.program", [("r  F5", "keys.analyze_again"), ("f", "keys.folder"), ("s", "keys.settings"),
                                      *back, (f"q  {esc}", "keys.back_or_close" if collection else "keys.close"),
                                      ("c", "keys.credits"), ("F1  ?", "keys.this_overview")]),
        ]
    return [(tr(title), [(key, tr(text)) for key, text in rows]) for title, rows in sections]


def key_notes(context: str) -> list[str]:
    """Explanations below the keys, one point each: in the overview what its states and switches mean."""
    if context == OVERVIEW:
        return [tr("keys.note.open"), tr("keys.note.state", changed=tr("overview.state.changed")),
                tr("keys.note.scan"), tr("keys.note.scan_all"),
                tr("keys.note.no_games", no_games=tr("overview.state.no_games"))]
    return []


def keys_title(context: str) -> str:
    where = {OVERVIEW: "keys.where.overview", GAME: "keys.where.game"}.get(context, "keys.where.list")
    return tr("keys.title", where=tr(where))
