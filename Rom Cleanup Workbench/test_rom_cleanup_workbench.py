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

import contextlib
import gc
import io
import json
import os
import sys
import queue
import re
import tempfile
import threading
import time
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest import mock

import rom_cleanup_workbench as rf
import translations


def rules_config():
    """The configuration the rule tests were written for: the earlier defaults.

    Priority USA > Europe > Japan > none > Beta, and Hack and Hacks as delete words. The program's
    own defaults (USA > Europe > none > Japan > Beta, no delete words) have tests of their own.
    """
    values = dict(rf.DEFAULT_CONFIG, region_priority=["USA", "Europe", "Japan", "none", "Beta"],
                  delete_tags=["Hack", "Hacks"])
    return rf.Config(**values)


class RedundanzTestCase(unittest.TestCase):
    def setUp(self):
        # The texts below are English; a test that switches the language switches it back.
        translations.set_language("en")
        self.addCleanup(translations.set_language, "en")
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.config = rules_config()

    def write(self, name, content=b"data"):
        (self.dir / name).write_bytes(content)

    def write_zip(self, name, members):
        with zipfile.ZipFile(self.dir / name, "w") as archive:
            for member, content in members.items():
                archive.writestr(member, content)

    def scan(self):
        return rf.scan_directory(self.dir, self.config)

    def single(self):
        results = self.scan()
        self.assertEqual(len(results), 1)
        return results[0]

    @staticmethod
    def names(entries):
        return [entry.path.name for entry in entries]


class ParseFilenameTests(unittest.TestCase):
    def test_name_and_tags(self):
        self.assertEqual(rf.parse_filename("Title (USA) (Proto).bin"), ("Title", ["USA", "Proto"]))

    def test_no_brackets(self):
        self.assertEqual(rf.parse_filename("Title.zip"), ("Title", []))

    def test_extension_before_bracket(self):
        self.assertEqual(rf.parse_filename("Title.abc (Japan).abc"), ("Title", ["Japan"]))

    def test_several_regions_in_one_bracket(self):
        self.assertEqual(rf.parse_filename("Title (USA, Europe).md"), ("Title", ["USA", "Europe"]))

    def test_dot_in_game_name(self):
        self.assertEqual(rf.parse_filename("Dr. Mario (USA).nes"), ("Dr. Mario", ["USA"]))

    def test_version_in_game_name(self):
        self.assertEqual(rf.parse_filename("Title v1.1 (USA).bin"), ("Title", ["v1.1", "USA"]))

    def test_version_after_separator_in_game_name(self):
        self.assertEqual(rf.parse_filename("Title_v1.1 (USA).bin"), ("Title", ["v1.1", "USA"]))
        self.assertEqual(rf.parse_filename("Title - v1.1.bin"), ("Title", ["v1.1"]))

    def test_number_without_dot_stays_part_of_game_name(self):
        self.assertEqual(rf.parse_filename("Title V2.bin"), ("Title V2", []))


class GameKeyTests(unittest.TestCase):
    def assert_same(self, *names):
        self.assertEqual(len({rf.game_key(name) for name in names}), 1, names)

    def assert_different(self, first, second):
        self.assertNotEqual(rf.game_key(first), rf.game_key(second))

    def test_und_equals_ampersand(self):
        self.assert_same("Katz und Maus", "Katz & Maus", "Katz&Maus", "KATZ UND MAUS")

    def test_and_equals_und_and_ampersand(self):
        self.assert_same("Tom and Jerry", "Tom AND Jerry", "Tom & Jerry", "Tom&Jerry", "Tom und Jerry")

    def test_und_only_as_whole_word(self):
        self.assert_different("Hund", "H&")
        self.assert_different("Katz Hund Maus", "Katz H & Maus")

    def test_and_only_as_whole_word(self):
        self.assert_different("Andy", "& y")
        self.assert_different("Band Hero", "B & Hero")
        self.assert_different("Land", "L und")

    def test_the_at_start_or_end(self):
        self.assert_same("The Title", "Title The", "Title, The", "Title,The", "Title The,", "the title")

    def test_the_may_be_missing(self):
        self.assert_same("The Game", "Game, The", "Game The", "Game", "game")

    def test_the_only_as_whole_word(self):
        self.assert_different("Bathe", "The Ba")

    def test_the_inside_name_stays(self):
        self.assert_different("Title the Game", "Title Game")

    def test_only_the(self):
        self.assertEqual(rf.game_key("The"), "the")
        self.assertEqual(rf.game_key(", The"), ",the")

    def test_both_rules_combined(self):
        self.assert_same("The Katz und Maus", "Katz & Maus, The")

    def test_spaces_hyphens_and_underscores_are_ignored(self):
        self.assert_same("Pac-Man", "Pac Man", "Pac_Man", "PacMan", "pac - man", "PAC__MAN")

    def test_word_rules_work_with_separators(self):
        self.assert_same("Tom_and_Jerry", "Tom-und-Jerry", "Tom & Jerry", "Tom&Jerry")
        self.assert_same("The_Game", "The-Game", "Game-The", "Game_The", "Game")

    def test_vs_equals_versus_and_vs_with_dot(self):
        self.assert_same("Robocop vs Terminator", "Robocop vs. Terminator", "Robocop versus Terminator",
                         "Robocop VS Terminator", "Robocop Versus Terminator", "Robocop_vs._Terminator")

    def test_roman_numerals_one_to_nine_equal_numbers(self):
        for number, roman in enumerate(("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"), 1):
            self.assert_same(f"Final Fantasy {roman}", f"Final Fantasy {number}", f"final fantasy {roman.lower()}")
        self.assert_same("Street Fighter II - The World Warrior", "Street Fighter 2: The World Warrior".replace(":", ""))
        self.assert_same("Rocky IV (Part)", "Rocky 4 (Part)")

    def test_roman_numerals_only_as_whole_words(self):
        self.assert_different("Vivi", "5vi")
        self.assert_different("Mega Man X", "Mega Man 10")  # only I to IX
        self.assert_different("Final Fantasy XI", "Final Fantasy 11")
        self.assert_different("Final Fantasy VII", "Final Fantasy 6")
        self.assert_different("Xevious", "10evious")

    def test_roman_i_in_front_is_no_number(self):
        self.assert_different("I Robot", "Robot")
        self.assertFalse(rf.has_leading_number("I Robot"))

    def test_double_ampersand_equals_and(self):
        self.assert_same("Tom && Jerry", "Tom&&Jerry", "Tom & Jerry", "Tom and Jerry", "Tom und Jerry")

    def test_apostrophes_do_not_count(self):
        self.assert_same("Sullivan's Island", "Sullivan`s Island", "Sullivan´s Island", "Sullivan’s Island",
                         "Sullivans Island", "sullivans island")
        self.assert_same("Rock 'n' Roll Racing", "Rock n Roll Racing")

    def test_vs_only_as_whole_word(self):
        self.assert_different("Canvas Hero", "Canvs Hero")
        self.assert_different("Vsat", "Versusat")

    def test_number_in_front_of_the_name_is_ignored(self):
        self.assert_same("057 Robocop vs Terminator", "Robocop vs Terminator", "057 - Robocop versus Terminator",
                         "057. Robocop vs. Terminator", "1 Robocop vs Terminator", "057_Robocop_vs_Terminator")

    def test_number_rule_works_with_the(self):
        self.assert_same("057 The Game", "Game, The", "Game")

    def test_a_name_of_only_a_number_stays(self):
        self.assertEqual(rf.game_key("1942"), "1942")
        self.assert_different("1942", "1943")
        self.assert_different("057", "Robocop")

    def test_number_inside_or_attached_stays(self):
        self.assert_different("Robocop 3", "Robocop")
        self.assert_different("2Fast Racer", "Fast Racer")

    def test_n_in_1_collections_stay_apart(self):
        self.assert_different("4 in 1 Fun Pak", "3 in 1 Fun Pak")
        self.assert_different("4-in-1 Fun Pak", "3-in-1 Fun Pak")

    def test_name_of_only_separators_stays_own_title(self):
        self.assert_different("---", "___")


class VersionNumberTests(unittest.TestCase):
    def test_compares_numerically(self):
        self.assertGreater(rf.version_number(["v1.10"]), rf.version_number(["v1.9"]))

    def test_trailing_zero_does_not_matter(self):
        self.assertEqual(rf.version_number(["v1.0"]), rf.version_number(["v1"]))

    def test_other_notations(self):
        for tag in ("V1.1", "Ver 1.1", "Version 1.1", "Rev 1.1"):
            self.assertEqual(rf.version_number([tag]), (1, 1), tag)

    def test_revision_letters(self):
        self.assertGreater(rf.version_number(["Rev B"]), rf.version_number(["Rev A"]))

    def test_other_tags_are_no_version(self):
        for tag in ("USA", "vs", "Vera", "Revenge", "Disc 1"):
            self.assertEqual(rf.version_number([tag]), (), tag)


class AnalyzeTests(RedundanzTestCase):
    def test_example_from_specification(self):
        self.write("Katz und Maus (USA).abc", b"usa")
        self.write("Katz und Maus (Europa).abc", b"eur")
        self.write("Katz und Maus.abc (Japan).abc", b"jap")
        self.write_zip("Katz und Maus.zip", {"Katz und Maus.abc": b"usa"})

        report = rf.render_report(self.scan())

        self.assertEqual(
            report,
            "Katz und Maus (game name)\n"
            "+ Katz und Maus (USA).abc\n"
            "  + Marked for deletion\n"
            "    - Katz und Maus (Europa).abc  [Priority: Europe after USA; Game content deviates from the kept version]\n"
            "    - Katz und Maus.abc (Japan).abc  [Priority: Japan after USA; Game content deviates from the kept version]\n"
            "    - Katz und Maus.zip  [Priority: none after USA; Content identical to Katz und Maus (USA).abc]",
        )

    def test_comparison_ignores_case(self):
        self.write("MaME (usa).bin")
        self.write("MAME (EUROPE).bin")
        self.write("mame.BIN")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["MaME (usa).bin"])
        self.assertEqual(len(result.marked), 2)

    def test_equivalent_names_form_one_group(self):
        self.write("The Katz und Maus (Japan).bin")
        self.write("Katz & Maus, The (USA).bin")
        self.write("Katz und Maus The (Europe).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Katz & Maus, The (USA).bin"])
        self.assertEqual(len(result.marked), 2)

    def test_file_without_the_belongs_to_same_group(self):
        self.write("The Game (Japan).bin")
        self.write("Game, The (Europe).bin")
        self.write("Game (USA).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Game (USA).bin"])
        self.assertEqual(len(result.marked), 2)

    def test_names_with_different_separators_form_one_group(self):
        self.write("Pac-Man (Japan).bin")
        self.write("Pac_Man (USA).bin")
        self.write("Pac Man (Europe).bin")
        self.write("PacMan.bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Pac_Man (USA).bin"])
        self.assertEqual(len(result.marked), 3)

    def test_falls_back_to_next_region(self):
        self.write("Title (Japan).bin")
        self.write("Title (Europe).bin")
        self.write("Title.bin")
        self.assertEqual(self.names(self.single().keep), ["Title (Europe).bin"])

    def test_custom_priority(self):
        self.config = rf.Config(["Japan", "none", "USA"], {}, [], [])
        self.write("Title (USA).bin")
        self.write("Title.bin")
        self.assertEqual(self.names(self.single().keep), ["Title.bin"])

    def test_best_region_of_combined_bracket_counts(self):
        self.write("Title (Japan, USA).bin")
        self.write("Title (Europe).bin")
        self.assertEqual(self.names(self.single().keep), ["Title (Japan, USA).bin"])

    def test_delete_tag_marks_even_single_file(self):
        self.write("Title (USA) (Hack).bin")
        result = self.single()
        self.assertEqual(result.keep, [])
        self.assertEqual(self.names(result.marked), ["Title (USA) (Hack).bin"])

    def test_delete_tag_never_wins_over_other_files(self):
        self.write("Title (USA) (Hack 2).bin")
        self.write("Title (Japan).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (Japan).bin"])

    def test_no_delete_words_and_japan_after_none_by_default(self):
        self.assertEqual(rf.DEFAULT_CONFIG["delete_tags"], [])
        self.assertEqual(rf.DEFAULT_CONFIG["region_priority"], ["USA", "Europe", "none", "Japan", "Beta"])
        self.config = rf.Config.load(None)
        for name in ("Title (USA) (Hack).bin", "Title (Japan).bin", "Title.bin"):
            self.write(name)
        result = self.single()
        # Without delete words the hack counts as USA and wins; a file without region beats Japan.
        self.assertEqual(self.names(result.keep), ["Title (USA) (Hack).bin"])
        self.assertEqual(sorted(self.names(result.marked)), ["Title (Japan).bin", "Title.bin"])

    def test_shipped_configuration_matches_the_defaults(self):
        shipped = json.loads(rf.DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        for key in ("language", "region_priority", "delete_tags"):
            self.assertEqual(shipped[key], rf.DEFAULT_CONFIG[key], key)

    def test_hack_and_hacks_are_deleted_when_configured(self):
        self.write("Title (USA).bin")
        for name in ("Title (USA) (Hack).bin", "Title (USA) (Hacks).bin", "Title (Japan) (Hack 2).bin",
                     "Title (Hack by Someone).bin"):
            self.write(name)
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).bin"])
        self.assertEqual(sorted(self.names(result.marked)), [
            "Title (Hack by Someone).bin", "Title (Japan) (Hack 2).bin", "Title (USA) (Hack).bin",
            "Title (USA) (Hacks).bin",
        ])
        notes = {entry.path.name: entry.notes for entry in result.marked}
        self.assertIn("Deleted according to delete keyword (Hack) - as requested", notes["Title (USA) (Hack).bin"])
        self.assertIn("Deleted according to delete keyword (Hacks) - as requested", notes["Title (USA) (Hacks).bin"])

    def test_proto_is_no_longer_deleted_by_default(self):
        self.write("Title (USA) (Proto).bin")
        self.write("Other (Hackers).bin")  # a word that only starts with Hack
        results = self.scan()
        self.assertEqual([result.marked for result in results], [[], []])

    def test_delete_tag_matches_whole_word_only(self):
        self.write("Title (Hackers).bin")
        self.assertEqual(self.single().marked, [])

    def test_all_discs_of_best_version_are_kept(self):
        self.write("Title (USA) (Disc 1).bin")
        self.write("Title (USA) (Disc 2).bin")
        self.write("Title (Europe) (Disc 1).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA) (Disc 1).bin", "Title (USA) (Disc 2).bin"])
        self.assertEqual(self.names(result.marked), ["Title (Europe) (Disc 1).bin"])

    def test_cue_and_bin_stay_together(self):
        self.write("Title (USA).bin")
        self.write("Title (USA).cue")
        self.assertEqual(self.single().marked, [])

    def test_tie_is_reported(self):
        self.write("Title (USA).bin")
        self.write("Title (USA) (Alt).bin", b"new")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).bin"])
        self.assertIn("Tie at priority", result.marked[0].notes)

    def test_highest_version_wins(self):
        self.write("Title (USA) (v1.0).bin")
        self.write("Title (USA) (v1.1).bin")
        self.write("Title (USA) (v1.10).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA) (v1.10).bin"])
        self.assertEqual(result.marked[0].notes, ["Older version", "Content identical to Title (USA) (v1.10).bin"])

    def test_versions_in_game_name_are_grouped(self):
        self.write("Title v1.0.bin")
        self.write("Title v1.1.bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title v1.1.bin"])

    def test_version_beats_file_without_version(self):
        self.write("Title (USA).bin")
        self.write("Title (USA) (Rev 1).bin")
        self.assertEqual(self.names(self.single().keep), ["Title (USA) (Rev 1).bin"])

    def test_region_counts_before_version(self):
        self.write("Title (USA) (v1.0).bin")
        self.write("Title (Japan) (v2.0).bin")
        self.assertEqual(self.names(self.single().keep), ["Title (USA) (v1.0).bin"])

    def test_beta_with_higher_version_still_loses(self):
        self.write("Title (USA) (v1.0).bin")
        self.write("Title (USA) (v2.0) (Beta).bin")
        self.assertEqual(self.names(self.single().keep), ["Title (USA) (v1.0).bin"])

    def test_all_discs_of_highest_version_are_kept(self):
        self.write("Title (USA) (v1.1) (Disc 1).bin")
        self.write("Title (USA) (v1.1) (Disc 2).bin")
        self.write("Title (USA) (v1.0) (Disc 1).bin")
        result = self.single()
        self.assertEqual(len(result.keep), 2)
        self.assertEqual(self.names(result.marked), ["Title (USA) (v1.0) (Disc 1).bin"])

    def test_beta_loses_even_against_file_without_region(self):
        self.write("Title (USA) (Beta).bin")
        self.write("Title.bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title.bin"])
        self.assertEqual(self.names(result.marked), ["Title (USA) (Beta).bin"])

    def test_beta_is_kept_if_nothing_else_exists(self):
        self.write("Title (Beta 2).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (Beta 2).bin"])
        self.assertEqual(result.marked, [])

    def test_betas_are_ordered_by_region(self):
        self.write("Title (Japan) (Beta).bin")
        self.write("Title (USA) (Beta).bin")
        self.assertEqual(self.names(self.single().keep), ["Title (USA) (Beta).bin"])

    def test_highest_beta_number_wins(self):
        self.write("Title (USA) (Beta 1).bin")
        self.write("Title (USA) (Beta 2).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA) (Beta 2).bin"])
        self.assertEqual(self.names(result.marked), ["Title (USA) (Beta 1).bin"])
        self.assertIn("Older beta", result.marked[0].notes)
        self.assertEqual(result.problems, [])

    def test_beta_numbers_are_compared_numerically(self):
        self.write("Title (Beta 9).bin")
        self.write("Title (Beta 10).bin")
        self.write("Title (Beta).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (Beta 10).bin"])
        self.assertEqual(self.names(result.marked), ["Title (Beta 9).bin", "Title (Beta).bin"])

    def test_region_counts_before_beta_number(self):
        self.write("Title (Japan) (Beta 2).bin")
        self.write("Title (USA) (Beta 1).bin")
        self.assertEqual(self.names(self.single().keep), ["Title (USA) (Beta 1).bin"])

    def test_beta_number_does_not_beat_a_release(self):
        self.write("Title (Japan).bin")
        self.write("Title (USA) (Beta 3).bin")
        self.assertEqual(self.names(self.single().keep), ["Title (Japan).bin"])

    def test_all_discs_of_highest_beta_are_kept(self):
        for name in ("(Beta 1) (Disc 1)", "(Beta 1) (Disc 2)", "(Beta 2) (Disc 1)", "(Beta 2) (Disc 2)"):
            self.write(f"Title (USA) {name}.bin")
        result = self.single()
        self.assertEqual(
            self.names(result.keep), ["Title (USA) (Beta 2) (Disc 1).bin", "Title (USA) (Beta 2) (Disc 2).bin"],
        )

    def test_keyword_number(self):
        for tags, expected in (
            (["Beta 2"], (2,)), (["beta2"], (2,)), (["Beta 1.10"], (1, 10)), (["Beta"], ()),
            (["Beta 2.0"], (2,)), (["Betamax 3"], ()), (["Beta v2"], ()), (["USA", "Beta 4"], (4,)),
        ):
            self.assertEqual(self.config.keyword_number(tags), expected, tags)

    # Keywords in the priority list (docs/keywords-plan.md, step 1) --------------------------

    def use_priority(self, *entries, **options):
        self.config = rf.Config(list(entries), dict(rf.DEFAULT_CONFIG["region_aliases"], **options.get(
            "aliases", {})), [], list(rf.DEFAULT_CONFIG["part_tags"]))

    def test_beta_at_the_end_of_the_list_loses_to_a_worse_region(self):
        self.use_priority("USA", "Europe", "Japan", "none", "Beta")
        self.write("Title (USA) (Beta).bin")
        self.write("Title (Japan).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (Japan).bin"])
        self.assertEqual(self.names(result.marked), ["Title (USA) (Beta).bin"])

    def test_several_regions_in_one_bracket_still_count_with_the_best(self):
        # The user's own list puts Japan after "none": (USA, Japan) must still count as USA.
        self.use_priority("Germany", "Europe", "USA", "none", "Japan", "Beta")
        self.write("Title (USA, Japan).bin")
        self.write("Title (Europe) (Beta).bin")
        self.write("Title.bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA, Japan).bin"])
        self.assertEqual(self.config.rank(["USA", "Japan"], [["USA", "Japan"]]), (2, 2))
        self.assertEqual(self.config.rank(["Japan"]), (4, 3))  # after "none", and no better than it

    def test_region_after_none_loses_to_a_file_without_region(self):
        self.use_priority("Germany", "Europe", "USA", "none", "Japan")
        self.write("Title (Japan).bin")
        self.write("Title (Rev 1).bin")
        self.assertEqual(self.names(self.single().keep), ["Title (Rev 1).bin"])

    def test_order_of_the_keywords_counts(self):
        self.use_priority("USA", "Europe", "none", "Beta", "Proto")
        self.write("Title (USA) (Proto).bin")
        self.write("Title (Europe) (Beta).bin")
        self.assertEqual(self.names(self.single().keep), ["Title (Europe) (Beta).bin"])
        self.use_priority("USA", "Europe", "none", "Proto", "Beta")
        self.assertEqual(self.names(self.single().keep), ["Title (USA) (Proto).bin"])

    def test_keywords_match_whole_words_with_numbers(self):
        self.use_priority("USA", "none", "Alpha")
        self.write("Title (USA) (Alpha 2).bin")
        self.write("Title (USA) (Alpha 1).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA) (Alpha 2).bin"])
        self.assertIn("Older beta", result.marked[0].notes)
        self.write("Title (USA) (Alphabet).bin")  # no keyword: an ordinary USA file
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA) (Alphabet).bin"])
        self.assertEqual(self.names(result.marked), ["Title (USA) (Alpha 2).bin", "Title (USA) (Alpha 1).bin"])

    def test_old_low_priority_tags_become_keywords_after_none(self):
        config = rf.Config(["USA", "none", "Japan"], {}, [], [], ["Beta", "Proto", "japan"])
        self.assertEqual(config.region_priority, ["USA", "none", "Japan", "Beta", "Proto"])
        self.assertEqual(config.low_priority_tags, [])
        without_none = rf.Config(["USA", "Europe"], {}, [], [], ["Beta"])
        self.assertEqual(without_none.region_priority, ["USA", "Europe", "none", "Beta"])

    def test_old_configuration_file_with_low_priority_tags_still_loads(self):
        temp = tempfile.TemporaryDirectory()  # not in the game folder: it would count as a game
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "old.json"
        path.write_text('{"region_priority": ["Germany", "Europe", "USA", "none", "Japan"], '
                        '"low_priority_tags": ["Beta", "Proto", "Alpha"], "delete_tags": []}', encoding="utf-8")
        self.config = rf.Config.load(path)
        self.assertEqual(self.config.region_priority,
                         ["Germany", "Europe", "USA", "none", "Japan", "Beta", "Proto", "Alpha"])
        self.write("Title (USA) (Beta).bin")
        self.write("Title (Japan).bin")
        self.assertEqual(self.names(self.single().keep), ["Title (Japan).bin"])

    def test_priority_option_keeps_the_keywords_of_the_configuration(self):
        config = rf.Config(["USA", "Europe", "none", "Beta", "Proto"], {}, [], [])
        self.assertEqual(config.with_regions(["Japan", "USA"]), ["Japan", "USA", "none", "Beta", "Proto"])
        self.assertEqual(config.with_regions(["Japan", "none"]), ["Japan", "none"])  # given whole
        self.assertEqual(config.with_regions(["Beta", "USA"]), ["Beta", "USA", "none", "Proto"])

    def test_keyword_inside_a_zip_is_no_region_for_its_name(self):
        self.use_priority("USA", "Europe", "none", "Beta")
        self.write_zip("Title.zip", {"Title (Beta).bin": b"zip"})
        self.write("Title (Europe).bin", b"plain")
        result = self.single()
        zip_entry = next(entry for entry in result.keep + result.marked if entry.is_zip)
        self.assertNotIn("beta", zip_entry.tags)
        self.assertFalse(any("Beta" in note for note in zip_entry.notes))

    def test_much_smaller_file_is_kept_as_suspected_save_file(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title.srm", b"x" * 100)
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).sfc", "Title.srm"])
        self.assertEqual(result.marked, [])
        [note] = [note for note in result.keep[1].notes if note.startswith("Suspected")]
        self.assertEqual(note, "Suspected status or save file: less than 1/4 of the size of Title (USA).sfc")
        self.assertIn("Suspected status or save file", result.problems)

    def test_file_of_exactly_a_quarter_is_marked_as_usual(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title (Japan).sfc", b"x" * 250)
        result = self.single()
        self.assertEqual(self.names(result.marked), ["Title (Japan).sfc"])
        self.assertEqual(result.problems, [])

    def test_files_of_similar_size_are_marked_as_usual(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title (Japan).sfc", b"x" * 900)
        self.assertEqual(self.names(self.single().marked), ["Title (Japan).sfc"])

    def test_small_file_next_to_a_large_file_of_its_version_stays_marked(self):
        self.write("Title (USA).cue", b"x" * 10)
        self.write("Title (USA).bin", b"x" * 1000)
        self.write("Title (Japan).cue", b"x" * 10)
        self.write("Title (Japan).bin", b"x" * 1000)
        result = self.single()
        self.assertEqual(self.names(result.marked), ["Title (Japan).bin", "Title (Japan).cue"])
        self.assertEqual(result.problems, [])

    def test_delete_tag_still_marks_a_small_file(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title (USA) (Hack).sfc", b"x" * 10)
        self.assertEqual(self.names(self.single().marked), ["Title (USA) (Hack).sfc"])

    def test_zip_is_compared_by_its_unpacked_size(self):
        self.write("Title (USA).sfc", b"x" * 4000)
        with zipfile.ZipFile(self.dir / "Title (Japan).zip", "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("Title (Japan).sfc", b"x" * 3000)
        result = self.single()
        self.assertTrue((self.dir / "Title (Japan).zip").stat().st_size * 4 < 4000)
        self.assertEqual(self.names(result.marked), ["Title (Japan).zip"])

    def test_save_state_next_to_zip_does_not_push_out_the_rom(self):
        """The case from the window: 1941.state was kept and 1941.zip marked."""
        self.write("1941.state", b"x" * 500)
        self.write_zip("1941.zip", {"1941.bin": b"x" * 100_000})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["1941.zip", "1941.state"])
        self.assertEqual(result.marked, [])
        self.assertTrue(any(note.startswith("Suspected") for note in result.keep[1].notes))
        self.assertFalse(any(note.startswith("WARNING") for entry in result.keep for note in entry.notes))

    def test_save_file_with_better_region_does_not_push_out_the_rom(self):
        self.write("Title (USA).srm", b"x" * 100)
        self.write("Title (Japan).sfc", b"x" * 1000)
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (Japan).sfc", "Title (USA).srm"])
        self.assertEqual(result.marked, [])

    def test_save_file_does_not_hide_a_real_duplicate(self):
        self.write("Title.srm", b"x" * 100)
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title (Japan).sfc", b"x" * 1000)
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).sfc", "Title.srm"])
        self.assertEqual(self.names(result.marked), ["Title (Japan).sfc"])

    def test_small_plain_file_next_to_a_zip_of_its_version_is_suspected(self):
        self.write("Title (USA).sav", b"x" * 100)
        self.write_zip("Title (USA).zip", {"Title (USA).sfc": b"x" * 1000})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).zip", "Title (USA).sav"])
        self.assertEqual(result.marked, [])

    def test_small_file_of_a_marked_version_is_marked_with_it(self):
        """Dead or Alive 2: The small .A1.bin belongs to the [RDC] version and goes with it."""
        self.write("Dead or Alive 2 (USA).cdi", b"x" * 8000)
        self.write("Dead or Alive 2 (USA)[RDC].A1.bin", b"x" * 100)
        self.write("Dead or Alive 2 (USA)[RDC].cdi", b"x" * 8000)
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Dead or Alive 2 (USA).cdi"])
        self.assertEqual(
            self.names(result.marked), ["Dead or Alive 2 (USA)[RDC].A1.bin", "Dead or Alive 2 (USA)[RDC].cdi"],
        )

    def test_small_track_of_its_version_stays_marked(self):
        self.write("Title (USA) (Track 1).bin", b"x" * 8000)
        self.write("Title (USA) (Track 2).bin", b"x" * 100)
        self.write("Title (Japan) (Track 1).bin", b"x" * 8000)
        self.write("Title (Japan) (Track 2).bin", b"x" * 100)
        result = self.single()
        self.assertEqual(self.names(result.marked), ["Title (Japan) (Track 1).bin", "Title (Japan) (Track 2).bin"])
        self.assertEqual(result.problems, [])

    def test_small_gdi_of_its_version_stays_marked(self):
        self.write("Title (USA).gdi", b"x" * 10)
        self.write("Title (USA) (Track 1).bin", b"x" * 8000)
        self.write("Title (Japan).gdi", b"x" * 10)
        self.write("Title (Japan) (Track 1).bin", b"x" * 8000)
        result = self.single()
        self.assertEqual(self.names(result.marked), ["Title (Japan) (Track 1).bin", "Title (Japan).gdi"])

    def test_much_smaller_file_can_still_be_demoted_by_hand(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title.srm", b"x" * 100)
        result = self.single()
        review = rf.Review([result], self.config)
        self.assertTrue(review.demote(result, result.keep[1]))
        self.assertEqual(self.names(result.marked), ["Title.srm"])

    def test_delete_tag_wins_over_low_priority_tag(self):
        self.config = rf.Config(["USA", "none"], {}, ["Beta"], [], ["Beta"])
        self.write("Title (Beta).bin")
        self.assertEqual(self.names(self.single().marked), ["Title (Beta).bin"])


class PreferZipTests(RedundanzTestCase):
    """prefer_zip: the same game as a plain file and as a ZIP file, the ZIP file remains."""

    def setUp(self):
        super().setUp()
        self.config = replace(self.config, prefer_zip=True)

    def test_default_keeps_the_plain_file(self):
        self.assertFalse(rf.DEFAULT_CONFIG["prefer_zip"])
        self.assertFalse(rf.Config.load(None).prefer_zip)

    def test_zip_with_the_same_content_remains_and_the_plain_file_is_marked(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (USA).zip", {"Title (USA).bin": b"rom"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).zip"])
        self.assertEqual(self.names(result.marked), ["Title (USA).bin"])
        notes = result.marked[0].notes
        self.assertIn("ZIP file preferred", notes)
        self.assertIn("Content identical to Title (USA).zip", notes)
        self.assertEqual(result.problems, [])

    def test_plain_file_with_other_content_gets_a_warning_and_a_problem(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (USA).zip", {"Title (USA).bin": b"different"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).zip"])
        self.assertEqual(self.names(result.marked), ["Title (USA).bin"])
        self.assertEqual(result.marked[0].notes[-1], "Game content deviates from the kept version")
        self.assertIn("Same version as the kept file, but different content", result.problems)

    def test_all_plain_files_of_the_version_give_way(self):
        self.write("Title (USA).cue", b"cue" * 10)
        self.write("Title (USA).bin", b"bin" * 10)
        self.write_zip("Title (USA).zip", {"Title (USA).cue": b"cue" * 10, "Title (USA).bin": b"bin" * 10})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).zip"])
        self.assertEqual(sorted(self.names(result.marked)), ["Title (USA).bin", "Title (USA).cue"])
        self.assertEqual(result.problems, [])

    def test_the_priority_still_comes_first(self):
        self.write("Title (USA).bin", b"usa")
        self.write_zip("Title (Japan).zip", {"a.bin": b"jap"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).bin"])
        self.assertEqual(self.names(result.marked), ["Title (Japan).zip"])

    def test_an_unreadable_zip_pushes_out_no_plain_file(self):
        self.write("Title (USA).bin", b"rom")
        self.write("Title (USA).zip", b"not a zip")
        result = self.single()
        self.assertIn("Title (USA).bin", self.names(result.keep))
        self.assertNotIn("Title (USA).bin", self.names(result.marked))

    def test_off_the_plain_file_remains_as_before(self):
        self.config = replace(self.config, prefer_zip=False)
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (USA).zip", {"Title (USA).bin": b"rom"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).bin"])
        self.assertIn("Plain file preferred", result.marked[0].notes)

    def test_the_configuration_file_switches_it(self):
        path = self.dir.parent / f"{self.dir.name}-config.json"
        self.addCleanup(path.unlink, missing_ok=True)
        path.write_text('{"prefer_zip": true}', encoding="utf-8")
        self.assertTrue(rf.Config.load(path).prefer_zip)
        path.write_text('{"prefer_zip": "yes"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            rf.Config.load(path)


class EquivalenceTests(RedundanzTestCase):
    def test_numbered_and_vs_spellings_are_one_game(self):
        self.write("057 Robocop vs Terminator (USA).md", b"usa")
        self.write("Robocop versus Terminator (Europe).md", b"eur")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["057 Robocop vs Terminator (USA).md"])
        self.assertEqual(self.names(result.marked), ["Robocop versus Terminator (Europe).md"])
        self.assertIn("Different spellings of the name", result.problems)


