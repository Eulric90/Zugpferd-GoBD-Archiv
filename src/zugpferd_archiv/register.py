"""Immutable originals and replayable, append-oriented business records."""

from __future__ import annotations

import os
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .errors import ArchiveError
from .journal import Journal, now
from . import storage


def actor_identity() -> str:
    if os.name == "nt":
        import subprocess

        import csv

        result = subprocess.run(
            ["whoami", "/user", "/fo", "csv", "/nh"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
            creationflags=0x08000000,
        )
        return next(csv.reader([result.stdout.strip()]))[1]
    return f"local-uid:{os.getuid()}"


def amount(value: str) -> Decimal:
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result.as_tuple().exponent < -8:
            raise ValueError()
        return result
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ArchiveError("Ungültiger Dezimalbetrag") from exc


class Register:
    def __new__(cls, root: Path, actor=None):
        from .service import protected, RemoteRegister

        if protected(root):
            return RemoteRegister(root, actor)
        return super().__new__(cls)

    def __init__(self, root: Path, actor: str | None = None):
        self.root = storage.safe_path(root)
        self.actor = actor or actor_identity()
        self.folder = storage.child(self.root, "Archivverwaltung/Register")
        self.folder.mkdir(parents=True, exist_ok=True)
        self.journal = Journal(self.folder / "events.jsonl")

    def events(self) -> list[dict]:
        return self.journal.verify()

    def save_setup(self, values: dict) -> dict:
        required = (
            "organization",
            "address",
            "vat_id",
            "responsible",
            "deputy",
            "digital_start",
        )
        if any(not str(values.get(key, "")).strip() for key in required):
            raise ArchiveError(
                "Betriebseinrichtung braucht Unternehmen, Zuständigkeiten und digitalen Stichtag"
            )
        date.fromisoformat(values["digital_start"])
        with storage.exclusive_lock(self.root):
            record = dict(
                id=str(uuid.uuid4()), values=values, created_at=now(), actor=self.actor
            )
            target = storage.child(
                self.root, f"Archivverwaltung/Konfiguration/Betrieb-{record['id']}.json"
            )
            storage.write_new(target, storage.canonical(record))
            self._append("business_setup", record)
            return record

    def business_setup(self) -> dict | None:
        entries = [e["data"] for e in self.events() if e["event"] == "business_setup"]
        return entries[-1] if entries else None

    def _append(self, event: str, data: dict) -> None:
        self.journal.append(event, data | {"actor": self.actor})

    def series(self, year: int) -> dict:
        state = None
        for entry in self.events():
            data = entry["data"]
            if data.get("year") == year:
                if entry["event"] == "series_started":
                    state = dict(data)
                elif entry["event"] == "number_reserved" and state:
                    state["last"] = max(state["last"], data["sequence"])
        if state is None:
            raise ArchiveError(
                "Jahresserie zuerst mit bisherigem Nummernstand bestätigen"
            )
        return state

    def start_series(self, year: int, separator: str, last: int, reason: str) -> None:
        if not (
            1 <= year <= 9999
            and separator in ("", "-", "/", ".")
            and type(last) is int
            and 0 <= last <= 9999
            and reason.strip()
        ):
            raise ArchiveError("Ungültige Jahresserie oder fehlende Begründung")
        with storage.exclusive_lock(self.root):
            if any(
                e["event"] == "series_started" and e["data"]["year"] == year
                for e in self.events()
            ):
                raise ArchiveError("Jahresserie bereits eingerichtet")
            self._append(
                "series_started",
                dict(year=year, separator=separator, last=last, reason=reason),
            )

    def reserve(self, year: int, reason: str = "Neue Rechnung in PDF24") -> str:
        with storage.exclusive_lock(self.root):
            state = self.series(year)
            sequence = state["last"] + 1
            if sequence > 9999:
                raise ArchiveError("Nummernserie bei 9999 ausgeschöpft")
            number = f"{year:04}{state['separator']}{sequence:04}"
            self._append(
                "number_reserved",
                dict(year=year, sequence=sequence, number=number, reason=reason),
            )
            return number

    def records(self) -> list[dict]:
        records = {}
        for entry in self.events():
            data = entry["data"]
            if entry["event"] == "invoice_imported":
                record = dict(data["record"])
                if record["id"] in records:
                    raise ArchiveError("Doppelter Register-Commit")
                records[record["id"]] = record
            elif entry["event"] in ("metadata_corrected", "sent", "status_changed"):
                record = records[data["id"]]
                if any(record.get(k) != v for k, v in data["before"].items()):
                    raise ArchiveError("Registerkorrektur widerspricht Vorgänger")
                record.update(data["changes"])
                record["backup_status"] = "Lokal geändert – A/B ausstehend"
            elif entry["event"] == "related_file":
                records[data["id"]].setdefault("related_files", []).append(data["file"])
                records[data["id"]]["backup_status"] = "Lokal geändert – A/B ausstehend"
            elif entry["event"] == "register_backup_verified":
                for identity in data["ids"]:
                    if identity in records:
                        records[identity]["backup_status"] = (
                            "A und B rückgelesen und verifiziert"
                        )
        for record in records.values():
            path = storage.child(self.root, record["original_relative"])
            if not path.is_file() or storage.sha256(path) != record["sha256"]:
                raise ArchiveError(f"Original fehlt oder verändert: {record['id']}")
            for item in record.get("related_files", []):
                if (
                    storage.sha256(storage.child(self.root, item["path"]))
                    != item["sha256"]
                ):
                    raise ArchiveError("Zugeordnete Datei verändert")
        return list(records.values())

    def ingest(self, source: Path, fields: dict) -> dict:
        source = storage.safe_path(source)
        fields = dict(fields)
        for key in (
            "direction",
            "number",
            "invoice_date",
            "partner",
            "currency",
            "source",
        ):
            if not isinstance(fields.get(key), str) or not fields[key].strip():
                raise ArchiveError(f"Pflichtangabe fehlt: {key}")
        if fields["direction"] not in ("Eingang", "Ausgang"):
            raise ArchiveError("Ungültige Belegrichtung")
        invoice_date = date.fromisoformat(fields["invoice_date"])
        if not re.fullmatch(r"[A-Z]{3}", fields["currency"]):
            raise ArchiveError("Währung muss dreistellig sein")
        if amount(fields["net"]) + amount(fields["tax"]) != amount(fields["gross"]):
            raise ArchiveError("Summen: Netto plus Steuer entspricht nicht Brutto")
        digest = storage.sha256(source)
        with storage.exclusive_lock(self.root):
            records = self.records()
            for record in records:
                if record["sha256"] == digest:
                    if record["direction"] != fields["direction"]:
                        raise ArchiveError("Identisches Original mit anderer Richtung")
                    return record
                if (
                    record["direction"] == fields["direction"]
                    and record["number"] == fields["number"]
                    and (
                        fields["direction"] == "Ausgang"
                        or record["partner"].casefold() == fields["partner"].casefold()
                    )
                ):
                    raise ArchiveError(
                        "Rechnungsnummer bereits mit anderem Original vorhanden"
                    )
            if fields["direction"] == "Ausgang" and not fields.get("historical"):
                state = self.series(invoice_date.year)
                match = re.fullmatch(
                    f"{invoice_date.year:04}{re.escape(state['separator'])}(\\d{{4}})",
                    fields["number"],
                )
                if not match or not 1 <= int(match[1]) <= 9999:
                    raise ArchiveError(
                        "Ausgangsnummer widerspricht bestätigter Jahresserie"
                    )
                if not fields.get("reviewed") or fields.get("critical_errors"):
                    raise ArchiveError(
                        "Sachliche Freigabe fehlt oder technische Fehler offen"
                    )
                sequence = int(match[1])
                if sequence > state["last"]:
                    self._append(
                        "number_reserved",
                        dict(
                            year=invoice_date.year,
                            sequence=sequence,
                            number=fields["number"],
                            reason="Übernahme vorhandener PDF24-Rechnung",
                        ),
                    )
            identity = str(uuid.uuid4())
            pending_record = None
            transactions = self.folder / "Vorgaenge"
            if transactions.exists():
                import json

                committed = {r["id"] for r in records}
                for pending in transactions.glob("*.json"):
                    item = json.loads(pending.read_text(encoding="utf-8"))
                    if item["id"] not in committed and item["sha256"] == digest:
                        if any(item.get(key) != value for key, value in fields.items()):
                            raise ArchiveError(
                                "Offener Import mit abweichenden Daten; ursprünglichen Vorgang fortsetzen"
                            )
                        identity = item["id"]
                        pending_record = item
                        break
            relative = (
                f"{fields['direction']}/{invoice_date.year:04}/{identity}/{source.name}"
            )
            destination = storage.child(self.root, relative)
            stat = source.stat()
            record = fields | dict(
                id=identity,
                original_relative=relative,
                original_filename=source.name,
                source_relative=str(source),
                sha256=digest,
                size=stat.st_size,
                source_mtime_ns=stat.st_mtime_ns,
                source_ctime_ns=stat.st_ctime_ns,
                imported_at=now(),
                actor=self.actor,
                status="freigegeben" if fields.get("reviewed") else "offen",
                backup_status="Lokal übernommen – A/B ausstehend",
            )
            transaction = self.folder / "Vorgaenge" / f"{identity}.json"
            if pending_record:
                record = pending_record
                destination = storage.child(self.root, record["original_relative"])
            else:
                storage.write_new(transaction, storage.canonical(record))
            storage.verified_copy(source, destination, digest)
            self._append("invoice_imported", {"record": record})
            return record

    def correct(
        self,
        identity: str,
        changes: dict,
        reason: str,
        event: str = "metadata_corrected",
    ) -> None:
        allowed = {
            "partner",
            "number",
            "invoice_date",
            "service_period",
            "reference",
            "payment_reference",
            "status",
            "hold",
            "related_id",
            "sent_at",
            "recipient",
        }
        if not reason.strip() or not changes or set(changes) - allowed:
            raise ArchiveError("Korrektur braucht zulässige Felder und Begründung")
        with storage.exclusive_lock(self.root):
            records = self.records()
            record = next((r for r in records if r["id"] == identity), None)
            if record is None:
                raise ArchiveError("Unbekannte Beleg-ID")
            if "invoice_date" in changes:
                date.fromisoformat(changes["invoice_date"])
            if "status" in changes and changes["status"] not in (
                "offen",
                "geprüft",
                "freigegeben",
                "versandt",
                "korrigiert",
                "storniert",
            ):
                raise ArchiveError("Unzulässiger Belegstatus")
            if changes.get("status") == "versandt" and event != "sent":
                raise ArchiveError(
                    "Versand nur mit geprüftem identischem Anhang bestätigen"
                )
            if (
                "related_id" in changes
                and changes["related_id"]
                and not any(r["id"] == changes["related_id"] for r in records)
            ):
                raise ArchiveError("Beziehung braucht vorhandene Beleg-ID")
            if "number" in changes and any(
                r["id"] != identity
                and r["direction"] == record["direction"]
                and r["number"] == changes["number"]
                and (
                    record["direction"] == "Ausgang"
                    or r["partner"] == changes.get("partner", record["partner"])
                )
                for r in records
            ):
                raise ArchiveError("Korrektur erzeugt doppelte Rechnungsnummer")
            self._append(
                event,
                dict(
                    id=identity,
                    before={k: record.get(k) for k in changes},
                    changes=changes,
                    reason=reason,
                ),
            )

    def mark_sent(
        self, identity: str, sent_date: str, recipient: str, attachment: Path
    ) -> None:
        record = next(r for r in self.records() if r["id"] == identity)
        date.fromisoformat(sent_date)
        if record["direction"] != "Ausgang" or not recipient.strip():
            raise ArchiveError("Versand braucht Ausgangsrechnung und Empfänger")
        if storage.sha256(attachment) != record["sha256"]:
            raise ArchiveError("Versand-Anhang entspricht nicht archiviertem Original")
        self.correct(
            identity,
            dict(status="versandt", sent_at=sent_date, recipient=recipient),
            "Versand bestätigt; identischer Anhang geprüft",
            "sent",
        )

    def add_related(self, identity: str, source: Path, kind: str) -> dict:
        with storage.exclusive_lock(self.root):
            record = next(r for r in self.records() if r["id"] == identity)
            digest = storage.sha256(source)
            for item in record.get("related_files", []):
                if item["sha256"] == digest and item["kind"] == kind:
                    return item
            relative = (
                str(Path(record["original_relative"]).parent.as_posix())
                + f"/Nachweise/{uuid.uuid4()}/{source.name}"
            )
            storage.verified_copy(source, storage.child(self.root, relative), digest)
            item = dict(path=relative, sha256=digest, kind=kind, filename=source.name)
            self._append("related_file", dict(id=identity, file=item))
            return item

    def search(
        self, text: str = "", first: str = "0001-01-01", last: str = "9999-12-31"
    ) -> list[dict]:
        return [
            r
            for r in self.records()
            if first <= r["invoice_date"] <= last
            and text.casefold()
            in " ".join(
                str(r.get(k, ""))
                for k in (
                    "number",
                    "partner",
                    "gross",
                    "reference",
                    "payment_reference",
                )
            ).casefold()
        ]
