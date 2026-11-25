# Rom Cleanup Workbench
# Copyright (C) 2026 M. Kärcher
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.

"""Terminal version of Rom Cleanup Workbench, built with Textual (python3 rom_cleanup_workbench.py --tui).

The rules are in the Review object from rom_cleanup_workbench.py, the shared state in workbench_state.py.
Like the window, this module does not import the program, because it would otherwise be loaded a
second time when started as a script.

It has what the window has: the list with background analysis, selecting several rows, the three
views, the filter, the settings, questions and messages inside the terminal, deleting and choosing
the folder, with the same keys as the window.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from rich.cells import cell_len
from rich.console import Console
from rich.measure import Measurement
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.geometry import Region
from textual.renderables.bar import Bar as BarRenderable
from textual.screen import ModalScreen, Screen
from textual.scrollbar import ScrollBar, ScrollBarRender
from textual.widgets import (
    Button, Checkbox, DataTable, Input, OptionList, ProgressBar, RadioButton, RadioSet, Static, TextArea, Tree,
)
from textual.widgets.data_table import ColumnKey

from translations import LANGUAGE_NAMES, current_language, tr
from workbench_state import (
    SCOPES, SETTINGS_PATH, add_confirmed_saves, drives, format_kb, load_confirmed_saves, load_hide_empty,
    load_last_collection, load_overview_sort, load_scope, save_hide_empty, save_last_collection, save_overview_sort,
    save_scope,
    scope_flags, subfolders,
)

APP_NAME = "Rom Cleanup Workbench"
# As in the window: Rebuilding a long list on every keystroke would make typing sluggish.
FILTER_DELAY = 0.2
YES_NO = (("dialog.yes", True), ("dialog.no", False))
OK = (("dialog.ok", None),)
# The actions that change or move in the list; a question locks them, as in the window.
_LIST_ACTIONS = {
    "move_cursor", "move_game", "demote", "promote", "choose_view", "focus_filter", "leave_filter", "proceed",
    "choose_folder", "open_settings", "reanalyze", "credits", "game_view", "toggle_no_game", "report",
    "write_gamelist",
}
# As in the window: Redrawing after every deleted file would slow down large deletions.
DELETE_REDRAW = 0.05

# Terminals that cannot show the block and line characters Textual draws by default. The Linux
# console's fonts have only a few hundred characters; vt100 and dumb terminals know only ASCII.
_ASCII_TERMS = ("linux", "vt100", "vt102", "vt220", "dumb")
# Instead of ▐●▌, the question's ●, the tree's lines and arrows, and the bars of the progress bar.
ASCII_RADIO = ("(", "*", ")")
ASCII_DOT = "*"
ASCII_TREE_LINES = ("  ", "| ", "`-", "|-")
ASCII_TREE_ICONS = ("+ ", "- ")


def wants_ascii(environ=os.environ) -> bool:
    """True on the Linux console and similar terminals, or when the locale names another charset.

    A locale such as "de_DE.ISO-8859-1" or "en_US" (whose charset is Latin-1) cannot show UTF-8.
    "C", "POSIX" or none at all says nothing: Python then uses UTF-8 itself, and so do most
    terminals today; --ascii forces it where that is wrong.

    When the locale named in LANG is not installed, Python sets LC_CTYPE to C.UTF-8 itself at
    startup (PEP 538). That says nothing about the terminal either, so LANG decides then.
    """
    if environ.get("TERM", "") in _ASCII_TERMS:
        return True
    lc_ctype = environ.get("LC_CTYPE") or ""
    if not environ.get("LC_ALL") and lc_ctype.lower().replace("-", "") == "c.utf8" and environ.get("LANG"):
        lc_ctype = ""  # very likely set by Python itself, see above
    locale_name = environ.get("LC_ALL") or lc_ctype or environ.get("LANG") or ""
    if locale_name in ("", "C", "POSIX"):
        return False
    return "utf8" not in locale_name.lower().replace("-", "").replace("_", "")


def wants_16_colors(color_system: str | None, environ=os.environ) -> bool:
    """True where the window's colors would turn into gray or black: 16 colors, or the Linux console.

    Converted to 16 colors, the green rows, the blue selection and the buttons all become the
    same gray, and the dark gray fields become black; the console has only 8 background colors.
    """
    return environ.get("TERM", "") == "linux" or color_system in ("standard", "windows")


class AsciiBar(BarRenderable):
    """The progress bar with "=" instead of line characters."""

    HALF_BAR_LEFT = "-"
    BAR = "="
    HALF_BAR_RIGHT = "-"


class AsciiScrollBarRender(ScrollBarRender):
    """Scroll bars of plain colored spaces, without the partial block characters at their ends."""

    VERTICAL_BARS = [" "] * 8
    HORIZONTAL_BARS = [" "] * 8


class DotSwitch(Checkbox):
    """A switch with the red dot of the views instead of a check mark (Deep Scan, Hide empty)."""

    BUTTON_INNER = "●"


def _plain_radio(button: RadioButton) -> RadioButton:
    button.BUTTON_LEFT, button.BUTTON_INNER, button.BUTTON_RIGHT = ASCII_RADIO
    return button


def _game_of(key: str) -> int | None:
    """Returns the game number of a row key such as g3, g3k or g3f5; None for the empty rows between games."""
    if not key.startswith("g"):
        return None
    digits = ""
    for char in key[1:]:
        if not char.isdigit():
            break
        digits += char
    return int(digits) if digits else None


class DashLine:
    """A cell of a game's title row: its text, then "-" up to the right end of the column.

    The table measures it by its text alone, so the line never widens a column; it is drawn in
    the width the column has. str() gives the text, as for the other cells.
    """

    def __init__(self, text: str = ""):
        self.text = text

    def __str__(self) -> str:
        return self.text.strip()

    def __rich_measure__(self, console, options) -> Measurement:
        width = cell_len(self.text)
        return Measurement(width, width)

    def __rich_console__(self, console, options):
        width = options.max_width
        if cell_len(self.text) <= width or options.no_wrap:
            line = Text(self.text, style="bold", no_wrap=True, overflow="crop")
            line.append("-" * max(0, width - cell_len(self.text)), style="bold")
            line.truncate(width)
            yield line
            return
        # Too long for its column (a narrow terminal): wrapped, the dashes after the last line.
        lines = Text(self.text.rstrip(), style="bold").wrap(console, width - 1)
        for number, line in enumerate(lines):
            line = Text(" ", style="bold") + line if number else line
            if number == len(lines) - 1:
                line.append(" " + "-" * max(0, width - cell_len(line.plain) - 1), style="bold")
            line.truncate(width)
            yield line


# In a narrow terminal: the least the note and the file column keep (see GameTable.column_layout).
_NOTE_MIN = 24
_FILE_MIN = 24
# Only for measuring when wrapping file names; it never prints.
_MEASURE = Console(width=200, file=open(os.devnull, "w", encoding="utf-8"), color_system=None)


def _hanging(cell: Text, width: int) -> Text:
    """A cell of the file column wrapped to its width, further lines below the name, not at the edge.

    "     + Super Mario World (Europe) (Beta).sfc " in 24 cells becomes
    "     + Super Mario World" and "       (Europe) (Beta).sfc".
    """
    plain = cell.plain.rstrip()
    if cell_len(plain) < width:
        return cell
    body = plain.lstrip()
    lead = len(plain) - len(body)
    if body[:2] in ("+ ", "- "):  # a file: continue below the name
        lead += 2
    prefix, name = plain[:lead], plain[lead:]
    room = max(8, width - lead - 1)
    lines = Text(name).wrap(_MEASURE, room)
    wrapped = "\n".join((prefix if number == 0 else " " * lead) + line.plain.rstrip()
                        for number, line in enumerate(lines))
    return Text(wrapped + " ", style=cell.style)


def _cell(text: str, **options) -> Text:
    """A cell with one space on each side: the table has no padding of its own (see GameTable)."""
    return Text(f" {text} ", **options)


def _call_analyze(analyze, directory, progress, rescan: bool, full: bool = False):
    """Passes rescan and full only to an analysis that knows them (tests hand in simpler ones)."""
    import inspect

    try:
        parameters = inspect.signature(analyze).parameters
    except (TypeError, ValueError):
        parameters = {}
    options = {name: value for name, value in (("rescan", rescan), ("full", full)) if name in parameters}
    return analyze(directory, progress, **options)


class GameTable(DataTable):
    """The game list: one cursor row plus a selection of several rows, as in the window's list.

    The table's own Up/Down would stop on the empty rows between the games and know no Shift,
    so the app moves the cursor itself.

    It has no cell padding: the table would fill it with spaces, which would break the dashed
    line of a game's title row. The cells carry their own spaces instead (_cell), and the last
    column reaches the right edge (see column_layout).
    """

    COMPONENT_CLASSES = DataTable.COMPONENT_CLASSES | {
        "datatable--selected", "datatable--moved",
    }
    BINDINGS = [
        Binding("up", "app.move_cursor(-1, False)", show=False),
        Binding("down", "app.move_cursor(1, False)", show=False),
        Binding("shift+up", "app.move_cursor(-1, True)", show=False),
        Binding("shift+down", "app.move_cursor(1, True)", show=False),
        Binding("enter", "app.game_view", show=False),  # the game view (formerly i); the cleanup is on F12
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, cell_padding=0, **kwargs)
        self.selected: set[str] = set()
        self.moved: set[str] = set()
        self.natural = (0, 0, 0)  # the widths file, size and note would need without wrapping
        self.title_width = 0  # the name column from the gamelist.xml at the right edge; 0 if not shown
        self.columns_layout = None  # (file, size, note, wrap) as the rows were added

    def available_width(self) -> int:
        """The width for the columns: without a vertical scroll bar, if one is shown.

        When the scroll bar appears or goes, the app lays the list out again (list_resized).
        """
        return max(0, self.scrollable_content_region.width - self.title_width)

    def column_layout(self) -> tuple[int, int, int, bool]:
        """Widths of file, size and note, and whether long names and notes wrap.

        Wide enough: one row per file, and the note column reaches the right edge. Too narrow
        (often 80 columns, as in PuTTY): the note column gets at least a third, never less than
        24 cells, and long file names and notes wrap in their column, so that nothing disappears
        off the right edge.
        """
        file, size, note = self.natural
        available = self.available_width()
        if not available or file + size + note <= available:
            return file, size, max(note, available - file - size), False
        note_width = min(note, max(_NOTE_MIN, available // 3))
        file_width = min(file, max(_FILE_MIN, available - size - note_width))
        note_width = max(note_width, available - size - file_width)
        return file_width, size, note_width, file_width < file or note_width < note

    def apply_layout(self, layout: tuple[int, int, int, bool]) -> None:
        """Sets the column widths before rows are added: their heights depend on them."""
        for key, width in zip(("file", "size", "note", "title"), (*layout[:3], self.title_width)):
            column = self.columns.get(ColumnKey(key))
            if column is not None:
                column.auto_width = False
                column.width = max(1, width)
        self.columns_layout = layout
        self._require_update_dimensions = True

    def on_resize(self, event) -> None:
        self.call_after_refresh(self.app.list_resized)

    def set_selection(self, keys) -> None:
        self.selected = set(keys)
        self._clear_caches()
        self.refresh()

    def set_moved(self, keys) -> None:
        """The files moved by hand; they are brown, as in the window.

        Unlike the window, the games are not striped: the user prefers a black background.
        """
        self.moved = set(keys)
        self._clear_caches()
        self.refresh()

    def _select_cursor_row(self, skip_empty: bool = True) -> None:
        """A click or a key of the table itself selects only the row under the cursor.

        A key that lands on an empty row between two games moves on to the game below it, so
        that something stays selected; a click on an empty row selects nothing.
        """
        if self.row_count:
            key = self.ordered_rows[self.cursor_row].key.value
            if skip_empty and _game_of(key) is None and self.cursor_row + 1 < self.row_count:
                self.move_cursor(row=self.cursor_row + 1)
            key = self.ordered_rows[self.cursor_row].key.value
            self.set_selection({key} if _game_of(key) is not None else ())

    async def _on_click(self, event) -> None:
        await super()._on_click(event)
        self._select_cursor_row(skip_empty=False)

    def action_page_up(self) -> None:
        super().action_page_up()
        self._select_cursor_row()

    def action_page_down(self) -> None:
        super().action_page_down()
        self._select_cursor_row()

    def action_scroll_top(self) -> None:
        super().action_scroll_top()
        self._select_cursor_row()

    def action_scroll_bottom(self) -> None:
        super().action_scroll_bottom()
        self._select_cursor_row()

    def action_scroll_home(self) -> None:
        super().action_scroll_home()
        self._select_cursor_row()

    def action_scroll_end(self) -> None:
        super().action_scroll_end()
        self._select_cursor_row()

    def _get_row_style(self, row_index: int, base_style):
        style = super()._get_row_style(row_index, base_style)
        if 0 <= row_index < self.row_count:
            key = self.ordered_rows[row_index].key.value
            if key in self.moved:
                style += self.get_component_styles("datatable--moved").rich_style
            if key in self.selected:
                style += self.get_component_styles("datatable--selected").rich_style
        return style


class FilterInput(Input):
    """The filter field. Letters typed here stay here, so a "d" or "p" never changes a mark.

    Textual hands each key to the widget that has the focus when the key arrives. Keys typed fast
    (or pasted, or sent by tmux) can therefore wait here while an earlier Enter leaves the field.
    So the field itself handles the keys that leave it, in the order they were typed, and passes
    the keys that come after them on to where the focus is now.
    """

    BINDINGS = [Binding("ctrl+f", "select_all", show=False)]
    # key -> whether leaving also clears the filter
    _LEAVE_KEYS = {"enter": False, "down": False, "tab": False, "shift+tab": False, "escape": True}

    async def _on_key(self, event: events.Key) -> None:
        app = self.app
        if app.focused is not self:  # typed ahead, before an Enter or Esc above it had left the field
            event.stop()
            event.prevent_default()
            # As App.on_event does with a new key: priority bindings first (a "/" comes back here),
            # then the widget that has the focus now.
            if not await app._check_bindings(event.key, priority=True):
                (app.focused or app.screen)._forward_event(events.Key(event.key, event.character))
            return
        if event.key in self._LEAVE_KEYS:
            event.stop()
            event.prevent_default()
            self.app.action_leave_filter(self._LEAVE_KEYS[event.key])
            return
        await super()._on_key(event)


class QuestionScreen(ModalScreen):
    """A question or message over the list, with buttons in the program's language.

    buttons: (text key, value) pairs. The button with the value default has the focus, Enter presses
    it, and Esc chooses the last button (No or OK), as in the window. Left and Right move between them.

    The screen keeps the chosen button itself (self.choice) instead of relying on the focus alone:
    keys typed right after the question was asked can arrive before the focus has moved.
    """

    BINDINGS = [
        Binding("escape", "answer_last", show=False),
        Binding("left", "move(-1)", show=False),
        Binding("right", "move(1)", show=False),
        Binding("enter", "answer_chosen", show=False),
    ]

    def __init__(self, kind: str, title: str, message: str, buttons, default=None):
        super().__init__(classes=f"kind-{kind}")
        self.kind = kind
        self.title_text = title
        self.message = message
        self.labels = [tr(key) for key, _value in buttons]
        self.values = [value for _key, value in buttons]
        self.default_index = self.values.index(default) if default in self.values else 0
        self.choice = self.default_index

    def compose(self) -> ComposeResult:
        with Vertical(id="question"):
            with Horizontal(id="question-head"):
                yield Static(ASCII_DOT if getattr(self.app, "ascii", False) else "●", id="question-dot")
                yield Static(self.title_text, id="question-title", markup=False)
            yield Static(self.message, id="question-text", markup=False)
            with Horizontal(id="question-buttons"):
                for index, label in enumerate(self.labels):
                    yield Button(label, id=f"answer-{index}", compact=True)

    def on_mount(self) -> None:
        app = self.app
        if getattr(app, "ascii", False) or getattr(app, "colors16", False):
            # "tall" is drawn with block characters; the color follows the kind, as the dot does.
            red = self.kind in ("warning", "error")
            if getattr(app, "colors16", False):
                color = "#ff5555" if red else "#00aa00"  # two of the 16 standard colors
            else:
                color = "#e5383b" if red else "#1a7f37"
            self.query_one("#question").styles.border = ("ascii" if getattr(app, "ascii", False) else "tall", color)
        self._focus_choice()

    def _focus_choice(self) -> None:
        buttons = list(self.query(Button))
        if buttons:  # None while the program is just ending.
            self.set_focus(buttons[self.choice])  # at once, unlike focus()

    def on_descendant_focus(self, event) -> None:
        """Tab or a click may also move the focus; the chosen button follows it."""
        widget_id = getattr(event.widget, "id", None) or ""
        if widget_id.startswith("answer-"):
            self.choice = int(widget_id.removeprefix("answer-"))

    def action_move(self, step: int) -> None:
        self.choice = max(0, min(len(self.values) - 1, self.choice + step))
        self._focus_choice()

    def action_answer_chosen(self) -> None:
        self._answer(self.values[self.choice])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self._answer(self.values[int(event.button.id.removeprefix("answer-"))])

    def action_answer_last(self) -> None:
        self._answer(self.values[-1])

    def _answer(self, value) -> None:
        """Only the first answer counts: an Enter typed twice must not answer the next question too."""
        if self.is_current:
            self.dismiss(value)


def _folder_key(path: Path) -> str:
    """Compares folders as the system does: without case on Windows."""
    return os.path.normcase(os.path.abspath(path))


class FolderTree(Tree):
    """The folders; each one reads its subfolders only when it opens, so that large drives cost nothing."""

    BINDINGS = [
        Binding("enter", "screen.choose", show=False),
        Binding("right", "open_folder", show=False),
        Binding("left", "close_folder", show=False),
    ]

    def action_open_folder(self) -> None:
        node = self.cursor_node
        if node is None or not node.allow_expand:
            return
        if node.is_expanded and node.children:
            self.move_cursor(node.children[0])
        else:
            self.screen.load(node)
            if node.allow_expand:  # A folder without subfolders stays closed.
                node.expand()

    def on_click(self, event) -> None:
        """A double click chooses the folder; on the arrow it only opens or closes it."""
        if getattr(event, "chain", 1) == 2 and not (event.style and event.style.meta.get("toggle")):
            self.call_after_refresh(self._choose_cursor)

    def _choose_cursor(self) -> None:
        node = self.cursor_node
        if node is not None and node.data is not None:
            self.screen.query_one("#folder-path", Input).value = str(node.data["path"])
            self.screen.action_choose()

    def action_close_folder(self) -> None:
        node = self.cursor_node
        if node is None:
            return
        if node.is_expanded and node.children:
            node.collapse()
        elif node.parent is not None and not node.parent.is_root:
            self.move_cursor(node.parent)


class FolderScreen(Screen):
    """Chooses the folder in place of the list, as the window does, in the program's language.

    The tree starts at the drives (/ on Linux) and the home folder. dismiss() hands the chosen
    folder to the app, or None after Cancel and Esc.
    """

    BINDINGS = [Binding("escape", "cancel", show=False)]

    def __init__(self, start: Path | None):
        super().__init__()
        self.start = start if start is not None and start.is_dir() else Path.home()

    def compose(self) -> ComposeResult:
        with Horizontal(id="folder-head"):
            yield Static(tr("window.choose_folder"), id="folder-title", markup=False)
            yield Button(tr("folder.select"), id="folder-select", compact=True)
            yield Button(tr("settings.cancel"), id="folder-cancel", compact=True)
        with Horizontal(id="folder-path-row"):
            yield Static(tr("folder.path"), id="folder-path-label", markup=False)
            yield Input(id="folder-path")
        tree = FolderTree("", id="folder-tree")
        tree.show_root = False
        tree.auto_expand = False
        if getattr(self.app, "ascii", False):
            tree.LINES = {name: ASCII_TREE_LINES for name in Tree.LINES}
            tree.ICON_NODE, tree.ICON_NODE_EXPANDED = ASCII_TREE_ICONS
        yield tree
        yield Static(tr("folder.tui_hint"), id="folder-hint", markup=False)

    def on_mount(self) -> None:
        tree = self.query_one("#folder-tree", FolderTree)
        roots = list(drives())
        home = Path.home()
        if all(_folder_key(home) != _folder_key(root) for root in roots):
            roots.append(home)
        for root in roots:
            self._add(tree.root, root, str(root))
        tree.focus()
        self.reveal(self.start)

    def _add(self, parent, path: Path, label: str):
        return parent.add(Text(label), data={"path": path, "loaded": False}, allow_expand=True)

    def load(self, node) -> None:
        """Reads the subfolders of a folder the first time it opens."""
        data = node.data
        if data is None or data["loaded"]:
            return
        data["loaded"] = True
        for folder in subfolders(data["path"]):
            self._add(node, folder, folder.name)
        if not node.children:
            node.allow_expand = False  # no arrow any more

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        self.load(event.node)

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        if event.node.data is not None:
            self.query_one("#folder-path", Input).value = str(event.node.data["path"])

    def reveal(self, path: Path) -> None:
        """Opens the tree down to path and highlights it, as far as the folders exist."""
        tree = self.query_one("#folder-tree", FolderTree)
        path = Path(os.path.abspath(path))
        wanted = [_folder_key(folder) for folder in reversed([path, *path.parents])]
        node, found = tree.root, None
        for key in wanted:
            child = next((child for child in node.children if _folder_key(child.data["path"]) == key), None)
            if child is None:
                if found is None:
                    continue  # not below this root yet: the drive comes first
                break
            found = node = child
            self.load(node)
            node.expand()
        if found is not None:
            self.query_one("#folder-path", Input).value = str(found.data["path"])
            self.call_after_refresh(self._show_folder, found)

    def _show_folder(self, node) -> None:
        """Highlights the folder; first its last subfolder, so that they also come into view if they fit."""
        tree = self.query_one("#folder-tree", FolderTree)
        if node.children:
            tree.scroll_to_node(node.children[-1], animate=False)
        tree.move_cursor(node)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.action_choose()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "folder-select":
            self.action_choose()
        else:
            self.action_cancel()

    def action_choose(self) -> None:
        """Takes the typed path, which follows the highlighted folder; quotes as in a copied path are dropped."""
        text = self.query_one("#folder-path", Input).value.strip().strip('"')
        folder = Path(text) if text else None
        if folder is None or not folder.is_dir():
            self.app.show_message("error", tr("window.choose_folder"),
                                  tr("error.directory_not_found", directory=text))
            return
        self.dismiss(folder)

    def action_cancel(self) -> None:
        self.dismiss(None)


class OverviewScreen(Screen):
    """The collection: one row per platform folder, as in the window. The start page.

    dismiss() hands (platform, rescan, full) to the app, or "folder" for the folder choice.
    """

    BINDINGS = [
        Binding("escape,q", "app.quit", show=False),
        Binding("enter", "open", show=False, priority=True),
        Binding("r,R,f5", "scan", show=False),
        Binding("a,A", "scan_all", show=False),
        Binding("d,D", "toggle_full", show=False),
        Binding("h,H", "toggle_hide_empty", show=False),
        Binding("n,N", "toggle_no_games", show=False),
        Binding("w,W", "write_gamelist", show=False),
        Binding("f,F", "folder", show=False),
    ]
    TOTAL = "*total*"
    LINE = "*line*"

    def __init__(self, root: Path, rows, message: str | None = None):
        super().__init__()
        self.message = message  # shown instead of the counts, for example after scanning all
        self.root_folder = root
        self.rows = {row.folder: row for row in rows}
        self.scanning = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="overview-head"):
            yield Static(tr("overview.title"), id="overview-title", markup=False)
            yield Static(tr("window.folder", directory=self.root_folder), id="overview-folder", markup=False)
        yield ShortKeys("overview", id="overview-keys")
        table = DataTable(id="overview-table", cursor_type="row", zebra_stripes=False)
        yield table
        with Horizontal(id="overview-buttons"):
            yield Button(tr("overview.open"), id="overview-open", compact=True)
            yield Button(tr("overview.scan"), id="overview-scan", compact=True)
            yield Button(tr("overview.scan_all"), id="overview-scan-all", compact=True)
            for switch in (DotSwitch(tr("overview.full"), id="overview-full", compact=True),
                           DotSwitch(tr("overview.hide_empty"), load_hide_empty(self.app.settings_path),
                                     id="overview-hide", compact=True)):
                yield _plain_radio(switch) if getattr(self.app, "ascii", False) else switch
            yield Button(tr("settings.cancel"), id="overview-cancel", compact=True)
        yield Static("", id="overview-status", markup=False)

    def on_mount(self) -> None:
        self.sort_column, self.sort_descending = load_overview_sort(self.app.settings_path)
        table = self.query_one("#overview-table", DataTable)
        table.add_column(tr("overview.platform"), key="platform")
        for column in (*self._NUMBERS, "last_scan", "state"):
            table.add_column(tr(f"overview.{column}"), key=column)
        self._show_sort_arrow()
        self.query_one("#overview-cancel", Button).display = False
        self._fill(self.message)
        table.focus()

    def visible(self) -> list:
        """The rows shown, in the chosen order: all, or without the folders that hold no game file."""
        from workbench_db import sort_rows

        hide = self.query_one("#overview-hide", Checkbox).value
        rows = [row for row in self.rows.values() if row.has_games or not hide]
        return sort_rows(rows, self.sort_column, self.sort_descending)

    _SORTABLE = ("platform", "files", "games", "marked", "problematic", "info", "gamelist_problems")

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """A click on a column heading sorts by it; a second click turns the order round."""
        event.stop()
        if event.column_key.value in self._SORTABLE:
            self.sort_by(event.column_key.value)

    def sort_by(self, column: str) -> None:
        if column == self.sort_column:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column, self.sort_descending = column, False
        save_overview_sort(self.app.settings_path, self.sort_column, self.sort_descending)
        self._show_sort_arrow()
        self._fill()

    def _show_sort_arrow(self) -> None:
        table = self.query_one("#overview-table", DataTable)
        arrow = " v" if self.sort_descending else " ^"
        if not getattr(self.app, "ascii", False):
            arrow = " ▼" if self.sort_descending else " ▲"
        for column in self._SORTABLE:
            text = tr(f"overview.{column}") + (arrow if column == self.sort_column else "")
            table.columns[column].label = Text(text)  # a ColumnKey equals its text
        table.refresh()

    def _fill(self, message: str | None = None) -> None:
        """Shows the visible rows and the total; the highlighted platform stays if it is still shown."""
        table = self.query_one("#overview-table", DataTable)
        selected = self.selected()
        table.clear()
        visible = self.visible()
        for row in visible:
            table.add_row(Text(row.folder + (" *" if row.has_own_config else "")), *self._cells(row), key=row.folder)
        totals = self._totals()
        # A line above the total, as wide as each column's widest entry.
        names = [tr("overview.total")] + [row.folder + (" *" if row.has_own_config else "") for row in visible]
        widths = [max(cell_len(text) for text in names) + 2]
        columns = (*self._NUMBERS, "last_scan", "state")
        for index, column in enumerate(columns):
            texts = [str(self._cells(row)[index]) for row in visible] + [tr(f"overview.{column}")]
            widths.append(max(cell_len(text) for text in texts) + 2)
        line = "-" if getattr(self.app, "ascii", False) else "─"
        table.add_row(*(Text(line * width, style="#888888") for width in widths), key=self.LINE)
        table.add_row(Text(tr("overview.total"), style="bold"),
                      *(Text(_count(value), justify="right", style="bold") for value in totals),
                      Text(""), Text(""), key=self.TOTAL)
        names = [row.folder for row in visible]
        if selected in names:
            table.move_cursor(row=names.index(selected))
        self.query_one("#overview-status", Static).update(
            message or tr("overview.status", platforms=len(visible), files=_count(totals[0])))

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "overview-hide":
            event.stop()
            save_hide_empty(self.app.settings_path, event.value)
            self._fill()

    def action_toggle_hide_empty(self) -> None:
        box = self.query_one("#overview-hide", Checkbox)
        box.value = not box.value

    _NUMBERS = ("files", "games", "marked", "problematic", "info", "gamelist_problems")

    def _cells(self, row) -> list[Text]:
        # "changed" in yellow: the platform should be scanned again.
        yellow = "#ffff55" if getattr(self.app, "colors16", False) else "#e3b341"
        state = Text(tr(f"overview.state.{row.state}"), style=yellow if row.state == "changed" else "")
        return [*(Text(_count(getattr(row, name)), justify="right") for name in OverviewScreen._NUMBERS),
                Text(_when(row.last_scan)), state]

    def _totals(self) -> list[int]:
        return [sum(getattr(row, name) or 0 for row in self.visible()) for name in self._NUMBERS]

    def set_row(self, row) -> None:
        """A platform's new numbers, for example as soon as scan all has finished it."""
        if row.folder not in self.rows:
            return
        self.rows[row.folder] = row
        table = self.query_one("#overview-table", DataTable)
        columns = (*self._NUMBERS, "last_scan", "state")
        if row.folder in {key.value for key in table.rows}:
            for column, cell in zip(columns, self._cells(row)):
                table.update_cell(row.folder, column, cell)
        for column, value in zip(self._NUMBERS, self._totals()):
            table.update_cell(self.TOTAL, column, Text(_count(value), justify="right", style="bold"))

    def selected(self) -> str | None:
        table = self.query_one("#overview-table", DataTable)
        if not table.row_count:
            return None
        key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        return key if key in self.rows else None

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        self.action_open()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        actions = {"overview-open": self.action_open, "overview-scan": self.action_scan,
                   "overview-scan-all": self.action_scan_all, "overview-cancel": self.app.cancel_scan_all}
        actions[event.button.id]()

    def _full(self) -> bool:
        return self.query_one("#overview-full", Checkbox).value

    def action_toggle_full(self) -> None:
        box = self.query_one("#overview-full", Checkbox)
        box.value = not box.value

    def action_open(self, rescan: bool = False) -> None:
        platform = self.selected()
        if platform is None or self.scanning:
            return
        if self.rows[platform].state == "no_games":  # never scanned, never opened
            self.show_status(tr("overview.no_games_locked", platform=platform))
            return
        self.dismiss((platform, rescan, self._full() if rescan else False))

    def action_write_gamelist(self) -> None:
        """w: the gamelist.xml of the highlighted platform."""
        from workbench_db import platform_row

        platform = self.selected()
        if platform is None or self.scanning:
            return

        def written() -> None:
            self.rows[platform] = platform_row(self.root_folder, platform, self.app.config_loader())
            self._fill()

        self.app.write_gamelist(self.root_folder / platform, then=written)

    def action_toggle_no_games(self) -> None:
        """n: the highlighted folder holds no games (or does again)."""
        from workbench_db import toggle_no_games

        platform = self.selected()
        if platform is None or self.scanning:
            return
        self.rows[platform] = toggle_no_games(self.root_folder, platform, self.app.config_loader())
        self._fill()

    def action_scan(self) -> None:
        self.action_open(rescan=True)

    def action_scan_all(self) -> None:
        if not self.scanning:
            self.app.scan_all(self, self._full())

    def action_folder(self) -> None:
        if not self.scanning:
            self.dismiss("folder")

    def set_scanning(self, scanning: bool) -> None:
        self.scanning = scanning
        for widget_id in ("#overview-open", "#overview-scan", "#overview-scan-all", "#overview-full"):
            self.query_one(widget_id).disabled = scanning
        self.query_one("#overview-cancel", Button).display = scanning

    def show_status(self, text: str) -> None:
        self.query_one("#overview-status", Static).update(text)


