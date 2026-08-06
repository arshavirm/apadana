from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox, simpledialog

from .. import apt_backend


def prompt_for_root_password() -> str | None:
    """Blocking pre-flight password check, shown before the main window.

    Returns the verified password (so it can be cached) or None if sudo
    isn't in use / the user cancelled.
    """
    auth_root = tk.Tk()
    auth_root.withdraw()

    if not __import__("shutil").which("sudo"):
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

        if apt_backend.verify_sudo_password(password):
            break

        messagebox.showerror(
            "Authentication Failed",
            "Incorrect password. Please try again.",
            parent=auth_root,
        )

    auth_root.destroy()
    return password


def ask_sudo_password(parent) -> str | None:
    return simpledialog.askstring(
        "Password required",
        "Enter your administrator (sudo) password:",
        show="*",
        parent=parent,
    )
