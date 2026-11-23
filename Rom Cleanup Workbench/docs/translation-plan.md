# Plan: documentation in all six languages

Goal (user, 2026-11-22): "Generiere für alle unterstützten Sprachen die Dokumentation." The program speaks English, German, Italian, Spanish, French and Japanese (`translations.py`); the documentation so far exists only in English.

## Scope

- **README** of the program folder (about 3,700 words): one file per language, `README.de.md`, `README.it.md`, `README.es.md`, `README.fr.md`, `README.ja.md`, next to `README.md`. Each starts with a line of links to all six. The root `README.md` gets the same line.
- **User guide** (Word and PDF, 17 pages, about 3,600 words): one pair per language in `docs/`, for example `Rom Cleanup Workbench - Benutzerhandbuch.docx/.pdf`. Same layout, styles, tables and page breaks as the English guide.
- **Not translated:** the plan logs (`keywords-plan.md`, this file), the LICENSE (the GPL is only legally valid in English; the READMEs say so), code comments, the `--help` output of the command line.
- **Screenshots** stay English in every language; each guide says so once under the first picture ("The pictures show the English version; with `language` set, the program shows the same texts in <language>.").

## Rules for the translations

- Every name the program shows (buttons, views, notes, questions, the help row) is quoted **exactly** as `translations.py` has it in that language, so readers find the same words on the screen. A script checks this (step 1).
- File names, options, keys, configuration keys (`region_priority`, `delete_tags`, ...) and code stay as they are.
- Same facts as the English text, nothing added or left out; the safety notes (no Recycle Bin, copy of the collection, no warranty) keep their full meaning.
- Japanese: a font with Japanese glyphs for the PDF (the guide sets `w:eastAsia`; LibreOffice on Windows has Yu Gothic/Meiryo); check the PDF for missing glyphs.

## Steps

1. **Tools.** `docs_extract.py`: the guide's paragraphs and table cells as numbered segments with inline tags for the six run formats (bold, code, ...), into a JSON file; `docs_build.py`: a translated JSON back into the XML, keeping every paragraph's and run's properties, then Word and PDF via LibreOffice. Round trip: English → English gives the same text and page count. `docs_check.py`: every quoted program text of a language exists in `translations.py`, every segment is translated, tags and code spans are unchanged. Not in the repository (scratchpad), like the earlier guide scripts.
2. **German** (README + guide).
3. **Italian.**
4. **Spanish.**
5. **French.**
6. **Japanese.**
7. **Links and final check:** language links in all READMEs and the root README; the program's `README.md` mention stays; all PDFs rendered and looked at; all tests on Windows and Linux.

Each step: done when the check script passes, the PDF has been looked at page by page, all tests pass on Windows and on Linux, and it is committed locally. Uploaded to GitHub only when the user asks.

## Log

- 2026-11-22: Plan written. The user approved an own plan and asked to work through it step by step without further questions.
- 2026-11-22: Step 1 done. `docs_extract.py` turns the guide into 342 segments (3,627 words) with tags `[[b]]`, `[[h]]` (table header), `[[t]]` (title), `[[i]]` (caption), `[[c]]`/`[[k]]` (code), `[[img:N]]`/`[[br:N]]`, plus the footer; `docs_build.py` writes them back with the English paragraph and run properties (Japanese: East Asian font Yu Gothic). Round trip English → English: identical segments, 17 pages, identical PDF text. `docs_check.py` compares tags, images, code spans (only the help row and the `language` example may change), untranslated segments and the program texts from `translations.py`; for READMEs code blocks, headings, table rows, list items, links and anchors. The braces in the guide's JSON examples ruled out `{b}` as tag syntax.
- 2026-11-22: Step 2 done. `README.de.md` and `docs/Rom Cleanup Workbench - Benutzerhandbuch.docx/.pdf` (19 pages; German runs longer). Informal "du" as in the program's German texts; keys with German names (Strg, Umschalt, Entf, Leertaste) as in `window.help`. The first caption says that the pictures mostly show the English version; the license paragraph adds that only the English original is legally binding. Segment files may list `_same` (segments that are the same in this language, such as names), `_code` (translated code spans: `key:action` → `Taste:Aktion`) and `_ignore` (program texts used in another grammatical form). Both checks pass; every page looked at; 421 tests pass on Windows and on Linux.
- 2026-11-22: Step 3 done. `README.it.md` and `docs/Rom Cleanup Workbench - Guida utente.docx/.pdf` (19 pages; the file name avoids the apostrophe of "Guida per l'utente", which stays the title). Informal "tu" as in the program's Italian texts; Italian key names (Maiusc, Invio, Canc, Spazio) as in `window.help`. Pages 1, 6, 13, 17 and 19 looked at; the others checked by their text (no empty page, no heading left at a page end; `linux_pdf_layout.sh`). Both checks pass; 421 tests pass on Windows and on Linux.
- 2026-11-22: Step 4 done. `README.es.md` and `docs/Rom Cleanup Workbench - Guía del usuario.docx/.pdf` (18 pages). Informal "tú" as in the program's Spanish texts, except the risk notice, which keeps the formal "Úselo bajo su propia responsabilidad" of `credits.license`; Spanish key names (Mayús, Intro, Supr, Espacio). Pages 1, 4 and 12 looked at, the others checked by their text. Both checks pass; 421 tests pass on Windows and on Linux.
- 2026-11-22: Step 5 done. `README.fr.md` and `docs/Rom Cleanup Workbench - Guide utilisateur.docx/.pdf` (19 pages). Formal "vous" as in the program's French texts; French key names (Maj, Entrée, Échap, Suppr, Espace), sizes in Ko. `french_spaces.py` puts non-breaking spaces before `:` `;` `?` `!` and inside « » outside code; the check treats them as spaces. Pages 3, 16 and 17 looked at, the others checked by their text. Both checks pass; 421 tests pass on Windows and on Linux.
- 2026-11-22: Step 6 done. `README.ja.md` and `docs/Rom Cleanup Workbench - ユーザーガイド.docx/.pdf` (22 pages; Japanese lines are taller). Polite です/ます style and 「」 quotes as in the program's Japanese texts. The build sets Yu Gothic as East Asian font in the styles; the first attempt wrote `w:eastAsia` twice into elements that already had `w:eastAsiaTheme`, which LibreOffice refused, so each `w:rFonts` is now rewritten with exactly one. The PDF embeds Yu Gothic (`pdffonts`). Code spans may come in another order (Japanese word order), so the check compares them unordered. Pages 3, 14, 20 and 21 looked at, the others checked by their text. Both checks pass; 421 tests pass on Windows and on Linux.
- 2026-11-22: Step 7 done, plan complete. Every README starts with a line of links to all six languages (the current one in bold), and the root README names the five translations. The check accepts these links and the guide links if the files exist; all local links of all READMEs resolve. All five languages pass both checks; 421 tests pass on Windows and on Linux. Committed locally, not uploaded.
