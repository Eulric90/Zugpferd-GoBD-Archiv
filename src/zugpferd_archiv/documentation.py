"""Operator-authored procedure documentation with immutable, verified versions."""

from __future__ import annotations

import hashlib
import html
import json
import os
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from . import __version__, storage
from .errors import ArchiveError
from .journal import Journal, now
from .reports import Report

if TYPE_CHECKING:
    from .core import ArchiveService

FIELD_GROUPS = [
    (
        "Unternehmen und Zuständigkeiten",
        [
            ("organization", "Unternehmen / Organisation", True),
            ("address", "Anschrift", True),
            ("scope", "Geltungsbereich (Bereiche, Standorte, Rechnungsarten)", True),
            ("responsible", "Verantwortliche Person und Zuständigkeit", True),
            ("deputy", "Vertretung und Zuständigkeit", False),
            ("vat_id", "USt-ID / Steuernummer und steuerlicher Geltungsbereich", False),
            (
                "digital_start",
                "Digitaler Stichtag und Behandlung des Papieraltbestands",
                False,
            ),
        ],
    ),
    (
        "Belegablage und Aufbewahrung",
        [
            ("receipt_process", "Eingang: Herkunft, Erfassung und Zuordnung", True),
            ("outgoing_process", "Ausgang: Erstellung, Erfassung und Zuordnung", True),
            (
                "numbering",
                "PDF24-Nummernserie, Reservierung und Erklärung von Lücken",
                False,
            ),
            (
                "mail_process",
                "Portal/Thunderbird, Originalanhänge und Versandzuordnung",
                False,
            ),
            (
                "completeness_control",
                "Kontrolle auf Vollständigkeit und richtige Zuordnung",
                True,
            ),
            ("access_control", "Zugriffsrechte und Schutz vor Änderungen", True),
            (
                "retention_policy",
                "Aufbewahrungsfristen und deren betriebliche Umsetzung",
                True,
            ),
        ],
    ),
    (
        "Sicherung und Prüfung",
        [
            (
                "backup_schedule",
                "Sicherungsrhythmus, Zuständigkeit und Erfolgskontrolle",
                True,
            ),
            (
                "integrity_schedule",
                "Prüfrhythmus, Berichtsauswertung und externe Journalanker",
                True,
            ),
            (
                "location_a",
                "Physische Kennzeichnung, Aufbewahrung und Transport von A",
                True,
            ),
            (
                "location_b",
                "Physische Kennzeichnung, Aufbewahrung und Transport von B",
                True,
            ),
        ],
    ),
    (
        "Störungen, Änderungen und Export",
        [
            (
                "incident_process",
                "Verhalten bei Fehlern, Unterbrechungen und Wiederanlauf",
                True,
            ),
            (
                "change_process",
                "Klärung geänderter Quellen und Freigabe von Eingriffen",
                True,
            ),
            (
                "export_process",
                "Prüfexport: Zuständigkeit, Auswahl und sichere Weitergabe",
                True,
            ),
            ("change_note", "Änderungsgrund gegenüber der vorherigen Fassung", False),
            (
                "recovery_process",
                "Wiederherstellungsprobe, Dienstrechte und geschützte Schlüsselsicherung",
                False,
            ),
        ],
    ),
]
LOCAL_BASE = "Archivverwaltung/Verfahrensdokumentation/Fassungen"
MEDIA_BASE = "Verfahrensdokumentation/Fassungen"


