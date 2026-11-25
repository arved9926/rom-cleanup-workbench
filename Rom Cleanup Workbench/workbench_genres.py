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

"""The numeric genre of a gamelist.xml (<genreid>): Recalbox's genre list.

Recalbox's EmulationStation (es-app/src/games/classifications/Genres.h, enum GameGenres) numbers
its genres as main genre x 256 + sub genre: 0x0100 Action, 0x0101 Platform, ..., 0x0600 Sports,
0x0602 Sport Simulation. Recalbox writes this number as <genreid>, and tools such as ARRM fill it
in when they scrape. It is not ScreenScraper's genre number (there, 10 is Action).
The names are in translations.py as genre.<key>.
"""
from __future__ import annotations

from translations import tr

# number -> key (Recalbox's short name), in Recalbox's order
GENRES: dict[int, str] = {
    0x0000: "none",
    0x0100: "action", 0x0101: "actionplatformer", 0x0102: "actionplatformshooter",
    0x0103: "actionfirstpersonshooter", 0x0104: "actionshootemup", 0x0105: "actionshootwithgun",
    0x0106: "actionfighting", 0x0107: "actionbeatemup", 0x0108: "actionstealth", 0x0109: "actionbattleroyale",
    0x010A: "actionrythm",
    0x0200: "adventure", 0x0201: "adventuretext", 0x0202: "adventuregraphics", 0x0203: "adventurevisualnovels",
    0x0204: "adventureinteractivemovie", 0x0205: "adventurerealtime3d", 0x0206: "adventuresurvivalhorror",
    0x0300: "rpg", 0x0301: "rpgaction", 0x0302: "rpgmmo", 0x0303: "rpgdungeoncrawler", 0x0304: "rpgtactical",
    0x0305: "rpgjapanese", 0x0306: "rpgfirstpersonpartybased",
    0x0400: "simulation", 0x0401: "simulationbuildandmanagement", 0x0402: "simulationlife",
    0x0403: "simulationfishandhunt", 0x0404: "simulationvehicle", 0x0405: "simulationscifi",
    0x0500: "strategy", 0x0501: "strategy4x", 0x0502: "strategyartillery", 0x0503: "strategyautobattler",
    0x0504: "strategymoba", 0x0505: "strategyrts", 0x0506: "strategytbs", 0x0507: "strategytowerdefense",
    0x0508: "strategywargame",
    0x0600: "sports", 0x0601: "sportracing", 0x0602: "sportsimulation", 0x0603: "sportcompetitive",
    0x0604: "sportfight",
    0x0700: "pinball", 0x0800: "board", 0x0900: "casual", 0x0A00: "digitalcard", 0x0B00: "puzzleandlogic",
    0x0C00: "party", 0x0D00: "trivia", 0x0E00: "casino", 0x0F00: "compilation", 0x1000: "demoscene",
    0x1100: "educative",
}


def genre_name(value) -> str | None:
    """The genre's name in the current language; None for a number that is no genre of the list."""
    try:
        number = int(str(value).strip(), 0) if str(value).strip().lower().startswith("0x") else int(value)
    except (TypeError, ValueError):
        return None
    key = GENRES.get(number)
    return tr(f"genre.{key}") if key else None


def main_genre(value) -> str | None:
    """The main genre of a sub genre (1538 Sport Simulation -> Sports); None if unknown."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    name = genre_name(number & 0xFF00) if number in GENRES else None
    # "Sports (all)" names the main genre as a choice; as the parent of a sub genre it is just "Sports".
    return name.split(" (")[0].split("（")[0] if name else None


def describe(value) -> str:
    """For the game view: "1538 – Sport Simulation (Sports)"; the number alone if it is unknown."""
    name = genre_name(value)
    if name is None:
        return str(value)
    number = int(value)
    parent = main_genre(number) if number & 0xFF else None
    return f"{number} – {name}" + (f" ({parent})" if parent else "")
