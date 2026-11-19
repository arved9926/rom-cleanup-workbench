# Rom Cleanup Workbench (deutsch)

Findet in einem Verzeichnis redundante Dateien anhand des Spielnamens und löscht sie auf Wunsch.
Benötigt Python 3.10 oder neuer, aber keine zusätzlichen Pakete.

## Aufruf

```bash
python redundanz_finder.py "D:\Spiele"
```

Das Programm öffnet das Analysefenster und zeigt dort alles an; im Terminal gibt es nichts aus und fragt nichts. Ohne Verzeichnis fragt das Fenster nach dem Ordner. Gelöscht wird nur nach der Rückfrage im Fenster. **Gelöschte Dateien landen nicht im Papierkorb.**

| Option | Wirkung |
| --- | --- |
| `--review alle` | Fenster für diesen Start mit `Alle Löschmarkierungen` öffnen |
| `--review probleme` | Fenster für diesen Start mit `Problematische Löschmarkierungen` öffnen |
| `--priority USA Europe Japan keine` | Priorität für diesen Lauf festlegen |
| `--delete-tag Proto Beta` | Zusatzinfos für diesen Lauf festlegen |
| `--config datei.json` | andere Konfiguration verwenden |
| `--report-only` | ohne Fenster: nur den Bericht im Terminal ausgeben |
| `--yes` | ohne Fenster: markierte Dateien ohne Rückfrage löschen |
| `--all` | mit `--report-only`: auch Spiele ohne markierte Dateien zeigen |

In VS Code: Ordner `Rom Cleanup Workbench (deutsch)` öffnen, mit F5 starten und das Verzeichnis eingeben.
Die Tests laufen über die Testansicht oder mit `python -m unittest`.

## Analysefenster

Das Fenster nennt oben in der grünen Zeile links `Rom Cleanup Workbench` und rechts den Ordner, darunter die aktive Priorität mit ihrer Quelle. Die grüne vorletzte Zeile zeigt den Stand, während der Analyse zum Beispiel `Analysiere: 120 von 2007 Dateien`. Zusätzlich erscheint dann in der Mitte ein Fortschrittsbalken. Fehler, etwa in der Konfiguration, zeigt es ebenfalls an, und solange die Analyse nicht klappt, lässt sich nichts löschen. Während des Löschens erscheint in der Mitte der Fortschrittsbalken, und die grüne Zeile zeigt zum Beispiel `Lösche: 120 von 500 Dateien`; bis das Löschen fertig ist, nimmt das Fenster keine Eingaben an. Nach dem Löschen meldet es das Ergebnis und entfernt die gelöschten Dateien aus der Liste, ohne den Ordner neu zu analysieren; Dateien, die sich nicht löschen ließen, bleiben markiert. `F5` analysiert den Ordner neu, wenn du das möchtest.

Ist im ganzen Ordner nichts markiert und keine Datei steht unter Verdacht, eine Status- oder Spielstanddatei zu sein, blinkt in der Mitte des Fensters `Nichts zu tun.`

Die drei Radio Buttons legen fest, was die Liste zeigt:

- `Problematische Löschmarkierungen`: nur Spiele mit markierter Datei, die als problematisch gelten (Vorgabe beim ersten Start)
- `Alle Löschmarkierungen`: alle Spiele mit markierter Datei
- `Alle Romdateien`: alle Spiele. Dann lassen sich auch deren Dateien mit `D` markieren, und problematische Fälle ohne markierte Datei, etwa ein nicht lesbares ZIP, erscheinen ebenfalls.

Das Fenster merkt sich die zuletzt gewählte Anzeige und die bestätigten Status- oder Spielstanddateien (Regel 9) in `redundanz_einstellungen.json` neben dem Programm.

