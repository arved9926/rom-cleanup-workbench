# Rom Cleanup Workbench

[English](README.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · **Français** · [日本語](README.ja.md)

**Guide de l'utilisateur avec captures d'écran :** [PDF](<docs/Rom Cleanup Workbench - Guide utilisateur.pdf>) · [Word](<docs/Rom Cleanup Workbench - Guide utilisateur.docx>)

Trouve les fichiers ROM en double dans un dossier d'après le nom du jeu et les supprime sur demande.
Nécessite Python 3.10 ou plus récent. La fenêtre n'a besoin d'aucun paquet supplémentaire ; la version terminal pour Linux nécessite Textual (voir [Version terminal (Linux)](#version-terminal-linux)).
Le programme parle anglais, allemand, italien, espagnol, français et japonais (voir [Langue](#langue)).

## Utilisation

```bash
python rom_cleanup_workbench.py "D:\Games"
```

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
| `--all` | avec `--report-only` : montre aussi les jeux sans fichier marqué |
| `--tui` | utilise la version terminal au lieu de la fenêtre (automatique sous Linux sans affichage graphique) |
| `--ascii` | version terminal avec des caractères ASCII seulement (automatique sur la console Linux) ; implique `--tui` |

Les options de la ligne de commande et leur aide (`--help`) sont toujours en anglais.

Dans VS Code : ouvrez le dossier `Rom Cleanup Workbench`, démarrez avec F5 et saisissez le dossier.
Les tests se lancent depuis la vue des tests ou avec `python -m unittest`.

## Fenêtre d'analyse

La ligne verte du haut affiche `Rom Cleanup Workbench` à gauche et le dossier à droite ; en dessous, la fenêtre indique la priorité en vigueur et sa source. L'avant-dernière ligne verte montre l'état, pendant l'analyse par exemple `Analyse : 120 sur 2007 fichiers`. Pendant ce temps, une barre de progression apparaît aussi au milieu. La fenêtre affiche aussi les erreurs, par exemple dans la configuration, et tant que l'analyse échoue, rien ne peut être supprimé. Pendant la suppression, la barre de progression apparaît au milieu et la ligne verte affiche par exemple `Suppression : 120 sur 500 fichiers` ; la fenêtre n'accepte aucune saisie avant la fin de la suppression. Ensuite elle indique le résultat et retire de la liste les fichiers supprimés sans analyser à nouveau le dossier ; les fichiers qui n'ont pas pu être supprimés restent marqués. `F5` analyse à nouveau le dossier quand vous le souhaitez.

Si rien n'est marqué dans tout le dossier et qu'aucun fichier n'est soupçonné d'être un fichier d'état ou de sauvegarde, `Rien à faire.` clignote au milieu de la fenêtre.

Les trois boutons radio déterminent ce que montre la liste :

- `Marquages problématiques` : seulement les jeux avec un fichier marqué qui sont considérés comme problématiques (par défaut au premier démarrage)
- `Tous les marquages` : tous les jeux avec un fichier marqué
- `Tous les fichiers ROM` : tous les jeux. Leurs fichiers peuvent alors aussi être marqués avec `D`, et les cas problématiques sans fichier marqué, comme un ZIP illisible, apparaissent aussi.

La fenêtre retient la dernière vue choisie et les fichiers d'état ou de sauvegarde confirmés (règle 9) dans `rom_cleanup_workbench_settings.json` à côté du programme.

| Touche | Effet |
| --- | --- |
| Flèches | choisit une ligne, avec Maj plusieurs (par exemple tous les disques d'un jeu) |
| `Tab` / `Maj+Tab` | va au jeu suivant / précédent ; le premier fichier du jeu est choisi |
| `D` (Demote) | marque le fichier pour suppression ; il passe à la fin de son jeu |
| `P` (Promote) | garde le fichier ; il passe à la place que lui donnent les règles |
| `Ctrl` + molette de la souris | agrandit ou réduit le texte (de 8 à 32 pt, jusqu'à la fermeture de la fenêtre) |
| `Ctrl+E` | comme le bouton `Paramètres...` : affiche ou masque les paramètres de langue, de priorité et de mots à supprimer (voir [Paramètres](#paramètres)) |
| `Ctrl+F` | va au champ de filtre |
| `Ctrl+L` | comme le bouton `Exécuter...` : supprime après une confirmation et confirme les fichiers d'état ou de sauvegarde présumés (règle 9) |
| `Ctrl+O` | choisit un autre dossier, dans la fenêtre à la place de la liste : ouvrez les dossiers par un double-clic ou avec la flèche, ou saisissez un chemin dans `Chemin :`, puis `Sélectionner` ou `Entrée` ; `Annuler` ou `Échap` gardent le dossier actuel |
| `F5` | analyse à nouveau, relit aussi la configuration |
| `F1` | affiche les crédits |
| `Échap` | ferme sans rien supprimer |

Des lignes horizontales séparent les jeux, et un jeu sur deux a un fond gris foncé. La colonne `Taille` montre la taille de chaque fichier en Ko, arrondie au supérieur comme dans l'Explorateur Windows (`1 234 Ko`) ; `?` signifie que la taille n'a pas pu être lue. La taille est lue pendant l'analyse. Les fichiers conservés sont affichés en gras sous `Garder :`, ceux à supprimer en caractères normaux sous `Marqué pour suppression`. La fenêtre affiche du texte blanc en Lucida Sans Typewriter 11 pt sur fond noir. Si la police n'est pas installée, Windows choisit discrètement une police de substitution. Les fichiers déplacés à la main ont un fond marron et portent la remarque `À la main` ; tant que la ligne est choisie, elle apparaît en bleu. Les remarques du programme restent inchangées, même si elles concernent un fichier que vous avez déplacé.

`Marquages problématiques` masque les jeux sans problème. **Leurs fichiers marqués sont quand même supprimés lorsque vous supprimez** ; la confirmation indique leur nombre. Les jeux que vous avez modifiés à la main restent toujours visibles, sauf si le filtre les masque.

### Filtre

Le champ de filtre à gauche de la ligne du bas restreint la vue actuelle aux jeux dont un nom de fichier contient le motif. Un jeu reste complet si l'un de ses fichiers correspond. La liste se met à jour peu après la saisie ; le contenu des fichiers n'est pas lu.

- `*` remplace un nombre quelconque de caractères, `?` exactement un. Tous les autres caractères, y compris `[` et `]`, comptent littéralement, et les majuscules et minuscules ne comptent pas.
- Le motif peut apparaître n'importe où dans le nom : `Beta`, `*Beta*` et `Mario?2` trouvent tous aussi `Super Mario 2 (Beta).nes`. Par conséquent, `S*` trouve tout nom contenant un `S`, pas seulement les noms qui commencent par lui.
- `Entrée`, `Tab` et la flèche vers le bas reviennent à la liste ; `Échap` vide le filtre et revient à la liste.
- Tant que le curseur est dans le champ, les touches n'écrivent que là : `D`, `P`, `Ctrl+L`, `Ctrl+O`, `F5` et `Échap` n'exécutent pas leurs fonctions de liste.
- Le filtre reste actif après `F5`, après la suppression et après le choix d'un autre dossier. Il n'est pas enregistré.

**Le filtre ne change que l'affichage. Les fichiers marqués masqués par le filtre sont quand même supprimés lorsque vous supprimez** ; la confirmation indique leur nombre.

### Paramètres

Le bouton `Paramètres...` de la ligne du bas, ou `Ctrl+E`, montre les modifications les plus fréquentes de `redundanz_config.json` dans la fenêtre principale, à la place de la liste des fichiers. `Enregistrer` ou `Annuler`, `Échap`, un second `Ctrl+E` ou un nouveau clic sur `Paramètres...` ramènent la liste. Pendant ce temps, le filtre, les vues, `Exécuter...`, `Analyser à nouveau` et `Dossier...` sont bloqués, et `D`, `P` et `Ctrl+L` ne font rien, afin que rien ne puisse changer dans la liste cachée.

- **Langue :** choisissez parmi les six langues. Une nouvelle langue s'applique au prochain démarrage du programme.
- **Priorité :** la meilleure région en haut ; les infos supplémentaires comme `Beta` ou `Proto` se placent après `none`, pour que ces fichiers viennent en dernier (règle 6). Choisissez une entrée et déplacez-la avec `Monter` et `Descendre`, retirez-la avec `Retirer` ou la touche `Suppr`, et ajoutez-en une nouvelle avec le champ sous la liste et `Ajouter` (ou `Entrée`).
- **Mots à supprimer :** séparés par des virgules, par exemple `Hack, Hacks`. Les fichiers qui les contiennent sont marqués pour suppression (règle 2).

`Enregistrer` écrit le fichier et analyse à nouveau le dossier si la priorité ou les mots ont changé ; si vous avez modifié des marquages à la main, le programme demande d'abord, car ces modifications sont perdues. Toutes les autres entrées du fichier restent telles quelles. Les valeurs erronées, comme une liste de régions vide ou deux fois la même région, sont signalées, rien n'est écrit et les paramètres restent ouverts. Si le fichier ne peut pas être lu, les paramètres ne s'ouvrent pas, afin qu'ils ne puissent pas écraser des entrées qu'ils ne connaissent pas. Avec `--config`, les paramètres modifient ce fichier ; avec `--priority`, la priorité qui y est indiquée reste valable pour cette exécution.

Un jeu est considéré comme problématique si

- aucun de ses fichiers ne serait conservé,
- le contenu d'un ZIP marqué n'apparaît nulle part ailleurs (`ATTENTION`),
- un ZIP est endommagé, chiffré ou illisible,
- un fichier est conservé comme fichier d'état ou de sauvegarde présumé (règle 9),
- les règles n'ont décidé que par `Égalité`,
- plusieurs ZIP de la même version ont un contenu différent,
- les noms de fichier écrivent le jeu différemment (`Title 1-2` et `Title 12`),
- un fichier marqué a un autre type de fichier que les fichiers conservés (`.nes` et `.sfc`).

La fenêtre utilise `tkinter`, qui fait partie de l'installation habituelle de Python sous Windows. S'il manque, le programme le signale et ne supprime rien.

## Version terminal (Linux)

Le même programme fonctionne aussi dans un terminal texte, par exemple via SSH (PuTTY, MobaXterm), dans `tmux` ou sur la console Linux. Il montre la même liste, applique les mêmes règles et partage avec la fenêtre `redundanz_config.json`, `rom_cleanup_workbench_settings.json` et `translations.py`.

Sous Linux, elle démarre d'elle-même lorsqu'il n'y a pas d'affichage graphique (ni `DISPLAY` ni `WAYLAND_DISPLAY` ne sont définies, comme via SSH). `--tui` la démarre partout ailleurs, aussi sous Windows ; utilisez-le là où un affichage graphique existe mais où vous voulez le terminal, par exemple dans MobaXterm ou sous WSL.

Elle nécessite [Textual](https://textual.textualize.io/) (testé avec 8.2.8), de préférence dans un environnement virtuel :

```bash
python3 -m venv ~/venvs/rom-cleanup-workbench
~/venvs/rom-cleanup-workbench/bin/pip install textual==8.2.8
~/venvs/rom-cleanup-workbench/bin/python rom_cleanup_workbench.py --tui ~/roms
```

Sans Textual, le programme le dit et ne supprime rien. L'écran a les lignes de la fenêtre de haut en bas : la ligne de titre verte avec le dossier, une ligne d'aide, la priorité, la liste, le champ de filtre, les trois vues et la ligne d'état verte. Dans la liste, chaque jeu commence par son nom en gras, suivi de tirets jusqu'au bord droit ; une remarque comme `Orthographes différentes du nom` figure sur cette ligne. Dans un terminal étroit, comme les 80 colonnes de PuTTY, les noms de fichier et les remarques longs passent à la ligne dans leur colonne au lieu de sortir de l'écran. `Rien à faire.` clignote avec le clignotement propre au terminal ; dans PuTTY, il faut parfois d'abord activer le texte clignotant. Les questions et les messages apparaissent dans un cadre au-dessus de la liste, avec des boutons dans la langue du programme ; `Non` est présélectionné.

La ligne d'aide montre les touches sous la forme `touche:action`, par exemple `x:supprimer  k:garder`. La version terminal a ses propres touches ; la fenêtre garde `D`, `P` et les touches `Ctrl`.

| Touche | Effet |
| --- | --- |
| Flèches | choisit une ligne, avec Maj plusieurs |
| `Tab` / `Maj+Tab` | jeu suivant / précédent ; son premier fichier est choisi |
| `x` / `k` | marque les fichiers choisis pour suppression / les garde |
| `1` `2` `3` | les vues `Marquages problématiques`, `Tous les marquages`, `Tous les fichiers ROM` |
| `/` | va au champ de filtre (`Entrée`, `Tab` ou la flèche vers le bas reviennent, `Échap` le vide) |
| `Entrée` | exécuter : supprime après une confirmation (comme `Exécuter...`) |
| `f` | choisit un autre dossier : `Droite` ou `Espace` ouvre un dossier, `Gauche` le ferme, `Entrée` choisit ; on peut aussi saisir un chemin |
| `s` | paramètres : `Maj+Haut`/`Maj+Bas` déplacent une région, `Suppr` la retire, `Ctrl+S` enregistre, `Échap` annule |
| `r` ou `F5` | analyse à nouveau |
| `c` ou `F1` | affiche les crédits (aussi `c`, car certains terminaux réservent `F1` à leur propre aide) |
| `q` ou `Échap` | ferme sans rien supprimer ; après des modifications à la main, le programme demande d'abord |
| Dans une question | `Gauche`/`Droite` choisissent un bouton, `Entrée` l'actionne, `Échap` répond `Non` |

La souris fonctionne aussi : un clic choisit une ligne, la molette fait défiler, et on peut cliquer sur les vues et les boutons. Les lettres tapées dans un champ restent dans le champ, même tapées vite ou collées : un `x` dans le filtre ne marque jamais un fichier.

**Couleurs et caractères.** Avec 256 couleurs ou plus, la version terminal utilise les couleurs de la fenêtre, mais du noir derrière chaque jeu (pas de rayures). Là où le terminal n'a que 16 couleurs (`TERM=xterm`, `TERM=linux`), elle passe à des couleurs ANSI simples : sélection bleue, lignes de titre et d'état vertes, lignes marron modifiées à la main. Sur la console Linux, dans des terminaux comme `vt100` et quand la locale indique un jeu de caractères autre que UTF-8 (par exemple `en_US` ou `de_DE.ISO-8859-1`), elle ne dessine que des caractères ASCII : vues sous la forme `(*)`, cadres faits de `+`, `-` et `|`. `--ascii` l'impose. PuTTY se présente comme `xterm` (16 couleurs) ; pour les couleurs de la fenêtre, réglez *Connection → Data → Terminal-type string* sur `xterm-256color`. Les noms de fichier et les textes dans d'autres écritures, comme le japonais, nécessitent toujours un terminal et une police capables de les afficher.

Différences avec la fenêtre : pas de zoom du texte, car la police appartient au terminal (dans PuTTY : *Window → Appearance*) ; et les jeux ne sont pas rayés mais commencent par une ligne de tirets. Avec 16 couleurs, les lignes vertes ont du texte noir, qui reste lisible sur un vert clair. Pendant la suppression, la version terminal supprime en arrière-plan et montre la barre de progression ; toutes les touches sont bloquées jusqu'à la fin. La fenêtre et la version terminal conservent leur vue et les fichiers de sauvegarde confirmés dans le même `rom_cleanup_workbench_settings.json`.

## Configuration : `redundanz_config.json`

Le fichier se trouve à côté du programme et est relu à chaque analyse. La langue, la priorité et les mots à supprimer se modifient le plus facilement dans la fenêtre avec `Paramètres...` (voir [Paramètres](#paramètres)). Dans le fichier lui-même, il suffit de changer l'ordre dans `region_priority` et d'enregistrer le fichier :

```json
"region_priority": ["Germany", "Europe", "USA", "none", "Japan", "Beta", "Proto"],
"delete_tags": ["Hack", "Hacks"],
```

Si le fichier contient une erreur, comme une entrée mal orthographiée, aucune analyse n'a lieu et rien n'est supprimé. Si le fichier ou une entrée manque, les valeurs par défaut du programme s'appliquent ; la priorité y est USA, Europe, Japan, none, Beta, les mots à supprimer sont Hack et Hacks, et la langue est l'anglais.

- `language` : la langue de la fenêtre, des remarques et de la sortie dans le terminal (voir ci-dessous).
- `region_priority` : régions et infos supplémentaires, la meilleure d'abord. `none` désigne les fichiers sans région connue ; les mots des autres langues (`keine`, `nessuna`, `ninguna`, `aucune`, `なし`) fonctionnent aussi. Une info supplémentaire comme `Beta` après `none` place ces fichiers en dernier (règle 6) ; `Beta` correspond aussi à `Beta 2`.
- `region_aliases` : autres orthographes d'une région, par exemple `Europa` pour `Europe`.
- `delete_tags` : les mots à supprimer, infos supplémentaires qui mènent toujours à la suppression (règle 2). `Hack` correspond aussi à `Hack 2` et `Hack by Someone`, mais pas à `Hacks` ni à `Hackers`, d'où `Hack` et `Hacks`.
- `part_tags` : parties d'une version, par exemple `Disc 1`.

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

1. Les fichiers vont ensemble si le texte avant la première parenthèse est identique. Les majuscules, espaces, tirets et tirets bas ne comptent pas, donc `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. Cela donne aussi `Title 1-2` = `Title 12`. De plus, `und` = `and` = `&` ainsi que `The Title` = `Title The` = `Title, The` = `Title` comptent comme égaux. Un `The` au milieu du nom compte en revanche.
2. Les fichiers avec un mot à supprimer (`delete_tags`, par défaut `Hack` et `Hacks`) sont toujours marqués, même s'il s'agit du seul fichier du jeu. `P` garde quand même un tel fichier.
3. Parmi les fichiers restants, celui qui a la meilleure entrée dans `region_priority` est conservé. Dans une même parenthèse, la meilleure entrée compte : avec `(USA, Japan)`, la meilleure des deux. D'une parenthèse à l'autre, la moins bonne compte : `(USA) (Beta)` compte comme `Beta` (règle 6).
4. Tous les fichiers d'une même version sont conservés ensemble, par exemple `(Disc 1)` et `(Disc 2)` ou `.cue` et `.bin`. Tout le reste est marqué.
5. Une région absente de `region_priority` compte comme `none`. Cela vaut aussi pour des indications comme `(Rev 1)`.
6. Les infos supplémentaires comme `Beta`, `Proto` ou `Alpha` s'écrivent dans `region_priority` après `none`. Les fichiers qui les portent viennent après tous les autres, même après les fichiers sans région, et dans l'ordre de la liste : avec `none, Beta, Proto`, une Beta vient avant un Proto. Ils ne sont conservés que s'il n'y a pas de meilleur fichier du jeu. Entre eux, la région compte de nouveau, puis la version de la règle 7, puis le numéro après l'info supplémentaire : `Beta 2` l'emporte sur `Beta 1`, et `Beta 1` sur `Beta` sans numéro. Les numéros sont comparés numériquement (`Beta 10` avant `Beta 9`). Le fichier perdant reçoit la remarque `Bêta plus ancienne`.
7. À priorité égale, le numéro de version le plus élevé l'emporte, comparé numériquement (`v1.10` avant `v1.9`). Sont reconnus entre parenthèses `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` et `Rev A` ; dans le nom du jeu seulement la forme `Title v1.1`, aussi avec `-` ou `_` à la place de l'espace. Un fichier sans version perd face à un fichier avec version. La région compte avant la version.
8. Ensuite le fichier avec le moins d'informations supplémentaires l'emporte, puis un fichier sans ZIP, puis l'ordre alphabétique. Le rapport affiche alors `Égalité`.
9. Un fichier plus petit que 1/4 du plus grand fichier du jeu est mis de côté avant les règles 3 à 8 et conservé : il peut s'agir d'un fichier d'état ou de sauvegarde. Il ne peut donc être ni supprimé ni évincer la vraie ROM, par exemple `1941.state` le fichier `1941.zip`. La colonne des remarques indique alors `Fichier d'état ou de sauvegarde présumé`, et le jeu est considéré comme problématique. Un tel jeu apparaît dans les trois vues, même si aucun de ses fichiers n'est marqué. Lorsque vous supprimez, le programme confirme comme légitimes tous les fichiers présumés restants : ils restent où ils sont, ne sont toujours jamais supprimés et n'apparaissent plus dans `Marquages problématiques` ni dans `Tous les marquages`, même après `F5` ou un nouveau démarrage. La confirmation indique leur nombre. Le programme les mémorise avec leur chemin et leur taille dans `rom_cleanup_workbench_settings.json` ; si la taille change, le fichier redevient suspect. Si rien n'est marqué, `Ctrl+L` propose de les confirmer sans rien supprimer. Les ZIP comptent avec leur taille décompressée. Cela ne vaut pas pour un petit fichier normal à côté d'un grand fichier normal de sa propre version, comme un `.cue` à côté de son `.bin`, ni pour les fichiers marqués à cause de `delete_tags` ou d'un ZIP endommagé. Avec `D`, vous pouvez quand même marquer le fichier à la main.

## Fichiers ZIP

Chaque fichier ZIP est lu entièrement, même s'il est le seul fichier d'un jeu. Son contenu est comparé aux autres fichiers du jeu à l'aide de SHA-256.

- **Même contenu qu'un fichier conservé :** le fichier ZIP est marqué et le rapport nomme le fichier au même contenu.
- **S'il reste un ZIP et un fichier normal après la sélection :** le ZIP est toujours marqué, même avec un contenu différent, s'il est le seul fichier contenant une partie comme `(Disc 1)` ou s'il est illisible.
- **Plusieurs ZIP de la même version au contenu différent :** tous sont conservés et le rapport le signale.
- **Marqué, mais le contenu n'apparaît dans aucun fichier conservé :** le rapport affiche `ATTENTION`. Le fichier reste marqué.
- **Pas de région ni de version dans le nom du ZIP :** l'information est tirée des fichiers du ZIP, à condition qu'ils aient le même nom de jeu.
- **ZIP endommagé ou chiffré :** le fichier est toujours marqué, même s'il est le seul fichier du jeu. Le contenu d'un ZIP chiffré n'est pas vérifié.
- **ZIP verrouillé ou méthode inconnue (par exemple Deflate64) :** cela ne dit rien de l'état du fichier. Sans fichier normal du jeu, il est conservé et signalé dans le rapport.

## Licence et clause de non-responsabilité

Copyright (C) 2026 Arved Retrogamer

Rom Cleanup Workbench est un logiciel libre : vous pouvez le redistribuer et/ou le modifier selon les termes de la GNU General Public License publiée par la Free Software Foundation, soit la version 3 de la licence, soit (à votre choix) toute version ultérieure. Le texte complet se trouve dans [LICENSE](<../LICENSE>) ; seul ce texte original anglais fait foi juridiquement.

**Utilisation à vos propres risques.** Le programme supprime des fichiers et aucune garantie d'aucune sorte n'est fournie ; quiconque l'utilise assume tous les risques qui en découlent. Nous recommandons de l'utiliser d'abord sur une copie de votre propre collection de ROM.

## Crédits

- Idée : Arved Retrogamer
- Programmation : Claude Code
