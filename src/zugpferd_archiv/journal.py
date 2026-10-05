"""Append-only canonical SHA-256 chain; not write-once storage."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .errors import ArchiveError
from .storage import append_line, canonical, read_lines


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


class Journal:
    def __init__(self, path: Path):
        self.path = path

    def verify(self) -> list[dict]:
        entries = read_lines(self.path)
        previous = '0' * 64
        for sequence, entry in enumerate(entries, 1):
            payload = {key: value for key, value in entry.items() if key != 'entry_hash'}
            digest = hashlib.sha256(canonical(payload)).hexdigest()
            if (entry.get('sequence') != sequence or entry.get('previous_hash') != previous
                    or entry.get('entry_hash') != digest or not isinstance(entry.get('data'), dict)
                    or not isinstance(entry.get('event'), str) or not isinstance(entry.get('timestamp'), str)):
                raise ArchiveError(f'Journal-Kette ungültig: {self.path}, Eintrag {sequence}')
            previous = digest
        return entries

    def append(self, event: str, data: dict) -> dict:
        entries = self.verify()
        entry = {'sequence': len(entries) + 1, 'timestamp': now(), 'event': event,
                 'data': data, 'previous_hash': entries[-1]['entry_hash'] if entries else '0' * 64}
        entry['entry_hash'] = hashlib.sha256(canonical(entry)).hexdigest()
        append_line(self.path, entry)
        return entry
