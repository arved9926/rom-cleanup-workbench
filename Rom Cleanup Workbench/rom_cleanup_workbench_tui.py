"""Terminal version of Rom Cleanup Workbench, built with Textual (python3 rom_cleanup_workbench.py --tui).

The rules are in the Review object from rom_cleanup_workbench.py, the shared state in workbench_state.py.
Like the window, this module does not import the program, because it would otherwise be loaded a
second time when started as a script.

Done so far (see docs/tui-plan.md): start, title row, the read-only list with background analysis,
moving the cursor and selecting several rows.
"""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.geometry import Region
from textual.widgets import DataTable, ProgressBar, Static

from translations import tr
from workbench_state import SETTINGS_PATH, format_kb, load_confirmed_saves, load_scope, scope_flags

APP_NAME = "Rom Cleanup Workbench"


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

    COMPONENT_CLASSES = DataTable.COMPONENT_CLASSES | {"datatable--selected"}
    BINDINGS = [
        Binding("up", "app.move_cursor(-1, False)", show=False),
        Binding("down", "app.move_cursor(1, False)", show=False),
        Binding("shift+up", "app.move_cursor(-1, True)", show=False),
        Binding("shift+down", "app.move_cursor(1, True)", show=False),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected: set[str] = set()

    def set_selection(self, keys) -> None:
        self.selected = set(keys)
        self._clear_caches()
        self.refresh()

    def _get_row_style(self, row_index: int, base_style):
        style = super()._get_row_style(row_index, base_style)
        if 0 <= row_index < self.row_count and self.ordered_rows[row_index].key.value in self.selected:
            style += self.get_component_styles("datatable--selected").rich_style
        return style


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
    #games > .datatable--selected { background: #0a4a8a; color: #ffffff; }
    #nothing { height: 1fr; content-align: center middle; text-style: bold; display: none; }
    #progress { height: 1; padding: 0 1; display: none; }
    #status { height: auto; background: #1a7f37; color: #ffffff; padding: 0 1; }
    """
    BINDINGS = [
        Binding("q", "quit", show=False),
        Binding("escape", "quit", show=False),
        # priority: otherwise Tab would move the focus to the next widget, as usual in Textual.
        Binding("tab", "move_game(1)", show=False, priority=True),
        Binding("shift+tab", "move_game(-1)", show=False, priority=True),
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
        # The row the app itself has just moved the cursor to: its highlight message must not reset the selection.
        self._expected_cursor: str | None = None

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
        yield Static("", id="status", markup=False)

    def on_mount(self) -> None:
        if self.directory is None:
            self._set_status(tr("window.choose_folder_status"))
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

        def report(done: int, total: int) -> None:
            self.call_from_thread(self._show_progress, number, done, total)

        def work() -> None:
            try:
                review = self.analyze(self.directory, report)
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
            return
        self.show_review(review)

    def show_review(self, review) -> None:
        self.review = review
        review.confirm_save_files(load_confirmed_saves(self.settings_path))
        self.query_one("#info", Static).update(review.priority_text())
        self.show_games()

    # The list ---------------------------------------------------------------------------------

    def _clear_list(self) -> None:
        self.files = {}
        table = self.query_one("#games", GameTable)
        table.clear()
        table.set_selection(())
        self._show_nothing_to_do(False)

    def show_games(self) -> None:
        """Fills the list with the games of the current view, as the window does."""
        table = self.query_one("#games", GameTable)
        table.clear()
        table.set_selection(())
        self.files = {}
        review = self.review
        flags = scope_flags(self.scope)
        if review.nothing_to_do() and not flags[1]:
            self._show_nothing_to_do(True)
            self._set_status(tr("window.nothing_to_do_status"))
            return
        self._show_nothing_to_do(False)
        visible = [result for result in review.results if review.is_visible(result, *flags)]
        for game_index, result in enumerate(visible):
            if game_index:
                # An empty row between the games: a drawn line would widen the file column to its length.
                table.add_row("", "", "", key=f"s{game_index}")
            table.add_row(
                Text(result.title, style="bold"), "", Text("; ".join(result.problems), style="bold"),
                key=f"g{game_index}",
            )
            entries = [("k", "window.section.keep", "+", "bold", result.keep),
                       ("h", "window.section.marked", "-", "", result.marked)]
            file_index = 0
            for suffix, label, sign, style, group in entries:
                if not group:
                    continue
                table.add_row(Text("  " + tr(label)), "", "", key=f"g{game_index}{suffix}")
                for entry in group:
                    key = f"g{game_index}f{file_index}"
                    file_index += 1
                    self.files[key] = (result, entry)
                    table.add_row(
                        Text(f"    {sign} {entry.path.name}", style=style),
                        Text(format_kb(entry.size()), justify="right", style=style),
                        Text("; ".join(entry.notes), style="italic"),
                        key=key,
                    )
        self._select_first_file()
        self._set_status(review.status(*flags))

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
        index = table.get_row_index(key)
        if index != table.cursor_row:
            self._expected_cursor = key
            table.move_cursor(row=index)

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
        target = games[0] if game is None else game + step
        if target not in games:
            return
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

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """A click or a key of the table itself (Page Up, Home, ...) selects only the new row."""
        key = event.row_key.value
        if key == self._expected_cursor:
            self._expected_cursor = None
            return
        self._expected_cursor = None
        event.data_table.set_selection({key} if _game_of(key) is not None else ())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """A click on the cursor row, or Enter, leaves only that row selected."""
        key = event.row_key.value
        event.data_table.set_selection({key} if _game_of(key) is not None else ())

    def _list_shown(self) -> bool:
        return self.review is not None and self.query_one("#games", GameTable).row_count > 0

    def _show_nothing_to_do(self, shown: bool) -> None:
        self.query_one("#games", DataTable).display = not shown
        self.query_one("#nothing", Static).display = shown

    # Helpers ----------------------------------------------------------------------------------

    def _folder_text(self) -> str:
        return tr("window.folder", directory=self.directory) if self.directory else tr("window.no_folder")

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)


def run_tui(analyze, directory: Path | None, scope: str | None = None, config_file=None) -> int:
    """Shows the terminal version and returns the program's exit code."""
    app = WorkbenchApp(analyze, directory, scope, config_file)
    app.run()
    return app.return_code or 0