class NumberInFrontTests(RedundanzTestCase):
    """073 Batman: in a tie the name with the number wins; region and delete keywords come first."""

    def test_same_version_the_numbered_name_remains(self):
        self.write("073 Batman (USA).sfc", b"rom")
        self.write("Batman (USA).sfc", b"rom")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["073 Batman (USA).sfc"])
        self.assertEqual(self.names(result.marked), ["Batman (USA).sfc"])
        self.assertIn("Name with number preferred", result.marked[0].notes)

    def test_numbered_name_wins_a_tie_in_extra_info(self):
        # The number comes before "fewer extra info", which would favor the other file.
        self.write("073 Batman (USA) (Alt).sfc", b"one")
        self.write("Batman (USA).sfc", b"two")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["073 Batman (USA) (Alt).sfc"])
        self.assertEqual(self.names(result.marked), ["Batman (USA).sfc"])

    def test_region_wins_over_the_number(self):
        self.write("073 Batman (Europe).sfc", b"eur")
        self.write("Batman (USA).sfc", b"usa")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Batman (USA).sfc"])
        self.assertEqual(self.names(result.marked), ["073 Batman (Europe).sfc"])

    def test_delete_keyword_wins_over_the_number(self):
        self.write("073 Batman (USA) (Hack).sfc", b"hack")
        self.write("Batman (USA).sfc", b"usa")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Batman (USA).sfc"])
        self.assertIn("Deleted according to delete keyword (Hack) - as requested", result.marked[0].notes)

    def test_newer_version_wins_over_the_number(self):
        self.write("073 Batman (USA).sfc", b"old")
        self.write("Batman (USA) (Rev 1).sfc", b"new")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Batman (USA) (Rev 1).sfc"])

    def test_all_parts_of_the_numbered_version_remain(self):
        self.write("073 Batman (USA).cue", b"c" * 10)
        self.write("073 Batman (USA).bin", b"b" * 10)
        self.write("Batman (USA).cue", b"c" * 10)
        self.write("Batman (USA).bin", b"b" * 10)
        result = self.single()
        self.assertEqual(sorted(self.names(result.keep)), ["073 Batman (USA).bin", "073 Batman (USA).cue"])
        self.assertEqual(sorted(self.names(result.marked)), ["Batman (USA).bin", "Batman (USA).cue"])

    def test_numbered_zip_beats_plain_file_without_number(self):
        self.write("Batman (USA).sfc", b"rom")
        self.write_zip("073 Batman (USA).zip", {"Batman (USA).sfc": b"rom"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["073 Batman (USA).zip"])
        self.assertIn("Name with number preferred", result.marked[0].notes)

    def test_two_numbers_stay_together_as_before(self):
        self.write("073 Batman (USA).sfc", b"one")
        self.write("112 Batman (USA).sfc", b"two")
        self.assertEqual(self.single().marked, [])

    def test_number_alone_or_n_in_1_counts_as_no_number(self):
        self.assertTrue(rf.has_leading_number("073 Batman"))
        self.assertTrue(rf.has_leading_number("073 - Batman"))
        self.assertFalse(rf.has_leading_number("1942"))
        self.assertFalse(rf.has_leading_number("4 in 1 Fun Pak"))
        self.assertFalse(rf.has_leading_number("Batman 2"))


class RenameNumberTests(RedundanzTestCase):
    """Proceed removes the number in front of the kept names: 073 Batman (USA).sfc -> Batman (USA).sfc."""

    def review(self):
        return rf.Review(self.scan(), self.config)

    def files(self):
        return sorted(path.name for path in self.dir.iterdir())

    def test_proceed_deletes_then_renames_the_numbered_file(self):
        self.write("073 Batman (USA).sfc", b"rom")
        self.write("Batman (USA).sfc", b"rom")
        review = self.review()
        message = review.confirm_message(False)
        self.assertIn("1 kept file(s) lose the number in front of the name, for example "
                      "073 Batman (USA).sfc \u2192 Batman (USA).sfc.", message)
        deleted, errors = review.delete()
        self.assertEqual((deleted, errors), (1, []))
        self.assertEqual(self.files(), ["Batman (USA).sfc"])
        self.assertEqual((self.dir / "Batman (USA).sfc").read_bytes(), b"rom")
        self.assertEqual(review.done_message(1), "1 file(s) deleted.\n1 file(s) renamed.")
        self.assertEqual(self.names(review.results[0].keep), ["Batman (USA).sfc"])

    def test_every_separator_after_the_number_goes(self):
        for name in ("057 - Robocop (USA).md", "058. Contra (USA).nes", "059_Zelda (USA).sfc", "060 Tetris.gb"):
            self.write(name)
        self.review().delete()
        self.assertEqual(self.files(), ["Contra (USA).nes", "Robocop (USA).md", "Tetris.gb", "Zelda (USA).sfc"])

    def test_names_that_are_numbers_stay(self):
        for name in ("1942 (Japan).bin", "4 in 1 Fun Pak (USA).gb", "2Fast (USA).gba"):
            self.write(name)
        review = self.review()
        self.assertFalse(review.has_work())
        review.delete()
        self.assertEqual(self.files(), ["1942 (Japan).bin", "2Fast (USA).gba", "4 in 1 Fun Pak (USA).gb"])

    def test_nothing_marked_still_proceeds_with_the_renames(self):
        self.write("073 Batman (USA).sfc", b"rom")
        review = self.review()
        self.assertTrue(review.has_work())
        self.assertTrue(review.confirm_message(False).startswith(
            "Nothing is marked. Remove the number in front of the name of 1 file(s), for example "
            "073 Batman (USA).sfc \u2192 Batman (USA).sfc?"))
        self.assertEqual(review.delete(), (0, []))
        self.assertEqual(self.files(), ["Batman (USA).sfc"])

    def test_games_with_a_cue_file_keep_their_number(self):
        self.write("073 Batman (USA).cue", b'FILE "073 Batman (USA).bin" BINARY')
        self.write("073 Batman (USA).bin", b"b" * 100)
        review = self.review()
        self.assertFalse(review.has_work())
        self.write("Other (USA).bin", b"o")
        self.write("Other (Europe).bin", b"o")
        review = self.review()
        self.assertIn("2 file(s) keep their number", review.confirm_message(False))
        review.delete()
        self.assertIn("073 Batman (USA).cue", self.files())
        self.assertIn("073 Batman (USA).bin", self.files())

    def test_a_name_taken_by_a_kept_file_is_not_overwritten(self):
        self.write("073 Batman (USA).sfc", b"one")
        self.write("Batman (USA).sfc", b"two")
        review = self.review()
        result = review.results[0]
        review.promote(result, result.marked[0])  # k: both stay
        self.assertFalse(review.has_work())
        self.assertEqual(review.delete(), (0, []))
        self.assertEqual(self.files(), ["073 Batman (USA).sfc", "Batman (USA).sfc"])
        self.assertEqual((self.dir / "Batman (USA).sfc").read_bytes(), b"two")

    def test_two_numbers_for_the_same_name_rename_only_one(self):
        self.write("073 Batman (USA).sfc", b"one")
        self.write("112 Batman (USA).sfc", b"two")
        review = self.review()
        self.assertIn("1 file(s) keep their number", review.confirm_message(False))
        review.delete()
        self.assertEqual(self.files(), ["112 Batman (USA).sfc", "Batman (USA).sfc"])

    def test_a_file_that_could_not_be_deleted_blocks_the_rename(self):
        self.write("073 Batman (USA).sfc", b"rom")
        self.write("Batman (USA).sfc", b"rom")
        review = self.review()
        with mock.patch.object(rf.Path, "unlink", side_effect=PermissionError("locked")):
            deleted, errors = review.delete()
        self.assertEqual(deleted, 0)
        self.assertIn("073 Batman (USA).sfc: not renamed, Batman (USA).sfc already exists", errors)
        self.assertEqual(self.files(), ["073 Batman (USA).sfc", "Batman (USA).sfc"])

    def test_yes_mode_renames_too(self):
        self.write("073 Batman (USA).sfc", b"rom")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = rf.main([str(self.dir), "--yes", "--config", str(self.empty_config())])
        self.assertEqual(code, 0)
        self.assertIn("1 file(s) renamed.", output.getvalue())
        self.assertEqual(self.files(), ["Batman (USA).sfc"])

    def empty_config(self):
        path = self.dir.parent / f"{self.dir.name}-config.json"
        path.write_text("{}", encoding="utf-8")
        self.addCleanup(path.unlink, missing_ok=True)
        return path


class PriorityNoteTests(RedundanzTestCase):
    """A file that loses through the priority list names its own entry and the one that won."""

    def test_addams_family_usa_loses_to_europe(self):
        self.config = replace(self.config, region_priority=["Germany", "Europe", "USA", "none", "Japan", "Beta"])
        self.write_zip("Addams Family The (Europe) (En Fr De).zip", {"a.nes": b"e" * 3000})
        self.write_zip("Addams Family The (USA).zip", {"a.nes": b"u" * 3000})
        marked = self.single().marked[0]
        self.assertEqual(marked.notes, ["Priority: USA after Europe", "Game content deviates from the kept version"])

    def test_extra_info_names_its_keyword(self):
        self.write("Title (USA).bin", b"usa")
        self.write("Title (USA) (Beta).bin", b"beta!")
        self.assertEqual(self.single().marked[0].notes[0], "Priority: Beta after USA")

    def test_the_note_speaks_the_language(self):
        translations.set_language("de")
        self.write("Title (USA).bin", b"usa")
        self.write("Title (Europe).bin", b"eur!")
        self.assertEqual(self.single().marked[0].notes[0], "Priorität: Europe nach USA")

    def test_same_priority_gets_no_priority_note(self):
        self.write("Title (USA) (v1.1).bin", b"new")
        self.write("Title (USA) (v1.0).bin", b"old")
        self.assertEqual(self.single().marked[0].notes[0], "Older version")


class PlainContentNoteTests(RedundanzTestCase):
    """A marked plain file says whether its content is kept elsewhere (information, no problem)."""

    def test_athena_numbered_file_names_the_identical_kept_zip(self):
        self.config = replace(self.config, prefer_zip=True)
        rom = b"athena" * 1000
        self.write_zip("Athena (USA).zip", {"Athena (USA).nes": rom})
        self.write("Athena (USA).nes", rom)
        self.write("168 Athena.nes", rom)
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Athena (USA).zip"])
        notes = {entry.path.name: list(entry.notes) for entry in result.marked}
        self.assertIn("Content identical to Athena (USA).zip", notes["168 Athena.nes"])
        self.assertIn("Content identical to Athena (USA).zip", notes["Athena (USA).nes"])

    def test_a_different_region_says_its_content_differs_without_a_problem(self):
        self.write("Title (USA).bin", b"usa!")
        self.write("Title (Europe).bin", b"eur!")
        result = self.single()
        self.assertEqual(list(result.marked[0].notes), ["Priority: Europe after USA", "Game content deviates from the kept version"])
        self.assertEqual(result.problems, [])

    def test_the_same_content_under_another_region_is_named(self):
        self.write("Title (USA).bin", b"same")
        self.write("Title (World).bin", b"same")
        result = self.single()
        self.assertEqual(list(result.marked[0].notes), ["Priority: none after USA", "Content identical to Title (USA).bin"])

    def test_no_checksum_without_a_kept_file_of_the_same_size(self):
        self.write("Title (USA).bin", b"usa")
        self.write("Title (Europe).bin", b"europe")
        with mock.patch.object(rf.Entry, "sha256", side_effect=AssertionError("checksum computed")):
            result = self.single()
        self.assertEqual(list(result.marked[0].notes), ["Priority: Europe after USA", "Game content deviates from the kept version"])


class DeleteKeywordNoteTests(RedundanzTestCase):
    def test_a_game_only_of_keyword_files_gets_no_content_warning(self):
        self.write_zip("Bubble Bobble by John's Program (Bubble Bobble Hack).zip", {"a.nes": b"hack"})
        result = self.single()
        self.assertEqual(result.keep, [])
        self.assertEqual(list(result.marked[0].notes),
                         ["Deleted according to delete keyword (Hack) - as requested"])
        self.assertEqual(result.problems, ["No file is kept"])

    def test_a_keyword_zip_next_to_kept_files_gets_no_warning_either(self):
        self.write("Title (USA).bin", b"usa")
        self.write_zip("Title (USA) (Hack).zip", {"a.bin": b"hack"})
        result = self.single()
        self.assertEqual(list(result.marked[0].notes),
                         ["Deleted according to delete keyword (Hack) - as requested"])
        self.assertEqual(result.problems, [])


class DeleteKeywordAnywhereTests(RedundanzTestCase):
    """A delete keyword counts as a whole word anywhere inside a bracket."""

    def test_keyword_inside_the_bracket_marks_the_file(self):
        self.write("Title (USA).nes", b"u")
        for name in ("Title (Micks Hack).nes", "Title (USA) [Super Hack 2].nes", "Title (Hack by Mick).nes",
                     "Title (Mick's HACK).nes"):
            self.write(name, name.encode())
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).nes"])
        self.assertEqual(len(result.marked), 4)
        for entry in result.marked:
            self.assertIn("Deleted according to delete keyword (Hack) - as requested", entry.notes)

    def test_only_the_whole_word_counts(self):
        self.write("Title (USA).nes", b"u")
        self.write("Title (Hackers Edition).nes", b"h")
        self.write("Title (Shack).nes", b"s")
        result = self.single()
        notes = [note for entry in result.keep + result.marked for note in entry.notes]
        self.assertFalse(any(note.startswith("Deleted according to delete keyword") for note in notes))

    def test_outside_brackets_nothing_counts(self):
        self.write("Hack Attack (USA).nes", b"h")
        self.assertEqual(self.single().marked, [])


class ShortRegionTests(RedundanzTestCase):
    """(U), (E) and (J): the short forms of GoodTools names."""

    def test_short_forms_count_as_their_regions(self):
        self.write("Title (J).nes", b"j")
        self.write("Title (U).nes", b"u")
        self.write("Title (E).nes", b"e")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (U).nes"])
        self.assertEqual(self.names(result.marked), ["Title (E).nes", "Title (J).nes"])

    def test_short_forms_with_the_shipped_priority(self):
        self.config = rf.Config.load(None)  # USA, Europe, none, Japan, Beta
        self.write("Title (J).nes", b"j")
        self.write("Title.nes", b"n")
        self.assertEqual(self.names(self.single().keep), ["Title.nes"])

    def test_only_the_whole_bracket_counts(self):
        self.write("Title (Jumbo).nes", b"j")
        self.write("Title (E).nes", b"e")
        self.assertEqual(self.names(self.single().keep), ["Title (E).nes"])

    def test_shipped_file_has_the_short_forms(self):
        shipped = json.loads(rf.DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        for region, aliases in rf.DEFAULT_CONFIG["region_aliases"].items():
            self.assertEqual(shipped["region_aliases"][region], aliases, region)


class SameTypeSmallFileTests(RedundanzTestCase):
    """A small file of the same type as the largest file is a ROM, not a status or save file."""

    def test_small_files_of_the_same_type_are_decided_by_the_rules(self):
        self.config = rf.Config.load(None)  # the shipped priority: none before Japan
        self.write("Dynamite Bowl (J) [o2].nes", b"o" * 577 * 1024)
        self.write("283 Dynamite Bowl.nes", b"a" * 65 * 1024)
        self.write("Dynamite Bowl (J) [o1].nes", b"b" * 65 * 1024)
        self.write("Dynamite Bowl (J) [p1][!].nes", b"c" * 65 * 1024)
        self.write("Dynamite Bowl (J).nes", b"d" * 65 * 1024)
        result = self.single()
        self.assertEqual(result.title, "Dynamite Bowl")
        self.assertEqual(self.names(result.keep), ["283 Dynamite Bowl.nes"])
        self.assertEqual(len(result.marked), 4)
        self.assertIn("Dynamite Bowl (J) [o2].nes", self.names(result.marked))
        notes = [note for entry in result.keep + result.marked for note in entry.notes]
        self.assertFalse(any(getattr(note, "kind", "") == "save_suspected" for note in notes))

    def test_with_japan_before_none_the_plain_j_file_wins(self):
        self.write("Dynamite Bowl (J) [o2].nes", b"o" * 577 * 1024)
        self.write("283 Dynamite Bowl.nes", b"a" * 65 * 1024)
        self.write("Dynamite Bowl (J).nes", b"d" * 65 * 1024)
        result = self.single()  # USA > Europe > Japan > none: (J) is Japan now
        self.assertEqual(self.names(result.keep), ["Dynamite Bowl (J).nes"])

    def test_a_small_file_of_another_type_is_still_suspected(self):
        self.write_zip("1941.zip", {"1941.bin": b"r" * 64 * 1024})
        self.write("1941.state", b"s" * 1024)
        result = self.single()
        self.assertEqual(sorted(self.names(result.keep)), ["1941.state", "1941.zip"])
        state = next(entry for entry in result.keep if entry.path.name == "1941.state")
        self.assertTrue(any(getattr(note, "kind", "") == "save_suspected" for note in state.notes))


class GameTitleTests(RedundanzTestCase):
    def test_the_title_uses_the_spelling_of_the_first_kept_file(self):
        self.write("Street Fighter 2 (Japan).sfc", b"j")
        self.write("Street Fighter II (USA).sfc", b"u")
        review = rf.Review(self.scan(), self.config)
        result = review.results[0]
        self.assertEqual(result.title, "Street Fighter II")
        review.promote(result, result.marked[0])
        review.demote(result, next(e for e in result.keep if "USA" in e.path.name))
        self.assertEqual(result.title, "Street Fighter 2")  # k and x: the new first kept file
        review.demote(result, result.keep[0])
        self.assertEqual(result.title, "Street Fighter II")  # nothing kept: the first marked file (USA)

    def test_the_title_leaves_out_the_number_in_front(self):
        self.write("073 Batman (USA).sfc", b"rom")
        self.write("Batman (Japan).sfc", b"jap")
        self.assertEqual(self.single().title, "Batman")

    def test_names_that_are_numbers_keep_their_title(self):
        self.write("1942 (Japan).bin")
        self.assertEqual(self.single().title, "1942")


class CollectionDatabaseBase(unittest.TestCase):
    """The database of a roms folder (workbench_db): created on opening, keeps the facts of a scan."""

    def setUp(self):
        translations.set_language("en")
        self.addCleanup(translations.set_language, "en")
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.roms = Path(temp.name) / "roms"
        (self.roms / "nes").mkdir(parents=True)
        (self.roms / "snes").mkdir()
        self.config = rules_config()

    def open(self):
        import workbench_db

        collection = workbench_db.Collection(self.roms)
        self.addCleanup(collection.close)
        return collection

    def write(self, platform, name, content=b"data"):
        (self.roms / platform / name).write_bytes(content)

    def write_zip(self, platform, name, members):
        with zipfile.ZipFile(self.roms / platform / name, "w") as archive:
            for member, content in members.items():
                archive.writestr(member, content)

    @staticmethod
    def summary(results):
        return [(result.title, [e.path.name for e in result.keep], [e.path.name for e in result.marked],
                 [[str(note) for note in e.notes] for e in result.keep + result.marked], list(result.problems))
                for result in results]


class CollectionDatabaseTests(CollectionDatabaseBase):

    def test_opening_creates_a_hidden_database_folder(self):
        import workbench_db

        collection = self.open()
        folder = self.roms / ".rom_cleanup_workbench"
        self.assertTrue((folder / "rom_cleanup_workbench.sqlite").is_file())
        self.assertEqual(collection.path, folder / "rom_cleanup_workbench.sqlite")
        if os.name == "nt":
            self.assertTrue(folder.stat().st_file_attributes & 0x2)
        self.assertEqual(workbench_db.SCHEMA_VERSION, 1)

    def test_platforms_are_the_visible_subfolders(self):
        (self.roms / ".git").mkdir()
        (self.roms / "gamelists").mkdir()
        (self.roms / "readme.txt").write_text("x")
        collection = self.open()
        self.assertEqual([folder.name for folder in collection.platform_folders()], ["nes", "snes"])

    def test_facts_survive_closing_and_decide_as_a_fresh_scan(self):
        self.write("nes", "Title (USA).nes", b"rom")
        self.write("nes", "Title (Europe).nes", b"eur")
        self.write_zip("nes", "Title (USA).zip", {"Title (USA).nes": b"rom"})
        self.write_zip("nes", "Other (Japan).zip", {"a.nes": b"jap", "b.txt": b"readme"})
        (self.roms / "nes" / "Broken (USA).zip").write_bytes(b"no zip")
        directory = self.roms / "nes"
        fresh = rf.scan_directory(directory, self.config)
        facts = rf.scan_facts(directory)
        self.open().save_facts("nes", facts)
        loaded = self.open().load_facts("nes")
        self.assertEqual([item.name for item in loaded], [item.name for item in facts])
        broken = next(item for item in loaded if item.name == "Broken (USA).zip")
        self.assertEqual(broken.zip_error_kind, "zip_defective")
        other = next(item for item in loaded if item.name == "Other (Japan).zip")
        self.assertEqual([member.name for member in other.members], ["a.nes", "b.txt"])
        with mock.patch.object(rf, "_read_zip", side_effect=AssertionError("ZIP read again")):
            again = rf.decide(directory, loaded, self.config)
        self.assertEqual(self.summary(again), self.summary(fresh))

    def test_a_platform_never_scanned_has_no_facts(self):
        collection = self.open()
        self.assertIsNone(collection.load_facts("snes"))
        self.assertIsNone(collection.platform("snes").last_scan)

    def test_scanning_again_replaces_the_facts(self):
        self.write("nes", "A (USA).nes")
        collection = self.open()
        collection.save_facts("nes", rf.scan_facts(self.roms / "nes"))
        (self.roms / "nes" / "A (USA).nes").unlink()
        self.write("nes", "B (USA).nes")
        collection.save_facts("nes", rf.scan_facts(self.roms / "nes"))
        self.assertEqual([item.name for item in collection.load_facts("nes")], ["B (USA).nes"])
        self.assertEqual(collection.platform("nes").files, 1)

    def test_checksums_computed_while_deciding_are_kept(self):
        self.write("nes", "Title (USA).nes", b"same")
        self.write("nes", "Title (World).nes", b"same")
        collection = self.open()
        collection.save_facts("nes", rf.scan_facts(self.roms / "nes"))
        results = rf.decide(self.roms / "nes", collection.load_facts("nes"), self.config)
        collection.update_checksums("nes", rf.known_checksums(results))
        loaded = {item.name: item.sha256 for item in collection.load_facts("nes")}
        self.assertTrue(loaded["Title (USA).nes"] and loaded["Title (World).nes"])

    def test_deleted_and_renamed_files_are_updated(self):
        for name in ("073 Batman (USA).nes", "Batman (Europe).nes"):
            self.write("nes", name)
        collection = self.open()
        collection.save_facts("nes", rf.scan_facts(self.roms / "nes"))
        collection.remove_files("nes", ["Batman (Europe).nes"])
        collection.rename_file("nes", "073 Batman (USA).nes", "Batman (USA).nes")
        self.assertEqual([item.name for item in collection.load_facts("nes")], ["Batman (USA).nes"])
        self.assertEqual(collection.platform("nes").files, 1)

    def test_summary_and_own_config(self):
        collection = self.open()
        collection.save_summary("nes", games=10, marked=3, problematic=1, key="k1")
        row = collection.platform("nes")
        self.assertEqual((row.games, row.marked, row.problematic, row.summary_key), (10, 3, 1, "k1"))
        self.assertFalse(row.has_own_config)
        collection.set_own_config("nes", {"region_priority": ["Japan", "none"]})
        self.assertEqual(collection.own_config("nes"), {"region_priority": ["Japan", "none"]})
        self.assertTrue(collection.platform("nes").has_own_config)
        self.assertIsNone(collection.platform("nes").summary_key)  # the numbers must be computed again
        collection.set_own_config("nes", None)
        self.assertIsNone(collection.own_config("nes"))

    def test_a_newer_database_is_refused(self):
        import sqlite3

        import workbench_db

        self.open().close()
        db = sqlite3.connect(self.roms / ".rom_cleanup_workbench" / "rom_cleanup_workbench.sqlite")
        with db:
            db.execute("UPDATE schema_info SET version = 99")
        db.close()
        with self.assertRaises(ValueError):
            workbench_db.Collection(self.roms)


class PlatformFromDatabaseBase(CollectionDatabaseBase):
    """Step 2: a platform of a collection is decided from its database; F5 scans again."""

    def open_platform(self, platform="nes", config=None, rescan=False):
        import workbench_db

        return workbench_db.open_platform(self.roms, self.roms / platform, config or self.config, rescan=rescan)


class PlatformFromDatabaseTests(PlatformFromDatabaseBase):

    def test_without_a_database_a_folder_stays_on_its_own(self):
        import workbench_db

        self.assertIsNone(workbench_db.collection_root(self.roms / "nes"))
        self.open().close()
        self.assertEqual(workbench_db.collection_root(self.roms / "nes"), self.roms)

    def test_the_first_opening_scans_the_second_reads_the_database(self):
        self.write("nes", "Title (USA).nes", b"usa")
        self.write_zip("nes", "Title (Europe).zip", {"a.nes": b"eur"})
        first = self.open_platform()
        with mock.patch.object(rf, "read_facts", side_effect=AssertionError("folder read again")):
            second = self.open_platform()
        self.assertEqual(self.summary(second), self.summary(first))
        row = self.open().platform("nes")
        self.assertEqual((row.files, row.games, row.marked, row.problematic), (2, 1, 1, 0))
        self.assertTrue(row.last_scan)

    def test_new_settings_decide_again_without_a_scan(self):
        self.write("nes", "Title (USA).nes", b"usa")
        self.write("nes", "Title (Japan).nes", b"jap")
        self.open_platform()
        japan_first = replace(self.config, region_priority=["Japan", "USA", "none"])
        with mock.patch.object(rf, "read_facts", side_effect=AssertionError("folder read again")):
            results = self.open_platform(config=japan_first)
        self.assertEqual([e.path.name for e in results[0].keep], ["Title (Japan).nes"])

    def test_rescan_reads_the_folder_again(self):
        self.write("nes", "Title (USA).nes", b"usa")
        self.open_platform()
        self.write("nes", "Title (Japan).nes", b"jap")
        self.assertEqual(len(self.open_platform()[0].marked), 0)  # still the old facts
        self.assertEqual(len(self.open_platform(rescan=True)[0].marked), 1)
        self.assertEqual(self.open().platform("nes").files, 2)

    def test_proceed_records_deletions_and_renames(self):
        import workbench_db

        self.write("nes", "073 Batman (USA).nes", b"usa")
        self.write("nes", "Batman (Japan).nes", b"jap")
        directory = self.roms / "nes"
        results = self.open_platform()
        review = rf.Review(results, self.config, collection_root=self.roms, directory=directory)
        self.assertEqual(review.delete(), (1, []))
        self.assertEqual([item.name for item in self.open().load_facts("nes")], ["Batman (USA).nes"])
        row = self.open().platform("nes")
        self.assertEqual((row.files, row.games, row.marked), (1, 1, 0))
        self.assertEqual(workbench_db.collection_root(directory), self.roms)

    def test_main_uses_the_database_of_a_collection(self):
        self.write("nes", "Title (USA).nes", b"usa")
        self.write("nes", "Title (Japan).nes", b"jap")
        self.open().close()
        config = self.roms.parent / "config.json"
        config.write_text("{}", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            rf.main([str(self.roms / "nes"), "--report-only", "--config", str(config)])
        self.assertEqual(self.open().platform("nes").files, 2)


class PlatformStateAndQuickScanTests(CollectionDatabaseBase):
    """Step 3: changed since the last scan; the quick scan reads only changes, the full scan everything."""

    def scan(self, full=False):
        import workbench_db

        with workbench_db.Collection(self.roms) as collection:
            return workbench_db.scan_platform(collection, self.roms / "nes", full=full)

    def state(self):
        import workbench_db

        with workbench_db.Collection(self.roms) as collection:
            return collection.state(self.roms / "nes")

    def test_states(self):
        self.write("nes", "A (USA).nes", b"a")
        self.assertEqual(self.state(), "not_scanned")
        self.scan()
        self.assertEqual(self.state(), "current")
        self.write("nes", "B (USA).nes", b"b")
        self.assertEqual(self.state(), "changed")
        self.scan()
        self.assertEqual(self.state(), "current")
        (self.roms / "nes" / "A (USA).nes").unlink()
        self.assertEqual(self.state(), "changed")

    def test_a_changed_size_or_time_counts_as_changed(self):
        self.write("nes", "A (USA).nes", b"a")
        self.scan()
        path = self.roms / "nes" / "A (USA).nes"
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000_000))
        self.assertEqual(self.state(), "changed")

    def test_the_quick_scan_reads_only_new_and_changed_files(self):
        self.write_zip("nes", "A (USA).zip", {"a.nes": b"a"})
        self.write_zip("nes", "B (USA).zip", {"b.nes": b"b"})
        self.assertEqual(self.scan(), 2)
        self.write_zip("nes", "C (USA).zip", {"c.nes": b"c"})
        (self.roms / "nes" / "B (USA).zip").unlink()
        reads = []
        original = rf.read_facts
        with mock.patch("workbench_db.read_facts", side_effect=lambda path: reads.append(path.name) or original(path)):
            self.assertEqual(self.scan(), 1)
        self.assertEqual(reads, ["C (USA).zip"])
        names = [item.name for item in self.open().load_facts("nes")]
        self.assertEqual(names, ["A (USA).zip", "C (USA).zip"])

    def test_the_full_scan_reads_everything(self):
        self.write("nes", "A (USA).nes", b"a")
        self.write("nes", "B (USA).nes", b"b")
        self.scan()
        self.assertEqual(self.scan(full=True), 2)

    def test_the_quick_scan_keeps_known_checksums(self):
        import workbench_db

        self.write("nes", "Title (USA).nes", b"same")
        self.write("nes", "Title (World).nes", b"same")
        workbench_db.open_platform(self.roms, self.roms / "nes", self.config)
        self.write("nes", "Other (USA).nes", b"o")
        self.scan()
        loaded = {item.name: item.sha256 for item in self.open().load_facts("nes")}
        self.assertTrue(loaded["Title (USA).nes"])


class OverviewWindowBase(CollectionDatabaseBase):
    """Step 4: the overview of a collection is the window's start page."""

    def analyze(self, directory, progress=None, rescan=False, full=False):
        import workbench_db

        root = workbench_db.collection_root(directory)
        if root is None:
            return rf.Review(rf.scan_directory(directory, self.config, progress), self.config)
        results = workbench_db.open_platform(root, directory, self.config, progress, rescan=rescan, full=full)
        return rf.Review(results, self.config, collection_root=root, directory=directory)

    def make_window(self, directory, settings=None):
        try:
            import tkinter

            import rom_cleanup_workbench_window
            window = rom_cleanup_workbench_window.ReviewWindow(
                self.analyze, directory, "all", settings or self.roms.parent / "settings.json",
                config_loader=lambda: self.config,
            )
        except (ImportError, RuntimeError) as error:
            self.skipTest(f"No window possible: {error}")

        def close():
            with contextlib.suppress(tkinter.TclError):
                window.root.destroy()

        self.addCleanup(close)
        window.root.withdraw()
        return window

    def wait(self, window):
        deadline = time.monotonic() + 10
        while window._analysis is not None and time.monotonic() < deadline:
            window.root.update()
            time.sleep(0.01)
        for worker in list(window._workers):
            worker.join(10)
        window.root.update()

    def fill(self):
        self.write("nes", "Title (USA).nes", b"usa")
        self.write("nes", "Title (Japan).nes", b"jap")
        self.write("snes", "Game (USA).sfc", b"g")


class OverviewWindowTests(OverviewWindowBase):

    def test_a_roms_folder_opens_its_overview(self):
        self.fill()
        window = self.make_window(self.roms)
        window.open_folder(self.roms)
        panel = window.overview_panel
        self.assertIsNotNone(panel)
        self.assertEqual(list(panel.rows), ["nes", "snes"])
        self.assertEqual(panel.tree.item("nes", "values")[-1], "not scanned")
        self.assertTrue((self.roms / ".rom_cleanup_workbench" / "rom_cleanup_workbench.sqlite").is_file())

    def test_ctrl_and_the_mouse_wheel_change_the_font_size_in_the_overview(self):
        self.fill()
        window = self.make_window(self.roms)
        window.open_folder(self.roms)
        tree = window.overview_panel.tree
        before, width = window.font_size, tree.column("files", "width")
        tree.event_generate("<Control-MouseWheel>", delta=120, when="now")
        self.assertEqual(window.font_size, before + 1)
        self.assertGreater(tree.column("files", "width"), width)  # the columns fit the new size

    def test_escape_goes_from_a_platform_to_the_overview_and_then_closes(self):
        self.fill()
        window = self.make_window(self.roms)
        window.open_folder(self.roms)
        window.overview_panel.open()
        self.wait(window)
        self.assertIsNone(window.overview_panel)
        with mock.patch.object(window, "close") as close:
            window._on_escape()
            self.assertIsNotNone(window.overview_panel)
            close.assert_not_called()
            window._on_escape()
            close.assert_called_once()

    def test_the_overview_has_its_own_help_line(self):
        self.fill()
        window = self.make_window(self.roms)
        window.open_folder(self.roms)
        help_text = window.help_label.cget("text")
        self.assertEqual(help_text, translations.tr("window.help_overview"))
        for word in ("a: Scan all", "v: Full", "q or Esc: Close"):
            self.assertIn(word, help_text)
        self.assertNotIn("x: delete", help_text)
        window.overview_panel.open()
        self.wait(window)
        self.assertEqual(window.help_label.cget("text"), translations.tr("window.help"))

    def test_the_keys_of_the_help_line_work_in_the_overview(self):
        self.fill()
        window = self.make_window(self.roms)
        window.open_folder(self.roms)
        tree = window.overview_panel.tree
        # Tk sends keys only to a window with the focus, which a test cannot rely on: the list passes
        # its keys on to the window's bindings, and those call these methods.
        self.assertIn(str(window.root), tree.bindtags())
        keys = {"<KeyPress-v>": "_toggle_full_key", "<KeyPress-a>": "_scan_all_key", "<KeyPress-c>": "show_credits",
                "<KeyPress-q>": "_quit_key", "<Escape>": "_on_escape", "<KeyPress-r>": "reanalyze",
                "<KeyPress-s>": "toggle_settings", "<KeyPress-f>": "choose_directory"}

        def press(key):
            getattr(window, keys[key])()  # looked up now, so that the mocks below take effect
            window.root.update()

        press("<KeyPress-v>")
        self.assertTrue(window.overview_panel.full.get())
        press("<KeyPress-v>")
        self.assertFalse(window.overview_panel.full.get())
        with mock.patch.object(window, "scan_all") as scan_all:
            press("<KeyPress-a>")
        scan_all.assert_called_once()
        with mock.patch.object(window, "show_credits") as credits:
            press("<KeyPress-c>")
        credits.assert_called_once()
        with mock.patch.object(window, "close") as close:
            press("<KeyPress-q>")
            press("<Escape>")
        self.assertEqual(close.call_count, 2)
        with mock.patch.object(window, "open_platform") as open_platform:
            press("<KeyPress-r>")
        open_platform.assert_called_once_with("nes", rescan=True, full=False)
        press("<KeyPress-s>")  # no settings in the overview
        self.assertIsNone(window.settings_panel)
        press("<KeyPress-f>")
        self.assertIsNotNone(window.folder_panel)

    def test_escape_closes_a_folder_on_its_own(self):
        self.fill()
        window = self.make_window(self.roms / "nes")
        window.open_folder(self.roms / "nes")
        self.wait(window)
        with mock.patch.object(window, "close") as close:
            window._on_escape()
        close.assert_called_once()

    def test_side_files_do_not_hide_a_roms_folder(self):
        import workbench_db

        self.fill()
        for name in ("info.txt", "Readme.PDF", "cover.jpg"):
            (self.roms / name).write_bytes(b"side")
        self.assertTrue(workbench_db.is_collection(self.roms))
        (self.roms / "Lost (USA).nes").write_bytes(b"rom")  # a ROM: a folder on its own, as before
        self.assertFalse(workbench_db.is_collection(self.roms))

    def test_opening_a_platform_scans_it_and_the_overview_shows_the_numbers(self):
        self.fill()
        window = self.make_window(self.roms)
        window.open_folder(self.roms)
        window.overview_panel.tree.selection_set("nes")
        window.overview_panel.open()
        self.wait(window)
        self.assertIsNone(window.overview_panel)
        self.assertEqual(window.directory, self.roms / "nes")
        self.assertEqual(len(window.review.results), 1)
        self.assertTrue(window.overview_button.winfo_manager())
        window.show_overview()
        values = window.overview_panel.tree.item("nes", "values")
        self.assertEqual(values[:4], ("2", "1", "1", "0"))
        self.assertEqual(values[-1], "current")
        total = window.overview_panel.tree.item(window.overview_panel._TOTAL, "values")
        self.assertEqual(total[0], "2")

    def test_the_last_collection_opens_at_the_start(self):
        self.fill()
        settings = self.roms.parent / "settings.json"
        window = self.make_window(self.roms, settings)
        window.open_folder(self.roms)
        window.root.destroy()
        window = self.make_window(None, settings)
        window.root.after(200, window.root.quit)
        window.run()
        self.assertIsNotNone(window.overview_panel)
        self.assertEqual(window.collection_root, self.roms)

    def test_a_platform_folder_on_its_own_opens_as_before(self):
        self.write("nes", "Title (USA).nes", b"usa")
        self.write("nes", "Title (Japan).nes", b"jap")
        window = self.make_window(self.roms / "nes")
        window.open_folder(self.roms / "nes")
        self.wait(window)
        self.assertIsNone(window.overview_panel)
        self.assertIsNone(window.collection_root)
        self.assertFalse(window.overview_button.winfo_manager())
        self.assertFalse((self.roms / ".rom_cleanup_workbench").exists())

    def test_full_scan_reads_every_file_again(self):
        self.fill()
        window = self.make_window(self.roms)
        window.open_folder(self.roms)
        window.overview_panel.tree.selection_set("nes")
        window.overview_panel.open()
        self.wait(window)
        window.show_overview()
        reads = []
        original = rf.read_facts
        with mock.patch("rom_cleanup_workbench.read_facts", side_effect=lambda path: reads.append(path.name) or original(path)):
            window.overview_panel.tree.selection_set("nes")
            window.overview_panel.open(rescan=True, full=True)
            self.wait(window)
        self.assertEqual(sorted(reads), ["Title (Japan).nes", "Title (USA).nes"])


