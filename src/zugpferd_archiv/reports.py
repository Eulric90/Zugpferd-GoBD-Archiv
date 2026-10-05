"""Portable machine-readable and human-readable operation reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4

from .journal import now
from . import storage
from .storage import canonical


@dataclass
class Report:
    operation: str
    archive_id: str = ""
    medium_ids: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=now)
    success: bool = False
    totals: dict[str, int] = field(
        default_factory=lambda: {
            "candidates": 0,
            "verified": 0,
            "copied": 0,
            "already_archived": 0,
            "valid": 0,
            "missing": 0,
            "changed": 0,
            "unexpected": 0,
            "conflicting": 0,
            "interrupted": 0,
        }
    )
    exceptions: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)
    report_json: Path | None = None
    report_text: Path | None = None

    def issue(self, kind: str, path: object, detail: str) -> None:
        self.exceptions.append({"kind": kind, "path": str(path), "detail": detail})
        self.totals[kind] = self.totals.get(kind, 0) + 1

    def data(self) -> dict:
        value = asdict(self)
        value.pop("report_json")
        value.pop("report_text")
        return value

    def text(self) -> str:
        lines = [
            "GoBD-unterstützende Archivierung",
            f"Vorgang: {self.operation}",
            f"Zeitpunkt (UTC): {self.timestamp}",
            f"Archiv: {self.archive_id}",
            f"Medien: {self.medium_ids}",
            "Ergebnis: "
            + ("ERFOLGREICH" if self.success else "FEHLER / UNVOLLSTÄNDIG"),
            "",
            *(f"{key}: {value}" for key, value in self.totals.items()),
            "",
            *(
                f"{item['kind']}: {item['path']} – {item['detail']}"
                for item in self.exceptions
            ),
            *(
                f"WARNUNG {item['kind']}: {item['path']} – {item['detail']}"
                for item in self.warnings
            ),
            "",
            "Die Software allein garantiert keine GoBD-Konformität.",
            "Eine Hash-Kette ist kein unveränderlicher Schreibschutz.",
        ]
        return "\n".join(lines) + "\n"

    def save(self, folder: Path) -> None:
        stem = f"{self.operation}-{self.timestamp.replace(':', '-')}-{uuid4()}"
        self.report_json = folder / f"{stem}.json"
        self.report_text = folder / f"{stem}.txt"
        storage.write_new(self.report_json, canonical(self.data()) + b"\n")
        storage.write_new(self.report_text, self.text().encode("utf-8"))
