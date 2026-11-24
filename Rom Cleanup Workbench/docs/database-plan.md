# Konzept: ROM-Sammlung mit Datenbank, Übersicht und Batch-Analyse

Stand: Entwurf vom 2026-11-24, alle Fragen beantwortet, wartet auf die Freigabe. Noch ist nichts davon programmiert.

## Ausgangslage

Heute arbeitet das Programm mit **einem** Ordner, etwa `roms/nes`. Bei jedem Start und bei jedem `F5` liest es den Ordner vollständig neu: Es entpackt jedes ZIP, berechnet Prüfsummen (SHA-256) und entscheidet. Nichts davon wird gespeichert. Gespeichert werden nur die gewählte Ansicht und die bestätigten Spielstanddateien, und zwar in `rom_cleanup_workbench_settings.json` neben dem Programm.

Eine Sammlung sieht aber meist so aus:

```
roms
+--- nes
+--- snes
+--- n64
+--- gamecube
```

## Ziele (deine vier Punkte)

1. **Datenbank:** eine leichtgewichtige Datenbank in `roms/database`, beim ersten Start leer angelegt.
2. **Speichern und Laden:** Die Ergebnisse eines Scans landen in der Datenbank. Beim nächsten Öffnen kommen sie von dort, bis du neu scannst.
3. **Übersicht als neue Startseite:** alle Plattform-Ordner mit der Zahl der gescannten Dateien.
4. **Batch-Analyse:** ein Lauf über alle Plattform-Ordner, der die Ergebnisse in die Datenbank schreibt.

## Vorschlag

### 1. Datenbank: SQLite

- **SQLite** gehört zu Python (`sqlite3`). Es muss nichts installiert werden, weder unter Windows noch unter Linux. Die Datenbank ist eine einzige Datei, die man kopieren und sichern kann.
- Ort: `roms/.rom_cleanup_workbench/rom_cleanup_workbench.sqlite`, ein versteckter Ordner (Frage 6). Er wird angelegt, sobald du einen `roms`-Ordner öffnest. Das Programm schreibt damit zum ersten Mal etwas in deine Sammlung, und zwar nur diesen einen Ordner.
- Dieser Ordner gilt nie als Plattform, ebenso andere versteckte Ordner wie `.git` und Ordner, die mit `gamelist` beginnen.
- Eine Versionsnummer in der Datenbank erlaubt spätere Änderungen am Aufbau, ohne dass alte Daten verloren gehen.

### 2. Was gespeichert wird: die Fakten, nicht die Entscheidungen

Teuer ist das **Lesen**: ZIPs entpacken und Prüfsummen rechnen. Das Entscheiden nach den Regeln dauert dagegen nur Millisekunden. Deshalb speichert die Datenbank die Fakten:

- je Plattform: Ordnername, Zeitpunkt des letzten Scans, Zahl der Dateien
- je Datei: Name, Größe, Änderungszeit, bei Bedarf die Prüfsumme
- je ZIP: der Inhalt (Name, Größe und Prüfsumme jeder Datei darin) oder der Lesefehler (defekt, verschlüsselt, unbekannte Methode)

Die Entscheidungen (behalten, markieren, Hinweise, Probleme) rechnet das Programm beim Öffnen aus diesen Fakten neu. Das hat zwei Vorteile:

- Änderst du die Priorität, die Löschwörter oder den ZIP-Schalter, wirkt das sofort, **ohne neuen Scan**.
- Neue Regeln, etwa die Hinweise von heute, gelten auch für alte Scans.

Zusätzlich speichert die Datenbank je Plattform eine kleine **Zusammenfassung**: Spiele, markierte Dateien und problematische Spiele. Die Übersicht kann so sofort zeigen, ohne alle Plattformen durchzurechnen. Diese Zahlen werden nach jedem Scan und nach jeder Einstellungsänderung neu berechnet.

### 3. Aktuell oder veraltet?

Beim Öffnen einer Plattform vergleicht das Programm den Ordner mit der Datenbank, und zwar nur nach Namen, Größe und Änderungszeit. Das geht schnell, auch bei Tausenden Dateien. Hat sich etwas geändert (Datei neu, gelöscht oder verändert), zeigt die Übersicht bei dieser Plattform **„geändert seit dem letzten Scan“**. Neu gelesen wird erst, wenn du scannst.

