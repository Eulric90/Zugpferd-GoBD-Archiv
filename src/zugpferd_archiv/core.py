"""GUI-independent fail-closed redundant archive transactions."""

from __future__ import annotations

import json
import os
import re
from contextlib import ExitStack
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .documentation import DocumentationData

from . import storage
from .errors import ArchiveError
from .journal import Journal, now
from .media import Medium, read_marker, validate_pair
from .reports import Report

CONFIG_NAME = "Archivverwaltung/Konfiguration/archive.json"


class ArchiveService:
    def __new__(cls, root: Path, progress=None):
        from .service import protected, RemoteArchive

        if protected(root):
            return RemoteArchive(root, progress)
        return super().__new__(cls)

    def __init__(self, root: Path, progress: Callable[[str], None] | None = None):
        self.root = storage.safe_path(root)
        self.progress = progress or (lambda message: None)
        from .register import actor_identity

        self.actor = actor_identity()

    def setup(self, year: int | None = None) -> None:
        year = year or date.today().year
        if not 1 <= year <= 9999:
            raise ArchiveError("Ungültiges Jahr")
        self.root.mkdir(parents=True, exist_ok=True)
        for name in (
            f"Eingang/{year:04}",
            f"Ausgang/{year:04}",
            "Archivverwaltung/Protokolle",
            "Archivverwaltung/Pruefberichte",
            "Archivverwaltung/Konfiguration",
        ):
            storage.child(self.root, name).mkdir(parents=True, exist_ok=True)

    def configure(self, a: Path, b: Path) -> None:
        self.setup()
        ma, mb = read_marker(a), read_marker(b)
        validate_pair(a, b, ma, mb)
        self._separate(a, b)
        self.records(a)
        self.records(b)
        config = {
            "schema_version": 1,
            "archive_id": ma.archive_id,
            "A": asdict(ma),
            "B": asdict(mb),
        }
        path = storage.child(self.root, CONFIG_NAME)
        with storage.exclusive_lock(self.root):
            if path.exists():
                if self.configuration() != config:
                    raise ArchiveError(
                        "Arbeitsordner ist bereits mit einem anderen Archiv verbunden"
                    )
                return
            storage.write_new(path, storage.canonical(config) + b"\n")

    def configuration(self) -> dict:
        try:
            value = json.loads(
                storage.child(self.root, CONFIG_NAME).read_text(encoding="utf-8")
            )
            if value["schema_version"] != 1:
                raise ValueError("schema")
            return value
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ArchiveError(
                "Medien müssen zuerst registriert und zugeordnet werden"
            ) from exc

    def _separate(self, a: Path, b: Path) -> None:
        for medium in (a, b):
            root, target = self.root.resolve(), storage.safe_path(medium).resolve()
            if root.is_relative_to(target) or target.is_relative_to(root):
                raise ArchiveError(
                    "Arbeitsablage und Archivmedium müssen getrennt sein"
                )
            from . import media

            if media.volume_id(root) is not None and media.volume_id(
                root
            ) == media.volume_id(target):
                raise ArchiveError(
                    "Arbeitsablage darf nicht auf einem Archivmedium liegen"
                )

    def _pair(self, a: Path, b: Path, report: Report) -> tuple[Medium, Medium]:
        Journal(
            storage.child(self.root, "Archivverwaltung/Protokolle/operations.jsonl")
        ).verify()
        config = self.configuration()
        try:
            ma, mb = Medium(**config["A"]), Medium(**config["B"])
        except (TypeError, KeyError) as exc:
            raise ArchiveError("Beschädigte Medienkonfiguration") from exc
        if config.get("archive_id") != ma.archive_id or ma.archive_id != mb.archive_id:
            raise ArchiveError("Archiv-ID in Konfiguration widerspricht den Medien")
        report.archive_id = config["archive_id"]
        report.medium_ids = {"A": ma.medium_uuid, "B": mb.medium_uuid}
        self._separate(a, b)
        return validate_pair(a, b, ma, mb)

    def _locks(self, a: Path, b: Path, stack: ExitStack) -> None:
        for root in sorted(
            (self.root, a, b), key=lambda p: str(p.resolve()).casefold()
        ):
            stack.enter_context(storage.exclusive_lock(root))

    def records(self, medium: Path) -> list[dict]:
        marker = read_marker(medium)
        manifest = storage.child(medium, "Manifest/records.jsonl")
        journal_path = storage.child(medium, "Journal/events.jsonl")
        if not manifest.is_file() or not journal_path.is_file():
            raise ArchiveError(
                "Manifest/Journal fehlt; keine automatische Neuerstellung"
            )
        entries = Journal(journal_path).verify()
        if (
            not entries
            or entries[0]["event"] != "registered"
            or entries[0]["data"] != asdict(marker)
        ):
            raise ArchiveError("Journal passt nicht zur Medienkennung")
        records = storage.read_lines(manifest)
        journal_records = [
            entry["data"] for entry in entries if entry["event"] == "archived"
        ]
        if records != journal_records:
            raise ArchiveError(
                "Manifest und Journal widersprechen sich; manuelle Prüfung erforderlich"
            )
        seen: set[str] = set()
        for record in records:
            try:
                logical = record["source_relative"]
                parts = logical.split("/")
                if (
                    len(parts) < 3
                    or parts[0] not in ("Eingang", "Ausgang")
                    or not re.fullmatch(r"\d{4}", parts[1])
                    or int(parts[1]) < 1
                    or record["archive_relative"] != self._destination(logical)
                    or record["filename"] != parts[-1]
                    or record["archive_id"] != marker.archive_id
                    or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                    or type(record["size"]) is not int
                    or record["size"] < 0
                    or type(record["source_mtime_ns"]) is not int
                    or type(record["source_ctime_ns"]) is not int
                ):
                    raise ValueError("record")
                datetime.fromisoformat(record["archived_at"])
                storage.child(medium, record["archive_relative"])
                storage.child(self.root, logical)
                if logical.casefold() in seen:
                    raise ValueError("duplicate logical path")
                seen.add(logical.casefold())
            except (KeyError, ValueError, TypeError, AttributeError) as exc:
                raise ArchiveError("Ungültiger Manifest-Eintrag") from exc
        return records

    @staticmethod
    def _destination(logical: str) -> str:
        direction, year, rest = logical.split("/", 2)
        return f"Archive/{year}/{direction}/{rest}"

    def _candidates(self) -> list[dict]:
        result = []
        seen: set[str] = set()
        for direction in ("Eingang", "Ausgang"):
            folder = storage.child(self.root, direction)
            for current, dirs, files in os.walk(folder, followlinks=False):
                for name in dirs:
                    storage.safe_path(Path(current) / name)
                for name in sorted(files):
                    source = storage.safe_path(Path(current) / name)
                    if not source.is_file():
                        raise ArchiveError(f"Keine reguläre Quelldatei: {source}")
                    logical = source.relative_to(self.root).as_posix()
                    parts = logical.split("/")
                    if (
                        len(parts) < 3
                        or not re.fullmatch(r"\d{4}", parts[1])
                        or int(parts[1]) < 1
                    ):
                        raise ArchiveError(
                            f"Quelldatei muss in Eingang/Ausgang/<Jahr> liegen: {source}"
                        )
                    if logical.casefold() in seen or ".partial-" in name:
                        raise ArchiveError(
                            f"Mehrdeutiger/reservierter Dateiname: {logical}"
                        )
                    seen.add(logical.casefold())
                    before = source.stat()
                    digest = storage.sha256(source)
                    after = source.stat()
                    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                        after.st_size,
                        after.st_mtime_ns,
                        after.st_ino,
                    ):
                        raise ArchiveError(
                            f"Quelle während Prüfung verändert: {source}"
                        )
                    result.append(
                        {
                            "schema_version": 1,
                            "source_relative": logical,
                            "filename": name,
                            "archive_relative": self._destination(logical),
                            "size": after.st_size,
                            "source_mtime_ns": after.st_mtime_ns,
                            "source_ctime_ns": after.st_ctime_ns,
                            "sha256": digest,
                            "archived_at": now(),
                        }
                    )
        return sorted(result, key=lambda record: record["source_relative"])

    def _inspect(
        self,
        medium: Path,
        records: list[dict],
        report: Report,
        allowed_untracked: dict[str, dict] | None = None,
        ignore_partials: bool = False,
    ) -> None:
        medium = storage.safe_path(medium)
        expected = {r["archive_relative"]: r for r in records}
        for relative, record in expected.items():
            path = storage.child(medium, relative)
            self.progress(f"Prüfe {path}")
            if not path.is_file():
                report.issue(
                    "missing", path, "Archivobjekt fehlt; keine automatische Reparatur"
                )
            elif (
                storage.sha256(path) != record["sha256"]
                or path.stat().st_size != record["size"]
            ):
                report.issue(
                    "changed", path, "SHA-256/Größe stimmt nicht mit Manifest überein"
                )
            else:
                report.totals["valid"] += 1
        archive = storage.child(medium, "Archive")
        if not archive.is_dir():
            raise ArchiveError(f"Archivordner fehlt: {archive}")
        for current, dirs, files in os.walk(archive, followlinks=False):
            for name in dirs:
                storage.safe_path(Path(current) / name)
            for name in files:
                path = storage.safe_path(Path(current) / name)
                relative = path.relative_to(medium).as_posix()
                if ".partial-" in name:
                    if not ignore_partials:
                        report.issue(
                            "interrupted",
                            path,
                            "Temporäre Kopie; niemals als Original akzeptiert",
                        )
                    elif not any(w["path"] == str(path) for w in report.warnings):
                        report.warnings.append(
                            {
                                "kind": "interrupted",
                                "path": str(path),
                                "detail": "Temporäre Kopie erhalten; manuell prüfen",
                            }
                        )
                elif relative not in expected:
                    candidate = (allowed_untracked or {}).get(relative)
                    if candidate and storage.sha256(path) == candidate["sha256"]:
                        continue  # Verified orphan from a crash is explicitly journaled during backup.
                    report.issue(
                        "conflicting" if candidate else "unexpected",
                        path,
                        "Vorhandenes Ziel widerspricht der Quelle; kein Überschreiben"
                        if candidate
                        else "Objekt ohne passenden Manifest-Eintrag",
                    )

    def _compare_records(
        self, ra: list[dict], rb: list[dict], report: Report, require_equal: bool = True
    ) -> None:
        da = {r["source_relative"]: r for r in ra}
        db = {r["source_relative"]: r for r in rb}
        for logical in sorted(da.keys() | db.keys()):
            if logical not in da or logical not in db:
                if require_equal:
                    report.issue(
                        "conflicting",
                        logical,
                        "Manifest-Eintrag nur auf einem Medium vorhanden",
                    )
            elif da[logical] != db[logical]:
                report.issue("conflicting", logical, "A/B-Metadaten widersprechen sich")

    def _finish(
        self, report: Report, a: Path | None = None, b: Path | None = None
    ) -> Report:
        report.actor_sid = self.actor
        report.success = not report.exceptions
        folder = storage.child(self.root, "Archivverwaltung/Pruefberichte")
        report.save(folder)
        # Reports are not invoice history. Failures to persist them on either medium
        # mean the operation cannot be advertised as a complete success.
        if a is not None and b is not None:
            for medium in (a, b):
                try:
                    report.save(storage.child(medium, "Pruefberichte"))
                except (OSError, ArchiveError) as exc:
                    report.issue("report_error", medium, str(exc))
            if report.exceptions:
                report.success = False
                report.save(folder)
        # Expose the local report path to the UI, even if media reports were written.
        if report.report_json and not report.report_json.is_relative_to(folder):
            report.save(folder)
        Journal(
            storage.child(self.root, "Archivverwaltung/Protokolle/operations.jsonl")
        ).append(report.operation, report.data())
        return report

    def backup(self, a: Path, b: Path) -> Report:
        report = Report("backup")
        self.setup()
        try:
            self._pair(a, b, report)
            with ExitStack() as stack:
                self._locks(a, b, stack)
                self._pair(a, b, report)
                ra, rb = self.records(a), self.records(b)
                candidates = self._candidates()
                report.totals["candidates"] = len(candidates)
                histories = {r["source_relative"]: r for r in ra + rb}
                case_history = {logical.casefold(): logical for logical in histories}
                for candidate in candidates:
                    candidate["archive_id"] = report.archive_id
                    logical = candidate["source_relative"]
                    if (
                        logical.casefold() in case_history
                        and case_history[logical.casefold()] != logical
                    ):
                        report.issue(
                            "conflicting",
                            logical,
                            "Schreibweise des archivierten Quellpfads geändert; Historie bleibt erhalten",
                        )
                    old = histories.get(candidate["source_relative"])
                    if old and (
                        old["sha256"] != candidate["sha256"]
                        or old["size"] != candidate["size"]
                    ):
                        report.issue(
                            "changed_source",
                            candidate["source_relative"],
                            "Quelle geändert; bestehende Historie bleibt erhalten",
                        )
                self._compare_records(ra, rb, report, require_equal=False)
                from .documentation import (
                    audit_documentations,
                    audit_local_documentation,
                )

                audit_documentations(a, b, report)
                audit_local_documentation(self.root, report)
                if (self.root / "Archivverwaltung/Register/events.jsonl").exists():
                    from .register import Register
                    from .snapshots import audit_snapshots

                    Register(self.root).records()
                    report.warnings.extend(
                        audit_snapshots(self.root, a, b, require_equal=False)
                    )
                allowed = {r["archive_relative"]: r for r in candidates}
                self._inspect(a, ra, report, allowed, ignore_partials=True)
                self._inspect(b, rb, report, allowed, ignore_partials=True)
                # Source removal after partial replication must not produce success.
                missing_candidates = (
                    set(r["source_relative"] for r in ra)
                    ^ set(r["source_relative"] for r in rb)
                ) - set(r["source_relative"] for r in candidates)
                for logical in sorted(missing_candidates):
                    report.issue(
                        "conflicting",
                        logical,
                        "Unvollständige Replikation, Quelle fehlt",
                    )
                if report.exceptions:
                    for medium in (a, b):
                        Journal(medium / "Journal/events.jsonl").append(
                            "backup_rejected", report.data()
                        )
                else:
                    by_medium = {
                        a: {r["source_relative"]: r for r in ra},
                        b: {r["source_relative"]: r for r in rb},
                    }
                    for candidate in candidates:
                        logical = candidate["source_relative"]
                        record = histories.get(logical, candidate)
                        source = storage.child(self.root, logical)
                        for medium in (a, b):
                            self._pair(a, b, report)
                            self.progress(f"Archiviere {logical} auf {medium}")
                            existing_record = by_medium[medium].get(logical)
                            copied = storage.verified_copy(
                                source,
                                storage.child(medium, record["archive_relative"]),
                                record["sha256"],
                            )
                            self._pair(a, b, report)
                            report.totals["verified"] += 1
                            report.totals[
                                "copied" if copied else "already_archived"
                            ] += 1
                            if not existing_record:
                                storage.append_line(
                                    medium / "Manifest/records.jsonl", record
                                )
                                Journal(medium / "Journal/events.jsonl").append(
                                    "archived", record
                                )
                                by_medium[medium][logical] = record
                    # Final audit before declaring redundancy, also detects media/source races.
                    final_a, final_b = self.records(a), self.records(b)
                    self._inspect(a, final_a, report, ignore_partials=True)
                    self._inspect(b, final_b, report, ignore_partials=True)
                    self._compare_records(final_a, final_b, report)
                    for candidate in candidates:
                        if (
                            storage.sha256(
                                storage.child(self.root, candidate["source_relative"])
                            )
                            != candidate["sha256"]
                        ):
                            report.issue(
                                "changed_source",
                                candidate["source_relative"],
                                "Quelle während Lauf geändert",
                            )
                    self._pair(a, b, report)
                    if (self.root / "Archivverwaltung/Register/events.jsonl").exists():
                        from .snapshots import (
                            create_snapshot,
                            replicate_snapshot,
                            FOLDER,
                            resume_snapshot,
                        )

                        snapshot_folder = storage.child(self.root, FOLDER)
                        if snapshot_folder.exists():
                            for previous in snapshot_folder.iterdir():
                                resume_snapshot(previous, self.root)
                                replicate_snapshot(
                                    previous, a, b, lambda: self._pair(a, b, report)
                                )
                        key_folder = self.root.parent / (
                            "." + self.root.name + "-Schluessel"
                        )
                        snapshot = create_snapshot(self.root, key_folder)
                        replicate_snapshot(
                            snapshot, a, b, lambda: self._pair(a, b, report)
                        )
                        report.warnings.extend(audit_snapshots(self.root, a, b))
                        if not report.exceptions:
                            Register(self.root, actor=self.actor)._append(
                                "register_backup_verified",
                                dict(
                                    ids=[
                                        r["id"] for r in Register(self.root).records()
                                    ],
                                    snapshot=snapshot.name,
                                    media=report.medium_ids,
                                ),
                            )
                    report.success = not report.exceptions
                    for medium in (a, b):
                        Journal(medium / "Journal/events.jsonl").append(
                            "backup_completed"
                            if not report.exceptions
                            else "backup_failed",
                            report.data(),
                        )
                return self._finish(report, a, b)
        except (OSError, ArchiveError) as exc:
            report.issue("error", "", str(exc))
            # Do not write reports onto media after identity validation has failed.
            return self._finish(report)

    def _audit(self, a: Path, b: Path, report: Report) -> tuple[list[dict], list[dict]]:
        self._pair(a, b, report)
        ra, rb = self.records(a), self.records(b)
        self._inspect(a, ra, report)
        self._inspect(b, rb, report)
        self._compare_records(ra, rb, report)
        from .documentation import audit_documentations, audit_local_documentation

        audit_documentations(a, b, report)
        audit_local_documentation(self.root, report)
        if (self.root / "Archivverwaltung/Register/events.jsonl").exists():
            from .register import Register
            from .snapshots import audit_snapshots

            Register(self.root).records()
            for warning in audit_snapshots(self.root, a, b):
                report.issue("interrupted", warning["path"], warning["detail"])
        self._pair(a, b, report)
        return ra, rb

    def _check(self, a: Path, b: Path, operation: str) -> Report:
        report = Report(operation)
        self.setup()
        try:
            self._pair(a, b, report)
            with ExitStack() as stack:
                self._locks(a, b, stack)
                self._audit(a, b, report)
                return self._finish(report, a, b)
        except (OSError, ArchiveError) as exc:
            report.issue("error", "", str(exc))
            return self._finish(report)

    def check(self, a: Path, b: Path) -> Report:
        return self._check(a, b, "integrity")

    def compare(self, a: Path, b: Path) -> Report:
        return self._check(a, b, "comparison")

    def create_documentation(self, a: Path, b: Path, data: DocumentationData) -> Report:
        from .documentation import save_documentation

        return save_documentation(self, a, b, data)

    def last_backup(self) -> dict | None:
        rows = Journal(
            storage.child(self.root, "Archivverwaltung/Protokolle/operations.jsonl")
        ).verify()
        backups = [row["data"] for row in rows if row["event"] == "backup"]
        return backups[-1] if backups else None

    def last_backup_success(self) -> dict | None:
        last = self.last_backup()
        return last if last and last["success"] else None

    def export(
        self,
        a: Path,
        b: Path,
        destination: Path,
        first_year: int,
        last_year: int,
        first_date: date | None = None,
        last_date: date | None = None,
    ) -> Report:
        report = Report("export")
        self.setup()
        try:
            self._pair(a, b, report)
            destination = storage.safe_path(destination)
            if not 1 <= first_year <= last_year <= 9999:
                raise ArchiveError("Ungültiger Jahresbereich")
            if first_date and last_date and first_date > last_date:
                raise ArchiveError("Ungültiger Datumsbereich")
            if destination.exists():
                raise ArchiveError(
                    "Export erfordert einen neuen Zielordner; kein Überschreiben"
                )
            for root in (self.root, a, b):
                if destination.is_relative_to(
                    root.resolve()
                ) or root.resolve().is_relative_to(destination):
                    raise ArchiveError(
                        "Export muss außerhalb von Arbeitsablage und Archivmedien liegen"
                    )
            with ExitStack() as stack:
                self._locks(a, b, stack)
                records, _ = self._audit(a, b, report)
                if report.exceptions:
                    return self._finish(report)
                selected = [
                    r
                    for r in records
                    if first_year
                    <= int(r["source_relative"].split("/")[1])
                    <= last_year
                    and (
                        not first_date
                        or datetime.fromisoformat(r["archived_at"]).date() >= first_date
                    )
                    and (
                        not last_date
                        or datetime.fromisoformat(r["archived_at"]).date() <= last_date
                    )
                ]
                destination.mkdir(parents=True, exist_ok=False)
                report.totals["candidates"] = len(selected)
                for record in selected:
                    self._pair(a, b, report)
                    target = storage.child(
                        destination, "Originale/" + record["source_relative"]
                    )
                    storage.verified_copy(
                        storage.child(a, record["archive_relative"]),
                        target,
                        record["sha256"],
                    )
                    report.totals["verified"] += 1
                index = {
                    "schema_version": 1,
                    "archive_id": report.archive_id,
                    "medium_ids": report.medium_ids,
                    "exported_at": now(),
                    "year_range": [first_year, last_year],
                    "archive_date_range": [
                        str(first_date) if first_date else None,
                        str(last_date) if last_date else None,
                    ],
                    "records": selected,
                }
                storage.write_new(
                    destination / "index.json", storage.canonical(index) + b"\n"
                )
                # Re-read every exported original and the portable index.
                if (
                    json.loads((destination / "index.json").read_text(encoding="utf-8"))
                    != index
                ):
                    raise ArchiveError("Exportindex konnte nicht verifiziert werden")
                for record in selected:
                    if (
                        storage.sha256(
                            storage.child(
                                destination, "Originale/" + record["source_relative"]
                            )
                        )
                        != record["sha256"]
                    ):
                        raise ArchiveError("Exportprüfung fehlgeschlagen")
                report.success = True
                report.save(destination / "Pruefberichte")
                return self._finish(report)
        except (OSError, ArchiveError) as exc:
            report.issue("error", destination, str(exc))
            return self._finish(report)