class ScanAllTests(OverviewWindowBase):
    """Step 5: scan every platform (window and --scan-all), quick or full; nothing is deleted."""

    def test_scan_all_saves_every_platform(self):
        import workbench_db

        self.fill()
        seen = []
        finished = workbench_db.scan_all(self.roms, progress=lambda *args: seen.append(args[:3]))
        self.assertEqual([name for name, _files, _read in finished], ["nes", "snes"])
        self.assertIn(("snes", 2, 2), seen)
        with workbench_db.Collection(self.roms) as collection:
            self.assertEqual(collection.state(self.roms / "nes"), "current")
            self.assertEqual(collection.platform("snes").files, 1)
        self.assertEqual(sorted(path.name for path in (self.roms / "nes").iterdir()),
                         ["Title (Japan).nes", "Title (USA).nes"])  # nothing deleted

    def test_a_quick_scan_all_reads_only_changes_a_full_one_everything(self):
        import workbench_db

        self.fill()
        workbench_db.scan_all(self.roms)
        self.write("snes", "New (USA).sfc", b"n")
        self.assertEqual([read for _n, _f, read in workbench_db.scan_all(self.roms)], [0, 1])
        self.assertEqual([read for _n, _f, read in workbench_db.scan_all(self.roms, full=True)], [2, 2])

    def test_cancel_keeps_the_finished_platforms(self):
        import workbench_db

        self.fill()

        def stop_in_snes(platform, *_rest):
            if platform == "snes":
                raise workbench_db.ScanCancelled

        with self.assertRaises(workbench_db.ScanCancelled):
            workbench_db.scan_all(self.roms, progress=stop_in_snes)
        with workbench_db.Collection(self.roms) as collection:
            self.assertEqual(collection.state(self.roms / "nes"), "current")
            self.assertEqual(collection.state(self.roms / "snes"), "not_scanned")

    def test_the_window_scans_all_and_shows_the_numbers(self):
        self.fill()
        window = self.make_window(self.roms)
        window.open_folder(self.roms)
        window.scan_all()
        self.assertTrue(window.overview_panel.cancel_button.winfo_manager())
        deadline = time.monotonic() + 10
        while window._batch is not None and time.monotonic() < deadline:
            window.root.update()
            time.sleep(0.01)
        self.assertIsNone(window._batch)
        self.assertEqual(window.status.get(), "2 platform(s) scanned.")
        self.assertEqual(window.overview_panel.tree.item("nes", "values")[-1], "current")
        self.assertFalse(window.overview_panel.cancel_button.winfo_manager())

    def test_each_finished_platform_reports_its_numbers_at_once(self):
        import workbench_db

        self.fill()
        rows = []
        workbench_db.scan_all(self.roms, config=self.config, finished_row=rows.append)
        self.assertEqual([(r.folder, r.state, r.files, r.games, r.marked, r.problematic) for r in rows],
                         [("nes", "current", 2, 1, 1, 0), ("snes", "current", 1, 1, 0, 0)])
        with workbench_db.Collection(self.roms) as collection:  # the overview needs no new decision
            self.assertEqual(collection.platform("nes").summary_key, workbench_db.config_key(self.config))

    def test_the_window_fills_in_a_row_and_the_total(self):
        import workbench_db

        self.fill()
        window = self.make_window(self.roms)
        window.open_folder(self.roms)
        panel = window.overview_panel
        panel.set_row(workbench_db.OverviewRow("nes", "current", 2, 1, 1, 0, "2026-11-24T20:15:00"))
        self.assertEqual(panel.tree.item("nes", "values")[:4], ("2", "1", "1", "0"))
        self.assertEqual(panel.tree.item("nes", "values")[-2:], ("2026-11-24 20:15", "current"))
        self.assertEqual(panel.tree.item(panel._TOTAL, "values")[:4], ("2", "1", "1", "0"))
        panel.set_row(workbench_db.OverviewRow("snes", "current", 1, 1, 0, 0, "2026-11-24T20:16:00"))
        self.assertEqual(panel.tree.item(panel._TOTAL, "values")[:4], ("3", "2", "1", "0"))

    def test_scan_all_on_the_command_line(self):
        self.fill()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = rf.main([str(self.roms), "--scan-all"])
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue().splitlines(), [
            "nes: 2 file(s), 2 read", "snes: 1 file(s), 1 read", "2 platform(s) scanned; nothing was deleted."])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rf.main([str(self.roms), "--scan-all", "--full"])
        self.assertIn("nes: 2 file(s), 2 read", output.getvalue())

    def test_scan_all_refuses_a_platform_folder(self):
        self.fill()
        error = io.StringIO()
        with contextlib.redirect_stderr(error), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rf.main([str(self.roms / "nes"), "--scan-all"]), 1)
        self.assertIn("is no roms folder", error.getvalue())


class OverviewTerminalBase(unittest.IsolatedAsyncioTestCase):
    """Step 6: the overview and the scan of all platforms in the terminal version."""

    def setUp(self):
        try:
            import rom_cleanup_workbench_tui as tui
        except ImportError as error:
            self.skipTest(f"Textual missing: {error}")
        self.tui = tui
        translations.set_language("en")
        self.addCleanup(translations.set_language, "en")
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.roms = Path(temp.name) / "roms"
        for platform, names in {"nes": {"Title (USA).nes": b"u", "Title (Japan).nes": b"j"},
                                "snes": {"Game (USA).sfc": b"g"}}.items():
            (self.roms / platform).mkdir(parents=True)
            for name, content in names.items():
                (self.roms / platform / name).write_bytes(content)
        self.config = rules_config()
        self.settings = Path(temp.name) / "settings.json"

    def analyze(self, directory, progress=None, rescan=False, full=False):
        import workbench_db

        root = workbench_db.collection_root(directory)
        if root is None:
            return rf.Review(rf.scan_directory(directory, self.config, progress), self.config)
        results = workbench_db.open_platform(root, directory, self.config, progress, rescan=rescan, full=full)
        return rf.Review(results, self.config, collection_root=root, directory=directory)

    def app(self, directory):
        return self.tui.WorkbenchApp(self.analyze, directory, "all", settings_path=self.settings,
                                     config_loader=lambda: self.config)

    async def settle(self, app, pilot):
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()

    def overview_rows(self, app):
        table = app.screen.query_one("#overview-table")
        return {key.value: [str(cell) for cell in table.get_row(key)] for key in table.rows}


class OverviewTerminalTests(OverviewTerminalBase):

    async def test_a_roms_folder_starts_with_the_overview(self):
        app = self.app(self.roms)
        async with app.run_test(size=(140, 30)) as pilot:
            await self.settle(app, pilot)
            self.assertTrue(app.overview_open())
            rows = self.overview_rows(app)
            self.assertEqual(list(rows), ["nes", "snes", "*total*"])
            self.assertEqual(rows["nes"][-1], "not scanned")

    async def test_enter_opens_a_platform_and_o_comes_back(self):
        app = self.app(self.roms)
        async with app.run_test(size=(140, 30)) as pilot:
            await self.settle(app, pilot)
            await pilot.press("enter")
            await self.settle(app, pilot)
            self.assertFalse(app.overview_open())
            self.assertEqual(app.directory, self.roms / "nes")
            self.assertEqual(len(app.review.results), 1)
            await pilot.press("o")
            await self.settle(app, pilot)
            self.assertTrue(app.overview_open())
            rows = self.overview_rows(app)
            self.assertEqual(rows["nes"][1:5], ["2", "1", "1", "0"])
            self.assertEqual(rows["nes"][-1], "current")

    async def test_escape_goes_back_to_the_overview_and_ends_there(self):
        app = self.app(self.roms)
        async with app.run_test(size=(140, 30)) as pilot:
            await self.settle(app, pilot)
            await pilot.press("enter")
            await self.settle(app, pilot)
            self.assertFalse(app.overview_open())
            await pilot.press("escape")
            await self.settle(app, pilot)
            self.assertTrue(app.overview_open())
            self.assertTrue(app.is_running)
            await pilot.press("escape")
            await pilot.pause()
            self.assertFalse(app.is_running)

    async def test_a_scans_all_platforms(self):
        app = self.app(self.roms)
        async with app.run_test(size=(140, 30)) as pilot:
            await self.settle(app, pilot)
            await pilot.press("a")
            await self.settle(app, pilot)
            self.assertTrue(app.overview_open())
            self.assertIsNone(app._batch)
            rows = self.overview_rows(app)
            self.assertEqual((rows["nes"][-1], rows["snes"][-1]), ("current", "current"))
            self.assertEqual(str(app.screen.query_one("#overview-status").render()), "2 platform(s) scanned.")

    async def test_a_finished_platform_is_filled_in_with_the_total(self):
        import workbench_db

        app = self.app(self.roms)
        async with app.run_test(size=(140, 30)) as pilot:
            await self.settle(app, pilot)
            app.screen.set_row(workbench_db.OverviewRow("nes", "current", 2, 1, 1, 0, "2026-11-24T20:15:00"))
            await pilot.pause()
            rows = self.overview_rows(app)
            self.assertEqual(rows["nes"][1:], ["2", "1", "1", "0", "2026-11-24 20:15", "current"])
            self.assertEqual(rows["*total*"][1:5], ["2", "1", "1", "0"])

    async def test_the_last_collection_opens_at_the_start(self):
        self.tui.save_last_collection(self.settings, self.roms)
        app = self.app(None)
        async with app.run_test(size=(140, 30)) as pilot:
            await self.settle(app, pilot)
            self.assertTrue(app.overview_open())
            self.assertEqual(app.collection_root, self.roms)

    async def test_a_platform_folder_on_its_own_opens_as_before(self):
        app = self.app(self.roms / "nes")
        async with app.run_test(size=(140, 30)) as pilot:
            await self.settle(app, pilot)
            self.assertFalse(app.overview_open())
            self.assertIsNone(app.collection_root)
            self.assertFalse((self.roms / ".rom_cleanup_workbench").exists())


class ManualMovesTests(PlatformFromDatabaseBase):
    """Step 7: k and x stay in the database until Proceed or a new scan; a changed file forgets them."""

    def review(self):
        directory = self.roms / "nes"
        return rf.Review(self.open_platform(), self.config, collection_root=self.roms, directory=directory)

    def two_files(self):
        self.write("nes", "Title (USA).nes", b"usa")
        self.write("nes", "Title (Japan).nes", b"jap")

    def moved(self, review):
        return {entry.path.name: (entry in result.keep) for result in review.results
                for entry in result.keep + result.marked if entry.moved}

    def test_k_survives_closing(self):
        self.two_files()
        review = self.review()
        result = review.results[0]
        review.promote(result, result.marked[0])
        again = self.review()
        self.assertEqual(self.moved(again), {"Title (Japan).nes": True})
        self.assertEqual(again.moved_count(), 1)

    def test_x_survives_closing_and_k_back_forgets_it(self):
        self.two_files()
        review = self.review()
        result = review.results[0]
        usa = result.keep[0]
        review.demote(result, usa)
        self.assertEqual(self.moved(self.review()), {"Title (USA).nes": False})
        review.promote(result, usa)  # back where the rules put it
        self.assertEqual(self.moved(self.review()), {})

    def test_a_changed_file_forgets_its_move(self):
        self.two_files()
        review = self.review()
        result = review.results[0]
        review.promote(result, result.marked[0])
        path = self.roms / "nes" / "Title (Japan).nes"
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000_000))
        self.open().save_facts("nes", rf.scan_facts(self.roms / "nes"))  # facts with the new time
        self.assertEqual(self.moved(self.review()), {})

    def test_a_new_scan_and_proceed_forget_the_moves(self):
        self.two_files()
        review = self.review()
        result = review.results[0]
        review.promote(result, result.marked[0])
        self.open_platform(rescan=True)
        self.assertEqual(self.moved(self.review()), {})
        review = self.review()
        result = review.results[0]
        review.demote(result, result.keep[0])
        review.delete()
        self.assertEqual(self.open().moves("nes"), {})


class ConfirmedSavesInDatabaseTests(PlatformFromDatabaseBase):
    """Step 7: confirmed status or save files of a collection live in its database."""

    def save_game(self):
        self.write_zip("nes", "1941.zip", {"1941.nes": b"r" * 8000})
        self.write("nes", "1941.state", b"s" * 100)

    def review(self):
        return rf.Review(self.open_platform(), self.config, collection_root=self.roms, directory=self.roms / "nes")

    def test_confirmed_files_go_into_the_database(self):
        import workbench_state

        self.save_game()
        settings = self.roms.parent / "settings.json"
        review = self.review()
        save_files = review.save_file_keys()
        self.assertEqual(len(save_files), 1)
        review.remember_save_files(settings, save_files)
        self.assertFalse(settings.exists())  # nothing in the settings file
        self.assertEqual(self.open().confirmed("nes"), {"1941.state": 100})
        again = self.review()
        again.confirm_save_files(again.confirmed_saves(settings))
        self.assertEqual(again.save_file_keys(), {})
        self.assertEqual(workbench_state.load_confirmed_saves(settings), {})

    def test_older_confirmations_from_the_settings_file_are_taken_over(self):
        import workbench_state

        self.save_game()
        settings = self.roms.parent / "settings.json"
        key = rf.save_file_key(self.roms / "nes" / "1941.state")
        other = rf.save_file_key(self.roms / "snes" / "x.state")
        workbench_state.add_confirmed_saves(settings, {key: 100, other: 5})
        review = self.review()
        review.confirm_save_files(review.confirmed_saves(settings))
        self.assertEqual(review.save_file_keys(), {})
        self.assertEqual(self.open().confirmed("nes"), {"1941.state": 100})  # only its own platform

    def test_a_folder_on_its_own_keeps_the_settings_file(self):
        import workbench_state

        self.save_game()
        settings = self.roms.parent / "settings.json"
        review = rf.Review(rf.scan_directory(self.roms / "nes", self.config), self.config)
        review.remember_save_files(settings, review.save_file_keys())
        self.assertEqual(len(workbench_state.load_confirmed_saves(settings)), 1)
        self.assertFalse((self.roms / ".rom_cleanup_workbench").exists())


class OwnPlatformSettingsTests(OverviewWindowBase):
    """Step 7: a default configuration plus, if wished, a platform's own priority, keywords and ZIP choice."""

    def config_file(self):
        path = self.roms.parent / "redundanz_config.json"
        if not path.exists():
            path.write_text('{"language": "en", "region_priority": ["USA", "none", "Japan"]}', encoding="utf-8")
        return rf.ConfigFile(path)

    def test_own_settings_are_stored_for_the_platform_only(self):
        import workbench_db

        self.fill()
        config_file = self.config_file()
        workbench_db.Collection(self.roms).close()
        values, own = workbench_db.settings_for(config_file, self.roms, "nes")
        self.assertFalse(own)
        workbench_db.save_settings_for(config_file, self.roms, "nes", True, "en", ["Japan", "none", "USA"], [], False)
        self.assertEqual(config_file.read()["region_priority"], ["USA", "none", "Japan"])  # the default stays
        values, own = workbench_db.settings_for(config_file, self.roms, "nes")
        self.assertTrue(own)
        self.assertEqual(values["region_priority"], ["Japan", "none", "USA"])
        self.assertEqual(workbench_db.settings_for(config_file, self.roms, "snes")[0]["region_priority"],
                         ["USA", "none", "Japan"])
        # back to the default: the own values are gone
        workbench_db.save_settings_for(config_file, self.roms, "nes", False, "en", ["USA", "none", "Japan"], [], False)
        self.assertFalse(workbench_db.settings_for(config_file, self.roms, "nes")[1])

    def test_a_new_own_configuration_starts_from_the_default(self):
        import workbench_db

        config_file = self.config_file()
        workbench_db.Collection(self.roms).close()
        values, own = workbench_db.settings_for(config_file, self.roms, "nes", own=True)
        self.assertTrue(own)
        self.assertEqual(values["region_priority"], ["USA", "none", "Japan"])

    def test_the_platform_and_the_overview_decide_with_the_own_settings(self):
        import workbench_db

        self.fill()
        with workbench_db.Collection(self.roms) as collection:
            collection.set_own_config("nes", {"region_priority": ["Japan", "none", "USA"]})
        config = workbench_db.platform_config(self.roms, self.roms / "nes", self.config)
        results = workbench_db.open_platform(self.roms, self.roms / "nes", config)
        self.assertEqual([e.path.name for e in results[0].keep], ["Title (Japan).nes"])
        rows = {row.folder: row for row in workbench_db.overview(self.roms, self.config)}
        self.assertTrue(rows["nes"].has_own_config)
        self.assertFalse(rows["snes"].has_own_config)

    def test_the_window_offers_default_or_own_and_saves_own(self):
        self.fill()
        window = self.make_window(self.roms)
        window.config_file = self.config_file()
        window.open_folder(self.roms)
        window.overview_panel.tree.selection_set("nes")
        window.overview_panel.open()
        self.wait(window)
        window.open_settings()
        panel = window.settings_panel
        self.assertEqual(panel.platform, "nes")
        self.assertEqual([button.cget("text") for button in panel.scope_buttons], ["Use the default", "Own for nes"])
        panel.own.set(True)
        panel._scope_changed()
        panel.regions.delete(0, "end")
        for region in ("Japan", "none", "USA"):
            panel.regions.insert("end", region)
        with mock.patch.object(window, "start_analysis") as analysis:
            window.save_settings(panel)
        analysis.assert_called_once()
        import workbench_db

        with workbench_db.Collection(self.roms) as collection:
            self.assertEqual(collection.own_config("nes")["region_priority"], ["Japan", "none", "USA"])
        self.assertEqual(window.config_file.read()["region_priority"], ["USA", "none", "Japan"])
        window.show_overview()
        self.assertEqual(window.overview_panel.tree.item("nes", "text"), "nes *")

    def test_a_folder_on_its_own_has_no_choice(self):
        self.write("nes", "Title (USA).nes", b"usa")
        window = self.make_window(self.roms / "nes")
        window.config_file = self.config_file()
        window.open_folder(self.roms / "nes")
        self.wait(window)
        window.open_settings()
        self.assertIsNone(window.settings_panel.platform)


class OwnPlatformSettingsTerminalTests(OverviewTerminalBase):
    async def test_the_terminal_settings_offer_default_or_own(self):
        import workbench_db

        config = self.roms.parent / "redundanz_config.json"
        config.write_text('{"language": "en", "region_priority": ["USA", "none", "Japan"]}', encoding="utf-8")
        app = self.tui.WorkbenchApp(self.analyze, self.roms, "all", config_file=rf.ConfigFile(config),
                                    settings_path=self.settings, config_loader=lambda: self.config)
        async with app.run_test(size=(140, 40)) as pilot:
            await self.settle(app, pilot)
            await pilot.press("enter")  # open nes
            await self.settle(app, pilot)
            await pilot.press("s")
            await self.settle(app, pilot)
            screen = app.screen
            self.assertEqual(screen.platform, "nes")
            screen.query_one("#scope-own").value = True
            await pilot.pause()
            self.assertTrue(screen.own)
            screen.regions = ["Japan", "none", "USA"]
            await pilot.press("ctrl+s")
            await self.settle(app, pilot)
            with workbench_db.Collection(self.roms) as collection:
                self.assertEqual(collection.own_config("nes")["region_priority"], ["Japan", "none", "USA"])
            self.assertEqual(rf.ConfigFile(config).read()["region_priority"], ["USA", "none", "Japan"])


class RescanFlagTests(unittest.TestCase):
    """F5 asks for a new scan; analyses without the parameter (as in many tests) still work."""

    def test_both_front_ends_pass_rescan_only_where_it_is_known(self):
        import rom_cleanup_workbench_window as window_module

        modules = [window_module]
        try:
            import rom_cleanup_workbench_tui as tui_module
            modules.append(tui_module)
        except ImportError:
            pass
        for module in modules:
            calls = []

            def knows(directory, progress=None, rescan=False):
                calls.append(rescan)

            module._call_analyze(knows, Path("."), None, True)
            module._call_analyze(lambda d, p=None: calls.append("old"), Path("."), None, True)
            self.assertEqual(calls, [True, "old"], module.__name__)


