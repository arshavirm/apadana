#!/usr/bin/env python3

import re
import shutil
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import os


def build_privileged_command(cmd_list):
    if shutil.which("sudo"):
        return ["sudo", "-S"] + cmd_list, True
    elif shutil.which("pkexec"):
        return ["pkexec"] + cmd_list, False
    else:
        return cmd_list, False


def verify_sudo_password(password):
    if not shutil.which("sudo"):
        return True
    try:
        proc = subprocess.run(
            ["sudo", "-S", "-k", "-v"],
            input=password + "\n",
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode == 0
    except Exception:
        return False


def prompt_for_root_password():
    auth_root = tk.Tk()
    auth_root.withdraw()

    if not shutil.which("sudo"):
        auth_root.destroy()
        return None

    password = None
    while True:
        password = simpledialog.askstring(
            "Authentication Required",
            "Apadana needs administrator access to manage software.\n"
            "Enter your password to continue:",
            show="*",
            parent=auth_root,
        )
        if password is None:
            auth_root.destroy()
            sys.exit(0)

        if verify_sudo_password(password):
            break

        messagebox.showerror(
            "Authentication Failed",
            "Incorrect password. Please try again.",
            parent=auth_root,
        )

    auth_root.destroy()
    return password


class ApadanaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Apadana")
        self.geometry("980x680")
        self.minsize(760, 540)

        if getattr(sys, "frozen", False):
            self.iconphoto(
                False, tk.PhotoImage(file=os.path.join(sys._MEIPASS, "src/logo.png"))
            )
        else:
            self.iconphoto(False, tk.PhotoImage(file="src/logo.png"))

        self.output_queue = queue.Queue()
        self.current_process = None
        self.cached_sudo_password = None

        self.installed_data = {}
        self.search_data = {}

        self.build_ui()
        self.poll_queue()
        self.after(200, self.refresh_installed)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.cached_sudo_password = None
        if shutil.which("sudo"):
            try:
                subprocess.run(["sudo", "-k"], timeout=5)
            except Exception:
                pass
        self.destroy()

    def build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=24)

        self.title_label = ttk.Label(
            self, text="Apadana v1.2 - Arshavir Mirzakhani", justify="center"
        ).pack()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self.installed_tab = ttk.Frame(notebook)
        self.search_tab = ttk.Frame(notebook)
        notebook.add(self.installed_tab, text="Installed Software")
        notebook.add(self.search_tab, text="Find New Software")

        self.build_installed_tab()
        self.build_search_tab()

        details_frame = ttk.LabelFrame(self, text="Details", padding=8)
        details_frame.pack(fill="x", padx=10, pady=8)
        self.details_var = tk.StringVar(
            value="Select a package to see its description here."
        )
        details_label = ttk.Label(
            details_frame, textvariable=self.details_var, wraplength=940, justify="left"
        )
        details_label.pack(fill="x")

        status_frame = ttk.Frame(self, padding=(10, 0, 10, 4))
        status_frame.pack(fill="x")
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side="left")
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=160)
        self.progress.pack(side="left", padx=10)
        self.cancel_btn = ttk.Button(
            status_frame, text="Cancel", command=self.cancel_current, state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=6)

        self.log_toggle_btn = ttk.Button(
            status_frame, text="Show Technical Log \u25be", command=self.toggle_log
        )
        self.log_toggle_btn.pack(side="right")

        self.log_frame = ttk.Frame(self)
        self.output_text = tk.Text(
            self.log_frame,
            height=10,
            wrap="word",
            bg="#111",
            fg="#0f0",
            insertbackground="#0f0",
            font=("Consolas", 9),
        )
        self.output_text.pack(
            side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10)
        )
        log_scroll = ttk.Scrollbar(self.log_frame, command=self.output_text.yview)
        log_scroll.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))
        self.output_text.config(yscrollcommand=log_scroll.set)
        self.log_visible = False  # log_frame not packed initially

    def build_installed_tab(self):
        top = ttk.Frame(self.installed_tab, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Filter:").pack(side="left")
        self.installed_filter_var = tk.StringVar()
        filter_entry = ttk.Entry(top, textvariable=self.installed_filter_var, width=40)
        filter_entry.pack(side="left", padx=6)
        filter_entry.bind("<KeyRelease>", lambda e: self.apply_installed_filter())

        ttk.Button(top, text="Refresh List", command=self.refresh_installed).pack(
            side="left", padx=6
        )

        columns = ("name", "version", "arch")
        self.installed_tree = ttk.Treeview(
            self.installed_tab, columns=columns, show="headings", selectmode="extended"
        )
        self.installed_tree.heading("name", text="Package")
        self.installed_tree.heading("version", text="Version")
        self.installed_tree.heading("arch", text="Architecture")
        self.installed_tree.column("name", width=340, anchor="w")
        self.installed_tree.column("version", width=260, anchor="w")
        self.installed_tree.column("arch", width=100, anchor="center")
        self.installed_tree.pack(fill="both", expand=True, padx=8)
        self.installed_tree.bind(
            "<<TreeviewSelect>>", lambda e: self.on_select(self.installed_tree)
        )

        tscroll = ttk.Scrollbar(self.installed_tab, command=self.installed_tree.yview)
        self.installed_tree.configure(yscrollcommand=tscroll.set)

        action_bar = ttk.Frame(self.installed_tab, padding=8)
        action_bar.pack(fill="x")
        ttk.Button(
            action_bar, text="Upgrade Selected", command=self.upgrade_selected
        ).pack(side="left", padx=3)
        ttk.Button(
            action_bar, text="Remove Selected", command=self.remove_selected
        ).pack(side="left", padx=3)
        ttk.Button(
            action_bar,
            text="Purge Selected (incl. config files)",
            command=self.purge_selected,
        ).pack(side="left", padx=3)
        ttk.Separator(action_bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(
            action_bar, text="Check for Updates", command=self.update_index
        ).pack(side="left", padx=3)
        ttk.Button(
            action_bar, text="Upgrade All Software", command=self.upgrade_all
        ).pack(side="left", padx=3)
        ttk.Button(
            action_bar, text="Remove Unused Packages", command=self.autoremove
        ).pack(side="left", padx=3)

    def build_search_tab(self):
        top = ttk.Frame(self.search_tab, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=self.search_var, width=40)
        search_entry.pack(side="left", padx=6)
        search_entry.bind("<Return>", lambda e: self.search_packages())
        ttk.Button(top, text="Search", command=self.search_packages).pack(
            side="left", padx=6
        )

        columns = ("name", "status", "description")
        self.search_tree = ttk.Treeview(
            self.search_tab, columns=columns, show="headings", selectmode="extended"
        )
        self.search_tree.heading("name", text="Package")
        self.search_tree.heading("status", text="Status")
        self.search_tree.heading("description", text="Description")
        self.search_tree.column("name", width=220, anchor="w")
        self.search_tree.column("status", width=90, anchor="center")
        self.search_tree.column("description", width=560, anchor="w")
        self.search_tree.pack(fill="both", expand=True, padx=8)
        self.search_tree.bind(
            "<<TreeviewSelect>>", lambda e: self.on_select(self.search_tree)
        )

        action_bar = ttk.Frame(self.search_tab, padding=8)
        action_bar.pack(fill="x")
        ttk.Button(
            action_bar, text="Install Selected", command=self.install_selected
        ).pack(side="left", padx=3)

    def toggle_log(self):
        if self.log_visible:
            self.log_frame.pack_forget()
            self.log_toggle_btn.config(text="Show Technical Log \u25be")
        else:
            self.log_frame.pack(fill="both", expand=False)
            self.log_toggle_btn.config(text="Hide Technical Log \u25b4")
        self.log_visible = not self.log_visible

    def log(self, text):
        self.output_queue.put(text)

    def poll_queue(self):
        try:
            while True:
                line = self.output_queue.get_nowait()
                self.output_text.insert("end", line)
                self.output_text.see("end")
        except queue.Empty:
            pass
        self.after(100, self.poll_queue)

    def on_select(self, tree):
        sel = tree.selection()
        if not sel:
            return
        if len(sel) > 1:
            self.details_var.set(f"{len(sel)} packages selected.")
            return
        values = tree.item(sel[0], "values")
        name = values[0]
        if tree is self.search_tree and name in self.search_data:
            self.details_var.set(f"{name}: {self.search_data[name]}")
        elif tree is self.installed_tree:
            self.details_var.set(f"Fetching description for {name}...")
            threading.Thread(
                target=self.fetch_description, args=(name,), daemon=True
            ).start()

    def fetch_description(self, name):
        try:
            result = subprocess.run(
                ["apt-cache", "show", name], capture_output=True, text=True, timeout=10
            )
            desc = ""
            for line in result.stdout.splitlines():
                if line.startswith("Description:") or line.startswith(
                    "Description-en:"
                ):
                    desc = line.split(":", 1)[1].strip()
                    break
            self.details_var.set(f"{name}: {desc or 'No description available.'}")
        except Exception:
            self.details_var.set(f"{name}: (could not fetch description)")

    def refresh_installed(self):
        self.status_var.set("Loading installed software...")
        self.start_progress()
        threading.Thread(target=self.load_installed_worker, daemon=True).start()

    def load_installed_worker(self):
        try:
            result = subprocess.run(
                ["apt", "list", "--installed"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            data = {}
            pattern = re.compile(r"^(\S+)/\S+\s+(\S+)\s+(\S+)")
            for line in result.stdout.splitlines():
                m = pattern.match(line)
                if m:
                    name, version, arch = m.group(1), m.group(2), m.group(3)
                    data[name] = {"version": version, "arch": arch}
            self.installed_data = data
            self.after(0, self.populate_installed_tree)
        except Exception as e:
            self.log(f"Error loading installed packages: {e}\n")
        finally:
            self.after(0, self.stop_progress)
            self.after(0, lambda: self.status_var.set("Ready."))

    def populate_installed_tree(self):
        self.installed_tree.delete(*self.installed_tree.get_children())
        for name, info in sorted(self.installed_data.items()):
            self.installed_tree.insert(
                "", "end", values=(name, info["version"], info["arch"])
            )
        self.apply_installed_filter()

    def apply_installed_filter(self):

        term = self.installed_filter_var.get().strip().lower()

        for item in self.installed_tree.get_children():
            name = self.installed_tree.item(item, "values")[0].lower()
            if term and term not in name:
                self.installed_tree.detach(item)
            else:
                self.installed_tree.reattach(item, "", "end")

    def search_packages(self):
        term = self.search_var.get().strip()
        if not term:
            messagebox.showinfo("Search", "Type something to search for first.")
            return
        self.status_var.set(f"Searching for '{term}'...")
        self.start_progress()
        threading.Thread(target=self.search_worker, args=(term,), daemon=True).start()

    def search_worker(self, term):
        try:
            result = subprocess.run(
                ["apt-cache", "search", term],
                capture_output=True,
                text=True,
                timeout=30,
            )
            data = {}
            for line in result.stdout.splitlines():
                if " - " in line:
                    name, desc = line.split(" - ", 1)
                    data[name.strip()] = desc.strip()
            self.search_data = data
            self.after(0, self.populate_search_tree)
        except Exception as e:
            self.log(f"Error searching packages: {e}\n")
        finally:
            self.after(0, self.stop_progress)
            self.after(0, lambda: self.status_var.set("Ready."))

    def populate_search_tree(self):
        self.search_tree.delete(*self.search_tree.get_children())
        for name, desc in sorted(self.search_data.items()):
            status = "Installed" if name in self.installed_data else ""
            self.search_tree.insert("", "end", values=(name, status, desc))

    def start_progress(self):
        self.progress.start(12)

    def stop_progress(self):
        self.progress.stop()

    def run_command(
        self, cmd_list, needs_root=False, description="", on_done=None, _retry=False
    ):
        if self.current_process is not None:
            messagebox.showwarning(
                "Busy",
                "Another operation is already running. Please wait for it to finish.",
            )
            return

        password = None
        final_cmd = cmd_list
        if needs_root:
            final_cmd, needs_password = build_privileged_command(cmd_list)
            if needs_password:
                # On a retry (previous attempt's cached password was wrong)
                # always ask fresh instead of reusing the bad one.
                if _retry or not self.cached_sudo_password:
                    password = simpledialog.askstring(
                        "Password required",
                        "Enter your administrator (sudo) password:",
                        show="*",
                        parent=self,
                    )
                    if password is None:
                        self.status_var.set("Cancelled: no password provided.")
                        return
                    self.cached_sudo_password = password
                else:
                    password = self.cached_sudo_password

        self.log(f"\n$ {' '.join(final_cmd)}\n{'-'*60}\n")
        self.status_var.set(f"{description or 'Working'}...")
        self.start_progress()
        self.cancel_btn.config(state="normal")

        thread = threading.Thread(
            target=self.worker,
            args=(final_cmd, password, description, on_done, cmd_list, needs_root),
            daemon=True,
        )
        thread.start()

    def worker(
        self,
        cmd_list,
        password,
        description,
        on_done,
        original_cmd_list=None,
        needs_root=False,
    ):
        auth_failed = False
        lock_error = False
        retry_pending = False
        try:
            proc = subprocess.Popen(
                cmd_list,
                stdin=subprocess.PIPE if password else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.current_process = proc

            if password:
                try:
                    stdin = proc.stdin
                    if stdin:
                        stdin.write(password + "\n")
                        stdin.flush()
                        stdin.close()
                except Exception:
                    pass

            # Stream output live as it's produced, instead of waiting for
            # the process to exit first (the old code never read stdout at
            # all, which could also deadlock on commands with lots of
            # output once the OS pipe buffer filled up).
            if proc.stdout:
                for line in proc.stdout:
                    self.log(line)
                    lower = line.lower()
                    if password and (
                        "incorrect password" in lower or "sorry, try again" in lower
                    ):
                        auth_failed = True
                    if (
                        "could not get lock" in lower
                        or "resource temporarily unavailable" in lower
                    ):
                        lock_error = True

            proc.wait()
            code = proc.returncode
            self.current_process = None
            self.log(f"\n{'-'*60}\nFinished with exit code {code}\n")

            if auth_failed:
                # The cached password was wrong or stale (e.g. the user
                # changed it since caching). Clear it and ask again, then
                # automatically retry the same command once. We deliberately
                # do NOT call on_done here (via retry_pending) since the
                # operation hasn't actually completed yet.
                self.cached_sudo_password = None
                self.after(
                    0,
                    lambda: self.status_var.set(
                        "Incorrect password — please try again."
                    ),
                )
                if original_cmd_list is not None:
                    self.after(
                        0,
                        lambda: self.run_command(
                            original_cmd_list,
                            needs_root=needs_root,
                            description=description,
                            on_done=on_done,
                            _retry=True,
                        ),
                    )
                retry_pending = True
            elif lock_error and code != 0:
                self.after(
                    0,
                    lambda: self.status_var.set(
                        f"{description or 'Operation'} failed: package manager is locked."
                    ),
                )
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Package Manager Locked",
                        "Another program (or a background update check) is using "
                        "apt/dpkg right now.\n\nClose other package managers "
                        "(Software Updater, apt in another terminal, etc.) and "
                        "try again.",
                    ),
                )
            elif code == 0:
                self.after(
                    0,
                    lambda: self.status_var.set(
                        f"{description or 'Operation'} completed successfully."
                    ),
                )
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Success",
                        f"{description or 'Operation'} completed successfully.",
                    ),
                )
            else:
                self.after(
                    0,
                    lambda: self.status_var.set(
                        f"{description or 'Operation'} failed (exit code {code})."
                    ),
                )
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error",
                        f"{description or 'Operation'} failed (exit code {code}).\n"
                        f"Open 'Show Technical Log' for details.",
                    ),
                )
        except FileNotFoundError as e:
            self.log(f"Error: {e}\n")
            self.after(
                0, lambda: self.status_var.set("Error: required command not found.")
            )
            self.after(
                0,
                lambda: messagebox.showerror(
                    "Error", f"Required command not found:\n{e}"
                ),
            )
        except Exception as e:
            self.log(f"Unexpected error: {e}\n")
            self.after(0, lambda: self.status_var.set("Unexpected error."))
            self.after(
                0, lambda: messagebox.showerror("Error", f"Unexpected error:\n{e}")
            )
        finally:
            self.current_process = None
            if not retry_pending:
                self.after(0, lambda: self.cancel_btn.config(state="disabled"))
                self.after(0, self.stop_progress)
                if on_done:
                    self.after(0, on_done)

    def cancel_current(self):
        if self.current_process is not None:
            try:
                self.current_process.terminate()
                self.log("\n[Cancelled by user]\n")
                self.status_var.set("Cancelled.")
            except Exception as e:
                self.log(f"Could not cancel: {e}\n")

    def selected_names(self, tree):
        return [tree.item(item, "values")[0] for item in tree.selection()]

    def remove_selected(self):
        names = self.selected_names(self.installed_tree)
        if not names:
            messagebox.showinfo(
                "No selection", "Select one or more packages from the list first."
            )
            return
        if not messagebox.askyesno(
            "Confirm removal", "Remove the following package(s)?\n\n" + "\n".join(names)
        ):
            return
        self.run_command(
            ["apt-get", "remove", "-y"] + names,
            needs_root=True,
            description="Removing package(s)",
            on_done=self.refresh_installed,
        )

    def purge_selected(self):
        names = self.selected_names(self.installed_tree)
        if not names:
            messagebox.showinfo(
                "No selection", "Select one or more packages from the list first."
            )
            return
        if not messagebox.askyesno(
            "Confirm purge",
            "Purge the following package(s) and their configuration files?\n\n"
            + "\n".join(names),
        ):
            return
        self.run_command(
            ["apt-get", "purge", "-y"] + names,
            needs_root=True,
            description="Purging package(s)",
            on_done=self.refresh_installed,
        )

    def upgrade_selected(self):
        names = self.selected_names(self.installed_tree)
        if not names:
            messagebox.showinfo(
                "No selection", "Select one or more packages from the list first."
            )
            return
        self.run_command(
            ["apt-get", "install", "--only-upgrade", "-y"] + names,
            needs_root=True,
            description="Upgrading package(s)",
            on_done=self.refresh_installed,
        )

    def update_index(self):
        self.run_command(
            ["apt-get", "update"], needs_root=True, description="Checking for updates"
        )

    def upgrade_all(self):
        if not messagebox.askyesno(
            "Confirm upgrade", "Upgrade all installed software to the latest version?"
        ):
            return
        self.run_command(
            ["apt-get", "upgrade", "-y"],
            needs_root=True,
            description="Upgrading all software",
            on_done=self.refresh_installed,
        )

    def autoremove(self):
        if not messagebox.askyesno(
            "Confirm cleanup", "Remove packages that are no longer needed?"
        ):
            return
        self.run_command(
            ["apt-get", "autoremove", "-y"],
            needs_root=True,
            description="Removing unused packages",
            on_done=self.refresh_installed,
        )

    def install_selected(self):
        names = self.selected_names(self.search_tree)
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
            self.refresh_installed()
            self.populate_search_tree()

        self.run_command(
            ["apt-get", "install", "-y"] + names,
            needs_root=True,
            description="Installing package(s)",
            on_done=after_install,
        )


if __name__ == "__main__":
    if not shutil.which("apt-get"):
        _err_root = tk.Tk()
        _err_root.withdraw()
        messagebox.showerror(
            "Unsupported System",
            "Apadana requires 'apt-get' (Debian/Ubuntu-based systems) and it "
            "was not found on this system.",
        )
        _err_root.destroy()
        sys.exit(1)

    verified_password = prompt_for_root_password()
    app = ApadanaApp()
    if verified_password:
        app.cached_sudo_password = verified_password
    app.mainloop()
