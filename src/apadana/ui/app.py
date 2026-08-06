from __future__ import annotations

import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk

from .. import apt_backend
from . import theme
from .controller import Callbacks, OperationController
from .dialogs import ask_sudo_password
from .discover_view import DiscoverView
from .installed_view import InstalledView
from .sources_view import SourcesView

NAV_ITEMS = [
    ("discover", "Discover"),
    ("installed", "Installed"),
    ("sources", "Sources"),
]


class ApadanaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Apadana")
        self.geometry("1080x720")
        self.minsize(860, 560)
        self._set_icon()

        self.style = theme.apply_theme(self)

        self.cached_sudo_password = None
        self.installed_data = {}
        self.log_visible = False

        self._build_layout()

        self.controller = OperationController(
            self,
            Callbacks(
                log=self.log,
                set_status=self.set_status,
                set_busy=self.set_busy,
                ask_password=lambda: ask_sudo_password(self),
            ),
        )

        self.views = {
            "discover": DiscoverView(self.content_area, self),
            "installed": InstalledView(self.content_area, self),
            "sources": SourcesView(self.content_area, self),
        }
        for view in self.views.values():
            view.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.show_view("discover")

        self.after(150, self.refresh_installed)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # -- window chrome -------------------------------------------------------
    def _set_icon(self):
        try:
            base = sys._MEIPASS if getattr(sys, "frozen", False) else "."
            icon_path = os.path.join(base, "src", "logo.png")
            if os.path.isfile(icon_path):
                self.iconphoto(False, tk.PhotoImage(file=icon_path))
        except Exception:
            pass  # icon is cosmetic; never block startup on it

    def _build_layout(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # -- sidebar --
        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=200)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        brand = ttk.Frame(sidebar, style="Sidebar.TFrame", padding=(18, 22, 18, 18))
        brand.pack(fill="x")
        ttk.Label(brand, text="Apadana", style="SidebarTitle.TLabel").pack(anchor="w")
        ttk.Label(brand, text="Software Center", style="SidebarSubtitle.TLabel").pack(anchor="w")

        self.nav_buttons: dict[str, ttk.Button] = {}
        nav_frame = ttk.Frame(sidebar, style="Sidebar.TFrame", padding=(8, 8))
        nav_frame.pack(fill="x")
        for key, label in NAV_ITEMS:
            btn = ttk.Button(
                nav_frame,
                text=label,
                style="Sidebar.TButton",
                command=lambda k=key: self.show_view(k),
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[key] = btn

        # -- main column: content + details + status/log --
        main = ttk.Frame(self)
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)

        self.content_area = ttk.Frame(main)
        self.content_area.grid(row=0, column=0, sticky="nsew")

        details_frame = ttk.Frame(main, padding=(20, 0, 20, 8))
        details_frame.grid(row=1, column=0, sticky="ew")
        self.details_var = tk.StringVar(value="Select a package to see its description here.")
        ttk.Label(
            details_frame,
            textvariable=self.details_var,
            wraplength=820,
            justify="left",
            foreground=theme.INK_MUTED,
        ).pack(fill="x")

        status_frame = ttk.Frame(main, style="Status.TFrame", padding=(16, 8))
        status_frame.grid(row=2, column=0, sticky="ew")
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel").pack(side="left")
        self.progress = ttk.Progressbar(
            status_frame, mode="indeterminate", length=160, style="Status.Horizontal.TProgressbar"
        )
        self.progress.pack(side="left", padx=10)
        self.cancel_btn = ttk.Button(
            status_frame, text="Cancel", style="Ghost.TButton", command=self._cancel, state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=6)
        self.log_toggle_btn = ttk.Button(
            status_frame, text="Show Technical Log \u25be", style="Ghost.TButton", command=self.toggle_log
        )
        self.log_toggle_btn.pack(side="right")

        self.log_frame = ttk.Frame(main)
        self.output_text = tk.Text(
            self.log_frame,
            height=10,
            wrap="word",
            bg="#111417",
            fg="#4CD97B",
            insertbackground="#4CD97B",
            font=theme.Fonts.mono,
            borderwidth=0,
        )
        self.output_text.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=(0, 10))
        log_scroll = ttk.Scrollbar(self.log_frame, command=self.output_text.yview)
        log_scroll.pack(side="right", fill="y", padx=(0, 20), pady=(0, 10))
        self.output_text.config(yscrollcommand=log_scroll.set)
        # log_frame not gridded initially — toggled on demand
        self.log_frame_row = 3
        main.rowconfigure(self.log_frame_row, weight=0)

    # -- navigation -----------------------------------------------------------
    def show_view(self, key: str):
        for k, view in self.views.items():
            if k == key:
                view.tkraise()
        for k, btn in self.nav_buttons.items():
            btn.configure(style="SidebarActive.TButton" if k == key else "Sidebar.TButton")

    def toggle_log(self):
        if self.log_visible:
            self.log_frame.grid_forget()
            self.log_toggle_btn.config(text="Show Technical Log \u25be")
        else:
            self.log_frame.grid(row=self.log_frame_row, column=0, sticky="ew")
            self.log_toggle_btn.config(text="Hide Technical Log \u25b4")
        self.log_visible = not self.log_visible

    # -- shared UI hooks used by views / controller ---------------------------
    def log(self, text: str):
        self.output_text.insert("end", text)
        self.output_text.see("end")

    def set_status(self, text: str):
        self.status_var.set(text)

    def set_details(self, text: str):
        self.details_var.set(text)

    def set_busy(self, busy: bool):
        if busy:
            self.progress.start(12)
            self.cancel_btn.config(state="normal")
        else:
            self.progress.stop()
            self.cancel_btn.config(state="disabled")

    def _cancel(self):
        self.controller.cancel_current()

    def refresh_installed(self):
        self.views["installed"].refresh()

    def on_installed_data_changed(self, data):
        self.installed_data = data

    # -- lifecycle -------------------------------------------------------------
    def on_close(self):
        self.cached_sudo_password = None
        apt_backend.drop_cached_credentials()
        self.destroy()