def _count(value) -> str:
    return "–" if value is None else f"{value:,}".replace(",", ".")


def _is_collection(folder: Path) -> bool:
    from workbench_db import is_collection

    return is_collection(folder)


def _when(moment: str | None) -> str:
    return moment.replace("T", " ")[:16] if moment else tr("overview.never")


class RegionList(OptionList):
    """The region priority, best first. Shift+Up/Down move the highlighted region, Delete removes it."""

    BINDINGS = [
        Binding("shift+up", "screen.move_region(-1)", show=False),
        Binding("shift+down", "screen.move_region(1)", show=False),
        Binding("delete", "screen.remove_region", show=False),
    ]


class KeysScreen(Screen):
    """All keys of the current view, grouped, in place of the list or the overview (F1 or ?)."""

    BINDINGS = [Binding("escape,f1,question_mark", "close", show=False)]

    def __init__(self, context: str, collection: bool):
        super().__init__()
        self.context = context
        self.collection = collection

    def compose(self) -> ComposeResult:
        from workbench_keys import key_notes, key_sections, keys_title

        ascii = getattr(self.app, "ascii", False)
        green = _green(self.app)
        title = keys_title(self.context)
        with Horizontal(id="keys-head"):
            yield Static(Text(title.replace("–", "-") if ascii else title, style=f"bold {green}"), id="keys-title")
            yield Static(tr("keys.close_hint"), id="keys-hint", markup=False)
        sections = key_sections(self.context, window=False, collection=self.collection, ascii=ascii)
        left = (len(sections) + 1) // 2
        columns = [self._column(part, green) for part in (sections[:left], sections[left:])]
        # Side by side only if both fit (each with its padding); a narrow terminal shows them one below the other.
        widths = [max(cell_len(line) for line in text.plain.split("\n")) for text in columns]
        side_by_side = sum(widths) + 7 * len(widths) <= self.app.size.width
        with VerticalScroll(id="keys-body"):
            with (Horizontal if side_by_side else Vertical)(id="keys-columns"):
                for text in columns:
                    yield Static(text, classes="keys-column")
            notes = key_notes(self.context)
            if notes:
                yield Static(Text(tr("keys.section.notes").upper(), style="bold"), id="keys-notes-title")
                bullet = "-" if getattr(self.app, "ascii", False) else "•"
                with Vertical(id="keys-notes"):
                    for note in notes:  # one point each, wrapped under its own text
                        with Horizontal(classes="keys-note"):
                            yield Static(Text(bullet, style=green), classes="keys-bullet")
                            yield Static(note, classes="keys-note-text", markup=False)

    @staticmethod
    def _column(sections, green: str) -> Text:
        width = max(cell_len(key) for _title, rows in sections for key, _text in rows)
        text = Text()
        for index, (title, rows) in enumerate(sections):
            if index:
                text.append("\n")
            text.append(title.upper() + "\n", style="bold")
            for key, description in rows:
                text.append("  ")
                text.append(key + " " * (width - cell_len(key) + 3), style=f"bold {green}")
                text.append(description + "\n")
        text.rstrip()
        return text

    def action_close(self) -> None:
        self.dismiss(None)


