from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .. import sources as src
from . import theme
from .widgets import Badge, ScrollableFrame, SectionHeader


class AddSourceDialog(tk.Toplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add Repository")
        self.configure(bg=theme.APP_BG)
        self.result: tuple[str, str] | None = None  # (kind, value)
        self.resizable(False, False)
        self.transient(parent)

        pad = {"padx": 16, "pady": 8}
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Enter a PPA (ppa:user/name) or a full 'deb ...' source line.",
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        self.value_var = tk.StringVar()
        entry = ttk.Entry(
            frame, textvariable=self.value_var, width=52, style="Search.TEntry"
        )
        entry.pack(fill="x")
        entry.focus_set()

        note = ttk.Label(
            frame,
            text=(
                "PPAs are handled with add-apt-repository, which also fetches the "
                "correct signing key. Custom 'deb' lines are appended as-is — make "
                "sure the vendor's signing key is already installed."
            ),
            wraplength=420,
            justify="left",
            foreground=theme.INK_MUTED,
            font=theme.Fonts.small,
        )
        note.pack(anchor="w", pady=(10, 0))

        btns = ttk.Frame(frame, padding=(0, 14, 0, 0))
        btns.pack(fill="x")
        ttk.Button(
            btns, text="Cancel", style="Ghost.TButton", command=self.destroy
        ).pack(side="right")
        ttk.Button(btns, text="Add", style="Accent.TButton", command=self._submit).pack(
            side="right", padx=(0, 8)
        )

        self.bind("<Return>", lambda e: self._submit())
        self.grab_set()

    def _submit(self):
        text = self.value_var.get().strip()
        if not text:
            return
        if src.looks_like_ppa(text):
            self.result = ("ppa", text)
        elif src.looks_like_deb_line(text):
            self.result = ("line", text)
        else:
            messagebox.showerror(
                "Unrecognized format",
                "This doesn't look like a ppa:user/name entry or a valid "
                "'deb <uri> <distribution> [components]' line.",
                parent=self,
            )
            return
        self.destroy()


class SourceRow(ttk.Frame):
    def __init__(self, parent, source: src.AptSource, on_toggle, on_remove):
        super().__init__(parent, style="Card.TFrame", padding=(14, 8))
        border = tk.Frame(self, bg=theme.CARD_BORDER)
        border.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lower(border)

        self.enabled_var = tk.BooleanVar(value=source.enabled)
        chk = ttk.Checkbutton(
            self,
            variable=self.enabled_var,
            style="Card.TCheckbutton",
            command=lambda: on_toggle(source, self.enabled_var.get()),
        )
        chk.pack(side="left")

        text_frame = ttk.Frame(self, style="Card.TFrame")
        text_frame.pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Label(
            text_frame,
            text=source.display_name,
            style="Card.TLabel",
            font=theme.Fonts.body_bold,
            foreground=theme.INK if source.enabled else theme.INK_MUTED,
        ).pack(anchor="w")
        meta = f"{source.file_label}"
        if source.parse_ok and source.components:
            meta += f"  \u2022  {source.entry_type}  \u2022  {source.components}"
        ttk.Label(
            text_frame,
            text=meta,
            style="Card.TLabel",
            foreground=theme.INK_MUTED,
            font=theme.Fonts.small,
        ).pack(anchor="w")

        if not source.parse_ok:
            Badge(self, "Unrecognized", bg="#F3E3C7", fg=theme.GOLD).pack(
                side="left", padx=(0, 8)
            )

        ttk.Button(
            self,
            text="Remove",
            style="Ghost.TButton",
            command=lambda: on_remove(source),
        ).pack(side="right")


class SourcesView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame", padding=20)
        self.app = app
        self.sources: list[src.AptSource] = []

        header_row = ttk.Frame(self, style="Header.TFrame")
        header_row.pack(fill="x")
        SectionHeader(
            header_row,
            "Software Sources",
            "Enable, disable, add or remove the apt repositories this system uses.",
        ).pack(side="left", anchor="w")
        ttk.Button(
            header_row,
            text="Add Repository\u2026",
            style="Accent.TButton",
            command=self.add_repository,
        ).pack(side="right", anchor="e", pady=(4, 0))

        self.warning_label = ttk.Label(
            self,
            text="",
            foreground=theme.GOLD,
            font=theme.Fonts.small,
            wraplength=760,
            justify="left",
        )
        self.warning_label.pack(anchor="w", pady=(8, 0))

        toolbar = ttk.Frame(self, padding=(0, 10, 0, 6))
        toolbar.pack(fill="x")
        ttk.Button(
            toolbar, text="Refresh", style="Ghost.TButton", command=self.refresh
        ).pack(side="left")

        self.list_area = ScrollableFrame(self)
        self.list_area.pack(fill="both", expand=True)

        self.refresh()

    def refresh(self):
        self.sources = src.list_sources()
        unsupported = src.list_unsupported_deb822_files()
        if unsupported:
            names = ", ".join(f.split("/")[-1] for f in unsupported)
            self.warning_label.config(
                text=(
                    f"Note: {names} use the newer deb822 .sources format and are shown "
                    "read-only here — edit them with a text editor if needed."
                )
            )
        else:
            self.warning_label.config(text="")

        self.list_area.clear()
        if not self.sources:
            ttk.Label(
                self.list_area.inner,
                text="No apt sources found.",
                foreground=theme.INK_MUTED,
                padding=20,
            ).pack(anchor="w")
            return

        by_file: dict[str, list[src.AptSource]] = {}
        for s in self.sources:
            by_file.setdefault(s.file_path, []).append(s)

        for file_path in sorted(by_file):
            ttk.Label(
                self.list_area.inner,
                text=file_path,
                font=theme.Fonts.small_muted,
                foreground=theme.INK_MUTED,
                padding=(2, 10, 0, 4),
            ).pack(anchor="w")
            for s in sorted(by_file[file_path], key=lambda x: x.line_number):
                row = SourceRow(self.list_area.inner, s, self._toggle, self._remove)
                row.pack(fill="x", pady=(0, 6), padx=1)

    # -- actions -----------------------------------------------------------
    def _toggle(self, source: src.AptSource, enable: bool):
        cmd = src.build_toggle_command(source, enable)
        self.app.controller.run(
            cmd,
            needs_root=True,
            description="Enabling source" if enable else "Disabling source",
            on_done=self.refresh,
        )

    def _remove(self, source: src.AptSource):
        if not messagebox.askyesno(
            "Remove source",
            f"Remove this source entry?\n\n{source.display_name}\n\nfrom {source.file_path}",
        ):
            return
        cmd = src.build_remove_command(source)
        self.app.controller.run(
            cmd, needs_root=True, description="Removing source", on_done=self.refresh
        )

    def add_repository(self):
        dialog = AddSourceDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        kind, value = dialog.result
        if kind == "ppa":
            cmd = src.build_add_ppa_command(value)
            if cmd is None:
                messagebox.showerror(
                    "software-properties-common not found",
                    "Adding PPAs requires the 'software-properties-common' package "
                    "(provides add-apt-repository). Install it first, then try again.",
                )
                return
            self.app.controller.run(
                cmd,
                needs_root=True,
                description=f"Adding {value}",
                on_done=self.refresh,
            )
        else:
            cmd = src.build_add_line_command(value)
            self.app.controller.run(
                cmd, needs_root=True, description="Adding source", on_done=self.refresh
            )
