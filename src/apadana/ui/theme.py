from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# --- Palette ---------------------------------------------------------------
INK = "#1F2430"  # primary text
INK_MUTED = "#6B7280"  # secondary text
SIDEBAR_BG = "#1B2A4A"  # deep indigo
SIDEBAR_BG_HOVER = "#243759"
SIDEBAR_TEXT = "#D8DEEC"
SIDEBAR_TEXT_ACTIVE = "#FFFFFF"
ACCENT = "#2E9CA6"  # Persian turquoise
ACCENT_HOVER = "#257F87"
ACCENT_SOFT = "#DCF1F1"
GOLD = "#C99A3B"  # muted gold, used sparingly for "installed" badges
DANGER = "#B5453F"
DANGER_HOVER = "#93382F"
APP_BG = "#F1EEE6"  # warm stone background
CARD_BG = "#FFFFFF"
CARD_BORDER = "#E3DFD3"
CARD_BORDER_HOVER = "#C9C2AE"


def pick_font_family(root: tk.Misc) -> str:
    available = set(tkfont.families(root))
    for candidate in ("Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", "Segoe UI"):
        if candidate in available:
            return candidate
    return "TkDefaultFont"


class Fonts:
    """Populated once a Tk root exists via :func:`apply_theme`."""

    family = "TkDefaultFont"
    display: tuple = ("TkDefaultFont", 20, "bold")
    heading: tuple = ("TkDefaultFont", 12, "bold")
    body: tuple = ("TkDefaultFont", 10)
    body_bold: tuple = ("TkDefaultFont", 10, "bold")
    small: tuple = ("TkDefaultFont", 9)
    small_muted: tuple = ("TkDefaultFont", 9)
    mono: tuple = ("Consolas", 9)


def apply_theme(root: tk.Tk) -> ttk.Style:
    family = pick_font_family(root)
    Fonts.family = family
    Fonts.display = (family, 20, "bold")
    Fonts.heading = (family, 12, "bold")
    Fonts.body = (family, 10)
    Fonts.body_bold = (family, 10, "bold")
    Fonts.small = (family, 9)
    Fonts.small_muted = (family, 9)

    root.configure(bg=APP_BG)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=APP_BG, foreground=INK, font=Fonts.body)
    style.configure("TFrame", background=APP_BG)
    style.configure("TLabel", background=APP_BG, foreground=INK, font=Fonts.body)

    style.configure("Card.TFrame", background=CARD_BG)
    style.configure("Card.TLabel", background=CARD_BG, foreground=INK)

    style.configure(
        "Sidebar.TFrame", background=SIDEBAR_BG, borderwidth=0, relief="flat"
    )
    style.configure(
        "SidebarTitle.TLabel",
        background=SIDEBAR_BG,
        foreground=SIDEBAR_TEXT_ACTIVE,
        font=(family, 15, "bold"),
    )
    style.configure(
        "SidebarSubtitle.TLabel",
        background=SIDEBAR_BG,
        foreground=SIDEBAR_TEXT,
        font=Fonts.small,
    )
    style.configure(
        "Sidebar.TButton",
        background=SIDEBAR_BG,
        foreground=SIDEBAR_TEXT,
        borderwidth=0,
        focusthickness=0,
        padding=(16, 10),
        font=Fonts.body,
        anchor="w",
    )
    style.map(
        "Sidebar.TButton",
        background=[("active", SIDEBAR_BG_HOVER)],
        foreground=[("active", SIDEBAR_TEXT_ACTIVE)],
    )
    style.configure(
        "SidebarActive.TButton",
        background=ACCENT,
        foreground="#FFFFFF",
        borderwidth=0,
        focusthickness=0,
        padding=(16, 10),
        font=Fonts.body_bold,
        anchor="w",
    )
    style.map("SidebarActive.TButton", background=[("active", ACCENT)])

    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground="#FFFFFF",
        borderwidth=0,
        focusthickness=0,
        padding=(14, 7),
        font=Fonts.body_bold,
    )
    style.map(
        "Accent.TButton",
        background=[("active", ACCENT_HOVER), ("disabled", "#A9C9CB")],
    )

    style.configure(
        "Danger.TButton",
        background=DANGER,
        foreground="#FFFFFF",
        borderwidth=0,
        focusthickness=0,
        padding=(14, 7),
        font=Fonts.body_bold,
    )
    style.map(
        "Danger.TButton",
        background=[("active", DANGER_HOVER), ("disabled", "#D9AFAC")],
    )

    style.configure(
        "Ghost.TButton",
        background=APP_BG,
        foreground=INK,
        borderwidth=1,
        focusthickness=0,
        padding=(12, 6),
        font=Fonts.body,
    )
    style.map(
        "Ghost.TButton",
        background=[("active", CARD_BG)],
        bordercolor=[("!disabled", CARD_BORDER_HOVER)],
    )

    style.configure(
        "Search.TEntry",
        padding=8,
        fieldbackground=CARD_BG,
        bordercolor=CARD_BORDER,
        lightcolor=CARD_BG,
        darkcolor=CARD_BG,
    )

    style.configure("Header.TFrame", background=APP_BG)
    style.configure(
        "PageTitle.TLabel", background=APP_BG, foreground=INK, font=Fonts.display
    )
    style.configure(
        "PageSubtitle.TLabel",
        background=APP_BG,
        foreground=INK_MUTED,
        font=Fonts.body,
    )

    style.configure(
        "Status.TFrame", background=SIDEBAR_BG, borderwidth=0, relief="flat"
    )
    style.configure(
        "Status.TLabel",
        background=SIDEBAR_BG,
        foreground=SIDEBAR_TEXT,
        font=Fonts.small,
    )
    style.configure(
        "Status.Horizontal.TProgressbar",
        background=ACCENT,
        troughcolor=SIDEBAR_BG_HOVER,
    )

    style.configure(
        "Treeview",
        rowheight=28,
        background=CARD_BG,
        fieldbackground=CARD_BG,
        foreground=INK,
        borderwidth=0,
        font=Fonts.body,
    )
    style.configure(
        "Treeview.Heading",
        background=APP_BG,
        foreground=INK_MUTED,
        font=Fonts.body_bold,
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", ACCENT_SOFT)],
        foreground=[("selected", INK)],
    )

    style.configure(
        "Card.TCheckbutton", background=CARD_BG, foreground=INK, font=Fonts.body
    )

    return style
