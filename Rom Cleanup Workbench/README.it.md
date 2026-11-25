# Rom Cleanup Workbench

[English](README.md) · [Deutsch](README.de.md) · **Italiano** · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md)

**Guida per l'utente con schermate:** [PDF](<docs/Rom Cleanup Workbench - Guida utente.pdf>) · [Word](<docs/Rom Cleanup Workbench - Guida utente.docx>)


Trova i file ROM duplicati in una cartella in base al nome del gioco e li elimina su richiesta.
Richiede Python 3.10 o successivo. La finestra non ha bisogno di pacchetti aggiuntivi; la versione per terminale per Linux richiede Textual (vedi [Versione per terminale (Linux)](#versione-per-terminale-linux)).
Il programma parla inglese, tedesco, italiano, spagnolo, francese e giapponese (vedi [Lingua](#lingua)).

**Importante:** non usare questo programma sui tuoi file ROM originali. Crea una copia del tuo archivio di ROM e usa il programma per fare la pulizia solo sulla copia.

## Installazione

Non serve un account GitHub. Ogni comando sta in un riquadro a sé; scrivilo così e premi Invio.

### Windows

Scrivi tutti i comandi in PowerShell.

1. **Controllare se Python è installato:**

   ```powershell
   python --version
   ```

   - **Compare `Python 3.10` o superiore:** Python c'è, prosegui con il passo 2.

   - **Compare un errore o una versione più vecchia:** scarica Python 3.10 o più recente da [python.org/downloads](https://www.python.org/downloads/) e installalo. Se il programma di installazione offre “Add python.exe to PATH”, spunta l'opzione. `tkinter` per la finestra è incluso. Poi apri una nuova finestra di PowerShell e ripeti il controllo.

2. **Controllare se Git è installato:**

   ```powershell
   git --version
   ```

   - **Compare un numero di versione, per esempio `git version 2.47.0`:** scarica il programma con Git:

     ```powershell
     git clone https://github.com/arved9926/rom-cleanup-workbench.git
     ```

   - **Compare un errore:** scarica il programma come file ZIP. Nel browser, sulla [pagina GitHub](https://github.com/arved9926/rom-cleanup-workbench), scegli **Code** e poi **Download ZIP**; poi estrai il file con il tasto destro del mouse (**Estrai tutto...**) e rinomina la cartella `rom-cleanup-workbench-main` in `rom-cleanup-workbench`. Oppure in PowerShell, un comando alla volta:

     ```powershell
     Invoke-WebRequest https://github.com/arved9926/rom-cleanup-workbench/archive/refs/heads/main.zip -OutFile rom-cleanup-workbench.zip
     ```

     ```powershell
     Expand-Archive rom-cleanup-workbench.zip -DestinationPath .
     ```

     ```powershell
     Rename-Item rom-cleanup-workbench-main rom-cleanup-workbench
     ```

3. **Entrare nella cartella del programma:**

   ```powershell
   cd "rom-cleanup-workbench\Rom Cleanup Workbench"
   ```

   La finestra non richiede altri pacchetti. Solo chi vuole usare la versione per terminale su Windows installa anche Textual:

   ```powershell
   python -m pip install textual==8.2.8
   ```

### Linux

Scrivi tutti i comandi in un terminale. Gli esempi valgono per Debian e Ubuntu.

1. **Controllare se Python è installato:**

   ```bash
   python3 --version
   ```

   - **Compare `Python 3.10` o superiore:** Python c'è, prosegui con il passo 2.

   - **Compare un errore o una versione più vecchia:** installa Python:

     ```bash
     sudo apt install python3 python3-venv
     ```

   Il pacchetto `python3-tk` serve solo se su Linux con un display grafico vuoi usare la finestra invece della versione per terminale.

2. **Controllare se Git è installato:**

   ```bash
   git --version
   ```

   - **Compare un numero di versione:** scarica il programma con Git:

     ```bash
     git clone https://github.com/arved9926/rom-cleanup-workbench.git
     ```

   - **Compare un errore:** scarica il programma come file ZIP ed estrailo, un comando alla volta:

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

3. **Entrare nella cartella del programma:**

   ```bash
   cd "rom-cleanup-workbench/Rom Cleanup Workbench"
   ```

4. **Installare Textual in un ambiente virtuale:**

   ```bash
   python3 -m venv ~/venvs/rom-cleanup-workbench
   ```

   ```bash
   ~/venvs/rom-cleanup-workbench/bin/pip install textual==8.2.8
   ```

## Uso

### Windows

Apri un terminale (per esempio PowerShell) nella cartella `Rom Cleanup Workbench` e avvia il programma con la cartella dei tuoi giochi:

```powershell
cd "rom-cleanup-workbench\Rom Cleanup Workbench"
```

```powershell
python rom_cleanup_workbench.py "D:\Games"
```

Senza una cartella il programma riapre l'ultima cartella scelta, una cartella `roms` con la sua panoramica, qualsiasi altra direttamente; la prima volta la finestra ne chiede una. Per la versione da terminale si aggiunge `--tui`.

### Linux

Entra nella cartella `Rom Cleanup Workbench` e avvia il programma con il Python dell'ambiente virtuale e la cartella dei tuoi giochi:

```bash
cd "rom-cleanup-workbench/Rom Cleanup Workbench"
```

```bash
~/venvs/rom-cleanup-workbench/bin/python rom_cleanup_workbench.py ~/roms
```

Senza display grafico, per esempio tramite SSH, la versione per terminale parte da sola. Con un display grafico si apre la finestra (serve `python3-tk`); con `--tui` parte comunque la versione per terminale. Altro in [Versione per terminale (Linux)](#versione-per-terminale-linux).

### Che cosa succede poi

Il programma apre la finestra di analisi e mostra tutto lì; nel terminale non stampa nulla e non chiede nulla. Anche domande, messaggi e la scelta della cartella compaiono dentro la finestra, nella lingua del programma, mai come popup di Windows; Invio sceglie il pulsante preselezionato ed Esc risponde No. Senza una cartella, la finestra chiede la cartella. I file vengono eliminati solo dopo la conferma nella finestra. **I file eliminati non finiscono nel Cestino.**

| Opzione | Effetto |
| --- | --- |
| `--review all` | apre la finestra con `Da eliminare` per questo avvio |
| `--review problems` | apre la finestra con `Da verificare` per questo avvio |
| `--priority USA Europe Japan none` | imposta la priorità per questa esecuzione |
| `--delete-tag Hack Hacks Proto` | imposta le parole da eliminare per questa esecuzione |
| `--config file.json` | usa un'altra configurazione |
| `--report-only` | senza finestra: stampa solo il rapporto nel terminale |
| `--yes` | senza finestra: elimina i file marcati senza chiedere |
| `--scan-all` | senza finestra: scansiona tutte le cartelle delle piattaforme della cartella `roms` indicata e le salva nel suo database; non elimina nulla |
| `--deep-scan` | con `--scan-all`: scansione profonda, rilegge ogni file invece dei soli file nuovi e modificati (`--full` funziona ancora) |
| `--write-gamelists` | senza finestra: scrive il `gamelist.xml` di ogni piattaforma della cartella `roms` indicata dal suo database; ogni file precedente resta come copia |
| `--all` | con `--report-only`: mostra anche i giochi senza file marcati |
| `--tui` | usa la versione per terminale invece della finestra (automatico su Linux senza display grafico) |
| `--ascii` | versione per terminale solo con caratteri ASCII (automatico sulla console di Linux); implica `--tui` |

Le opzioni della riga di comando e il loro aiuto (`--help`) sono sempre in inglese.

I test si eseguono con `python -m unittest`.

## La raccolta: molte piattaforme e il database

Di solito i giochi si trovano in una cartella comune, divisi per piattaforma, per esempio `roms/nes`, `roms/snes`, `roms/n64`. Se scegli questa cartella `roms`, il programma mostra la **panoramica** di tutte le piattaforme. Da quel momento parte sempre con l'ultima cartella scelta, quindi con la sua panoramica nel caso di una cartella `roms`. Conta come cartella `roms` una cartella che ha già un database oppure che non contiene file ROM ma sottocartelle. I file di accompagnamento come `info.txt`, immagini o PDF non contano come file ROM. Ogni altra cartella viene analizzata da sola come prima, senza database.

**Il database.** La prima volta il programma crea nella cartella `roms` la cartella nascosta `.rom_cleanup_workbench` con un database SQLite. È l'unica cosa che scrive nella tua raccolta. Vi si salvano i risultati di ogni scansione: file, dimensioni, date di modifica, il contenuto degli ZIP con i checksum. Da questi il programma ricalcola le decisioni in un attimo quando si apre una piattaforma. Le impostazioni modificate valgono quindi subito, senza una nuova scansione. Vi stanno anche le modifiche a mano (`k`/`x`), i file di stato e di salvataggio confermati e le impostazioni proprie delle singole piattaforme. Conta la cartella: se una cartella di piattaforma non esiste più, la panoramica all'apertura cancella tutto ciò che il database sapeva di essa, comprese le impostazioni proprie e `senza giochi`. Una nuova cartella con lo stesso nome ricomincia allora da capo. Se la cartella `roms` stessa non è raggiungibile, per esempio un'unità di rete senza connessione, non si cancella nulla.

**La panoramica** mostra per ogni piattaforma: file, giochi, file marcati da eliminare, giochi problematici, giochi rimossi del tutto (di cui non resterebbe alcun file), l'ultima scansione e lo stato (`non scansionata`, `aggiornata` o `modificata` se da allora file sono stati aggiunti, tolti o modificati), con il totale sotto. Una linea separa il totale dalle piattaforme; lo stato `modificata` è in giallo (nella finestra l'intera riga). Un clic sull'intestazione `Piattaforma`, `File`, `Giochi`, `Da eliminare`, `Problematici`, `Rimossi del tutto`, `Info` o `Problemi gamelist` ordina secondo essa, un secondo clic al contrario; una freccia mostra la direzione, il totale resta in fondo, le piattaforme senza numeri vengono per ultime e la scelta resta salvata.

| Pulsante | Tasto | Effetto |
| --- | --- | --- |
| `Apri` | `Invio` | apre la piattaforma evidenziata nel solito elenco (anche doppio clic) |
| `Scansiona` | `r` o `F5` | scansiona la piattaforma evidenziata e la apre |
| `Scansiona tutto` | `a` | scansiona tutte le piattaforme una dopo l'altra; ognuna viene salvata subito e i suoi numeri compaiono subito nella panoramica; `Annulla` tiene quelle finite; non elimina nulla |
| `Scansione profonda` | `d` | interruttore (punto rosso) per Scansiona e Scansiona tutto: rilegge ogni file invece dei soli file nuovi e modificati |
| `Nascondi vuote` | `h` | interruttore (punto rosso): nasconde le cartelle senza file di gioco, per esempio `bios` o una cartella con solo `info.txt`; i file di contorno non contano come file di gioco; la scelta viene ricordata |
| `Cartella...` | `f` | sceglie un'altra cartella `roms` |
| | `n` | segna la cartella evidenziata come `senza giochi` o lo annulla (vedi sotto) |
| | `w` | scrive il `gamelist.xml` della piattaforma evidenziata dal database (dopo una domanda) |
| | `m` | elimina i file multimediali inutilizzati della piattaforma evidenziata (dopo una domanda, vedi sotto) |
| | `q` o `Esc` | chiude il programma |

I tasti sono gli stessi nella finestra e nella versione per terminale. La riga sopra la tabella nomina i principali; `F1` o `?` li mostra tutti.

**Scansione.** Una scansione di solito è veloce: legge solo i file nuovi e modificati (riconosciuti da nome, dimensione e data di modifica) e prende tutto il resto dal database. Con `Scansione profonda` ogni file viene riletto. `F5` nell'elenco scansiona velocemente la piattaforma aperta. Esegui registra subito i file eliminati e rinominati; dopo non serve una nuova scansione.

**Tornare alla panoramica**: nell'elenco con `Esc`, `q` o il pulsante `Panoramica`, nella versione per terminale anche con `o`. `Esc` o `q` nella panoramica chiude il programma; per uscire del tutto si preme quindi due volte.

**Il gamelist.xml.** Se una cartella di piattaforma contiene un `gamelist.xml` (EmulationStation, RetroPie, Batocera, ES-DE, ARRM), la scansione lo legge e riporta nel database ciò che si può verificare: nome, descrizione, valutazione, data, sviluppatore, editore, genere, giocatori, regione, preferito, tempo di gioco e i riferimenti ai file multimediali come immagini e video, per categoria (`wheel` e `logo` restano distinti anche se puntano allo stesso file). Tutti gli altri campi vengono portati avanti invariati. Il numero in `<genreid>` (per esempio `1538`) viene dall'elenco dei generi di Recalbox: genere principale × 256 più sottogenere, quindi `1538` = `0x0602` = Sport, sottogenere 2 «Simulazione sportiva»; strumenti come ARRM lo scrivono durante lo scraping. La vista del gioco mostra il numero con il suo nome, per esempio «1538 – Simulazione sportiva (Sport)». Non ha nulla a che fare con i numeri di genere di ScreenScraper. Se una piattaforma ha numeri di genere, l'elenco mostra una colonna `Genere`. Un clic sulla sua intestazione ordina i giochi per genere (nell'ordine dell'elenco Recalbox, i giochi senza genere per ultimi, per nome all'interno di un genere), un secondo clic o un clic su `File` di nuovo per nome; la scelta resta salvata. Nel modulo di modifica `Genere (lista Recalbox)` sceglie il numero tra tutti i generi Recalbox; il campo di testo `Genere` resta libero accanto. Un numero scelto a mano resta anche con una nuova importazione. Non vengono riportate, e contano come problemi, le voci la cui ROM non è nella cartella della piattaforma e i riferimenti a file che non esistono. I percorsi di un altro computer come `/home/pi/RetroPie/roms/nes/…` vengono riscritti sulla cartella della piattaforma e contati come avvisi. Il file viene letto solo se è cambiato; un `gamelist.xml` modificato imposta lo stato su `modificata`. Il file stesso non viene modificato. Il deposito è il database, non il `gamelist.xml`: se il file viene cancellato, le informazioni restano; se invece una ROM o un file multimediale sparisce dalla cartella, sparisce anche dal database, e una ROM eliminata porta con sé le sue informazioni. La panoramica mostra in `Info` quante ROM hanno informazioni e in `Problemi gamelist` ciò che non è stato riportato; dopo il nome della piattaforma un testo grigio dice quante voci sono state riportate. Se il file è rovinato, non si riporta nulla e resta ciò che c'era.

**gamelist.xml e file multimediali fuori dalla cartella della piattaforma.** Se la cartella della piattaforma non ha un proprio `gamelist.xml`, il Workbench cerca dove i frontend lo tengono, in quest'ordine: `~/ES-DE/gamelists/<piattaforma>/` (ES-DE), `~/.emulationstation/gamelists/<piattaforma>/` (EmulationStation, RetroPie) e su Linux `/etc/emulationstation/gamelists/<piattaforma>/`. Il nome della cartella della piattaforma vale come nome del sistema. Percorsi come `%ROMPATH%/nes/…` si riferiscono alla cartella della piattaforma. La riga grigia, il rapporto e la domanda prima della scrittura indicano il luogo; si scrive nello stesso luogo, con la copia di sicurezza lì. Il Workbench cerca file multimediali anche in `~/ES-DE/downloaded_media/<piattaforma>/` (o nella cartella multimediale scelta nelle impostazioni di ES-DE) e in `~/.emulationstation/downloaded_media/` e `downloaded_images/`. Questi file fuori dalla raccolta vengono solo mostrati e scritti nel `gamelist.xml`, ma mai eliminati o rinominati.

**File multimediali nelle sottocartelle.** A ogni scansione il Workbench cerca inoltre in tutte le sottocartelle di una piattaforma immagini, video e manuali che il `gamelist.xml` non nomina già. Si assegna solo ciò che il nome dice in modo univoco: una cartella per categoria con il nome della ROM (`wheel/10yard.png`, `marquees/10yard.png`) oppure nome della ROM, separatore (`-`, `.` o `_`) e categoria in una cartella qualsiasi (`downloaded_images/10yard-wheel.png`, `game.image.jpg`). Se corrispondono più ROM, vince il nome più lungo (`sf2ce-image.png` appartiene a `sf2ce.zip`, non a `sf2.zip`); non c'è un'assegnazione per somiglianza. Ciò che non è univoco resta senza ROM. Ogni ROM di gioco senza voce nel `gamelist.xml` riceve una voce vuota con il nome prima della prima parentesi; i file BIOS (`BIOS` in una parentesi o nomi noti come `neogeo`, `pgm`, `skns`) non contano come giochi e non ricevono file multimediali. Dopo il nome della piattaforma un testo grigio dice quanti file multimediali sono assegnati e quanti sono rimasti senza ROM; `Info` conta anche le voci vuote per cui sono stati trovati file multimediali.

**Eliminare i file multimediali inutilizzati.** `m` (nella piattaforma o nella panoramica per la piattaforma evidenziata) cerca immagini, video e manuali che niente usa più: nessuna ROM della cartella ha il loro nome e nessun `gamelist.xml` li collega, per esempio le immagini di una ROM eliminata fuori dal Workbench. Si cerca solo nelle cartelle multimediali dentro la cartella della piattaforma, cioè in cartelle il cui nome è una categoria (`images`, `videos`, `marquees`, `wheel`, `manuals` …) oppure `media`, `downloaded_images`, `downloaded_media`, `artwork`, `boxart`, `covers`. I file direttamente nella cartella della piattaforma, in altre sottocartelle (per esempio nella cartella di un gioco) e nelle cartelle multimediali di ES-DE o RetroPie fuori dalla raccolta non vengono mai toccati. Prima il Workbench rilegge la cartella e un `gamelist.xml` modificato; se il `gamelist.xml` non è leggibile, non elimina nulla. La domanda indica numero, dimensione e i primi file; i file eliminati non vanno nel cestino. Quali file multimediali sono senza ROM lo mostra prima il rapporto con `g`.

**Vista del gioco, nome e rapporto.** Il nome del `gamelist.xml` vale per l'intero gioco, non per un file: l'intestazione di un gioco mostra il nome del file mantenuto e il nostro titolo tra parentesi dopo, per esempio `10-Yard Fight (10yard)`; se sono uguali o non c'è un nome, c'è solo il nostro titolo. Nella riga con il nome di un gioco la colonna `Nota` mostra, dopo eventuali problemi, valutazione, giocatori e anno di uscita, per esempio `★ 4.5 · 1-2 giocatori · 1991` (con `--ascii` `* 4.5 - 1-2 giocatori - 1991`); vengono dal file mantenuto o, se questo non li ha, da un altro file del gioco. I file BIOS e i file segnati con `n` mostrano `non è un gioco` nella colonna `Nota`. `Enter` (nella finestra anche un doppio clic su un file) mostra al posto dell'elenco tutto ciò che si sa del gioco: i suoi file con la loro decisione, i campi come descrizione, valutazione (come x / 5), data, sviluppatore, tempo di gioco e preferito, gli altri campi del `gamelist.xml` e i file multimediali per categoria; le anteprime mancano di proposito. `g` mostra il rapporto gamelist: cosa non è stato riportato e perché, gli avvisi, le ROM senza informazioni, i file multimediali senza ROM e i file che non sono giochi. `n` segna i file selezionati come `non è un gioco` o lo annulla; un `gamelist.xml` successivo non lo cambia. Se un file si mantiene o si elimina lo decidono sempre le regole. Il riepilogo di `gamelist.xml` e file multimediali sta in grigio su una riga propria sotto la riga della piattaforma.

**Eliminare e rinominare portano con sé i file multimediali.** Quando `Esegui...` elimina una ROM, i suoi file multimediali vengono eliminati con essa, immagini, video e manuali del `gamelist.xml` come delle sottocartelle; la domanda prima dell'eliminazione ne indica il numero. Un file multimediale usato anche da una ROM che resta rimane. Una ROM eliminata porta con sé anche le sue informazioni, preferito e tempo di gioco compresi. Quando `Esegui...` toglie il numero davanti a un nome, i file multimediali il cui nome inizia con il vecchio nome della ROM vengono rinominati con essa (`01 - Alpha (USA)-image.png` diventa `Alpha (USA)-image.png`). Il `gamelist.xml` stesso non viene modificato.

**Modificare le informazioni del gioco.** Nella vista del gioco `e` apre un modulo per il file: nome, nome per ordinare, descrizione, valutazione (da 0 a 5 stelle, anche 3,5), data di uscita (`AAAA`, `AAAA-MM` o `AAAA-MM-GG`), sviluppatore, editore, genere, giocatori, regione, lingue, oltre a preferito, nascosto e per bambini. Tempo di gioco, numero di partite e l'identificativo restano come li tengono frontend e scraper. `Ctrl+S` o `Salva` salva, `Esc` o `Annulla` torna alla vista del gioco senza salvare; un valore sbagliato viene indicato e il modulo resta aperto. I campi modificati portano una `✎` nella vista del gioco; una nuova importazione del `gamelist.xml` li lascia come sono. Una voce vuota diventa vera con la modifica. Quando si scrive il `gamelist.xml`, le modifiche vi entrano.

**Scrivere il gamelist.xml.** Solo su richiesta il Workbench riscrive il `gamelist.xml` di una piattaforma dal suo database: con `w` nella piattaforma o nella panoramica per la piattaforma evidenziata, con `--write-gamelists` per tutte. Dopo una pulizia che ha eliminato file lo propone, se la piattaforma ha un `gamelist.xml`. Prima il file precedente viene salvato come `gamelist.xml.<data_ora>.bak`; restano le ultime tre copie, le più vecchie vengono eliminate. Il nuovo file nasce prima con un altro nome e poi sostituisce il vecchio in un solo passo, così non resta mai un file a metà. Contiene tutti i giochi, anche quelli con una voce vuota, ma non i file BIOS e gli altri non giochi; inoltre tutti i campi noti, i file multimediali per categoria (un file in due categorie compare due volte), l'identificativo e tutti gli altri campi come sono stati letti. I valori uguali al predefinito mancano, come in EmulationStation. Nel blocco `<provider>` come software c'è `RCW` (Rom Cleanup Workbench) con la nostra pagina GitHub; il sistema resta. Dopo, il file conta come letto.

**Cartelle senza giochi.** Una cartella come `bios` o `saves` non contiene giochi. `n` segna la cartella evidenziata come `senza giochi`: non viene né scansionata (nemmeno da `Scansiona tutto` e `--scan-all`) né aperta, non conta nel totale e `Nascondi vuote` la nasconde. Ciò che il database sapeva di essa viene cancellato. Un secondo `n` lo annulla; la cartella è allora `non scansionata`. Di proposito non c'è un pulsante per questo.

**Le modifiche a mano** (`k`/`x`) restano salvate, anche dopo la chiusura, finché esegui o scansioni di nuovo la piattaforma. Se un file cambia, la sua modifica a mano decade.

**Impostazioni per una piattaforma.** Quando una piattaforma è aperta, le impostazioni mostrano in alto `Impostazioni generali` o `Impostazioni specifiche per NES`. Con la scelta specifica, priorità, parole da eliminare e la scelta tra file normale e ZIP valgono solo per questa piattaforma; stanno nel database, e `redundanz_config.json` resta lo standard per tutte le altre. Nuove impostazioni specifiche partono dai valori standard; tornare a `Impostazioni generali` le scarta. La riga sotto il titolo delle impostazioni indica dove vengono salvate: `redundanz_config.json` oppure, con la scelta specifica, il database della raccolta (la lingua resta in `redundanz_config.json`). La lingua vale sempre per tutto. Nella panoramica queste piattaforme hanno un `*` dopo il nome.

**Senza finestra**, `--scan-all` scansiona tutte le piattaforme, per esempio di notte:

```powershell
python rom_cleanup_workbench.py "D:\roms" --scan-all
```

Con `--deep-scan` ogni file viene riletto. In questo modo non viene mai eliminato nulla.

## Finestra di analisi

Poiché i file ZIP devono essere estratti per ottenere dimensione, checksum SHA-256 e nome del loro contenuto, dopo la scelta di una cartella può passare un momento prima che compaiano i risultati.

La riga verde in alto mostra a sinistra `Rom Cleanup Workbench` e a destra la cartella; sotto c'è in verde `Piattaforma:` con il nome della cartella aperta in grassetto, seguito da `*` come nella panoramica se la piattaforma ha impostazioni proprie; poi segue una riga vuota. A destra ci sono i tasti principali della vista, nell'elenco `x Elimina`, `k Mantieni`, `Enter Info gioco`, `F12 Esegui la pulizia` e `F1 / ? Aiuto: altri tasti`. `F1` o `?` mostra al posto dell'elenco tutti i tasti, ordinati per argomento; `Esc`, `F1` o `?` li chiude di nuovo. Nella panoramica entrambi mostrano i tasti della panoramica e sotto, in `Da sapere`, cosa significano gli stati, la scansione e la scansione profonda. La priorità in vigore la mostrano le impostazioni. Nella panoramica anche la parola `Raccolta` è verde. La penultima riga verde mostra lo stato, durante l'analisi per esempio `Analisi: 120 di 2007 file`. Nel frattempo compare anche una barra di avanzamento al centro. La finestra mostra anche gli errori, per esempio nella configurazione, e finché l'analisi fallisce non si può eliminare nulla. Durante l'eliminazione la barra di avanzamento compare al centro e la riga verde mostra per esempio `Eliminazione: 120 di 500 file`; la finestra non accetta input finché l'eliminazione non è finita. Poi comunica il risultato e toglie i file eliminati dall'elenco senza analizzare di nuovo la cartella; i file che non si sono potuti eliminare restano marcati. `F5` analizza di nuovo la cartella se lo vuoi.

Se in tutta la cartella non è marcato nulla e nessun file è sospettato di essere un file di stato o salvataggio, al centro della finestra lampeggia `Niente da fare.`.

I quattro pulsanti di opzione stabiliscono cosa mostra l'elenco:

- `Da verificare`: solo i giochi con un file marcato che contano come problematici, cioè dove qualcosa può andare perso senza volerlo (predefinito al primo avvio)
- `Da eliminare`: tutti i giochi con un file marcato
- `Rimossi del tutto`: i giochi di cui non resterebbe alcun file, per lo più perché le parole da eliminare colpiscono tutti i loro file (per esempio `Ikaruga (Japan).cdi` con la parola da eliminare `Japan`). Vale la pena controllare se le parole da eliminare prendono troppo. La conferma nomina questi giochi separatamente: quelli rimossi dalle parole da eliminare, come richiesto, e gli altri.
- `Tutti i giochi`: tutti i giochi, per esempio per scorrere le informazioni dei giochi o per ordinarli per genere. I loro file si possono allora marcare anche con `x`, e compaiono anche i casi problematici senza file marcato, come uno ZIP illeggibile.

**Solo nomi dei giochi.** L'interruttore `Solo nomi dei giochi` (nella finestra accanto alle viste, nel terminale a destra del campo filtro) o `z` riduce l'elenco alle righe con i nomi dei giochi, senza linee di separazione: così vedi a colpo d'occhio quali giochi ha la piattaforma, con valutazione, giocatori e anno nella colonna `Nota`. Filtro, viste e ordinamento per genere continuano a valere. `Tab` salta da un gioco all'altro, `Enter` mostra la vista del gioco del file mantenuto. `x` e `k` agiscono solo sui file; nella finestra un doppio clic o la freccia a destra apre un singolo gioco. Un secondo `z` mostra di nuovo i file; la scelta resta salvata.

La finestra ricorda l'ultima vista scelta e i file di stato o salvataggio confermati (regola 9) in `rom_cleanup_workbench_settings.json` accanto al programma.

| Tasto | Effetto |
| --- | --- |
| Frecce | seleziona una riga, con Maiusc più righe (per esempio tutti i dischi di un gioco) |
| `Tab` / `Maiusc+Tab` | va al gioco successivo / precedente; viene selezionato il primo file del gioco |
| `x` | marca il file per l'eliminazione; si sposta alla fine del suo gioco |
| `k` | mantiene il file; si sposta nella posizione che gli danno le regole |
| `1` `2` `3` `4` | le viste `Da verificare`, `Da eliminare`, `Rimossi del tutto`, `Tutti i giochi` |
| `z` | mostra solo i nomi dei giochi o di nuovo i file (come l'interruttore `Solo nomi dei giochi`) |
| `Ctrl` + rotellina del mouse | ingrandisce o rimpicciolisce il testo (da 8 a 32 pt, vale finché la finestra resta aperta) |
| `s` | come il pulsante `Impostazioni...`: mostra o nasconde le impostazioni per lingua, priorità, parole da eliminare e ZIP o file normale (vedi [Impostazioni](#impostazioni)) |
| `/` | va al campo del filtro |
| `F12` | come il pulsante `Esegui...`: dopo una conferma elimina, toglie il numero davanti ai nomi dei file mantenuti (regola 10) e conferma i presunti file di stato o di salvataggio (regola 9) |
| `f` | sceglie un'altra cartella, dentro la finestra al posto dell'elenco: apri le cartelle con la freccia, scegline una subito con un doppio clic, oppure scrivi un percorso in `Percorso:`, poi `Seleziona` o `Invio`; `Annulla` o `Esc` mantengono la cartella attuale |
| `r` o `F5` | analizza di nuovo, rilegge anche la configurazione |
| `c` | mostra i riconoscimenti |
| `Enter` | in una piattaforma della raccolta: tutto ciò che si sa del gioco evidenziato (anche doppio clic nella finestra); `Enter`, `Esc` o `q` chiude |
| `n` | in una piattaforma della raccolta: segna i file selezionati come `non è un gioco` (per esempio un file BIOS) o lo annulla |
| `g` | in una piattaforma della raccolta: il rapporto gamelist della piattaforma |
| `e` | nella vista del gioco: modifica le informazioni del gioco; `Ctrl+S` salva, `Esc` torna indietro |
| `w` | in una piattaforma della raccolta: scrive il suo `gamelist.xml` dal database (dopo una domanda) |
| `m` | in una piattaforma della raccolta: elimina i suoi file multimediali inutilizzati (dopo una domanda) |
| `F1` o `?` | mostra o nasconde tutti i tasti |
| `q` o `Esc` | chiude senza eliminare nulla; in una piattaforma di una raccolta entrambi tornano prima alla panoramica; dopo modifiche a mano il programma chiede prima |

Linee orizzontali separano i giochi, e un gioco su due ha lo sfondo grigio scuro. La colonna `Dimensione` mostra la dimensione di ogni file in KB, arrotondata per eccesso come in Esplora file di Windows (`1.234 KB`); `?` significa che non è stato possibile leggere la dimensione. La dimensione viene letta durante l'analisi. I file mantenuti sono mostrati in grassetto verde sotto `Mantieni:`, quelli da eliminare in rosso sotto `Da eliminare`. La finestra mostra testo bianco in Lucida Sans Typewriter 11 pt su sfondo nero. Se il font non è installato, Windows sceglie in silenzio un sostituto. I file spostati a mano hanno lo sfondo marrone e portano la nota `A mano`; mentre la riga è selezionata, appare blu. Le note del programma restano invariate, anche se si riferiscono a un file che hai spostato.

`Da verificare` nasconde i giochi non problematici, `Rimossi del tutto` tutti i giochi di cui resta qualcosa. **I loro file marcati vengono comunque eliminati all'eliminazione**; la conferma ne indica il numero. I giochi che hai modificato a mano restano sempre visibili, a meno che il filtro non li nasconda.

### Filtro

Il campo del filtro a sinistra nella riga in basso restringe la vista attuale ai giochi con un nome di file che contiene il modello. Un gioco resta completo se uno dei suoi file corrisponde. L'elenco si aggiorna poco dopo la digitazione; il contenuto dei file non viene letto.

- `*` sta per un numero qualsiasi di caratteri, `?` per esattamente uno. Tutti gli altri caratteri, compresi `[` e `]`, valgono alla lettera, e maiuscole e minuscole non contano. Gli spazi all'inizio e alla fine contano solo tra virgolette: `" by "` trova `Mario by Mick` ma non `Moby Dick`; senza virgolette `by` li trova entrambi.
- Il modello può comparire in qualsiasi punto del nome: `Beta`, `*Beta*` e `Mario?2` trovano tutti anche `Super Mario 2 (Beta).nes`. Di conseguenza `S*` trova ogni nome che contiene una `S`, non solo i nomi che iniziano con essa.
- `Invio`, `Tab` e la freccia giù tornano all'elenco; `Esc` svuota il filtro e torna all'elenco.
- Finché il cursore è nel campo, i tasti scrivono solo lì: `x`, `k`, `Enter`, `f`, `r`, `F5` ed `Esc` non eseguono le loro funzioni dell'elenco.
- Il filtro resta attivo dopo `F5`, dopo l'eliminazione e dopo la scelta di un'altra cartella. Non viene salvato.

**Il filtro cambia solo la visualizzazione. I file marcati nascosti dal filtro vengono comunque eliminati quando elimini**; la conferma ne indica il numero.

### Impostazioni

Il pulsante `Impostazioni...` nella riga in basso, o `s`, mostra le modifiche più frequenti a `redundanz_config.json` nella finestra principale, al posto dell'elenco dei file. `Salva` o `Annulla`, `Esc`, `Ctrl+E` o un altro clic su `Impostazioni...` riportano l'elenco. Nel frattempo il filtro, le viste, `Esegui...`, `Analizza di nuovo` e `Cartella...` sono bloccati, e `x`, `k`, `Enter` e `F12` non fanno nulla, perché nell'elenco nascosto non cambi niente.

- **Lingua:** Stabilisce la lingua dell'interfaccia. Scegli tra le sei lingue. Una nuova lingua vale dal prossimo avvio del programma.
- **Priorità:** Stabilisce quali versioni regionali hanno la precedenza sulle altre. La regione migliore in alto; le info aggiuntive come `Beta` o `Proto` vanno dopo `none`, così questi file vengono per ultimi (regola 6). Seleziona una voce e spostala con `Su` e `Giù`, rimuovila con `Rimuovi` o con il tasto `Canc`, e aggiungine una nuova con il campo sotto l'elenco e `Aggiungi` (o `Invio`).
- **Parole da eliminare:** Stabiliscono quali versioni di un gioco vengono eliminate in ogni caso. Separate da virgole, per esempio `Hack, Hacks`. I file che le contengono vengono marcati per l'eliminazione (regola 2).
- **Stesso gioco come file normale e come file ZIP:** Stabilisce quale dei due resta quando entrambi sono della stessa versione. `Mantieni il file normale` (predefinito) marca il file ZIP, `Mantieni il file ZIP` marca i file normali (vedi [File ZIP](#file-zip)).
- **Preferiti e giochi giocati (gamelist.xml):** `Solo un avviso nell'elenco` (predefinito) lascia decidere le regole; un file che deve essere eliminato ed è preferito o ha tempo di gioco secondo il `gamelist.xml` riceve l'avviso `Preferito o giocato – verrà eliminato`. `Preferire di tenerli` mantiene, all'interno di un gioco, il file preferito, altrimenti quello con più tempo di gioco; se le regole avevano mantenuto un altro singolo file, questo cede il posto, e i salvataggi seguono il file mantenuto. Vale in generale o per piattaforma (`prefer_played` nella configurazione).

`Salva` scrive il file e analizza di nuovo la cartella se la priorità, le parole o la scelta tra file normale e file ZIP sono cambiate; se hai modificato marcature a mano, il programma chiede prima, perché queste modifiche vanno perse. Tutte le altre voci del file restano come sono. I valori errati, come un elenco di regioni vuoto o la stessa regione due volte, vengono segnalati, non viene scritto nulla e le impostazioni restano aperte. Se il file non si può leggere, le impostazioni non si aprono, così da non poter sovrascrivere voci che non conoscono. Con `--config` le impostazioni modificano quel file; con `--priority` per questa esecuzione resta valida la priorità indicata lì.

È problematico solo ciò per cui qualcosa può andare perso senza volerlo. Ciò che chiedono le parole da eliminare è voluto, e un file il cui contenuto si trova in un file mantenuto (`Contenuto identico a …`) non va perso. Un gioco conta come problematico se

- nessuno dei suoi file verrebbe mantenuto senza che le parole da eliminare lo chiedano (un gioco che se ne va del tutto per le parole da eliminare o come salvataggio senza ROM sta in `Rimossi del tutto`, ma non è problematico),
- il contenuto di uno ZIP marcato non compare altrove (`Il contenuto del gioco differisce dalla versione mantenuta`),
- uno ZIP è danneggiato, cifrato o non leggibile,
- un file viene mantenuto come possibile file di stato o salvataggio (regola 9),
- le regole hanno deciso solo per `Parità` e il file marcato ha un contenuto diverso,
- più ZIP della stessa versione hanno contenuto diverso,
- i nomi dei file scrivono il gioco in modo diverso (`Title 1-2` e `Title 12`) e un file marcato di una grafia diversa da ogni file mantenuto ha un contenuto diverso,
- un file marcato ha un tipo di file diverso da quelli mantenuti (`.nes` e `.sfc`) e il suo contenuto non si trova in nessun file mantenuto.

Se una parola da eliminare marca un file, questo non rende il gioco problematico in nessuno di questi casi.

La finestra usa `tkinter`, che fa parte della normale installazione di Python su Windows. Se manca, il programma lo segnala e non elimina nulla.

## Dopo la pulizia automatica

Anche dopo la pulizia automatica possono restare versioni ridondanti di un gioco. Il modo più semplice per trovarle è il filtro (tasto `/` e poi il nome del gioco). Dopo puoi marcare i file che vanno ancora eliminati.

## Versione per terminale (Linux)

Lo stesso programma funziona anche in un terminale di testo, per esempio tramite SSH (PuTTY, MobaXterm), in `tmux` o sulla console di Linux. Mostra lo stesso elenco, applica le stesse regole e condivide con la finestra `redundanz_config.json`, `rom_cleanup_workbench_settings.json` e `translations.py`.

Su Linux si avvia da sola quando non c'è un display grafico (né `DISPLAY` né `WAYLAND_DISPLAY` sono impostate, come tramite SSH). `--tui` la avvia ovunque altrove, anche su Windows; usalo dove esiste un display grafico ma vuoi il terminale, per esempio in MobaXterm o sotto WSL.

Richiede [Textual](https://textual.textualize.io/) (testato con 8.2.8). Come installarlo e avviare il programma è descritto in [Installazione](#installazione) e [Uso](#uso).

Senza Textual il programma lo dice e non elimina nulla. Lo schermo ha le righe della finestra dall'alto in basso: la riga verde del titolo con la cartella, la piattaforma con i tasti principali, l'elenco, il campo filtro con l'interruttore `Solo nomi dei giochi`, le quattro viste e la riga verde di stato. Nell'elenco ogni gioco inizia con il suo nome in grassetto, seguito da trattini fino al bordo destro; un avviso come `Grafie diverse del nome` sta in questa riga. In un terminale stretto, per esempio le 80 colonne di PuTTY, i nomi dei file e gli avvisi lunghi vanno a capo nella loro colonna invece di uscire dallo schermo. `Niente da fare.` lampeggia con il lampeggio proprio del terminale; in PuTTY il testo lampeggiante va forse prima attivato. Domande e messaggi compaiono in una cornice sopra l'elenco, con pulsanti nella lingua del programma; `No` è preselezionato.

A destra della piattaforma ci sono i tasti principali; `F1` o `?` li mostra tutti, ordinati per tema. La finestra e la versione per terminale hanno gli stessi tasti.

| Tasto | Effetto |
| --- | --- |
| Frecce | seleziona una riga, con Maiusc più righe |
| `Tab` / `Maiusc+Tab` | gioco successivo / precedente; viene selezionato il suo primo file |
| `x` / `k` | marca i file selezionati per l'eliminazione / li mantiene |
| `1` `2` `3` `4` | le viste `Da verificare`, `Da eliminare`, `Rimossi del tutto`, `Tutti i giochi` |
| `z` | mostra solo i nomi dei giochi o di nuovo i file (come l'interruttore `Solo nomi dei giochi`) |
| `/` | va al campo del filtro |
| `F12` | esegui: dopo una conferma elimina (come `Esegui...`) |
| `f` | sceglie un'altra cartella: `Destra` o `Spazio` apre una cartella, `Sinistra` la chiude, `Invio` o un doppio clic la sceglie; si può anche scrivere un percorso |
| `s` | impostazioni: `Maiusc+Su`/`Maiusc+Giù` spostano una regione, `Canc` la rimuove, `Ctrl+S` salva, `Esc` annulla |
| `r` o `F5` | analizza di nuovo, rilegge anche la configurazione |
| `c` | mostra i riconoscimenti |
| `Enter` | in una piattaforma della raccolta: tutto ciò che si sa del gioco evidenziato (anche doppio clic nella finestra); `Enter`, `Esc` o `q` chiude |
| `n` | in una piattaforma della raccolta: segna i file selezionati come `non è un gioco` (per esempio un file BIOS) o lo annulla |
| `g` | in una piattaforma della raccolta: il rapporto gamelist della piattaforma |
| `e` | nella vista del gioco: modifica le informazioni del gioco; `Ctrl+S` salva, `Esc` torna indietro |
| `w` | in una piattaforma della raccolta: scrive il suo `gamelist.xml` dal database (dopo una domanda) |
| `m` | in una piattaforma della raccolta: elimina i suoi file multimediali inutilizzati (dopo una domanda) |
| `F1` o `?` | mostra o nasconde tutti i tasti (anche `?`, perché alcuni terminali tengono `F1` per il proprio aiuto) |
| `q` o `Esc` | chiude senza eliminare nulla; in una piattaforma di una raccolta entrambi tornano prima alla panoramica; dopo modifiche a mano il programma chiede prima |
| In una domanda | `Sinistra`/`Destra` scelgono un pulsante, `Invio` lo preme, `Esc` risponde `No` |

Funziona anche il mouse: un clic seleziona una riga, la rotellina scorre, e le viste e i pulsanti si possono cliccare. Le lettere scritte in un campo restano nel campo, anche se digitate velocemente o incollate: una `x` nel filtro non marca mai un file.

**Colori e caratteri.** Con 256 colori o più, la versione per terminale usa i colori della finestra, ma nero dietro ogni gioco (niente strisce). Dove il terminale ha solo 16 colori (`TERM=xterm`, `TERM=linux`), passa a semplici colori ANSI: selezione blu, righe di titolo e di stato verdi, file mantenuti verdi e file marcati rossi, righe marroni con testo nero modificate a mano. Sulla console di Linux, in terminali come `vt100` e quando la locale indica un set di caratteri diverso da UTF-8 (per esempio `en_US` o `de_DE.ISO-8859-1`), disegna solo caratteri ASCII: viste come `(*)`, cornici fatte di `+`, `-` e `|`. `--ascii` lo impone. PuTTY si presenta come `xterm` (16 colori); per i colori della finestra imposta *Connection → Data → Terminal-type string* su `xterm-256color`. Nomi di file e testi in altre scritture, come il giapponese, richiedono comunque un terminale e un font in grado di mostrarli.

Differenze rispetto alla finestra: niente zoom del testo, perché il font appartiene al terminale (in PuTTY: *Window → Appearance*); e i giochi non sono a strisce ma iniziano con una linea tratteggiata. Con 16 colori le righe verdi hanno testo nero, che resta leggibile su un verde chiaro. Durante l'eliminazione, la versione per terminale elimina in background e mostra la barra di avanzamento; tutti i tasti sono bloccati finché non ha finito. La finestra e la versione per terminale conservano la vista e i file di salvataggio confermati nello stesso `rom_cleanup_workbench_settings.json`.

## Configurazione: `redundanz_config.json`

Il file si trova accanto al programma e viene riletto a ogni analisi. Lingua, priorità, parole da eliminare e la scelta tra file normale e file ZIP si cambiano più facilmente nella finestra con `Impostazioni...` (vedi [Impostazioni](#impostazioni)). Nel file stesso basta cambiare l'ordine in `region_priority` e salvare il file:

```json
"region_priority": ["USA", "Europe", "none", "Japan", "Beta"],
"delete_tags": [],
"prefer_zip": false,
```

Se il file contiene un errore, per esempio una voce scritta male, non avviene nessuna analisi e non viene eliminato nulla. Il file fornito è così: la lingua è l'inglese, la priorità USA, Europe, none, Japan, Beta, non ci sono parole da eliminare e accanto a un file ZIP resta il file normale. I file senza regione vengono quindi prima di quelli giapponesi. Se manca il file o una voce, valgono gli stessi valori predefiniti.

- `language`: la lingua della finestra, delle note e dell'output nel terminale (vedi sotto).
- `region_priority`: regioni e info aggiuntive, la migliore per prima. `none` sta per i file senza una regione nota; funzionano anche le parole delle altre lingue (`keine`, `nessuna`, `ninguna`, `aucune`, `なし`). Info aggiuntive come `Beta` dopo `none` mettono questi file per ultimi (regola 6); `Beta` vale anche per `Beta 2`.
- `region_aliases`: altre grafie di una regione, per esempio `Europa` per `Europe`. Sono incluse anche le forme brevi `U`, `E` e `J` dei nomi GoodTools come `Title (J) [o1].nes`.
- `delete_tags`: le parole da eliminare, info aggiuntive che portano sempre all'eliminazione (regola 2). Per impostazione predefinita l'elenco è vuoto. Una parola da eliminare conta come parola intera in qualsiasi punto di una parentesi: `Hack` corrisponde a `(Hack)`, `(Hack 2)`, `(Hack by Someone)` e `(Micks Hack)`, ma non a `(Hacks)` o `(Hackers)`, né a una parola fuori dalle parentesi come in `Hack Attack (USA)`; chi vuole eliminare gli hack inserisce quindi sia `Hack` sia `Hacks`.
- `part_tags`: parti di una versione, per esempio `Disc 1`.
- `prefer_zip`: `false` (predefinito) mantiene il file normale quando un gioco esiste come file normale e come file ZIP della stessa versione, `true` mantiene il file ZIP.

I file più vecchi possono contenere ancora `low_priority_tags`, info aggiuntive con la priorità più bassa. Il programma legge le sue voci come se stessero alla fine di `region_priority`, dopo `none`; le impostazioni le spostano lì quando salvano, e la voce scompare.

### Lingua

```json
"language": "de",
```

| Valore | Lingua |
| --- | --- |
| `en` | inglese (predefinita) |
| `de` | tedesco |
| `it` | italiano |
| `es` | spagnolo |
| `fr` | francese |
| `ja` | giapponese |

La lingua vale per la finestra, le note e l'output nel terminale, e il programma la legge all'avvio: dopo averla cambiata, chiudi il programma e riavvialo. `F5` non cambia la lingua. Un valore sconosciuto conta come errore nella configurazione, come descritto sopra. Le regole decidono allo stesso modo in ogni lingua. I testi si trovano in `translations.py`.

Per il giapponese Windows mostra i caratteri con un font sostitutivo, perché Lucida Sans Typewriter non ha caratteri giapponesi.

## Regole

Alcuni file il programma li ignora del tutto: non compaiono da nessuna parte e non vengono mai eliminati. Contano come parentesi `( )`, `[ ]` e `{ }`, ovunque allo stesso modo: per il nome del gioco, la priorità, le versioni e le parole da eliminare.

- I file il cui nome inizia con `gamelist`, senza distinzione tra maiuscole e minuscole. Non sono file ROM.
- I file nascosti: nomi che iniziano con un punto, come `.xxx` o `.DS_Store`, e file con l'attributo di Windows «nascosto».

1. I file vanno insieme se il testo prima della prima parentesi è uguale. Maiuscole e minuscole, spazi, trattini e trattini bassi non contano, quindi `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. Così vale anche `Title 1-2` = `Title 12`. Inoltre valgono come uguali `und` = `and` = `&` = `&&`, `Sullivan's` = ``Sullivan`s`` = `Sullivan´s` = `Sullivans` (gli apostrofi non contano), i numeri romani da `I` a `IX` come parola intera uguali a `1`-`9` (`Final Fantasy VII` = `Final Fantasy 7`; da `X` in poi restano come sono, perché `Mega Man X` e `Mega Man 10` sono due giochi) e `The Title` = `Title The` = `Title, The` = `Title`. Un `The` in mezzo al nome conta invece. Allo stesso modo vale `vs` = `vs.` = `versus`. Un numero davanti al nome, per esempio da una raccolta numerata, non conta: `057 Robocop vs Terminator` = `057 - Robocop vs Terminator` = `Robocop vs Terminator`. Se il nome è fatto solo del numero (`1942`) o il numero è attaccato alla parola (`2Fast`), resta parte del nome; `4 in 1` e `3 in 1` restano giochi diversi. Poiché i nomi coincidono allora solo grazie al confronto, il gioco conta come problematico (`Grafie diverse del nome`), se un file marcato dell'altra grafia ha un contenuto diverso da quelli mantenuti.
2. I file con una parola da eliminare (`delete_tags`, nessuna come predefinito, per esempio `Hack` e `Hacks`) vengono sempre marcati, anche se è l'unico file del gioco. `k` mantiene comunque un tale file. L'avviso dice allora `Eliminato per la parola da eliminare (Hack) - come richiesto`; per questi file non c'è un avviso sul contenuto, il loro contenuto deve sparire. Eccezione: se una parentesi nomina più regioni e una di esse è esattamente la parola da eliminare, ma un'altra è una regione del tuo elenco di priorità, la parola da eliminare non vale per quella parentesi. `(Japan, USA)` è anche la versione USA: con la parola da eliminare `Japan` e `USA` nell'elenco resta e viene classificata come versione USA; `(Japan)` da solo continua a essere marcato.
3. Tra i file rimanenti viene mantenuto quello con la voce migliore in `region_priority`. All'interno di una parentesi conta la voce migliore: con `(USA, Japan)` la migliore delle due. Tra parentesi diverse conta la peggiore: `(USA) (Beta)` vale come `Beta` (regola 6).
4. Tutti i file della stessa versione vengono mantenuti insieme, per esempio `(Disc 1)` e `(Disc 2)` oppure `.cue` e `.bin`. Tutto il resto viene marcato. Eccezione: se solo una parte di questi file ha un numero davanti al nome (`073 Batman (USA).sfc` e `Batman (USA).sfc`), restano quelli con il numero e gli altri vengono marcati (`Preferito il nome con numero`).
5. Una regione che non è in `region_priority` vale come `none`. Questo vale anche per indicazioni come `(Rev 1)`.
6. Le info aggiuntive come `Beta`, `Proto` o `Alpha` si scrivono in `region_priority` dopo `none`. I file che le contengono vengono dopo tutti gli altri, anche dopo i file senza regione, e nell'ordine dell'elenco: con `none, Beta, Proto` una Beta viene prima di un Proto. Vengono mantenuti solo se non c'è un file migliore del gioco. Tra di loro conta di nuovo la regione, poi la versione della regola 7, poi il numero dopo l'info aggiuntiva: `Beta 2` vince su `Beta 1`, e `Beta 1` su `Beta` senza numero. I numeri sono confrontati numericamente (`Beta 10` prima di `Beta 9`). Il file che perde riceve la nota `Beta precedente`.
7. A parità di priorità vince il numero di versione più alto, confrontato numericamente (`v1.10` prima di `v1.9`). Tra parentesi sono riconosciuti `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` e `Rev A`; nel nome del gioco solo la forma `Title v1.1`, anche con `-` o `_` al posto dello spazio. Un file senza versione perde contro uno con versione. La regione conta prima della versione.
8. Dopo di che vince il file con un numero davanti al nome (`073 Batman` prima di `Batman`), poi quello con meno informazioni aggiuntive, poi un file senza ZIP (con `prefer_zip`: un file ZIP), poi l'ordine alfabetico. Il rapporto mostra allora `Parità`.
9. Un file più piccolo di 1/4 del file più grande del gioco viene messo da parte prima delle regole da 3 a 8 e mantenuto: potrebbe essere un file di stato o di salvataggio. Non può quindi né essere eliminato né scalzare la vera ROM, per esempio `1941.state` il file `1941.zip`. La colonna degli avvisi mostra allora `Possibile file di stato o salvataggio` e il gioco conta come problematico. Un tale gioco compare in `Da verificare`, `Da eliminare` e `Tutti i giochi`, anche se nessuno dei suoi file è marcato. All'eliminazione il programma conferma tutti gli altri file sospetti come legittimi: restano dove sono, continuano a non essere mai eliminati e non compaiono più in `Da verificare` e `Da eliminare`, anche dopo `F5` o un riavvio. La conferma ne indica il numero. Il programma li ricorda con percorso e dimensione in `rom_cleanup_workbench_settings.json`; se la dimensione cambia, il file torna sospetto. Se nulla è marcato, `F12` propone di confermarli senza eliminare nulla. Gli ZIP contano con la loro dimensione decompressa. Ciò non vale per un piccolo file normale accanto a un grande file normale della sua stessa versione, per esempio un `.cue` accanto al suo `.bin`, né per un file con la stessa estensione del file più grande (un piccolo `.nes` accanto a un grande `.nes` è una ROM su cui decidono le regole da 3 a 8), né per i file marcati per `delete_tags` o per uno ZIP difettoso. Con `x` puoi comunque marcare il file a mano. I salvataggi con un'estensione tipica (`.srm`, `.sav`, `.eep`, `.mpk`, `.fla`, `.sra`, `.rtc`, `.dsv`, `.mcr`, `.state`, `.state1` …, `.state.auto`, `.st0` …, `.ss0` …) non rientrano in questa regola: un emulatore carica un salvataggio solo se si chiama esattamente come la ROM (senza estensione). Un salvataggio resta quindi solo se un file mantenuto ha esattamente questo nome, per esempio `Mario Kart 64 (USA).srm` accanto a `Mario Kart 64 (USA).n64`. Ogni altro viene marcato, anche uno di un'altra regione o di un'altra versione come `Mario Kart 64 (U) [!].mpk`, con l'avviso `Salvataggio senza un file ROM con lo stesso nome`. Le parole da eliminare valgono anche per i salvataggi.
10. All'esecuzione, dopo l'eliminazione, a ogni file mantenuto viene tolto il numero davanti al nome, con gli spazi, punti, trattini o trattini bassi che seguono: `073 Batman (USA).sfc` diventa `Batman (USA).sfc`, `057 - Robocop.md` diventa `Robocop.md`. La conferma indica prima il numero di file e un esempio; se nulla è marcato, `F12` chiede solo della rinomina. Il numero resta se al gioco appartiene un file `.cue`, `.gdi`, `.m3u`, `.mds`, `.toc` o `.ccd` (nomina i nomi dei file nel suo contenuto) o se il nome senza numero è già occupato; la conferma indica anche questo numero. Il contenuto degli ZIP non viene rinominato. Nella riga del titolo di un gioco il nome compare nella grafia del primo file mantenuto (`Street Fighter II` o `Street Fighter 2`), sempre senza numero; se sposti file con `k` o `x`, il titolo si adegua. Un numero conta come numero di elenco solo quando è chiaro: con uno zero iniziale (`057`), con un separatore dopo (`057 - `, `283. `) o se lo stesso gioco c'è anche senza numero (`283 Dynamite Bowl` accanto a `Dynamite Bowl (J)`); se un numero di un gioco è chiaro, tutti i suoi numeri contano come numeri di elenco. Altrimenti il numero appartiene al titolo e resta, nel nome del file come nella riga del titolo: `1080 Snowboarding`, `720 Degrees`.

## File ZIP

Ogni file ZIP viene letto per intero, anche se è l'unico file di un gioco. Il suo contenuto viene confrontato con gli altri file del gioco tramite SHA-256.

- **Stesso contenuto di un file mantenuto:** il file ZIP viene marcato e il rapporto indica il file con lo stesso contenuto.
- **Se dopo la selezione restano uno ZIP e un file normale:** lo ZIP viene sempre marcato, anche con contenuto diverso, se è l'unico file che contiene una parte come `(Disc 1)` o se non è leggibile.
- **Con `Mantieni il file ZIP` (`prefer_zip`):** È il contrario: accanto a un file ZIP leggibile della stessa versione vengono marcati i file normali (`Preferito il file ZIP`). Se il contenuto di un tale file non compare in nessuno ZIP mantenuto, il rapporto mostra `Il contenuto del gioco differisce dal file ZIP mantenuto` e il gioco è considerato problematico (`Il contenuto di un file normale marcato non viene mantenuto`). Uno ZIP non leggibile non scalza nessun file normale. La priorità viene comunque prima: un file normale `(USA)` vince su uno ZIP `(Japan)`.
- **Più ZIP della stessa versione con contenuto diverso:** vengono mantenuti tutti e il rapporto lo segnala.
- **Marcato, ma il contenuto non compare in nessun file mantenuto:** il rapporto mostra `Il contenuto del gioco differisce dalla versione mantenuta`. Il file resta marcato.
- **Nessuna regione o versione nel nome dello ZIP:** l'informazione viene presa dai file nello ZIP, purché abbiano lo stesso nome del gioco.
- **ZIP danneggiato o cifrato:** il file viene sempre marcato, anche se è l'unico file del gioco. Il contenuto di uno ZIP cifrato non viene verificato.
- **ZIP bloccato o metodo sconosciuto (per esempio Deflate64):** questo non dice nulla sullo stato del file. Senza un file normale del gioco viene mantenuto e indicato nel rapporto.

## Sviluppare il programma con Claude Code

Il programma è software libero: puoi clonare il repository e svilupparlo ulteriormente con [Claude Code](https://claude.com/claude-code), senza programmare di persona. È anche così che è stato scritto.

1. Installa Claude Code. Serve un abbonamento a Claude o un account per l'API di Claude. Su Windows in PowerShell:

   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```

   Su Linux:

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

2. Clona il repository e avvia Claude Code al suo interno:

   ```bash
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   cd rom-cleanup-workbench
   claude
   ```

3. Descrivi con parole tue che cosa deve cambiare, per esempio "Aggiungi un'opzione che mostra solo i file ZIP". Claude Code legge il codice, propone modifiche e chiede prima di cambiare file o eseguire comandi. Poi fagli eseguire i test (`python -m unittest` nella cartella `Rom Cleanup Workbench`) e prova la modifica su una copia della tua raccolta.

I piani delle modifiche precedenti si trovano in `docs/`. Chi distribuisce le proprie modifiche deve pubblicarle anch'esse sotto la GPL.

## Licenza ed esclusione di responsabilità

Copyright (C) 2026 M. Kärcher

Rom Cleanup Workbench è software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della GNU General Public License pubblicata dalla Free Software Foundation, nella versione 3 della licenza o (a tua scelta) in qualsiasi versione successiva. Il testo completo si trova in [LICENSE](<../LICENSE>); ha valore legale solo questo testo originale inglese.

**Uso a proprio rischio.** Il programma elimina file e non è prevista alcuna garanzia; chi lo usa si assume tutti i rischi che ne derivano. Consigliamo vivamente di usarlo solo su una copia della propria raccolta di ROM.

## Riconoscimenti

- Idea: M. Kärcher
- Programmazione: Claude Code
