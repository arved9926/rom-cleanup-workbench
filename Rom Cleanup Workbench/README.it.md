# Rom Cleanup Workbench

[English](README.md) · [Deutsch](README.de.md) · **Italiano** · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md)

**Guida per l'utente con schermate:** [PDF](<docs/Rom Cleanup Workbench - Guida utente.pdf>) · [Word](<docs/Rom Cleanup Workbench - Guida utente.docx>)

**Video:** [come funziona il programma (YouTube)](https://youtu.be/D1yXZQXg-iM)

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

Senza cartella, la finestra la chiede. Chi vuole la versione per terminale aggiunge `--tui`.

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
| `--review all` | apre la finestra con `Tutte le marcature` per questo avvio |
| `--review problems` | apre la finestra con `Marcature problematiche` per questo avvio |
| `--priority USA Europe Japan none` | imposta la priorità per questa esecuzione |
| `--delete-tag Hack Hacks Proto` | imposta le parole da eliminare per questa esecuzione |
| `--config file.json` | usa un'altra configurazione |
| `--report-only` | senza finestra: stampa solo il rapporto nel terminale |
| `--yes` | senza finestra: elimina i file marcati senza chiedere |
| `--all` | con `--report-only`: mostra anche i giochi senza file marcati |
| `--tui` | usa la versione per terminale invece della finestra (automatico su Linux senza display grafico) |
| `--ascii` | versione per terminale solo con caratteri ASCII (automatico sulla console di Linux); implica `--tui` |

Le opzioni della riga di comando e il loro aiuto (`--help`) sono sempre in inglese.

I test si eseguono con `python -m unittest`.

## Finestra di analisi

Poiché i file ZIP devono essere estratti per ottenere dimensione, checksum SHA-256 e nome del loro contenuto, dopo la scelta di una cartella può passare un momento prima che compaiano i risultati.

La riga verde in alto mostra `Rom Cleanup Workbench` a sinistra e la cartella a destra; sotto, la finestra indica la priorità in uso con la sua provenienza. La penultima riga verde mostra lo stato, durante l'analisi per esempio `Analisi: 120 di 2007 file`. In quel momento compare anche una barra di avanzamento al centro. La finestra mostra anche gli errori, per esempio nella configurazione, e finché l'analisi non riesce non si può eliminare nulla. Durante l'eliminazione la barra di avanzamento compare al centro e la riga verde mostra per esempio `Eliminazione: 120 di 500 file`; la finestra non accetta input finché l'eliminazione non è terminata. Al termine comunica il risultato e toglie dall'elenco i file eliminati senza analizzare di nuovo la cartella; i file che non è stato possibile eliminare restano marcati. `F5` analizza di nuovo la cartella quando lo desideri.

Se in tutta la cartella non è marcato nulla e nessun file è sospettato di essere un file di stato o salvataggio, al centro della finestra lampeggia `Niente da fare.`.

I tre pulsanti di opzione decidono cosa mostra l'elenco:

- `Marcature problematiche`: solo i giochi con un file marcato che sono considerati problematici (predefinita al primo avvio)
- `Tutte le marcature`: tutti i giochi con un file marcato
- `Tutti i file ROM`: tutti i giochi. I loro file si possono allora marcare anche con `x`, e compaiono anche i casi problematici senza file marcato, come uno ZIP non leggibile.

La finestra ricorda l'ultima vista scelta e i file di stato o salvataggio confermati (regola 9) in `rom_cleanup_workbench_settings.json` accanto al programma.

| Tasto | Effetto |
| --- | --- |
| Frecce | seleziona una riga, con Maiusc più righe (per esempio tutti i dischi di un gioco) |
| `Tab` / `Maiusc+Tab` | va al gioco successivo / precedente; viene selezionato il primo file del gioco |
| `x` | marca il file per l'eliminazione; si sposta alla fine del suo gioco |
| `k` | mantiene il file; si sposta nella posizione che gli danno le regole |
| `1` `2` `3` | le viste `Marcature problematiche`, `Tutte le marcature`, `Tutti i file ROM` |
| `Ctrl` + rotellina del mouse | ingrandisce o rimpicciolisce il testo (da 8 a 32 pt, vale finché la finestra resta aperta) |
| `s` | come il pulsante `Impostazioni...`: mostra o nasconde le impostazioni per lingua, priorità, parole da eliminare e ZIP o file normale (vedi [Impostazioni](#impostazioni)) |
| `/` | va al campo del filtro |
| `Enter` | come il pulsante `Esegui...`: elimina dopo una conferma, toglie il numero davanti ai nomi dei file mantenuti (regola 10) e conferma i possibili file di stato o salvataggio (regola 9) |
| `f` | sceglie un'altra cartella, dentro la finestra al posto dell'elenco: apri le cartelle con la freccia, scegline una subito con un doppio clic, oppure scrivi un percorso in `Percorso:`, poi `Seleziona` o `Invio`; `Annulla` o `Esc` mantengono la cartella attuale |
| `r` o `F5` | analizza di nuovo, rilegge anche la configurazione |
| `c` o `F1` | mostra i riconoscimenti |
| `q` o `Esc` | chiude senza eliminare nulla; dopo modifiche a mano il programma chiede prima |

Linee orizzontali separano i giochi, e un gioco su due ha lo sfondo grigio scuro. La colonna `Dimensione` mostra la dimensione di ogni file in KB, arrotondata per eccesso come in Esplora file di Windows (`1.234 KB`); `?` significa che non è stato possibile leggere la dimensione. La dimensione viene letta durante l'analisi. I file mantenuti sono mostrati in grassetto verde sotto `Mantieni:`, quelli da eliminare in rosso sotto `Da eliminare`. La finestra mostra testo bianco in Lucida Sans Typewriter 11 pt su sfondo nero. Se il font non è installato, Windows sceglie in silenzio un sostituto. I file spostati a mano hanno lo sfondo marrone e portano la nota `A mano`; mentre la riga è selezionata, appare blu. Le note del programma restano invariate, anche se si riferiscono a un file che hai spostato.

`Marcature problematiche` nasconde i giochi senza problemi. **I loro file marcati vengono comunque eliminati quando elimini**; la conferma ne indica il numero. I giochi che hai modificato a mano restano sempre visibili, a meno che il filtro non li nasconda.

### Filtro

Il campo del filtro a sinistra nella riga in basso restringe la vista attuale ai giochi con un nome di file che contiene il modello. Un gioco resta completo se uno dei suoi file corrisponde. L'elenco si aggiorna poco dopo la digitazione; il contenuto dei file non viene letto.

- `*` sta per un numero qualsiasi di caratteri, `?` per esattamente uno. Tutti gli altri caratteri, compresi `[` e `]`, valgono alla lettera, e maiuscole e minuscole non contano.
- Il modello può comparire in qualsiasi punto del nome: `Beta`, `*Beta*` e `Mario?2` trovano tutti anche `Super Mario 2 (Beta).nes`. Di conseguenza `S*` trova ogni nome che contiene una `S`, non solo i nomi che iniziano con essa.
- `Invio`, `Tab` e la freccia giù tornano all'elenco; `Esc` svuota il filtro e torna all'elenco.
- Finché il cursore è nel campo, i tasti scrivono solo lì: `x`, `k`, `Enter`, `f`, `r`, `F5` ed `Esc` non eseguono le loro funzioni dell'elenco.
- Il filtro resta attivo dopo `F5`, dopo l'eliminazione e dopo la scelta di un'altra cartella. Non viene salvato.

**Il filtro cambia solo la visualizzazione. I file marcati nascosti dal filtro vengono comunque eliminati quando elimini**; la conferma ne indica il numero.

### Impostazioni

Il pulsante `Impostazioni...` nella riga in basso, o `s`, mostra le modifiche più frequenti a `redundanz_config.json` nella finestra principale, al posto dell'elenco dei file. `Salva` o `Annulla`, `Esc`, `Ctrl+E` o un altro clic su `Impostazioni...` riportano l'elenco. Nel frattempo il filtro, le viste, `Esegui...`, `Analizza di nuovo` e `Cartella...` sono bloccati, e `x`, `k` e `Enter` non fanno nulla, così che nell'elenco nascosto non possa cambiare niente.

- **Lingua:** Stabilisce la lingua dell'interfaccia. Scegli tra le sei lingue. Una nuova lingua vale dal prossimo avvio del programma.
- **Priorità:** Stabilisce quali versioni regionali hanno la precedenza sulle altre. La regione migliore in alto; le info aggiuntive come `Beta` o `Proto` vanno dopo `none`, così questi file vengono per ultimi (regola 6). Seleziona una voce e spostala con `Su` e `Giù`, rimuovila con `Rimuovi` o con il tasto `Canc`, e aggiungine una nuova con il campo sotto l'elenco e `Aggiungi` (o `Invio`).
- **Parole da eliminare:** Stabiliscono quali versioni di un gioco vengono eliminate in ogni caso. Separate da virgole, per esempio `Hack, Hacks`. I file che le contengono vengono marcati per l'eliminazione (regola 2).
- **Stesso gioco come file normale e come file ZIP:** Stabilisce quale dei due resta quando entrambi sono della stessa versione. `Mantieni il file normale` (predefinito) marca il file ZIP, `Mantieni il file ZIP` marca i file normali (vedi [File ZIP](#file-zip)).

`Salva` scrive il file e analizza di nuovo la cartella se la priorità, le parole o la scelta tra file normale e file ZIP sono cambiate; se hai modificato marcature a mano, il programma chiede prima, perché queste modifiche vanno perse. Tutte le altre voci del file restano come sono. I valori errati, come un elenco di regioni vuoto o la stessa regione due volte, vengono segnalati, non viene scritto nulla e le impostazioni restano aperte. Se il file non si può leggere, le impostazioni non si aprono, così da non poter sovrascrivere voci che non conoscono. Con `--config` le impostazioni modificano quel file; con `--priority` per questa esecuzione resta valida la priorità indicata lì.

Un gioco è considerato problematico se

- nessuno dei suoi file verrebbe mantenuto,
- il contenuto di uno ZIP marcato non compare altrove (`Il contenuto del gioco differisce dalla versione mantenuta`),
- uno ZIP è danneggiato, cifrato o non leggibile,
- un file viene mantenuto come possibile file di stato o salvataggio (regola 9),
- le regole hanno deciso solo per `Parità`,
- più ZIP della stessa versione hanno contenuto diverso,
- i nomi dei file scrivono il gioco in modo diverso (`Title 1-2` e `Title 12`),
- un file marcato ha un tipo di file diverso da quelli mantenuti (`.nes` e `.sfc`).

La finestra usa `tkinter`, che fa parte della normale installazione di Python su Windows. Se manca, il programma lo segnala e non elimina nulla.

## Dopo la pulizia automatica

Anche dopo la pulizia automatica possono restare versioni ridondanti di un gioco. Il modo più semplice per trovarle è il filtro (tasto `/` e poi il nome del gioco). Dopo puoi marcare i file che vanno ancora eliminati.

## Versione per terminale (Linux)

Lo stesso programma funziona anche in un terminale di testo, per esempio tramite SSH (PuTTY, MobaXterm), in `tmux` o sulla console di Linux. Mostra lo stesso elenco, applica le stesse regole e condivide con la finestra `redundanz_config.json`, `rom_cleanup_workbench_settings.json` e `translations.py`.

Su Linux si avvia da sola quando non c'è un display grafico (né `DISPLAY` né `WAYLAND_DISPLAY` sono impostate, come tramite SSH). `--tui` la avvia ovunque altrove, anche su Windows; usalo dove esiste un display grafico ma vuoi il terminale, per esempio in MobaXterm o sotto WSL.

Richiede [Textual](https://textual.textualize.io/) (testato con 8.2.8). Come installarlo e avviare il programma è descritto in [Installazione](#installazione) e [Uso](#uso).

Senza Textual il programma lo dice e non elimina nulla. Lo schermo ha le righe della finestra dall'alto in basso: la riga del titolo verde con la cartella, una riga di aiuto, la priorità, l'elenco, il campo del filtro, le tre viste e la riga di stato verde. Nell'elenco ogni gioco inizia con il suo nome in grassetto, seguito da trattini fino al bordo destro; una nota come `Grafie diverse del nome` si trova su quella riga. In un terminale stretto, come le 80 colonne di PuTTY, i nomi di file e le note lunghe vanno a capo nella loro colonna invece di uscire dallo schermo. `Niente da fare.` lampeggia con il lampeggio proprio del terminale; in PuTTY può essere necessario attivare prima il testo lampeggiante. Domande e messaggi compaiono in una cornice sopra l'elenco, con pulsanti nella lingua del programma; `No` è preselezionato.

La riga di aiuto mostra i tasti come `tasto:azione`, per esempio `x:elimina  k:mantieni`. La finestra e la versione per terminale hanno gli stessi tasti.

| Tasto | Effetto |
| --- | --- |
| Frecce | seleziona una riga, con Maiusc più righe |
| `Tab` / `Maiusc+Tab` | gioco successivo / precedente; viene selezionato il suo primo file |
| `x` / `k` | marca i file selezionati per l'eliminazione / li mantiene |
| `1` `2` `3` | le viste `Marcature problematiche`, `Tutte le marcature`, `Tutti i file ROM` |
| `/` | va al campo del filtro |
| `Invio` | esegue: elimina dopo una conferma (come `Esegui...`) |
| `f` | sceglie un'altra cartella: `Destra` o `Spazio` apre una cartella, `Sinistra` la chiude, `Invio` o un doppio clic la sceglie; si può anche scrivere un percorso |
| `s` | impostazioni: `Maiusc+Su`/`Maiusc+Giù` spostano una regione, `Canc` la rimuove, `Ctrl+S` salva, `Esc` annulla |
| `r` o `F5` | analizza di nuovo, rilegge anche la configurazione |
| `c` o `F1` | mostra i riconoscimenti |
| `q` o `Esc` | chiude senza eliminare nulla; dopo modifiche a mano il programma chiede prima |
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

Il programma ignora del tutto alcuni file: non compaiono da nessuna parte e non vengono mai eliminati.

- I file il cui nome inizia con `gamelist`, senza distinzione tra maiuscole e minuscole. Non sono file ROM.
- I file nascosti: nomi che iniziano con un punto, come `.xxx` o `.DS_Store`, e file con l'attributo di Windows «nascosto».

1. I file vanno insieme se il testo prima della prima parentesi è uguale. Maiuscole, spazi, trattini e trattini bassi non contano, quindi `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. Ne segue anche `Title 1-2` = `Title 12`. Inoltre valgono come uguali `und` = `and` = `&` = `&&`, `Sullivan's` = ``Sullivan`s`` = `Sullivan´s` = `Sullivans` (gli apostrofi non contano), i numeri romani da `I` a `IX` come parola intera = da `1` a `9` (`Final Fantasy VII` = `Final Fantasy 7`; da `X` in poi restano come sono, perché `Mega Man X` e `Mega Man 10` sono due giochi) e `The Title` = `Title The` = `Title, The` = `Title`. Un `The` in mezzo al nome invece conta. Allo stesso modo `vs` = `vs.` = `versus`. Un numero davanti al nome, per esempio di una raccolta numerata, non conta: `057 Robocop vs Terminator` = `057 - Robocop vs Terminator` = `Robocop vs Terminator`. Se il nome è solo il numero (`1942`) o il numero è attaccato alla parola (`2Fast`), resta parte del nome; `4 in 1` e `3 in 1` restano giochi diversi. Poiché i nomi coincidono solo grazie al confronto, il gioco è considerato problematico (`Grafie diverse del nome`).
2. I file con una parola da eliminare (`delete_tags`, nessuna per impostazione predefinita, per esempio `Hack` e `Hacks`) vengono sempre marcati, anche se sono l'unico file del gioco. `k` mantiene comunque un file del genere.
3. Tra i file rimanenti viene mantenuto quello con la voce migliore in `region_priority`. All'interno di una parentesi conta la voce migliore: con `(USA, Japan)` la migliore delle due. Tra parentesi diverse conta la peggiore: `(USA) (Beta)` vale come `Beta` (regola 6).
4. Tutti i file della stessa versione vengono mantenuti insieme, per esempio `(Disc 1)` e `(Disc 2)` oppure `.cue` e `.bin`. Tutto il resto viene marcato. Eccezione: se solo una parte di questi file ha un numero davanti al nome (`073 Batman (USA).sfc` e `Batman (USA).sfc`), restano quelli con il numero e gli altri vengono marcati (`Preferito il nome con numero`).
5. Una regione che non è in `region_priority` vale come `none`. Questo vale anche per indicazioni come `(Rev 1)`.
6. Le info aggiuntive come `Beta`, `Proto` o `Alpha` si scrivono in `region_priority` dopo `none`. I file che le contengono vengono dopo tutti gli altri, anche dopo i file senza regione, e nell'ordine dell'elenco: con `none, Beta, Proto` una Beta viene prima di un Proto. Vengono mantenuti solo se non c'è un file migliore del gioco. Tra di loro conta di nuovo la regione, poi la versione della regola 7, poi il numero dopo l'info aggiuntiva: `Beta 2` vince su `Beta 1`, e `Beta 1` su `Beta` senza numero. I numeri sono confrontati numericamente (`Beta 10` prima di `Beta 9`). Il file che perde riceve la nota `Beta precedente`.
7. A parità di priorità vince il numero di versione più alto, confrontato numericamente (`v1.10` prima di `v1.9`). Tra parentesi sono riconosciuti `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` e `Rev A`; nel nome del gioco solo la forma `Title v1.1`, anche con `-` o `_` al posto dello spazio. Un file senza versione perde contro uno con versione. La regione conta prima della versione.
8. Dopo di che vince il file con un numero davanti al nome (`073 Batman` prima di `Batman`), poi quello con meno informazioni aggiuntive, poi un file senza ZIP (con `prefer_zip`: un file ZIP), poi l'ordine alfabetico. Il rapporto mostra allora `Parità`.
9. Un file più piccolo di 1/4 del file più grande del gioco viene messo da parte prima delle regole da 3 a 8 e mantenuto: potrebbe essere un file di stato o salvataggio. Non può quindi essere eliminato né scalzare la vera ROM, per esempio `1941.state` il file `1941.zip`. La colonna delle note dice allora `Possibile file di stato o salvataggio`, e il gioco è considerato problematico. Un gioco del genere compare in tutte e tre le viste, anche se nessuno dei suoi file è marcato. Quando elimini, il programma conferma come legittimi tutti i possibili file rimanenti: restano dove sono, continuano a non essere mai eliminati e non compaiono più in `Marcature problematiche` e `Tutte le marcature`, anche dopo `F5` o un nuovo avvio. La conferma ne indica il numero. Il programma li memorizza con percorso e dimensione in `rom_cleanup_workbench_settings.json`; se la dimensione cambia, il file torna sospetto. Se non è marcato nulla, `Enter` propone di confermarli senza eliminare nulla. Gli ZIP contano con la loro dimensione decompressa. Questo non vale per un file normale piccolo accanto a un file normale grande della sua stessa versione, come un `.cue` accanto al suo `.bin`, né per un file con la stessa estensione del file più grande (un `.nes` piccolo accanto a un `.nes` grande è una ROM su cui decidono le regole da 3 a 8), né per i file marcati a causa di `delete_tags` o di uno ZIP danneggiato. Con `x` puoi comunque marcare il file a mano.
10. Quando esegui, dopo l'eliminazione il programma toglie a ogni file mantenuto il numero davanti al nome, con gli spazi, i punti, i trattini o i trattini bassi che lo seguono: `073 Batman (USA).sfc` diventa `Batman (USA).sfc`, `057 - Robocop.md` diventa `Robocop.md`. La conferma ne indica prima il numero e un esempio; se non è marcato nulla, `Invio` chiede solo di rinominare. Il numero resta se il gioco ha un file `.cue`, `.gdi`, `.m3u`, `.mds`, `.toc` o `.ccd` (nomina i file nel suo contenuto) o se il nome senza numero è già usato; la conferma indica anche questo numero. Il contenuto degli ZIP non viene rinominato. La riga del titolo di un gioco mostra il nome scritto come nel primo file mantenuto (`Street Fighter II` o `Street Fighter 2`), sempre senza numero; se sposti file con `k` o `x`, il titolo si adegua.

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