| Taste | Wirkung |
| --- | --- |
| Pfeiltasten | Zeile wählen, mit Umschalt mehrere (zum Beispiel alle Discs eines Spiels) |
| `Tab` / `Umschalt+Tab` | zum nächsten / vorigen Spiel; die erste Datei des Spiels wird ausgewählt |
| `D` (Demote) | Datei zum Löschen markieren; sie rückt ans Ende ihres Spiels |
| `P` (Promote) | Datei behalten; sie rückt an die Stelle, die ihr nach den Regeln zusteht |
| `Strg` + Scrollrad | Schrift vergrößern oder verkleinern (8 bis 32 pt, gilt bis zum Schließen des Fensters) |
| `Strg+F` | zum Filterfeld |
| `Strg+L` | wie der Knopf `Ausführen...`: nach einer Rückfrage löschen und die vermuteten Status- oder Spielstanddateien bestätigen (Regel 9) |
| `Strg+O` | anderen Ordner wählen |
| `F5` | neu analysieren, liest auch die Konfiguration neu |
| `Esc` | schließen, ohne etwas zu löschen |

Horizontale Striche trennen die Spiele, und jedes zweite Spiel ist dunkelgrau hinterlegt. Die Spalte `Größe` zeigt die Größe jeder Datei in KB, aufgerundet wie im Windows Explorer (`1.234 KB`); `?` bedeutet, dass sich die Größe nicht lesen ließ. Die Größe wird während der Analyse gelesen. Behaltene Dateien stehen fett unter `Bleibt erhalten:`, zu löschende normal unter `Zum Löschen markiert`. Das Fenster zeigt weiße Schrift in Lucida Sans Typewriter 11 pt auf schwarzem Grund. Ist die Schrift nicht installiert, wählt Windows ohne Meldung eine Ersatzschrift. Von Hand verschobene Dateien sind braun hinterlegt und tragen den Hinweis `Von Hand`; ist die Zeile gerade ausgewählt, erscheint sie blau. Die Hinweise des Programms bleiben dabei unverändert, auch wenn sie sich auf eine Datei beziehen, die du verschoben hast.

`Problematische Löschmarkierungen` blendet die unproblematischen Spiele aus. **Deren markierte Dateien werden beim Löschen trotzdem mitgelöscht**; die Rückfrage nennt ihre Anzahl. Spiele, die du von Hand geändert hast, bleiben immer sichtbar, außer der Filter blendet sie aus.

### Filter

Das Filterfeld links in der untersten Zeile beschränkt die aktuelle Ansicht auf Spiele mit einem Dateinamen, der das Muster enthält. Ein Spiel bleibt vollständig, wenn eine seiner Dateien passt. Die Liste aktualisiert sich kurz nach dem Tippen; die Dateiinhalte werden nicht gelesen.

- `*` steht für beliebig viele Zeichen, `?` für genau eines. Alle anderen Zeichen, auch `[` und `]`, zählen wörtlich, und Groß- und Kleinschreibung zählt nicht.
- Das Muster darf überall im Namen stehen: `Beta`, `*Beta*` und `Mario?2` finden alle auch `Super Mario 2 (Beta).nes`. Entsprechend findet `S*` jeden Namen, der ein `S` enthält, nicht nur Namen, die damit beginnen.
- `Enter`, `Tab` und der Pfeil nach unten führen zurück zur Liste; `Esc` leert den Filter und führt zurück zur Liste.
- Solange der Cursor im Feld steht, schreiben die Tasten nur dort: `D`, `P`, `Strg+L`, `Strg+O`, `F5` und `Esc` führen ihre Listenfunktionen nicht aus.
- Der Filter bleibt nach `F5`, nach dem Löschen und nach dem Wechsel des Ordners aktiv. Er wird nicht gespeichert.

**Der Filter ändert nur die Anzeige. Markierte Dateien, die der Filter ausblendet, werden beim Löschen trotzdem mitgelöscht**; die Rückfrage nennt ihre Anzahl.

Als problematisch gilt ein Spiel, wenn

