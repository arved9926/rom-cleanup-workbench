"""Terminal version of Rom Cleanup Workbench, built with Textual (python3 rom_cleanup_workbench.py --tui).

The rules are in the Review object from rom_cleanup_workbench.py, the shared state in workbench_state.py.
Like the window, this module does not import the program, because it would otherwise be loaded a
second time when started as a script.

Done so far (see docs/tui-plan.md): start, title row, the read-only list with background analysis,
moving the cursor and selecting several rows, D and P, the three views, the filter, questions
and messages inside the terminal, deleting (Proceed) and choosing the folder.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.geometry import Region
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Input, ProgressBar, RadioButton, RadioSet, Static, Tree

from translations import tr
from workbench_state import (
    SCOPES, SETTINGS_PATH, add_confirmed_saves, drives, format_kb, load_confirmed_saves, load_scope, save_scope,
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
    "choose_folder",
}
# As in the window: Redrawing after every deleted file would slow down large deletions.
DELETE_REDRAW = 0.05


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


class GameTable(DataTable):
    """The game list: one cursor row plus a selection of several rows, as in the window's list.

    The table's own Up/Down would stop on the empty rows between the games and know no Shift,
    so the app moves the cursor itself.
    """

    COMPONENT_CLASSES = DataTable.COMPONENT_CLASSES | {"datatable--selected", "datatable--moved"}
    BINDINGS = [
        Binding("up", "app.move_cursor(-1, False)", show=False),
        Binding("down", "app.move_cursor(1, False)", show=False),
        Binding("shift+up", "app.move_cursor(-1, True)", show=False),
        Binding("shift+down", "app.move_cursor(1, True)", show=False),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected: set[str] = set()
        self.moved: set[str] = set()

    def set_selection(self, keys) -> None:
        self.selected = set(keys)
        self._clear_caches()
        self.refresh()

    def set_moved(self, keys) -> None:
        """The files moved by hand; they are brown, as in the window."""
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

    Its own bindings come before the app's: Esc clears the filter instead of ending the program.
    """

    BINDINGS = [
        Binding("escape", "app.leave_filter(True)", show=False),
        Binding("down", "app.leave_filter(False)", show=False),
        Binding("ctrl+f", "select_all", show=False),
    ]


class QuestionScreen(ModalScreen):
    """A question or message over the list, with buttons in the program's language.

    buttons: (text key, value) pairs. The button with the value default has the focus, Enter presses
    it, and Esc chooses the last button (No or OK), as in the window. Left and Right move between them.
    """

    BINDINGS = [
        Binding("escape", "answer_last", show=False),
        Binding("left", "app.focus_previous", show=False),
        Binding("right", "app.focus_next", show=False),
    ]

    def __init__(self, kind: str, title: str, message: str, buttons, default=None):
        super().__init__(classes=f"kind-{kind}")
        self.kind = kind
        self.title_text = title
        self.message = message
        self.labels = [tr(key) for key, _value in buttons]
        self.values = [value for _key, value in buttons]
        self.default_index = self.values.index(default) if default in self.values else 0

    def compose(self) -> ComposeResult:
        with Vertical(id="question"):
            with Horizontal(id="question-head"):
                yield Static("●", id="question-dot")
                yield Static(self.title_text, id="question-title", markup=False)
            yield Static(self.message, id="question-text", markup=False)
            with Horizontal(id="question-buttons"):
                for index, label in enumerate(self.labels):
                    yield Button(label, id=f"answer-{index}", compact=True)

    def on_mount(self) -> None:
        buttons = list(self.query(Button))
        if buttons:  # None while the program is just ending.
            buttons[self.default_index].focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(self.values[int(event.button.id.removeprefix("answer-"))])

    def action_answer_last(self) -> None:
        self.dismiss(self.values[-1])


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


