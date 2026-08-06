from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .. import apt_operations as ops
from . import theme
from .widgets import SectionHeader


class InstalledView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame", padding=20)
        self.app = app
        self.installed_data: dict[str, ops.InstalledPackage] = {}

        SectionHeader(
            self, "Installed Software", "Everything currently on this system."
        ).pack(anchor="w", fill="x")

        toolbar = ttk.Frame(self, padding=(0, 14, 0, 10))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Filter:").pack(side="left")
        self.filter_var = tk.StringVar()
        entry = ttk.Entry(toolbar, textvariable=self.filter_var, width=36, style="Search.TEntry")
        entry.pack(side="left", padx=(6, 6))
        entry.bind("<KeyRelease>", lambda e: self.apply_filter())
        ttk.Button(toolbar, text="Refresh List", style="Ghost.TButton", command=self.refresh).pack(
            side="left"
        )

        table_wrap = ttk.Frame(self, style="Card.TFrame")
        table_wrap.pack(fill="both", expand=True)
        columns = ("name", "version", "arch")
        self.tree = ttk.Treeview(
            table_wrap, columns=columns, show="headings", selectmode="extended"
        )
        self.tree.heading("name", text="Package")
        self.tree.heading("version", text="Version")
        self.tree.heading("arch", text="Architecture")
        self.tree.column("name", width=340, anchor="w")
        self.tree.column("version", width=260, anchor="w")
        self.tree.column("arch", width=100, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        scroll = ttk.Scrollbar(table_wrap, command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        action_bar = ttk.Frame(self, padding=(0, 10, 0, 0))
        action_bar.pack(fill="x")
        ttk.Button(
            action_bar, text="Upgrade Selected", style="Accent.TButton", command=self.upgrade_selected
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            action_bar, text="Remove Selected", style="Danger.TButton", command=self.remove_selected
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            action_bar,
            text="Purge (incl. config files)",
            style="Danger.TButton",
            command=self.purge_selected,
        ).pack(side="left", padx=(0, 6))
        ttk.Separator(action_bar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(
            action_bar, text="Check for Updates", style="Ghost.TButton", command=self.update_index
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            action_bar, text="Upgrade All Software", style="Accent.TButton", command=self.upgrade_all
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            action_bar,
            text="Remove Unused Packages",
            style="Ghost.TButton",
            command=self.autoremove,
        ).pack(side="left")

    # -- data loading -----------------------------------------------------
    def refresh(self):
        self.app.set_status("Loading installed software...")
        self.app.set_busy(True)
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        try:
            import subprocess

            result = subprocess.run(
                ops.cmd_list_installed(), capture_output=True, text=True, timeout=30
            )
            self.installed_data = ops.parse_installed_list(result.stdout)
            self.after(0, self._populate)
        except Exception as e:
            self.app.log(f"Error loading installed packages: {e}\n")
        finally:
            self.after(0, lambda: self.app.set_busy(False))
            self.after(0, lambda: self.app.set_status("Ready."))

    def _populate(self):
        self.tree.delete(*self.tree.get_children())
        for name, pkg in sorted(self.installed_data.items()):
            self.tree.insert("", "end", values=(name, pkg.version, pkg.arch))
        self.apply_filter()
        self.app.on_installed_data_changed(self.installed_data)

    def apply_filter(self):
        term = self.filter_var.get().strip().lower()
        for item in self.tree.get_children():
            name = self.tree.item(item, "values")[0].lower()
            if term and term not in name:
                self.tree.detach(item)
            else:
                self.tree.reattach(item, "", "end")

    # -- selection / details -----------------------------------------------
    def _selected_names(self) -> list[str]:
        return [self.tree.item(i, "values")[0] for i in self.tree.selection()]

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        if len(sel) > 1:
            self.app.set_details(f"{len(sel)} packages selected.")
            return
        name = self.tree.item(sel[0], "values")[0]
        self.app.set_details(f"Fetching description for {name}...")
        threading.Thread(target=self._fetch_description, args=(name,), daemon=True).start()

    def _fetch_description(self, name):
        desc = ops.fetch_description(name)
        self.after(0, lambda: self.app.set_details(f"{name}: {desc}"))

    # -- actions -----------------------------------------------------------
    def remove_selected(self):
        names = self._selected_names()
        if not names:
            messagebox.showinfo("No selection", "Select one or more packages from the list first.")
            return
        if not messagebox.askyesno("Confirm removal", "Remove the following package(s)?\n\n" + "\n".join(names)):
            return
        self.app.controller.run(
            ops.cmd_remove(names), needs_root=True, description="Removing package(s)", on_done=self.refresh
        )

    def purge_selected(self):
        names = self._selected_names()
        if not names:
            messagebox.showinfo("No selection", "Select one or more packages from the list first.")
            return
        if not messagebox.askyesno(
            "Confirm purge",
            "Purge the following package(s) and their configuration files?\n\n" + "\n".join(names),
        ):
            return
        self.app.controller.run(
            ops.cmd_purge(names), needs_root=True, description="Purging package(s)", on_done=self.refresh
        )

    def upgrade_selected(self):
        names = self._selected_names()
        if not names:
            messagebox.showinfo("No selection", "Select one or more packages from the list first.")
            return
        self.app.controller.run(
            ops.cmd_upgrade_packages(names),
            needs_root=True,
            description="Upgrading package(s)",
            on_done=self.refresh,
        )

    def update_index(self):
        self.app.controller.run(ops.cmd_update_index(), needs_root=True, description="Checking for updates")

    def upgrade_all(self):
        if not messagebox.askyesno("Confirm upgrade", "Upgrade all installed software to the latest version?"):
            return
        self.app.controller.run(
            ops.cmd_upgrade_all(), needs_root=True, description="Upgrading all software", on_done=self.refresh
        )

    def autoremove(self):
        if not messagebox.askyesno("Confirm cleanup", "Remove packages that are no longer needed?"):
            return
        self.app.controller.run(
            ops.cmd_autoremove(), needs_root=True, description="Removing unused packages", on_done=self.refresh
        )
