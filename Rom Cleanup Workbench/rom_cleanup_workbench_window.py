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

"""Analysis window: analyze a folder, review the result, reorder with x and k, and delete.

The rules are in the Review object from rom_cleanup_workbench.py. This module does not import
the program, because it would otherwise be loaded a second time when started as a script.
"""

from __future__ import annotations

import ctypes
import gc
import os
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox as _system_messagebox
from tkinter import ttk

from translations import LANGUAGE_NAMES, current_language, tr
# The settings file, the views, sizes and folders are shared with the terminal version.
from workbench_state import (  # noqa: F401  (SETTINGS_PATH and the scope names belong to this module's interface)
    DEFAULT_SCOPE, SCOPE_ALL_FILES, SCOPE_MARKED, SCOPE_PROBLEMS, SETTINGS_PATH, add_confirmed_saves,
    format_kb, load_confirmed_saves, load_hide_empty, load_last_collection, load_scope, save_hide_empty,
    save_last_collection, save_scope,
)
from workbench_state import SCOPES as _SCOPES
from workbench_state import drives as _drives
from workbench_state import subfolders as _subfolders

_BLACK = "#000000"
_WHITE = "#ffffff"
_DARK_GRAY = "#222222"
_GRAY = "#444444"
_LIGHT_GRAY = "#666666"
_SELECTED = "#0a4a8a"
_MOVED = "#5c4400"
_GREEN = "#1a7f37"
_RED = "#e5383b"
# The text of the file rows: kept files green, marked files red; light enough on black.
_KEEP_TEXT = "#3fb950"
_DOT_STYLE = "Dot.TCheckbutton"  # a switch that looks like the view choice: red dot when on
_MARKED_TEXT = "#ff6b6b"
_HIGHLIGHT_STYLE = "Highlight.TLabel"
_HIGHLIGHT_FRAME_STYLE = "Highlight.TFrame"
_APP_NAME = "Rom Cleanup Workbench"
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


def _call_analyze(analyze, directory, progress, rescan: bool, full: bool = False):
    """Passes rescan and full only to an analysis that knows them (tests hand in simpler ones)."""
    import inspect

    try:
        parameters = inspect.signature(analyze).parameters
    except (TypeError, ValueError):
        parameters = {}
    options = {name: value for name, value in (("rescan", rescan), ("full", full)) if name in parameters}
    return analyze(directory, progress, **options)


class FolderPanel:
    """Chooses a folder in place of the file list, instead of the Windows folder dialog.

    The Windows dialog labels its buttons in the language of Windows; this one speaks the program's language.
    """

    _PLACEHOLDER = "…"

    def __init__(self, window: "ReviewWindow", start: Path | None):
        self.window = window
        frame = self.frame = ttk.Frame(window.middle, padding=(16, 8, 16, 8))
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        heading = ttk.Frame(frame)
        heading.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        ttk.Button(heading, text=tr("settings.cancel"), command=self.close).pack(side="right")
        ttk.Button(heading, text=tr("folder.select"), command=self.choose).pack(side="right", padx=8)
        ttk.Label(heading, text=tr("window.choose_folder"), font=window.bold_font).pack(side="left")

        ttk.Label(frame, text=tr("folder.path")).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        self.path = tk.StringVar(frame)
        self.entry = ttk.Entry(frame, textvariable=self.path)
        self.entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(0, 8))
        self.entry.bind("<Return>", lambda _event: self.choose())

        self.tree = ttk.Treeview(frame, show="tree", selectmode="browse")
        self.tree.grid(row=2, column=0, columnspan=2, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=2, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewOpen>>", lambda _event: self._load(self.tree.focus()))
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._show_selection())
        self.tree.bind("<Return>", lambda _event: self.choose())
        self.tree.bind("<Double-Button-1>", self._choose_clicked)
        hint = ttk.Label(frame, text=tr("folder.hint"))
        hint.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        hint.bind("<Configure>", lambda event: hint.configure(wraplength=max(event.width, 1)))

        # Where text is typed, the window's keys must not fire: An "x" in a path marks nothing.
        for widget in (self.entry, self.tree):
            widget.bindtags((str(widget), widget.winfo_class(), "all"))
            widget.bind("<Escape>", lambda _event: self.close())
            widget.bind("<Control-MouseWheel>", window._on_zoom)
        self.tree.bind("<Control-MouseWheel>", window._on_zoom)

        self.paths: dict[str, Path] = {}
        for drive in _drives():
            self._insert("", drive, str(drive))
        self.reveal(start if start is not None and start.is_dir() else Path.home())
        self.tree.focus_set()

    @staticmethod
    def _key(path: Path) -> str:
        return os.path.normcase(os.path.abspath(path))

    def _insert(self, parent: str, path: Path, text: str) -> str:
        key = self._key(path)
        if self.tree.exists(key):
            return key
        self.paths[key] = path
        self.tree.insert(parent, "end", key, text=text)
        # A placeholder, so that the folder shows the open arrow; it is replaced when the folder opens.
        self.tree.insert(key, "end", key + self._PLACEHOLDER, text=self._PLACEHOLDER)
        return key

    def _load(self, key: str) -> None:
        """Reads the subfolders only when a folder opens, so that large drives cost nothing."""
        placeholder = key + self._PLACEHOLDER
        if not key or not self.tree.exists(placeholder):
            return
        self.tree.delete(placeholder)
        for folder in _subfolders(self.paths[key]):
            self._insert(key, folder, folder.name)

    def reveal(self, path: Path) -> None:
        """Opens the tree down to path and selects it, as far as the folders exist."""
        path = Path(os.path.abspath(path))
        chain = [path, *path.parents]
        key = ""
        for folder in reversed(chain):
            candidate = self._key(folder)
            if not self.tree.exists(candidate):
                if key:
                    self._load(key)
                if not self.tree.exists(candidate):
                    break
            key = candidate
            self.tree.item(key, open=True)
            self._load(key)
        if key:
            self.tree.selection_set(key)
            self.tree.focus(key)
            self.tree.see(key)
            self.path.set(str(self.paths[key]))  # At once: Tk delivers the selection event only later.

    def _show_selection(self) -> None:
        selection = self.tree.selection()
        if selection and selection[0] in self.paths:
            self.path.set(str(self.paths[selection[0]]))

    def _choose_clicked(self, event) -> str | None:
        """A double click chooses the folder; on the arrow it only opens or closes it, as before."""
        key = self.tree.identify_row(event.y)
        if not key or key not in self.paths or "indicator" in self.tree.identify_element(event.x, event.y):
            return None
        self.tree.selection_set(key)
        self.tree.focus(key)
        self.path.set(str(self.paths[key]))
        return self.choose()  # "break": the tree does not open the folder as well

    def choose(self) -> str:
        text = self.path.get().strip().strip('"')
        folder = Path(text) if text else None
        if folder is None or not folder.is_dir():
            messagebox.showerror(
                tr("window.choose_folder"), tr("error.directory_not_found", directory=text), parent=self.window.root,
            )
            return "break"
        self.window.folder_chosen(folder)
        return "break"

    def close(self) -> str:
        self.window.close_folder_panel()
        return "break"


# Every open window under the name of its Tk root, so that a question finds the window it belongs to.
_WINDOWS: dict = {}


