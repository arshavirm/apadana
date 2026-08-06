from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .. import apt_operations as ops
from . import theme
from .widgets import PackageCard, ScrollableFrame, SectionHeader

MAX_RESULTS_RENDERED = 150


class DiscoverView(ttk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame", padding=20)
        self.app = app
        self.search_data: dict[str, str] = {}
        self.selected_names: set[str] = set()

        SectionHeader(
            self,
            "Discover Software",
            "Search the apt repositories your system knows about.",
        ).pack(anchor="w", fill="x")

        search_bar = ttk.Frame(self, padding=(0, 14, 0, 10))
        search_bar.pack(fill="x")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(
            search_bar,
            textvariable=self.search_var,
            style="Search.TEntry",
            font=theme.Fonts.body,
        )
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e: self.search())
        entry.insert(0, "")
        ttk.Button(
            search_bar, text="Search", style="Accent.TButton", command=self.search
        ).pack(side="left", padx=(8, 0))

        self.install_bar = ttk.Frame(self, padding=(0, 0, 0, 10))
        self.selection_label = ttk.Label(
            self.install_bar, text="", style="TLabel", foreground=theme.INK_MUTED
        )
        self.selection_label.pack(side="left")
        self.install_btn = ttk.Button(
            self.install_bar,
            text="Install Selected",
            style="Accent.TButton",
            command=self.install_selected,
        )
        self.install_btn.pack(side="right")

        self.results_area = ScrollableFrame(self)
        self.results_area.pack(fill="both", expand=True)

        self._show_placeholder(
            "Search for software",
            'Type a package name or keyword above — try "editor", "gimp", or "vlc".',
        )

    # -- rendering ----------------------------------------------------------
    def _show_placeholder(self, title, subtitle):
        self.results_area.clear()
        self.install_bar.pack_forget()
        box = ttk.Frame(self.results_area.inner, padding=40)
        box.pack(fill="x")
        ttk.Label(
            box, text=title, font=theme.Fonts.heading, foreground=theme.INK_MUTED
        ).pack()
        ttk.Label(box, text=subtitle, foreground=theme.INK_MUTED).pack(pady=(4, 0))

    def search(self):
        term = self.search_var.get().strip()
        if not term:
            messagebox.showinfo("Search", "Type something to search for first.")
            return
        self.app.set_status(f"Searching for '{term}'...")
        self.app.set_busy(True)
        threading.Thread(target=self._search_worker, args=(term,), daemon=True).start()

    def _search_worker(self, term):
        try:
            import subprocess

            result = subprocess.run(
                ops.cmd_search(term), capture_output=True, text=True, timeout=30
            )
            self.search_data = ops.parse_search_results(result.stdout)
            self.after(0, self._populate_results)
        except Exception as e:
            self.app.log(f"Error searching packages: {e}\n")
        finally:
            self.after(0, lambda: self.app.set_busy(False))
            self.after(0, lambda: self.app.set_status("Ready."))

    def _populate_results(self):
        self.selected_names.clear()
        self._render_results()

    def _toggle_selection(self, name):
        if name in self.selected_names:
            self.selected_names.discard(name)
        else:
            self.selected_names.add(name)
        self._render_results()

    def _render_results(self):
        self.results_area.clear()

        if not self.search_data:
            self._show_placeholder("No results", "Try a different search term.")
            return

        self.install_bar.pack(fill="x", before=self.results_area)
        self._update_selection_label()

        all_names = sorted(self.search_data)
        total = len(all_names)
        shown_names = all_names[:MAX_RESULTS_RENDERED]

        if total > MAX_RESULTS_RENDERED:
            ttk.Label(
                self.results_area.inner,
                text=(
                    f"Showing the first {MAX_RESULTS_RENDERED} of {total} matches — "
                    "use a more specific search term to see the rest."
                ),
                foreground=theme.GOLD,
                font=theme.Fonts.small,
                padding=(2, 0, 2, 8),
                wraplength=760,
                justify="left",
            ).pack(anchor="w")

        installed = self.app.installed_data
        for name in shown_names:
            desc = self.search_data[name]
            is_installed = name in installed
            selected = name in self.selected_names
            card = PackageCard(
                self.results_area.inner,
                name=name,
                description=desc,
                installed=is_installed,
                primary_label=("Selected \u2713" if selected else "Select to Install"),
                on_select=lambda n=name: self._toggle_selection(n),
                on_primary=(
                    None if is_installed else (lambda n=name: self._toggle_selection(n))
                ),
                on_secondary=None,
                selected=selected,
            )
            card.pack(fill="x", pady=(0, 8), padx=1)

    def _update_selection_label(self):
        n = len(self.selected_names)
        self.selection_label.config(
            text=f"{n} package(s) selected" if n else "Click a result to select it"
        )
        self.install_btn.config(state="normal" if n else "disabled")

    # -- actions -------------------------------------------------------------
    def install_selected(self):
        names = sorted(self.selected_names)
        if not names:
            messagebox.showinfo(
                "No selection",
                "Select one or more packages from the search results first.",
            )
            return
        if not messagebox.askyesno(
            "Confirm installation",
            "Install the following package(s)?\n\n" + "\n".join(names),
        ):
            return

        def after_install():
            self.selected_names.clear()
            self.app.refresh_installed()
            self._render_results()

        self.app.controller.run(
            ops.cmd_install(names),
            needs_root=True,
            description="Installing package(s)",
            on_done=after_install,
        )