class InfoScreen(Screen):
    """The game view (i) or the gamelist report (g) in place of the list: blocks of workbench_view."""

    BINDINGS = [Binding("escape,q,Q", "close", show=False), Binding("enter", "close_kind('game')", show=False),
                Binding("g,G", "close_kind('report')", show=False), Binding("e,E", "edit", show=False)]

    def __init__(self, kind: str, title: str, subtitle: str, blocks: list):
        super().__init__()
        self.kind = kind
        self.title_text = title
        self.subtitle = subtitle
        self.blocks = blocks

    def compose(self) -> ComposeResult:
        green = _green(self.app)
        head = Text(self._plain(self.title_text), style=f"bold {green}")
        if self.subtitle:
            head.append("   " + self._plain(self.subtitle), style="#888888")
        with Horizontal(id="keys-head"):
            yield Static(head, id="keys-title")
            yield Static(tr("game.close_hint"), id="keys-hint", markup=False)
        with VerticalScroll(id="info-body"):
            yield Static(self.text(green), id="info-text")

    def _plain(self, text: str) -> str:
        if getattr(self.app, "ascii", False):
            return text.replace("◀", "<").replace("★", "*").replace("–", "-")
        return text

    def text(self, green: str = "") -> Text:
        text = Text()
        for index, block in enumerate(self.blocks):
            if block[0] == "heading":
                text.append(("" if index == 0 else "\n") + self._plain(block[1]).upper() + "\n",
                            style=f"bold {green}".strip())
            elif block[0] == "field":
                text.append("  " + self._plain(block[1]) + ": ", style="bold")
                text.append(self._plain(block[2]) + "\n")
            elif block[0] == "note":
                text.append("  " + self._plain(block[1]) + "\n", style="#888888")
            else:
                text.append("  " + self._plain(block[1]) + "\n")
        text.rstrip()
        return text

    def action_close(self) -> None:
        self.dismiss(None)

    def action_close_kind(self, kind: str) -> None:
        if kind == self.kind:
            self.dismiss(None)

    def action_edit(self) -> None:
        """e: the form for the game's information (the app opens it once this view is closed)."""
        if self.kind == "game":
            self.dismiss("edit")


class EditScreen(Screen):
    """The form for a game's information (e in the game view): Ctrl+S saves, Esc goes back unsaved."""

    BINDINGS = [Binding("ctrl+s", "save", show=False, priority=True), Binding("escape", "cancel", show=False)]

    def __init__(self, name: str, info: dict | None):
        super().__init__()
        self.file_name = name
        self.info = info

    def compose(self) -> ComposeResult:
        from workbench_view import EDIT_FIELDS, edit_label, form_values

        values = form_values(self.info)
        green = _green(self.app)
        with Horizontal(id="keys-head"):
            yield Static(Text(tr("game.edit.title", name=self.file_name), style=f"bold {green}"), id="keys-title")
            yield Static(tr("game.edit.tui_hint"), id="keys-hint", markup=False)
        with VerticalScroll(id="edit-body"):
            for column, kind in EDIT_FIELDS:
                if kind == "flag":
                    switch = DotSwitch(edit_label(column), values[column], id=f"edit-{column}", compact=True)
                    yield _plain_radio(switch) if getattr(self.app, "ascii", False) else switch
                    continue
                # Label and field on one line, compact, so that the whole form fits in 80 x 24.
                with Horizontal(classes="edit-row"):
                    yield Static(edit_label(column), classes="edit-label", markup=False)
                    if kind == "multiline":
                        yield TextArea(values[column], id=f"edit-{column}", soft_wrap=True, show_line_numbers=False,
                                       compact=True)
                    else:
                        # Not selected on focus: a typed letter must not replace the whole name.
                        yield Input(values[column], id=f"edit-{column}", select_on_focus=False, compact=True)
            with Horizontal(id="edit-buttons"):
                yield Button(tr("settings.save"), id="edit-save", compact=True)
                yield Button(tr("settings.cancel"), id="edit-cancel", compact=True)

    def on_mount(self) -> None:
        self.query_one("#edit-name", Input).focus()

    def values(self) -> dict:
        from workbench_view import EDIT_FIELDS

        result = {}
        for column, kind in EDIT_FIELDS:
            widget = self.query_one(f"#edit-{column}")
            result[column] = widget.text if isinstance(widget, TextArea) else widget.value
        return result

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "edit-save":
            self.action_save()
        elif event.button.id == "edit-cancel":
            self.action_cancel()

    def action_save(self) -> None:
        self.app.save_edit(self)

    def action_cancel(self) -> None:
        self.dismiss(None)


def _green(app) -> str:
    """The green of the kept files: in 16 colors the standard green."""
    return "#00aa00" if getattr(app, "colors16", False) else "#3fb950"


