from __future__ import annotations

import glob
import os
import re
import shlex
from dataclasses import dataclass

_COMMENTED_DEB_RE = re.compile(r"^(deb|deb-src)(\s|\[)")

SOURCES_LIST = "/etc/apt/sources.list"
SOURCES_LIST_D = "/etc/apt/sources.list.d"
MANAGED_FILE_NAME = "apadana-added.list"

_ENTRY_RE_PARTS = 4  # type, [options], uri, distribution, *components


@dataclass
class AptSource:
    file_path: str
    line_number: int  # 1-indexed line within file_path
    raw_line: str
    enabled: bool
    entry_type: str = ""  # "deb" or "deb-src"
    uri: str = ""
    distribution: str = ""
    components: str = ""
    parse_ok: bool = False

    @property
    def display_name(self) -> str:
        if self.parse_ok:
            return f"{self.uri} {self.distribution}"
        return self.raw_line.strip() or "(blank line)"

    @property
    def file_label(self) -> str:
        return os.path.basename(self.file_path)


def _parse_entry_line(content: str) -> tuple[str, str, str, str] | None:
    """Parse the active part of a deb/deb-src line, ignoring [options]."""
    try:
        tokens = shlex.split(content, comments=False)
    except ValueError:
        return None
    if not tokens or tokens[0] not in ("deb", "deb-src"):
        return None
    entry_type = tokens.pop(0)
    # Skip bracketed options like [arch=amd64 signed-by=...]
    tokens = [t for t in tokens if not (t.startswith("[") or t.endswith("]"))]
    if len(tokens) < 2:
        return None
    uri, distribution, *components = tokens
    return entry_type, uri, distribution, " ".join(components)


def _parse_line(file_path: str, line_number: int, raw_line: str) -> AptSource:
    stripped = raw_line.strip()
    enabled = True
    content = stripped
    if stripped.startswith("#"):
        enabled = False
        content = stripped.lstrip("#").strip()

    parsed = _parse_entry_line(content) if content else None
    if parsed:
        entry_type, uri, distribution, components = parsed
        return AptSource(
            file_path=file_path,
            line_number=line_number,
            raw_line=raw_line.rstrip("\n"),
            enabled=enabled,
            entry_type=entry_type,
            uri=uri,
            distribution=distribution,
            components=components,
            parse_ok=True,
        )
    return AptSource(
        file_path=file_path,
        line_number=line_number,
        raw_line=raw_line.rstrip("\n"),
        enabled=enabled,
        parse_ok=False,
    )


def _iter_list_files() -> list[str]:
    files = []
    if os.path.isfile(SOURCES_LIST):
        files.append(SOURCES_LIST)
    if os.path.isdir(SOURCES_LIST_D):
        files.extend(sorted(glob.glob(os.path.join(SOURCES_LIST_D, "*.list"))))
    return files


def list_sources() -> list[AptSource]:
    """Return every deb/deb-src entry (enabled or commented-out)."""
    sources: list[AptSource] = []
    for file_path in _iter_list_files():
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for i, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            source = _parse_line(file_path, i, raw_line)
            if source.parse_ok:
                sources.append(source)
            elif stripped.startswith("#") and _COMMENTED_DEB_RE.match(
                stripped.lstrip("#").strip()
            ):
                # Looks like a real commented-out "deb ..." line that our
                # tokenizer couldn't fully parse (e.g. odd quoting) — still
                # worth showing, just marked unrecognized.
                sources.append(source)
    return sources


def list_unsupported_deb822_files() -> list[str]:
    """.sources files present but not editable by this module."""
    if not os.path.isdir(SOURCES_LIST_D):
        return []
    return sorted(glob.glob(os.path.join(SOURCES_LIST_D, "*.sources")))


def _sed_toggle_script(source: AptSource, enable: bool) -> str:
    path = shlex.quote(source.file_path)
    n = source.line_number
    if enable:
        # Remove a single leading '#' plus following spaces, if present.
        expr = f"{n}s/^#[[:space:]]*//"
    else:
        expr = f"{n}s/^/#/"
    return f"sed -i '{expr}' {path}"


def build_toggle_command(source: AptSource, enable: bool) -> list[str]:
    """Comment/uncomment a single source line in place."""
    return ["bash", "-c", _sed_toggle_script(source, enable)]


def build_remove_command(source: AptSource) -> list[str]:
    """Delete a single source line from its file."""
    path = shlex.quote(source.file_path)
    script = f"sed -i '{source.line_number}d' {path}"
    return ["bash", "-c", script]


def build_add_line_command(entry_line: str, filename: str | None = None) -> list[str]:
    """Append a raw ``deb ...`` line to a managed file under sources.list.d."""
    safe_name = filename or MANAGED_FILE_NAME
    if not safe_name.endswith(".list"):
        safe_name += ".list"
    safe_name = os.path.basename(safe_name)  # no path traversal
    dest = os.path.join(SOURCES_LIST_D, safe_name)
    quoted_line = shlex.quote(entry_line.strip())
    quoted_dest = shlex.quote(dest)
    script = (
        f"mkdir -p {shlex.quote(SOURCES_LIST_D)} && echo {quoted_line} >> {quoted_dest}"
    )
    return ["bash", "-c", script]


def build_add_ppa_command(ppa: str) -> list[str] | None:
    """``ppa:user/name`` style repos, handled (incl. signing keys) by
    software-properties-common. Returns None if that tool is unavailable —
    the caller should tell the user to install it first."""
    import shutil

    if not shutil.which("add-apt-repository"):
        return None
    return ["add-apt-repository", "-y", ppa]


def looks_like_ppa(text: str) -> bool:
    return text.strip().startswith("ppa:")


def looks_like_deb_line(text: str) -> bool:
    return _parse_entry_line(text.strip()) is not None
