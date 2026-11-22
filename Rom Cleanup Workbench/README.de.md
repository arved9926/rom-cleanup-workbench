# Rom Cleanup Workbench

[English](README.md) · **Deutsch** · [Italiano](README.it.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md)

**Benutzerhandbuch mit Bildschirmfotos:** [PDF](<docs/Rom Cleanup Workbench - Benutzerhandbuch.pdf>) · [Word](<docs/Rom Cleanup Workbench - Benutzerhandbuch.docx>)

Findet doppelte ROM-Dateien in einem Verzeichnis anhand des Spielnamens und löscht sie auf Wunsch.
Braucht Python 3.10 oder neuer. Das Fenster braucht keine zusätzlichen Pakete; die Terminal-Version für Linux braucht Textual (siehe [Terminal-Version (Linux)](#terminal-version-linux)).
Das Programm spricht Englisch, Deutsch, Italienisch, Spanisch, Französisch und Japanisch (siehe [Sprache](#sprache)).

**Wichtig:** Wende dieses Programm nicht auf deine Originale an. Lege eine Kopie an und nutze das Programm, um die Bereinigung vorzunehmen.

## Installation

### Windows

1. **Python installieren:** Python 3.10 oder neuer von [python.org/downloads](https://www.python.org/downloads/) herunterladen und installieren. Bietet das Installationsprogramm „Add python.exe to PATH“ an, diese Option anhaken. `tkinter` für das Fenster ist dabei. Danach in einem neuen Terminal prüfen:

   ```powershell
   python --version
   ```

2. **Das Programm installieren:** Auf der [GitHub-Seite](https://github.com/arved9926/rom-cleanup-workbench) unter **Code → Download ZIP** herunterladen und entpacken, oder mit Git klonen:

   ```powershell
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   cd "rom-cleanup-workbench\Rom Cleanup Workbench"
   ```

   Das Programm liegt im Ordner `Rom Cleanup Workbench`. Für das Fenster sind keine weiteren Pakete nötig. Nur wer unter Windows die Terminal-Version nutzen will, installiert zusätzlich Textual:

   ```powershell
   python -m pip install textual==8.2.8
   ```

### Linux

1. **Python installieren:** Meist ist Python 3 schon da (`python3 --version`). Sonst unter Debian oder Ubuntu:

   ```bash
   sudo apt install python3 python3-venv git
   ```

   Das Paket `python3-tk` ist nur nötig, wenn du unter Linux mit grafischer Anzeige das Fenster statt der Terminal-Version nutzen willst.

2. **Das Programm installieren:** Das Repository klonen und Textual in einer virtuellen Umgebung installieren:

   ```bash
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   cd "rom-cleanup-workbench/Rom Cleanup Workbench"
   python3 -m venv ~/venvs/rom-cleanup-workbench
   ~/venvs/rom-cleanup-workbench/bin/pip install textual==8.2.8
   ```

## Aufruf

### Windows

Ein Terminal (zum Beispiel PowerShell) im Ordner `Rom Cleanup Workbench` öffnen und das Programm mit dem Ordner deiner Spiele starten:

```powershell
cd "rom-cleanup-workbench\Rom Cleanup Workbench"
python rom_cleanup_workbench.py "D:\Games"
```

Ohne Ordner fragt das Fenster danach. In VS Code: den Ordner `Rom Cleanup Workbench` öffnen, mit F5 starten und das Verzeichnis eingeben. Wer die Terminal-Version will, hängt `--tui` an.

### Linux

In den Ordner `Rom Cleanup Workbench` wechseln und das Programm mit der Python-Version der virtuellen Umgebung und dem Ordner deiner Spiele starten:

```bash
cd "rom-cleanup-workbench/Rom Cleanup Workbench"
~/venvs/rom-cleanup-workbench/bin/python rom_cleanup_workbench.py ~/roms
```

Ohne grafische Anzeige, etwa über SSH, startet von selbst die Terminal-Version. Mit grafischer Anzeige öffnet sich das Fenster (dafür braucht es `python3-tk`); mit `--tui` startet trotzdem die Terminal-Version. Mehr dazu unter [Terminal-Version (Linux)](#terminal-version-linux).

### Was dann passiert

Das Programm öffnet das Analysefenster und zeigt dort alles an; im Terminal gibt es nichts aus und fragt dort nichts. Fragen, Meldungen und die Ordnerwahl erscheinen ebenfalls im Fenster, in der Sprache des Programms, nie als Windows-Popups; Enter wählt die vorgewählte Schaltfläche, Esc antwortet Nein. Ohne Verzeichnis fragt das Fenster nach dem Ordner. Dateien werden erst nach der Bestätigung im Fenster gelöscht. **Gelöschte Dateien landen nicht im Papierkorb.**

| Option | Wirkung |
| --- | --- |
| `--review all` | öffnet das Fenster bei diesem Start mit `Alle Löschmarkierungen` |
| `--review problems` | öffnet das Fenster bei diesem Start mit `Problematische Löschmarkierungen` |
| `--priority USA Europe Japan none` | legt die Priorität für diesen Lauf fest |
| `--delete-tag Hack Hacks Proto` | legt die Löschwörter für diesen Lauf fest |
| `--config file.json` | verwendet eine andere Konfiguration |
| `--report-only` | ohne Fenster: nur den Bericht im Terminal ausgeben |
| `--yes` | ohne Fenster: markierte Dateien ohne Nachfrage löschen |
| `--all` | mit `--report-only`: auch Spiele ohne markierte Dateien zeigen |
| `--tui` | die Terminal-Version statt des Fensters verwenden (automatisch unter Linux ohne grafische Anzeige) |
| `--ascii` | Terminal-Version nur mit ASCII-Zeichen (automatisch auf der Linux-Konsole); schließt `--tui` ein |

Die Optionen der Befehlszeile und ihre Hilfe (`--help`) sind immer auf Englisch.

Die Tests laufen über die Testansicht oder mit `python -m unittest`.

## Analysefenster

Die grüne Zeile oben zeigt links `Rom Cleanup Workbench` und rechts den Ordner; darunter nennt das Fenster die geltende Priorität mit ihrer Herkunft. Die grüne vorletzte Zeile zeigt den Status, während der Analyse zum Beispiel `Analysiere: 120 von 2007 Dateien`. Solange erscheint auch ein Fortschrittsbalken in der Mitte. Das Fenster zeigt auch Fehler, etwa in der Konfiguration, und solange die Analyse scheitert, lässt sich nichts löschen. Beim Löschen erscheint der Fortschrittsbalken in der Mitte, und die grüne Zeile zeigt zum Beispiel `Lösche: 120 von 500 Dateien`; das Fenster nimmt keine Eingaben an, bis das Löschen fertig ist. Danach meldet es das Ergebnis und entfernt die gelöschten Dateien aus der Liste, ohne den Ordner neu zu analysieren; Dateien, die sich nicht löschen ließen, bleiben markiert. `F5` analysiert den Ordner neu, wenn du das willst.

Ist im ganzen Ordner nichts markiert und keine Datei als Status- oder Spielstanddatei verdächtig, blinkt `Nichts zu tun.` in der Mitte des Fensters.

Die drei Optionsfelder bestimmen, was die Liste zeigt:

- `Problematische Löschmarkierungen`: nur Spiele mit einer markierten Datei, die als problematisch gelten (Vorgabe beim ersten Start)
- `Alle Löschmarkierungen`: alle Spiele mit einer markierten Datei
- `Alle Romdateien`: alle Spiele. Ihre Dateien lassen sich dann auch mit `x` markieren, und problematische Fälle ohne markierte Datei, etwa ein nicht lesbares ZIP, erscheinen ebenfalls.

Das Fenster merkt sich die zuletzt gewählte Ansicht und die bestätigten Status- oder Spielstanddateien (Regel 9) in `rom_cleanup_workbench_settings.json` neben dem Programm.

| Taste | Wirkung |
| --- | --- |
| Pfeiltasten | eine Zeile wählen, mit Umschalt mehrere (zum Beispiel alle Discs eines Spiels) |
| `Tab` / `Umschalt+Tab` | zum nächsten / vorigen Spiel; die erste Datei des Spiels wird gewählt |
| `x` | die Datei zum Löschen markieren; sie rückt ans Ende ihres Spiels |
| `k` | die Datei behalten; sie rückt an die Stelle, die die Regeln ihr geben |
| `1` `2` `3` | die Ansichten `Problematische Löschmarkierungen`, `Alle Löschmarkierungen`, `Alle Romdateien` |
| `Strg` + Mausrad | Schrift vergrößern oder verkleinern (8 bis 32 pt, gilt bis das Fenster geschlossen wird) |
| `s` | wie die Schaltfläche `Einstellungen...`: die Einstellungen für Sprache, Priorität und Löschwörter zeigen oder ausblenden (siehe [Einstellungen](#einstellungen)) |
| `/` | ins Filterfeld wechseln |
| `Enter` | wie die Schaltfläche `Ausführen...`: nach einer Bestätigung löschen und die vermuteten Status- oder Spielstanddateien bestätigen (Regel 9) |
| `f` | einen anderen Ordner wählen, im Fenster an der Stelle der Liste: Ordner mit Doppelklick oder dem Pfeil öffnen oder einen Pfad in `Pfad:` tippen, dann `Auswählen` oder `Enter`; `Abbrechen` oder `Esc` behalten den aktuellen Ordner |
| `r` oder `F5` | neu analysieren, liest auch die Konfiguration neu |
| `c` oder `F1` | die Credits zeigen |
| `q` oder `Esc` | schließen, ohne etwas zu löschen; nach Änderungen von Hand fragt das Programm vorher |
| `Esc` | schließen, ohne etwas zu löschen |

Waagerechte Linien trennen die Spiele, und jedes zweite Spiel hat einen dunkelgrauen Hintergrund. Die Spalte `Größe` zeigt die Größe jeder Datei in KB, aufgerundet wie im Windows-Explorer (`1.234 KB`); `?` heißt, dass sich die Größe nicht lesen ließ. Die Größe wird bei der Analyse gelesen. Behaltene Dateien stehen fett unter `Bleibt erhalten:`, zu löschende Dateien in normaler Schrift unter `Zum Löschen markiert`. Das Fenster zeigt weiße Schrift in Lucida Sans Typewriter 11 pt auf schwarzem Grund. Ist die Schrift nicht installiert, nimmt Windows stillschweigend einen Ersatz. Von Hand verschobene Dateien haben einen braunen Hintergrund und tragen den Hinweis `Von Hand`; solange die Zeile gewählt ist, erscheint sie blau. Die Hinweise des Programms bleiben unverändert, auch wenn sie sich auf eine Datei beziehen, die du verschoben hast.

`Problematische Löschmarkierungen` blendet die unproblematischen Spiele aus. **Ihre markierten Dateien werden beim Löschen trotzdem gelöscht**; die Bestätigung nennt ihre Anzahl. Spiele, die du von Hand geändert hast, bleiben immer sichtbar, außer der Filter blendet sie aus.

### Filter

Das Filterfeld links in der unteren Zeile schränkt die aktuelle Ansicht auf Spiele ein, deren Dateiname das Muster enthält. Ein Spiel bleibt vollständig, wenn eine seiner Dateien passt. Die Liste folgt kurz nach dem Tippen; der Inhalt der Dateien wird nicht gelesen.

- `*` steht für beliebig viele Zeichen, `?` für genau eines. Alle anderen Zeichen, auch `[` und `]`, zählen wörtlich, und Groß- und Kleinschreibung zählt nicht.
- Das Muster darf irgendwo im Namen stehen: `Beta`, `*Beta*` und `Mario?2` finden alle auch `Super Mario 2 (Beta).nes`. Entsprechend findet `S*` jeden Namen, der ein `S` enthält, nicht nur Namen, die damit beginnen.
- `Enter`, `Tab` und der Pfeil nach unten führen zurück in die Liste; `Esc` leert den Filter und führt zurück in die Liste.
- Solange der Cursor im Feld steht, schreiben Tasten nur dort: `x`, `k`, `Enter`, `f`, `r`, `F5` und `Esc` führen ihre Listenfunktionen nicht aus.
- Der Filter bleibt nach `F5`, nach dem Löschen und nach der Wahl eines anderen Ordners aktiv. Er wird nicht gespeichert.

**Der Filter ändert nur die Anzeige. Markierte Dateien, die der Filter ausblendet, werden beim Löschen trotzdem gelöscht**; die Bestätigung nennt ihre Anzahl.

### Einstellungen

Die Schaltfläche `Einstellungen...` in der unteren Zeile oder `s` zeigt die häufigsten Änderungen an `redundanz_config.json` im Hauptfenster, an der Stelle der Dateiliste. `Speichern` oder `Abbrechen`, `Esc`, `Strg+E` oder ein weiterer Klick auf `Einstellungen...` bringen die Liste zurück. Solange sind der Filter, die Ansichten, `Ausführen...`, `Neu analysieren` und `Ordner...` gesperrt, und `x`, `k` und `Enter` tun nichts, damit sich in der verdeckten Liste nichts ändern kann.

- **Sprache:** Legt fest, welche Sprache das UI nutzt. Eine der sechs Sprachen wählen. Eine neue Sprache gilt ab dem nächsten Start des Programms.
- **Priorität:** Legt fest, welche Länderversionen Vorrang vor anderen haben. Die beste Region oben; Zusatzinfos wie `Beta` oder `Proto` gehören hinter `none`, damit solche Dateien zuletzt kommen (Regel 6). Einen Eintrag wählen und mit `Hoch` und `Runter` verschieben, mit `Entfernen` oder der Taste `Entf` entfernen, einen neuen mit dem Feld unter der Liste und `Hinzufügen` (oder `Enter`) hinzufügen.
- **Löschwörter:** Legt fest, welche Versionen eines Programms in jedem Fall gelöscht werden. Durch Kommas getrennt, zum Beispiel `Hack, Hacks`. Dateien damit werden zum Löschen markiert (Regel 2).

`Speichern` schreibt die Datei und analysiert den Ordner neu, wenn sich die Priorität oder die Löschwörter geändert haben; hast du Markierungen von Hand geändert, fragt das Programm vorher, weil diese Änderungen verloren gehen. Alle anderen Einträge der Datei bleiben, wie sie sind. Falsche Werte, etwa eine leere Regionsliste oder dieselbe Region zweimal, werden gemeldet, es wird nichts geschrieben, und die Einstellungen bleiben offen. Lässt sich die Datei nicht lesen, öffnen sich die Einstellungen nicht, damit sie keine Einträge überschreiben können, die sie nicht kennen. Mit `--config` bearbeiten die Einstellungen diese Datei; mit `--priority` gilt für diesen Lauf weiter die dort angegebene Priorität.

Ein Spiel gilt als problematisch, wenn

- keine seiner Dateien erhalten bliebe,
- der Inhalt eines markierten ZIPs sonst nirgends vorkommt (`WARNUNG`),
- ein ZIP defekt, verschlüsselt oder nicht lesbar ist,
- eine Datei als vermutete Status- oder Spielstanddatei erhalten bleibt (Regel 9),
- die Regeln nur durch einen `Gleichstand` entschieden haben,
- mehrere ZIPs derselben Version unterschiedlichen Inhalt haben,
- die Dateinamen das Spiel unterschiedlich schreiben (`Title 1-2` und `Title 12`),
- eine markierte Datei einen anderen Dateityp hat als die behaltenen (`.nes` und `.sfc`).

Das Fenster verwendet `tkinter`, das zur üblichen Python-Installation unter Windows gehört. Fehlt es, meldet das Programm das und löscht nichts.

## Terminal-Version (Linux)

Dasselbe Programm läuft auch in einem Textterminal, zum Beispiel über SSH (PuTTY, MobaXterm), in `tmux` oder auf der Linux-Konsole. Es zeigt dieselbe Liste, wendet dieselben Regeln an und teilt `redundanz_config.json`, `rom_cleanup_workbench_settings.json` und `translations.py` mit dem Fenster.

Unter Linux startet sie von selbst, wenn es keine grafische Anzeige gibt (weder `DISPLAY` noch `WAYLAND_DISPLAY` ist gesetzt, wie über SSH). `--tui` startet sie überall sonst, auch unter Windows; nimm es, wo es eine grafische Anzeige gibt, du aber das Terminal willst, zum Beispiel in MobaXterm oder unter WSL.

Sie braucht [Textual](https://textual.textualize.io/) (getestet mit 8.2.8). Wie du es installierst und das Programm startest, steht unter [Installation](#installation) und [Aufruf](#aufruf).

Ohne Textual sagt das Programm das und löscht nichts. Der Bildschirm hat die Zeilen des Fensters von oben nach unten: die grüne Titelzeile mit dem Ordner, eine Hilfezeile, die Priorität, die Liste, das Filterfeld, die drei Ansichten und die grüne Statuszeile. In der Liste beginnt jedes Spiel mit seinem Namen in Fettschrift, gefolgt von Strichen bis zum rechten Rand; ein Hinweis wie `Unterschiedliche Schreibweisen des Namens` steht in dieser Zeile. In einem schmalen Terminal, etwa den 80 Spalten von PuTTY, brechen lange Dateinamen und Hinweise in ihrer Spalte um, statt den Bildschirm zu verlassen. `Nichts zu tun.` blinkt mit dem eigenen Blinken des Terminals; in PuTTY muss blinkender Text eventuell erst eingeschaltet werden. Fragen und Meldungen erscheinen in einem Rahmen über der Liste, mit Schaltflächen in der Sprache des Programms; `Nein` ist vorgewählt.

Die Hilfezeile zeigt die Tasten als `Taste:Aktion`, zum Beispiel `x:löschen  k:behalten`. Fenster und Terminal-Version haben dieselben Tasten.

| Taste | Wirkung |
| --- | --- |
| Pfeiltasten | eine Zeile wählen, mit Umschalt mehrere |
| `Tab` / `Umschalt+Tab` | nächstes / voriges Spiel; seine erste Datei wird gewählt |
| `x` / `k` | die gewählten Dateien zum Löschen markieren / behalten |
| `1` `2` `3` | die Ansichten `Problematische Löschmarkierungen`, `Alle Löschmarkierungen`, `Alle Romdateien` |
| `/` | ins Filterfeld wechseln (`Enter`, `Tab` oder der Pfeil nach unten führen zurück, `Esc` leert) |
| `Enter` | ausführen: nach einer Bestätigung löschen (wie `Ausführen...`) |
| `f` | einen anderen Ordner wählen: `Rechts` oder `Leertaste` öffnet einen Ordner, `Links` schließt ihn, `Enter` wählt; ein Pfad lässt sich auch eintippen |
| `s` | Einstellungen: `Umschalt+Hoch`/`Umschalt+Runter` verschieben eine Region, `Entf` entfernt sie, `Strg+S` speichert, `Esc` bricht ab |
| `r` oder `F5` | neu analysieren |
| `c` oder `F1` | die Credits zeigen (auch `c`, weil manche Terminals `F1` für ihre eigene Hilfe behalten) |
| `q` oder `Esc` | schließen, ohne etwas zu löschen; nach Änderungen von Hand fragt das Programm vorher |
| In einer Frage | `Links`/`Rechts` wählen eine Schaltfläche, `Enter` drückt sie, `Esc` antwortet `Nein` |

Die Maus geht auch: Ein Klick wählt eine Zeile, das Rad scrollt, und die Ansichten und Schaltflächen lassen sich anklicken. Buchstaben, die in ein Feld getippt werden, bleiben im Feld, auch schnell getippt oder eingefügt: Ein `x` im Filter markiert nie eine Datei.

**Farben und Zeichen.** Mit 256 Farben oder mehr verwendet die Terminal-Version die Farben des Fensters, aber schwarz hinter jedem Spiel (keine Streifen). Hat das Terminal nur 16 Farben (`TERM=xterm`, `TERM=linux`), wechselt sie zu einfachen ANSI-Farben: blaue Auswahl, grüne Titel- und Statuszeile, braune Zeilen, die von Hand geändert wurden. Auf der Linux-Konsole, in Terminals wie `vt100` und wenn das Locale einen anderen Zeichensatz als UTF-8 nennt (zum Beispiel `en_US` oder `de_DE.ISO-8859-1`), zeichnet sie nur ASCII-Zeichen: Ansichten als `(*)`, Rahmen aus `+`, `-` und `|`. `--ascii` erzwingt das. PuTTY meldet sich als `xterm` (16 Farben); für die Farben des Fensters *Connection → Data → Terminal-type string* auf `xterm-256color` stellen. Dateinamen und Texte in anderen Schriften, etwa Japanisch, brauchen weiterhin ein Terminal und eine Schrift, die sie zeigen können.

Unterschiede zum Fenster: kein Schriftzoom, weil die Schrift dem Terminal gehört (in PuTTY: *Window → Appearance*); und die Spiele sind nicht gestreift, sondern beginnen mit einer Strichlinie. Mit 16 Farben haben die grünen Zeilen schwarze Schrift, die auch auf hellem Grün lesbar bleibt. Beim Löschen löscht die Terminal-Version im Hintergrund und zeigt den Fortschrittsbalken; alle Tasten sind gesperrt, bis sie fertig ist. Das Fenster und die Terminal-Version halten ihre Ansicht und die bestätigten Spielstanddateien in derselben `rom_cleanup_workbench_settings.json`.

## Konfiguration: `redundanz_config.json`

Die Datei liegt neben dem Programm und wird bei jeder Analyse neu gelesen. Sprache, Priorität und Löschwörter änderst du am einfachsten im Fenster mit `Einstellungen...` (siehe [Einstellungen](#einstellungen)). In der Datei selbst genügt es, die Reihenfolge in `region_priority` umzustellen und die Datei zu speichern:

```json
"region_priority": ["Germany", "Europe", "USA", "none", "Japan", "Beta", "Proto"],
"delete_tags": ["Hack", "Hacks"],
```

Enthält die Datei einen Fehler, etwa einen falsch geschriebenen Eintrag, findet keine Analyse statt, und es wird nichts gelöscht. Fehlt die Datei oder ein Eintrag, gelten die Vorgaben des Programms; die Priorität ist dort USA, Europe, Japan, none, Beta, die Löschwörter sind Hack und Hacks, und die Sprache ist Englisch.

- `language`: die Sprache des Fensters, der Hinweise und der Terminalausgabe (siehe unten).
- `region_priority`: Regionen und Zusatzinfos, die besten zuerst. `none` steht für Dateien ohne bekannte Region; die Wörter der anderen Sprachen (`keine`, `nessuna`, `ninguna`, `aucune`, `なし`) gehen ebenso. Zusatzinfos wie `Beta` hinter `none` setzen solche Dateien ans Ende (Regel 6); `Beta` passt auch zu `Beta 2`.
- `region_aliases`: andere Schreibweisen einer Region, zum Beispiel `Europa` für `Europe`.
- `delete_tags`: die Löschwörter, Zusatzinfos, die immer zum Löschen führen (Regel 2). `Hack` passt auch zu `Hack 2` und `Hack by Someone`, aber nicht zu `Hacks` oder `Hackers`, deshalb `Hack` und `Hacks`.
- `part_tags`: Teile einer Version, zum Beispiel `Disc 1`.

Ältere Dateien können noch `low_priority_tags` enthalten, Zusatzinfos mit der niedrigsten Priorität. Das Programm liest deren Einträge, als stünden sie am Ende von `region_priority`, hinter `none`; die Einstellungen verschieben sie beim Speichern dorthin, und der Eintrag verschwindet.

### Sprache

```json
"language": "de",
```

| Wert | Sprache |
| --- | --- |
| `en` | Englisch (Vorgabe) |
| `de` | Deutsch |
| `it` | Italienisch |
| `es` | Spanisch |
| `fr` | Französisch |
| `ja` | Japanisch |

Die Sprache gilt für das Fenster, die Hinweise und die Terminalausgabe, und das Programm liest sie beim Start: Nach einer Änderung das Programm schließen und neu starten. `F5` wechselt die Sprache nicht. Ein unbekannter Wert gilt als Fehler in der Konfiguration, wie oben beschrieben. Die Regeln entscheiden in jeder Sprache gleich. Die Texte stehen in `translations.py`.

Für Japanisch zeigt Windows die Zeichen in einer Ersatzschrift, weil Lucida Sans Typewriter keine japanischen Zeichen hat.

## Regeln

Manche Dateien übergeht das Programm ganz: Sie erscheinen nirgends und werden nie gelöscht.

- Dateien, deren Name mit `gamelist` beginnt, unabhängig von Groß- und Kleinschreibung. Sie sind keine ROM-Dateien.
- Versteckte Dateien: Namen, die mit einem Punkt beginnen, etwa `.xxx` oder `.DS_Store`, und Dateien mit dem Windows-Attribut „Versteckt“.

1. Dateien gehören zusammen, wenn der Text vor der ersten Klammer gleich ist. Groß- und Kleinschreibung, Leerzeichen, Bindestriche und Unterstriche zählen nicht, also `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. Damit gilt auch `Title 1-2` = `Title 12`. Außerdem gelten `und` = `and` = `&` sowie `The Title` = `Title The` = `Title, The` = `Title` als gleich. Ein `The` mitten im Namen zählt dagegen.
2. Dateien mit einem Löschwort (`delete_tags`, als Vorgabe `Hack` und `Hacks`) werden immer markiert, auch wenn es die einzige Datei des Spiels ist. `k` behält eine solche Datei trotzdem.
3. Von den übrigen Dateien bleibt die mit dem besten Eintrag in `region_priority` erhalten. Innerhalb einer Klammer zählt der beste Eintrag: bei `(USA, Japan)` der bessere der beiden. Über Klammern hinweg zählt der schlechteste: `(USA) (Beta)` zählt als `Beta` (Regel 6).
4. Alle Dateien derselben Version bleiben gemeinsam erhalten, zum Beispiel `(Disc 1)` und `(Disc 2)` oder `.cue` und `.bin`. Alles andere wird markiert.
5. Eine Region, die nicht in `region_priority` steht, zählt als `none`. Das gilt auch für Angaben wie `(Rev 1)`.
6. Zusatzinfos wie `Beta`, `Proto` oder `Alpha` werden in `region_priority` hinter `none` geschrieben. Dateien damit kommen nach allen anderen, auch nach Dateien ohne Region, und in der Reihenfolge der Liste: Bei `none, Beta, Proto` kommt eine Beta vor einem Proto. Sie bleiben nur erhalten, wenn es keine bessere Datei des Spiels gibt. Untereinander zählt wieder die Region, dann die Version aus Regel 7, dann die Nummer hinter der Zusatzinfo: `Beta 2` gewinnt gegen `Beta 1` und `Beta 1` gegen `Beta` ohne Nummer. Die Nummern werden numerisch verglichen (`Beta 10` vor `Beta 9`). Die unterlegene Datei bekommt den Hinweis `Ältere Beta`.
7. Bei gleicher Priorität gewinnt die höchste Versionsnummer, numerisch verglichen (`v1.10` vor `v1.9`). Erkannt werden in Klammern `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` und `Rev A`; im Spielnamen nur die Form `Title v1.1`, auch mit `-` oder `_` statt eines Leerzeichens. Eine Datei ohne Version verliert gegen eine mit Version. Die Region zählt vor der Version.
8. Danach gewinnt die Datei mit weniger Zusatzinformationen, dann eine Datei ohne ZIP, dann das Alphabet. Der Bericht zeigt dann `Gleichstand`.
9. Eine Datei, die kleiner ist als 1/4 der größten Datei des Spiels, wird vor den Regeln 3 bis 8 beiseitegelegt und behalten: Sie könnte eine Status- oder Spielstanddatei sein. Sie kann daher weder gelöscht werden noch das echte ROM verdrängen, etwa `1941.state` die Datei `1941.zip`. Die Hinweisspalte zeigt dann `Verdacht auf Status- oder Spielstanddatei`, und das Spiel gilt als problematisch. Ein solches Spiel erscheint in allen drei Ansichten, auch wenn keine seiner Dateien markiert ist. Beim Löschen bestätigt das Programm alle übrigen vermuteten Dateien als legitim: Sie bleiben, wo sie sind, werden weiterhin nie gelöscht und erscheinen nicht mehr in `Problematische Löschmarkierungen` und `Alle Löschmarkierungen`, auch nach `F5` oder einem Neustart. Die Bestätigung nennt ihre Anzahl. Das Programm merkt sie sich mit Pfad und Größe in `rom_cleanup_workbench_settings.json`; ändert sich die Größe, steht die Datei wieder unter Verdacht. Ist nichts markiert, bietet `Enter` an, sie zu bestätigen, ohne etwas zu löschen. ZIPs zählen mit ihrer entpackten Größe. Das gilt nicht für eine kleine normale Datei neben einer großen normalen Datei ihrer eigenen Version, etwa eine `.cue` neben ihrer `.bin`, und nicht für Dateien, die wegen `delete_tags` oder eines defekten ZIPs markiert sind. Mit `x` kannst du die Datei trotzdem von Hand markieren.

## ZIP-Dateien

Jede ZIP-Datei wird vollständig gelesen, auch wenn sie die einzige Datei eines Spiels ist. Ihr Inhalt wird mit SHA-256 mit den anderen Dateien des Spiels verglichen.

- **Gleicher Inhalt wie eine behaltene Datei:** Die ZIP-Datei wird markiert, und der Bericht nennt die Datei mit demselben Inhalt.
- **Bleiben nach der Auswahl ein ZIP und eine normale Datei übrig:** Das ZIP wird immer markiert, auch bei anderem Inhalt, wenn es die einzige Datei mit einem Teil wie `(Disc 1)` ist oder wenn es nicht lesbar ist.
- **Mehrere ZIPs derselben Version mit anderem Inhalt:** Alle bleiben erhalten, und der Bericht weist darauf hin.
- **Markiert, aber der Inhalt kommt in keiner behaltenen Datei vor:** Der Bericht zeigt `WARNUNG`. Die Datei bleibt markiert.
- **Keine Region oder Version im ZIP-Namen:** Die Angabe wird den Dateien im ZIP entnommen, sofern sie denselben Spielnamen haben.
- **Defektes oder verschlüsseltes ZIP:** Die Datei wird immer markiert, auch wenn sie die einzige Datei des Spiels ist. Der Inhalt eines verschlüsselten ZIPs wird nicht geprüft.
- **Gesperrtes ZIP oder unbekannte Methode (zum Beispiel Deflate64):** Das sagt nichts über den Zustand der Datei. Ohne normale Datei des Spiels bleibt es erhalten und wird im Bericht genannt.

## Weiterentwickeln mit Claude Code

Das Programm ist freie Software: Du kannst das Repository klonen und es mit [Claude Code](https://claude.com/claude-code) weiterentwickeln, ganz ohne selbst zu programmieren. So wurde es auch geschrieben.

1. Claude Code installieren. Es braucht ein Claude-Abo oder ein Konto bei der Claude-API. Unter Windows in PowerShell:

   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```

   Unter Linux:

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

2. Das Repository klonen und Claude Code darin starten:

   ```bash
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   cd rom-cleanup-workbench
   claude
   ```

3. In eigenen Worten beschreiben, was sich ändern soll, zum Beispiel „Füge eine Option hinzu, die nur ZIP-Dateien zeigt“. Claude Code liest den Code, schlägt Änderungen vor und fragt, bevor es Dateien ändert oder Befehle ausführt. Lass es danach die Tests laufen (`python -m unittest` im Ordner `Rom Cleanup Workbench`) und probiere die Änderung auf einer Kopie deiner Sammlung aus.

Die Pläne früherer Änderungen stehen in `docs/`. Wer seine Änderungen weitergibt, muss sie ebenfalls unter der GPL veröffentlichen.

## Lizenz und Haftungsausschluss

Copyright (C) 2026 M. Kärcher

Rom Cleanup Workbench ist freie Software: Du kannst sie unter den Bedingungen der GNU General Public License, wie von der Free Software Foundation veröffentlicht, weitergeben und/oder verändern, entweder gemäß Version 3 der Lizenz oder (nach deiner Wahl) jeder späteren Version. Der vollständige Text steht in [LICENSE](<../LICENSE>); rechtlich gilt nur dieser englische Originaltext.

**Nutzung auf eigenes Risiko.** Das Programm löscht Dateien, und es gibt keinerlei Gewährleistung; wer es verwendet, trägt alle damit verbundenen Risiken selbst. Wir empfehlen dringend, es ausschließlich auf einer Kopie der eigenen ROM-Sammlung zu verwenden.

## Credits

- Idee: M. Kärcher
- Programmierung: Claude Code