class ShortKeys(Static):
    """The few keys of a view, right of "Platform: nes": key in green, then what it does.

    A narrow terminal breaks the line only between entries, never inside one ("F1 / ?" stays whole).
    """

    def __init__(self, context: str, **kwargs):
        super().__init__("", **kwargs)
        self.context = context

    def _entries(self) -> list[Text]:
        from workbench_keys import short_keys

        green = _green(self.app)
        return [Text.assemble((key, f"bold {green}"), " " + description)
                for key, description in short_keys(self.context)]

    def _lines(self, width: int) -> list[Text]:
        lines, line = [], Text()
        for entry in self._entries():
            if line.cell_len and line.cell_len + 3 + entry.cell_len > width:
                lines.append(line)
                line = Text()
            if line.cell_len:
                line.append("   ")
            line.append_text(entry)
        lines.append(line)
        return lines

    def render(self) -> Text:
        return Text("\n").join(self._lines(self.content_region.width or 10_000))

    def get_content_width(self, container, viewport) -> int:
        return self._lines(10_000)[0].cell_len

    def get_content_height(self, container, viewport, width: int) -> int:
        return len(self._lines(width))


class SettingsScreen(Screen):
    """Language, region priority and low priority tags, in place of the list as in the window.

    It only edits; the app saves (WorkbenchApp.save_settings), as the window does. A broken file
    raises ValueError before anything opens, so that it is never overwritten.
    """

    BINDINGS = [
        Binding("escape", "cancel", show=False),
        # Priority: in a text field Ctrl+E would otherwise only move to the end (End does that too).
        Binding("ctrl+e", "cancel", show=False, priority=True),
        Binding("ctrl+s", "save", show=False, priority=True),
    ]

    def __init__(self, config_file, root_folder=None, platform=None):
        super().__init__()
        self.config_file = config_file
        from workbench_db import settings_for

        # A platform of a collection may have settings of its own (stored in the database).
        self.root_folder, self.platform = root_folder, platform
        self.values, self.own = settings_for(config_file, root_folder, platform)
        self.own_before = self.own
        self.regions = list(self.values["region_priority"])
        language = self.values["language"]
        self.language = language if language in LANGUAGE_NAMES else current_language()

    def compose(self) -> ComposeResult:
        with Horizontal(id="settings-head"):
            yield Static(tr("settings.title"), id="settings-title", markup=False)
            yield Button(tr("settings.save"), id="settings-save", compact=True)
            yield Button(tr("settings.cancel"), id="settings-cancel", compact=True)
        from workbench_db import settings_location

        # Where the settings are saved, in a line of its own: a long path must not be cut off.
        yield Static(settings_location(self.config_file, self.root_folder, self.own), id="settings-file", markup=False)
        if self.platform is not None:
            with Horizontal(id="scope-row"):
                yield Static(tr("settings.scope_label"), id="scope-label", markup=False)
                with RadioSet(id="scope"):
                    for value, text in ((False, tr("settings.scope_default")),
                                        (True, tr("settings.scope_own", platform=self.platform.upper()))):
                        button = RadioButton(text, value=value == self.own, id=f"scope-{'own' if value else 'default'}")
                        yield _plain_radio(button) if getattr(self.app, "ascii", False) else button
            # What "own" means, in a line of its own below the two choices.
            yield Static(tr("settings.scope_own_hint", platform=self.platform.upper()), id="scope-hint",
                         markup=False)
        with Horizontal(id="settings-columns"):
            with Vertical(id="settings-left"):
                yield Static(tr("settings.regions"), id="regions-label", markup=False)
                with Horizontal(id="regions-row"):
                    yield RegionList(id="regions")
                    with Vertical(id="region-buttons"):
                        yield Button(tr("settings.up"), id="region-up", compact=True)
                        yield Button(tr("settings.down"), id="region-down", compact=True)
                        yield Button(tr("settings.remove"), id="region-remove", compact=True)
                with Horizontal(id="new-region-row"):
                    yield Input(id="new-region")
                    yield Button(tr("settings.add"), id="region-add", compact=True)
            with VerticalScroll(id="settings-right"):
                yield Static(tr("settings.language"), markup=False)
                with RadioSet(id="languages"):
                    for code, name in LANGUAGE_NAMES.items():
                        button = RadioButton(name, value=code == self.language, id=f"language-{code}")
                        yield _plain_radio(button) if getattr(self.app, "ascii", False) else button
                yield Static(tr("settings.language_hint"), id="language-hint", markup=False)
                yield Static(tr("settings.delete_keywords"), id="tags-label", markup=False)
                yield Input(", ".join(self.values["delete_tags"]), id="tags")
                # prefer_zip: which of the two remains when a game exists as a plain file and as a ZIP.
                yield Static(tr("settings.prefer"), id="prefer-label", markup=False)
                with RadioSet(id="prefer"):
                    prefer_zip = bool(self.values["prefer_zip"])
                    for key, value in (("settings.prefer_plain", False), ("settings.prefer_zip", True)):
                        button = RadioButton(tr(key), value=value == prefer_zip, id=f"prefer-{str(value).lower()}")
                        yield _plain_radio(button) if getattr(self.app, "ascii", False) else button
                # prefer_played: favorites and played games (gamelist.xml) only noted, or kept.
                yield Static(tr("settings.played"), id="played-label", markup=False)
                with RadioSet(id="played"):
                    prefer_played = bool(self.values["prefer_played"])
                    for key, value in (("settings.played_note", False), ("settings.played_keep", True)):
                        button = RadioButton(tr(key), value=value == prefer_played,
                                             id=f"played-{str(value).lower()}")
                        yield _plain_radio(button) if getattr(self.app, "ascii", False) else button
        yield Static(tr("settings.tui_hint"), id="settings-hint", markup=False)

    def on_mount(self) -> None:
        self._show_regions(0 if self.regions else None)
        self.set_focus(self.query_one("#new-region", Input))  # as in the window

    # The values, as the window's panel gives them ----------------------------------------------

    def language_code(self) -> str:
        return self.language

    def region_list(self) -> list[str]:
        return list(self.regions)

    def tag_list(self) -> list[str]:
        return [tag.strip() for tag in self.query_one("#tags", Input).value.split(",") if tag.strip()]

    def prefers_zip(self) -> bool:
        return self.query_one("#prefer-true", RadioButton).value

    def prefers_played(self) -> bool:
        return self.query_one("#played-true", RadioButton).value

    # Editing the regions ---------------------------------------------------------------------

    def _show_regions(self, highlighted: int | None) -> None:
        listing = self.query_one("#regions", RegionList)
        listing.clear_options()
        listing.add_options([Text(region) for region in self.regions])  # Text: "[" stays literal
        if self.regions and highlighted is not None:
            listing.highlighted = max(0, min(highlighted, len(self.regions) - 1))

    def _highlighted(self) -> int | None:
        index = self.query_one("#regions", RegionList).highlighted
        return index if index is not None and 0 <= index < len(self.regions) else None

    def action_move_region(self, step: int) -> None:
        index = self._highlighted()
        if index is None or not 0 <= index + step < len(self.regions):
            return
        self.regions.insert(index + step, self.regions.pop(index))
        self._show_regions(index + step)

    def action_remove_region(self) -> None:
        index = self._highlighted()
        if index is not None:
            del self.regions[index]
            self._show_regions(index)

    def add_region(self) -> None:
        field = self.query_one("#new-region", Input)
        region = field.value.strip()
        if not region:
            return
        existing = [index for index, other in enumerate(self.regions) if other.casefold() == region.casefold()]
        if existing:
            self._show_regions(existing[0])  # Already in the list: show it instead of adding it twice.
        else:
            self.regions.append(region)
            self._show_regions(len(self.regions) - 1)
        field.value = ""

    # Buttons and keys --------------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        if event.input.id == "new-region":
            self.add_region()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        event.stop()  # not the app's views
        if event.radio_set.id == "languages":
            self.language = event.pressed.id.removeprefix("language-")
        elif event.radio_set.id == "scope":
            self._scope_changed(event.pressed.id == "scope-own")

    def _scope_changed(self, own: bool) -> None:
        """Default or own: the fields show the values of that choice (own starts from the default)."""
        from workbench_db import settings_for

        from workbench_db import settings_location

        self.own = own
        values, _own = settings_for(self.config_file, self.root_folder, self.platform, own=own)
        self.query_one("#settings-file", Static).update(settings_location(self.config_file, self.root_folder, own))
        self.regions = list(values["region_priority"])
        self._show_regions(0 if self.regions else None)
        self.query_one("#tags", Input).value = ", ".join(values["delete_tags"])
        self.query_one("#prefer-true", RadioButton).value = bool(values["prefer_zip"])
        self.query_one("#prefer-false", RadioButton).value = not values["prefer_zip"]
        self.query_one("#played-true", RadioButton).value = bool(values["prefer_played"])
        self.query_one("#played-false", RadioButton).value = not values["prefer_played"]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        actions = {
            "settings-save": self.action_save, "settings-cancel": self.action_cancel,
            "region-up": lambda: self.action_move_region(-1), "region-down": lambda: self.action_move_region(1),
            "region-remove": self.action_remove_region, "region-add": self.add_region,
        }
        actions[event.button.id]()

    def action_save(self) -> None:
        self.app.save_settings(self)

    def action_cancel(self) -> None:
        """Returns to the list without saving."""
        self.dismiss(None)


