"""Neutral verified exports, retention proposals and isolated recovery."""

from __future__ import annotations

import csv
import html
import io
import json
import hashlib
from datetime import date
from pathlib import Path

from . import storage
from .errors import ArchiveError
from .journal import now
from .register import Register


def retention(invoice_date: str, document_type: str, hold: str = "") -> dict:
    year = date.fromisoformat(invoice_date).year
    years = {
        "Rechnung": 8,
        "Buchungsbeleg": 8,
        "Storno": 8,
        "Berichtigung": 8,
        "Gutschrift": 8,
        "Verfahrensdokumentation": 10,
        "Bücher": 10,
        "Geschäftsbrief": 6,
    }.get(document_type)
    return dict(
        years=years,
        keep_until=f"{min(year + years, 9999):04}-12-31" if years else None,
        hold=hold,
        basis="Fristvorschlag ab Jahresende; betrieblich prüfen, keine Löschung",
    )


def csv_cell(value) -> str:
    value = str(value if value is not None else "")
    return (
        "'" + value
        if value.lstrip().startswith(("=", "+", "-", "@"))
        or value.startswith(("\t", "\r", "\n"))
        else value
    )


def new_destination(root: Path, destination: Path) -> Path:
    destination = storage.safe_path(destination)
    if (
        destination.exists()
        or destination.is_relative_to(root)
        or root.is_relative_to(destination)
    ):
        raise ArchiveError(
            "Export/Wiederherstellung braucht neuen Ordner außerhalb des Archivs"
        )
    destination.mkdir(parents=True)
    return destination


def export_register(
    register: Register, destination: Path, first: str, last: str
) -> dict:
    date.fromisoformat(first)
    date.fromisoformat(last)
    if first > last:
        raise ArchiveError("Ungültiger Belegzeitraum")
    records = register.search(first=first, last=last)
    all_records = {r["id"]: r for r in register.records()}
    selected_ids = {r["id"] for r in records}
    for record in records:
        related = record.get("related_id")
        if related and related in all_records and related not in selected_ids:
            selected_ids.add(related)
            records.append(all_records[related] | {"included_as_related": True})
    destination = new_destination(register.root, destination)
    checksums = {}

    def write(name: str, content: bytes):
        target = storage.child(destination, name)
        storage.write_new(target, content)
        expected = hashlib.sha256(content).hexdigest()
        if storage.sha256(target) != expected:
            raise ArchiveError("Exportmetadaten-Rückleseprüfung fehlgeschlagen")
        checksums[name] = expected

    for record in records:
        files = [record["original_relative"]] + [
            item["path"] for item in record.get("related_files", [])
        ]
        for relative in files:
            source = storage.child(register.root, relative)
            name = "Originale/" + relative
            digest = storage.sha256(source)
            storage.verified_copy(source, storage.child(destination, name), digest)
            checksums[name] = digest
    write(
        "register.json",
        storage.canonical(
            dict(
                schema_version=1,
                first=first,
                last=last,
                date_filter="invoice_date",
                exported_at=now(),
                records=records,
            )
        ),
    )
    write(
        "register-events.jsonl",
        register.journal.path.read_bytes() if register.journal.path.exists() else b"",
    )
    keys = [
        "id",
        "direction",
        "number",
        "invoice_date",
        "partner",
        "currency",
        "net",
        "tax",
        "gross",
        "reference",
        "payment_reference",
        "status",
        "imported_at",
        "actor",
        "sha256",
        "original_relative",
    ]
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(keys)
    writer.writerows([csv_cell(record.get(key)) for key in keys] for record in records)
    write("register.csv", buffer.getvalue().encode("utf-8-sig"))
    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(record.get(key, '')))}</td>"
            for key in ("number", "invoice_date", "partner", "gross", "status")
        )
        + f'<td><a href="{html.escape("Originale/" + record["original_relative"], quote=True)}">Original</a></td></tr>'
        for record in records
    )
    write(
        "index.html",
        (
            "<!doctype html><meta charset=utf-8><title>Belegregister</title>"
            "<style>td,th{border:1px solid #aaa;padding:6px}table{border-collapse:collapse}@media print{a{color:black}}</style>"
            f"<h1>Belegregister {html.escape(first)} bis {html.escape(last)}</h1>"
            "<p>Filter: Rechnungsdatum. Originale unverändert. Neutraler Export, kein DATEV-Buchungsstapel.</p>"
            "<table><tr><th>Nummer</th><th>Datum</th><th>Partner</th><th>Brutto</th><th>Status</th><th>Datei</th></tr>"
            + rows
            + "</table>"
        ).encode(),
    )
    write(
        "FORMAT.md",
        b"# Registerformat 1\nJSON UTF-8; CSV UTF-8 BOM, semicolon, quoted cells. Amounts: decimal strings, never binary float. Date: ISO8601. Leading apostrophe protects formula-like CSV cells; JSON is lossless. SHA-256: lowercase hexadecimal. Events retain corrections and original actor/time.\n",
    )
    for folder in (
        "Archivverwaltung/Verfahrensdokumentation",
        "Archivverwaltung/Pruefberichte",
        "Archivverwaltung/Konfiguration",
    ):
        source_folder = storage.child(register.root, folder)
        if source_folder.exists():
            for source in source_folder.rglob("*"):
                if source.is_file():
                    relative = (
                        "Nachweise/" + source.relative_to(register.root).as_posix()
                    )
                    digest = storage.sha256(source)
                    storage.verified_copy(
                        source, storage.child(destination, relative), digest
                    )
                    checksums[relative] = digest
    for name, digest in checksums.items():
        if storage.sha256(storage.child(destination, name)) != digest:
            raise ArchiveError("Export-Rückleseprüfung fehlgeschlagen")
    storage.write_new(destination / "checksums.json", storage.canonical(checksums))
    if (
        json.loads((destination / "checksums.json").read_text(encoding="utf-8"))
        != checksums
    ):
        raise ArchiveError("Exportprüfsummen-Rückleseprüfung fehlgeschlagen")
    return dict(verified=True, count=len(records), destination=str(destination))


def restore_snapshot(
    snapshot: Path, destination: Path, expected_public_key: str | None = None
) -> dict:
    from .snapshots import verify_snapshot

    if destination.exists():
        raise ArchiveError("Wiederherstellung überschreibt keine vorhandenen Ordner")
    manifest = verify_snapshot(snapshot, expected_public_key)
    destination = new_destination(storage.safe_path(snapshot), destination)
    for item in manifest["files"]:
        storage.verified_copy(
            storage.child(snapshot, "Dateien/" + item["path"]),
            storage.child(destination, item["path"]),
            item["sha256"],
        )
    # Read-only inspection first; never bind restored copies to a live service automatically.
    storage.write_new(
        destination / "WIEDERHERSTELLUNG.json",
        storage.canonical(
            dict(
                restored_at=now(),
                snapshot=manifest["id"],
                mode="Prüfkopie; Admin-Einrichtung vor Livebetrieb erforderlich",
            )
        ),
    )
    if (destination / "Archivverwaltung/Register/events.jsonl").exists():
        Register(destination).records()
    return dict(verified=True, destination=str(destination), snapshot=manifest["id"])
