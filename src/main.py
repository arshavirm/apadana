#!/usr/bin/env python3
"""Apadana — a graphical apt package manager.

Run with: python3 main.py
"""

import sys
import tkinter as tk
from tkinter import messagebox

from apadana import apt_backend
from apadana.ui.app import ApadanaApp
from apadana.ui.dialogs import prompt_for_root_password


def main():
    if not apt_backend.apt_get_available():
        err_root = tk.Tk()
        err_root.withdraw()
        messagebox.showerror(
            "Unsupported System",
            "Apadana requires 'apt-get' (Debian/Ubuntu-based systems) and it "
            "was not found on this system.",
        )
        err_root.destroy()
        sys.exit(1)

    verified_password = prompt_for_root_password()
    app = ApadanaApp()
    if verified_password:
        app.cached_sudo_password = verified_password
        app.controller.cached_sudo_password = verified_password
    app.mainloop()


if __name__ == "__main__":
    main()