@dataclass(frozen=True)
class DocumentationData:
    values: dict[str, str]
    valid_from: str = field(default_factory=lambda: date.today().isoformat())
    approved: bool = False
    approved_by: str = ""

    def validate(self) -> None:
        allowed = {key for _, fields in FIELD_GROUPS for key, _, _ in fields}
        if not isinstance(self.values, dict) or set(self.values) - allowed:
            raise ArchiveError("Ungültige Dokumentationsfelder")
        for _, fields in FIELD_GROUPS:
            for key, label, required in fields:
                value = self.values.get(key, "")
                if not isinstance(value, str) or len(value) > 5000 or "\x00" in value:
                    raise ArchiveError(
                        f"Ungültige Angabe: {label} (maximal 5000 Zeichen)"
                    )
                if required and not value.strip():
                    raise ArchiveError(f"Pflichtangabe fehlt: {label}")
        try:
            date.fromisoformat(self.valid_from)
        except (ValueError, TypeError) as exc:
            raise ArchiveError("Ungültiges Gültigkeitsdatum") from exc
        if (
            type(self.approved) is not bool
            or not isinstance(self.approved_by, str)
            or len(self.approved_by) > 500
        ):
            raise ArchiveError("Ungültige Freigabeangaben")
        if self.approved and not self.approved_by.strip():
            raise ArchiveError(
                "Für eine betriebliche Freigabe ist die freigebende Person erforderlich"
            )

    def normalized(self) -> dict:
        self.validate()
        return {
            "values": {
                key: self.values.get(key, "").strip()
                for _, fields in FIELD_GROUPS
                for key, _, _ in fields
            },
            "valid_from": self.valid_from,
            "approved": self.approved,
            "approved_by": self.approved_by.strip() if self.approved else "",
        }


def answers_from(record: dict) -> DocumentationData:
    return DocumentationData(
        record["answers"],
        record["valid_from"],
        record["status"] == "Betrieblich freigegeben",
        record["approved_by"],
    )


def context(service: ArchiveService, a: Path, b: Path) -> dict:
    config = service.configuration()
    return {
        "software_version": __version__,
        "root": str(service.root),
        "archive_id": config["archive_id"],
        "media": {
            role: {**config[role], "path_at_creation": str(storage.safe_path(path))}
            for role, path in (("A", a), ("B", b))
        },
        "last_backup": service.last_backup(),
        "date_filter": "Archivierungsdatum in UTC; kein Rechnungsdatum",
    }


def new_record(
    data: DocumentationData, ctx: dict, version: int, document_id: str | None = None
) -> dict:
    normalized = data.normalized()
    return {
        "schema_version": 1,
        "document_id": document_id or str(uuid4()),
        "version": version,
        "created_at": now(),
        "valid_from": normalized["valid_from"],
        "status": "Betrieblich freigegeben" if normalized["approved"] else "Entwurf",
        "approved_by": normalized["approved_by"],
        "answers": normalized["values"],
        "context": ctx,
    }


