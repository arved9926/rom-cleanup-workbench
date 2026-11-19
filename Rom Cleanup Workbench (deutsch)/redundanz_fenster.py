"""Analysefenster: Ordner analysieren, Ergebnis prüfen, mit D und P umsortieren und löschen.

Die Regeln stehen im Review-Objekt aus redundanz_finder.py. Dieses Modul importiert
das Programm nicht, weil es sonst beim Start als Skript ein zweites Mal geladen würde.
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
# Eigene Datei, damit das Fenster die von Hand gepflegte redundanz_config.json nicht umschreibt.
SETTINGS_PATH = Path(__file__).with_name("redundanz_einstellungen.json")
_SCOPE_KEY = "anzeige"
_CONFIRMED_KEY = "bestaetigte_spielstaende"
SCOPE_PROBLEMS = "problematisch"
SCOPE_MARKED = "markiert"
SCOPE_ALL_FILES = "alle"
DEFAULT_SCOPE = SCOPE_PROBLEMS
_SCOPES = (
    (SCOPE_PROBLEMS, "Problematische Löschmarkierungen"),
    (SCOPE_MARKED, "Alle Löschmarkierungen"),
    (SCOPE_ALL_FILES, "Alle Romdateien"),
)
_LINE_COLOR = "#888888"
# Die Liste kennt keine echten Trennlinien, deshalb ist jeder Strich eine eigene Zeile.
_LINE_TEXT = "─" * 400
_SEPARATOR_SUFFIX = "s"
_NOTHING_TO_DO = "Nichts zu tun."
_NOTHING_TO_DO_STATUS = "Analyse beendet: Nichts zu tun"
_NOTHING_TO_DO_SCALE = 3
_BLINK_MS = 600
_FONT_FAMILY = "Lucida Sans Typewriter"
_FONT_SIZE = 11
_MIN_FONT_SIZE = 8
_MAX_FONT_SIZE = 32
_HELP = (
    "D: Demote, Datei löschen  |  P: Promote, Datei behalten  |  Tab / Umschalt+Tab: nächstes / voriges Spiel\n"
    "Pfeiltasten: Zeile wählen (Umschalt: mehrere)  |  Strg+Scrollrad: Schriftgröße  |  "
    "Strg+F: Filter (* und ?)  |  Strg+L: Ausführen  |  Strg+O: Ordner  |  F5: Neu analysieren  |  Esc: Schließen"
)
_MIN_WIDTH = 800  # Darunter überlappen sich die Zeilen über und unter der Liste.
_MIN_HEIGHT = 400
_FILTER_MIN_CHARS = 16
_DELETE_REDRAW_S = 0.05
_CELL_GAP = "  "  # Zellen der Liste haben keinen Innenabstand: Hält die rechtsbündige Größe vom Hinweis fern.
_SEARCH_DELAY_MS = 200  # Bei jedem Tastendruck die lange Liste neu aufzubauen, würde das Tippen bremsen.


def format_kb(size: int | None) -> str:
    """Wie im Windows Explorer: Kilobytes aufgerundet, mit Tausenderpunkten."""
    if size is None:
        return "?"
    return f"{-(-size // 1024):,} KB".replace(",", ".")


def _load_settings(path: Path) -> dict:
    """Eine fehlende oder kaputte Datei bedeutet: Es gelten die Vorgaben."""
    try:
        with open(path, encoding="utf-8-sig") as handle:
            settings = json.load(handle)
    except (OSError, ValueError):
        return {}
    return settings if isinstance(settings, dict) else {}


def _save_settings(path: Path, **values) -> None:
    """Ändert nur die angegebenen Einträge, damit sich Anzeige und bestätigte Dateien nicht gegenseitig überschreiben."""
    settings = _load_settings(path)
    settings.update(values)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def load_scope(path: Path) -> str:
    scope = _load_settings(path).get(_SCOPE_KEY)
    return scope if scope in (value for value, _label in _SCOPES) else DEFAULT_SCOPE


def save_scope(path: Path, scope: str) -> None:
    _save_settings(path, **{_SCOPE_KEY: scope})


def load_confirmed_saves(path: Path) -> dict[str, int]:
    """Beim Löschen bestätigte Status- oder Spielstanddateien: Dateischlüssel zu Größe in Bytes."""
    confirmed = _load_settings(path).get(_CONFIRMED_KEY)
    if not isinstance(confirmed, dict):
        return {}
    return {key: size for key, size in confirmed.items() if isinstance(size, int) and not isinstance(size, bool)}


def add_confirmed_saves(path: Path, files: dict[str, int]) -> None:
    _save_settings(path, **{_CONFIRMED_KEY: {**load_confirmed_saves(path), **files}})


class _AnalysisReplaced(Exception):
    """Eine neuere Analyse hat diese abgelöst."""


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
        self.root.title("Rom Cleanup Workbench (deutsch)")
        self.root.geometry("1100x650")
        self.root.minsize(_MIN_WIDTH, _MIN_HEIGHT)
        # Eine ausdrückliche Wahl beim Start geht dem gespeicherten Stand vor.
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
        self.folder.set(f"Ordner: {self.directory}" if self.directory else "Ordner: noch keiner gewählt (Strg+O)")
        self.info.set("\n".join(lines))

    def _clear(self) -> None:
        self.review = None
        self._files = {}
        self.tree.delete(*self.tree.get_children())
        self._hide_nothing_to_do()
        self._show_directory()

    def start_analysis(self) -> None:
        """Analysiert im Hintergrund, damit das Fenster beim Lesen großer ZIPs nicht hängt.

        Läuft schon eine Analyse, wird sie abgelöst: Ihr Ergebnis zählt nicht mehr.
        """
        if self.directory is None:
            return
        self._clear()
        self.status.set("Analysiere den Ordner ...")
        self._progress = None
        self.progress_bar.configure(value=0, maximum=1)
        self.progress_bar.place(in_=self.tree, relx=0.5, rely=0.5, relwidth=0.6, anchor="center")
        self.progress_bar.lift()
        # Räumt die Speicherbereinigung im Hintergrund-Thread Tk-Objekte ab, stürzt Tcl ab.
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
                raise _AnalysisReplaced  # Bricht die abgelöste Analyse beim nächsten Spiel ab.
            # Nur merken: Tk darf allein der Hauptthread anfassen, _poll_analysis zeigt den Stand an.
            self._progress = (done, total)

        try:
            answer.put((self.analyze(directory, report), None))
        except Exception as error:  # Jeder Fehler muss das Fenster erreichen, sonst bliebe es bei "Analysiere".
            answer.put((None, str(error) or type(error).__name__))

    def _poll_analysis(self, answer: queue.Queue) -> None:
        if answer is not self._analysis:
            return
        try:
            review, error = answer.get_nowait()
        except queue.Empty:
            if self._progress:
                done, total = self._progress
                self.status.set(f"Analysiere: {done} von {total} Dateien")
                self.progress_bar.configure(value=done, maximum=max(total, 1))
            self.root.after(100, self._poll_analysis, answer)
            return
        self.progress_bar.place_forget()
        self._analysis = None
        self._enable_gc_when_idle()
        self._finish_analysis(review, error)

    def _enable_gc_when_idle(self) -> None:
        """Auch eine abgelöste Analyse kann noch laufen, zum Beispiel in einem großen ZIP."""
        self._workers = [worker for worker in self._workers if worker.is_alive()]
        if self._workers:
            self.root.after(100, self._enable_gc_when_idle)
        elif self._analysis is None:
            gc.enable()

    def _finish_analysis(self, review, error: str | None) -> None:
        if error:
            self._clear()
            self.status.set(f"Analyse nicht möglich: {error}")
            messagebox.showerror("Analyse nicht möglich", error, parent=self.root)
        else:
            self.show_review(review)

    def analyze_now(self) -> None:
        """Analysiert ohne Hintergrund-Thread."""
        self.show_review(self.analyze(self.directory))

    def show_review(self, review) -> None:
        self.tree.selection_set(())
        self.review = review
        # Jedes Mal neu lesen: Die Datei kann sich inzwischen in einem anderen Fenster geändert haben.
        review.confirm_save_files(load_confirmed_saves(self.settings_path))
        # Jede Datei behält ihre Zeilen-ID, damit die Auswahl beim Verschieben erhalten bleibt.
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
        return messagebox.askyesno("Änderungen verwerfen?", question, default="no", parent=self.root)

    def reanalyze(self) -> None:
        if self._may_discard_changes("Deine Änderungen gehen verloren, und es wird nichts gelöscht. Neu analysieren?"):
            self.start_analysis()

    def choose_directory(self) -> None:
        if not self._may_discard_changes(
            "Deine Änderungen gehen verloren, und es wird nichts gelöscht. Anderen Ordner wählen?"
        ):
            return
        chosen = filedialog.askdirectory(
            parent=self.root, mustexist=True, title="Ordner wählen", initialdir=self.directory or None,
        )
        if chosen:
            self.directory = Path(chosen)
            self.start_analysis()

    def _apply_font(self) -> None:
        # Alle ttk-Elemente beziehen ihre Schrift aus diesen benannten Tk-Schriften.
        for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkCaptionFont"):
            tkfont.nametofont(name).configure(family=_FONT_FAMILY, size=self.font_size, weight="normal")

    def _row_height(self) -> int:
        return tkfont.nametofont("TkDefaultFont").metrics("linespace") + 6

    def change_font_size(self, steps: int) -> None:
        """Ändert die Schriftgröße im ganzen Fenster, auch die Zeilenhöhe der Liste."""
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
        """Der Kreis wächst mit der Schrift, damit der rote Punkt gut zu sehen bleibt."""
        size = max(12, round(tkfont.nametofont("TkDefaultFont").metrics("linespace") * 0.8))
        ttk.Style(self.root).configure("TRadiobutton", indicatorsize=size, indicatormargin=(0, 0, 8, 0))

    def _fit_size_column(self) -> None:
        """Breit genug für Dateien bis 99 GB, auch nach dem Ändern der Schriftgröße."""
        width = tkfont.nametofont("TkDefaultFont").measure(format_kb(99 * 1024**3) + _CELL_GAP) + 16
        self.tree.column("size", width=width, minwidth=width)

    def _fit_bottom_row(self) -> None:
        """Hält das Filterfeld neben den Knöpfen benutzbar, auch bei großer Schrift."""
        self.root.update_idletasks()
        needed = min(self.bottom_row.winfo_reqwidth(), self.root.winfo_screenwidth())
        self.root.minsize(max(_MIN_WIDTH, needed), _MIN_HEIGHT)

    def _on_zoom(self, event) -> str:
        self.change_font_size(1 if event.delta > 0 else -1)
        return "break"  # Sonst scrollt die Liste beim Vergrößern mit.

    def _apply_dark_mode(self) -> None:
        self.root.configure(background=_BLACK)
        style = ttk.Style(self.root)
        # Das Windows-Standardthema ignoriert Hintergrundfarben, "clam" übernimmt sie.
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
        # Ein heller Ring auf Dunkelgrau und ein roter Punkt für die gewählte Ansicht: Auf Schwarz ist die Vorgabe kaum zu sehen.
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
        """Schaltet die Windows-Titelleiste dunkel; bleibt sie hell, stört das nicht weiter."""
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
        # Ein langer Pfad bricht neben dem Titel um, statt abgeschnitten zu werden.
        self.title_row.bind(
            "<Configure>",
            lambda event: self.folder_label.configure(
                wraplength=max(event.width - self.title_label.winfo_reqwidth() - 16, 1)
            ),
        )

        # Bricht bei großer Schrift um, statt rechts abgeschnitten zu werden.
        help_label = ttk.Label(self.root, text=_HELP, padding=8)
        help_label.pack(fill="x")
        help_label.bind("<Configure>", lambda event: help_label.configure(wraplength=event.width - 16))
        info_label = ttk.Label(self.root, textvariable=self.info, padding=(8, 0, 8, 8))
        info_label.pack(fill="x")
        info_label.bind("<Configure>", lambda event: info_label.configure(wraplength=event.width - 16))

        # Der Status steht in einer eigenen Zeile, damit er die Knöpfe nicht verdrängt.
        bottom = ttk.Frame(self.root, padding=8)
        bottom.pack(side="bottom", fill="x")
        self.status_label = ttk.Label(self.root, textvariable=self.status, style=_HIGHLIGHT_STYLE, padding=8)
        self.status_label.pack(side="bottom", fill="x")
        self.status_label.bind("<Configure>", lambda event: self.status_label.configure(wraplength=event.width - 16))
        # Die Knöpfe zuerst, damit sie bei wenig Platz sichtbar bleiben und nicht das Häkchen.
        ttk.Button(bottom, text="Schließen", command=self.close).pack(side="right")
        # "Ausführen": Außer dem Löschen bestätigt der Knopf auch die vermuteten Spielstanddateien.
        ttk.Button(bottom, text="Ausführen...", command=self.confirm_delete).pack(side="right", padx=8)
        ttk.Button(bottom, text="Neu analysieren", command=self.reanalyze).pack(side="right")
        ttk.Button(bottom, text="Ordner...", command=self.choose_directory).pack(side="right", padx=8)
        ttk.Label(bottom, text="Dateinamen filtern:").pack(side="left", padx=(0, 8))
        self.search_entry = ttk.Entry(bottom, textvariable=self.search, width=_FILTER_MIN_CHARS)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self._bind_search_entry()
        self.bottom_row = bottom

        # Über der grünen Zeile, damit sie die vorletzte Zeile des Fensters bleibt.
        options = ttk.Frame(self.root, padding=(8, 8, 8, 0))
        options.pack(side="bottom", fill="x")
        for value, label in _SCOPES:
            ttk.Radiobutton(
                options, text=label, value=value, variable=self.scope, command=self._scope_changed,
            ).pack(side="left", padx=(0, 16))

        middle = ttk.Frame(self.root)
        middle.pack(fill="both", expand=True)
        # "hint" bleibt der erste Wert jeder Zeile; nur die Anzeige stellt die Größe davor.
        self.tree = ttk.Treeview(
            middle, columns=("hint", "size"), displaycolumns=("size", "hint"), selectmode="extended",
        )
        self.tree.heading("#0", text="Datei", anchor="w")
        self.tree.heading("size", text="Größe" + _CELL_GAP, anchor="e")
        self.tree.heading("hint", text="Hinweis", anchor="w")
        self.tree.column("#0", width=560, stretch=True)
        self.tree.column("size", anchor="e", stretch=False)
        self.tree.column("hint", width=500, stretch=True)
        self._fit_size_column()
        scrollbar = ttk.Scrollbar(middle, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.nothing_font =self.bold_font.copy()
        self.nothing_font.configure(size=self.font_size * _NOTHING_TO_DO_SCALE)
        self.nothing_label = ttk.Label(middle, text=_NOTHING_TO_DO, font=self.nothing_font)
        self.progress_bar = ttk.Progressbar(middle, orient="horizontal", mode="determinate")
        # Früher angelegte Tags haben Vorrang: Eine verschobene Datei bleibt auch im Streifen braun.
        self.tree.tag_configure("moved", background=_MOVED)
        self.tree.tag_configure("striped", background=_DARK_GRAY)
        self.tree.tag_configure("game", font=self.bold_font)
        self.tree.tag_configure("problem", font=self.bold_font)
        self.tree.tag_configure("keep", font=self.bold_font)
        self.tree.tag_configure("separator", foreground=_LINE_COLOR)

        # Am Fenster statt an der Liste, damit die Tasten auch nach einem Klick auf das Häkchen wirken.
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
        # "break" verhindert, dass Tab wie üblich den Fokus zum nächsten Knopf weitergibt.
        self.root.bind("<Tab>", lambda _event: self._move_game(1))
        self.root.bind("<Shift-Tab>", lambda _event: self._move_game(-1))
        self.root.bind("<Escape>", lambda _event: self.close())
        # Die Liste braucht eine eigene Bindung, weil ihre Standardbindung sonst zuerst scrollt.
        self.root.bind("<Control-MouseWheel>", self._on_zoom)
        self.tree.bind("<Control-MouseWheel>", self._on_zoom)
        # Die Standardtasten der Liste würden auf den Trennstrichen halten und kennen kein Umschalt.
        self.tree.bind("<Up>", lambda _event: self._move_cursor(-1, False))
        self.tree.bind("<Down>", lambda _event: self._move_cursor(1, False))
        self.tree.bind("<Shift-Up>", lambda _event: self._move_cursor(-1, True))
        self.tree.bind("<Shift-Down>", lambda _event: self._move_cursor(1, True))
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._drop_separators_from_selection())
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _bind_search_entry(self) -> None:
        # Ohne den Bindetag des Fensters kann ein hier getipptes "d" oder "p" keine Löschmarkierung ändern.
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
        """Zeigt das aktuelle Ergebnis sofort und kehrt zur Liste zurück; Esc leert zusätzlich den Filter."""
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
        # Vom Filter ausgeblendete Zeilen verlassen die Auswahl; D und P sollen auf das Angezeigte wirken.
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
        # Auch wenn eine Analyse während des Tippens endet: In der Liste könnte der nächste Buchstabe ein D oder P sein.
        if self.root.focus_get() is not self.search_entry:
            self.tree.focus_set()

    def _scope_flags(self) -> tuple[bool, bool, str]:
        """Übersetzt die Auswahl in die Angaben only_problems, show_all und pattern des Review-Objekts."""
        return self.scope.get() == SCOPE_PROBLEMS, self.scope.get() == SCOPE_ALL_FILES, self.search.get()

    def _scope_changed(self) -> None:
        """Zeigt die Auswahl an und merkt sie sich für den nächsten Start."""
        self._show_all_groups()
        try:
            save_scope(self.settings_path, self.scope.get())
        except OSError as error:
            messagebox.showerror("Auswahl nicht gespeichert", str(error), parent=self.root)

    def _show_nothing_to_do(self) -> None:
        self.status.set(_NOTHING_TO_DO_STATUS)
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
                group_id, "end", f"{group_id}k", text="Bleibt erhalten:", open=True,
                tags=self._tags(group_id, "section"),
            )
            for entry in result.keep:
                self._insert_file(group_id, section, entry, "+", "keep", "Von Hand: behalten")
        if result.marked:
            section = self.tree.insert(
                group_id, "end", f"{group_id}h", text="Zum Löschen markiert", open=True,
                tags=self._tags(group_id, "section"),
            )
            for entry in result.marked:
                self._insert_file(group_id, section, entry, "-", "marked", "Von Hand: löschen")

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
        """Liefert die nächste sichtbare Zeile; "" am Ende der Liste."""
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
        """Liefert die vorige sichtbare Zeile; "" am Anfang der Liste."""
        previous = self.tree.prev(row)
        if not previous:
            return self.tree.parent(row)
        while self.tree.item(previous, "open") and self.tree.get_children(previous):
            previous = self.tree.get_children(previous)[-1]
        return previous

    def _move_cursor(self, step: int, extend: bool) -> str:
        """Bewegt die Auswahl über die Trennstriche hinweg; mit extend wächst oder schrumpft sie."""
        current = self.tree.focus()
        neighbor = self._next_row if step > 0 or not current else self._previous_row
        target = neighbor(current)
        while target and self._is_separator(target):
            target = neighbor(target)
        if target:
            if not extend:
                self.tree.selection_set(target)
            elif target in self.tree.selection():
                self.tree.selection_remove(current)  # Rückwärts: Die Auswahl schrumpft wieder.
            else:
                self.tree.selection_add(target)
            self.tree.focus(target)
            self.tree.see(target)
        return "break"

    def _move_game(self, step: int) -> str:
        """Springt zum Nachbarspiel und wählt dessen erste Datei, damit D und P sofort wirken."""
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
            # Erst das Ende, dann der Titel: So ist das ganze Spiel zu sehen, wenn es passt.
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
        if not messagebox.askyesno("Endgültig löschen?", message, icon="warning", default="no", parent=self.root):
            return
        # Vor dem Löschen erfasst: Danach werden sie als legitim gemerkt.
        save_files = self.review.save_file_keys()
        deleted, errors = self._delete_with_progress()
        self._remember_save_files(save_files)
        if errors:
            self.had_errors = True
            messagebox.showwarning(
                "Nicht alles gelöscht",
                f"{deleted} Datei(en) gelöscht.\n\nFehler:\n" + "\n".join(errors),
                parent=self.root,
            )
        else:
            messagebox.showinfo("Gelöscht", f"{deleted} Datei(en) gelöscht.", parent=self.root)
        # Das Review-Objekt hat die gelöschten Dateien entfernt; der Ordner wird nicht neu analysiert.
        self.show_review(self.review)

    def _confirm_save_files_only(self) -> None:
        """Ohne markierte Dateien kann Strg+L trotzdem die vermuteten Status- oder Spielstanddateien bestätigen."""
        save_files = self.review.save_file_keys()
        if not save_files:
            messagebox.showinfo("Nichts zu löschen", "Es ist keine Datei zum Löschen markiert.", parent=self.root)
            return
        question = (
            f"Es ist keine Datei zum Löschen markiert.\n\n{len(save_files)} vermutete Status- oder "
            "Spielstanddatei(en) als legitim bestätigen? Sie bleiben, wo sie sind, und werden nicht mehr angezeigt."
        )
        if messagebox.askyesno("Spielstände bestätigen?", question, default="no", parent=self.root):
            self._remember_save_files(save_files)
            self.show_review(self.review)

    def _remember_save_files(self, save_files: dict[str, int]) -> None:
        if not save_files:
            return
        try:
            add_confirmed_saves(self.settings_path, save_files)
        except OSError as error:
            messagebox.showerror("Spielstände nicht gemerkt", str(error), parent=self.root)

    def _delete_with_progress(self) -> tuple[int, list[str]]:
        """Löscht im Hauptthread und zeichnet dazwischen nur neu.

        update_idletasks verarbeitet keine Tasten oder Klicks, deshalb kann während des Löschens
        niemand die Markierungen ändern, ein zweites Löschen starten oder das Fenster schließen.
        """
        last_redraw = 0.0

        def report(done: int, total: int) -> None:
            nonlocal last_redraw
            now = time.monotonic()
            if done not in (0, total) and now - last_redraw < _DELETE_REDRAW_S:
                return  # Nach jeder Datei neu zu zeichnen, würde große Löschvorgänge bremsen.
            last_redraw = now
            self.status.set(f"Lösche: {done} von {total} Dateien")
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
        if self._may_discard_changes("Deine Änderungen gehen verloren, und es wird nichts gelöscht. Schließen?"):
            self.root.destroy()

    def run(self) -> int:
        if self.directory is None:
            self.status.set("Bitte einen Ordner wählen.")
            self.root.after(100, self.choose_directory)
        else:
            self.start_analysis()
        self.root.mainloop()
        return 1 if self.had_errors else 0


def run_window(analyze, directory: Path | None, scope: str | None = None) -> int:
    """Zeigt das Fenster und liefert den Rückgabewert des Programms."""
    return ReviewWindow(analyze, directory, scope).run()
