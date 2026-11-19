"""Analysis window: analyze a folder, review the result, reorder with D and P, and delete.

The rules are in the Review object from rom_cleanup_workbench.py. This module does not import
the program, because it would otherwise be loaded a second time when started as a script.
"""

from __future__ import annotations

import ctypes
import gc
import json
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from translations import tr

_BLACK = "#000000"
_WHITE = "#ffffff"
_DARK_GRAY = "#222222"
_GRAY = "#444444"
_LIGHT_GRAY = "#666666"
_SELECTED = "#0a4a8a"
_MOVED = "#5c4400"
_GREEN = "#1a7f37"
_RED = "#e5383b"
_HIGHLIGHT_STYLE = "Highlight.TLabel"
_HIGHLIGHT_FRAME_STYLE = "Highlight.TFrame"
_APP_NAME = "Rom Cleanup Workbench"
# A file of its own, so that the window does not rewrite the hand-maintained redundanz_config.json.
SETTINGS_PATH = Path(__file__).with_name("rom_cleanup_workbench_settings.json")
_SCOPE_KEY = "scope"
_CONFIRMED_KEY = "confirmed_save_files"
SCOPE_PROBLEMS = "problems"
SCOPE_MARKED = "marked"
SCOPE_ALL_FILES = "all"
DEFAULT_SCOPE = SCOPE_PROBLEMS
# The value is saved and stays the same in every language; the label is a text key.
_SCOPES = (
    (SCOPE_PROBLEMS, "window.scope.problems"),
    (SCOPE_MARKED, "window.scope.marked"),
    (SCOPE_ALL_FILES, "window.scope.all"),
)
_LINE_COLOR = "#888888"
# The list has no real dividing lines, so each line is a row of its own.
_LINE_TEXT = "─" * 400
_SEPARATOR_SUFFIX = "s"
_NOTHING_TO_DO_SCALE = 3
_BLINK_MS = 600
_FONT_FAMILY = "Lucida Sans Typewriter"
_FONT_SIZE = 11
_MIN_FONT_SIZE = 8
_MAX_FONT_SIZE = 32
_MIN_WIDTH = 800  # Below this, the rows above and below the list overlap.
_MIN_HEIGHT = 400
_FILTER_MIN_CHARS = 16
_DELETE_REDRAW_S = 0.05
_CELL_GAP = "  "  # Treeview cells have no padding: Keeps the right-aligned size away from the note.
_SEARCH_DELAY_MS = 200  # Rebuilding a long list on every keystroke would make typing sluggish.


def format_kb(size: int | None) -> str:
    """Like Windows Explorer: Kilobytes rounded up, with the language's thousands separator."""
    if size is None:
        return "?"
    number = f"{-(-size // 1024):,}".replace(",", tr("number.thousands"))
    return f"{number} {tr('unit.kb')}"


def _load_settings(path: Path) -> dict:
    """A missing or broken file means: The defaults apply."""
    try:
        with open(path, encoding="utf-8-sig") as handle:
            settings = json.load(handle)
    except (OSError, ValueError):
        return {}
    return settings if isinstance(settings, dict) else {}


def _save_settings(path: Path, **values) -> None:
    """Changes only the given entries, so that the view and the confirmed files do not overwrite each other."""
    settings = _load_settings(path)
    settings.update(values)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)
        handle.write("\n")


def load_scope(path: Path) -> str:
    scope = _load_settings(path).get(_SCOPE_KEY)
    return scope if scope in (value for value, _label in _SCOPES) else DEFAULT_SCOPE


def save_scope(path: Path, scope: str) -> None:
    _save_settings(path, **{_SCOPE_KEY: scope})


def load_confirmed_saves(path: Path) -> dict[str, int]:
    """Status or save files confirmed when deleting: file key to size in bytes."""
    confirmed = _load_settings(path).get(_CONFIRMED_KEY)
    if not isinstance(confirmed, dict):
        return {}
    return {key: size for key, size in confirmed.items() if isinstance(size, int) and not isinstance(size, bool)}


def add_confirmed_saves(path: Path, files: dict[str, int]) -> None:
    _save_settings(path, **{_CONFIRMED_KEY: {**load_confirmed_saves(path), **files}})


class _AnalysisReplaced(Exception):
    """A newer analysis has replaced this one."""