- keine seiner Dateien erhalten bliebe,
- der Inhalt eines markierten ZIPs sonst nirgends vorkommt (`WARNUNG`),
- ein ZIP defekt, verschlüsselt oder nicht lesbar ist,
- eine Datei als vermutete Status- oder Spielstanddatei erhalten bleibt (Regel 9),
- die Regeln nur durch einen `Gleichstand` entschieden haben,
- mehrere ZIPs derselben Version verschiedenen Inhalt haben,
- die Dateinamen das Spiel unterschiedlich schreiben (`Spiel 1-2` und `Spiel 12`),
- eine markierte Datei einen anderen Dateityp hat als die behaltenen (`.nes` und `.sfc`).

Das Fenster nutzt `tkinter`, das zur üblichen Python-Installation unter Windows gehört. Fehlt es, meldet das Programm das und löscht nichts.

## Konfiguration: `redundanz_config.json`

Die Datei liegt neben dem Programm und wird bei jeder Analyse neu gelesen. Zum Ändern der Priorität reicht es, die Reihenfolge in `region_priority` umzustellen und die Datei zu speichern:

```json
"region_priority": ["Germany", "Europe", "USA", "keine", "Japan"],
```

Bei einem Fehler in der Datei, etwa einem falsch geschriebenen Eintrag, findet keine Analyse statt, und es wird nichts gelöscht. Fehlt die Datei oder ein Eintrag, gelten die Standardwerte aus dem Programm; die Priorität ist dort USA, Europe, Japan, keine.

- `region_priority`: Regionen, die beste zuerst. `keine` steht für Dateien ohne bekannte Region.
- `region_aliases`: andere Schreibweisen einer Region, zum Beispiel `Europa` für `Europe`.
- `delete_tags`: Zusatzinfos, die immer zum Löschen führen. `Proto` passt auch auf `Proto 2`.
- `low_priority_tags`: Zusatzinfos mit der niedrigsten Priorität. `Beta` passt auch auf `Beta 2`.
- `part_tags`: Teile einer Version, zum Beispiel `Disc 1`.

## Regeln

Manche Dateien übergeht das Programm vollständig: Sie erscheinen nirgends und werden nie gelöscht.

- Dateien, deren Name mit `gamelist` beginnt, unabhängig von der Groß- und Kleinschreibung. Sie sind keine Romdateien.
- Versteckte Dateien: Namen mit einem Punkt am Anfang, etwa `.xxx` oder `.DS_Store`, und Dateien mit dem Windows-Attribut „versteckt“.

