from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class InstalledPackage:
    name: str
    version: str
    arch: str


_INSTALLED_LINE_RE = re.compile(r"^(\S+)/\S+\s+(\S+)\s+(\S+)")


def parse_installed_list(output: str) -> dict[str, InstalledPackage]:
    packages: dict[str, InstalledPackage] = {}
    for line in output.splitlines():
        m = _INSTALLED_LINE_RE.match(line)
        if m:
            name, version, arch = m.group(1), m.group(2), m.group(3)
            packages[name] = InstalledPackage(name=name, version=version, arch=arch)
    return packages


def parse_search_results(output: str) -> dict[str, str]:
    results: dict[str, str] = {}
    for line in output.splitlines():
        if " - " in line:
            name, desc = line.split(" - ", 1)
            results[name.strip()] = desc.strip()
    return results


def parse_description(show_output: str) -> str:
    for line in show_output.splitlines():
        if line.startswith("Description:") or line.startswith("Description-en:"):
            return line.split(":", 1)[1].strip()
    return ""


def cmd_list_installed() -> list[str]:
    return ["apt", "list", "--installed"]


def cmd_search(term: str) -> list[str]:
    return ["apt-cache", "search", term]


def cmd_show(name: str) -> list[str]:
    return ["apt-cache", "show", name]


def cmd_update_index() -> list[str]:
    return ["apt-get", "update"]


def cmd_upgrade_all() -> list[str]:
    return ["apt-get", "upgrade", "-y"]


def cmd_autoremove() -> list[str]:
    return ["apt-get", "autoremove", "-y"]


def cmd_install(names: list[str]) -> list[str]:
    return ["apt-get", "install", "-y"] + names


def cmd_upgrade_packages(names: list[str]) -> list[str]:
    return ["apt-get", "install", "--only-upgrade", "-y"] + names


def cmd_remove(names: list[str]) -> list[str]:
    return ["apt-get", "remove", "-y"] + names


def cmd_purge(names: list[str]) -> list[str]:
    return ["apt-get", "purge", "-y"] + names


def fetch_description(name: str) -> str:
    """Synchronous helper meant to be called off the main thread."""
    try:
        result = subprocess.run(
            cmd_show(name), capture_output=True, text=True, timeout=10
        )
        return parse_description(result.stdout) or "No description available."
    except Exception:
        return "(could not fetch description)"
