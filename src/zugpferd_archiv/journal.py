"""Append-only canonical SHA-256 chain; not write-once storage."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .errors import ArchiveError
from .storage import append_line, canonical, exclusive_lock, read_lines, safe_path


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Journal:
    # Pro-Prozess-Anker: (Größe, mtime_ns, Anzahl Einträge, letzter Hash).
    # Jede Größen-/Zeitstempelabweichung erzwingt eine vollständige Prüfung.
    _anchors: dict[str, tuple[int, int, int, str]] = {}

    def __init__(self, path: Path):
        self.path = path

    def _check_entry(self, entry: dict, sequence: int, previous: str) -> str:
        payload = {key: value for key, value in entry.items() if key != "entry_hash"}
        digest = hashlib.sha256(canonical(payload)).hexdigest()
        if (
            entry.get("sequence") != sequence
            or entry.get("previous_hash") != previous
            or entry.get("entry_hash") != digest
            or not isinstance(entry.get("data"), dict)
            or not isinstance(entry.get("event"), str)
            or not isinstance(entry.get("timestamp"), str)
        ):
            raise ArchiveError(
                f"Journal-Kette ungültig: {self.path}, Eintrag {sequence}"
            )
        return digest

    def verify(self) -> list[dict]:
        entries = read_lines(self.path)
        previous = "0" * 64
        for sequence, entry in enumerate(entries, 1):
            previous = self._check_entry(entry, sequence, previous)
        key = str(safe_path(self.path))
        if entries:
            info = self.path.stat()
            Journal._anchors[key] = (
                info.st_size,
                info.st_mtime_ns,
                len(entries),
                previous,
            )
        else:
            Journal._anchors.pop(key, None)
        return entries

    def _verified_state(self) -> tuple[int, str]:
        """Geprüfter Kettenstand; erst nach einer Größen- oder Zeitstempel-
        Abweichung wird die komplette Kette erneut verifiziert."""
        key = str(safe_path(self.path))
        if not self.path.exists():
            Journal._anchors.pop(key, None)
            return 0, "0" * 64
        info = self.path.stat()
        anchor = Journal._anchors.get(key)
        if anchor is not None and (info.st_size, info.st_mtime_ns) == anchor[:2]:
            return anchor[2], anchor[3]
        entries = read_lines(self.path)
        previous = "0" * 64
        for sequence, entry in enumerate(entries, 1):
            previous = self._check_entry(entry, sequence, previous)
        Journal._anchors[key] = (
            info.st_size,
            info.st_mtime_ns,
            len(entries),
            previous,
        )
        return len(entries), previous

    def append(self, event: str, data: dict) -> dict:
        safe_path(self.path.parent).mkdir(parents=True, exist_ok=True)
        with exclusive_lock(self.path.parent):
            count, previous = self._verified_state()
            entry = {
                "sequence": count + 1,
                "timestamp": now(),
                "event": event,
                "data": data,
                "previous_hash": previous,
            }
            entry["entry_hash"] = hashlib.sha256(canonical(entry)).hexdigest()
            append_line(self.path, entry)
            info = self.path.stat()
            Journal._anchors[str(safe_path(self.path))] = (
                info.st_size,
                info.st_mtime_ns,
                count + 1,
                entry["entry_hash"],
            )
            return entry
