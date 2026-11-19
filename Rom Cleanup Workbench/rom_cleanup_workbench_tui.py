"""Terminal version of Rom Cleanup Workbench, built with Textual (python3 rom_cleanup_workbench.py --tui).

The rules are in the Review object from rom_cleanup_workbench.py, the shared state in workbench_state.py.
Like the window, this module does not import the program, because it would otherwise be loaded a
second time when started as a script.

Done so far (see docs/tui-plan.md): start, title row, the read-only list with background analysis.
"""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import DataTable, ProgressBar, Static

from translations import tr
from workbench_state import SETTINGS_PATH, format_kb, load_confirmed_saves, load_scope, scope_flags

APP_NAME = "Rom Cleanup Workbench"


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
    #nothing { height: 1fr; content-align: center middle; text-style: bold; display: none; }
    #progress { height: 1; padding: 0 1; display: none; }
    #status { height: auto; background: #1a7f37; color: #ffffff; padding: 0 1; }
    """
    BINDINGS = [Binding("q", "quit", show=False), Binding("escape", "quit", show=False)]

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

    def compose(self) -> ComposeResult:
        with Horizontal(id="title-row"):
            yield Static(APP_NAME, id="title")
            yield Static(self._folder_text(), id="folder", markup=False)
        yield Static(tr("tui.help"), id="help", markup=False)
        yield Static("", id="info", markup=False)
        table = DataTable(id="games", cursor_type="row", zebra_stripes=False)
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
        self.query_one("#games", DataTable).clear()
        self._show_nothing_to_do(False)

    def show_games(self) -> None:
        """Fills the list with the games of the current view, as the window does."""
        table = self.query_one("#games", DataTable)
        table.clear()
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
        self._set_status(review.status(*flags))

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