def sections(record: dict) -> list[tuple[str, list[tuple[str, str]]]]:
    ctx = record["context"]
    result = [
        (
            "Fassung und Status",
            [
                ("Fassung", str(record["version"])),
                ("Dokument-ID", record["document_id"]),
                ("Erstellt (UTC)", record["created_at"]),
                ("Gültig ab", record["valid_from"]),
                ("Status", record["status"]),
                (
                    "Freigabe durch",
                    record["approved_by"] or "Noch nicht betrieblich freigegeben",
                ),
            ],
        )
    ]
    result.extend(
        (
            title,
            [
                (label, record["answers"].get(key, "") or "Nicht angegeben")
                for key, label, _ in fields
            ],
        )
        for title, fields in FIELD_GROUPS
    )
    technical = [
        ("Softwareversion", ctx["software_version"]),
        ("Arbeitsablage", ctx["root"]),
        ("Archiv-ID", ctx["archive_id"]),
    ]
    for role in ("A", "B"):
        medium = ctx["media"][role]
        technical.extend(
            [
                (f"Medium {role}: UUID", medium["medium_uuid"]),
                (
                    f"Medium {role}: Volume-Kennung",
                    medium.get("volume_id") or "Nicht verfügbar",
                ),
                (
                    f"Medium {role}: Pfad zum Erstellzeitpunkt",
                    medium["path_at_creation"],
                ),
            ]
        )
    last = ctx.get("last_backup")
    technical.append(
        (
            "Letzter Sicherungslauf zum Erstellzeitpunkt",
            f"{last['timestamp']} – {'erfolgreich' if last['success'] else 'fehlgeschlagen'}"
            if last
            else "Noch kein Sicherungslauf bekannt",
        )
    )
    technical.extend(
        [
            (
                "Arbeitsstruktur",
                "Eingang/<Jahr>/ und Ausgang/<Jahr>/; Verwaltung unter Archivverwaltung/. "
                "Alle regulären Dateien werden unverändert übernommen. Es erfolgt keine Rechnungsvalidierung oder Konvertierung.",
            ),
            (
                "Archivstruktur",
                "Archive/<Jahr>/Eingang/... bzw. Ausgang/...; Manifest/, Journal/, "
                "Pruefberichte/ und Verfahrensdokumentation/. Ursprüngliche relative Pfade verhindern Namenskollisionen.",
            ),
            (
                "Sicherungsablauf",
                "Quelle und Metadaten erfassen, SHA-256 berechnen; vorhandene Ziele prüfen; "
                "temporär auf A und B kopieren; flush/close; jedes Ziel vom jeweiligen Medium zurücklesen und SHA-256 "
                "prüfen; ohne Überschreiben veröffentlichen; Metadaten und verkettetes Journal anhängen. "
                "Erfolg erst nach Verifikation beider Medien. Identische Archivobjekte werden nicht neu geschrieben.",
            ),
            (
                "Metadaten und Journal",
                "Originalname, relativer Quellpfad, Zielpfad, Größe, Quell-mtime/ctime "
                "in Nanosekunden, UTC-Archivierungszeit und SHA-256. Journal: canonical JSON (UTF-8, sortierte Schlüssel), "
                "Sequenz, Zeitpunkt, Ereignis, Daten, Vorgängerhash und Eintragshash.",
            ),
            (
                "Integrität und Konflikte",
                "Vollprüfung und A/B-Vergleich prüfen Medienkennungen, Objekte, SHA-256, "
                "Manifest und Journal. Fehlende, veränderte oder widersprüchliche Originale werden nicht still repariert. "
                "Geänderte Quellen werden abgelehnt; die Historie bleibt erhalten. V1 hat keine Archivlöschfunktion.",
            ),
            (
                "Unterbrechung und Wiederanlauf",
                "Temporäre .partial-<UUID>-Dateien bleiben erkennbare Belege und sind "
                "keine Originale. Sperrdateien nach einem Absturz nur nach dokumentierter manueller Prüfung entfernen. "
                "Ein Widerspruch zwischen Manifest und Journal blockiert weitere Schreibvorgänge. "
                "Originale, Manifest und Journal nicht zur Fehlerbehebung löschen oder bearbeiten.",
            ),
            (
                "Export",
                "Ein Export kopiert ausgewählte Originale mit Index/Manifest und Prüfbericht in einen neuen "
                "Ordner. Jahresfilter beziehen sich auf die Quellablage, Datumsfilter auf UTC-Archivierungszeitpunkte. "
                "Quellen und Archivobjekte werden weder verschoben noch gelöscht.",
            ),
            (
                "Dokumentationsfassungen",
                "Diese Fassung liegt als Markdown, druckbare HTML-Datei und JSON "
                "mit SHA-256-Prüfsummen vor. Neue Fassungen ersetzen alte nicht. Kopien auf beiden zugeordneten "
                "Medien werden zurückgelesen und geprüft; Speicherung wird im Journal protokolliert.",
            ),
            (
                "Sicherheitsgrenzen",
                "Eine SHA-256-Hash-Kette ist manipulationsanzeigend, kein WORM-Speicher, "
                "keine Codesignatur und kein qualifizierter Zeitstempel. Konsistentes Neuschreiben aller Daten oder "
                "Kürzen von Journal und Manifest ist ohne unabhängige externe Anker nicht sicher erkennbar. "
                "Sperren koordinieren die Anwendung, nicht beliebige Fremdsoftware. Rechte, Medienaufbewahrung "
                "und regelmäßige dokumentierte Prüfungen müssen betrieblich umgesetzt werden.",
            ),
            (
                "Hinweis",
                "GoBD-unterstützende Archivierung. Die Software allein garantiert keine GoBD-Konformität. "
                "Die betrieblichen Angaben stammen vom Betreiber und müssen in der Praxis umgesetzt sowie geprüft werden. "
                "Der Status „Betrieblich freigegeben“ dokumentiert dessen Eingabe, keine rechtliche Zertifizierung.",
            ),
        ]
    )
    result.append(("Automatisch ergänzte technische Beschreibung", technical))
    return result


