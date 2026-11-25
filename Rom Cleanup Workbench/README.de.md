# Rom Cleanup Workbench

[English](README.md) · **Deutsch** · [Italiano](README.it.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md)

**Benutzerhandbuch mit Bildschirmfotos:** [PDF](<docs/Rom Cleanup Workbench - Benutzerhandbuch.pdf>) · [Word](<docs/Rom Cleanup Workbench - Benutzerhandbuch.docx>)

**Video:** [So funktioniert das Programm (YouTube)](https://youtu.be/D1yXZQXg-iM)

Findet doppelte ROM-Dateien in einem Verzeichnis anhand des Spielnamens und löscht sie auf Wunsch.
Braucht Python 3.10 oder neuer. Das Fenster braucht keine zusätzlichen Pakete; die Terminal-Version für Linux braucht Textual (siehe [Terminal-Version (Linux)](#terminal-version-linux)).
Das Programm spricht Englisch, Deutsch, Italienisch, Spanisch, Französisch und Japanisch (siehe [Sprache](#sprache)).

**Wichtig:** Wende dieses Programm nicht auf deine originalen ROM-Dateien an. Lege eine Kopie deines ROM-Repositorys an und nutze das Programm, um die Bereinigung ausschließlich an der Kopie vorzunehmen.

## Installation

Ein GitHub-Konto brauchst du nicht. Jeder Befehl steht in einem eigenen Kasten; gib ihn so ein und drücke Enter.

### Windows

Alle Befehle gibst du in PowerShell ein.

1. **Prüfen, ob Python installiert ist:**

   ```powershell
   python --version
   ```

   - **Es erscheint `Python 3.10` oder höher:** Python ist da, weiter mit Schritt 2.
   - **Es erscheint eine Fehlermeldung oder eine ältere Version:** Python 3.10 oder neuer von [python.org/downloads](https://www.python.org/downloads/) herunterladen und installieren. Bietet das Installationsprogramm „Add python.exe to PATH“ an, diese Option anhaken. `tkinter` für das Fenster ist dabei. Danach ein neues PowerShell-Fenster öffnen und die Prüfung wiederholen.

2. **Prüfen, ob Git installiert ist:**

   ```powershell
   git --version
   ```

   - **Es erscheint eine Versionsnummer, zum Beispiel `git version 2.47.0`:** Das Programm mit Git herunterladen:

     ```powershell
     git clone https://github.com/arved9926/rom-cleanup-workbench.git
     ```

   - **Es erscheint eine Fehlermeldung:** Das Programm als ZIP-Datei herunterladen. Im Browser geht das auf der [GitHub-Seite](https://github.com/arved9926/rom-cleanup-workbench) mit **Code** und dann **Download ZIP**; danach die Datei mit der rechten Maustaste entpacken (**Alle extrahieren...**) und den Ordner `rom-cleanup-workbench-main` in `rom-cleanup-workbench` umbenennen. Oder in PowerShell, Befehl für Befehl:

     ```powershell
     Invoke-WebRequest https://github.com/arved9926/rom-cleanup-workbench/archive/refs/heads/main.zip -OutFile rom-cleanup-workbench.zip
     ```

     ```powershell
     Expand-Archive rom-cleanup-workbench.zip -DestinationPath .
     ```

     ```powershell
     Rename-Item rom-cleanup-workbench-main rom-cleanup-workbench
     ```

3. **In den Programmordner wechseln:**

   ```powershell
   cd "rom-cleanup-workbench\Rom Cleanup Workbench"
   ```

   Für das Fenster sind keine weiteren Pakete nötig. Nur wer unter Windows die Terminal-Version nutzen will, installiert zusätzlich Textual:

   ```powershell
   python -m pip install textual==8.2.8
   ```

### Linux

Alle Befehle gibst du in einem Terminal ein. Die Beispiele gelten für Debian und Ubuntu.

1. **Prüfen, ob Python installiert ist:**

   ```bash
   python3 --version
   ```

   - **Es erscheint `Python 3.10` oder höher:** Python ist da, weiter mit Schritt 2.
   - **Es erscheint eine Fehlermeldung oder eine ältere Version:** Python installieren:

     ```bash
     sudo apt install python3 python3-venv
     ```

   Das Paket `python3-tk` ist nur nötig, wenn du unter Linux mit grafischer Anzeige das Fenster statt der Terminal-Version nutzen willst.

2. **Prüfen, ob Git installiert ist:**

   ```bash
   git --version
   ```

   - **Es erscheint eine Versionsnummer:** Das Programm mit Git herunterladen:

     ```bash
     git clone https://github.com/arved9926/rom-cleanup-workbench.git
     ```

   - **Es erscheint eine Fehlermeldung:** Das Programm als ZIP-Datei herunterladen und entpacken, Befehl für Befehl:

     ```bash
     sudo apt install wget unzip
     ```

     ```bash
     wget https://github.com/arved9926/rom-cleanup-workbench/archive/refs/heads/main.zip -O rom-cleanup-workbench.zip
     ```

     ```bash
     unzip rom-cleanup-workbench.zip
     ```

     ```bash
     mv rom-cleanup-workbench-main rom-cleanup-workbench
     ```

3. **In den Programmordner wechseln:**

   ```bash
   cd "rom-cleanup-workbench/Rom Cleanup Workbench"
   ```

4. **Textual in einer virtuellen Umgebung installieren:**

   ```bash
   python3 -m venv ~/venvs/rom-cleanup-workbench
   ```

   ```bash
   ~/venvs/rom-cleanup-workbench/bin/pip install textual==8.2.8
   ```

## Aufruf

### Windows

Ein Terminal (zum Beispiel PowerShell) öffnen, in den Ordner `Rom Cleanup Workbench` wechseln und das Programm mit dem Ordner deiner Spiele starten:

```powershell
cd "rom-cleanup-workbench\Rom Cleanup Workbench"
```

```powershell
python rom_cleanup_workbench.py "D:\Games"
```

Ohne Ordner öffnet das Programm den zuletzt gewählten Ordner wieder, einen `roms`-Ordner mit seiner Übersicht, jeden anderen direkt; beim ersten Mal fragt das Fenster danach. Wer die Terminal-Version will, hängt `--tui` an.

### Linux

In den Ordner `Rom Cleanup Workbench` wechseln und das Programm mit der Python-Version der virtuellen Umgebung und dem Ordner deiner Spiele starten:

```bash
cd "rom-cleanup-workbench/Rom Cleanup Workbench"
```

```bash
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
| `--scan-all` | ohne Fenster: alle Plattform-Ordner des angegebenen `roms`-Ordners scannen und in seiner Datenbank speichern; löscht nichts |
| `--deep-scan` | mit `--scan-all`: Tiefenscan, jede Datei neu lesen statt nur neue und geänderte (früher `--full`, das weiter geht) |
| `--write-gamelists` | ohne Fenster: die `gamelist.xml` jeder Plattform des angegebenen `roms`-Ordners aus seiner Datenbank schreiben; jede bisherige Datei bleibt als Kopie |
| `--all` | mit `--report-only`: auch Spiele ohne markierte Dateien zeigen |
| `--tui` | die Terminal-Version statt des Fensters verwenden (automatisch unter Linux ohne grafische Anzeige) |
| `--ascii` | Terminal-Version nur mit ASCII-Zeichen (automatisch auf der Linux-Konsole); schließt `--tui` ein |

Die Optionen der Befehlszeile und ihre Hilfe (`--help`) sind immer auf Englisch.

Die Tests laufen mit `python -m unittest`.

## Die Sammlung: viele Plattformen und die Datenbank

Meist liegen die Spiele nach Plattformen getrennt in einem gemeinsamen Ordner, etwa `roms/nes`, `roms/snes`, `roms/n64`. Wählst du diesen `roms`-Ordner, zeigt das Programm die **Übersicht** aller Plattformen. Ab dann startet es immer mit dem zuletzt gewählten Ordner, bei einem `roms`-Ordner also mit seiner Übersicht. Als `roms`-Ordner gilt ein Ordner, der schon eine Datenbank hat oder selbst keine ROM-Dateien, aber Unterordner enthält. Beipack-Dateien wie `info.txt`, Bilder oder PDFs zählen dabei nicht als ROM-Dateien. Jeder andere Ordner wird wie bisher allein analysiert, ohne Datenbank.

**Die Datenbank.** Beim ersten Öffnen legt das Programm im `roms`-Ordner den versteckten Ordner `.rom_cleanup_workbench` mit einer SQLite-Datenbank an. Das ist das Einzige, was es in deine Sammlung schreibt. Gespeichert werden die Ergebnisse jedes Scans: Dateien, Größen, Änderungszeiten, der Inhalt der ZIPs mit Prüfsummen. Die Entscheidungen rechnet das Programm daraus beim Öffnen in einem Augenblick neu. Geänderte Einstellungen wirken deshalb sofort, ohne neuen Scan. Außerdem stehen dort die Änderungen von Hand (`k`/`x`), die bestätigten Status- und Spielstanddateien und die eigenen Einstellungen einzelner Plattformen. Maßgeblich ist der Ordner: Gibt es einen Plattform-Ordner nicht mehr, löscht die Übersicht beim Öffnen alles, was die Datenbank über ihn wusste, auch eigene Einstellungen und `keine Spiele`. Ein neuer Ordner mit demselben Namen beginnt dann von vorn. Ist der `roms`-Ordner selbst nicht erreichbar, etwa ein Netzlaufwerk ohne Verbindung, wird nichts gelöscht.

**Die Übersicht** zeigt je Plattform: Dateien, Spiele, zum Löschen markierte Dateien, problematische Spiele, den letzten Scan und den Stand (`nicht gescannt`, `aktuell` oder `geändert`, wenn seitdem Dateien hinzukamen, wegfielen oder sich geändert haben), darunter die Summe. Ein Strich trennt die Summe von den Plattformen; der Stand `geändert` steht in Gelb (im Fenster die ganze Zeile). Ein Klick auf die Überschrift `Plattform`, `Dateien`, `Spiele`, `Zum Löschen` oder `Problematisch`, `Infos` oder `Gamelist-Probleme` sortiert danach, ein zweiter Klick andersherum; ein Pfeil zeigt die Richtung, die Summe bleibt unten, Plattformen ohne Zahlen kommen zuletzt, und die Wahl bleibt gespeichert.

| Knopf | Taste | Wirkung |
| --- | --- | --- |
| `Öffnen` | `Enter` | die markierte Plattform in der gewohnten Liste öffnen (auch Doppelklick) |
| `Scannen` | `r` oder `F5` | die markierte Plattform scannen und öffnen |
| `Alle scannen` | `a` | alle Plattformen nacheinander scannen; jede wird sofort gespeichert und ihre Zahlen erscheinen gleich in der Übersicht; `Abbrechen` behält die fertigen; löscht nichts |
| `Tiefenscan` | `d` | Schalter (roter Punkt) für Scannen und Alle scannen: jede Datei neu lesen statt nur neue und geänderte |
| `Leere ausblenden` | `h` | Schalter (roter Punkt): Ordner ohne Spieldatei ausblenden, etwa `bios` oder einen Ordner nur mit `info.txt`; Beipack-Dateien zählen nicht als Spieldatei; die Wahl bleibt gespeichert |
| `Ordner...` | `f` | einen anderen `roms`-Ordner wählen |
| | `n` | den markierten Ordner als `keine Spiele` kennzeichnen oder das wieder aufheben (siehe unten) |
| | `w` | die `gamelist.xml` der markierten Plattform aus der Datenbank schreiben (nach einer Frage) |
| | `q` oder `Esc` | das Programm schließen |

Die Tasten gelten im Fenster und in der Terminal-Version gleich. Die Zeile über der Tabelle nennt die wichtigsten, `F1` oder `?` zeigt alle.

**Scannen.** Ein Scan ist normalerweise schnell: Er liest nur neue und geänderte Dateien (erkannt an Name, Größe und Änderungszeit) und übernimmt alles andere aus der Datenbank. Mit `Tiefenscan` wird jede Datei neu gelesen. `F5` in der Liste scannt die geöffnete Plattform schnell. Ausführen trägt gelöschte und umbenannte Dateien sofort ein, ein neuer Scan ist danach nicht nötig.

**Zurück zur Übersicht** führt in der Liste `Esc`, `q` oder der Knopf `Übersicht`, in der Terminal-Version auch `o`. `Esc` oder `q` in der Übersicht beendet das Programm; wer ganz hinaus will, drückt also zweimal.

**Die gamelist.xml.** Liegt in einem Plattform-Ordner eine `gamelist.xml` (EmulationStation, RetroPie, Batocera, ES-DE, ARRM), liest der Scan sie ein und übernimmt, was sich prüfen lässt, in die Datenbank: Name, Beschreibung, Bewertung, Datum, Entwickler, Herausgeber, Genre, Spieler, Region, Favorit, Spielzeit und die Verweise auf Medien wie Bilder und Videos, getrennt nach Kategorie (`wheel` und `logo` bleiben verschieden, auch wenn sie auf dieselbe Datei zeigen). Alle übrigen Felder werden unverändert mitgeführt. Die Zahl in `<genreid>` (etwa `1538`) stammt aus der Genre-Liste von Recalbox: Hauptgenre × 256 plus Untergenre, also `1538` = `0x0602` = Sport, Untergenre 2 „Sportsimulation“; Werkzeuge wie ARRM schreiben sie beim Scrapen mit. Die Spielansicht zeigt die Zahl mit ihrem Namen, zum Beispiel „1538 – Sportsimulation (Sport)“. Mit den Genre-Nummern von ScreenScraper hat sie nichts zu tun. Hat eine Plattform Genre-Nummern, zeigt die Liste eine Spalte `Genre`. Ein Klick auf ihre Überschrift sortiert die Spiele nach Genre (in der Reihenfolge der Recalbox-Liste, Spiele ohne Genre zuletzt, innerhalb eines Genres nach Name), ein zweiter Klick oder ein Klick auf `Datei` wieder nach Name; die Wahl bleibt gespeichert. Im Bearbeiten-Formular wählt `Genre (Recalbox-Liste)` die Nummer aus allen Recalbox-Genres; das Textfeld `Genre` bleibt daneben frei. Eine von Hand gewählte Nummer bleibt bei einem neuen Import erhalten. Nicht übernommen und als Problem gezählt werden Einträge, deren ROM nicht im Plattform-Ordner liegt, und Verweise auf Dateien, die es nicht gibt. Pfade eines anderen Rechners wie `/home/pi/RetroPie/roms/nes/…` werden auf den Plattform-Ordner umgeschrieben und als Hinweis gezählt. Gelesen wird die Datei nur, wenn sie sich geändert hat; eine geänderte `gamelist.xml` setzt den Stand auf `geändert`. Die Datei selbst wird nicht verändert. Die Datenbank ist der Speicher, nicht die `gamelist.xml`: Wird sie gelöscht, bleiben die Informationen; verschwindet dagegen ein ROM oder ein Medium aus dem Ordner, verschwindet es auch aus der Datenbank, und mit einem gelöschten ROM gehen seine Informationen. Die Übersicht zeigt in `Infos`, wie viele ROMs Informationen haben, und in `Gamelist-Probleme`, was nicht übernommen wurde; hinter dem Plattformnamen steht grau, wie viele Einträge übernommen wurden. Ist die Datei kaputt, wird nichts übernommen und das Bisherige bleibt.

**gamelist.xml und Medien außerhalb des Plattform-Ordners.** Hat der Plattform-Ordner keine eigene `gamelist.xml`, sucht der Workbench dort, wo die Frontends sie ablegen, in dieser Reihenfolge: `~/ES-DE/gamelists/<Plattform>/` (ES-DE), `~/.emulationstation/gamelists/<Plattform>/` (EmulationStation, RetroPie) und unter Linux `/etc/emulationstation/gamelists/<Plattform>/`. Der Name des Plattform-Ordners gilt dabei als Systemname. Pfade wie `%ROMPATH%/nes/…` werden auf den Plattform-Ordner bezogen. Die graue Zeile, der Bericht und die Frage vor dem Schreiben nennen den Ort; geschrieben wird an derselben Stelle, mit Sicherungskopie dort. Medien sucht der Workbench zusätzlich in `~/ES-DE/downloaded_media/<Plattform>/` (oder dem in den ES-DE-Einstellungen gewählten Medienordner) sowie in `~/.emulationstation/downloaded_media/` und `downloaded_images/`. Solche Medien außerhalb der Sammlung werden nur angezeigt und in die `gamelist.xml` geschrieben, aber nie gelöscht oder umbenannt.

**Medien in den Unterordnern.** Bei jedem Scan sucht der Workbench außerdem in allen Unterordnern einer Plattform nach Bildern, Videos und Handbüchern, die die `gamelist.xml` nicht schon nennt. Zugeordnet wird nur, was der Name eindeutig sagt: ein Ordner je Kategorie mit dem Namen des ROMs (`wheel/10yard.png`, `marquees/10yard.png`) oder ROM-Name, Trennzeichen (`-`, `.` oder `_`) und Kategorie in einem beliebigen Ordner (`downloaded_images/10yard-wheel.png`, `game.image.jpg`). Passen mehrere ROMs, gewinnt der längste Name (`sf2ce-image.png` gehört zu `sf2ce.zip`, nicht zu `sf2.zip`); eine Zuordnung nach Ähnlichkeit gibt es nicht. Was nicht eindeutig ist, bleibt ohne ROM. Jedes Spiel-ROM ohne Eintrag in der `gamelist.xml` bekommt einen leeren Eintrag mit dem Namen vor der ersten Klammer; BIOS-Dateien (`BIOS` in einer Klammer oder bekannte Namen wie `neogeo`, `pgm`, `skns`) gelten als kein Spiel und bekommen keine Medien. Hinter dem Plattformnamen steht grau, wie viele Medien zugeordnet sind und wie viele ohne ROM blieben; `Infos` zählt auch leere Einträge, zu denen Medien gefunden wurden.

**Spielansicht, Namensspalte und Bericht.** Hat eine Plattform Informationen, zeigt die Liste eine Spalte `Name` mit dem Namen aus der `gamelist.xml`, mit `★` bei Favoriten und `kein Spiel` bei BIOS-Dateien. `Enter` (im Fenster auch ein Doppelklick auf eine Datei) zeigt an Stelle der Liste alles, was über das Spiel bekannt ist: seine Dateien mit ihrer Entscheidung, die Felder wie Beschreibung, Bewertung (als x / 5), Datum, Entwickler, Spielzeit und Favorit, die übrigen Felder der `gamelist.xml` und die Medien nach Kategorie; Vorschaubilder gibt es bewusst nicht. `g` zeigt den Gamelist-Bericht: was nicht übernommen wurde und warum, die Hinweise, ROMs ohne Informationen, Medien ohne ROM und die Dateien, die kein Spiel sind. `n` kennzeichnet die markierten Dateien als `kein Spiel` oder hebt das auf; eine spätere `gamelist.xml` ändert daran nichts. Ob eine Datei behalten oder gelöscht wird, entscheiden weiter die Regeln. Die Zusammenfassung von `gamelist.xml` und Medien steht grau in einer eigenen Zeile unter der Plattformzeile.

**Löschen und Umbenennen nehmen die Medien mit.** Löscht `Ausführen...` ein ROM, werden seine Medien mit gelöscht, Bilder, Videos und Handbücher aus der `gamelist.xml` wie aus den Unterordnern; die Frage vor dem Löschen nennt ihre Zahl. Ein Medium, das auch ein verbleibendes ROM nutzt, bleibt. Mit einem gelöschten ROM gehen auch seine Informationen, Favorit und Spielzeit eingeschlossen. Entfernt `Ausführen...` die Nummer vor einem Namen, werden Medien, deren Name mit dem alten ROM-Namen beginnt, mit umbenannt (`01 - Alpha (USA)-image.png` wird `Alpha (USA)-image.png`). Die `gamelist.xml` selbst wird dabei nicht geändert.

**Spielinformationen bearbeiten.** In der Spielansicht öffnet `e` ein Formular für die Datei: Name, Sortiername, Beschreibung, Bewertung (0 bis 5 Sterne, auch 3,5), Erscheinungsdatum (`JJJJ`, `JJJJ-MM` oder `JJJJ-MM-TT`), Entwickler, Herausgeber, Genre, Spieler, Region, Sprachen sowie Favorit, Ausgeblendet und Für Kinder. Spielzeit, Spielzähler und die Kennung bleiben, wie Frontend und Scraper sie führen. `Strg+S` oder `Speichern` speichert, `Esc` oder `Abbrechen` geht ohne Speichern zur Spielansicht zurück; ein falscher Wert wird genannt, und das Formular bleibt offen. Geänderte Felder tragen in der Spielansicht ein `✎`; ein neuer Import der `gamelist.xml` lässt sie, wie sie sind. Ein leerer Eintrag wird durch das Bearbeiten zu einem richtigen. Beim Schreiben der `gamelist.xml` kommen die Änderungen mit hinein.

**Die gamelist.xml schreiben.** Nur auf Wunsch schreibt der Workbench die `gamelist.xml` einer Plattform aus seiner Datenbank neu: mit `w` in der Plattform oder in der Übersicht für die markierte Plattform, mit `--write-gamelists` für alle. Nach einer Bereinigung, die Dateien gelöscht hat, bietet er es an, wenn die Plattform eine `gamelist.xml` hat. Vorher wird die bisherige Datei als `gamelist.xml.<Datum_Uhrzeit>.bak` gesichert; die letzten drei Kopien bleiben, ältere werden gelöscht. Die neue Datei entsteht erst unter einem anderen Namen und ersetzt die alte dann in einem Schritt, sodass nie eine halbe Datei liegen bleibt. Sie enthält alle Spiele, auch die mit leerem Eintrag, aber keine BIOS-Dateien und anderen Nicht-Spiele; dazu alle bekannten Felder, die Medien je Kategorie (eine Datei in zwei Kategorien steht zweimal da), die Kennung und alle übrigen Felder, wie sie gelesen wurden. Werte, die dem Standard entsprechen, fehlen wie bei EmulationStation. Im `<provider>`-Block steht als Software `RCW` (Rom Cleanup Workbench) mit unserer GitHub-Seite; das System bleibt. Danach gilt die Datei als eingelesen.

**Ordner ohne Spiele.** Ein Ordner wie `bios` oder `saves` enthält keine Spiele. `n` kennzeichnet den markierten Ordner als `keine Spiele`: Er wird weder gescannt (auch nicht von `Alle scannen` und `--scan-all`) noch geöffnet, zählt nicht in der Summe, und `Leere ausblenden` blendet ihn aus. Was die Datenbank über ihn wusste, wird gelöscht. Ein zweites `n` hebt das wieder auf; der Ordner ist dann `nicht gescannt`. Einen Knopf dafür gibt es bewusst nicht.

**Änderungen von Hand** (`k`/`x`) bleiben gespeichert, auch nach dem Schließen, bis du ausführst oder die Plattform neu scannst. Ändert sich eine Datei, verfällt ihre Änderung von Hand.

**Eigene Einstellungen je Plattform.** Ist eine Plattform geöffnet, zeigen die Einstellungen oben `Allgemeine Einstellungen` oder `Plattformspezifische Einstellungen für NES`. Mit der plattformspezifischen Wahl gelten Priorität, Löschwörter und die Wahl zwischen normaler Datei und ZIP nur für diese Plattform; sie liegen in der Datenbank, `redundanz_config.json` bleibt der Standard für alle anderen. Eine neue eigene Einstellung beginnt mit den Werten des Standards; zurück auf `Allgemeine Einstellungen` verwirft sie. Die Zeile unter der Überschrift der Einstellungen nennt, wo gespeichert wird: `redundanz_config.json` oder, bei der plattformspezifischen Wahl, die Datenbank der Sammlung (die Sprache bleibt in `redundanz_config.json`). Die Sprache gilt immer für alles. In der Übersicht steht hinter solchen Plattformen ein `*`.

**Ohne Fenster** scannt `--scan-all` alle Plattformen, etwa über Nacht:

```powershell
python rom_cleanup_workbench.py "D:\roms" --scan-all
```

Mit `--deep-scan` wird jede Datei neu gelesen (Tiefenscan). Gelöscht wird dabei nie etwas.

## Analysefenster

Da die ZIP-Dateien entpackt werden müssen, um Größe, SHA-256-Prüfsumme und Namen ihres Inhalts zu erhalten, kann es nach der Auswahl eines Verzeichnisses einen Moment dauern, bis die Ergebnisse angezeigt werden.

Die grüne Zeile oben zeigt links `Rom Cleanup Workbench` und rechts den Ordner; darunter steht in Grün `Plattform:` mit dem Namen des geöffneten Ordners in Fett, bei eigenen Einstellungen der Plattform mit `*` dahinter wie in der Übersicht; danach folgt eine Leerzeile. Rechts daneben stehen die wichtigsten Tasten der Ansicht, in der Liste `x Löschen`, `k Behalten`, `Enter Bereinigung durchführen` und `F1 / ? Hilfe: weitere Tasten`. `F1` oder `?` zeigt an der Stelle der Liste alle Tasten, nach Themen geordnet; `Esc`, `F1` oder `?` schließt sie wieder. In der Übersicht zeigen beide die Tasten der Übersicht und darunter unter `Gut zu wissen`, was die Stände, Scannen und Tiefenscan bedeuten. Die geltende Priorität zeigen die Einstellungen. In der Übersicht steht das Wort `Sammlung` ebenfalls in Grün. Die grüne vorletzte Zeile zeigt den Status, während der Analyse zum Beispiel `Analysiere: 120 von 2007 Dateien`. Solange erscheint auch ein Fortschrittsbalken in der Mitte. Das Fenster zeigt auch Fehler, etwa in der Konfiguration, und solange die Analyse scheitert, lässt sich nichts löschen. Beim Löschen erscheint der Fortschrittsbalken in der Mitte, und die grüne Zeile zeigt zum Beispiel `Lösche: 120 von 500 Dateien`; das Fenster nimmt keine Eingaben an, bis das Löschen fertig ist. Danach meldet es das Ergebnis und entfernt die gelöschten Dateien aus der Liste, ohne den Ordner neu zu analysieren; Dateien, die sich nicht löschen ließen, bleiben markiert. `F5` analysiert den Ordner neu, wenn du das willst.

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
| `s` | wie die Schaltfläche `Einstellungen...`: die Einstellungen für Sprache, Priorität, Löschwörter und ZIP oder normale Datei zeigen oder ausblenden (siehe [Einstellungen](#einstellungen)) |
| `/` | ins Filterfeld wechseln |
| `F12` | wie die Schaltfläche `Ausführen...`: nach einer Bestätigung löschen, die Nummer vor den behaltenen Dateinamen entfernen (Regel 10) und die vermuteten Status- oder Spielstanddateien bestätigen (Regel 9) |
| `f` | einen anderen Ordner wählen, im Fenster an der Stelle der Liste: Ordner mit dem Pfeil öffnen, mit Doppelklick sofort auswählen, oder einen Pfad in `Pfad:` tippen, dann `Auswählen` oder `Enter`; `Abbrechen` oder `Esc` behalten den aktuellen Ordner |
| `r` oder `F5` | neu analysieren, liest auch die Konfiguration neu |
| `c` | die Credits zeigen |
| `Enter` | in einer Plattform der Sammlung: alles, was über das markierte Spiel bekannt ist (auch Doppelklick im Fenster); `Enter`, `Esc` oder `q` schließt |
| `n` | in einer Plattform der Sammlung: die markierten Dateien als `kein Spiel` kennzeichnen (etwa eine BIOS-Datei) oder das aufheben |
| `g` | in einer Plattform der Sammlung: der Gamelist-Bericht der Plattform |
| `e` | in der Spielansicht: die Informationen des Spiels bearbeiten; `Strg+S` speichert, `Esc` geht zurück |
| `w` | in einer Plattform der Sammlung: ihre `gamelist.xml` aus der Datenbank schreiben (nach einer Frage) |
| `F1` oder `?` | alle Tasten zeigen oder wieder ausblenden |
| `q` oder `Esc` | schließen, ohne etwas zu löschen; in einer Plattform der Sammlung führen beide erst zurück zur Übersicht; nach Änderungen von Hand fragt das Programm vorher |

Waagerechte Linien trennen die Spiele, und jedes zweite Spiel hat einen dunkelgrauen Hintergrund. Dateien, die erhalten bleiben, stehen in Grün, Dateien, die zum Löschen markiert sind, in Rot. Die Spalte `Größe` zeigt die Größe jeder Datei in KB, aufgerundet wie im Windows-Explorer (`1.234 KB`); `?` heißt, dass sich die Größe nicht lesen ließ. Die Größe wird bei der Analyse gelesen. Behaltene Dateien stehen fett unter `Bleibt erhalten:`, zu löschende Dateien in normaler Schrift unter `Zum Löschen markiert`. Das Fenster zeigt weiße Schrift in Lucida Sans Typewriter 11 pt auf schwarzem Grund. Ist die Schrift nicht installiert, nimmt Windows stillschweigend einen Ersatz. Von Hand verschobene Dateien haben einen braunen Hintergrund und tragen den Hinweis `Von Hand`; solange die Zeile gewählt ist, erscheint sie blau. Die Hinweise des Programms bleiben unverändert, auch wenn sie sich auf eine Datei beziehen, die du verschoben hast.

`Problematische Löschmarkierungen` blendet die unproblematischen Spiele aus. **Ihre markierten Dateien werden beim Löschen trotzdem gelöscht**; die Bestätigung nennt ihre Anzahl. Spiele, die du von Hand geändert hast, bleiben immer sichtbar, außer der Filter blendet sie aus.

### Filter

Das Filterfeld links in der unteren Zeile schränkt die aktuelle Ansicht auf Spiele ein, deren Dateiname das Muster enthält. Ein Spiel bleibt vollständig, wenn eine seiner Dateien passt. Die Liste folgt kurz nach dem Tippen; der Inhalt der Dateien wird nicht gelesen.

- `*` steht für beliebig viele Zeichen, `?` für genau eines. Alle anderen Zeichen, auch `[` und `]`, zählen wörtlich, und Groß- und Kleinschreibung zählt nicht. Leerzeichen am Anfang und am Ende zählen nur in Anführungszeichen: `" by "` findet `Mario by Mick`, aber nicht `Moby Dick`; ohne Anführungszeichen findet `by` beide.
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
- **Gleiches Spiel als normale Datei und als ZIP-Datei:** Legt fest, welche der beiden erhalten bleibt, wenn beide dieselbe Version sind. `Normale Datei behalten` (Vorgabe) markiert die ZIP-Datei, `ZIP-Datei behalten` markiert die normalen Dateien (siehe [ZIP-Dateien](#zip-dateien)).
- **Favoriten und gespielte Spiele (gamelist.xml):** `Nur Hinweis in der Liste` (Vorgabe) lässt die Regeln entscheiden; eine Datei, die gelöscht werden soll und laut `gamelist.xml` Favorit ist oder Spielzeit hat, bekommt den Hinweis `Favorit oder gespielt – wird gelöscht`. `Bevorzugt behalten` behält innerhalb eines Spiels die Datei mit Favorit, sonst die mit der meisten Spielzeit; hatten die Regeln eine andere einzelne Datei behalten, weicht diese, und die Spielstände folgen der behaltenen Datei. Gilt allgemein oder je Plattform (`prefer_played` in der Konfiguration).

`Speichern` schreibt die Datei und analysiert den Ordner neu, wenn sich die Priorität, die Löschwörter oder die Wahl zwischen normaler Datei und ZIP-Datei geändert haben; hast du Markierungen von Hand geändert, fragt das Programm vorher, weil diese Änderungen verloren gehen. Alle anderen Einträge der Datei bleiben, wie sie sind. Falsche Werte, etwa eine leere Regionsliste oder dieselbe Region zweimal, werden gemeldet, es wird nichts geschrieben, und die Einstellungen bleiben offen. Lässt sich die Datei nicht lesen, öffnen sich die Einstellungen nicht, damit sie keine Einträge überschreiben können, die sie nicht kennen. Mit `--config` bearbeiten die Einstellungen diese Datei; mit `--priority` gilt für diesen Lauf weiter die dort angegebene Priorität.

Ein Spiel gilt als problematisch, wenn

- keine seiner Dateien erhalten bliebe,
- ein markiertes ZIP (oder, mit `ZIP-Datei behalten`, eine markierte normale Datei) dieselbe Fassung ist wie eine behaltene Datei, aber einen anderen Inhalt hat (`Gleiche Fassung wie die behaltene Datei, aber anderer Inhalt`): Welcher Dump ist der richtige?,
- ein ZIP defekt, verschlüsselt oder nicht lesbar ist,
- eine Datei als vermutete Status- oder Spielstanddatei erhalten bleibt (Regel 9),
- die Regeln nur durch einen `Gleichstand` entschieden haben,
- mehrere ZIPs derselben Version unterschiedlichen Inhalt haben,
- die Dateinamen das Spiel unterschiedlich schreiben (`Title 1-2` und `Title 12`),
- eine markierte Datei einen anderen Dateityp hat als die behaltenen (`.nes` und `.sfc`).

Das Fenster verwendet `tkinter`, das zur üblichen Python-Installation unter Windows gehört. Fehlt es, meldet das Programm das und löscht nichts.

## Nach der maschinellen Bereinigung

Auch nach der maschinellen Bereinigung können noch redundante Spielversionen vorhanden sein. Diese kannst du am einfachsten über die Filterfunktion finden (Taste `/` und dann den Namen des Spiels). Danach kannst du dann die noch zu löschenden Dateien markieren.

## Terminal-Version (Linux)

Dasselbe Programm läuft auch in einem Textterminal, zum Beispiel über SSH (PuTTY, MobaXterm), in `tmux` oder auf der Linux-Konsole. Es zeigt dieselbe Liste, wendet dieselben Regeln an und teilt `redundanz_config.json`, `rom_cleanup_workbench_settings.json` und `translations.py` mit dem Fenster.

Unter Linux startet sie von selbst, wenn es keine grafische Anzeige gibt (weder `DISPLAY` noch `WAYLAND_DISPLAY` ist gesetzt, wie über SSH). `--tui` startet sie überall sonst, auch unter Windows; nimm es, wo es eine grafische Anzeige gibt, du aber das Terminal willst, zum Beispiel in MobaXterm oder unter WSL.

Sie braucht [Textual](https://textual.textualize.io/) (getestet mit 8.2.8). Wie du es installierst und das Programm startest, steht unter [Installation](#installation) und [Aufruf](#aufruf).

Ohne Textual sagt das Programm das und löscht nichts. Der Bildschirm hat die Zeilen des Fensters von oben nach unten: die grüne Titelzeile mit dem Ordner, die Plattform mit den wichtigsten Tasten, die Liste, das Filterfeld, die drei Ansichten und die grüne Statuszeile. In der Liste beginnt jedes Spiel mit seinem Namen in Fettschrift, gefolgt von Strichen bis zum rechten Rand; ein Hinweis wie `Unterschiedliche Schreibweisen des Namens` steht in dieser Zeile. In einem schmalen Terminal, etwa den 80 Spalten von PuTTY, brechen lange Dateinamen und Hinweise in ihrer Spalte um, statt den Bildschirm zu verlassen. `Nichts zu tun.` blinkt mit dem eigenen Blinken des Terminals; in PuTTY muss blinkender Text eventuell erst eingeschaltet werden. Fragen und Meldungen erscheinen in einem Rahmen über der Liste, mit Schaltflächen in der Sprache des Programms; `Nein` ist vorgewählt.

Rechts neben der Plattform stehen die wichtigsten Tasten, `F1` oder `?` zeigt alle, nach Themen geordnet. Fenster und Terminal-Version haben dieselben Tasten.

| Taste | Wirkung |
| --- | --- |
| Pfeiltasten | eine Zeile wählen, mit Umschalt mehrere |
| `Tab` / `Umschalt+Tab` | nächstes / voriges Spiel; seine erste Datei wird gewählt |
| `x` / `k` | die gewählten Dateien zum Löschen markieren / behalten |
| `1` `2` `3` | die Ansichten `Problematische Löschmarkierungen`, `Alle Löschmarkierungen`, `Alle Romdateien` |
| `/` | ins Filterfeld wechseln (`Enter`, `Tab` oder der Pfeil nach unten führen zurück, `Esc` leert) |
| `F12` | ausführen: nach einer Bestätigung löschen (wie `Ausführen...`) |
| `f` | einen anderen Ordner wählen: `Rechts` oder `Leertaste` öffnet einen Ordner, `Links` schließt ihn, `Enter` oder ein Doppelklick wählt; ein Pfad lässt sich auch eintippen |
| `s` | Einstellungen: `Umschalt+Hoch`/`Umschalt+Runter` verschieben eine Region, `Entf` entfernt sie, `Strg+S` speichert, `Esc` bricht ab |
| `r` oder `F5` | neu analysieren |
| `c` | die Credits zeigen |
| `Enter` | in einer Plattform der Sammlung: alles, was über das markierte Spiel bekannt ist (auch Doppelklick im Fenster); `Enter`, `Esc` oder `q` schließt |
| `n` | in einer Plattform der Sammlung: die markierten Dateien als `kein Spiel` kennzeichnen (etwa eine BIOS-Datei) oder das aufheben |
| `g` | in einer Plattform der Sammlung: der Gamelist-Bericht der Plattform |
| `e` | in der Spielansicht: die Informationen des Spiels bearbeiten; `Strg+S` speichert, `Esc` geht zurück |
| `w` | in einer Plattform der Sammlung: ihre `gamelist.xml` aus der Datenbank schreiben (nach einer Frage) |
| `F1` oder `?` | alle Tasten zeigen oder wieder ausblenden (auch `?`, weil manche Terminals `F1` für ihre eigene Hilfe behalten) |
| `q` oder `Esc` | schließen, ohne etwas zu löschen; in einer Plattform der Sammlung führen beide erst zurück zur Übersicht; nach Änderungen von Hand fragt das Programm vorher |
| In einer Frage | `Links`/`Rechts` wählen eine Schaltfläche, `Enter` drückt sie, `Esc` antwortet `Nein` |

Die Maus geht auch: Ein Klick wählt eine Zeile, das Rad scrollt, und die Ansichten und Schaltflächen lassen sich anklicken. Buchstaben, die in ein Feld getippt werden, bleiben im Feld, auch schnell getippt oder eingefügt: Ein `x` im Filter markiert nie eine Datei.

**Farben und Zeichen.** Mit 256 Farben oder mehr verwendet die Terminal-Version die Farben des Fensters, aber schwarz hinter jedem Spiel (keine Streifen). Hat das Terminal nur 16 Farben (`TERM=xterm`, `TERM=linux`), wechselt sie zu einfachen ANSI-Farben: blaue Auswahl, grüne Titel- und Statuszeile, grüne behaltene und rote markierte Dateien, braune Zeilen mit schwarzer Schrift, die von Hand geändert wurden. Auf der Linux-Konsole, in Terminals wie `vt100` und wenn das Locale einen anderen Zeichensatz als UTF-8 nennt (zum Beispiel `en_US` oder `de_DE.ISO-8859-1`), zeichnet sie nur ASCII-Zeichen: Ansichten als `(*)`, Rahmen aus `+`, `-` und `|`. `--ascii` erzwingt das. PuTTY meldet sich als `xterm` (16 Farben); für die Farben des Fensters *Connection → Data → Terminal-type string* auf `xterm-256color` stellen. Dateinamen und Texte in anderen Schriften, etwa Japanisch, brauchen weiterhin ein Terminal und eine Schrift, die sie zeigen können.

Unterschiede zum Fenster: kein Schriftzoom, weil die Schrift dem Terminal gehört (in PuTTY: *Window → Appearance*); und die Spiele sind nicht gestreift, sondern beginnen mit einer Strichlinie. Mit 16 Farben haben die grünen Zeilen schwarze Schrift, die auch auf hellem Grün lesbar bleibt. Beim Löschen löscht die Terminal-Version im Hintergrund und zeigt den Fortschrittsbalken; alle Tasten sind gesperrt, bis sie fertig ist. Das Fenster und die Terminal-Version halten ihre Ansicht und die bestätigten Spielstanddateien in derselben `rom_cleanup_workbench_settings.json`.

## Konfiguration: `redundanz_config.json`

Die Datei liegt neben dem Programm und wird bei jeder Analyse neu gelesen. Sprache, Priorität, Löschwörter und die Wahl zwischen normaler Datei und ZIP-Datei änderst du am einfachsten im Fenster mit `Einstellungen...` (siehe [Einstellungen](#einstellungen)). In der Datei selbst genügt es, die Reihenfolge in `region_priority` umzustellen und die Datei zu speichern:

```json
"region_priority": ["USA", "Europe", "none", "Japan", "Beta"],
"delete_tags": [],
"prefer_zip": false,
```

Enthält die Datei einen Fehler, etwa einen falsch geschriebenen Eintrag, findet keine Analyse statt, und es wird nichts gelöscht. So sieht die mitgelieferte Datei aus: Die Sprache ist Englisch, die Priorität USA, Europe, none, Japan, Beta, es gibt keine Löschwörter, und neben einer ZIP-Datei bleibt die normale Datei erhalten. Dateien ohne Region kommen also vor japanischen. Fehlt die Datei oder ein Eintrag, gelten dieselben Vorgaben.

- `language`: die Sprache des Fensters, der Hinweise und der Terminalausgabe (siehe unten).
- `region_priority`: Regionen und Zusatzinfos, die besten zuerst. `none` steht für Dateien ohne bekannte Region; die Wörter der anderen Sprachen (`keine`, `nessuna`, `ninguna`, `aucune`, `なし`) gehen ebenso. Zusatzinfos wie `Beta` hinter `none` setzen solche Dateien ans Ende (Regel 6); `Beta` passt auch zu `Beta 2`.
- `region_aliases`: andere Schreibweisen einer Region, zum Beispiel `Europa` für `Europe`. Mitgeliefert sind auch die Kurzformen `U`, `E` und `J` aus GoodTools-Namen wie `Title (J) [o1].nes`.
- `delete_tags`: die Löschwörter, Zusatzinfos, die immer zum Löschen führen (Regel 2). Als Vorgabe ist die Liste leer. Ein Löschwort zählt als ganzes Wort irgendwo in einer Klammer: `Hack` passt zu `(Hack)`, `(Hack 2)`, `(Hack by Someone)` und `(Micks Hack)`, aber nicht zu `(Hacks)` oder `(Hackers)` und nicht zu einem Wort außerhalb der Klammern wie in `Hack Attack (USA)`; wer Hacks löschen will, trägt deshalb `Hack` und `Hacks` ein.
- `part_tags`: Teile einer Version, zum Beispiel `Disc 1`.
- `prefer_zip`: `false` (Vorgabe) behält die normale Datei, wenn es ein Spiel als normale Datei und als ZIP-Datei derselben Version gibt, `true` behält die ZIP-Datei.

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

Manche Dateien übergeht das Programm ganz: Sie erscheinen nirgends und werden nie gelöscht. Als Klammern zählen `( )`, `[ ]` und `{ }`, überall gleich: für den Spielnamen, die Priorität, die Versionen und die Löschwörter.

- Dateien, deren Name mit `gamelist` beginnt, unabhängig von Groß- und Kleinschreibung. Sie sind keine ROM-Dateien.
- Versteckte Dateien: Namen, die mit einem Punkt beginnen, etwa `.xxx` oder `.DS_Store`, und Dateien mit dem Windows-Attribut „Versteckt“.

1. Dateien gehören zusammen, wenn der Text vor der ersten Klammer gleich ist. Groß- und Kleinschreibung, Leerzeichen, Bindestriche und Unterstriche zählen nicht, also `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. Damit gilt auch `Title 1-2` = `Title 12`. Außerdem gelten `und` = `and` = `&` = `&&`, `Sullivan's` = ``Sullivan`s`` = `Sullivan´s` = `Sullivans` (Apostrophe zählen nicht), die römischen Zahlen `I` bis `IX` als ganzes Wort gleich `1` bis `9` (`Final Fantasy VII` = `Final Fantasy 7`; ab `X` bleiben sie, wie sie sind, denn `Mega Man X` und `Mega Man 10` sind zwei Spiele) sowie `The Title` = `Title The` = `Title, The` = `Title` als gleich. Ein `The` mitten im Namen zählt dagegen. Ebenso gilt `vs` = `vs.` = `versus`. Eine Nummer vor dem Namen, etwa aus einer durchnummerierten Sammlung, zählt nicht: `057 Robocop vs Terminator` = `057 - Robocop vs Terminator` = `Robocop vs Terminator`. Besteht der Name nur aus der Zahl (`1942`) oder hängt sie am Wort (`2Fast`), bleibt sie Teil des Namens; `4 in 1` und `3 in 1` bleiben verschiedene Spiele. Weil die Namen dann nur durch den Vergleich übereinstimmen, gilt das Spiel als problematisch (`Unterschiedliche Schreibweisen des Namens`).
2. Dateien mit einem Löschwort (`delete_tags`, als Vorgabe keine, zum Beispiel `Hack` und `Hacks`) werden immer markiert, auch wenn es die einzige Datei des Spiels ist. `k` behält eine solche Datei trotzdem. Der Hinweis lautet dann `Gelöscht wegen Löschwort (Hack) - wie gewünscht`; eine Warnung zum Inhalt gibt es für solche Dateien nicht, ihr Inhalt soll ja weg. Ausnahme: Nennt eine Klammer mehrere Regionen und ist eine davon genau das Löschwort, eine andere aber eine Region aus deiner Prioritätenliste, gilt das Löschwort für diese Klammer nicht. `(Japan, USA)` ist auch die USA-Fassung: Mit dem Löschwort `Japan` und `USA` in der Liste bleibt sie und wird als USA-Fassung einsortiert; `(Japan)` allein wird weiter markiert.
3. Von den übrigen Dateien bleibt die mit dem besten Eintrag in `region_priority` erhalten. Innerhalb einer Klammer zählt der beste Eintrag: bei `(USA, Japan)` der bessere der beiden. Über Klammern hinweg zählt der schlechteste: `(USA) (Beta)` zählt als `Beta` (Regel 6). Eine Datei, die so verliert, bekommt den Hinweis `Priorität: USA nach Europe`: zuerst ihr eigener Eintrag, dann der, der gewonnen hat; ohne Region steht dort `none`.
4. Alle Dateien derselben Version bleiben gemeinsam erhalten, zum Beispiel `(Disc 1)` und `(Disc 2)` oder `.cue` und `.bin`. Alles andere wird markiert. Ausnahme: Hat nur ein Teil dieser Dateien eine Nummer vor dem Namen (`073 Batman (USA).sfc` und `Batman (USA).sfc`), bleiben die mit Nummer erhalten, die anderen werden markiert (`Name mit Nummer bevorzugt`). Bei jeder anderen markierten normalen Datei nennt der Bericht, ob ihr Inhalt in einer behaltenen Datei steckt (`Inhalt identisch mit …`) oder nicht (`Spielinhalt weicht von der behaltenen Version ab`). Das ist nur ein Hinweis: Das Spiel wird dadurch nicht problematisch, denn eine andere Regionsfassung hat meist einen anderen Inhalt. Verglichen wird zuerst die Größe; eine Prüfsumme wird nur bei gleicher Größe berechnet.
5. Eine Region, die nicht in `region_priority` steht, zählt als `none`. Das gilt auch für Angaben wie `(Rev 1)`.
6. Zusatzinfos wie `Beta`, `Proto` oder `Alpha` werden in `region_priority` hinter `none` geschrieben. Dateien damit kommen nach allen anderen, auch nach Dateien ohne Region, und in der Reihenfolge der Liste: Bei `none, Beta, Proto` kommt eine Beta vor einem Proto. Sie bleiben nur erhalten, wenn es keine bessere Datei des Spiels gibt. Untereinander zählt wieder die Region, dann die Version aus Regel 7, dann die Nummer hinter der Zusatzinfo: `Beta 2` gewinnt gegen `Beta 1` und `Beta 1` gegen `Beta` ohne Nummer. Die Nummern werden numerisch verglichen (`Beta 10` vor `Beta 9`). Die unterlegene Datei bekommt den Hinweis `Ältere Beta`.
7. Bei gleicher Priorität gewinnt die höchste Versionsnummer, numerisch verglichen (`v1.10` vor `v1.9`). Erkannt werden in Klammern `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` und `Rev A`; im Spielnamen nur die Form `Title v1.1`, auch mit `-` oder `_` statt eines Leerzeichens. Eine Datei ohne Version verliert gegen eine mit Version. Die Region zählt vor der Version.
8. Danach gewinnt die Datei mit einer Nummer vor dem Namen (`073 Batman` vor `Batman`), dann die mit weniger Zusatzinformationen, dann eine Datei ohne ZIP (mit `prefer_zip`: eine ZIP-Datei), dann das Alphabet. Der Bericht zeigt dann `Gleichstand`.
9. Eine Datei, die kleiner ist als 1/4 der größten Datei des Spiels, wird vor den Regeln 3 bis 8 beiseitegelegt und behalten: Sie könnte eine Status- oder Spielstanddatei sein. Sie kann daher weder gelöscht werden noch das echte ROM verdrängen, etwa `1941.state` die Datei `1941.zip`. Die Hinweisspalte zeigt dann `Verdacht auf Status- oder Spielstanddatei`, und das Spiel gilt als problematisch. Ein solches Spiel erscheint in allen drei Ansichten, auch wenn keine seiner Dateien markiert ist. Beim Löschen bestätigt das Programm alle übrigen vermuteten Dateien als legitim: Sie bleiben, wo sie sind, werden weiterhin nie gelöscht und erscheinen nicht mehr in `Problematische Löschmarkierungen` und `Alle Löschmarkierungen`, auch nach `F5` oder einem Neustart. Die Bestätigung nennt ihre Anzahl. Das Programm merkt sie sich mit Pfad und Größe in `rom_cleanup_workbench_settings.json`; ändert sich die Größe, steht die Datei wieder unter Verdacht. Ist nichts markiert, bietet `Enter` an, sie zu bestätigen, ohne etwas zu löschen. ZIPs zählen mit ihrer entpackten Größe. Das gilt nicht für eine kleine normale Datei neben einer großen normalen Datei ihrer eigenen Version, etwa eine `.cue` neben ihrer `.bin`, nicht für eine Datei mit derselben Endung wie die größte Datei (eine kleine `.nes` neben einer großen `.nes` ist ein ROM, über das die Regeln 3 bis 8 entscheiden) und nicht für Dateien, die wegen `delete_tags` oder eines defekten ZIPs markiert sind. Mit `x` kannst du die Datei trotzdem von Hand markieren. Spielstände mit typischer Endung (`.srm`, `.sav`, `.eep`, `.mpk`, `.fla`, `.sra`, `.rtc`, `.dsv`, `.mcr`, `.state`, `.state1` …, `.state.auto`, `.st0` …, `.ss0` …) fallen nicht unter diese Regel: Ein Emulator lädt einen Spielstand nur, wenn er genau so heißt wie das ROM (ohne Endung). Ein Spielstand bleibt deshalb nur erhalten, wenn eine behaltene Datei genau diesen Namen hat, etwa `Mario Kart 64 (USA).srm` neben `Mario Kart 64 (USA).n64`. Jeder andere wird markiert, auch einer anderer Region oder anderer Fassung wie `Mario Kart 64 (U) [!].mpk`, mit dem Hinweis `Spielstand ohne ROM-Datei gleichen Namens`. Löschwörter gelten auch für Spielstände.
10. Beim Ausführen wird nach dem Löschen bei jeder behaltenen Datei die Nummer vor dem Namen entfernt, mit den Leerzeichen, Punkten, Bindestrichen oder Unterstrichen danach: `073 Batman (USA).sfc` wird `Batman (USA).sfc`, `057 - Robocop.md` wird `Robocop.md`. Die Bestätigung nennt vorher die Anzahl und ein Beispiel; ist nichts markiert, fragt `Enter` nur nach dem Umbenennen. Die Nummer bleibt, wenn zum Spiel eine `.cue`-, `.gdi`-, `.m3u`-, `.mds`-, `.toc`- oder `.ccd`-Datei gehört (sie nennt die Dateinamen in ihrem Inhalt) oder wenn der Name ohne Nummer schon vergeben ist; die Bestätigung nennt auch diese Anzahl. Der Inhalt von ZIPs wird nicht umbenannt. In der Titelzeile eines Spiels steht der Name in der Schreibweise der ersten behaltenen Datei (`Street Fighter II` oder `Street Fighter 2`), immer ohne Nummer; verschiebst du Dateien mit `k` oder `x`, passt sich der Titel an. Als Listennummer gilt eine Zahl nur, wenn es eindeutig ist: mit führender Null (`057`), mit Trennzeichen danach (`057 - `, `283. `) oder wenn dasselbe Spiel auch ohne Nummer vorliegt (`283 Dynamite Bowl` neben `Dynamite Bowl (J)`); ist eine Nummer eines Spiels eindeutig, gelten alle seine Nummern als Listennummern. Sonst gehört die Zahl zum Titel und bleibt, im Dateinamen wie in der Titelzeile: `1080 Snowboarding`, `720 Degrees`.

## ZIP-Dateien

Jede ZIP-Datei wird vollständig gelesen, auch wenn sie die einzige Datei eines Spiels ist. Ihr Inhalt wird mit SHA-256 mit den anderen Dateien des Spiels verglichen.

- **Gleicher Inhalt wie eine behaltene Datei:** Die ZIP-Datei wird markiert, und der Bericht nennt die Datei mit demselben Inhalt.
- **Bleiben nach der Auswahl ein ZIP und eine normale Datei übrig:** Das ZIP wird immer markiert, auch bei anderem Inhalt, wenn es die einzige Datei mit einem Teil wie `(Disc 1)` ist oder wenn es nicht lesbar ist.
- **Mit `ZIP-Datei behalten` (`prefer_zip`):** Umgekehrt: Neben einer lesbaren ZIP-Datei derselben Version werden die normalen Dateien markiert (`ZIP-Datei bevorzugt`). Kommt der Inhalt einer solchen Datei in keinem behaltenen ZIP vor, zeigt der Bericht `Spielinhalt weicht von der behaltenen Version ab`, und das Spiel gilt als problematisch (`Gleiche Fassung wie die behaltene Datei, aber anderer Inhalt`). Ein nicht lesbares ZIP verdrängt keine normale Datei. Die Priorität geht weiterhin vor: Eine normale `(USA)`-Datei gewinnt gegen ein `(Japan)`-ZIP.
- **Mehrere ZIPs derselben Version mit anderem Inhalt:** Alle bleiben erhalten, und der Bericht weist darauf hin.
- **Markiert, aber der Inhalt kommt in keiner behaltenen Datei vor:** Der Bericht zeigt `Spielinhalt weicht von der behaltenen Version ab`. Die Datei bleibt markiert. Ist das ZIP dieselbe Fassung wie eine behaltene Datei, gilt das Spiel als problematisch (`Gleiche Fassung wie die behaltene Datei, aber anderer Inhalt`). Verliert es dagegen wegen der Priorität oder als ältere Version, ist ein anderer Inhalt zu erwarten: Dann ist es nur ein Hinweis. ZIPs, die wegen eines Löschworts markiert sind, bekommen keinen solchen Hinweis.
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
