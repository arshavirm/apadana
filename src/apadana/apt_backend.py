from __future__ import annotations

import shutil
import subprocess


def build_privileged_command(cmd_list: list[str]) -> tuple[list[str], bool]:
    if shutil.which("sudo"):
        return ["sudo", "-S"] + cmd_list, True
    elif shutil.which("pkexec"):
        return ["pkexec"] + cmd_list, False
    else:
        return cmd_list, False


def verify_sudo_password(password: str) -> bool:
    """Check a password against sudo without running a real command."""
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


def drop_cached_credentials() -> None:
    """Best-effort invalidation of the cached sudo timestamp on exit."""
    if shutil.which("sudo"):
        try:
            subprocess.run(["sudo", "-k"], timeout=5)
        except Exception:
            pass


def apt_get_available() -> bool:
    return shutil.which("apt-get") is not None