class WorkbenchApp(App):
    """The terminal window: the same rows as the Windows window, from top to bottom."""

    TITLE = APP_NAME
    CSS = """
    Screen { background: #000000; color: #ffffff; }
    /* Textual tints the focused widget a little; the list nearly always has the focus, and its
       black would turn dark gray. The focus shows through the cursor, the fields and buttons. */
    *, *:focus, *:focus-within { background-tint: #000000 0%; }
    /* Scroll bars in the window's grays instead of Textual's blue (long notes need the horizontal one). */
    * { scrollbar-background: #000000; scrollbar-background-hover: #000000; scrollbar-background-active: #000000;
        scrollbar-color: #444444; scrollbar-color-hover: #666666; scrollbar-color-active: #888888;
        scrollbar-corner-color: #000000; }
    /* Textual marks the view under its keyboard cursor in blue; the views never get the focus here. */
    #views > RadioButton.-selected, #languages > RadioButton.-selected, #prefer > RadioButton.-selected,
    #views > RadioButton.-selected, #languages > RadioButton.-selected, #played > RadioButton.-selected,
    #views > RadioButton.-selected > .toggle--label,
    #languages > RadioButton.-selected > .toggle--label,
    #prefer > RadioButton.-selected > .toggle--label { background: #000000; }
    #played > RadioButton.-selected > .toggle--label { background: #000000; }
    #title-row { height: 1; background: #1a7f37; color: #ffffff; }
    #title { width: auto; text-style: bold; padding: 0 1; }
    #folder { width: 1fr; text-align: right; padding: 0 1; }
    #info-row { height: auto; margin-bottom: 1; }
    #info { width: auto; padding: 0 1; }
    #gamelist-line { height: auto; padding: 0 1; margin-bottom: 1; color: #888888; display: none; }
    #short-keys { width: 1fr; height: auto; padding: 0 1; text-align: right; }
    #keys-head { height: 1; margin: 1 1 1 1; }
    #keys-title { width: 1fr; }
    #keys-hint { width: auto; color: #aaaaaa; }
    #keys-body { height: 1fr; }
    #info-body { height: 1fr; padding: 0 1; }
    #edit-body { height: 1fr; padding: 0 1; }
    .edit-row { height: auto; }
    .edit-row > Input { width: 1fr; background: #222222; }
    .edit-row > TextArea { width: 1fr; height: 4; background: #222222; }
    .edit-label { width: 29; color: #aaaaaa; }
    #edit-body > DotSwitch { margin-left: 29; }
    #edit-body > Checkbox { margin-left: 29; }
    #edit-buttons { height: auto; margin-top: 1; }
    #edit-buttons > Button { margin-right: 2; }
    #keys-columns { height: auto; }
    .keys-column { width: auto; height: auto; padding: 0 6 1 1; }
    #games { height: 1fr; background: #000000; }
    #games > .datatable--header { background: #222222; color: #ffffff; text-style: bold; }
    #games > .datatable--cursor { background: #0a4a8a; color: #ffffff; }
    #games > .datatable--moved { background: #5c4400; }
    #games > .datatable--selected { background: #0a4a8a; color: #ffffff; }
    #nothing { height: 1fr; content-align: center middle; text-style: bold; display: none; }
    #progress { height: 1; padding: 0 1; display: none; }
    #progress Bar > .bar--bar, #progress Bar > .bar--complete, #progress Bar > .bar--indeterminate {
        color: #1a7f37; background: #222222;
    }
    #filter-row { height: 1; padding: 0 1; }
    #filter-label { width: auto; margin-right: 1; }
    #filter { width: 1fr; height: 1; border: none; padding: 0 1; background: #222222; color: #ffffff; }
    #filter:focus { border: none; background: #333333; }
    #views { layout: horizontal; height: auto; width: 100%; border: none; background: #000000; padding: 0 1; }
    #views:focus-within { border: none; }
    #views > RadioButton { background: #000000; color: #ffffff; border: none; margin-right: 2; }
    #views > RadioButton > .toggle--button { color: #222222; background: #222222; }
    #views > RadioButton.-on > .toggle--button { color: #e5383b; background: #222222; }
    #status { height: auto; background: #1a7f37; color: #ffffff; padding: 0 1; }
    QuestionScreen { align: center middle; background: #000000 60%; }
    #question { width: 72; max-width: 100%; height: auto; max-height: 100%; background: #111111;
                border: tall #1a7f37; padding: 1 2; }
    QuestionScreen.kind-warning #question, QuestionScreen.kind-error #question { border: tall #e5383b; }
    #question-head { height: auto; }
    #question-dot { width: 2; color: #1a7f37; }
    QuestionScreen.kind-warning #question-dot, QuestionScreen.kind-error #question-dot { color: #e5383b; }
    #question-title { width: 1fr; text-style: bold; }
    #question-text { margin: 1 0 1 2; }
    #question-buttons { height: 1; margin-left: 2; }
    #question-buttons > Button { margin-right: 2; min-width: 8; background: #222222; color: #ffffff; }
    #question-buttons > Button:focus { background: #0a4a8a; text-style: bold; }
    FolderScreen { background: #000000; padding: 1 2; }
    #folder-head, #folder-path-row { height: 1; margin-bottom: 1; }
    #folder-title { width: 1fr; text-style: bold; }
    #folder-head > Button { margin-left: 2; min-width: 10; background: #222222; color: #ffffff; }
    #folder-head > Button:focus { background: #0a4a8a; text-style: bold; }
    #folder-path-label { width: auto; margin-right: 1; }
    #folder-path { width: 1fr; height: 1; border: none; padding: 0 1; background: #222222; color: #ffffff; }
    #folder-path:focus { border: none; background: #333333; }
    #folder-tree { height: 1fr; background: #000000; }
    #folder-tree > .tree--cursor { background: #0a4a8a; color: #ffffff; }
    #folder-hint { height: auto; margin-top: 1; }
    SettingsScreen { background: #000000; padding: 1 2; }
    SettingsScreen Button { background: #222222; color: #ffffff; min-width: 10; }
    SettingsScreen Button:focus { background: #0a4a8a; text-style: bold; }
    SettingsScreen Input { height: 1; border: none; padding: 0 1; background: #222222; color: #ffffff; }
    SettingsScreen Input:focus { border: none; background: #333333; }
    #settings-head { height: 1; margin-bottom: 1; }
    #settings-title { width: 1fr; text-style: bold; margin-right: 2; }
    #settings-file { height: auto; margin-bottom: 1; color: #aaaaaa; }
    #settings-head > Button { margin-left: 2; }
    #settings-columns { height: 1fr; }
    #settings-left { width: 1fr; margin-right: 2; }
    #settings-right { width: 1fr; height: 1fr; }
    #regions-row { height: auto; margin-top: 1; }
    #regions { width: 1fr; max-width: 26; height: auto; min-height: 5; max-height: 9; border: none; background: #222222; }
    #regions:focus { border: none; }
    #regions > .option-list--option-highlighted { background: #0a4a8a; color: #ffffff; }
    #region-buttons { width: 14; height: auto; margin-left: 1; }
    #region-buttons > Button { width: 100%; margin-bottom: 1; }
    #new-region-row { height: 1; margin-top: 1; }
    #new-region { width: 1fr; }
    #new-region-row > Button { margin-left: 1; width: 14; }
    #languages, #prefer { height: auto; border: none; background: #000000; margin-top: 1; }
    #languages, #played { height: auto; border: none; background: #000000; margin-top: 1; }
    #languages:focus-within, #prefer:focus-within { border: none; }
    #languages:focus-within, #played:focus-within { border: none; }
    #languages > RadioButton, #prefer > RadioButton { background: #000000; color: #ffffff; border: none; }
    #languages > RadioButton, #played > RadioButton { background: #000000; color: #ffffff; border: none; }
    #languages > RadioButton > .toggle--button, #prefer > RadioButton > .toggle--button { color: #222222; background: #222222; }
    #languages > RadioButton > .toggle--button, #played > RadioButton > .toggle--button { color: #222222; background: #222222; }
    #languages > RadioButton.-on > .toggle--button, #prefer > RadioButton.-on > .toggle--button { color: #e5383b; background: #222222; }
    #languages > RadioButton.-on > .toggle--button, #played > RadioButton.-on > .toggle--button { color: #e5383b; background: #222222; }
    #language-hint { margin: 1 0 1 0; color: #aaaaaa; }
    #tags-label { margin-bottom: 1; }
    #overview-head { height: 1; }
    #overview-keys { height: auto; margin-bottom: 1; text-align: right; }
    #overview-title { width: auto; text-style: bold; padding: 0 2 0 0; color: #3fb950; }
    .-colors16 #overview-title { color: #00aa00; }
    #overview-folder { width: 1fr; }
    #overview-table { height: 1fr; }
    #overview-buttons { height: 1; margin-top: 1; }
    #overview-buttons > Button, #overview-buttons > Checkbox { margin-right: 2; }
    #overview-full, #overview-hide { background: #000000; color: #ffffff; }
    #overview-full > .toggle--button, #overview-hide > .toggle--button { color: #222222; background: #222222; }
    #overview-full.-on > .toggle--button, #overview-hide.-on > .toggle--button { color: #e5383b; background: #222222; }
    .-colors16 #overview-full, .-colors16 #overview-hide { color: #aaaaaa; }
    .-colors16 #overview-full > .toggle--button, .-colors16 #overview-hide > .toggle--button {
        background: #000000; color: #000000; }
    .-colors16 #overview-full.-on > .toggle--button, .-colors16 #overview-hide.-on > .toggle--button {
        background: #000000; color: #ff5555; }
    #keys-notes-title { margin: 1 1 0 1; }
    #keys-notes { margin: 0 1 0 3; height: auto; }
    .keys-note { height: auto; }
    .keys-bullet { width: 2; }
    .keys-note-text { width: 1fr; height: auto; }
    #overview-status { height: 1; margin-top: 1; }
    #prefer-label { margin-top: 1; margin-bottom: 1; }
    #played-label { margin-top: 1; margin-bottom: 1; }
    #scope-row { height: auto; }
    #scope-label { width: auto; padding: 0 2 0 0; }
    #scope { height: auto; layout: horizontal; border: none; background: #000000; }
    #scope > RadioButton { background: #000000; margin-right: 2; }
    #scope-hint { height: auto; margin: 0 0 1 2; color: #aaaaaa; }
    #settings-hint { height: auto; margin-top: 1; }

    /* 16 colors and the Linux console (class -colors16, see wants_16_colors). The values are
       exactly the 16 standard colors (VGA), so that Rich turns each into its own ANSI color and
       nothing in between: #000000 black, #aa0000 red, #00aa00 green, #aa5500 brown, #0000aa blue,
       #00aaaa cyan, #aaaaaa light gray, #ff5555 bright red, #ffffff white. Backgrounds use only
       the first 8, which is all the console can show. Dark gray would become black, so fields and
       buttons are light gray, and the header is underlined. Nothing is transparent: blending
       would make colors between them. Each rule names the same ids as the normal one, which it
       must outrank. */
    .-colors16 Screen, .-colors16 #games, .-colors16 #views, .-colors16 #languages, .-colors16 #prefer,
    .-colors16 Screen, .-colors16 #games, .-colors16 #views, .-colors16 #languages, .-colors16 #played,
    .-colors16 #folder-tree, .-colors16 #question, .-colors16 QuestionScreen,
    .-colors16 FolderScreen, .-colors16 SettingsScreen { background: #000000; color: #aaaaaa; }
    /* Textual highlights the radio item under the keyboard cursor half-transparently, which would
       make a color between the 16 (the focus tint is off everywhere, see above). */
    .-colors16 #views > RadioButton.-selected, .-colors16 #languages > RadioButton.-selected,
    .-colors16 #prefer > RadioButton.-selected,
    .-colors16 #played > RadioButton.-selected,
    .-colors16 RadioButton > .toggle--label { background: #000000; }
    .-colors16 * { scrollbar-background: #000000; scrollbar-background-hover: #000000;
                   scrollbar-background-active: #000000; scrollbar-color: #aaaaaa;
                   scrollbar-color-hover: #ffffff; scrollbar-color-active: #ffffff;
                   scrollbar-corner-color: #000000; }
    /* Black on green: many terminals (PuTTY among them) show ANSI green so light that white
       text on it, such as the folder, is hard to read. */
    .-colors16 #title-row, .-colors16 #status { background: #00aa00; color: #000000; }
    .-colors16 #games > .datatable--header { background: #000000; color: #ffffff; text-style: bold underline; }
    /* ANSI 3 is brown on the Linux console but yellow in PuTTY and many others: black text on it. */
    .-colors16 #games > .datatable--moved { background: #aa5500; color: #000000; }
    .-colors16 #games > .datatable--cursor, .-colors16 #games > .datatable--selected,
    .-colors16 #folder-tree > .tree--cursor,
    .-colors16 #regions > .option-list--option-highlighted { background: #0000aa; color: #ffffff; }
    .-colors16 #filter, .-colors16 #folder-path, .-colors16 SettingsScreen Input,
    .-colors16 #regions { background: #aaaaaa; color: #000000; }
    .-colors16 #filter:focus, .-colors16 #folder-path:focus,
    .-colors16 SettingsScreen Input:focus { background: #00aaaa; color: #000000; }
    .-colors16 #filter > .input--cursor, .-colors16 #folder-path > .input--cursor,
    .-colors16 SettingsScreen Input > .input--cursor { background: #000000; color: #ffffff; text-style: none; }
    .-colors16 #filter > .input--selection, .-colors16 #folder-path > .input--selection,
    .-colors16 SettingsScreen Input > .input--selection { background: #0000aa; color: #ffffff; }
    .-colors16 #question-buttons > Button, .-colors16 #folder-head > Button,
    .-colors16 SettingsScreen Button { background: #aaaaaa; color: #000000; }
    .-colors16 #question-buttons > Button:focus, .-colors16 #folder-head > Button:focus,
    .-colors16 SettingsScreen Button:focus { background: #0000aa; color: #ffffff; }
    .-colors16 #views > RadioButton, .-colors16 #languages > RadioButton,
    .-colors16 #prefer > RadioButton { background: #000000; color: #aaaaaa; }
    .-colors16 #played > RadioButton { background: #000000; color: #aaaaaa; }
    .-colors16 #views > RadioButton > .toggle--button,
    .-colors16 #languages > RadioButton > .toggle--button,
    .-colors16 #prefer > RadioButton > .toggle--button { background: #000000; color: #000000; }
    .-colors16 #played > RadioButton > .toggle--button { background: #000000; color: #000000; }
    .-colors16 #views > RadioButton.-on > .toggle--button,
    .-colors16 #languages > RadioButton.-on > .toggle--button,
    .-colors16 #prefer > RadioButton.-on > .toggle--button { background: #000000; color: #ff5555; }
    .-colors16 #played > RadioButton.-on > .toggle--button { background: #000000; color: #ff5555; }
    .-colors16 #folder-tree > .tree--guides, .-colors16 #folder-tree > .tree--guides-hover,
    .-colors16 #folder-tree > .tree--guides-selected { color: #aaaaaa; }
    .-colors16 #question-dot { color: #00aa00; }
    .-colors16 QuestionScreen.kind-warning #question-dot,
    .-colors16 QuestionScreen.kind-error #question-dot { color: #ff5555; }
    .-colors16 #settings-file, .-colors16 #language-hint { color: #aaaaaa; }
    .-colors16 #progress Bar > .bar--bar, .-colors16 #progress Bar > .bar--complete,
    .-colors16 #progress Bar > .bar--indeterminate { color: #00aa00; background: #000000; }

    /* Only ASCII (class -ascii, see wants_ascii): no "…" when a label is too long. */
    .-ascii RadioButton, .-ascii Static, .-ascii Button { text-overflow: clip; }
    """
    BINDINGS = [
        Binding("q,escape", "escape", show=False),
        # priority: otherwise Tab would move the focus to the next widget, as usual in Textual.
        Binding("tab", "move_game(1)", show=False, priority=True),
        Binding("shift+tab", "move_game(-1)", show=False, priority=True),
        # The keys of the user's concept (2026-11-22): x delete, k keep, Enter execute, s settings,
        # f folder; the old d, p, x (proceed), e, o and the Ctrl keys of the window are gone here.
        Binding("x,X", "demote", show=False),
        Binding("o,O", "overview", show=False),
        Binding("k,K", "promote", show=False),
        Binding("n,N", "toggle_no_game", show=False),
        Binding("g,G", "report", show=False),
        Binding("w,W", "write_gamelist", show=False),
        Binding("1", "choose_view(0)", show=False),
        Binding("2", "choose_view(1)", show=False),
        Binding("3", "choose_view(2)", show=False),
        # Priority: Textual hands each key to the focused widget as soon as it arrives and only later
        # looks at the normal bindings. "/" must move the focus at once, or the letters typed right
        # after it (fast, pasted or sent by tmux) would still reach the list. In the field itself
        # check_action switches it off, so that "/" is typed there; FilterInput handles the way out.
        Binding("slash", "focus_filter", show=False, priority=True),
        # Enter opens the game view (bound in GameTable too, which would otherwise select the row);
        # the cleanup is on F12 since 2026-11-25.
        Binding("enter", "game_view", show=False),
        Binding("f12", "proceed", show=False),
        Binding("f,F", "choose_folder", show=False),
        Binding("s,S", "open_settings", show=False),
        Binding("r,R,f5", "reanalyze", show=False),
        Binding("c,C", "credits", show=False),
        # ? as well: some terminals keep F1 for their own help.
        Binding("f1,question_mark", "show_keys", show=False),
    ]

    def __init__(self, analyze, directory: Path | None, scope: str | None = None, config_file=None,
                 settings_path: Path = SETTINGS_PATH, ascii: bool = False, colors16: bool = False,
                 config_loader=None):
        super().__init__()
        self.config_loader = config_loader
        self.collection_root = None  # the roms folder of the collection; None for a folder on its own
        self._batch = None  # the running scan of all platforms: its cancel flag
        # run_tui finds both out for the terminal; tests choose them.
        self.ascii = ascii  # only ASCII characters: Linux console, terminals without UTF-8, --ascii
        self.colors16 = colors16  # ANSI colors instead of the window's: 16 colors, Linux console
        self._scrollbar_renderer = None
        self.analyze = analyze
        self.directory = directory
        self.config_file = config_file
        self.settings_path = settings_path
        # An explicit choice at startup takes precedence over the saved state, as in the window.
        self.scope = scope or load_scope(settings_path)
        self.review = None
        self.game_info = {}  # rom -> what the database knows about it (gamelist.xml, media)
        self.files = {}  # row key -> (game, file)
        self._analysis = 0  # Counts analyses, so that a replaced one cannot overwrite the newer result.
        self._visible = []  # the games shown, in the order of the list
        self._file_keys = {}  # id(entry) -> row key; stays the same for the whole analysis
        self._game_numbers = {}  # id(result) -> the game's number in the row keys
        self.pattern = ""  # the filter the list shows; the field may hold newer text during the delay
        self._filter_timer = None
        self.deleting = False  # While files are deleted in the background, nothing may change the list.
        self.had_errors = False  # A file could not be deleted: the program ends with exit code 1.

    def compose(self) -> ComposeResult:
        with Horizontal(id="title-row"):
            yield Static(APP_NAME, id="title")
            yield Static(self._folder_text(), id="folder", markup=False)
        with Horizontal(id="info-row"):
            yield Static("", id="info", markup=False)
            yield ShortKeys("list", id="short-keys")
        yield Static("", id="gamelist-line", markup=False)
        table = GameTable(id="games", cursor_type="row", zebra_stripes=False)
        table.add_column(_cell(tr("window.column.file")), key="file")
        table.add_column(_cell(tr("window.column.size"), justify="right"), key="size")
        table.add_column(_cell(tr("window.column.note")), key="note")
        yield table
        # Blinks with the terminal's own blinking (SGR 5), as it blinks in the window. In the text
        # itself: Textual 8.2.8 drops "blink" from a widget's text-style on the way to the screen.
        yield Static(Text(tr("window.nothing_to_do"), style="bold blink"), id="nothing")
        yield ProgressBar(id="progress", show_eta=False)
        with Horizontal(id="filter-row"):
            yield Static(tr("window.filter"), id="filter-label", markup=False)
            yield FilterInput(id="filter", select_on_focus=True)
        # Above the green row, as in the window; 1, 2 and 3 choose the same views.
        with RadioSet(id="views"):
            for value, label in SCOPES:
                button = RadioButton(tr(label), value=value == self.scope, id=f"view-{value}")
                yield _plain_radio(button) if self.ascii else button
        yield Static("", id="status", markup=False)

    def on_mount(self) -> None:
        if self.colors16:
            self.add_class("-colors16")
        if self.ascii:
            self.add_class("-ascii")
            self.query_one("#progress", ProgressBar).query_one("Bar").bar_renderable = AsciiBar
            # Class-wide in Textual; set back in on_unmount, so that it stays with this program run.
            self._scrollbar_renderer = ScrollBar.renderer
            ScrollBar.renderer = AsciiScrollBarRender
        # Not focusable: the keys must keep acting on the list after a view was clicked.
        self.query_one("#views", RadioSet).can_focus = False
        self.query_one("#games", GameTable).focus()
        directory = self.directory
        if directory is None and self.config_loader is not None:
            directory = load_last_collection(self.settings_path)
        if directory is None:
            self._set_status(tr("window.choose_folder_status"))
            self.call_after_refresh(self.action_choose_folder)  # as the window does at the start
        elif self.config_loader is not None and _is_collection(directory):
            self.call_after_refresh(self.open_folder, directory)  # the overview, once the list is built
        else:
            self.open_folder(directory)  # at once, as before: the analysis starts right away

    def on_unmount(self) -> None:
        if self._scrollbar_renderer is not None:
            ScrollBar.renderer = self._scrollbar_renderer
            self._scrollbar_renderer = None

    # Analysis ---------------------------------------------------------------------------------

    def start_analysis(self, rescan: bool = False, full: bool = False) -> None:
        """Analyzes in a background thread, so that the terminal does not hang while reading large ZIPs."""
        self._analysis += 1
        number = self._analysis
        self.review = None
        self._clear_list()
        self._set_status(tr("window.analyzing"))
        progress = self.query_one("#progress", ProgressBar)
        progress.update(total=None, progress=0)
        progress.display = True

        directory = self.directory  # A folder chosen meanwhile starts an analysis of its own.

        def report(done: int, total: int) -> None:
            self.call_from_thread(self._show_progress, number, done, total)

        def work() -> None:
            try:
                review = _call_analyze(self.analyze, directory, report, rescan, full)
            except Exception as error:  # Every error must reach the screen, otherwise it would stay at "Analyzing".
                self.call_from_thread(self._finish_analysis, number, None, str(error) or type(error).__name__)
            else:
                self.call_from_thread(self._finish_analysis, number, review, None)

        self.run_worker(work, thread=True, group="analysis", exit_on_error=False)

    def _show_progress(self, number: int, done: int, total: int) -> None:
        if number != self._analysis:
            return
        self.query_one("#progress", ProgressBar).update(total=max(total, 1), progress=done)
        self._set_status(tr("window.analyzing_progress", done=done, total=total))

    def _finish_analysis(self, number: int, review, error: str | None) -> None:
        if number != self._analysis:
            return  # A newer analysis has replaced this one.
        self.query_one("#progress", ProgressBar).display = False
        if error:
            self._set_status(tr("window.analysis_failed", error=error))
            self.show_message("error", tr("window.analysis_failed_title"), error)
            return
        self.show_review(review)

    def show_review(self, review) -> None:
        self.review = review
        review.confirm_save_files(review.confirmed_saves(self.settings_path))
        # Row keys follow the game's place among all games, so that they stay the same in every view.
        self._file_keys = {}
        self._game_numbers = {}
        for game_index, result in enumerate(review.results):
            self._game_numbers[id(result)] = game_index
            for file_index, entry in enumerate(result.keep + result.marked):
                self._file_keys[id(entry)] = f"g{game_index}f{file_index}"
        from workbench_db import gamelist_summary, load_game_info, platform_label

        self.game_info = load_game_info(self.directory)
        green = _green(self)
        summary = gamelist_summary(self.directory)
        self.query_one("#info", Static).update(
            Text.assemble((tr("window.platform"), f"bold {green}"), " ", (platform_label(self.directory), "bold")))
        line = self.query_one("#gamelist-line", Static)  # a gray line of its own below
        line.update(summary)
        line.display = bool(summary)
        self.show_games()

    # The list ---------------------------------------------------------------------------------

    def _clear_list(self) -> None:
        self.files = {}
        table = self.query_one("#games", GameTable)
        table.clear()
        table.set_selection(())
        self._show_nothing_to_do(False)

    def show_games(self, keep_selection: bool = False) -> None:
        """Fills the list with the games of the current view, as the window does.

        With keep_selection, the rows that are still shown stay selected (after changing the view).
        """
        table = self.query_one("#games", GameTable)
        previous = self.selected_keys() if keep_selection else []
        table.clear()
        table.set_selection(())
        self.files = {}
        self._visible = []
        review = self.review
        flags = scope_flags(self.scope, self.pattern)
        if review.nothing_to_do() and not flags[1]:
            self._show_nothing_to_do(True)
            self._set_status(tr("window.nothing_to_do_status"))
            return
        self._show_nothing_to_do(False)
        self._visible = [result for result in review.results if review.is_visible(result, *flags)]
        self._fill_table()
        keys = set(self._keys())
        previous = [key for key in previous if key in keys]
        if previous:
            self._place_cursor(previous[-1], previous)
        else:
            self._select_first_file()
        self._update_status()

    def _show_title_column(self, shown: bool) -> None:
        table = self.query_one("#games", GameTable)
        present = ColumnKey("title") in table.columns
        if shown and not present:
            table.add_column(_cell(tr("window.column.title")), key="title")
        elif not shown and present:
            table.remove_column(ColumnKey("title"))
            table.title_width = 0

    def _fill_table(self) -> None:
        from workbench_view import list_title

        table = self.query_one("#games", GameTable)
        table.clear()
        titled = any(list_title(info) for info in self.game_info.values())
        self._show_title_column(titled)
        self.files = {}
        moved = set()
        rows = []  # (cells, key); collected first, so that the column widths are known before adding
        for place, result in enumerate(self._visible):
            game_index = self._game_numbers[id(result)]
            if place:
                # An empty row between the games: a drawn line would widen the file column to its length.
                rows.append((("", "", "", "")[:4 if titled else 3], f"s{game_index}"))
            # The title row: bold, and dashes up to the right edge, so that a new game stands out.
            problems = "; ".join(result.problems)
            cells = (DashLine(f" {result.title} "), DashLine(), DashLine(f" {problems} " if problems else ""))
            rows.append((cells + ((DashLine(),) if titled else ()), f"g{game_index}"))
            # Kept files green, marked files red, as in the window; with 16 colors the ANSI ones.
            keep_color, marked_color = ("#00aa00", "#ff5555") if self.colors16 else ("#3fb950", "#ff6b6b")
            entries = [("k", "window.section.keep", "+", f"bold {keep_color}", "window.by_hand_keep", result.keep),
                       ("h", "window.section.marked", "-", marked_color, "window.by_hand_delete", result.marked)]
            for suffix, label, sign, color_style, moved_note, group in entries:
                if not group:
                    continue
                rows.append(((_cell("  " + tr(label)), "", "", "")[:4 if titled else 3], f"g{game_index}{suffix}"))
                for entry in group:
                    key = self._file_keys[id(entry)]
                    self.files[key] = (result, entry)
                    if entry.moved:
                        moved.add(key)
                    notes = ([tr(moved_note)] if entry.moved else []) + list(entry.notes)
                    # With 16 colors a moved row is black on brown (yellow in PuTTY): no green or red there.
                    style = color_style
                    if entry.moved and self.colors16:
                        style = "bold" if color_style.startswith("bold") else ""
                    cells = (
                        _cell(f"    {sign} {entry.path.name}", style=style),
                        _cell(format_kb(entry.size()), justify="right", style=style),
                        _cell("; ".join(notes), style="italic") if notes else "",
                    )
                    if titled:
                        title = list_title(self.game_info.get(entry.path.name), ascii=self.ascii)
                        cells += (_cell(title, style=style) if title else "",)
                    rows.append((cells, key))
        widths = [0] * len(table.ordered_columns)
        for cells, _key in rows + [((column.label for column in table.ordered_columns), None)]:
            for index, cell in enumerate(cells):
                text = cell.text if isinstance(cell, DashLine) else str(cell)
                widths[index] = max(widths[index], cell_len(text))
        table.natural = tuple(widths[:3])
        table.title_width = min(widths[3], 40) if titled else 0
        layout = table.column_layout()
        table.apply_layout(layout)
        # Wrapping rows take as many lines as they need; otherwise every row has one line.
        height = None if layout[3] else 1
        for cells, key in rows:
            if layout[3]:  # wrapped lines go on below the text, not at the edge of the column
                cells = tuple(_hanging(cell, width) if isinstance(cell, Text) and index != 1 else cell
                              for index, (cell, width) in enumerate(zip(cells, layout[:3]))) + tuple(cells[3:])
            table.add_row(*cells, key=key, height=height)
        table.set_moved(moved)
        # A vertical scroll bar may come or go with these rows and change the width.
        table.call_after_refresh(self.list_resized)

    def list_resized(self) -> None:
        """Lays the list out again when the terminal's width calls for other columns."""
        table = self.query_one("#games", GameTable)
        if (self._list_shown() and table.columns_layout is not None
                and table.column_layout() != table.columns_layout):
            self._redraw_keeping_place()

    def _redraw_keeping_place(self, fallback: str | None = None) -> None:
        """Fills the list again; cursor, selection and scroll position stay where they were."""
        table = self.query_one("#games", GameTable)
        cursor, selection, scroll = self.cursor_key(), table.selected, table.scroll_y
        self._fill_table()
        keys = self._keys()
        if cursor not in keys:  # The section row under the cursor has disappeared.
            cursor = fallback if fallback in keys else (keys[0] if keys else None)
        table.set_selection({key for key in selection if key in keys})
        table.scroll_to(y=scroll, animate=False, immediate=True)
        if cursor is not None:
            table.move_cursor(row=table.get_row_index(cursor), scroll=False)

    # Views ------------------------------------------------------------------------------------

    def action_choose_view(self, number: int) -> None:
        self.query_one(f"#view-{SCOPES[number][0]}", RadioButton).value = True  # reaches on_radio_set_changed

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        scope = event.pressed.id.removeprefix("view-")
        if scope != self.scope:
            self.set_scope(scope)

    def set_scope(self, scope: str) -> None:
        """Shows the view and remembers it for the next start, as in the window."""
        self.scope = scope
        if self.review is not None:
            self.show_games(keep_selection=True)
        try:
            save_scope(self.settings_path, scope)
        except OSError as error:
            self.show_message("error", tr("window.choice_not_saved"), str(error))

    def _update_status(self) -> None:
        self._set_status(self.review.status(*scope_flags(self.scope, self.pattern)))

    # Filter -----------------------------------------------------------------------------------

    def _filter_focused(self) -> bool:
        return isinstance(self.focused, FilterInput)

    def _focus_now(self, widget) -> None:
        """Moves the focus at once. focus() waits for the next round of the event loop, and keys
        typed fast (or sent by tmux, or pasted) would still reach the old place: a "d" typed right
        after "/" would then mark a file instead of going into the filter."""
        widget.screen.set_focus(widget)

    def action_focus_filter(self) -> None:
        field = self.query_one("#filter", FilterInput)
        self._focus_now(field)
        field.select_all()

    def action_leave_filter(self, clear: bool = False) -> None:
        """Shows the result at once and returns to the list; Esc also clears the filter."""
        field = self.query_one("#filter", FilterInput)
        if clear:
            field.value = ""
        self._apply_filter()
        self._focus_now(self.query_one("#games", GameTable))

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._filter_timer is not None:
            self._filter_timer.stop()
        self._filter_timer = self.set_timer(FILTER_DELAY, self._apply_filter)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_leave_filter()

    def _apply_filter(self) -> None:
        if self._filter_timer is not None:
            self._filter_timer.stop()
            self._filter_timer = None
        fields = self.query("#filter")
        if not fields:  # The timer ran out while the program was ending.
            return
        pattern = fields.first(FilterInput).value
        if pattern == self.pattern or self.deleting:  # After deleting, the list is redrawn anyway.
            return
        self.pattern = pattern
        # Rows hidden by the filter leave the selection; D and P should work on what is shown.
        if self.review is not None:
            self.show_games(keep_selection=True)

    # D and P ----------------------------------------------------------------------------------

    def action_demote(self) -> None:
        self._move_selected("demote")

    def action_promote(self) -> None:
        self._move_selected("promote")

    def _move_selected(self, move_name: str) -> None:
        """Moves the selected files between Keep and Marked; the selection and the view stay."""
        if not self._list_shown():
            return
        move = getattr(self.review, move_name)
        rows = [key for key in self.selected_keys() if key in self.files]
        changed = False
        for key in rows:
            result, entry = self.files[key]
            changed = move(result, entry) or changed
        if not changed:
            return
        self._redraw_keeping_place(fallback=rows[-1])
        self._update_status()

    # Proceed ----------------------------------------------------------------------------------

    def action_proceed(self) -> None:
        """x and Ctrl+L delete the marked files after a question, as Proceed does in the window."""
        if self.review is None or self.deleting:
            return
        if not self.review.has_work():
            self._confirm_save_files_only()
            return
        message = self.review.confirm_message(*scope_flags(self.scope, self.pattern))
        self.ask("warning", tr("window.delete_title"), message, then=self._delete_if_yes)

    def _delete_if_yes(self, yes) -> None:
        if not yes or self.review is None or self.deleting:
            return
        # Taken before deleting: Afterwards they are remembered as legitimate.
        save_files = self.review.save_file_keys()
        review = self.review
        self._lock_for_deleting(True)
        last_redraw = 0.0

        def report(done: int, total: int) -> None:
            nonlocal last_redraw
            now = time.monotonic()
            if done not in (0, total) and now - last_redraw < DELETE_REDRAW:
                return
            last_redraw = now
            self.call_from_thread(self._show_delete_progress, done, total)

        def work() -> None:
            try:
                deleted, errors = review.delete(report)
            except Exception as error:  # The list must not stay locked, whatever happens.
                deleted, errors = 0, [str(error) or type(error).__name__]
            self.call_from_thread(self._finish_delete, review, save_files, deleted, errors)

        self.run_worker(work, thread=True, group="delete", exit_on_error=False)

    def _lock_for_deleting(self, locked: bool) -> None:
        self.deleting = locked
        self.query_one("#filter", FilterInput).disabled = locked
        self.query_one("#views", RadioSet).disabled = locked
        progress = self.query_one("#progress", ProgressBar)
        progress.update(total=None, progress=0)
        progress.display = locked
        if locked:
            self._set_status(tr("window.deleting_progress", done=0, total=0))
        else:
            self.query_one("#games", GameTable).focus()

    def _show_delete_progress(self, done: int, total: int) -> None:
        self.query_one("#progress", ProgressBar).update(total=max(total, 1), progress=done)
        self._set_status(tr("window.deleting_progress", done=done, total=total))

    def _finish_delete(self, review, save_files: dict[str, int], deleted: int, errors: list[str]) -> None:
        self._lock_for_deleting(False)
        # Before redrawing: show_review reads the confirmed files back from the settings file.
        not_remembered = self._remember_save_files(save_files)
        # The Review object has dropped the deleted files; the folder is not analyzed again.
        self.show_review(review)
        self._apply_filter()  # A filter typed just before deleting.
        # The offer to write the gamelist.xml anew lies below the message, so it comes after it.
        from workbench_db import collection_root
        from workbench_gamelist import find_gamelist

        if (deleted and self.directory is not None and collection_root(self.directory) is not None
                and find_gamelist(self.directory) is not None):
            self.write_gamelist(self.directory, after_cleanup=True)
        if errors:
            self.had_errors = True
            self.show_message("warning", tr("window.partly_deleted_title"),
                              tr("window.partly_deleted", count=deleted, errors="\n".join(errors)))
        else:
            self.show_message("info", tr("window.deleted_title"), review.done_message(deleted))
        if not_remembered:  # On top, so that it is read first.
            self.show_message("error", tr("window.saves_not_remembered"), not_remembered)

    def _confirm_save_files_only(self) -> None:
        """Without marked files, x and Ctrl+L can still confirm the suspected status or save files."""
        save_files = self.review.save_file_keys()
        if not save_files:
            self.show_message("info", tr("window.nothing_to_delete_title"), tr("window.nothing_to_delete"))
            return

        def confirm(yes) -> None:
            if yes and self.review is not None:
                not_remembered = self._remember_save_files(save_files)
                self.show_review(self.review)
                if not_remembered:
                    self.show_message("error", tr("window.saves_not_remembered"), not_remembered)

        self.ask("question", tr("window.confirm_saves_title"), tr("window.confirm_saves", count=len(save_files)),
                 then=confirm)

    def _remember_save_files(self, save_files: dict[str, int]) -> str | None:
        """Writes the confirmed files into the settings file; returns the error, if there is one."""
        if not save_files:
            return None
        try:
            self.review.remember_save_files(self.settings_path, save_files)
        except OSError as error:
            return str(error)
        return None

    # Credits ----------------------------------------------------------------------------------

    def action_credits(self) -> None:
        """c: who had the idea and who programmed it, the license and the warning."""
        self.show_message("info", tr("credits.title"), tr("credits.text") + "\n\n" + tr("credits.license"))

    # Analyze again ----------------------------------------------------------------------------

    def action_reanalyze(self) -> None:
        """r and F5 read the folder and the configuration again, as F5 does in the window."""
        if self.directory is None or self.deleting:
            return
        if self.review is not None and self.review.moved_count():
            self.ask("question", tr("window.discard_title"), tr("window.discard_reanalyze"),
                     then=lambda yes: self.start_analysis(rescan=True) if yes else None)
        else:
            self.start_analysis(rescan=True)

    # Folder choice ----------------------------------------------------------------------------

    def action_choose_folder(self) -> None:
        """o and Ctrl+O choose the folder in place of the list; after changes by hand they ask first."""
        if self.folder_open() or self.deleting:
            return
        if self.review is not None and self.review.moved_count():
            self.ask("question", tr("window.discard_title"), tr("window.discard_folder"),
                     then=lambda yes: self._open_folder_choice() if yes else None)
        else:
            self._open_folder_choice()

    def _open_folder_choice(self) -> None:
        if not self.folder_open():
            self.push_screen(FolderScreen(self.directory), self.folder_chosen)

    def folder_chosen(self, folder: Path | None) -> None:
        """The analysis starts once a folder is chosen; Cancel leaves everything as it was."""
        if folder is None:
            if self.review is None and self.collection_root is not None:
                self.action_overview()  # Cancel from the overview goes back to it
            return
        self.open_folder(folder)

    def open_folder(self, folder: Path) -> None:
        """A roms folder opens its overview; any other folder is analyzed on its own, as before.

        Either way the folder opens again at the next start without a folder.
        """
        from workbench_db import is_collection

        if self.config_loader is not None:
            save_last_collection(self.settings_path, folder)
        if self.config_loader is not None and is_collection(folder):
            self.collection_root = folder
            self.action_overview()
            return
        self.collection_root = None
        self.directory = folder
        self.query_one("#folder", Static).update(self._folder_text())
        self.query_one("#games", GameTable).focus()
        self.start_analysis()

    # The overview -----------------------------------------------------------------------------

    def _settings_platform(self):
        """(roms folder, platform) while a platform of a collection is open; else (None, None)."""
        root, directory = self.collection_root, self.directory
        if root is not None and directory is not None and directory != root and directory.parent == root:
            return root, directory.name
        return None, None

    def overview_open(self) -> bool:
        return isinstance(self.screen, OverviewScreen)

    async def action_escape(self) -> None:
        """q and Esc: from a platform of a collection back to the overview (there they end); otherwise end."""
        if self.collection_root is not None and not self.question_open() and len(self.screen_stack) == 1:
            self.action_overview()
        else:
            await self.action_quit()

    def action_overview(self) -> None:
        """o: the platforms of the collection; after changes by hand it asks first."""
        if self.collection_root is None or self.overview_open() or self.deleting or len(self.screen_stack) > 1:
            return
        if self.review is not None and self.review.moved_count():
            self.ask("question", tr("window.discard_title"), tr("window.discard_folder"),
                     then=lambda yes: self._show_overview() if yes else None)
        else:
            self._show_overview()

    def _show_overview(self, message: str | None = None) -> None:
        from workbench_db import overview

        self._analysis += 1  # a running analysis no longer counts
        self.query_one("#progress", ProgressBar).display = False
        self.review = None
        self._clear_list()
        self.directory = self.collection_root
        self.query_one("#folder", Static).update(self._folder_text())
        try:
            rows = overview(self.collection_root, self.config_loader())
        except (OSError, ValueError) as error:
            self.show_message("error", tr("window.analysis_failed_title"), str(error))
            return
        self.push_screen(OverviewScreen(self.collection_root, rows, message), self._overview_closed)

    def _overview_closed(self, choice) -> None:
        if choice == "folder":
            self._open_folder_choice()
        elif choice:
            platform, rescan, full = choice
            self.directory = self.collection_root / platform
            self.query_one("#folder", Static).update(self._folder_text())
            self.query_one("#games", GameTable).focus()
            self.start_analysis(rescan=rescan, full=full)

    def scan_all(self, screen: OverviewScreen, full: bool) -> None:
        """Scans every platform in a background thread; each is saved at once; nothing is deleted."""
        import threading

        from workbench_db import ScanCancelled, scan_all

        cancel = threading.Event()
        self._batch = cancel
        screen.set_scanning(True)
        root = self.collection_root
        try:
            config = self.config_loader()
        except (OSError, ValueError) as error:
            self._batch = None
            screen.set_scanning(False)
            screen.show_status(tr("window.analysis_failed", error=str(error) or type(error).__name__))
            return

        def report(platform, number, count, done, total):
            if cancel.is_set():
                raise ScanCancelled
            self.call_from_thread(screen.show_status, tr("overview.scanning", platform=platform, done=done,
                                                         total=total, number=number, count=count))

        def work() -> None:
            try:
                finished = scan_all(root, full=full, progress=report, config=config,
                                    finished_row=lambda row: self.call_from_thread(screen.set_row, row))
                message = tr("overview.scan_finished", count=len(finished))
            except ScanCancelled:
                message = tr("overview.scan_cancelled")
            except Exception as error:  # every error must reach the screen
                message = tr("window.analysis_failed", error=str(error) or type(error).__name__)
            self.call_from_thread(self._scan_all_finished, screen, message)

        self.run_worker(work, thread=True, group="scan-all", exit_on_error=False)

    def cancel_scan_all(self) -> None:
        if self._batch is not None:
            self._batch.set()

    def _scan_all_finished(self, screen: OverviewScreen, message: str) -> None:
        self._batch = None
        if self.screen is screen:
            self.pop_screen()
        self._show_overview(message)

    # Settings ---------------------------------------------------------------------------------

    def action_open_settings(self) -> None:
        """e and Ctrl+E show the settings in place of the list; Esc or Ctrl+E again close them."""
        if self.config_file is None or self.settings_open() or self.folder_open() or self.deleting:
            return
        try:
            screen = SettingsScreen(self.config_file, *self._settings_platform())
        except ValueError as error:
            # A broken file is not overwritten: It may contain entries the settings do not know.
            self.show_message("error", tr("settings.error_title"), str(error))
            return
        self.push_screen(screen, lambda _result: self._focus_now(self.query_one("#games", GameTable)))

    def save_settings(self, screen: SettingsScreen) -> None:
        """Writes the settings, as the window does; a new priority or new tags take effect at once."""
        from workbench_db import save_settings_for

        language, regions, tags = screen.language_code(), screen.region_list(), screen.tag_list()
        prefer_zip, prefer_played = screen.prefers_zip(), screen.prefers_played()
        before = screen.values
        rules_changed = (regions != before["region_priority"] or tags != before["delete_tags"]
                         or prefer_zip != before["prefer_zip"] or prefer_played != before["prefer_played"]
                         or screen.own != screen.own_before)

        def write() -> None:
            try:
                save_settings_for(self.config_file, screen.root_folder, screen.platform, screen.own, language,
                                  regions, tags, prefer_zip, prefer_played)
            except (OSError, ValueError) as error:
                self.show_message("error", tr("settings.error_title"), str(error))  # the settings stay open
                return
            screen.dismiss(None)
            if language != before["language"]:
                # The open program keeps its language, so that the list and its notes match.
                self.show_message("info", tr("settings.restart_title"), tr("settings.language_hint"))
            if rules_changed and self.directory is not None:
                self.start_analysis()

        if rules_changed and self.review is not None and self.review.moved_count():
            self.ask("question", tr("window.discard_title"), tr("settings.discard"),
                     then=lambda yes: write() if yes else None)
        else:
            write()

    # Cursor and selection ---------------------------------------------------------------------

    def _keys(self) -> list[str]:
        return [row.key.value for row in self.query_one("#games", GameTable).ordered_rows]

    def cursor_key(self) -> str | None:
        """The row under the cursor; None when the list is empty."""
        table = self.query_one("#games", GameTable)
        if not table.row_count:
            return None
        return table.ordered_rows[table.cursor_row].key.value

    def selected_keys(self) -> list[str]:
        """The selected rows from top to bottom (D and P will work on the file rows among them)."""
        selected = self.query_one("#games", GameTable).selected
        return [key for key in self._keys() if key in selected]

    def _place_cursor(self, key: str, selection) -> None:
        table = self.query_one("#games", GameTable)
        table.set_selection(selection)
        table.move_cursor(row=table.get_row_index(key))

    def _select_first_file(self) -> None:
        first = next((key for key in self._keys() if key in self.files), None)
        if first:
            self._place_cursor(first, {first})

    def action_move_cursor(self, step: int, extend: bool) -> None:
        """Moves the selection across the empty rows; with extend it grows or shrinks, as in the window."""
        if not self._list_shown():
            return
        keys = self._keys()
        current = self.cursor_key()
        index = keys.index(current) + step
        while 0 <= index < len(keys) and _game_of(keys[index]) is None:
            index += step
        if not 0 <= index < len(keys):
            return
        target = keys[index]
        selected = set(self.query_one("#games", GameTable).selected)
        if not extend:
            selected = {target}
        elif target in selected:
            selected.discard(current)  # Backwards: The selection shrinks again.
        else:
            selected.add(target)
        self._place_cursor(target, selected)

    def action_move_game(self, step: int) -> None:
        """Jumps to the neighboring game and selects its first file, so that D and P work at once."""
        if not self._list_shown():
            return
        keys = self._keys()
        current = self.cursor_key()
        game = _game_of(current) if current else None
        if game is None and current:
            game = _game_of(keys[keys.index(current) - 1])  # an empty row belongs to the game above it
        games = sorted({_game_of(key) for key in keys} - {None})
        if not games:
            return
        place = games.index(game) + step if game is not None else 0
        if not 0 <= place < len(games):
            return
        target = games[place]
        rows = [key for key in keys if _game_of(key) == target]
        row = next((key for key in rows if key in self.files), rows[0])
        self._place_cursor(row, {row})
        table = self.query_one("#games", GameTable)
        # First the end, then the title: This shows the whole game if it fits.
        table.call_after_refresh(self._show_rows, rows[-1], rows[0])

    def _show_rows(self, *keys: str) -> None:
        table = self.query_one("#games", GameTable)
        for key in keys:
            if key in table.rows:
                _x, y, width, height = table._get_row_region(table.get_row_index(key))
                region = Region(int(table.scroll_x), y, width, height)
                table.scroll_to_region(region, animate=False, spacing=table._get_fixed_offset(), force=True,
                                       immediate=True)

    def _list_shown(self) -> bool:
        return self.review is not None and self.query_one("#games", GameTable).row_count > 0

    def _show_nothing_to_do(self, shown: bool) -> None:
        self.query_one("#games", DataTable).display = not shown
        self.query_one("#nothing", Static).display = shown

    # Questions and messages -------------------------------------------------------------------

    def ask(self, kind: str, title: str, message: str, buttons=YES_NO, default=False, then=None) -> None:
        """Shows a question over the list; then(value) receives the answer.

        Textual cannot wait here as Tk does, so the answer arrives in the callback. Meanwhile the
        list is locked (check_action), so that nothing changes behind the question.
        """
        self.push_screen(QuestionScreen(kind, title, message, buttons, default), then)

    def show_message(self, kind: str, title: str, message: str, then=None) -> None:
        self.ask(kind, title, message, OK, None, then)

    def question_open(self) -> bool:
        return isinstance(self.screen, QuestionScreen)

    def folder_open(self) -> bool:
        return any(isinstance(screen, FolderScreen) for screen in self.screen_stack)

    def settings_open(self) -> bool:
        return any(isinstance(screen, SettingsScreen) for screen in self.screen_stack)

    def keys_open(self) -> bool:
        return isinstance(self.screen, (KeysScreen, InfoScreen, EditScreen))

    # Game information: i, n and g in the list --------------------------------------------------

    def _in_collection(self) -> bool:
        """The open folder is a platform of a roms folder (from its overview or opened on its own)."""
        from workbench_db import collection_root

        return self.directory is not None and collection_root(self.directory) is not None

    def _highlighted(self):
        key = self.cursor_key()
        if key in self.files:
            return self.files[key]
        rows = [key for key in self.selected_keys() if key in self.files]
        return self.files[rows[-1]] if rows else None

    def action_game_view(self) -> None:
        self._open_info("game")

    def action_report(self) -> None:
        self._open_info("report")

    def _open_info(self, kind: str) -> None:
        """i: everything known about the highlighted game; g: the platform's gamelist report."""
        from workbench_db import gamelist_report
        from workbench_view import game_blocks, report_blocks

        if self.review is None:
            return
        if not self._in_collection():
            self._set_status(tr("game.only_collection"))
            return
        if kind == "game":
            highlighted = self._highlighted()
            if highlighted is None:
                self._set_status(tr("game.no_selection"))
                return
            title, subtitle, blocks = game_blocks(*highlighted, self.game_info, lambda entry: format_kb(entry.size()))
        else:
            title, subtitle = tr("report.title", platform=self.directory.name), ""
            blocks = report_blocks(gamelist_report(self.directory))
        self.push_screen(InfoScreen(kind, title, subtitle, blocks), self._info_closed)

    def _info_closed(self, result) -> None:
        if result == "edit":
            self._open_edit()
        else:
            self._focus_now(self.query_one("#games", GameTable))

    def _open_edit(self) -> None:
        highlighted = self._highlighted()
        if highlighted is None:
            return
        info = self.game_info.get(highlighted[1].path.name)
        if info is not None and info.get("kind") == "no_game":
            self._set_status(tr("game.no_game"))
            return
        self.push_screen(EditScreen(highlighted[1].path.name, info), self._edit_closed)

    def _edit_closed(self, changed) -> None:
        """Back in the game view, saved or not."""
        if changed is not None:
            self._set_status(tr("game.edit.saved", count=len(changed)) if changed else tr("game.edit.unchanged"))
        self._open_info("game")

    def save_edit(self, screen: "EditScreen") -> None:
        """Saves the form; a wrong value is named and the form stays open."""
        from workbench_db import edit_game, load_game_info

        try:
            changed = edit_game(self.directory, screen.file_name, screen.values())
        except (OSError, ValueError) as error:
            self.show_message("error", tr("game.edit.error_title"), str(error))
            return
        self.game_info = load_game_info(self.directory)
        self._redraw_keeping_place()
        screen.dismiss(changed)

    def action_write_gamelist(self) -> None:
        if self.review is not None and self.directory is not None:
            self.write_gamelist(self.directory)

    def write_gamelist(self, directory, after_cleanup: bool = False, then=None) -> None:
        """Asks, then writes the platform's gamelist.xml from the database; then() after writing."""
        from workbench_db import collection_root, writable_entries, write_gamelist
        from workbench_gamelist import GAMELIST_NAME

        directory = Path(directory)
        if collection_root(directory) is None:
            self._set_status(tr("game.only_collection"))
            return
        count = writable_entries(directory)
        if not count:
            if not after_cleanup:
                self.show_message("info", tr("gamelist.write_title"), tr("gamelist.nothing_to_write",
                                                                         platform=directory.name))
            return
        question = tr("gamelist.offer_after_cleanup" if after_cleanup else "gamelist.write_question",
                      platform=directory.name, count=count)
        from workbench_db import gamelist_path

        target = gamelist_path(directory)
        if target.parent != directory:  # ES-DE or RetroPie keep it outside the platform folder
            question += "\n\n" + tr("gamelist.from", path=target)
        if target.exists():
            question += "\n\n" + tr("gamelist.backup_note")

        def answered(yes) -> None:
            if not yes:
                return
            try:
                written, _backup = write_gamelist(directory)
            except (OSError, ValueError) as error:
                self.show_message("error", tr("gamelist.write_title"), tr("gamelist.write_failed", error=error))
                return
            if then is not None:  # first: refilling the overview would replace the message
                then()
            text = tr("gamelist.written", platform=directory.name, count=written)
            if self.overview_open():
                self.screen.show_status(text)
            else:
                if self.review is not None:
                    self.show_review(self.review)  # the gray line below the platform
                self._set_status(text)

        self.ask("question", tr("gamelist.write_title"), question, then=answered)

    def action_toggle_no_game(self) -> None:
        """n: the selected files are no game (BIOS files, say), or games again."""
        from workbench_db import load_game_info, toggle_no_game

        if not self._list_shown():
            return
        rows = [key for key in self.selected_keys() if key in self.files]
        if not rows:
            return
        if not self._in_collection():
            self._set_status(tr("game.only_collection"))
            return
        names = [self.files[key][1].path.name for key in rows]
        no_game = toggle_no_game(self.directory, names)
        self.game_info = load_game_info(self.directory)
        self._redraw_keeping_place(fallback=rows[-1])
        self._set_status(tr("game.now_no_game" if no_game else "game.now_game", count=len(names)))

    def action_show_keys(self) -> None:
        """F1 and ?: all keys of the list or the overview; F1, ? or Esc close them again."""
        context = "overview" if self.overview_open() else "list"
        self.push_screen(KeysScreen(context, self.collection_root is not None))

    def check_action(self, action: str, parameters) -> bool | None:
        if self.keys_open():
            return False  # the key overview closes itself; nothing acts behind it
        # In the folder choice or the settings, a "d" or "x" must not act on the list behind them.
        locked = self.question_open() or self.deleting or self.folder_open() or self.settings_open()
        if action == "show_keys" and (locked or self._filter_focused()):
            return False  # in the filter "?" is a wildcard
        if action in _LIST_ACTIONS and locked:
            return False
        if action in ("focus_filter", "move_game") and self._filter_focused():
            # "/" typed in the field is a "/", Ctrl+F there selects the text, and Tab reaches
            # FilterInput, which leaves the field in the order the keys were typed.
            return False
        if action in ("quit", "escape") and self.deleting:  # Half a deletion must not be left behind unreported.
            return False
        return True

    async def action_quit(self) -> None:
        """q and Esc end the program; after changes by hand they ask first, as the window does."""
        if self.question_open():
            self.screen.action_answer_last()  # Ctrl+Q answers an open question like Esc.
        elif self.review is not None and self.review.moved_count():
            self.ask("question", tr("window.discard_title"), tr("window.discard_close"),
                     then=lambda close: self.exit() if close else None)
        else:
            self.exit()

    # Helpers ----------------------------------------------------------------------------------

    def _folder_text(self) -> str:
        # Not the window's text: that names Ctrl+O, here the key is f.
        return tr("window.folder", directory=self.directory) if self.directory else tr("tui.no_folder")

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)


def run_tui(analyze, directory: Path | None, scope: str | None = None, config_file=None,
            ascii: bool | None = None, config_loader=None) -> int:
    """Shows the terminal version and returns the program's exit code.

    ascii: True for --ascii; None finds out from the terminal and the locale (wants_ascii).
    """
    app = WorkbenchApp(analyze, directory, scope, config_file, config_loader=config_loader)
    app.ascii = wants_ascii() if ascii is None else ascii
    # The app has already asked the terminal how many colors it has (Rich's detection).
    app.colors16 = wants_16_colors(app.console.color_system)
    app.run()
    if app.had_errors:  # as in the window: a file could not be deleted
        return 1
    return app.return_code or 0