def render_html(record: dict) -> str:
    blocks = [
        '<!doctype html><html lang="de"><meta charset="utf-8">',
        "<title>Verfahrensdokumentation</title><style>body{font:15px/1.5 sans-serif;max-width:900px;"
        "margin:40px auto;padding:0 20px}h2{break-after:avoid}dt{font-weight:bold;margin-top:12px}"
        "dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}@media print{body{margin:0;max-width:none}"
        "h2{margin-top:20px}dt,dd{break-inside:avoid}}</style><body><h1>Verfahrensdokumentation</h1>",
    ]
    for title, fields in sections(record):
        blocks.append(f"<h2>{html.escape(title)}</h2><dl>")
        blocks.extend(
            f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>"
            for label, value in fields
        )
        blocks.append("</dl>")
    return "".join(blocks) + "</body></html>\n"


def render_bundle(record: dict) -> dict[str, bytes]:
    markdown = ["# Verfahrensdokumentation", ""]
    for title, fields in sections(record):
        markdown.extend([f"## {title}", ""])
        for label, value in fields:
            markdown.extend(
                [f"### {label}", "", *(f"> {line}" for line in value.splitlines()), ""]
            )
    return {
        "document.json": storage.canonical(record) + b"\n",
        "Verfahrensdokumentation.md": ("\n".join(markdown) + "\n").encode("utf-8"),
        "Verfahrensdokumentation.html": render_html(record).encode("utf-8"),
    }