- **Schneller Scan (Normalfall):** Er liest nur geänderte Dateien neu, das ist bei großen Sammlungen viel schneller. **Voller Scan auf Wunsch:** Er liest jede Datei neu (Frage 4).

### 4. Übersicht (neue Startseite)

Eine Tabelle, eine Zeile je Plattform-Ordner:

| Plattform | Dateien | Spiele | Zum Löschen | Problematisch | Letzter Scan | Stand |
| --- | --- | --- | --- | --- | --- | --- |
| nes | 1.240 | 1.012 | 186 | 23 | 24.11.2026 10:14 | aktuell |
| snes | 830 | 791 | 39 | 4 | 23.11.2026 18:02 | geändert |
| n64 | – | – | – | – | nie | nicht gescannt |

- **Enter oder Doppelklick** auf eine Zeile öffnet die Plattform in der gewohnten Liste. Ein neuer Knopf **„Übersicht“** (oder `Esc`) führt zurück.
- **Knöpfe:** „Plattform scannen“ (die markierte Zeile), „Alle scannen“ (Batch), „Ordner...“ (einen anderen `roms`-Ordner wählen), „Einstellungen...“, „Schließen“.
- Die Zeile **Summe** unten zählt alle Plattformen zusammen.
- Die Übersicht gibt es im Fenster und in der Terminal-Version, wie alles andere.

### 5. Batch-Analyse

- „Alle scannen“ geht Plattform für Plattform durch. Der Fortschritt zeigt die aktuelle Plattform und die Dateien darin, zum Beispiel „snes: 412 von 830“.
- Jede fertige Plattform wird sofort gespeichert. Ein Abbruch oder Absturz verliert also höchstens die Plattform, die gerade läuft.
- **Abbrechen** ist jederzeit möglich. Bereits gescannte Plattformen bleiben gespeichert.
- Die Batch-Analyse **löscht nie etwas**. Gelöscht wird weiterhin nur in der Liste einer Plattform nach deiner Bestätigung.
- **Optional:** auf der Kommandozeile `--scan-all D:\roms` ohne Fenster, etwa für einen Lauf über Nacht.

### 6. Was außerdem in die Datenbank wandert

- **Bestätigte Spielstanddateien:** Heute liegen sie in `rom_cleanup_workbench_settings.json` neben dem Programm. Sie gehören aber zur Sammlung und ziehen deshalb in die Datenbank. Beim ersten Öffnen werden die vorhandenen übernommen.
- **Löschen und Umbenennen:** Beides trägt das Programm sofort in die Datenbank ein. Nach dem Ausführen ist kein neuer Scan nötig.
- **Von Hand verschoben (`k`/`x`):** Diese Änderungen werden gespeichert und bleiben über das Schließen hinaus erhalten (Frage 2).

### 7. Was bleibt, wie es ist

- Die Regeln, die Einstellungen in `redundanz_config.json` und die Liste einer Plattform mit allen Tasten.
- Ein **einzelner Plattform-Ordner** lässt sich weiter direkt öffnen, ohne Datenbank, so wie heute. Das Programm erkennt einen `roms`-Ordner daran, dass er Unterordner mit ROM-Dateien enthält oder schon einen Ordner `database` hat.
- `--report-only` und `--yes` arbeiten weiter auf einem Ordner.

## Datenbank-Aufbau (Entwurf)

```
schema_info  (version)
platforms    (id, folder, last_scan, files, games, marked, problematic, summary_config)
files        (id, platform_id, name, size, mtime, sha256 NULL, zip_error NULL)
zip_members  (file_id, name, size, sha256)
confirmed_saves (platform_id, name, size)
manual_moves    (platform_id, name, size, mtime, decision)
platform_config (platform_id, json)              -- eigene Konfiguration einer Plattform (Frage 3)
```

`summary_config` merkt sich, mit welchen Einstellungen die Zusammenfassung berechnet wurde. Ändern sich die Einstellungen, rechnet die Übersicht die Zahlen neu.

## Schritte