class _InWindowMessages:
    """Questions and messages inside the program window instead of Windows popups.

    Windows labels the buttons of its popups in its own language, whatever language the program speaks.
    The calls are the same as those of tkinter.messagebox, so the code and its tests stay as they are.
    """

    @staticmethod
    def _ask(kind, title, message, buttons, default, parent):
        window = _WINDOWS.get(str(parent))
        if window is None:  # No program window, for example a test of a single function.
            show = {"question": _system_messagebox.askyesno, "info": _system_messagebox.showinfo,
                    "warning": _system_messagebox.showwarning, "error": _system_messagebox.showerror}[kind]
            return show(title, message, parent=parent)
        return window.ask(kind, title, message, buttons, default)

    def askyesno(self, title, message, *, parent=None, default="yes", icon="question", **_options) -> bool:
        buttons = (("dialog.yes", True), ("dialog.no", False))
        return bool(self._ask("warning" if icon == "warning" else "question", title, message, buttons,
                              default == "yes", parent))

    def showinfo(self, title, message, *, parent=None, **_options) -> None:
        self._ask("info", title, message, (("dialog.ok", None),), None, parent)

    def showwarning(self, title, message, *, parent=None, **_options) -> None:
        self._ask("warning", title, message, (("dialog.ok", None),), None, parent)

    def showerror(self, title, message, *, parent=None, **_options) -> None:
        self._ask("error", title, message, (("dialog.ok", None),), None, parent)


messagebox = _InWindowMessages()


class _AnalysisReplaced(Exception):
    """A newer analysis has replaced this one."""