1. Dateien gehören zusammen, wenn der Text vor der ersten Klammer gleich ist. Groß- und Kleinschreibung, Leerzeichen, Bindestriche und Unterstriche zählen nicht, also `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. Damit gilt auch `Spiel 1-2` = `Spiel 12`. Außerdem gelten `und` = `and` = `&` sowie `The Spiel` = `Spiel The` = `Spiel, The` = `Spiel` als gleich. Ein `The` mitten im Namen zählt dagegen mit.
2. Dateien mit einer Zusatzinfo aus `delete_tags` werden immer markiert, auch wenn es die einzige Datei des Spiels ist.
3. Von den übrigen Dateien bleibt die mit der besten Region. Bei `(USA, Japan)` zählt die bessere der beiden.
4. Alle Dateien derselben Version bleiben zusammen erhalten, zum Beispiel `(Disc 1)` und `(Disc 2)` oder `.cue` und `.bin`. Alles andere wird markiert.
5. Eine Region, die nicht in `region_priority` steht, zählt wie `keine`. Das gilt auch für Angaben wie `(Rev 1)`.
6. Dateien mit einer Zusatzinfo aus `low_priority_tags` stehen hinter allen anderen, auch hinter Dateien ohne Region. Sie bleiben nur erhalten, wenn es keine andere Datei des Spiels gibt. Untereinander zählt wieder die Region, danach die Version aus Regel 7, danach die Nummer nach der Zusatzinfo: `Beta 2` gewinnt gegen `Beta 1`, und `Beta 1` gegen `Beta` ohne Nummer. Die Nummern werden numerisch verglichen (`Beta 10` vor `Beta 9`). Die unterlegene Datei bekommt den Hinweis `Ältere Beta`.
7. Bei gleicher Priorität gewinnt die höchste Versionsnummer, numerisch verglichen (`v1.10` vor `v1.9`). Erkannt werden in Klammern `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` und `Rev A`, im Spielnamen nur die Form `Spiel v1.1`, auch mit `-` oder `_` statt Leerzeichen. Eine Datei ohne Version verliert gegen eine mit Version. Die Region zählt vor der Version.
8. Danach gewinnt die Datei mit weniger Zusatzangaben, danach eine Datei ohne ZIP, danach das Alphabet. Der Bericht zeigt dann `Gleichstand` an.
9. Eine Datei, die kleiner als 1/4 der größten Datei des Spiels ist, wird vor den Regeln 3 bis 8 beiseitegelegt und bleibt erhalten: Sie könnte eine Status- oder Spielstanddatei sein. Sie kann deshalb weder gelöscht werden noch die echte ROM verdrängen, etwa `1941.state` die Datei `1941.zip`. Die Hinweisspalte zeigt dann `Verdacht auf Status- oder Spielstanddatei`, und das Spiel gilt als problematisch. Ein solches Spiel erscheint in allen drei Ansichten, auch wenn keine seiner Dateien markiert ist. Beim Löschen bestätigt das Programm alle verbliebenen verdächtigen Dateien als legitim: Sie bleiben, wo sie sind, werden weiterhin nie gelöscht und erscheinen nicht mehr in `Problematische Löschmarkierungen` und `Alle Löschmarkierungen`, auch nach `F5` oder einem neuen Start. Die Rückfrage nennt ihre Anzahl. Das Programm merkt sie sich mit Pfad und Größe in `redundanz_einstellungen.json`; ändert sich die Größe, steht die Datei wieder unter Verdacht. Ist nichts markiert, bietet `Strg+L` an, sie zu bestätigen, ohne etwas zu löschen. ZIPs zählen mit ihrer entpackten Größe. Das gilt nicht für eine kleine normale Datei neben einer großen normalen Datei ihrer eigenen Version, etwa eine `.cue` neben ihrer `.bin`, und nicht für Dateien, die wegen `delete_tags` oder eines defekten ZIPs markiert sind. Mit `D` lässt sich die Datei trotzdem von Hand markieren.

## ZIP-Dateien

Jede ZIP-Datei wird vollständig gelesen, auch wenn sie die einzige Datei eines Spiels ist. Ihr Inhalt wird per SHA-256 mit den anderen Dateien des Spiels verglichen.

- **Gleicher Inhalt wie eine behaltene Datei:** Die ZIP-Datei wird markiert, und der Bericht nennt die Datei mit dem gleichen Inhalt.
- **Bleiben nach der Auswahl ein ZIP und eine normale Datei übrig:** Das ZIP wird immer markiert, auch bei anderem Inhalt, wenn es als einzige Datei einen Teil wie `(Disc 1)` enthält oder wenn es nicht lesbar ist.
- **Mehrere ZIPs derselben Version mit anderem Inhalt:** Alle bleiben erhalten, und der Bericht weist darauf hin.
- **Markiert, aber Inhalt kommt in keiner behaltenen Datei vor:** Der Bericht zeigt `WARNUNG`. Die Datei bleibt markiert.
- **Keine Region oder Version im ZIP-Namen:** Die Angabe wird aus den Dateien im ZIP übernommen, sofern diese denselben Spielnamen tragen.
- **Defektes oder verschlüsseltes ZIP:** Die Datei wird immer markiert, auch wenn es die einzige Datei des Spiels ist. Der Inhalt eines verschlüsselten ZIPs wird dabei nicht geprüft.
- **Gesperrtes ZIP oder unbekanntes Verfahren (zum Beispiel Deflate64):** Das sagt nichts über den Zustand der Datei aus. Ohne normale Datei des Spiels bleibt sie erhalten und wird im Bericht genannt.