Jeder Schritt gilt als fertig, wenn seine Tests unter Windows und in der WSL laufen und er lokal committet ist. Doku nur auf Deutsch, Upload erst zum Feierabend.

1. **Datenbank-Schicht** (neue Datei `workbench_db.py`): anlegen, Version, Plattform und Dateien schreiben und lesen. Ohne Oberfläche, nur mit Tests.
2. **Scan speichern und laden:** Ein Scan schreibt die Fakten. Beim Öffnen werden die Entscheidungen aus der Datenbank berechnet, die Ergebnisse sind dieselben wie bei einem frischen Scan (Tests vergleichen beides). Löschen und Umbenennen tragen sich ein.
3. **„Geändert seit dem letzten Scan“** erkennen; schneller Scan als Normalfall, voller Scan auf Wunsch.
4. **Übersicht im Fenster:** neue Startseite, Wechsel zur Plattform und zurück.
5. **Batch-Analyse im Fenster:** „Alle scannen“ mit Fortschritt und Abbrechen.
6. **Übersicht und Batch in der Terminal-Version.**
7. **Bestätigte Spielstanddateien** in die Datenbank, die alten werden übernommen.
8. **Doku** (README.de.md und Benutzerhandbuch): neues Kapitel „Die Sammlung“, neue Bilder.

## Offene Fragen an dich

1. ~~**Startverhalten**~~ **Entschieden (2026-11-24):** Beim Start zeigt das Programm immer die Übersicht, nie direkt eine Plattform. Geöffnet wird der zuletzt benutzte `roms`-Ordner. Beim allerersten Start, oder wenn der Ordner fehlt, wählst du ihn zuerst aus. Ein Ordner auf der Kommandozeile hat Vorrang.
2. ~~**Änderungen von Hand**~~ **Entschieden:** Ja. `k`/`x` werden in der Datenbank gespeichert und bleiben erhalten, auch nach dem Schließen, bis du ausführst oder die Plattform neu scannst. Ändert sich eine Datei, verfällt ihre Änderung von Hand.
3. ~~**Einstellungen je Plattform**~~ **Entschieden:** eine Standardkonfiguration (`redundanz_config.json`) und die Möglichkeit, für eine Plattform eine eigene zu hinterlegen. Die Einstellungen einer Plattform zeigen oben die Wahl „Standard verwenden“ oder „Eigene für diese Plattform“. Eine eigene Konfiguration übernimmt beim Anlegen die Werte des Standards und liegt in der Datenbank. Die Übersicht zeigt bei solchen Plattformen ein Kennzeichen.
4. ~~**Schneller Scan**~~ **Entschieden:** Der schnelle Scan ist der Normalfall: Er liest nur neue und geänderte Dateien (Name, Größe, Änderungszeit) und nimmt gelöschte aus der Datenbank. Auf Wunsch gibt es jederzeit einen vollen Scan, der jede Datei neu liest: für eine Plattform („Vollständig neu scannen“), für alle (Batch mit der Wahl „vollständig“) und auf der Kommandozeile (`--scan-all --full`).
5. ~~**Kommandozeile**~~ **Entschieden:** Ja, `--scan-all <roms-Ordner>` scannt alle Plattformen ohne Fenster, gibt den Fortschritt im Terminal aus und löscht nichts.
6. ~~**Name des Ordners**~~ **Entschieden:** versteckt, `roms/.rom_cleanup_workbench/`. Unter Windows bekommt der Ordner zusätzlich das Attribut „Versteckt“, weil der Punkt dort allein nicht versteckt.

## Log

- 2026-11-24: Konzept entworfen, wartet auf Freigabe und Antworten auf die offenen Fragen.
- 2026-11-24: Frage 1 entschieden: Start immer mit der Übersicht (zuletzt benutzter `roms`-Ordner).
- 2026-11-24: Fragen 2, 3, 5, 6 entschieden: `k`/`x` speichern, Standard- plus Plattformkonfiguration, `--scan-all`, versteckter Ordner. Frage 4 erklärt.
- 2026-11-24: Frage 4 entschieden: schneller Scan als Normalfall, voller Scan auf Wunsch. Alle Fragen beantwortet; das Konzept wartet auf die Freigabe.
