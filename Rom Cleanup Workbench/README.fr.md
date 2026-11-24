# Rom Cleanup Workbench

[English](README.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · **Français** · [日本語](README.ja.md)

**Guide de l'utilisateur avec captures d'écran :** [PDF](<docs/Rom Cleanup Workbench - Guide utilisateur.pdf>) · [Word](<docs/Rom Cleanup Workbench - Guide utilisateur.docx>)

**Vidéo:** [comment fonctionne le programme (YouTube)](https://youtu.be/D1yXZQXg-iM)

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

Sans dossier, la fenêtre le demande. Pour la version terminal, ajoutez `--tui`.

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
| `--review all` | ouvre la fenêtre avec `Tous les marquages` pour ce démarrage |
| `--review problems` | ouvre la fenêtre avec `Marquages problématiques` pour ce démarrage |
| `--priority USA Europe Japan none` | fixe la priorité pour cette exécution |
| `--delete-tag Hack Hacks Proto` | fixe les mots à supprimer pour cette exécution |
| `--config file.json` | utilise une autre configuration |
| `--report-only` | sans fenêtre : affiche seulement le rapport dans le terminal |
| `--yes` | sans fenêtre : supprime les fichiers marqués sans demander |
| `--scan-all` | sans fenêtre : analyse tous les dossiers de plateforme du dossier `roms` indiqué et les enregistre dans sa base de données ; ne supprime rien |
| `--deep-scan` | avec `--scan-all` : analyse approfondie, relit chaque fichier au lieu des seuls fichiers nouveaux et modifiés (`--full` marche toujours) |
| `--all` | avec `--report-only` : montre aussi les jeux sans fichier marqué |
| `--tui` | utilise la version terminal au lieu de la fenêtre (automatique sous Linux sans affichage graphique) |
| `--ascii` | version terminal avec des caractères ASCII seulement (automatique sur la console Linux) ; implique `--tui` |

Les options de la ligne de commande et leur aide (`--help`) sont toujours en anglais.

Les tests se lancent avec `python -m unittest`.

## La collection : de nombreuses plateformes et la base de données

En général, les jeux se trouvent dans un dossier commun, séparés par plateforme, par exemple `roms/nes`, `roms/snes`, `roms/n64`. Si tu choisis ce dossier `roms`, le programme affiche la **vue d'ensemble** de toutes les plateformes. Ensuite, il démarre toujours avec la vue d'ensemble du dernier dossier `roms` utilisé. Compte comme dossier `roms` un dossier qui a déjà une base de données ou qui ne contient pas lui-même de fichiers ROM, mais des sous-dossiers. Les fichiers annexes comme `info.txt`, des images ou des PDF ne comptent pas comme fichiers ROM. Tout autre dossier est analysé seul comme avant, sans base de données.

**La base de données.** À la première ouverture d'un dossier `roms`, le programme y crée le dossier caché `.rom_cleanup_workbench` avec une base de données SQLite. C'est la seule chose qu'il écrit dans ta collection. Elle conserve les résultats de chaque analyse : fichiers, tailles, dates de modification, le contenu des ZIP avec leurs sommes de contrôle. À partir de là, le programme redécide en un instant chaque fois qu'il ouvre une plateforme ; les paramètres modifiés s'appliquent donc tout de suite, sans nouvelle analyse. Elle contient aussi les modifications à la main (`k`/`x`), les fichiers d'état et de sauvegarde confirmés et les paramètres propres à certaines plateformes.

**La vue d'ensemble** affiche pour chaque plateforme : fichiers, jeux, fichiers marqués pour suppression, jeux problématiques, la dernière analyse et l'état (`non analysée`, `à jour` ou `modifiée` si des fichiers ont été ajoutés, retirés ou modifiés depuis), avec le total en dessous.

| Bouton | Touche | Effet |
| --- | --- | --- |
| `Ouvrir` | `Entrée` | ouvre la plateforme surlignée dans la liste habituelle (aussi double clic) |
| `Analyser` | `r` ou `F5` | analyse la plateforme surlignée et l'ouvre |
| `Tout analyser` | `a` | analyse toutes les plateformes l'une après l'autre ; chacune est enregistrée tout de suite et ses chiffres apparaissent aussitôt dans la vue d'ensemble ; `Annuler` garde celles qui sont finies ; ne supprime rien |
| `Analyse approfondie` | `d` | interrupteur (point rouge) pour Analyser et Tout analyser : relit chaque fichier au lieu des seuls fichiers nouveaux et modifiés |
| `Masquer les vides` | `h` | interrupteur (point rouge) : masque les dossiers sans fichier de jeu, par exemple `bios` ou un dossier avec seulement `info.txt` ; les fichiers annexes ne comptent pas comme fichiers de jeu ; le choix est mémorisé |
| `Dossier...` | `f` | choisit un autre dossier `roms` |
| | `q` ou `Échap` | ferme le programme |

Les touches sont les mêmes dans la fenêtre et dans la version terminal. La ligne au-dessus du tableau nomme les principales ; `F1` ou `?` les montre toutes.

**Analyser.** Une analyse est d'habitude rapide : elle ne lit que les fichiers nouveaux et modifiés (reconnus par leur nom, leur taille et leur date de modification) et reprend tout le reste de la base de données. Avec `Analyse approfondie`, chaque fichier est relu. `F5` dans la liste analyse rapidement la plateforme ouverte. Exécuter inscrit tout de suite les fichiers supprimés et renommés ; aucune nouvelle analyse n'est nécessaire ensuite.

**Retour à la vue d'ensemble** : dans la liste avec `Échap`, `q` ou le bouton `Vue d'ensemble`, dans la version terminal aussi avec `o`. `Échap` ou `q` dans la vue d'ensemble ferme le programme ; pour sortir complètement, on appuie donc deux fois.

**Les modifications à la main** (`k`/`x`) restent enregistrées, même après la fermeture, jusqu'à ce que tu exécutes ou analyses de nouveau la plateforme. Si un fichier change, sa modification à la main tombe.

**Paramètres d'une plateforme.** Quand une plateforme est ouverte, les paramètres affichent en haut `Paramètres généraux` ou `Paramètres propres à NES`. Avec le choix propre à la plateforme, la priorité, les mots de suppression et le choix entre fichier normal et ZIP ne valent que pour cette plateforme ; ils sont dans la base de données, et `redundanz_config.json` reste le standard pour toutes les autres. De nouveaux paramètres propres partent des valeurs standard ; revenir à `Paramètres généraux` les abandonne. La ligne sous le titre des paramètres indique où ils sont enregistrés : `redundanz_config.json` ou, avec le choix propre à la plateforme, la base de données de la collection (la langue reste dans `redundanz_config.json`). La langue vaut toujours pour tout. Dans la vue d'ensemble, ces plateformes ont un `*` après leur nom.

**Sans fenêtre**, `--scan-all` analyse toutes les plateformes, par exemple pendant la nuit :

```powershell
python rom_cleanup_workbench.py "D:\roms" --scan-all
```

Avec `--deep-scan`, chaque fichier est relu. Rien n'est jamais supprimé ainsi.

## Fenêtre d'analyse

Comme les fichiers ZIP doivent être décompressés pour obtenir la taille, la somme SHA-256 et le nom de leur contenu, il peut falloir un moment après le choix d'un dossier avant que les résultats s'affichent.

La ligne verte du haut affiche `Rom Cleanup Workbench` à gauche et le dossier à droite ; en dessous figure en vert `Plateforme :` avec le nom du dossier ouvert. À droite se trouvent les touches principales de la vue, dans la liste `x Supprimer`, `k Garder`, `Entrée Effectuer le nettoyage` et `F1 / ? Aide : autres touches`. `F1` ou `?` affiche toutes les touches à la place de la liste, rangées par thème ; `Échap`, `F1` ou `?` les referme. Dans la vue d'ensemble, les deux montrent les touches de la vue d'ensemble et en dessous, sous `Bon à savoir`, ce que signifient les états, l'analyse et l'analyse approfondie. La priorité en vigueur se voit dans les paramètres. Dans la vue d'ensemble, le mot `Collection` est vert lui aussi. L'avant-dernière ligne verte montre l'état, pendant l'analyse par exemple `Analyse : 120 sur 2007 fichiers`. Pendant ce temps, une barre de progression apparaît aussi au milieu. La fenêtre affiche aussi les erreurs, par exemple dans la configuration, et tant que l'analyse échoue, rien ne peut être supprimé. Pendant la suppression, la barre de progression apparaît au milieu et la ligne verte affiche par exemple `Suppression : 120 sur 500 fichiers` ; la fenêtre n'accepte aucune saisie avant la fin de la suppression. Ensuite elle indique le résultat et retire de la liste les fichiers supprimés sans analyser à nouveau le dossier ; les fichiers qui n'ont pas pu être supprimés restent marqués. `F5` analyse à nouveau le dossier quand vous le souhaitez.

Si rien n'est marqué dans tout le dossier et qu'aucun fichier n'est soupçonné d'être un fichier d'état ou de sauvegarde, `Rien à faire.` clignote au milieu de la fenêtre.

Les trois boutons radio déterminent ce que montre la liste :

- `Marquages problématiques` : seulement les jeux avec un fichier marqué qui sont considérés comme problématiques (par défaut au premier démarrage)
- `Tous les marquages` : tous les jeux avec un fichier marqué
- `Tous les fichiers ROM` : tous les jeux. Leurs fichiers peuvent alors aussi être marqués avec `x`, et les cas problématiques sans fichier marqué, comme un ZIP illisible, apparaissent aussi.

La fenêtre retient la dernière vue choisie et les fichiers d'état ou de sauvegarde confirmés (règle 9) dans `rom_cleanup_workbench_settings.json` à côté du programme.

| Touche | Effet |
| --- | --- |
| Flèches | choisit une ligne, avec Maj plusieurs (par exemple tous les disques d'un jeu) |
| `Tab` / `Maj+Tab` | va au jeu suivant / précédent ; le premier fichier du jeu est choisi |
| `x` | marque le fichier pour suppression ; il passe à la fin de son jeu |
| `k` | garde le fichier ; il passe à la place que lui donnent les règles |
| `1` `2` `3` | les vues `Marquages problématiques`, `Tous les marquages`, `Tous les fichiers ROM` |
| `Ctrl` + molette de la souris | agrandit ou réduit le texte (de 8 à 32 pt, jusqu'à la fermeture de la fenêtre) |
| `s` | comme le bouton `Paramètres...` : affiche ou masque les paramètres de langue, de priorité, de mots à supprimer et de ZIP ou fichier normal (voir [Paramètres](#paramètres)) |
| `/` | va au champ de filtre |
| `Enter` | comme le bouton `Exécuter...` : supprime après une confirmation, retire le numéro devant les noms des fichiers conservés (règle 10) et confirme les fichiers d'état ou de sauvegarde présumés (règle 9) |
| `f` | choisit un autre dossier, dans la fenêtre à la place de la liste : ouvrez les dossiers avec la flèche, choisissez-en un aussitôt par un double-clic, ou saisissez un chemin dans `Chemin :`, puis `Sélectionner` ou `Entrée` ; `Annuler` ou `Échap` gardent le dossier actuel |
| `r` ou `F5` | analyse à nouveau, relit aussi la configuration |
| `c` | affiche les crédits |
| `F1` ou `?` | affiche ou masque toutes les touches |
| `q` ou `Échap` | ferme sans rien supprimer ; dans une plateforme d'une collection, les deux reviennent d'abord à la vue d'ensemble ; après des modifications à la main, le programme demande d'abord |

Des lignes horizontales séparent les jeux, et un jeu sur deux a un fond gris foncé. La colonne `Taille` montre la taille de chaque fichier en Ko, arrondie au supérieur comme dans l'Explorateur Windows (`1 234 Ko`) ; `?` signifie que la taille n'a pas pu être lue. La taille est lue pendant l'analyse. Les fichiers conservés sont affichés en gras et en vert sous `Garder :`, ceux à supprimer en rouge sous `Marqué pour suppression`. La fenêtre affiche du texte blanc en Lucida Sans Typewriter 11 pt sur fond noir. Si la police n'est pas installée, Windows choisit discrètement une police de substitution. Les fichiers déplacés à la main ont un fond marron et portent la remarque `À la main` ; tant que la ligne est choisie, elle apparaît en bleu. Les remarques du programme restent inchangées, même si elles concernent un fichier que vous avez déplacé.

`Marquages problématiques` masque les jeux sans problème. **Leurs fichiers marqués sont quand même supprimés lorsque vous supprimez** ; la confirmation indique leur nombre. Les jeux que vous avez modifiés à la main restent toujours visibles, sauf si le filtre les masque.

### Filtre

Le champ de filtre à gauche de la ligne du bas restreint la vue actuelle aux jeux dont un nom de fichier contient le motif. Un jeu reste complet si l'un de ses fichiers correspond. La liste se met à jour peu après la saisie ; le contenu des fichiers n'est pas lu.

- `*` remplace un nombre quelconque de caractères, `?` exactement un. Tous les autres caractères, y compris `[` et `]`, comptent littéralement, et les majuscules et minuscules ne comptent pas. Les espaces au début et à la fin ne comptent qu'entre guillemets : `" by "` trouve `Mario by Mick` mais pas `Moby Dick` ; sans guillemets, `by` trouve les deux.
- Le motif peut apparaître n'importe où dans le nom : `Beta`, `*Beta*` et `Mario?2` trouvent tous aussi `Super Mario 2 (Beta).nes`. Par conséquent, `S*` trouve tout nom contenant un `S`, pas seulement les noms qui commencent par lui.
- `Entrée`, `Tab` et la flèche vers le bas reviennent à la liste ; `Échap` vide le filtre et revient à la liste.
- Tant que le curseur est dans le champ, les touches n'écrivent que là : `x`, `k`, `Enter`, `f`, `r`, `F5` et `Échap` n'exécutent pas leurs fonctions de liste.
- Le filtre reste actif après `F5`, après la suppression et après le choix d'un autre dossier. Il n'est pas enregistré.

**Le filtre ne change que l'affichage. Les fichiers marqués masqués par le filtre sont quand même supprimés lorsque vous supprimez** ; la confirmation indique leur nombre.

### Paramètres

Le bouton `Paramètres...` de la ligne du bas, ou `s`, montre les modifications les plus fréquentes de `redundanz_config.json` dans la fenêtre principale, à la place de la liste des fichiers. `Enregistrer` ou `Annuler`, `Échap`, `Ctrl+E` ou un nouveau clic sur `Paramètres...` ramènent la liste. Pendant ce temps, le filtre, les vues, `Exécuter...`, `Analyser à nouveau` et `Dossier...` sont bloqués, et `x`, `k` et `Enter` ne font rien, afin que rien ne puisse changer dans la liste cachée.

- **Langue :** Définit la langue de l'interface. Choisissez parmi les six langues. Une nouvelle langue s'applique au prochain démarrage du programme.
- **Priorité :** Définit quelles versions régionales ont la priorité sur les autres. La meilleure région en haut ; les infos supplémentaires comme `Beta` ou `Proto` se placent après `none`, pour que ces fichiers viennent en dernier (règle 6). Choisissez une entrée et déplacez-la avec `Monter` et `Descendre`, retirez-la avec `Retirer` ou la touche `Suppr`, et ajoutez-en une nouvelle avec le champ sous la liste et `Ajouter` (ou `Entrée`).
- **Mots à supprimer :** Définissent quelles versions d'un jeu sont toujours supprimées. Séparés par des virgules, par exemple `Hack, Hacks`. Les fichiers qui les contiennent sont marqués pour suppression (règle 2).
- **Même jeu en fichier normal et en fichier ZIP :** Définit lequel des deux est conservé quand les deux sont de la même version. `Garder le fichier normal` (par défaut) marque le fichier ZIP, `Garder le fichier ZIP` marque les fichiers normaux (voir [Fichiers ZIP](#fichiers-zip)).

`Enregistrer` écrit le fichier et analyse à nouveau le dossier si la priorité, les mots ou le choix entre fichier normal et fichier ZIP ont changé ; si vous avez modifié des marquages à la main, le programme demande d'abord, car ces modifications sont perdues. Toutes les autres entrées du fichier restent telles quelles. Les valeurs erronées, comme une liste de régions vide ou deux fois la même région, sont signalées, rien n'est écrit et les paramètres restent ouverts. Si le fichier ne peut pas être lu, les paramètres ne s'ouvrent pas, afin qu'ils ne puissent pas écraser des entrées qu'ils ne connaissent pas. Avec `--config`, les paramètres modifient ce fichier ; avec `--priority`, la priorité qui y est indiquée reste valable pour cette exécution.

Un jeu est considéré comme problématique si

- aucun de ses fichiers ne serait conservé,
- le contenu d'un ZIP marqué n'apparaît nulle part ailleurs (`Le contenu du jeu diffère de la version conservée`),
- un ZIP est endommagé, chiffré ou illisible,
- un fichier est conservé comme fichier d'état ou de sauvegarde présumé (règle 9),
- les règles n'ont décidé que par `Égalité`,
- plusieurs ZIP de la même version ont un contenu différent,
- les noms de fichier écrivent le jeu différemment (`Title 1-2` et `Title 12`),
- un fichier marqué a un autre type de fichier que les fichiers conservés (`.nes` et `.sfc`).

La fenêtre utilise `tkinter`, qui fait partie de l'installation habituelle de Python sous Windows. S'il manque, le programme le signale et ne supprime rien.

## Après le nettoyage automatique

Même après le nettoyage automatique, des versions redondantes d'un jeu peuvent rester. Le plus simple pour les trouver est le filtre (touche `/` puis le nom du jeu). Vous pouvez ensuite marquer les fichiers qui restent à supprimer.

## Version terminal (Linux)

Le même programme fonctionne aussi dans un terminal texte, par exemple via SSH (PuTTY, MobaXterm), dans `tmux` ou sur la console Linux. Il montre la même liste, applique les mêmes règles et partage avec la fenêtre `redundanz_config.json`, `rom_cleanup_workbench_settings.json` et `translations.py`.

Sous Linux, elle démarre d'elle-même lorsqu'il n'y a pas d'affichage graphique (ni `DISPLAY` ni `WAYLAND_DISPLAY` ne sont définies, comme via SSH). `--tui` la démarre partout ailleurs, aussi sous Windows ; utilisez-le là où un affichage graphique existe mais où vous voulez le terminal, par exemple dans MobaXterm ou sous WSL.

Elle nécessite [Textual](https://textual.textualize.io/) (testé avec 8.2.8). L'installation et le lancement du programme sont décrits dans [Installation](#installation) et [Utilisation](#utilisation).

Sans Textual, le programme le dit et ne supprime rien. L'écran a les lignes de la fenêtre de haut en bas : la ligne de titre verte avec le dossier, la plateforme avec les touches principales, la liste, le champ de filtre, les trois vues et la ligne d'état verte. Dans la liste, chaque jeu commence par son nom en gras, suivi de tirets jusqu'au bord droit ; une remarque comme `Orthographes différentes du nom` figure sur cette ligne. Dans un terminal étroit, comme les 80 colonnes de PuTTY, les noms de fichier et les remarques longs passent à la ligne dans leur colonne au lieu de sortir de l'écran. `Rien à faire.` clignote avec le clignotement propre au terminal ; dans PuTTY, il faut parfois d'abord activer le texte clignotant. Les questions et les messages apparaissent dans un cadre au-dessus de la liste, avec des boutons dans la langue du programme ; `Non` est présélectionné.

À droite de la plateforme se trouvent les touches principales ; `F1` ou `?` les montre toutes, rangées par thème. La fenêtre et la version terminal ont les mêmes touches.

| Touche | Effet |
| --- | --- |
| Flèches | choisit une ligne, avec Maj plusieurs |
| `Tab` / `Maj+Tab` | jeu suivant / précédent ; son premier fichier est choisi |
| `x` / `k` | marque les fichiers choisis pour suppression / les garde |
| `1` `2` `3` | les vues `Marquages problématiques`, `Tous les marquages`, `Tous les fichiers ROM` |
| `/` | va au champ de filtre |
| `Entrée` | exécuter : supprime après une confirmation (comme `Exécuter...`) |
| `f` | choisit un autre dossier : `Droite` ou `Espace` ouvre un dossier, `Gauche` le ferme, `Entrée` ou un double-clic le choisit ; on peut aussi saisir un chemin |
| `s` | paramètres : `Maj+Haut`/`Maj+Bas` déplacent une région, `Suppr` la retire, `Ctrl+S` enregistre, `Échap` annule |
| `r` ou `F5` | analyse à nouveau, relit aussi la configuration |
| `c` | affiche les crédits |
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

Le programme ignore complètement certains fichiers : ils n'apparaissent nulle part et ne sont jamais supprimés.

- Les fichiers dont le nom commence par `gamelist`, sans tenir compte des majuscules. Ce ne sont pas des fichiers ROM.
- Les fichiers cachés : noms commençant par un point, comme `.xxx` ou `.DS_Store`, et fichiers avec l'attribut Windows « caché ».

1. Les fichiers vont ensemble si le texte avant la première parenthèse est identique. Les majuscules, espaces, tirets et tirets bas ne comptent pas, donc `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. Cela donne aussi `Title 1-2` = `Title 12`. De plus, `und` = `and` = `&` = `&&`, `Sullivan's` = ``Sullivan`s`` = `Sullivan´s` = `Sullivans` (les apostrophes ne comptent pas), les chiffres romains de `I` à `IX` comme mot entier = de `1` à `9` (`Final Fantasy VII` = `Final Fantasy 7` ; à partir de `X`, ils restent tels quels, car `Mega Man X` et `Mega Man 10` sont deux jeux) ainsi que `The Title` = `Title The` = `Title, The` = `Title` comptent comme égaux. Un `The` au milieu du nom compte en revanche. De même `vs` = `vs.` = `versus`. Un numéro devant le nom, par exemple d'une collection numérotée, ne compte pas : `057 Robocop vs Terminator` = `057 - Robocop vs Terminator` = `Robocop vs Terminator`. Si le nom n'est que le numéro (`1942`) ou si le numéro est collé au mot (`2Fast`), il reste une partie du nom ; `4 in 1` et `3 in 1` restent des jeux différents. Comme les noms ne correspondent alors que grâce à la comparaison, le jeu est considéré comme problématique (`Orthographes différentes du nom`).
2. Les fichiers avec un mot à supprimer (`delete_tags`, aucun par défaut, par exemple `Hack` et `Hacks`) sont toujours marqués, même s'ils sont le seul fichier du jeu. `k` garde quand même un tel fichier.
3. Parmi les fichiers restants, celui qui a la meilleure entrée dans `region_priority` est conservé. Dans une même parenthèse, la meilleure entrée compte : avec `(USA, Japan)`, la meilleure des deux. D'une parenthèse à l'autre, la moins bonne compte : `(USA) (Beta)` compte comme `Beta` (règle 6).
4. Tous les fichiers d'une même version sont conservés ensemble, par exemple `(Disc 1)` et `(Disc 2)` ou `.cue` et `.bin`. Tout le reste est marqué. Exception : si une partie seulement de ces fichiers a un numéro devant le nom (`073 Batman (USA).sfc` et `Batman (USA).sfc`), ceux avec le numéro sont conservés et les autres sont marqués (`Nom avec numéro préféré`).
5. Une région absente de `region_priority` compte comme `none`. Cela vaut aussi pour des indications comme `(Rev 1)`.
6. Les infos supplémentaires comme `Beta`, `Proto` ou `Alpha` s'écrivent dans `region_priority` après `none`. Les fichiers qui les portent viennent après tous les autres, même après les fichiers sans région, et dans l'ordre de la liste : avec `none, Beta, Proto`, une Beta vient avant un Proto. Ils ne sont conservés que s'il n'y a pas de meilleur fichier du jeu. Entre eux, la région compte de nouveau, puis la version de la règle 7, puis le numéro après l'info supplémentaire : `Beta 2` l'emporte sur `Beta 1`, et `Beta 1` sur `Beta` sans numéro. Les numéros sont comparés numériquement (`Beta 10` avant `Beta 9`). Le fichier perdant reçoit la remarque `Bêta plus ancienne`.
7. À priorité égale, le numéro de version le plus élevé l'emporte, comparé numériquement (`v1.10` avant `v1.9`). Sont reconnus entre parenthèses `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` et `Rev A` ; dans le nom du jeu seulement la forme `Title v1.1`, aussi avec `-` ou `_` à la place de l'espace. Un fichier sans version perd face à un fichier avec version. La région compte avant la version.
8. Ensuite le fichier avec un numéro devant le nom l'emporte (`073 Batman` avant `Batman`), puis celui avec le moins d'informations supplémentaires, puis un fichier sans ZIP (avec `prefer_zip` : un fichier ZIP), puis l'ordre alphabétique. Le rapport affiche alors `Égalité`.
9. Un fichier plus petit que 1/4 du plus grand fichier du jeu est mis de côté avant les règles 3 à 8 et conservé : il peut s'agir d'un fichier d'état ou de sauvegarde. Il ne peut donc être ni supprimé ni évincer la vraie ROM, par exemple `1941.state` le fichier `1941.zip`. La colonne des remarques indique alors `Fichier d'état ou de sauvegarde présumé`, et le jeu est considéré comme problématique. Un tel jeu apparaît dans les trois vues, même si aucun de ses fichiers n'est marqué. Lorsque vous supprimez, le programme confirme comme légitimes tous les fichiers présumés restants : ils restent où ils sont, ne sont toujours jamais supprimés et n'apparaissent plus dans `Marquages problématiques` ni dans `Tous les marquages`, même après `F5` ou un nouveau démarrage. La confirmation indique leur nombre. Le programme les mémorise avec leur chemin et leur taille dans `rom_cleanup_workbench_settings.json` ; si la taille change, le fichier redevient suspect. Si rien n'est marqué, `Enter` propose de les confirmer sans rien supprimer. Les ZIP comptent avec leur taille décompressée. Cela ne vaut pas pour un petit fichier normal à côté d'un grand fichier normal de sa propre version, comme un `.cue` à côté de son `.bin`, ni pour un fichier de même extension que le plus grand fichier (un petit `.nes` à côté d'un grand `.nes` est une ROM sur laquelle décident les règles 3 à 8), ni pour les fichiers marqués à cause de `delete_tags` ou d'un ZIP endommagé. Avec `x`, vous pouvez quand même marquer le fichier à la main.
10. Quand vous exécutez, le programme retire après la suppression le numéro devant le nom de chaque fichier conservé, avec les espaces, points, tirets ou tirets bas qui le suivent : `073 Batman (USA).sfc` devient `Batman (USA).sfc`, `057 - Robocop.md` devient `Robocop.md`. La confirmation en indique d'abord le nombre et un exemple ; si rien n'est marqué, `Entrée` demande seulement de renommer. Le numéro reste si le jeu a un fichier `.cue`, `.gdi`, `.m3u`, `.mds`, `.toc` ou `.ccd` (il nomme les fichiers dans son contenu) ou si le nom sans numéro est déjà pris ; la confirmation indique aussi ce nombre. Le contenu des ZIP n'est pas renommé. La ligne de titre d'un jeu montre le nom écrit comme dans le premier fichier conservé (`Street Fighter II` ou `Street Fighter 2`), toujours sans numéro ; si vous déplacez des fichiers avec `k` ou `x`, le titre suit.

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
