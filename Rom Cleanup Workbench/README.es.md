# Rom Cleanup Workbench

[English](README.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · **Español** · [Français](README.fr.md) · [日本語](README.ja.md)

**Guía del usuario con capturas de pantalla:** [PDF](<docs/Rom Cleanup Workbench - Guía del usuario.pdf>) · [Word](<docs/Rom Cleanup Workbench - Guía del usuario.docx>)

Encuentra archivos ROM duplicados en una carpeta según el nombre del juego y los elimina si se lo pides.
Necesita Python 3.10 o posterior. La ventana no necesita paquetes adicionales; la versión para terminal para Linux necesita Textual (consulta [Versión para terminal (Linux)](#versión-para-terminal-linux)).
El programa habla inglés, alemán, italiano, español, francés y japonés (consulta [Idioma](#idioma)).

**Importante:** no uses este programa con tus archivos ROM originales. Haz una copia de tu repositorio de ROM y usa el programa para limpiar solo esa copia.

## Instalación

### Windows

1. **Instalar Python:** descarga Python 3.10 o posterior de [python.org/downloads](https://www.python.org/downloads/) e instálalo. Si el instalador ofrece "Add python.exe to PATH", marca esa opción. `tkinter` para la ventana viene incluido. Después compruébalo en un terminal nuevo:

   ```powershell
   python --version
   ```

2. **Descargar el programa:** sin Git, lo más sencillo es un archivo ZIP. En el navegador: en la [página de GitHub](https://github.com/arved9926/rom-cleanup-workbench) elige el botón verde **Code** y luego **Download ZIP**, haz clic con el botón derecho en el archivo `rom-cleanup-workbench-main.zip` en el Explorador, elige **Extraer todo...** y cambia el nombre de la carpeta extraída `rom-cleanup-workbench-main` a `rom-cleanup-workbench`. O lo mismo en PowerShell:

   ```powershell
   Invoke-WebRequest https://github.com/arved9926/rom-cleanup-workbench/archive/refs/heads/main.zip -OutFile rom-cleanup-workbench.zip
   Expand-Archive rom-cleanup-workbench.zip -DestinationPath .
   Rename-Item rom-cleanup-workbench-main rom-cleanup-workbench
   cd "rom-cleanup-workbench\Rom Cleanup Workbench"
   ```

   Si tienes Git instalado, puedes clonar el repositorio en su lugar:

   ```powershell
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   cd "rom-cleanup-workbench\Rom Cleanup Workbench"
   ```

   El programa está en la carpeta `Rom Cleanup Workbench`. La ventana no necesita más paquetes. Solo quien quiera usar la versión para terminal en Windows instala además Textual:

   ```powershell
   python -m pip install textual==8.2.8
   ```

### Linux

1. **Instalar Python:** normalmente Python 3 ya está instalado (`python3 --version`). Si no, en Debian o Ubuntu:

   ```bash
   sudo apt install python3 python3-venv wget unzip
   ```

   El paquete `python3-tk` solo hace falta si en Linux con pantalla gráfica quieres usar la ventana en lugar de la versión para terminal.

2. **Descargar el programa:** sin Git, descárgalo de GitHub como archivo ZIP y descomprímelo:

   ```bash
   wget https://github.com/arved9926/rom-cleanup-workbench/archive/refs/heads/main.zip -O rom-cleanup-workbench.zip
   unzip rom-cleanup-workbench.zip
   mv rom-cleanup-workbench-main rom-cleanup-workbench
   ```

   Si tienes Git instalado (`sudo apt install git`), puedes clonar el repositorio en su lugar:

   ```bash
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   ```

3. **Instalar Textual en un entorno virtual:**

   ```bash
   cd "rom-cleanup-workbench/Rom Cleanup Workbench"
   python3 -m venv ~/venvs/rom-cleanup-workbench
   ~/venvs/rom-cleanup-workbench/bin/pip install textual==8.2.8
   ```

## Uso

### Windows

Abre un terminal (por ejemplo PowerShell) en la carpeta `Rom Cleanup Workbench` e inicia el programa con la carpeta de tus juegos:

```powershell
cd "rom-cleanup-workbench\Rom Cleanup Workbench"
python rom_cleanup_workbench.py "D:\Games"
```

Sin carpeta, la ventana la pide. Si quieres la versión para terminal, añade `--tui`.

### Linux

Entra en la carpeta `Rom Cleanup Workbench` e inicia el programa con el Python del entorno virtual y la carpeta de tus juegos:

```bash
cd "rom-cleanup-workbench/Rom Cleanup Workbench"
~/venvs/rom-cleanup-workbench/bin/python rom_cleanup_workbench.py ~/roms
```

Sin pantalla gráfica, por ejemplo por SSH, la versión para terminal se inicia sola. Con pantalla gráfica se abre la ventana (necesita `python3-tk`); con `--tui` se inicia igualmente la versión para terminal. Más en [Versión para terminal (Linux)](#versión-para-terminal-linux).

### Qué ocurre después

El programa abre la ventana de análisis y lo muestra todo allí; no escribe nada en el terminal ni pregunta nada allí. Las preguntas, los mensajes y la elección de carpeta también aparecen dentro de la ventana, en el idioma del programa, nunca como ventanas emergentes de Windows; Intro elige el botón preseleccionado y Esc responde No. Sin carpeta, la ventana pide la carpeta. Los archivos solo se eliminan tras la confirmación en la ventana. **Los archivos eliminados no van a la Papelera de reciclaje.**

| Opción | Efecto |
| --- | --- |
| `--review all` | abre la ventana con `Todas las marcas` en este inicio |
| `--review problems` | abre la ventana con `Marcas problemáticas` en este inicio |
| `--priority USA Europe Japan none` | fija la prioridad para esta ejecución |
| `--delete-tag Hack Hacks Proto` | fija las palabras para eliminar para esta ejecución |
| `--config file.json` | usa otra configuración |
| `--report-only` | sin ventana: solo muestra el informe en el terminal |
| `--yes` | sin ventana: elimina los archivos marcados sin preguntar |
| `--all` | con `--report-only`: muestra también los juegos sin archivos marcados |
| `--tui` | usa la versión para terminal en lugar de la ventana (automático en Linux sin pantalla gráfica) |
| `--ascii` | versión para terminal solo con caracteres ASCII (automático en la consola de Linux); implica `--tui` |

Las opciones de la línea de comandos y su ayuda (`--help`) están siempre en inglés.

Las pruebas se ejecutan con `python -m unittest`.

## Ventana de análisis

Como los archivos ZIP se tienen que descomprimir para obtener el tamaño, la suma SHA-256 y el nombre de su contenido, tras elegir una carpeta puede pasar un momento hasta que se muestren los resultados.

La fila verde superior muestra `Rom Cleanup Workbench` a la izquierda y la carpeta a la derecha; debajo, la ventana indica la prioridad vigente con su origen. La penúltima fila verde muestra el estado, durante el análisis por ejemplo `Analizando: 120 de 2007 archivos`. Mientras tanto aparece también una barra de progreso en el centro. La ventana muestra también los errores, por ejemplo en la configuración, y mientras el análisis falle no se puede eliminar nada. Al eliminar, la barra de progreso aparece en el centro y la fila verde muestra por ejemplo `Eliminando: 120 de 500 archivos`; la ventana no acepta entradas hasta que termina la eliminación. Después informa del resultado y quita de la lista los archivos eliminados sin volver a analizar la carpeta; los archivos que no se pudieron eliminar siguen marcados. `F5` vuelve a analizar la carpeta cuando lo quieras.

Si en toda la carpeta no hay nada marcado y ningún archivo es sospechoso de ser un archivo de estado o partida guardada, `Nada que hacer.` parpadea en el centro de la ventana.

Los tres botones de opción deciden qué muestra la lista:

- `Marcas problemáticas`: solo los juegos con un archivo marcado que se consideran problemáticos (predeterminada en el primer inicio)
- `Todas las marcas`: todos los juegos con un archivo marcado
- `Todos los archivos ROM`: todos los juegos. Sus archivos se pueden marcar entonces también con `x`, y aparecen también los casos problemáticos sin archivo marcado, como un ZIP no legible.

La ventana recuerda la última vista elegida y los archivos de estado o partidas guardadas confirmados (regla 9) en `rom_cleanup_workbench_settings.json` junto al programa.

| Tecla | Efecto |
| --- | --- |
| Flechas | elige una fila, con Mayús varias (por ejemplo todos los discos de un juego) |
| `Tab` / `Mayús+Tab` | va al juego siguiente / anterior; se elige el primer archivo del juego |
| `x` | marca el archivo para eliminar; pasa al final de su juego |
| `k` | conserva el archivo; pasa al lugar que le dan las reglas |
| `1` `2` `3` | las vistas `Marcas problemáticas`, `Todas las marcas`, `Todos los archivos ROM` |
| `Ctrl` + rueda del ratón | agranda o reduce la letra (de 8 a 32 pt, vale hasta cerrar la ventana) |
| `s` | como el botón `Ajustes...`: muestra u oculta los ajustes de idioma, prioridad y palabras para eliminar (consulta [Ajustes](#ajustes)) |
| `/` | va al campo de filtro |
| `Enter` | como el botón `Ejecutar...`: elimina tras una confirmación y confirma los posibles archivos de estado o partidas guardadas (regla 9) |
| `f` | elige otra carpeta, dentro de la ventana en lugar de la lista: abre carpetas con doble clic o con la flecha, o escribe una ruta en `Ruta:`, y luego `Seleccionar` o `Intro`; `Cancelar` o `Esc` conservan la carpeta actual |
| `r` o `F5` | analiza de nuevo, también vuelve a leer la configuración |
| `c` o `F1` | muestra los créditos |
| `q` o `Esc` | cierra sin eliminar nada; tras cambios a mano el programa pregunta antes |

Unas líneas horizontales separan los juegos, y uno de cada dos juegos tiene fondo gris oscuro. La columna `Tamaño` muestra el tamaño de cada archivo en KB, redondeado hacia arriba como en el Explorador de Windows (`1.234 KB`); `?` significa que no se pudo leer el tamaño. El tamaño se lee durante el análisis. Los archivos conservados aparecen en negrita bajo `Conservar:`, los que se van a eliminar en letra normal bajo `Marcado para eliminar`. La ventana muestra texto blanco en Lucida Sans Typewriter 11 pt sobre fondo negro. Si la fuente no está instalada, Windows elige en silencio una sustituta. Los archivos movidos a mano tienen fondo marrón y llevan la nota `A mano`; mientras la fila está elegida, aparece azul. Las notas del programa no cambian, aunque se refieran a un archivo que has movido.

`Marcas problemáticas` oculta los juegos sin problemas. **Sus archivos marcados también se eliminan cuando eliminas**; la confirmación indica su número. Los juegos que has cambiado a mano siempre siguen visibles, salvo que el filtro los oculte.

### Filtro

El campo de filtro a la izquierda de la fila inferior limita la vista actual a los juegos con un nombre de archivo que contiene el patrón. Un juego se muestra completo si uno de sus archivos coincide. La lista se actualiza poco después de escribir; no se lee el contenido de los archivos.

- `*` representa cualquier número de caracteres, `?` exactamente uno. Todos los demás caracteres, incluidos `[` y `]`, cuentan literalmente, y no se distingue entre mayúsculas y minúsculas.
- El patrón puede aparecer en cualquier parte del nombre: `Beta`, `*Beta*` y `Mario?2` encuentran todos también `Super Mario 2 (Beta).nes`. Por tanto, `S*` encuentra cualquier nombre que contenga una `S`, no solo los que empiezan por ella.
- `Intro`, `Tab` y la flecha abajo vuelven a la lista; `Esc` vacía el filtro y vuelve a la lista.
- Mientras el cursor está en el campo, las teclas solo escriben allí: `x`, `k`, `Enter`, `f`, `r`, `F5` y `Esc` no ejecutan sus funciones de la lista.
- El filtro sigue activo después de `F5`, después de eliminar y después de elegir otra carpeta. No se guarda.

**El filtro solo cambia la visualización. Los archivos marcados ocultos por el filtro también se eliminan cuando eliminas**; la confirmación indica su número.

### Ajustes

El botón `Ajustes...` de la fila inferior, o `s`, muestra los cambios más frecuentes de `redundanz_config.json` en la ventana principal, en lugar de la lista de archivos. `Guardar` o `Cancelar`, `Esc`, `Ctrl+E` u otro clic en `Ajustes...` devuelven la lista. Mientras tanto el filtro, las vistas, `Ejecutar...`, `Analizar de nuevo` y `Carpeta...` están bloqueados, y `x`, `k` y `Enter` no hacen nada, para que no pueda cambiar nada en la lista oculta.

- **Idioma:** Establece el idioma de la interfaz. Elige entre los seis idiomas. Un idioma nuevo se aplica a partir del próximo inicio del programa.
- **Prioridad:** Establece qué versiones regionales tienen preferencia sobre las demás. La mejor región arriba; la información adicional como `Beta` o `Proto` va tras `none`, para que esos archivos queden al final (regla 6). Elige una entrada y muévela con `Subir` y `Bajar`, quítala con `Quitar` o con la tecla `Supr`, y añade una nueva con el campo bajo la lista y `Añadir` (o `Intro`).
- **Palabras para eliminar:** Establecen qué versiones de un juego se eliminan siempre. Separadas por comas, por ejemplo `Hack, Hacks`. Los archivos que las contienen se marcan para eliminar (regla 2).

`Guardar` escribe el archivo y vuelve a analizar la carpeta si la prioridad o las palabras han cambiado; si has cambiado marcas a mano, el programa pregunta antes, porque esos cambios se pierden. Todas las demás entradas del archivo se quedan como están. Los valores incorrectos, como una lista de regiones vacía o la misma región dos veces, se notifican, no se escribe nada y los ajustes siguen abiertos. Si el archivo no se puede leer, los ajustes no se abren, para que no puedan sobrescribir entradas que no conocen. Con `--config`, los ajustes editan ese archivo; con `--priority`, para esta ejecución sigue valiendo la prioridad indicada allí.

Un juego se considera problemático si

- no se conservaría ninguno de sus archivos,
- el contenido de un ZIP marcado no aparece en ningún otro sitio (`AVISO`),
- un ZIP está dañado, cifrado o no es legible,
- un archivo se conserva como posible archivo de estado o partida guardada (regla 9),
- las reglas solo decidieron por un `Empate`,
- varios ZIP de la misma versión tienen contenido distinto,
- los nombres de archivo escriben el juego de forma distinta (`Title 1-2` y `Title 12`),
- un archivo marcado tiene un tipo de archivo distinto al de los conservados (`.nes` y `.sfc`).

La ventana usa `tkinter`, que forma parte de la instalación habitual de Python en Windows. Si falta, el programa lo notifica y no elimina nada.

## Después de la limpieza automática

Incluso después de la limpieza automática pueden quedar versiones redundantes de un juego. La forma más sencilla de encontrarlas es el filtro (tecla `/` y luego el nombre del juego). Después puedes marcar los archivos que aún hay que eliminar.

## Versión para terminal (Linux)

El mismo programa funciona también en un terminal de texto, por ejemplo por SSH (PuTTY, MobaXterm), en `tmux` o en la consola de Linux. Muestra la misma lista, aplica las mismas reglas y comparte con la ventana `redundanz_config.json`, `rom_cleanup_workbench_settings.json` y `translations.py`.

En Linux se inicia por sí sola cuando no hay pantalla gráfica (ni `DISPLAY` ni `WAYLAND_DISPLAY` están definidas, como por SSH). `--tui` la inicia en cualquier otro lugar, también en Windows; úsalo donde haya una pantalla gráfica pero quieras el terminal, por ejemplo en MobaXterm o en WSL.

Necesita [Textual](https://textual.textualize.io/) (probado con 8.2.8). Cómo instalarlo e iniciar el programa se describe en [Instalación](#instalación) y [Uso](#uso).

Sin Textual, el programa lo dice y no elimina nada. La pantalla tiene las filas de la ventana de arriba abajo: la fila de título verde con la carpeta, una fila de ayuda, la prioridad, la lista, el campo de filtro, las tres vistas y la fila de estado verde. En la lista, cada juego empieza con su nombre en negrita, seguido de guiones hasta el borde derecho; una nota como `Distintas grafías del nombre` aparece en esa línea. En un terminal estrecho, como las 80 columnas de PuTTY, los nombres de archivo y las notas largas pasan a la línea siguiente dentro de su columna en lugar de salirse de la pantalla. `Nada que hacer.` parpadea con el parpadeo propio del terminal; en PuTTY puede ser necesario activar antes el texto parpadeante. Las preguntas y los mensajes aparecen en un marco sobre la lista, con botones en el idioma del programa; `No` está preseleccionado.

La fila de ayuda muestra las teclas como `tecla:acción`, por ejemplo `x:eliminar  k:conservar`. La ventana y la versión para terminal tienen las mismas teclas.

| Tecla | Efecto |
| --- | --- |
| Flechas | elige una fila, con Mayús varias |
| `Tab` / `Mayús+Tab` | juego siguiente / anterior; se elige su primer archivo |
| `x` / `k` | marca los archivos elegidos para eliminar / los conserva |
| `1` `2` `3` | las vistas `Marcas problemáticas`, `Todas las marcas`, `Todos los archivos ROM` |
| `/` | va al campo de filtro |
| `Intro` | ejecutar: elimina tras una confirmación (como `Ejecutar...`) |
| `f` | elige otra carpeta, dentro de la ventana en lugar de la lista: abre carpetas con doble clic o con la flecha, o escribe una ruta en `Ruta:`, y luego `Seleccionar` o `Intro`; `Cancelar` o `Esc` conservan la carpeta actual |
| `s` | ajustes: `Mayús+Arriba`/`Mayús+Abajo` mueven una región, `Supr` la quita, `Ctrl+S` guarda, `Esc` cancela |
| `r` o `F5` | analiza de nuevo, también vuelve a leer la configuración |
| `c` o `F1` | muestra los créditos |
| `q` o `Esc` | cierra sin eliminar nada; tras cambios a mano el programa pregunta antes |
| En una pregunta | `Izquierda`/`Derecha` eligen un botón, `Intro` lo pulsa, `Esc` responde `No` |

El ratón también funciona: un clic elige una fila, la rueda desplaza, y las vistas y los botones se pueden pulsar. Las letras escritas en un campo se quedan en el campo, aunque se escriban rápido o se peguen: una `x` en el filtro nunca marca un archivo.

**Colores y caracteres.** Con 256 colores o más, la versión para terminal usa los colores de la ventana, pero negro detrás de cada juego (sin rayas). Donde el terminal solo tiene 16 colores (`TERM=xterm`, `TERM=linux`), pasa a colores ANSI sencillos: selección azul, filas de título y de estado verdes, filas marrones cambiadas a mano. En la consola de Linux, en terminales como `vt100` y cuando la configuración regional indica un juego de caracteres distinto de UTF-8 (por ejemplo `en_US` o `de_DE.ISO-8859-1`), dibuja solo caracteres ASCII: vistas como `(*)`, marcos hechos de `+`, `-` y `|`. `--ascii` lo fuerza. PuTTY se identifica como `xterm` (16 colores); para los colores de la ventana, pon *Connection → Data → Terminal-type string* en `xterm-256color`. Los nombres de archivo y los textos en otras escrituras, como el japonés, siguen necesitando un terminal y una fuente que puedan mostrarlos.

Diferencias con la ventana: no hay zoom de letra, porque la fuente pertenece al terminal (en PuTTY: *Window → Appearance*); y los juegos no van a rayas, sino que empiezan con una línea de guiones. Con 16 colores, las filas verdes tienen texto negro, que sigue siendo legible sobre un verde claro. Al eliminar, la versión para terminal elimina en segundo plano y muestra la barra de progreso; todas las teclas están bloqueadas hasta que termina. La ventana y la versión para terminal guardan su vista y las partidas guardadas confirmadas en el mismo `rom_cleanup_workbench_settings.json`.

## Configuración: `redundanz_config.json`

El archivo está junto al programa y se vuelve a leer en cada análisis. Idioma, prioridad y palabras para eliminar se cambian más fácilmente en la ventana con `Ajustes...` (consulta [Ajustes](#ajustes)). En el propio archivo basta con cambiar el orden en `region_priority` y guardar el archivo:

```json
"region_priority": ["USA", "Europe", "none", "Japan", "Beta"],
"delete_tags": [],
```

Si el archivo contiene un error, por ejemplo una entrada mal escrita, no se realiza ningún análisis y no se elimina nada. Así es el archivo incluido: el idioma es el inglés, la prioridad USA, Europe, none, Japan, Beta, y no hay palabras para eliminar. Por tanto, los archivos sin región van antes que los japoneses. Si falta el archivo o una entrada, se aplican los mismos valores predeterminados.

- `language`: el idioma de la ventana, de las notas y de la salida en el terminal (ver abajo).
- `region_priority`: regiones e información adicional, la mejor primero. `none` representa los archivos sin región conocida; las palabras de los otros idiomas (`keine`, `nessuna`, `ninguna`, `aucune`, `なし`) también sirven. La información adicional como `Beta` tras `none` deja esos archivos al final (regla 6); `Beta` también coincide con `Beta 2`.
- `region_aliases`: otras grafías de una región, por ejemplo `Europa` para `Europe`.
- `delete_tags`: las palabras para eliminar, información adicional que siempre lleva a eliminar (regla 2). De forma predeterminada la lista está vacía. `Hack` también coincide con `Hack 2` y `Hack by Someone`, pero no con `Hacks` ni `Hackers`; quien quiera eliminar los hacks introduce por tanto `Hack` y `Hacks`.
- `part_tags`: partes de una versión, por ejemplo `Disc 1`.

Los archivos antiguos pueden contener todavía `low_priority_tags`, información adicional con la prioridad más baja. El programa lee sus entradas como si estuvieran al final de `region_priority`, tras `none`; los ajustes las mueven allí al guardar, y la entrada desaparece.

### Idioma

```json
"language": "de",
```

| Valor | Idioma |
| --- | --- |
| `en` | inglés (predeterminado) |
| `de` | alemán |
| `it` | italiano |
| `es` | español |
| `fr` | francés |
| `ja` | japonés |

El idioma vale para la ventana, las notas y la salida en el terminal, y el programa lo lee al iniciarse: después de cambiarlo, cierra el programa y vuelve a iniciarlo. `F5` no cambia el idioma. Un valor desconocido cuenta como error en la configuración, como se describe arriba. Las reglas deciden igual en todos los idiomas. Los textos están en `translations.py`.

Para el japonés, Windows muestra los caracteres con una fuente sustituta, porque Lucida Sans Typewriter no tiene caracteres japoneses.

## Reglas

El programa ignora por completo algunos archivos: no aparecen en ningún sitio y nunca se eliminan.

- Archivos cuyo nombre empieza por `gamelist`, sin distinguir mayúsculas y minúsculas. No son archivos ROM.
- Archivos ocultos: nombres que empiezan por un punto, como `.xxx` o `.DS_Store`, y archivos con el atributo de Windows «oculto».

1. Los archivos van juntos si el texto anterior al primer paréntesis es igual. Mayúsculas, espacios, guiones y guiones bajos no cuentan, así que `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. Por eso también `Title 1-2` = `Title 12`. Además cuentan como iguales `und` = `and` = `&` así como `The Title` = `Title The` = `Title, The` = `Title`. Un `The` en medio del nombre sí cuenta.
2. Los archivos con una palabra para eliminar (`delete_tags`, ninguna de forma predeterminada, por ejemplo `Hack` y `Hacks`) se marcan siempre, aunque sean el único archivo del juego. `k` conserva ese archivo de todos modos.
3. De los archivos restantes se conserva el que tiene la mejor entrada en `region_priority`. Dentro de un paréntesis cuenta la mejor entrada: con `(USA, Japan)`, la mejor de las dos. Entre paréntesis distintos cuenta la peor: `(USA) (Beta)` cuenta como `Beta` (regla 6).
4. Todos los archivos de la misma versión se conservan juntos, por ejemplo `(Disc 1)` y `(Disc 2)` o `.cue` y `.bin`. Todo lo demás se marca.
5. Una región que no está en `region_priority` cuenta como `none`. Esto vale también para indicaciones como `(Rev 1)`.
6. La información adicional como `Beta`, `Proto` o `Alpha` se escribe en `region_priority` tras `none`. Los archivos que la llevan van después de todos los demás, incluso después de los archivos sin región, y en el orden de la lista: con `none, Beta, Proto`, una Beta va antes que un Proto. Solo se conservan si no hay un archivo mejor del juego. Entre ellos cuenta de nuevo la región, luego la versión de la regla 7 y luego el número tras la información adicional: `Beta 2` gana a `Beta 1`, y `Beta 1` a `Beta` sin número. Los números se comparan numéricamente (`Beta 10` antes que `Beta 9`). El archivo que pierde recibe la nota `Beta anterior`.
7. Con la misma prioridad gana el número de versión más alto, comparado numéricamente (`v1.10` antes que `v1.9`). Entre paréntesis se reconocen `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` y `Rev A`; en el nombre del juego solo la forma `Title v1.1`, también con `-` o `_` en lugar del espacio. Un archivo sin versión pierde frente a uno con versión. La región cuenta antes que la versión.
8. Después gana el archivo con menos información adicional, luego un archivo sin ZIP y luego el orden alfabético. El informe muestra entonces `Empate`.
9. Un archivo más pequeño que 1/4 del archivo más grande del juego se aparta antes de las reglas 3 a 8 y se conserva: puede ser un archivo de estado o una partida guardada. Por eso no puede eliminarse ni desplazar la ROM real, por ejemplo `1941.state` al archivo `1941.zip`. La columna de notas dice entonces `Posible archivo de estado o partida guardada`, y el juego se considera problemático. Un juego así aparece en las tres vistas, aunque ninguno de sus archivos esté marcado. Al eliminar, el programa confirma como legítimos todos los posibles archivos que quedan: se quedan donde están, siguen sin eliminarse nunca y ya no aparecen en `Marcas problemáticas` ni en `Todas las marcas`, tampoco después de `F5` o de un nuevo inicio. La confirmación indica su número. El programa los recuerda con ruta y tamaño en `rom_cleanup_workbench_settings.json`; si el tamaño cambia, el archivo vuelve a ser sospechoso. Si no hay nada marcado, `Enter` ofrece confirmarlos sin eliminar nada. Los ZIP cuentan con su tamaño descomprimido. Esto no vale para un archivo normal pequeño junto a un archivo normal grande de su misma versión, como un `.cue` junto a su `.bin`, ni para los archivos marcados por `delete_tags` o por un ZIP dañado. Con `x` puedes marcar el archivo a mano de todos modos.

## Archivos ZIP

Cada archivo ZIP se lee completo, aunque sea el único archivo de un juego. Su contenido se compara con los demás archivos del juego mediante SHA-256.

- **Mismo contenido que un archivo conservado:** el archivo ZIP se marca y el informe indica el archivo con el mismo contenido.
- **Si tras la selección quedan un ZIP y un archivo normal:** el ZIP siempre se marca, incluso con contenido distinto, si es el único archivo que contiene una parte como `(Disc 1)` o si no es legible.
- **Varios ZIP de la misma versión con contenido distinto:** se conservan todos y el informe lo indica.
- **Marcado, pero el contenido no aparece en ningún archivo conservado:** el informe muestra `AVISO`. El archivo sigue marcado.
- **Sin región ni versión en el nombre del ZIP:** el dato se toma de los archivos del ZIP, siempre que tengan el mismo nombre de juego.
- **ZIP dañado o cifrado:** el archivo siempre se marca, aunque sea el único archivo del juego. El contenido de un ZIP cifrado no se comprueba.
- **ZIP bloqueado o método desconocido (por ejemplo Deflate64):** esto no dice nada sobre el estado del archivo. Sin un archivo normal del juego, se conserva y se indica en el informe.

## Seguir desarrollándolo con Claude Code

El programa es software libre: puedes clonar el repositorio y seguir desarrollándolo con [Claude Code](https://claude.com/claude-code), sin programar tú mismo. Así se escribió también.

1. Instala Claude Code. Necesita una suscripción a Claude o una cuenta de la API de Claude. En Windows, en PowerShell:

   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```

   En Linux:

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

2. Clona el repositorio e inicia Claude Code en él:

   ```bash
   git clone https://github.com/arved9926/rom-cleanup-workbench.git
   cd rom-cleanup-workbench
   claude
   ```

3. Describe con tus palabras qué debe cambiar, por ejemplo "Añade una opción que muestre solo los archivos ZIP". Claude Code lee el código, propone cambios y pregunta antes de cambiar archivos o ejecutar comandos. Después haz que ejecute las pruebas (`python -m unittest` en la carpeta `Rom Cleanup Workbench`) y prueba el cambio en una copia de tu colección.

Los planes de cambios anteriores están en `docs/`. Quien distribuya sus cambios debe publicarlos también bajo la GPL.

## Licencia y exención de responsabilidad

Copyright (C) 2026 M. Kärcher

Rom Cleanup Workbench es software libre: puedes redistribuirlo y/o modificarlo según los términos de la GNU General Public License publicada por la Free Software Foundation, ya sea la versión 3 de la licencia o (a tu elección) cualquier versión posterior. El texto completo está en [LICENSE](<../LICENSE>); solo este texto original en inglés tiene validez legal.

**Úselo bajo su propia responsabilidad.** El programa elimina archivos y no hay ninguna garantía; quien lo usa asume todos los riesgos que conlleva. Recomendamos encarecidamente usarlo solo con una copia de su propia colección de ROM.

## Créditos

- Idea: M. Kärcher
- Programación: Claude Code
