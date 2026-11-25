# Rom Cleanup Workbench

[English](README.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · **Español** · [Français](README.fr.md) · [日本語](README.ja.md)

**Guía del usuario con capturas de pantalla:** [PDF](<docs/Rom Cleanup Workbench - Guía del usuario.pdf>) · [Word](<docs/Rom Cleanup Workbench - Guía del usuario.docx>)


Encuentra archivos ROM duplicados en una carpeta según el nombre del juego y los elimina si se lo pides.
Necesita Python 3.10 o posterior. La ventana no necesita paquetes adicionales; la versión para terminal para Linux necesita Textual (consulta [Versión para terminal (Linux)](#versión-para-terminal-linux)).
El programa habla inglés, alemán, italiano, español, francés y japonés (consulta [Idioma](#idioma)).

**Importante:** no uses este programa con tus archivos ROM originales. Haz una copia de tu repositorio de ROM y usa el programa para limpiar solo esa copia.

## Instalación

No necesitas una cuenta de GitHub. Cada comando está en su propio recuadro; escríbelo así y pulsa Intro.

### Windows

Escribe todos los comandos en PowerShell.

1. **Comprobar si Python está instalado:**

   ```powershell
   python --version
   ```

   - **Aparece `Python 3.10` o superior:** Python está instalado, sigue con el paso 2.

   - **Aparece un error o una versión más antigua:** descarga Python 3.10 o posterior desde [python.org/downloads](https://www.python.org/downloads/) e instálalo. Si el instalador ofrece “Add python.exe to PATH”, marca esa opción. `tkinter` para la ventana viene incluido. Después abre una nueva ventana de PowerShell y repite la comprobación.

2. **Comprobar si Git está instalado:**

   ```powershell
   git --version
   ```

   - **Aparece un número de versión, por ejemplo `git version 2.47.0`:** descarga el programa con Git:

     ```powershell
     git clone https://github.com/arved9926/rom-cleanup-workbench.git
     ```

   - **Aparece un error:** descarga el programa como archivo ZIP. En el navegador, en la [página de GitHub](https://github.com/arved9926/rom-cleanup-workbench), elige **Code** y luego **Download ZIP**; después descomprime el archivo con el botón derecho del ratón (**Extraer todo...**) y cambia el nombre de la carpeta `rom-cleanup-workbench-main` a `rom-cleanup-workbench`. O en PowerShell, comando a comando:

     ```powershell
     Invoke-WebRequest https://github.com/arved9926/rom-cleanup-workbench/archive/refs/heads/main.zip -OutFile rom-cleanup-workbench.zip
     ```

     ```powershell
     Expand-Archive rom-cleanup-workbench.zip -DestinationPath .
     ```

     ```powershell
     Rename-Item rom-cleanup-workbench-main rom-cleanup-workbench
     ```

3. **Entrar en la carpeta del programa:**

   ```powershell
   cd "rom-cleanup-workbench\Rom Cleanup Workbench"
   ```

   La ventana no necesita más paquetes. Solo quien quiera usar la versión para terminal en Windows instala además Textual:

   ```powershell
   python -m pip install textual==8.2.8
   ```

### Linux

Escribe todos los comandos en un terminal. Los ejemplos son para Debian y Ubuntu.

1. **Comprobar si Python está instalado:**

   ```bash
   python3 --version
   ```

   - **Aparece `Python 3.10` o superior:** Python está instalado, sigue con el paso 2.

   - **Aparece un error o una versión más antigua:** instala Python:

     ```bash
     sudo apt install python3 python3-venv
     ```

   El paquete `python3-tk` solo hace falta si en Linux con pantalla gráfica quieres usar la ventana en lugar de la versión para terminal.

2. **Comprobar si Git está instalado:**

   ```bash
   git --version
   ```

   - **Aparece un número de versión:** descarga el programa con Git:

     ```bash
     git clone https://github.com/arved9926/rom-cleanup-workbench.git
     ```

   - **Aparece un error:** descarga el programa como archivo ZIP y descomprímelo, comando a comando:

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

3. **Entrar en la carpeta del programa:**

   ```bash
   cd "rom-cleanup-workbench/Rom Cleanup Workbench"
   ```

4. **Instalar Textual en un entorno virtual:**

   ```bash
   python3 -m venv ~/venvs/rom-cleanup-workbench
   ```

   ```bash
   ~/venvs/rom-cleanup-workbench/bin/pip install textual==8.2.8
   ```

## Uso

### Windows

Abre un terminal (por ejemplo PowerShell) en la carpeta `Rom Cleanup Workbench` e inicia el programa con la carpeta de tus juegos:

```powershell
cd "rom-cleanup-workbench\Rom Cleanup Workbench"
```

```powershell
python rom_cleanup_workbench.py "D:\Games"
```

Sin carpeta, el programa vuelve a abrir la última carpeta elegida, una carpeta `roms` con su vista general, cualquier otra directamente; la primera vez la ventana pide una. Para la versión de terminal se añade `--tui`.

### Linux

Entra en la carpeta `Rom Cleanup Workbench` e inicia el programa con el Python del entorno virtual y la carpeta de tus juegos:

```bash
cd "rom-cleanup-workbench/Rom Cleanup Workbench"
```

```bash
~/venvs/rom-cleanup-workbench/bin/python rom_cleanup_workbench.py ~/roms
```

Sin pantalla gráfica, por ejemplo por SSH, la versión para terminal se inicia sola. Con pantalla gráfica se abre la ventana (necesita `python3-tk`); con `--tui` se inicia igualmente la versión para terminal. Más en [Versión para terminal (Linux)](#versión-para-terminal-linux).

### Qué ocurre después

El programa abre la ventana de análisis y lo muestra todo allí; no escribe nada en el terminal ni pregunta nada allí. Las preguntas, los mensajes y la elección de carpeta también aparecen dentro de la ventana, en el idioma del programa, nunca como ventanas emergentes de Windows; Intro elige el botón preseleccionado y Esc responde No. Sin carpeta, la ventana pide la carpeta. Los archivos solo se eliminan tras la confirmación en la ventana. **Los archivos eliminados no van a la Papelera de reciclaje.**

| Opción | Efecto |
| --- | --- |
| `--review all` | abre la ventana con `Para eliminar` en este inicio |
| `--review problems` | abre la ventana con `Por revisar` en este inicio |
| `--priority USA Europe Japan none` | fija la prioridad para esta ejecución |
| `--delete-tag Hack Hacks Proto` | fija las palabras para eliminar para esta ejecución |
| `--config file.json` | usa otra configuración |
| `--report-only` | sin ventana: solo muestra el informe en el terminal |
| `--yes` | sin ventana: elimina los archivos marcados sin preguntar |
| `--scan-all` | sin ventana: analiza todas las carpetas de plataforma de la carpeta `roms` indicada y las guarda en su base de datos; no elimina nada |
| `--deep-scan` | con `--scan-all`: análisis profundo, vuelve a leer cada archivo en lugar de solo los nuevos y cambiados (`--full` sigue funcionando) |
| `--write-gamelists` | sin ventana: escribe el `gamelist.xml` de cada plataforma de la carpeta `roms` indicada a partir de su base de datos; cada archivo anterior queda como copia |
| `--all` | con `--report-only`: muestra también los juegos sin archivos marcados |
| `--tui` | usa la versión para terminal en lugar de la ventana (automático en Linux sin pantalla gráfica) |
| `--ascii` | versión para terminal solo con caracteres ASCII (automático en la consola de Linux); implica `--tui` |

Las opciones de la línea de comandos y su ayuda (`--help`) están siempre en inglés.

Las pruebas se ejecutan con `python -m unittest`.

## La colección: muchas plataformas y la base de datos

Normalmente los juegos están en una carpeta común, separados por plataforma, por ejemplo `roms/nes`, `roms/snes`, `roms/n64`. Si eliges esta carpeta `roms`, el programa muestra la **vista general** de todas las plataformas. Desde entonces empieza siempre con la última carpeta elegida, es decir, con su vista general en el caso de una carpeta `roms`. Cuenta como carpeta `roms` una carpeta que ya tiene una base de datos o que no contiene archivos ROM, pero sí subcarpetas. Los archivos de acompañamiento como `info.txt`, imágenes o PDF no cuentan como archivos ROM. Cualquier otra carpeta se analiza sola como antes, sin base de datos.

**La base de datos.** La primera vez, el programa crea en la carpeta `roms` la carpeta oculta `.rom_cleanup_workbench` con una base de datos SQLite. Es lo único que escribe en tu colección. Guarda los resultados de cada análisis: archivos, tamaños, fechas de modificación, el contenido de los ZIP con sumas de comprobación. A partir de ellos el programa recalcula las decisiones en un momento al abrir una plataforma. Por eso los ajustes cambiados se aplican enseguida, sin un nuevo análisis. También guarda los cambios a mano (`k`/`x`), los archivos de estado y de partida confirmados y los ajustes propios de cada plataforma. Lo que cuenta es la carpeta: si una carpeta de plataforma ya no existe, la vista general borra al abrirse todo lo que la base de datos sabía de ella, incluidos los ajustes propios y `sin juegos`. Una carpeta nueva con el mismo nombre empieza entonces de cero. Si la propia carpeta `roms` no es accesible, por ejemplo una unidad de red sin conexión, no se borra nada.

**La vista general** muestra por plataforma: archivos, juegos, archivos marcados para eliminar, juegos problemáticos, juegos eliminados por completo (de los que no quedaría ningún archivo), el último análisis y el estado (`sin analizar`, `al día` o `cambiada` si desde entonces se añadieron, quitaron o cambiaron archivos), con el total debajo. Una línea separa el total de las plataformas; el estado `cambiada` aparece en amarillo (en la ventana toda la fila). Un clic en el encabezado `Plataforma`, `Archivos`, `Juegos`, `Para eliminar`, `Problemáticos`, `Eliminados por completo`, `Info` o `Problemas gamelist` ordena por él, un segundo clic al revés; una flecha muestra la dirección, el total queda abajo, las plataformas sin números van al final y la elección queda guardada.

| Botón | Tecla | Efecto |
| --- | --- | --- |
| `Abrir` | `Intro` | abre la plataforma resaltada en la lista habitual (también doble clic) |
| `Analizar` | `r` o `F5` | analiza la plataforma resaltada y la abre |
| `Analizar todo` | `a` | analiza todas las plataformas una tras otra; cada una se guarda enseguida y sus números aparecen de inmediato en el resumen; `Cancelar` conserva las terminadas; no elimina nada |
| `Análisis profundo` | `d` | interruptor (punto rojo) para Analizar y Analizar todo: vuelve a leer cada archivo en lugar de solo los nuevos y cambiados |
| `Ocultar vacías` | `h` | interruptor (punto rojo): oculta las carpetas sin archivo de juego, por ejemplo `bios` o una carpeta solo con `info.txt`; los archivos adjuntos no cuentan como archivos de juego; la elección se recuerda |
| `Carpeta...` | `f` | elige otra carpeta `roms` |
| | `n` | marca la carpeta resaltada como `sin juegos` o lo deshace (ver más abajo) |
| | `w` | escribe el `gamelist.xml` de la plataforma resaltada a partir de la base de datos (tras una pregunta) |
| | `m` | elimina los archivos multimedia sin uso de la plataforma resaltada (tras una pregunta, ver más abajo) |
| | `q` o `Esc` | cierra el programa |

Las teclas son las mismas en la ventana y en la versión para terminal. La línea sobre la tabla nombra las principales; `F1` o `?` las muestra todas.

**Analizar.** Un análisis suele ser rápido: solo lee los archivos nuevos y cambiados (reconocidos por nombre, tamaño y fecha de modificación) y toma todo lo demás de la base de datos. Con `Análisis profundo` se vuelve a leer cada archivo. `F5` en la lista analiza rápidamente la plataforma abierta. Ejecutar registra enseguida los archivos eliminados y renombrados; después no hace falta un nuevo análisis.

**Volver al resumen**: en la lista con `Esc`, `q` o el botón `Resumen`, en la versión para terminal también con `o`. `Esc` o `q` en el resumen cierra el programa; para salir del todo se pulsa, pues, dos veces.

**El gamelist.xml.** Si una carpeta de plataforma contiene un `gamelist.xml` (EmulationStation, RetroPie, Batocera, ES-DE, ARRM), el análisis lo lee y pasa a la base de datos lo que se puede comprobar: nombre, descripción, valoración, fecha, desarrollador, editor, género, jugadores, región, favorito, tiempo de juego y las referencias a archivos multimedia como imágenes y vídeos, por categoría (`wheel` y `logo` siguen separados aunque apunten al mismo archivo). Todos los demás campos se conservan sin cambios. El número de `<genreid>` (por ejemplo `1538`) viene de la lista de géneros de Recalbox: género principal × 256 más subgénero, así que `1538` = `0x0602` = Deportes, subgénero 2 «Simulación deportiva»; herramientas como ARRM lo escriben al hacer scraping. La vista del juego muestra el número con su nombre, por ejemplo «1538 – Simulación deportiva (Deportes)». No tiene nada que ver con los números de género de ScreenScraper. Si una plataforma tiene números de género, la lista muestra una columna `Género`. Un clic en su encabezado ordena los juegos por género (en el orden de la lista de Recalbox, los juegos sin género al final, por nombre dentro de un género), un segundo clic o un clic en `Archivo` de nuevo por nombre; la elección queda guardada. En el formulario de edición, `Género (lista Recalbox)` elige el número entre todos los géneros de Recalbox; el campo de texto `Género` sigue libre al lado. Un número elegido a mano se mantiene en una nueva importación. No se pasan, y cuentan como problemas, las entradas cuya ROM no está en la carpeta de la plataforma y las referencias a archivos que no existen. Las rutas de otro ordenador como `/home/pi/RetroPie/roms/nes/…` se reescriben a la carpeta de la plataforma y cuentan como avisos. El archivo solo se lee si ha cambiado; un `gamelist.xml` cambiado pone el estado en `cambiada`. El archivo en sí no se modifica. El almacén es la base de datos, no el `gamelist.xml`: si se borra el archivo, la información se queda; si en cambio desaparece una ROM o un archivo multimedia de la carpeta, desaparece también de la base de datos, y una ROM eliminada se lleva su información. La vista general muestra en `Info` cuántas ROM tienen información y en `Problemas gamelist` lo que no se pasó; tras el nombre de la plataforma, un texto gris dice cuántas entradas se pasaron. Si el archivo está dañado, no se pasa nada y se queda lo que había.

**gamelist.xml y archivos multimedia fuera de la carpeta de la plataforma.** Si la carpeta de la plataforma no tiene un `gamelist.xml` propio, el Workbench busca donde lo guardan los frontends, en este orden: `~/ES-DE/gamelists/<plataforma>/` (ES-DE), `~/.emulationstation/gamelists/<plataforma>/` (EmulationStation, RetroPie) y en Linux `/etc/emulationstation/gamelists/<plataforma>/`. El nombre de la carpeta de la plataforma vale como nombre del sistema. Las rutas como `%ROMPATH%/nes/…` se refieren a la carpeta de la plataforma. La línea gris, el informe y la pregunta antes de escribir indican el lugar; se escribe en el mismo lugar, con la copia de seguridad allí. El Workbench busca además archivos multimedia en `~/ES-DE/downloaded_media/<plataforma>/` (o en la carpeta multimedia elegida en los ajustes de ES-DE) y en `~/.emulationstation/downloaded_media/` y `downloaded_images/`. Esos archivos fuera de la colección solo se muestran y se escriben en el `gamelist.xml`, pero nunca se eliminan ni se renombran.

**Archivos multimedia en las subcarpetas.** En cada análisis el Workbench busca además en todas las subcarpetas de una plataforma imágenes, vídeos y manuales que el `gamelist.xml` no nombra ya. Solo se asigna lo que el nombre dice sin duda: una carpeta por categoría con el nombre de la ROM (`wheel/10yard.png`, `marquees/10yard.png`) o nombre de la ROM, separador (`-`, `.` o `_`) y categoría en cualquier carpeta (`downloaded_images/10yard-wheel.png`, `game.image.jpg`). Si encajan varias ROM, gana el nombre más largo (`sf2ce-image.png` pertenece a `sf2ce.zip`, no a `sf2.zip`); no hay asignación por parecido. Lo que no está claro se queda sin ROM. Cada ROM de juego sin entrada en el `gamelist.xml` recibe una entrada vacía con el nombre antes del primer paréntesis; los archivos BIOS (`BIOS` en un paréntesis o nombres conocidos como `neogeo`, `pgm`, `skns`) no cuentan como juegos y no reciben archivos multimedia. Tras el nombre de la plataforma, un texto gris dice cuántos archivos multimedia están asignados y cuántos quedaron sin ROM; `Info` cuenta también las entradas vacías para las que se encontraron archivos multimedia.

**Eliminar archivos multimedia sin uso.** `m` (en la plataforma o en la vista general para la plataforma resaltada) busca imágenes, vídeos y manuales que ya nada usa: ninguna ROM de la carpeta se llama como ellos y ningún `gamelist.xml` los enlaza, por ejemplo las imágenes de una ROM eliminada fuera del Workbench. Solo se busca en las carpetas multimedia dentro de la carpeta de la plataforma, es decir, carpetas cuyo nombre es una categoría (`images`, `videos`, `marquees`, `wheel`, `manuals` …) o `media`, `downloaded_images`, `downloaded_media`, `artwork`, `boxart`, `covers`. Los archivos directamente en la carpeta de la plataforma, en otras subcarpetas (por ejemplo en la carpeta de un juego) y en las carpetas multimedia de ES-DE o RetroPie fuera de la colección nunca se tocan. Antes, el Workbench vuelve a leer la carpeta y un `gamelist.xml` cambiado; si el `gamelist.xml` no se puede leer, no elimina nada. La pregunta indica cantidad, tamaño y los primeros archivos; los archivos eliminados no van a la papelera. Qué archivos multimedia no tienen ROM lo muestra antes el informe con `g`.

**Vista del juego, nombre e informe.** El nombre del `gamelist.xml` vale para todo el juego, no para un archivo: el encabezado de un juego muestra el nombre del archivo conservado y nuestro título entre paréntesis detrás, por ejemplo `10-Yard Fight (10yard)`; si ambos son iguales o no hay ninguno, solo aparece nuestro título. En la fila con el nombre de un juego, la columna `Nota` muestra, tras los posibles problemas, valoración, jugadores y año de lanzamiento, por ejemplo `★ 4.5 · 1-2 jugadores · 1991` (con `--ascii` `* 4.5 - 1-2 jugadores - 1991`); vienen del archivo conservado o, si este no los tiene, de otro archivo del juego. Los archivos BIOS y los marcados con `n` muestran `no es un juego` en la columna `Nota`. `Enter` (en la ventana también un doble clic en un archivo) muestra en lugar de la lista todo lo que se sabe del juego: sus archivos con su decisión, los campos como descripción, valoración (como x / 5), fecha, desarrollador, tiempo de juego y favorito, los demás campos del `gamelist.xml` y los archivos multimedia por categoría; a propósito no hay vistas previas. `g` muestra el informe gamelist: lo que no se pasó y por qué, los avisos, las ROM sin información, los archivos multimedia sin ROM y los archivos que no son juegos. `n` marca los archivos seleccionados como `no es un juego` o lo deshace; un `gamelist.xml` posterior no lo cambia. Si un archivo se conserva o se elimina lo siguen decidiendo las reglas. El resumen de `gamelist.xml` y archivos multimedia aparece en gris en una línea propia bajo la línea de la plataforma.

**Eliminar y renombrar se llevan los archivos multimedia.** Cuando `Ejecutar...` elimina una ROM, sus archivos multimedia se eliminan con ella, imágenes, vídeos y manuales tanto del `gamelist.xml` como de las subcarpetas; la pregunta antes de eliminar indica su número. Un archivo multimedia que también usa una ROM que se queda, se queda. Una ROM eliminada se lleva también su información, favorito y tiempo de juego incluidos. Cuando `Ejecutar...` quita el número delante de un nombre, los archivos multimedia cuyo nombre empieza por el nombre antiguo de la ROM se renombran con ella (`01 - Alpha (USA)-image.png` pasa a ser `Alpha (USA)-image.png`). El `gamelist.xml` en sí no se modifica.

**Editar la información del juego.** En la vista del juego, `e` abre un formulario para el archivo: nombre, nombre para ordenar, descripción, valoración (de 0 a 5 estrellas, también 3,5), fecha de lanzamiento (`AAAA`, `AAAA-MM` o `AAAA-MM-DD`), desarrollador, editor, género, jugadores, región, idiomas, además de favorito, oculto y para niños. El tiempo de juego, el número de partidas y el identificador quedan como los llevan el frontend y el scraper. `Ctrl+S` o `Guardar` guarda, `Esc` o `Cancelar` vuelve a la vista del juego sin guardar; un valor erróneo se indica y el formulario sigue abierto. Los campos cambiados llevan un `✎` en la vista del juego; una nueva importación del `gamelist.xml` los deja como están. Al editarla, una entrada vacía se convierte en una de verdad. Al escribir el `gamelist.xml`, los cambios entran en él.

**Escribir el gamelist.xml.** Solo cuando se le pide, el Workbench vuelve a escribir el `gamelist.xml` de una plataforma a partir de su base de datos: con `w` en la plataforma o en la vista general para la plataforma resaltada, con `--write-gamelists` para todas. Tras una limpieza que ha eliminado archivos, lo ofrece si la plataforma tiene un `gamelist.xml`. Antes, el archivo anterior se guarda como `gamelist.xml.<fecha_hora>.bak`; se quedan las tres últimas copias, las más antiguas se eliminan. El archivo nuevo se crea primero con otro nombre y luego sustituye al antiguo en un solo paso, para que nunca quede un archivo a medias. Contiene todos los juegos, también los de entrada vacía, pero no los archivos BIOS ni otros que no son juegos; además todos los campos conocidos, los archivos multimedia por categoría (un archivo en dos categorías aparece dos veces), el identificador y todos los demás campos tal como se leyeron. Los valores iguales al predeterminado faltan, como en EmulationStation. En el bloque `<provider>` figura como software `RCW` (Rom Cleanup Workbench) con nuestra página de GitHub; el sistema se queda. Después, el archivo cuenta como leído.

**Carpetas sin juegos.** Una carpeta como `bios` o `saves` no contiene juegos. `n` marca la carpeta resaltada como `sin juegos`: no se analiza (tampoco con `Analizar todo` ni `--scan-all`) ni se abre, no cuenta en el total y `Ocultar vacías` la oculta. Lo que la base de datos sabía de ella se borra. Un segundo `n` lo deshace; la carpeta queda entonces `sin analizar`. A propósito no hay un botón para ello.

**Los cambios a mano** (`k`/`x`) se conservan, también tras cerrar, hasta que ejecutes o vuelvas a analizar la plataforma. Si un archivo cambia, su cambio a mano se descarta.

**Ajustes para una plataforma.** Con una plataforma abierta, los ajustes muestran arriba `Ajustes generales` o `Ajustes específicos de NES`. Con la opción específica, la prioridad, las palabras de borrado y la elección entre archivo normal y ZIP valen solo para esta plataforma; se guardan en la base de datos, y `redundanz_config.json` sigue siendo el estándar para todas las demás. Unos ajustes específicos nuevos empiezan con los valores estándar; volver a `Ajustes generales` los descarta. La línea bajo el título de los ajustes indica dónde se guardan: `redundanz_config.json` o, con la opción específica, la base de datos de la colección (el idioma sigue en `redundanz_config.json`). El idioma vale siempre para todo. En el resumen, esas plataformas llevan un `*` tras el nombre.

**Sin ventana**, `--scan-all` analiza todas las plataformas, por ejemplo de noche:

```powershell
python rom_cleanup_workbench.py "D:\roms" --scan-all
```

Con `--deep-scan` se vuelve a leer cada archivo. Así nunca se elimina nada.

## Ventana de análisis

Como los archivos ZIP se tienen que descomprimir para obtener el tamaño, la suma SHA-256 y el nombre de su contenido, tras elegir una carpeta puede pasar un momento hasta que se muestren los resultados.

La fila verde de arriba muestra a la izquierda `Rom Cleanup Workbench` y a la derecha la carpeta; debajo aparece en verde `Plataforma:` con el nombre de la carpeta abierta en negrita, seguido de `*` como en la vista general si la plataforma tiene ajustes propios; luego viene una línea vacía. A la derecha están las teclas principales de la vista, en la lista `x Eliminar`, `k Conservar`, `Enter Info del juego`, `F12 Realizar la limpieza` y `F1 / ? Ayuda: más teclas`. `F1` o `?` muestra en lugar de la lista todas las teclas, ordenadas por tema; `Esc`, `F1` o `?` las cierra de nuevo. En la vista general ambas muestran las teclas de la vista general y debajo, en `Bueno saber`, qué significan los estados, el análisis y el análisis profundo. La prioridad vigente la muestran los ajustes. En la vista general la palabra `Colección` también está en verde. La penúltima fila verde muestra el estado, durante el análisis por ejemplo `Analizando: 120 de 2007 archivos`. Mientras tanto aparece también una barra de progreso en el centro. La ventana muestra también los errores, por ejemplo en la configuración, y mientras el análisis falle no se puede eliminar nada. Al eliminar, la barra de progreso aparece en el centro y la fila verde muestra por ejemplo `Eliminando: 120 de 500 archivos`; la ventana no acepta entradas hasta que termina la eliminación. Después comunica el resultado y quita de la lista los archivos eliminados sin volver a analizar la carpeta; los archivos que no se pudieron eliminar siguen marcados. `F5` vuelve a analizar la carpeta si lo quieres.

Si en toda la carpeta no hay nada marcado y ningún archivo es sospechoso de ser un archivo de estado o partida guardada, `Nada que hacer.` parpadea en el centro de la ventana.

Los cuatro botones de opción deciden lo que muestra la lista:

- `Por revisar`: solo los juegos con un archivo marcado que cuentan como problemáticos, es decir, donde algo puede perderse sin querer (predeterminado en el primer inicio)
- `Para eliminar`: todos los juegos con un archivo marcado
- `Eliminados por completo`: los juegos de los que no quedaría ningún archivo, casi siempre porque las palabras para eliminar afectan a todos sus archivos (por ejemplo `Ikaruga (Japan).cdi` con la palabra para eliminar `Japan`). Vale la pena comprobar si las palabras para eliminar abarcan demasiado. La confirmación nombra estos juegos por separado: los eliminados por palabras para eliminar, como se pidió, y los demás.
- `Todos los juegos`: todos los juegos, por ejemplo para repasar la información de los juegos u ordenarlos por género. Sus archivos se pueden marcar entonces también con `x`, y aparecen además los casos problemáticos sin archivo marcado, como un ZIP ilegible.

**Solo nombres de juegos.** El interruptor `Solo nombres de juegos` (en la ventana junto a las vistas, en el terminal a la derecha del campo de filtro) o `z` pliega la lista a las filas con los nombres de los juegos, sin líneas de separación: así ves de un vistazo qué juegos tiene la plataforma, con valoración, jugadores y año en la columna `Nota`. El filtro, las vistas y el orden por género siguen valiendo. `Tab` salta de un juego a otro, `Enter` muestra la vista del juego del archivo conservado. `x` y `k` solo actúan sobre archivos; en la ventana, un doble clic o la flecha derecha despliega un solo juego. Un segundo `z` vuelve a mostrar los archivos; la elección queda guardada.

La ventana recuerda la última vista elegida y los archivos de estado o partidas guardadas confirmados (regla 9) en `rom_cleanup_workbench_settings.json` junto al programa.

| Tecla | Efecto |
| --- | --- |
| Flechas | elige una fila, con Mayús varias (por ejemplo todos los discos de un juego) |
| `Tab` / `Mayús+Tab` | va al juego siguiente / anterior; se elige el primer archivo del juego |
| `x` | marca el archivo para eliminar; pasa al final de su juego |
| `k` | conserva el archivo; pasa al lugar que le dan las reglas |
| `1` `2` `3` `4` | las vistas `Por revisar`, `Para eliminar`, `Eliminados por completo`, `Todos los juegos` |
| `z` | mostrar solo los nombres de los juegos o de nuevo los archivos (como el interruptor `Solo nombres de juegos`) |
| `Ctrl` + rueda del ratón | agranda o reduce la letra (de 8 a 32 pt, vale hasta cerrar la ventana) |
| `s` | como el botón `Ajustes...`: muestra u oculta los ajustes de idioma, prioridad, palabras para eliminar y ZIP o archivo normal (consulta [Ajustes](#ajustes)) |
| `/` | va al campo de filtro |
| `F12` | como el botón `Ejecutar...`: tras una confirmación elimina, quita el número delante de los nombres de los archivos conservados (regla 10) y confirma los supuestos archivos de estado o de partida (regla 9) |
| `f` | elige otra carpeta, dentro de la ventana en lugar de la lista: abre carpetas con la flecha, elige una al instante con doble clic, o escribe una ruta en `Ruta:`, y luego `Seleccionar` o `Intro`; `Cancelar` o `Esc` conservan la carpeta actual |
| `r` o `F5` | analiza de nuevo, también vuelve a leer la configuración |
| `c` | muestra los créditos |
| `Enter` | en una plataforma de la colección: todo lo que se sabe del juego resaltado (también doble clic en la ventana); `Enter`, `Esc` o `q` cierra |
| `n` | en una plataforma de la colección: marca los archivos seleccionados como `no es un juego` (por ejemplo un archivo BIOS) o lo deshace |
| `g` | en una plataforma de la colección: el informe gamelist de la plataforma |
| `e` | en la vista del juego: editar la información del juego; `Ctrl+S` guarda, `Esc` vuelve |
| `w` | en una plataforma de la colección: escribir su `gamelist.xml` a partir de la base de datos (tras una pregunta) |
| `m` | en una plataforma de la colección: eliminar sus archivos multimedia sin uso (tras una pregunta) |
| `F1` o `?` | muestra u oculta todas las teclas |
| `q` o `Esc` | cierra sin eliminar nada; en una plataforma de una colección ambas vuelven primero al resumen; tras cambios a mano el programa pregunta antes |

Unas líneas horizontales separan los juegos, y uno de cada dos juegos tiene fondo gris oscuro. La columna `Tamaño` muestra el tamaño de cada archivo en KB, redondeado hacia arriba como en el Explorador de Windows (`1.234 KB`); `?` significa que no se pudo leer el tamaño. El tamaño se lee durante el análisis. Los archivos conservados aparecen en negrita verde bajo `Conservar:`, los que se van a eliminar en rojo bajo `Marcado para eliminar`. La ventana muestra texto blanco en Lucida Sans Typewriter 11 pt sobre fondo negro. Si la fuente no está instalada, Windows elige en silencio una sustituta. Los archivos movidos a mano tienen fondo marrón y llevan la nota `A mano`; mientras la fila está elegida, aparece azul. Las notas del programa no cambian, aunque se refieran a un archivo que has movido.

`Por revisar` oculta los juegos no problemáticos, `Eliminados por completo` todos los juegos de los que queda algo. **Sus archivos marcados se eliminan igualmente al eliminar**; la confirmación indica su número. Los juegos que has cambiado a mano siempre quedan visibles, salvo que el filtro los oculte.

### Filtro

El campo de filtro a la izquierda de la fila inferior limita la vista actual a los juegos con un nombre de archivo que contiene el patrón. Un juego se muestra completo si uno de sus archivos coincide. La lista se actualiza poco después de escribir; no se lee el contenido de los archivos.

- `*` representa cualquier número de caracteres, `?` exactamente uno. Todos los demás caracteres, incluidos `[` y `]`, cuentan literalmente, y no se distingue entre mayúsculas y minúsculas. Los espacios al principio y al final solo cuentan entre comillas: `" by "` encuentra `Mario by Mick` pero no `Moby Dick`; sin comillas `by` encuentra ambos.
- El patrón puede aparecer en cualquier parte del nombre: `Beta`, `*Beta*` y `Mario?2` encuentran todos también `Super Mario 2 (Beta).nes`. Por tanto, `S*` encuentra cualquier nombre que contenga una `S`, no solo los que empiezan por ella.
- `Intro`, `Tab` y la flecha abajo vuelven a la lista; `Esc` vacía el filtro y vuelve a la lista.
- Mientras el cursor está en el campo, las teclas solo escriben allí: `x`, `k`, `Enter`, `f`, `r`, `F5` y `Esc` no ejecutan sus funciones de la lista.
- El filtro sigue activo después de `F5`, después de eliminar y después de elegir otra carpeta. No se guarda.

**El filtro solo cambia la visualización. Los archivos marcados ocultos por el filtro también se eliminan cuando eliminas**; la confirmación indica su número.

### Ajustes

El botón `Ajustes...` de la fila inferior, o `s`, muestra los cambios más frecuentes de `redundanz_config.json` en la ventana principal, en lugar de la lista de archivos. `Guardar` o `Cancelar`, `Esc`, `Ctrl+E` u otro clic en `Ajustes...` devuelven la lista. Mientras tanto, el filtro, las vistas, `Ejecutar...`, `Analizar de nuevo` y `Carpeta...` están bloqueados, y `x`, `k`, `Enter` y `F12` no hacen nada, para que nada cambie en la lista oculta.

- **Idioma:** Establece el idioma de la interfaz. Elige entre los seis idiomas. Un idioma nuevo se aplica a partir del próximo inicio del programa.
- **Prioridad:** Establece qué versiones regionales tienen preferencia sobre las demás. La mejor región arriba; la información adicional como `Beta` o `Proto` va tras `none`, para que esos archivos queden al final (regla 6). Elige una entrada y muévela con `Subir` y `Bajar`, quítala con `Quitar` o con la tecla `Supr`, y añade una nueva con el campo bajo la lista y `Añadir` (o `Intro`).
- **Palabras para eliminar:** Establecen qué versiones de un juego se eliminan siempre. Separadas por comas, por ejemplo `Hack, Hacks`. Los archivos que las contienen se marcan para eliminar (regla 2).
- **El mismo juego como archivo normal y como archivo ZIP:** Establece cuál de los dos se conserva cuando ambos son de la misma versión. `Conservar el archivo normal` (predeterminado) marca el archivo ZIP, `Conservar el archivo ZIP` marca los archivos normales (consulta [Archivos ZIP](#archivos-zip)).
- **Favoritos y juegos jugados (gamelist.xml):** `Solo un aviso en la lista` (predeterminado) deja decidir a las reglas; un archivo que se va a eliminar y que según el `gamelist.xml` es favorito o tiene tiempo de juego recibe el aviso `Favorito o jugado – se borrará`. `Conservarlos con preferencia` conserva, dentro de un juego, el archivo favorito, si no el de más tiempo de juego; si las reglas habían conservado otro archivo único, este cede, y las partidas guardadas siguen al archivo conservado. Vale en general o por plataforma (`prefer_played` en la configuración).

`Guardar` escribe el archivo y vuelve a analizar la carpeta si la prioridad, las palabras o la elección entre archivo normal y archivo ZIP han cambiado; si has cambiado marcas a mano, el programa pregunta antes, porque esos cambios se pierden. Todas las demás entradas del archivo se quedan como están. Los valores incorrectos, como una lista de regiones vacía o la misma región dos veces, se notifican, no se escribe nada y los ajustes siguen abiertos. Si el archivo no se puede leer, los ajustes no se abren, para que no puedan sobrescribir entradas que no conocen. Con `--config`, los ajustes editan ese archivo; con `--priority`, para esta ejecución sigue valiendo la prioridad indicada allí.

Solo es problemático aquello en lo que algo puede perderse sin querer. Lo que piden las palabras para eliminar es deseado, y un archivo cuyo contenido está en un archivo conservado (`Contenido idéntico a …`) no se pierde. Un juego cuenta como problemático si

- no se conservaría ninguno de sus archivos sin que lo pidan las palabras para eliminar (un juego que desaparece del todo por palabras para eliminar o como partida guardada sin ROM aparece en `Eliminados por completo`, pero no es problemático),
- el contenido de un ZIP marcado no aparece en ningún otro sitio (`El contenido del juego difiere de la versión conservada`),
- un ZIP está dañado, cifrado o no es legible,
- un archivo se conserva como posible archivo de estado o partida guardada (regla 9),
- las reglas solo decidieron por un `Empate` y el archivo marcado tiene otro contenido,
- varios ZIP de la misma versión tienen contenido distinto,
- los nombres de archivo escriben el juego de forma distinta (`Title 1-2` y `Title 12`) y un archivo marcado de una grafía distinta a la de todos los conservados tiene otro contenido,
- un archivo marcado tiene un tipo de archivo distinto al de los conservados (`.nes` y `.sfc`) y su contenido no está en ningún archivo conservado.

Si una palabra para eliminar marca un archivo, este no hace problemático el juego en ninguno de estos casos.

La ventana usa `tkinter`, que forma parte de la instalación habitual de Python en Windows. Si falta, el programa lo notifica y no elimina nada.

## Después de la limpieza automática

Incluso después de la limpieza automática pueden quedar versiones redundantes de un juego. La forma más sencilla de encontrarlas es el filtro (tecla `/` y luego el nombre del juego). Después puedes marcar los archivos que aún hay que eliminar.

## Versión para terminal (Linux)

El mismo programa funciona también en un terminal de texto, por ejemplo por SSH (PuTTY, MobaXterm), en `tmux` o en la consola de Linux. Muestra la misma lista, aplica las mismas reglas y comparte con la ventana `redundanz_config.json`, `rom_cleanup_workbench_settings.json` y `translations.py`.

En Linux se inicia por sí sola cuando no hay pantalla gráfica (ni `DISPLAY` ni `WAYLAND_DISPLAY` están definidas, como por SSH). `--tui` la inicia en cualquier otro lugar, también en Windows; úsalo donde haya una pantalla gráfica pero quieras el terminal, por ejemplo en MobaXterm o en WSL.

Necesita [Textual](https://textual.textualize.io/) (probado con 8.2.8). Cómo instalarlo e iniciar el programa se describe en [Instalación](#instalación) y [Uso](#uso).

Sin Textual, el programa lo dice y no elimina nada. La pantalla tiene las filas de la ventana de arriba abajo: la fila verde del título con la carpeta, la plataforma con las teclas principales, la lista, el campo de filtro con el interruptor `Solo nombres de juegos`, las cuatro vistas y la fila verde de estado. En la lista, cada juego empieza con su nombre en negrita, seguido de guiones hasta el borde derecho; un aviso como `Distintas grafías del nombre` aparece en esa fila. En un terminal estrecho, por ejemplo las 80 columnas de PuTTY, los nombres de archivo y los avisos largos pasan a la línea siguiente en su columna en lugar de salirse de la pantalla. `Nada que hacer.` parpadea con el parpadeo propio del terminal; en PuTTY puede que haya que activar antes el texto parpadeante. Las preguntas y los mensajes aparecen en un marco sobre la lista, con botones en el idioma del programa; `No` está preseleccionado.

A la derecha de la plataforma están las teclas principales; `F1` o `?` las muestra todas, ordenadas por tema. La ventana y la versión para terminal tienen las mismas teclas.

| Tecla | Efecto |
| --- | --- |
| Flechas | elige una fila, con Mayús varias |
| `Tab` / `Mayús+Tab` | juego siguiente / anterior; se elige su primer archivo |
| `x` / `k` | marca los archivos elegidos para eliminar / los conserva |
| `1` `2` `3` `4` | las vistas `Por revisar`, `Para eliminar`, `Eliminados por completo`, `Todos los juegos` |
| `z` | mostrar solo los nombres de los juegos o de nuevo los archivos (como el interruptor `Solo nombres de juegos`) |
| `/` | va al campo de filtro |
| `F12` | ejecutar: eliminar tras una confirmación (como `Ejecutar...`) |
| `f` | elige otra carpeta: `Derecha` o `Espacio` abre una carpeta, `Izquierda` la cierra, `Intro` o un doble clic la elige; también se puede escribir una ruta |
| `s` | ajustes: `Mayús+Arriba`/`Mayús+Abajo` mueven una región, `Supr` la quita, `Ctrl+S` guarda, `Esc` cancela |
| `r` o `F5` | analiza de nuevo, también vuelve a leer la configuración |
| `c` | muestra los créditos |
| `Enter` | en una plataforma de la colección: todo lo que se sabe del juego resaltado (también doble clic en la ventana); `Enter`, `Esc` o `q` cierra |
| `n` | en una plataforma de la colección: marca los archivos seleccionados como `no es un juego` (por ejemplo un archivo BIOS) o lo deshace |
| `g` | en una plataforma de la colección: el informe gamelist de la plataforma |
| `e` | en la vista del juego: editar la información del juego; `Ctrl+S` guarda, `Esc` vuelve |
| `w` | en una plataforma de la colección: escribir su `gamelist.xml` a partir de la base de datos (tras una pregunta) |
| `m` | en una plataforma de la colección: eliminar sus archivos multimedia sin uso (tras una pregunta) |
| `F1` o `?` | muestra u oculta todas las teclas (también `?`, porque algunos terminales reservan `F1` para su propia ayuda) |
| `q` o `Esc` | cierra sin eliminar nada; en una plataforma de una colección ambas vuelven primero al resumen; tras cambios a mano el programa pregunta antes |
| En una pregunta | `Izquierda`/`Derecha` eligen un botón, `Intro` lo pulsa, `Esc` responde `No` |

El ratón también funciona: un clic elige una fila, la rueda desplaza, y las vistas y los botones se pueden pulsar. Las letras escritas en un campo se quedan en el campo, aunque se escriban rápido o se peguen: una `x` en el filtro nunca marca un archivo.

**Colores y caracteres.** Con 256 colores o más, la versión para terminal usa los colores de la ventana, pero negro detrás de cada juego (sin rayas). Donde el terminal solo tiene 16 colores (`TERM=xterm`, `TERM=linux`), pasa a colores ANSI sencillos: selección azul, filas de título y de estado verdes, archivos conservados en verde y marcados en rojo, filas marrones con texto negro cambiadas a mano. En la consola de Linux, en terminales como `vt100` y cuando la configuración regional indica un juego de caracteres distinto de UTF-8 (por ejemplo `en_US` o `de_DE.ISO-8859-1`), dibuja solo caracteres ASCII: vistas como `(*)`, marcos hechos de `+`, `-` y `|`. `--ascii` lo fuerza. PuTTY se identifica como `xterm` (16 colores); para los colores de la ventana, pon *Connection → Data → Terminal-type string* en `xterm-256color`. Los nombres de archivo y los textos en otras escrituras, como el japonés, siguen necesitando un terminal y una fuente que puedan mostrarlos.

Diferencias con la ventana: no hay zoom de letra, porque la fuente pertenece al terminal (en PuTTY: *Window → Appearance*); y los juegos no van a rayas, sino que empiezan con una línea de guiones. Con 16 colores, las filas verdes tienen texto negro, que sigue siendo legible sobre un verde claro. Al eliminar, la versión para terminal elimina en segundo plano y muestra la barra de progreso; todas las teclas están bloqueadas hasta que termina. La ventana y la versión para terminal guardan su vista y las partidas guardadas confirmadas en el mismo `rom_cleanup_workbench_settings.json`.

## Configuración: `redundanz_config.json`

El archivo está junto al programa y se vuelve a leer en cada análisis. Idioma, prioridad, palabras para eliminar y la elección entre archivo normal y archivo ZIP se cambian más fácilmente en la ventana con `Ajustes...` (consulta [Ajustes](#ajustes)). En el propio archivo basta con cambiar el orden en `region_priority` y guardar el archivo:

```json
"region_priority": ["USA", "Europe", "none", "Japan", "Beta"],
"delete_tags": [],
"prefer_zip": false,
```

Si el archivo contiene un error, por ejemplo una entrada mal escrita, no se realiza ningún análisis y no se elimina nada. Así es el archivo incluido: el idioma es el inglés, la prioridad USA, Europe, none, Japan, Beta, no hay palabras para eliminar y junto a un archivo ZIP se conserva el archivo normal. Por tanto, los archivos sin región van antes que los japoneses. Si falta el archivo o una entrada, se aplican los mismos valores predeterminados.

- `language`: el idioma de la ventana, de las notas y de la salida en el terminal (ver abajo).
- `region_priority`: regiones e información adicional, la mejor primero. `none` representa los archivos sin región conocida; las palabras de los otros idiomas (`keine`, `nessuna`, `ninguna`, `aucune`, `なし`) también sirven. La información adicional como `Beta` tras `none` deja esos archivos al final (regla 6); `Beta` también coincide con `Beta 2`.
- `region_aliases`: otras grafías de una región, por ejemplo `Europa` para `Europe`. También se incluyen las formas cortas `U`, `E` y `J` de los nombres GoodTools como `Title (J) [o1].nes`.
- `delete_tags`: las palabras para eliminar, información adicional que siempre lleva a eliminar (regla 2). De forma predeterminada la lista está vacía. Una palabra para eliminar cuenta como palabra entera en cualquier lugar de un paréntesis: `Hack` coincide con `(Hack)`, `(Hack 2)`, `(Hack by Someone)` y `(Micks Hack)`, pero no con `(Hacks)` ni `(Hackers)`, ni con una palabra fuera de los paréntesis como en `Hack Attack (USA)`; quien quiera eliminar los hacks introduce por tanto `Hack` y `Hacks`.
- `part_tags`: partes de una versión, por ejemplo `Disc 1`.
- `prefer_zip`: `false` (predeterminado) conserva el archivo normal cuando un juego existe como archivo normal y como archivo ZIP de la misma versión, `true` conserva el archivo ZIP.

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

El programa pasa por alto algunos archivos por completo: no aparecen en ningún sitio y nunca se eliminan. Cuentan como paréntesis `( )`, `[ ]` y `{ }`, igual en todas partes: para el nombre del juego, la prioridad, las versiones y las palabras para eliminar.

- Archivos cuyo nombre empieza por `gamelist`, sin distinguir mayúsculas y minúsculas. No son archivos ROM.
- Archivos ocultos: nombres que empiezan por un punto, como `.xxx` o `.DS_Store`, y archivos con el atributo de Windows «oculto».

1. Los archivos van juntos si el texto antes del primer paréntesis es igual. Mayúsculas y minúsculas, espacios, guiones y guiones bajos no cuentan, así que `Pac-Man` = `Pac Man` = `Pac_Man` = `PacMan`. Por eso también `Title 1-2` = `Title 12`. Además cuentan como iguales `und` = `and` = `&` = `&&`, `Sullivan's` = ``Sullivan`s`` = `Sullivan´s` = `Sullivans` (los apóstrofos no cuentan), los números romanos de `I` a `IX` como palabra completa iguales a `1`-`9` (`Final Fantasy VII` = `Final Fantasy 7`; a partir de `X` se quedan como están, porque `Mega Man X` y `Mega Man 10` son dos juegos) y `The Title` = `Title The` = `Title, The` = `Title`. Un `The` en medio del nombre sí cuenta. Del mismo modo, `vs` = `vs.` = `versus`. Un número delante del nombre, por ejemplo de una colección numerada, no cuenta: `057 Robocop vs Terminator` = `057 - Robocop vs Terminator` = `Robocop vs Terminator`. Si el nombre consiste solo en el número (`1942`) o el número va pegado a la palabra (`2Fast`), sigue siendo parte del nombre; `4 in 1` y `3 in 1` siguen siendo juegos distintos. Como entonces los nombres solo coinciden gracias a la comparación, el juego cuenta como problemático (`Distintas grafías del nombre`) si un archivo marcado de la otra grafía tiene un contenido distinto al de los conservados.
2. Los archivos con una palabra para eliminar (`delete_tags`, ninguna de forma predeterminada, por ejemplo `Hack` y `Hacks`) se marcan siempre, aunque sea el único archivo del juego. `k` conserva igualmente un archivo así. El aviso dice entonces `Eliminado por la palabra para eliminar (Hack) - como se pidió`; para estos archivos no hay advertencia sobre el contenido, ya que su contenido debe desaparecer. Excepción: si un paréntesis nombra varias regiones y una de ellas es exactamente la palabra para eliminar, pero otra es una región de tu lista de prioridad, la palabra para eliminar no vale para ese paréntesis. `(Japan, USA)` es también la versión USA: con la palabra para eliminar `Japan` y `USA` en la lista se queda y se clasifica como versión USA; `(Japan)` solo se sigue marcando.
3. De los archivos restantes se conserva el que tiene la mejor entrada en `region_priority`. Dentro de un paréntesis cuenta la mejor entrada: con `(USA, Japan)`, la mejor de las dos. Entre paréntesis distintos cuenta la peor: `(USA) (Beta)` cuenta como `Beta` (regla 6).
4. Todos los archivos de la misma versión se conservan juntos, por ejemplo `(Disc 1)` y `(Disc 2)` o `.cue` y `.bin`. Todo lo demás se marca. Excepción: si solo una parte de estos archivos tiene un número delante del nombre (`073 Batman (USA).sfc` y `Batman (USA).sfc`), se conservan los que tienen número y los demás se marcan (`Se prefiere el nombre con número`).
5. Una región que no está en `region_priority` cuenta como `none`. Esto vale también para indicaciones como `(Rev 1)`.
6. La información adicional como `Beta`, `Proto` o `Alpha` se escribe en `region_priority` tras `none`. Los archivos que la llevan van después de todos los demás, incluso después de los archivos sin región, y en el orden de la lista: con `none, Beta, Proto`, una Beta va antes que un Proto. Solo se conservan si no hay un archivo mejor del juego. Entre ellos cuenta de nuevo la región, luego la versión de la regla 7 y luego el número tras la información adicional: `Beta 2` gana a `Beta 1`, y `Beta 1` a `Beta` sin número. Los números se comparan numéricamente (`Beta 10` antes que `Beta 9`). El archivo que pierde recibe la nota `Beta anterior`.
7. Con la misma prioridad gana el número de versión más alto, comparado numéricamente (`v1.10` antes que `v1.9`). Entre paréntesis se reconocen `v1.1`, `Ver 1.1`, `Version 1.1`, `Rev 1` y `Rev A`; en el nombre del juego solo la forma `Title v1.1`, también con `-` o `_` en lugar del espacio. Un archivo sin versión pierde frente a uno con versión. La región cuenta antes que la versión.
8. Después gana el archivo con un número delante del nombre (`073 Batman` antes que `Batman`), luego el que tiene menos información adicional, luego un archivo sin ZIP (con `prefer_zip`: un archivo ZIP) y luego el orden alfabético. El informe muestra entonces `Empate`.
9. Un archivo más pequeño que 1/4 del archivo más grande del juego se aparta antes de las reglas 3 a 8 y se conserva: podría ser un archivo de estado o de partida guardada. Por eso no se puede eliminar ni desplazar a la ROM verdadera, por ejemplo `1941.state` al archivo `1941.zip`. La columna de avisos muestra entonces `Posible archivo de estado o partida guardada` y el juego cuenta como problemático. Un juego así aparece en `Por revisar`, `Para eliminar` y `Todos los juegos`, aunque ninguno de sus archivos esté marcado. Al eliminar, el programa confirma todos los demás archivos sospechosos como legítimos: se quedan donde están, siguen sin eliminarse nunca y ya no aparecen en `Por revisar` ni en `Para eliminar`, tampoco después de `F5` o de reiniciar. La confirmación indica su número. El programa los recuerda con ruta y tamaño en `rom_cleanup_workbench_settings.json`; si el tamaño cambia, el archivo vuelve a ser sospechoso. Si no hay nada marcado, `F12` ofrece confirmarlos sin eliminar nada. Los ZIP cuentan con su tamaño descomprimido. Esto no vale para un archivo normal pequeño junto a un archivo normal grande de su misma versión, por ejemplo un `.cue` junto a su `.bin`, ni para un archivo con la misma extensión que el más grande (un `.nes` pequeño junto a un `.nes` grande es una ROM sobre la que deciden las reglas 3 a 8), ni para archivos marcados por `delete_tags` o por un ZIP defectuoso. Con `x` puedes marcar igualmente el archivo a mano. Las partidas guardadas con una extensión típica (`.srm`, `.sav`, `.eep`, `.mpk`, `.fla`, `.sra`, `.rtc`, `.dsv`, `.mcr`, `.state`, `.state1` …, `.state.auto`, `.st0` …, `.ss0` …) no entran en esta regla: un emulador carga una partida solo si se llama exactamente igual que la ROM (sin extensión). Por eso una partida guardada solo se conserva si un archivo conservado tiene exactamente ese nombre, por ejemplo `Mario Kart 64 (USA).srm` junto a `Mario Kart 64 (USA).n64`. Cualquier otra se marca, también una de otra región o de otra versión como `Mario Kart 64 (U) [!].mpk`, con el aviso `Partida guardada sin archivo ROM del mismo nombre`. Las palabras para eliminar valen también para las partidas guardadas.
10. Al ejecutar, tras eliminar, a cada archivo conservado se le quita el número delante del nombre, con los espacios, puntos, guiones o guiones bajos que lo siguen: `073 Batman (USA).sfc` pasa a ser `Batman (USA).sfc`, `057 - Robocop.md` pasa a ser `Robocop.md`. La confirmación indica antes el número de archivos y un ejemplo; si no hay nada marcado, `F12` solo pregunta por el cambio de nombre. El número se queda si al juego pertenece un archivo `.cue`, `.gdi`, `.m3u`, `.mds`, `.toc` o `.ccd` (nombra los nombres de archivo en su contenido) o si el nombre sin número ya está ocupado; la confirmación indica también este número. El contenido de los ZIP no se renombra. En la fila del título de un juego aparece el nombre con la grafía del primer archivo conservado (`Street Fighter II` o `Street Fighter 2`), siempre sin número; si mueves archivos con `k` o `x`, el título se adapta. Un número cuenta como número de lista solo cuando está claro: con un cero inicial (`057`), con un separador detrás (`057 - `, `283. `) o si el mismo juego está también sin número (`283 Dynamite Bowl` junto a `Dynamite Bowl (J)`); si un número de un juego está claro, todos sus números cuentan como números de lista. Si no, el número pertenece al título y se queda, en el nombre del archivo como en la fila del título: `1080 Snowboarding`, `720 Degrees`.

## Archivos ZIP

Cada archivo ZIP se lee completo, aunque sea el único archivo de un juego. Su contenido se compara con los demás archivos del juego mediante SHA-256.

- **Mismo contenido que un archivo conservado:** el archivo ZIP se marca y el informe indica el archivo con el mismo contenido.
- **Si tras la selección quedan un ZIP y un archivo normal:** el ZIP siempre se marca, incluso con contenido distinto, si es el único archivo que contiene una parte como `(Disc 1)` o si no es legible.
- **Con `Conservar el archivo ZIP` (`prefer_zip`):** Es al revés: junto a un archivo ZIP legible de la misma versión se marcan los archivos normales (`Se prefiere el archivo ZIP`). Si el contenido de un archivo así no aparece en ningún ZIP conservado, el informe muestra `El contenido del juego difiere del archivo ZIP conservado` y el juego se considera problemático (`El contenido de un archivo normal marcado no se conserva`). Un ZIP no legible no desplaza ningún archivo normal. La prioridad sigue yendo primero: un archivo normal `(USA)` gana a un ZIP `(Japan)`.
- **Varios ZIP de la misma versión con contenido distinto:** se conservan todos y el informe lo indica.
- **Marcado, pero el contenido no aparece en ningún archivo conservado:** el informe muestra `El contenido del juego difiere de la versión conservada`. El archivo sigue marcado.
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