class ReviewWindow:
    def __init__(self, analyze, directory: Path | None, scope: str | None = None, settings_path: Path = SETTINGS_PATH):
        self.settings_path = settings_path
        self.analyze = analyze
        self.directory = directory
        self.review = None
        self._blink_job = None
        self.had_errors = False
        self.font_size = _FONT_SIZE
        self._analysis = None
        self._workers = []
        self._progress = None
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            raise RuntimeError(str(error)) from error
        self.root.title("Rom Cleanup Workbench")
        self.root.geometry("1100x650")
        self.root.minsize(_MIN_WIDTH, _MIN_HEIGHT)
        # An explicit choice at startup takes precedence over the saved state.
        self.scope = tk.StringVar(self.root, scope or load_scope(settings_path))
        self.status = tk.StringVar(self.root)
        self.info = tk.StringVar(self.root)
        self.folder = tk.StringVar(self.root)
        self.search = tk.StringVar(self.root)
        self._search_job = None
        self._striped = set()
        self._group_ids = {}
        self._file_ids = {}
        self._files = {}

        self._build_widgets()
        self._fit_bottom_row()
        self._show_directory()
        self.tree.focus_set()
        self._use_dark_title_bar()

    def _show_directory(self, *lines: str) -> None:
        self.folder.set(tr("window.folder", directory=self.directory) if self.directory else tr("window.no_folder"))
        self.info.set("\n".join(lines))

    def _clear(self) -> None:
        self.review = None
        self._files = {}
        self.tree.delete(*self.tree.get_children())
        self._hide_nothing_to_do()
        self._show_directory()

    def start_analysis(self) -> None:
        """Analyzes in the background, so that the window does not hang while reading large ZIPs.

        If an analysis is already running, it is replaced: Its result no longer counts.
        """
        if self.directory is None:
            return
        self._clear()
        self.status.set(tr("window.analyzing"))
        self._progress = None
        self.progress_bar.configure(value=0, maximum=1)
        self.progress_bar.place(in_=self.tree, relx=0.5, rely=0.5, relwidth=0.6, anchor="center")
        self.progress_bar.lift()
        # If garbage collection cleans up Tk objects in the background thread, Tcl crashes.
        gc.disable()
        answer = queue.Queue()
        self._analysis = answer
        worker = threading.Thread(target=self._analyze_in_background, args=(self.directory, answer), daemon=True)
        self._workers.append(worker)
        worker.start()
        self.root.after(100, self._poll_analysis, answer)

    def _analyze_in_background(self, directory: Path, answer: queue.Queue) -> None:
        def report(done: int, total: int) -> None:
            if answer is not self._analysis:
                raise _AnalysisReplaced  # Stops the replaced analysis at the next game.
            # Only remember it: Only the main thread may touch Tk, _poll_analysis shows the state.
            self._progress = (done, total)

        try:
            answer.put((self.analyze(directory, report), None))
        except Exception as error:  # Every error must reach the window, otherwise it would stay at "Analyzing".
            answer.put((None, str(error) or type(error).__name__))

    def _poll_analysis(self, answer: queue.Queue) -> None:
        if answer is not self._analysis:
            return
        try:
            review, error = answer.get_nowait()
        except queue.Empty:
            if self._progress:
                done, total = self._progress
                self.status.set(tr("window.analyzing_progress", done=done, total=total))
                self.progress_bar.configure(value=done, maximum=max(total, 1))
            self.root.after(100, self._poll_analysis, answer)
            return
        self.progress_bar.place_forget()
        self._analysis = None
        self._enable_gc_when_idle()
        self._finish_analysis(review, error)

    def _enable_gc_when_idle(self) -> None:
        """A replaced analysis may also still be running, for example in a large ZIP."""
        self._workers = [worker for worker in self._workers if worker.is_alive()]
        if self._workers:
            self.root.after(100, self._enable_gc_when_idle)
        elif self._analysis is None:
            gc.enable()

    def _finish_analysis(self, review, error: str | None) -> None:
        if error:
            self._clear()
            self.status.set(tr("window.analysis_failed", error=error))
            messagebox.showerror(tr("window.analysis_failed_title"), error, parent=self.root)
        else:
            self.show_review(review)

    def analyze_now(self) -> None:
        """Analyzes without a background thread."""
        self.show_review(self.analyze(self.directory))

    def show_review(self, review) -> None:
        self.tree.selection_set(())
        self.review = review
        # Read again every time: The file may have changed in another window since.
        review.confirm_save_files(load_confirmed_saves(self.settings_path))
        # Each file keeps its row ID, so that the selection survives moving.
        self._group_ids = {}
        self._file_ids = {}
        self._files = {}
        for group_index, result in enumerate(review.results):
            self._group_ids[id(result)] = f"g{group_index}"
            for file_index, entry in enumerate(result.keep + result.marked):
                row = f"g{group_index}f{file_index}"
                self._file_ids[id(entry)] = row
                self._files[row] = (result, entry)
        self._show_directory(review.priority_text())
        self._show_all_groups()
        self._select_first_file()

    def _may_discard_changes(self, question: str) -> bool:
        if self.review is None or not self.review.moved_count():
            return True
        return messagebox.askyesno(tr("window.discard_title"), question, default="no", parent=self.root)

    def reanalyze(self) -> None:
        if self._may_discard_changes(tr("window.discard_reanalyze")):
            self.start_analysis()

    def choose_directory(self) -> None:
        if not self._may_discard_changes(tr("window.discard_folder")):
            return
        chosen = filedialog.askdirectory(
            parent=self.root, mustexist=True, title=tr("window.choose_folder"), initialdir=self.directory or None,
        )
        if chosen:
            self.directory = Path(chosen)
            self.start_analysis()

    def _apply_font(self) -> None:
        # All ttk elements get their font from these named Tk fonts.
        for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkCaptionFont"):
            tkfont.nametofont(name).configure(family=_FONT_FAMILY, size=self.font_size, weight="normal")

    def _row_height(self) -> int:
        return tkfont.nametofont("TkDefaultFont").metrics("linespace") + 6

    def change_font_size(self, steps: int) -> None:
        """Changes the font size in the whole window, including the row height of the list."""
        size = min(_MAX_FONT_SIZE, max(_MIN_FONT_SIZE, self.font_size + steps))
        if size == self.font_size:
            return
        self.font_size = size
        self._apply_font()
        self.bold_font.configure(size=size)
        self.nothing_font.configure(size=size * _NOTHING_TO_DO_SCALE)
        ttk.Style(self.root).configure("Treeview", rowheight=self._row_height())
        self._fit_radio_indicator()
        self._fit_size_column()
        self._fit_bottom_row()

    def _fit_radio_indicator(self) -> None:
        """The circle grows with the font, so that the red dot stays easy to see."""
        size = max(12, round(tkfont.nametofont("TkDefaultFont").metrics("linespace") * 0.8))
        ttk.Style(self.root).configure("TRadiobutton", indicatorsize=size, indicatormargin=(0, 0, 8, 0))

    def _fit_size_column(self) -> None:
        """Wide enough for files up to 99 GB, also after changing the font size."""
        width = tkfont.nametofont("TkDefaultFont").measure(format_kb(99 * 1024**3) + _CELL_GAP) + 16
        self.tree.column("size", width=width, minwidth=width)

    def _fit_bottom_row(self) -> None:
        """Keeps the filter field usable next to the buttons, also with a large font."""
        self.root.update_idletasks()
        needed = min(self.bottom_row.winfo_reqwidth(), self.root.winfo_screenwidth())
        self.root.minsize(max(_MIN_WIDTH, needed), _MIN_HEIGHT)

    def _on_zoom(self, event) -> str:
        self.change_font_size(1 if event.delta > 0 else -1)
        return "break"  # Otherwise the list scrolls along while zooming.

    def _apply_dark_mode(self) -> None:
        self.root.configure(background=_BLACK)
        style = ttk.Style(self.root)
        # The Windows default theme ignores background colors, "clam" applies them.
        style.theme_use("clam")
        style.configure(
            ".", background=_BLACK, foreground=_WHITE, fieldbackground=_BLACK,
            bordercolor=_BLACK, lightcolor=_BLACK, darkcolor=_BLACK,
        )
        style.configure("Treeview", background=_BLACK, foreground=_WHITE, rowheight=self._row_height(), borderwidth=0)
        style.map("Treeview", background=[("selected", _SELECTED)], foreground=[("selected", _WHITE)])
        style.configure("Treeview.Heading", background=_DARK_GRAY, foreground=_WHITE, relief="flat")
        style.map("Treeview.Heading", background=[("active", _GRAY)])
        style.configure("TButton", background=_DARK_GRAY, foreground=_WHITE, bordercolor=_GRAY)
        style.map("TButton", background=[("active", _GRAY)])
        style.configure("TCheckbutton", background=_BLACK, foreground=_WHITE, indicatorbackground=_BLACK)
        style.map(
            "TCheckbutton",
            background=[("active", _BLACK)],
            indicatorbackground=[("selected", _SELECTED), ("active", _DARK_GRAY)],
        )
        # A light ring on dark gray, and a red dot for the chosen view: On black, the default is hard to see.
        style.configure(
            "TRadiobutton", background=_BLACK, foreground=_WHITE, indicatorbackground=_DARK_GRAY,
            indicatorforeground=_RED, upperbordercolor=_LINE_COLOR, lowerbordercolor=_LINE_COLOR,
        )
        style.map(
            "TRadiobutton",
            background=[("active", _BLACK)],
            indicatorbackground=[("active", _GRAY)],
        )
        self._fit_radio_indicator()
        style.configure(_HIGHLIGHT_STYLE, background=_GREEN, foreground=_WHITE)
        style.configure(_HIGHLIGHT_FRAME_STYLE, background=_GREEN)
        style.configure(
            "TEntry", fieldbackground=_DARK_GRAY, foreground=_WHITE, insertcolor=_WHITE,
            bordercolor=_GRAY, selectbackground=_SELECTED, selectforeground=_WHITE,
        )
        style.configure("Horizontal.TProgressbar", background=_GREEN, troughcolor=_DARK_GRAY, bordercolor=_GRAY, thickness=24)
        style.configure("Vertical.TScrollbar", background=_GRAY, troughcolor=_BLACK, arrowcolor=_WHITE, bordercolor=_BLACK)
        style.map("Vertical.TScrollbar", background=[("active", _LIGHT_GRAY)])

    def _use_dark_title_bar(self) -> None:
        """Switches the Windows title bar to dark; if it stays light, no harm is done."""
        try:
            self.root.update_idletasks()
            handle = ctypes.windll.user32.GetParent(self.root.winfo_id())
            enabled = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 20, ctypes.byref(enabled), ctypes.sizeof(enabled))
        except (AttributeError, OSError):
            pass

    def _build_widgets(self) -> None:
        self._apply_font()
        self._apply_dark_mode()
        self.bold_font = tkfont.nametofont("TkDefaultFont").copy()
        self.bold_font.configure(weight="bold")

        self.title_row = ttk.Frame(self.root, style=_HIGHLIGHT_FRAME_STYLE)
        self.title_row.pack(fill="x")
        self.title_label = ttk.Label(
            self.title_row, text=_APP_NAME, style=_HIGHLIGHT_STYLE, font=self.bold_font, padding=8,
        )
        self.title_label.pack(side="left", anchor="n")
        self.folder_label = ttk.Label(
            self.title_row, textvariable=self.folder, style=_HIGHLIGHT_STYLE, padding=8, justify="right",
        )
        self.folder_label.pack(side="right")
        # A long path wraps next to the title instead of being cut off.
        self.title_row.bind(
            "<Configure>",
            lambda event: self.folder_label.configure(
                wraplength=max(event.width - self.title_label.winfo_reqwidth() - 16, 1)
            ),
        )

        # Wraps with a large font instead of being cut off on the right.
        help_label = ttk.Label(self.root, text=tr("window.help"), padding=8)
        help_label.pack(fill="x")
        help_label.bind("<Configure>", lambda event: help_label.configure(wraplength=event.width - 16))
        info_label = ttk.Label(self.root, textvariable=self.info, padding=(8, 0, 8, 8))
        info_label.pack(fill="x")
        info_label.bind("<Configure>", lambda event: info_label.configure(wraplength=event.width - 16))

        # The status has a row of its own, so that it does not push out the buttons.
        bottom = ttk.Frame(self.root, padding=8)
        bottom.pack(side="bottom", fill="x")
        self.status_label = ttk.Label(self.root, textvariable=self.status, style=_HIGHLIGHT_STYLE, padding=8)
        self.status_label.pack(side="bottom", fill="x")
        self.status_label.bind("<Configure>", lambda event: self.status_label.configure(wraplength=event.width - 16))
        ttk.Button(bottom, text=tr("window.button.close"), command=self.close).pack(side="right")
        # "Proceed": Besides deleting, the button also confirms the suspected save files.
        ttk.Button(bottom, text=tr("window.button.proceed"), command=self.confirm_delete).pack(side="right", padx=8)
        ttk.Button(bottom, text=tr("window.button.reanalyze"), command=self.reanalyze).pack(side="right")
        ttk.Button(bottom, text=tr("window.button.folder"), command=self.choose_directory).pack(side="right", padx=8)
        ttk.Label(bottom, text=tr("window.filter")).pack(side="left", padx=(0, 8))
        self.search_entry = ttk.Entry(bottom, textvariable=self.search, width=_FILTER_MIN_CHARS)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self._bind_search_entry()
        self.bottom_row = bottom

        # Above the green row, so that it stays the second-to-last row of the window.
        options = ttk.Frame(self.root, padding=(8, 8, 8, 0))
        options.pack(side="bottom", fill="x")
        for value, label in _SCOPES:
            ttk.Radiobutton(
                options, text=tr(label), value=value, variable=self.scope, command=self._scope_changed,
            ).pack(side="left", padx=(0, 16))

        middle = ttk.Frame(self.root)
        middle.pack(fill="both", expand=True)
        # "hint" stays the first value of every row; only the display puts the size before it.
        self.tree = ttk.Treeview(
            middle, columns=("hint", "size"), displaycolumns=("size", "hint"), selectmode="extended",
        )
        self.tree.heading("#0", text=tr("window.column.file"), anchor="w")
        self.tree.heading("size", text=tr("window.column.size") + _CELL_GAP, anchor="e")
        self.tree.heading("hint", text=tr("window.column.note"), anchor="w")
        self.tree.column("#0", width=560, stretch=True)
        self.tree.column("size", anchor="e", stretch=False)
        self.tree.column("hint", width=500, stretch=True)
        self._fit_size_column()
        scrollbar = ttk.Scrollbar(middle, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.nothing_font = self.bold_font.copy()
        self.nothing_font.configure(size=self.font_size * _NOTHING_TO_DO_SCALE)
        self.nothing_label = ttk.Label(middle, text=tr("window.nothing_to_do"), font=self.nothing_font)
        self.progress_bar = ttk.Progressbar(middle, orient="horizontal", mode="determinate")
        # Tags created earlier take precedence: A moved file stays brown even inside a stripe.
        self.tree.tag_configure("moved", background=_MOVED)
        self.tree.tag_configure("striped", background=_DARK_GRAY)
        self.tree.tag_configure("game", font=self.bold_font)
        self.tree.tag_configure("problem", font=self.bold_font)
        self.tree.tag_configure("keep", font=self.bold_font)
        self.tree.tag_configure("separator", foreground=_LINE_COLOR)

        # On the window instead of the list, so that the keys also work after clicking a radio button.
        for key in ("d", "D"):
            self.root.bind(f"<KeyPress-{key}>", lambda _event: self.demote_selected())
        for key in ("p", "P"):
            self.root.bind(f"<KeyPress-{key}>", lambda _event: self.promote_selected())
        self.root.bind("<Control-l>", lambda _event: self.confirm_delete())
        self.root.bind("<Control-L>", lambda _event: self.confirm_delete())
        self.root.bind("<Control-o>", lambda _event: self.choose_directory())
        self.root.bind("<Control-O>", lambda _event: self.choose_directory())
        self.root.bind("<F5>", lambda _event: self.reanalyze())
        self.root.bind("<Control-f>", lambda _event: self.focus_search())
        self.root.bind("<Control-F>", lambda _event: self.focus_search())
        # "break" prevents Tab from passing the focus to the next button as usual.
        self.root.bind("<Tab>", lambda _event: self._move_game(1))
        self.root.bind("<Shift-Tab>", lambda _event: self._move_game(-1))
        self.root.bind("<Escape>", lambda _event: self.close())
        # The list needs its own binding, because its default binding would otherwise scroll first.
        self.root.bind("<Control-MouseWheel>", self._on_zoom)
        self.tree.bind("<Control-MouseWheel>", self._on_zoom)
        # The list's default keys would stop on the dividing lines and do not know Shift.
        self.tree.bind("<Up>", lambda _event: self._move_cursor(-1, False))
        self.tree.bind("<Down>", lambda _event: self._move_cursor(1, False))
        self.tree.bind("<Shift-Up>", lambda _event: self._move_cursor(-1, True))
        self.tree.bind("<Shift-Down>", lambda _event: self._move_cursor(1, True))
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._drop_separators_from_selection())
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _bind_search_entry(self) -> None:
        # Without the window's bindtag, typing a "d" or "p" here cannot change a deletion mark.
        entry = self.search_entry
        entry.bindtags((str(entry), entry.winfo_class(), "all"))
        self.search.trace_add("write", lambda *_args: self._search_changed())
        entry.bind("<Return>", lambda _event: self.leave_search())
        entry.bind("<Tab>", lambda _event: self.leave_search())
        entry.bind("<Shift-Tab>", lambda _event: self.leave_search())
        entry.bind("<Down>", lambda _event: self.leave_search())
        entry.bind("<Escape>", lambda _event: self.leave_search(clear=True))
        entry.bind("<Control-MouseWheel>", self._on_zoom)

    def focus_search(self) -> str:
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")
        self.search_entry.icursor("end")
        return "break"

    def leave_search(self, clear: bool = False) -> str:
        """Shows the current result at once and returns to the list; Esc also clears the search."""
        if clear:
            self.search.set("")
        self._apply_search()
        self.tree.focus_set()
        return "break"

    def _search_changed(self) -> None:
        if self._search_job is not None:
            self.root.after_cancel(self._search_job)
        self._search_job = self.root.after(_SEARCH_DELAY_MS, self._apply_search)

    def _apply_search(self) -> None:
        if self._search_job is not None:
            self.root.after_cancel(self._search_job)
            self._search_job = None
        self._show_all_groups()
        # Rows hidden by the search leave the selection; D and P should work on what is shown.
        if not self.tree.selection():
            self._select_first_file()

    def _show_all_groups(self) -> None:
        if self.review is None:
            return
        selection = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        self._striped.clear()
        self._hide_nothing_to_do()
        if self.review.nothing_to_do() and self.scope.get() != SCOPE_ALL_FILES:
            self._show_nothing_to_do()
            return
        visible = [result for result in self.review.results if self.review.is_visible(result, *self._scope_flags())]
        for index, result in enumerate(visible):
            group_id = self._group_ids[id(result)]
            if index % 2:
                self._striped.add(group_id)
            if index:
                self.tree.insert(
                    "", "end", group_id + _SEPARATOR_SUFFIX, text=_LINE_TEXT, values=(_LINE_TEXT, _LINE_TEXT),
                    tags=("separator",),
                )
            self.tree.insert(
                "", "end", group_id, text=result.title, open=True,
                values=("; ".join(result.problems),),
                tags=self._tags(group_id, "problem" if result.problems else "game"),
            )
            self._fill_group(result)
        self._restore_selection(selection)
        self._update_status()
        # Also when an analysis ends during typing: In the list, the next letter could be a D or P.
        if self.root.focus_get() is not self.search_entry:
            self.tree.focus_set()

    def _scope_flags(self) -> tuple[bool, bool, str]:
        """Translates the choice into the values only_problems, show_all and pattern of the Review object."""
        return self.scope.get() == SCOPE_PROBLEMS, self.scope.get() == SCOPE_ALL_FILES, self.search.get()

    def _scope_changed(self) -> None:
        """Shows the choice and remembers it for the next start."""
        self._show_all_groups()
        try:
            save_scope(self.settings_path, self.scope.get())
        except OSError as error:
            messagebox.showerror(tr("window.choice_not_saved"), str(error), parent=self.root)

    def _show_nothing_to_do(self) -> None:
        self.status.set(tr("window.nothing_to_do_status"))
        self.nothing_label.place(in_=self.tree, relx=0.5, rely=0.5, anchor="center")
        self.nothing_label.lift()
        self._blink(visible=True)

    def _hide_nothing_to_do(self) -> None:
        if self._blink_job is not None:
            self.root.after_cancel(self._blink_job)
            self._blink_job = None
        self.nothing_label.place_forget()

    def _blink(self, visible: bool) -> None:
        self.nothing_label.configure(foreground=_WHITE if visible else _BLACK)
        self._blink_job = self.root.after(_BLINK_MS, self._blink, not visible)

    def _tags(self, group_id: str, *tags: str) -> tuple:
        return tags + ("striped",) if group_id in self._striped else tags

    def _fill_group(self, result) -> None:
        group_id = self._group_ids[id(result)]
        self.tree.delete(*self.tree.get_children(group_id))
        if result.keep:
            section = self.tree.insert(
                group_id, "end", f"{group_id}k", text=tr("window.section.keep"), open=True,
                tags=self._tags(group_id, "section"),
            )
            for entry in result.keep:
                self._insert_file(group_id, section, entry, "+", "keep", tr("window.by_hand_keep"))
        if result.marked:
            section = self.tree.insert(
                group_id, "end", f"{group_id}h", text=tr("window.section.marked"), open=True,
                tags=self._tags(group_id, "section"),
            )
            for entry in result.marked:
                self._insert_file(group_id, section, entry, "-", "marked", tr("window.by_hand_delete"))

    def _insert_file(self, group_id: str, parent: str, entry, sign: str, tag: str, moved_note: str) -> None:
        notes = ([moved_note] if entry.moved else []) + entry.notes
        tags = (tag, "moved") if entry.moved else (tag,)
        self.tree.insert(
            parent, "end", self._file_ids[id(entry)], text=f"{sign} {entry.path.name}",
            values=("; ".join(notes), format_kb(entry.size()) + _CELL_GAP), tags=self._tags(group_id, *tags),
        )

    @staticmethod
    def _is_separator(row: str) -> bool:
        return row.endswith(_SEPARATOR_SUFFIX)

    def _next_row(self, row: str) -> str:
        """Returns the next visible row; "" at the end of the list."""
        children = self.tree.get_children(row)
        if children and (not row or self.tree.item(row, "open")):
            return children[0]
        while row:
            following = self.tree.next(row)
            if following:
                return following
            row = self.tree.parent(row)
        return ""

    def _previous_row(self, row: str) -> str:
        """Returns the previous visible row; "" at the start of the list."""
        previous = self.tree.prev(row)
        if not previous:
            return self.tree.parent(row)
        while self.tree.item(previous, "open") and self.tree.get_children(previous):
            previous = self.tree.get_children(previous)[-1]
        return previous

    def _move_cursor(self, step: int, extend: bool) -> str:
        """Moves the selection across the dividing lines; with extend it grows or shrinks."""
        current = self.tree.focus()
        neighbor = self._next_row if step > 0 or not current else self._previous_row
        target = neighbor(current)
        while target and self._is_separator(target):
            target = neighbor(target)
        if target:
            if not extend:
                self.tree.selection_set(target)
            elif target in self.tree.selection():
                self.tree.selection_remove(current)  # Backwards: The selection shrinks again.
            else:
                self.tree.selection_add(target)
            self.tree.focus(target)
            self.tree.see(target)
        return "break"

    def _move_game(self, step: int) -> str:
        """Jumps to the neighboring game and selects its first file, so that D and P work at once."""
        game = self.tree.focus()
        while game and self.tree.parent(game):
            game = self.tree.parent(game)
        if not game:
            games = self.tree.get_children()
            target = games[0] if games else ""
        else:
            neighbor = self.tree.next if step > 0 else self.tree.prev
            target = neighbor(game)
            while target and self._is_separator(target):
                target = neighbor(target)
        if target:
            row = next((row for row in self._walk(target) if row in self._files), target)
            self.tree.selection_set(row)
            self.tree.focus(row)
            # First the end, then the title: This shows the whole game if it fits.
            rows = list(self._walk(target))
            if rows:
                self.tree.see(rows[-1])
            self.tree.see(target)
        return "break"

    def _drop_separators_from_selection(self) -> None:
        selection = self.tree.selection()
        rows = [row for row in selection if not self._is_separator(row)]
        if len(rows) != len(selection):
            self.tree.selection_set(rows)

    def _restore_selection(self, rows) -> None:
        rows = [row for row in rows if self.tree.exists(row)]
        self.tree.selection_set(rows)
        if rows:
            self.tree.focus(rows[-1])
            self.tree.see(rows[-1])

    def _select_first_file(self) -> None:
        for group_id in self.tree.get_children():
            for row in self._walk(group_id):
                if row in self._files:
                    self._restore_selection([row])
                    return

    def _walk(self, row: str):
        for child in self.tree.get_children(row):
            yield child
            yield from self._walk(child)

    def _update_status(self) -> None:
        self.status.set(self.review.status(*self._scope_flags()))

    def _move_selected(self, move_name: str) -> None:
        if self.review is None:
            return
        move = getattr(self.review, move_name)
        rows = [row for row in self.tree.selection() if row in self._files]
        changed = []
        for row in rows:
            result, entry = self._files[row]
            if move(result, entry) and not any(result is other for other in changed):
                changed.append(result)
        for result in changed:
            self._fill_group(result)
        if changed:
            self._restore_selection(rows)
            self._update_status()

    def demote_selected(self) -> None:
        self._move_selected("demote")

    def promote_selected(self) -> None:
        self._move_selected("promote")

    def confirm_delete(self) -> None:
        if self.review is None:
            return
        if not any(result.marked for result in self.review.results):
            self._confirm_save_files_only()
            return
        message = self.review.confirm_message(*self._scope_flags())
        if not messagebox.askyesno(
            tr("window.delete_title"), message, icon="warning", default="no", parent=self.root,
        ):
            return
        # Taken before deleting: Afterwards they are remembered as legitimate.
        save_files = self.review.save_file_keys()
        deleted, errors = self._delete_with_progress()
        self._remember_save_files(save_files)
        if errors:
            self.had_errors = True
            messagebox.showwarning(
                tr("window.partly_deleted_title"),
                tr("window.partly_deleted", count=deleted, errors="\n".join(errors)),
                parent=self.root,
            )
        else:
            messagebox.showinfo(tr("window.deleted_title"), tr("terminal.deleted", count=deleted), parent=self.root)
        # The Review object has dropped the deleted files; the folder is not analyzed again.
        self.show_review(self.review)

    def _confirm_save_files_only(self) -> None:
        """Without marked files, Ctrl+L can still confirm the suspected status or save files."""
        save_files = self.review.save_file_keys()
        if not save_files:
            messagebox.showinfo(
                tr("window.nothing_to_delete_title"), tr("window.nothing_to_delete"), parent=self.root,
            )
            return
        question = tr("window.confirm_saves", count=len(save_files))
        if messagebox.askyesno(tr("window.confirm_saves_title"), question, default="no", parent=self.root):
            self._remember_save_files(save_files)
            self.show_review(self.review)

    def _remember_save_files(self, save_files: dict[str, int]) -> None:
        if not save_files:
            return
        try:
            add_confirmed_saves(self.settings_path, save_files)
        except OSError as error:
            messagebox.showerror(tr("window.saves_not_remembered"), str(error), parent=self.root)

    def _delete_with_progress(self) -> tuple[int, list[str]]:
        """Deletes in the main thread and only redraws in between.

        update_idletasks processes no keys or clicks, so nothing can change the marks,
        start a second deletion or close the window while files are being deleted.
        """
        last_redraw = 0.0

        def report(done: int, total: int) -> None:
            nonlocal last_redraw
            now = time.monotonic()
            if done not in (0, total) and now - last_redraw < _DELETE_REDRAW_S:
                return  # Redrawing after every file would slow down large deletions.
            last_redraw = now
            self.status.set(tr("window.deleting_progress", done=done, total=total))
            self.progress_bar.configure(value=done, maximum=max(total, 1))
            self.root.update_idletasks()

        self.progress_bar.configure(value=0, maximum=1)
        self.progress_bar.place(in_=self.tree, relx=0.5, rely=0.5, relwidth=0.6, anchor="center")
        self.progress_bar.lift()
        try:
            return self.review.delete(report)
        finally:
            self.progress_bar.place_forget()

    def close(self) -> None:
        if self._may_discard_changes(tr("window.discard_close")):
            self.root.destroy()

    def run(self) -> int:
        if self.directory is None:
            self.status.set(tr("window.choose_folder_status"))
            self.root.after(100, self.choose_directory)
        else:
            self.start_analysis()
        self.root.mainloop()
        return 1 if self.had_errors else 0


def run_window(analyze, directory: Path | None, scope: str | None = None) -> int:
    """Shows the window and returns the program's exit code."""
    return ReviewWindow(analyze, directory, scope).run()
