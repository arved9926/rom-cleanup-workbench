# Handover: keywords in the priority list, delete keywords

Status: **planned, step 1 is next.** Concerns the rules, the window and the terminal version.

## Decisions (agreed with the user, 2026-11-22)

- **Low priority tags go away.** Extra info such as `Beta`, `Proto` or `Alpha` is written at the end of the priority list instead, after `none`: `USA, Europe, Japan, none, Beta, Proto`.
- **Such a keyword counts before the region.** A file with `Beta` is placed at Beta's position, even if its region is better: `Game (Japan)` is kept, `Game (USA) (Beta)` is marked. Among several files at the same keyword, the region decides, then the number (`Beta 2` before `Beta 1`, note "Older beta"), as the low priority tags do today. The order of the keywords counts: with `…, none, Beta, Proto`, a Beta beats a Proto.
- **Which entries are keywords** (decided by Claude from "at the end of the list"): the entries after `none`. The entries up to `none` stay regions, where the better one counts (`(USA, Europe)`), as before. A list without `none` has no keywords.
- **Delete keywords:** extra info that marks a file for deletion by default (the existing `delete_tags`, rule 2: marked even if it is the only file of a game; `P` keeps it anyway). Default from now on: `Hack, Hacks` (before: `Proto`). A keyword matches a whole word at the start of a bracket: `Hack` matches `(Hack)` and `(Hack 2)`, not `(Hacks)`, hence both.
- **Settings** (window and terminal version): the field "Low priority tags" is replaced by "Delete keywords" (`delete_tags`). The priority list explains that entries after `none` are keywords.
- **Old configuration files keep working:** an entry `low_priority_tags` is read as keywords at the end of the priority list (after `none`, which is added if missing). When the settings save, they write the merged list and drop `low_priority_tags`. An existing `delete_tags` stays as it is: the user's own file has `"delete_tags": []`, so Hack and Hacks only apply there once entered in the settings.
- `--delete-tag` stays. `--priority` takes keywords after `none` too.
- Rules, texts and settings stay shared; the Windows window changes only where these rules and settings change.

## How to work

As in `tui-plan.md`: one step at a time; a step is done when all tests pass on Windows and in the WSL Ubuntu (`python -m unittest`) and it is committed locally; upload only when the user asks. Texts in all six languages (`translations.py`). Never run the program on a real game folder.

## Steps

- [ ] **1. Keywords in the priority list.** `Config.rank`: the position of a file is the later of its best region (or `none`) and the latest keyword it carries; then region, version, keyword number as today. `low_priority_tags` read as keywords after `none`; `Config` and `ConfigFile.read` merge them. Done when: the rules tests for Beta, Proto and Alpha pass with keywords in the list instead of low priority tags, plus tests for the order of keywords, a list without `none`, and an old file with `low_priority_tags`.
- [ ] **2. Delete keywords Hack, Hacks.** Default `delete_tags` becomes `["Hack", "Hacks"]`. Done when: tests show `(Hack)`, `(Hacks)` and `(Hack 2)` marked by default and `(Hackers)` not.
- [ ] **3. Settings in the window.** "Delete keywords" field instead of "Low priority tags"; the label of the priority list explains keywords after `none`; `ConfigFile.write(language, region_priority, delete_tags)` writes the merged list and drops `low_priority_tags`. Done when: the window's settings tests pass with the new field.
- [ ] **4. Settings in the terminal version.** The same in `SettingsScreen`. Done when: the terminal settings tests pass, checked once in tmux.
- [ ] **5. Documentation.** README (rules 2 and 6, configuration, settings) and the user guide (Word and PDF: chapters 8, 10, 11, 13 and 17 where they name low priority tags). Done when: no text names low priority tags any more, except where old files are explained.

## Log

- 2026-11-22: Plan agreed. Next: step 1.
