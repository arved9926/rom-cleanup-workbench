"""Terminal version of Rom Cleanup Workbench, built with Textual (python3 rom_cleanup_workbench.py --tui).

The rules are in the Review object from rom_cleanup_workbench.py, the shared state in workbench_state.py.
Like the window, this module does not import the program, because it would otherwise be loaded a
second time when started as a script.

Step 2 of docs/tui-plan.md: only the start and the title row exist so far.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Static

from translations import tr

APP_NAME = "Rom Cleanup Workbench"


class WorkbenchApp(App):
    """The terminal window: title row with the folder, the rest follows in the next steps."""

    TITLE = APP_NAME
    CSS = """
    Screen { background: #000000; color: #ffffff; }
    #title-row { height: 1; background: #1a7f37; color: #ffffff; }
    #title { width: auto; text-style: bold; padding: 0 1; }
    #folder { width: 1fr; text-align: right; padding: 0 1; }
    """
    BINDINGS = [Binding("q", "quit", show=False), Binding("escape", "quit", show=False)]

    def __init__(self, analyze, directory: Path | None, scope: str | None = None, config_file=None):
        super().__init__()
        self.analyze = analyze
        self.directory = directory
        self.scope = scope
        self.config_file = config_file

    def compose(self) -> ComposeResult:
        folder = tr("window.folder", directory=self.directory) if self.directory else tr("window.no_folder")
        with Horizontal(id="title-row"):
            yield Static(APP_NAME, id="title")
            yield Static(folder, id="folder")


def run_tui(analyze, directory: Path | None, scope: str | None = None, config_file=None) -> int:
    """Shows the terminal version and returns the program's exit code."""
    app = WorkbenchApp(analyze, directory, scope, config_file)
    app.run()
    return app.return_code or 0
