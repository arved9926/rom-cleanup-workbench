# Rom Cleanup Workbench

[English](README.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · **Français** · [日本語](README.ja.md)

**Guide de l'utilisateur avec captures d'écran :** [PDF](<docs/Rom Cleanup Workbench - Guide utilisateur.pdf>) · [Word](<docs/Rom Cleanup Workbench - Guide utilisateur.docx>)


Trouve les fichiers ROM en double dans un dossier d'après le nom du jeu et les supprime sur demande.
Nécessite Python 3.10 ou plus récent. La fenêtre n'a besoin d'aucun paquet supplémentaire ; la version terminal pour Linux nécessite Textual (voir [Version terminal (Linux)](#version-terminal-linux)).
Le programme parle anglais, allemand, italien, espagnol, français et japonais (voir [Langue](#langue)).

**Important :** n'utilisez pas ce programme sur vos fichiers ROM originaux. Faites une copie de votre dépôt de ROM et utilisez le programme pour nettoyer uniquement cette copie.

## Installation

Aucun compte GitHub n'est nécessaire. Chaque commande se trouve dans son propre cadre ; saisissez-la telle quelle et appuyez sur Entrée.

### Windows

Saisissez toutes les commandes dans PowerShell.

1. **Vérifier si Python est installé :**

   ```powershell
   python --version
   ```

   - **Il affiche `Python 3.10` ou plus :** Python est là, passez à l'étape 2.

   - **Il affiche une erreur ou une version plus ancienne :** téléchargez Python 3.10 ou plus récent sur [python.org/downloads](https://www.python.org/downloads/) et installez-le. Si l'installateur propose « Add python.exe to PATH », cochez cette option. `tkinter` pour la fenêtre est inclus. Ouvrez ensuite une nouvelle fenêtre PowerShell et refaites la vérification.

2. **Vérifier si Git est installé :**

   ```powershell
   git --version
   ```

   - **Il affiche un numéro de version, par exemple `git version 2.47.0` :** téléchargez le programme avec Git :

     ```powershell
     git clone https://github.com/arved9926/rom-cleanup-workbench.git
     ```

   - **Il affiche une erreur :** téléchargez le programme sous forme de fichier ZIP. Dans le navigateur, sur la [page GitHub](https://github.com/arved9926/rom-cleanup-workbench), choisissez **Code** puis **Download ZIP** ; décompressez ensuite le fichier avec le bouton droit de la souris (**Extraire tout...**) et renommez le dossier `rom-cleanup-workbench-main` en `rom-cleanup-workbench`. Ou dans PowerShell, commande par commande :

     ```powershell
     Invoke-WebRequest https://github.com/arved9926/rom-cleanup-workbench/archive/refs/heads/main.zip -OutFile rom-cleanup-workbench.zip
     ```

     ```powershell
     Expand-Archive rom-cleanup-workbench.zip -DestinationPath .
     ```

     ```powershell
     Rename-Item rom-cleanup-workbench-main rom-cleanup-workbench
     ```

3. **Aller dans le dossier du programme :**

   ```powershell
   cd "rom-cleanup-workbench\Rom Cleanup Workbench"
   ```

   La fenêtre n'a besoin d'aucun autre paquet. Seuls ceux qui veulent la version terminal sous Windows installent en plus Textual :

   ```powershell
   python -m pip install textual==8.2.8
   ```

### Linux

Saisissez toutes les commandes dans un terminal. Les exemples valent pour Debian et Ubuntu.

1. **Vérifier si Python est installé :**

   ```bash
   python3 --version
   ```

   - **Il affiche `Python 3.10` ou plus :** Python est là, passez à l'étape 2.

   - **Il affiche une erreur ou une version plus ancienne :** installez Python :

     ```bash
     sudo apt install python3 python3-venv
     ```

   Le paquet `python3-tk` n'est nécessaire que si vous voulez la fenêtre au lieu de la version terminal sous Linux avec un affichage graphique.

2. **Vérifier si Git est installé :**

   ```bash
   git --version
   ```

   - **Il affiche un numéro de version :** téléchargez le programme avec Git :

     ```bash
     git clone https://github.com/arved9926/rom-cleanup-workbench.git
     ```

   - **Il affiche une erreur :** téléchargez le programme sous forme de fichier ZIP et décompressez-le, commande par commande :

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

3. **Aller dans le dossier du programme :**

   ```bash
   cd "rom-cleanup-workbench/Rom Cleanup Workbench"
   ```

4. **Installer Textual dans un environnement virtuel :**

   ```bash
   python3 -m venv ~/venvs/rom-cleanup-workbench
   ```

   ```bash
   ~/venvs/rom-cleanup-workbench/bin/pip install textual==8.2.8
   ```

## Utilisation

### Windows

Ouvrez un terminal (par exemple PowerShell) dans le dossier `Rom Cleanup Workbench` et lancez le programme avec le dossier de vos jeux :

```powershell
cd "rom-cleanup-workbench\Rom Cleanup Workbench"
```

```powershell
python rom_cleanup_workbench.py "D:\Games"
```

Sans dossier, le programme rouvre le dernier dossier choisi, un dossier `roms` avec sa vue d'ensemble, tout autre directement ; la première fois, la fenêtre en demande un. Pour la version terminal, ajoutez `--tui`.

### Linux

Placez-vous dans le dossier `Rom Cleanup Workbench` et lancez le programme avec le Python de l'environnement virtuel et le dossier de vos jeux :

```bash
cd "rom-cleanup-workbench/Rom Cleanup Workbench"
```

```bash
~/venvs/rom-cleanup-workbench/bin/python rom_cleanup_workbench.py ~/roms
```

Sans affichage graphique, par exemple via SSH, la version terminal démarre d'elle-même. Avec un affichage graphique, la fenêtre s'ouvre (il faut `python3-tk`) ; avec `--tui`, la version terminal démarre quand même. Plus d'informations dans [Version terminal (Linux)](#version-terminal-linux).

### Ce qui se passe ensuite

Le programme ouvre la fenêtre d'analyse et y affiche tout ; il n'écrit rien dans le terminal et n'y demande rien. Les questions, les messages et le choix du dossier apparaissent aussi dans la fenêtre, dans la langue du programme, jamais comme fenêtres surgissantes de Windows ; Entrée choisit le bouton présélectionné et Échap répond Non. Sans dossier, la fenêtre demande le dossier. Les fichiers ne sont supprimés qu'après la confirmation dans la fenêtre. **Les fichiers supprimés ne vont pas dans la Corbeille.**

| Option | Effet |
| --- | --- |
| `--review all` | ouvre la fenêtre avec `À supprimer` pour ce démarrage |
| `--review problems` | ouvre la fenêtre avec `À vérifier` pour ce démarrage |
| `--priority USA Europe Japan none` | fixe la priorité pour cette exécution |
| `--delete-tag Hack Hacks Proto` | fixe les mots à supprimer pour cette exécution |
| `--config file.json` | utilise une autre configuration |
| `--report-only` | sans fenêtre : affiche seulement le rapport dans le terminal |
| `--yes` | sans fenêtre : supprime les fichiers marqués sans demander |
| `--scan-all` | sans fenêtre : analyse tous les dossiers de plateforme du dossier `roms` indiqué et les enregistre dans sa base de données ; ne supprime rien |
| `--deep-scan` | avec `--scan-all` : analyse approfondie, relit chaque fichier au lieu des seuls fichiers nouveaux et modifiés (`--full` marche toujours) |
| `--write-gamelists` | sans fenêtre : écrit le `gamelist.xml` de chaque plateforme du dossier `roms` indiqué à partir de sa base de données ; chaque fichier précédent reste en copie |
| `--all` | avec `--report-only` : montre aussi les jeux sans fichier marqué |
| `--tui` | utilise la version terminal au lieu de la fenêtre (automatique sous Linux sans affichage graphique) |
| `--ascii` | version terminal avec des caractères ASCII seulement (automatique sur la console Linux) ; implique `--tui` |

Les options de la ligne de commande et leur aide (`--help`) sont toujours en anglais.

Les tests se lancent avec `python -m unittest`.

## La collection : de nombreuses plateformes et la base de données

En général, les jeux se trouvent dans un dossier commun, séparés par plateforme, par exemple `roms/nes`, `roms/snes`, `roms/n64`. Si vous choisissez ce dossier `roms`, le programme affiche la **vue d'ensemble** de toutes les plateformes. Ensuite, il démarre toujours avec le dernier dossier choisi, donc avec sa vue d'ensemble pour un dossier `roms`. Compte comme dossier `roms` un dossier qui a déjà une base de données ou qui ne contient lui-même aucun fichier ROM, mais des sous-dossiers. Les fichiers d'accompagnement comme `info.txt`, des images ou des PDF ne comptent pas comme fichiers ROM. Tout autre dossier est analysé seul comme avant, sans base de données.

**La base de données.** La première fois, le programme crée dans le dossier `roms` le dossier caché `.rom_cleanup_workbench` avec une base de données SQLite. C'est la seule chose qu'il écrit dans votre collection. Elle enregistre les résultats de chaque analyse : fichiers, tailles, dates de modification, le contenu des ZIP avec leurs sommes de contrôle. À partir de là, le programme recalcule les décisions en un instant à l'ouverture d'une plateforme. Les paramètres modifiés s'appliquent donc tout de suite, sans nouvelle analyse. Elle contient aussi les changements à la main (`k`/`x`), les fichiers d'état et de sauvegarde confirmés et les paramètres propres à chaque plateforme. C'est le dossier qui compte : si un dossier de plateforme n'existe plus, la vue d'ensemble efface à l'ouverture tout ce que la base de données savait de lui, paramètres propres et `sans jeux` compris. Un nouveau dossier du même nom repart alors de zéro. Si le dossier `roms` lui-même n'est pas joignable, par exemple un lecteur réseau sans connexion, rien n'est effacé.

**La vue d'ensemble** affiche par plateforme : fichiers, jeux, fichiers marqués pour suppression, jeux problématiques, jeux retirés entièrement (dont aucun fichier ne resterait), la dernière analyse et l'état (`non analysée`, `à jour` ou `modifiée` si des fichiers ont été ajoutés, retirés ou modifiés depuis), avec le total en dessous. Un trait sépare le total des plateformes ; l'état `modifiée` est en jaune (dans la fenêtre, toute la ligne). Un clic sur l'en-tête `Plateforme`, `Fichiers`, `Jeux`, `À supprimer`, `Problématiques`, `Retirés entièrement`, `Infos` ou `Problèmes gamelist` trie selon celui-ci, un second clic dans l'autre sens ; une flèche indique le sens, le total reste en bas, les plateformes sans chiffres viennent en dernier et le choix est mémorisé.

| Bouton | Touche | Effet |
| --- | --- | --- |
| `Ouvrir` | `Entrée` | ouvre la plateforme surlignée dans la liste habituelle (aussi double clic) |
| `Analyser` | `r` ou `F5` | analyse la plateforme surlignée et l'ouvre |
| `Tout analyser` | `a` | analyse toutes les plateformes l'une après l'autre ; chacune est enregistrée tout de suite et ses chiffres apparaissent aussitôt dans la vue d'ensemble ; `Annuler` garde celles qui sont finies ; ne supprime rien |
| `Analyse approfondie` | `d` | interrupteur (point rouge) pour Analyser et Tout analyser : relit chaque fichier au lieu des seuls fichiers nouveaux et modifiés |
| `Masquer les vides` | `h` | interrupteur (point rouge) : masque les dossiers sans fichier de jeu, par exemple `bios` ou un dossier avec seulement `info.txt` ; les fichiers annexes ne comptent pas comme fichiers de jeu ; le choix est mémorisé |
| `Dossier...` | `f` | choisit un autre dossier `roms` |
| | `n` | marque le dossier surligné comme `sans jeux` ou annule cela (voir plus bas) |
| | `w` | écrit le `gamelist.xml` de la plateforme surlignée à partir de la base de données (après une question) |
| | `m` | supprime les fichiers multimédias inutilisés de la plateforme surlignée (après une question, voir plus bas) |
| | `q` ou `Échap` | ferme le programme |

Les touches sont les mêmes dans la fenêtre et dans la version terminal. La ligne au-dessus du tableau nomme les principales ; `F1` ou `?` les montre toutes.

**Analyser.** Une analyse est d'habitude rapide : elle ne lit que les fichiers nouveaux et modifiés (reconnus par leur nom, leur taille et leur date de modification) et reprend tout le reste de la base de données. Avec `Analyse approfondie`, chaque fichier est relu. `F5` dans la liste analyse rapidement la plateforme ouverte. Exécuter inscrit tout de suite les fichiers supprimés et renommés ; aucune nouvelle analyse n'est nécessaire ensuite.

**Retour à la vue d'ensemble** : dans la liste avec `Échap`, `q` ou le bouton `Vue d'ensemble`, dans la version terminal aussi avec `o`. `Échap` ou `q` dans la vue d'ensemble ferme le programme ; pour sortir complètement, on appuie donc deux fois.

**Le gamelist.xml.** Si un dossier de plateforme contient un `gamelist.xml` (EmulationStation, RetroPie, Batocera, ES-DE, ARRM), l'analyse le lit et reprend dans la base de données ce qui peut être vérifié : nom, description, note, date, développeur, éditeur, genre, joueurs, région, favori, temps de jeu et les liens vers les fichiers multimédias comme les images et les vidéos, par catégorie (`wheel` et `logo` restent distincts même s'ils pointent vers le même fichier). Tous les autres champs sont conservés tels quels. Le nombre de `<genreid>` (par exemple `1538`) vient de la liste des genres de Recalbox : genre principal × 256 plus sous-genre, donc `1538` = `0x0602` = Sport, sous-genre 2 « Simulation sportive » ; des outils comme ARRM l'écrivent lors du scraping. La vue du jeu affiche le nombre avec son nom, par exemple « 1538 – Simulation sportive (Sport) ». Il n'a rien à voir avec les numéros de genre de ScreenScraper. Si une plateforme a des numéros de genre, la liste affiche une colonne `Genre`. Un clic sur son en-tête trie les jeux par genre (dans l'ordre de la liste Recalbox, les jeux sans genre en dernier, par nom au sein d'un genre), un second clic ou un clic sur `Fichier` de nouveau par nom ; le choix est mémorisé. Dans le formulaire de modification, `Genre (liste Recalbox)` choisit le numéro parmi tous les genres Recalbox ; le champ texte `Genre` reste libre à côté. Un numéro choisi à la main est conservé lors d'une nouvelle importation. Ne sont pas repris, et comptent comme problèmes, les entrées dont la ROM n'est pas dans le dossier de la plateforme et les liens vers des fichiers qui n'existent pas. Les chemins d'un autre ordinateur comme `/home/pi/RetroPie/roms/nes/…` sont réécrits vers le dossier de la plateforme et comptés comme remarques. Le fichier n'est lu que s'il a changé ; un `gamelist.xml` modifié met l'état sur `modifiée`. Le fichier lui-même n'est pas modifié. Le stockage, c'est la base de données, pas le `gamelist.xml` : si le fichier est supprimé, les informations restent ; si en revanche une ROM ou un fichier multimédia disparaît du dossier, il disparaît aussi de la base de données, et une ROM supprimée emporte ses informations. La vue d'ensemble indique dans `Infos` combien de ROM ont des informations et dans `Problèmes gamelist` ce qui n'a pas été repris ; après le nom de la plateforme, un texte gris indique combien d'entrées ont été reprises. Si le fichier est abîmé, rien n'est repris et l'existant reste.

**gamelist.xml et fichiers multimédias hors du dossier de la plateforme.** Si le dossier de la plateforme n'a pas son propre `gamelist.xml`, le Workbench cherche là où les frontends le rangent, dans cet ordre : `~/ES-DE/gamelists/<plateforme>/` (ES-DE), `~/.emulationstation/gamelists/<plateforme>/` (EmulationStation, RetroPie) et sous Linux `/etc/emulationstation/gamelists/<plateforme>/`. Le nom du dossier de la plateforme sert de nom de système. Les chemins comme `%ROMPATH%/nes/…` sont rapportés au dossier de la plateforme. La ligne grise, le rapport et la question avant l'écriture indiquent l'emplacement ; l'écriture se fait au même endroit, avec la copie de sauvegarde là-bas. Le Workbench cherche aussi des fichiers multimédias dans `~/ES-DE/downloaded_media/<plateforme>/` (ou dans le dossier multimédia choisi dans les paramètres d'ES-DE) ainsi que dans `~/.emulationstation/downloaded_media/` et `downloaded_images/`. Ces fichiers hors de la collection sont seulement affichés et écrits dans le `gamelist.xml`, mais jamais supprimés ni renommés.

**Fichiers multimédias dans les sous-dossiers.** À chaque analyse, le Workbench cherche en outre dans tous les sous-dossiers d'une plateforme les images, vidéos et manuels que le `gamelist.xml` ne nomme pas déjà. N'est attribué que ce que le nom dit sans ambiguïté : un dossier par catégorie avec le nom de la ROM (`wheel/10yard.png`, `marquees/10yard.png`) ou nom de la ROM, séparateur (`-`, `.` ou `_`) et catégorie dans un dossier quelconque (`downloaded_images/10yard-wheel.png`, `game.image.jpg`). Si plusieurs ROM correspondent, le nom le plus long gagne (`sf2ce-image.png` appartient à `sf2ce.zip`, pas à `sf2.zip`) ; il n'y a pas d'attribution par ressemblance. Ce qui n'est pas univoque reste sans ROM. Chaque ROM de jeu sans entrée dans le `gamelist.xml` reçoit une entrée vide avec le nom avant la première parenthèse ; les fichiers BIOS (`BIOS` dans une parenthèse ou des noms connus comme `neogeo`, `pgm`, `skns`) ne comptent pas comme jeux et ne reçoivent pas de fichiers multimédias. Après le nom de la plateforme, un texte gris indique combien de fichiers multimédias sont attribués et combien sont restés sans ROM ; `Infos` compte aussi les entrées vides pour lesquelles des fichiers multimédias ont été trouvés.

**Supprimer les fichiers multimédias inutilisés.** `m` (dans la plateforme ou dans la vue d'ensemble pour la plateforme surlignée) cherche les images, vidéos et manuels que plus rien n'utilise : aucune ROM du dossier ne porte leur nom et aucun `gamelist.xml` n'y renvoie, par exemple les images d'une ROM supprimée en dehors du Workbench. Seuls les dossiers multimédias à l'intérieur du dossier de la plateforme sont parcourus, c'est-à-dire les dossiers dont le nom est une catégorie (`images`, `videos`, `marquees`, `wheel`, `manuals` …) ou `media`, `downloaded_images`, `downloaded_media`, `artwork`, `boxart`, `covers`. Les fichiers directement dans le dossier de la plateforme, dans d'autres sous-dossiers (par exemple dans le dossier d'un jeu) et dans les dossiers multimédias d'ES-DE ou de RetroPie hors de la collection ne sont jamais touchés. Avant cela, le Workbench relit le dossier et un `gamelist.xml` modifié ; si le `gamelist.xml` est illisible, il ne supprime rien. La question indique le nombre, la taille et les premiers fichiers ; les fichiers supprimés ne vont pas à la corbeille. Le rapport avec `g` montre au préalable quels fichiers multimédias sont sans ROM.

**Vue du jeu, nom et rapport.** Le nom du `gamelist.xml` vaut pour tout le jeu, pas pour un fichier : l'en-tête d'un jeu affiche le nom du fichier conservé et notre titre entre parenthèses derrière, par exemple `10-Yard Fight (10yard)` ; si les deux sont identiques ou s'il n'y en a pas, seul notre titre apparaît. Dans la ligne portant le nom d'un jeu, la colonne `Remarque` affiche, après d'éventuels problèmes, la note, les joueurs et l'année de sortie, par exemple `★ 4.5 · 1-2 joueurs · 1991` (avec `--ascii` `* 4.5 - 1-2 joueurs - 1991`) ; elles viennent du fichier conservé ou, s'il n'en a pas, d'un autre fichier du jeu. Les fichiers BIOS et les fichiers marqués avec `n` affichent `pas un jeu` dans la colonne `Remarque`. `Entrée` (dans la fenêtre aussi un double-clic sur un fichier) affiche à la place de la liste tout ce que l'on sait du jeu : ses fichiers avec leur décision, les champs comme la description, la note (en x / 5), la date, le développeur, le temps de jeu et le favori, les autres champs du `gamelist.xml` et les fichiers multimédias par catégorie ; il n'y a volontairement pas d'aperçus. `g` affiche le rapport gamelist : ce qui n'a pas été repris et pourquoi, les remarques, les ROM sans informations, les fichiers multimédias sans ROM et les fichiers qui ne sont pas des jeux. `n` marque les fichiers sélectionnés comme `pas un jeu` ou annule cela ; un `gamelist.xml` ultérieur n'y change rien. Ce sont toujours les règles qui décident si un fichier est gardé ou supprimé. Le résumé du `gamelist.xml` et des fichiers multimédias apparaît en gris sur une ligne à part sous la ligne de la plateforme.

**Supprimer et renommer emportent les fichiers multimédias.** Quand `Exécuter...` supprime une ROM, ses fichiers multimédias sont supprimés avec elle, images, vidéos et manuels du `gamelist.xml` comme des sous-dossiers ; la question avant la suppression en indique le nombre. Un fichier multimédia qu'utilise aussi une ROM restante reste. Une ROM supprimée emporte aussi ses informations, favori et temps de jeu compris. Quand `Exécuter...` retire le numéro devant un nom, les fichiers multimédias dont le nom commence par l'ancien nom de la ROM sont renommés avec elle (`01 - Alpha (USA)-image.png` devient `Alpha (USA)-image.png`). Le `gamelist.xml` lui-même n'est pas modifié.

**Modifier les informations du jeu.** Dans la vue du jeu, `e` ouvre un formulaire pour le fichier : nom, nom de tri, description, note (de 0 à 5 étoiles, aussi 3,5), date de sortie (`AAAA`, `AAAA-MM` ou `AAAA-MM-JJ`), développeur, éditeur, genre, joueurs, région, langues ainsi que favori, masqué et pour enfants. Le temps de jeu, le nombre de parties et l'identifiant restent tels que le frontend et le scraper les tiennent. `Ctrl+S` ou `Enregistrer` enregistre, `Échap` ou `Annuler` revient à la vue du jeu sans enregistrer ; une valeur erronée est signalée et le formulaire reste ouvert. Les champs modifiés portent un `✎` dans la vue du jeu ; une nouvelle importation du `gamelist.xml` les laisse tels quels. La modification transforme une entrée vide en une vraie entrée. Lors de l'écriture du `gamelist.xml`, les modifications y entrent.

**Écrire le gamelist.xml.** Seulement sur demande, le Workbench réécrit le `gamelist.xml` d'une plateforme à partir de sa base de données : avec `w` dans la plateforme ou dans la vue d'ensemble pour la plateforme surlignée, avec `--write-gamelists` pour toutes. Après un nettoyage qui a supprimé des fichiers, il le propose si la plateforme a un `gamelist.xml`. Auparavant, le fichier précédent est sauvegardé sous `gamelist.xml.<date_heure>.bak` ; les trois dernières copies restent, les plus anciennes sont supprimées. Le nouveau fichier est d'abord créé sous un autre nom, puis remplace l'ancien en une seule étape, si bien qu'il ne reste jamais de fichier à moitié écrit. Il contient tous les jeux, aussi ceux à l'entrée vide, mais pas les fichiers BIOS et autres non-jeux ; en plus, tous les champs connus, les fichiers multimédias par catégorie (un fichier dans deux catégories figure deux fois), l'identifiant et tous les autres champs tels qu'ils ont été lus. Les valeurs égales à la valeur par défaut sont omises, comme chez EmulationStation. Le bloc `<provider>` indique comme logiciel `RCW` (Rom Cleanup Workbench) avec notre page GitHub ; le système reste. Ensuite, le fichier compte comme lu.

**Dossiers sans jeux.** Un dossier comme `bios` ou `saves` ne contient pas de jeux. `n` marque le dossier surligné comme `sans jeux` : il n'est ni analysé (pas non plus par `Tout analyser` et `--scan-all`) ni ouvert, ne compte pas dans le total, et `Masquer les vides` le masque. Ce que la base de données savait de lui est effacé. Un second `n` annule cela ; le dossier est alors `non analysée`. Il n'y a volontairement pas de bouton pour cela.

**Les modifications à la main** (`k`/`x`) restent enregistrées, même après la fermeture, jusqu'à ce que tu exécutes ou analyses de nouveau la plateforme. Si un fichier change, sa modification à la main tombe.

**Paramètres d'une plateforme.** Quand une plateforme est ouverte, les paramètres affichent en haut `Paramètres généraux` ou `Paramètres propres à NES`. Avec le choix propre à la plateforme, la priorité, les mots de suppression et le choix entre fichier normal et ZIP ne valent que pour cette plateforme ; ils sont dans la base de données, et `redundanz_config.json` reste le standard pour toutes les autres. De nouveaux paramètres propres partent des valeurs standard ; revenir à `Paramètres généraux` les abandonne. La ligne sous le titre des paramètres indique où ils sont enregistrés : `redundanz_config.json` ou, avec le choix propre à la plateforme, la base de données de la collection (la langue reste dans `redundanz_config.json`). La langue vaut toujours pour tout. Dans la vue d'ensemble, ces plateformes ont un `*` après leur nom.

**Sans fenêtre**, `--scan-all` analyse toutes les plateformes, par exemple pendant la nuit :

```powershell
python rom_cleanup_workbench.py "D:\roms" --scan-all
```

Avec `--deep-scan`, chaque fichier est relu. Rien n'est jamais supprimé ainsi.

## Fenêtre d'analyse

Comme les fichiers ZIP doivent être décompressés pour obtenir la taille, la somme SHA-256 et le nom de leur contenu, il peut falloir un moment après le choix d'un dossier avant que les résultats s'affichent.

La ligne verte du haut affiche à gauche `Rom Cleanup Workbench` et à droite le dossier ; en dessous figure en vert `Plateforme :` avec le nom du dossier ouvert en gras, suivi de `*` comme dans la vue d'ensemble si la plateforme a ses propres paramètres ; vient ensuite une ligne vide. À droite se trouvent les principales touches de la vue, dans la liste `x Supprimer`, `k Garder`, `Entrée Infos du jeu`, `F12 Effectuer le nettoyage` et `F1 / ? Aide : autres touches`. `F1` ou `?` affiche toutes les touches à la place de la liste, classées par thème ; `Échap`, `F1` ou `?` les referme. Dans la vue d'ensemble, les deux affichent les touches de la vue d'ensemble et en dessous, sous `Bon à savoir`, ce que signifient les états, l'analyse et l'analyse approfondie. Les paramètres montrent la priorité en vigueur. Dans la vue d'ensemble, le mot `Collection` est aussi en vert. L'avant-dernière ligne verte affiche l'état, pendant l'analyse par exemple `Analyse : 120 sur 2007 fichiers`. Pendant ce temps, une barre de progression apparaît aussi au milieu. La fenêtre affiche aussi les erreurs, par exemple dans la configuration, et tant que l'analyse échoue, rien ne peut être supprimé. Pendant la suppression, la barre de progression apparaît au milieu et la ligne verte affiche par exemple `Suppression : 120 sur 500 fichiers` ; la fenêtre n'accepte aucune saisie avant la fin de la suppression. Ensuite, elle indique le résultat et retire les fichiers supprimés de la liste sans analyser à nouveau le dossier ; les fichiers qui n'ont pas pu être supprimés restent marqués. `F5` analyse à nouveau le dossier si vous le souhaitez.

Si rien n'est marqué dans tout le dossier et qu'aucun fichier n'est soupçonné d'être un fichier d'état ou de sauvegarde, `Rien à faire.` clignote au milieu de la fenêtre.

Les quatre boutons radio déterminent ce que montre la liste :

- `À vérifier` : seulement les jeux avec un fichier marqué qui comptent comme problématiques, c'est-à-dire où quelque chose peut être perdu involontairement (par défaut au premier démarrage)
- `À supprimer` : tous les jeux avec un fichier marqué
- `Retirés entièrement` : les jeux dont aucun fichier ne resterait, le plus souvent parce que des mots à supprimer touchent tous leurs fichiers (par exemple `Ikaruga (Japan).cdi` avec le mot à supprimer `Japan`). Il vaut la peine de vérifier si les mots à supprimer en prennent trop. La confirmation nomme ces jeux séparément : ceux retirés par des mots à supprimer, comme demandé, et les autres.
- `Tous les jeux` : tous les jeux, par exemple pour parcourir les informations des jeux ou pour les trier par genre. Leurs fichiers peuvent alors aussi être marqués avec `x`, et les cas problématiques sans fichier marqué, comme un ZIP illisible, apparaissent aussi.

**Noms des jeux seulement.** L'interrupteur `Noms des jeux seulement` (dans la fenêtre à côté des vues, dans le terminal à droite du champ de filtre) ou `z` replie la liste sur les lignes portant les noms des jeux, sans traits de séparation : vous voyez ainsi d'un coup d'œil quels jeux a la plateforme, avec la note, les joueurs et l'année dans la colonne `Remarque`. Le filtre, les vues et le tri par genre s'appliquent toujours. `Tab` passe d'un jeu à l'autre, `Entrée` affiche la vue du jeu du fichier conservé. `x` et `k` n'agissent que sur des fichiers ; dans la fenêtre, un double-clic ou la flèche droite déplie un seul jeu. Un second `z` affiche de nouveau les fichiers ; le choix est mémorisé.

La fenêtre retient la dernière vue choisie et les fichiers d'état ou de sauvegarde confirmés (règle 9) dans `rom_cleanup_workbench_settings.json` à côté du programme.

| Touche | Effet |
| --- | --- |
| Flèches | choisit une ligne, avec Maj plusieurs (par exemple tous les disques d'un jeu) |
| `Tab` / `Maj+Tab` | va au jeu suivant / précédent ; le premier fichier du jeu est choisi |
| `x` | marque le fichier pour suppression ; il passe à la fin de son jeu |
| `k` | garde le fichier ; il passe à la place que lui donnent les règles |
| `1` `2` `3` `4` | les vues `À vérifier`, `À supprimer`, `Retirés entièrement`, `Tous les jeux` |
| `z` | afficher seulement les noms des jeux ou de nouveau les fichiers (comme l'interrupteur `Noms des jeux seulement`) |
| `Ctrl` + molette de la souris | agrandit ou réduit le texte (de 8 à 32 pt, jusqu'à la fermeture de la fenêtre) |
| `s` | comme le bouton `Paramètres...` : affiche ou masque les paramètres de langue, de priorité, de mots à supprimer et de ZIP ou fichier normal (voir [Paramètres](#paramètres)) |
| `/` | va au champ de filtre |
| `F12` | comme le bouton `Exécuter...` : après une confirmation, supprime, retire le numéro devant les noms des fichiers conservés (règle 10) et confirme les fichiers d'état ou de sauvegarde présumés (règle 9) |
| `f` | choisit un autre dossier, dans la fenêtre à la place de la liste : ouvrez les dossiers avec la flèche, choisissez-en un aussitôt par un double-clic, ou saisissez un chemin dans `Chemin :`, puis `Sélectionner` ou `Entrée` ; `Annuler` ou `Échap` gardent le dossier actuel |
| `r` ou `F5` | analyse à nouveau, relit aussi la configuration |
| `c` | affiche les crédits |
| `Entrée` | dans une plateforme de la collection : tout ce que l'on sait du jeu surligné (aussi double-clic dans la fenêtre) ; `Entrée`, `Échap` ou `q` ferme |
| `n` | dans une plateforme de la collection : marque les fichiers sélectionnés comme `pas un jeu` (par exemple un fichier BIOS) ou annule cela |
| `g` | dans une plateforme de la collection : le rapport gamelist de la plateforme |
| `e` | dans la vue du jeu : modifier les informations du jeu ; `Ctrl+S` enregistre, `Échap` revient |
| `w` | dans une plateforme de la collection : écrire son `gamelist.xml` à partir de la base de données (après une question) |
| `m` | dans une plateforme de la collection : supprimer ses fichiers multimédias inutilisés (après une question) |
| `F1` ou `?` | affiche ou masque toutes les touches |
| `q` ou `Échap` | ferme sans rien supprimer ; dans une plateforme d'une collection, les deux reviennent d'abord à la vue d'ensemble ; après des modifications à la main, le programme demande d'abord |

Des lignes horizontales séparent les jeux, et un jeu sur deux a un fond gris foncé. La colonne `Taille` montre la taille de chaque fichier en Ko, arrondie au supérieur comme dans l'Explorateur Windows (`1 234 Ko`) ; `?` signifie que la taille n'a pas pu être lue. La taille est lue pendant l'analyse. Les fichiers conservés sont affichés en gras et en vert sous `Garder :`, ceux à supprimer en rouge sous `Marqué pour suppression`. La fenêtre affiche du texte blanc en Lucida Sans Typewriter 11 pt sur fond noir. Si la police n'est pas installée, Windows choisit discrètement une police de substitution. Les fichiers déplacés à la main ont un fond marron et portent la remarque `À la main` ; tant que la ligne est choisie, elle apparaît en bleu. Les remarques du programme restent inchangées, même si elles concernent un fichier que vous avez déplacé.

`À vérifier` masque les jeux non problématiques, `Retirés entièrement` tous les jeux dont il reste quelque chose. **Leurs fichiers marqués sont tout de même supprimés lors de la suppression** ; la confirmation en indique le nombre. Les jeux que vous avez modifiés à la main restent toujours visibles, sauf si le filtre les masque.

### Filtre

Le champ de filtre à gauche de la ligne du bas restreint la vue actuelle aux jeux dont un nom de fichier contient le motif. Un jeu reste complet si l'un de ses fichiers correspond. La liste se met à jour peu après la saisie ; le contenu des fichiers n'est pas lu.

- `*` remplace un nombre quelconque de caractères, `?` exactement un. Tous les autres caractères, y compris `[` et `]`, comptent littéralement, et les majuscules et minuscules ne comptent pas. Les espaces au début et à la fin ne comptent qu'entre guillemets : `" by "` trouve `Mario by Mick` mais pas `Moby Dick` ; sans guillemets, `by` trouve les deux.
- Le motif peut apparaître n'importe où dans le nom : `Beta`, `*Beta*` et `Mario?2` trouvent tous aussi `Super Mario 2 (Beta).nes`. Par conséquent, `S*` trouve tout nom contenant un `S`, pas seulement les noms qui commencent par lui.
- `Entrée`, `Tab` et la flèche vers le bas reviennent à la liste ; `Échap` vide le filtre et revient à la liste.
- Tant que le curseur est dans le champ, les touches n'écrivent que là : `x`, `k`, `Enter`, `f`, `r`, `F5` et `Échap` n'exécutent pas leurs fonctions de liste.
- Le filtre reste actif après `F5`, après la suppression et après le choix d'un autre dossier. Il n'est pas enregistré.

**Le filtre ne change que l'affichage. Les fichiers marqués masqués par le filtre sont quand même supprimés lorsque vous supprimez** ; la confirmation indique leur nombre.

### Paramètres

Le bouton `Paramètres...` de la ligne du bas, ou `s`, affiche les modifications les plus fréquentes de `redundanz_config.json` dans la fenêtre principale, à la place de la liste des fichiers. `Enregistrer` ou `Annuler`, `Échap`, `Ctrl+E` ou un autre clic sur `Paramètres...` ramènent la liste. Pendant ce temps, le filtre, les vues, `Exécuter...`, `Analyser à nouveau` et `Dossier...` sont bloqués, et `x`, `k`, `Entrée` et `F12` ne font rien, afin que rien ne change dans la liste masquée.

- **Langue :** Définit la langue de l'interface. Choisissez parmi les six langues. Une nouvelle langue s'applique au prochain démarrage du programme.
- **Priorité :** Définit quelles versions régionales ont la priorité sur les autres. La meilleure région en haut ; les infos supplémentaires comme `Beta` ou `Proto` se placent après `none`, pour que ces fichiers viennent en dernier (règle 6). Choisissez une entrée et déplacez-la avec `Monter` et `Descendre`, retirez-la avec `Retirer` ou la touche `Suppr`, et ajoutez-en une nouvelle avec le champ sous la liste et `Ajouter` (ou `Entrée`).
- **Mots à supprimer :** Définissent quelles versions d'un jeu sont toujours supprimées. Séparés par des virgules, par exemple `Hack, Hacks`. Les fichiers qui les contiennent sont marqués pour suppression (règle 2).
- **Même jeu en fichier normal et en fichier ZIP :** Définit lequel des deux est conservé quand les deux sont de la même version. `Garder le fichier normal` (par défaut) marque le fichier ZIP, `Garder le fichier ZIP` marque les fichiers normaux (voir [Fichiers ZIP](#fichiers-zip)).
- **Favoris et jeux joués (gamelist.xml) :** `Seulement une remarque dans la liste` (par défaut) laisse décider les règles ; un fichier qui doit être supprimé et qui, selon le `gamelist.xml`, est un favori ou a du temps de jeu reçoit la remarque `Favori ou joué – sera supprimé`. `Les garder de préférence` garde, au sein d'un jeu, le fichier favori, sinon celui qui a le plus de temps de jeu ; si les règles avaient gardé un autre fichier unique, celui-ci cède la place, et les sauvegardes suivent le fichier gardé. S'applique en général ou par plateforme (`prefer_played` dans la configuration).

`Enregistrer` écrit le fichier et analyse à nouveau le dossier si la priorité, les mots ou le choix entre fichier normal et fichier ZIP ont changé ; si vous avez modifié des marquages à la main, le programme demande d'abord, car ces modifications sont perdues. Toutes les autres entrées du fichier restent telles quelles. Les valeurs erronées, comme une liste de régions vide ou deux fois la même région, sont signalées, rien n'est écrit et les paramètres restent ouverts. Si le fichier ne peut pas être lu, les paramètres ne s'ouvrent pas, afin qu'ils ne puissent pas écraser des entrées qu'ils ne connaissent pas. Avec `--config`, les paramètres modifient ce fichier ; avec `--priority`, la priorité qui y est indiquée reste valable pour cette exécution.

N'est problématique que ce qui peut être perdu involontairement. Ce que demandent les mots à supprimer est voulu, et un fichier dont le contenu se trouve dans un fichier conservé (`Contenu identique à …`) n'est pas perdu. Un jeu compte comme problématique si

- aucun de ses fichiers ne serait conservé sans que des mots à supprimer le demandent (un jeu qui disparaît entièrement à cause de mots à supprimer ou comme sauvegarde sans ROM figure dans `Retirés entièrement`, mais n'est pas problématique),
- le contenu d'un ZIP marqué n'apparaît nulle part ailleurs (`Le contenu du jeu diffère de la version conservée`),
- un ZIP est endommagé, chiffré ou illisible,
- un fichier est conservé comme fichier d'état ou de sauvegarde présumé (règle 9),
- les règles n'ont décidé que par `Égalité` et le fichier marqué a un contenu différent,
- plusieurs ZIP de la même version ont un contenu différent,
- les noms de fichiers écrivent le jeu différemment (`Title 1-2` et `Title 12`) et un fichier marqué d'une orthographe différente de celle de chaque fichier conservé a un contenu différent,
- un fichier marqué a un autre type de fichier que les fichiers conservés (`.nes` et `.sfc`) et son contenu ne se trouve dans aucun fichier conservé.

Si un mot à supprimer marque un fichier, celui-ci ne rend le jeu problématique dans aucun de ces cas.

La fenêtre utilise `tkinter`, qui fait partie de l'installation habituelle de Python sous Windows. S'il manque, le programme le signale et ne supprime rien.

## Après le nettoyage automatique

Même après le nettoyage automatique, des versions redondantes d'un jeu peuvent rester. Le plus simple pour les trouver est le filtre (touche `/` puis le nom du jeu). Vous pouvez ensuite marquer les fichiers qui restent à supprimer.

## Version terminal (Linux)

Le même programme fonctionne aussi dans un terminal texte, par exemple via SSH (PuTTY, MobaXterm), dans `tmux` ou sur la console Linux. Il montre la même liste, applique les mêmes règles et partage avec la fenêtre `redundanz_config.json`, `rom_cleanup_workbench_settings.json` et `translations.py`.

Sous Linux, elle démarre d'elle-même lorsqu'il n'y a pas d'affichage graphique (ni `DISPLAY` ni `WAYLAND_DISPLAY` ne sont définies, comme via SSH). `--tui` la démarre partout ailleurs, aussi sous Windows ; utilisez-le là où un affichage graphique existe mais où vous voulez le terminal, par exemple dans MobaXterm ou sous WSL.

Elle nécessite [Textual](https://textual.textualize.io/) (testé avec 8.2.8). L'installation et le lancement du programme sont décrits dans [Installation](#installation) et [Utilisation](#utilisation).

Sans Textual, le programme le signale et ne supprime rien. L'écran reprend les lignes de la fenêtre de haut en bas : la ligne de titre verte avec le dossier, la plateforme avec les principales touches, la liste, le champ de filtre avec l'interrupteur `Noms des jeux seulement`, les quatre vues et la ligne d'état verte. Dans la liste, chaque jeu commence par son nom en gras, suivi de tirets jusqu'au bord droit ; une remarque comme `Orthographes différentes du nom` figure sur cette ligne. Dans un terminal étroit, par exemple les 80 colonnes de PuTTY, les noms de fichiers et les remarques longs passent à la ligne dans leur colonne au lieu de sortir de l'écran. `Rien à faire.` clignote avec le clignotement propre du terminal ; dans PuTTY, il faut peut-être d'abord activer le texte clignotant. Les questions et les messages apparaissent dans un cadre au-dessus de la liste, avec des boutons dans la langue du programme ; `Non` est présélectionné.

À droite de la plateforme se trouvent les touches principales ; `F1` ou `?` les montre toutes, rangées par thème. La fenêtre et la version terminal ont les mêmes touches.

| Touche | Effet |
| --- | --- |
| Flèches | choisit une ligne, avec Maj plusieurs |
| `Tab` / `Maj+Tab` | jeu suivant / précédent ; son premier fichier est choisi |
| `x` / `k` | marque les fichiers choisis pour suppression / les garde |
| `1` `2` `3` `4` | les vues `À vérifier`, `À supprimer`, `Retirés entièrement`, `Tous les jeux` |
| `z` | afficher seulement les noms des jeux ou de nouveau les fichiers (comme l'interrupteur `Noms des jeux seulement`) |
| `/` | va au champ de filtre |
| `F12` | exécuter : supprimer après une confirmation (comme `Exécuter...`) |
| `f` | choisit un autre dossier : `Droite` ou `Espace` ouvre un dossier, `Gauche` le ferme, `Entrée` ou un double-clic le choisit ; on peut aussi saisir un chemin |
| `s` | paramètres : `Maj+Haut`/`Maj+Bas` déplacent une région, `Suppr` la retire, `Ctrl+S` enregistre, `Échap` annule |
| `r` ou `F5` | analyse à nouveau, relit aussi la configuration |
| `c` | affiche les crédits |
| `Entrée` | dans une plateforme de la collection : tout ce que l'on sait du jeu surligné (aussi double-clic dans la fenêtre) ; `Entrée`, `Échap` ou `q` ferme |
| `n` | dans une plateforme de la collection : marque les fichiers sélectionnés comme `pas un jeu` (par exemple un fichier BIOS) ou annule cela |
| `g` | dans une plateforme de la collection : le rapport gamelist de la plateforme |
| `e` | dans la vue du jeu : modifier les informations du jeu ; `Ctrl+S` enregistre, `Échap` revient |
| `w` | dans une plateforme de la collection : écrire son `gamelist.xml` à partir de la base de données (après une question) |
| `m` | dans une plateforme de la collection : supprimer ses fichiers multimédias inutilisés (après une question) |
| `F1` ou `?` | affiche ou masque toutes les touches (aussi `?`, car certains terminaux gardent `F1` pour leur propre aide) |
| `q` ou `Échap` | ferme sans rien supprimer ; dans une plateforme d'une collection, les deux reviennent d'abord à la vue d'ensemble ; après des modifications à la main, le programme demande d'abord |
| Dans une question | `Gauche`/`Droite` choisissent un bouton, `Entrée` l'actionne, `Échap` répond `Non` |

La souris fonctionne aussi : un clic choisit une ligne, la molette fait défiler, et on peut cliquer sur les vues et les boutons. Les lettres tapées dans un champ restent dans le champ, même tapées vite ou collées : un `x` dans le filtre ne marque jamais un fichier.

**Couleurs et caractères.** Avec 256 couleurs ou plus, la version terminal utilise les couleurs de la fenêtre, mais du noir derrière chaque jeu (pas de rayures). Là où le terminal n'a que 16 couleurs (`TERM=xterm`, `TERM=linux`), elle passe à des couleurs ANSI simples : sélection bleue, lignes de titre et d'état vertes, fichiers conservés en vert et marqués en rouge, lignes marron à texte noir modifiées à la main. Sur la console Linux, dans des terminaux comme `vt100` et quand la locale indique un jeu de caractères autre que UTF-8 (par exemple `en_US` ou `de_DE.ISO-8859-1`), elle ne dessine que des caractères ASCII : vues sous la forme `(*)`, cadres faits de `+`, `-` et `|`. `--ascii` l'impose. PuTTY se présente comme `xterm` (16 couleurs) ; pour les couleurs de la fenêtre, réglez *Connection → Data → Terminal-type string* sur `xterm-256color`. Les noms de fichier et les textes dans d'autres écritures, comme le japonais, nécessitent toujours un terminal et une police capables de les afficher.

Différences avec la fenêtre : pas de zoom du texte, car la police appartient au terminal (dans PuTTY : *Window → Appearance*) ; et les jeux ne sont pas rayés mais commencent par une ligne de tirets. Avec 16 couleurs, les lignes vertes ont du texte noir, qui reste lisible sur un vert clair. Pendant la suppression, la version terminal supprime en arrière-plan et montre la barre de progression ; toutes les touches sont bloquées jusqu'à la fin. La fenêtre et la version terminal conservent leur vue et les fichiers de sauvegarde confirmés dans le même `rom_cleanup_workbench_settings.json`.

## Configuration : `redundanz_config.json`

Le fichier se trouve à côté du programme et est relu à chaque analyse. La langue, la priorité, les mots à supprimer et le choix entre fichier normal et fichier ZIP se modifient le plus facilement dans la fenêtre avec `Paramètres...` (voir [Paramètres](#paramètres)). Dans le fichier lui-même, il suffit de changer l'ordre dans `region_priority` et d'enregistrer le fichier :

```json
"region_priority": ["USA", "Europe", "none", "Japan", "Beta"],
"delete_tags": [],
"prefer_zip": false,
```

Si le fichier contient une erreur, par exemple une entrée mal écrite, aucune analyse n'a lieu et rien n'est supprimé. Voici le fichier fourni : la langue est l'anglais, la priorité USA, Europe, none, Japan, Beta, il n'y a pas de mots à supprimer, et à côté d'un fichier ZIP le fichier normal est conservé. Les fichiers sans région passent donc avant les fichiers japonais. Si le fichier ou une entrée manque, les mêmes valeurs par défaut s'appliquent.

- `language` : la langue de la fenêtre, des remarques et de la sortie dans le terminal (voir ci-dessous).
- `region_priority` : régions et infos supplémentaires, la meilleure d'abord. `none` désigne les fichiers sans région connue ; les mots des autres langues (`keine`, `nessuna`, `ninguna`, `aucune`, `なし`) fonctionnent aussi. Une info supplémentaire comme `Beta` après `none` place ces fichiers en dernier (règle 6) ; `Beta` correspond aussi à `Beta 2`.
- `region_aliases` : autres orthographes d'une région, par exemple `Europa` pour `Europe`. Les formes courtes `U`, `E` et `J` des noms GoodTools comme `Title (J) [o1].nes` sont également fournies.
- `delete_tags` : les mots à supprimer, infos supplémentaires qui mènent toujours à la suppression (règle 2). Par défaut, la liste est vide. Un mot à supprimer compte comme mot entier n'importe où dans une parenthèse : `Hack` correspond à `(Hack)`, `(Hack 2)`, `(Hack by Someone)` et `(Micks Hack)`, mais pas à `(Hacks)` ni à `(Hackers)`, ni à un mot hors des parenthèses comme dans `Hack Attack (USA)` ; pour supprimer les hacks, saisissez donc `Hack` et `Hacks`.
- `part_tags` : parties d'une version, par exemple `Disc 1`.
- `prefer_zip` : `false` (par défaut) conserve le fichier normal quand un jeu existe en fichier normal et en fichier ZIP de la même version, `true` conserve le fichier ZIP.

Les anciens fichiers peuvent encore contenir `low_priority_tags`, des infos supplémentaires avec la priorité la plus basse. Le programme lit ses entrées comme si elles se trouvaient à la fin de `region_priority`, après `none` ; les paramètres les y déplacent lors de l'enregistrement, et l'entrée disparaît.

### Langue

```json
"language": "de",
```

| Valeur | Langue |
| --- | --- |
| `en` | anglais (par défaut) |
| `de` | allemand |
| `it` | italien |
| `es` | espagnol |
| `fr` | français |
| `ja` | japonais |

La langue s'applique à la fenêtre, aux remarques et à la sortie dans le terminal, et le programme la lit au démarrage : après l'avoir changée, fermez le programme et redémarrez-le. `F5` ne change pas la langue. Une valeur inconnue compte comme une erreur dans la configuration, comme décrit plus haut. Les règles décident de la même façon dans toutes les langues. Les textes se trouvent dans `translations.py`.

Pour le japonais, Windows affiche les caractères dans une police de substitution, car Lucida Sans Typewriter n'a pas de caractères japonais.

## Règles

Le programme ignore complètement certains fichiers : ils n'apparaissent nulle part et ne sont jamais supprimés. Comptent comme parenthèses `( )`, `[ ]` et `{ }`, partout de la même façon : pour le nom du jeu, la priorité, les versions et les mots à supprimer.

- Les fichiers dont le nom commence par `gamelist`, sans tenir compte des majuscules. Ce ne sont pas des fichiers ROM.
- Les fichiers cachés : noms commençant par un point, comme `.xxx` ou `.DS_Store`, et fichiers avec l'attribut Windows « caché ».

1. Les fichiers vont ensemble si le texte avant la première parenthèse est identique. Majuscules et minuscules, espaces, traits d'union et tirets bas ne comptent pas, donc `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. Ainsi `Title 1-2` = `Title 12` aussi. De plus, comptent comme identiques `und` = `and` = `&` = `&&`, `Sullivan's` = ``Sullivan`s`` = `Sullivan´s` = `Sullivans` (les apostrophes ne comptent pas), les chiffres romains de `I` à `IX` en tant que mot entier égaux à `1`-`9` (`Final Fantasy VII` = `Final Fantasy 7` ; à partir de `X`, ils restent tels quels, car `Mega Man X` et `Mega Man 10` sont deux jeux) et `The Title` = `Title The` = `Title, The` = `Title`. Un `The` au milieu du nom compte en revanche. De même, `vs` = `vs.` = `versus`. Un numéro devant le nom, par exemple issu d'une collection numérotée, ne compte pas : `057 Robocop vs Terminator` = `057 - Robocop vs Terminator` = `Robocop vs Terminator`. Si le nom ne se compose que du nombre (`1942`) ou si le nombre est collé au mot (`2Fast`), il reste une partie du nom ; `4 in 1` et `3 in 1` restent des jeux différents. Comme les noms ne concordent alors que grâce à la comparaison, le jeu compte comme problématique (`Orthographes différentes du nom`) si un fichier marqué de l'autre orthographe a un contenu différent de celui des fichiers conservés.
2. Les fichiers avec un mot à supprimer (`delete_tags`, aucun par défaut, par exemple `Hack` et `Hacks`) sont toujours marqués, même si c'est le seul fichier du jeu. `k` garde tout de même un tel fichier. La remarque indique alors `Supprimé selon le mot à supprimer (Hack) - comme demandé` ; il n'y a pas d'avertissement sur le contenu pour ces fichiers, puisque leur contenu doit disparaître. Exception : si une parenthèse nomme plusieurs régions et que l'une d'elles est exactement le mot à supprimer, mais qu'une autre est une région de votre liste de priorité, le mot à supprimer ne s'applique pas à cette parenthèse. `(Japan, USA)` est aussi la version USA : avec le mot à supprimer `Japan` et `USA` dans la liste, elle reste et est classée comme version USA ; `(Japan)` seul reste marqué.
3. Parmi les fichiers restants, celui qui a la meilleure entrée dans `region_priority` est conservé. Dans une même parenthèse, la meilleure entrée compte : avec `(USA, Japan)`, la meilleure des deux. D'une parenthèse à l'autre, la moins bonne compte : `(USA) (Beta)` compte comme `Beta` (règle 6).
4. Tous les fichiers d'une même version sont conservés ensemble, par exemple `(Disc 1)` et `(Disc 2)` ou `.cue` et `.bin`. Tout le reste est marqué. Exception : si une partie seulement de ces fichiers a un numéro devant le nom (`073 Batman (USA).sfc` et `Batman (USA).sfc`), ceux avec le numéro sont conservés et les autres sont marqués (`Nom avec numéro préféré`).
5. Une région absente de `region_priority` compte comme `none`. Cela vaut aussi pour des indications comme `(Rev 1)`.
6. Les infos supplémentaires comme `Beta`, `Proto` ou `Alpha` s'écrivent dans `region_priority` après `none`. Les fichiers qui les portent viennent après tous les autres, même après les fichiers sans région, et dans l'ordre de la liste : avec `none, Beta, Proto`, une Beta vient avant un Proto. Ils ne sont conservés que s'il n'y a pas de meilleur fichier du jeu. Entre eux, la région compte de nouveau, puis la version de la règle 7, puis le numéro après l'info supplémentaire : `Beta 2` l'emporte sur `Beta 1`, et `Beta 1` sur `Beta` sans numéro. Les numéros sont comparés numériquement (`Beta 10` avant `Beta 9`). Le fichier perdant reçoit la remarque `Bêta plus ancienne`.
7. À priorité égale, le numéro de version le plus élevé l'emporte, comparé numériquement (`v1.10` avant `v1.9`). Sont reconnus entre parenthèses `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` et `Rev A` ; dans le nom du jeu seulement la forme `Title v1.1`, aussi avec `-` ou `_` à la place de l'espace. Un fichier sans version perd face à un fichier avec version. La région compte avant la version.
8. Ensuite le fichier avec un numéro devant le nom l'emporte (`073 Batman` avant `Batman`), puis celui avec le moins d'informations supplémentaires, puis un fichier sans ZIP (avec `prefer_zip` : un fichier ZIP), puis l'ordre alphabétique. Le rapport affiche alors `Égalité`.
9. Un fichier plus petit que 1/4 du plus grand fichier du jeu est mis de côté avant les règles 3 à 8 et conservé : il pourrait s'agir d'un fichier d'état ou de sauvegarde. Il ne peut donc ni être supprimé ni évincer la vraie ROM, par exemple `1941.state` le fichier `1941.zip`. La colonne des remarques affiche alors `Fichier d'état ou de sauvegarde présumé`, et le jeu compte comme problématique. Un tel jeu apparaît dans `À vérifier`, `À supprimer` et `Tous les jeux`, même si aucun de ses fichiers n'est marqué. Lors de la suppression, le programme confirme tous les autres fichiers présumés comme légitimes : ils restent où ils sont, ne sont toujours jamais supprimés et n'apparaissent plus dans `À vérifier` et `À supprimer`, même après `F5` ou un redémarrage. La confirmation en indique le nombre. Le programme les mémorise avec leur chemin et leur taille dans `rom_cleanup_workbench_settings.json` ; si la taille change, le fichier redevient suspect. Si rien n'est marqué, `F12` propose de les confirmer sans rien supprimer. Les ZIP comptent avec leur taille décompressée. Cela ne s'applique pas à un petit fichier normal à côté d'un grand fichier normal de sa propre version, par exemple un `.cue` à côté de son `.bin`, ni à un fichier ayant la même extension que le plus grand fichier (un petit `.nes` à côté d'un grand `.nes` est une ROM sur laquelle décident les règles 3 à 8), ni aux fichiers marqués à cause de `delete_tags` ou d'un ZIP défectueux. Avec `x`, vous pouvez tout de même marquer le fichier à la main. Les sauvegardes avec une extension typique (`.srm`, `.sav`, `.eep`, `.mpk`, `.fla`, `.sra`, `.rtc`, `.dsv`, `.mcr`, `.state`, `.state1` …, `.state.auto`, `.st0` …, `.ss0` …) ne relèvent pas de cette règle : un émulateur ne charge une sauvegarde que si elle porte exactement le nom de la ROM (sans extension). Une sauvegarde n'est donc conservée que si un fichier conservé porte exactement ce nom, par exemple `Mario Kart 64 (USA).srm` à côté de `Mario Kart 64 (USA).n64`. Toute autre est marquée, même une d'une autre région ou d'une autre version comme `Mario Kart 64 (U) [!].mpk`, avec la remarque `Sauvegarde sans fichier ROM du même nom`. Les mots à supprimer s'appliquent aussi aux sauvegardes.
10. Lors de l'exécution, après la suppression, le numéro devant le nom de chaque fichier conservé est retiré, avec les espaces, points, traits d'union ou tirets bas qui suivent : `073 Batman (USA).sfc` devient `Batman (USA).sfc`, `057 - Robocop.md` devient `Robocop.md`. La confirmation indique auparavant le nombre et un exemple ; si rien n'est marqué, `F12` demande seulement pour le renommage. Le numéro reste si un fichier `.cue`, `.gdi`, `.m3u`, `.mds`, `.toc` ou `.ccd` appartient au jeu (il cite les noms de fichiers dans son contenu) ou si le nom sans numéro est déjà pris ; la confirmation indique aussi ce nombre. Le contenu des ZIP n'est pas renommé. La ligne de titre d'un jeu affiche le nom dans l'orthographe du premier fichier conservé (`Street Fighter II` ou `Street Fighter 2`), toujours sans numéro ; si vous déplacez des fichiers avec `k` ou `x`, le titre s'adapte. Un nombre ne compte comme numéro de liste que lorsque c'est clair : avec un zéro initial (`057`), avec un séparateur après (`057 - `, `283. `) ou si le même jeu existe aussi sans numéro (`283 Dynamite Bowl` à côté de `Dynamite Bowl (J)`) ; si un numéro d'un jeu est clair, tous ses numéros comptent comme numéros de liste. Sinon, le nombre fait partie du titre et reste, dans le nom du fichier comme dans la ligne de titre : `1080 Snowboarding`, `720 Degrees`.

## Fichiers ZIP

Chaque fichier ZIP est lu entièrement, même s'il est le seul fichier d'un jeu. Son contenu est comparé aux autres fichiers du jeu à l'aide de SHA-256.

- **Même contenu qu'un fichier conservé :** le fichier ZIP est marqué et le rapport nomme le fichier au même contenu.
- **S'il reste un ZIP et un fichier normal après la sélection :** le ZIP est toujours marqué, même avec un contenu différent, s'il est le seul fichier contenant une partie comme `(Disc 1)` ou s'il est illisible.
- **Avec `Garder le fichier ZIP` (`prefer_zip`) :** C'est l'inverse : à côté d'un fichier ZIP lisible de la même version, les fichiers normaux sont marqués (`Fichier ZIP préféré`). Si le contenu d'un tel fichier n'apparaît dans aucun ZIP conservé, le rapport affiche `Le contenu du jeu diffère du fichier ZIP conservé` et le jeu est considéré comme problématique (`Le contenu d'un fichier normal marqué n'est pas conservé`). Un ZIP illisible n'évince aucun fichier normal. La priorité passe toujours en premier : un fichier normal `(USA)` l'emporte sur un ZIP `(Japan)`.
- **Plusieurs ZIP de la même version au contenu différent :** tous sont conservés et le rapport le signale.
- **Marqué, mais le contenu n'apparaît dans aucun fichier conservé :** le rapport affiche `Le contenu du jeu diffère de la version conservée`. Le fichier reste marqué.
- **Pas de région ni de version dans le nom du ZIP :** l'information est tirée des fichiers du ZIP, à condition qu'ils aient le même nom de jeu.
- **ZIP endommagé ou chiffré :** le fichier est toujours marqué, même s'il est le seul fichier du jeu. Le contenu d'un ZIP chiffré n'est pas vérifié.
- **ZIP verrouillé ou méthode inconnue (par exemple Deflate64) :** cela ne dit rien de l'état du fichier. Sans fichier normal du jeu, il est conservé et signalé dans le rapport.

## Faire évoluer le programme avec Claude Code

Le programme est un logiciel libre : vous pouvez cloner le dépôt et le faire évoluer avec [Claude Code](https://claude.com/claude-code), sans programmer vous-même. C'est aussi ainsi qu'il a été écrit.

1. Installez Claude Code. Il faut un abonnement Claude ou un compte pour l'API Claude. Sous Windows, dans PowerShell :

   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```

   Sous Linux :

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

2. Clonez le dépôt et lancez Claude Code dedans :

   ```bash
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   cd rom-cleanup-workbench
   claude
   ```

3. Décrivez avec vos propres mots ce qui doit changer, par exemple « Ajoute une option qui n'affiche que les fichiers ZIP ». Claude Code lit le code, propose des modifications et demande avant de modifier des fichiers ou d'exécuter des commandes. Faites-lui ensuite lancer les tests (`python -m unittest` dans le dossier `Rom Cleanup Workbench`) et essayez la modification sur une copie de votre collection.

Les plans des modifications précédentes se trouvent dans `docs/`. Si vous diffusez vos modifications, vous devez aussi les publier sous la GPL.

## Licence et clause de non-responsabilité

Copyright (C) 2026 M. Kärcher

Rom Cleanup Workbench est un logiciel libre : vous pouvez le redistribuer et/ou le modifier selon les termes de la GNU General Public License publiée par la Free Software Foundation, soit la version 3 de la licence, soit (à votre choix) toute version ultérieure. Le texte complet se trouve dans [LICENSE](<../LICENSE>) ; seul ce texte original anglais fait foi juridiquement.

**Utilisation à vos propres risques.** Le programme supprime des fichiers et aucune garantie n'est fournie ; celui qui l'utilise en assume tous les risques. Nous recommandons vivement de l'utiliser uniquement sur une copie de votre propre collection de ROM.

## Crédits

- Idée : M. Kärcher
- Programmation : Claude Code
