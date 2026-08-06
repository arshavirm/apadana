from __future__ import annotations

import queue
import subprocess
import threading
from dataclasses import dataclass
from tkinter import messagebox

from .. import apt_backend


@dataclass
class Callbacks:
    log: callable  # (text: str) -> None
    set_status: callable  # (text: str) -> None
    set_busy: callable  # (is_busy: bool) -> None
    ask_password: callable  # () -> str | None


class OperationController:
    def __init__(self, root, callbacks: Callbacks):
        self.root = root
        self.cb = callbacks
        self.output_queue: "queue.Queue[str]" = queue.Queue()
        self.current_process: subprocess.Popen | None = None
        self.cached_sudo_password: str | None = None
        self._poll()

    # -- output pump ---------------------------------------------------
    def _poll(self):
        try:
            while True:
                line = self.output_queue.get_nowait()
                self.cb.log(line)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _log(self, text: str):
        self.output_queue.put(text)

    # -- public API ------------------------------------------------------
    def run(self, cmd_list, *, needs_root=False, description="", on_done=None):
        self._start(cmd_list, needs_root, description, on_done, cmd_list, _retry=False)

    def cancel_current(self):
        if self.current_process is not None:
            try:
                self.current_process.terminate()
                self._log("\n[Cancelled by user]\n")
                self.root.after(0, lambda: self.cb.set_status("Cancelled."))
            except Exception as e:
                self._log(f"Could not cancel: {e}\n")

    # -- internals ---------------------------------------------------------
    def _start(
        self, cmd_list, needs_root, description, on_done, original_cmd_list, _retry
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
            final_cmd, needs_password = apt_backend.build_privileged_command(cmd_list)
            if needs_password:
                if _retry or not self.cached_sudo_password:
                    password = self.cb.ask_password()
                    if password is None:
                        self.cb.set_status("Cancelled: no password provided.")
                        return
                    self.cached_sudo_password = password
                else:
                    password = self.cached_sudo_password

        self._log(f"\n$ {' '.join(final_cmd)}\n{'-' * 60}\n")
        self.cb.set_status(f"{description or 'Working'}...")
        self.cb.set_busy(True)

        thread = threading.Thread(
            target=self._worker,
            args=(
                final_cmd,
                password,
                description,
                on_done,
                original_cmd_list,
                needs_root,
            ),
            daemon=True,
        )
        thread.start()

    def _worker(
        self, cmd_list, password, description, on_done, original_cmd_list, needs_root
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

            if proc.stdout:
                for line in proc.stdout:
                    self._log(line)
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
            self._log(f"\n{'-' * 60}\nFinished with exit code {code}\n")

            if auth_failed:
                # Cached password was wrong/stale. Clear it and retry once
                # automatically with a fresh prompt; on_done is deliberately
                # NOT called here since the operation hasn't finished yet.
                self.cached_sudo_password = None
                self.root.after(
                    0,
                    lambda: self.cb.set_status(
                        "Incorrect password — please try again."
                    ),
                )
                if original_cmd_list is not None:
                    self.root.after(
                        0,
                        lambda: self._start(
                            original_cmd_list,
                            needs_root,
                            description,
                            on_done,
                            original_cmd_list,
                            _retry=True,
                        ),
                    )
                retry_pending = True
            elif lock_error and code != 0:
                self.root.after(
                    0,
                    lambda: self.cb.set_status(
                        f"{description or 'Operation'} failed: package manager is locked."
                    ),
                )
                self.root.after(
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
                self.root.after(
                    0,
                    lambda: self.cb.set_status(
                        f"{description or 'Operation'} completed successfully."
                    ),
                )
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Success",
                        f"{description or 'Operation'} completed successfully.",
                    ),
                )
            else:
                self.root.after(
                    0,
                    lambda: self.cb.set_status(
                        f"{description or 'Operation'} failed (exit code {code})."
                    ),
                )
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error",
                        f"{description or 'Operation'} failed (exit code {code}).\n"
                        f"Open 'Show Technical Log' for details.",
                    ),
                )
        except FileNotFoundError as e:
            self._log(f"Error: {e}\n")
            self.root.after(
                0, lambda: self.cb.set_status("Error: required command not found.")
            )
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Error", f"Required command not found:\n{e}"
                ),
            )
        except Exception as e:
            self._log(f"Unexpected error: {e}\n")
            self.root.after(0, lambda: self.cb.set_status("Unexpected error."))
            self.root.after(
                0, lambda: messagebox.showerror("Error", f"Unexpected error:\n{e}")
            )
        finally:
            self.current_process = None
            if not retry_pending:
                self.root.after(0, lambda: self.cb.set_busy(False))
                if on_done:
                    self.root.after(0, on_done)