class ZipTests(RedundanzTestCase):
    def test_zip_with_same_tags_and_same_content_is_redundant(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (USA).zip", {"Title (USA).bin": b"rom"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).bin"])
        self.assertEqual(self.names(result.marked), ["Title (USA).zip"])

    def test_zip_next_to_plain_file_is_marked_even_with_other_content(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (USA).zip", {"Title (USA).bin": b"different"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).bin"])
        self.assertEqual(self.names(result.marked), ["Title (USA).zip"])
        self.assertIn("Plain file preferred", result.marked[0].notes)
        self.assertEqual(result.marked[0].notes[-1], "Game content deviates from the kept version")

    def test_all_zips_next_to_plain_file_are_marked(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (USA).zip", {"a.bin": b"different"})
        self.write_zip("Title [USA].zip", {"a.bin": b"different"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).bin"])
        for entry in result.marked:
            self.assertEqual(entry.notes[-1], "Game content deviates from the kept version")

    def test_zip_with_better_region_stays_without_plain_file_of_same_version(self):
        self.write("Title (Japan).bin", b"jap")
        self.write_zip("Title (USA).zip", {"a.bin": b"usa"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).zip"])
        self.assertEqual(self.names(result.marked), ["Title (Japan).bin"])

    def test_zip_with_only_copy_of_a_disc_is_marked_with_warning(self):
        self.write("Title (USA) (Disc 2).bin", b"two")
        self.write_zip("Title (USA) (Disc 1).zip", {"a.bin": b"one"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA) (Disc 2).bin"])
        self.assertEqual(result.marked[0].notes[-1], "Game content deviates from the kept version")

    def test_zips_of_all_discs_stay_without_plain_file(self):
        self.write_zip("Title (USA) (Disc 1).zip", {"a.bin": b"one"})
        self.write_zip("Title (USA) (Disc 2).zip", {"a.bin": b"two"})
        self.assertEqual(self.single().marked, [])

    def test_zip_of_a_disc_with_plain_copy_is_marked(self):
        self.write("Title (USA) (Disc 1).bin", b"one")
        self.write("Title (USA) (Disc 2).bin", b"two")
        self.write_zip("Title (USA) (Disc 1).zip", {"a.bin": b"one"})
        result = self.single()
        self.assertEqual(len(result.keep), 2)
        self.assertEqual(self.names(result.marked), ["Title (USA) (Disc 1).zip"])

    def test_marked_zip_with_unique_content_gets_warning(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (Europe).zip", {"a.bin": b"unique"})
        marked = self.single().marked[0]
        self.assertEqual(marked.notes, ["Priority: Europe after USA", "Game content deviates from the kept version"])

    def test_two_identical_zips_leave_one(self):
        self.write_zip("Title (USA).zip", {"a.bin": b"rom"})
        self.write_zip("Title [USA].zip", {"a.bin": b"rom"})
        result = self.single()
        self.assertEqual(len(result.keep), 1)
        self.assertEqual(len(result.marked), 1)

    def test_region_is_taken_from_zip_content(self):
        self.write("Title (Europe).bin", b"eur")
        self.write_zip("Title.zip", {"Title (USA).bin": b"usa"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title.zip"])
        self.assertEqual(self.names(result.marked), ["Title (Europe).bin"])

    def test_region_is_taken_from_zip_content_with_other_separators(self):
        self.write("Pac Man (Japan).bin", b"jap")
        self.write_zip("Pac-Man.zip", {"Pac_Man (USA).bin": b"usa"})
        self.assertEqual(self.names(self.single().keep), ["Pac-Man.zip"])

    def test_region_is_taken_from_zip_content_with_equivalent_name(self):
        self.write("Katz und Maus, The (Japan).bin", b"jap")
        self.write_zip("The Katz & Maus.zip", {"Katz und Maus, The (USA).bin": b"usa"})
        self.assertEqual(self.names(self.single().keep), ["The Katz & Maus.zip"])

    def test_version_is_taken_from_zip_content(self):
        self.write("Title (USA) (v1.0).bin", b"old")
        self.write_zip("Title (USA).zip", {"Title (USA) (v1.1).bin": b"new"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).zip"])
        self.assertEqual(self.names(result.marked), ["Title (USA) (v1.0).bin"])

    def patch_zip(self, name, local_offset, central_offset, value):
        """Changes a field in the local and the central header of the archive."""
        path = self.dir / name
        data = bytearray(path.read_bytes())
        data[data.index(b"PK\x03\x04") + local_offset] = value
        data[data.index(b"PK\x01\x02") + central_offset] = value
        path.write_bytes(data)

    def test_defective_zip_is_marked(self):
        self.write("Title (USA).zip", b"not a zip")
        self.write("Title (Japan).bin", b"rom")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (Japan).bin"])
        self.assertEqual(self.names(result.marked), ["Title (USA).zip"])
        self.assertIn("ZIP defective", result.marked[0].notes[0])

    def test_single_defective_zip_is_marked(self):
        self.write("Title (USA).zip", b"not a zip")
        result = self.single()
        self.assertEqual(result.keep, [])
        self.assertEqual(self.names(result.marked), ["Title (USA).zip"])

    def test_zip_with_damaged_content_is_marked(self):
        self.write_zip("Title (USA).zip", {"a.bin": b"intact-bytes content"})
        path = self.dir / "Title (USA).zip"
        path.write_bytes(path.read_bytes().replace(b"intact-bytes", b"damaged-byte"))
        self.assertEqual(self.names(self.single().marked), ["Title (USA).zip"])

    def test_encrypted_zip_is_marked(self):
        self.write_zip("Title (USA).zip", {"a.bin": b"rom"})
        self.patch_zip("Title (USA).zip", 6, 8, 0x1)
        result = self.single()
        self.assertEqual(self.names(result.marked), ["Title (USA).zip"])
        self.assertIn("encrypted", result.marked[0].notes[0])

    def test_zip_with_unknown_compression_next_to_plain_file_is_marked(self):
        self.write("Title (Japan).bin", b"rom")
        self.write_zip("Title (USA).zip", {"a.bin": b"rom"})
        self.patch_zip("Title (USA).zip", 8, 10, 9)  # 9 = Deflate64
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (Japan).bin"])
        self.assertEqual(self.names(result.marked), ["Title (USA).zip"])
        self.assertIn("please check yourself", result.marked[0].notes[0])

    def test_unreadable_zip_takes_no_part_in_the_size_comparison(self):
        self.write("Title (Japan).bin", b"x" * 10)
        self.write_zip("Title (USA).zip", {"a.bin": b"x" * 10_000})
        self.patch_zip("Title (USA).zip", 8, 10, 9)  # 9 = Deflate64
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (Japan).bin"])
        self.assertFalse(any(note.startswith("Suspected") for note in result.keep[0].notes))

    def test_single_zip_with_unknown_compression_is_kept(self):
        self.write_zip("Title (USA).zip", {"a.bin": b"rom"})
        self.patch_zip("Title (USA).zip", 8, 10, 9)  # 9 = Deflate64
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).zip"])
        self.assertEqual(result.marked, [])

    def test_locked_zip_is_kept(self):
        self.write_zip("Title (USA).zip", {"a.bin": b"rom"})
        with mock.patch("zipfile.ZipFile", side_effect=PermissionError("locked")):
            result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).zip"])
        self.assertEqual(result.marked, [])

    def test_malicious_member_path_writes_nothing(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title.zip", {"../../evil.bin": b"rom"})
        result = self.single()
        self.assertEqual(self.names(result.marked), ["Title.zip"])
        self.assertFalse((self.dir.parent.parent / "evil.bin").exists())


class ProblemTests(RedundanzTestCase):
    def test_clear_decision_is_no_problem(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        self.assertEqual(self.single().problems, [])

    def assert_problem(self, text):
        self.assertTrue(any(text in problem for problem in self.single().problems), self.single().problems)

    def test_nothing_left(self):
        self.write("Title (USA) (Hack).bin")
        self.assert_problem("No file")

    def test_zip_of_the_same_version_with_other_content(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (USA).zip", {"a.bin": b"other"})
        self.assert_problem("Same version as the kept file, but different content")

    def test_zip_of_another_region_with_other_content_is_no_problem(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (Europe).zip", {"a.bin": b"unique"})
        result = self.single()
        self.assertEqual(result.problems, [])
        self.assertEqual(result.marked[0].notes,
                         ["Priority: Europe after USA", "Game content deviates from the kept version"])

    def test_arch_rivals_only_names_the_spellings(self):
        self.config = replace(self.config, region_priority=["Germany", "Europe", "USA", "none", "Japan", "Beta"],
                              prefer_zip=True)
        eur, usa = b"e" * 4000, b"u" * 4000
        self.write_zip("Arch Rivals - A Basketbrawl! (Europe).zip", {"a.nes": eur})
        self.write("Arch Rivals - A Basketbrawl! (Europe).nes", eur)
        self.write_zip("Arch Rivals - A Basketbrawl! (USA).zip", {"a.nes": usa})
        self.write("Arch Rivals - A Basketbrawl! (USA).nes", usa)
        self.write("160 Arch Rivals-A Basket Brawl!.nes", b"n" * 4000)
        self.assertEqual(self.single().problems, ["Different spellings of the name"])

    def test_defective_zip(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).zip", b"not a zip")
        self.assert_problem("ZIP defective")

    def test_unreadable_zip_that_is_kept(self):
        self.write_zip("Title (USA).zip", {"a.bin": b"rom"})
        with mock.patch("zipfile.ZipFile", side_effect=PermissionError("locked")):
            result = self.single()
        self.assertIn("ZIP unreadable", result.problems)

    def test_tie(self):
        self.write("Title (USA) (Foo).bin")
        self.write("Title (USA) (Bar).bin")
        self.assert_problem("Tie")

    def test_zips_with_different_content(self):
        self.write_zip("Title (USA).zip", {"a.bin": b"one"})
        self.write_zip("Title [USA].zip", {"a.bin": b"two"})
        self.assert_problem("ZIPs with different content")

    def test_different_spelling(self):
        self.write("Title 1-2 (USA).bin")
        self.write("Title 12 (Japan).bin")
        self.assert_problem("spellings")

    def test_case_alone_is_no_different_spelling(self):
        self.write("TITLE (USA).bin")
        self.write("title (Japan).bin")
        self.assertEqual(self.single().problems, [])

    def test_other_file_type(self):
        self.write("Title (USA).nes")
        self.write("Title (Japan).sfc")
        self.assert_problem("Different file type")

    def test_file_type_inside_kept_zip_counts(self):
        self.write_zip("Title (USA).zip", {"Title (USA).nes": b"usa"})
        self.write("Title (Japan).nes", b"jap")
        self.assertEqual(self.single().problems, [])


class ReviewTests(RedundanzTestCase):
    def review(self):
        results = self.scan()
        return rf.Review(results, self.config), results

    def test_promote_moves_file_to_its_place_among_kept_files(self):
        self.write("Title (USA) (Disc 2).bin")
        self.write("Title (USA) (Disc 3).bin")
        self.write("Title (USA) (Disc 1).zip", b"not a zip")
        review, [result] = self.review()
        self.write("Title (USA) (Disc 1).bin")
        entry = rf.Entry(self.dir / "Title (USA) (Disc 1).bin", "Title", ["usa", "Disc 1"])
        result.marked.append(entry)
        self.assertTrue(review.promote(result, entry))
        self.assertEqual(
            self.names(result.keep),
            ["Title (USA) (Disc 1).bin", "Title (USA) (Disc 2).bin", "Title (USA) (Disc 3).bin"],
        )
        self.assertNotIn(entry, result.marked)

    def test_demote_moves_file_to_the_bottom(self):
        self.write("Title (USA).bin")
        self.write("Title (Europe).bin")
        self.write("Title (Japan).bin")
        review, [result] = self.review()
        kept = result.keep[0]
        self.assertTrue(review.demote(result, kept))
        self.assertEqual(result.keep, [])
        self.assertEqual(result.marked[-1], kept)
        self.assertEqual(len(result.marked), 3)

    def test_moving_in_wrong_direction_changes_nothing(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        review, [result] = self.review()
        self.assertFalse(review.promote(result, result.keep[0]))
        self.assertFalse(review.demote(result, result.marked[0]))
        self.assertEqual(review.moved_count(), 0)

    def test_moving_back_is_no_manual_change(self):
        self.write("Title (USA).bin")
        review, [result] = self.review()
        entry = result.keep[0]
        review.demote(result, entry)
        self.assertEqual(review.moved_count(), 1)
        review.promote(result, entry)
        self.assertEqual(review.moved_count(), 0)

    def test_game_without_marked_file_is_hidden(self):
        self.write("Clear (USA).bin")
        review, [result] = self.review()
        self.assertFalse(review.is_visible(result, False))
        self.assertFalse(review.is_visible(result, True))

    def test_problem_without_marked_file_is_hidden_and_not_counted(self):
        self.write_zip("Title (USA).zip", {"a.bin": b"one"})
        self.write_zip("Title [USA].zip", {"a.bin": b"two"})
        review, [result] = self.review()
        self.assertTrue(result.problems)
        self.assertFalse(review.is_visible(result, True))
        self.assertIn("Problematic: 0", review.status(False))

    def test_filter_shows_problems_and_manual_changes(self):
        self.write("Clear (USA).bin")
        self.write("Clear (Japan).bin")
        self.write("Problem (USA) (Hack).bin")
        review, results = self.review()
        clear, problem = results
        self.assertFalse(review.is_visible(clear, True))
        self.assertTrue(review.is_visible(problem, True))
        self.assertTrue(review.is_visible(clear, False))
        review.demote(clear, clear.keep[0])
        self.assertTrue(review.is_visible(clear, True))

    def write_save_file_game(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title.srm", b"x" * 100)

    def test_confirmed_save_file_is_kept_but_no_longer_shown(self):
        self.write_save_file_game()
        review, [result] = self.review()
        keys = review.save_file_keys()
        self.assertEqual(keys, {rf.save_file_key(self.dir / "Title.srm"): 100})
        review.confirm_save_files(keys)
        self.assertEqual(self.names(result.keep), ["Title (USA).sfc", "Title.srm"])
        self.assertEqual(result.keep[1].notes, ["Status or save file, confirmed when deleting"])
        self.assertEqual(result.problems, [])
        self.assertFalse(review.is_visible(result, True))
        self.assertFalse(review.is_visible(result, False))
        self.assertTrue(review.is_visible(result, False, True))
        self.assertTrue(review.nothing_to_do())
        self.assertEqual(review.save_file_keys(), {})

    def test_save_file_with_changed_size_is_suspected_again(self):
        self.write_save_file_game()
        review, [result] = self.review()
        review.confirm_save_files({rf.save_file_key(self.dir / "Title.srm"): 99})
        self.assertIn("Suspected status or save file", result.problems)
        self.assertFalse(review.nothing_to_do())

    def test_confirmed_save_file_is_still_never_deleted(self):
        self.write_save_file_game()
        self.write("Title (Japan).sfc", b"x" * 1000)
        review, [result] = self.review()
        review.confirm_save_files(review.save_file_keys())
        self.assertEqual(rf.marked_paths(review.results), [self.dir / "Title (Japan).sfc"])

    def test_save_file_key_ignores_case_and_relative_paths_on_windows(self):
        key = rf.save_file_key(self.dir / "Title.srm")
        self.assertEqual(key, rf.save_file_key(Path(str(self.dir / "Title.srm"))))
        self.assertTrue(Path(key).is_absolute())

    def test_confirm_message_names_save_files_that_become_legitimate(self):
        self.write_save_file_game()
        self.write("Title (Japan).sfc", b"x" * 1000)
        review, _ = self.review()
        self.assertIn("Kept as status or save files: 1 file(s)", review.confirm_message(False))
        review.confirm_save_files(review.save_file_keys())
        self.assertNotIn("status or save files", review.confirm_message(False))

    def test_suspected_save_file_is_visible_in_every_view(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title.srm", b"x" * 100)
        review, [result] = self.review()
        self.assertEqual(result.marked, [])
        self.assertTrue(review.is_visible(result, True))
        self.assertTrue(review.is_visible(result, False))
        self.assertFalse(review.nothing_to_do())
        self.assertIn("Showing: 1 of 1 games", review.status(True))
        self.assertIn("Problematic: 1", review.status(True))
        self.assertIn("To delete: 0 file(s)", review.status(True))

    def test_confirm_message_names_hidden_files_and_lost_games(self):
        self.write("Clear (USA).bin")
        self.write("Clear (Japan).bin")
        self.write("Problem (USA) (Hack).bin")
        review, _ = self.review()
        message = review.confirm_message(True)
        self.assertIn("2 file(s)", message)
        self.assertIn("Not shown: 1 file(s)", message)
        self.assertIn("game(s): Problem", message)

    def test_search_finds_text_anywhere_and_ignores_case(self):
        self.write("Super Mario (USA).bin")
        _, [result] = self.review()
        for pattern in ("mario", "MARIO", "(usa)", ".bin", "", "   "):
            self.assertTrue(rf.matches_search(result, pattern), pattern)
        self.assertFalse(rf.matches_search(result, "Zelda"))

    def test_search_knows_star_and_question_mark(self):
        self.write("Super Mario 2 (USA).bin")
        _, [result] = self.review()
        self.assertTrue(rf.matches_search(result, "*Mario*"))
        self.assertTrue(rf.matches_search(result, "Super*(USA)"))
        self.assertTrue(rf.matches_search(result, "Mario?2"))
        self.assertFalse(rf.matches_search(result, "Mario?3"))
        self.assertFalse(rf.matches_search(result, "Mario??2"))

    def test_search_treats_other_characters_literally(self):
        self.write("Title [!].bin")
        _, [result] = self.review()
        self.assertTrue(rf.matches_search(result, "[!]"))
        self.assertFalse(rf.matches_search(result, "[abc]"))
        self.assertFalse(rf.matches_search(result, "T.tle"))

    def test_search_looks_at_every_file_of_the_game(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        _, [result] = self.review()
        self.assertTrue(rf.matches_search(result, "Japan"))
        self.assertTrue(rf.matches_search(result, "USA"))

    def test_search_narrows_the_view_and_the_status(self):
        self.write("One (USA).bin")
        self.write("One (Japan).bin")
        self.write("Two (USA).bin")
        self.write("Two (Japan).bin")
        review, results = self.review()
        one, two = results
        self.assertTrue(review.is_visible(one, False, False, "One"))
        self.assertFalse(review.is_visible(two, False, False, "One"))
        self.assertIn("Showing: 1 of 2 games", review.status(False, False, "One"))
        self.assertIn("To delete: 2 file(s)", review.status(False, False, "One"))

    def test_search_also_hides_games_changed_by_hand(self):
        self.write("One (USA).bin")
        self.write("Two (USA).bin")
        review, results = self.review()
        one, two = results
        review.demote(one, one.keep[0])
        self.assertTrue(review.is_visible(one, True))
        self.assertTrue(review.is_visible(one, True, False, "One"))
        self.assertFalse(review.is_visible(one, True, False, "Two"))

    def test_confirm_message_names_files_hidden_by_the_search(self):
        self.write("One (USA).bin")
        self.write("One (Japan).bin")
        self.write("Two (USA).bin")
        self.write("Two (Japan).bin")
        review, _ = self.review()
        message = review.confirm_message(False, False, "One")
        self.assertIn("Permanently delete 2 file(s)", message)
        self.assertIn("Not shown: 1 file(s) from games hidden by the filter", message)


class LanguageTests(RedundanzTestCase):
    @staticmethod
    def fields(text):
        import string

        return {name for _, name, _, _ in string.Formatter().parse(text) if name}

    def test_every_language_has_every_text_with_the_same_fields(self):
        english = translations.LANGUAGES["en"]
        self.assertEqual(set(translations.LANGUAGES), {"en", "de", "it", "es", "fr", "ja"})
        for language, texts in translations.LANGUAGES.items():
            self.assertEqual(set(texts), set(english), language)
            for key, text in texts.items():
                self.assertEqual(self.fields(text), self.fields(english[key]), f"{language} {key}")
                self.assertTrue(text, f"{language} {key}")

    def test_every_text_can_be_filled_in_every_language(self):
        for language in translations.LANGUAGES:
            translations.set_language(language)
            for key, text in translations.LANGUAGES[language].items():
                translations.tr(key, **{name: "1" for name in self.fields(text)})

    def test_unknown_language_is_refused(self):
        with self.assertRaises(ValueError):
            translations.set_language("xx")
        self.assertEqual(translations.current_language(), "en")

    def test_language_comes_from_the_configuration(self):
        path = self.dir.with_name(self.dir.name + "-config.json")
        self.addCleanup(path.unlink, missing_ok=True)
        self.assertEqual(rf.Config.load(None).language, "en")
        path.write_text('{"language": "ja"}', encoding="utf-8")
        self.assertEqual(rf.Config.load(path).language, "ja")
        path.write_text('{"language": "xx"}', encoding="utf-8")
        with self.assertRaises(ValueError) as error:
            rf.Config.load(path)
        self.assertIn("en, de, it, es, fr, ja", str(error.exception))
        # The text has a field called "key": It must not collide with the parameter of tr().
        path.write_text('{"part_tags": "Disc"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, 'Wrong type for "part_tags"'):
            rf.Config.load(path)

    def test_no_region_word_of_every_language_works(self):
        for word in translations.NO_REGION_WORDS:
            config = rf.Config(["USA", word, "Japan"], {}, [], [])
            self.assertEqual(config.rank([]), (1, 1), word)  # (place, best entry): both "none"
            self.assertFalse(config.is_region(config.canonical(word)), word)

    def test_rules_decide_the_same_in_every_language(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title (Japan).sfc", b"x" * 1000)
        self.write("Title.srm", b"x" * 100)
        self.write("Other (USA) (Beta 1).bin")
        self.write("Other (USA) (Beta 2).bin")
        self.write("Tie (USA).bin")
        self.write("Tie [USA].bin")
        decisions = {}
        for language in translations.LANGUAGES:
            translations.set_language(language)
            review = rf.Review(self.scan(), self.config)
            decisions[language] = [
                (self.names(result.keep), self.names(result.marked), len(result.problems)) for result in review.results
            ]
            review.confirm_save_files(review.save_file_keys())
            self.assertTrue(review.nothing_to_do() is False)
            self.assertEqual(review.save_file_keys(), {}, language)
        self.assertEqual(len({str(value) for value in decisions.values()}), 1, decisions)

    def test_notes_and_problems_are_shown_in_the_chosen_language(self):
        translations.set_language("de")
        self.write("Title (USA) (Beta 1).bin")
        self.write("Title (USA) (Beta 2).bin")
        self.write("Save (USA).sfc", b"x" * 1000)
        self.write("Save.srm", b"x" * 100)
        save, other = self.scan()
        self.assertEqual(save.title, "Save")
        self.assertIn("Ältere Beta", other.marked[0].notes)
        self.assertIn("Verdacht auf Status- oder Spielstanddatei", save.problems)
        review = rf.Review([save], self.config)
        review.confirm_save_files(review.save_file_keys())
        self.assertEqual(save.keep[1].notes, ["Status- oder Spielstanddatei, beim Löschen bestätigt"])
        self.assertIn("Angezeigt: 0 von 1 Spielen", review.status(False))

    def test_format_kb_uses_the_separator_of_the_language(self):
        import rom_cleanup_workbench_window as window_module

        for language, expected in (
            ("en", "1,234 KB"), ("de", "1.234 KB"), ("it", "1.234 KB"),
            ("es", "1.234 KB"), ("fr", "1 234 Ko"), ("ja", "1,234 KB"),
        ):
            translations.set_language(language)
            self.assertEqual(window_module.format_kb(1234 * 1024), expected, language)


class ConfigFileTests(RedundanzTestCase):
    def config_file(self, content=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "redundanz_config.json"
        if content is not None:
            path.write_text(content, encoding="utf-8")
        return rf.ConfigFile(path)

    def test_missing_file_shows_the_defaults(self):
        values = self.config_file().read()
        self.assertEqual(values, {
            "language": "en", "region_priority": ["USA", "Europe", "none", "Japan", "Beta"],
            "delete_tags": [], "prefer_zip": False,
        })

    def test_write_keeps_other_entries_and_their_order(self):
        config = self.config_file(
            '{\n  "region_priority": ["USA"],\n  "region_aliases": {"Germany": ["DE"]},\n  "delete_tags": []\n}\n'
        )
        config.write("de", ["Germany", "Europe", "none"], ["Hack", "Hacks"])
        text = config.path.read_text(encoding="utf-8")
        self.assertEqual(text, (
            '{\n  "region_priority": ["Germany", "Europe", "none"],\n'
            '  "region_aliases": {\n    "Germany": ["DE"]\n  },\n'
            '  "delete_tags": ["Hack", "Hacks"],\n  "language": "de"\n}\n'
        ))
        loaded = rf.Config.load(config.path)
        self.assertEqual(loaded.region_aliases, {"Germany": ["DE"]})
        self.assertEqual(config.read()["region_priority"], ["Germany", "Europe", "none"])

    def test_write_saves_prefer_zip_and_none_leaves_it(self):
        config = self.config_file('{"prefer_zip": true}')
        self.assertTrue(config.read()["prefer_zip"])
        config.write("en", ["USA"], [])
        self.assertTrue(rf.Config.load(config.path).prefer_zip)
        config.write("en", ["USA"], [], False)
        self.assertFalse(rf.Config.load(config.path).prefer_zip)
        self.assertFalse(config.read()["prefer_zip"])

    def test_write_creates_a_missing_file(self):
        config = self.config_file()
        config.write("ja", ["Japan", "USA"], [])
        self.assertEqual(rf.Config.load(config.path).language, "ja")
        self.assertEqual(config.read()["delete_tags"], [])

    def test_write_drops_empty_entries_and_spaces(self):
        config = self.config_file()
        config.write("en", [" USA ", "", "Japan"], [" Hack ", " "])
        self.assertEqual(config.read()["region_priority"], ["USA", "Japan"])
        self.assertEqual(config.read()["delete_tags"], ["Hack"])

    def test_old_file_shows_its_low_priority_tags_in_the_list_and_saving_drops_them(self):
        old = ('{\n  "region_priority": ["Germany", "Europe", "USA", "none", "Japan"],\n'
               '  "delete_tags": [],\n  "low_priority_tags": ["Beta", "Proto", "Alpha"]\n}\n')
        config = self.config_file(old)
        values = config.read()
        self.assertEqual(values["region_priority"],
                         ["Germany", "Europe", "USA", "none", "Japan", "Beta", "Proto", "Alpha"])
        self.assertEqual(values["delete_tags"], [])  # the user's own value stays
        config.write("en", values["region_priority"], ["Hack", "Hacks"])
        text = config.path.read_text(encoding="utf-8")
        self.assertNotIn("low_priority_tags", text)
        self.assertIn('"region_priority": ["Germany", "Europe", "USA", "none", "Japan", "Beta", "Proto", "Alpha"]',
                      text)
        loaded = rf.Config.load(config.path)
        self.assertEqual(loaded.delete_tags, ["Hack", "Hacks"])
        self.assertEqual(loaded.region_priority,
                         ["Germany", "Europe", "USA", "none", "Japan", "Beta", "Proto", "Alpha"])

    def test_old_file_without_none_gets_none_before_the_keywords(self):
        config = self.config_file('{"region_priority": ["USA", "Europe"], "low_priority_tags": ["Beta"]}')
        self.assertEqual(config.read()["region_priority"], ["USA", "Europe", "none", "Beta"])

    def test_low_priority_tags_of_the_wrong_type_are_reported(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "c.json"
        path.write_text('{"low_priority_tags": "Beta"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, 'Wrong type for "low_priority_tags"'):
            rf.Config.load(path)

    def test_wrong_values_leave_the_file_unchanged(self):
        original = '{"region_priority": ["USA"], "language": "en"}'
        config = self.config_file(original)
        for language, regions, tags, message in (
            ("en", [], [], "at least one region"),
            ("en", [" "], [], "at least one region"),
            ("en", ["USA", "usa"], [], '"usa" appears more than once'),
            ("en", ["USA"], ["Beta", "beta"], '"beta" appears more than once'),
            ("xx", ["USA"], [], 'Unknown language "xx"'),
        ):
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                config.write(language, regions, tags)
            self.assertEqual(config.path.read_text(encoding="utf-8"), original)
        self.assertEqual(sorted(path.name for path in config.path.parent.iterdir()), ["redundanz_config.json"])

    def test_broken_file_is_neither_read_nor_overwritten(self):
        for content in ("{not json", "[1, 2]"):
            config = self.config_file(content)
            with self.subTest(content):
                with self.assertRaises(ValueError):
                    config.read()
                with self.assertRaises(ValueError):
                    config.write("en", ["USA"], [])
                self.assertEqual(config.path.read_text(encoding="utf-8"), content)


class ProgressTests(RedundanzTestCase):
    def test_scan_ignores_files_starting_with_gamelist(self):
        for name in ("gamelist.xml", "gamelist.xml.old", "GameList (USA).txt", "gamelist2 (Proto).bin"):
            self.write(name)
        self.write("Title (USA).bin")
        self.write("My gamelist (USA).bin")
        reports = []
        results = rf.scan_directory(self.dir, self.config, lambda done, total: reports.append((done, total)))
        self.assertEqual([result.title for result in results], ["My gamelist", "Title"])
        self.assertEqual(reports[-1], (2, 2))
        self.assertEqual(rf.marked_paths(results), [])

    def test_scan_ignores_names_starting_with_a_dot(self):
        for name in (".xxx", ".Title (Japan).bin", "._Title (USA).bin", ".DS_Store"):
            self.write(name)
        self.write("Title (USA).bin")
        self.write("Title.v1 (USA).bin")
        reports = []
        results = rf.scan_directory(self.dir, self.config, lambda done, total: reports.append((done, total)))
        self.assertEqual(
            sorted(entry.path.name for result in results for entry in result.keep + result.marked),
            ["Title (USA).bin", "Title.v1 (USA).bin"],
        )
        self.assertEqual(reports[-1], (2, 2))

    @unittest.skipUnless(hasattr(__import__("ctypes"), "windll"), "Windows only")
    def test_scan_ignores_files_with_the_windows_hidden_attribute(self):
        import ctypes

        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        hidden = self.dir / "Title (Japan).bin"
        self.assertTrue(ctypes.windll.kernel32.SetFileAttributesW(str(hidden), 0x2))
        self.addCleanup(ctypes.windll.kernel32.SetFileAttributesW, str(hidden), 0x80)
        results = rf.scan_directory(self.dir, self.config)
        self.assertEqual([self.names(result.keep) for result in results], [["Title (USA).bin"]])
        self.assertEqual(rf.marked_paths(results), [])

    def test_unreadable_attributes_do_not_hide_a_file(self):
        self.write("Title (USA).bin")
        with mock.patch.object(Path, "stat", side_effect=OSError("locked")):
            self.assertFalse(rf._is_hidden(self.dir / "Title (USA).bin"))

    def test_scan_reports_every_file_up_to_the_total(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        self.write("Another (USA).bin")
        reports = []
        rf.scan_directory(self.dir, self.config, lambda done, total: reports.append((done, total)))
        self.assertEqual(reports[0], (0, 3))
        self.assertEqual(reports[-1], (3, 3))
        self.assertEqual({total for _, total in reports}, {3})

    def test_empty_folder_reports_zero(self):
        reports = []
        rf.scan_directory(self.dir, self.config, lambda done, total: reports.append((done, total)))
        self.assertEqual(reports, [(0, 0)])


class ReviewWindowTests(RedundanzTestCase):
    def settings_file(self):
        """Outside the test folder, so that the file does not count as a game there."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name) / "settings.json"

    def open_window(self, only_problems=False, settings_path=None, scope="marked"):
        """Most tests need the games with marks; scope=None uses the saved state."""
        try:
            import tkinter

            import rom_cleanup_workbench_window
            window = rom_cleanup_workbench_window.ReviewWindow(
                lambda _directory, _progress=None: rf.Review(self.scan(), self.config), self.dir,
                "problems" if only_problems else scope,
                settings_path or self.settings_file(),
            )
        except (ImportError, RuntimeError) as error:
            self.skipTest(f"No window possible: {error}")
        def close():
            with contextlib.suppress(tkinter.TclError):
                window.root.destroy()

        self.addCleanup(close)
        window.root.withdraw()
        window.analyze_now()
        return window

    def wait_for_analysis(self, window):
        deadline = time.monotonic() + 10
        while window._analysis is not None and time.monotonic() < deadline:
            window.root.update()
            time.sleep(0.01)
        self.assertIsNone(window._analysis)
        # Garbage collection may only run again once all threads have finished.
        for worker in list(window._workers):
            worker.join(10)
        window._enable_gc_when_idle()
        self.assertTrue(gc.isenabled())

    def row_of(self, window, name):
        return next(row for row, (_, entry) in window._files.items() if entry.path.name == name)

    def children_text(self, window, parent):
        return [window.tree.item(row, "text") for row in window.tree.get_children(parent)]

    def write_two_games(self):
        self.write("One (USA).bin")
        self.write("One (Japan).bin")
        self.write("Two (USA).bin")
        self.write("Two (Japan).bin")

    def search_for(self, window, pattern):
        window.search.set(pattern)
        window._apply_search()

    def test_search_filters_the_list_and_clearing_restores_it(self):
        self.write_two_games()
        window = self.open_window()
        self.search_for(window, "Two")
        self.assertEqual(self.children_text_of_games(window), ["Two"])
        self.assertIn("Showing: 1 of 2 games", window.status.get())
        self.search_for(window, "")
        self.assertEqual(self.children_text_of_games(window), ["One", "Two"])

    def children_text_of_games(self, window):
        return [text for text in self.children_text(window, "") if not text.startswith("─")]

    def test_search_without_hit_shows_an_empty_list(self):
        self.write_two_games()
        window = self.open_window()
        self.search_for(window, "Zelda")
        self.assertEqual(window.tree.get_children(), ())
        self.assertIn("Showing: 0 of 2 games", window.status.get())
        window.demote_selected()  # Must not fail, and there is nothing it could change.
        self.assertEqual(window.review.moved_count(), 0)

    def test_search_only_takes_effect_after_the_delay(self):
        self.write_two_games()
        window = self.open_window()
        window.search.set("Two")
        self.assertIsNotNone(window._search_job)
        self.assertEqual(self.children_text_of_games(window), ["One", "Two"])
        window.leave_search()
        self.assertIsNone(window._search_job)
        self.assertEqual(self.children_text_of_games(window), ["Two"])

    def test_search_selects_a_visible_file_so_d_cannot_hit_a_hidden_one(self):
        self.write_two_games()
        window = self.open_window()
        window.tree.selection_set(self.row_of(window, "One (USA).bin"))
        self.search_for(window, "Two")
        window.demote_selected()
        one, two = window.review.results
        self.assertEqual(window.review._moved_count([one]), 0)
        self.assertEqual(window.review._moved_count([two]), 1)

    def test_keys_of_the_window_do_not_reach_the_search_field(self):
        self.write_two_games()
        window = self.open_window()
        self.assertNotIn(str(window.root), window.search_entry.bindtags())

    def test_view_keeps_focus_in_search_field_while_typing(self):
        self.write_two_games()
        window = self.open_window()
        with mock.patch.object(window.root, "focus_get", return_value=window.search_entry), mock.patch.object(
            window.tree, "focus_set"
        ) as focus_set:
            self.search_for(window, "Two")
        focus_set.assert_not_called()

    def test_escape_in_search_field_clears_it(self):
        self.write_two_games()
        window = self.open_window()
        self.search_for(window, "Two")
        window.leave_search(clear=True)
        self.assertEqual(window.search.get(), "")
        self.assertEqual(self.children_text_of_games(window), ["One", "Two"])

    def test_search_stays_active_after_analyzing_again(self):
        self.write_two_games()
        window = self.open_window()
        self.search_for(window, "Two")
        window.analyze_now()
        self.assertEqual(self.children_text_of_games(window), ["Two"])

    def test_delete_message_counts_files_hidden_by_the_search(self):
        self.write_two_games()
        window = self.open_window()
        self.search_for(window, "Two")
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=False) as ask:
            window.confirm_delete()
        message = ask.call_args.args[1]
        self.assertIn("Permanently delete 2 file(s)", message)
        self.assertIn("Not shown: 1 file(s)", message)
        self.assertTrue((self.dir / "One (Japan).bin").exists())

    def test_deleting_confirms_save_files_and_hides_them_for_good(self):
        import rom_cleanup_workbench_window

        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title (Japan).sfc", b"x" * 1000)
        self.write("Title.srm", b"x" * 100)
        self.write("Other (USA).sfc", b"x" * 1000)
        self.write("Other.state", b"x" * 10)
        window = self.open_window(only_problems=True)
        self.delete_confirmed(window)
        self.assertEqual(
            sorted(path.name for path in self.dir.iterdir()),
            ["Other (USA).sfc", "Other.state", "Title (USA).sfc", "Title.srm"],
        )
        self.assert_nothing_to_do(window)
        confirmed = rom_cleanup_workbench_window.load_confirmed_saves(window.settings_path)
        self.assertEqual(
            confirmed, {rf.save_file_key(self.dir / "Title.srm"): 100, rf.save_file_key(self.dir / "Other.state"): 10},
        )
        window.analyze = lambda _directory, _progress=None: rf.Review(self.scan(), self.config)
        window.analyze_now()  # Like F5 or a new start: The confirmation lasts.
        self.assert_nothing_to_do(window)

    def test_ctrl_l_without_marked_files_offers_to_confirm_save_files(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title.srm", b"x" * 100)
        window = self.open_window(only_problems=True)
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=False) as ask:
            window.confirm_delete()
        self.assertIn("Confirm 1 suspected status or save file(s)", ask.call_args.args[1])
        self.assertEqual(window.tree.get_children(), ("g0",))
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=True):
            window.confirm_delete()
        self.assert_nothing_to_do(window)
        self.assertEqual(len(list(self.dir.iterdir())), 2)

    def test_settings_keep_view_and_confirmed_files_side_by_side(self):
        import rom_cleanup_workbench_window

        path = self.settings_file()
        rom_cleanup_workbench_window.add_confirmed_saves(path, {"a": 1})
        rom_cleanup_workbench_window.save_scope(path, "all")
        rom_cleanup_workbench_window.add_confirmed_saves(path, {"b": 2})
        self.assertEqual(rom_cleanup_workbench_window.load_scope(path), "all")
        self.assertEqual(rom_cleanup_workbench_window.load_confirmed_saves(path), {"a": 1, "b": 2})

    def test_broken_confirmed_entries_are_ignored(self):
        import rom_cleanup_workbench_window

        path = self.settings_file()
        for content, expected in (
            ('{"confirmed_save_files": []}', {}),
            ('{"confirmed_save_files": {"a": "1", "b": true, "c": 3}}', {"c": 3}),
            ("[", {}),
        ):
            path.write_text(content, encoding="utf-8")
            self.assertEqual(rom_cleanup_workbench_window.load_confirmed_saves(path), expected, content)

    def test_failed_remembering_is_reported_and_deletes_as_usual(self):
        self.write_save_file_game_for_window()
        window = self.open_window()
        with mock.patch("workbench_state.add_confirmed_saves", side_effect=PermissionError("locked")), mock.patch(
            "rom_cleanup_workbench_window.messagebox.showerror"
        ) as error:
            self.delete_confirmed(window)
        self.assertIn("locked", error.call_args.args[1])
        self.assertFalse((self.dir / "Title (Japan).sfc").exists())

    def write_save_file_game_for_window(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title (Japan).sfc", b"x" * 1000)
        self.write("Title.srm", b"x" * 100)

    def test_window_shows_game_with_only_a_suspected_save_file(self):
        self.write("Title (USA).sfc", b"x" * 1000)
        self.write("Title.srm", b"x" * 100)
        window = self.open_window(only_problems=True)
        self.assertEqual(window.tree.get_children(), ("g0",))
        self.assertEqual(window.nothing_label.place_info(), {})
        self.assertIn("Suspected status or save file", window.tree.set(self.row_of(window, "Title.srm"), "hint"))

    def test_format_kb_rounds_up_like_explorer(self):
        import rom_cleanup_workbench_window

        for size, expected in ((0, "0 KB"), (1, "1 KB"), (1024, "1 KB"), (1025, "2 KB"),
                               (1234 * 1024, "1,234 KB"), (None, "?")):
            self.assertEqual(rom_cleanup_workbench_window.format_kb(size), expected, size)

    def test_kept_and_marked_files_show_their_size(self):
        self.write("Title (USA).bin", b"x" * 3000)
        self.write("Title (Japan).bin", b"x" * 1000)
        window = self.open_window()
        keep = self.row_of(window, "Title (USA).bin")
        marked = self.row_of(window, "Title (Japan).bin")
        self.assertEqual(window.tree.set(keep, "size").strip(), "3 KB")
        self.assertEqual(window.tree.set(marked, "size").strip(), "1 KB")
        self.assertEqual(window.tree.set("g0", "size"), "")
        self.assertEqual(window.tree["displaycolumns"], ("size", "hint"))
        self.assertEqual(window.tree.heading("size", "text").strip(), "Size")

    def test_size_stays_with_the_file_after_moving_it(self):
        self.write("Title (USA).bin", b"x" * 3000)
        self.write("Title (Japan).bin", b"x" * 1000)
        window = self.open_window()
        row = self.row_of(window, "Title (USA).bin")
        window.tree.selection_set(row)
        window.demote_selected()
        self.assertEqual(window.tree.set(row, "size").strip(), "3 KB")
        self.assertIn("By hand: delete", window.tree.set(row, "hint"))

    def test_size_is_read_during_the_scan(self):
        self.write("Title (USA).bin", b"x" * 10)
        [result] = self.scan()
        with mock.patch.object(Path, "stat", side_effect=AssertionError("file read again")):
            self.assertEqual(result.keep[0].size(), 10)

    def test_size_column_grows_with_the_font(self):
        self.write("Title (USA).bin")
        window = self.open_window()
        before = window.tree.column("size", "width")
        window.change_font_size(5)
        self.assertGreater(window.tree.column("size", "width"), before)

    def test_help_line_separates_every_key_evenly(self):
        import re

        for language in translations.LANGUAGES:
            translations.set_language(language)
            text = translations.tr("window.help").replace("\n", "  |  ")
            self.assertEqual(re.findall(r"\S\|| \|\S|\|\s?\S", text.replace("  |  ", "")), [], language)
        translations.set_language("en")
        self.assertIn("Enter: Proceed  |  s: Settings  |  f: Folder", translations.tr("window.help"))

    def test_window_has_the_keys_of_the_terminal_version(self):
        window = self.open_window()
        for key in ("x", "X", "k", "K", "s", "S", "f", "F", "r", "R", "c", "C", "q", "Q", "1", "2", "3"):
            self.assertTrue(window.root.bind(f"<KeyPress-{key}>"), key)
        for sequence in ("<Return>", "<slash>", "<F5>", "<F1>", "<Escape>", "<Tab>", "<Shift-Tab>"):
            self.assertTrue(window.root.bind(sequence), sequence)
        # The old keys are gone, as in the terminal version.
        for sequence in ("<KeyPress-d>", "<KeyPress-D>", "<KeyPress-p>", "<KeyPress-P>", "<Control-l>",
                         "<Control-o>", "<Control-f>"):
            self.assertFalse(window.root.bind(sequence), sequence)

    def test_help_row_of_the_window_names_the_new_keys_in_every_language(self):
        for language in translations.LANGUAGES:
            translations.set_language(language)
            help_text, no_folder = translations.tr("window.help"), translations.tr("window.no_folder")
            for key in ("x", "k", "1-3", "/", "s", "f", "r", "c", "q"):
                self.assertRegex(help_text, rf"(^|  ){re.escape(key)}( ?:| )", (language, key))
            for old in ("Ctrl+L", "Ctrl+O", "Ctrl+E", "Ctrl+F", "Strg+L", "Strg+O", "Demote", "Promote"):
                self.assertNotIn(old, help_text, (language, old))
            self.assertTrue(no_folder.endswith("(f)"), language)
        translations.set_language("en")

    def test_number_keys_choose_the_view(self):
        self.write_two_games()
        window = self.open_window()
        with mock.patch.object(window, "_scope_changed") as changed:
            window._choose_scope(2)
        self.assertEqual(window.scope.get(), "all")
        changed.assert_called_once()
        with mock.patch.object(window, "_list_locked", return_value=True):
            window._choose_scope(0)
        self.assertEqual(window.scope.get(), "all")

    def test_q_does_not_close_while_the_list_is_locked(self):
        window = self.open_window()
        with mock.patch.object(window, "close") as close, mock.patch.object(window, "_list_locked", return_value=True):
            window._quit_key()
        close.assert_not_called()
        with mock.patch.object(window, "close") as close:
            window._quit_key()
        close.assert_called_once()

    def test_f1_shows_the_credits(self):
        window = self.open_window()
        self.assertTrue(window.root.bind("<F1>"))
        self.assertIn("F1: Credits", translations.tr("window.help"))
        with mock.patch("rom_cleanup_workbench_window.messagebox.showinfo") as info:
            window.show_credits()
        title, message = info.call_args.args[:2]
        self.assertEqual(title, "Credits")
        self.assertTrue(message.startswith("Idea: M. Kärcher\nProgramming: Claude Code\n\n"))
        self.assertIn("Copyright (C) 2026 M. Kärcher", message)
        self.assertIn("GNU General Public License, version 3 or later", message)
        self.assertIn("no warranty", message)
        self.assertIn("on a copy of your own ROM collection", message)
        translations.set_language("de")
        self.assertEqual(translations.tr("credits.text"), "Idee: M. Kärcher\nProgrammierung: Claude Code")
        self.assertIn("Kopie der eigenen ROM-Sammlung", translations.tr("credits.license"))

    def test_license_file_and_notices_are_there(self):
        folder = Path(rf.__file__).parent
        license_text = (folder.parent / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("GNU GENERAL PUBLIC LICENSE", license_text)
        self.assertIn("Version 3, 29 June 2007", license_text)
        for path in folder.glob("*.py"):
            head = path.read_text(encoding="utf-8")[:1500]
            self.assertIn("Copyright (C) 2026 M. Kärcher", head, path.name)
            self.assertIn("either version 3 of the", head, path.name)
        self.assertIn("GNU General Public License", " ".join(rf.build_parser().format_help().split()))  # wraps

    def window_with_settings(self, content='{"language": "en", "region_priority": ["USA", "Japan"]}'):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "redundanz_config.json"
        path.write_text(content, encoding="utf-8")
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.config_file = rf.ConfigFile(path)
        return window

    def test_settings_button_is_shown_with_a_configuration_file(self):
        import rom_cleanup_workbench_window

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        window = rom_cleanup_workbench_window.ReviewWindow(
            lambda _directory, _progress=None: rf.Review(self.scan(), self.config), self.dir, "marked",
            self.settings_file(), config_file=rf.ConfigFile(Path(temp.name) / "c.json"),
        )
        self.addCleanup(window.root.destroy)
        window.root.withdraw()
        self.assertIn(window.settings_button, window.bottom_row.pack_slaves())
        plain = self.open_window()
        self.assertNotIn(plain.settings_button, plain.bottom_row.pack_slaves())
        plain.open_settings()  # Without a configuration file nothing opens.
        self.assertIsNone(plain.settings_panel)

    def test_settings_panel_shows_the_current_values(self):
        window = self.window_with_settings()
        window.open_settings()
        dialog = window.settings_panel
        self.assertEqual(dialog.language.get(), "English")
        self.assertEqual(dialog.region_list(), ["USA", "Japan"])
        self.assertEqual(dialog.tag_list(), [])  # the delete keywords; the file has none, nor do the defaults
        window.open_settings()  # Already open: nothing happens.
        self.assertIs(window.settings_panel, dialog)

    def test_settings_panel_moves_adds_and_removes_regions(self):
        window = self.window_with_settings()
        window.open_settings()
        dialog = window.settings_panel
        dialog.regions.selection_set(1)
        dialog.move(-1)
        self.assertEqual(dialog.region_list(), ["Japan", "USA"])
        dialog.move(-1)  # Already at the top: nothing changes.
        self.assertEqual(dialog.region_list(), ["Japan", "USA"])
        dialog.new_region.set(" Germany ")
        dialog.add()
        dialog.new_region.set("usa")
        dialog.add()  # Already there: selected instead of added twice.
        self.assertEqual(dialog.region_list(), ["Japan", "USA", "Germany"])
        self.assertEqual(dialog.regions.curselection(), (1,))
        dialog.remove()
        self.assertEqual(dialog.region_list(), ["Japan", "Germany"])
        self.assertEqual(dialog.new_region.get(), "")

    def test_saving_settings_writes_the_file_and_analyzes_again(self):
        window = self.window_with_settings()
        window.open_settings()
        dialog = window.settings_panel
        dialog.regions.selection_set(1)
        dialog.move(-1)
        dialog.tags.set("Hack, Hacks, Proto")
        with mock.patch.object(window, "start_analysis") as analysis, mock.patch(
            "rom_cleanup_workbench_window.messagebox.showinfo"
        ) as info:
            window.save_settings(dialog)
        analysis.assert_called_once()
        info.assert_not_called()  # The language stayed the same.
        self.assertIsNone(window.settings_panel)
        values = window.config_file.read()
        self.assertEqual(values["region_priority"], ["Japan", "USA"])
        self.assertEqual(values["delete_tags"], ["Hack", "Hacks", "Proto"])

    def test_settings_show_and_change_the_delete_keywords(self):
        window = self.window_with_settings(
            '{"language": "en", "region_priority": ["USA", "Japan", "none", "Beta"], "delete_tags": ["Hack"]}')
        window.open_settings()
        dialog = window.settings_panel
        self.assertEqual(dialog.tag_list(), ["Hack"])
        texts = [widget.cget("text") for widget in self._descendants(dialog.frame)
                 if widget.winfo_class() == "TLabel"]
        self.assertIn("Delete keywords (separated by commas; marked for deletion):", texts)
        self.assertIn("Priority (best first; extra info such as Beta after none):", texts)
        dialog.tags.set("Hack, Hacks")
        with mock.patch.object(window, "start_analysis") as analysis:
            window.save_settings(dialog)
        analysis.assert_called_once()  # a new delete keyword changes the rules: analyze again
        self.assertEqual(rf.Config.load(window.config_file.path).delete_tags, ["Hack", "Hacks"])

    def test_settings_switch_between_plain_file_and_zip_file(self):
        window = self.window_with_settings()
        window.open_settings()
        dialog = window.settings_panel
        self.assertFalse(dialog.prefers_zip())
        texts = [widget.cget("text") for widget in self._descendants(dialog.frame)
                 if widget.winfo_class() in ("TLabel", "TRadiobutton")]
        for text in ("Same game as a plain file and as a ZIP file:", "Keep the plain file", "Keep the ZIP file"):
            self.assertIn(text, texts)
        dialog.prefer_buttons[1].invoke()
        self.assertTrue(dialog.prefers_zip())
        with mock.patch.object(window, "start_analysis") as analysis:
            window.save_settings(dialog)
        analysis.assert_called_once()  # the switch changes the rules: analyze again
        self.assertTrue(rf.Config.load(window.config_file.path).prefer_zip)
        window.open_settings()
        self.assertTrue(window.settings_panel.prefers_zip())

    def test_label_of_the_priority_list_wraps_instead_of_being_cut(self):
        window = self.window_with_settings()
        window.open_settings()
        label = window.settings_panel.regions_label
        window.root.update()
        self.assertEqual(label.grid_info()["sticky"], "ew")
        self.assertGreater(int(str(label.cget("wraplength"))), 1)  # follows the width of its column
        self.assertLessEqual(label.winfo_reqwidth(), label.master.winfo_width())

    def test_settings_of_an_old_file_show_its_low_priority_tags_as_keywords(self):
        window = self.window_with_settings(
            '{"language": "en", "region_priority": ["USA", "none", "Japan"], "low_priority_tags": ["Beta"]}')
        window.open_settings()
        dialog = window.settings_panel
        self.assertEqual(dialog.region_list(), ["USA", "none", "Japan", "Beta"])
        self.assertEqual(dialog.tag_list(), [])  # the file has none: the defaults, which are empty

    def test_new_language_is_announced_for_the_next_start(self):
        window = self.window_with_settings()
        window.open_settings()
        dialog = window.settings_panel
        dialog.language.set("Italiano")
        with mock.patch.object(window, "start_analysis") as analysis, mock.patch(
            "rom_cleanup_workbench_window.messagebox.showinfo"
        ) as info:
            window.save_settings(dialog)
        self.assertEqual(window.config_file.read()["language"], "it")
        self.assertIn("next start", info.call_args.args[1])
        analysis.assert_not_called()  # Priority and tags are unchanged: nothing to analyze again.
        self.assertEqual(translations.current_language(), "en")  # The open window keeps its language.

    def test_saving_settings_asks_before_dropping_changes_by_hand(self):
        window = self.window_with_settings()
        window.tree.selection_set(self.row_of(window, "Title (USA).bin"))
        window.demote_selected()
        original = window.config_file.path.read_text(encoding="utf-8")
        window.open_settings()
        dialog = window.settings_panel
        dialog.regions.selection_set(1)
        dialog.move(-1)
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=False) as ask:
            window.save_settings(dialog)
        ask.assert_called_once()
        self.assertEqual(window.config_file.path.read_text(encoding="utf-8"), original)
        self.assertIs(window.settings_panel, dialog)
        self.assertEqual(window.review.moved_count(), 1)

    def test_wrong_settings_are_reported_and_the_dialog_stays_open(self):
        window = self.window_with_settings()
        window.open_settings()
        dialog = window.settings_panel
        dialog.regions.delete(0, "end")
        with mock.patch("rom_cleanup_workbench_window.messagebox.showerror") as error:
            window.save_settings(dialog)
        self.assertIn("at least one region", error.call_args.args[1])
        self.assertIs(window.settings_panel, dialog)

    def test_broken_configuration_is_not_opened_for_editing(self):
        window = self.window_with_settings("{not json")
        with mock.patch("rom_cleanup_workbench_window.messagebox.showerror") as error:
            window.open_settings()
        error.assert_called_once()
        self.assertIsNone(window.settings_panel)
        self.assertEqual(window.config_file.path.read_text(encoding="utf-8"), "{not json")
        self.assertTrue(window.list_frame.winfo_manager())  # The list stays in place.

    def no_system_popups(self):
        """Fails the test if a Windows popup would open instead of a question in the window."""
        import rom_cleanup_workbench_window as window_module

        stack = contextlib.ExitStack()
        for name in ("askyesno", "showinfo", "showwarning", "showerror"):
            stack.enter_context(mock.patch.object(
                window_module._system_messagebox, name, side_effect=AssertionError("Windows popup opened"),
            ))
        self.addCleanup(stack.close)

    def answer_soon(self, window, button, seen=None):
        """Presses a button of the question that is about to open, like a person would."""
        def press():
            frame = window._questions[-1][0] if window._questions else None
            # A question already answered is still listed until its wait ends: wait for the next one.
            if frame is None or getattr(frame, "answered_by_test", False):
                window.root.after(20, press)
                return
            frame.answered_by_test = True
            buttons = [w for w in self._descendants(frame) if w.winfo_class() == "TButton"]
            if seen is not None:
                seen.append({
                    "buttons": [b.cget("text") for b in buttons],
                    "texts": [w.cget("text") for w in self._descendants(frame) if w.winfo_class() == "TLabel"],
                    "locked": [w.instate(["disabled"]) for w in window._list_controls],
                    "placed": frame.winfo_manager() == "place" and frame.master is window.middle,
                })
            buttons[button].invoke()
        window.root.after(20, press)

    def test_question_appears_in_the_window_with_buttons_in_its_language(self):
        self.no_system_popups()
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        seen = []
        self.answer_soon(window, 1, seen)
        import rom_cleanup_workbench_window as window_module

        self.assertFalse(window_module.messagebox.askyesno("Title?", "Really?", parent=window.root))
        self.assertEqual(seen[0]["buttons"], ["Yes", "No"])
        self.assertIn("Really?", seen[0]["texts"])
        self.assertTrue(seen[0]["placed"])
        self.assertTrue(all(seen[0]["locked"]))
        self.assertFalse(window._questions)
        self.assertFalse(any(widget.instate(["disabled"]) for widget in window._list_controls))
        self.answer_soon(window, 0)
        self.assertTrue(window_module.messagebox.askyesno("Title?", "Really?", parent=window.root))

    def test_question_buttons_follow_the_language(self):
        self.no_system_popups()
        import rom_cleanup_workbench_window as window_module

        for language, expected in (("de", ["Ja", "Nein"]), ("it", ["Sì", "No"]), ("ja", ["はい", "いいえ"])):
            translations.set_language(language)
            window = self.open_window()
            seen = []
            self.answer_soon(window, 1, seen)
            window_module.messagebox.askyesno("?", "?", parent=window.root)
            self.assertEqual(seen[0]["buttons"], expected, language)
            window.root.destroy()

    def test_escape_and_the_window_close_answer_no(self):
        self.no_system_popups()
        window = self.open_window()
        import rom_cleanup_workbench_window as window_module

        window.root.after(50, window._on_escape)
        self.assertFalse(window_module.messagebox.askyesno("?", "?", parent=window.root, default="yes"))
        window.root.after(50, window.close)
        self.assertFalse(window_module.messagebox.askyesno("?", "?", parent=window.root, default="yes"))
        self.assertTrue(window.root.winfo_exists())

    def test_keys_of_the_list_do_nothing_while_a_question_is_open(self):
        self.no_system_popups()
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.tree.selection_set(self.row_of(window, "Title (USA).bin"))
        import rom_cleanup_workbench_window as window_module

        def try_keys():
            window.demote_selected()
            window.confirm_delete()  # Must not open a second question.
            self.keys_tried = len(window._questions)
            window._answer(0)
        window.root.after(50, try_keys)
        window_module.messagebox.showinfo("Info", "Hello", parent=window.root)
        self.assertEqual(self.keys_tried, 1)
        self.assertEqual(window.review.moved_count(), 0)

    def test_deleting_asks_in_the_window(self):
        self.no_system_popups()
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.analyze = mock.Mock(side_effect=AssertionError("analyzed again"))
        seen = []
        self.answer_soon(window, 0, seen)  # Yes, delete.
        self.answer_soon(window, 0)  # OK to the result; scheduled now, it waits for the second question.
        window.confirm_delete()
        self.assertIn("Permanently delete 1 file(s)", " ".join(seen[0]["texts"]))
        self.assertEqual([path.name for path in self.dir.iterdir()], ["Title (USA).bin"])
        self.assertFalse(window._questions)

    def test_settings_take_the_place_of_the_list_in_the_main_window(self):
        window = self.window_with_settings()
        window.toggle_settings()
        panel = window.settings_panel
        self.assertIs(panel.frame.master, window.middle)
        self.assertEqual(panel.frame.winfo_manager(), "pack")
        self.assertEqual(window.list_frame.winfo_manager(), "")
        self.assertFalse([child for child in window.root.winfo_children() if child.winfo_class() == "Toplevel"])
        window.toggle_settings()  # Settings... or Ctrl+E a second time: back to the list.
        self.assertIsNone(window.settings_panel)
        self.assertEqual(window.list_frame.winfo_manager(), "pack")
        self.assertEqual(window.tree.item("g0", "text"), "Title")

    def test_list_is_locked_while_the_settings_are_open(self):
        window = self.window_with_settings()
        window.tree.selection_set(self.row_of(window, "Title (USA).bin"))
        window.open_settings()
        self.assertTrue(all(widget.instate(["disabled"]) for widget in window._list_controls))
        self.assertFalse(window.settings_button.instate(["disabled"]))
        window.demote_selected()
        window.promote_selected()
        self.assertEqual(window.review.moved_count(), 0)
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno") as ask, mock.patch.object(
            window, "start_analysis"
        ) as analysis:
            window.confirm_delete()
            window.reanalyze()
            window.choose_directory()
        ask.assert_not_called()
        analysis.assert_not_called()
        self.assertIsNone(window.folder_panel)
        self.assertIsNone(window._move_game(1))  # Tab moves between the fields instead.
        self.assertEqual(len(list(self.dir.iterdir())), 2)
        window.close_settings()
        self.assertFalse(any(widget.instate(["disabled"]) for widget in window._list_controls))

    def test_typing_in_the_settings_never_reaches_the_list(self):
        window = self.window_with_settings()
        window.open_settings()
        panel = window.settings_panel
        for widget in (panel.regions, *[w for w in self._descendants(panel.frame) if w.winfo_class() == "TEntry"]):
            self.assertNotIn(str(window.root), widget.bindtags())

    @staticmethod
    def _descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from ReviewWindowTests._descendants(child)

    def test_settings_make_a_low_window_tall_enough_and_closing_restores_the_minimum(self):
        window = self.window_with_settings()
        before = window.root.minsize()
        window.open_settings()
        window.root.update_idletasks()
        self.assertGreaterEqual(window.root.minsize()[1], min(window.root.winfo_reqheight(), window.root.winfo_screenheight()))
        window.close_settings()
        self.assertEqual(window.root.minsize(), before)

    def test_escape_closes_only_the_settings(self):
        window = self.window_with_settings()
        window.open_settings()
        with mock.patch.object(window, "close") as close:
            window.settings_panel.close()
        close.assert_not_called()
        self.assertIsNone(window.settings_panel)
        self.assertTrue(window.root.winfo_exists())

    def test_window_speaks_the_chosen_language(self):
        translations.set_language("de")
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        texts = [widget.cget("text") for widget in window.bottom_row.pack_slaves()]
        self.assertIn("Ausführen...", texts)
        self.assertIn("Dateinamen filtern:", texts)
        self.assertEqual(window.tree.heading("hint", "text"), "Hinweis")
        self.assertIn("Zum Löschen: 1 Datei(en)", window.status.get())
        self.assertTrue(window.folder.get().startswith("Ordner: "))

    def test_window_opens_in_every_language(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        for language in translations.LANGUAGES:
            with self.subTest(language):
                translations.set_language(language)
                window = self.open_window()
                self.assertEqual(window.tree.heading("#0", "text"), translations.tr("window.column.file"))
                self.assertEqual(window.tree.item("g0", "text"), "Title")
                window.root.destroy()

    def test_delete_button_is_called_proceed(self):
        window = self.open_window()
        texts = [widget.cget("text") for widget in window.bottom_row.pack_slaves() if widget.winfo_class() == "TButton"]
        self.assertIn("Proceed...", texts)
        self.assertNotIn("Delete...", texts)

    def test_chosen_view_shows_a_red_dot_in_a_visible_ring(self):
        window = self.open_window()
        from tkinter import ttk

        style = ttk.Style(window.root)
        self.assertEqual(style.lookup("TRadiobutton", "indicatorforeground"), "#e5383b")
        self.assertEqual(style.lookup("TRadiobutton", "indicatorbackground"), "#222222")
        self.assertEqual(style.lookup("TRadiobutton", "upperbordercolor"), "#888888")
        # The selected state must not paint over the dot with another background.
        self.assertEqual(style.lookup("TRadiobutton", "indicatorbackground", ("selected",)), "#222222")

    def test_radio_indicator_grows_with_the_font(self):
        window = self.open_window()
        from tkinter import ttk

        style = ttk.Style(window.root)
        before = int(style.lookup("TRadiobutton", "indicatorsize"))
        window.change_font_size(10)
        self.assertGreater(int(style.lookup("TRadiobutton", "indicatorsize")), before)

    def test_dark_mode_uses_black_background_and_white_text(self):
        self.write("Title (USA).bin")
        window = self.open_window()
        from tkinter import ttk

        style = ttk.Style(window.root)
        self.assertEqual(style.lookup("Treeview", "background"), "#000000")
        self.assertEqual(style.lookup("Treeview", "foreground"), "#ffffff")
        self.assertEqual(str(window.root.cget("background")), "#000000")

    def test_font_is_lucida_sans_typewriter_11(self):
        self.write("Title (USA).bin")
        window = self.open_window()
        from tkinter import font

        default = font.nametofont("TkDefaultFont", root=window.root)
        # The requested font instead of the actual one: It is not installed on every computer.
        self.assertEqual(default.cget("family"), "Lucida Sans Typewriter")
        self.assertEqual(default.cget("size"), 11)

    def test_font_size_changes_text_bold_rows_and_stays_in_limits(self):
        self.write("Title (USA).bin")
        window = self.open_window()
        from tkinter import font, ttk

        default = font.nametofont("TkDefaultFont", root=window.root)
        height = ttk.Style(window.root).lookup("Treeview", "rowheight")
        window.change_font_size(3)
        self.assertEqual(default.cget("size"), 14)
        self.assertEqual(window.bold_font.cget("size"), 14)
        self.assertGreater(int(ttk.Style(window.root).lookup("Treeview", "rowheight")), int(height))
        window.change_font_size(100)
        self.assertEqual(default.cget("size"), 32)
        window.change_font_size(-100)
        self.assertEqual(default.cget("size"), 8)

    def test_mouse_wheel_direction_changes_size_and_stops_scrolling(self):
        self.write("Title (USA).bin")
        window = self.open_window()
        up, down = mock.Mock(delta=120), mock.Mock(delta=-120)
        self.assertEqual(window._on_zoom(up), "break")
        self.assertEqual(window.font_size, 12)
        window._on_zoom(down)
        window._on_zoom(down)
        self.assertEqual(window.font_size, 10)

    def test_demote_and_promote_move_the_rows(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        keep_row = self.row_of(window, "Title (USA).bin")
        mark_row = self.row_of(window, "Title (Japan).bin")

        window.tree.selection_set(keep_row)
        window.demote_selected()
        self.assertEqual(window.tree.parent(keep_row), "g0h")
        self.assertEqual(window.tree.selection(), (keep_row,))
        self.assertIn("By hand: delete", window.tree.item(keep_row, "values")[0])

        window.tree.selection_set(mark_row)
        window.promote_selected()
        self.assertEqual(window.tree.parent(mark_row), "g0k")
        self.assertEqual(self.children_text(window, "g0k")[0], "+ Title (Japan).bin")

    def test_kept_files_stand_under_their_own_heading(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        self.assertEqual(self.children_text(window, "g0"), ["Keep:", "Marked for deletion"])
        self.assertEqual(self.children_text(window, "g0k"), ["+ Title (USA).bin"])

    def test_heading_disappears_when_nothing_is_kept(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        self.assertEqual(self.children_text(window, "g0"), ["Keep:", "Marked for deletion"])
        window.tree.selection_set(self.row_of(window, "Title (USA).bin"))
        window.demote_selected()
        self.assertEqual(self.children_text(window, "g0"), ["Marked for deletion"])

    def test_several_rows_move_together(self):
        self.write("Title (USA) (Disc 1).bin")
        self.write("Title (USA) (Disc 2).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.tree.selection_set(
            self.row_of(window, "Title (USA) (Disc 1).bin"), self.row_of(window, "Title (USA) (Disc 2).bin")
        )
        window.demote_selected()
        self.assertEqual(len(window.tree.get_children("g0h")), 3)

    def test_keys_on_game_rows_do_nothing(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.tree.selection_set("g0")
        window.demote_selected()
        self.assertEqual(window.review.moved_count(), 0)

    def test_games_without_marked_file_are_not_listed(self):
        self.write("Other (USA).bin")
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        self.assertEqual(window.tree.get_children(), ("g1",))
        self.assertEqual(self.children_text(window, "g1k"), ["+ Title (USA).bin"])
        self.assertIn("Showing: 1 of 2 games", window.status.get())

    def test_show_all_is_off_by_default_and_shows_other_games(self):
        self.write("Other (USA).bin")
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        self.assertEqual(window.tree.get_children(), ("g1",))
        window.scope.set("all")
        window._show_all_groups()
        self.assertEqual(window.tree.get_children(), ("g0", "g1s", "g1"))
        self.assertIn("Showing: 2 of 2", window.status.get())
        self.assertFalse(window.settings_path.exists())

    def test_show_all_replaces_nothing_to_do(self):
        self.write("Other (USA).bin")
        window = self.open_window()
        self.assert_nothing_to_do(window)
        window.scope.set("all")
        window._show_all_groups()
        self.assertEqual(window.tree.get_children(), ("g0",))
        self.assertEqual(window.nothing_label.place_info(), {})
        self.assertIsNone(window._blink_job)
        window.scope.set("marked")
        window._show_all_groups()
        self.assert_nothing_to_do(window)

    def test_show_all_allows_demoting_and_keeps_the_game_visible(self):
        self.write("Other (USA).bin")
        window = self.open_window()
        window.scope.set("all")
        window._show_all_groups()
        row = self.row_of(window, "Other (USA).bin")
        window.tree.selection_set(row)
        window.demote_selected()
        self.assertEqual(window.tree.parent(row), "g0h")
        window.scope.set("marked")
        window._show_all_groups()
        self.assertEqual(window.tree.get_children(), ("g0",))

    def test_all_files_scope_shows_problems_without_marks(self):
        self.write("Other (USA).bin")
        self.write_zip("Zip (USA).zip", {"a.bin": b"one"})
        self.write_zip("Zip [USA].zip", {"a.bin": b"two"})
        window = self.open_window()
        window.scope.set("all")
        window._show_all_groups()
        self.assertEqual(window.tree.get_children(), ("g0", "g1s", "g1"))
        self.assertIn("Problematic: 1", window.status.get())

    def test_scope_is_offered_as_three_radio_buttons(self):
        window = self.open_window()
        radios = []

        def collect(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TRadiobutton":
                    radios.append(child)
                collect(child)

        collect(window.root)
        self.assertEqual(
            [radio.cget("text") for radio in radios],
            ["Problematic deletion marks", "All deletion marks", "All ROM files"],
        )
        self.assertEqual(window.scope.get(), "marked")
        radios[2].invoke()
        self.assertEqual(window.scope.get(), "all")
        radios[0].invoke()
        self.assertEqual(window.scope.get(), "problems")

    def test_each_scope_shows_its_games(self):
        self.write("Other (USA).bin")
        self.write("Clear (USA).bin")
        self.write("Clear (Japan).bin")
        self.write("Zelda (USA).nes")
        self.write("Zelda (Japan).sfc")
        window = self.open_window()
        titles = lambda: [window.tree.item(row, "text") for row in window.tree.get_children() if not row.endswith("s")]
        self.assertEqual(titles(), ["Clear", "Zelda"])
        window.scope.set("problems")
        window._show_all_groups()
        self.assertEqual(titles(), ["Zelda"])
        window.scope.set("all")
        window._show_all_groups()
        self.assertEqual(titles(), ["Clear", "Other", "Zelda"])

    def test_first_start_shows_problematic_marks(self):
        self.write("Clear (USA).bin")
        self.write("Clear (Japan).bin")
        self.write("Zelda (USA).nes")
        self.write("Zelda (Japan).sfc")
        window = self.open_window(scope=None)
        self.assertEqual(window.scope.get(), "problems")
        self.assertEqual(window.tree.get_children(), ("g1",))

    def test_marks_without_problems_show_an_empty_list_not_nothing_to_do(self):
        self.write("Clear (USA).bin")
        self.write("Clear (Japan).bin")
        window = self.open_window(scope=None)
        self.assertEqual(window.tree.get_children(), ())
        self.assertEqual(window.nothing_label.place_info(), {})
        self.assertIn("To delete: 1", window.status.get())

    def invoke_radio(self, window, label):
        def find(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TRadiobutton" and child.cget("text") == label:
                    return child
                found = find(child)
                if found:
                    return found
            return None

        find(window.root).invoke()

    def test_chosen_scope_is_saved_and_used_by_the_next_window(self):
        self.write("Other (USA).bin")
        path = self.settings_file()
        window = self.open_window(settings_path=path, scope=None)
        self.invoke_radio(window, "All ROM files")
        self.assertEqual(window.tree.get_children(), ("g0",))
        window.root.destroy()

        second = self.open_window(settings_path=path, scope=None)
        self.assertEqual(second.scope.get(), "all")
        self.assertEqual(second.tree.get_children(), ("g0",))
        self.invoke_radio(second, "All deletion marks")
        second.root.destroy()

        third = self.open_window(settings_path=path, scope=None)
        self.assertEqual(third.scope.get(), "marked")

    def test_scope_from_command_line_is_not_saved_and_wins(self):
        path = self.settings_file()
        path.write_text('{"scope": "all"}', encoding="utf-8")
        window = self.open_window(only_problems=True, settings_path=path)
        self.assertEqual(window.scope.get(), "problems")
        self.assertEqual(path.read_text(encoding="utf-8"), '{"scope": "all"}')

    def test_failed_save_keeps_the_choice_and_reports(self):
        self.write("Other (USA).bin")
        window = self.open_window()
        with mock.patch("rom_cleanup_workbench_window.save_scope", side_effect=PermissionError("locked")), mock.patch(
            "rom_cleanup_workbench_window.messagebox.showerror"
        ) as error:
            self.invoke_radio(window, "All ROM files")
        self.assertIn("locked", error.call_args.args[1])
        self.assertEqual(window.scope.get(), "all")
        self.assertEqual(window.tree.get_children(), ("g0",))

    def test_faulty_or_old_settings_file_means_default(self):
        import rom_cleanup_workbench_window

        path = self.settings_file()
        for content in ("{not json", "[true]", '{"scope": "nonsense"}', '{"scope": 1}', '{"old_key": true}'):
            path.write_text(content, encoding="utf-8")
            self.assertEqual(rom_cleanup_workbench_window.load_scope(path), "problems", content)
        self.assertEqual(rom_cleanup_workbench_window.load_scope(path.with_name("missing.json")), "problems")

    def test_confirm_message_does_not_count_shown_files_as_hidden(self):
        self.write("Clear (USA).bin")
        self.write("Clear (Japan).bin")
        self.write("Problem (USA) (Hack).bin")
        review = rf.Review(self.scan(), self.config)
        self.assertIn("Not shown", review.confirm_message(True, False))
        self.assertIn("Not shown", review.confirm_message(True, True))
        self.assertNotIn("Not shown", review.confirm_message(False, True))

    def test_filter_hides_clear_games(self):
        self.write("Clear (USA).bin")
        self.write("Clear (Japan).bin")
        self.write("Problem (USA) (Hack).bin")
        window = self.open_window(only_problems=True)
        self.assertEqual(window.tree.get_children(), ("g1",))
        window.scope.set("marked")
        window._show_all_groups()
        self.assertEqual(window.tree.get_children(), ("g0", "g1s", "g1"))

    def write_three_games(self):
        for game in ("Alpha", "Beta", "Gamma"):
            self.write(f"{game} (USA).bin")
            self.write(f"{game} (Japan).bin")

    def test_title_has_no_constant_text(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        self.assertEqual(window.tree.item("g0", "text"), "Title")

    def test_kept_files_are_bold_and_marked_files_normal(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        self.assertEqual(str(window.tree.tag_configure("keep", "font")), str(window.bold_font))
        self.assertIn("keep", window.tree.item(self.row_of(window, "Title (USA).bin"), "tags"))
        marked = window.tree.item(self.row_of(window, "Title (Japan).bin"), "tags")
        self.assertIn("marked", marked)
        self.assertEqual(window.tree.tag_configure("marked", "font"), "")

    def test_games_are_separated_and_every_second_is_striped(self):
        self.write_three_games()
        window = self.open_window()
        self.assertEqual(window.tree.get_children(), ("g0", "g1s", "g1", "g2s", "g2"))
        self.assertIn("separator", window.tree.item("g1s", "tags"))
        self.assertNotIn("striped", window.tree.item("g0", "tags"))
        self.assertIn("striped", window.tree.item("g1", "tags"))
        self.assertNotIn("striped", window.tree.item("g2", "tags"))
        self.assertIn("striped", window.tree.item(self.row_of(window, "Beta (Japan).bin"), "tags"))
        self.assertIn("striped", window.tree.item("g1h", "tags"))

    def test_stripes_follow_the_visible_games(self):
        self.write("Clear (USA).bin")
        self.write("Problem A (USA) (Hack).bin")
        self.write("Problem B (USA) (Hack).bin")
        window = self.open_window(only_problems=True)
        self.assertEqual(window.tree.get_children(), ("g1", "g2s", "g2"))
        self.assertIn("striped", window.tree.item("g2", "tags"))

    def test_stripe_survives_moving_a_file(self):
        self.write_three_games()
        window = self.open_window()
        row = self.row_of(window, "Beta (USA).bin")
        window.tree.selection_set(row)
        window.demote_selected()
        self.assertEqual(set(window.tree.item(row, "tags")), {"marked", "moved", "striped"})

    def test_arrow_keys_skip_separators(self):
        self.write_three_games()
        window = self.open_window()
        last_of_first_game = self.row_of(window, "Alpha (Japan).bin")
        window.tree.focus(last_of_first_game)
        window.tree.selection_set(last_of_first_game)
        window._move_cursor(1, False)
        self.assertEqual(window.tree.selection(), ("g1",))
        window._move_cursor(-1, False)
        self.assertEqual(window.tree.selection(), (last_of_first_game,))

    def test_arrow_keys_stop_at_both_ends(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.tree.focus("g0")
        window.tree.selection_set("g0")
        window._move_cursor(-1, False)
        self.assertEqual(window.tree.selection(), ("g0",))
        row = self.row_of(window, "Title (Japan).bin")
        window.tree.focus(row)
        window.tree.selection_set(row)
        window._move_cursor(1, False)
        self.assertEqual(window.tree.selection(), (row,))

    def test_tab_moves_between_games(self):
        self.write_three_games()
        window = self.open_window()
        alpha = self.row_of(window, "Alpha (USA).bin")
        beta = self.row_of(window, "Beta (USA).bin")
        gamma = self.row_of(window, "Gamma (USA).bin")
        self.assertEqual(window.tree.selection(), (alpha,))
        window._move_game(1)
        self.assertEqual(window.tree.selection(), (beta,))
        self.assertEqual(window.tree.focus(), beta)
        window._move_game(1)
        self.assertEqual(window.tree.selection(), (gamma,))
        window._move_game(-1)
        self.assertEqual(window.tree.selection(), (beta,))

    def test_tab_stops_at_both_ends(self):
        self.write_three_games()
        window = self.open_window()
        alpha = self.row_of(window, "Alpha (USA).bin")
        window._move_game(-1)
        self.assertEqual(window.tree.selection(), (alpha,))
        window._move_game(1)
        window._move_game(1)
        gamma = self.row_of(window, "Gamma (USA).bin")
        window._move_game(1)
        self.assertEqual(window.tree.selection(), (gamma,))

    def test_tab_works_from_any_row_of_a_game(self):
        self.write_three_games()
        window = self.open_window()
        for row in ("g0", "g0k", "g0h", self.row_of(window, "Alpha (Japan).bin")):
            window.tree.focus(row)
            window.tree.selection_set(row)
            window._move_game(1)
            self.assertEqual(window.tree.selection(), (self.row_of(window, "Beta (USA).bin"),), row)

    def test_tab_collapses_multiple_selection(self):
        self.write_three_games()
        window = self.open_window()
        window._move_cursor(1, True)
        window._move_game(1)
        self.assertEqual(window.tree.selection(), (self.row_of(window, "Beta (USA).bin"),))

    def test_tab_with_nothing_to_do_changes_nothing(self):
        window = self.open_window()
        self.assertEqual(window._move_game(1), "break")
        self.assertEqual(window.tree.selection(), ())

    def test_shift_arrow_extends_and_shrinks_selection(self):
        self.write("Title (USA) (Disc 1).bin")
        self.write("Title (USA) (Disc 2).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        first = self.row_of(window, "Title (USA) (Disc 1).bin")
        second = self.row_of(window, "Title (USA) (Disc 2).bin")
        window.tree.focus(first)
        window.tree.selection_set(first)
        window._move_cursor(1, True)
        self.assertEqual(set(window.tree.selection()), {first, second})
        window._move_cursor(-1, True)
        self.assertEqual(window.tree.selection(), (first,))

    def test_separator_cannot_stay_selected(self):
        self.write_three_games()
        window = self.open_window()
        window.tree.selection_set("g1s")
        window._drop_separators_from_selection()
        self.assertEqual(window.tree.selection(), ())

    def test_declined_confirmation_keeps_window_open(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=False):
            window.confirm_delete()
        self.assertEqual(len(list(self.dir.iterdir())), 2)
        self.assertTrue(window.root.winfo_exists())

    def delete_confirmed(self, window):
        """Deletes as after a yes; fails if the folder is analyzed again."""
        window.analyze = mock.Mock(side_effect=AssertionError("analyzed again"))
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=True), mock.patch(
            "rom_cleanup_workbench_window.messagebox.showinfo"
        ) as info, mock.patch.object(window, "start_analysis") as start:
            window.confirm_delete()
        start.assert_not_called()
        return info

    def test_delete_files_reports_progress_also_for_failures(self):
        self.write("a.bin")
        reports = []
        deleted, errors = rf.delete_files(
            [self.dir / "a.bin", self.dir / "missing.bin"], lambda done, total: reports.append((done, total)),
        )
        self.assertEqual((deleted, len(errors)), (1, 1))
        self.assertEqual(reports, [(0, 2), (1, 2), (2, 2)])

    def test_progress_bar_is_shown_while_deleting_and_hidden_afterwards(self):
        for game in ("Alpha", "Beta", "Gamma"):
            self.write(f"{game} (USA).bin")
            self.write(f"{game} (Japan).bin")
        window = self.open_window()
        seen = []
        real_unlink = Path.unlink

        def unlink(path, *args, **kwargs):
            window.root.update_idletasks()
            seen.append((bool(window.progress_bar.place_info()), window.status.get()))  # The test window is hidden.
            real_unlink(path, *args, **kwargs)

        with mock.patch("pathlib.Path.unlink", unlink), mock.patch(
            "rom_cleanup_workbench_window.time.monotonic", side_effect=range(0, 1000)
        ):
            self.delete_confirmed(window)
        self.assertEqual(len(seen), 3)
        self.assertTrue(all(mapped for mapped, _status in seen))
        self.assertEqual([status for _mapped, status in seen][1:], ["Deleting: 1 of 3 files", "Deleting: 2 of 3 files"])
        self.assertEqual(float(window.progress_bar.cget("maximum")), 3)
        self.assertEqual(window.progress_bar.place_info(), {})
        self.assertEqual(len(list(self.dir.iterdir())), 3)

    def test_progress_bar_is_hidden_even_if_deleting_fails_unexpectedly(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=True), mock.patch.object(
            window.review, "delete", side_effect=RuntimeError("boom")
        ), self.assertRaises(RuntimeError):
            window.confirm_delete()
        self.assertEqual(window.progress_bar.place_info(), {})

    def test_confirmation_deletes_and_reports_without_analyzing_again(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        info = self.delete_confirmed(window)
        self.assertEqual(info.call_args.args[1], "1 file(s) deleted.")
        self.assertEqual([path.name for path in self.dir.iterdir()], ["Title (USA).bin"])
        self.assertIsNone(window._analysis)
        self.assert_nothing_to_do(window)

    def test_deleted_files_leave_the_list_and_kept_ones_stay_in_all_files_view(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window(scope="all")
        self.delete_confirmed(window)
        names = [entry.path.name for _, entry in window._files.values()]
        self.assertEqual(names, ["Title (USA).bin"])
        self.assertEqual(window.tree.get_children(), ("g0",))
        self.assertIn("To delete: 0 file(s)", window.status.get())

    def test_game_without_remaining_file_disappears_after_deleting(self):
        self.write("Gone (USA) (Hack).bin")
        self.write("Stays (USA).bin")
        self.write("Stays (Japan).bin")
        window = self.open_window(scope="all")
        self.delete_confirmed(window)
        self.assertEqual([result.title for result in window.review.results], ["Stays"])
        self.assertIn("Showing: 1 of 1 games", window.status.get())

    def test_problems_are_updated_after_deleting(self):
        self.write("Title (USA).nes")
        self.write("Title (Japan).sfc")
        window = self.open_window(scope="all")
        [result] = window.review.results
        self.assertIn("Different file type than the kept file", result.problems)
        self.delete_confirmed(window)
        self.assertEqual(result.problems, [])

    def test_changes_by_hand_are_done_after_deleting(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.tree.selection_set(self.row_of(window, "Title (Japan).bin"))
        window.promote_selected()
        window.tree.selection_set(self.row_of(window, "Title (USA).bin"))
        window.demote_selected()
        self.delete_confirmed(window)
        self.assertEqual([path.name for path in self.dir.iterdir()], ["Title (Japan).bin"])
        self.assertEqual(window.review.moved_count(), 0)
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno") as ask:
            window.close()
        ask.assert_not_called()

    def test_search_stays_active_after_deleting(self):
        self.write_two_games()
        window = self.open_window(scope="all")
        self.search_for(window, "Two")
        self.delete_confirmed(window)
        self.assertEqual(window.search.get(), "Two")
        self.assertEqual(self.children_text_of_games(window), ["Two"])

    def assert_nothing_to_do(self, window):
        self.assertEqual(window.tree.get_children(), ())
        self.assertEqual(window.status.get(), "Analysis finished: Nothing to do")
        self.assertEqual(window.nothing_label.cget("text"), "Nothing to do.")
        self.assertEqual(window.nothing_label.place_info()["relx"], "0.5")
        self.assertEqual(window.nothing_label.place_info()["rely"], "0.5")
        self.assertIsNotNone(window._blink_job)

    def test_folder_without_marked_files_shows_only_nothing_to_do(self):
        self.write("Alpha (USA).bin")
        self.write("Beta (USA).bin")
        window = self.open_window()
        self.assert_nothing_to_do(window)
        window.scope.set("problems")
        window._show_all_groups()
        self.assert_nothing_to_do(window)

    def test_empty_folder_shows_nothing_to_do(self):
        self.assert_nothing_to_do(self.open_window())

    def test_nothing_to_do_blinks(self):
        window = self.open_window()
        self.assertEqual(str(window.nothing_label.cget("foreground")), "#ffffff")
        window._blink(visible=False)
        self.assertEqual(str(window.nothing_label.cget("foreground")), "#000000")
        window._blink(visible=True)
        self.assertEqual(str(window.nothing_label.cget("foreground")), "#ffffff")

    def test_nothing_to_do_disappears_with_new_results(self):
        window = self.open_window()
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window.analyze_now()
        self.assertEqual(window.nothing_label.place_info(), {})
        self.assertIsNone(window._blink_job)
        self.assertEqual(window.tree.get_children(), ("g0",))

    def test_nothing_to_do_grows_with_the_font(self):
        window = self.open_window()
        window.change_font_size(1)
        self.assertEqual(window.nothing_font.cget("size"), 36)

    def test_nothing_to_do_ignores_keys_and_deletes_nothing(self):
        self.write("Alpha (USA).bin")
        window = self.open_window()
        window.demote_selected()
        window.promote_selected()
        with mock.patch("rom_cleanup_workbench_window.messagebox.showinfo") as info:
            window.confirm_delete()
        info.assert_called_once()
        self.assertEqual(window.review.moved_count(), 0)
        self.assertEqual(len(list(self.dir.iterdir())), 1)

    def test_promoting_last_marked_file_keeps_the_list(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.tree.selection_set(self.row_of(window, "Title (Japan).bin"))
        window.promote_selected()
        self.assertEqual(window.tree.get_children(), ("g0",))
        self.assertIn("To delete: 0", window.status.get())

    def test_failed_delete_is_reported_and_sets_exit_code(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=True), mock.patch(
            "rom_cleanup_workbench_window.messagebox.showwarning"
        ) as warning, mock.patch("pathlib.Path.unlink", side_effect=PermissionError("locked")):
            window.confirm_delete()
        self.assertIn("locked", warning.call_args.args[1])
        self.assertTrue(window.had_errors)
        self.assertIsNone(window._analysis)
        self.assertEqual(len(list(self.dir.iterdir())), 2)
        self.assertEqual(len(window.review.results[0].marked), 1)
        self.assertIn("To delete: 1 file(s)", window.status.get())

    def test_close_after_changes_asks_first(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.tree.selection_set(self.row_of(window, "Title (USA).bin"))
        window.demote_selected()
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=False) as ask:
            window.close()
        ask.assert_called_once()
        self.assertTrue(window.root.winfo_exists())
        self.assertEqual(len(list(self.dir.iterdir())), 2)

    def test_closing_with_changes_deletes_nothing(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.tree.selection_set(self.row_of(window, "Title (USA).bin"))
        window.demote_selected()
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=True):
            window.close()
        self.assertEqual(len(list(self.dir.iterdir())), 2)

    def test_window_shows_folder_and_priority(self):
        self.write("Title (USA).bin")
        window = self.open_window()
        self.assertIn(str(self.dir), window.folder.get())
        self.assertNotIn(str(self.dir), window.info.get())
        self.assertIn("Priority: USA > Europe", window.info.get())

    def test_folder_is_right_aligned_in_the_green_title_row(self):
        window = self.open_window()
        self.assertEqual(window.folder_label.master, window.title_row)
        self.assertEqual(window.folder_label.pack_info()["side"], "right")
        self.assertEqual(str(window.folder_label.cget("style")), "Highlight.TLabel")

    def test_filter_is_left_aligned_in_the_bottom_row(self):
        window = self.open_window()
        bottom = window.search_entry.master
        from_bottom = [widget for widget in window.root.pack_slaves() if widget.pack_info()["side"] == "bottom"]
        self.assertEqual(from_bottom[0], bottom)  # The first row packed from the bottom is the lowest.
        lefts = [widget for widget in bottom.pack_slaves() if widget.pack_info()["side"] == "left"]
        self.assertEqual(lefts[-1], window.search_entry)
        self.assertEqual(lefts[0].cget("text"), "Filter file names:")

    def test_minimum_width_grows_with_the_font_so_the_filter_stays_usable(self):
        window = self.open_window()
        before = window.root.minsize()[0]
        window.change_font_size(8)
        window.root.update_idletasks()
        self.assertGreater(window.root.minsize()[0], before)
        self.assertGreaterEqual(window.root.minsize()[0], window.bottom_row.winfo_reqwidth())

    def test_background_analysis_fills_the_list(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.start_analysis()
        self.assertEqual(window.tree.get_children(), ())
        self.assertIn("Analyzing", window.status.get())
        self.wait_for_analysis(window)
        self.assertEqual(window.tree.get_children(), ("g0",))

    def test_progress_is_shown_during_analysis(self):
        window = self.open_window()
        release = threading.Event()

        def slow_analysis(_directory, progress):
            progress(3, 10)
            release.wait(10)
            return rf.Review([], self.config)

        window.analyze = slow_analysis
        window.start_analysis()
        deadline = time.monotonic() + 10
        while "3 of 10" not in window.status.get() and time.monotonic() < deadline:
            window.root.update()
            time.sleep(0.01)
        release.set()
        self.assertEqual(window.status.get(), "Analyzing: 3 of 10 files")
        self.assertEqual(window.progress_bar.place_info()["relx"], "0.5")
        self.assertEqual(float(window.progress_bar.cget("value")), 3)
        self.assertEqual(float(window.progress_bar.cget("maximum")), 10)
        self.wait_for_analysis(window)
        self.assertEqual(window.status.get(), "Analysis finished: Nothing to do")
        self.assertEqual(window.progress_bar.place_info(), {})

    def test_progress_bar_is_hidden_without_analysis(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        self.assertEqual(window.progress_bar.place_info(), {})

    def test_progress_bar_starts_empty_on_every_analysis(self):
        window = self.open_window()
        window.progress_bar.configure(value=5, maximum=5)
        window.start_analysis()
        self.assertEqual(float(window.progress_bar.cget("value")), 0)
        self.wait_for_analysis(window)

    def test_progress_bar_disappears_after_error(self):
        window = self.open_window()
        window.analyze = mock.Mock(side_effect=ValueError("broken"))
        with mock.patch("rom_cleanup_workbench_window.messagebox.showerror"):
            window.start_analysis()
            self.assertNotEqual(window.progress_bar.place_info(), {})
            self.wait_for_analysis(window)
        self.assertEqual(window.progress_bar.place_info(), {})

    def test_title_and_status_rows_are_green(self):
        window = self.open_window()
        from tkinter import ttk

        self.assertEqual(window.title_label.cget("text"), "Rom Cleanup Workbench")
        self.assertEqual(ttk.Style(window.root).lookup("Highlight.TLabel", "background"), "#1a7f37")
        self.assertEqual(str(window.title_label.cget("style")), "Highlight.TLabel")
        self.assertEqual(window.root.pack_slaves()[0], window.title_row)
        self.assertEqual(str(window.status_label.cget("style")), "Highlight.TLabel")

    def test_analysis_error_is_shown_in_the_window(self):
        window = self.open_window()
        window.analyze = mock.Mock(side_effect=ValueError("Configuration unreadable: broken"))
        with mock.patch("rom_cleanup_workbench_window.messagebox.showerror") as error:
            window.start_analysis()
            self.wait_for_analysis(window)
        self.assertIn("broken", error.call_args.args[1])
        self.assertIn("broken", window.status.get())
        self.assertIsNone(window.review)

    def test_keys_without_analysis_do_nothing(self):
        window = self.open_window()
        window.review = None
        window.demote_selected()
        window.promote_selected()
        window.confirm_delete()
        window._show_all_groups()

    def test_reanalyze_keeps_changes_when_declined(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.tree.selection_set(self.row_of(window, "Title (USA).bin"))
        window.demote_selected()
        with mock.patch("rom_cleanup_workbench_window.messagebox.askyesno", return_value=False):
            window.reanalyze()
        self.assertIsNone(window._analysis)
        self.assertEqual(window.review.moved_count(), 1)

    def test_chosen_folder_is_analyzed(self):
        self.write("Title (USA).bin")
        window = self.open_window()
        with tempfile.TemporaryDirectory() as other:
            (Path(other) / "Another (USA).bin").write_bytes(b"x")
            (Path(other) / "Another (Japan).bin").write_bytes(b"y")
            window.analyze = lambda directory, _progress=None: rf.Review(
                rf.scan_directory(directory, self.config), self.config
            )
            self.choose_in_window(window, other)
            self.wait_for_analysis(window)
            self.assertEqual(window.tree.item("g0", "text"), "Another")
            self.assertIn(other, window.folder.get())

    def slow_folder_analysis(self, other):
        """The test folder hangs until release is set; the other folder finishes at once."""
        release = threading.Event()
        replaced = []

        def analyze(directory, progress=None):
            if str(directory) == str(other):
                return rf.Review(rf.scan_directory(Path(other), self.config), self.config)
            progress(1, 2)
            release.wait(10)
            try:
                progress(2, 2)
            except Exception as error:
                replaced.append(type(error).__name__)
                raise
            return rf.Review([], self.config)

        return analyze, release, replaced

    def test_folder_can_be_changed_during_analysis(self):
        self.write("Title (USA).bin")
        window = self.open_window()
        with tempfile.TemporaryDirectory() as other:
            (Path(other) / "Another (USA).bin").write_bytes(b"x")
            (Path(other) / "Another (Japan).bin").write_bytes(b"y")
            window.analyze, release, replaced = self.slow_folder_analysis(other)
            window.start_analysis()
            first = window._workers[-1]
            self.choose_in_window(window, other)
            deadline = time.monotonic() + 10
            while window._analysis is not None and time.monotonic() < deadline:
                window.root.update()
                time.sleep(0.01)
            self.assertEqual(window.tree.item("g0", "text"), "Another")
            self.assertFalse(gc.isenabled(), "The replaced analysis is still running")

            release.set()
            first.join(10)
            self.assertEqual(replaced, ["_AnalysisReplaced"])
            self.wait_for_analysis(window)
            window.root.update()
            self.assertEqual(window.tree.item("g0", "text"), "Another")
            self.assertIn(other, window.folder.get())

    def test_reanalyze_during_analysis_starts_over(self):
        window = self.open_window()
        release = threading.Event()
        window.analyze = lambda _directory, _progress=None: release.wait(10) and rf.Review([], self.config)
        window.start_analysis()
        first = window._analysis
        window.reanalyze()
        self.assertIsNot(window._analysis, first)
        release.set()
        self.wait_for_analysis(window)

    def test_old_result_cannot_overwrite_the_new_analysis(self):
        self.write("Title (USA).bin")
        window = self.open_window()
        old = queue.Queue()
        old.put((rf.Review([], self.config), None))
        window._poll_analysis(old)
        self.assertIsNotNone(window.review)
        self.assertEqual(len(window.review.results), 1)

    def test_cancelled_folder_choice_changes_nothing(self):
        self.write("Title (USA).bin")
        window = self.open_window()
        window.choose_directory()
        window.folder_panel.close()  # Cancel or Esc
        self.assertIsNone(window.folder_panel)
        self.assertEqual(window.directory, self.dir)
        self.assertIsNone(window._analysis)
        self.assertEqual(window.list_frame.winfo_manager(), "pack")

    def choose_in_window(self, window, folder):
        """Chooses a folder in the folder choice of the window, as a person would."""
        window.choose_directory()
        panel = window.folder_panel
        panel.reveal(Path(folder))
        self.assertEqual(os.path.normcase(panel.path.get()), os.path.normcase(str(Path(folder))))
        panel.choose()
        self.assertIsNone(window.folder_panel)

    def test_folder_choice_appears_in_the_window_and_opens_at_the_current_folder(self):
        self.no_system_popups()
        (self.dir / "Sub B").mkdir()
        (self.dir / "sub a").mkdir()
        (self.dir / ".hidden").mkdir()
        window = self.open_window()
        window.choose_directory()
        panel = window.folder_panel
        self.assertIs(panel.frame.master, window.middle)
        self.assertEqual(window.list_frame.winfo_manager(), "")
        self.assertFalse([child for child in window.root.winfo_children() if child.winfo_class() == "Toplevel"])
        self.assertEqual(os.path.normcase(panel.path.get()), os.path.normcase(str(self.dir)))
        key = panel.tree.selection()[0]
        self.assertTrue(panel.tree.item(key, "open"))
        self.assertEqual([panel.tree.item(child, "text") for child in panel.tree.get_children(key)], ["sub a", "Sub B"])
        self.assertTrue(all(widget.instate(["disabled"]) for widget in window._list_controls))
        self.assertTrue(window.settings_button.instate(["disabled"]))

    def test_folder_choice_takes_a_typed_path_and_refuses_a_missing_one(self):
        self.no_system_popups()
        window = self.open_window()
        with tempfile.TemporaryDirectory() as other:
            window.choose_directory()
            panel = window.folder_panel
            panel.path.set(str(Path(other) / "missing"))
            with mock.patch("rom_cleanup_workbench_window.messagebox.showerror") as error:
                panel.choose()
            self.assertIn("missing", error.call_args.args[1])
            self.assertIs(window.folder_panel, panel)
            panel.path.set(f'"{other}"')  # Pasted with quotes, as Explorer copies a path.
            with mock.patch.object(window, "start_analysis") as analysis:
                panel.choose()
            analysis.assert_called_once()
            self.assertEqual(window.directory, Path(other))

    def test_kept_files_are_green_and_marked_files_red(self):
        import rom_cleanup_workbench_window as window_module
        self.write("Title (USA).bin", b"usa")
        self.write("Title (Japan).bin", b"jap")
        window = self.open_window()
        self.assertEqual(str(window.tree.tag_configure("keep", "foreground")), window_module._KEEP_TEXT)
        self.assertEqual(str(window.tree.tag_configure("marked", "foreground")), window_module._MARKED_TEXT)
        rows = [row for row in window._file_ids.values() if window.tree.exists(row)]
        self.assertTrue(rows)
        for row in rows:
            tags = window.tree.item(row, "tags")
            self.assertTrue("keep" in tags or "marked" in tags, tags)

    def test_double_click_chooses_the_folder(self):
        self.no_system_popups()
        (self.dir / "More").mkdir()
        window = self.open_window()
        window.choose_directory()
        panel = window.folder_panel
        key = panel._key(self.dir / "More")
        panel.tree.see(key)
        for _ in range(100):  # until the tree is drawn (under WSLg this takes a moment)
            window.root.update()
            if panel.tree.bbox(key):
                break
            time.sleep(0.02)
        else:
            self.skipTest("The folder tree was not drawn")
        x, y, width, height = panel.tree.bbox(key)
        event = mock.Mock(x=x + width - 5, y=y + height // 2)
        with mock.patch.object(window, "start_analysis") as analysis:
            self.assertEqual(panel._choose_clicked(event), "break")
        analysis.assert_called_once()
        self.assertEqual(window.directory, self.dir / "More")
        self.assertIsNone(window.folder_panel)

    def test_double_click_on_empty_space_chooses_nothing(self):
        window = self.open_window()
        window.choose_directory()
        panel = window.folder_panel
        with mock.patch.object(window, "start_analysis") as analysis:
            self.assertIsNone(panel._choose_clicked(mock.Mock(x=5, y=10000)))
        analysis.assert_not_called()
        self.assertIs(window.folder_panel, panel)

    def test_folders_are_read_only_when_opened(self):
        (self.dir / "Outer").mkdir()
        (self.dir / "Outer" / "Inner").mkdir()
        window = self.open_window()
        window.choose_directory()
        panel = window.folder_panel
        outer = panel._key(self.dir / "Outer")
        self.assertEqual(panel.tree.get_children(outer), (outer + panel._PLACEHOLDER,))
        panel._load(outer)
        self.assertEqual([panel.tree.item(child, "text") for child in panel.tree.get_children(outer)], ["Inner"])

    def test_keys_of_the_list_do_nothing_while_choosing_a_folder(self):
        self.write("Title (USA).bin")
        self.write("Title (Japan).bin")
        window = self.open_window()
        window.tree.selection_set(self.row_of(window, "Title (USA).bin"))
        window.choose_directory()
        window.demote_selected()
        window.toggle_settings()
        self.assertEqual(window.review.moved_count(), 0)
        self.assertIsNone(window.settings_panel)
        for widget in (window.folder_panel.entry, window.folder_panel.tree):
            self.assertNotIn(str(window.root), widget.bindtags())
        window._on_escape()
        self.assertIsNone(window.folder_panel)
        self.assertTrue(window.root.winfo_exists())


class MainTests(RedundanzTestCase):
    def setUp(self):
        super().setUp()
        # Without --config the program reads redundanz_config.json next to it; the tests must not
        # depend on the language or priority someone has set there.
        patcher = mock.patch.object(rf, "DEFAULT_CONFIG_PATH", self.dir.with_name(self.dir.name + "-missing.json"))
        patcher.start()
        self.addCleanup(patcher.stop)
        # These tests expect the window; on a Linux test machine without a display the program
        # would otherwise choose the terminal version on its own.
        display = mock.patch.dict(os.environ, {"DISPLAY": ":0"})
        display.start()
        self.addCleanup(display.stop)

    def choose_front_end(self, *args, platform="win32", environment=None):
        """Starts main and reports which front end it chose; neither one really opens."""
        try:
            # Loaded before sys.platform is changed below: Textual reads it once when it is imported.
            import rom_cleanup_workbench_tui  # noqa: F401
        except ImportError as error:
            self.skipTest(f"Textual is not installed: {error}")
        chosen = []
        environment = environment if environment is not None else {}
        with mock.patch.object(rf.sys, "platform", platform), mock.patch.dict(os.environ, environment), mock.patch(
            "rom_cleanup_workbench_window.run_window", lambda *a, **_k: chosen.append("window") or 0
        ), mock.patch("rom_cleanup_workbench_tui.run_tui", lambda *a, **_k: chosen.append(("tui", a[1:])) or 0):
            for name in ("DISPLAY", "WAYLAND_DISPLAY"):
                if name not in environment:
                    os.environ.pop(name, None)
            code = rf.main([str(self.dir), *args])
        return code, chosen

    def test_tui_option_starts_the_terminal_version(self):
        code, chosen = self.choose_front_end("--tui", "--review", "problems")
        self.assertEqual(code, 0)
        self.assertEqual(chosen[0][0], "tui")
        directory, scope, config_file, ascii_mode = chosen[0][1]
        self.assertEqual((directory, scope), (self.dir, "problems"))
        self.assertIsInstance(config_file, rf.ConfigFile)
        self.assertIsNone(ascii_mode)  # the terminal version finds out itself

    def test_ascii_option_starts_the_terminal_version_with_ascii(self):
        code, chosen = self.choose_front_end("--ascii", platform="win32")
        self.assertEqual(code, 0)
        self.assertEqual(chosen[0][0], "tui")
        self.assertIs(chosen[0][1][3], True)

    def test_linux_without_display_starts_the_terminal_version(self):
        self.assertEqual(self.choose_front_end(platform="linux")[1][0][0], "tui")
        self.assertEqual(self.choose_front_end(platform="linux", environment={"DISPLAY": ":0"})[1], ["window"])
        self.assertEqual(self.choose_front_end(platform="linux", environment={"WAYLAND_DISPLAY": "w"})[1], ["window"])

    def test_windows_starts_the_window_without_tui(self):
        self.assertEqual(self.choose_front_end(platform="win32")[1], ["window"])

    def test_missing_textual_is_reported_and_nothing_is_deleted(self):
        self.prepare()
        error = io.StringIO()
        with mock.patch.dict(sys.modules, {"rom_cleanup_workbench_tui": None}), contextlib.redirect_stderr(error):
            code, output = self.run_main("--tui")
        self.assertEqual(code, 1)
        self.assertIn("pip install textual", error.getvalue())
        self.assertIn("Nothing was deleted.", output)
        self.assertEqual(len(self.remaining()), 2)

    def run_main(self, *args):
        output = io.StringIO()
        # An unexpected window or terminal prompt should fail the test, not block it.
        with mock.patch("builtins.input", side_effect=AssertionError("Prompt in terminal")), mock.patch(
            "rom_cleanup_workbench_window.run_window", side_effect=AssertionError("Window opened")
        ), contextlib.redirect_stdout(output):
            code = rf.main([str(self.dir), *args])
        return code, output.getvalue()

    def run_window_main(self, *args, delete=False, demote=None, promote=None, argv=None):
        """Replaces the window and carries out the requested changes directly."""
        self.window_calls = []

        def run(analyze, directory, scope, config_file=None, _config_loader=None):
            self.window_calls.append((directory, scope))
            self.config_file = config_file
            if directory is None:
                return 0
            review = analyze(directory)
            for result in review.results:
                for entry in list(result.keep):
                    if entry.path.name == demote:
                        review.demote(result, entry)
                for entry in list(result.marked):
                    if entry.path.name == promote:
                        review.promote(result, entry)
            if delete:
                review.delete()
            return 0

        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=AssertionError("Prompt in terminal")), mock.patch(
            "rom_cleanup_workbench_window.run_window", run
        ), contextlib.redirect_stdout(output):
            code = rf.main(argv if argv is not None else [str(self.dir), *args])
        return code, output.getvalue()

    def prepare(self):
        self.write("Title (USA).bin", b"usa")
        self.write("Title (Japan).bin", b"jap")

    def remaining(self):
        return sorted(path.name for path in self.dir.iterdir())

    def test_report_only_deletes_nothing(self):
        self.prepare()
        self.run_main("--report-only")
        self.assertEqual(len(self.remaining()), 2)

    def test_default_opens_window_without_terminal_output(self):
        self.prepare()
        code, output = self.run_window_main()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")
        self.assertEqual(self.window_calls, [(self.dir, None)])
        self.assertEqual(len(self.remaining()), 2)

    def test_directory_is_optional_for_the_window(self):
        self.prepare()
        self.run_window_main(argv=[])
        self.assertEqual(self.window_calls, [(None, None)])

    def test_terminal_modes_need_a_directory(self):
        for option in ("--report-only", "--yes"):
            with self.subTest(option), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    rf.main([option])

    def test_missing_directory_reaches_the_window_as_error(self):
        captured = []

        def run(analyze, directory, _only_problems, _config_file=None, _config_loader=None):
            with self.assertRaisesRegex(ValueError, "not found"):
                analyze(directory)
            captured.append(directory)
            return 0

        with mock.patch("rom_cleanup_workbench_window.run_window", run):
            rf.main([str(self.dir / "missing")])
        self.assertEqual(len(captured), 1)

    def test_faulty_config_reaches_the_window_as_error_and_deletes_nothing(self):
        self.prepare()
        path = self.write_config("{not json")
        captured = []

        def run(analyze, directory, _only_problems, _config_file=None, _config_loader=None):
            with self.assertRaisesRegex(ValueError, "Configuration unreadable"):
                analyze(directory)
            captured.append(directory)
            return 0

        with mock.patch("rom_cleanup_workbench_window.run_window", run):
            rf.main([str(self.dir), "--config", str(path)])
        self.assertEqual(len(captured), 1)
        self.assertEqual(len(self.remaining()), 2)

    def test_config_is_read_again_for_every_analysis(self):
        self.prepare()
        path = self.write_config('{"region_priority": ["Japan", "USA"]}')
        priorities = []

        def run(analyze, directory, _only_problems, _config_file=None, _config_loader=None):
            priorities.append(analyze(directory).config.region_priority)
            path.write_text('{"region_priority": ["USA", "Japan"]}', encoding="utf-8")
            priorities.append(analyze(directory).config.region_priority)
            return 0

        with mock.patch("rom_cleanup_workbench_window.run_window", run):
            rf.main([str(self.dir), "--config", str(path)])
        self.assertEqual(priorities, [["Japan", "USA"], ["USA", "Japan"]])

    def test_yes_deletes_without_prompt(self):
        self.prepare()
        self.run_main("--yes")
        self.assertEqual(self.remaining(), ["Title (USA).bin"])

    def test_review_option_opens_window_with_problems(self):
        self.prepare()
        self.run_window_main("--review", "problems")
        self.assertEqual(self.window_calls, [(self.dir, "problems")])
        self.run_window_main("--review", "all")
        self.assertEqual(self.window_calls, [(self.dir, "marked")])

    def test_window_deletes_according_to_the_changes(self):
        self.prepare()
        self.run_window_main(delete=True, demote="Title (USA).bin", promote="Title (Japan).bin")
        self.assertEqual(self.remaining(), ["Title (Japan).bin"])

    def test_window_can_delete_file_without_redundancy(self):
        self.write("Title (USA).bin")
        self.run_window_main(delete=True, demote="Title (USA).bin")
        self.assertEqual(self.remaining(), [])

    def test_closed_window_deletes_nothing(self):
        self.prepare()
        self.run_window_main(demote="Title (USA).bin")
        self.assertEqual(len(self.remaining()), 2)

    def test_program_without_window_deletes_nothing(self):
        self.prepare()
        output = io.StringIO()
        with mock.patch("rom_cleanup_workbench_window.run_window", side_effect=RuntimeError("no display")), contextlib.redirect_stdout(
            output
        ), contextlib.redirect_stderr(io.StringIO()):
            code = rf.main([str(self.dir)])
        self.assertEqual(code, 1)
        self.assertIn("Nothing was deleted", output.getvalue())
        self.assertEqual(len(self.remaining()), 2)

    def test_review_cannot_be_combined_with_yes(self):
        self.prepare()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.run_main("--review", "all", "--yes")
        self.assertEqual(len(self.remaining()), 2)

    def test_priority_option_overrides_config(self):
        self.prepare()
        self.run_main("--priority", "Japan", "USA", "--yes")
        self.assertEqual(self.remaining(), ["Title (Japan).bin"])

    def test_delete_tag_option(self):
        self.write("Title (Beta).bin")
        self.run_main("--delete-tag", "Beta", "--yes")
        self.assertEqual(self.remaining(), [])

    def write_config(self, content):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "config.json"
        path.write_bytes(content.encode("utf-8"))
        return path

    def test_priority_comes_from_config_file(self):
        self.prepare()
        path = self.write_config('{"region_priority": ["Japan", "USA"]}')
        _, output = self.run_main("--config", str(path), "--yes")
        self.assertEqual(self.remaining(), ["Title (Japan).bin"])
        self.assertIn("Priority: Japan > USA", output)

    def test_language_from_config_file_applies_to_the_terminal(self):
        self.prepare()
        path = self.write_config('{"language": "de"}')
        _, output = self.run_main("--config", str(path), "--report-only")
        self.assertIn("Priorität: USA > Europe", output)
        self.assertIn("Es wurde nichts gelöscht.", output)
        self.assertEqual(translations.current_language(), "de")

    def test_window_gets_the_configuration_file_the_analysis_reads(self):
        self.prepare()
        path = self.write_config('{"language": "en"}')
        self.run_window_main("--config", str(path))
        self.assertEqual(self.config_file.path, path)
        self.run_window_main()
        self.assertEqual(self.config_file.path, rf.DEFAULT_CONFIG_PATH)

    def test_broken_config_falls_back_to_english_texts(self):
        self.prepare()
        path = self.write_config('{"language": "xx"}')
        with contextlib.redirect_stderr(io.StringIO()) as error, self.assertRaises(SystemExit):
            self.run_main("--config", str(path), "--report-only")
        self.assertIn('Unknown language "xx"', error.getvalue())

    def test_config_file_with_bom_is_accepted(self):
        self.prepare()
        path = self.write_config('﻿{"region_priority": ["Japan", "USA"]}')
        self.run_main("--config", str(path), "--yes")
        self.assertEqual(self.remaining(), ["Title (Japan).bin"])

    def test_faulty_config_file_stops_before_deleting(self):
        self.prepare()
        for content in (
            '{"region_priorty": ["Japan"]}',
            '{"region_priority": "Japan"}',
            '["Japan"]',
            "{not json",
            '{"language": "xx"}',
            '{"language": ["de"]}',
            '{"part_tags": "Disc"}',
        ):
            path = self.write_config(content)
            with self.subTest(content), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    self.run_main("--config", str(path), "--yes")
                self.assertEqual(len(self.remaining()), 2)


if __name__ == "__main__":
    unittest.main()


class TerminalVersionTests(unittest.IsolatedAsyncioTestCase):
    """The terminal version runs invisibly here; Textual's Pilot presses the keys."""

    def setUp(self):
        translations.set_language("en")
        self.addCleanup(translations.set_language, "en")
        try:
            import rom_cleanup_workbench_tui
        except ImportError as error:
            self.skipTest(f"Textual is not installed: {error}")
        self.tui = rom_cleanup_workbench_tui

    async def asyncSetUp(self):
        # unittest runs these tests in asyncio's debug mode, which reports every slow screen update.
        import asyncio

        asyncio.get_running_loop().set_debug(False)

    @staticmethod
    def text(app, selector):
        return str(app.query_one(selector).render())

    async def test_title_row_names_the_program_and_the_folder(self):
        app = self.tui.WorkbenchApp(None, Path("/home/user/games"))
        async with app.run_test():
            self.assertEqual(self.text(app, "#title"), "Rom Cleanup Workbench")
            self.assertIn("games", self.text(app, "#folder"))
            self.assertTrue(self.text(app, "#folder").startswith("Folder: "))

    async def test_title_row_speaks_the_language(self):
        translations.set_language("de")
        app = self.tui.WorkbenchApp(None, None)
        async with app.run_test():
            self.assertEqual(self.text(app, "#folder"), "Ordner: noch keiner gewählt (f)")  # the key here is f

    async def test_q_ends_the_program(self):
        app = self.tui.WorkbenchApp(None, None)
        async with app.run_test() as pilot:
            await self.started(app, pilot)
            await pilot.press("q")
            await pilot.pause()
            self.assertFalse(app.is_running)

    async def started(self, app, pilot):
        """Without a folder, the folder choice opens at the start; waits until it is there."""
        for _ in range(50):
            if app.folder_open():
                return
            await pilot.pause(0.02)
        self.fail("The folder choice did not open")

    def demo_folder(self, files):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name) / "games"
        folder.mkdir()
        for name, content in files.items():
            (folder / name).write_bytes(content)
        return folder

    def app_for(self, files, scope="marked", analyze=None, **options):
        folder = self.demo_folder(files)
        config = rules_config()
        analyze = analyze or (lambda directory, progress=None: rf.Review(
            rf.scan_directory(directory, config, progress), config))
        return self.tui.WorkbenchApp(analyze, folder, scope, settings_path=folder.with_name("settings.json"),
                                     **options)

    async def analyzed(self, app, pilot):
        await app.workers.wait_for_complete()
        await pilot.pause()

    @staticmethod
    def rows(app):
        from textual.widgets import DataTable

        table = app.query_one("#games", DataTable)
        # The cells carry their own spaces (the table has no padding of its own).
        return [[str(cell).strip() for cell in table.get_row(key)] for key in table.rows]

    async def test_list_shows_games_sections_sizes_and_notes(self):
        app = self.app_for({
            "Title (USA).bin": b"x" * 3000, "Title (Japan).bin": b"x" * 3000, "Other (USA) (Hack).bin": b"x" * 10,
        })
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            rows = self.rows(app)
            texts = [row[0].strip() for row in rows]
            self.assertIn("Title", texts)
            self.assertIn("Keep:", texts)
            self.assertIn("Marked for deletion", texts)
            self.assertIn("+ Title (USA).bin", texts)
            self.assertIn("- Title (Japan).bin", texts)
            japan = next(row for row in rows if row[0].strip() == "- Title (Japan).bin")
            self.assertEqual(japan[1], "3 KB")
            proto = next(row for row in rows if row[0].strip() == "- Other (USA) (Hack).bin")
            self.assertEqual(" ".join(proto[2].split()), "Deleted according to delete keyword (Hack) - as requested")
            self.assertIn("Showing: 2 of 2 games", self.text(app, "#status"))
            self.assertIn("Priority: USA > Europe", self.text(app, "#info"))
            self.assertEqual(len(app.files), 3)

    async def test_brackets_in_file_names_are_shown_literally(self):
        app = self.app_for({"Title [!] (USA).bin": b"a", "Title [b1] (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertIn("+ Title [!] (USA).bin", [row[0].strip() for row in self.rows(app)])

    async def test_nothing_to_do_is_shown_in_the_middle(self):
        app = self.app_for({"Alone (USA).bin": b"a"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertTrue(app.query_one("#nothing").display)
            self.assertFalse(app.query_one("#games").display)
            self.assertEqual(self.text(app, "#status"), "Analysis finished: Nothing to do")

    async def test_all_files_view_shows_games_without_marks(self):
        app = self.app_for({"Alone (USA).bin": b"a"}, scope="all")
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertFalse(app.query_one("#nothing").display)
            self.assertIn("+ Alone (USA).bin", [row[0].strip() for row in self.rows(app)])

    async def test_analysis_error_reaches_the_status_row(self):
        def broken(_directory, _progress=None):
            raise ValueError("Configuration unreadable: broken")
        app = self.app_for({}, analyze=broken)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertEqual(self.text(app, "#status"), "Analysis not possible: Configuration unreadable: broken")
            self.assertFalse(app.query_one("#progress").display)

    async def test_progress_and_replaced_analyses(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            app._show_progress(app._analysis, 1, 2)
            self.assertEqual(self.text(app, "#status"), "Analyzing: 1 of 2 files")
            before = app.review
            app._finish_analysis(app._analysis - 1, rf.Review([], rf.Config.load(None)), None)  # an older one
            self.assertIs(app.review, before)

    async def test_confirmed_save_files_are_not_suspected_again(self):
        import workbench_state

        app = self.app_for({"Title (USA).sfc": b"x" * 1000, "Title.srm": b"x" * 100})
        save = app.directory / "Title.srm"
        workbench_state.add_confirmed_saves(app.settings_path, {rf.save_file_key(save): 100})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertTrue(app.query_one("#nothing").display)

    # Step 4: moving the cursor ------------------------------------------------------------------

    TWO_GAMES = {"A (USA).bin": b"a", "A (Japan).bin": b"b", "B (USA).bin": b"c", "B (Japan).bin": b"d"}

    async def test_first_file_is_selected_after_the_analysis(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertEqual(app.cursor_key(), "g0f0")
            self.assertEqual(app.selected_keys(), ["g0f0"])

    async def test_arrows_move_the_selection_across_the_empty_rows(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("down")
            self.assertEqual(app.selected_keys(), ["g0h"])
            await pilot.press("down", "down")
            self.assertEqual(app.selected_keys(), ["g1"])  # not the empty row s1
            await pilot.press("up")
            self.assertEqual(app.selected_keys(), ["g0f1"])
            await pilot.press("up", "up", "up", "up", "up", "up")
            self.assertEqual(app.selected_keys(), ["g0"])  # stops at the top

    async def test_shift_arrows_grow_and_shrink_the_selection(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("shift+down", "shift+down")
            self.assertEqual(app.selected_keys(), ["g0f0", "g0h", "g0f1"])
            table = app.query_one("#games")
            from rich.style import Style
            colors = [table._get_row_style(index, Style()).bgcolor for index in range(6)]
            self.assertEqual(colors[2], colors[3])  # selected rows are painted like the cursor row
            self.assertNotEqual(colors[0], colors[2])
            await pilot.press("shift+up")
            self.assertEqual(app.selected_keys(), ["g0f0", "g0h"])
            self.assertEqual(app.cursor_key(), "g0h")
            await pilot.press("shift+down", "shift+down")
            self.assertEqual(app.selected_keys(), ["g0f0", "g0h", "g0f1", "g1"])
            await pilot.press("down")
            self.assertEqual(app.selected_keys(), ["g1k"])

    async def test_tab_jumps_to_the_first_file_of_the_next_game(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("shift+down")
            await pilot.press("tab")
            self.assertEqual(app.selected_keys(), ["g1f0"])
            await pilot.press("tab")  # the last game: stays
            self.assertEqual(app.selected_keys(), ["g1f0"])
            self.assertIs(app.focused, app.query_one("#games"))
            await pilot.press("shift+tab")
            self.assertEqual(app.selected_keys(), ["g0f0"])
            await pilot.press("shift+tab")
            self.assertEqual(app.selected_keys(), ["g0f0"])

    async def test_tab_shows_the_whole_next_game(self):
        files = {}
        for number in range(30):
            files[f"Game {number:02} (USA).bin"] = b"a"
            files[f"Game {number:02} (Japan).bin"] = b"b"
        app = self.app_for(files)
        async with app.run_test(size=(80, 24)) as pilot:
            await self.analyzed(app, pilot)
            table = app.query_one("#games")
            for _ in range(5):
                await pilot.press("tab")
            await pilot.pause()
            self.assertEqual(app.cursor_key(), "g5f0")
            top = int(table.scroll_y)
            visible = table.scrollable_content_region.height - 1  # minus the header
            title, last = table.get_row_index("g5"), table.get_row_index("g5f1")
            self.assertTrue(top <= title and last < top + visible, (top, title, last, visible))

    async def test_mouse_click_selects_one_row_and_the_wheel_scrolls(self):
        files = {}
        for number in range(30):
            files[f"Game {number:02} (USA).bin"] = b"a"
            files[f"Game {number:02} (Japan).bin"] = b"b"
        app = self.app_for(files)
        async with app.run_test(size=(140, 24)) as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("shift+down", "shift+down")
            # Row 0 of the table is the header; row 5 of the list is g0f1 ("- Game 00 (Japan).bin").
            await pilot.click("#games", offset=(10, 5))
            await pilot.pause()
            self.assertEqual(app.selected_keys(), ["g0f1"])
            await pilot.click("#games", offset=(10, 6))  # the empty row between two games
            await pilot.pause()
            self.assertEqual(app.selected_keys(), [])
            table = app.query_one("#games")
            self.assertEqual(table.scroll_y, 0)
            await pilot.hover("#games", offset=(10, 5))
            from textual import events
            for _ in range(3):
                table.post_message(events.MouseScrollDown(table, 10, 5, 0, 0, 0, False, False, False))
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            self.assertGreater(table.scroll_y, 0)
            await pilot.press("tab", "shift+down", "pagedown")
            self.assertEqual(app.selected_keys(), [app.cursor_key()])
            await pilot.press("shift+up", "ctrl+home")
            self.assertEqual(app.selected_keys(), ["g0"])

    # Step 5: D and P ----------------------------------------------------------------------------

    def row_texts(self, app):
        return [row[0].strip() for row in self.rows(app)]

    def note_of(self, app, name):
        return next(row[2] for row in self.rows(app) if row[0].strip()[2:] == name)

    async def test_d_and_p_move_the_rows_and_keep_the_selection(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            keep_row = app.cursor_key()
            self.assertEqual(self.row_texts(app)[2], "+ Title (USA).bin")
            await pilot.press("x")
            self.assertEqual(app.selected_keys(), [keep_row])
            self.assertEqual(app.cursor_key(), keep_row)
            self.assertIn("- Title (USA).bin", self.row_texts(app))
            self.assertIn("By hand: delete", self.note_of(app, "Title (USA).bin"))
            self.assertEqual(app.review.moved_count(), 1)
            self.assertIn(keep_row, app.query_one("#games").moved)
            await pilot.press("K")
            self.assertEqual(app.review.moved_count(), 0)
            self.assertEqual(self.row_texts(app)[2], "+ Title (USA).bin")
            self.assertNotIn("By hand", self.note_of(app, "Title (USA).bin"))
            self.assertEqual(app.query_one("#games").moved, set())

    async def test_p_sorts_the_file_in_among_kept_files(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("down", "down")
            self.assertEqual(app.selected_keys(), ["g0f1"])
            await pilot.press("k")
            self.assertEqual(self.row_texts(app)[1:4], ["Keep:", "+ Title (USA).bin", "+ Title (Japan).bin"])
            self.assertIn("By hand: keep", self.note_of(app, "Title (Japan).bin"))
            self.assertEqual(app.selected_keys(), ["g0f1"])

    async def test_heading_disappears_when_nothing_is_kept(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("x")
            self.assertEqual(self.row_texts(app), ["Title", "Marked for deletion",
                                                   "- Title (Japan).bin", "- Title (USA).bin"])
            self.assertEqual(app.cursor_key(), "g0f0")

    async def test_several_rows_move_together_and_game_rows_do_nothing(self):
        app = self.app_for({"Title (USA) (Disc 1).bin": b"a", "Title (USA) (Disc 2).bin": b"b",
                            "Title (Japan).bin": b"c"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("up", "x", "up", "x")  # the heading and the game row
            self.assertEqual(app.selected_keys(), ["g0"])
            self.assertEqual(app.review.moved_count(), 0)
            await pilot.press("down", "down", "shift+down", "x")
            self.assertEqual(app.review.moved_count(), 2)
            self.assertEqual(sum(text.startswith("- ") for text in self.row_texts(app)), 3)
            self.assertEqual(len(app.selected_keys()), 2)

    async def test_status_row_follows_the_changes_by_hand(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            before = self.text(app, "#status")
            await pilot.press("x")
            self.assertEqual(self.text(app, "#status"), app.review.status(False, False, ""))
            self.assertNotEqual(self.text(app, "#status"), before)

    async def test_d_and_p_do_nothing_before_the_analysis(self):
        app = self.tui.WorkbenchApp(None, None)
        async with app.run_test() as pilot:
            await self.started(app, pilot)
            await pilot.press("x", "k", "down", "tab")
            self.assertEqual(self.text(app, "#status"), translations.tr("window.choose_folder_status"))

    # Step 6: views ------------------------------------------------------------------------------

    VIEW_GAMES = {"Other (USA).bin": b"a", "Clear (USA).bin": b"b", "Clear (Japan).bin": b"c",
                  "Zelda (USA).nes": b"d", "Zelda (Japan).sfc": b"e"}

    def titles(self, app):
        return [str(app.query_one("#games").get_row(key)[0]) for key in app._keys()
                if key[0] == "g" and key[1:].isdigit()]

    async def test_keys_1_2_3_show_each_view(self):
        app = self.app_for(self.VIEW_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertEqual(self.titles(app), ["Clear", "Zelda"])
            await pilot.press("1")
            self.assertEqual(app.scope, "problems")
            self.assertEqual(self.titles(app), ["Zelda"])
            await pilot.press("3")
            self.assertEqual(self.titles(app), ["Clear", "Other", "Zelda"])
            self.assertIn("Showing: 3 of 3", self.text(app, "#status"))
            await pilot.press("2")
            self.assertEqual(self.titles(app), ["Clear", "Zelda"])
            self.assertTrue(app.query_one("#view-marked").value)
            self.assertFalse(app.query_one("#view-all").value)

    async def test_views_are_three_clickable_radio_items(self):
        from textual.widgets import RadioButton

        app = self.app_for(self.VIEW_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            labels = [str(button.label) for button in app.query(RadioButton)]
            self.assertEqual(labels, ["Problematic deletion marks", "All deletion marks", "All ROM files"])
            await pilot.click("#view-all")
            await pilot.pause()
            self.assertEqual(app.scope, "all")
            self.assertEqual(self.titles(app), ["Clear", "Other", "Zelda"])
            self.assertIs(app.focused, app.query_one("#games"))  # d and the arrows still act on the list
            await pilot.click("#view-problems")
            await pilot.pause()
            self.assertEqual(self.titles(app), ["Zelda"])

    async def test_view_is_saved_and_used_at_the_next_start(self):
        import workbench_state

        app = self.app_for(self.VIEW_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("3")
        self.assertEqual(workbench_state.load_scope(app.settings_path), "all")
        again = self.tui.WorkbenchApp(app.analyze, app.directory, settings_path=app.settings_path)
        async with again.run_test() as pilot:
            await self.analyzed(again, pilot)
            self.assertEqual(again.scope, "all")
            self.assertTrue(again.query_one("#view-all").value)

    async def test_view_that_cannot_be_saved_is_reported(self):
        app = self.app_for(self.VIEW_GAMES)
        app.settings_path = app.directory  # a folder: writing fails
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("1")
            await pilot.pause()
            self.assertTrue(app.question_open())
            self.assertEqual(self.text(app.screen, "#question-title"), "Choice not saved")
            self.assertTrue(self.text(app.screen, "#question-text"))  # the error of the system
            self.assertIn("kind-error", app.screen.classes)
            self.assertEqual(self.titles(app), ["Zelda"])
            await pilot.press("enter")  # OK
            await pilot.pause()
            self.assertFalse(app.question_open())
            self.assertIs(app.focused, app.query_one("#games"))

    async def test_selection_stays_when_the_view_changes(self):
        app = self.app_for(self.VIEW_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("tab")  # Zelda
            zelda = app.selected_keys()
            await pilot.press("3")
            self.assertEqual(app.selected_keys(), zelda)
            self.assertEqual(app.cursor_key(), zelda[0])
            await pilot.press("shift+tab")
            self.assertEqual(str(app.query_one("#games").get_row(app.cursor_key())[0]).strip(), "+ Other (USA).bin")
            await pilot.press("1")  # Other is not shown there: the first file is selected
            self.assertEqual(app.selected_keys(), [zelda[0]])

    async def test_all_files_view_replaces_nothing_to_do_and_demoted_games_stay(self):
        app = self.app_for({"Other (USA).bin": b"a"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertTrue(app.query_one("#nothing").display)
            await pilot.press("3")
            self.assertFalse(app.query_one("#nothing").display)
            await pilot.press("x")
            await pilot.press("2")
            self.assertEqual(self.titles(app), ["Other"])
            self.assertEqual(app.review.moved_count(), 1)

    # Step 7: filter -----------------------------------------------------------------------------

    FILTER_GAMES = {"One (USA).bin": b"a", "One (Japan).bin": b"b", "Two (USA).bin": b"c", "Two (Japan).bin": b"d"}

    async def filter_for(self, app, pilot, *keys):
        """Types into the filter field and returns to the list with Enter."""
        await pilot.press("slash", *keys, "enter")
        await pilot.pause()

    async def test_filter_shows_matching_games_and_clearing_restores_them(self):
        app = self.app_for(self.FILTER_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertEqual(self.titles(app), ["One", "Two"])
            await self.filter_for(app, pilot, *"two")
            self.assertEqual(self.titles(app), ["Two"])
            self.assertIn("Showing: 1 of 2 games", self.text(app, "#status"))
            self.assertIs(app.focused, app.query_one("#games"))
            await pilot.press("slash", "escape")
            await pilot.pause()
            self.assertEqual(app.query_one("#filter").value, "")
            self.assertEqual(self.titles(app), ["One", "Two"])
            self.assertIs(app.focused, app.query_one("#games"))
            self.assertTrue(app.is_running)  # Esc in the field does not end the program

    async def test_filter_knows_star_and_question_mark_but_not_brackets(self):
        app = self.app_for({"A [!] (USA).bin": b"a", "A (Japan).bin": b"b",
                            "Bb (USA).bin": b"c", "Bb (Japan).bin": b"d"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            field = app.query_one("#filter")
            for pattern, titles in (("b? *japan", ["Bb"]), ("[!]", ["A"]), ("*", ["A", "Bb"])):
                await pilot.press("slash")
                field.value = pattern
                await pilot.press("enter")
                await pilot.pause()
                self.assertEqual(self.titles(app), titles, pattern)

    async def test_keys_typed_in_the_filter_never_act_on_the_list(self):
        app = self.app_for(self.FILTER_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("slash", *"xkq3", "tab")
            await pilot.pause()
            self.assertEqual(app.query_one("#filter").value, "xkq3")
            self.assertEqual(app.review.moved_count(), 0)
            self.assertEqual(app.scope, "marked")
            self.assertTrue(app.is_running)
            self.assertIs(app.focused, app.query_one("#games"))  # Tab only left the field
            self.assertEqual(self.titles(app), [])
            self.assertIn("Showing: 0 of 2 games", self.text(app, "#status"))
            await pilot.press("x", "down", "tab")  # an empty list: nothing happens, nothing fails
            self.assertEqual(app.review.moved_count(), 0)

    async def test_filter_only_takes_effect_after_the_delay(self):
        app = self.app_for(self.FILTER_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("slash", *"two")
            self.assertEqual(self.titles(app), ["One", "Two"])
            self.assertIs(app.focused, app.query_one("#filter"))
            await pilot.pause(self.tui.FILTER_DELAY + 0.3)
            self.assertEqual(self.titles(app), ["Two"])
            self.assertIs(app.focused, app.query_one("#filter"))  # typing goes on in the field
            await pilot.press("down")
            self.assertIs(app.focused, app.query_one("#games"))

    async def test_filter_selects_a_shown_file_so_d_cannot_hit_a_hidden_one(self):
        app = self.app_for(self.FILTER_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertEqual(app.selected_keys(), ["g0f0"])  # a file of One
            await self.filter_for(app, pilot, *"two")
            self.assertEqual(app.selected_keys(), ["g1f0"])
            await pilot.press("x")
            one, two = app.review.results
            self.assertEqual(app.review._moved_count([one]), 0)
            self.assertEqual(app.review._moved_count([two]), 1)

    async def test_filter_stays_with_the_view_and_a_new_analysis(self):
        app = self.app_for(self.FILTER_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await self.filter_for(app, pilot, *"two")
            await pilot.press("3")
            self.assertEqual(self.titles(app), ["Two"])
            app.start_analysis()
            await self.analyzed(app, pilot)
            self.assertEqual(self.titles(app), ["Two"])
            self.assertEqual(self.text(app, "#status"), app.review.status(False, True, "two"))

    async def test_filter_field_is_labelled_in_the_language(self):
        translations.set_language("de")
        app = self.tui.WorkbenchApp(None, None)
        async with app.run_test() as pilot:
            self.assertEqual(self.text(app, "#filter-label"), "Dateinamen filtern:")
            await self.started(app, pilot)
            await pilot.press("escape", "slash", "x")  # leave the folder choice; then typing works, nothing fails
            await pilot.pause(self.tui.FILTER_DELAY + 0.3)
            self.assertEqual(app.query_one("#filter").value, "x")

    # Step 8: questions and messages -------------------------------------------------------------

    async def ask(self, app, pilot, **options):
        """Opens a question and returns the list its answer will be added to."""
        answers = []
        options.setdefault("then", answers.append)
        app.ask(options.pop("kind", "question"), "Title?", "Really?", **options)
        await pilot.pause()
        return answers

    def buttons(self, app):
        from textual.widgets import Button

        return [str(button.label) for button in app.screen.query(Button)]

    async def test_question_shows_title_text_and_buttons_with_no_preselected(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            answers = await self.ask(app, pilot)
            self.assertTrue(app.question_open())
            self.assertEqual(self.text(app.screen, "#question-title"), "Title?")
            self.assertEqual(self.text(app.screen, "#question-text"), "Really?")
            self.assertEqual(self.buttons(app), ["Yes", "No"])
            self.assertEqual(str(app.focused.label), "No")
            self.assertIn("kind-question", app.screen.classes)
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(answers, [False])
            self.assertFalse(app.question_open())
            self.assertIs(app.focused, app.query_one("#games"))  # back to the list

    async def test_question_is_answered_with_the_arrows_or_a_click(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            answers = await self.ask(app, pilot)
            await pilot.press("left")
            self.assertEqual(str(app.focused.label), "Yes")
            await pilot.press("enter")
            await pilot.pause()
            answers2 = await self.ask(app, pilot)
            await pilot.click("#answer-0")
            await pilot.pause()
            answers3 = await self.ask(app, pilot)
            await pilot.click("#answer-1")
            await pilot.pause()
            self.assertEqual(answers + answers2 + answers3, [True, True, False])

    async def test_question_buttons_follow_the_language(self):
        for language, expected in (("de", ["Ja", "Nein"]), ("it", ["Sì", "No"]), ("ja", ["はい", "いいえ"])):
            translations.set_language(language)
            app = self.tui.WorkbenchApp(None, None)
            async with app.run_test() as pilot:
                await self.started(app, pilot)
                await self.ask(app, pilot)
                self.assertEqual(self.buttons(app), expected, language)
                app.show_message("info", "i", "i")
                await pilot.pause()
                self.assertEqual(self.buttons(app), ["OK"], language)

    async def test_escape_and_ctrl_q_answer_no_and_the_program_stays(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            answers = await self.ask(app, pilot, default=True)
            self.assertEqual(str(app.focused.label), "Yes")
            await pilot.press("escape")
            await pilot.pause()
            await self.ask(app, pilot, default=True, then=answers.append)
            await pilot.press("ctrl+q")
            await pilot.pause()
            await self.ask(app, pilot, then=answers.append)
            await pilot.press("q")  # q is no answer
            await pilot.pause()
            self.assertTrue(app.question_open())
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(answers, [False, False, False])
            self.assertTrue(app.is_running)

    async def test_keys_of_the_list_do_nothing_while_a_question_is_open(self):
        app = self.app_for(self.VIEW_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            before = app.selected_keys()
            await self.ask(app, pilot)
            await pilot.press("x", "k", "down", "shift+down", "tab", "3", "slash", "s", "f")
            await pilot.pause(self.tui.FILTER_DELAY + 0.3)
            self.assertTrue(app.question_open())
            self.assertEqual(app.review.moved_count(), 0)
            self.assertEqual(app.selected_keys(), before)
            self.assertEqual(app.scope, "marked")
            self.assertEqual(app.query_one("#filter").value, "")
            self.assertIn(str(app.focused.label), ("Yes", "No"))  # Tab only moved between the buttons
            await pilot.click(offset=(10, 6))  # where the list is: the question covers it
            await pilot.pause()
            self.assertTrue(app.question_open())
            self.assertEqual(app.selected_keys(), before)

    async def test_messages_have_ok_and_their_color(self):
        app = self.tui.WorkbenchApp(None, None)
        async with app.run_test() as pilot:
            await self.started(app, pilot)
            answers = []
            app.show_message("warning", "Careful", "Something [!] happened", then=answers.append)
            await pilot.pause()
            self.assertIn("kind-warning", app.screen.classes)
            self.assertEqual(self.text(app.screen, "#question-text"), "Something [!] happened")
            dot = app.screen.query_one("#question-dot").styles.color
            self.assertEqual(dot.hex.lower(), "#e5383b")
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(answers, [None])
            app.show_message("info", "Done", "3 file(s) deleted.")
            await pilot.pause()
            self.assertEqual(app.screen.query_one("#question-dot").styles.color.hex.lower(), "#1a7f37")

    async def test_analysis_error_is_also_shown_as_a_message(self):
        def broken(_directory, _progress=None):
            raise ValueError("Configuration unreadable: broken")
        app = self.app_for({}, analyze=broken)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertTrue(app.question_open())
            self.assertEqual(self.text(app.screen, "#question-title"), "Analysis not possible")
            self.assertEqual(self.text(app.screen, "#question-text"), "Configuration unreadable: broken")
            await pilot.press("enter")
            await pilot.pause()
            self.assertFalse(app.question_open())

    async def test_quitting_after_changes_by_hand_asks_first(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("x", "q")
            await pilot.pause()
            self.assertTrue(app.question_open())
            self.assertEqual(self.text(app.screen, "#question-title"), "Discard changes?")
            await pilot.press("enter")  # No is preselected
            await pilot.pause()
            self.assertTrue(app.is_running)
            self.assertEqual(app.review.moved_count(), 1)
            await pilot.press("escape")  # Esc in the list also asks
            await pilot.pause()
            self.assertTrue(app.question_open())
            await pilot.press("left", "enter")
            await pilot.pause()
            self.assertFalse(app.is_running)
        self.assertEqual(len(list(app.directory.iterdir())), 4)  # nothing was deleted

    # Step 9: proceed ----------------------------------------------------------------------------

    def names(self, app):
        return sorted(path.name for path in app.directory.iterdir())

    def no_new_analysis(self, app):
        """After the first analysis: deleting must not read the folder again."""
        def fail(_directory, _progress=None):
            raise AssertionError("analyzed again")
        app.analyze = fail

    async def proceed(self, app, pilot, key="enter", answer="yes"):
        """Presses x (or Ctrl+L), answers the question and waits for the deletion and its message."""
        await pilot.press(key)
        await pilot.pause()
        self.assertTrue(app.question_open())
        await pilot.press(*(["left", "enter"] if answer == "yes" else ["enter"]))
        await app.workers.wait_for_complete()
        await pilot.pause()

    async def test_proceed_asks_with_the_confirm_message_and_no_deletes_nothing(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("enter")
            await pilot.pause()
            self.assertIn("kind-warning", app.screen.classes)
            self.assertEqual(self.text(app.screen, "#question-text"), app.review.confirm_message(False, False, ""))
            self.assertIn("Permanently delete 1 file(s)", self.text(app.screen, "#question-text"))
            self.assertEqual(str(app.focused.label), "No")
            await pilot.press("enter")
            await pilot.pause()
            self.assertFalse(app.question_open())
            self.assertEqual(self.names(app), ["Title (Japan).bin", "Title (USA).bin"])

    async def test_yes_deletes_reports_and_the_files_leave_the_list(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b",
                            "Gone (USA) (Hack).bin": b"c", "Stays (USA).bin": b"d"}, scope="all")
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.no_new_analysis(app)
            await self.proceed(app, pilot, key="enter")
            self.assertEqual(self.names(app), ["Stays (USA).bin", "Title (USA).bin"])
            self.assertTrue(app.question_open())
            self.assertEqual(self.text(app.screen, "#question-title"), "Deleted")
            self.assertEqual(self.text(app.screen, "#question-text"), "2 file(s) deleted.")
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual([entry.path.name for _result, entry in app.files.values()],
                             ["Stays (USA).bin", "Title (USA).bin"])
            self.assertEqual(self.titles(app), ["Stays", "Title"])  # Gone had no file left
            self.assertIn("To delete: 0 file(s)", self.text(app, "#status"))
            self.assertFalse(app.query_one("#progress").display)
            self.assertFalse(app.had_errors)
            self.assertIs(app.focused, app.query_one("#games"))

    async def test_changes_by_hand_are_carried_out_and_quitting_then_asks_nothing(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("down", "down", "k", "up", "x")  # keep Japan, then delete USA
            self.assertEqual(app.review.moved_count(), 2)
            await self.proceed(app, pilot)
            await pilot.press("enter")
            self.assertEqual(self.names(app), ["Title (Japan).bin"])
            self.assertEqual(app.review.moved_count(), 0)
            await pilot.press("q")
            await pilot.pause()
            self.assertFalse(app.is_running)

    async def test_progress_is_shown_while_deleting_and_the_list_is_locked(self):
        files = {}
        for game in ("Alpha", "Beta", "Gamma"):
            files[f"{game} (USA).bin"] = b"a"
            files[f"{game} (Japan).bin"] = b"b"
        app = self.app_for(files)
        seen = []
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            real_delete = app.review.delete

            def slow_delete(progress=None):
                def report(done, total):
                    progress(done, total)
                    seen.append((done, total))
                    time.sleep(0.1)  # time for the keys below
                return real_delete(report)
            app.review.delete = slow_delete
            await pilot.press("enter", "left", "enter")
            await pilot.pause(0.05)
            self.assertTrue(app.deleting)
            self.assertTrue(app.query_one("#progress").display)
            self.assertTrue(self.text(app, "#status").startswith("Deleting: "))
            self.assertTrue(app.query_one("#filter").disabled)
            self.assertTrue(app.query_one("#views").disabled)
            await pilot.press("x", "3", "slash", "enter", "q")
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertTrue(app.is_running)
            self.assertFalse(app.deleting)
            self.assertFalse(app.query_one("#progress").display)
            self.assertFalse(app.query_one("#filter").disabled)
            self.assertEqual(app.scope, "marked")
            self.assertEqual(app.review.moved_count(), 0)
            self.assertEqual(seen, [(0, 3), (1, 3), (2, 3), (3, 3)])
            self.assertEqual(self.text(app.screen, "#question-text"), "3 file(s) deleted.")
            self.assertEqual(len(list(app.directory.iterdir())), 3)

    async def test_failed_delete_is_reported_and_sets_the_exit_code(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            with mock.patch("pathlib.Path.unlink", side_effect=PermissionError("locked")):
                await self.proceed(app, pilot)
            self.assertIn("kind-warning", app.screen.classes)
            self.assertIn("locked", self.text(app.screen, "#question-text"))
            self.assertTrue(app.had_errors)
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(len(app.review.results[0].marked), 1)
            self.assertIn("To delete: 1 file(s)", self.text(app, "#status"))
        self.assertEqual(len(list(app.directory.iterdir())), 2)

    async def test_unexpected_error_while_deleting_unlocks_the_list(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            app.review.delete = mock.Mock(side_effect=RuntimeError("boom"))
            await self.proceed(app, pilot)
            self.assertIn("boom", self.text(app.screen, "#question-text"))
            self.assertFalse(app.deleting)
            self.assertFalse(app.query_one("#progress").display)
            self.assertTrue(app.had_errors)

    def test_run_tui_ends_with_exit_code_1_after_a_failed_delete(self):
        with mock.patch.object(self.tui.WorkbenchApp, "run",
                               lambda app: setattr(app, "had_errors", True)):
            self.assertEqual(self.tui.run_tui(None, None), 1)
        with mock.patch.object(self.tui.WorkbenchApp, "run", lambda app: None):
            self.assertEqual(self.tui.run_tui(None, None), 0)

    async def test_save_files_are_confirmed_after_deleting_and_stay_confirmed(self):
        import workbench_state

        app = self.app_for({"Title (USA).sfc": b"x" * 1000, "Title (Japan).sfc": b"x" * 1000,
                            "Title.srm": b"x" * 100, "Other (USA).sfc": b"x" * 1000, "Other.state": b"x" * 10},
                           scope="problems")
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await self.proceed(app, pilot)
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(self.names(app), ["Other (USA).sfc", "Other.state", "Title (USA).sfc", "Title.srm"])
            self.assertTrue(app.query_one("#nothing").display)
            self.assertEqual(workbench_state.load_confirmed_saves(app.settings_path), {
                rf.save_file_key(app.directory / "Title.srm"): 100,
                rf.save_file_key(app.directory / "Other.state"): 10,
            })
        again = self.tui.WorkbenchApp(app.analyze, app.directory, "problems", settings_path=app.settings_path)
        async with again.run_test() as pilot:
            await self.analyzed(again, pilot)
            self.assertTrue(again.query_one("#nothing").display)

    async def test_failed_remembering_is_reported_and_deletes_as_usual(self):
        app = self.app_for({"Title (USA).sfc": b"x" * 1000, "Title (Japan).sfc": b"x" * 1000,
                            "Title.srm": b"x" * 100})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            with mock.patch("workbench_state.add_confirmed_saves", side_effect=PermissionError("locked")):
                await self.proceed(app, pilot)
            self.assertEqual(self.text(app.screen, "#question-title"), translations.tr("window.saves_not_remembered"))
            self.assertIn("locked", self.text(app.screen, "#question-text"))
            await pilot.press("enter")  # then the result
            await pilot.pause()
            self.assertEqual(self.text(app.screen, "#question-text"), "1 file(s) deleted.")
            self.assertFalse((app.directory / "Title (Japan).sfc").exists())

    async def test_without_marked_files_proceed_offers_to_confirm_save_files(self):
        app = self.app_for({"Title (USA).sfc": b"x" * 1000, "Title.srm": b"x" * 100}, scope="problems")
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("enter")
            await pilot.pause()
            self.assertIn("Confirm 1 suspected status or save file(s)", self.text(app.screen, "#question-text"))
            await pilot.press("enter")  # No
            await pilot.pause()
            self.assertEqual(self.titles(app), ["Title"])
            await pilot.press("enter", "left", "enter")
            await pilot.pause()
            self.assertTrue(app.query_one("#nothing").display)
            self.assertEqual(len(list(app.directory.iterdir())), 2)

    async def test_nothing_to_delete_is_a_message_and_deletes_nothing(self):
        app = self.app_for({"Alpha (USA).bin": b"a"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(self.text(app.screen, "#question-title"), "Nothing to delete")
            self.assertEqual(self.buttons(app), ["OK"])
            await pilot.press("enter")
            await pilot.pause()
        self.assertEqual(len(list(app.directory.iterdir())), 1)

    async def test_filter_stays_after_deleting_and_the_message_names_hidden_files(self):
        app = self.app_for(self.FILTER_GAMES, scope="all")
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await self.filter_for(app, pilot, *"two")
            await pilot.press("enter")
            await pilot.pause()
            self.assertIn("Not shown: 1 file(s)", self.text(app.screen, "#question-text"))
            await pilot.press("left", "enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(app.query_one("#filter").value, "two")
            self.assertEqual(self.titles(app), ["Two"])
            self.assertEqual(self.names(app), ["One (USA).bin", "Two (USA).bin"])

    # Step 10: folder choice --------------------------------------------------------------------

    def other_folder(self, files=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name) / "other"
        folder.mkdir()
        for name, content in (files or {"Another (USA).bin": b"x", "Another (Japan).bin": b"y"}).items():
            (folder / name).write_bytes(content)
        return folder

    async def open_folder_choice(self, app, pilot, key="f"):
        await pilot.press(key)
        await pilot.pause()
        await pilot.pause()
        self.assertTrue(app.folder_open())
        return app.screen.query_one("#folder-tree"), app.screen.query_one("#folder-path")

    @staticmethod
    def same_folder(first, second):
        return os.path.normcase(os.path.abspath(first)) == os.path.normcase(os.path.abspath(second))

    async def test_folder_choice_opens_at_the_current_folder_with_its_subfolders(self):
        app = self.app_for(self.TWO_GAMES)
        for name in ("Sub B", "sub a", ".hidden"):
            (app.directory / name).mkdir()
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            tree, path = await self.open_folder_choice(app, pilot, key="f")
            self.assertTrue(self.same_folder(path.value, app.directory))
            node = tree.cursor_node
            self.assertTrue(self.same_folder(node.data["path"], app.directory))
            self.assertTrue(node.is_expanded)
            self.assertEqual([str(child.label) for child in node.children], ["sub a", "Sub B"])
            self.assertIs(app.focused, tree)
            self.assertEqual(self.text(app.screen, "#folder-title"), "Choose folder")
            roots = [child.data["path"] for child in tree.root.children]
            self.assertTrue(any(self.same_folder(root, Path.home()) for root in roots))
            self.assertTrue(any(root == Path(root.anchor) for root in roots))  # a drive, or / on Linux

    async def test_folder_is_chosen_in_the_tree_and_analyzed(self):
        app = self.app_for(self.TWO_GAMES)
        (app.directory / "More").mkdir()
        (app.directory / "More" / "Other (USA).bin").write_bytes(b"a")
        (app.directory / "More" / "Other (Japan).bin").write_bytes(b"b")
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            tree, path = await self.open_folder_choice(app, pilot)
            await pilot.press("right")  # to the first subfolder
            await pilot.pause()
            self.assertEqual(str(tree.cursor_node.label), "More")
            self.assertTrue(path.value.endswith("More"))
            more = app.directory / "More"
            await pilot.press("enter")
            await self.analyzed(app, pilot)
            self.assertFalse(app.folder_open())
            self.assertTrue(self.same_folder(app.directory, more))
            self.assertEqual(self.titles(app), ["Other"])
            self.assertIn("More", self.text(app, "#folder"))
            self.assertIs(app.focused, app.query_one("#games"))

    async def test_double_click_chooses_the_folder(self):
        app = self.app_for(self.TWO_GAMES)
        (app.directory / "More").mkdir()
        (app.directory / "More" / "Other (USA).bin").write_bytes(b"a")
        (app.directory / "More" / "Other (Japan).bin").write_bytes(b"b")
        more_folder = app.directory / "More"
        async with app.run_test(size=(100, 30)) as pilot:
            await self.analyzed(app, pilot)
            tree, path = await self.open_folder_choice(app, pilot)
            await pilot.press("right")  # the cursor on More
            await pilot.pause()
            more = tree.cursor_node
            self.assertEqual(str(more.label), "More")
            row = more.line - tree.scroll_offset.y
            await pilot.click(tree, offset=(12, row), times=2)
            await self.analyzed(app, pilot)
            self.assertFalse(app.folder_open())
            self.assertTrue(self.same_folder(app.directory, more_folder))
            self.assertEqual(self.titles(app), ["Other"])

    async def test_single_click_only_highlights_the_folder(self):
        app = self.app_for(self.TWO_GAMES)
        (app.directory / "More").mkdir()
        async with app.run_test(size=(100, 30)) as pilot:
            await self.analyzed(app, pilot)
            tree, path = await self.open_folder_choice(app, pilot)
            await pilot.press("right")
            await pilot.pause()
            row = tree.cursor_node.line - tree.scroll_offset.y
            await pilot.click(tree, offset=(12, row))
            await pilot.pause()
            self.assertTrue(app.folder_open())

    async def test_typed_path_is_taken_and_a_missing_one_is_refused(self):
        app = self.app_for(self.TWO_GAMES)
        other = self.other_folder()
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            _tree, path = await self.open_folder_choice(app, pilot)
            path.value = str(other / "missing")
            await pilot.click("#folder-select")
            await pilot.pause()
            self.assertTrue(app.question_open())
            self.assertIn("missing", self.text(app.screen, "#question-text"))
            self.assertIn("kind-error", app.screen.classes)
            await pilot.press("enter")
            await pilot.pause()
            self.assertTrue(app.folder_open())  # the choice stays open
            self.assertEqual(self.titles(app), ["A", "B"])
            path.value = f'"{other}"'  # pasted with quotes, as a file manager copies a path
            path.focus()
            await pilot.press("enter")
            await self.analyzed(app, pilot)
            self.assertFalse(app.folder_open())
            self.assertEqual(app.directory, other)
            self.assertEqual(self.titles(app), ["Another"])

    async def test_cancel_and_escape_change_nothing(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            folder, before = app.directory, app.review
            self.no_new_analysis(app)
            await self.open_folder_choice(app, pilot)
            await pilot.click("#folder-cancel")
            await pilot.pause()
            self.assertFalse(app.folder_open())
            await self.open_folder_choice(app, pilot)
            await pilot.press("escape")
            await pilot.pause()
            self.assertFalse(app.folder_open())
            self.assertTrue(app.is_running)
            self.assertEqual(app.directory, folder)
            self.assertIs(app.review, before)
            self.assertEqual(self.titles(app), ["A", "B"])
            self.assertIs(app.focused, app.query_one("#games"))

    async def test_keys_of_the_list_do_nothing_while_choosing_a_folder(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await self.open_folder_choice(app, pilot)
            await pilot.press("x", "k", "3", "slash", "f", "s", "tab")
            await pilot.pause()
            self.assertTrue(app.folder_open())
            self.assertFalse(app.question_open())
            self.assertEqual(app.review.moved_count(), 0)
            self.assertEqual(app.scope, "marked")
            self.assertEqual(app.query_one("#filter").value, "")
            self.assertEqual(len(app.screen_stack), 2)  # o did not open a second choice
        self.assertEqual(len(list(app.directory.iterdir())), 4)

    async def test_changes_by_hand_ask_before_choosing_another_folder(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("x", "f")
            await pilot.pause()
            self.assertTrue(app.question_open())
            self.assertIn("Choose another folder?", self.text(app.screen, "#question-text"))
            await pilot.press("enter")  # No
            await pilot.pause()
            self.assertFalse(app.folder_open())
            self.assertEqual(app.review.moved_count(), 1)
            await pilot.press("f", "left", "enter")  # Yes
            await pilot.pause()
            await pilot.pause()
            self.assertTrue(app.folder_open())

    async def test_without_a_folder_the_choice_opens_at_the_start(self):
        other = self.other_folder()
        config = rules_config()
        app = self.tui.WorkbenchApp(lambda directory, progress=None: rf.Review(
            rf.scan_directory(directory, config, progress), config), None, "marked",
            settings_path=other.with_name("settings.json"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            self.assertTrue(app.folder_open())
            self.assertTrue(self.same_folder(app.screen.query_one("#folder-path").value, Path.home()))
            app.screen.query_one("#folder-path").value = str(other)
            app.screen.query_one("#folder-path").focus()
            await pilot.press("enter")
            await self.analyzed(app, pilot)
            self.assertEqual(self.titles(app), ["Another"])
            self.assertIn(str(other), self.text(app, "#folder"))

    async def test_folder_can_be_changed_during_analysis(self):
        other = self.other_folder()
        release = threading.Event()
        config = rules_config()
        seen = []

        def analyze(directory, progress=None):
            seen.append(directory)
            if directory != other:
                release.wait(10)  # the first folder hangs, as a large ZIP would
            return rf.Review(rf.scan_directory(directory, config), config)
        app = self.app_for(self.TWO_GAMES, analyze=analyze)
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIsNone(app.review)  # still analyzing
            _tree, path = await self.open_folder_choice(app, pilot)
            path.value = str(other)
            path.focus()
            await pilot.press("enter")
            await pilot.pause(0.3)
            self.assertEqual(self.titles(app), ["Another"])
            release.set()
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(self.titles(app), ["Another"])  # the old result came too late
            self.assertEqual(seen[1], other)
            self.assertNotEqual(seen[0], other)

    async def test_folders_are_read_only_when_opened_and_left_closes_them(self):
        app = self.app_for(self.TWO_GAMES)
        (app.directory / "Outer").mkdir()
        (app.directory / "Outer" / "Inner").mkdir()
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            tree, _path = await self.open_folder_choice(app, pilot)
            await pilot.press("right")
            await pilot.pause()
            outer = tree.cursor_node
            self.assertEqual(str(outer.label), "Outer")
            self.assertFalse(outer.data["loaded"])
            self.assertEqual(list(outer.children), [])
            await pilot.press("right")  # opens it
            await pilot.pause()
            self.assertTrue(outer.data["loaded"])
            self.assertEqual([str(child.label) for child in outer.children], ["Inner"])
            await pilot.press("right")  # into it
            await pilot.pause()
            inner = tree.cursor_node
            self.assertEqual(str(inner.label), "Inner")
            await pilot.press("right")  # has no subfolders: the arrow disappears
            await pilot.pause()
            self.assertFalse(inner.allow_expand)
            await pilot.press("left")  # to the parent
            await pilot.pause()
            self.assertIs(tree.cursor_node, outer)
            await pilot.press("left")  # closes it
            await pilot.pause()
            self.assertFalse(outer.is_expanded)

    async def test_folder_choice_speaks_the_language(self):
        translations.set_language("de")
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await self.open_folder_choice(app, pilot)
            from textual.widgets import Button
            self.assertEqual(self.text(app.screen, "#folder-title"), "Ordner wählen")
            self.assertEqual([str(button.label) for button in app.screen.query(Button)], ["Auswählen", "Abbrechen"])
            self.assertEqual(self.text(app.screen, "#folder-path-label"), "Pfad:")
            self.assertTrue(self.text(app.screen, "#folder-hint").startswith("Rechts oder Leertaste"))

    # Keys typed faster than the screen changes -------------------------------------------------

    _CHARACTERS = {"slash": "/", "enter": "\r", "escape": "\x1b", "space": " ", "left": None, "right": None,
                   "down": None, "up": None, "tab": "\t"}

    async def burst(self, app, pilot, *keys):
        """Sends the keys at once, as tmux, a paste or a fast typist does; Pilot's press waits after each one."""
        from textual import events

        for key in keys:
            app.post_message(events.Key(key, self._CHARACTERS.get(key, key)))
        await pilot.pause(0.3)
        await pilot.pause()

    async def test_letters_typed_right_after_slash_go_into_the_filter(self):
        app = self.app_for(self.FILTER_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await self.burst(app, pilot, "slash", *"xkf", "s")
            self.assertEqual(app.query_one("#filter").value, "xkfs")
            self.assertEqual(app.review.moved_count(), 0)
            self.assertFalse(app.question_open())
            self.assertFalse(app.folder_open())
            await self.burst(app, pilot, "escape", "x")  # back in the list at once: the x acts there
            self.assertEqual(app.query_one("#filter").value, "")
            self.assertEqual(app.review.moved_count(), 1)

    async def test_filter_typed_ahead_then_enter_and_d_act_in_order(self):
        app = self.app_for(self.FILTER_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await self.burst(app, pilot, "slash", *"two", "enter", "x")
            self.assertEqual(self.titles(app), ["Two"])
            one, two = app.review.results
            self.assertEqual(app.review._moved_count([one]), 0)
            self.assertEqual(app.review._moved_count([two]), 1)

    async def test_tab_and_slash_typed_ahead_act_in_order(self):
        app = self.app_for(self.FILTER_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await self.burst(app, pilot, "slash", *"two", "tab", "x")
            self.assertEqual(self.titles(app), ["Two"])
            one, two = app.review.results
            self.assertEqual(app.review._moved_count([one]), 0)
            self.assertEqual(app.review._moved_count([two]), 1)  # the d after Tab acted in the list
            self.assertEqual(app.query_one("#filter").value, "two")
            # The first "/" arrives at the field after a Tab has left it: it must come back into it,
            # select "two", and the second "/" replaces that.
            await self.burst(app, pilot, "slash", "tab", "slash", "slash")
            self.assertEqual(app.query_one("#filter").value, "/")
            self.assertIs(app.focused, app.query_one("#filter"))

    async def test_answer_typed_ahead_reaches_the_question(self):
        app = self.app_for({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await self.burst(app, pilot, "enter", "left", "enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(self.names(app), ["Title (USA).bin"])  # Yes was chosen
            await self.burst(app, pilot, "enter", "x")  # OK, then the list again
            self.assertFalse(app.question_open())

    async def test_keys_typed_ahead_after_o_stay_in_the_folder_choice(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await self.burst(app, pilot, "f", "x", "k", "s")
            self.assertTrue(app.folder_open())
            self.assertFalse(app.question_open())
            self.assertEqual(app.review.moved_count(), 0)
            await self.burst(app, pilot, "escape", "x")
            self.assertFalse(app.folder_open())
            self.assertEqual(app.review.moved_count(), 1)

    # Step 11: settings -------------------------------------------------------------------------

    def app_with_settings(self, content='{"language": "en", "region_priority": ["USA", "Japan"]}'):
        """An app with a configuration file, which the analysis reads again each time, as main does."""
        folder = self.demo_folder({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        path = folder.with_name("redundanz_config.json")
        path.write_text(content, encoding="utf-8")

        def analyze(directory, progress=None):
            config = rf.Config.load(path)
            return rf.Review(rf.scan_directory(directory, config, progress), config, str(path))
        return self.tui.WorkbenchApp(analyze, folder, "marked", rf.ConfigFile(path),
                                     settings_path=folder.with_name("settings.json"))

    async def open_settings(self, app, pilot, key="s"):
        await pilot.press(key)
        await pilot.pause()
        await pilot.pause()
        self.assertTrue(app.settings_open())
        return app.screen

    def region_texts(self, screen):
        listing = screen.query_one("#regions")
        return [str(listing.get_option_at_index(index).prompt) for index in range(listing.option_count)]

    async def test_settings_show_and_change_the_delete_keywords(self):
        app = self.app_with_settings(
            '{"language": "en", "region_priority": ["USA", "Japan", "none", "Beta"], "delete_tags": ["Hack"]}')
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            before = app.review
            screen = await self.open_settings(app, pilot)
            self.assertEqual(self.text(screen, "#tags-label"),
                             "Delete keywords (separated by commas; marked for deletion):")
            self.assertEqual(self.text(screen, "#regions-label"),
                             "Priority (best first; extra info such as Beta after none):")  # may wrap on screen
            self.assertEqual(screen.tag_list(), ["Hack"])
            screen.query_one("#tags").value = "Hack, Hacks"
            await pilot.press("ctrl+s")
            await self.analyzed(app, pilot)
            self.assertFalse(app.settings_open())
            self.assertIsNot(app.review, before)  # a new delete keyword analyzes again
            self.assertEqual(rf.Config.load(app.config_file.path).delete_tags, ["Hack", "Hacks"])

    async def test_settings_switch_between_plain_file_and_zip_file(self):
        app = self.app_with_settings()
        async with app.run_test(size=(110, 40)) as pilot:
            await self.analyzed(app, pilot)
            before = app.review
            screen = await self.open_settings(app, pilot)
            self.assertEqual(self.text(screen, "#prefer-label"), "Same game as a plain file and as a ZIP file:")
            self.assertTrue(screen.query_one("#prefer-false").value)
            self.assertFalse(screen.prefers_zip())
            screen.query_one("#prefer-true").value = True
            await pilot.pause()
            self.assertTrue(screen.prefers_zip())
            self.assertEqual(screen.language_code(), "en")  # the other radio set leaves the language alone
            await pilot.press("ctrl+s")
            await self.analyzed(app, pilot)
            self.assertFalse(app.settings_open())
            self.assertIsNot(app.review, before)
            self.assertTrue(rf.Config.load(app.config_file.path).prefer_zip)

    async def test_settings_of_an_old_file_show_its_low_priority_tags_and_saving_drops_them(self):
        app = self.app_with_settings('{"language": "en", "region_priority": ["Germany", "USA", "none", "Japan"], '
                                     '"delete_tags": [], "low_priority_tags": ["Beta", "Proto"]}')
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            screen = await self.open_settings(app, pilot)
            self.assertEqual(screen.region_list(), ["Germany", "USA", "none", "Japan", "Beta", "Proto"])
            self.assertEqual(self.region_texts(screen), ["Germany", "USA", "none", "Japan", "Beta", "Proto"])
            self.assertEqual(screen.tag_list(), [])  # the file's own empty list stays
            screen.query_one("#tags").value = "Hack, Hacks"
            await pilot.press("ctrl+s")
            await self.analyzed(app, pilot)
            text = app.config_file.path.read_text(encoding="utf-8")
            self.assertNotIn("low_priority_tags", text)
            loaded = rf.Config.load(app.config_file.path)
            self.assertEqual(loaded.region_priority, ["Germany", "USA", "none", "Japan", "Beta", "Proto"])
            self.assertEqual(loaded.delete_tags, ["Hack", "Hacks"])

    async def test_without_a_configuration_file_e_does_nothing(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("s", "s")
            await pilot.pause()
            self.assertFalse(app.settings_open())
            self.assertFalse(app.question_open())

    async def test_settings_show_the_current_values(self):
        app = self.app_with_settings()
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            screen = await self.open_settings(app, pilot, key="s")
            self.assertEqual(self.text(screen, "#settings-title"), "Settings")
            self.assertIn("redundanz_config.json", self.text(screen, "#settings-file"))
            self.assertTrue(screen.query_one("#language-en").value)
            self.assertEqual(screen.language_code(), "en")
            self.assertEqual(screen.region_list(), ["USA", "Japan"])
            self.assertEqual(self.region_texts(screen), ["USA", "Japan"])
            self.assertEqual(screen.tag_list(), rf.DEFAULT_CONFIG["delete_tags"])
            self.assertIs(app.focused, screen.query_one("#new-region"))  # as in the window
            await pilot.press("s")  # typed into the field; no second settings screen
            self.assertEqual(screen.query_one("#new-region").value, "s")
            self.assertEqual(len(app.screen_stack), 2)

    async def test_regions_are_moved_added_and_removed(self):
        app = self.app_with_settings()
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            screen = await self.open_settings(app, pilot)
            listing = screen.query_one("#regions")
            listing.highlighted = 1
            screen.set_focus(listing)
            await pilot.press("shift+up")
            self.assertEqual(screen.region_list(), ["Japan", "USA"])
            self.assertEqual(listing.highlighted, 0)
            await pilot.press("shift+up")  # already at the top: nothing changes
            self.assertEqual(screen.region_list(), ["Japan", "USA"])
            await pilot.click("#region-down")  # the buttons do the same
            await pilot.pause()
            self.assertEqual(screen.region_list(), ["USA", "Japan"])
            await pilot.click("#region-up")
            await pilot.pause()
            field = screen.query_one("#new-region")
            screen.set_focus(field)
            field.value = " Germany "
            await pilot.press("enter")
            field.value = "usa"
            await pilot.press("enter")  # already there: highlighted instead of added twice
            self.assertEqual(screen.region_list(), ["Japan", "USA", "Germany"])
            self.assertEqual(self.region_texts(screen), ["Japan", "USA", "Germany"])
            self.assertEqual(listing.highlighted, 1)
            self.assertEqual(field.value, "")
            screen.set_focus(listing)
            await pilot.press("delete")
            self.assertEqual(screen.region_list(), ["Japan", "Germany"])
            field.value = "Europe [!]"
            await pilot.click("#region-add")
            await pilot.pause()
            self.assertEqual(self.region_texts(screen)[-1], "Europe [!]")  # brackets stay literal
            await pilot.click("#region-remove")
            await pilot.pause()
            self.assertEqual(screen.region_list(), ["Japan", "Germany"])

    async def test_saving_writes_the_file_and_analyzes_again(self):
        app = self.app_with_settings()
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            self.assertEqual(self.text(app, "#status"), app.review.status(False, False, ""))
            before = app.review
            screen = await self.open_settings(app, pilot)
            listing = screen.query_one("#regions")
            listing.highlighted = 1
            screen.set_focus(listing)
            await pilot.press("shift+up")
            screen.query_one("#tags").value = "Beta, Proto"
            await pilot.press("ctrl+s")
            await self.analyzed(app, pilot)
            self.assertFalse(app.settings_open())
            self.assertFalse(app.question_open())  # the language stayed the same: no message
            values = app.config_file.read()
            self.assertEqual(values["region_priority"], ["Japan", "USA"])
            self.assertEqual(values["delete_tags"], ["Beta", "Proto"])
            self.assertIsNot(app.review, before)  # analyzed again with the new rules
            self.assertIn("Priority: Japan > USA", self.text(app, "#info"))
            self.assertIn("+ Title (Japan).bin", self.row_texts(app))
            self.assertIs(app.focused, app.query_one("#games"))

    async def test_new_language_is_announced_for_the_next_start(self):
        app = self.app_with_settings()
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            before = app.review
            await self.open_settings(app, pilot)
            await pilot.click("#language-it")
            await pilot.pause()
            await pilot.click("#settings-save")
            await pilot.pause()
            self.assertEqual(app.config_file.read()["language"], "it")
            self.assertTrue(app.question_open())
            self.assertEqual(self.text(app.screen, "#question-title"), "Language changed")
            self.assertIn("next start", self.text(app.screen, "#question-text"))
            await pilot.press("enter")
            await pilot.pause()
            self.assertIs(app.review, before)  # priority and tags are unchanged: nothing to analyze again
            self.assertEqual(translations.current_language(), "en")  # the open program keeps its language

    async def test_saving_asks_before_dropping_changes_by_hand(self):
        app = self.app_with_settings()
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("x")
            original = app.config_file.path.read_text(encoding="utf-8")
            screen = await self.open_settings(app, pilot)
            screen.query_one("#regions").highlighted = 1
            screen.set_focus(screen.query_one("#regions"))
            await pilot.press("shift+up", "ctrl+s")
            await pilot.pause()
            self.assertTrue(app.question_open())
            self.assertIn("Save the settings and analyze again?", self.text(app.screen, "#question-text"))
            await pilot.press("enter")  # No
            await pilot.pause()
            self.assertEqual(app.config_file.path.read_text(encoding="utf-8"), original)
            self.assertTrue(app.settings_open())
            self.assertEqual(app.review.moved_count(), 1)
            await pilot.press("ctrl+s")
            await pilot.pause()
            await pilot.press("left", "enter")  # Yes
            await self.analyzed(app, pilot)
            self.assertFalse(app.settings_open())
            self.assertEqual(app.config_file.read()["region_priority"], ["Japan", "USA"])
            self.assertEqual(app.review.moved_count(), 0)

    async def test_wrong_settings_are_reported_and_the_settings_stay_open(self):
        app = self.app_with_settings()
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            original = app.config_file.path.read_text(encoding="utf-8")
            screen = await self.open_settings(app, pilot)
            screen.set_focus(screen.query_one("#regions"))
            await pilot.press("delete", "delete")
            self.assertEqual(screen.region_list(), [])
            await pilot.press("ctrl+s")
            await pilot.pause()
            self.assertIn("kind-error", app.screen.classes)
            self.assertEqual(self.text(app.screen, "#question-title"), "Settings not saved")
            self.assertIn("at least one region", self.text(app.screen, "#question-text"))
            await pilot.press("enter")
            await pilot.pause()
            self.assertIs(app.screen, screen)
            screen.query_one("#new-region").value = "USA"
            screen.add_region()
            screen.query_one("#tags").value = "Beta, beta"
            await pilot.press("ctrl+s")
            await pilot.pause()
            self.assertIn('"beta" appears more than once', self.text(app.screen, "#question-text"))
            await pilot.press("escape")  # OK
            await pilot.pause()
            self.assertIs(app.screen, screen)
            self.assertEqual(app.config_file.path.read_text(encoding="utf-8"), original)

    async def test_broken_configuration_is_not_opened_for_editing(self):
        app = self.app_with_settings("{not json")
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)  # the analysis reports it too
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("s")
            await pilot.pause()
            self.assertFalse(app.settings_open())
            self.assertTrue(app.question_open())
            self.assertEqual(self.text(app.screen, "#question-title"), "Settings not saved")
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(app.config_file.path.read_text(encoding="utf-8"), "{not json")

    async def test_list_is_locked_while_the_settings_are_open(self):
        app = self.app_with_settings()
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            screen = await self.open_settings(app, pilot)
            screen.set_focus(screen.query_one("#regions"))
            await pilot.press("x", "k", "f", "s", "3", "slash", "r")
            await pilot.pause()
            self.assertIs(app.screen, screen)
            self.assertEqual(app.review.moved_count(), 0)
            self.assertEqual(app.scope, "marked")
            self.assertEqual(app.query_one("#filter").value, "")
            self.assertEqual(len(app.screen_stack), 2)
            await pilot.press("tab")  # Tab moves between the fields
            self.assertIsNot(app.focused, screen.query_one("#regions"))
            self.assertIs(app.focused.screen, screen)
            screen.set_focus(screen.query_one("#tags"))
            await self.burst(app, pilot, *"xkf")  # typed into the field, also when fast
            self.assertTrue(screen.query_one("#tags").value.endswith("xkf"))
            self.assertEqual(app.review.moved_count(), 0)
        self.assertEqual(len(list(app.directory.iterdir())), 2)

    async def test_escape_and_ctrl_e_close_only_the_settings(self):
        app = self.app_with_settings()
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            original = app.config_file.path.read_text(encoding="utf-8")
            screen = await self.open_settings(app, pilot)
            screen.query_one("#tags").value = "Changed"
            await pilot.press("escape")
            await pilot.pause()
            self.assertFalse(app.settings_open())
            self.assertTrue(app.is_running)
            self.assertIs(app.focused, app.query_one("#games"))
            await self.open_settings(app, pilot)
            self.assertNotEqual(app.screen.query_one("#tags").value, "Changed")  # nothing was kept
            await pilot.press("ctrl+e")
            await pilot.pause()
            self.assertFalse(app.settings_open())
            await self.open_settings(app, pilot)
            await pilot.click("#settings-cancel")
            await pilot.pause()
            self.assertFalse(app.settings_open())
            self.assertEqual(app.config_file.path.read_text(encoding="utf-8"), original)

    async def test_settings_speak_the_language(self):
        translations.set_language("de")
        app = self.app_with_settings('{"language": "de", "region_priority": ["USA", "Japan"]}')
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            screen = await self.open_settings(app, pilot)
            from textual.widgets import Button, RadioButton
            self.assertEqual(self.text(screen, "#settings-title"), "Einstellungen")
            self.assertEqual([str(button.label) for button in screen.query(Button)],
                             ["Speichern", "Abbrechen", "Hoch", "Runter", "Entfernen", "Hinzufügen"])
            self.assertEqual([str(button.label) for button in screen.query(RadioButton)],
                             ["English", "Deutsch", "Italiano", "Español", "Français", "日本語",
                              "Normale Datei behalten", "ZIP-Datei behalten"])
            self.assertEqual(self.text(screen, "#prefer-label"),
                             "Gleiches Spiel als normale Datei und als ZIP-Datei:")
            self.assertTrue(screen.query_one("#language-de").value)
            self.assertTrue(self.text(screen, "#settings-hint").startswith("Umschalt+Hoch/Runter"))

    # Step 12: colors and fallbacks --------------------------------------------------------------

    @staticmethod
    def strips(app):
        """The rows Textual would draw on the terminal now, with their styles."""
        return app.screen._compositor.render_strips()

    def screen_lines(self, app):
        return [strip.text for strip in self.strips(app)]

    async def visit_every_screen(self, app, pilot, check):
        """Calls check(name) on the list, a question, the folder choice and the settings."""
        await self.analyzed(app, pilot)
        await pilot.press("shift+down", "down", "x")  # a moved row and a selection
        check("list")
        app.show_message("warning", "Careful", "Something happened")
        await pilot.pause()
        check("question")
        await pilot.press("enter")
        await pilot.pause()
        await self.open_folder_choice(app, pilot)
        check("folder choice")
        await pilot.press("escape")
        await pilot.pause()
        await self.open_settings(app, pilot)
        check("settings")
        await pilot.press("escape")
        await pilot.pause()

    def colored_app(self, **options):
        # Without NO_COLOR: Textual would put a gray filter over everything (this shell sets it).
        with mock.patch.dict(os.environ):
            os.environ.pop("NO_COLOR", None)
            app = self.app_with_settings()
        app.ascii, app.colors16 = options.get("ascii", False), options.get("colors16", False)
        (app.directory / "Other (USA).bin").write_bytes(b"c")
        (app.directory / "Other (Japan).bin").write_bytes(b"d")
        return app

    async def test_games_are_not_striped_the_background_stays_black(self):
        # Unlike the window: the user prefers black behind every game.
        with mock.patch.dict(os.environ):
            os.environ.pop("NO_COLOR", None)  # else Textual draws everything gray
            app = self.app_for(self.VIEW_GAMES, scope="all")
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("tab", "x")  # a selected and moved row in the second game
            table = app.query_one("#games")
            from rich.style import Style

            def background(key):
                color = table._get_row_style(table.get_row_index(key), Style()).bgcolor
                return color.name if color else None
            moved = {key for key in app.files if app.files[key][1].moved}
            plain = [key for key in app._keys() if key not in table.selected and key not in moved]
            self.assertEqual({background(key) for key in plain}, {None})  # the table's own black
            self.assertEqual(background(app.cursor_key()), "#0a4a8a")
            table.set_selection(())
            self.assertEqual({background(key) for key in moved}, {"#5c4400"})
            lines = self.screen_lines(app)
            strips = self.strips(app)
            row = next(index for index, line in enumerate(lines) if "Other" in line)
            self.assertEqual({segment.style.bgcolor.name for segment in strips[row] if segment.style.bgcolor},
                             {"#000000"})

    @staticmethod
    def as_16_colors(color):
        """The ANSI color number a 16-color terminal gets for this color, as Rich converts it."""
        from rich.color import ColorSystem, ColorType

        if color is None or color.type == ColorType.DEFAULT:
            return None
        return color.downgrade(ColorSystem.STANDARD).number

    async def test_16_colors_are_exact_and_backgrounds_fit_the_console(self):
        from rich._palettes import STANDARD_PALETTE

        standard = {f"#{r:02x}{g:02x}{b:02x}" for r, g, b in STANDARD_PALETTE._colors[:16]}
        app = self.colored_app(colors16=True)
        async with app.run_test(size=(110, 32)) as pilot:
            def check(name):
                between, bright_backgrounds = set(), set()
                for strip in self.strips(app):
                    for segment in strip:
                        style = segment.style
                        for where, color in (("fg", style.color), ("bg", style.bgcolor)) if style else ():
                            if color is None or self.as_16_colors(color) is None:
                                continue
                            if color.get_truecolor().hex not in standard:  # would be rounded: not ours
                                between.add((where, color.get_truecolor().hex, segment.text.strip()[:15]))
                            if where == "bg" and self.as_16_colors(color) > 7:
                                bright_backgrounds.add((color.get_truecolor().hex, segment.text.strip()[:15]))
                self.assertEqual(between, set(), name)
                self.assertEqual(bright_backgrounds, set(), name)  # the Linux console has 8 of them
            await self.visit_every_screen(app, pilot, check)
            self.assertTrue(app.has_class("-colors16"))

    async def test_16_colors_keep_selection_moved_rows_and_title_apart(self):
        app = self.colored_app(colors16=True)
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("x", "down")  # the first file moved by hand, the cursor one below
            lines = self.screen_lines(app)
            strips = self.strips(app)

            def background_of(text):
                row = next(index for index, line in enumerate(lines) if text in line)
                segment = next(segment for segment in strips[row] if text[:4] in segment.text)
                return self.as_16_colors(segment.style.bgcolor)

            moved = app.files[next(key for key in app.files if app.files[key][1].moved)][1].path.name
            cursor = str(app.query_one("#games").get_row(app.cursor_key())[0]).strip()
            # ANSI 2 green, 3 brown (yellow), 4 blue: three different colors, as in the window.
            self.assertEqual(background_of("Rom Cleanup Workbench"), 2)
            self.assertEqual(background_of("Showing:"), 2)
            self.assertEqual(background_of(moved), 3)
            # ANSI 3 is yellow in PuTTY: the text on it must be black, also the note and the size.
            row = next(index for index, line in enumerate(lines) if moved in line)
            colors = {self.as_16_colors(segment.style.color) for segment in strips[row] if segment.text.strip()}
            self.assertEqual(colors, {0})
            self.assertEqual(background_of(cursor), 4)
            self.assertIn(background_of("Filter"), (0, None))  # the label; the field itself is light gray

    async def test_kept_files_are_green_and_marked_files_red(self):
        for colors16, green, red in ((False, "#3fb950", "#ff6b6b"), (True, "#00aa00", "#ff5555")):
            app = self.colored_app(colors16=colors16)
            async with app.run_test(size=(110, 32)) as pilot:
                await self.analyzed(app, pilot)
                table = app.query_one("#games")
                for key, (result, entry) in app.files.items():
                    cell = table.get_row(key)[0]
                    wanted = green if entry in result.keep else red
                    self.assertIn(wanted, str(cell.style), (colors16, entry.path.name))

    async def test_ascii_mode_draws_only_ascii_on_every_screen(self):
        app = self.colored_app(ascii=True, colors16=True)
        app.directory.with_name("redundanz_config.json").write_text(
            '{"language": "en", "region_priority": ["USA", "Japan"]}', encoding="utf-8")
        async with app.run_test(size=(110, 32)) as pilot:
            def check(name):
                text = "\n".join(self.screen_lines(app))
                # The settings name the languages in their own script; that is text, not drawing.
                text = text.replace("Español", "").replace("Français", "").replace("日本語", "")
                self.assertEqual(sorted({char for char in text if ord(char) > 127}), [], name)
            await self.visit_every_screen(app, pilot, check)
            self.assertIn("(*)", "\n".join(self.screen_lines(app)))
            app.show_message("info", "Done", "OK")
            await pilot.pause()
            self.assertIn("+---", "\n".join(self.screen_lines(app)))  # an ASCII frame around the question
        from textual.scrollbar import ScrollBar, ScrollBarRender
        self.assertIs(ScrollBar.renderer, ScrollBarRender)  # set back when the program ends

    async def test_ascii_folder_tree_and_progress_bar(self):
        app = self.app_for(self.TWO_GAMES, ascii=True)
        (app.directory / "Sub").mkdir()
        async with app.run_test(size=(100, 30)) as pilot:
            await self.analyzed(app, pilot)
            progress = app.query_one("#progress")
            progress.display = True
            progress.update(total=4, progress=2)
            await pilot.pause()
            row = next(line for line in self.screen_lines(app) if "=" in line)
            self.assertIn("50%", row)
            self.assertNotIn("━", row)
            progress.display = False
            await self.open_folder_choice(app, pilot)
            text = "\n".join(self.screen_lines(app))
            self.assertIn("`-", text)
            self.assertNotIn("▶", text)
            self.assertNotIn("├", text)

    async def test_japanese_rows_keep_their_width_and_the_columns_line_up(self):
        from rich.cells import cell_len

        translations.set_language("ja")
        files = {"ゼルダの伝説 (Japan).bin": b"x" * 3000, "ゼルダの伝説 (USA).bin": b"x" * 2000,
                 "Mario (USA).bin": b"x" * 5000, "Mario (Japan).bin": b"x" * 4000}
        app = self.app_for(files, scope="all")
        async with app.run_test(size=(80, 24)) as pilot:
            await self.analyzed(app, pilot)
            strips = self.strips(app)
            self.assertTrue(all(strip.cell_length == 80 for strip in strips))
            unit = translations.tr("unit.kb")
            ends = set()
            for line in self.screen_lines(app):
                if f" {unit}" in line and (".bin" in line):
                    ends.add(cell_len(line[:line.index(f" {unit}")]))
            self.assertEqual(len(ends), 1, ends)  # the size column is right-aligned in every row
            self.assertIn("ゼルダの伝説", "\n".join(self.screen_lines(app)))
            await self.open_folder_choice(app, pilot)
            self.assertTrue(all(strip.cell_length == 80 for strip in self.strips(app)))

    def test_ascii_and_16_colors_are_chosen_from_the_terminal(self):
        ascii_mode, colors = self.tui.wants_ascii, self.tui.wants_16_colors
        self.assertTrue(ascii_mode({"TERM": "linux", "LANG": "de_DE.UTF-8"}))
        self.assertTrue(ascii_mode({"TERM": "vt100"}))
        self.assertTrue(ascii_mode({"TERM": "xterm", "LANG": "de_DE.ISO-8859-1"}))
        self.assertTrue(ascii_mode({"TERM": "xterm", "LANG": "en_US"}))  # Latin-1 without a charset
        self.assertTrue(ascii_mode({"TERM": "xterm", "LC_ALL": "en_US.ISO-8859-15", "LANG": "en_US.UTF-8"}))
        self.assertFalse(ascii_mode({"TERM": "xterm-256color", "LANG": "de_DE.UTF-8"}))
        self.assertFalse(ascii_mode({"TERM": "xterm-256color", "LC_CTYPE": "C.utf8"}))
        # Python replaces a locale that is not installed by LC_CTYPE=C.UTF-8 itself: LANG counts.
        self.assertTrue(ascii_mode({"TERM": "xterm-256color", "LANG": "en_US", "LC_CTYPE": "C.UTF-8"}))
        self.assertFalse(ascii_mode({"TERM": "xterm-256color", "LANG": "de_DE.UTF-8", "LC_CTYPE": "C.UTF-8"}))
        self.assertFalse(ascii_mode({"TERM": "xterm-256color", "LANG": "C"}))
        self.assertFalse(ascii_mode({}))  # Windows: no TERM, no locale variables
        self.assertTrue(colors("standard", {"TERM": "xterm"}))
        self.assertTrue(colors("256", {"TERM": "linux"}))
        self.assertTrue(colors("windows", {}))
        self.assertFalse(colors("256", {"TERM": "xterm-256color"}))
        self.assertFalse(colors("truecolor", {"TERM": "xterm-256color", "COLORTERM": "truecolor"}))
        self.assertFalse(colors(None, {"TERM": "dumb"}))  # no colors at all: nothing to replace

    def test_run_tui_detects_or_takes_the_modes(self):
        seen = []
        with mock.patch.object(self.tui.WorkbenchApp, "run", lambda app: seen.append((app.ascii, app.colors16))), \
                mock.patch.object(self.tui, "wants_ascii", return_value=True), \
                mock.patch.object(self.tui, "wants_16_colors", return_value=True):
            self.tui.run_tui(None, None)
            self.tui.run_tui(None, None, None, None, False)
        with mock.patch.object(self.tui.WorkbenchApp, "run", lambda app: seen.append((app.ascii, app.colors16))), \
                mock.patch.object(self.tui, "wants_ascii", return_value=False), \
                mock.patch.object(self.tui, "wants_16_colors", return_value=False):
            self.tui.run_tui(None, None, None, None, True)
        self.assertEqual(seen, [(True, True), (False, True), (True, False)])

    def test_delete_question_names_the_trash_of_the_system(self):
        folder = self.demo_folder({"Title (USA).bin": b"a", "Title (Japan).bin": b"b"})
        config = rules_config()
        review = rf.Review(rf.scan_directory(folder, config), config)
        with mock.patch.object(rf.os, "name", "nt"):
            self.assertIn("Recycle Bin", review.confirm_message(False))
        with mock.patch.object(rf.os, "name", "posix"):
            self.assertIn("do not go to the trash", review.confirm_message(False))
            translations.set_language("es")
            self.assertIn("papelera.", review.confirm_message(False))

    # r and F5: analyze again (the help row named r, but it was missing until step 14) -----------

    async def test_r_and_f5_read_the_folder_again(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            self.assertEqual(self.titles(app), ["A", "B"])
            (app.directory / "C (USA).bin").write_bytes(b"e")
            (app.directory / "C (Japan).bin").write_bytes(b"f")
            await pilot.press("r")
            await self.analyzed(app, pilot)
            self.assertEqual(self.titles(app), ["A", "B", "C"])
            (app.directory / "C (Japan).bin").unlink()
            await pilot.press("f5")
            await self.analyzed(app, pilot)
            self.assertEqual(self.titles(app), ["A", "B"])

    async def test_analyzing_again_asks_after_changes_by_hand(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            before = app.review
            await pilot.press("x", "r")
            await pilot.pause()
            self.assertTrue(app.question_open())
            self.assertIn("Analyze again?", self.text(app.screen, "#question-text"))
            await pilot.press("enter")  # No
            await pilot.pause()
            self.assertIs(app.review, before)
            self.assertEqual(app.review.moved_count(), 1)
            await pilot.press("r", "left", "enter")  # Yes
            await self.analyzed(app, pilot)
            self.assertIsNot(app.review, before)
            self.assertEqual(app.review.moved_count(), 0)

    async def test_r_is_typed_in_fields_and_does_nothing_without_a_folder(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            before = app.review
            await pilot.press("slash", "r")
            await pilot.pause()
            self.assertEqual(app.query_one("#filter").value, "r")
            self.assertIs(app.review, before)
        empty = self.tui.WorkbenchApp(None, None)
        async with empty.run_test() as pilot:
            await self.started(empty, pilot)
            await pilot.press("escape", "r")  # leave the folder choice; no folder: nothing to analyze
            await pilot.pause()
            self.assertEqual(self.text(empty, "#status"), translations.tr("window.choose_folder_status"))

    # A game's title row and the blinking "Nothing to do." --------------------------------------

    async def test_title_row_is_bold_and_dashed_to_the_right_edge(self):
        app = self.app_for({"Pac-Man (USA).nes": b"a", "PacMan (Japan).nes": b"b",
                            "Tetris (USA).gb": b"c", "Tetris (Japan).gb": b"d"})
        async with app.run_test(size=(90, 24)) as pilot:
            await self.analyzed(app, pilot)
            await pilot.pause()
            lines = self.screen_lines(app)
            strips = self.strips(app)
            pac = next(index for index, line in enumerate(lines) if line.startswith(" Pac-Man "))
            tetris = next(index for index, line in enumerate(lines) if line.startswith(" Tetris "))
            self.assertRegex(lines[pac], r"^ Pac-Man -+ Different spellings of the name -+$")
            self.assertRegex(lines[tetris], r"^ Tetris -+$")  # no note: dashes all the way
            self.assertEqual(len(lines[tetris]), 90)  # up to the right edge
            for row in (pac, tetris):
                self.assertTrue(all(segment.style.bold for segment in strips[row] if segment.text.strip()))
            # The file rows keep their columns: the sizes end in the same place, before the notes.
            sizes = {line.index("KB") for line in lines if "KB" in line}
            self.assertEqual(len(sizes), 1)
            self.assertEqual(self.titles(app), ["Pac-Man", "Tetris"])

    async def test_dashed_line_follows_the_width_of_the_terminal(self):
        app = self.app_for({"Tetris (USA).gb": b"c", "Tetris (Japan).gb": b"d"})
        async with app.run_test(size=(70, 20)) as pilot:
            await self.analyzed(app, pilot)
            await pilot.pause()
            line = next(line for line in self.screen_lines(app) if line.startswith(" Tetris "))
            self.assertRegex(line, r"^ Tetris -+$")
            self.assertEqual(len(line), 70)
            await pilot.resize_terminal(100, 20)
            await pilot.pause()
            await pilot.pause()
            line = next(line for line in self.screen_lines(app) if line.startswith(" Tetris "))
            self.assertRegex(line, r"^ Tetris -+$")
            self.assertEqual(len(line), 100)

    LONG_NAMES = {
        "Street Fighter II' - Champion Edition (USA) (Rev 1).sfc": b"x" * 3000,
        "Street Fighter II' - Champion Edition (Japan).sfc": b"x" * 3000,
        "Mega Man X (USA).sfc": b"x" * 3000, "Mega Man X.srm": b"x" * 10,
    }

    async def test_notes_stay_visible_in_a_narrow_terminal(self):
        # PuTTY opens with 80 columns: the long names must not push the notes off the right edge.
        app = self.app_for(self.LONG_NAMES, scope="all")
        async with app.run_test(size=(80, 30)) as pilot:
            await self.analyzed(app, pilot)
            await pilot.pause()
            lines = self.screen_lines(app)
            text = "\n".join(lines)
            self.assertTrue(app.query_one("#games").columns_layout[3])  # wrapping
            self.assertIn("Suspected status or save file", " ".join(text.split()))  # wrapped, but all there
            self.assertTrue(all(strip.cell_length == 80 for strip in self.strips(app)))
            # A wrapped name goes on below the name, not at the left edge.
            first = next(index for index, line in enumerate(lines) if "+ Street Fighter" in line)
            self.assertTrue(lines[first + 1].startswith("       ") and lines[first + 1].strip())
            self.assertIn("KB", lines[first])  # the size stays next to the name
            sizes = {line.index("KB") for line in lines if "KB" in line}
            self.assertEqual(len(sizes), 1)  # and in one column

    async def test_wide_terminal_keeps_one_row_per_file(self):
        app = self.app_for(self.LONG_NAMES, scope="all")
        async with app.run_test(size=(220, 30)) as pilot:
            await self.analyzed(app, pilot)
            await pilot.pause()
            self.assertFalse(app.query_one("#games").columns_layout[3])
            line = next(line for line in self.screen_lines(app) if "+ Mega Man X.srm" in line)
            self.assertIn("Suspected status or save file", line)

    async def test_changing_the_width_lays_the_list_out_again_and_keeps_the_place(self):
        app = self.app_for(self.LONG_NAMES, scope="all")
        async with app.run_test(size=(220, 30)) as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("tab", "shift+down")
            cursor, selection = app.cursor_key(), app.selected_keys()
            await pilot.resize_terminal(80, 30)
            await pilot.pause()
            await pilot.pause()
            self.assertTrue(app.query_one("#games").columns_layout[3])
            self.assertEqual((app.cursor_key(), app.selected_keys()), (cursor, selection))
            await pilot.resize_terminal(220, 30)
            await pilot.pause()
            await pilot.pause()
            self.assertFalse(app.query_one("#games").columns_layout[3])
            self.assertEqual((app.cursor_key(), app.selected_keys()), (cursor, selection))

    async def test_16_colors_write_black_on_the_green_rows(self):
        app = self.colored_app(colors16=True)
        async with app.run_test(size=(110, 32)) as pilot:
            await self.analyzed(app, pilot)
            lines, strips = self.screen_lines(app), self.strips(app)
            for text in ("Folder:", "Showing:"):
                row = next(index for index, line in enumerate(lines) if text in line)
                segment = next(segment for segment in strips[row] if text[:4] in segment.text)
                self.assertEqual(self.as_16_colors(segment.style.bgcolor), 2, text)  # green
                self.assertEqual(self.as_16_colors(segment.style.color), 0, text)  # black

    async def test_help_row_names_the_new_keys_in_every_language(self):
        expected = {"en": "x:delete  k:keep", "de": "x:löschen  k:behalten", "it": "x:elimina  k:mantieni",
                    "es": "x:eliminar  k:conservar", "fr": "x:supprimer  k:garder", "ja": "x:削除  k:保持"}
        for language, start in expected.items():
            translations.set_language(language)
            help_row = translations.tr("tui.help")
            self.assertTrue(help_row.startswith(start), language)
            for key in ("Tab:", "1-3:", "/:", "s:", "f:", "r:", "c:", "q:"):
                self.assertIn(key, help_row, language)
            self.assertNotIn("d:", help_row, language)

    async def test_help_row_breaks_only_between_entries(self):
        app = self.tui.WorkbenchApp(None, Path("/home/user/games"))
        for width in (80, 104, 60):
            async with app.run_test(size=(width, 30)) as pilot:
                await pilot.pause()
                help_widget = app.query_one("#help")
                lines = [strip.text.strip() for strip in app.screen._compositor.render_strips()
                         [help_widget.region.y:help_widget.region.bottom]]
                self.assertGreater(len(lines), 1, width)  # too long for one row at these widths
                self.assertEqual("  ".join(lines), translations.tr("tui.help"), width)
                self.assertTrue(all(line.split("  ")[0].count(":") == 1 for line in lines), lines)
            app = self.tui.WorkbenchApp(None, Path("/home/user/games"))

    async def test_old_keys_do_nothing_any_more(self):
        app = self.app_for(self.TWO_GAMES)
        app.config_file = rf.ConfigFile(app.directory.with_name("config.json"))
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("d", "p", "e", "o", "ctrl+l", "ctrl+e", "ctrl+o", "ctrl+f")
            await pilot.pause()
            self.assertEqual(app.review.moved_count(), 0)
            self.assertFalse(app.question_open())
            self.assertFalse(app.folder_open())
            self.assertFalse(app.settings_open())
            self.assertIs(app.focused, app.query_one("#games"))
            await pilot.press("x", "k")  # the new ones act: marked, then kept again
            self.assertEqual(app.review.moved_count(), 0)
            await pilot.press("x")
            self.assertEqual(app.review.moved_count(), 1)

    async def test_c_and_f1_show_the_credits(self):
        app = self.app_for(self.TWO_GAMES)
        async with app.run_test(size=(110, 30)) as pilot:
            await self.analyzed(app, pilot)
            self.assertIn("c:credits", str(app.query_one("#help").content))
            for key in ("c", "f1"):
                await pilot.press(key)
                await pilot.pause()
                self.assertTrue(app.question_open(), key)
                self.assertEqual(self.text(app.screen, "#question-title"), "Credits")
                text = self.text(app.screen, "#question-text")
                self.assertTrue(text.startswith("Idea: M. Kärcher\nProgramming: Claude Code\n\n"))
                self.assertIn("GNU General Public License", text)
                self.assertIn("copy of your own ROM collection", text)
                self.assertEqual(self.buttons(app), ["OK"])
                await pilot.press("enter")
                await pilot.pause()
                self.assertFalse(app.question_open())
            await pilot.press("slash", "c")  # in the filter field, c is a letter
            await pilot.pause()
            self.assertFalse(app.question_open())
            self.assertEqual(app.query_one("#filter").value, "c")

    async def test_nothing_to_do_blinks_with_the_terminal_attribute(self):
        app = self.app_for({"Alone (USA).bin": b"a"})
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            row = next(strip for strip in self.strips(app) if "Nothing to do." in strip.text)
            styles = [segment.style for segment in row if "Nothing" in segment.text]
            self.assertTrue(styles and all(style.blink and style.bold for style in styles))

    async def test_x_typed_in_the_filter_deletes_nothing(self):
        app = self.app_for(self.FILTER_GAMES)
        async with app.run_test() as pilot:
            await self.analyzed(app, pilot)
            await pilot.press("slash", "x", "enter")
            await pilot.pause()
            self.assertEqual(app.query_one("#filter").value, "x")
        self.assertEqual(len(list(app.directory.iterdir())), 4)