class WorkbenchApp(App):
    """The terminal window: the same rows as the Windows window, from top to bottom."""

    TITLE = APP_NAME
    CSS = """
    Screen { background: #000000; color: #ffffff; }
    #title-row { height: 1; background: #1a7f37; color: #ffffff; }
    #title { width: auto; text-style: bold; padding: 0 1; }
    #folder { width: 1fr; text-align: right; padding: 0 1; }
    #help, #info { padding: 0 1; }
    #info { margin-bottom: 1; }
    #games { height: 1fr; background: #000000; }
    #games > .datatable--header { background: #222222; color: #ffffff; text-style: bold; }
    #games > .datatable--cursor { background: #0a4a8a; color: #ffffff; }
    #games > .datatable--moved { background: #5c4400; }
    #games > .datatable--selected { background: #0a4a8a; color: #ffffff; }
    #nothing { height: 1fr; content-align: center middle; text-style: bold; display: none; }
    #progress { height: 1; padding: 0 1; display: none; }
    #filter-row { height: 1; padding: 0 1; }
    #filter-label { width: auto; margin-right: 1; }
    #filter { width: 1fr; height: 1; border: none; padding: 0 1; background: #222222; color: #ffffff; }
    #filter:focus { border: none; background: #333333; }
    #views { layout: horizontal; height: auto; width: 100%; border: none; background: #000000; padding: 0 1; }
    #views:focus-within { border: none; }
    #views > RadioButton { background: #000000; color: #ffffff; border: none; margin-right: 2; }
    #views > RadioButton > .toggle--button { color: #333333; background: #333333; }
    #views > RadioButton.-on > .toggle--button { color: #e5383b; background: #333333; }
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
    #question-buttons > Button { margin-right: 2; min-width: 8; background: #333333; color: #ffffff; }
    #question-buttons > Button:focus { background: #0a4a8a; text-style: bold; }
    FolderScreen { background: #000000; padding: 1 2; }
    #folder-head, #folder-path-row { height: 1; margin-bottom: 1; }
    #folder-title { width: 1fr; text-style: bold; }
    #folder-head > Button { margin-left: 2; min-width: 10; background: #333333; color: #ffffff; }
    #folder-head > Button:focus { background: #0a4a8a; text-style: bold; }
    #folder-path-label { width: auto; margin-right: 1; }
    #folder-path { width: 1fr; height: 1; border: none; padding: 0 1; background: #222222; color: #ffffff; }
    #folder-path:focus { border: none; background: #333333; }
    #folder-tree { height: 1fr; background: #000000; }
    #folder-tree > .tree--cursor { background: #0a4a8a; color: #ffffff; }
    #folder-hint { height: auto; margin-top: 1; }
    """
    BINDINGS = [
        Binding("q", "quit", show=False),
        Binding("escape", "quit", show=False),
        # priority: otherwise Tab would move the focus to the next widget, as usual in Textual.
        Binding("tab", "move_game(1)", show=False, priority=True),
        Binding("shift+tab", "move_game(-1)", show=False, priority=True),
        Binding("d,D", "demote", show=False),
        Binding("1", "choose_view(0)", show=False),
        Binding("2", "choose_view(1)", show=False),
        Binding("3", "choose_view(2)", show=False),
        Binding("p,P", "promote", show=False),
        Binding("slash,ctrl+f", "focus_filter", show=False),
        Binding("x,X,ctrl+l", "proceed", show=False),
        Binding("o,O,ctrl+o", "choose_folder", show=False),
    ]

    def __init__(self, analyze, directory: Path | None, scope: str | None = None, config_file=None,
                 settings_path: Path = SETTINGS_PATH):
        super().__init__()
        self.analyze = analyze
        self.directory = directory
        self.config_file = config_file
        self.settings_path = settings_path
        # An explicit choice at startup takes precedence over the saved state, as in the window.
        self.scope = scope or load_scope(settings_path)
        self.review = None
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
        yield Static(tr("tui.help"), id="help", markup=False)
        yield Static("", id="info", markup=False)
        table = GameTable(id="games", cursor_type="row", zebra_stripes=False)
        table.add_column(tr("window.column.file"), key="file")
        table.add_column(Text(tr("window.column.size"), justify="right"), key="size")
        table.add_column(tr("window.column.note"), key="note")
        yield table
        yield Static(tr("window.nothing_to_do"), id="nothing")
        yield ProgressBar(id="progress", show_eta=False)
        with Horizontal(id="filter-row"):
            yield Static(tr("window.filter"), id="filter-label", markup=False)
            yield FilterInput(id="filter", select_on_focus=True)
        # Above the green row, as in the window; 1, 2 and 3 choose the same views.
        with RadioSet(id="views"):
            for value, label in SCOPES:
                yield RadioButton(tr(label), value=value == self.scope, id=f"view-{value}")
        yield Static("", id="status", markup=False)

    def on_mount(self) -> None:
        # Not focusable: the keys must keep acting on the list after a view was clicked.
        self.query_one("#views", RadioSet).can_focus = False
        self.query_one("#games", GameTable).focus()
        if self.directory is None:
            self._set_status(tr("window.choose_folder_status"))
            self.call_after_refresh(self.action_choose_folder)  # as the window does at the start
        else:
            self.start_analysis()

    # Analysis ---------------------------------------------------------------------------------

    def start_analysis(self) -> None:
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
                review = self.analyze(directory, report)
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
        review.confirm_save_files(load_confirmed_saves(self.settings_path))
        # Row keys follow the game's place among all games, so that they stay the same in every view.
        self._file_keys = {}
        self._game_numbers = {}
        for game_index, result in enumerate(review.results):
            self._game_numbers[id(result)] = game_index
            for file_index, entry in enumerate(result.keep + result.marked):
                self._file_keys[id(entry)] = f"g{game_index}f{file_index}"
        self.query_one("#info", Static).update(review.priority_text())
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

    def _fill_table(self) -> None:
        table = self.query_one("#games", GameTable)
        table.clear()
        self.files = {}
        moved = set()
        for place, result in enumerate(self._visible):
            game_index = self._game_numbers[id(result)]
            if place:
                # An empty row between the games: a drawn line would widen the file column to its length.
                table.add_row("", "", "", key=f"s{game_index}")
            table.add_row(
                Text(result.title, style="bold"), "", Text("; ".join(result.problems), style="bold"),
                key=f"g{game_index}",
            )
            entries = [("k", "window.section.keep", "+", "bold", "window.by_hand_keep", result.keep),
                       ("h", "window.section.marked", "-", "", "window.by_hand_delete", result.marked)]
            for suffix, label, sign, style, moved_note, group in entries:
                if not group:
                    continue
                table.add_row(Text("  " + tr(label)), "", "", key=f"g{game_index}{suffix}")
                for entry in group:
                    key = self._file_keys[id(entry)]
                    self.files[key] = (result, entry)
                    if entry.moved:
                        moved.add(key)
                    notes = ([tr(moved_note)] if entry.moved else []) + list(entry.notes)
                    table.add_row(
                        Text(f"    {sign} {entry.path.name}", style=style),
                        Text(format_kb(entry.size()), justify="right", style=style),
                        Text("; ".join(notes), style="italic"),
                        key=key,
                    )
        table.set_moved(moved)

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
        return self.focused is self.query_one("#filter", FilterInput)

    def action_focus_filter(self) -> None:
        field = self.query_one("#filter", FilterInput)
        field.focus()
        field.select_all()

    def action_leave_filter(self, clear: bool = False) -> None:
        """Shows the result at once and returns to the list; Esc also clears the filter."""
        field = self.query_one("#filter", FilterInput)
        if clear:
            field.value = ""
        self._apply_filter()
        self.query_one("#games", GameTable).focus()

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
        table = self.query_one("#games", GameTable)
        cursor, selection, scroll = self.cursor_key(), table.selected, table.scroll_y
        self._fill_table()
        keys = self._keys()
        if cursor not in keys:  # The section row under the cursor has disappeared.
            cursor = rows[-1]
        selection = {key for key in selection if key in keys}
        table.set_selection(selection)
        table.scroll_to(y=scroll, animate=False, immediate=True)
        table.move_cursor(row=table.get_row_index(cursor), scroll=False)
        self._update_status()

    # Proceed ----------------------------------------------------------------------------------

    def action_proceed(self) -> None:
        """x and Ctrl+L delete the marked files after a question, as Proceed does in the window."""
        if self.review is None or self.deleting:
            return
        if not any(result.marked for result in self.review.results):
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
        if errors:
            self.had_errors = True
            self.show_message("warning", tr("window.partly_deleted_title"),
                              tr("window.partly_deleted", count=deleted, errors="\n".join(errors)))
        else:
            self.show_message("info", tr("window.deleted_title"), tr("terminal.deleted", count=deleted))
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
            add_confirmed_saves(self.settings_path, save_files)
        except OSError as error:
            return str(error)
        return None

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
            return
        self.directory = folder
        self.query_one("#folder", Static).update(self._folder_text())
        self.query_one("#games", GameTable).focus()
        self.start_analysis()

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
        if self._filter_focused():  # Tab is a priority key; in the filter it only returns to the list.
            self.action_leave_filter()
            return
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

    def check_action(self, action: str, parameters) -> bool | None:
        # In the folder choice, a "d" or "x" must not act on the list behind it.
        if action in _LIST_ACTIONS and (self.question_open() or self.deleting or self.folder_open()):
            return False
        if action == "quit" and self.deleting:  # Half a deletion must not be left behind unreported.
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
        return tr("window.folder", directory=self.directory) if self.directory else tr("window.no_folder")

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)


def run_tui(analyze, directory: Path | None, scope: str | None = None, config_file=None) -> int:
    """Shows the terminal version and returns the program's exit code."""
    app = WorkbenchApp(analyze, directory, scope, config_file)
    app.run()
    if app.had_errors:  # as in the window: a file could not be deleted
        return 1
    return app.return_code or 0
