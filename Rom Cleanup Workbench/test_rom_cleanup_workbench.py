import contextlib
import gc
import io
import queue
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import rom_cleanup_workbench as rf
import translations


class RedundanzTestCase(unittest.TestCase):
    def setUp(self):
        # The texts below are English; a test that switches the language switches it back.
        translations.set_language("en")
        self.addCleanup(translations.set_language, "en")
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.config = rf.Config.load(None)

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
            "    - Katz und Maus (Europa).abc\n"
            "    - Katz und Maus.abc (Japan).abc\n"
            "    - Katz und Maus.zip  [Content identical to Katz und Maus (USA).abc]",
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
        self.write("Title (USA) (Proto).bin")
        result = self.single()
        self.assertEqual(result.keep, [])
        self.assertEqual(self.names(result.marked), ["Title (USA) (Proto).bin"])

    def test_delete_tag_never_wins_over_other_files(self):
        self.write("Title (USA) (Proto 2).bin")
        self.write("Title (Japan).bin")
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (Japan).bin"])

    def test_delete_tag_matches_whole_word_only(self):
        self.write("Title (Protocol).bin")
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
        self.assertEqual(result.marked[0].notes, ["Older version"])

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

    def test_low_priority_number(self):
        for tags, expected in (
            (["Beta 2"], (2,)), (["beta2"], (2,)), (["Beta 1.10"], (1, 10)), (["Beta"], ()),
            (["Beta 2.0"], (2,)), (["Betamax 3"], ()), (["Beta v2"], ()), (["USA", "Beta 4"], (4,)),
        ):
            self.assertEqual(self.config.low_priority_number(tags), expected, tags)

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
        self.write("Title (USA) (Proto).sfc", b"x" * 10)
        self.assertEqual(self.names(self.single().marked), ["Title (USA) (Proto).sfc"])

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
        self.assertIn("WARNING", result.marked[0].notes[-1])

    def test_all_zips_next_to_plain_file_are_marked(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (USA).zip", {"a.bin": b"different"})
        self.write_zip("Title [USA].zip", {"a.bin": b"different"})
        result = self.single()
        self.assertEqual(self.names(result.keep), ["Title (USA).bin"])
        for entry in result.marked:
            self.assertIn("WARNING", entry.notes[-1])

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
        self.assertIn("WARNING", result.marked[0].notes[-1])

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
        self.assertIn("WARNING", marked.notes[0])

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
        self.write("Title (USA) (Proto).bin")
        self.assert_problem("No file")

    def test_zip_with_unique_content(self):
        self.write("Title (USA).bin", b"rom")
        self.write_zip("Title (Europe).zip", {"a.bin": b"unique"})
        self.assert_problem("Content of a marked ZIP")

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
        self.write("Problem (USA) (Proto).bin")
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
        self.write("Problem (USA) (Proto).bin")
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
            self.assertEqual(config.rank([]), 1, word)
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
        with mock.patch("rom_cleanup_workbench_window.add_confirmed_saves", side_effect=PermissionError("locked")), mock.patch(
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
        self.assertIn("Ctrl+L: Proceed  |  Ctrl+O: Folder", translations.tr("window.help"))

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
        self.write("Problem (USA) (Proto).bin")
        review = rf.Review(self.scan(), self.config)
        self.assertIn("Not shown", review.confirm_message(True, False))
        self.assertIn("Not shown", review.confirm_message(True, True))
        self.assertNotIn("Not shown", review.confirm_message(False, True))

    def test_filter_hides_clear_games(self):
        self.write("Clear (USA).bin")
        self.write("Clear (Japan).bin")
        self.write("Problem (USA) (Proto).bin")
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
        self.write("Problem A (USA) (Proto).bin")
        self.write("Problem B (USA) (Proto).bin")
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
        self.write("Gone (USA) (Proto).bin")
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
            with mock.patch("rom_cleanup_workbench_window.filedialog.askdirectory", return_value=other):
                window.choose_directory()
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
            with mock.patch("rom_cleanup_workbench_window.filedialog.askdirectory", return_value=other) as ask:
                window.choose_directory()
            ask.assert_called_once()
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
        with mock.patch("rom_cleanup_workbench_window.filedialog.askdirectory", return_value=""):
            window.choose_directory()
        self.assertEqual(window.directory, self.dir)
        self.assertIsNone(window._analysis)


class MainTests(RedundanzTestCase):
    def setUp(self):
        super().setUp()
        # Without --config the program reads redundanz_config.json next to it; the tests must not
        # depend on the language or priority someone has set there.
        patcher = mock.patch.object(rf, "DEFAULT_CONFIG_PATH", self.dir.with_name(self.dir.name + "-missing.json"))
        patcher.start()
        self.addCleanup(patcher.stop)

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

        def run(analyze, directory, scope):
            self.window_calls.append((directory, scope))
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

        def run(analyze, directory, _only_problems):
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

        def run(analyze, directory, _only_problems):
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

        def run(analyze, directory, _only_problems):
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
