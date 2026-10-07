"""Durable filesystem primitives. No invoice replacement or deletion."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator
from uuid import uuid4

from .errors import ArchiveError


def canonical(data: object) -> bytes:
    return json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def safe_path(path: Path) -> Path:
    """Reject symlinks and Windows reparse points in every existing component."""
    path = Path(os.path.abspath(path))
    for component in (*reversed(path.parents), path):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ArchiveError(f"Unsicherer Link/Reparse-Punkt: {component}")
    return path


def child(root: Path, relative: str) -> Path:
    from pathlib import PurePosixPath

    parts = PurePosixPath(relative).parts
    if (
        not parts
        or PurePosixPath(relative).is_absolute()
        or any(
            part in (".", "..")
            or any(char in part for char in '\\:<>"|?*')
            or any(ord(char) < 32 for char in part)
            or part.endswith((".", " "))
            or re.fullmatch(
                r"(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?",
                part,
                re.IGNORECASE,
            )
            for part in parts
        )
    ):
        raise ArchiveError(f"Ungültiger relativer Pfad: {relative}")
    target = safe_path(root.joinpath(*parts))
    if not target.is_relative_to(safe_path(root)):
        raise ArchiveError("Pfad außerhalb des Archivs")
    return target


def sha256(path: Path) -> str:
    safe_path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _flush_volume_windows(path: Path) -> None:
    import ctypes

    GENERIC_WRITE = 0x40000000
    OPEN_EXISTING = 3
    handle = ctypes.windll.kernel32.CreateFileW(
        "\\\\.\\" + os.path.abspath(path).split("\\", 1)[0],
        GENERIC_WRITE,
        0,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if handle == -1:
        raise ctypes.WinError()
    try:
        if not ctypes.windll.kernel32.FlushFileBuffers(handle):
            raise ctypes.WinError()
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def sync_directory(path: Path) -> None:
    if os.name == "nt":
        _flush_volume_windows(path)
        return
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_new(path: Path, data: bytes) -> None:
    safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def append_line(path: Path, data: dict) -> None:
    safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        stream.write(canonical(data) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def read_lines(path: Path) -> list[dict]:
    safe_path(path)
    if not path.exists():
        return []
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ArchiveError(f"Unterbrochene Metadaten: {path}")
    try:
        rows = [json.loads(line) for line in raw.splitlines()]
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError("not an object")
        return rows
    except (ValueError, UnicodeError) as exc:
        raise ArchiveError(f"Beschädigte Metadaten: {path}") from exc


def copy_stream(source: Path, target: BinaryIO) -> None:
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            target.write(block)


def publish_new(temp: Path, destination: Path) -> None:
    # Windows rename refuses existing targets (including FAT/exFAT). POSIX rename
    # replaces targets, so use an atomic no-replace hard link on POSIX instead.
    safe_path(destination)
    if os.name == "nt":
        os.rename(temp, destination)
    else:
        os.link(temp, destination)
        temp.unlink()  # Only our verified temporary hard link, never an original.
    sync_directory(destination.parent)


def verified_copy(source: Path, destination: Path, expected: str) -> bool:
    safe_path(source)
    safe_path(destination)
    if destination.exists():
        if not destination.is_file() or sha256(destination) != expected:
            raise ArchiveError(f"Zielkonflikt: {destination}")
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".partial-" + str(uuid4()))
    with temp.open("xb") as stream:
        copy_stream(source, stream)
        stream.flush()
        os.fsync(stream.fileno())
    if sha256(temp) != expected:
        raise ArchiveError(f"Hash-Abweichung beim Zurücklesen: {temp}")
    if sha256(source) != expected:
        raise ArchiveError(f"Quelle während Kopie verändert: {source}")
    publish_new(temp, destination)
    if sha256(destination) != expected:
        raise ArchiveError(f"Hash-Abweichung am endgültigen Ziel: {destination}")
    return True


def _process_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _remove_stale_lock(path: Path) -> None:
    pid = None
    try:
        rows = read_lines(path)
        if rows and isinstance(rows[-1].get("pid"), int):
            pid = rows[-1]["pid"]
    except Exception:
        pid = None
    if pid is None or _process_alive(pid):
        raise ArchiveError(
            f"Medium/Arbeitsordner gesperrt: {path}. Nach Absturz manuell prüfen."
        )
    path.unlink()


@contextmanager
def exclusive_lock(root: Path) -> Iterator[None]:
    path = safe_path(root / ".zugpferd-operation.lock")
    try:
        write_new(path, canonical({"pid": os.getpid(), "operation": str(uuid4())}))
    except FileExistsError:
        _remove_stale_lock(path)
        try:
            write_new(path, canonical({"pid": os.getpid(), "operation": str(uuid4())}))
        except FileExistsError as exc:
            raise ArchiveError(
                f"Medium/Arbeitsordner gesperrt: {path}. Nach Absturz manuell prüfen."
            ) from exc
    try:
        yield
    finally:
        path.unlink()  # Our operation lock, never an invoice.
        sync_directory(root)
