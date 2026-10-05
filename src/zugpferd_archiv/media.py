"""Portable markers and mockable Windows removable-volume discovery."""

from __future__ import annotations

import ctypes
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID, uuid4

from .errors import ArchiveError
from .journal import Journal, now
from .storage import canonical, exclusive_lock, safe_path, write_new

MARKER = ".zugpferd-medium.json"


@dataclass(frozen=True)
class Medium:
    schema_version: int
    archive_id: str
    role: str
    medium_uuid: str
    created_at: str
    volume_id: str | None = None


@dataclass(frozen=True)
class Drive:
    root: Path
    label: str
    volume_id: str


def volume_id(root: Path) -> str | None:
    if os.name != "nt":
        return None
    from ctypes import wintypes

    serial = wintypes.DWORD()
    label = ctypes.create_unicode_buffer(261)
    fs = ctypes.create_unicode_buffer(261)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    if not kernel.GetVolumeInformationW(
        str(root.anchor),
        label,
        len(label),
        ctypes.byref(serial),
        None,
        None,
        fs,
        len(fs),
    ):
        raise ArchiveError(f"Windows-Medium nicht lesbar: {root}")
    # Serial and filesystem persist when Windows assigns a different drive letter.
    # The archive/medium UUIDs remain the principal logical identity.
    return f"{serial.value:08x}:{fs.value}"


def discover() -> list[Drive]:
    if os.name != "nt":
        return []
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    mask = kernel.GetLogicalDrives()
    result = []
    for index in range(26):
        if mask & (1 << index):
            root = Path(f"{chr(65 + index)}:\\")
            # Removable USB and USB disks exposed as fixed volumes are supported.
            if kernel.GetDriveTypeW(str(root)) in (2, 3):
                try:
                    result.append(Drive(root, str(root), volume_id(root) or ""))
                except ArchiveError:
                    continue
    return result


def read_marker(root: Path) -> Medium:
    safe_path(root)
    if not root.is_dir():
        raise ArchiveError(f"Medium fehlt: {root}")
    try:
        path = safe_path(root / MARKER)
        medium = Medium(**json.loads(path.read_text(encoding="utf-8")))
        UUID(medium.archive_id)
        UUID(medium.medium_uuid)
        if medium.schema_version != 1 or medium.role not in ("A", "B"):
            raise ValueError("schema/role")
        if volume_id(root) != medium.volume_id:
            raise ValueError("volume identity changed")
        return medium
    except (OSError, ValueError, TypeError) as exc:
        raise ArchiveError(f"Ungültige/fehlende Medienkennung: {root}: {exc}") from exc


def register(root: Path, role: str, archive_id: str | None = None) -> Medium:
    root = safe_path(root)
    if not root.is_dir() or role not in ("A", "B"):
        raise ArchiveError("Vorhandenes Medium und Rolle A/B erforderlich")
    if (root / MARKER).exists():
        raise ArchiveError(
            "Medium bereits registriert; Kennung wird nicht überschrieben"
        )
    if any((root / name).exists() for name in ("Archive", "Manifest", "Journal")):
        raise ArchiveError(
            "Vorhandene Archivstruktur ohne Kennung; Registrierung abgebrochen"
        )
    identity = archive_id or str(uuid4())
    UUID(identity)
    medium = Medium(1, identity, role, str(uuid4()), now(), volume_id(root))
    with exclusive_lock(root):
        write_new(root / MARKER, canonical(asdict(medium)) + b"\n")
        for folder in (
            "Archive",
            "Manifest",
            "Journal",
            "Pruefberichte",
            "Verfahrensdokumentation",
        ):
            safe_path(root / folder).mkdir(exist_ok=True)
        write_new(root / "Manifest/records.jsonl", b"")
        Journal(root / "Journal/events.jsonl").append("registered", asdict(medium))
        write_new(
            root / "Verfahrensdokumentation/HINWEISE.txt",
            (
                "GoBD-unterstützende Archivierung\nDie Software allein garantiert keine GoBD-Konformität.\n"
                "Das SHA-256-Journal ist manipulationsanzeigend, kein WORM-/Schreibschutz.\n"
                "Verantwortlichkeiten, Aufbewahrungsfristen, Zugriffsrechte und Prüfabläufe "
                "müssen betrieblich dokumentiert werden.\n"
            ).encode("utf-8"),
        )
    return medium


def validate_pair(
    a: Path, b: Path, expected_a: Medium, expected_b: Medium
) -> tuple[Medium, Medium]:
    ma, mb = read_marker(a), read_marker(b)
    if ma != expected_a or mb != expected_b:
        raise ArchiveError(
            "Unerwartetes Medium: Kennung stimmt nicht mit Konfiguration überein"
        )
    if (
        ma.role != "A"
        or mb.role != "B"
        or ma.archive_id != mb.archive_id
        or ma.medium_uuid == mb.medium_uuid
        or a.resolve() == b.resolve()
        or (ma.volume_id is not None and ma.volume_id == mb.volume_id)
    ):
        raise ArchiveError("A/B müssen verschiedene Medien desselben Archivs sein")
    if a.resolve().is_relative_to(b.resolve()) or b.resolve().is_relative_to(
        a.resolve()
    ):
        raise ArchiveError("Verschachtelte Medien sind unzulässig")
    return ma, mb