class SettingsPanel:
    """Edits language, region priority, delete keywords and ZIP or plain file in place of the file list.

    The list and everything that acts on it is locked meanwhile (see ReviewWindow._refresh_locks).
    """

    def __init__(self, window: "ReviewWindow"):
        from workbench_db import settings_for

        self.window = window
        # A platform of a collection may have settings of its own (stored in the database).
        self.root_folder, self.platform = window.settings_platform()
        # A broken file raises ValueError before anything opens.
        self.values, own = settings_for(window.config_file, self.root_folder, self.platform)
        self.own_before = own
        frame = self.frame = ttk.Frame(window.middle, padding=(16, 8, 16, 8))
        frame.columnconfigure(0, weight=1, uniform="half")
        frame.columnconfigure(1, weight=1, uniform="half")
        frame.rowconfigure(2, weight=1)
        self.own = tk.BooleanVar(frame, own)
        if self.platform is not None:
            scope = ttk.Frame(frame)
            scope.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 24))
            scope.columnconfigure(3, weight=1)
            ttk.Label(scope, text=tr("settings.scope_label")).grid(row=0, column=0, sticky="w", padx=(0, 16))
            self.scope_buttons = [
                ttk.Radiobutton(scope, text=text, variable=self.own, value=value, command=self._scope_changed)
                for text, value in ((tr("settings.scope_default"), False),
                                    (tr("settings.scope_own", platform=self.platform.upper()), True))
            ]
            for column, button in enumerate(self.scope_buttons, start=1):
                button.grid(row=0, column=column, sticky="w", padx=(0, 16))
            # What "own" means, in a line of its own below the two choices.
            scope_hint = ttk.Label(scope, text=tr("settings.scope_own_hint", platform=self.platform.upper()),
                                   foreground=_LIGHT_GRAY)
            scope_hint.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(4, 0))
            scope_hint.bind("<Configure>", lambda event: scope_hint.configure(wraplength=max(event.width, 1)))
        heading = ttk.Frame(frame)
        heading.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        # Save and Cancel at the top, so that they stay visible even in a low window.
        ttk.Button(heading, text=tr("settings.cancel"), command=self.close).pack(side="right")
        ttk.Button(heading, text=tr("settings.save"), command=lambda: window.save_settings(self)).pack(side="right", padx=8)
        ttk.Label(heading, text=tr("settings.title"), font=window.bold_font).pack(side="left", padx=(0, 16))
        from workbench_db import settings_location

        # Where the settings are saved, in a line of its own below: a long path must not hide behind the buttons.
        self.location_label = ttk.Label(heading, text=settings_location(window.config_file, self.root_folder, own),
                                        foreground=_LIGHT_GRAY)
        self.location_label.pack(side="bottom", fill="x", anchor="w", pady=(8, 0), before=heading.winfo_children()[0])
        self.location_label.bind("<Configure>", lambda event: self.location_label.configure(
            wraplength=max(event.width, 1)))

        # Two columns side by side, so that the region list keeps its height in a low window.
        left = ttk.Frame(frame)
        left.grid(row=2, column=0, sticky="nsew", padx=(0, 16))
        left.columnconfigure(2, weight=1)
        left.rowconfigure(3, weight=1)  # the list keeps its size; free space stays below
        # Wraps like the labels on the right: the text names the keywords after none and is long.
        regions_label = ttk.Label(left, text=tr("settings.regions"))
        regions_label.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        regions_label.bind("<Configure>", lambda event: regions_label.configure(wraplength=max(event.width, 1)))
        self.regions_label = regions_label
        self.regions = tk.Listbox(
            left, height=max(4, min(8, len(self.values["region_priority"]) + 1)), width=24, activestyle="none", exportselection=False, font="TkDefaultFont",
            background=_DARK_GRAY, foreground=_WHITE, selectbackground=_SELECTED, selectforeground=_WHITE,
            highlightthickness=1, highlightbackground=_GRAY, highlightcolor=_LINE_COLOR, borderwidth=0,
        )
        self.regions.grid(row=1, column=0, sticky="nw")
        for region in self.values["region_priority"]:
            self.regions.insert("end", region)
        self.regions.bind("<Delete>", lambda _event: self.remove())
        buttons = ttk.Frame(left)
        buttons.grid(row=1, column=1, sticky="n", padx=(8, 0))
        for key, command in (("settings.up", lambda: self.move(-1)), ("settings.down", lambda: self.move(1)),
                             ("settings.remove", self.remove)):
            ttk.Button(buttons, text=tr(key), command=command).pack(fill="x", pady=(0, 4))
        self.new_region = tk.StringVar(frame)
        new_entry = ttk.Entry(left, textvariable=self.new_region, width=24)
        new_entry.grid(row=2, column=0, sticky="nw", pady=(12, 0))
        new_entry.bind("<Return>", lambda _event: self.add())
        ttk.Button(left, text=tr("settings.add"), command=self.add).grid(row=2, column=1, sticky="nw", padx=(8, 0), pady=(12, 0))

        right = ttk.Frame(frame)
        right.grid(row=2, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(8, weight=1)
        ttk.Label(right, text=tr("settings.language")).grid(row=0, column=0, sticky="w", pady=(0, 8))
        name = LANGUAGE_NAMES.get(self.values["language"], LANGUAGE_NAMES[current_language()])
        self.language = tk.StringVar(frame, name)
        language_box = ttk.Combobox(
            right, textvariable=self.language, values=list(LANGUAGE_NAMES.values()), state="readonly", width=16,
        )
        language_box.grid(row=1, column=0, sticky="w")
        hint = ttk.Label(right, text=tr("settings.language_hint"))
        hint.grid(row=2, column=0, sticky="ew", pady=(8, 28))
        hint.bind("<Configure>", lambda event: hint.configure(wraplength=max(event.width, 1)))
        tags_label = ttk.Label(right, text=tr("settings.delete_keywords"))
        tags_label.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        tags_label.bind("<Configure>", lambda event: tags_label.configure(wraplength=max(event.width, 1)))
        # The delete keywords (delete_tags): extra info that marks a file for deletion by default.
        self.tags = tk.StringVar(frame, ", ".join(self.values["delete_tags"]))
        tags_entry = ttk.Entry(right, textvariable=self.tags)
        tags_entry.grid(row=4, column=0, sticky="ew")
        # prefer_zip: which of the two remains when a game exists as a plain file and as a ZIP file.
        prefer_label = ttk.Label(right, text=tr("settings.prefer"))
        prefer_label.grid(row=5, column=0, sticky="ew", pady=(28, 8))
        prefer_label.bind("<Configure>", lambda event: prefer_label.configure(wraplength=max(event.width, 1)))
        self.prefer_zip = tk.BooleanVar(frame, bool(self.values["prefer_zip"]))
        self.prefer_buttons = [
            ttk.Radiobutton(right, text=tr(key), variable=self.prefer_zip, value=value)
            for key, value in (("settings.prefer_plain", False), ("settings.prefer_zip", True))
        ]
        for row, button in enumerate(self.prefer_buttons, start=6):
            button.grid(row=row, column=0, sticky="w", pady=(0, 6))

        # Where text is typed, the window's keys must not fire: An "x" in a region name marks nothing.
        for widget in (language_box, self.regions, new_entry, tags_entry):
            widget.bindtags((str(widget), widget.winfo_class(), "all"))
            widget.bind("<Escape>", lambda _event: self.close())
            widget.bind("<Control-MouseWheel>", window._on_zoom)
        self.regions.bind("<Control-e>", lambda _event: self.close())
        new_entry.focus_set()

    def language_code(self) -> str:
        chosen = self.language.get()
        return next((code for code, name in LANGUAGE_NAMES.items() if name == chosen), current_language())

    def region_list(self) -> list[str]:
        return list(self.regions.get(0, "end"))

    def tag_list(self) -> list[str]:
        return [tag.strip() for tag in self.tags.get().split(",") if tag.strip()]

    def prefers_zip(self) -> bool:
        return bool(self.prefer_zip.get())

    def _scope_changed(self) -> None:
        """Default or own: the fields show the values of that choice (own starts from the default)."""
        from workbench_db import settings_for

        from workbench_db import settings_location

        values, _own = settings_for(self.window.config_file, self.root_folder, self.platform, own=self.own.get())
        self.location_label.configure(text=settings_location(self.window.config_file, self.root_folder, self.own.get()))
        self.window.root.after_idle(self.window._grow_to_fit)  # the longer line may wrap
        self.regions.delete(0, "end")
        for region in values["region_priority"]:
            self.regions.insert("end", region)
        self.tags.set(", ".join(values["delete_tags"]))
        self.prefer_zip.set(bool(values["prefer_zip"]))

    def _select(self, index: int) -> None:
        self.regions.selection_clear(0, "end")
        if self.regions.size():
            index = max(0, min(index, self.regions.size() - 1))
            self.regions.selection_set(index)
            self.regions.see(index)

    def move(self, step: int) -> None:
        selection = self.regions.curselection()
        if not selection:
            return
        index = selection[0]
        target = index + step
        if 0 <= target < self.regions.size():
            region = self.regions.get(index)
            self.regions.delete(index)
            self.regions.insert(target, region)
            self._select(target)

    def remove(self) -> None:
        selection = self.regions.curselection()
        if selection:
            self.regions.delete(selection[0])
            self._select(selection[0])

    def add(self) -> None:
        region = self.new_region.get().strip()
        if not region:
            return
        existing = [index for index, other in enumerate(self.region_list()) if other.casefold() == region.casefold()]
        if existing:
            self._select(existing[0])  # Already in the list: show it instead of adding it twice.
        else:
            self.regions.insert("end", region)
            self._select(self.regions.size() - 1)
        self.new_region.set("")

    def close(self) -> str:
        """Returns to the file list without saving."""
        self.window.close_settings()
        return "break"


class KeysPanel:
    """All keys of the current view, grouped, in place of the list or the overview (F1 or ?)."""

    def __init__(self, window: "ReviewWindow", context: str):
        from workbench_keys import key_notes, key_sections, keys_title

        self.window = window
        self.context = context
        frame = self.frame = ttk.Frame(window.middle, padding=(16, 8, 16, 8))
        heading = ttk.Frame(frame)
        heading.pack(fill="x", pady=(0, 12))
        ttk.Label(heading, text=keys_title(context), font=window.bold_font, foreground=_KEEP_TEXT).pack(side="left")
        ttk.Label(heading, text=tr("keys.close_hint"), foreground=_LIGHT_GRAY).pack(side="right")
        columns = ttk.Frame(frame)
        columns.pack(fill="x", anchor="nw")
        sections = key_sections(context, window=True, collection=window.collection_root is not None)
        left = (len(sections) + 1) // 2  # the first half of the sections on the left, the rest on the right
        self.key_labels = []
        for part in (sections[:left], sections[left:]):
            column = ttk.Frame(columns)
            column.pack(side="left", fill="y", anchor="nw", padx=(0, 48))
            row = 0
            for title, rows in part:
                ttk.Label(column, text=title.upper(), font=window.bold_font).grid(
                    row=row, column=0, columnspan=2, sticky="w", pady=(0 if row == 0 else 12, 4))
                for key, text in rows:
                    row += 1
                    ttk.Label(column, text=key, font=window.bold_font, foreground=_KEEP_TEXT).grid(
                        row=row, column=0, sticky="w", padx=(16, 24))
                    ttk.Label(column, text=text).grid(row=row, column=1, sticky="w")
                    self.key_labels.append((key, text))
                row += 1
        self.notes = key_notes(context)
        if self.notes:
            ttk.Label(frame, text=tr("keys.section.notes").upper(), font=window.bold_font).pack(
                anchor="w", pady=(16, 4))
            for note in self.notes:  # one point each, wrapped under its own text
                line = ttk.Frame(frame, padding=(16, 0, 0, 2))
                line.pack(fill="x", anchor="w")
                ttk.Label(line, text="•", foreground=_KEEP_TEXT).pack(side="left", anchor="n", padx=(0, 10))
                label = ttk.Label(line, text=note)
                label.pack(side="left", fill="x", expand=True, anchor="w")
                label.bind("<Configure>", lambda event, label=label: label.configure(
                    wraplength=max(event.width, 1)))


class OverviewPanel:
    """The collection: one row per platform folder, in place of the file list. The start page."""

    _COLUMNS = ("files", "games", "marked", "problematic", "last_scan", "state")

    def __init__(self, window: "ReviewWindow", rows):
        self.window = window
        self.rows = {row.folder: row for row in rows}
        frame = self.frame = ttk.Frame(window.middle, padding=(16, 8, 16, 8))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        heading = ttk.Frame(frame)
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.full = tk.BooleanVar(frame, False)
        self.buttons = []
        for key, command in (("overview.scan_all", window.scan_all),
                             ("overview.scan", lambda: self.open(rescan=True, full=self.full.get())),
                             ("overview.open", self.open)):
            button = ttk.Button(heading, text=tr(key), command=command)
            button.pack(side="right", padx=(8, 0))
            self.buttons.append(button)
        self.full_box = ttk.Checkbutton(heading, text=tr("overview.full"), variable=self.full, style=_DOT_STYLE)
        self.full_box.pack(side="right", padx=(8, 0))
        self.hide_empty = tk.BooleanVar(frame, load_hide_empty(window.settings_path))
        self.hide_box = ttk.Checkbutton(heading, text=tr("overview.hide_empty"), variable=self.hide_empty,
                                        command=self._hide_empty_changed, style=_DOT_STYLE)
        self.hide_box.pack(side="right", padx=(8, 0))
        self.cancel_button = ttk.Button(heading, text=tr("settings.cancel"), command=window.cancel_scan_all)
        ttk.Label(heading, text=tr("overview.title"), font=window.bold_font, foreground=_KEEP_TEXT).pack(side="left")

        self.tree = ttk.Treeview(frame, columns=self._COLUMNS, selectmode="browse")
        self.tree.heading("#0", text=tr("overview.platform"), anchor="w")
        self.tree.column("#0", width=200, stretch=True)
        for column in self._COLUMNS:
            numeric = column in ("files", "games", "marked", "problematic")
            self.tree.heading(column, text=tr(f"overview.{column}"), anchor="e" if numeric else "w")
            self.tree.column(column, width=110 if numeric else 200, anchor="e" if numeric else "w",
                             stretch=not numeric)
        self.tree.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self._fit_columns(rows)
        self.tree.tag_configure("total", font=window.bold_font)
        self._fill()
        self.tree.bind("<Double-Button-1>", self._open_clicked)
        self.tree.bind("<Return>", lambda _event: self.open() or "break")
        # Ctrl+mouse wheel changes the font size here as in the list (the window's binding is not reached).
        self.tree.bind("<Control-MouseWheel>", window._on_zoom)
        self.tree.bindtags((str(self.tree), self.tree.winfo_class(), str(window.root), "all"))

    def visible(self) -> list:
        """The rows shown: all, or without the folders that hold no game file."""
        return [row for row in self.rows.values() if row.has_games or not self.hide_empty.get()]

    def _fill(self) -> None:
        """Shows the visible rows and the total; the highlighted platform stays if it is still shown."""
        selected = self.selected()
        self.tree.delete(*self.tree.get_children())
        visible = self.visible()
        for row in visible:
            self.tree.insert("", "end", row.folder, text=row.folder + (" *" if row.has_own_config else ""),
                             values=self._values(row))
        self.tree.insert("", "end", self._TOTAL, text=tr("overview.total"), tags=("total",))
        totals = self._update_total()
        first = selected if selected in {row.folder for row in visible} else (visible[0].folder if visible else None)
        if first is not None:
            self.tree.selection_set(first)
            self.tree.focus(first)
            self.tree.see(first)
        self.window.status.set(tr("overview.status", platforms=len(visible), files=_count(totals[0])))

    def _hide_empty_changed(self) -> None:
        save_hide_empty(self.window.settings_path, self.hide_empty.get())
        self._fill()

    def toggle_hide_empty(self) -> None:
        self.hide_empty.set(not self.hide_empty.get())
        self._hide_empty_changed()

    _TOTAL = "*total*"  # no folder name: * is not allowed in Windows names

    @staticmethod
    def _values(row) -> tuple:
        return (*(_count(value) for value in (row.files, row.games, row.marked, row.problematic)),
                _when(row.last_scan), tr(f"overview.state.{row.state}"))

    def _update_total(self) -> list[int]:
        totals = [sum(getattr(row, name) or 0 for row in self.visible())
                  for name in ("files", "games", "marked", "problematic")]
        self.tree.item(self._TOTAL, values=(*(_count(value) for value in totals), "", ""))
        return totals

    def set_row(self, row) -> None:
        """A platform's new numbers, for example as soon as scan all has finished it."""
        if row.folder not in self.rows:
            return
        self.rows[row.folder] = row
        if self.tree.exists(row.folder):
            self.tree.item(row.folder, values=self._values(row))
        self._update_total()

    def _fit_columns(self, rows) -> None:
        """Every column as wide as its heading and its longest value, in the window's font."""
        font = tkfont.nametofont("TkDefaultFont")
        texts = {column: [tr(f"overview.{column}")] for column in self._COLUMNS}
        texts["#0"] = [tr("overview.platform"), tr("overview.total")] + [row.folder for row in rows]
        texts["files"].append(_count(999999))
        for column in ("games", "marked", "problematic"):
            texts[column].append(_count(99999))
        texts["last_scan"].append("2026-11-24 13:15")
        texts["state"] += [tr(f"overview.state.{state}") for state in ("not_scanned", "current", "changed")]
        for column, values in texts.items():
            width = max(font.measure(text) for text in values) + (48 if column == "problematic" else 32)
            self.tree.column(column, width=width, minwidth=width, stretch=column == "#0")

    def selected(self) -> str | None:
        selection = self.tree.selection() if self.tree.get_children() else ()
        return selection[0] if selection and selection[0] in self.rows else None

    def _open_clicked(self, event) -> str | None:
        row = self.tree.identify_row(event.y)
        if row not in self.rows:
            return None
        self.tree.selection_set(row)
        self.open()
        return "break"

    def open(self, rescan: bool = False, full: bool = False) -> None:
        folder = self.selected()
        if folder is not None and self.window._batch is None:
            self.window.open_platform(folder, rescan=rescan, full=full)

    def set_scanning(self, scanning: bool) -> None:
        """While all platforms are scanned, only Cancel works."""
        for widget in self.buttons + [self.full_box]:
            widget.state(["disabled"] if scanning else ["!disabled"])
        if scanning:
            self.cancel_button.pack(side="right", padx=(8, 0))
        else:
            self.cancel_button.pack_forget()


def _count(value) -> str:
    return "–" if value is None else f"{value:,}".replace(",", "\u202f")


def _when(moment: str | None) -> str:
    if not moment:
        return tr("overview.never")
    return moment.replace("T", " ")[:16]


class ReviewWindow:
    def __init__(
        self, analyze, directory: Path | None, scope: str | None = None, settings_path: Path = SETTINGS_PATH,
        config_file=None, config_loader=None,
    ):
        self.settings_path = settings_path
        # The ConfigFile from rom_cleanup_workbench.py; without one, the settings are not offered.
        self.config_file = config_file
        self.settings_panel = None
        self.folder_panel = None
        self.keys_panel = None  # all keys, on F1 or ?
        self.overview_panel = None
        self._batch = None  # the running scan of all platforms: (queue, cancel flag)
        # The roms folder of the collection; None while a folder is open on its own.
        self.collection_root = None
        self.config_loader = config_loader
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
        # Open questions, the newest last: each (frame, answer variable, values, index for Esc).
        self._questions = []
        _WINDOWS[str(self.root)] = self
        self.root.bind("<Destroy>", lambda event: _WINDOWS.pop(str(self.root), None) if event.widget is self.root else None,
                       add="+")

        self._build_widgets()
        self._fit_bottom_row()
        self._show_directory()
        self.tree.focus_set()
        self._use_dark_title_bar()

    def _show_directory(self, platform: str | None = None) -> None:
        """The folder in the title row; below it "Platform: nes" while a platform's list is shown."""
        self.folder.set(tr("window.folder", directory=self.directory) if self.directory else tr("window.no_folder"))
        self.info.set(platform or "")
        if platform:
            self.platform_label.pack(side="left", padx=(0, 6), before=self.info_label)
        else:
            self.platform_label.pack_forget()
        self.root.after_idle(self._place_short_keys)

    def _clear(self) -> None:
        self.review = None
        self._files = {}
        self.tree.delete(*self.tree.get_children())
        self._hide_nothing_to_do()
        self._show_directory()

    def start_analysis(self, rescan: bool = False, full: bool = False) -> None:
        """Analyzes in the background, so that the window does not hang while reading large ZIPs.

        If an analysis is already running, it is replaced: Its result no longer counts.
        rescan (F5): a platform of a collection is read again instead of taken from its database.
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
        worker = threading.Thread(target=self._analyze_in_background, args=(self.directory, answer, rescan, full),
                                  daemon=True)
        self._workers.append(worker)
        worker.start()
        self.root.after(100, self._poll_analysis, answer)

    def _analyze_in_background(self, directory: Path, answer: queue.Queue, rescan: bool = False,
                               full: bool = False) -> None:
        def report(done: int, total: int) -> None:
            if answer is not self._analysis:
                raise _AnalysisReplaced  # Stops the replaced analysis at the next game.
            # Only remember it: Only the main thread may touch Tk, _poll_analysis shows the state.
            self._progress = (done, total)

        try:
            answer.put((_call_analyze(self.analyze, directory, report, rescan, full), None))
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
        review.confirm_save_files(review.confirmed_saves(self.settings_path))
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
        self._show_directory(self.directory.name if self.directory else None)
        self._show_all_groups()
        self._select_first_file()

    def _may_discard_changes(self, question: str) -> bool:
        if self.review is None or not self.review.moved_count():
            return True
        return messagebox.askyesno(tr("window.discard_title"), question, default="no", parent=self.root)

    def reanalyze(self) -> None:
        if self._overview_keys_work():  # r and F5 in the overview scan the highlighted platform
            self.overview_panel.open(rescan=True, full=self.overview_panel.full.get())
        elif not self._list_locked() and self._may_discard_changes(tr("window.discard_reanalyze")):
            self.start_analysis(rescan=True)

    def show_credits(self) -> None:
        """c: who had the idea and who programmed it, the license and the warning, in the window."""
        if not self._questions:  # not on top of an open question
            message = tr("credits.text") + "\n\n" + tr("credits.license")
            messagebox.showinfo(tr("credits.title"), message, parent=self.root)

    def choose_directory(self) -> None:
        """Folder... and f choose the folder in place of the list; the analysis starts once it is chosen."""
        if self.overview_panel is not None and not self._questions and self.folder_panel is None:
            self.close_overview()
        elif self._list_locked() or not self._may_discard_changes(tr("window.discard_folder")):
            return
        panel = self.folder_panel = FolderPanel(self, self.directory)
        self._show_panel(panel.frame)
        panel.tree.focus_set()

    def folder_chosen(self, folder: Path) -> None:
        self.close_folder_panel()
        self.open_folder(folder)

    def open_folder(self, folder: Path) -> None:
        """A roms folder opens its overview; any other folder is analyzed on its own, as before."""
        from workbench_db import is_collection

        if self.config_loader is not None and is_collection(folder):
            self.collection_root = folder
            save_last_collection(self.settings_path, folder)
            self.show_overview()
        else:
            self.collection_root = None
            self.directory = folder
            self._refresh_overview_button()
            self.start_analysis()

    # The overview -----------------------------------------------------------------------------

    def show_overview(self) -> None:
        """The platforms of the collection in place of the list; the numbers come from the database."""
        from workbench_db import overview

        if self.collection_root is None or self._questions:
            return
        if self.review is not None and not self._may_discard_changes(tr("window.discard_folder")):
            return
        self._analysis = None  # a running analysis no longer counts
        self.progress_bar.place_forget()
        self._clear()
        self.directory = self.collection_root
        self._show_directory()
        try:
            rows = overview(self.collection_root, self.config_loader())
        except (OSError, ValueError) as error:
            messagebox.showerror(tr("window.analysis_failed_title"), str(error), parent=self.root)
            return
        self.close_keys()
        self.close_overview()
        panel = self.overview_panel = OverviewPanel(self, rows)
        self._show_short_keys()
        self._show_panel(panel.frame)
        self._refresh_overview_button()
        panel.tree.focus_set()

    def close_overview(self) -> None:
        if self.overview_panel is None:
            return
        self.close_keys()
        self.overview_panel.frame.destroy()
        self.overview_panel = None
        self._show_short_keys()
        self._hide_panel()

    def scan_all(self) -> None:
        """Scans every platform in the background; each is saved at once; nothing is deleted."""
        from workbench_db import ScanCancelled, scan_all

        panel = self.overview_panel
        if panel is None or self._batch is not None:
            return
        answer, cancel, state = queue.Queue(), threading.Event(), {"rows": queue.Queue()}
        self._batch = (answer, cancel)
        full = panel.full.get()
        root = self.collection_root
        try:
            config = self.config_loader()
        except (OSError, ValueError) as error:
            self._batch = None
            messagebox.showerror(tr("window.analysis_failed_title"), str(error), parent=self.root)
            return

        def report(platform, number, count, done, total):
            if cancel.is_set():
                raise ScanCancelled
            state["now"] = (platform, number, count, done, total)

        def work():
            try:
                answer.put(("done", scan_all(root, full=full, progress=report, config=config,
                                             finished_row=state["rows"].put)))
            except ScanCancelled:
                answer.put(("cancelled", None))
            except Exception as error:  # every error must reach the window
                answer.put(("error", str(error) or type(error).__name__))

        panel.set_scanning(True)
        self.progress_bar.configure(value=0, maximum=1)
        self.progress_bar.place(in_=panel.tree, relx=0.5, rely=0.5, relwidth=0.6, anchor="center")
        self.progress_bar.lift()
        gc.disable()  # as for the analysis: Tk objects must not be collected in the worker thread
        worker = threading.Thread(target=work, daemon=True)
        self._workers.append(worker)
        worker.start()
        self.root.after(100, self._poll_scan_all, answer, state)

    def cancel_scan_all(self) -> None:
        if self._batch is not None:
            self._batch[1].set()

    def _poll_scan_all(self, answer: queue.Queue, state: dict) -> None:
        if self._batch is None or self._batch[0] is not answer:
            return
        while not state["rows"].empty():  # each finished platform at once
            row = state["rows"].get_nowait()
            if self.overview_panel is not None:
                self.overview_panel.set_row(row)
        try:
            outcome, value = answer.get_nowait()
        except queue.Empty:
            if "now" in state:
                platform, number, count, done, total = state["now"]
                self.status.set(tr("overview.scanning", platform=platform, done=done, total=total,
                                   number=number, count=count))
                self.progress_bar.configure(value=done, maximum=max(total, 1))
            self.root.after(100, self._poll_scan_all, answer, state)
            return
        self._batch = None
        self.progress_bar.place_forget()
        self._enable_gc_when_idle()
        self.show_overview()
        if outcome == "error":
            messagebox.showerror(tr("window.analysis_failed_title"), value, parent=self.root)
        elif outcome == "cancelled":
            self.status.set(tr("overview.scan_cancelled"))
        else:
            self.status.set(tr("overview.scan_finished", count=len(value)))

    def open_platform(self, folder: str, rescan: bool = False, full: bool = False) -> None:
        self.close_overview()
        self.directory = self.collection_root / folder
        self._refresh_overview_button()
        self.start_analysis(rescan=rescan, full=full)

    def _refresh_overview_button(self) -> None:
        if self.collection_root is not None and self.overview_panel is None:
            if not self.overview_button.winfo_ismapped():
                neighbour = self.settings_button if self.settings_button.winfo_manager() else self.folder_button
                self.overview_button.pack(side="right", padx=(0, 8), before=neighbour)
        else:
            self.overview_button.pack_forget()

    def close_folder_panel(self) -> None:
        if self.folder_panel is None:
            return
        self.folder_panel.frame.destroy()
        self.folder_panel = None
        self._hide_panel()
        if self.review is None and self._analysis is None and self.collection_root is not None:
            self.show_overview()  # Cancel from the overview goes back to it

    def _show_panel(self, frame) -> None:
        """Puts the settings or the folder choice in place of the list and locks everything that acts on it."""
        self._hide_nothing_to_do()
        self.list_frame.pack_forget()
        frame.pack(fill="both", expand=True)
        self._refresh_locks()
        self._grow_to_fit()

    def _grow_to_fit(self) -> None:
        """A low window grows until every field of a panel fits; closing the panel restores the old minimum."""
        self.root.update_idletasks()
        width, height = self.root.minsize()
        self.root.minsize(width, max(height, min(self.root.winfo_reqheight(), self.root.winfo_screenheight())))

    def _hide_panel(self) -> None:
        """Brings the file list back, as it was."""
        self.list_frame.pack(fill="both", expand=True)
        self._refresh_locks()
        self._fit_bottom_row()  # Back to the usual minimum size.
        if self.review is not None and self._analysis is None:
            self._show_all_groups()  # Also brings back "Nothing to do." if it applies.
        self.tree.focus_set()

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
        if self.overview_panel is not None:
            self.overview_panel._fit_columns(self.overview_panel.rows.values())

    def _fit_radio_indicator(self) -> None:
        """The circle grows with the font, so that the red dot stays easy to see."""
        size = max(12, round(tkfont.nametofont("TkDefaultFont").metrics("linespace") * 0.8))
        for name in ("TRadiobutton", _DOT_STYLE):
            ttk.Style(self.root).configure(name, indicatorsize=size, indicatormargin=(0, 0, 8, 0))

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
        style.map("TButton", background=[("active", _GRAY)], foreground=[("disabled", _LIGHT_GRAY)])
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
            foreground=[("disabled", _LIGHT_GRAY)],
            indicatorbackground=[("active", _GRAY)],
            indicatorforeground=[("disabled", _LIGHT_GRAY)],
        )
        # Switches such as Deep Scan: the circle with the red dot of the views, not a check box.
        style.layout(_DOT_STYLE, style.layout("TRadiobutton"))
        style.configure(_DOT_STYLE, **style.configure("TRadiobutton"))
        style.map(_DOT_STYLE, **style.map("TRadiobutton"))
        self._fit_radio_indicator()
        style.configure(_HIGHLIGHT_STYLE, background=_GREEN, foreground=_WHITE)
        style.configure(_HIGHLIGHT_FRAME_STYLE, background=_GREEN)
        style.configure(
            "TEntry", fieldbackground=_DARK_GRAY, foreground=_WHITE, insertcolor=_WHITE,
            bordercolor=_GRAY, selectbackground=_SELECTED, selectforeground=_WHITE,
        )
        style.configure(
            "TCombobox", fieldbackground=_DARK_GRAY, background=_DARK_GRAY, foreground=_WHITE,
            arrowcolor=_WHITE, bordercolor=_GRAY,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", _DARK_GRAY)], foreground=[("readonly", _WHITE)],
            selectbackground=[("readonly", _DARK_GRAY)], selectforeground=[("readonly", _WHITE)],
        )
        # The open list of a combobox is a plain Tk listbox; it only takes colors from the option database.
        for option, color in (("background", _DARK_GRAY), ("foreground", _WHITE),
                              ("selectBackground", _SELECTED), ("selectForeground", _WHITE)):
            self.root.option_add(f"*TCombobox*Listbox.{option}", color)
        style.configure("Horizontal.TProgressbar", background=_GREEN, troughcolor=_DARK_GRAY, bordercolor=_GRAY, thickness=24)
        style.configure("Vertical.TScrollbar", background=_GRAY, troughcolor=_BLACK, arrowcolor=_WHITE, bordercolor=_BLACK)
        style.map("Vertical.TScrollbar", background=[("active", _LIGHT_GRAY)])

    def _use_dark_title_bar(self, toplevel=None) -> None:
        """Switches the Windows title bar to dark; if it stays light, no harm is done."""
        toplevel = toplevel or self.root
        try:
            toplevel.update_idletasks()
            handle = ctypes.windll.user32.GetParent(toplevel.winfo_id())
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

        info_row = self.info_row = ttk.Frame(self.root, padding=8)
        info_row.pack(fill="x")
        info_row.columnconfigure(1, weight=1)
        platform_part = self.platform_part = ttk.Frame(info_row)
        platform_part.grid(row=0, column=0, sticky="w")
        self.short_keys = ttk.Frame(info_row)
        self.short_keys.grid(row=0, column=1, sticky="e")
        info_row.bind("<Configure>", lambda _event: self._place_short_keys())
        self.platform_label = ttk.Label(platform_part, text=tr("window.platform"), foreground=_KEEP_TEXT,
                                        font=self.bold_font)
        self.info_label = ttk.Label(platform_part, textvariable=self.info)
        self.info_label.pack(side="left")
        self._show_short_keys()

        # The status has a row of its own, so that it does not push out the buttons.
        bottom = ttk.Frame(self.root, padding=8)
        bottom.pack(side="bottom", fill="x")
        self.status_label = ttk.Label(self.root, textvariable=self.status, style=_HIGHLIGHT_STYLE, padding=8)
        self.status_label.pack(side="bottom", fill="x")
        self.status_label.bind("<Configure>", lambda event: self.status_label.configure(wraplength=event.width - 16))
        self.close_button = ttk.Button(bottom, text=tr("window.button.close"), command=self.close)
        self.close_button.pack(side="right")
        # "Proceed": Besides deleting, the button also confirms the suspected save files.
        proceed = ttk.Button(bottom, text=tr("window.button.proceed"), command=self.confirm_delete)
        proceed.pack(side="right", padx=8)
        reanalyze = ttk.Button(bottom, text=tr("window.button.reanalyze"), command=self.reanalyze)
        reanalyze.pack(side="right")
        folder = self.folder_button = ttk.Button(bottom, text=tr("window.button.folder"), command=self.choose_directory)
        folder.pack(side="right", padx=8)
        self.overview_button = ttk.Button(bottom, text=tr("window.button.overview"), command=self.show_overview)
        self.settings_button = ttk.Button(bottom, text=tr("window.button.settings"), command=self.toggle_settings)
        if self.config_file is not None:
            self.settings_button.pack(side="right")
        ttk.Label(bottom, text=tr("window.filter")).pack(side="left", padx=(0, 8))
        self.search_entry = ttk.Entry(bottom, textvariable=self.search, width=_FILTER_MIN_CHARS)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self._bind_search_entry()
        self.bottom_row = bottom
        # Everything that acts on the file list; locked while the settings take its place.
        self._list_controls = [proceed, reanalyze, folder, self.search_entry]

        # Above the green row, so that it stays the second-to-last row of the window.
        options = ttk.Frame(self.root, padding=(8, 8, 8, 0))
        options.pack(side="bottom", fill="x")
        for value, label in _SCOPES:
            button = ttk.Radiobutton(
                options, text=tr(label), value=value, variable=self.scope, command=self._scope_changed,
            )
            button.pack(side="left", padx=(0, 16))
            self._list_controls.append(button)

        middle = self.middle = ttk.Frame(self.root)
        middle.pack(fill="both", expand=True)
        # The list and its scrollbar, hidden together while the settings are open.
        self.list_frame = ttk.Frame(middle)
        self.list_frame.pack(fill="both", expand=True)
        # "hint" stays the first value of every row; only the display puts the size before it.
        self.tree = ttk.Treeview(
            self.list_frame, columns=("hint", "size"), displaycolumns=("size", "hint"), selectmode="extended",
        )
        self.tree.heading("#0", text=tr("window.column.file"), anchor="w")
        self.tree.heading("size", text=tr("window.column.size") + _CELL_GAP, anchor="e")
        self.tree.heading("hint", text=tr("window.column.note"), anchor="w")
        self.tree.column("#0", width=560, stretch=True)
        self.tree.column("size", anchor="e", stretch=False)
        self.tree.column("hint", width=500, stretch=True)
        self._fit_size_column()
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview)
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
        self.tree.tag_configure("keep", font=self.bold_font, foreground=_KEEP_TEXT)
        self.tree.tag_configure("marked", foreground=_MARKED_TEXT)
        self.tree.tag_configure("separator", foreground=_LINE_COLOR)

        # On the window instead of the list, so that the keys also work after clicking a radio button.
        # The keys of the terminal version (2026-11-23): x delete, k keep, Enter execute, s settings,
        # f folder, r analyze again, c credits, / filter, 1-3 views, q quit; D, P and the Ctrl keys are gone.
        # Fields where text is typed leave the window's bindtag out, so a letter typed there stays text.
        keys = {
            "x": self.demote_selected, "k": self.promote_selected, "s": self.toggle_settings,
            "f": self.choose_directory, "r": self.reanalyze, "c": self.show_credits, "q": self._quit_key,
            "a": self._scan_all_key, "d": self._toggle_full_key, "h": self._hide_empty_key,
        }
        for key, action in keys.items():
            for variant in (key, key.upper()):
                self.root.bind(f"<KeyPress-{variant}>", lambda _event, action=action: action())
        for number in range(len(_SCOPES)):
            self.root.bind(f"<KeyPress-{number + 1}>", lambda _event, number=number: self._choose_scope(number))
        self.root.bind("<Return>", lambda _event: self.confirm_delete())
        self.root.bind("<KP_Enter>", lambda _event: self.confirm_delete())
        self.root.bind("<slash>", lambda _event: self.focus_search())
        self.root.bind("<KP_Divide>", lambda _event: self.focus_search())
        self.root.bind("<F5>", lambda _event: self.reanalyze())
        self.root.bind("<F1>", lambda _event: self.toggle_keys())
        self.root.bind("<question>", lambda _event: self.toggle_keys())
        # As in the terminal version, Ctrl+E only closes the settings.
        self.root.bind("<Control-e>", lambda _event: self._close_settings_key())
        self.root.bind("<Control-E>", lambda _event: self._close_settings_key())
        # "break" prevents Tab from passing the focus to the next button as usual.
        self.root.bind("<Tab>", lambda _event: self._move_game(1))
        self.root.bind("<Shift-Tab>", lambda _event: self._move_game(-1))
        # With the settings open, Esc only returns to the list.
        self.root.bind("<Escape>", lambda _event: self._on_escape())
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
        # Without the window's bindtag, typing an "x" or "k" here cannot change a deletion mark.
        entry = self.search_entry
        entry.bindtags((str(entry), entry.winfo_class(), "all"))
        self.search.trace_add("write", lambda *_args: self._search_changed())
        entry.bind("<Return>", lambda _event: self.leave_search())
        entry.bind("<Tab>", lambda _event: self.leave_search())
        entry.bind("<Shift-Tab>", lambda _event: self.leave_search())
        entry.bind("<Down>", lambda _event: self.leave_search())
        entry.bind("<Escape>", lambda _event: self.leave_search(clear=True))
        entry.bind("<Control-MouseWheel>", self._on_zoom)

    def _choose_scope(self, number: int) -> None:
        """1, 2 and 3 choose a view, like a click on its option."""
        if self._list_locked():
            return
        value = _SCOPES[number][0]
        if self.scope.get() != value:
            self.scope.set(value)
            self._scope_changed()

    def _quit_key(self) -> None:
        """q goes one step back like Esc, but not while the settings, the folder choice or a question is open."""
        if not self._list_locked() or self._overview_keys_work():
            self._on_escape()

    def _overview_keys_work(self) -> bool:
        """The overview is shown and nothing lies on top of it."""
        return (self.overview_panel is not None and self.settings_panel is None and self.folder_panel is None
                and self.keys_panel is None and not self._questions)

    # The keys ---------------------------------------------------------------------------------

    def _show_short_keys(self) -> None:
        """The few keys of the current view, right of "Platform: nes"; F1 or ? shows all."""
        from workbench_keys import LIST, OVERVIEW, short_keys

        for child in self.short_keys.winfo_children():
            child.destroy()
        context = OVERVIEW if self.overview_panel is not None else LIST
        for index, (key, text) in enumerate(short_keys(context)):
            ttk.Label(self.short_keys, text=key, font=self.bold_font, foreground=_KEEP_TEXT).pack(
                side="left", padx=(0 if index == 0 else 24, 6))
            ttk.Label(self.short_keys, text=text).pack(side="left")
        self.root.after_idle(self._place_short_keys)

    def _place_short_keys(self) -> None:
        """Beside "Platform: nes" if both fit, else in a line of their own below it."""
        width = self.info_row.winfo_width() - 16
        needed = self.platform_part.winfo_reqwidth() + 24 + self.short_keys.winfo_reqwidth()
        place = (0, 1) if needed <= width else (1, 0)
        if (int(self.short_keys.grid_info().get("row", -1)), int(self.short_keys.grid_info().get("column", -1))) != place:
            self.short_keys.grid(row=place[0], column=place[1], columnspan=2 if place[1] == 0 else 1, sticky="e")

    def toggle_keys(self) -> str:
        """F1 and ? show all keys of the current view in place of the list, and a second time close them."""
        if self.keys_panel is not None:
            self.close_keys()
        elif not self._questions and self.settings_panel is None and self.folder_panel is None:
            self.open_keys()
        return "break"

    def open_keys(self) -> None:
        from workbench_keys import LIST, OVERVIEW

        if self.keys_panel is not None:
            return
        context = OVERVIEW if self.overview_panel is not None else LIST
        panel = self.keys_panel = KeysPanel(self, context)
        if self.overview_panel is not None:
            self.overview_panel.frame.pack_forget()  # comes back when the keys close
            panel.frame.pack(fill="both", expand=True)
            self._refresh_locks()
            self._grow_to_fit()
        else:
            self._show_panel(panel.frame)

    def close_keys(self) -> None:
        if self.keys_panel is None:
            return
        self.keys_panel.frame.destroy()
        self.keys_panel = None
        if self.overview_panel is not None:
            self.overview_panel.frame.pack(fill="both", expand=True)
            self._refresh_locks()
            self._fit_bottom_row()
            self.overview_panel.tree.focus_set()
        else:
            self._hide_panel()

    def _scan_all_key(self) -> None:
        if self._overview_keys_work():
            self.scan_all()

    def _hide_empty_key(self) -> None:
        if self._overview_keys_work():
            self.overview_panel.toggle_hide_empty()

    def _toggle_full_key(self) -> None:
        if self._overview_keys_work() and self._batch is None:
            self.overview_panel.full.set(not self.overview_panel.full.get())

    def _close_settings_key(self) -> None:
        if self.settings_panel is not None and not self._questions:
            self.close_settings()

    def focus_search(self) -> str | None:
        if self._list_locked():
            return None
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
        # Rows hidden by the search leave the selection; x and k should work on what is shown.
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
        # Also when an analysis ends during typing: In the list, the next letter could be an x or k.
        if self.root.focus_get() is not self.search_entry and not self._list_locked():
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
        self.tree.item(group_id, text=result.title)  # k and x may change the first kept file
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

    def _move_game(self, step: int) -> str | None:
        """Jumps to the neighboring game and selects its first file, so that x and k work at once."""
        if self._list_locked():
            return None  # Tab moves between the fields of the settings as usual.
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
        # With the settings open, the list is hidden: x and k must not change what cannot be seen.
        if self.review is None or self._list_locked():
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
        if self.review is None or self._list_locked():
            return
        if not self.review.has_work():
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
            messagebox.showinfo(tr("window.deleted_title"), self.review.done_message(deleted), parent=self.root)
        # The Review object has dropped the deleted files; the folder is not analyzed again.
        self.show_review(self.review)

    def toggle_settings(self) -> str:
        """Settings... and s open the settings in place of the list, and a second time close them."""
        if self._questions or self.folder_panel is not None:
            pass  # A question or the folder choice is open: it must be finished first.
        elif self.settings_panel is not None:
            self.close_settings()
        else:
            self.open_settings()
        return "break"

    def open_settings(self) -> None:
        if self.config_file is None or self.settings_panel is not None or self.overview_panel is not None:
            return  # in the overview there are no settings, as in the terminal version
        try:
            panel = SettingsPanel(self)
        except ValueError as error:
            # A broken file is not overwritten: It may contain entries the settings do not know.
            messagebox.showerror(tr("settings.error_title"), str(error), parent=self.root)
            return
        self.settings_panel = panel
        self._show_panel(panel.frame)

    def close_settings(self) -> None:
        """Brings the file list back, as it was."""
        if self.settings_panel is None:
            return
        self.settings_panel.frame.destroy()
        self.settings_panel = None
        self._hide_panel()

    def settings_platform(self) -> tuple[Path | None, str | None]:
        """(roms folder, platform) while a platform of a collection is open; else (None, None)."""
        root, directory = self.collection_root, self.directory
        if root is not None and directory is not None and directory != root and directory.parent == root:
            return root, directory.name
        return None, None

    def save_settings(self, panel: SettingsPanel) -> None:
        """Writes the settings; new rules (priority, tags, ZIP or plain) take effect at once through a new analysis."""
        from workbench_db import save_settings_for

        language, regions, tags = panel.language_code(), panel.region_list(), panel.tag_list()
        prefer_zip = panel.prefers_zip()
        own = panel.own.get()
        before = panel.values
        rules_changed = (regions != before["region_priority"] or tags != before["delete_tags"]
                         or prefer_zip != before["prefer_zip"] or own != panel.own_before)
        if rules_changed and not self._may_discard_changes(tr("settings.discard")):
            return
        try:
            save_settings_for(self.config_file, panel.root_folder, panel.platform, own, language, regions, tags,
                              prefer_zip)
        except (OSError, ValueError) as error:
            messagebox.showerror(tr("settings.error_title"), str(error), parent=self.root)
            return
        self.close_settings()
        if language != before["language"]:
            messagebox.showinfo(tr("settings.restart_title"), tr("settings.language_hint"), parent=self.root)
        if rules_changed:
            self.start_analysis()

    def _confirm_save_files_only(self) -> None:
        """Without marked files, Enter can still confirm the suspected status or save files."""
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
            self.review.remember_save_files(self.settings_path, save_files)
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
        if self._questions:
            self._answer(self._questions[-1][3])  # The X of the window answers an open question like Esc.
            return
        if self._may_discard_changes(tr("window.discard_close")):
            self.root.destroy()

    def ask(self, kind: str, title: str, message: str, buttons, default) -> object:
        """Shows a question or message in place of the list and waits for the answer.

        buttons: (text key, value) pairs. Enter chooses default, Esc the last button. Meanwhile the list
        and its commands are locked, so that nothing changes behind the question.
        """
        colors = {"warning": _RED, "error": _RED, "question": _GREEN, "info": _GREEN}
        frame = ttk.Frame(self.middle, padding=32)
        frame.columnconfigure(1, weight=1)
        dot = tk.Canvas(frame, width=22, height=22, background=_BLACK, highlightthickness=0)
        dot.create_oval(2, 2, 20, 20, fill=colors.get(kind, _GREEN), outline="")
        dot.grid(row=0, column=0, sticky="nw", padx=(0, 12), pady=(4, 0))
        ttk.Label(frame, text=title, font=self.bold_font).grid(row=0, column=1, sticky="w")
        body = ttk.Label(frame, text=message, justify="left")
        body.grid(row=1, column=1, sticky="ew", pady=(12, 24))
        frame.bind("<Configure>", lambda event: body.configure(wraplength=max(event.width - 120, 200)))
        row = ttk.Frame(frame)
        row.grid(row=2, column=1, sticky="w")
        answer = tk.IntVar(self.root, -1)
        values = [value for _key, value in buttons]
        widgets = []
        for index, (key, _value) in enumerate(buttons):
            button = ttk.Button(row, text=tr(key), command=lambda index=index: answer.set(index))
            button.pack(side="left", padx=(0, 8))
            # "break": Enter answers the question and must not also reach the window's Enter (execute).
            button.bind("<Return>", lambda _event, index=index: answer.set(index) or "break")
            widgets.append(button)
        default_index = values.index(default) if default in values else 0
        self._questions.append((frame, answer, values, len(values) - 1))
        frame.place(in_=self.middle, relx=0, rely=0, relwidth=1, relheight=1)
        frame.lift()
        self._refresh_locks()
        widgets[default_index].focus_set()
        try:
            self.root.wait_variable(answer)
            chosen = answer.get()
        except tk.TclError:  # The window was destroyed meanwhile.
            return values[-1]
        self._questions.pop()
        frame.destroy()
        self._refresh_locks()
        if not self._questions:
            self._focus_after_question()
        return values[chosen] if 0 <= chosen < len(values) else values[-1]

    def _answer(self, index: int) -> None:
        if self._questions:
            self._questions[-1][1].set(index)

    def _focus_after_question(self) -> None:
        if self.folder_panel is not None:
            self.folder_panel.tree.focus_set()
        elif self.settings_panel is not None:
            self.settings_panel.frame.focus_set()
        else:
            self.tree.focus_set()

    def _on_escape(self) -> None:
        if self._questions:
            self._answer(self._questions[-1][3])
        elif self.keys_panel is not None:
            self.close_keys()
        elif self.folder_panel is not None:
            self.close_folder_panel()
        elif self.settings_panel is not None:
            self.close_settings()
        elif self.collection_root is not None and self.overview_panel is None:
            self.show_overview()  # a platform of a collection: back to the overview; Esc there closes
        else:
            self.close()

    def _list_locked(self) -> bool:
        """The list is hidden behind the settings, the folder choice or a question: nothing may change it."""
        return (self.settings_panel is not None or self.folder_panel is not None or self.overview_panel is not None
                or self.keys_panel is not None or bool(self._questions))

    def _refresh_locks(self) -> None:
        locked = self._list_locked()
        for widget in self._list_controls:
            widget.state(["disabled"] if locked else ["!disabled"])
        self.settings_button.state(["disabled"] if self._questions or self.folder_panel or self.overview_panel
                                   else ["!disabled"])
        self.folder_button.state(["disabled"] if self._questions or self.folder_panel or self.settings_panel
                                 else ["!disabled"])
        self.close_button.state(["disabled"] if self._questions else ["!disabled"])

    def run(self) -> int:
        directory = self.directory
        if directory is None and self.config_loader is not None:
            directory = load_last_collection(self.settings_path)
        if directory is None:
            self.status.set(tr("window.choose_folder_status"))
            self.root.after(100, self.choose_directory)
        else:
            self.open_folder(directory)
        self.root.mainloop()
        return 1 if self.had_errors else 0


def run_window(analyze, directory: Path | None, scope: str | None = None, config_file=None,
               config_loader=None) -> int:
    """Shows the window and returns the program's exit code."""
    return ReviewWindow(analyze, directory, scope, config_file=config_file, config_loader=config_loader).run()