def bundle_with_checksums(record: dict) -> dict[str, bytes]:
    bundle = render_bundle(record)
    index = {
        "document_id": record["document_id"],
        "files": [
            {
                "filename": name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
            for name, data in bundle.items()
        ],
    }
    return {**bundle, "checksums.json": storage.canonical(index) + b"\n"}


def load_latest(root: Path, include_pending: bool = False) -> dict | None:
    base = storage.child(root, LOCAL_BASE)
    if not base.exists():
        return None
    versions = []
    for folder in base.iterdir():
        storage.safe_path(folder)
        if not folder.is_dir():
            raise ArchiveError(
                f"Unerwarteter Inhalt in Dokumentationsfassungen: {folder}"
            )
        try:
            record = json.loads(
                storage.safe_path(folder / "document.json").read_text(encoding="utf-8")
            )
            if (
                record["schema_version"] != 1
                or record["document_id"] != folder.name
                or type(record["version"]) is not int
            ):
                raise ValueError("identity/schema")
            UUID(record["document_id"])
            answers_from(record).validate()
            expected = bundle_with_checksums(record)
            complete = storage.safe_path(folder / "completion.json").is_file()
            for name, data in expected.items():
                path = storage.safe_path(folder / name)
                if path.exists():
                    if storage.sha256(path) != hashlib.sha256(data).hexdigest():
                        raise ArchiveError(f"Lokale Dokumentation verändert: {path}")
                elif complete:
                    raise ArchiveError(f"Lokale Dokumentationsdatei fehlt: {path}")
            if complete:
                completion = json.loads(
                    (folder / "completion.json").read_text(encoding="utf-8")
                )
                if completion != event_data(record, expected):
                    raise ArchiveError(
                        "Lokaler Dokumentationsabschluss widerspricht den Dateien"
                    )
            if complete or include_pending:
                versions.append({**record, "completed": complete})
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ArchiveError(f"Dokumentationsfassung unlesbar: {folder}") from exc
    return max(versions, key=lambda r: r["version"]) if versions else None


def event_data(record: dict, bundle: dict[str, bytes]) -> dict:
    return {
        "document_id": record["document_id"],
        "version": record["version"],
        "archive_id": record["context"]["archive_id"],
        "status": record["status"],
        "files": [
            {
                "path": f"{MEDIA_BASE}/{record['document_id']}/{name}",
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
            for name, data in bundle.items()
        ],
    }


def documentation_events(medium: Path, report: Report) -> dict[str, dict]:
    events = {}
    for row in Journal(storage.child(medium, "Journal/events.jsonl")).verify():
        if row["event"] != "documentation_saved":
            continue
        entry = row["data"]
        try:
            identity = entry["document_id"]
            UUID(identity)
            if identity in events or not entry["files"]:
                raise ValueError("duplicate/empty")
            for item in entry["files"]:
                if not item["path"].startswith(f"{MEDIA_BASE}/{identity}/"):
                    raise ValueError("path")
                path = storage.child(medium, item["path"])
                if not path.is_file():
                    report.issue(
                        "missing",
                        path,
                        "Dokumentationsdatei fehlt; keine stille Reparatur",
                    )
                elif (
                    storage.sha256(path) != item["sha256"]
                    or path.stat().st_size != item["size"]
                ):
                    report.issue(
                        "changed",
                        path,
                        "Dokumentationsdatei entspricht nicht dem Journal",
                    )
                else:
                    report.totals["valid"] += 1
            events[identity] = entry
        except (ValueError, KeyError, TypeError) as exc:
            raise ArchiveError("Ungültiger Dokumentationseintrag im Journal") from exc
    return events


def audit_documentations(
    a: Path,
    b: Path,
    report: Report,
    resume_id: str | None = None,
    allow_temporaries: bool = False,
) -> tuple[dict, dict]:
    da, db = documentation_events(a, report), documentation_events(b, report)
    for medium, events in ((a, da), (b, db)):
        expected = {
            item["path"] for entry in events.values() for item in entry["files"]
        }
        folder = storage.child(medium, MEDIA_BASE)
        for current, directories, files in os.walk(folder, followlinks=False):
            for name in directories:
                storage.safe_path(Path(current) / name)
            for name in files:
                path = storage.safe_path(Path(current) / name)
                relative = path.relative_to(storage.safe_path(medium)).as_posix()
                if ".partial-" in name:
                    if allow_temporaries:
                        if not any(w["path"] == str(path) for w in report.warnings):
                            report.warnings.append(
                                {
                                    "kind": "interrupted",
                                    "path": str(path),
                                    "detail": "Temporäre Dokumentationskopie erhalten; manuell prüfen",
                                }
                            )
                    else:
                        report.issue(
                            "interrupted",
                            path,
                            "Temporäre Dokumentationskopie, keine abgeschlossene Fassung",
                        )
                elif relative not in expected and not (
                    resume_id and relative.startswith(f"{MEDIA_BASE}/{resume_id}/")
                ):
                    report.issue(
                        "unexpected", path, "Dokumentationsdatei ohne Journalabschluss"
                    )
    for identity in da.keys() | db.keys():
        if identity not in da or identity not in db:
            if identity != resume_id:
                report.issue(
                    "conflicting",
                    identity,
                    "Dokumentation nur auf einem Medium abgeschlossen",
                )
        elif da[identity] != db[identity]:
            report.issue(
                "conflicting",
                identity,
                "Dokumentationsfassungen auf A und B widersprechen sich",
            )
    return da, db


def audit_local_documentation(root: Path, report: Report) -> None:
    latest = load_latest(root, include_pending=True)
    if latest and not latest["completed"]:
        report.issue(
            "documentation_pending",
            latest["document_id"],
            "Dokumentationsfassung noch nicht vollständig lokal und auf A/B gespeichert; Assistent erneut öffnen",
        )


def _write_once(path: Path, content: bytes) -> None:
    expected = hashlib.sha256(content).hexdigest()
    if path.exists():
        if storage.sha256(path) != expected:
            raise ArchiveError(f"Zielkonflikt in Dokumentation: {path}")
    else:
        storage.write_new(path, content)
    if storage.sha256(path) != expected:
        raise ArchiveError(f"Rückleseprüfung der Dokumentation fehlgeschlagen: {path}")


def save_documentation(
    service: ArchiveService, a: Path, b: Path, data: DocumentationData
) -> Report:
    report = Report("documentation")
    service.setup()
    try:
        data.validate()
        service._pair(a, b, report)
        with ExitStack() as stack:
            service._locks(a, b, stack)
            service._pair(a, b, report)
            latest = load_latest(service.root, include_pending=True)
            pending = latest if latest and not latest["completed"] else None
            if pending:
                if answers_from(pending).normalized() != data.normalized():
                    raise ArchiveError(
                        "Ausstehende Fassung zuerst mit unveränderten Angaben erneut speichern"
                    )
                if pending["context"]["archive_id"] != report.archive_id:
                    raise ArchiveError(
                        "Ausstehende Fassung gehört zu einem anderen Archiv"
                    )
                record = {
                    key: value for key, value in pending.items() if key != "completed"
                }
            else:
                record = new_record(
                    data, context(service, a, b), latest["version"] + 1 if latest else 1
                )
            # Existing invoice history and documentation must be intact before writes.
            ra, rb = service.records(a), service.records(b)
            service._inspect(a, ra, report)
            service._inspect(b, rb, report)
            service._compare_records(ra, rb, report)
            da, db = audit_documentations(
                a,
                b,
                report,
                record["document_id"] if pending else None,
                allow_temporaries=True,
            )
            if report.exceptions:
                return service._finish(report)
            bundle = bundle_with_checksums(record)
            local = storage.child(service.root, f"{LOCAL_BASE}/{record['document_id']}")
            for name, content_bytes in bundle.items():
                _write_once(storage.child(local, name), content_bytes)
            report.outputs = [
                str(local / name) for name in bundle if name != "checksums.json"
            ]
            event = event_data(record, bundle)
            report.totals["candidates"] = len(bundle)
            for medium, events in ((a, da), (b, db)):
                for name, content_bytes in bundle.items():
                    service._pair(a, b, report)
                    source = storage.child(local, name)
                    target = storage.child(
                        medium, f"{MEDIA_BASE}/{record['document_id']}/{name}"
                    )
                    service.progress(
                        f"Dokumentationsfassung {record['version']}: {target}"
                    )
                    copied = storage.verified_copy(
                        source, target, hashlib.sha256(content_bytes).hexdigest()
                    )
                    report.totals["verified"] += 1
                    report.totals["copied" if copied else "already_archived"] += 1
                service._pair(a, b, report)
                if record["document_id"] in events:
                    if events[record["document_id"]] != event:
                        raise ArchiveError(
                            "Vorhandener Dokumentations-Journaleintrag widerspricht der Fassung"
                        )
                else:
                    Journal(storage.child(medium, "Journal/events.jsonl")).append(
                        "documentation_saved", event
                    )
            audit_documentations(a, b, report, allow_temporaries=True)
            service._pair(a, b, report)
            if not report.exceptions:
                _write_once(local / "completion.json", storage.canonical(event) + b"\n")
            return service._finish(report, a, b)
    except (ArchiveError, OSError) as exc:
        report.issue("error", "", str(exc))
        return service._finish(report)
