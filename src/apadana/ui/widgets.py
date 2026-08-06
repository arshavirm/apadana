from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme


class ScrollableFrame(ttk.Frame):
    """A vertically scrollable area (canvas + inner frame) with mouse-wheel
    support, used for the store-style package grid."""

    def __init__(self, parent, *, background=theme.APP_BG, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, background=background, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self._window, width=e.width),
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        for widget in (self.canvas, self.inner):
            widget.bind("<Enter>", lambda e: self._bind_wheel())
            widget.bind("<Leave>", lambda e: self._unbind_wheel())

    def _bind_wheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", self._on_wheel)
        self.canvas.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event):
        if getattr(event, "num", None) == 4:
            self.canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas.yview_scroll(3, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120) * 3), "units")

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()


class Badge(tk.Label):
    """Small pill-style status label (e.g. 'Installed')."""

    def __init__(self, parent, text, *, bg=theme.ACCENT_SOFT, fg=theme.ACCENT, **kw):
        super().__init__(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            font=theme.Fonts.small,
            padx=8,
            pady=1,
            **kw,
        )


class PackageCard(ttk.Frame):
    """A single store-style listing: name, description, status badge and
    one or two action buttons."""

    def __init__(
        self,
        parent,
        *,
        name: str,
        description: str,
        installed: bool,
        on_select=None,
        on_primary=None,
        on_secondary=None,
        primary_label: str = "Install",
        secondary_label: str | None = None,
        selected: bool = False,
    ):
        super().__init__(parent, style="Card.TFrame", padding=(14, 10))
        self._on_select = on_select
        self.configure(relief="flat")

        border = tk.Frame(
            self,
            bg=theme.ACCENT if selected else theme.CARD_BORDER,
            highlightthickness=0,
        )
        border.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lower(border)

        top = ttk.Frame(self, style="Card.TFrame")
        top.pack(fill="x")

        name_label = ttk.Label(
            top, text=name, style="Card.TLabel", font=theme.Fonts.body_bold
        )
        name_label.pack(side="left")

        if installed:
            Badge(top, "Installed", bg=theme.ACCENT_SOFT, fg=theme.ACCENT_HOVER).pack(
                side="left", padx=(8, 0)
            )

        desc_label = ttk.Label(
            self,
            text=description or "No description available.",
            style="Card.TLabel",
            foreground=theme.INK_MUTED,
            wraplength=560,
            justify="left",
        )
        desc_label.pack(fill="x", pady=(4, 8), anchor="w")

        actions = ttk.Frame(self, style="Card.TFrame")
        actions.pack(fill="x")
        if on_primary is not None:
            ttk.Button(
                actions,
                text=primary_label,
                style="Accent.TButton",
                command=on_primary,
            ).pack(side="left")
        if on_secondary is not None and secondary_label:
            ttk.Button(
                actions,
                text=secondary_label,
                style="Ghost.TButton",
                command=on_secondary,
            ).pack(side="left", padx=(8, 0))

        for widget in (self, top, name_label, desc_label, actions):
            widget.bind("<Button-1>", self._handle_click)

    def _handle_click(self, _event):
        if self._on_select:
            self._on_select()


class SectionHeader(ttk.Frame):
    def __init__(self, parent, title: str, subtitle: str = ""):
        super().__init__(parent, style="Header.TFrame")
        ttk.Label(self, text=title, style="PageTitle.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(self, text=subtitle, style="PageSubtitle.TLabel").pack(
                anchor="w", pady=(2, 0)
            )
